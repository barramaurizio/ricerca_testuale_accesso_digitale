# -*- coding: utf-8 -*-
"""RTAD OCR — Windows.Media.Ocr + EasyOCR + Google Vision, cache locale, gemello SA/Add-on.

Motori:
  1) Windows.Media.Ocr (Win10+, predefinito) — winrt/winsdk oppure PowerShell
  2) EasyOCR (opzionale, pip install easyocr) — scritte stilizzate in locale
  3) Google Cloud Vision (chiave API personale dell’utente) — grafiche difficili

Usato solo se l'utente attiva la casella OCR nella ricerca.
Google Vision: ogni utente inserisce la propria chiave (nessuna chiave condivisa nel software).

Dalla 1.6.3: analisi visiva (etichette/oggetti/colori), descrizione accessibile
in italiano e scheda tecnica (dimensioni/EXIF) — opt-in, stessa chiave Vision.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# Limiti anti-blocco (allineati allo spirito 1.5.5 / 1.5.6)
MAX_OCR_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_OCR_PDF_PAGES = 8
OCR_SOFT_TIMEOUT_SEC = 35
# v17: Google retry anche fascia bassa/margini + merge pezzi OCR; clear cache da menu
OCR_CACHE_VERSION = 17
# Cache separata per etichette/descrizione Vision (1.6.3)
VISION_CACHE_VERSION = 1

ENGINE_WINDOWS = "windows"
ENGINE_EASYOCR = "easyocr"
ENGINE_GOOGLE = "google"

_GOOGLE_VISION_URL = "https://vision.googleapis.com/v1/images:annotate"
# Gemini (Google AI Studio) — descrizione avanzata accessibile (1.6.3)
# Preferenza: Flash 3.x (attuali). I 1.5/2.0 spesso danno 404 su chiavi nuove.
_GEMINI_MODELS_PREFERRED = (
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)
_GEMINI_TIMEOUT_SEC = 75
_gemini_models_cache = None  # elenco scoperto via ListModels (per chiave)
_gemini_models_cache_key = ""

_IMG_EXTS = {
    ".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".gif",
    ".tif", ".tiff", ".webp", ".ico",
}

_cache_dir = ""
_cache_lock = threading.Lock()
_engine_checked = False
_engine_ok = False
_engine_note = ""
_preferred_engine = ENGINE_WINDOWS
_easyocr_checked = False
_easyocr_ok = False
_easyocr_note = ""
_easyocr_reader = None
_easyocr_lock = threading.Lock()
_google_api_key = ""
_google_last_error = ""
_gemini_api_key = ""
_gemini_last_error = ""
_ps_script_path = None
_stats = {
    "images_ocr": 0,
    "pdf_pages_ocr": 0,
    "cache_hits": 0,
    "failures": 0,
    "unavailable": 0,
    "google_calls": 0,
    "gemini_calls": 0,
}


def configure(cache_dir: str) -> None:
    """Imposta la cartella cache (es. CONFIG_DIR/ocr_cache)."""
    global _cache_dir
    _cache_dir = cache_dir or ""
    if _cache_dir:
        try:
            os.makedirs(_cache_dir, exist_ok=True)
        except Exception:
            pass


def get_ocr_cache_dir() -> str:
    """Cartella cache OCR configurata (può essere vuota)."""
    return _cache_dir or ""


def get_ocr_cache_count() -> int:
    """Numero di file .json nella cache OCR."""
    d = _cache_dir
    if not d or not os.path.isdir(d):
        return 0
    try:
        return sum(
            1
            for name in os.listdir(d)
            if name.endswith(".json") and os.path.isfile(os.path.join(d, name))
        )
    except Exception:
        return 0


def clear_ocr_cache() -> int:
    """Elimina i file della cache OCR. Restituisce quanti file rimossi."""
    d = _cache_dir
    if not d or not os.path.isdir(d):
        return 0
    removed = 0
    with _cache_lock:
        try:
            names = list(os.listdir(d))
        except Exception:
            return 0
        for name in names:
            if not name.endswith(".json"):
                continue
            path = os.path.join(d, name)
            try:
                if os.path.isfile(path):
                    os.unlink(path)
                    removed += 1
            except Exception:
                pass
    return removed


def reset_stats() -> None:
    for k in _stats:
        _stats[k] = 0


def get_stats() -> dict:
    return dict(_stats)


def supported_image_exts() -> tuple:
    return tuple(sorted(_IMG_EXTS))


def is_image_path(path: str) -> bool:
    if not path:
        return False
    return os.path.splitext(path)[1].lower() in _IMG_EXTS


def set_engine_preference(name: str) -> str:
    """Imposta il motore: 'windows' | 'easyocr' | 'google'. Restituisce quello effettivo."""
    global _preferred_engine, _engine_checked
    n = (name or ENGINE_WINDOWS).strip().lower()
    if n in ("easy", "easy-ocr", "easy_ocr"):
        n = ENGINE_EASYOCR
    if n in ("google", "google-vision", "google_vision", "vision", "gcv"):
        n = ENGINE_GOOGLE
    if n not in (ENGINE_WINDOWS, ENGINE_EASYOCR, ENGINE_GOOGLE):
        n = ENGINE_WINDOWS
    _preferred_engine = n
    _engine_checked = False
    return _preferred_engine


def get_engine_preference() -> str:
    return _preferred_engine or ENGINE_WINDOWS


def set_google_api_key(key: str) -> None:
    """Imposta la chiave API Google Vision (solo in memoria di processo; salvataggio lato UI)."""
    global _google_api_key, _google_last_error
    _google_api_key = (key or "").strip()
    _google_last_error = ""


def get_google_api_key() -> str:
    return _google_api_key or ""


def has_google_api_key() -> bool:
    return bool((_google_api_key or "").strip())


def set_gemini_api_key(key: str) -> None:
    """Imposta la chiave API Gemini (Google AI Studio), personale dell’utente."""
    global _gemini_api_key, _gemini_last_error
    global _gemini_models_cache, _gemini_models_cache_key
    _gemini_api_key = (key or "").strip()
    _gemini_last_error = ""
    # Nuova chiave → riscopri i modelli disponibili
    _gemini_models_cache = None
    _gemini_models_cache_key = ""


def get_gemini_api_key() -> str:
    return _gemini_api_key or ""


def has_gemini_api_key() -> bool:
    return bool((_gemini_api_key or "").strip())


def gemini_last_error() -> str:
    return _gemini_last_error or ""


def google_available(force_recheck: bool = False) -> bool:
    """True se c’è una chiave API configurata (la validità si verifica al primo uso)."""
    global _google_last_error
    if force_recheck:
        _google_last_error = ""
    return has_google_api_key()


def easyocr_available(force_recheck: bool = False) -> bool:
    """True se il modulo EasyOCR è importabile (modelli scaricati al primo uso)."""
    global _easyocr_checked, _easyocr_ok, _easyocr_note
    if _easyocr_checked and not force_recheck:
        return _easyocr_ok
    _easyocr_checked = True
    _easyocr_ok = False
    _easyocr_note = ""
    try:
        import easyocr  # noqa: F401
        _easyocr_ok = True
        _easyocr_note = f"EasyOCR ({getattr(easyocr, '__version__', '?')})"
        return True
    except Exception as e:
        _easyocr_note = (
            "EasyOCR non installato. Nella Standalone: "
            "pip install -r requirements-ocr-easy.txt "
            f"(dettaglio: {e})"
        )
        return False


def _windows_engine_available(force_recheck: bool = False) -> bool:
    """Probe solo Windows.Media.Ocr (winrt / PowerShell)."""
    global _engine_checked, _engine_ok, _engine_note
    # Nota: riusiamo _engine_ok/_note per lo stato Windows; EasyOCR ha i suoi flag.
    if _engine_checked and not force_recheck:
        return _engine_ok
    _engine_checked = True
    _engine_ok = False
    _engine_note = ""
    if os.name != "nt":
        _engine_note = "OCR Windows disponibile solo su Windows."
        return False
    if _try_winrt_probe():
        _engine_ok = True
        _engine_note = "Windows.Media.Ocr (winrt)"
        return True
    ok, note = _try_powershell_probe()
    if ok:
        _engine_ok = True
        _engine_note = note or "Windows.Media.Ocr (PowerShell)"
        return True
    _engine_note = note or (
        "OCR Windows non disponibile. Installa il pacchetto lingua OCR "
        "da Impostazioni → Ora e lingua → Lingua e area geografica."
    )
    return False


def active_engine() -> str:
    """Motore che verrà usato adesso (con eventuale fallback)."""
    pref = get_engine_preference()
    if pref == ENGINE_GOOGLE:
        if google_available():
            return ENGINE_GOOGLE
        # senza chiave: fallback locale se possibile
        if _windows_engine_available():
            return ENGINE_WINDOWS
        if easyocr_available():
            return ENGINE_EASYOCR
        return ENGINE_GOOGLE
    if pref == ENGINE_EASYOCR:
        if easyocr_available():
            return ENGINE_EASYOCR
        if _windows_engine_available():
            return ENGINE_WINDOWS
        return ENGINE_EASYOCR
    if _windows_engine_available():
        return ENGINE_WINDOWS
    if easyocr_available():
        return ENGINE_EASYOCR
    if google_available():
        return ENGINE_GOOGLE
    return ENGINE_WINDOWS


def engine_available(force_recheck: bool = False) -> bool:
    """True se almeno un motore OCR utilizzabile è disponibile per la preferenza."""
    pref = get_engine_preference()
    if pref == ENGINE_GOOGLE:
        if google_available(force_recheck=force_recheck):
            return True
        if _windows_engine_available(force_recheck=force_recheck):
            return True
        return easyocr_available(force_recheck=force_recheck)
    if pref == ENGINE_EASYOCR:
        if easyocr_available(force_recheck=force_recheck):
            return True
        return _windows_engine_available(force_recheck=force_recheck)
    if _windows_engine_available(force_recheck=force_recheck):
        return True
    return easyocr_available(force_recheck=force_recheck)


def engine_status_message() -> str:
    pref = get_engine_preference()
    win_ok = _windows_engine_available()
    easy_ok = easyocr_available()
    google_ok = google_available()
    active = active_engine()
    if pref == ENGINE_GOOGLE:
        if google_ok and active == ENGINE_GOOGLE:
            return (
                "OCR Google Cloud Vision pronto (chiave API personale configurata). "
                "Serve Internet; le richieste contano sul tuo account Google Cloud."
            )
        if not google_ok:
            base = (
                "Google Vision: inserisci la tua chiave API "
                "(Strumenti → Chiave API Google Vision, oppure il pulsante Chiave Google)."
            )
            if win_ok:
                return base + f" Nel frattempo uso Windows OCR ({_engine_note})."
            if easy_ok:
                return base + f" Nel frattempo uso EasyOCR ({_easyocr_note})."
            return base
        return "Google Vision selezionato."
    if pref == ENGINE_EASYOCR:
        if easy_ok and active == ENGINE_EASYOCR:
            return (
                f"OCR EasyOCR pronto ({_easyocr_note}). "
                "Al primo uso scarica i modelli (serve Internet)."
            )
        if easy_ok:
            return f"EasyOCR installato ({_easyocr_note})."
        if win_ok:
            return (
                f"EasyOCR non disponibile — uso Windows OCR ({_engine_note}). "
                f"{_easyocr_note}"
            )
        return _easyocr_note or "Nessun motore OCR disponibile."
    # preferenza Windows
    if win_ok and active == ENGINE_WINDOWS:
        extras = []
        if easy_ok:
            extras.append("EasyOCR")
        if google_ok:
            extras.append("Google Vision")
        extra = ""
        if extras:
            extra = " Altri motori selezionabili: " + ", ".join(extras) + "."
        return f"OCR Windows pronto ({_engine_note}).{extra}"
    if easy_ok:
        return (
            f"OCR Windows non disponibile — posso usare EasyOCR ({_easyocr_note})."
        )
    if google_ok:
        return "OCR Windows non disponibile — posso usare Google Cloud Vision (chiave presente)."
    return _engine_note or "OCR Windows non disponibile."


def ocr_image_file(path: str, should_abort=None, hint_terms=None) -> str:
    """OCR su file immagine. Restituisce testo (può essere vuoto). Usa cache.

    Per grafica difficile (stripes, font stilizzati, testo verticale) prova
    più varianti preprocessate (scala di grigi, ritaglio basso, rotazioni).
    hint_terms: se forniti, interrompe appena tutti i termini compaiono.
    """
    if not path or not os.path.isfile(path):
        return ""
    if should_abort and should_abort():
        return ""
    if not is_image_path(path):
        return ""
    try:
        size = os.path.getsize(path)
    except Exception:
        size = -1
    if size < 0 or size > MAX_OCR_IMAGE_BYTES:
        return ""
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = 0.0

    cache_key = _cache_key_for_file(path, size, mtime)
    cached = _cache_get(cache_key)
    if cached is not None:
        _stats["cache_hits"] += 1
        return cached

    if not engine_available():
        _stats["unavailable"] += 1
        return ""

    text = ""
    temps = []
    ocr_ok = False
    last_diag = ""
    eng = active_engine()
    try:
        # WinRT/StorageFile spesso fallisce con emoji/unicode nei path
        # (es. "Buon compleanno … 🎂.jpg") → copia su temp ASCII.
        work_path = _ascii_safe_copy(path, temps)
        # Google Vision: prima l’originale (1 chiamata). Se la query non matcha,
        # ritenta poche varianti preprocess (font a strisce / contrasto).
        # EasyOCR: ~10 slot; Windows: più varianti preprocess.
        if eng == ENGINE_GOOGLE:
            # Originale + ritentativi fasce titolo/basa/margini (Vision a pagamento)
            max_var = 8
            variants = [work_path]
        elif eng == ENGINE_EASYOCR:
            max_var = 10
            variants = _build_image_variants(work_path, temps, max_variants=max_var)
        else:
            max_var = 14
            variants = _build_image_variants(work_path, temps, max_variants=max_var)
        chunks = []
        empty_errs = []
        google_extra_tried = False
        vi = 0
        while vi < len(variants):
            vp = variants[vi]
            vi += 1
            if should_abort and should_abort():
                break
            try:
                piece, diag = _ocr_path_impl(
                    vp,
                    should_abort=should_abort,
                    with_diag=True,
                    hint_terms=hint_terms,
                )
                piece = piece or ""
                if diag and not piece:
                    empty_errs.append(diag)
            except Exception as e:
                logging.debug(f"OCR variante fallita ({vp}): {e}")
                piece = ""
                empty_errs.append(str(e))
            if piece.strip():
                chunks.append(piece.strip())
                # Match termini anche sul reverse (testo ruotato)
                if hint_terms and ocr_text_matches_terms(
                    piece + "\n" + piece[::-1], hint_terms
                ):
                    matching = [
                        c for c in chunks
                        if ocr_text_matches_terms(c + "\n" + c[::-1], hint_terms)
                    ]
                    text = _pick_best_ocr_text(matching or chunks, hint_terms)
                    break
            # Google: se dopo l’originale la query non c’è, aggiungi varianti preprocess
            if (
                eng == ENGINE_GOOGLE
                and hint_terms
                and not google_extra_tried
                and vi >= len(variants)
            ):
                merged_so_far = "\n".join(chunks)
                if not ocr_text_matches_terms(
                    merged_so_far + "\n" + merged_so_far[::-1], hint_terms
                ):
                    google_extra_tried = True
                    # Prima fascia titolo (poster/grafiche), poi le altre varianti
                    extra = _build_google_retry_variants(
                        work_path, temps, max_variants=max_var
                    )
                    for ep in extra:
                        if ep not in variants:
                            variants.append(ep)
                    if len(variants) < max_var:
                        more = _build_image_variants(
                            work_path, temps, max_variants=max_var
                        )
                        for ep in more:
                            if ep not in variants and len(variants) < max_var:
                                variants.append(ep)
        else:
            text = _pick_best_ocr_text(chunks, hint_terms)
        _stats["images_ocr"] += 1
        ocr_ok = True
        if text:
            preview = " ".join(text.split())[:120]
            logging.info(
                f"OCR OK ({len(text)} car.) su {os.path.basename(path)} "
                f"motore={eng} con {len(variants)} varianti | anteprima: {preview!r}"
            )
        else:
            if empty_errs:
                last_diag = empty_errs[0][:240]
            logging.info(
                f"OCR vuoto su {os.path.basename(path)} "
                f"({len(variants)} varianti, motore={eng}"
                f"{'; diag=' + last_diag if last_diag else ''})"
            )
    except Exception as e:
        logging.info(f"OCR immagine fallito ({path}): {e}")
        _stats["failures"] += 1
        text = ""
        ocr_ok = False
    finally:
        for t in temps:
            try:
                os.unlink(t)
            except Exception:
                pass

    # Cache solo OCR riuscito (anche testo vuoto genuino). Mai i fallimenti.
    if ocr_ok:
        _cache_put(cache_key, text)
    return text


def ocr_image_bytes(data: bytes, *, suffix: str = ".jpg", cache_key: str = "") -> str:
    """OCR su bytes immagine (es. JPEG/PNG estratti da PDF)."""
    if not data:
        return ""
    if len(data) > MAX_OCR_IMAGE_BYTES:
        return ""
    key = cache_key or ("bytes:" + hashlib.sha1(data).hexdigest())
    cached = _cache_get(key)
    if cached is not None:
        _stats["cache_hits"] += 1
        return cached
    if not engine_available():
        _stats["unavailable"] += 1
        return ""
    tmp = None
    text = ""
    ocr_ok = False
    try:
        fd, tmp = tempfile.mkstemp(suffix=suffix or ".jpg", prefix="rtad_ocr_")
        os.write(fd, data)
        os.close(fd)
        text = _ocr_path_impl(tmp) or ""
        _stats["pdf_pages_ocr"] += 1
        ocr_ok = True
    except Exception as e:
        logging.debug(f"OCR bytes fallito: {e}")
        _stats["failures"] += 1
        text = ""
        ocr_ok = False
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:
                pass
    if ocr_ok:
        _cache_put(key, text)
    return text


def ocr_pdf_image_records(records, *, max_pages: int = MAX_OCR_PDF_PAGES, should_abort=None) -> str:
    """OCR sulle immagini pagina estratte da un PDF (record kind jpeg|rgb).

    records: lista dict con chiavi w/h/kind/data come extract_images_from_pdf.
    """
    if not records:
        return ""
    if not engine_available():
        _stats["unavailable"] += 1
        return ""
    parts = []
    n = 0
    for rec in records:
        if should_abort and should_abort():
            break
        if n >= max_pages:
            break
        if not isinstance(rec, dict):
            continue
        kind = rec.get("kind")
        data = rec.get("data") or b""
        if not data:
            continue
        if kind == "jpeg":
            chunk = ocr_image_bytes(
                data,
                suffix=".jpg",
                cache_key="pdfjpg:" + hashlib.sha1(data).hexdigest(),
            )
        elif kind == "rgb":
            png = _rgb_to_png_bytes(data, int(rec.get("w") or 0), int(rec.get("h") or 0))
            if not png:
                continue
            chunk = ocr_image_bytes(
                png,
                suffix=".png",
                cache_key="pdfrgb:" + hashlib.sha1(png).hexdigest(),
            )
        else:
            continue
        if chunk and chunk.strip():
            parts.append(chunk.strip())
            n += 1
    return "\n".join(parts)


def snippet_from_ocr_text(text: str, terms, max_len: int = 200) -> str:
    """Estrae uno snippet intorno al primo termine trovato (anche reverse/OCR-fold/sinonimi)."""
    if not text:
        return ""
    low_src = text.lower()
    pos = -1
    for t in terms or []:
        if not t:
            continue
        for cand in _ocr_term_alternatives(str(t)):
            pos = low_src.find(cand)
            if pos >= 0:
                break
            pos = low_src.find(cand[::-1])
            if pos >= 0:
                break
        if pos >= 0:
            break
    if pos < 0:
        folded = _ocr_fold(text)
        for t in terms or []:
            if not t:
                continue
            for cand in _ocr_term_alternatives(str(t)):
                tf = _ocr_fold(cand)
                if tf and (tf in folded or tf[::-1] in folded):
                    return " ".join(text.split())[:max_len]
        return " ".join(text.split())[:max_len]
    a = max(0, pos - 40)
    b = min(len(text), pos + max_len - 40)
    return " ".join(text[a:b].split())[:max_len]


def _ocr_fold(text: str) -> str:
    """Normalizza confusabili tipici OCR Windows (0/O, 1/I/l, …)."""
    if not text:
        return ""
    import unicodedata
    t = text.lower()
    # Togli accenti: sarò→saro (junk/canzone)
    t = "".join(
        c for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    )
    repl = str.maketrans({
        "0": "o",
        "1": "i",
        "2": "z",
        "3": "e",
        "4": "a",
        "5": "s",
        "6": "g",
        "7": "t",
        "8": "b",
        "9": "g",
        "|": "i",
        "!": "i",
        "l": "i",  # OCR confonde spesso l minuscola con I
        "$": "s",
        "@": "a",
        "€": "e",
    })
    t = t.translate(repl)
    return "".join(ch for ch in t if ch.isalnum())


# Gruppi di lettere che Windows OCR scambia spesso sulle grafiche stilizzate
_OCR_CONFUSABLES = {
    "a": "a4@w",
    "b": "b8",
    "c": "c",
    "d": "d",
    "e": "e3",
    "f": "f",
    "g": "g69",
    "h": "h",
    "i": "i1l|!",
    "j": "j",
    "k": "k",
    "m": "m",
    "n": "n",
    "o": "o0",
    "p": "p",
    "q": "q",
    "r": "r",
    "s": "s5$",
    "t": "t7",
    "u": "uv",
    "v": "vu",
    "w": "wa",
    "x": "x",
    "y": "yv",
    "z": "z2",
}


def _ocr_chars_match(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    if a == b:
        return True
    ga = _OCR_CONFUSABLES.get(a, a)
    gb = _OCR_CONFUSABLES.get(b, b)
    return a in gb or b in ga


def _ocr_edit_distance(a: str, b: str) -> int:
    """Distanza di Levenshtein con uguaglianza confusabile OCR."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(a) + 1))
    for i, cb in enumerate(b, 1):
        cur = [i]
        for j, ca in enumerate(a, 1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if _ocr_chars_match(ca, cb) else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def _ocr_fuzzy_term_in(hay_fold: str, term_fold: str) -> bool:
    """Match fuzzy: sottostringa esatta o edit-distance su finestre.

    Copre casi come Windows OCR che legge BIRTHDAY come fiBlRTHDW / BRTHDW,
    e Vision che su font a strisce legge SQUADLIST come SQUADST.
    Evita falsi positivi tipo «tribunale» al contrario (…birt…) ≈ birthd.
    """
    if not term_fold:
        return False
    if term_fold in hay_fold or term_fold[::-1] in hay_fold:
        return True
    n = len(term_fold)
    if n < 5:
        return False
    # Termine lungo: più tolleranza (Vision/OCR spesso saltano 1–2 lettere stilizzate)
    if n <= 6:
        max_err = 1
        win_slack = 1
    elif n <= 9:
        max_err = 2
        win_slack = 2
    else:
        max_err = 3
        win_slack = 2
    targets = [(term_fold, max_err)]
    if n >= 7:
        targets.append((term_fold[:-1], min(1, max_err)))
    for target, te in targets:
        tn = len(target)
        for i in range(len(hay_fold)):
            if not _ocr_chars_match(hay_fold[i], target[0]):
                continue
            for wlen in range(tn - win_slack, tn + win_slack + 1):
                if wlen < 4 or i + wlen > len(hay_fold):
                    continue
                if abs(wlen - tn) > win_slack:
                    continue
                if _ocr_edit_distance(hay_fold[i : i + wlen], target) <= te:
                    logging.debug(
                        f"OCR fuzzy hit: term={term_fold!r} "
                        f"window={hay_fold[i:i + wlen]!r}"
                    )
                    return True
    # Lettere mancanti in mezzo: «squadst» ⊆ «squadlist» (font a strisce → LIST→ST)
    if n >= 7 and _ocr_missing_letters_hit(hay_fold, term_fold):
        logging.debug(
            f"OCR missing-letters hit: term={term_fold!r} hay≈{hay_fold[:40]!r}"
        )
        return True
    return False


def _ocr_is_subsequence(short: str, long: str) -> bool:
    """True se tutti i caratteri di short compaiono in ordine in long."""
    if not short:
        return True
    if not long or len(short) > len(long):
        return False
    j = 0
    for ch in long:
        if _ocr_chars_match(ch, short[j]):
            j += 1
            if j >= len(short):
                return True
    return False


def _ocr_missing_letters_hit(hay_fold: str, term_fold: str) -> bool:
    """Match se un pezzo OCR è il termine con alcune lettere saltate (es. squadst≈squadlist)."""
    n = len(term_fold)
    if n < 7 or not hay_fold:
        return False
    min_tok = max(5, n - 3)
    # Scorri finestre e anche token alfanumerici già contigui
    candidates = set()
    i = 0
    while i < len(hay_fold):
        if not hay_fold[i].isalnum():
            i += 1
            continue
        j = i
        while j < len(hay_fold) and hay_fold[j].isalnum():
            j += 1
        tok = hay_fold[i:j]
        if len(tok) >= min_tok:
            candidates.add(tok)
        i = j
    for i in range(len(hay_fold)):
        for wlen in range(min_tok, n + 1):
            if i + wlen > len(hay_fold):
                break
            candidates.add(hay_fold[i : i + wlen])
    for tok in candidates:
        if len(tok) < min_tok or len(tok) > n:
            continue
        if _ocr_is_subsequence(tok, term_fold) or _ocr_is_subsequence(
            tok, term_fold[::-1]
        ):
            # Copertura sufficiente: non accettare pezzi troppo corti rispetto al termine
            if len(tok) >= int(n * 0.65):
                return True
    return False


# Forme tipiche in cui Windows/EasyOCR rende «BIRTHDAY» sulle grafiche stilizzate
_OCR_BIRTHDAY_FORMS = (
    "fiblrthdw", "fiblrthow", "fiblrfiow",
    "brthdw", "brthow", "brthday", "ebirthday",
    "blpthdav", "blrthdav", "blrthddy", "blpthdov", "bipthdah",
    "blpthday", "blrthday", "birthdav", "birihday",
    "wdhtrlbif", "wohtrlbif", "woifrlbif",
    "wdhtrb", "wohtrb",
)

# Sinonimi OCR: grafiche IT spesso scrivono COMPLEANNO al posto di BIRTHDAY
# (solo match OCR, non la ricerca su documenti di testo).
_OCR_TERM_SYNONYMS = {
    "birthday": ("birthday", "compleanno", "happybirthday", "buoncompleanno"),
    "compleanno": ("compleanno", "birthday", "happybirthday", "buoncompleanno"),
}


def _ocr_term_alternatives(term: str) -> tuple:
    """Restituisce il termine + eventuali sinonimi OCR (minuscolo)."""
    t = (term or "").strip().lower()
    if not t:
        return ()
    syn = _OCR_TERM_SYNONYMS.get(t)
    if syn:
        return syn
    return (t,)


def _ocr_birthday_alias_hit(fold_blob: str) -> bool:
    """True se nel testo OCR compaiono forme note di BIRTHDAY (anche reverse)."""
    if not fold_blob:
        return False
    for form in _OCR_BIRTHDAY_FORMS:
        ff = _ocr_fold(form)
        if not ff:
            continue
        if ff in fold_blob or ff[::-1] in fold_blob:
            return True
    return False


def ocr_text_matches_terms(text: str, terms) -> bool:
    """Match tollerante per testo OCR (reverse, fold, fuzzy, sinonimi birthday↔compleanno)."""
    if not text or not terms:
        return False
    terms_l = [str(t).lower() for t in terms if t]
    if not terms_l:
        return False
    # Anche senza spazi: «squad list» ↔ «squadlist» (titoli stilizzati / OCR spezza le parole)
    nospace = lambda s: "".join((s or "").split())
    haystacks = [
        text.lower(),
        text[::-1].lower(),
        _ocr_fold(text),
        _ocr_fold(text)[::-1],
        nospace(text.lower()),
        nospace(text[::-1].lower()),
        nospace(_ocr_fold(text)),
        nospace(_ocr_fold(text)[::-1]),
    ]
    fold_blob = _ocr_fold(text) + _ocr_fold(text[::-1])
    fold_blob_ns = nospace(fold_blob)

    def _one_term_ok(term: str) -> bool:
        alts = _ocr_term_alternatives(term)
        for alt in alts:
            tf = _ocr_fold(alt)
            alt_ns = nospace(alt)
            tf_ns = nospace(tf) if tf else ""
            for hay in haystacks:
                if not hay:
                    continue
                if alt in hay or (tf and tf in hay):
                    return True
                if alt_ns and alt_ns in hay:
                    return True
                if tf_ns and tf_ns in hay:
                    return True
            target = tf or alt
            target_ns = nospace(target)
            if len(target_ns) < 3:
                if target_ns and (target_ns in fold_blob or target_ns in fold_blob_ns):
                    return True
                continue
            if _ocr_fuzzy_term_in(fold_blob, target) or _ocr_fuzzy_term_in(
                fold_blob_ns, target_ns
            ):
                return True
            if target == "birthday" and _ocr_birthday_alias_hit(fold_blob):
                return True
        return False

    return all(_one_term_ok(t) for t in terms_l)


def _ocr_clipboard_light_cleanup(text: str) -> str:
    """Pulizia leggera per documenti/loghi: tiene il testo, toglie reverse e vuoti."""
    import re
    lines_out = []
    seen = set()
    for line in text.splitlines():
        s = " ".join(line.split())
        if not s:
            if lines_out and lines_out[-1] != "":
                lines_out.append("")
            continue
        ff = _ocr_fold(s)
        if ff and (ff in seen or ff[::-1] in seen):
            continue
        # Scarta linee che sono quasi solo reverse di una già tenuta (OCR doppio)
        if ff and len(ff) >= 8:
            skip = False
            for prev in list(seen):
                if len(prev) >= 8 and (ff == prev[::-1] or prev == ff[::-1]):
                    skip = True
                    break
            if skip:
                continue
        if ff:
            seen.add(ff)
        lines_out.append(s)
    result = "\n".join(lines_out).strip()
    # Una sola riga: dedup token reverse / quasi-duplicati lunghi
    if "\n" not in result:
        toks = result.split()
        out = []
        seen_t = set()
        for t in toks:
            ff = _ocr_fold(t)
            if ff and (ff in seen_t or ff[::-1] in seen_t):
                continue
            near = False
            if ff and len(ff) >= 8:
                for prev in seen_t:
                    if abs(len(prev) - len(ff)) <= 1 and _ocr_edit_distance(prev, ff) <= 1:
                        near = True
                        break
            if near:
                continue
            if ff:
                seen_t.add(ff)
            out.append(t)
        result = " ".join(out)
    # Compatta spazi multipli restanti
    result = re.sub(r"[ \t]{2,}", " ", result)
    return result.strip()


def _ocr_clipboard_birthday_cleanup(text: str) -> str:
    """Pulizia aggressiva per grafiche HAPPY/BIRTHDAY stilizzate."""
    import re
    known_bday = set()
    for form in _OCR_BIRTHDAY_FORMS:
        ff = _ocr_fold(form)
        if ff:
            known_bday.add(ff)
            known_bday.add(ff[::-1])
    known_bday.update({
        "brthdav", "ebrthdav", "brthdayip", "birthdavip", "brthdavip",
        "ebrthday", "ebirthday", "blpthdov", "blrthddy", "bipthdah",
        "blpthdav", "blrthdav",
    })
    happy_forms = {"happy", "hpppy", "happv", "nappy", "yappah", "yppph", "vppah"}
    _junk_raw = (
        "jeep", "heep", "yeepl", "peugonit", "pephu", "pohered", "powered", "ered",
        "felicia", "visit", "detroit", "adidas", "juuentus", "juijentus",
        "juventus", "gilcteb", "betclig", "sjlcen", "hollandi", "fial",
        "group", "new", "aiisto", "w6ep", "bhtgel", "det2ob", "v49oi",
        "uuero", "auuero", "ccla", "oit", "uel", "uelche", "se1", "izlo",
        "white", "nero", "amore", "grande", "solo", "per", "che", "sar",
        "the", "and", "by", "eston", "clig", "gilcte",
        "storla", "storia", "lanco", "abbraccia", "salza", "sialza", "fischla",
        "finizio", "inizio", "inizla", "sogn", "vibit", "deod", "vish",
        "hee", "jro", "ando", "quel", "dauuero", "davvero", "urj",
        "saro", "sara", "juve", "fischia", "inizla", "un", "dun", "cla",
        "oit", "izlo", "tee", "per", "solo",
    )
    junk_folds = set()
    for j in _junk_raw:
        ff = _ocr_fold(j)
        if ff:
            junk_folds.add(ff)
            junk_folds.add(ff[::-1])

    def _norm_token(raw: str) -> str:
        folded = _ocr_fold(raw)
        if not folded:
            return ""
        if folded in known_bday or (
            len(folded) >= 7
            and any(b in folded or folded in b for b in ("birthday", "brthdav", "blrthdav", "blpthdav"))
        ):
            return "BIRTHDAY"
        if folded in happy_forms:
            return "HAPPY"
        if len(folded) >= 7 and _ocr_fuzzy_term_in(folded, "birthday"):
            return "BIRTHDAY"
        return raw.strip()

    raw_tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]{2,}", text)
    seen = set()
    has_happy = False
    has_bday = False
    names = []

    for raw in raw_tokens:
        if raw.isdigit():
            continue
        if len(raw) <= 2 and not raw.isalpha():
            continue
        norm = _norm_token(raw)
        if not norm:
            continue
        ff = _ocr_fold(norm)
        if not ff or len(ff) < 2:
            continue
        if ff in junk_folds or ff[::-1] in junk_folds:
            continue
        if ff in seen or ff[::-1] in seen:
            continue
        if ff in ("yadhtrib", "yappyh", "yppah") or ff[::-1] in ("happy", "birthday"):
            continue
        seen.add(ff)
        if norm == "HAPPY":
            has_happy = True
            continue
        if norm == "BIRTHDAY":
            has_bday = True
            continue
        letters = sum(1 for c in norm if c.isalpha())
        if any(c.isdigit() for c in norm):
            continue
        if letters >= 3 and letters >= len(norm) - 1:
            names.append(norm.upper() if norm.isupper() or norm.istitle() or norm.isalpha() else norm)

    parts = []
    if has_happy:
        parts.append("HAPPY")
    if has_bday:
        parts.append("BIRTHDAY")
    name_seen = set()
    for n in names:
        nf = _ocr_fold(n)
        if nf in name_seen or nf[::-1] in name_seen:
            continue
        if nf in ("happy", "birthday"):
            continue
        name_seen.add(nf)
        parts.append(n)

    if not (has_happy or has_bday):
        return ""

    out_lines = []
    if has_happy and has_bday:
        out_lines.append("HAPPY BIRTHDAY")
    else:
        if has_happy:
            out_lines.append("HAPPY")
        if has_bday:
            out_lines.append("BIRTHDAY")
    name_parts = [p for p in parts if p not in ("HAPPY", "BIRTHDAY")]
    folds_names = [_ocr_fold(n) for n in name_parts]
    filtered_names = []
    for i, n in enumerate(name_parts):
        nf = folds_names[i]
        if len(nf) < 4:
            continue
        covered = False
        for j, other in enumerate(folds_names):
            if i == j or len(other) <= len(nf):
                continue
            if nf in other or nf[::-1] in other:
                covered = True
                break
        if not covered:
            filtered_names.append(n)
    if filtered_names:
        # Nomi giocatore: di solito 2 token (nome+cognome); evita coda della canzone
        out_lines.append(" ".join(filtered_names[:2]))
    return "\n".join(out_lines).strip()


