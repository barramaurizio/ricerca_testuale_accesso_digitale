# -*- coding: utf-8 -*-
"""RTAD — conversazione Gemini sul file già cercato o analizzato (1.8.0).

Gemello Standalone ↔ Add-on. La chiave resta quella personale di AI Studio.
Niente temperature. La cronologia è testo sul PC: non contiene la chiave
né i byte dell'immagine.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request

try:
    import rtad_ocr
except ImportError:
    rtad_ocr = None

try:
    import rtad_docstruct
except ImportError:
    rtad_docstruct = None

CONTEXT_CHAR_CAP = 80000
STORED_TEXT_CAP = 400000
PRIOR_REPORT_CAP = 24000
FOCUS_SLICE_CAP = 8000
MAX_TURNS_IN_REQUEST = 12
MAX_OUTPUT_TOKENS = 8192
REQUEST_TIMEOUT_SEC = 90
CHAT_VERSION = 1

_IMAGE_MIME = {
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
}

_GIORNI = (
    "lunedì",
    "martedì",
    "mercoledì",
    "giovedì",
    "venerdì",
    "sabato",
    "domenica",
)
_MESI = (
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
)

_PAGE_RE = re.compile(r"\bpag(?:ina|\.)?\s*(\d{1,5})\b", re.IGNORECASE)

_SUGGESTED = {
    "image": (
        "Riassumi che cosa si vede e che cosa c'è scritto.",
        "Quali date o nomi compaiono, e sono coerenti con oggi?",
        "Che cosa non è chiaro e andrebbe approfondito?",
    ),
    "document": (
        "Riassumi i punti principali.",
        "Elenca i titoli e di che cosa parla ciascuno.",
        "C'è una data nel documento? È coerente con oggi?",
    ),
}


def suggested_questions(kind: str) -> tuple:
    return _SUGGESTED.get(kind or "", _SUGGESTED["document"])


def format_now(when: datetime.datetime | None = None) -> str:
    when = when or datetime.datetime.now()
    giorno = _GIORNI[when.weekday()]
    mese = _MESI[when.month - 1]
    return f"{giorno} {when.day} {mese} {when.year}, ore {when:%H:%M}"


def _mtime_label(path: str) -> tuple:
    """(timestamp float, etichetta gg/mm/aaaa HH:MM) oppure (None, '')."""
    try:
        ts = os.path.getmtime(path)
    except Exception:
        return None, ""
    try:
        label = datetime.datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
    except Exception:
        label = ""
    return ts, label


def _file_key(path: str) -> str:
    norm = os.path.normcase(os.path.abspath(path or ""))
    return hashlib.sha256(norm.encode("utf-8", errors="replace")).hexdigest()[:20]


def _temp_media_name(name: str) -> bool:
    """Scarico da URL: il nome su disco è rtad_media_*, non il titolo del video."""
    stem = os.path.splitext(os.path.basename(name or ""))[0].lower()
    return stem.startswith("rtad_media_")


def media_source_identity(path: str) -> dict:
    """Chiave stabile per uno scarico da URL: titolo e indirizzo, non il file in Temp."""
    meta = {}
    try:
        import rtad_media as media

        if path:
            meta = media.read_media_source_meta(path) or {}
    except Exception:
        meta = {}
    if not isinstance(meta, dict):
        return {}
    url = str(meta.get("webpage_url") or meta.get("url") or "").strip()
    title = str(meta.get("title") or "").strip()
    src_id = str(meta.get("id") or "").strip()
    token = url or (f"media-id:{src_id}" if src_id else "")
    if not token:
        return {}
    key = hashlib.sha256(token.strip().lower().encode("utf-8", errors="replace")).hexdigest()[:20]
    return {"key": key, "title": title, "url": url, "id": src_id}


def _attach_source_identity(session: dict) -> None:
    ident = media_source_identity((session or {}).get("path") or "")
    if not ident:
        return
    session["stable_key"] = ident["key"]
    if ident.get("url"):
        session["source_url"] = ident["url"]
    if ident.get("title"):
        session["title"] = ident["title"]


def _storage_key(file_path: str, session: dict | None = None) -> str:
    if session and session.get("stable_key"):
        return session["stable_key"]
    ident = media_source_identity(file_path)
    if ident.get("key"):
        return ident["key"]
    return _file_key(file_path)


def _keys_for_path(file_path: str, session: dict | None = None) -> list:
    keys = []

    def add(key):
        if key and key not in keys:
            keys.append(key)

    if session and session.get("stable_key"):
        add(session["stable_key"])
    ident = media_source_identity(file_path)
    add(ident.get("key"))
    add(_file_key(file_path))
    return keys


def chat_dir(base_dir: str) -> str:
    folder = os.path.join(base_dir or "", "chat")
    os.makedirs(folder, exist_ok=True)
    return folder


def system_instruction(session: dict, when: datetime.datetime | None = None) -> str:
    """Regole, data di oggi e materiale del file. Non va nella cronologia visibile."""
    when = when or datetime.datetime.now()
    kind = (session or {}).get("kind") or "document"
    kind_label = "immagine" if kind == "image" else "documento"
    lines = [
        "Sei l'assistente di Ricerca Testuale Accesso Digitale.",
        f"Oggi è {format_now(when)} (ora locale del computer).",
        "Rispondi nella lingua della domanda. Se la domanda è in italiano, rispondi in italiano.",
        f"Stai parlando di un file ({kind_label}) già aperto in RTAD. "
        "Il materiale qui sotto è la fonte principale.",
        "Quando servi entrambi i piani, separali con questi titoli esatti:",
        "Nel file:",
        "Approfondimento:",
        "«Nel file» contiene solo ciò che è nel materiale RTAD.",
        "«Approfondimento» solo se in questa richiesta è attiva la consultazione web, "
        "e solo per ciò che non è già nel file. Includi i link delle fonti.",
        "Se un dato non c'è nel file e il web non è attivo, dillo. Non inventare citazioni, nomi o date.",
        "Quando citi una pagina, usa solo un indirizzo che risulta dalle fonti consultate. "
        "Non inventare né abbreviare un dominio. Se non hai l'indirizzo esatto, "
        "dì il nome del sito senza link.",
        "Non presentare come recensione o articolo su questo file una pagina che parla d'altro.",
        "Se nel file c'è una data, preferiscila a una data trovata sul web e segnala il contrasto.",
        "Usa il web per persone, aggiornamenti, «è ancora così» e notizie. "
        "Non usarlo per riscrivere ciò che il file già dice.",
        "",
        "=== Materiale del file ===",
        (session or {}).get("context_text") or "(Nessun testo del file disponibile.)",
    ]
    note = (session or {}).get("context_note") or ""
    if note:
        lines.append("")
        lines.append(note)
    return "\n".join(lines)


def _outline_block(outline: list) -> str:
    rows = []
    for i, item in enumerate(outline or [], 1):
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        if not title:
            continue
        level = int(item.get("level") or 1)
        page = item.get("page")
        bit = f" (pagina {int(page)})" if page else ""
        rows.append(f"{i}. [H{level}] {title}{bit}")
    if not rows:
        return ""
    return "Sommario:\n" + "\n".join(rows)


def compose_document_text(path: str, struct: dict | None, displayed: str = "") -> str:
    struct = struct or {}
    parts = []
    name = os.path.basename(path or "") or "documento"
    parts.append(f"File: {name}")
    _ts, label = _mtime_label(path) if path else (None, "")
    if label:
        parts.append(f"Data di modifica del file: {label}")
    msg = (struct.get("message") or "").strip()
    if msg:
        parts.append(msg)
    outline = _outline_block(struct.get("outline") or [])
    if outline:
        parts.append(outline)
    body = (struct.get("body") or struct.get("plain") or "").strip()
    if not body:
        body = (displayed or "").strip()
    if body:
        parts.append("Testo:")
        parts.append(body)
    text = "\n\n".join(p for p in parts if p).strip()
    if len(text) > STORED_TEXT_CAP:
        text = text[:STORED_TEXT_CAP] + "\n\n(Il resto del documento non è stato caricato in memoria.)"
    return text


def compose_image_text(path: str, prior_report: str = "", source_path: str = "") -> str:
    parts = ["Tipo: immagine"]
    name = os.path.basename(path or "") or "immagine"
    parts.append(f"File: {name}")
    _ts, label = _mtime_label(path)
    if label:
        parts.append(f"Data di modifica del file: {label}")
    src = (source_path or "").strip()
    if src and os.path.basename(src) and os.path.basename(src) != name:
        parts.append(f"File di origine: {os.path.basename(src)}")
        _s, slabel = _mtime_label(src)
        if slabel:
            parts.append(f"Data di modifica dell'origine: {slabel}")
    if rtad_ocr is not None and hasattr(rtad_ocr, "_parse_date_hint_from_name"):
        try:
            hint = rtad_ocr._parse_date_hint_from_name(name) or ""
        except Exception:
            hint = ""
        if hint:
            parts.append(
                f"Data suggerita dal nome file: {hint}. "
                "Se nell'immagine leggi una data diversa, preferisci quella dell'immagine."
            )
    prior = (prior_report or "").strip()
    if prior:
        if len(prior) > PRIOR_REPORT_CAP:
            prior = prior[:PRIOR_REPORT_CAP] + "\n…"
        parts.append(
            "Analisi già svolta in RTAD. Rispettala: se la contraddici, dillo."
        )
        parts.append(prior)
    else:
        parts.append(
            "Non c'è un testo di analisi precedente. Leggi l'immagine allegata a questa richiesta."
        )
    parts.append("L'immagine è allegata all'ultima domanda, a ogni scambio.")
    return "\n\n".join(parts)


def _image_bytes(path: str) -> tuple:
    """(b64, mime) oppure ('', '')."""
    if not path or not os.path.isfile(path):
        return "", ""
    try:
        size = os.path.getsize(path)
    except Exception:
        size = 0
    limit = 25 * 1024 * 1024
    if rtad_ocr is not None:
        limit = int(getattr(rtad_ocr, "MAX_OCR_IMAGE_BYTES", limit) or limit)
    if size <= 0 or size > limit:
        return "", ""
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except Exception:
        return "", ""
    if not raw or len(raw) > limit:
        return "", ""
    ext = os.path.splitext(path)[1].lower()
    mime = _IMAGE_MIME.get(ext, "image/jpeg")
    return base64.b64encode(raw).decode("ascii"), mime


def new_session(
    kind: str,
    path: str,
    *,
    struct: dict | None = None,
    displayed: str = "",
    prior_report: str = "",
    source_path: str = "",
    do_refresh: bool = True,
) -> dict:
    now = datetime.datetime.now().replace(microsecond=0).isoformat(timespec="seconds")
    session = {
        "v": CHAT_VERSION,
        "kind": kind if kind in ("image", "document") else "document",
        "path": path or "",
        "source_path": source_path or "",
        "title": os.path.basename(path or "") or "File",
        "mtime": None,
        "created": now,
        "updated": now,
        "turns": [],
        "context_text": "",
        "context_note": "",
        "full_text": "",
        "outline": [],
        "image_b64": "",
        "image_mime": "",
        "image_missing": False,
        "stable_key": "",
        "source_url": "",
    }
    _attach_source_identity(session)
    if session["kind"] == "document" and struct:
        session["outline"] = list(struct.get("outline") or [])
        session["_struct"] = struct
        session["_displayed"] = displayed or ""
    if session["kind"] == "image":
        session["_prior"] = prior_report or ""
    if do_refresh:
        refresh_context(session)
    return session


def refresh_context(session: dict) -> None:
    """Rilegge il file. Non tocca i turni."""
    if not session:
        return
    path = session.get("path") or ""
    ts, _label = _mtime_label(path) if path else (None, "")
    old = session.get("mtime")
    if old and ts and abs(float(ts) - float(old)) > 1:
        session["context_note"] = (
            "Il file sul disco è stato modificato dopo l'ultimo scambio di questa conversazione."
        )
    session["mtime"] = ts
    kind = session.get("kind")
    if kind == "image":
        b64, mime = _image_bytes(path)
        if b64:
            session["image_b64"] = b64
            session["image_mime"] = mime
            session["image_missing"] = False
        elif not session.get("image_b64"):
            session["image_missing"] = True
        session["context_text"] = compose_image_text(
            path,
            session.get("_prior") or "",
            session.get("source_path") or "",
        )
        session["full_text"] = session["context_text"]
        return

    struct = session.get("_struct")
    if struct is None and path and rtad_docstruct is not None and os.path.isfile(path):
        try:
            struct = rtad_docstruct.extract_document_structure(path)
            session["_struct"] = struct
        except Exception as exc:
            logging.debug(f"Chat: struttura documento non riletta: {exc}")
            struct = None
    if struct:
        session["outline"] = list(struct.get("outline") or [])
    full = compose_document_text(path, struct, session.get("_displayed") or "")
    session["full_text"] = full
    if len(full) > CONTEXT_CHAR_CAP:
        session["context_text"] = (
            full[:CONTEXT_CHAR_CAP]
            + "\n\n(Questo è l'inizio del documento. "
            "Se la domanda indica una pagina o un titolo più avanti, "
            "un estratto aggiuntivo arriva insieme alla domanda.)"
        )
    else:
        session["context_text"] = full


def _window_from(full_text: str, needle: str, start_at: int) -> tuple:
    """(posizione, estratto) a partire da start_at, oppure (-1, '')."""
    needle = (needle or "").strip()
    if not needle or not full_text:
        return -1, ""
    pos = full_text.find(needle, max(0, start_at))
    if pos < 0:
        compact = re.sub(r"\s+", "", needle)
        if compact and compact != needle:
            pos = full_text.find(compact, max(0, start_at))
            if pos >= 0:
                needle = compact
    if pos < 0:
        return -1, ""
    end = min(len(full_text), pos + FOCUS_SLICE_CAP)
    return pos, full_text[pos:end]


def focus_slice(session: dict, question: str) -> str:
    """Estratto oltre il pacchetto iniziale, se la domanda indica pagina o titolo."""
    full = (session or {}).get("full_text") or ""
    if len(full) <= CONTEXT_CHAR_CAP:
        return ""
    question = question or ""
    outline = (session or {}).get("outline") or []
    wanted = []
    match = _PAGE_RE.search(question)
    if match:
        number = int(match.group(1))
        for item in outline:
            if not isinstance(item, dict):
                continue
            try:
                page = int(item.get("page") or 0)
            except Exception:
                page = 0
            title = (item.get("title") or "").strip()
            if page == number or title.lower() == f"pagina {number}":
                if title:
                    wanted.append(title)
                break
        if not wanted:
            wanted.append(f"Pagina {number}")
    q_low = question.lower()
    for item in outline:
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        if len(title) >= 8 and title.lower() in q_low and title not in wanted:
            wanted.append(title)
    chunks = []
    for needle in wanted:
        pos, snip = _window_from(full, needle, CONTEXT_CHAR_CAP)
        if pos >= CONTEXT_CHAR_CAP and snip:
            chunks.append(snip.strip())
        if sum(len(c) for c in chunks) >= FOCUS_SLICE_CAP:
            break
    if not chunks:
        return ""
    text = "\n\n".join(chunks)
    if len(text) > FOCUS_SLICE_CAP:
        text = text[:FOCUS_SLICE_CAP]
    return text


def build_payload(
    session: dict,
    question: str,
    use_web: bool,
    when: datetime.datetime | None = None,
) -> dict:
    """Corpo generateContent. Senza chiave e senza temperature."""
    question = (question or "").strip()
    extra = focus_slice(session, question)
    user_text = question
    if extra:
        user_text += (
            "\n\nEstratto aggiuntivo del file, fuori dall'inizio già fornito:\n"
            + extra
        )
    if session.get("kind") == "image" and session.get("image_missing") and not session.get("image_b64"):
        user_text += "\n\n(L'immagine non è più leggibile dal disco: rispondi sul testo di analisi, e dillo.)"
    contents = []
    turns = list(session.get("turns") or [])
    if len(turns) > MAX_TURNS_IN_REQUEST:
        turns = turns[-MAX_TURNS_IN_REQUEST:]
    for turn in turns:
        role = turn.get("role")
        if role not in ("user", "model"):
            continue
        text = (turn.get("text") or "").strip()
        if not text:
            continue
        contents.append({"role": role, "parts": [{"text": text}]})
    parts = [{"text": user_text}]
    if session.get("kind") == "image" and session.get("image_b64"):
        parts.append(
            {
                "inline_data": {
                    "mime_type": session.get("image_mime") or "image/jpeg",
                    "data": session.get("image_b64"),
                }
            }
        )
    contents.append({"role": "user", "parts": parts})
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction(session, when)}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": MAX_OUTPUT_TOKENS},
    }
    if use_web:
        payload["tools"] = [{"google_search": {}}]
    return payload


def _safe_err(model: str, exc: Exception) -> str:
    text = str(exc or "")
    text = re.sub(r"key=[^&\s\"']+", "key=…", text)
    if len(text) > 300:
        text = text[:300] + "…"
    return f"{model}: {text}" if model else text


def _readable_error(err: str) -> str:
    """Frase da mostrare. Il dettaglio tecnico resta nel log."""
    raw = (err or "").strip()
    low = raw.lower()
    if "429" in raw or "resource_exhausted" in low or "quota" in low:
        return (
            "Gemini non ha risposto: per questa chiave le richieste disponibili sono esaurite. "
            "Si riprova più tardi."
        )
    if any(code in raw for code in ("401", "403")) or "api key" in low or "api_key" in low:
        return "Gemini non ha risposto: la chiave API non è accettata. Controlla in Strumenti."
    if "timed out" in low or "timeout" in low:
        return "Gemini non ha risposto: tempo scaduto. Riprova."
    if "testo vuoto" in low or "nessuna risposta" in low:
        return "Gemini non ha risposto: è arrivata una risposta vuota."
    if not raw:
        return "Gemini non ha risposto."
    if len(raw) > 400:
        return raw[:400] + "…"
    return raw


def _fail(error: str, model: str = "", aborted: bool = False) -> dict:
    raw = (error or "").strip()
    if raw and not aborted:
        logging.warning(f"Chat Gemini fallita: {raw}")
    return {
        "ok": False,
        "text": "",
        "model": model or "",
        "error": "" if aborted else _readable_error(raw),
        "aborted": aborted,
    }


def _model_candidates(key: str) -> list:
    if rtad_ocr is not None and hasattr(rtad_ocr, "_gemini_model_candidates"):
        try:
            found = list(rtad_ocr._gemini_model_candidates(key) or [])
        except Exception:
            found = []
        if found:
            return found
    if rtad_ocr is not None:
        return list(getattr(rtad_ocr, "_GEMINI_MODELS_PREFERRED", ()) or ())
    return []


_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_BARE_URL_RE = re.compile(r"https?://[^\s<>\]\)\"']+")


def extract_links(text: str) -> list:
    """Link nel testo della chat, senza doppioni. Il .txt resta piano."""
    found = []
    seen = set()

    def add(label: str, url: str) -> None:
        url = (url or "").strip().rstrip(".,;:)")
        if not url.startswith("http") or url in seen:
            return
        seen.add(url)
        found.append({"label": (label or "").strip(), "url": url})

    raw = text or ""
    for match in _MD_LINK_RE.finditer(raw):
        add(match.group(1), match.group(2))
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("- ") or "http" not in line:
            continue
        body = line[2:]
        sep = body.find(": http")
        if sep < 0:
            continue
        add(body[:sep], body[sep + 2 :])
    for match in _BARE_URL_RE.finditer(raw):
        add("", match.group(0))
    return found


def link_label(item: dict) -> str:
    """Nome leggibile. L'indirizzo intero resta nel testo e si usa per aprire."""
    label = (item.get("label") or "").strip()
    url = (item.get("url") or "").strip()
    if "grounding-api-redirect" in url:
        return label or "Fonte web"
    if label and label not in url:
        if len(url) > 80:
            return label
        return f"{label}: {url}"
    if len(url) > 90:
        return url[:70] + "…"
    return url or label or "Link"


