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
import uuid
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
FILE_API_TIMEOUT_SEC = 900
CHAT_VERSION = 1

# Dal .rtad.txt già salvato (1.8.4). Stessa frase a schermo e in voce.
NOTICE_REPORT_ORPHAN = (
    "Il file originale non è più accanto a questo resoconto. "
    "La conversazione resta sul testo salvato."
)
NOTICE_HIT_ONLY = (
    "Da questo risultato non esce un testo intero. "
    "La conversazione parte dal punto della ricerca."
)
NOTICE_NO_TEXT = "In questo file non c'è testo da leggere."
_MESSAGE_PREFIXES = ("[MBOX]", "[FEED]", "[RSS]", "[FEED-RIGA]")
_REPORT_MATERIAL_MESSAGE = (
    "Resoconto già salvato in RTAD. Non è stata rifatta l'analisi del file."
)
_EMPTY_REPORT = "(Il resoconto salvato è vuoto.)"
MAX_ATTACHMENTS = 12


def free_save_name(folder: str, filename: str) -> str:
    """Nome libero nella cartella: se c'è già, aggiunge (1), (2), …"""
    filename = (filename or "file.txt").strip() or "file.txt"
    folder = folder or ""
    if not folder or not os.path.isdir(folder):
        return filename
    if filename.lower().endswith(".chat.txt"):
        base = filename[: -len(".chat.txt")]
        ext = ".chat.txt"
    else:
        base, ext = os.path.splitext(filename)
    candidate = filename
    n = 1
    while os.path.exists(os.path.join(folder, candidate)):
        candidate = f"{base} ({n}){ext}"
        n += 1
        if n > 999:
            break
    return candidate


ATTACH_TEXT_CAP = 60000
MAX_ATTACH_DOC_BYTES = 80 * 1024 * 1024

_DOC_EXTS = {
    ".txt", ".log", ".csv", ".md", ".rtf",
    ".html", ".htm",
    ".docx", ".doc", ".odt",
    ".xlsx",
    ".pdf",
    ".epub",
}
_PLAIN_EXTS = {".txt", ".log", ".csv", ".md", ".rtf", ".html", ".htm"}
_text_extractor = None

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
    "free": (
        "Spiega questo argomento in modo chiaro.",
        "Che cosa conviene verificare, e che cosa non si può sapere da qui?",
        "Riassumi in pochi punti.",
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
    if (file_path or "").strip():
        ident = media_source_identity(file_path)
        add(ident.get("key"))
        add(_file_key(file_path))
    return keys


def chat_dir(base_dir: str) -> str:
    folder = os.path.join(base_dir or "", "chat")
    os.makedirs(folder, exist_ok=True)
    return folder


def set_text_extractor(fn) -> None:
    """Lettura documenti già usata dal programma (PDF, Word, Excel, testo)."""
    global _text_extractor
    _text_extractor = fn


def attachment_kind(path: str) -> str:
    """image | document | audio | video | '' se non allegabile."""
    ext = os.path.splitext(path or "")[1].lower()
    if ext in _IMAGE_MIME:
        return "image"
    try:
        import rtad_media as media

        if media.is_media_path(path):
            return media.media_kind(path)
    except Exception:
        pass
    if ext in _DOC_EXTS:
        return "document"
    return ""


def attachment_wildcard() -> str:
    """Filtro del dialogo di scelta, con gli stessi tipi che la chat sa leggere."""
    exts = set(_IMAGE_MIME) | set(_DOC_EXTS)
    try:
        import rtad_media as media

        exts.update(media.MEDIA_EXTS)
    except Exception:
        pass
    pat = ";".join("*" + ext for ext in sorted(exts))
    return f"File allegabili|{pat}|Tutti i file (*.*)|*.*"


def _size_it(n: int) -> str:
    n = int(n or 0)
    if n < 0:
        n = 0
    if n < 1024:
        return f"{n} byte"
    if n < 1024 * 1024:
        value = f"{n / 1024:.1f}"
        unit = "KB"
    elif n < 1024 * 1024 * 1024:
        value = f"{n / (1024 * 1024):.2f}"
        unit = "MB"
    else:
        value = f"{n / (1024 * 1024 * 1024):.2f}"
        unit = "GB"
    return value.replace(".", ",") + " " + unit


def _mtime_it(mtime: float) -> str:
    try:
        return datetime.datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M")
    except (OSError, OverflowError, ValueError):
        return ""


def attach_type_label(name: str) -> str:
    """Tipo in italiano, dal nome: Video MP4, Immagine JPEG, Documento PDF."""
    ext = os.path.splitext(name or "")[1].lower()
    kind = attachment_kind("file" + ext) if ext else ""
    word = {
        "image": "Immagine",
        "document": "Documento",
        "audio": "Audio",
        "video": "Video",
    }.get(kind, "File")
    if ext:
        return f"{word} {ext[1:].upper()}"
    return word


def attach_row_label(name: str, mtime: float, size: int) -> str:
    """Una riga sola: nome, data, tipo, dimensione. La legge anche la sintesi."""
    when = _mtime_it(mtime)
    parts = [name or "", when, attach_type_label(name), _size_it(size)]
    return ". ".join(part for part in parts if part) + "."


def list_folder_files(folder: str) -> list:
    """File della cartella, i più recenti in cima. Non entra nelle sottocartelle."""
    rows = []
    with os.scandir(folder) as entries:
        for entry in entries:
            try:
                if not entry.is_file(follow_symlinks=False):
                    continue
                st = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            rows.append(
                {
                    "path": entry.path,
                    "name": entry.name,
                    "mtime": float(st.st_mtime or 0),
                    "size": int(st.st_size or 0),
                }
            )
    rows.sort(key=lambda row: (-row["mtime"], (row["name"] or "").lower()))
    return rows


def _kind_it(kind: str) -> str:
    return {
        "image": "immagine",
        "document": "documento",
        "audio": "audio",
        "video": "video",
        "free": "senza file",
    }.get(kind or "", "file")


def _same_path(left: str, right: str) -> bool:
    if not left or not right:
        return False
    try:
        return os.path.normcase(os.path.abspath(left)) == os.path.normcase(
            os.path.abspath(right)
        )
    except Exception:
        return False


def _read_plain(path: str) -> str:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_ATTACH_DOC_BYTES + 1)
    except Exception:
        return ""
    if not raw:
        return ""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16", errors="ignore")
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin1", errors="ignore")
    return text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _attachment_document_text(path: str) -> str:
    text = ""
    if _text_extractor is not None:
        try:
            text = (_text_extractor(path) or "").strip()
        except Exception as exc:
            logging.debug(f"Chat: lettura allegato non riuscita: {exc}")
            text = ""
    if not text:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".pdf", ".docx", ".epub") and rtad_docstruct is not None:
            try:
                struct = rtad_docstruct.extract_document_structure(path)
                text = compose_document_text(path, struct)
            except Exception as exc:
                logging.debug(f"Chat: struttura allegato non letta: {exc}")
                text = ""
        elif ext in _PLAIN_EXTS:
            text = _read_plain(path)
    if len(text) > STORED_TEXT_CAP:
        text = text[:STORED_TEXT_CAP] + "\n\n(Il resto del documento non è stato incluso.)"
    return text.strip()