def _ocr_repair_tokens_toward_hints(text: str, hint_terms) -> str:
    """In Copia pulito: sostituisce token OCR mutilati (SQUAD ST) con la query (SQUADLIST)."""
    import re
    if not text or not hint_terms:
        return text
    terms = [str(t).strip() for t in hint_terms if t and str(t).strip()]
    if not terms:
        return text

    def _case_like(sample: str, word: str) -> str:
        if sample.isupper():
            return word.upper()
        if sample[:1].isupper() and sample[1:].islower():
            return word[:1].upper() + word[1:].lower()
        return word.lower()

    def _fix_token(tok: str) -> str:
        ff = _ocr_fold(tok)
        if not ff or len(ff) < 4:
            return tok
        for term in terms:
            tf = _ocr_fold(term)
            if not tf or len(tf) < 4:
                continue
            if ff == tf or ff == tf[::-1]:
                return _case_like(tok, term)
            # Match fuzzy / lettere mancanti sul singolo token o su token senza spazi vicini
            if ocr_text_matches_terms(tok, [term]):
                return _case_like(tok, term)
        return tok

    lines_out = []
    for line in text.splitlines():
        parts = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+|[^A-Za-zÀ-ÖØ-öø-ÿ0-9]+", line)
        # Prova anche a fondere due token consecutivi tipo «SQUAD»+«ST»
        i = 0
        rebuilt = []
        while i < len(parts):
            p = parts[i]
            if p.isalnum() and i + 2 < len(parts):
                mid = parts[i + 1]
                nxt = parts[i + 2]
                if nxt.isalnum() and mid.strip() == "":
                    merged = p + nxt
                    fixed = _fix_token(merged)
                    if fixed != merged and _ocr_fold(fixed) != _ocr_fold(merged):
                        rebuilt.append(fixed)
                        i += 3
                        continue
                    # Spazio singolo tra due pezzi: prova comunque
                if nxt.isalnum() and (not mid.strip() or mid.isspace()):
                    merged = p + " " + nxt if mid.isspace() else p + nxt
                    # Per il match usiamo senza spazio
                    if ocr_text_matches_terms(p + nxt, terms):
                        # Quale term?
                        for term in terms:
                            if ocr_text_matches_terms(p + nxt, [term]):
                                rebuilt.append(_case_like(p, term))
                                i += 3
                                break
                        else:
                            rebuilt.append(_fix_token(p))
                            i += 1
                        continue
            if p.isalnum():
                rebuilt.append(_fix_token(p))
            else:
                rebuilt.append(p)
            i += 1
        lines_out.append("".join(rebuilt))
    return "\n".join(lines_out)