def _sources_block(candidate: dict) -> str:
    meta = (candidate or {}).get("groundingMetadata") or {}
    chunks = meta.get("groundingChunks") or []
    lines = []
    seen = set()
    for chunk in chunks:
        web = (chunk or {}).get("web") or {}
        uri = (web.get("uri") or "").strip()
        title = (web.get("title") or "").strip() or uri
        if not uri or uri in seen:
            continue
        seen.add(uri)
        lines.append(f"- {title}: {uri}")
    if not lines:
        return ""
    return "\n\nFonti web:\n" + "\n".join(lines)


def _text_from_response(data: dict) -> tuple:
    """(testo, finish_reason, errore breve)."""
    cands = (data or {}).get("candidates") or []
    if not cands:
        feedback = (data or {}).get("promptFeedback") or {}
        return "", "", f"nessuna risposta ({feedback or 'vuoto'})"
    parts = (((cands[0] or {}).get("content") or {}).get("parts")) or []
    texts = []
    for part in parts:
        if part.get("thought"):
            continue
        bit = (part.get("text") or "").strip()
        if bit:
            texts.append(bit)
    text = "\n".join(texts).strip()
    finish = str((cands[0] or {}).get("finishReason") or "")
    if text and finish.upper() in ("MAX_TOKENS", "LENGTH"):
        if not text.endswith((".", "!", "?", "»", '"', "…")):
            text = text.rstrip(",;:") + "…"
        text += "\n\n(Nota: la risposta è stata accorciata dal limite tecnico.)"
    sources = _sources_block(cands[0] or {})
    if sources and "Fonti web:" not in text:
        text = (text + sources).strip()
    if not text:
        return "", finish, "testo vuoto"
    return text, finish, ""