def attachment_blocks(session: dict) -> str:
    """Testo degli allegati per l'istruzione. Le immagini e i media vanno anche nei byte."""
    blocks = []
    used = 0
    for att in (session or {}).get("attachments") or []:
        if not isinstance(att, dict):
            continue
        kind = att.get("kind") or ""
        title = att.get("title") or os.path.basename(att.get("path") or "") or "allegato"
        path = att.get("path") or ""
        label = _kind_it(kind)
        if not path or not os.path.isfile(path):
            blocks.append(f"--- {title} ({label}) ---\nFile non più trovato sul disco.")
            continue
        if kind == "document":
            body = _attachment_document_text(path)
            room = ATTACH_TEXT_CAP - used
            if room <= 200:
                blocks.append(
                    f"--- {title} (documento) ---\n"
                    "(Testo non incluso: la richiesta ha già abbastanza materiale.)"
                )
                continue
            if len(body) > room:
                body = body[:room] + "\n…(testo accorciato)"
            used += len(body)
            blocks.append(f"--- {title} (documento) ---\n{body or '(Nessun testo letto.)'}")
        elif kind == "image":
            blocks.append(
                f"--- {title} (immagine) ---\n"
                "Immagine allegata insieme a questa domanda."
            )
        else:
            blocks.append(
                f"--- {title} ({label}) ---\n"
                "File audio o video allegato insieme a questa domanda. "
                "Ascoltalo o guardalo, non inventare ciò che non c'è."
            )
    if not blocks:
        return ""
    return (
        "=== Allegati aggiunti in questa conversazione ===\n\n"
        + "\n\n".join(blocks)
    )