def ocr_text_for_clipboard(text: str, mode: str = "clean", hint_terms=None) -> str:
    """Pulisce il testo OCR per la copia.

    mode:
      - "clean": grafiche HAPPY/BIRTHDAY → saluto+nome; documenti → cleanup leggero
      - "full": OCR completo (canzone/sponsor/tutto), solo dedup reverse/rumore estremo
    hint_terms: se presenti in clean, ripara token mutilati verso la parola cercata.
    """
    if not text:
        return ""
    mode = (mode or "clean").strip().lower()
    if mode == "full":
        return _ocr_clipboard_light_cleanup(text)

    looks_bday = ocr_text_matches_terms(text, ["birthday"]) or ocr_text_matches_terms(
        text, ["happy"]
    )
    if looks_bday:
        cleaned = _ocr_clipboard_birthday_cleanup(text)
        if cleaned and ("BIRTHDAY" in cleaned or "HAPPY" in cleaned):
            alpha = sum(1 for c in text if c.isalpha())
            lines = [ln for ln in text.splitlines() if ln.strip()]
            # Solo lettere/documenti molto lunghi restano in modalità leggera
            if alpha > 450 and len(lines) >= 10:
                out = _ocr_clipboard_light_cleanup(text)
            else:
                return cleaned
        else:
            out = _ocr_clipboard_light_cleanup(text)
    else:
        out = _ocr_clipboard_light_cleanup(text)
    if hint_terms:
        try:
            out = _ocr_repair_tokens_toward_hints(out, hint_terms)
        except Exception:
            pass
    return out


def _score_ocr_candidate(text: str, hint_terms=None) -> float:
    """Punteggio qualità testo OCR: preferisci match termini + testo leggibile."""
    if not text or not str(text).strip():
        return -1.0
    t = str(text).strip()
    alpha = sum(1 for c in t if c.isalpha())
    digit = sum(1 for c in t if c.isdigit())
    space = sum(1 for c in t if c.isspace())
    other = max(0, len(t) - alpha - digit - space)
    if alpha < 3:
        return -0.5
    ratio = alpha / max(1, alpha + other)
    score = alpha * ratio
    if hint_terms and ocr_text_matches_terms(t + "\n" + t[::-1], hint_terms):
        score += 500.0
    words = [w for w in t.split() if len(w) >= 2]
    score += min(80, len(words)) * 2.0
    return score


def _ocr_chunk_norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def _ocr_chunk_covered_by(candidate: str, existing: str) -> bool:
    """True se candidate è quasi già contenuto in existing (evita merge ridondanti)."""
    a = _ocr_chunk_norm(candidate)
    b = _ocr_chunk_norm(existing)
    if not a:
        return True
    if a == b:
        return True
    # Sottostringa chiara (anche breve): «hello» dentro «hello world»
    if a in b:
        return True
    # existing più corto ma quasi uguale al candidate → tienilo coperto
    if b in a and len(a) <= max(12, int(len(b) * 1.25)):
        return True
    return False


def _pick_best_ocr_text(chunks: list, hint_terms=None) -> str:
    """Sceglie il pezzo OCR migliore; se pezzi diversi si completano, li unisce.

    Utile con Vision a fasce: titolo in alto + firma/byline in basso possono
    arrivare da ritagli diversi; il merge mantiene entrambi senza duplicare.
    """
    if not chunks:
        return ""
    cleaned = []
    for ch in chunks:
        t = (ch or "").strip()
        if t:
            cleaned.append(t)
    if not cleaned:
        return ""

    uniq = []
    for ch in cleaned:
        replaced = False
        for i, u in enumerate(uniq):
            if _ocr_chunk_covered_by(ch, u):
                replaced = True
                break
            if _ocr_chunk_covered_by(u, ch):
                uniq[i] = ch
                replaced = True
                break
        if not replaced:
            uniq.append(ch)

    best = ""
    best_score = -1.0
    for ch in uniq:
        sc = _score_ocr_candidate(ch, hint_terms=hint_terms)
        if sc > best_score:
            best_score = sc
            best = ch
    if len(uniq) <= 1:
        return best or ""

    merged = "\n".join(uniq)
    merged_score = _score_ocr_candidate(merged, hint_terms=hint_terms)
    if hint_terms:
        rev_m = merged + "\n" + merged[::-1]
        rev_b = (best or "") + "\n" + (best or "")[::-1]
        if ocr_text_matches_terms(rev_m, hint_terms) and not ocr_text_matches_terms(
            rev_b, hint_terms
        ):
            return merged
    if merged_score > best_score:
        return merged
    return best or ""


def _text_has_all_terms(text: str, terms) -> bool:
    return ocr_text_matches_terms(text, terms)


def _ascii_safe_copy(path: str, temps: list) -> str:
    """Copia l'immagine su un path temp ASCII-only.

    Windows.Storage.StorageFile / WinRT OCR falliscono spesso con emoji
    o caratteri speciali nel nome file (tipici dei compleanni Juve).
    """
    ext = os.path.splitext(path)[1].lower() or ".jpg"
    if ext not in _IMG_EXTS:
        ext = ".jpg"
    fd, tmp = tempfile.mkstemp(suffix=ext, prefix="rtad_ocr_src_")
    os.close(fd)
    try:
        import shutil
        shutil.copyfile(path, tmp)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        return path
    temps.append(tmp)
    return tmp


def _wx_save_temp_image(img, suffix=".png") -> str:
    """Salva wx.Image in temp; restituisce path o ''."""
    if img is None:
        return ""
    try:
        if not img.IsOk():
            return ""
    except Exception:
        return ""
    fd, tmp = tempfile.mkstemp(suffix=suffix, prefix="rtad_ocr_var_")
    os.close(fd)
    try:
        import wx
        ok = img.SaveFile(tmp, wx.BITMAP_TYPE_PNG)
        if not ok:
            try:
                os.unlink(tmp)
            except Exception:
                pass
            return ""
        return tmp
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        return ""


def _wx_boost_contrast(img, factor: float = 1.45):
    """Aumenta contrasto su wx.Image greyscale/RGB."""
    import wx
    if img is None or not img.IsOk():
        return img
    w, h = img.GetWidth(), img.GetHeight()
    data = bytearray(img.GetData())
    mid = 128.0
    f = float(factor)
    for i in range(0, len(data), 3):
        for j in range(3):
            v = data[i + j]
            nv = int((v - mid) * f + mid)
            if nv < 0:
                nv = 0
            elif nv > 255:
                nv = 255
            data[i + j] = nv
    out = wx.Image(w, h, bytes(data))
    return out if out.IsOk() else img


def _wx_invert(img):
    """Inverti colori (testo bianco su fondi scuri → nero su chiaro)."""
    import wx
    if img is None or not img.IsOk():
        return img
    w, h = img.GetWidth(), img.GetHeight()
    data = bytearray(img.GetData())
    for i in range(len(data)):
        data[i] = 255 - data[i]
    out = wx.Image(w, h, bytes(data))
    return out if out.IsOk() else img


def _wx_threshold(img, cut: int = 150):
    """Binarizza: utile su strisce Juve e testo bianco pieno."""
    import wx
    if img is None or not img.IsOk():
        return img
    w, h = img.GetWidth(), img.GetHeight()
    data = bytearray(img.GetData())
    c = int(cut)
    for i in range(0, len(data), 3):
        v = data[i]
        nv = 255 if v >= c else 0
        data[i] = data[i + 1] = data[i + 2] = nv
    out = wx.Image(w, h, bytes(data))
    return out if out.IsOk() else img


def _wx_keep_bright(img, cut: int = 200):
    """Isola testo chiaro (BIRTHDAY bianco) su fondi scuri/strisce: resto nero."""
    return _wx_threshold(img, cut=cut)


def _wx_remove_vertical_stripes(img):
    """Toglie strisce verticali (alto-pass orizzontale per colonna).

    Sulle grafiche Juve il testo BIRTHDAY bianco è spezzato dalle strisce
    bianche/nere: togliendo la media di colonna restano i tratti orizzontali
    delle lettere, molto più leggibili per Windows OCR.
    """
    import wx
    if img is None or not img.IsOk():
        return img
    w, h = img.GetWidth(), img.GetHeight()
    if w < 8 or h < 8:
        return img
    src = img.GetData()
    # canale grigio (R=G=B dopo ConvertToGreyscale)
    gray = [src[i] for i in range(0, len(src), 3)]
    col_sum = [0.0] * w
    for y in range(h):
        row = y * w
        for x in range(w):
            col_sum[x] += gray[row + x]
    inv_h = 1.0 / float(h)
    col_avg = [col_sum[x] * inv_h for x in range(w)]
    out = bytearray(w * h * 3)
    for y in range(h):
        row = y * w
        for x in range(w):
            v = int(gray[row + x] - col_avg[x] + 128.0)
            if v < 0:
                v = 0
            elif v > 255:
                v = 255
            j = (row + x) * 3
            out[j] = out[j + 1] = out[j + 2] = v
    res = wx.Image(w, h, bytes(out))
    return res if res.IsOk() else img