def _post_generate(model: str, key: str, payload: dict) -> tuple:
    """(ok, data, errore)."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={urllib.parse.quote(key, safe='')}"
    )
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return True, json.loads(raw) if raw else {}, ""
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            pass
        err = f"HTTP {exc.code} ({model})"
        if err_body:
            err += f": {err_body}"
        err = re.sub(r"key=[^&\s\"']+", "key=…", err)
        return False, {"_http": exc.code}, err
    except Exception as exc:
        return False, {}, _safe_err(model, exc)


def ask(
    session: dict,
    question: str,
    *,
    use_web: bool = False,
    should_abort=None,
    when: datetime.datetime | None = None,
) -> dict:
    """Un turno. Non modifica session: lo fa chi chiama, se ok."""
    question = (question or "").strip()
    if not question:
        return _fail("Domanda vuota.")
    if should_abort and should_abort():
        return _fail("", aborted=True)
    key = ""
    if rtad_ocr is not None and hasattr(rtad_ocr, "get_gemini_api_key"):
        key = (rtad_ocr.get_gemini_api_key() or "").strip()
    if not key:
        return _fail("Chiave API Gemini assente. Aggiungila da Strumenti.")
    models = _model_candidates(key)
    if not models:
        return _fail("Nessun modello Gemini disponibile per questa chiave.")
    payload = build_payload(session, question, use_web, when)
    web_note = ""
    last_err = ""
    for model in models:
        if should_abort and should_abort():
            return _fail("", aborted=True)
        ok, data, err = _post_generate(model, key, payload)
        if not ok and use_web and int((data or {}).get("_http") or 0) == 400:
            fallback = dict(payload)
            fallback.pop("tools", None)
            ok, data, err = _post_generate(model, key, fallback)
            if ok:
                web_note = (
                    "\n\n(La consultazione web non è riuscita in questo scambio. "
                    "La risposta usa il file.)"
                )
        if not ok:
            last_err = err or "errore Gemini"
            code = int((data or {}).get("_http") or 0)
            if code in (404, 429):
                continue
            if code == 400 and "not found" in (err or "").lower():
                continue
            return _fail(last_err, model)
        text, _finish, parse_err = _text_from_response(data)
        if text:
            if web_note and web_note.strip() not in text:
                text += web_note
            return {"ok": True, "text": text, "model": model, "error": "", "aborted": False}
        last_err = f"{model}: {parse_err or 'testo vuoto'}"
        continue
    return _fail(last_err or "Nessun modello ha risposto.")


def append_exchange(session: dict, question: str, answer: str, model: str = "") -> None:
    now = datetime.datetime.now().replace(microsecond=0).isoformat(timespec="seconds")
    session.setdefault("turns", [])
    session["turns"].append({"role": "user", "text": (question or "").strip()})
    session["turns"].append(
        {"role": "model", "text": (answer or "").strip(), "model": model or ""}
    )
    session["updated"] = now
    if session.get("mtime") is None:
        ts, _label = _mtime_label(session.get("path") or "")
        session["mtime"] = ts


def transcript(session: dict) -> str:
    """Testo piano per leggere, copiare, salvare, stampare. Senza chiave."""
    lines = [
        "Ricerca Testuale Accesso Digitale — Conversazione con Gemini",
        f"File: {session.get('title') or ''}",
    ]
    if session.get("source_url"):
        lines.append(f"URL: {session.get('source_url')}")
    path = session.get("path") or ""
    if path and not _temp_media_name(path):
        lines.append(f"Percorso: {path}")
    created = session.get("created") or ""
    updated = session.get("updated") or ""
    if created:
        lines.append(f"Iniziata: {created}")
    if updated:
        lines.append(f"Aggiornata: {updated}")
    model = ""
    for turn in session.get("turns") or []:
        if turn.get("role") == "model" and turn.get("model"):
            model = turn.get("model")
    if model:
        lines.append(f"Modello: {model}")
    lines.append("")
    if not session.get("turns"):
        lines.append("(Nessuno scambio ancora.)")
    for turn in session.get("turns") or []:
        who = "Tu" if turn.get("role") == "user" else "Gemini"
        lines.append(f"{who}:")
        lines.append((turn.get("text") or "").strip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _public_dict(session: dict) -> dict:
    """Ciò che si scrive su disco. Niente immagine, niente chiave, niente testo integrale duplicato."""
    return {
        "v": CHAT_VERSION,
        "kind": session.get("kind") or "document",
        "path": session.get("path") or "",
        "source_path": session.get("source_path") or "",
        "title": session.get("title") or "",
        "mtime": session.get("mtime"),
        "created": session.get("created") or "",
        "updated": session.get("updated") or "",
        **({"stable_key": session.get("stable_key")} if session.get("stable_key") else {}),
        **({"source_url": session.get("source_url")} if session.get("source_url") else {}),
        "turns": [
            {
                "role": t.get("role"),
                "text": t.get("text") or "",
                **({"model": t.get("model")} if t.get("model") else {}),
            }
            for t in (session.get("turns") or [])
            if t.get("role") in ("user", "model")
        ],
    }


def _current_path(base_dir: str, file_path: str, session: dict | None = None) -> str:
    return os.path.join(chat_dir(base_dir), _storage_key(file_path, session) + ".json")


def _candidate_current_paths(base_dir: str, file_path: str) -> list:
    folder = chat_dir(base_dir)
    return [os.path.join(folder, key + ".json") for key in _keys_for_path(file_path)]


def promote_url_identity(base_dir: str, json_path: str, data: dict) -> tuple:
    """Sposta una chat da URL sulla chiave dell'indirizzo, col titolo vero."""
    if not isinstance(data, dict) or not json_path:
        return json_path, data or {}
    path = data.get("path") or ""
    ident = media_source_identity(path)
    if not ident.get("key"):
        return json_path, data
    changed = False
    if data.get("stable_key") != ident["key"]:
        data["stable_key"] = ident["key"]
        changed = True
    if ident.get("url") and data.get("source_url") != ident["url"]:
        data["source_url"] = ident["url"]
        changed = True
    if ident.get("title") and _temp_media_name(data.get("title") or ""):
        data["title"] = ident["title"]
        changed = True
    folder = chat_dir(base_dir)
    new_path = os.path.join(folder, ident["key"] + ".json")
    same = os.path.normcase(os.path.abspath(new_path)) == os.path.normcase(os.path.abspath(json_path))
    if not changed and same:
        return json_path, data
    if not same and os.path.isfile(new_path):
        return json_path, data
    try:
        with open(new_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1)
    except Exception as exc:
        logging.warning(f"Chat: non posso ancorare la conversazione all'URL: {exc}")
        return json_path, data
    if not same:
        try:
            os.remove(json_path)
        except Exception:
            pass
        old_key = _file_key(path)
        if old_key != ident["key"]:
            try:
                names = os.listdir(folder)
            except Exception:
                names = []
            prefix = old_key + "__"
            for name in names:
                if name.startswith(prefix) and name.endswith(".json"):
                    dest = os.path.join(folder, ident["key"] + name[len(old_key):])
                    try:
                        os.replace(os.path.join(folder, name), dest)
                    except Exception:
                        pass
    return new_path, data