def system_instruction(session: dict, when: datetime.datetime | None = None) -> str:
    """Regole, data di oggi e materiale del file. Non va nella cronologia visibile."""
    when = when or datetime.datetime.now()
    kind = (session or {}).get("kind") or "document"
    free = kind == "free"
    if free:
        about = (
            "Non c'è un file di partenza. Rispondi alla domanda. "
            "Se più sotto ci sono allegati, quelli sono il materiale da usare."
        )
        plane = "Nella conversazione:"
        plane_rule = (
            "«Nella conversazione» contiene solo la domanda e gli allegati di questa chat."
        )
    else:
        kind_label = "immagine" if kind == "image" else "documento"
        about = (
            f"Stai parlando di un file ({kind_label}) già aperto in RTAD. "
            "Il materiale qui sotto è la fonte principale. "
            "Gli allegati aggiunti dopo, se ci sono, si usano insieme a quel file: "
            "il file di partenza resta."
        )
        plane = "Nel file:"
        plane_rule = "«Nel file» contiene solo ciò che è nel materiale RTAD."
    lines = [
        "Sei l'assistente di Ricerca Testuale Accesso Digitale.",
        f"Oggi è {format_now(when)} (ora locale del computer).",
        "Rispondi nella lingua della domanda. Se la domanda è in italiano, rispondi in italiano.",
        about,
        "Quando servi entrambi i piani, separali con questi titoli esatti:",
        plane,
        "Approfondimento:",
        plane_rule,
        "«Approfondimento» solo se in questa richiesta è attiva la consultazione web, "
        "e solo per ciò che non è già nel materiale. Includi i link delle fonti.",
        "Se un dato non c'è nel materiale e il web non è attivo, dillo. "
        "Non inventare citazioni, nomi o date.",
        "Quando citi una pagina, usa solo un indirizzo che risulta dalle fonti consultate. "
        "Non inventare né abbreviare un dominio. Se non hai l'indirizzo esatto, "
        "dì il nome del sito senza link.",
        "Non presentare come recensione o articolo su questo materiale una pagina che parla d'altro.",
        "Se nel materiale c'è una data, preferiscila a una data trovata sul web e segnala il contrasto.",
        "Usa il web per persone, aggiornamenti, «è ancora così» e notizie. "
        "Non usarlo per riscrivere ciò che il materiale già dice.",
        "",
        "=== Materiale del file ===",
        (session or {}).get("context_text") or "(Nessun testo del file disponibile.)",
    ]
    extra = attachment_blocks(session)
    if extra:
        lines.append("")
        lines.append(extra)
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


def format_hit_notice(location: str, snippet: str) -> str:
    """Frase del risultato, a schermo e in voce, e nel materiale di Gemini."""
    loc = " ".join((location or "").split())
    snip = " ".join((snippet or "").split())
    if len(snip) > 240:
        snip = snip[:240].rstrip() + "…"
    if loc and snip:
        return f"Punto della ricerca: {loc}. Estratto: {snip}"
    if loc:
        return f"Punto della ricerca: {loc}."
    if snip:
        return f"Estratto della ricerca: {snip}"
    return ""


def message_storage_key(file_path: str, index) -> str:
    """Una conversazione per messaggio, non per l'intera casella o il feed."""
    try:
        number = int(index)
    except (TypeError, ValueError):
        number = 0
    token = _file_key(file_path) + f":msg:{number}"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:20]


def text_result_key(token: str) -> str:
    """Conversazione su una riga che non è un file sul disco (notizia, indirizzo)."""
    raw = (token or "").strip().lower()
    if not raw:
        return ""
    return hashlib.sha256(
        ("rtad-hit:" + raw).encode("utf-8", errors="replace")
    ).hexdigest()[:20]


def result_message_key(path, prefix, index, viewer_text, attachment_path="") -> str:
    """Chiave se il risultato è un messaggio dentro un archivio. Vuota altrimenti."""
    if (attachment_path or "").strip() and os.path.isfile(attachment_path):
        return ""
    if not (viewer_text or "").strip():
        return ""
    if not str(prefix or "").startswith(_MESSAGE_PREFIXES):
        return ""
    if index is None:
        return ""
    return message_storage_key(path, index)


def _cap_stored(text: str) -> str:
    text = (text or "").strip()
    if len(text) > STORED_TEXT_CAP:
        return (
            text[:STORED_TEXT_CAP]
            + "\n\n(Il resto del testo non è stato caricato in memoria.)"
        )
    return text


def _with_hit(text: str, session: dict) -> str:
    note = ((session or {}).get("hit_notice") or "").strip()
    body = (text or "").strip()
    if not note:
        return body
    if body.startswith(note):
        return body
    if not body:
        return note
    return note + "\n\n" + body


def _document_body(struct) -> str:
    if not isinstance(struct, dict):
        return ""
    return (struct.get("body") or struct.get("plain") or "").strip()