def _wx_dilate_horizontal(img, radius: int = 8):
    """Max orizzontale: ricongiunge pezzi di lettera spezzati dalle strisce."""
    import wx
    if img is None or not img.IsOk():
        return img
    w, h = img.GetWidth(), img.GetHeight()
    if w < 8 or h < 8:
        return img
    src = img.GetData()
    gray = [src[i] for i in range(0, len(src), 3)]
    r = max(1, min(int(radius), w // 2))
    out_g = bytearray(w * h)
    for y in range(h):
        row = y * w
        for x in range(w):
            a = x - r if x >= r else 0
            b = x + r + 1 if x + r + 1 <= w else w
            m = 0
            for xx in range(a, b):
                v = gray[row + xx]
                if v > m:
                    m = v
            out_g[row + x] = m
    data = bytearray(w * h * 3)
    for i, v in enumerate(out_g):
        j = i * 3
        data[j] = data[j + 1] = data[j + 2] = v
    res = wx.Image(w, h, bytes(data))
    return res if res.IsOk() else img


def _wx_upscale_min(img, min_side: int = 1400):
    """Ingrandisce se troppo piccola (OCR Windows ama risoluzioni maggiori)."""
    import wx
    if img is None or not img.IsOk():
        return img
    w, h = img.GetWidth(), img.GetHeight()
    m = max(w, h)
    if m >= min_side or m < 8:
        return img
    scale = float(min_side) / float(m)
    nw = max(8, int(w * scale))
    nh = max(8, int(h * scale))
    try:
        out = img.Scale(nw, nh, wx.IMAGE_QUALITY_BICUBIC)
    except Exception:
        out = img.Scale(nw, nh)
    return out if out is not None and out.IsOk() else img


def _append_variant(out: list, temps: list, img) -> None:
    p = _wx_save_temp_image(img)
    if p:
        temps.append(p)
        out.append(p)


def _build_google_retry_variants(path: str, temps: list, max_variants: int = 8) -> list:
    """Poche varianti mirate per Google quando la query non matcha sull’originale.

    Priorità:
      1) fascia superiore/centrale (titoli poster tipo SQUADLIST)
      2) fascia bassa (byline / firma tipo «di Giulia …» su Tuttosport)
      3) margini sinistro/destro (nomi verticali o colonne laterali)
      4) intera anti-strisce
    """
    out = []
    max_variants = max(1, int(max_variants or 8))
    try:
        import wx
    except Exception:
        return out
    try:
        img = wx.Image(path, wx.BITMAP_TYPE_ANY)
        if img is None or not img.IsOk():
            return out
    except Exception:
        return out
    w, h = img.GetWidth(), img.GetHeight()
    if w < 8 or h < 8:
        return out
    try:
        base = img.ConvertToGreyscale()
    except Exception:
        base = img
    try:
        base = _wx_upscale_min(base, 1600)
        base = _wx_boost_contrast(base, 1.7)
    except Exception:
        pass
    bw, bh = base.GetWidth(), base.GetHeight()

    def _band_pipeline(crop, *, min_side=1800, dilate=12, bright_thr=140, invert=True):
        if crop is None or not crop.IsOk() or len(out) >= max_variants:
            return
        try:
            crop = _wx_upscale_min(crop, min_side)
            dest = _wx_remove_vertical_stripes(crop)
            dest = _wx_boost_contrast(dest, 1.9)
            dest = _wx_dilate_horizontal(dest, radius=dilate)
            bright = _wx_keep_bright(dest, bright_thr)
            _append_variant(out, temps, bright)
            if invert and len(out) < max_variants:
                _append_variant(out, temps, _wx_invert(bright))
        except Exception as e:
            logging.debug(f"Google band variant fallita: {e}")

    # 1) Fascia titolo: circa 5%–58% (sotto header, sopra corpo articolo / lista)
    for y0r, y1r in ((0.10, 0.48), (0.05, 0.40), (0.15, 0.58)):
        if len(out) >= max_variants:
            break
        try:
            y0 = max(0, int(bh * y0r))
            y1 = min(bh, int(bh * y1r))
            if y1 - y0 < 24:
                continue
            _band_pipeline(
                base.GetSubImage(wx.Rect(0, y0, bw, y1 - y0)),
                min_side=1800,
                dilate=12,
            )
        except Exception as e:
            logging.debug(f"Google title-band variant fallita: {e}")

    # 2) Fascia bassa — byline / crediti foto (spesso sotto il corpo)
    for y0r, y1r in ((0.72, 1.0), (0.58, 0.88), (0.80, 1.0)):
        if len(out) >= max_variants:
            break
        try:
            y0 = max(0, int(bh * y0r))
            y1 = min(bh, int(bh * y1r))
            if y1 - y0 < 20:
                continue
            _band_pipeline(
                base.GetSubImage(wx.Rect(0, y0, bw, y1 - y0)),
                min_side=2000,
                dilate=8,
                bright_thr=150,
                invert=True,
            )
        except Exception as e:
            logging.debug(f"Google bottom-band variant fallita: {e}")

    # 3) Margini laterali (testo verticale / colonne strette)
    if len(out) < max_variants:
        try:
            x1 = max(8, int(bw * 0.28))
            left = base.GetSubImage(wx.Rect(0, 0, x1, bh))
            left = _wx_upscale_min(left, 1600)
            rot = left.Rotate90(clockwise=False)
            if rot is not None and rot.IsOk():
                _band_pipeline(rot, min_side=1800, dilate=8, invert=False)
        except Exception as e:
            logging.debug(f"Google left-margin variant fallita: {e}")
    if len(out) < max_variants:
        try:
            x0 = max(0, int(bw * 0.72))
            right = base.GetSubImage(wx.Rect(x0, 0, max(8, bw - x0), bh))
            right = _wx_upscale_min(right, 1600)
            rot = right.Rotate90(clockwise=False)
            if rot is not None and rot.IsOk():
                _band_pipeline(rot, min_side=1800, dilate=8, invert=False)
        except Exception as e:
            logging.debug(f"Google right-margin variant fallita: {e}")

    # 4) Intera immagine con anti-strisce (se c’è ancora posto)
    if len(out) < max_variants:
        try:
            dest = _wx_remove_vertical_stripes(base)
            dest = _wx_boost_contrast(dest, 1.85)
            dest = _wx_dilate_horizontal(dest, radius=10)
            _append_variant(out, temps, _wx_keep_bright(dest, 145))
        except Exception:
            pass
    return out[:max_variants]


def _build_image_variants(path: str, temps: list, max_variants: int = 14) -> list:
    """Elenco path da passare all'OCR: originale + preprocess wx se disponibile.

    Priorità (importante con pochi slot EasyOCR):
      1) fascia destra «clean» ruotata — BIRTHDAY verticale tipo Alajbegovic/McKennie
         (senza anti-strisce: il testo bianco su nero andrebbe distrutto)
      2) fascia inferiore anti-strisce — BIRTHDAY orizzontale su zebrature tipo Conte
      3) altre fasce / invert / rotazioni intere
    """
    out = [path]
    max_variants = max(1, int(max_variants or 14))
    try:
        import wx
    except Exception:
        return out
    try:
        img = wx.Image(path, wx.BITMAP_TYPE_ANY)
        if img is None or not img.IsOk():
            return out
    except Exception:
        return out

    w, h = img.GetWidth(), img.GetHeight()
    if w < 8 or h < 8:
        return out

    try:
        base = img.ConvertToGreyscale()
    except Exception:
        base = img
    try:
        base = _wx_upscale_min(base, 1400)
    except Exception:
        pass
    try:
        base = _wx_boost_contrast(base, 1.55)
    except Exception:
        pass

    def _stripe_pipeline(crop, *, rotate90=False, min_side=2000, extra=False):
        """Anti-strisce + dilatazione; con extra=True aggiunge anche dest e soglia soft."""
        if crop is None or not crop.IsOk() or len(out) >= max_variants:
            return
        try:
            crop = _wx_upscale_min(crop, min_side)
            if rotate90:
                crop = crop.Rotate90(clockwise=False)
                if crop is None or not crop.IsOk():
                    return
            dest = _wx_remove_vertical_stripes(crop)
            dest = _wx_boost_contrast(dest, 1.8)
            dest = _wx_dilate_horizontal(dest, radius=10)
            bright = _wx_keep_bright(dest, 150)
            _append_variant(out, temps, bright)
            if len(out) < max_variants:
                _append_variant(out, temps, _wx_invert(bright))
            if extra and len(out) < max_variants:
                _append_variant(out, temps, dest)
            if extra and len(out) < max_variants:
                try:
                    bright2 = _wx_keep_bright(crop, 190)
                    _append_variant(out, temps, _wx_invert(bright2))
                except Exception:
                    pass
        except Exception as e:
            logging.debug(f"OCR stripe pipeline fallita: {e}")

    def _clean_rotate_panel(crop, *, clockwise: bool, min_side: int = 1800):
        """Ritaglio + rotazione senza anti-strisce (pannello nero + testo bianco)."""
        if crop is None or not crop.IsOk() or len(out) >= max_variants:
            return
        try:
            crop = _wx_upscale_min(crop, min_side)
            rot = crop.Rotate90(clockwise=clockwise)
            if rot is None or not rot.IsOk():
                return
            boost = _wx_boost_contrast(rot, 1.7)
            _append_variant(out, temps, boost)
            if len(out) < max_variants:
                _append_variant(out, temps, _wx_invert(boost))
        except Exception as e:
            logging.debug(f"OCR clean rotate fallita: {e}")

    bw, bh = base.GetWidth(), base.GetHeight()

    # 1) Fascia destra «clean» — BIRTHDAY verticale (priorità alta)
    try:
        x0 = max(0, int(bw * 0.58))
        right = base.GetSubImage(wx.Rect(x0, 0, max(8, bw - x0), bh))
        # Testo ruotato CW in grafica → CCW per leggerlo; teniamo anche CW
        _clean_rotate_panel(right, clockwise=False, min_side=2000)
        _clean_rotate_panel(right, clockwise=True, min_side=2000)
    except Exception as e:
        logging.debug(f"OCR crop destro clean fallito: {e}")

    # 2) Fascia inferiore — pipeline anti-strisce (Conte / Rampulla)
    try:
        y0 = max(0, int(bh * 0.52))
        _stripe_pipeline(
            base.GetSubImage(wx.Rect(0, y0, bw, max(8, bh - y0))),
            min_side=2200,
            extra=True,
        )
    except Exception as e:
        logging.debug(f"OCR crop basso fallito: {e}")

    # 3) Fascia sinistra clean (HAPPY / nome verticali)
    try:
        if len(out) < max_variants:
            x1 = max(8, int(bw * 0.42))
            left = base.GetSubImage(wx.Rect(0, 0, x1, bh))
            _clean_rotate_panel(left, clockwise=False, min_side=1600)
    except Exception as e:
        logging.debug(f"OCR crop sinistro clean fallito: {e}")

    # 4) Fascia alta
    try:
        if len(out) < max_variants:
            y1 = max(8, int(bh * 0.45))
            _stripe_pipeline(base.GetSubImage(wx.Rect(0, 0, bw, y1)), min_side=1800)
    except Exception as e:
        logging.debug(f"OCR crop alto fallito: {e}")

    # 5) Intera invertita / grigi
    try:
        if len(out) < max_variants:
            _append_variant(out, temps, _wx_invert(base))
    except Exception:
        pass
    if len(out) < max_variants:
        _append_variant(out, temps, base)

    # 6) Rotazioni intere residue
    for clockwise in (False, True):
        if len(out) >= max_variants:
            break
        try:
            rot = base.Rotate90(clockwise=clockwise)
            if rot is not None and rot.IsOk():
                _append_variant(out, temps, _wx_invert(rot))
        except Exception:
            pass

    seen = set()
    uniq = []
    for pth in out:
        ap = os.path.normcase(os.path.abspath(pth))
        if ap in seen:
            continue
        seen.add(ap)
        uniq.append(pth)
        if len(uniq) >= max_variants:
            break
    return uniq


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_key_for_file(path: str, size: int, mtime: float) -> str:
    eng = active_engine()
    raw = (
        f"v{OCR_CACHE_VERSION}|{eng}|"
        f"{os.path.normcase(os.path.abspath(path))}|{size}|{mtime:.3f}"
    )
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()


def _cache_path(key: str) -> str:
    if not _cache_dir:
        return ""
    return os.path.join(_cache_dir, f"{key}.json")


def _cache_get(key: str):
    path = _cache_path(key)
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if int(data.get("v", 0)) != OCR_CACHE_VERSION:
            return None
        return str(data.get("text", "") or "")
    except Exception:
        return None


def _cache_put(key: str, text: str) -> None:
    path = _cache_path(key)
    if not path:
        return
    with _cache_lock:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {"v": OCR_CACHE_VERSION, "text": text or "", "ts": time.time()},
                    f,
                    ensure_ascii=False,
                )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# PNG helper (RGB grezzo → PNG minimo senza dipendenze)
# ---------------------------------------------------------------------------

def _rgb_to_png_bytes(rgb: bytes, width: int, height: int) -> bytes:
    """Scrive un PNG RGB 8-bit minimale (zlib + filtri none)."""
    import struct
    import zlib as _zlib

    if width <= 0 or height <= 0:
        return b""
    need = width * height * 3
    if len(rgb) < need:
        return b""
    raw = rgb[:need]

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", _zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    # Filtri: ogni riga inizia con 0 (None)
    row_stride = width * 3
    filtered = bytearray()
    for y in range(height):
        filtered.append(0)
        filtered.extend(raw[y * row_stride : (y + 1) * row_stride])
    compressed = _zlib.compress(bytes(filtered), 6)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

def _try_winrt_probe() -> bool:
    try:
        # winrt (vecchio) o winsdk
        try:
            from winrt.windows.media.ocr import OcrEngine  # type: ignore
        except Exception:
            from winsdk.windows.media.ocr import OcrEngine  # type: ignore
        eng = OcrEngine.try_create_from_user_profile_languages()
        return eng is not None
    except Exception:
        return False


def _ocr_via_winrt(path: str) -> str:
    """OCR via winrt/winsdk. Restituisce None se backend non usabile, '' se vuoto."""
    import asyncio

    async def _run():
        try:
            from winrt.windows.media.ocr import OcrEngine  # type: ignore
            from winrt.windows.graphics.imaging import (  # type: ignore
                BitmapDecoder,
                SoftwareBitmap,
                BitmapPixelFormat,
                BitmapAlphaMode,
            )
            from winrt.windows.storage import StorageFile  # type: ignore
            from winrt.windows.globalization import Language  # type: ignore
        except Exception:
            from winsdk.windows.media.ocr import OcrEngine  # type: ignore
            from winsdk.windows.graphics.imaging import (  # type: ignore
                BitmapDecoder,
                SoftwareBitmap,
                BitmapPixelFormat,
                BitmapAlphaMode,
            )
            from winsdk.windows.storage import StorageFile  # type: ignore
            from winsdk.windows.globalization import Language  # type: ignore

        file = await StorageFile.get_file_from_path_async(os.path.abspath(path))
        stream = await file.open_read_async()
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        # Windows OCR richiede Gray8/Ignore o Bgra8
        try:
            if (
                bitmap.bitmap_pixel_format != BitmapPixelFormat.GRAY8
                or bitmap.bitmap_alpha_mode != BitmapAlphaMode.IGNORE
            ):
                bitmap = SoftwareBitmap.convert(
                    bitmap, BitmapPixelFormat.GRAY8, BitmapAlphaMode.IGNORE
                )
        except Exception:
            try:
                bitmap = SoftwareBitmap.convert(
                    bitmap, BitmapPixelFormat.BGRA8, BitmapAlphaMode.IGNORE
                )
            except Exception:
                pass

        chunks = []
        engines = []
        try:
            e0 = OcrEngine.try_create_from_user_profile_languages()
            if e0 is not None:
                engines.append(e0)
        except Exception:
            pass
        for tag in ("en-US", "it-IT", "en-GB"):
            try:
                lang = Language(tag)
                eng = OcrEngine.try_create_from_language(lang)
                if eng is not None:
                    engines.append(eng)
            except Exception:
                pass
        seen_eng = set()
        for eng in engines:
            try:
                mid = id(eng)
                if mid in seen_eng:
                    continue
                seen_eng.add(mid)
            except Exception:
                pass
            try:
                result = await eng.recognize_async(bitmap)
                t = (result.text or "").strip() if result else ""
                if t:
                    chunks.append(t)
            except Exception:
                pass
        return "\n".join(chunks).strip()

    try:
        return asyncio.run(_run())
    except Exception as e:
        logging.debug(f"winrt OCR fallito: {e}")
        return None


def _powershell_script() -> str:
    """Script PS1: OCR Windows con bitmap Bgra8 tipizzato + lingue multiple."""
    return r"""
param([Parameter(Mandatory=$true)][string]$ImagePath)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null

# Carica TUTTI i tipi WinRT necessari (senza enum caricati, Convert fallisce in silenzio)
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap,Windows.Graphics,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapPixelFormat,Windows.Graphics,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapAlphaMode,Windows.Graphics,ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]

function Await-WinRT {
  param($Async, [Type]$ResultType)
  $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
      $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1
    })[0]
  if ($null -eq $asTaskGeneric) { throw 'AsTask non trovato' }
  $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
  $task = $asTask.Invoke($null, @($Async))
  $ok = $task.Wait(60000)
  if (-not $ok) { throw 'Timeout Await WinRT' }
  if ($task.IsFaulted) { throw $task.Exception }
  return $task.Result
}

$path = [System.IO.Path]::GetFullPath($ImagePath)
if (-not [System.IO.File]::Exists($path)) { Write-Error "File assente: $path"; exit 2 }

$file = Await-WinRT ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
$stream = Await-WinRT ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await-WinRT ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])

# Formato esplicito richiesto da Windows.Media.Ocr
$bitmap = $null
try {
  $bitmap = Await-WinRT (
    $decoder.GetSoftwareBitmapAsync(
      [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,
      [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied
    )
  ) ([Windows.Graphics.Imaging.SoftwareBitmap])
} catch {
  $bitmap = Await-WinRT ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
}
try {
  $bitmap = [Windows.Graphics.Imaging.SoftwareBitmap]::Convert(
    $bitmap,
    [Windows.Graphics.Imaging.BitmapPixelFormat]::Gray8,
    [Windows.Graphics.Imaging.BitmapAlphaMode]::Ignore
  )
} catch {}

$texts = New-Object System.Collections.Generic.List[string]
$engines = New-Object System.Collections.Generic.List[object]
$e0 = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($null -ne $e0) { [void]$engines.Add($e0) }
foreach ($tag in @('en-US','it-IT','en-GB')) {
  try {
    $lang = [Windows.Globalization.Language]::new($tag)
    $eng = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
    if ($null -ne $eng) { [void]$engines.Add($eng) }
  } catch {}
}
if ($engines.Count -eq 0) {
  Write-Error 'OcrEngine non disponibile (pacchetto lingua OCR mancante?)'
  exit 3
}
foreach ($engine in $engines) {
  try {
    $result = Await-WinRT ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    if ($null -ne $result) {
      $t = [string]$result.Text
      if (-not [string]::IsNullOrWhiteSpace($t)) { [void]$texts.Add($t.Trim()) }
    }
  } catch {}
}
if ($texts.Count -eq 0) { Write-Output ''; exit 0 }
Write-Output (($texts | Select-Object -Unique) -join "`n")
"""


def _ensure_ps_script() -> str:
    global _ps_script_path
    base = _cache_dir or tempfile.gettempdir()
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        base = tempfile.gettempdir()
    # Nome versionato: forza riscrittura dopo fix path/emoji/Bgra8
    path = os.path.join(base, f"rtad_windows_ocr_v{OCR_CACHE_VERSION}.ps1")
    body = _powershell_script()
    need_write = True
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                if f.read() == body:
                    need_write = False
        except Exception:
            need_write = True
    if need_write:
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
    _ps_script_path = path
    return path


def _try_powershell_probe() -> tuple:
    if os.name != "nt":
        return False, "OCR solo su Windows"
    try:
        script = _ensure_ps_script()
    except Exception as e:
        return False, f"Impossibile preparare script OCR: {e}"
    # Probe: crea PNG 1x1 e tenta OCR (può restituire vuoto ma non errore fatale)
    try:
        png = _rgb_to_png_bytes(b"\xff\xff\xff", 1, 1)
        fd, tmp = tempfile.mkstemp(suffix=".png", prefix="rtad_ocr_probe_")
        os.write(fd, png)
        os.close(fd)
        try:
            text, err = _run_powershell_ocr(tmp, timeout=20)
            if err and "OcrEngine" in err:
                return False, (
                    "Pacchetto OCR Windows assente o non attivabile. "
                    "Impostazioni → Lingua → funzionalità lingua → OCR."
                )
            # Anche testo vuoto = motore raggiungibile
            return True, "Windows.Media.Ocr (PowerShell)"
        finally:
            try:
                os.unlink(tmp)
            except Exception:
                pass
    except Exception as e:
        return False, f"Probe OCR fallito: {e}"


def _hidden_subprocess_kwargs() -> dict:
    """Evita il flash della console PowerShell su Windows (Standalone e Add-on NVDA)."""
    kwargs = {}
    if os.name != "nt":
        return kwargs
    # CREATE_NO_WINDOW: niente nuova console per powershell.exe
    kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE
        kwargs["startupinfo"] = si
    except Exception:
        pass
    return kwargs


def _run_powershell_ocr(image_path: str, timeout: int = OCR_SOFT_TIMEOUT_SEC) -> tuple:
    script = _ensure_ps_script()
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        script,
        "-ImagePath",
        os.path.abspath(image_path),
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            check=False,
            **_hidden_subprocess_kwargs(),
        )
    except subprocess.TimeoutExpired:
        return "", "timeout"
    except Exception as e:
        return "", str(e)
    out = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    err = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
    if proc.returncode != 0 and not out:
        return "", err or f"exit {proc.returncode}"
    return out, err