def save_current(base_dir: str, session: dict) -> str:
    path = session.get("path") or ""
    dest = _current_path(base_dir, path, session)
    with open(dest, "w", encoding="utf-8") as handle:
        json.dump(_public_dict(session), handle, ensure_ascii=False, indent=1)
    return dest


def _session_from_public(
    data: dict,
    *,
    struct=None,
    displayed="",
    prior_report="",
    do_refresh: bool = True,
) -> dict:
    session = new_session(
        data.get("kind") or "document",
        data.get("path") or "",
        struct=struct,
        displayed=displayed,
        prior_report=prior_report,
        source_path=data.get("source_path") or "",
        do_refresh=False,
    )
    session["created"] = data.get("created") or session["created"]
    session["updated"] = data.get("updated") or session["updated"]
    session["mtime"] = data.get("mtime")
    session["turns"] = []
    for turn in data.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        if role not in ("user", "model"):
            continue
        item = {"role": role, "text": turn.get("text") or ""}
        if turn.get("model"):
            item["model"] = turn.get("model")
        session["turns"].append(item)
    if data.get("stable_key"):
        session["stable_key"] = data.get("stable_key")
    if data.get("source_url"):
        session["source_url"] = data.get("source_url")
    saved_title = str(data.get("title") or "").strip()
    if saved_title and not _temp_media_name(saved_title):
        session["title"] = saved_title
    elif _temp_media_name(session.get("title") or "") and saved_title:
        session["title"] = saved_title
    if do_refresh:
        refresh_context(session)
    else:
        session["context_text"] = (
            f"File: {session.get('title') or ''}\n"
            "Il file viene riletto quando invii una nuova domanda."
        )
        session["full_text"] = session["context_text"]
    return session