def _fill_document_body(session: dict, struct, path: str) -> dict:
    """Testo del file, oppure il messaggio già letto in ricerca. Non rilegge una casella intera."""
    if session.get("locked_material"):
        body = _cap_stored(session.get("material_text") or "")
        session["material_text"] = body
        return {
            "body": body,
            "plain": body,
            "outline": [],
            "message": "",
        }
    if not isinstance(struct, dict):
        struct = {}
    else:
        struct = dict(struct)
    if (
        not _document_body(struct)
        and path
        and os.path.isfile(path)
        and _text_extractor is not None
    ):
        try:
            extra = (_text_extractor(path) or "").strip()
        except Exception as exc:
            logging.debug(f"Chat: testo del file non letto: {exc}")
            extra = ""
        if extra:
            extra = _cap_stored(extra)
            struct["body"] = extra
            struct["plain"] = extra
            low = (struct.get("message") or "").lower()
            if "non supportat" in low or "non espone" in low:
                struct["message"] = ""
    if not _document_body(struct):
        msg = (struct.get("message") or "").strip()
        low = msg.lower()
        generic = (not msg) or ("non supportat" in low) or ("non espone" in low)
        if (session.get("hit_notice") or "").strip() and generic:
            struct["message"] = NOTICE_HIT_ONLY
        elif not msg and path:
            struct["message"] = NOTICE_NO_TEXT
    return struct