def _quiet_torch_warnings():
    """Evita spam cmd: pin_memory senza GPU e deprecazioni quantize di torch."""
    import warnings
    warnings.filterwarnings(
        "ignore",
        message=r".*pin_memory.*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=r".*quantize_per_tensor.*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=r".*deprecated and will be removed.*",
        module=r"torch\..*",
        category=UserWarning,
    )


def _get_easyocr_reader():
    """Lazy singleton EasyOCR Reader (it+en). Thread-safe."""
    global _easyocr_reader
    with _easyocr_lock:
        if _easyocr_reader is not None:
            return _easyocr_reader
        import warnings
        import easyocr
        logging.info(
            "Inizializzazione EasyOCR (it+en): al primo avvio può scaricare i modelli…"
        )
        _quiet_torch_warnings()
        # gpu=False: compatibilità ampia su PC senza CUDA
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            _easyocr_reader = easyocr.Reader(["it", "en"], gpu=False, verbose=False)
        return _easyocr_reader


def _ocr_via_easyocr(path: str) -> str:
    """OCR con EasyOCR. Restituisce testo o ''."""
    if not path or not os.path.isfile(path):
        return ""
    try:
        import warnings
        reader = _get_easyocr_reader()
        _quiet_torch_warnings()
        # detail=0 → solo stringhe; paragraph unisce meglio le righe
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            try:
                lines = reader.readtext(path, detail=0, paragraph=True)
            except TypeError:
                # API più vecchie senza paragraph=
                raw = reader.readtext(path, detail=1)
                lines = [t[1] for t in (raw or []) if t and len(t) > 1 and t[1]]
        if not lines:
            return ""
        if isinstance(lines, str):
            return lines.strip()
        return "\n".join(str(x).strip() for x in lines if str(x).strip())
    except Exception as e:
        logging.debug(f"EasyOCR fallito su {path}: {e}")
        return ""


def _ocr_via_google(path: str) -> tuple:
    """OCR via Google Cloud Vision REST (chiave API utente). Restituisce (testo, diag)."""
    global _google_last_error
    key = (_google_api_key or "").strip()
    if not key:
        _google_last_error = "chiave API assente"
        return "", "google: chiave API assente"
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception as e:
        _google_last_error = f"lettura file: {e}"
        return "", f"google: lettura ({e})"
    if not raw:
        return "", "google: file vuoto"
    if len(raw) > MAX_OCR_IMAGE_BYTES:
        return "", "google: file troppo grande"

    payload = {
        "requests": [
            {
                "image": {"content": base64.b64encode(raw).decode("ascii")},
                "features": [
                    {"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1},
                    {"type": "TEXT_DETECTION", "maxResults": 1},
                ],
                "imageContext": {"languageHints": ["it", "en"]},
            }
        ]
    }
    url = f"{_GOOGLE_VISION_URL}?key={urllib.parse.quote(key, safe='')}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        _stats["google_calls"] = int(_stats.get("google_calls", 0) or 0) + 1
        with urllib.request.urlopen(req, timeout=OCR_SOFT_TIMEOUT_SEC) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            pass
        msg = f"HTTP {e.code}"
        if err_body:
            msg += f": {err_body}"
        _google_last_error = msg
        logging.warning(f"Google Vision OCR fallito: {msg}")
        return "", f"google: {msg}"
    except Exception as e:
        _google_last_error = str(e)
        logging.warning(f"Google Vision OCR errore: {e}")
        return "", f"google: {e}"

    try:
        responses = data.get("responses") or []
        if not responses:
            return "", "google: risposta vuota"
        r0 = responses[0] or {}
        if r0.get("error"):
            err = r0.get("error") or {}
            msg = err.get("message") or str(err)
            _google_last_error = msg
            return "", f"google: {msg}"
        # Preferisci fullTextAnnotation (DOCUMENT_TEXT_DETECTION)
        full = r0.get("fullTextAnnotation") or {}
        text = (full.get("text") or "").strip()
        if not text:
            anns = r0.get("textAnnotations") or []
            if anns:
                text = (anns[0].get("description") or "").strip()
        _google_last_error = ""
        return text, "google"
    except Exception as e:
        _google_last_error = str(e)
        return "", f"google parse: {e}"


def _ocr_windows_path(path: str) -> tuple:
    """OCR solo Windows su un path. Restituisce (testo, diag)."""
    text = None
    diag = ""
    use_winrt = False
    if _engine_ok and "winrt" in (_engine_note or "").lower():
        use_winrt = True
    elif _try_winrt_probe():
        use_winrt = True
    if use_winrt:
        text = _ocr_via_winrt(path)
        if text:
            return text.strip(), diag
        if text is None:
            diag = "winrt errore"
        else:
            diag = "winrt vuoto"
    text2, err = _run_powershell_ocr(path)
    if err and not text2:
        diag = (diag + "; " if diag else "") + f"ps:{err[:180]}"
        logging.debug(f"PowerShell OCR: {err}")
    merged = (text2 or "").strip()
    if not merged and text:
        merged = text.strip()
    return merged, diag


def _ocr_path_impl(path: str, should_abort=None, with_diag: bool = False, hint_terms=None):
    """OCR su un path. Se with_diag=True restituisce (text, diag).

    Con EasyOCR: se i hint_terms non compaiono nel testo EasyOCR, completa con
    Windows sullo stesso ritaglio (tipico: EasyOCR legge nome/HAPPY ma salta
    BIRTHDAY verticale; Windows sul crop ruotato lo prende).
    """
    if should_abort and should_abort():
        return ("", "abort") if with_diag else ""

    eng = active_engine()
    diag = ""
    if eng == ENGINE_GOOGLE:
        text, gdiag = _ocr_via_google(path)
        if text:
            return (text, gdiag or "google") if with_diag else text
        # Fallback locale se la chiamata cloud fallisce / chiave invalida
        if _windows_engine_available():
            win_txt, wdiag = _ocr_windows_path(path)
            if win_txt:
                merged_diag = f"{gdiag}; fallback windows"
                if wdiag:
                    merged_diag += f" ({wdiag})"
                return (win_txt, merged_diag) if with_diag else win_txt
        return ("", gdiag or "google vuoto") if with_diag else ""

    if eng == ENGINE_EASYOCR:
        easy = (_ocr_via_easyocr(path) or "").strip()
        terms_ok = bool(easy) and (
            not hint_terms or ocr_text_matches_terms(easy, hint_terms)
        )
        if terms_ok:
            return (easy, "easyocr") if with_diag else easy
        win_txt = ""
        if _windows_engine_available():
            win_txt, wdiag = _ocr_windows_path(path)
            if wdiag:
                diag = ("easyocr+windows: " + wdiag) if easy else ("fallback windows: " + wdiag)
            else:
                diag = "easyocr+windows" if easy else "easyocr vuoto; fallback windows"
        parts = []
        if easy:
            parts.append(easy)
        if win_txt:
            parts.append(win_txt.strip())
        merged = "\n".join(parts).strip()
        if with_diag:
            return merged, diag or ("easyocr vuoto" if not merged else "easyocr")
        return merged

    merged, diag = _ocr_windows_path(path)
    if with_diag:
        return merged, diag
    return merged


# ---------------------------------------------------------------------------
# 1.6.3 — Analisi visiva, descrizione accessibile, scheda tecnica
# ---------------------------------------------------------------------------

# Traduzioni etichette Vision più comuni (EN → IT). Fallback: etichetta originale.
_LABEL_IT = {
    "person": "persona",
    "people": "persone",
    "man": "uomo",
    "woman": "donna",
    "child": "bambino",
    "boy": "ragazzo",
    "girl": "ragazza",
    "face": "volto",
    "smile": "sorriso",
    "dog": "cane",
    "cat": "gatto",
    "bird": "uccello",
    "horse": "cavallo",
    "animal": "animale",
    "pet": "animale domestico",
    "flower": "fiore",
    "plant": "pianta",
    "tree": "albero",
    "grass": "erba",
    "sky": "cielo",
    "cloud": "nuvola",
    "sun": "sole",
    "sunset": "tramonto",
    "beach": "spiaggia",
    "sea": "mare",
    "ocean": "oceano",
    "water": "acqua",
    "mountain": "montagna",
    "hill": "collina",
    "forest": "bosco",
    "nature": "natura",
    "landscape": "paesaggio",
    "building": "edificio",
    "house": "casa",
    "architecture": "architettura",
    "street": "strada",
    "road": "strada",
    "car": "auto",
    "vehicle": "veicolo",
    "bicycle": "bicicletta",
    "food": "cibo",
    "meal": "pasto",
    "drink": "bevanda",
    "table": "tavolo",
    "chair": "sedia",
    "furniture": "arredamento",
    "room": "stanza",
    "indoor": "interno",
    "outdoor": "esterno",
    "text": "testo",
    "font": "carattere tipografico",
    "screenshot": "screenshot",
    "photograph": "fotografia",
    "photo": "fotografia",
    "art": "arte",
    "drawing": "disegno",
    "painting": "dipinto",
    "poster": "locandina",
    "logo": "logo",
    "sign": "cartello",
    "book": "libro",
    "document": "documento",
    "paper": "carta",
    "clothing": "abbigliamento",
    "shirt": "maglietta",
    "dress": "abito",
    "shoe": "scarpa",
    "glasses": "occhiali",
    "phone": "telefono",
    "computer": "computer",
    "laptop": "portatile",
    "screen": "schermo",
    "television": "televisione",
    "festivity": "festa",
    "celebration": "celebrazione",
    "birthday": "compleanno",
    "party": "festa",
    "cake": "torta",
    "gift": "regalo",
    "christmas": "Natale",
    "wedding": "matrimonio",
    "family": "famiglia",
    "group": "gruppo",
    "crowd": "folla",
    "sport": "sport",
    "ball": "palla",
    "game": "gioco",
    "music": "musica",
    "instrument": "strumento",
    "night": "notte",
    "day": "giorno",
    "snow": "neve",
    "rain": "pioggia",
    "window": "finestra",
    "door": "porta",
    "wall": "muro",
    "floor": "pavimento",
    "light": "luce",
    "shadow": "ombra",
    "black": "nero",
    "white": "bianco",
    "red": "rosso",
    "blue": "blu",
    "green": "verde",
    "yellow": "giallo",
    "orange": "arancione",
    "pink": "rosa",
    "purple": "viola",
    "brown": "marrone",
    "gray": "grigio",
    "grey": "grigio",
}


def _label_to_it(label: str) -> str:
    raw = (label or "").strip()
    if not raw:
        return ""
    key = raw.lower()
    if key in _LABEL_IT:
        return _LABEL_IT[key]
    # Prova senza plurale grezzo
    if key.endswith("s") and key[:-1] in _LABEL_IT:
        return _LABEL_IT[key[:-1]]
    return raw


def _color_name_it(r: float, g: float, b: float) -> str:
    """Nome colore approssimato in italiano da RGB 0–1 o 0–255."""
    if r > 1.5 or g > 1.5 or b > 1.5:
        r, g, b = r / 255.0, g / 255.0, b / 255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx < 0.12:
        return "nero"
    if mn > 0.88:
        return "bianco"
    if mx - mn < 0.08:
        if mx < 0.35:
            return "grigio scuro"
        if mx > 0.7:
            return "grigio chiaro"
        return "grigio"
    # Hue grezzo
    if r >= g and r >= b:
        if g > b * 1.2:
            return "arancione" if g > 0.45 else "rosso"
        if b > g * 1.2:
            return "rosa" if r > 0.7 else "viola"
        return "rosso"
    if g >= r and g >= b:
        if b > r * 1.15:
            return "turchese"
        return "verde"
    # blu dominante
    if r > g * 1.2:
        return "viola"
    return "blu"


def _vision_cache_key(path: str, size: int, mtime: float, kind: str) -> str:
    raw = (
        f"vision{VISION_CACHE_VERSION}|{kind}|"
        f"{os.path.normcase(os.path.abspath(path))}|{size}|{mtime:.3f}"
    )
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()


def _vision_cache_get(key: str):
    path = _cache_path(key)
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if int(data.get("v", 0)) != VISION_CACHE_VERSION:
            return None
        return data.get("payload")
    except Exception:
        return None


def _vision_cache_put(key: str, payload) -> None:
    path = _cache_path(key)
    if not path:
        return
    with _cache_lock:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {"v": VISION_CACHE_VERSION, "payload": payload, "ts": time.time()},
                    f,
                    ensure_ascii=False,
                )
        except Exception:
            pass