def load_current(
    base_dir: str,
    file_path: str,
    *,
    struct=None,
    displayed="",
    prior_report="",
) -> dict | None:
    for dest in _candidate_current_paths(base_dir, file_path):
        if not os.path.isfile(dest):
            continue
        try:
            with open(dest, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:
            logging.warning(f"Chat: lettura cronologia non riuscita: {exc}")
            continue
        if not isinstance(data, dict):
            continue
        dest, data = promote_url_identity(base_dir, dest, data)
        return _session_from_public(
            data,
            struct=struct,
            displayed=displayed,
            prior_report=prior_report,
        )
    return None


def archive_current(base_dir: str, session: dict) -> str:
    """Copia la conversazione corrente in archivio e svuota i turni."""
    path = session.get("path") or ""
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(chat_dir(base_dir), f"{_storage_key(path, session)}__{stamp}.json")
    if session.get("turns"):
        with open(dest, "w", encoding="utf-8") as handle:
            json.dump(_public_dict(session), handle, ensure_ascii=False, indent=1)
    session["turns"] = []
    now = datetime.datetime.now().replace(microsecond=0).isoformat(timespec="seconds")
    session["created"] = now
    session["updated"] = now
    save_current(base_dir, session)
    return dest


def list_saved(base_dir: str, file_path: str) -> list:
    """Elenco per questo file: corrente per prima, poi archivio dal più recente."""
    keys = _keys_for_path(file_path)
    folder = chat_dir(base_dir)
    rows = []
    current = ""
    for key in keys:
        cand = os.path.join(folder, key + ".json")
        if os.path.isfile(cand):
            current = cand
            break
    if current:
        rows.append(_saved_row(current, current=True))
    archives = []
    try:
        names = os.listdir(folder)
    except Exception:
        names = []
    for key in keys:
        prefix = key + "__"
        for name in names:
            if name.startswith(prefix) and name.endswith(".json"):
                archives.append(os.path.join(folder, name))
    archives.sort(reverse=True)
    for item in archives:
        rows.append(_saved_row(item, current=False))
    return rows


def _saved_row(json_path: str, current: bool) -> dict:
    label = "Conversazione attuale"
    title = ""
    updated = ""
    count = 0
    try:
        with open(json_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            updated = str(data.get("updated") or data.get("created") or "")
            title = str(data.get("title") or os.path.basename(data.get("path") or ""))
            count = len(data.get("turns") or []) // 2
    except Exception:
        data = {}
    if not current:
        label = "Archivio"
    if updated:
        label = f"{label} — {updated}"
    if count:
        scambi = "scambio" if count == 1 else "scambi"
        label = f"{label} ({count} {scambi})"
    return {
        "path": json_path,
        "label": label,
        "current": current,
        "updated": updated,
        "title": title,
        "count": count,
    }


def load_saved(
    json_path: str,
    *,
    struct=None,
    displayed="",
    prior_report="",
    do_refresh: bool = True,
) -> dict | None:
    try:
        with open(json_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return _session_from_public(
        data,
        struct=struct,
        displayed=displayed,
        prior_report=prior_report,
        do_refresh=do_refresh,
    )


def has_saved(base_dir: str, file_path: str) -> bool:
    for dest in _candidate_current_paths(base_dir, file_path):
        if not os.path.isfile(dest):
            continue
        try:
            with open(dest, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            continue
        if isinstance(data, dict) and data.get("turns"):
            return True
    return False


def saved_json_path(base_dir: str, file_path: str) -> str:
    paths = _candidate_current_paths(base_dir, file_path)
    for dest in paths:
        if os.path.isfile(dest):
            return dest
    return paths[0] if paths else ""


def list_all_saved(base_dir: str) -> list:
    """Tutte le conversazioni con almeno uno scambio, dalla più recente."""
    folder = chat_dir(base_dir)
    rows = []
    try:
        names = os.listdir(folder)
    except Exception:
        return []
    for name in names:
        if not name.endswith(".json"):
            continue
        full = os.path.join(folder, name)
        if "__" not in name:
            try:
                with open(full, "r", encoding="utf-8") as handle:
                    raw = json.load(handle)
            except Exception:
                raw = None
            if isinstance(raw, dict):
                full, _raw = promote_url_identity(base_dir, full, raw)
        row = _saved_row(full, current="__" not in os.path.basename(full))
        if not row.get("count"):
            continue
        title = row.get("title") or "Conversazione"
        if not row.get("current"):
            title = f"{title} — archivio"
        label = title
        if row.get("updated"):
            label += f" — {row['updated']}"
        n = int(row.get("count") or 0)
        scambi = "scambio" if n == 1 else "scambi"
        label += f" ({n} {scambi})"
        row["label"] = label
        rows.append(row)
    rows.sort(key=lambda item: item.get("updated") or "", reverse=True)
    return rows


def find_export(base_dir: str, chat_txt_path: str) -> str:
    """Collega un .chat.txt salvato alla conversazione sullo stesso titolo."""
    name = os.path.basename(chat_txt_path or "")
    stem = name
    if stem.lower().endswith(".txt"):
        stem = stem[:-4]
    if stem.lower().endswith(".chat"):
        stem = stem[:-5]
    stem = stem.strip()
    if not stem:
        return ""
    best = ""
    best_updated = ""
    for row in list_all_saved(base_dir):
        title = row.get("title") or ""
        title_stem = os.path.splitext(title)[0]
        if title_stem != stem and title != stem:
            continue
        if row.get("current"):
            return row.get("path") or ""
        updated = row.get("updated") or ""
        if updated >= best_updated:
            best = row.get("path") or ""
            best_updated = updated
    return best


def delete_saved(json_path: str) -> bool:
    try:
        if json_path and os.path.isfile(json_path):
            os.remove(json_path)
            return True
    except Exception as exc:
        logging.warning(f"Chat: eliminazione non riuscita: {exc}")
    return False