def new_session(
    kind: str,
    path: str,
    *,
    struct: dict | None = None,
    displayed: str = "",
    prior_report: str = "",
    source_path: str = "",
    do_refresh: bool = True,
    hit_notice: str = "",
    material_text: str = "",
    stable_key: str = "",
    title: str = "",
) -> dict:
    now = datetime.datetime.now().replace(microsecond=0).isoformat(timespec="seconds")
    session = {
        "v": CHAT_VERSION,
        "kind": kind if kind in ("image", "document", "free") else "document",
        "path": path or "",
        "source_path": source_path or "",
        "title": os.path.basename(path or "") or ("Conversazione" if kind == "free" else "File"),
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
        "attachments": [],
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
    notice = (hit_notice or "").strip()
    if notice:
        session["hit_notice"] = notice
    material = _cap_stored(material_text or "")
    if material:
        session["locked_material"] = True
        session["material_text"] = material
        session["_struct"] = {
            "body": material,
            "plain": material,
            "outline": [],
            "message": "",
        }
        session["_displayed"] = material
    key = (stable_key or "").strip()
    if key:
        session["stable_key"] = key
    if (title or "").strip():
        session["title"] = title.strip()
    if do_refresh:
        refresh_context(session)
    return session


def new_free_session() -> dict:
    """Conversazione senza un file già aperto. Gli allegati si aggiungono dopo."""
    session = new_session("free", "", do_refresh=False)
    session["title"] = "Conversazione"
    session["stable_key"] = "c" + uuid.uuid4().hex[:19]
    session["context_text"] = (
        "Nessun file di partenza. "
        "Rispondi alla domanda e, se ci sono, agli allegati."
    )
    session["full_text"] = session["context_text"]
    return session


def attachment_problem(session: dict, path: str) -> str:
    """Motivo breve se il file non va proprio messo nel gruppo. Vuoto se può entrare.

    Non legge il contenuto: testo assente, immagine illeggibile e limiti
    audio/video si controllano quando si conferma con Invio.
    """
    path = (path or "").strip()
    name = os.path.basename(path) or "file"
    if not path or not os.path.isfile(path):
        return f"{name}: file non trovato."
    if not attachment_kind(path):
        return f"{name}: questo formato non si allega."
    if _same_path(path, (session or {}).get("path") or ""):
        return f"{name} è già il file di questa conversazione."
    for att in (session or {}).get("attachments") or []:
        if isinstance(att, dict) and _same_path(att.get("path") or "", path):
            return f"{name} è già allegato."
    return ""


def add_attachment(session: dict, path: str) -> tuple:
    """(ok, messaggio). Il messaggio è il nome del file, oppure il motivo del rifiuto."""
    path = (path or "").strip()
    name = os.path.basename(path) or "file"
    problem = attachment_problem(session, path)
    if problem:
        return False, problem
    kind = attachment_kind(path)
    atts = session.setdefault("attachments", [])
    if len(atts) >= MAX_ATTACHMENTS:
        return False, (
            f"In questa conversazione si allega fino a {MAX_ATTACHMENTS} file."
        )
    try:
        size = os.path.getsize(path)
    except Exception:
        size = 0
    if kind == "image":
        b64, _mime = _image_bytes(path)
        if not b64:
            return False, f"{name}: immagine troppo grande o non leggibile (max 25 MB)."
    elif kind in ("audio", "video"):
        try:
            import rtad_media as media

            err = media._check_ai_limits(path)
        except Exception as exc:
            err = str(exc)
        if err:
            return False, f"{name}: {err}"
    else:
        if size > MAX_ATTACH_DOC_BYTES:
            return False, f"{name}: documento troppo grande per allegarlo in chat."
        text = _attachment_document_text(path)
        if not text:
            return False, f"{name}: non c'è testo da leggere."
    atts.append({"path": path, "kind": kind, "title": name})
    title = (session.get("title") or "").strip()
    if session.get("kind") == "free" and title in ("", "Conversazione", "File"):
        session["title"] = name
    return True, name


def remove_attachment(session: dict, index: int) -> str:
    """Toglie un allegato. Restituisce il nome, o stringa vuota."""
    atts = (session or {}).get("attachments") or []
    if index < 0 or index >= len(atts):
        return ""
    att = atts.pop(index)
    _discard_media_cache(att if isinstance(att, dict) else {})
    if isinstance(att, dict):
        return att.get("title") or os.path.basename(att.get("path") or "")
    return ""


def _discard_media_cache(att: dict) -> None:
    cache = {}
    if isinstance(att, dict):
        cache = att.pop("_media_cache", None) or {}
    names = cache.get("names") or []
    if not names:
        return
    key = ""
    if rtad_ocr is not None and hasattr(rtad_ocr, "get_gemini_api_key"):
        try:
            key = (rtad_ocr.get_gemini_api_key() or "").strip()
        except Exception:
            key = ""
    if not key:
        return
    try:
        import rtad_media as media

        media._gemini_files_delete(names, key)
    except Exception:
        logging.debug("Chat: file Gemini non cancellato", exc_info=True)


def refresh_context(session: dict) -> None:
    """Rilegge il file. Non tocca i turni."""
    if not session:
        return
    path = session.get("path") or ""
    ts, _label = _mtime_label(path) if path else (None, "")
    old = session.get("mtime")
    if old and ts and abs(float(ts) - float(old)) > 1 and not session.get("locked_material"):
        session["context_note"] = (
            "Il file sul disco è stato modificato dopo l'ultimo scambio di questa conversazione."
        )
    session["mtime"] = ts
    _apply_report_material(session)
    kind = session.get("kind")
    if kind == "free" and not path:
        session["context_text"] = (
            "Nessun file di partenza. "
            "Rispondi alla domanda e, se ci sono, agli allegati."
        )
        session["full_text"] = session["context_text"]
        session["image_b64"] = ""
        session["image_missing"] = False
        return
    if kind == "image":
        b64, mime = _image_bytes(path)
        if b64:
            session["image_b64"] = b64
            session["image_mime"] = mime
            session["image_missing"] = False
        elif not session.get("image_b64"):
            session["image_missing"] = True
        session["context_text"] = _with_hit(
            compose_image_text(
                path,
                session.get("_prior") or "",
                session.get("source_path") or "",
            ),
            session,
        )
        session["full_text"] = session["context_text"]
        return

    struct = None if session.get("locked_material") else session.get("_struct")
    if (
        not session.get("locked_material")
        and struct is None
        and path
        and rtad_docstruct is not None
        and os.path.isfile(path)
    ):
        try:
            struct = rtad_docstruct.extract_document_structure(path)
        except Exception as exc:
            logging.debug(f"Chat: struttura documento non riletta: {exc}")
            struct = None
    struct = _fill_document_body(session, struct, path)
    session["_struct"] = struct
    if struct and struct.get("outline"):
        session["outline"] = list(struct.get("outline") or [])
    full = _with_hit(
        compose_document_text(path, struct, session.get("_displayed") or ""),
        session,
    )
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
    if session.get("report_orphan"):
        session["context_note"] = NOTICE_REPORT_ORPHAN


def is_rtad_report(path: str) -> bool:
    """True per un resoconto già salvato (nome.rtad.txt)."""
    return (path or "").lower().endswith(".rtad.txt")


def notice_report_ready(name: str) -> str:
    """Frase quando la foto, il video o il documento è ancora accanto."""
    label = (name or "").strip() or "file"
    return (
        "Resoconto già salvato, senza rifare l'analisi. "
        f"File di partenza: {label}."
    )


def _report_body(path: str) -> str:
    """Testo del resoconto. Il glossario attivo, se c'è, resta in memoria."""
    text = _read_plain(path).strip()
    try:
        import rtad_media as media

        fn = getattr(media, "apply_transcript_glossary", None)
        if fn and text:
            text = (fn(text) or "").strip()
    except Exception:
        logging.debug("Chat: glossario sul resoconto non applicato", exc_info=True)
    return text or _EMPTY_REPORT


def _report_struct(body: str) -> dict:
    return {
        "body": body or _EMPTY_REPORT,
        "plain": body or _EMPTY_REPORT,
        "outline": [],
        "message": _REPORT_MATERIAL_MESSAGE,
    }


def _apply_report_material(session: dict) -> None:
    """Il testo salvato è il materiale. Non si rilegge il video come documento."""
    if not session:
        return
    report_path = (session.get("report_path") or "").strip()
    if not report_path or not os.path.isfile(report_path):
        return
    body = _report_body(report_path)
    if session.get("kind") == "image":
        session["_prior"] = body
        return
    session["_struct"] = _report_struct(body)
    session["_displayed"] = body


def _is_report_source(path: str) -> bool:
    """Foto, audio, video o documento. Non un altro resoconto."""
    if not path or is_rtad_report(path) or path.lower().endswith(".chat.txt"):
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext in _IMAGE_MIME or ext in _DOC_EXTS:
        return True
    try:
        import rtad_media as media

        if ext in getattr(media, "MEDIA_EXTS", ()):
            return True
    except Exception:
        pass
    return False


def _extensions_named_in_report(stem: str, head: str) -> list:
    """Estensioni che il resoconto scrive accanto al nome (anche a capo)."""
    compact = re.sub(r"\s+", "", head or "").lower()
    stem_c = re.sub(r"\s+", "", stem or "").lower()
    if not stem_c or not compact:
        return []
    exts = set(_IMAGE_MIME) | set(_DOC_EXTS)
    try:
        import rtad_media as media

        exts |= set(getattr(media, "MEDIA_EXTS", ()))
    except Exception:
        pass
    found = []
    for ext in exts:
        if (stem_c + ext) in compact and ext not in found:
            found.append(ext)
    return found


def _source_rank(path: str) -> int:
    ext = os.path.splitext(path)[1].lower()
    try:
        import rtad_media as media

        if ext in getattr(media, "MEDIA_EXTS", ()):
            return 0
    except Exception:
        pass
    if ext in _IMAGE_MIME:
        return 1
    if ext in _DOC_EXTS:
        return 2
    return 9


def original_beside_report(path: str) -> str:
    """File con lo stesso nome, nella stessa cartella. Vuoto se non c'è più.

    «video.mp4» sta accanto a «video.rtad.txt».
    Vale anche «video.mp4.rtad.txt», il nome intero più .rtad.txt.
    """
    path = os.path.abspath(path or "")
    if not is_rtad_report(path) or not os.path.isfile(path):
        return ""
    folder = os.path.dirname(path)
    name = os.path.basename(path)
    stem = name[: -len(".rtad.txt")]
    if not stem:
        return ""
    direct = os.path.join(folder, stem)
    if os.path.isfile(direct) and _is_report_source(direct):
        return os.path.abspath(direct)
    stem_key = os.path.normcase(stem)
    candidates = []
    try:
        entries = os.listdir(folder)
    except OSError:
        return ""
    for entry in entries:
        full = os.path.join(folder, entry)
        if not os.path.isfile(full) or not _is_report_source(full):
            continue
        base = os.path.splitext(entry)[0]
        if os.path.normcase(base) != stem_key:
            continue
        candidates.append(os.path.abspath(full))
    if not candidates:
        return ""
    head = _read_plain(path)[:12000]
    named_exts = _extensions_named_in_report(stem, head)
    if named_exts:
        picked = [
            c for c in candidates
            if os.path.splitext(c)[1].lower() in named_exts
        ]
        if not picked:
            return ""
        candidates = picked
    if len(candidates) == 1:
        return candidates[0]
    compact_head = re.sub(r"\s+", "", head)
    named = []
    for cand in candidates:
        token = re.sub(r"\s+", "", os.path.basename(cand))
        if token and token in compact_head:
            named.append(cand)
    pool = named or candidates
    pool.sort(key=lambda p: (_source_rank(p), os.path.basename(p).lower()))
    return pool[0]


def chat_anchor_for_report(path: str) -> str:
    """Cronologia: sull'originale se c'è, altrimenti sul resoconto."""
    original = original_beside_report(path)
    if original:
        return original
    return os.path.abspath(path or "")


def new_session_from_report(path: str) -> dict:
    """Conversazione sul testo già salvato. Nessuna nuova descrizione o trascrizione."""
    path = os.path.abspath(path or "")
    body = _report_body(path)
    original = original_beside_report(path)
    struct = _report_struct(body)
    if original:
        kind = attachment_kind(original)
        if kind == "image":
            session = new_session(
                "image",
                original,
                prior_report=body,
                do_refresh=False,
            )
        else:
            # Audio e video restano il file di partenza, ma non vengono ricaricati.
            session = new_session(
                "document",
                original,
                struct=struct,
                displayed=body,
                do_refresh=False,
            )
        session["report_notice"] = notice_report_ready(os.path.basename(original))
        session["report_orphan"] = False
    else:
        session = new_session(
            "document",
            path,
            struct=struct,
            displayed=body,
            do_refresh=False,
        )
        session["report_notice"] = NOTICE_REPORT_ORPHAN
        session["report_orphan"] = True
        session["context_note"] = NOTICE_REPORT_ORPHAN
        session["title"] = os.path.basename(path)
    session["report_path"] = path
    refresh_context(session)
    if session.get("report_orphan"):
        session["context_note"] = NOTICE_REPORT_ORPHAN
        session["report_notice"] = NOTICE_REPORT_ORPHAN
    return session


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
    for att in session.get("attachments") or []:
        if not isinstance(att, dict) or att.get("kind") != "image":
            continue
        apath = att.get("path") or ""
        if _same_path(apath, session.get("path") or ""):
            continue
        b64, mime = _image_bytes(apath)
        title = att.get("title") or os.path.basename(apath) or "immagine"
        if not b64:
            parts.append(
                {
                    "text": (
                        f"Allegato immagine {title}: non più leggibile dal disco."
                    )
                }
            )
            continue
        parts.append({"text": f"Allegato immagine: {title}"})
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime or "image/jpeg",
                    "data": b64,
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
    if rtad_ocr is not None and hasattr(rtad_ocr, "readable_gemini_error"):
        try:
            return rtad_ocr.readable_gemini_error(err)
        except Exception:
            logging.debug("Frase Gemini non tradotta", exc_info=True)
    raw = (err or "").strip()
    return raw or "Gemini non ha risposto."


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


def _post_generate(model: str, key: str, payload: dict, timeout: int = REQUEST_TIMEOUT_SEC) -> tuple:
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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


def _payload_uses_file_api(payload: dict) -> bool:
    for content in (payload or {}).get("contents") or []:
        for part in (content or {}).get("parts") or []:
            if isinstance(part, dict) and ("file_data" in part or "fileData" in part):
                return True
    return False


def _media_parts(att: dict, key: str, should_abort=None) -> tuple:
    """(parti senza il prompt, errore). Riusa l'upload finché il file non cambia."""
    path = (att or {}).get("path") or ""
    try:
        size = os.path.getsize(path)
        mtime = int(os.path.getmtime(path))
    except Exception as exc:
        return [], str(exc)
    sig = (size, mtime)
    cache = att.get("_media_cache") or {}
    if cache.get("sig") == sig and cache.get("parts"):
        return list(cache["parts"]), ""
    try:
        import rtad_media as media
    except Exception as exc:
        return [], str(exc)
    if cache.get("names"):
        try:
            media._gemini_files_delete(cache.get("names") or [], key)
        except Exception:
            pass
    title = att.get("title") or os.path.basename(path)
    parts, names, _mode, err = media._gemini_build_media_parts(
        path,
        f"Allegato: {title}",
        key,
        should_abort=should_abort,
    )
    if err or not parts:
        return [], err or "allegato non pronto"
    body = list(parts[1:])
    att["_media_cache"] = {"sig": sig, "parts": body, "names": list(names or [])}
    return body, ""


def _append_media_parts(session: dict, payload: dict, key: str, should_abort=None) -> str:
    """Aggiunge audio/video all'ultima domanda. Stringa vuota se ok, 'aborted' se annullato."""
    contents = (payload or {}).get("contents") or []
    if not contents:
        return ""
    parts = contents[-1].setdefault("parts", [])
    for att in (session or {}).get("attachments") or []:
        if should_abort and should_abort():
            return "aborted"
        if not isinstance(att, dict) or att.get("kind") not in ("audio", "video"):
            continue
        path = att.get("path") or ""
        title = att.get("title") or os.path.basename(path) or "file"
        if not os.path.isfile(path):
            return f"{title}: file non più trovato."
        got, err = _media_parts(att, key, should_abort)
        if err:
            if should_abort and should_abort():
                return "aborted"
            return f"{title}: {err}"
        parts.append({"text": f"Allegato {att.get('kind')}: {title}"})
        parts.extend(got)
    return ""


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
    media_err = _append_media_parts(session, payload, key, should_abort)
    if media_err == "aborted":
        return _fail("", aborted=True)
    if media_err:
        return _fail(media_err)
    timeout = FILE_API_TIMEOUT_SEC if _payload_uses_file_api(payload) else REQUEST_TIMEOUT_SEC
    web_note = ""
    last_err = ""
    for model in models:
        if should_abort and should_abort():
            return _fail("", aborted=True)
        ok, data, err = _post_generate(model, key, payload, timeout)
        if not ok and use_web and int((data or {}).get("_http") or 0) == 400:
            fallback = dict(payload)
            fallback.pop("tools", None)
            ok, data, err = _post_generate(model, key, fallback, timeout)
            if ok:
                web_note = (
                    "\n\n(La consultazione web non è riuscita in questo scambio.)"
                )
        if not ok:
            last_err = err or "errore Gemini"
            code = int((data or {}).get("_http") or 0)
            # 402: crediti prepagati finiti. Non si prova un altro modello.
            if code == 402:
                return _fail(last_err, model)
            if code in (404, 429, 503):
                logging.info(
                    "Chat Gemini %s HTTP %s, provo il modello successivo",
                    model,
                    code,
                )
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
    if session.get("kind") == "free":
        title = (session.get("title") or "").strip()
        if title in ("", "Conversazione", "File"):
            short = " ".join((question or "").split())
            if short:
                session["title"] = short[:60] + ("…" if len(short) > 60 else "")
    if session.get("mtime") is None:
        ts, _label = _mtime_label(session.get("path") or "")
        session["mtime"] = ts


def transcript(session: dict) -> str:
    """Testo piano per leggere, copiare, salvare, stampare. Senza chiave."""
    lines = [
        "Ricerca Testuale Accesso Digitale — Conversazione con Gemini",
    ]
    if (session.get("kind") == "free") and not (session.get("path") or ""):
        lines.append(f"Conversazione: {session.get('title') or 'Conversazione'}")
        lines.append("File: nessuno")
    else:
        lines.append(f"File: {session.get('title') or ''}")
    attached = []
    for att in session.get("attachments") or []:
        if isinstance(att, dict):
            name = att.get("title") or os.path.basename(att.get("path") or "")
            if name:
                attached.append(f"{name} ({_kind_it(att.get('kind') or '')})")
    if attached:
        lines.append("Allegati: " + "; ".join(attached))
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
        **({"report_path": session.get("report_path")} if session.get("report_path") else {}),
        **({"report_orphan": True} if session.get("report_orphan") else {}),
        **({"report_notice": session.get("report_notice")} if session.get("report_notice") else {}),
        **({"hit_notice": session.get("hit_notice")} if session.get("hit_notice") else {}),
        **({"locked_material": True} if session.get("locked_material") else {}),
        **({"material_text": session.get("material_text") or ""} if session.get("locked_material") else {}),
        "turns": [
            {
                "role": t.get("role"),
                "text": t.get("text") or "",
                **({"model": t.get("model")} if t.get("model") else {}),
            }
            for t in (session.get("turns") or [])
            if t.get("role") in ("user", "model")
        ],
        "attachments": [
            {
                "path": a.get("path") or "",
                "kind": a.get("kind") or "",
                "title": a.get("title") or "",
            }
            for a in (session.get("attachments") or [])
            if isinstance(a, dict) and (a.get("path") or "")
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
    session["attachments"] = []
    for att in data.get("attachments") or []:
        if not isinstance(att, dict):
            continue
        apath = (att.get("path") or "").strip()
        if not apath:
            continue
        session["attachments"].append(
            {
                "path": apath,
                "kind": att.get("kind") or attachment_kind(apath) or "document",
                "title": att.get("title") or os.path.basename(apath),
            }
        )
    if data.get("stable_key"):
        session["stable_key"] = data.get("stable_key")
    if data.get("source_url"):
        session["source_url"] = data.get("source_url")
    saved_title = str(data.get("title") or "").strip()
    if saved_title and not _temp_media_name(saved_title):
        session["title"] = saved_title
    elif _temp_media_name(session.get("title") or "") and saved_title:
        session["title"] = saved_title
    if data.get("report_path"):
        session["report_path"] = data.get("report_path")
    session["report_orphan"] = bool(data.get("report_orphan"))
    if data.get("report_notice"):
        session["report_notice"] = data.get("report_notice")
    if data.get("hit_notice"):
        session["hit_notice"] = data.get("hit_notice")
    if data.get("locked_material"):
        session["locked_material"] = True
        session["material_text"] = data.get("material_text") or ""
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


def list_saved(base_dir: str, file_path: str, session: dict | None = None) -> list:
    """Elenco per questo file: corrente per prima, poi archivio dal più recente."""
    keys = _keys_for_path(file_path, session)
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


def load_by_key(
    base_dir: str,
    key: str,
    *,
    struct=None,
    displayed="",
    prior_report="",
) -> dict | None:
    """Cronologia di un messaggio o di una riga, non del file intero."""
    key = (key or "").strip()
    if not key:
        return None
    dest = os.path.join(chat_dir(base_dir), key + ".json")
    if not os.path.isfile(dest):
        return None
    try:
        with open(dest, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        logging.warning(f"Chat: lettura cronologia non riuscita: {exc}")
        return None
    if not isinstance(data, dict):
        return None
    return _session_from_public(
        data,
        struct=struct,
        displayed=displayed,
        prior_report=prior_report,
    )


def has_saved_key(base_dir: str, key: str) -> bool:
    key = (key or "").strip()
    if not key:
        return False
    dest = os.path.join(chat_dir(base_dir), key + ".json")
    if not os.path.isfile(dest):
        return False
    try:
        with open(dest, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return False
    return isinstance(data, dict) and bool(data.get("turns"))


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