def _read_image_dimensions(path: str) -> tuple:
    """(width, height) senza dipendenze esterne; (0,0) se sconosciuto."""
    import struct
    try:
        with open(path, "rb") as f:
            head = f.read(32)
            if len(head) < 10:
                return 0, 0
            # PNG
            if head.startswith(b"\x89PNG\r\n\x1a\n"):
                f.seek(16)
                wh = f.read(8)
                if len(wh) == 8:
                    w, h = struct.unpack(">II", wh)
                    return int(w), int(h)
            # GIF
            if head[:6] in (b"GIF87a", b"GIF89a"):
                w, h = struct.unpack("<HH", head[6:10])
                return int(w), int(h)
            # BMP
            if head[:2] == b"BM":
                f.seek(18)
                wh = f.read(8)
                if len(wh) == 8:
                    w, h = struct.unpack("<ii", wh)
                    return abs(int(w)), abs(int(h))
            # JPEG: cerca SOF0/SOF2
            if head[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2:
                        break
                    if marker[0] != 0xFF:
                        break
                    code = marker[1]
                    while code == 0xFF:
                        b = f.read(1)
                        if not b:
                            return 0, 0
                        code = b[0]
                    if code in (0xD8, 0xD9):
                        continue
                    seglen = f.read(2)
                    if len(seglen) < 2:
                        break
                    length = struct.unpack(">H", seglen)[0]
                    if length < 2:
                        break
                    if code in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
                        data = f.read(length - 2)
                        if len(data) >= 5:
                            h, w = struct.unpack(">HH", data[1:5])
                            return int(w), int(h)
                        break
                    f.seek(length - 2, os.SEEK_CUR)
            # WebP (RIFF....WEBP)
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                f.seek(12)
                chunk = f.read(16)
                if chunk[:4] == b"VP8 " and len(chunk) >= 14:
                    # lossy: width/height in frame header after 10 bytes of payload start
                    pass
                if chunk[:4] == b"VP8X" and len(chunk) >= 14:
                    # canvas size: 3 bytes each little-endian minus 1
                    raw = chunk[8:14] if len(chunk) >= 14 else b""
                    if len(raw) == 6:
                        w = 1 + raw[0] + (raw[1] << 8) + (raw[2] << 16)
                        h = 1 + raw[3] + (raw[4] << 8) + (raw[5] << 16)
                        return int(w), int(h)
    except Exception:
        pass
    return 0, 0


def _read_jpeg_exif_basic(path: str) -> dict:
    """EXIF minimi da JPEG (data scatto, marca, modello) senza Pillow."""
    import struct
    out = {}
    try:
        with open(path, "rb") as f:
            if f.read(2) != b"\xff\xd8":
                return out
            while True:
                marker = f.read(2)
                if len(marker) < 2 or marker[0] != 0xFF:
                    break
                code = marker[1]
                if code in (0xD8, 0xD9):
                    continue
                seglen = f.read(2)
                if len(seglen) < 2:
                    break
                length = struct.unpack(">H", seglen)[0]
                if length < 2:
                    break
                data = f.read(length - 2)
                if code == 0xE1 and data.startswith(b"Exif\x00\x00"):
                    tiff = data[6:]
                    if len(tiff) < 8:
                        break
                    endian = "<" if tiff[:2] == b"II" else ">"
                    if tiff[2:4] != (b"\x2a\x00" if endian == "<" else b"\x00\x2a"):
                        break
                    ifd0 = struct.unpack(endian + "I", tiff[4:8])[0]
                    out.update(_parse_exif_ifd(tiff, ifd0, endian))
                    # EXIF sub-IFD (tag 0x8769) per DateTimeOriginal
                    sub = out.pop("_exif_ifd", None)
                    if sub:
                        out.update(_parse_exif_ifd(tiff, sub, endian))
                    break
                if code == 0xDA:  # SOS — fine header
                    break
    except Exception:
        pass
    return out


def _parse_exif_ifd(tiff: bytes, offset: int, endian: str) -> dict:
    import struct
    out = {}
    try:
        if offset < 0 or offset + 2 > len(tiff):
            return out
        n = struct.unpack(endian + "H", tiff[offset:offset + 2])[0]
        pos = offset + 2
        for _ in range(n):
            if pos + 12 > len(tiff):
                break
            tag, typ, count = struct.unpack(endian + "HHI", tiff[pos:pos + 8])
            val_raw = tiff[pos + 8:pos + 12]
            pos += 12
            type_size = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1}.get(typ, 1)
            nbytes = count * type_size
            if nbytes <= 4:
                data = val_raw[:nbytes]
            else:
                off = struct.unpack(endian + "I", val_raw)[0]
                data = tiff[off:off + nbytes]
            if tag == 0x010F and typ == 2:  # Make
                out["make"] = data.split(b"\x00")[0].decode("latin1", errors="ignore").strip()
            elif tag == 0x0110 and typ == 2:  # Model
                out["model"] = data.split(b"\x00")[0].decode("latin1", errors="ignore").strip()
            elif tag == 0x0132 and typ == 2:  # DateTime
                out["datetime"] = data.split(b"\x00")[0].decode("latin1", errors="ignore").strip()
            elif tag == 0x9003 and typ == 2:  # DateTimeOriginal
                out["datetime_original"] = (
                    data.split(b"\x00")[0].decode("latin1", errors="ignore").strip()
                )
            elif tag == 0x8769 and typ == 4:  # ExifIFDPointer
                out["_exif_ifd"] = struct.unpack(endian + "I", val_raw)[0]
    except Exception:
        pass
    return out


def get_image_tech_info(path: str) -> dict:
    """Scheda tecnica locale (B): dimensioni, formato, dimensione file, date, EXIF base."""
    info = {
        "path": path or "",
        "file_name": os.path.basename(path or "") or "",
        "ext": "",
        "format_label": "",
        "width": 0,
        "height": 0,
        "size_bytes": 0,
        "mtime": 0.0,
        "mtime_label": "",
        "exif_datetime": "",
        "exif_camera": "",
        "ok": False,
        "error": "",
    }
    if not path or not os.path.isfile(path):
        info["error"] = "File non trovato."
        return info
    ext = os.path.splitext(path)[1].lower()
    info["ext"] = ext
    fmt_map = {
        ".jpg": "JPEG", ".jpeg": "JPEG", ".jfif": "JPEG",
        ".png": "PNG", ".gif": "GIF", ".bmp": "BMP",
        ".tif": "TIFF", ".tiff": "TIFF", ".webp": "WebP", ".ico": "ICO",
    }
    info["format_label"] = fmt_map.get(ext, ext.replace(".", "").upper() or "sconosciuto")
    try:
        info["size_bytes"] = int(os.path.getsize(path))
    except Exception:
        info["size_bytes"] = 0
    try:
        info["mtime"] = float(os.path.getmtime(path))
        import datetime as _dt
        info["mtime_label"] = _dt.datetime.fromtimestamp(info["mtime"]).strftime(
            "%d/%m/%Y %H:%M"
        )
    except Exception:
        pass
    w, h = _read_image_dimensions(path)
    info["width"], info["height"] = w, h
    if ext in (".jpg", ".jpeg", ".jfif"):
        exif = _read_jpeg_exif_basic(path)
        dt = exif.get("datetime_original") or exif.get("datetime") or ""
        info["exif_datetime"] = dt.replace(":", "-", 2) if dt else ""
        cam_parts = [p for p in (exif.get("make"), exif.get("model")) if p]
        # Evita "Canon Canon EOS…"
        if len(cam_parts) == 2 and cam_parts[1].lower().startswith(cam_parts[0].lower()):
            info["exif_camera"] = cam_parts[1]
        else:
            info["exif_camera"] = " ".join(cam_parts).strip()
    info["ok"] = True
    return info


def format_tech_sheet(info: dict) -> str:
    """Testo accessibile della scheda tecnica (B)."""
    if not info:
        return "Scheda tecnica non disponibile."
    if not info.get("ok"):
        return info.get("error") or "Scheda tecnica non disponibile."
    lines = [
        f"Scheda tecnica: {info.get('file_name') or 'immagine'}",
        f"Formato: {info.get('format_label') or 'sconosciuto'}.",
    ]
    w, h = int(info.get("width") or 0), int(info.get("height") or 0)
    if w > 0 and h > 0:
        lines.append(f"Dimensioni: {w} per {h} pixel.")
    else:
        lines.append("Dimensioni: non rilevate.")
    size_b = int(info.get("size_bytes") or 0)
    if size_b > 0:
        if size_b < 1024:
            sz = f"{size_b} byte"
        elif size_b < 1024 * 1024:
            sz = f"{size_b / 1024:.1f} KB"
        else:
            sz = f"{size_b / (1024 * 1024):.2f} MB"
        lines.append(f"Dimensione file: {sz}.")
    if info.get("mtime_label"):
        lines.append(f"Data file: {info['mtime_label']}.")
    if info.get("exif_datetime"):
        lines.append(f"Data scatto (EXIF): {info['exif_datetime']}.")
    if info.get("exif_camera"):
        lines.append(f"Fotocamera: {info['exif_camera']}.")
    return "\n".join(lines)


def _google_vision_annotate(path: str, features: list) -> tuple:
    """Chiama Vision annotate. Restituisce (response_dict|None, diag)."""
    global _google_last_error
    key = (_google_api_key or "").strip()
    if not key:
        _google_last_error = "chiave API assente"
        return None, "google: chiave API assente"
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception as e:
        return None, f"google: lettura ({e})"
    if not raw:
        return None, "google: file vuoto"
    if len(raw) > MAX_OCR_IMAGE_BYTES:
        return None, "google: file troppo grande"
    payload = {
        "requests": [
            {
                "image": {"content": base64.b64encode(raw).decode("ascii")},
                "features": features,
                "imageContext": {"languageHints": ["it", "en"]},
            }
        ]
    }
    url = f"{_GOOGLE_VISION_URL}?key={urllib.parse.quote(key, safe='')}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        _stats["google_calls"] = int(_stats.get("google_calls", 0) or 0) + 1
        with urllib.request.urlopen(req, timeout=OCR_SOFT_TIMEOUT_SEC) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            pass
        msg = f"HTTP {e.code}"
        if err_body:
            msg += f": {err_body}"
        _google_last_error = msg
        return None, f"google: {msg}"
    except Exception as e:
        _google_last_error = str(e)
        return None, f"google: {e}"
    try:
        responses = data.get("responses") or []
        if not responses:
            return None, "google: risposta vuota"
        r0 = responses[0] or {}
        if r0.get("error"):
            err = r0.get("error") or {}
            msg = err.get("message") or str(err)
            _google_last_error = msg
            return None, f"google: {msg}"
        _google_last_error = ""
        return r0, "google"
    except Exception as e:
        return None, f"google parse: {e}"


def _parse_vision_response(r0: dict) -> dict:
    """Estrae etichette, oggetti, colori, landmark e testo da una response Vision."""
    labels = []
    for ann in r0.get("labelAnnotations") or []:
        desc = (ann.get("description") or "").strip()
        if not desc:
            continue
        score = float(ann.get("score") or 0)
        labels.append({"en": desc, "it": _label_to_it(desc), "score": score})
    objects = []
    for ann in r0.get("localizedObjectAnnotations") or []:
        name = (ann.get("name") or "").strip()
        if not name:
            continue
        score = float(ann.get("score") or 0)
        objects.append({"en": name, "it": _label_to_it(name), "score": score})
    colors = []
    props = r0.get("imagePropertiesAnnotation") or {}
    colors_block = (props.get("dominantColors") or {}).get("colors") or []
    for c in colors_block[:6]:
        col = c.get("color") or {}
        r = float(col.get("red") or 0)
        g = float(col.get("green") or 0)
        b = float(col.get("blue") or 0)
        frac = float(c.get("pixelFraction") or 0)
        colors.append({
            "r": r, "g": g, "b": b,
            "name_it": _color_name_it(r, g, b),
            "fraction": frac,
        })
    landmarks = []
    for ann in r0.get("landmarkAnnotations") or []:
        desc = (ann.get("description") or "").strip()
        if desc:
            landmarks.append(desc)
    ocr_text = ""
    full = r0.get("fullTextAnnotation") or {}
    ocr_text = (full.get("text") or "").strip()
    if not ocr_text:
        anns = r0.get("textAnnotations") or []
        if anns:
            ocr_text = (anns[0].get("description") or "").strip()
    return {
        "labels": labels,
        "objects": objects,
        "colors": colors,
        "landmarks": landmarks,
        "ocr_text": ocr_text,
    }


def analyze_image_visual(path: str, should_abort=None, use_cache: bool = True) -> dict:
    """Analisi Vision (etichette/oggetti/colori/landmark/testo). Richiede chiave Google.

    Restituisce dict con ok, error, labels, objects, colors, landmarks, ocr_text, source.
    """
    result = {
        "ok": False,
        "error": "",
        "labels": [],
        "objects": [],
        "colors": [],
        "landmarks": [],
        "ocr_text": "",
        "source": "",
        "path": path or "",
    }
    if not path or not os.path.isfile(path):
        result["error"] = "File non trovato."
        return result
    if not is_image_path(path):
        result["error"] = "Il file non è un'immagine supportata."
        return result
    if should_abort and should_abort():
        result["error"] = "Annullato."
        return result
    try:
        size = os.path.getsize(path)
        mtime = os.path.getmtime(path)
    except Exception as e:
        result["error"] = str(e)
        return result
    if size <= 0 or size > MAX_OCR_IMAGE_BYTES:
        result["error"] = "File troppo grande o vuoto per l'analisi."
        return result

    cache_key = _vision_cache_key(path, size, mtime, "full")
    if use_cache:
        cached = _vision_cache_get(cache_key)
        if isinstance(cached, dict) and cached.get("ok"):
            _stats["cache_hits"] = int(_stats.get("cache_hits", 0) or 0) + 1
            cached = dict(cached)
            cached["source"] = (cached.get("source") or "cache") + "+cache"
            return cached

    if not has_google_api_key():
        result["error"] = (
            "Per descrivere il contenuto dell'immagine serve la chiave API "
            "Google Vision (Strumenti → Chiave API Google Vision)."
        )
        return result

    features = [
        {"type": "LABEL_DETECTION", "maxResults": 12},
        {"type": "OBJECT_LOCALIZATION", "maxResults": 10},
        {"type": "IMAGE_PROPERTIES", "maxResults": 1},
        {"type": "LANDMARK_DETECTION", "maxResults": 3},
        {"type": "TEXT_DETECTION", "maxResults": 1},
    ]
    r0, diag = _google_vision_annotate(path, features)
    if not r0:
        result["error"] = diag or "Analisi Vision non riuscita."
        return result
    parsed = _parse_vision_response(r0)
    result.update(parsed)
    result["ok"] = True
    result["source"] = diag or "google"
    result["error"] = ""
    if use_cache:
        _vision_cache_put(cache_key, {
            "ok": True,
            "error": "",
            "labels": result["labels"],
            "objects": result["objects"],
            "colors": result["colors"],
            "landmarks": result["landmarks"],
            "ocr_text": result["ocr_text"],
            "source": "google",
            "path": path,
        })
    return result


def get_image_label_strings(path: str, should_abort=None) -> list:
    """Elenco stringhe (IT+EN) per ricerca contenuto visivo. Cache Vision."""
    data = analyze_image_visual(path, should_abort=should_abort, use_cache=True)
    if not data.get("ok"):
        return []
    out = []
    for item in (data.get("labels") or []) + (data.get("objects") or []):
        for k in ("it", "en"):
            s = (item.get(k) or "").strip().lower()
            if s and s not in out:
                out.append(s)
    for lm in data.get("landmarks") or []:
        s = str(lm).strip().lower()
        if s and s not in out:
            out.append(s)
    for c in data.get("colors") or []:
        s = (c.get("name_it") or "").strip().lower()
        if s and s not in out:
            out.append(s)
    return out


def visual_labels_match_terms(labels, terms) -> bool:
    """True se tutti i termini compaiono nelle etichette/oggetti (IT o EN)."""
    if not labels or not terms:
        return False
    blob = " ".join(str(x).lower() for x in labels if x)
    if not blob:
        return False
    # Riusa la logica tollerante OCR (sinonimi, fold)
    return ocr_text_matches_terms(blob, terms)


def _uniq_keep_order(items):
    out = []
    seen = set()
    for x in items:
        s = (str(x) or "").strip()
        if not s:
            continue
        key = s.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def format_labels_text(data: dict) -> str:
    """Testo etichette/oggetti per dialoghi e copia."""
    if not data:
        return "Nessuna etichetta disponibile."
    if not data.get("ok"):
        return data.get("error") or "Analisi non disponibile."
    lines = []
    labs = data.get("labels") or []
    if labs:
        parts = []
        for L in labs[:12]:
            it = L.get("it") or L.get("en") or ""
            en = L.get("en") or ""
            if it and en and it.lower() != en.lower():
                parts.append(f"{it} ({en})")
            elif it:
                parts.append(it)
        parts = _uniq_keep_order(parts)
        if parts:
            lines.append("Etichette: " + ", ".join(parts) + ".")
    objs = data.get("objects") or []
    if objs:
        parts = []
        for O in objs[:10]:
            it = O.get("it") or O.get("en") or ""
            if it:
                parts.append(it)
        parts = _uniq_keep_order(parts)
        if parts:
            lines.append("Oggetti riconosciuti: " + ", ".join(parts) + ".")
    lms = data.get("landmarks") or []
    if lms:
        lines.append("Luoghi: " + ", ".join(_uniq_keep_order(lms)) + ".")
    cols = data.get("colors") or []
    if cols:
        names = []
        for c in cols[:5]:
            n = c.get("name_it") or ""
            if n and n not in names:
                names.append(n)
        if names:
            lines.append("Colori dominanti: " + ", ".join(names) + ".")
    if not lines:
        return "Nessuna etichetta rilevata in questa immagine."
    return "\n".join(lines)


def format_image_description(path: str, visual: dict = None, tech: dict = None,
                             include_tech: bool = True, include_ocr: bool = True) -> str:
    """Descrizione accessibile da etichette Vision (fallback se Gemini assente)."""
    parts = []
    name = os.path.basename(path or "") or "immagine"
    parts.append(f"Descrizione di: {name}")
    parts.append(
        "(Livello etichette Google Vision. Per una descrizione narrativa "
        "completa inserisci la chiave API Gemini in Strumenti.)"
    )

    if visual is None:
        visual = analyze_image_visual(path) if path else {"ok": False, "error": "Percorso assente."}

    if visual.get("ok"):
        labs = visual.get("labels") or []
        objs = visual.get("objects") or []
        top = _uniq_keep_order(
            [L.get("it") or L.get("en") for L in labs[:6] if (L.get("it") or L.get("en"))]
        )
        if top:
            if len(top) == 1:
                parts.append(f"L'immagine riguarda soprattutto: {top[0]}.")
            else:
                parts.append(
                    "L'immagine riguarda soprattutto: "
                    + ", ".join(top[:-1])
                    + " e "
                    + top[-1]
                    + "."
                )
        obj_names = _uniq_keep_order(
            [O.get("it") or O.get("en") for O in objs[:8] if (O.get("it") or O.get("en"))]
        )
        top_cf = {t.casefold() for t in top}
        obj_names = [o for o in obj_names if o.casefold() not in top_cf]
        if obj_names:
            parts.append("Si vedono anche: " + ", ".join(obj_names) + ".")
        lms = _uniq_keep_order(visual.get("landmarks") or [])
        if lms:
            parts.append("Luogo riconosciuto: " + ", ".join(lms) + ".")
        cols = visual.get("colors") or []
        cnames = []
        for c in cols[:4]:
            n = c.get("name_it") or ""
            if n and n not in cnames:
                cnames.append(n)
        if cnames:
            parts.append("Colori dominanti: " + ", ".join(cnames) + ".")
        if include_ocr:
            ocr = (visual.get("ocr_text") or "").strip()
            if ocr:
                compact = " ".join(ocr.split())
                if len(compact) > 500:
                    compact = compact[:497] + "…"
                parts.append(f"Testo presente nell'immagine: {compact}")
    else:
        err = visual.get("error") or ""
        if err:
            parts.append(err)
        else:
            parts.append("Descrizione del contenuto non disponibile.")
        if include_ocr and path and engine_available():
            try:
                ocr = (ocr_image_file(path) or "").strip()
            except Exception:
                ocr = ""
            if ocr:
                compact = " ".join(ocr.split())
                if len(compact) > 500:
                    compact = compact[:497] + "…"
                parts.append(f"Testo letto con OCR: {compact}")

    if include_tech:
        if tech is None:
            tech = get_image_tech_info(path)
        tech_block = format_tech_sheet(tech)
        if tech_block:
            parts.append("")
            parts.append(tech_block)

    return "\n".join(parts).strip()


_GEMINI_DESCRIBE_PROMPT = """\
Sei un assistente di accessibilità per persone cieche e ipovedenti.
Descrivi l'immagine in italiano chiaro, preciso e immersivo: chi ascolta
deve potersi sentire «dentro» la scena.

PRIORITÀ ASSOLUTA — anti-allucinazione:
1) Descrivi SOLO ciò che vedi in QUESTA immagine, non articoli o prime pagine
   famose del passato che ti ricordano qualcosa di simile.
2) Se nel messaggio utente c'è un blocco «Indizi dal file / OCR», usalo come
   ancoraggio: date nel nome file, data OCR, citazioni OCR hanno priorità
   sulla tua memoria storica.
3) Se leggi una data nell'immagine (giorno/mese/anno), riportala ESATTAMENTE
   come appare. Non «correggerla» in anni precedenti (es. 2026 non diventa 2020).
4) Nomi propri di persone: solo se sei molto sicuro dal volto O se il nome
   è scritto nell'immagine/OCR. Se non sei sicuro, descrivi senza nome
   («uomo calvo con barba», «allenatore in polo», «pilota con tuta») invece
   di inventare o ripescare nomi d'epoca sbagliata.
5) Non mescolare epoche: se la pagina è del 2026, non raccontare come se fosse
   il 2020 (Nations League di allora, Pirlo allenatore Juve, ecc.) a meno che
   il testo nell'immagine lo dica chiaramente.
6) Per i testi: preferisci le stringhe dell'OCR fornito; puoi correggere solo
   errori OCR evidenti (lettere scambiate), non riscrivere i fatti.

Altre regole:
- Scrivi solo in italiano.
- Distingui fotografia reale da grafica/locandina/prima pagina di giornale.
- Completa SEMPRE tutte le sezioni: non interrompere a metà frase.
- Titoli di sezione in testo semplice (senza markdown ** grassetto).

Usa ESATTAMENTE queste sezioni (titoli inclusi):

Titolo
Una riga che riassume l'immagine.

Layout e composizione
Come è costruita l'immagine (sfondo, riquadri, colonne, foto, grafica).

Testi visibili
Elenco dei testi leggibili, con posizione. Se non ce ne sono: «Nessun testo rilevante.».

Soggetti e dettagli
Persone, abbigliamento, oggetti, espressioni. Nomi propri solo se sicuri
(vedi regole sopra). Chiudi con una frase completa.

Postura e movimento
Se ci sono persone: orientamento del corpo, appoggio, gambe/braccia, sguardo,
senso del movimento. Se non ci sono figure in azione:
«Nessuna figura in movimento rilevante.».

Luogo e contesto
Ambientazione e occasione. Allinea il contesto alla data letta nell'immagine
o negli indizi file/OCR, non a ricordi di altre epoche.

Note
Solo se serve una precisazione breve (es. «alcuni volti nei riquadri piccoli
non sono identificabili con certezza»); altrimenti ometti la sezione.
"""

_GEMINI_ALT_TEXT_PROMPT = """\
Sei un assistente di accessibilità per persone cieche e ipovedenti.
Scrivi un ALT-TEXT breve in italiano per questa immagine.

Obiettivo: dare l'idea dell'immagine in una frase completa (due solo se serve).
Lunghezza ideale 100–160 caratteri; completa sempre la frase (punto finale).

Includi, se riconoscibili: chi/cosa è in primo piano, contesto (es. maglia,
evento, slide), testi importanti leggibili (nomi, titoli).

Vietato:
- markdown, asterischi, elenchi, titoli tipo Context/Description/Alt-text
- inglese o altre lingue
- note tecniche, scuse, puntini di sospensione finali
- nomi o date inventati (se non sicuri, resta generico)

Output: solo la frase alt in italiano, nient'altro.
"""


def _clean_alt_text(raw: str) -> str:
    """Normalizza l'alt Gemini: italiano in chiaro, senza markdown/scheletri."""
    clean = (raw or "").replace("\r", "\n").strip()
    if not clean:
        return ""
    # Se il modello ha risposto con blocchi tipo **Context:** … tieni solo
    # pezzi utili in italiano, scarta etichette inglesi/markdown.
    lines = []
    for line in clean.split("\n"):
        s = line.strip()
        if not s:
            continue
        s = re.sub(r"^#{1,6}\s*", "", s)
        s = re.sub(r"^\*+\s*", "", s)
        s = re.sub(r"^[-•]\s*", "", s)
        s = re.sub(r"\*+", "", s)
        s = re.sub(r"`+", "", s)
        s = s.strip().strip('"').strip("'").strip()
        low = s.lower()
        if low.startswith((
            "context:", "description:", "alt-text:", "alt text:",
            "alt:", "image description:", "caption:",
        )):
            s = s.split(":", 1)[-1].strip()
        if not s or s in {".", "…", "...", '""', "''"}:
            continue
        # Scarta residui tipici di scheletri inglesi
        if re.match(r"^(there is an?|this (image|graphic)|context)\b", s, re.I):
            continue
        lines.append(s)
    clean = " ".join(lines) if lines else " ".join(clean.split())
    clean = " ".join(clean.split())
    if clean.lower().startswith("alt-text:"):
        clean = clean[9:].strip()
    for marker in (
        "(Nota: la descrizione è stata leggermente",
        "(nota: la descrizione è stata leggermente",
        "Nota: la descrizione è stata leggermente",
    ):
        idx = clean.find(marker)
        if idx >= 0:
            clean = clean[:idx].strip()
    # Al più due frasi
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", clean)
        if s.strip()
    ]
    if not sentences:
        return ""
    # Evita di tenere una sola "frase" tagliata con … se c'è di meglio
    picked = []
    for s in sentences:
        if s.endswith("…") and len(s) < 40 and picked:
            continue
        picked.append(s)
        if len(picked) >= 2:
            break
    clean = " ".join(picked).strip()
    # Taglio morbido a ~180, preferendo fine parola; evita … se già completa
    if len(clean) > 180:
        cut = clean[:177].rsplit(" ", 1)[0]
        clean = (cut or clean[:177]).rstrip(",;:…")
        if not clean.endswith((".", "!", "?")):
            clean += "…"
    return clean


def _parse_date_hint_from_name(name: str) -> str:
    """Estrae indizio data da nome file tipo 05-10-2026 o 2026-10-05."""
    import re
    s = name or ""
    m = re.search(r"(?<!\d)(\d{2})[-_.](\d{2})[-_.](\d{4})(?!\d)", s)
    if m:
        gg, mm, aaaa = m.group(1), m.group(2), m.group(3)
        try:
            if 1 <= int(mm) <= 12 and 1 <= int(gg) <= 31:
                return f"{gg}/{mm}/{aaaa}"
        except Exception:
            pass
    m = re.search(r"(?<!\d)(\d{4})[-_.](\d{2})[-_.](\d{2})(?!\d)", s)
    if m:
        aaaa, mm, gg = m.group(1), m.group(2), m.group(3)
        try:
            if 1 <= int(mm) <= 12 and 1 <= int(gg) <= 31:
                return f"{gg}/{mm}/{aaaa}"
        except Exception:
            pass
    return ""


def _build_gemini_grounding(path: str) -> str:
    """Indizi file + OCR Vision per ancorare Gemini e ridurre allucinazioni."""
    lines = ["Indizi dal file / OCR (ancora fattuale — rispettali):"]
    base = os.path.basename(path or "") or ""
    if base:
        lines.append(f"- Nome file: {base}")
    date_hint = _parse_date_hint_from_name(base)
    if date_hint:
        lines.append(
            f"- Data suggerita dal nome file: {date_hint} "
            f"(se nell'immagine leggi una data diversa, preferisci quella "
            f"dell'immagine; non sostituirla con anni di articoli storici)."
        )
    try:
        tech = get_image_tech_info(path)
        if tech.get("mtime_label"):
            lines.append(f"- Data del file sul disco: {tech['mtime_label']}")
    except Exception:
        pass
    ocr_txt = ""
    try:
        if has_google_api_key():
            vis = analyze_image_visual(path, use_cache=True)
            if vis.get("ok"):
                ocr_txt = (vis.get("ocr_text") or "").strip()
        if not ocr_txt and engine_available():
            ocr_txt = (ocr_image_file(path) or "").strip()
    except Exception:
        ocr_txt = ""
    if ocr_txt:
        compact = " ".join(ocr_txt.split())
        if len(compact) > 2500:
            compact = compact[:2497] + "…"
        lines.append("- Testo OCR rilevato nell'immagine (usa come riferimento per citazioni e date):")
        lines.append(compact)
    else:
        lines.append(
            "- OCR non disponibile: leggi i testi direttamente dall'immagine, "
            "senza inventare citazioni."
        )
    lines.append(
        "Se un volto nei riquadri piccoli non è riconoscibile con certezza, "
        "NON assegnare un nome famoso: descrivi solo aspetto e ruolo."
    )
    return "\n".join(lines)


def _mime_for_image_path(path: str) -> str:
    ext = os.path.splitext(path or "")[1].lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".jfif": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".ico": "image/x-icon",
    }.get(ext, "image/jpeg")


def _gemini_list_generate_models(key: str) -> list:
    """Elenco modelli che supportano generateContent (nome corto, senza 'models/')."""
    global _gemini_models_cache, _gemini_models_cache_key
    key = (key or "").strip()
    if not key:
        return []
    if _gemini_models_cache is not None and _gemini_models_cache_key == key:
        return list(_gemini_models_cache)
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models"
        f"?key={urllib.parse.quote(key, safe='')}&pageSize=100"
    )
    names = []
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body) if body else {}
        for m in data.get("models") or []:
            methods = m.get("supportedGenerationMethods") or []
            if "generateContent" not in methods:
                continue
            name = (m.get("name") or "").strip()
            if name.startswith("models/"):
                name = name[len("models/"):]
            # Solo Flash/Pro utili per descrizione immagini (niente TTS/Live/Embedding)
            low = name.lower()
            if any(
                skip in low
                for skip in (
                    "tts", "live", "embed", "image", "veo", "lyria",
                    "transcribe", "robotics", "omni", "deep-research",
                    "antigravity", "computer-use",
                )
            ):
                continue
            if "flash" in low or "pro" in low or low.endswith("-latest"):
                if name and name not in names:
                    names.append(name)
    except Exception as e:
        logging.debug(f"ListModels Gemini fallito: {e}")
        names = []
    _gemini_models_cache = names
    _gemini_models_cache_key = key
    return list(names)


def _gemini_model_candidates(key: str) -> list:
    """Ordine di prova: preferiti attuali, poi quelli scoperti dalla chiave."""
    ordered = []
    seen = set()

    def _add(name: str):
        n = (name or "").strip()
        if not n or n in seen:
            return
        seen.add(n)
        ordered.append(n)

    for n in _GEMINI_MODELS_PREFERRED:
        _add(n)
    for n in _gemini_list_generate_models(key):
        _add(n)
    return ordered


def _gemini_generate_description(
    path: str,
    should_abort=None,
    prompt: str = None,
    max_output_tokens: int = 8192,
    use_grounding: bool = True,
    append_truncation_note: bool = True,
) -> tuple:
    """Chiama Gemini multimodal. Restituisce (testo, diag)."""
    global _gemini_last_error
    key = (_gemini_api_key or "").strip()
    if not key:
        _gemini_last_error = "chiave API Gemini assente"
        return "", "gemini: chiave API assente"
    if should_abort and should_abort():
        return "", "gemini: annullato"
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception as e:
        _gemini_last_error = f"lettura file: {e}"
        return "", f"gemini: lettura ({e})"
    if not raw:
        return "", "gemini: file vuoto"
    if len(raw) > MAX_OCR_IMAGE_BYTES:
        return "", "gemini: file troppo grande"

    b64 = base64.b64encode(raw).decode("ascii")
    mime = _mime_for_image_path(path)
    grounding = ""
    if use_grounding:
        try:
            grounding = _build_gemini_grounding(path)
        except Exception as e:
            logging.debug(f"Grounding Gemini non disponibile: {e}")
            grounding = ""
    user_text = prompt or _GEMINI_DESCRIBE_PROMPT
    if grounding:
        user_text = user_text + "\n\n" + grounding
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": user_text},
                    {"inline_data": {"mime_type": mime, "data": b64}},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": int(max_output_tokens or 8192),
        },
    }
    body = json.dumps(payload).encode("utf-8")
    last_err = ""
    tried = []
    models = _gemini_model_candidates(key)
    if not models:
        models = list(_GEMINI_MODELS_PREFERRED)
    for model in models:
        if should_abort and should_abort():
            return "", "gemini: annullato"
        tried.append(model)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={urllib.parse.quote(key, safe='')}"
        )
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            _stats["gemini_calls"] = int(_stats.get("gemini_calls", 0) or 0) + 1
            with urllib.request.urlopen(req, timeout=_GEMINI_TIMEOUT_SEC) as resp:
                resp_body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(resp_body) if resp_body else {}
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                pass
            last_err = f"HTTP {e.code} ({model})"
            if err_body:
                last_err += f": {err_body}"
            # 404/429: prova il modello successivo
            if e.code in (404, 429):
                continue
            # 400 spesso = modello non adatto all'immagine → continua
            if e.code == 400 and "not found" in (err_body or "").lower():
                continue
            _gemini_last_error = last_err
            logging.warning(f"Gemini descrizione fallita: {last_err}")
            return "", f"gemini: {last_err}"
        except Exception as e:
            last_err = f"{model}: {e}"
            _gemini_last_error = last_err
            logging.warning(f"Gemini errore: {e}")
            return "", f"gemini: {e}"

        try:
            cands = data.get("candidates") or []
            if not cands:
                pf = data.get("promptFeedback") or {}
                last_err = f"{model}: nessuna risposta ({pf or 'vuoto'})"
                continue
            parts = (((cands[0] or {}).get("content") or {}).get("parts")) or []
            texts = []
            for p in parts:
                t = (p.get("text") or "").strip()
                if t:
                    texts.append(t)
            text = "\n".join(texts).strip()
            if text:
                finish = str((cands[0] or {}).get("finishReason") or "")
                if finish.upper() in ("MAX_TOKENS", "LENGTH"):
                    # Completa in modo leggibile se il modello ha tagliato
                    if not text.endswith((".", "!", "?", "»", '"', "…")):
                        text = text.rstrip(",;:") + "…"
                    if append_truncation_note:
                        text += (
                            "\n\n(Nota: la descrizione è stata leggermente "
                            "accorciata dal limite tecnico; i punti principali "
                            "restano comunque presenti.)"
                        )
                _gemini_last_error = ""
                return text, f"gemini:{model}"
            last_err = f"{model}: testo vuoto"
        except Exception as e:
            last_err = f"{model} parse: {e}"
            continue

    short_tried = ", ".join(tried[:6])
    if len(tried) > 6:
        short_tried += f"… (+{len(tried) - 6})"
    _gemini_last_error = last_err or "nessun modello Gemini disponibile"
    return (
        "",
        f"gemini: {_gemini_last_error} [provati: {short_tried}]",
    )


def describe_image_gemini(path: str, should_abort=None, use_cache: bool = True) -> dict:
    """Descrizione narrativa avanzata via Gemini. Dict: ok, text, error, source."""
    result = {
        "ok": False,
        "text": "",
        "error": "",
        "source": "",
        "path": path or "",
    }
    if not path or not os.path.isfile(path):
        result["error"] = "File non trovato."
        return result
    if not is_image_path(path):
        result["error"] = "Il file non è un'immagine supportata."
        return result
    if not has_gemini_api_key():
        result["error"] = (
            "Per la descrizione avanzata serve la chiave API Gemini "
            "(Strumenti → Chiave API Gemini / Google AI Studio)."
        )
        return result
    try:
        size = os.path.getsize(path)
        mtime = os.path.getmtime(path)
    except Exception as e:
        result["error"] = str(e)
        return result
    if size <= 0 or size > MAX_OCR_IMAGE_BYTES:
        result["error"] = "File troppo grande o vuoto."
        return result

    # v6: grounding OCR/data file + anti-allucinazione epoche/nomi
    cache_key = _vision_cache_key(path, size, mtime, "gemini_desc_v6")
    if use_cache:
        cached = _vision_cache_get(cache_key)
        if isinstance(cached, dict) and cached.get("ok") and cached.get("text"):
            _stats["cache_hits"] = int(_stats.get("cache_hits", 0) or 0) + 1
            out = dict(cached)
            out["source"] = (out.get("source") or "gemini") + "+cache"
            return out

    text, diag = _gemini_generate_description(path, should_abort=should_abort)
    if not text:
        result["error"] = diag or (_gemini_last_error or "Descrizione Gemini non riuscita.")
        return result
    result["ok"] = True
    result["text"] = text
    result["source"] = diag or "gemini"
    result["error"] = ""
    if use_cache:
        _vision_cache_put(cache_key, {
            "ok": True,
            "text": text,
            "error": "",
            "source": result["source"],
            "path": path,
        })
    return result


def describe_image_alt_text(path: str, should_abort=None, use_cache: bool = True) -> dict:
    """Alt-text breve via Gemini. Dict: ok, text, error, source."""
    result = {
        "ok": False,
        "text": "",
        "error": "",
        "source": "",
        "path": path or "",
    }
    if not path or not os.path.isfile(path):
        result["error"] = "File non trovato."
        return result
    if not is_image_path(path):
        result["error"] = "Il file non è un'immagine supportata."
        return result
    if not has_gemini_api_key():
        result["error"] = (
            "Per l'alt-text serve la chiave API Gemini "
            "(Strumenti → Chiave API Gemini / Google AI Studio)."
        )
        return result
    try:
        size = os.path.getsize(path)
        mtime = os.path.getmtime(path)
    except Exception as e:
        result["error"] = str(e)
        return result
    if size <= 0 or size > MAX_OCR_IMAGE_BYTES:
        result["error"] = "File troppo grande o vuoto."
        return result

    # v3: budget token più alto (i modelli 3.x usano thinking) + pulizia markdown
    cache_key = _vision_cache_key(path, size, mtime, "gemini_alt_v3")
    if use_cache:
        cached = _vision_cache_get(cache_key)
        if isinstance(cached, dict) and cached.get("ok") and cached.get("text"):
            cached_text = (cached.get("text") or "").strip()
            # Non riusare alt troppo corti/rotti da prove precedenti
            if (
                len(cached_text) >= 40
                and "**" not in cached_text
                and "Context:" not in cached_text
            ):
                _stats["cache_hits"] = int(_stats.get("cache_hits", 0) or 0) + 1
                out = dict(cached)
                out["source"] = (out.get("source") or "gemini") + "+cache"
                return out

    text, diag = _gemini_generate_description(
        path,
        should_abort=should_abort,
        prompt=_GEMINI_ALT_TEXT_PROMPT,
        # Budget largo: sui Flash 3.x parte dei token va al thinking interno
        max_output_tokens=2048,
        use_grounding=True,
        append_truncation_note=False,
    )
    if not text:
        result["error"] = diag or (_gemini_last_error or "Alt-text Gemini non riuscito.")
        return result
    clean = _clean_alt_text(text)
    if len(clean) < 24 or "**" in clean or re.search(r"\bContext:\b", clean):
        result["error"] = "Alt-text troppo incompleto o non utilizzabile; riprova."
        return result
    result["ok"] = True
    result["text"] = clean
    result["source"] = diag or "gemini"
    result["error"] = ""
    if use_cache:
        _vision_cache_put(cache_key, {
            "ok": True,
            "text": clean,
            "error": "",
            "source": result["source"],
            "path": path,
        })
    return result


def format_alt_and_long_description(
    path: str, should_abort=None, include_tech: bool = True
) -> str:
    """Alt-text breve + descrizione lunga (+ scheda tecnica opzionale)."""
    parts = [f"Immagine: {os.path.basename(path) or 'immagine'}", ""]
    alt = describe_image_alt_text(path, should_abort=should_abort, use_cache=True)
    if alt.get("ok") and (alt.get("text") or "").strip():
        parts.extend(["Alt-text breve", (alt.get("text") or "").strip(), ""])
    else:
        parts.extend([
            "Alt-text breve",
            f"(Non disponibile: {alt.get('error') or 'errore sconosciuto'})",
            "",
        ])
    long_body = describe_image(
        path,
        should_abort=should_abort,
        include_tech=False,
        include_ocr=True,
        prefer_gemini=True,
    )
    if long_body:
        parts.extend(["Descrizione dettagliata", "", long_body.strip()])
    if include_tech:
        try:
            tech_block = format_tech_sheet(get_image_tech_info(path))
            if tech_block:
                parts.extend(["", tech_block])
        except Exception:
            pass
    return "\n".join(parts).strip()


def describe_image(path: str, should_abort=None, include_tech: bool = True,
                   include_ocr: bool = True, prefer_gemini: bool = True) -> str:
    """Descrizione completa: Gemini (se chiave) altrimenti Vision + scheda tecnica."""
    tech = get_image_tech_info(path)
    tech_block = format_tech_sheet(tech) if include_tech else ""

    if prefer_gemini and has_gemini_api_key():
        adv = describe_image_gemini(path, should_abort=should_abort, use_cache=True)
        if adv.get("ok") and (adv.get("text") or "").strip():
            parts = [
                f"Descrizione avanzata di: {os.path.basename(path) or 'immagine'}",
                "",
                (adv.get("text") or "").strip(),
            ]
            if tech_block:
                parts.extend(["", tech_block])
            return "\n".join(parts).strip()
        # Gemini fallita: continua con fallback Vision (segnala l’errore)
        note = adv.get("error") or gemini_last_error() or "Gemini non disponibile."
        visual = analyze_image_visual(path, should_abort=should_abort, use_cache=True)
        base = format_image_description(
            path, visual=visual, tech=tech,
            include_tech=False, include_ocr=include_ocr,
        )
        parts = [base, "", f"Nota: descrizione avanzata Gemini non usata ({note})."]
        if tech_block:
            parts.extend(["", tech_block])
        return "\n".join(parts).strip()

    visual = analyze_image_visual(path, should_abort=should_abort, use_cache=True)
    return format_image_description(
        path, visual=visual, tech=tech,
        include_tech=include_tech, include_ocr=include_ocr,
    )


def vision_status_message() -> str:
    """Messaggio stato analisi visiva (per UI)."""
    bits = []
    if has_gemini_api_key():
        bits.append("Descrizione avanzata Gemini pronta.")
    else:
        bits.append(
            "Descrizione avanzata: inserisci la chiave API Gemini "
            "(Strumenti → Chiave API Gemini)."
        )
    if has_google_api_key():
        bits.append("Etichette/ricerca visiva Google Vision pronte.")
    else:
        bits.append("Per etichette e ricerca visiva serve la chiave Google Vision.")
    bits.append("La scheda tecnica funziona sempre, anche senza chiavi.")
    return " ".join(bits)


# ---------------------------------------------------------------------------
# Materializza immagini da URL / bytes / rettangolo schermo (1.6.4)
# Usato da Standalone (URL, appunti, cattura) e Add-on (grafica navigator).
# ---------------------------------------------------------------------------

_WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 RTAD/1.6.4"
)
_WEB_MAX_BYTES = MAX_OCR_IMAGE_BYTES
_TEMP_IMAGE_PREFIXES = (
    "rtad_web_", "rtad_clip_", "rtad_cap_", "rtad_ocr_", "rtad_pdf_",
)


def is_likely_image_url(url: str) -> bool:
    """True se l'URL sembra un'immagine scaricabile (http/https)."""
    u = (url or "").strip()
    if not u:
        return False
    low = u.lower()
    if not (low.startswith("http://") or low.startswith("https://")):
        return False
    if low.startswith("https://data:") or "javascript:" in low:
        return False
    path = urllib.parse.urlparse(u).path.lower()
    if any(path.endswith(ext) for ext in _IMG_EXTS):
        return True
    # CDN / trasformazioni senza estensione nel path (Cloudinary-like, ecc.)
    if any(
        token in low
        for token in (
            "/image/",
            "/images/",
            "/img/",
            "/media/",
            "/photo",
            "/photos",
            "format=jpg",
            "format=png",
            "format=webp",
            "f_auto",
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
        )
    ):
        return True
    return False


def _sniff_image_suffix(data: bytes, content_type: str = "", url: str = "") -> str:
    """Estensione file da magic bytes / Content-Type / URL."""
    ct = (content_type or "").split(";")[0].strip().lower()
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:2] == b"BM":
        return ".bmp"
    ct_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/x-ms-bmp": ".bmp",
        "image/tiff": ".tif",
    }
    if ct in ct_map:
        return ct_map[ct]
    path = urllib.parse.urlparse(url or "").path.lower()
    for ext in sorted(_IMG_EXTS, key=len, reverse=True):
        if path.endswith(ext):
            return ext
    return ".jpg"


def materialize_image_from_bytes(
    data: bytes,
    suffix: str = "",
    prefix: str = "rtad_web_",
) -> dict:
    """Scrive bytes immagine su file temp. Dict: ok, path, error."""
    out = {"ok": False, "path": "", "error": ""}
    if not data:
        out["error"] = "Dati immagine vuoti."
        return out
    if len(data) > _WEB_MAX_BYTES:
        out["error"] = "Immagine troppo grande."
        return out
    ext = suffix if suffix.startswith(".") else _sniff_image_suffix(data)
    if ext not in _IMG_EXTS:
        ext = ".jpg"
    try:
        fd, tmp = tempfile.mkstemp(suffix=ext, prefix=prefix)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        out["ok"] = True
        out["path"] = tmp
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


def materialize_image_from_url(url: str, timeout: int = 45) -> dict:
    """Scarica un'immagine da URL http(s) su file temp. Dict: ok, path, error, url."""
    out = {"ok": False, "path": "", "error": "", "url": (url or "").strip()}
    u = out["url"]
    if not u:
        out["error"] = "URL vuoto."
        return out
    if not (u.lower().startswith("http://") or u.lower().startswith("https://")):
        out["error"] = "Serve un URL http o https."
        return out
    try:
        req = urllib.request.Request(
            u,
            headers={
                "User-Agent": _WEB_UA,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = resp.headers.get("Content-Type", "") or ""
            data = resp.read(_WEB_MAX_BYTES + 1)
            final_url = resp.geturl() or u
    except urllib.error.HTTPError as e:
        out["error"] = f"HTTP {e.code}: download immagine non riuscito."
        return out
    except Exception as e:
        out["error"] = f"Download non riuscito: {e}"
        return out
    if not data:
        out["error"] = "Risposta vuota dal server."
        return out
    if len(data) > _WEB_MAX_BYTES:
        out["error"] = "Immagine troppo grande."
        return out
    # Evita di passare HTML di errore a Gemini
    ctype_l = ctype.lower()
    if "text/html" in ctype_l or "application/json" in ctype_l:
        if not _sniff_image_suffix(data).startswith(".") or data[:1] in (b"<", b"{", b"["):
            if data.lstrip()[:1] in (b"<", b"{", b"["):
                out["error"] = "L'URL non punta a un'immagine (ricevuta pagina o JSON)."
                return out
    suffix = _sniff_image_suffix(data, ctype, final_url)
    saved = materialize_image_from_bytes(data, suffix=suffix, prefix="rtad_web_")
    if not saved.get("ok"):
        return saved
    out["ok"] = True
    out["path"] = saved["path"]
    out["url"] = final_url
    return out


def materialize_image_from_screen_rect(
    left: int, top: int, width: int, height: int
) -> dict:
    """Cattura un rettangolo dello schermo in BMP temp (Win32 GDI). Dict: ok, path, error."""
    out = {"ok": False, "path": "", "error": ""}
    try:
        left = int(left)
        top = int(top)
        width = int(width)
        height = int(height)
    except Exception:
        out["error"] = "Coordinate cattura non valide."
        return out
    if width < 2 or height < 2:
        out["error"] = "Area troppo piccola per la cattura."
        return out
    if width > 16000 or height > 16000:
        out["error"] = "Area di cattura troppo grande."
        return out
    import ctypes
    from ctypes import wintypes

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    hwnd_desk = user32.GetDesktopWindow()
    hdc_screen = user32.GetWindowDC(hwnd_desk)
    hdc_mem = None
    hbmp = None
    path = ""
    try:
        if not hdc_screen:
            out["error"] = "Impossibile accedere allo schermo."
            return out
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
        if not hdc_mem or not hbmp:
            out["error"] = "Impossibile creare il buffer di cattura."
            return out
        old = gdi32.SelectObject(hdc_mem, hbmp)
        ok_blit = gdi32.BitBlt(
            hdc_mem, 0, 0, width, height, hdc_screen, left, top, 0x00CC0020
        )
        gdi32.SelectObject(hdc_mem, old)
        if not ok_blit:
            out["error"] = "Cattura schermo non riuscita."
            return out

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = 40
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height  # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 24
        bmi.bmiHeader.biCompression = 0
        row = ((width * 3 + 3) // 4) * 4
        buf_size = row * height
        buf = (ctypes.c_byte * buf_size)()
        got = gdi32.GetDIBits(
            hdc_screen, hbmp, 0, height, buf, ctypes.byref(bmi), 0
        )
        if not got:
            out["error"] = "Lettura bitmap non riuscita."
            return out
        fd, path = tempfile.mkstemp(suffix=".bmp", prefix="rtad_cap_")
        with os.fdopen(fd, "wb") as f:
            file_size = 14 + 40 + buf_size
            f.write(b"BM")
            f.write(file_size.to_bytes(4, "little"))
            f.write((0).to_bytes(4, "little"))
            f.write((14 + 40).to_bytes(4, "little"))
            f.write(bytes(bmi.bmiHeader))
            f.write(bytes(buf))
        if os.path.getsize(path) < 32:
            out["error"] = "File di cattura non valido."
            cleanup_temp_image(path)
            return out
        out["ok"] = True
        out["path"] = path
        return out
    except Exception as e:
        if path:
            cleanup_temp_image(path)
        out["error"] = f"Cattura non riuscita: {e}"
        return out
    finally:
        try:
            if hbmp:
                gdi32.DeleteObject(hbmp)
        except Exception:
            pass
        try:
            if hdc_mem:
                gdi32.DeleteDC(hdc_mem)
        except Exception:
            pass
        try:
            if hdc_screen:
                user32.ReleaseDC(hwnd_desk, hdc_screen)
        except Exception:
            pass


def cleanup_temp_image(path: str) -> None:
    """Elimina un file temp RTAD se sembra nostro (best-effort)."""
    if not path or not isinstance(path, str):
        return
    base = os.path.basename(path)
    if not any(base.startswith(p) for p in _TEMP_IMAGE_PREFIXES):
        return
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass

