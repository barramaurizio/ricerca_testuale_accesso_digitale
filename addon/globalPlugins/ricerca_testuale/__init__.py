import addonHandler
import ctypes
import datetime
import globalPluginHandler
import globalVars
import json
import os
import re
import shutil
import scriptHandler
import subprocess
import sys
import tempfile
import threading
import time
import ui
import webbrowser
import wx
import xml.etree.ElementTree as ET
import zipfile
import zlib
import quopri
import urllib.parse
import urllib.request
import email
from email import policy
from email.header import decode_header
from email.utils import parsedate_to_datetime
import html
import csv
import platform

try:
    import tones
except ImportError:
    tones = None

try:
    import feedparser
except ImportError:
    feedparser = None

addonHandler.initTranslation()

APP_TITLE = "Ricerca Testuale Accesso Digitale"
APP_VERSION = "1.5.3"
DONATION_URL = "https://paypal.me/AccessoDigitale"
YOUTUBE_URL = "https://www.youtube.com/@AccessoDigitale"
GITHUB_URL = "https://github.com/barramaurizio/ricerca_testuale_accesso_digitale/releases"
GITHUB_API_LATEST = "https://api.github.com/repos/barramaurizio/ricerca_testuale_accesso_digitale/releases/latest"
EMAIL_DESTINATARIO = "mauritechstudio@gmail.com"

CONFIG_DIR = os.path.join(globalVars.appArgs.configPath, "rtad_data")
if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass
CONFIG_FILE = os.path.join(CONFIG_DIR, "rtad_settings.json")


def normalize_search_text(txt, remove_accents=False):
    if not txt:
        return ""
    for ap in ["’", "‘", "`", "´", "ʼ", "ʻ", "′", "‵", "՚", "Ꞌ"]:
        txt = txt.replace(ap, "'")
    for q in ["“", "”", "«", "»", "„"]:
        txt = txt.replace(q, '"')
    txt = txt.replace(chr(160), " ")
    if remove_accents:
        import unicodedata
        nfkd = unicodedata.normalize('NFKD', txt)
        return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return txt.lower()

def text_matches_terms(text, terms):
    if not text or not terms:
        return False
    n = normalize_search_text(text, False)
    if all(t in n for t in terms):
        return True
    n_no = normalize_search_text(text, True)
    terms_no = [normalize_search_text(t, True) for t in terms]
    return all(t in n_no for t in terms_no)

def clean_eml_text(raw_text):
    try:
        decoded = quopri.decodestring(raw_text.encode("latin1", errors="ignore")).decode("utf-8", errors="ignore")
    except Exception:
        decoded = raw_text
    decoded = urllib.parse.unquote_plus(decoded)
    decoded = re.sub(r"<[^<]+?>", " ", decoded)
    return " ".join(decoded.split())


def decode_email_header(raw_header):
    if not raw_header:
        return ""
    try:
        decoded_parts = decode_header(str(raw_header))
        result = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(encoding or "utf-8", errors="ignore")
            else:
                result += str(part)
        return " ".join(result.splitlines()).strip()
    except Exception:
        return str(raw_header)


def get_clean_email_text(msg):
    """Estrae solo testo/HTML dall'email; salta allegati e parti binarie (PDF, ecc.)."""
    body = ""
    body_html = ""
    skipped = []
    max_bytes = 1_500_000

    def _looks_binary(payload):
        if not payload:
            return False
        head = payload[:8192]
        if head.startswith(b"%PDF"):
            return True
        if b"\x00" in head:
            return True
        return False

    def _consume_part(part):
        nonlocal body, body_html
        ctype = (part.get_content_type() or "").lower()
        if ctype.startswith("multipart/"):
            return
        cdisp = str(part.get("Content-Disposition") or "").lower()
        filename = ""
        try:
            filename = part.get_filename() or ""
        except Exception:
            filename = ""
        label = filename or ctype

        if "attachment" in cdisp:
            skipped.append(label)
            return
        if ctype not in ("text/plain", "text/html"):
            if filename or ctype.startswith(("application/", "image/", "audio/", "video/", "model/")):
                skipped.append(label)
            return

        try:
            payload = part.get_payload(decode=True)
        except Exception:
            payload = None
        if not payload:
            return
        if _looks_binary(payload):
            skipped.append(label or "binario")
            return
        if len(payload) > max_bytes:
            payload = payload[:max_bytes]

        charset = part.get_content_charset() or "utf-8"
        try:
            text_part = payload.decode(charset, errors="ignore")
        except Exception:
            text_part = payload.decode("latin1", errors="ignore")

        if ctype == "text/plain":
            body += text_part + "\n"
        else:
            body_html += text_part + "\n"

    try:
        if msg.is_multipart():
            for part in msg.walk():
                _consume_part(part)
        else:
            _consume_part(msg)
    except Exception:
        pass

    if not body.strip() and body_html:
        body = body_html

    body = re.sub(r"<style.*?>.*?</style>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<script.*?>.*?</script>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.IGNORECASE)
    body = re.sub(r"</p>", "\n\n", body, flags=re.IGNORECASE)
    body = re.sub(r"</div>", "\n", body, flags=re.IGNORECASE)
    body = re.sub(r"<[^>]+>", " ", body)
    body = html.unescape(body)
    lines = [line.strip() for line in body.split("\n")]
    text = "\n".join([line for line in lines if line])

    if skipped:
        seen = set()
        uniq = []
        for s in skipped:
            key = str(s).strip() or "allegato"
            if key not in seen:
                seen.add(key)
                uniq.append(key)
        note = ", ".join(uniq[:8])
        if len(uniq) > 8:
            note += f" (+{len(uniq) - 8})"
        text = (text + "\n\n" if text else "") + f"[Allegati non testuali omessi: {note}]"
    return text


def strip_html_to_text(html_content):
    if not html_content:
        return ""
    text = str(html_content)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join([line for line in lines if line])


def extract_feed_entry_text(entry):
    parts = []
    title = entry.get("title") or ""
    if title:
        parts.append(str(title))
    for key in ("summary", "description"):
        val = entry.get(key)
        if val:
            parts.append(strip_html_to_text(val))
    content_list = entry.get("content") or []
    for item in content_list:
        if isinstance(item, dict):
            val = item.get("value")
            if val:
                parts.append(strip_html_to_text(val))
        elif item:
            parts.append(strip_html_to_text(item))
    tags = entry.get("tags") or []
    for tag in tags:
        if isinstance(tag, dict):
            term = tag.get("term") or tag.get("label") or ""
        else:
            term = str(tag)
        if term:
            parts.append(str(term))
    return "\n".join([p for p in parts if p]).strip()


def search_online_or_local_feed(source, terms):
    results = []
    if feedparser is None:
        return results
    try:
        feed = feedparser.parse(source)
    except Exception:
        return results
    for entry in getattr(feed, "entries", []) or []:
        text = extract_feed_entry_text(entry)
        title = entry.get("title") or "(Nessun Titolo)"
        if not text_matches_terms(text, terms) and not text_matches_terms(title, terms):
            continue
        link = entry.get("link") or source
        clean = strip_html_to_text(text)
        snippet = clean[:150] + "..." if len(clean) > 150 else clean
        display_title = title[:60] + "..." if len(title) > 60 else title
        results.append({
            "file_path": link,
            "file_name": display_title,
            "prefix": "[RSS]",
            "mtime": time.time(),
            "line_number": None,
            "paragraph_index": None,
            "location_info": "Notizia Feed RSS",
            "snippet": snippet,
            "article_url": link,
        })
    return results


def parse_opml_urls(path):
    urls = []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        for outline in root.iter():
            tag = outline.tag.lower() if isinstance(outline.tag, str) else ""
            if not tag.endswith("outline"):
                continue
            url = outline.attrib.get("xmlUrl") or outline.attrib.get("xmlurl")
            if not url:
                url = outline.attrib.get("url")
            if url and (url.startswith("http://") or url.startswith("https://")):
                urls.append(url)
    except Exception:
        pass
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def find_thunderbird_feeds_dirs():
    found = []
    appdata = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    for tb_name in ("Thunderbird", "thunderbird"):
        profiles_root = os.path.join(appdata, tb_name, "Profiles")
        if not os.path.isdir(profiles_root):
            continue
        try:
            for profile in os.listdir(profiles_root):
                feeds_dir = os.path.join(profiles_root, profile, "Mail", "Feeds")
                if os.path.isdir(feeds_dir):
                    found.append(os.path.normpath(feeds_dir))
        except Exception:
            pass
    seen = set()
    unique = []
    for d in found:
        key = d.lower()
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def is_thunderbird_junk_file(path):
    """Indici/database Thunderbird da non scansionare (.msf, sqlite, ecc.)."""
    if not path:
        return False
    name = os.path.basename(path).lower()
    for bad in (".msf", ".sqlite", ".sqlite-wal", ".sqlite-shm", ".json", ".dat", ".ini"):
        if name.endswith(bad):
            return True
    if name in ("msgfilterrules.dat", "filterlog.html", "feeds.rdf", "feeditems.json"):
        return True
    return False


def is_thunderbird_feeds_path(path):
    if not path:
        return False
    low = path.replace("/", "\\").lower()
    return "thunderbird" in low and ("\\mail\\feeds" in low or low.endswith("\\feeds") or "\\feeds\\" in low)


def is_thunderbird_mail_container(path):
    """Narrow detection: Thunderbird mail/feeds containers only, skip indexes/DBs."""
    if not path:
        return False
    if is_thunderbird_junk_file(path):
        return False
    low = path.replace("/", "\\").lower()
    if "thunderbird" not in low:
        return False
    return ("\\mail\\" in low) or ("\\imapmail\\" in low) or ("\\feeds" in low) or low.endswith("\\feeds")


def read_file_bytes_shared(file_path):
    """Legge un file anche se Thunderbird (o altro) lo tiene aperto.

    Su Windows usa CreateFile con condivisione lettura/scrittura; altrove open normale.
    """
    if sys.platform.startswith("win"):
        try:
            GENERIC_READ = 0x80000000
            FILE_SHARE_READ = 0x00000001
            FILE_SHARE_WRITE = 0x00000002
            FILE_SHARE_DELETE = 0x00000004
            OPEN_EXISTING = 3
            FILE_ATTRIBUTE_NORMAL = 0x80
            INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
            CreateFileW = ctypes.windll.kernel32.CreateFileW
            CreateFileW.restype = ctypes.c_void_p
            handle = CreateFileW(
                str(file_path),
                GENERIC_READ,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                None,
                OPEN_EXISTING,
                FILE_ATTRIBUTE_NORMAL,
                None,
            )
            if handle is None or handle == INVALID_HANDLE_VALUE or handle == -1:
                raise OSError("CreateFile non riuscita")
            try:
                GetFileSizeEx = ctypes.windll.kernel32.GetFileSizeEx
                size = ctypes.c_longlong(0)
                if not GetFileSizeEx(ctypes.c_void_p(handle), ctypes.byref(size)):
                    raise OSError("GetFileSizeEx fallita")
                buf = ctypes.create_string_buffer(size.value)
                read = ctypes.c_ulong(0)
                if not ctypes.windll.kernel32.ReadFile(
                    ctypes.c_void_p(handle), buf, size.value, ctypes.byref(read), None
                ):
                    raise OSError("ReadFile fallita")
                return buf.raw[: read.value]
            finally:
                ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(handle))
        except Exception:
            pass
    with open(file_path, "rb") as f:
        return f.read()


def message_date_timestamp(msg, fallback=0):
    """Timestamp dall'header Date del messaggio (per ordinare i feed dal più recente)."""
    raw = None
    try:
        raw = msg.get("Date") or msg.get("date")
    except Exception:
        raw = None
    if raw:
        try:
            dt = parsedate_to_datetime(str(raw))
            if dt is not None:
                if getattr(dt, "tzinfo", None) is None:
                    return dt.timestamp()
                return dt.timestamp()
        except Exception:
            pass
    return fallback


def format_email_date_label(msg, fallback_ts=0):
    """Data breve dd/mm/yyyy dall'header Date (come nei risultati Feed)."""
    ts = message_date_timestamp(msg, fallback=fallback_ts or 0)
    if not ts:
        return ""
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%d/%m/%Y")
    except Exception:
        return ""


def _format_email_viewer_text(msg):
    subject = decode_email_header(msg.get("subject", "(Nessun oggetto)"))
    sender = decode_email_header(msg.get("from", "(Sconosciuto)"))
    to = decode_email_header(msg.get("to", "(Sconosciuto)"))
    date = msg.get("date", "(Nessuna data)")
    body = get_clean_email_text(msg)
    full_text = (
        f"Oggetto: {subject}\n"
        f"Da: {sender}\n"
        f"A: {to}\n"
        f"Data: {date}\n"
        f"{'-'*60}\n\n"
        f"{body}"
    )
    return full_text.replace("\r\n", "\n").replace("\n", "\r\n")


def _find_query_in_viewer_text(full_text, search_query):
    if not search_query or not full_text:
        return -1, 0
    terms = search_query.split()
    text_lower = full_text.lower()
    for term in terms:
        t = term.lower()
        idx = text_lower.find(t)
        if idx != -1:
            return idx, len(t)
    text_norm = normalize_search_text(full_text, True)
    for term in normalize_search_text(search_query, True).split():
        idx = text_norm.find(term)
        if idx != -1:
            return idx, len(term)
    return -1, 0


def load_mbox_message_by_index(file_path, msg_index, should_abort=None, on_progress=None):
    """Carica UN solo messaggio MBOX per indice senza caricare tutta la casella in RAM.

    Nota: in NVDA non c'è il modulo mailbox; scorre le righe From_ in streaming.
    """
    if msg_index is None or msg_index < 0:
        raise IndexError("Indice messaggio non valido")

    def _open():
        if sys.platform.startswith("win"):
            try:
                import msvcrt
                GENERIC_READ = 0x80000000
                FILE_SHARE_READ = 0x00000001
                FILE_SHARE_WRITE = 0x00000002
                FILE_SHARE_DELETE = 0x00000004
                OPEN_EXISTING = 3
                FILE_ATTRIBUTE_NORMAL = 0x80
                INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
                CreateFileW = ctypes.windll.kernel32.CreateFileW
                CreateFileW.restype = ctypes.c_void_p
                handle = CreateFileW(
                    str(file_path),
                    GENERIC_READ,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                    None,
                    OPEN_EXISTING,
                    FILE_ATTRIBUTE_NORMAL,
                    None,
                )
                if handle is None or handle == INVALID_HANDLE_VALUE or handle == -1:
                    raise OSError("CreateFile non riuscita")
                fd = msvcrt.open_osfhandle(int(handle), os.O_RDONLY)
                return os.fdopen(fd, "rb")
            except Exception:
                pass
        return open(file_path, "rb")

    def _parse(raw):
        if not raw:
            raise ValueError("Messaggio MBOX vuoto")
        if raw.startswith(b"From "):
            nl = raw.find(b"\n")
            if nl != -1:
                raw = raw[nl + 1 :]
        try:
            return email.message_from_bytes(raw, policy=policy.default)
        except Exception:
            return email.message_from_bytes(raw)

    current = -1
    start_pos = None
    f = _open()
    try:
        while True:
            if should_abort and should_abort():
                raise InterruptedError("Caricamento interrotto")
            line_start = f.tell()
            line = f.readline()
            if not line:
                break
            if line.startswith(b"From "):
                if current == msg_index:
                    end_pos = line_start
                    f.seek(start_pos)
                    return _parse(f.read(end_pos - start_pos))
                current += 1
                if current == msg_index:
                    start_pos = line_start
                if on_progress and current > 0 and current % 25000 == 0:
                    try:
                        on_progress(current)
                    except Exception:
                        pass
        if start_pos is None:
            raise IndexError(
                f"Messaggio {msg_index} non trovato (trovati {current + 1} messaggi)"
            )
        f.seek(start_pos)
        return _parse(f.read())
    finally:
        try:
            f.close()
        except Exception:
            pass


def extract_article_url_from_message(msg, body_text=""):
    for header in ("Content-Base", "Content-Location", "content-base", "content-location"):
        val = msg.get(header)
        if val:
            val = str(val).strip().strip("<>").strip()
            if val.startswith("http://") or val.startswith("https://"):
                return val
    raw_headers = ""
    try:
        raw_headers = str(msg)
    except Exception:
        pass
    m = re.search(r'base\s+href=["\'](https?://[^"\']+)["\']', raw_headers, re.IGNORECASE)
    if m:
        return m.group(1)
    search_blob = (body_text or "") + "\n" + raw_headers
    candidates = re.findall(r"https?://[^\s<>\"']+", search_blob)
    preferred = []
    others = []
    for c in candidates:
        url = c.rstrip(").,;]")
        low = url.lower()
        if any(x in low for x in ("facebook.com", "twitter.com", "instagram.com", "mailto:", "javascript:")):
            continue
        if "/news/" in low or "tuttosport.com/news" in low or re.search(r"/\d{4}/\d{2}/", low):
            preferred.append(url)
        else:
            others.append(url)
    if preferred:
        return preferred[0]
    if others:
        return others[0]
    return ""


def _parse_messages_from_bytes(data):
    """Split mbox-like bytes on From_ lines and yield (index, message)."""
    if not data:
        return
    parts = re.split(br"(?m)^From ", data)
    idx = 0
    for i, part in enumerate(parts):
        chunk = part if i == 0 else (b"From " + part)
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            msg = email.message_from_bytes(chunk, policy=policy.default)
        except Exception:
            try:
                msg = email.message_from_bytes(chunk)
            except Exception:
                continue
        if not msg.get("subject") and not msg.get("from") and not msg.get_payload():
            continue
        yield idx, msg
        idx += 1


def iter_mbox_like_messages(file_path, prefer_from_split=False):
    """Yield (index, email.message) splitting on From_ lines.

    Nota: il modulo stdlib ``mailbox`` NON è disponibile in NVDA, quindi
    usiamo solo il parser nativo basato su From_.
    """
    data = None
    try:
        data = read_file_bytes_shared(file_path)
    except Exception:
        pass
    if not data:
        return
    # prefer_from_split è mantenuto per compatibilità API; in NVDA è sempre From-split
    for item in _parse_messages_from_bytes(data):
        yield item


def _match_message_to_result(file_path, file_name, msg, msg_idx, terms, mtime, prefix="[FEED]"):
    subject = decode_email_header(str(msg.get("subject", "")))
    sender = decode_email_header(str(msg.get("from", "")))
    body = get_clean_email_text(msg)
    haystack = f"{subject}\n{sender}\n{body}"
    if not text_matches_terms(haystack, terms):
        return None
    snippet = ""
    if body:
        for line in body.split("\n"):
            if text_matches_terms(line, terms):
                snippet = line.strip()
                break
        if not snippet:
            snippet = " ".join(body.split())[:200]
    if not snippet:
        snippet = f"{subject} — {sender}".strip(" —")
    if len(snippet) > 200:
        snippet = snippet[:200] + "..."
    article_url = extract_article_url_from_message(msg, body)
    display = subject[:60] + ("..." if len(subject) > 60 else "") if subject else file_name
    article_ts = message_date_timestamp(msg, fallback=mtime or 0)
    date_label = format_email_date_label(msg, fallback_ts=mtime or 0)
    loc = "Articolo Feed"
    if date_label:
        loc = f"Articolo Feed {date_label}"
    return {
        "file_path": file_path,
        "file_name": display or file_name,
        "prefix": prefix,
        "mtime": article_ts if article_ts else (mtime or 0),
        "line_number": msg_idx,
        "paragraph_index": None,
        "location_info": loc,
        "snippet": snippet,
        "article_url": article_url,
        "viewer_text": _format_email_viewer_text(msg),
    }


def count_raw_term_occurrences(file_path, terms):
    """Conta quante volte i termini compaiono nel file grezzo (stile Notepad++)."""
    if not terms:
        return 0
    try:
        raw = read_file_bytes_shared(file_path)
    except Exception:
        return 0
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16", errors="ignore")
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin1", errors="ignore")
    text = text.replace("\x00", "")
    norm = normalize_search_text(text, False)
    if len(terms) == 1:
        term = terms[0]
        if not term:
            return 0
        count = 0
        start = 0
        while True:
            pos = norm.find(term, start)
            if pos < 0:
                break
            count += 1
            start = pos + max(1, len(term))
        if count:
            return count
        norm2 = normalize_search_text(text, True)
        term2 = normalize_search_text(terms[0], True)
        count = 0
        start = 0
        while term2:
            pos = norm2.find(term2, start)
            if pos < 0:
                break
            count += 1
            start = pos + max(1, len(term2))
        return count
    lines = text.splitlines()
    return sum(1 for line in lines if text_matches_terms(line, terms))


def search_thunderbird_feed_file(file_path, terms, mtime, include_raw_lines=False):
    """Search Thunderbird Feeds file: one result per matching message (cleaned text)."""
    results = []
    if is_thunderbird_junk_file(file_path):
        return results, 0
    file_name = os.path.basename(file_path)
    parsed_any = False
    raw_occurrences = count_raw_term_occurrences(file_path, terms)
    try:
        for msg_idx, msg in iter_mbox_like_messages(file_path, prefer_from_split=True):
            parsed_any = True
            hit = _match_message_to_result(file_path, file_name, msg, msg_idx, terms, mtime)
            if hit:
                hit["raw_occurrences_in_file"] = raw_occurrences
                results.append(hit)
    except Exception:
        parsed_any = False

    if include_raw_lines:
        try:
            raw = read_file_bytes_shared(file_path)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin1", errors="ignore")
            lines = text.replace("\x00", "").splitlines()
            max_lines = min(len(lines), 20000)
            added = 0
            max_raw_results = 500
            for idx in range(max_lines):
                if added >= max_raw_results:
                    break
                line = lines[idx]
                if not text_matches_terms(line, terms):
                    continue
                snippet = strip_html_to_text(line)
                snippet = " ".join(snippet.split())
                if not snippet:
                    continue
                results.append({
                    "file_path": file_path,
                    "file_name": file_name,
                    "prefix": "[FEED-RIGA]",
                    "mtime": mtime or 0,
                    "line_number": idx + 1,
                    "paragraph_index": None,
                    "location_info": f"Riga grezza {idx + 1}",
                    "snippet": snippet[:200] + ("..." if len(snippet) > 200 else ""),
                    "article_url": "",
                })
                added += 1
        except Exception:
            pass

    if parsed_any or results:
        return results, raw_occurrences

    try:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            with open(file_path, "r", encoding="latin1", errors="ignore") as f:
                lines = f.readlines()
        max_lines = min(len(lines), 5000)
        for idx in range(max_lines):
            line = lines[idx]
            if not text_matches_terms(line, terms):
                continue
            start_i = max(0, idx - 2)
            end_i = min(len(lines), idx + 3)
            snippet = " ".join([l.strip() for l in lines[start_i:end_i]]).strip()
            snippet = strip_html_to_text(snippet)
            snippet = " ".join(snippet.split())
            article_url = ""
            for j in range(idx, max(-1, idx - 30), -1):
                match_base = re.search(r'base\s+href=["\'](https?://[^"\']+)["\']', lines[j], re.IGNORECASE)
                if match_base:
                    article_url = match_base.group(1)
                    break
            if not article_url:
                mlink = re.search(r"https?://[^\s<>\"']+", snippet)
                if mlink:
                    article_url = mlink.group(0)
            results.append({
                "file_path": file_path,
                "file_name": file_name,
                "prefix": "[FEED]",
                "mtime": mtime,
                "line_number": idx + 1,
                "paragraph_index": None,
                "location_info": "Articolo Feed",
                "snippet": snippet[:200] + ("..." if len(snippet) > 200 else ""),
                "article_url": article_url,
                "raw_occurrences_in_file": raw_occurrences,
            })
            break
    except Exception:
        pass
    return results, raw_occurrences


def check_first_run_update():
    try:
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        last_v = data.get("last_version", "")
        if last_v != APP_VERSION:
            data["last_version"] = APP_VERSION
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return True
    except Exception:
        pass
    return False

def load_last_path():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                path = data.get("last_path", "")
                if path:
                    first = re.split(r"[;,]", path)[0].strip()
                    if first.startswith("http://") or first.startswith("https://"):
                        return path
                    if os.path.exists(first):
                        return path
    except Exception:
        pass
    return os.path.expanduser("~\\Downloads")

def save_last_path(path):
    try:
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["last_path"] = path
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def load_bookmarks():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("bookmarks", [])
    except Exception:
        pass
    return []

def save_bookmarks(bookmarks_list):
    try:
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["bookmarks"] = bookmarks_list
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

HISTORY_MAX = 20


def _load_settings_dict():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _save_settings_dict(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def load_query_history():
    hist = _load_settings_dict().get("query_history", [])
    return [x for x in hist if isinstance(x, str) and x.strip()]


def load_path_history():
    hist = _load_settings_dict().get("path_history", [])
    return [x for x in hist if isinstance(x, str) and x.strip()]


VALID_SORT_TYPES = ("recent_first", "oldest_first", "name")


def load_sort_preference():
    raw = _load_settings_dict().get("results_sort", "recent_first")
    return raw if raw in VALID_SORT_TYPES else "recent_first"


def save_sort_preference(sort_type):
    if sort_type not in VALID_SORT_TYPES:
        return
    data = _load_settings_dict()
    data["results_sort"] = sort_type
    _save_settings_dict(data)


def _push_history_item(key, value, max_items=HISTORY_MAX):
    value = (value or "").strip()
    if not value:
        return
    data = _load_settings_dict()
    hist = [x for x in data.get(key, []) if isinstance(x, str) and x.strip()]
    hist = [x for x in hist if x.casefold() != value.casefold()]
    hist.insert(0, value)
    data[key] = hist[:max_items]
    _save_settings_dict(data)


def add_query_to_history(query):
    _push_history_item("query_history", query)


def add_path_to_history(path):
    _push_history_item("path_history", path)


def clear_query_history():
    data = _load_settings_dict()
    data["query_history"] = []
    _save_settings_dict(data)


def clear_path_history():
    data = _load_settings_dict()
    data["path_history"] = []
    _save_settings_dict(data)


def get_dynamic_desktop_path():
    desktop_path = os.path.expanduser("~\\Desktop")
    if not os.path.exists(desktop_path):
        desktop_path = os.path.expanduser("~\\OneDrive\\Desktop")
        if not os.path.exists(desktop_path):
            desktop_path = os.path.expanduser("~")
    return desktop_path

def get_real_ready_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if bitmask & 1:
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                try:
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    if drive_type in (2, 3):  
                        os.listdir(drive_path)
                        drives.append(drive_path)
                except Exception:
                    pass
        bitmask >>= 1
    return drives

def extract_paragraphs_from_docx(file_path):
    try:
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            paragraphs = []
            for p in tree.iter():
                if p.tag.endswith("p"):
                    p_text = "".join(
                        [elem.text for elem in p.iter() if elem.tag.endswith("t") and elem.text]
                    )
                    if p_text.strip():
                        paragraphs.append(p_text.strip())
            return paragraphs
    except Exception:
        return []

PDF_READ_MAX_BYTES = 20 * 1024 * 1024

# Marcatori tipici di stream immagine / struttura PDF (non testo leggibile)
_PDF_IMAGE_MARKERS = (
    b"/Subtype/Image",
    b"/Subtype /Image",
    b"/Image/Height",
    b"/BitsPerComponent",
    b"/ColorSpace/DeviceRGB",
    b"/ColorSpace /DeviceRGB",
    b"/ColorSpace/DeviceGray",
)
_PDF_STRUCT_NOISE = re.compile(
    r"(endstream|endobj|startxref|/Type\s*/XObject|/Filter\s*/FlateDecode|"
    r"/ColorSpace|/BitsPerComponent|/Subtype\s*/Image|DeviceRGB|DeviceGray)",
    re.IGNORECASE,
)
# Evita inflate lunghi SOLO se ancora sospetti; i content stream utili possono superare 512KB
_PDF_INFLATE_MAX = 512 * 1024
_PDF_CONTENT_INFLATE_MAX = 8 * 1024 * 1024
_PDF_FILTER_FLATE = re.compile(
    br"/Filter\s*(?:/\s*(?:FlateDecode|Fl)\b|\[\s*/\s*(?:FlateDecode|Fl)\b)"
)
_PDF_FILTER_DCT = re.compile(
    br"/Filter\s*(?:/\s*(?:DCTDecode|DCT)\b|\[\s*/\s*(?:DCTDecode|DCT)\b)"
)


def _pdf_dict_has_flate(dict_blob):
    return bool(dict_blob and _PDF_FILTER_FLATE.search(dict_blob))


def _pdf_dict_has_dct(dict_blob):
    return bool(dict_blob and _PDF_FILTER_DCT.search(dict_blob))


def _pdf_dict_is_image(dict_blob):
    if not dict_blob:
        return False
    if b"/Subtype" in dict_blob and b"/Image" in dict_blob:
        return True
    if any(m in dict_blob for m in _PDF_IMAGE_MARKERS):
        return True
    # Width+Height senza Font/Resources → quasi certamente immagine
    has_wh = (b"/Width" in dict_blob or b"/W " in dict_blob) and (
        b"/Height" in dict_blob or b"/H " in dict_blob
    )
    if has_wh and b"/Font" not in dict_blob and b"/Resources" not in dict_blob:
        return True
    return False


def _pdf_bytes_look_like_content(data):
    """True se lo stream sembra contenuto di pagina (operatori testo), non binario grezzo."""
    if not data or len(data) < 4:
        return False
    # troppi null / byte alti → probabilmente immagine decompressa
    sample = data[:8000]
    nul = sample.count(b"\x00")
    if nul > len(sample) // 10:
        return False
    return (
        (b"Tj" in data)
        or (b"TJ" in data)
        or (b"BT" in data)
        or (b"Tm" in data and b"(" in data)
        or (b"'" in data and b"(" in data)
    )


def extract_lines_from_pdf(file_path):
    """Estrae righe di testo da un PDF senza librerie esterne.

    Decomprime solo stream di contenuto (non Image XObject), poi legge Tj/TJ.
    I PDF solo-immagine restituiscono lista vuota (niente spazzatura endstream/Image).
    """
    try:
        with open(file_path, "rb") as f:
            raw = f.read(PDF_READ_MAX_BYTES)
    except Exception:
        return []

    if not raw.startswith(b"%PDF"):
        return _pdf_fallback_crude_lines(raw)

    cmap = _pdf_parse_tounicode_cmaps(raw)

    pieces = []
    pos = 0
    while True:
        m = re.search(br"stream\r?\n", raw[pos:])
        if not m:
            break
        start = pos + m.end()
        end = raw.find(b"endstream", start)
        if end < 0:
            break
        stream = raw[start:end]
        if stream.endswith(b"\r\n"):
            stream = stream[:-2]
        elif stream.endswith(b"\n") or stream.endswith(b"\r"):
            stream = stream[:-1]

        dict_start = raw.rfind(b"<<", max(pos, start - 1600), start)
        dict_blob = raw[dict_start:start] if dict_start != -1 else b""

        # Non decomprimere / interpretare stream immagine (lenti e producono spazzatura)
        if _pdf_dict_is_image(dict_blob):
            pos = end + 9
            continue

        is_flate = _pdf_dict_has_flate(dict_blob)
        if is_flate:
            # Content stream di tabellini densissimi possono superare 512KB: ok gonfiarli
            if len(stream) > _PDF_CONTENT_INFLATE_MAX:
                pos = end + 9
                continue
            data = _pdf_inflate_stream(stream)
        else:
            data = stream
            if (
                not _pdf_bytes_look_like_content(data)
                and len(stream) <= _PDF_CONTENT_INFLATE_MAX
            ):
                inflated = _pdf_inflate_stream(stream)
                if _pdf_bytes_look_like_content(inflated):
                    data = inflated

        if _pdf_bytes_look_like_content(data):
            pieces.extend(_pdf_text_from_content_stream(data, cmap))
        pos = end + 9

    blob = " ".join(pieces)
    blob = blob.replace("\r\n", "\n").replace("\r", "\n")
    # toglie byte di controllo lasciati da CID non mappati
    blob = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", blob)
    lines = []
    for part in blob.split("\n"):
        part = re.sub(r"[ \t]+", " ", part).strip()
        if not part or _pdf_looks_like_garbage(part):
            continue
        if len(part) <= 240:
            lines.append(part)
        else:
            while part:
                if len(part) <= 240:
                    lines.append(part)
                    break
                cut = part.rfind(" ", 0, 240)
                if cut < 40:
                    cut = 240
                lines.append(part[:cut].strip())
                part = part[cut:].strip()

    return lines


def _pdf_unescape_literal_bytes(raw):
    """Unescape PDF literal string → bytes grezzi (prima della decodifica testo)."""
    out = bytearray()
    i = 0
    n = len(raw)
    while i < n:
        b = raw[i]
        if b == 0x5C and i + 1 < n:
            nxt = raw[i + 1]
            if nxt == 0x6E:
                out.append(0x0A)
                i += 2
            elif nxt == 0x72:
                out.append(0x0D)
                i += 2
            elif nxt == 0x74:
                out.append(0x09)
                i += 2
            elif nxt == 0x62:
                out.append(0x08)
                i += 2
            elif nxt == 0x66:
                out.append(0x0C)  # \f form-feed: spesso CID per '('
                i += 2
            elif nxt in (0x28, 0x29, 0x5C):
                out.append(nxt)
                i += 2
            elif 0x30 <= nxt <= 0x37:
                j = i + 1
                octal = bytearray()
                while j < n and len(octal) < 3 and 0x30 <= raw[j] <= 0x37:
                    octal.append(raw[j])
                    j += 1
                try:
                    out.append(int(octal.decode("ascii"), 8) & 0xFF)
                except Exception:
                    pass
                i = j
            else:
                out.append(nxt)
                i += 2
        else:
            out.append(b)
            i += 1
    return bytes(out)


def _pdf_unescape_literal(raw):
    out = _pdf_unescape_literal_bytes(raw)
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return out.decode("latin1", errors="ignore")


def _pdf_utf16_hex_to_str(hx):
    cleaned = re.sub(br"[^0-9A-Fa-f]", b"", hx)
    if len(cleaned) % 2:
        cleaned = cleaned[:-1]
    if not cleaned:
        return ""
    try:
        data = bytes.fromhex(cleaned.decode("ascii"))
    except Exception:
        return ""
    if len(data) >= 2:
        try:
            return data.decode("utf-16-be")
        except Exception:
            pass
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin1", errors="ignore")


def _pdf_parse_tounicode_cmaps(raw):
    """Unisce tutte le CMap ToUnicode del PDF: codice CID (int) → carattere."""
    merged = {}
    pos = 0
    while True:
        m = re.search(br"stream\r?\n", raw[pos:])
        if not m:
            break
        start = pos + m.end()
        end = raw.find(b"endstream", start)
        if end < 0:
            break
        stream = raw[start:end]
        if stream.endswith(b"\r\n"):
            stream = stream[:-2]
        elif stream.endswith(b"\n") or stream.endswith(b"\r"):
            stream = stream[:-1]
        dict_start = raw.rfind(b"<<", max(pos, start - 1600), start)
        dict_blob = raw[dict_start:start] if dict_start != -1 else b""
        pos = end + 9
        if _pdf_dict_is_image(dict_blob):
            continue
        if _pdf_dict_has_flate(dict_blob):
            if len(stream) > _PDF_CONTENT_INFLATE_MAX:
                continue
            data = _pdf_inflate_stream(stream)
        else:
            data = stream
            inflated = _pdf_inflate_stream(stream)
            if b"beginbfchar" in inflated or b"beginbfrange" in inflated:
                data = inflated
        if b"beginbfchar" not in data and b"beginbfrange" not in data:
            continue
        cmap = {}
        for sm in re.finditer(br"[0-9]+\s+beginbfchar(.*?)endbfchar", data, flags=re.S):
            for src, dst in re.findall(
                br"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", sm.group(1)
            ):
                try:
                    cmap[int(src, 16)] = _pdf_utf16_hex_to_str(dst)
                except Exception:
                    continue
        for sm in re.finditer(br"[0-9]+\s+beginbfrange(.*?)endbfrange", data, flags=re.S):
            body = sm.group(1)
            for a, b, arr in re.findall(
                br"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", body, flags=re.S
            ):
                try:
                    start_c, end_c = int(a, 16), int(b, 16)
                except Exception:
                    continue
                dests = re.findall(br"<([0-9A-Fa-f]+)>", arr)
                for i, code in enumerate(range(start_c, end_c + 1)):
                    if i < len(dests):
                        cmap[code] = _pdf_utf16_hex_to_str(dests[i])
            for a, b, dst in re.findall(
                br"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", body
            ):
                try:
                    start_c, end_c = int(a, 16), int(b, 16)
                    base = int(dst, 16)
                    nbytes = max(1, len(dst) // 2)
                except Exception:
                    continue
                for i, code in enumerate(range(start_c, end_c + 1)):
                    hx = f"{base + i:0{nbytes * 2}X}".encode("ascii")
                    cmap[code] = _pdf_utf16_hex_to_str(hx)
        merged.update(cmap)
    return merged


def _pdf_decode_cid_bytes(data, cmap):
    """Decodifica stringa a 2 byte (Identity-H / CID) con ToUnicode."""
    if not data:
        return ""
    if len(data) % 2 == 1:
        data = data[1:]
    chars = []
    for i in range(0, len(data) - 1, 2):
        code = (data[i] << 8) | data[i + 1]
        ch = cmap.get(code)
        if ch:
            chars.append(ch)
        elif data[i] == 0 and 32 <= data[i + 1] < 127:
            chars.append(chr(data[i + 1]))
    return "".join(chars)


def _pdf_looks_like_cid_bytes(data):
    if not data or len(data) < 2:
        return False
    sample = data[: min(len(data), 200)]
    if len(sample) < 2:
        return False
    nulls = sample.count(b"\x00")
    return nulls >= max(1, len(sample) // 4)


def _pdf_bytes_to_text(data, cmap):
    if not data:
        return ""
    if cmap and (_pdf_looks_like_cid_bytes(data) or (len(data) % 2 == 0 and len(data) >= 2)):
        # Preferisci CID se c'è CMap e lunghezza pari (tipico Identity-H)
        if _pdf_looks_like_cid_bytes(data) or (cmap and len(data) % 2 == 0 and b"\x00" in data):
            mapped = _pdf_decode_cid_bytes(data, cmap)
            if mapped.strip():
                return mapped
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin1", errors="ignore")


def _pdf_hex_to_str(hex_body, cmap=None):
    cleaned = re.sub(br"[^0-9A-Fa-f]", b"", hex_body)
    if len(cleaned) % 2:
        cleaned = cleaned[:-1]
    if not cleaned:
        return ""
    try:
        data = bytes.fromhex(cleaned.decode("ascii"))
    except Exception:
        return ""
    if cmap:
        # Codici a 2 byte tipici: <0030><0044>...
        if len(cleaned) % 4 == 0 or _pdf_looks_like_cid_bytes(data):
            mapped = _pdf_decode_cid_bytes(data, cmap)
            if mapped.strip():
                return mapped
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin1", errors="ignore")


def _pdf_text_from_content_stream(data, cmap=None):
    if cmap is None:
        cmap = {}
    pieces = []
    for m in re.finditer(br"\((?:\\.|[^\\()])*\)\s*(?:Tj|'|\")", data):
        lit = re.sub(br"\s*(?:Tj|'|\")\s*$", b"", m.group(0))
        if lit.startswith(b"(") and lit.endswith(b")"):
            raw_bytes = _pdf_unescape_literal_bytes(lit[1:-1])
            pieces.append(_pdf_bytes_to_text(raw_bytes, cmap))
    for m in re.finditer(br"<([0-9A-Fa-f\s]+)>\s*Tj", data):
        pieces.append(_pdf_hex_to_str(m.group(1), cmap))
    for m in re.finditer(br"\[(.*?)\]\s*TJ", data, flags=re.DOTALL):
        arr = m.group(1)
        parts = []
        for sm in re.finditer(br"\((?:\\.|[^\\()])*\)|<([0-9A-Fa-f\s]+)>", arr):
            if sm.group(0).startswith(b"("):
                raw_bytes = _pdf_unescape_literal_bytes(sm.group(0)[1:-1])
                parts.append(_pdf_bytes_to_text(raw_bytes, cmap))
            else:
                parts.append(_pdf_hex_to_str(sm.group(1) or b"", cmap))
        if parts:
            pieces.append("".join(parts))
    return [p for p in pieces if p]


def _pdf_looks_like_garbage(line: str):
    s = line.strip()
    if len(s) < 2:
        return True
    if _PDF_STRUCT_NOISE.search(s):
        return True
    if re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        s,
    ):
        return True
    if re.fullmatch(r"D:\d{8,}.*", s):
        return True
    if s in ("True", "False", "Standard", "it", "en", "Identity", "stream", "obj"):
        return True
    # poca lettera/cifra rispetto alla lunghezza → binario/simboli
    alnum = sum(1 for c in s if c.isalnum() or c.isspace())
    if alnum < max(3, len(s) // 2):
        return True
    bad = sum(1 for c in s if ord(c) < 9 or c in "\x00\ufffdþÿÎÔ")
    if bad and bad >= max(1, len(s) // 5):
        return True
    return False


def _pdf_inflate_stream(stream: bytes):
    for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
        try:
            return zlib.decompress(stream, wbits)
        except Exception:
            continue
    return stream


def _pdf_fallback_crude_lines(raw):
    """Ultimo tentativo su file non-PDF o senza stream riconoscibili; molto selettivo."""
    try:
        content = raw.decode("latin1", errors="ignore")
    except Exception:
        return []
    matches = re.findall(r"\((?:\\.|[^\\()])*\)", content)
    lines = []
    for m in matches:
        inner = m[1:-1]
        try:
            text = _pdf_unescape_literal(inner.encode("latin1", errors="ignore"))
        except Exception:
            text = inner
        text = re.sub(r"[ \t]+", " ", text).strip()
        if text and not _pdf_looks_like_garbage(text) and len(text) >= 4:
            if text.isdigit() and len(text) < 6:
                continue
            # evita frammenti PDF tecnici corti
            if text.startswith("/") or text.endswith("obj"):
                continue
            lines.append(text)
    return lines[:200]


# Inflate consentito solo su richiesta esplicita «Copia immagine» (non in ricerca)
_PDF_IMAGE_INFLATE_MAX = 15 * 1024 * 1024
_PDF_IMAGE_MIN_SIDE = 48
_PDF_IMAGE_MIN_AREA = 80 * 80
# Sotto questa soglia = logo/icona, non «pagina» da copiare (es. stemma 324×324)
_PDF_PAGE_IMAGE_MIN_SIDE = 400
_PDF_PAGE_IMAGE_MIN_AREA = 400 * 400


def _pdf_dict_int(dict_blob, *keys):
    for key in keys:
        m = re.search(re.escape(key) + br"\s+(\d+)", dict_blob)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                continue
    return 0


def _pdf_image_colorspace(dict_blob):
    if (
        b"DeviceGray" in dict_blob
        or b"/CS/G" in dict_blob
        or b"/ColorSpace/G" in dict_blob
    ):
        return "gray"
    if b"DeviceCMYK" in dict_blob:
        return "cmyk"
    if b"DeviceRGB" in dict_blob or b"/CS/RGB" in dict_blob:
        return "rgb"
    if b"/ICCBased" in dict_blob:
        return "rgb"
    return "rgb"


def _pdf_image_filter(dict_blob):
    if _pdf_dict_has_dct(dict_blob):
        return "jpeg"
    if b"/JPXDecode" in dict_blob:
        return "jpx"
    if _pdf_dict_has_flate(dict_blob):
        return "flate"
    if b"/CCITTFaxDecode" in dict_blob:
        return "ccitt"
    return "raw"


def _pdf_gray_to_rgb(data, width, height):
    need = width * height
    if len(data) < need:
        return b""
    out = bytearray(need * 3)
    src = memoryview(data[:need])
    j = 0
    for i in range(need):
        v = src[i]
        out[j] = v
        out[j + 1] = v
        out[j + 2] = v
        j += 3
    return bytes(out)


def _pdf_rgb_is_nearly_flat(data):
    """True se l'immagine è quasi monocromatica (cerchio bianco, maschera, ecc.)."""
    if not data or len(data) < 30:
        return True
    step = max(3, (len(data) // 4000) * 3)
    sample = data[::step][:2000]
    if not sample:
        return True
    return len(set(sample)) < 8


def extract_images_from_pdf(file_path):
    """Elenco immagini XObject estraibili: dict w/h/kind/data (kind: jpeg|rgb).

    Usato solo da «Copia immagine», non dalla ricerca testo.
    """
    try:
        with open(file_path, "rb") as f:
            raw = f.read(PDF_READ_MAX_BYTES)
    except Exception:
        return []

    if not raw.startswith(b"%PDF"):
        return []

    found = []
    pos = 0
    while True:
        m = re.search(br"stream\r?\n", raw[pos:])
        if not m:
            break
        start = pos + m.end()
        end = raw.find(b"endstream", start)
        if end < 0:
            break
        stream = raw[start:end]
        if stream.endswith(b"\r\n"):
            stream = stream[:-2]
        elif stream.endswith(b"\n") or stream.endswith(b"\r"):
            stream = stream[:-1]

        dict_start = raw.rfind(b"<<", max(pos, start - 1600), start)
        dict_blob = raw[dict_start:start] if dict_start != -1 else b""
        pos = end + 9

        if not _pdf_dict_is_image(dict_blob):
            continue
        # Maschere mono: non sono la pagina del tabellino
        if b"/ImageMask" in dict_blob:
            continue

        width = _pdf_dict_int(dict_blob, b"/Width", b"/W")
        height = _pdf_dict_int(dict_blob, b"/Height", b"/H")
        if width < _PDF_IMAGE_MIN_SIDE or height < _PDF_IMAGE_MIN_SIDE:
            continue
        if width * height < _PDF_IMAGE_MIN_AREA:
            continue

        bpc = _pdf_dict_int(dict_blob, b"/BitsPerComponent") or 8
        if bpc != 8:
            continue

        filt = _pdf_image_filter(dict_blob)
        colorspace = _pdf_image_colorspace(dict_blob)
        if filt == "jpx" or filt == "ccitt" or colorspace == "cmyk":
            continue

        if filt == "jpeg":
            if not stream.startswith(b"\xff\xd8"):
                soi = stream.find(b"\xff\xd8")
                if soi < 0:
                    continue
                stream = stream[soi:]
            found.append(
                {"w": width, "h": height, "kind": "jpeg", "data": stream}
            )
            continue

        if filt in ("flate", "raw"):
            if len(stream) > _PDF_IMAGE_INFLATE_MAX:
                continue
            data = _pdf_inflate_stream(stream) if filt == "flate" else stream
            if colorspace == "gray":
                rgb = _pdf_gray_to_rgb(data, width, height)
                if not rgb or _pdf_rgb_is_nearly_flat(rgb):
                    continue
                found.append({"w": width, "h": height, "kind": "rgb", "data": rgb})
            else:
                need = width * height * 3
                if len(data) < need:
                    continue
                rgb = data[:need]
                if _pdf_rgb_is_nearly_flat(rgb):
                    continue
                found.append({"w": width, "h": height, "kind": "rgb", "data": rgb})

    found.sort(key=lambda im: im["w"] * im["h"], reverse=True)
    return found


def get_largest_pdf_image(file_path):
    """Compat: prima immagine per area (anche logo). Preferire get_best_pdf_page_image."""
    images = extract_images_from_pdf(file_path)
    return images[0] if images else None


def get_best_pdf_page_image(file_path):
    """Immagine di pagina (non logo/icona). None se ci sono solo stemmi piccoli."""
    images = extract_images_from_pdf(file_path)
    for im in images:
        if (
            im["w"] >= _PDF_PAGE_IMAGE_MIN_SIDE
            and im["h"] >= _PDF_PAGE_IMAGE_MIN_SIDE
            and im["w"] * im["h"] >= _PDF_PAGE_IMAGE_MIN_AREA
        ):
            return im
    return None


# Lato max per gli appunti (scansioni ScanSnap enormi altrimenti falliscono)
_PDF_CLIPBOARD_MAX_SIDE = 1800


def pdf_image_record_to_wx_image(record, fit_for_clipboard=True):
    """Converte un record di extract_images_from_pdf in wx.Image, o None."""
    if not record:
        return None
    img = None
    try:
        if record["kind"] == "jpeg":
            try:
                stream = wx.MemoryInputStream(record["data"], len(record["data"]))
                img = wx.Image(stream, wx.BITMAP_TYPE_JPEG)
            except Exception:
                img = None
            if img is None or not img.IsOk():
                # Fallback: JPEG grandi / wx capriccioso → file temporaneo
                tmp = None
                try:
                    fd, tmp = tempfile.mkstemp(suffix=".jpg")
                    os.write(fd, record["data"])
                    os.close(fd)
                    img = wx.Image(tmp, wx.BITMAP_TYPE_JPEG)
                    if not img.IsOk():
                        img = wx.Image(tmp, wx.BITMAP_TYPE_ANY)
                finally:
                    if tmp:
                        try:
                            os.unlink(tmp)
                        except Exception:
                            pass
        elif record["kind"] == "rgb":
            img = wx.Image(record["w"], record["h"], record["data"])
        if img is not None and img.IsOk():
            if fit_for_clipboard:
                return _wx_image_fit_for_clipboard(img)
            return img
    except Exception:
        pass
    return None


def _wx_image_fit_for_clipboard(img):
    """Riduce immagini enormi così gli appunti/Windows non falliscono."""
    try:
        w, h = img.GetWidth(), img.GetHeight()
        side = max(w, h)
        if side <= _PDF_CLIPBOARD_MAX_SIDE or side <= 0:
            return img
        scale = _PDF_CLIPBOARD_MAX_SIDE / float(side)
        nw = max(1, int(w * scale))
        nh = max(1, int(h * scale))
        scaled = img.Scale(nw, nh, wx.IMAGE_QUALITY_HIGH)
        return scaled if scaled.IsOk() else img
    except Exception:
        return img


def save_pdf_image_record_to_path(record, dest_path):
    """Salva record immagine PDF su disco a piena risoluzione. True se ok."""
    if not record or not dest_path:
        return False
    ext = os.path.splitext(dest_path)[1].lower()
    try:
        if record["kind"] == "jpeg" and ext in (".jpg", ".jpeg"):
            with open(dest_path, "wb") as f:
                f.write(record["data"])
            return True
        img = pdf_image_record_to_wx_image(record, fit_for_clipboard=False)
        if img is None or not img.IsOk():
            return False
        if ext == ".png":
            return bool(img.SaveFile(dest_path, wx.BITMAP_TYPE_PNG))
        if ext in (".jpg", ".jpeg"):
            return bool(img.SaveFile(dest_path, wx.BITMAP_TYPE_JPEG))
        if ext == ".bmp":
            return bool(img.SaveFile(dest_path, wx.BITMAP_TYPE_BMP))
        # default jpeg
        if not ext:
            dest_path = dest_path + ".jpg"
        return bool(img.SaveFile(dest_path, wx.BITMAP_TYPE_JPEG))
    except Exception:
        pass
        return False


def format_file_date_label(mtime):
    if not mtime:
        return ""
    try:
        return datetime.datetime.fromtimestamp(mtime).strftime("%d/%m/%Y")
    except Exception:
        return ""


def pdf_info_date_timestamp(file_path, fallback=0):
    try:
        with open(file_path, "rb") as f:
            head = f.read(min(PDF_READ_MAX_BYTES, 2 * 1024 * 1024))
    except Exception:
        return fallback
    for key in (b"/ModDate", b"/CreationDate"):
        idx = head.find(key)
        if idx < 0:
            continue
        m = re.search(
            br"\(D:(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?",
            head[idx : idx + 80],
        )
        if not m:
            continue
        try:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            hh = int(m.group(4) or 0)
            mi = int(m.group(5) or 0)
            ss = int(m.group(6) or 0)
            return datetime.datetime(y, mo, d, hh, mi, ss).timestamp()
        except Exception:
            continue
    return fallback


def deep_ocr_jpg_scan(file_path):
    try:
        with open(file_path, "rb") as f:
            header = f.read(4194304)
            content_str = header.decode("latin1", errors="ignore")
            words = re.findall(r"[A-Za-z0-9\s]{3,}", content_str)
            return " ".join(words)
    except Exception:
        return ""

def jump_to_line_in_editor(file_path, line_number):
    def _jump_worker():
        npp_path = shutil.which("notepad++.exe") or r"C:\Program Files\Notepad++\notepad++.exe"
        vscode_path = shutil.which("code.cmd") or shutil.which("code.exe")

        if os.path.exists(npp_path):
            subprocess.Popen([npp_path, f"-n{line_number}", file_path])
            return

        if vscode_path:
            subprocess.Popen([vscode_path, "-g", f"{file_path}:{line_number}"])
            return

        subprocess.Popen(["notepad.exe", file_path])
        time.sleep(0.6)

        VK_CONTROL = 0x11
        VK_G = 0x47
        VK_RETURN = 0x0D

        user32 = ctypes.windll.user32
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_G, 0, 0, 0)
        user32.keybd_event(VK_G, 0, 2, 0)
        user32.keybd_event(VK_CONTROL, 0, 2, 0)
        time.sleep(0.3)

        for digit in str(line_number):
            vk = ord(digit)
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
            time.sleep(0.05)

        user32.keybd_event(VK_RETURN, 0, 0, 0)
        user32.keybd_event(VK_RETURN, 0, 2, 0)

    threading.Thread(target=_jump_worker, daemon=True).start()

class EmlViewerFrame(wx.Frame):
    def __init__(self, parent, file_path, search_query):
        super(EmlViewerFrame, self).__init__(
            parent,
            title=f"Lettore Email - {os.path.basename(file_path)}",
            size=(800, 650),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.file_path = file_path
        self.search_query = search_query
        self._closed = False

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.txt_display = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self.txt_display.SetValue(
            "Caricamento email in corso…\r\n"
            "Se il messaggio ha allegati grandi, attendere qualche secondo."
        )
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_close = wx.Button(panel, label="C&hiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        hbox_btns.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_btns, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(vbox)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        ui.message("Caricamento email in corso.")
        threading.Thread(target=self._load_worker, daemon=True).start()

    def on_close(self, event):
        self._closed = True
        event.Skip()

    def _load_worker(self):
        full_text = None
        err = None
        try:
            try:
                with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                    msg = email.message_from_file(f, policy=policy.default)
            except Exception:
                with open(self.file_path, "r", encoding="latin1", errors="ignore") as f:
                    msg = email.message_from_file(f, policy=policy.default)
            full_text = _format_email_viewer_text(msg)
        except Exception:
            err = True
        if self._closed:
            return
        if err:
            wx.CallAfter(self._apply_loaded_text, "Errore durante la lettura del file email.")
        else:
            wx.CallAfter(self._apply_loaded_text, full_text)

    def _apply_loaded_text(self, full_text):
        if self._closed:
            return
        try:
            if not self.txt_display:
                return
        except RuntimeError:
            return
        self.txt_display.SetValue(full_text or "")
        pos, term_len = _find_query_in_viewer_text(full_text or "", self.search_query)
        self.txt_display.SetFocus()
        if pos != -1:
            self.txt_display.SetSelection(pos, pos + term_len)
        else:
            self.txt_display.SetInsertionPoint(0)
        ui.message("Email caricata.")

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
        else:
            event.Skip()


class MboxViewerFrame(wx.Frame):
    def __init__(self, parent, mbox_file_path, msg_index, search_query, cached_text=None):
        super(MboxViewerFrame, self).__init__(
            parent,
            title=f"Lettore MBOX - Messaggio {msg_index + 1}",
            size=(800, 650),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.mbox_file_path = mbox_file_path
        self.msg_index = msg_index
        self.search_query = search_query
        self.cached_text = cached_text
        self._closed = False

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.txt_display = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        if cached_text:
            self.txt_display.SetValue("Preparazione visualizzazione…\r\n")
        else:
            self.txt_display.SetValue(
                "Caricamento messaggio in corso…\r\n"
                "Su caselle Thunderbird molto grandi può richiedere alcuni secondi.\r\n"
                "Puoi chiudere con ESC."
            )
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_close = wx.Button(panel, label="C&hiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        hbox_btns.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_btns, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(vbox)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        if cached_text:
            ui.message(f"Messaggio {msg_index + 1} dalla ricerca.")
            wx.CallAfter(self._apply_loaded_text, cached_text)
        else:
            ui.message(f"Caricamento messaggio {msg_index + 1} dall'archivio. Attendere.")
            threading.Thread(target=self._load_worker, daemon=True).start()

    def on_close(self, event):
        self._closed = True
        event.Skip()

    def _load_worker(self):
        full_text = None
        err = None

        def _progress(n):
            if self._closed:
                return
            wx.CallAfter(
                self._set_status_text,
                f"Caricamento in corso… scanditi {n} messaggi "
                f"(destinazione {self.msg_index + 1}).\r\n"
                "Puoi chiudere con ESC.",
            )

        try:
            msg = load_mbox_message_by_index(
                self.mbox_file_path,
                self.msg_index,
                should_abort=lambda: self._closed,
                on_progress=_progress,
            )
            full_text = _format_email_viewer_text(msg)
        except InterruptedError:
            return
        except Exception:
            err = True
        if self._closed:
            return
        if err:
            wx.CallAfter(
                self._apply_loaded_text,
                "Errore durante la lettura del messaggio.\r\n"
                "Riavvia la ricerca e riapri il risultato "
                "(il testo resta in memoria e si apre subito).",
            )
        else:
            wx.CallAfter(self._apply_loaded_text, full_text)

    def _set_status_text(self, text):
        if self._closed:
            return
        try:
            if self.txt_display:
                self.txt_display.SetValue(text)
        except RuntimeError:
            pass

    def _apply_loaded_text(self, full_text):
        if self._closed:
            return
        try:
            if not self.txt_display:
                return
        except RuntimeError:
            return
        self.txt_display.SetValue(full_text or "")
        pos, term_len = _find_query_in_viewer_text(full_text or "", self.search_query)
        self.txt_display.SetFocus()
        if pos != -1:
            self.txt_display.SetSelection(pos, pos + term_len)
        else:
            self.txt_display.SetInsertionPoint(0)
        ui.message("Messaggio caricato.")

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
        else:
            event.Skip()

class WhatsNewFrame(wx.Frame):
    def __init__(self, parent):
        super(WhatsNewFrame, self).__init__(
            parent,
            title=f"Novità della Versione {APP_VERSION}",
            size=(700, 500),
            style=wx.DEFAULT_FRAME_STYLE,
        )

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        text_content = (
            f"Benvenuto nella versione {APP_VERSION} dell'Add-on per NVDA!\n\n"
            "Ecco le principali novità di questo aggiornamento:\n"
            "--------------------------------------------------\n"
            "• PDF migliorato: testo reale da stream compressi; salta Image XObject (niente simboli).\n"
            "• Menu: «Copia Testo» e «Copia Immagine» separate (anche da PDF scansionati).\n"
            "• Data documento nei risultati PDF; avviso se il PDF è solo immagine.\n\n"
            "• Restano attive le novità della 1.5.2 (MBOX, date email, ordinamento).\n"
            "--------------------------------------------------\n"
            "Grazie per usare Ricerca Testuale Accesso Digitale!\n"
        )

        lbl_info = wx.StaticText(panel, label="Leggi tutte le novità dell'ultimo aggiornamento:")
        vbox.Add(lbl_info, 0, wx.ALL, 8)

        self.txt_display = wx.TextCtrl(panel, value=text_content, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_close = wx.Button(panel, label="Chiudi e Continua (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
        hbox_btns.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_btns, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(vbox)
        self.Centre()
        self.txt_display.SetFocus()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        
        ui.message("Finestra delle novità aperta. Usa le frecce per leggere.")

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            event.Skip()

class ShortcutsFrame(wx.Frame):
    def __init__(self, parent):
        super(ShortcutsFrame, self).__init__(
            parent,
            title=f"{APP_TITLE} v{APP_VERSION} - Comandi e Info",
            size=(680, 560),
            style=wx.DEFAULT_FRAME_STYLE,
        )

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.text_content = (
            f"{APP_TITLE} v{APP_VERSION}\n"
            "Autore e Sviluppatore: Maurizio Barra (Accesso Digitale)\n\n"
            "--------------------------------------------------\n"
            "COMANDI E SCORCIATOIE DA TASTIERA:\n"
            "--------------------------------------------------\n"
            "Comandi Globali NVDA:\n"
            "  - NVDA + Shift + Control + F : Apri la finestra principale di ricerca\n"
            "  - NVDA + Shift + Control + S : Apri questa finestra comandi\n"
            "  - NVDA + Shift + Control + D : Apri la pagina per le Donazioni PayPal\n"
            "  - (Per la Guida in formato Web, usa Gestione Componenti Aggiuntivi -> Guida)\n\n"
            "Comandi Finestra di Ricerca:\n"
            "  - Alt + T : Imposta la scansione su TUTTO IL PC (tutte le unità attive)\n"
            "  - Alt + N : Annulla ricerca in corso e mantieni i risultati\n"
            "  - Alt + I : Mostra Info Versione e Autore\n"
            "  - Alt + P : Annuncia lo stato (due volte velocemente per copiare negli appunti)\n"
            "  - Pulsante Copia Stato : copia i dettagli della ricerca negli appunti\n"
            "  - Ctrl + H : Cronologia testi cercati (riprendi una ricerca precedente)\n"
            "  - Ctrl + Shift + H : Cronologia percorsi usati\n"
            "  - Ctrl + F : Salta alla casella per filtrare i risultati trovati\n"
            "  - TAB oppure Alt+S / S : Raggiunge anche il campo 'Stato avanzamento' leggibile dallo screen reader\n"
            "  - Alt + K : Scatta uno screenshot salvato in 'Catture di schermata'\n"
            "  - Ctrl + P : Stampa rapida dei risultati di ricerca in lista\n"
            "  - Ctrl + E : Esporta Risultati\n"
            "  - Ctrl + D : Aggiunge percorso attuale ai Segnalibri\n"
            "  - INVIO (su campo testo) : Avvia subito la ricerca\n"
            "  - INVIO (sui risultati) : Apri file alla riga esatta, oppure articolo feed nel browser\n"
            "  - SPAZIO / F4 : Anteprima vocale immediata del contesto\n"
            "  - Tasto APPLICAZIONI : Menu contestuale del file selezionato\n"
            "  - ESC : Chiudi la finestra\n\n"
            "Feed RSS e Thunderbird:\n"
            "  - Pulsante 'Feed Thunderbird' : trova le cartelle Mail\\Feeds del profilo\n"
            "  - Nel percorso puoi incollare URL http(s) o più percorsi separati da ; o ,\n"
            "  - Casella 'occorrenze grezze' : aggiunge anche risultati [FEED-RIGA] nel file\n"
            "  - [RSS] / [FEED] : Invio apre l'articolo nel browser\n"
            "  - [FEED-RIGA] : Invio salta alla riga nel file (Notepad++ se disponibile)\n\n"
            "--------------------------------------------------\n"
            "SOSTIENI IL PROGETTO:\n"
            f"{DONATION_URL}\n"
            "--------------------------------------------------"
        )

        lbl_info = wx.StaticText(
            panel,
            label="Usa le frecce Su/Giù e Sinistra/Destra per navigare nel testo:",
        )
        vbox.Add(lbl_info, 0, wx.ALL, 8)

        self.txt_display = wx.TextCtrl(
            panel,
            value=self.text_content,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
        )
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_copy = wx.Button(panel, label="&Copia Testo Comandi")
        btn_copy.Bind(wx.EVT_BUTTON, self.on_copy_text)
        hbox_btns.Add(btn_copy, 0, wx.ALL, 5)

        btn_donate = wx.Button(panel, label="Apri Link &Donazione...")
        btn_donate.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open(DONATION_URL))
        hbox_btns.Add(btn_donate, 0, wx.ALL, 5)

        btn_close = wx.Button(panel, label="C&hiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
        hbox_btns.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_btns, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(vbox)
        self.Centre()
        self.txt_display.SetFocus()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def on_copy_text(self, event):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.text_content))
            wx.TheClipboard.Close()
            ui.message("Testo dei comandi copiato negli appunti!")

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            event.Skip()


class SearchFrame(wx.Frame):

    def __init__(self):
        super(SearchFrame, self).__init__(
            None,
            title=f"{APP_TITLE} v{APP_VERSION} - Maurizio Barra",
            size=(860, 780),
            style=wx.DEFAULT_FRAME_STYLE,
        )

        self._stop_search = False
        self.current_percent = 0
        self.scanned_count = 0
        self.current_matches = []
        self.file_map = {}
        self.current_query = ""
        self.live_matches_count = 0
        self.bookmark_items = []
        self.history_query_items = []
        self.last_alt_p_time = 0
        self.last_feed_raw_occurrences = 0
        self.current_sort = load_sort_preference()

        self._init_menu_bar()

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        lbl_query = wx.StaticText(panel, label="&Testo o frase da cercare (supporta più termini e dialetti):")
        vbox.Add(lbl_query, 0, wx.ALL, 5)
        hbox_query = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_query = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.txt_query.Bind(wx.EVT_TEXT_ENTER, lambda e: self.start_search_thread())
        hbox_query.Add(self.txt_query, 1, wx.EXPAND | wx.ALL, 5)
        btn_query_hist = wx.Button(panel, label="Cronolo&gia")
        btn_query_hist.Bind(wx.EVT_BUTTON, self.on_recall_query_history)
        hbox_query.Add(btn_query_hist, 0, wx.ALL, 5)
        vbox.Add(hbox_query, 0, wx.EXPAND)

        hbox_filter = wx.BoxSizer(wx.HORIZONTAL)
        vbox_filter_choice = wx.BoxSizer(wx.VERTICAL)
        lbl_filter = wx.StaticText(panel, label="T&ipo di file da cercare:")
        vbox_filter_choice.Add(lbl_filter, 0, wx.ALL, 5)
        self.combo_filter = wx.Choice(
            panel,
            choices=[
                "Tutti i tipi di file",
                "Solo Immagini (.jpg, .png, .jpeg, .bmp)",
                "Solo Audio e Video (.mp4, .mp3, .mkv, .avi, .wav)",
                "Solo Documenti (.txt, .docx, .doc, .pdf, .eml, .log, .csv)",
                "Estensione Personalizzata...",
            ],
        )
        self.combo_filter.SetSelection(0)
        self.combo_filter.Bind(wx.EVT_CHOICE, self.on_filter_changed)
        vbox_filter_choice.Add(self.combo_filter, 1, wx.EXPAND | wx.ALL, 5)
        hbox_filter.Add(vbox_filter_choice, 1, wx.EXPAND)

        self.vbox_custom_ext = wx.BoxSizer(wx.VERTICAL)
        lbl_custom_ext = wx.StaticText(panel, label="Estensione specifica (es. .ini o .srt):")
        self.vbox_custom_ext.Add(lbl_custom_ext, 0, wx.ALL, 5)
        self.txt_custom_ext = wx.TextCtrl(panel, value=".txt")
        self.txt_custom_ext.Enable(False)
        self.vbox_custom_ext.Add(self.txt_custom_ext, 1, wx.EXPAND | wx.ALL, 5)
        hbox_filter.Add(self.vbox_custom_ext, 1, wx.EXPAND)
        vbox.Add(hbox_filter, 0, wx.EXPAND)

        lbl_path = wx.StaticText(panel, label="&Percorso di ricerca (Memoria automatica o inserisci link Feed RSS):")
        vbox.Add(lbl_path, 0, wx.ALL, 5)

        hbox_path = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_path = wx.TextCtrl(panel, value=load_last_path())
        hbox_path.Add(self.txt_path, 1, wx.EXPAND | wx.ALL, 5)

        btn_browse = wx.Button(panel, label="S&foglia...")
        btn_browse.Bind(wx.EVT_BUTTON, self.on_browse)
        hbox_path.Add(btn_browse, 0, wx.ALL, 5)

        btn_all_pc = wx.Button(panel, label="&Tutto il PC")
        btn_all_pc.Bind(wx.EVT_BUTTON, self.on_search_all_pc)
        hbox_path.Add(btn_all_pc, 0, wx.ALL, 5)

        btn_tb_feeds = wx.Button(panel, label="Feed &Thunderbird")
        btn_tb_feeds.Bind(wx.EVT_BUTTON, self.on_detect_thunderbird_feeds)
        hbox_path.Add(btn_tb_feeds, 0, wx.ALL, 5)
        vbox.Add(hbox_path, 0, wx.EXPAND)

        self.chk_feed_raw = wx.CheckBox(
            panel,
            label="Nei feed, elenca anche le &occorrenze grezze (oltre agli articoli)",
        )
        self.chk_feed_raw.SetValue(False)
        vbox.Add(self.chk_feed_raw, 0, wx.ALL, 5)

        hbox_actions = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_search = wx.Button(panel, label="&Avvia Ricerca")
        self.btn_search.Bind(wx.EVT_BUTTON, lambda e: self.start_search_thread())
        hbox_actions.Add(self.btn_search, 0, wx.ALL, 5)

        self.btn_cancel = wx.Button(panel, label="A&nnulla Ricerca")
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel_search)
        self.btn_cancel.Disable()
        hbox_actions.Add(self.btn_cancel, 0, wx.ALL, 5)

        btn_info = wx.Button(panel, label="&Info Versione")
        btn_info.Bind(wx.EVT_BUTTON, self.on_show_info)
        hbox_actions.Add(btn_info, 0, wx.ALL, 5)

        btn_progress_now = wx.Button(panel, label="&Percentuale (Alt+P)")
        btn_progress_now.Bind(wx.EVT_BUTTON, lambda e: self.announce_progress())
        hbox_actions.Add(btn_progress_now, 0, wx.ALL, 5)

        btn_copy_status = wx.Button(panel, label="Copia S&tato")
        btn_copy_status.Bind(wx.EVT_BUTTON, lambda e: self.copy_status_to_clipboard())
        hbox_actions.Add(btn_copy_status, 0, wx.ALL, 5)

        btn_screenshot = wx.Button(panel, label="Cattura Sc&hermo (Alt+K)")
        btn_screenshot.Bind(wx.EVT_BUTTON, self.on_take_screenshot)
        hbox_actions.Add(btn_screenshot, 0, wx.ALL, 5)

        vbox.Add(hbox_actions, 0, wx.ALIGN_CENTER)

        lbl_status_progress = wx.StaticText(
            panel,
            label="&Stato avanzamento ricerca (raggiungibile con Tab e premendo S):",
        )
        vbox.Add(lbl_status_progress, 0, wx.ALL, 5)

        self.txt_status_progress = wx.TextCtrl(
            panel,
            value="Pronto per la ricerca. Premi Alt+P, Tab oppure S per lo stato.",
            style=wx.TE_READONLY,
        )
        self.txt_status_progress.SetName("Stato avanzamento ricerca")
        vbox.Add(self.txt_status_progress, 0, wx.EXPAND | wx.ALL, 5)

        self.gauge = wx.Gauge(panel, range=100)
        vbox.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 5)

        lbl_filter_res = wx.StaticText(panel, label="&Filtra i risultati nella lista (Ctrl+F):")
        vbox.Add(lbl_filter_res, 0, wx.ALL, 5)
        self.txt_filter = wx.TextCtrl(panel)
        self.txt_filter.Bind(wx.EVT_TEXT, self.on_filter_text)
        vbox.Add(self.txt_filter, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        lbl_results = wx.StaticText(
            panel,
            label="&Risultati trovati (INVIO per riga esatta, SPAZIO/F4 anteprima audio, APPLICAZIONI opzioni):",
        )
        vbox.Add(lbl_results, 0, wx.ALL, 5)
        self.lst_results = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.lst_results.Bind(wx.EVT_CHAR_HOOK, self.on_list_char_hook)
        self.lst_results.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open_file_event)
        self.lst_results.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        vbox.Add(self.lst_results, 1, wx.EXPAND | wx.ALL, 5)

        hbox_bottom = wx.BoxSizer(wx.HORIZONTAL)
        btn_open = wx.Button(panel, label="&Apri File (Alla Riga)")
        btn_open.Bind(wx.EVT_BUTTON, self.on_open_file_event)
        hbox_bottom.Add(btn_open, 0, wx.ALL, 5)

        btn_preview = wx.Button(panel, label="Anteprima &Voce (F4)")
        btn_preview.Bind(wx.EVT_BUTTON, lambda e: self.speak_selected_preview())
        hbox_bottom.Add(btn_preview, 0, wx.ALL, 5)
        
        btn_export = wx.Button(panel, label="&Esporta Risultati...")
        btn_export.Bind(wx.EVT_BUTTON, self.on_export_results)
        hbox_bottom.Add(btn_export, 0, wx.ALL, 5)
        
        btn_print = wx.Button(panel, label="Stam&pa Risultati...")
        btn_print.Bind(wx.EVT_BUTTON, self.on_print_results)
        hbox_bottom.Add(btn_print, 0, wx.ALL, 5)

        btn_github = wx.Button(panel, label="Pagina &GitHub")
        btn_github.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open(GITHUB_URL))
        hbox_bottom.Add(btn_github, 0, wx.ALL, 5)

        btn_close = wx.Button(panel, label="C&hiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        hbox_bottom.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_bottom, 0, wx.EXPAND)
        panel.SetSizer(vbox)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_general_char_hook)

    def show_whats_new_dialog(self):
        dlg = WhatsNewFrame(self)
        dlg.Show()
        dlg.Raise()

    def show_shortcuts_dialog(self):
        dlg = ShortcutsFrame(self)
        dlg.Show()
        dlg.Raise()

    def on_send_feedback(self, event):
        try:
            sys_info = f"{platform.system()} {platform.release()} ({platform.version()})"
            subject = urllib.parse.quote(f"Feedback {APP_TITLE} Add-on v{APP_VERSION}")
            body = urllib.parse.quote(
                f"Ciao Maurizio,\n\nTi scrivo per segnalarti un suggerimento o un problema riscontrato "
                f"con l'Add-on NVDA...\n\n"
                f"[SE SEGNALI UN ERRORE, ALLEGA SE POSSIBILE IL LOG DI NVDA "
                f"(NVDA+F1 oppure Strumenti -> Visualizza log)]\n\n"
                f"----------------------------------------\n"
                f"Dati Tecnici per Assistenza (non eliminare):\n"
                f"Versione Add-on: {APP_VERSION}\n"
                f"Sistema Operativo: {sys_info}\n"
                f"----------------------------------------\n"
            )
            url = f"mailto:{EMAIL_DESTINATARIO}?subject={subject}&body={body}"
            webbrowser.open(url)
            ui.message("Apertura client di posta per la segnalazione...")
        except Exception:
            ui.message("Impossibile aprire il programma di posta.")

    def on_export_diagnostic(self, event):
        try:
            desktop = get_dynamic_desktop_path()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(desktop, f"Diagnostica_RTAD_Addon_{timestamp}.txt")
            sys_info = f"{platform.system()} {platform.release()} ({platform.version()})"
            content = (
                f"{APP_TITLE} - Scheda Diagnostica Add-on\n"
                f"Versione: {APP_VERSION}\n"
                f"Data: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"Sistema: {sys_info}\n"
                f"Config locale: {CONFIG_DIR}\n"
                f"GitHub: {GITHUB_URL}\n\n"
                f"Nota: per errori NVDA allega anche il log completo "
                f"(NVDA+F1 o Strumenti -> Visualizza log).\n"
            )
            with open(dest, "w", encoding="utf-8") as f:
                f.write(content)
            ui.message("Scheda diagnostica esportata sul Desktop.")
            wx.MessageBox(
                f"File salvato:\n{dest}",
                "Esportazione riuscita",
                wx.OK | wx.ICON_INFORMATION,
            )
        except Exception:
            ui.message("Errore nell'esportazione della scheda diagnostica.")

    def on_print_guide(self, event):
        try:
            guide = (
                f"{APP_TITLE} v{APP_VERSION} - Guida comandi Add-on\n"
                "Autore: Maurizio Barra (Accesso Digitale)\n\n"
                "NVDA+Shift+Control+F : Apri ricerca\n"
                "NVDA+Shift+Control+S : Comandi\n"
                "NVDA+Shift+Control+D : Donazioni\n"
                "Ctrl+H : Cronologia testi\n"
                "Ctrl+Shift+H : Cronologia percorsi\n"
                "Ctrl+F : Filtra risultati\n"
                "Alt+P : Stato (due volte = copia)\n"
                "Alt+S / S : Campo stato avanzamento\n"
                "Ctrl+U : Verifica aggiornamenti\n"
                "Ctrl+E / Ctrl+P / Ctrl+D : Esporta / Stampa / Segnalibro\n"
            )
            temp = os.path.join(CONFIG_DIR, "stampa_guida_addon.txt")
            with open(temp, "w", encoding="utf-8") as f:
                f.write(guide)
            notepad = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "notepad.exe")
            if not os.path.exists(notepad):
                notepad = "notepad.exe"
            subprocess.Popen([notepad, "/p", temp])
            ui.message("Guida inviata alla stampante predefinita.")
        except Exception:
            ui.message("Impossibile stampare la guida.")

    def on_check_updates(self, event=None, silent=False):
        def _check():
            try:
                if not silent:
                    wx.CallAfter(ui.message, "Verifica aggiornamenti in corso...")
                req = urllib.request.Request(
                    GITHUB_API_LATEST,
                    headers={"User-Agent": "RTAD-Addon-Updater"},
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = json.loads(response.read().decode("utf-8"))
                latest_tag = data.get("tag_name", "").replace("app-", "").replace("v", "").strip()
                html_url = data.get("html_url", GITHUB_URL)
                if not latest_tag:
                    if not silent:
                        wx.CallAfter(ui.message, "Nessuna informazione di versione online.")
                    return
                try:
                    v_online = [int(x) for x in latest_tag.split(".")]
                    v_local = [int(x) for x in APP_VERSION.split(".")]
                    is_newer = v_online > v_local
                except Exception:
                    is_newer = latest_tag != APP_VERSION
                if is_newer:
                    addon_url = None
                    for asset in data.get("assets", []):
                        name = asset.get("name", "")
                        if name.endswith(".nvda-addon"):
                            addon_url = asset.get("browser_download_url")
                            break

                    def _prompt():
                        dlg = wx.MessageDialog(
                            self,
                            f"Nuova versione {latest_tag} disponibile!\n\n"
                            f"Apro la pagina di download?",
                            "Aggiornamento Add-on",
                            wx.YES_NO | wx.ICON_QUESTION,
                        )
                        if dlg.ShowModal() == wx.ID_YES:
                            webbrowser.open(addon_url or html_url)
                            ui.message("Apertura pagina download aggiornamento...")
                        dlg.Destroy()

                    wx.CallAfter(_prompt)
                else:
                    if not silent:
                        wx.CallAfter(ui.message, "Versione aggiornata.")
            except Exception:
                if not silent:
                    wx.CallAfter(ui.message, "Impossibile verificare la connessione.")

        threading.Thread(target=_check, daemon=True).start()

    def _init_menu_bar(self):
        menubar = wx.MenuBar()

        # Menu File
        file_menu = wx.Menu()
        item_export = file_menu.Append(wx.ID_ANY, "Esporta &Risultati...\tCtrl+E")
        item_print = file_menu.Append(wx.ID_ANY, "&Stampa Risultati...\tCtrl+P")
        file_menu.AppendSeparator()
        item_exit = file_menu.Append(wx.ID_EXIT, "E&sci\tCtrl+Q")
        menubar.Append(file_menu, "&File")

        # Menu Segnalibri
        self.bookmarks_menu = wx.Menu()
        item_add_bm = self.bookmarks_menu.Append(wx.ID_ANY, "Aggiungi percorso attuale ai Segnalibri\tCtrl+D")
        item_manage_bm = self.bookmarks_menu.Append(wx.ID_ANY, "Gestisci Segnalibri...")
        self.bookmarks_menu.AppendSeparator()
        menubar.Append(self.bookmarks_menu, "Se&gnalibri")
        
        self.Bind(wx.EVT_MENU, self.on_add_bookmark, item_add_bm)
        self.Bind(wx.EVT_MENU, self.on_manage_bookmarks, item_manage_bm)
        self.update_bookmarks_menu()

        # Menu Cronologia
        self.history_menu = wx.Menu()
        item_hist_query = self.history_menu.Append(wx.ID_ANY, "Richiama &testo cercato...\tCtrl+H")
        item_hist_path = self.history_menu.Append(wx.ID_ANY, "Richiama &percorso...\tCtrl+Shift+H")
        self.history_menu.AppendSeparator()
        item_clear_queries = self.history_menu.Append(wx.ID_ANY, "Svuota cronologia &testi")
        item_clear_paths = self.history_menu.Append(wx.ID_ANY, "Svuota cronologia p&ercorsi")
        self.history_menu.AppendSeparator()
        menubar.Append(self.history_menu, "Cro&nologia")

        self.Bind(wx.EVT_MENU, self.on_recall_query_history, item_hist_query)
        self.Bind(wx.EVT_MENU, self.on_recall_path_history, item_hist_path)
        self.Bind(wx.EVT_MENU, self.on_clear_query_history, item_clear_queries)
        self.Bind(wx.EVT_MENU, self.on_clear_path_history, item_clear_paths)
        self.update_history_menu()

        # Menu Strumenti
        tools_menu = wx.Menu()
        item_update = tools_menu.Append(wx.ID_ANY, "Verifica &Aggiornamenti...	Ctrl+U")
        menubar.Append(tools_menu, "&Strumenti")

        # Menu Aiuto
        help_menu = wx.Menu()
        item_whatsnew = help_menu.Append(wx.ID_ANY, "&Novità della Versione")
        item_guide = help_menu.Append(wx.ID_ANY, "&Guida ai Comandi	F1")
        item_print_guide = help_menu.Append(wx.ID_ANY, "Stampa &Guida ai Comandi")
        item_github = help_menu.Append(wx.ID_ANY, "Pagina Ufficiale &GitHub")
        item_info = help_menu.Append(wx.ID_ANY, "&Info Versione	Alt+I")
        help_menu.AppendSeparator()
        item_diag = help_menu.Append(wx.ID_ANY, "Esporta Info &Diagnostica sul Desktop")
        item_feedback = help_menu.Append(wx.ID_ANY, "Segnala un Problema / Invia &Feedback")
        menubar.Append(help_menu, "&Aiuto")

        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self.on_export_results, item_export)
        self.Bind(wx.EVT_MENU, self.on_print_results, item_print)
        self.Bind(wx.EVT_MENU, self.on_close, item_exit)
        self.Bind(wx.EVT_MENU, self.on_check_updates, item_update)
        self.Bind(wx.EVT_MENU, lambda e: self.show_whats_new_dialog(), item_whatsnew)
        self.Bind(wx.EVT_MENU, lambda e: self.show_shortcuts_dialog(), item_guide)
        self.Bind(wx.EVT_MENU, self.on_print_guide, item_print_guide)
        self.Bind(wx.EVT_MENU, lambda e: webbrowser.open(GITHUB_URL), item_github)
        self.Bind(wx.EVT_MENU, self.on_show_info, item_info)
        self.Bind(wx.EVT_MENU, self.on_export_diagnostic, item_diag)
        self.Bind(wx.EVT_MENU, self.on_send_feedback, item_feedback)

    def on_add_bookmark(self, event=None):
        path = self.txt_path.GetValue().strip()
        if not path:
            wx.CallLater(200, lambda: ui.message("Nessun percorso da salvare."))
            return
        bms = load_bookmarks()
        if path not in bms:
            bms.append(path)
            save_bookmarks(bms)
            self.update_bookmarks_menu()
            wx.CallLater(200, lambda: ui.message("Percorso salvato nei segnalibri."))
        else:
            wx.CallLater(200, lambda: ui.message("Percorso già presente nei segnalibri."))

    def on_manage_bookmarks(self, event=None):
        bms = load_bookmarks()
        if not bms:
            wx.CallLater(200, lambda: ui.message("Nessun segnalibro salvato."))
            return
        dlg = wx.SingleChoiceDialog(self, "Seleziona il segnalibro da ELIMINARE:", "Gestione Segnalibri", bms)
        if dlg.ShowModal() == wx.ID_OK:
            sel = dlg.GetStringSelection()
            if sel in bms:
                bms.remove(sel)
                save_bookmarks(bms)
                self.update_bookmarks_menu()
                wx.CallLater(200, lambda: ui.message("Segnalibro eliminato correttamente."))
        dlg.Destroy()

    def on_select_bookmark(self, path):
        self.txt_path.SetValue(path)
        save_last_path(path)
        wx.CallLater(200, lambda: ui.message(f"Segnalibro caricato: {path}"))

    def update_bookmarks_menu(self):
        for item_id in self.bookmark_items:
            self.bookmarks_menu.Remove(item_id)
        self.bookmark_items.clear()
        
        bms = load_bookmarks()
        for bm in bms:
            item = self.bookmarks_menu.Append(wx.ID_ANY, bm)
            self.bookmark_items.append(item.GetId())
            self.Bind(wx.EVT_MENU, lambda e, p=bm: self.on_select_bookmark(p), item)

    def on_recall_query_history(self, event=None):
        hist = load_query_history()
        if not hist:
            wx.CallLater(200, lambda: ui.message("Nessun testo nella cronologia."))
            return
        dlg = wx.SingleChoiceDialog(
            self,
            "Seleziona un testo già cercato da riprendere:",
            "Cronologia testi",
            hist,
        )
        if dlg.ShowModal() == wx.ID_OK:
            sel = dlg.GetStringSelection()
            if sel:
                self.on_apply_history_query(sel)
        dlg.Destroy()

    def on_recall_path_history(self, event=None):
        hist = load_path_history()
        if not hist:
            wx.CallLater(200, lambda: ui.message("Nessun percorso nella cronologia."))
            return
        dlg = wx.SingleChoiceDialog(
            self,
            "Seleziona un percorso già usato da riprendere:",
            "Cronologia percorsi",
            hist,
        )
        if dlg.ShowModal() == wx.ID_OK:
            sel = dlg.GetStringSelection()
            if sel:
                self.txt_path.SetValue(sel)
                save_last_path(sel)
                self.txt_path.SetFocus()
                self.txt_path.SetInsertionPointEnd()
                wx.CallLater(200, lambda: ui.message(f"Percorso ripreso: {sel}"))
        dlg.Destroy()

    def on_apply_history_query(self, query):
        self.txt_query.SetValue(query)
        self.txt_query.SetFocus()
        self.txt_query.SetInsertionPointEnd()
        wx.CallLater(200, lambda: ui.message(f"Testo ripreso: {query}"))

    def on_clear_query_history(self, event=None):
        if not load_query_history():
            wx.CallLater(200, lambda: ui.message("La cronologia testi è già vuota."))
            return
        clear_query_history()
        self.update_history_menu()
        wx.CallLater(200, lambda: ui.message("Cronologia testi svuotata."))

    def on_clear_path_history(self, event=None):
        if not load_path_history():
            wx.CallLater(200, lambda: ui.message("La cronologia percorsi è già vuota."))
            return
        clear_path_history()
        wx.CallLater(200, lambda: ui.message("Cronologia percorsi svuotata."))

    def update_history_menu(self):
        for item_id in self.history_query_items:
            try:
                self.history_menu.Remove(item_id)
            except Exception:
                pass
        self.history_query_items.clear()
        for query in load_query_history()[:10]:
            label = query if len(query) <= 60 else query[:57] + "..."
            item = self.history_menu.Append(wx.ID_ANY, label)
            self.history_query_items.append(item.GetId())
            self.Bind(wx.EVT_MENU, lambda e, q=query: self.on_apply_history_query(q), item)

    def on_cancel_search(self, event):
        if not self.btn_search.IsEnabled():
            self._stop_search = True
            self.btn_cancel.Disable()
            ui.message("Ricerca interrotta dall'utente. Salvataggio risultati parziali in corso...")

    def on_show_info(self, event):
        msg = f"{APP_TITLE}\nVersione: {APP_VERSION}\nAutore: Maurizio Barra\nLicenza: GPL v2"
        ui.message(f"Versione installata {APP_VERSION}. Autore Maurizio Barra.")
        wx.MessageBox(msg, "Informazioni Versione", wx.OK | wx.ICON_INFORMATION)

    def on_filter_changed(self, event):
        sel = self.combo_filter.GetSelection()
        self.txt_custom_ext.Enable(sel == 4)

    def on_search_all_pc(self, event):
        drives = get_real_ready_drives()
        drives_str = ";".join(drives)
        self.txt_path.SetValue(drives_str)
        save_last_path(drives_str)
        ui.message(f"Tutto il PC impostato: {len(drives)} unità attive. Premi Invio per avviare.")
        self.btn_search.SetFocus()

    def on_detect_thunderbird_feeds(self, event):
        dirs = find_thunderbird_feeds_dirs()
        if not dirs:
            ui.message(
                "Nessuna cartella Feed Thunderbird trovata. "
                "Verifica che Thunderbird sia installato e che esistano i Feed RSS nel profilo."
            )
            return
        joined = ";".join(dirs)
        self.txt_path.SetValue(joined)
        save_last_path(joined)
        n = len(dirs)
        ui.message(
            f"Trovate {n} cartelle Feed Thunderbird. Percorso aggiornato. "
            "Inserisci la parola da cercare e premi Avvia Ricerca."
        )
        self.txt_query.SetFocus()

    def copy_status_to_clipboard(self):
        if not self.btn_search.IsEnabled():
            found = getattr(self, "live_matches_count", 0)
            msg = (
                f"Avanzamento {self.current_percent} percento. "
                f"File esaminati {self.scanned_count}. Risultati trovati {found}."
            )
        else:
            found = self.lst_results.GetCount()
            msg = (
                f"Stato: {self.txt_status_progress.GetValue()} "
                f"Risultati in lista filtrata: {found}."
            )
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(msg))
            wx.TheClipboard.Close()
            ui.message("Stato copiato negli appunti.")
        else:
            ui.message("Impossibile copiare negli appunti.")

    def focus_status_progress(self, event=None):
        try:
            self.txt_status_progress.SetFocus()
            self.txt_status_progress.SetInsertionPoint(0)
            msg = self.txt_status_progress.GetValue().strip() or "Stato avanzamento non disponibile."
            ui.message(msg)
        except Exception:
            ui.message("Impossibile raggiungere lo stato di avanzamento.")

    def announce_progress(self):
        current_time = time.time()
        is_double_tap = (current_time - getattr(self, "last_alt_p_time", 0)) < 0.6
        self.last_alt_p_time = current_time
        if is_double_tap:
            self.copy_status_to_clipboard()
            return
        if not self.btn_search.IsEnabled():
            found = getattr(self, "live_matches_count", 0)
            msg = (
                f"Avanzamento ricerca: {self.current_percent} percento. "
                f"File esaminati: {self.scanned_count}. Trovati: {found}."
            )
        else:
            found = self.lst_results.GetCount()
            msg = (
                f"Stato: {self.txt_status_progress.GetValue()}. "
                f"Risultati in lista: {found}."
            )
        ui.message(msg)

    def on_filter_text(self, event):
        self.update_list_display()

    def on_general_char_hook(self, event):
        key = event.GetKeyCode()
        ctrl = event.ControlDown()
        alt = event.AltDown()
        
        if ctrl and key in (ord("F"), ord("f")):
            self.txt_filter.SetFocus()
            ui.message("Filtra risultati")
            return
        elif ctrl and key in (ord("H"), ord("h")) and event.ShiftDown():
            self.on_recall_path_history()
            return
        elif ctrl and key in (ord("H"), ord("h")):
            self.on_recall_query_history()
            return
        elif ctrl and key in (ord("U"), ord("u")):
            self.on_check_updates(None)
            return
        elif key == wx.WXK_F1:
            self.show_shortcuts_dialog()
            return
        elif ctrl and key in (ord("P"), ord("p")):
            self.on_print_results(None)
            return
        elif ctrl and key in (ord("E"), ord("e")):
            self.on_export_results(None)
            return
        elif ctrl and key in (ord("D"), ord("d")):
            self.on_add_bookmark(None)
            return
        elif alt and key in (ord("K"), ord("k")):
            self.on_take_screenshot(None)
            return
        elif alt and key in (ord("T"), ord("t")):
            self.on_search_all_pc(None)
            return
        elif alt and key in (ord("P"), ord("p")):
            self.announce_progress()
            return
        elif alt and key in (ord("S"), ord("s")):
            self.focus_status_progress()
            return
        elif key in (ord("S"), ord("s")) and not ctrl and not alt and not event.ShiftDown():
            focus = wx.Window.FindFocus()
            text_ctrls = (self.txt_query, self.txt_path, self.txt_custom_ext, self.txt_filter)
            if focus not in text_ctrls and not isinstance(focus, wx.TextCtrl):
                self.focus_status_progress()
                return
            event.Skip()
            return
        elif alt and key in (ord("N"), ord("n")):
            self.on_cancel_search(None)
            return
        elif alt and key in (ord("I"), ord("i")):
            self.on_show_info(None)
            return
        elif key == wx.WXK_ESCAPE:
            self._stop_search = True
            self.Destroy()
            return
        else:
            event.Skip()

    def on_close(self, event):
        self._stop_search = True
        self.Destroy()

    def on_browse(self, event):
        dlg = wx.DirDialog(
            self,
            "Seleziona la cartella o l'unità per la ricerca",
            defaultPath=self.txt_path.GetValue(),
        )
        if dlg.ShowModal() == wx.ID_OK:
            selected_path = dlg.GetPath()
            self.txt_path.SetValue(selected_path)
            save_last_path(selected_path)
            ui.message(f"Percorso impostato: {selected_path}.")
        dlg.Destroy()

    def on_take_screenshot(self, event):
        try:
            screen = wx.ScreenDC()
            size = screen.GetSize()
            bmp = wx.Bitmap(size.width, size.height)
            mem = wx.MemoryDC(bmp)
            mem.Blit(0, 0, size.width, size.height, screen, 0, 0)
            mem.SelectObject(wx.NullBitmap)

            pictures_dir = os.path.expanduser("~\\Pictures\\Catture di schermata")
            if not os.path.exists(pictures_dir):
                pictures_dir = os.path.expanduser("~\\OneDrive\\Immagini\\Catture di schermata")
                if not os.path.exists(pictures_dir):
                    os.makedirs(pictures_dir, exist_ok=True)

            filename = f"Screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            full_path = os.path.join(pictures_dir, filename)
            bmp.SaveFile(full_path, wx.BITMAP_TYPE_PNG)
            ui.message("Screenshot salvato con successo in Catture di schermata.")
        except Exception:
            ui.message("Impossibile salvare lo screenshot.")

    def on_export_results(self, event):
        if not self.current_matches:
            ui.message("Nessun risultato da esportare.")
            return

        wildcard_filters = "File di Testo (*.txt)|*.txt|Pagina Web HTML (*.html)|*.html|File CSV per Tabelle (*.csv)|*.csv"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dlg = wx.FileDialog(self, message="Esporta Risultati", 
                            defaultDir=get_dynamic_desktop_path(),
                            defaultFile=f"Risultati_Ricerca_{timestamp}",
                            wildcard=wildcard_filters, 
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            export_file = dlg.GetPath()
            ext = os.path.splitext(export_file)[1].lower()
            
            try:
                if ext == ".csv":
                    with open(export_file, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f, delimiter=';')
                        writer.writerow(["Numero", "Nome File", "Percorso", "Informazione Posizione", "Estratto"])
                        for idx, item in enumerate(self.current_matches, 1):
                            writer.writerow([idx, item['file_name'], item['file_path'], item.get('location_info', ''), item.get('snippet', '')])
                
                elif ext == ".html":
                    with open(export_file, "w", encoding="utf-8") as f:
                        f.write("<!DOCTYPE html><html lang='it'><head><meta charset='utf-8'><title>Risultati Ricerca</title></head><body>\n")
                        f.write(f"<h1>Risultati Ricerca - {APP_TITLE}</h1>\n")
                        f.write(f"<p>Parola cercata: <strong>{self.current_query}</strong></p>\n")
                        f.write(f"<p>Totale risultati trovati: <strong>{len(self.current_matches)}</strong></p><hr>\n")
                        for idx, item in enumerate(self.current_matches, 1):
                            f.write(f"<h2>{idx}. {item['file_name']}</h2>\n<ul>\n")
                            f.write(f"<li><strong>Percorso Completo:</strong> {item['file_path']}</li>\n")
                            if item.get("location_info"):
                                f.write(f"<li><strong>Posizione:</strong> {item['location_info']}</li>\n")
                            if item.get("snippet"):
                                f.write(f"<li><strong>Estratto:</strong> {item['snippet']}</li>\n")
                            f.write("</ul>\n<hr>\n")
                        f.write("</body></html>")
                
                else: 
                    with open(export_file, "w", encoding="utf-8") as f:
                        f.write(f"=== {APP_TITLE} v{APP_VERSION} - Risultati Ricerca ===\n")
                        f.write(f"Data: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                        f.write(f"Parola cercata: {self.current_query}\n")
                        f.write(f"Totale risultati: {len(self.current_matches)}\n\n")
                        for idx, item in enumerate(self.current_matches, 1):
                            loc = f" [{item.get('location_info', '')}]" if item.get("location_info") else ""
                            f.write(f"{idx}. {item['file_name']}{loc}\n    Percorso: {item['file_path']}\n")
                            if item.get("snippet"):
                                f.write(f"    Estratto: {item['snippet']}\n")
                            f.write("-" * 50 + "\n")
                
                ui.message("Risultati esportati con successo nel formato scelto.")
            except Exception:
                ui.message("Errore durante l'esportazione dei risultati.")
        dlg.Destroy()

    def on_print_results(self, event):
        total_matches = len(self.current_matches)
        if total_matches == 0:
            ui.message("Nessun risultato da stampare.")
            return

        dlg = wx.TextEntryDialog(
            self,
            f"Hai trovato {total_matches} risultati.\nQuanti vuoi stamparne partendo dal primo?\n(Lascia vuoto e premi Invio per stamparli tutti)",
            "Opzioni di Stampa"
        )
        
        if dlg.ShowModal() == wx.ID_OK:
            val = dlg.GetValue().strip()
            limit = total_matches
            if val.isdigit():
                limit = int(val)
                if limit <= 0:
                    limit = total_matches
                elif limit > total_matches:
                    limit = total_matches
            
            dlg.Destroy()
            
            temp_print_path = os.path.join(CONFIG_DIR, "stampa_temporanea.txt")
            try:
                with open(temp_print_path, "w", encoding="utf-8") as f:
                    f.write(f"=== {APP_TITLE} - Risultati Ricerca ===\n")
                    f.write(f"Data Stampa: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                    f.write(f"Parola cercata: {self.current_query}\n")
                    f.write(f"Risultati stampati: {limit} di {total_matches}\n\n")
                    
                    for idx, item in enumerate(self.current_matches[:limit], 1):
                        loc = f" [{item.get('location_info', '')}]" if item.get("location_info") else ""
                        f.write(f"{idx}. {item['file_name']}{loc}\n    Percorso: {item['file_path']}\n")
                        if item.get("snippet"):
                            f.write(f"    Estratto: {item['snippet']}\n")
                        f.write("-" * 40 + "\n")
                
                notepad_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "notepad.exe")
                if not os.path.exists(notepad_path):
                    notepad_path = "notepad.exe"
                    
                subprocess.Popen([notepad_path, "/p", temp_print_path])
                
                if limit == total_matches:
                    ui.message("Inviati tutti i risultati alla stampante predefinita.")
                else:
                    ui.message(f"Inviati i primi {limit} risultati alla stampante predefinita.")
            except Exception:
                ui.message("Impossibile stampare. Assicurati di avere una stampante configurata.")
        else:
            dlg.Destroy()
            ui.message("Stampa annullata.")


    def speak_selected_preview(self):
        sel = self.lst_results.GetSelection()
        if sel != wx.NOT_FOUND and sel in self.file_map:
            item = self.file_map[sel]
            snippet = item.get("snippet", "")
            loc = item.get("location_info", "")
            if snippet:
                ui.message(f"{loc}: {snippet}")
            else:
                ui.message(f"{item['file_name']} - Nessuna anteprima di testo disponibile.")

    def start_search_thread(self):
        query = self.txt_query.GetValue().strip()
        target_input = self.txt_path.GetValue().strip()
        filter_mode = self.combo_filter.GetSelection()
        custom_ext = self.txt_custom_ext.GetValue().strip().lower()
        if not custom_ext.startswith(".") and custom_ext:
            custom_ext = "." + custom_ext
        include_feed_raw = bool(self.chk_feed_raw.GetValue())

        if not query:
            ui.message("Inserire un testo da cercare.")
            return

        self._stop_search = False
        self.current_query = query
        self.current_percent = 0
        self.scanned_count = 0
        self.live_matches_count = 0
        self.last_feed_raw_occurrences = 0
        save_last_path(target_input)
        add_query_to_history(query)
        add_path_to_history(target_input)
        self.update_history_menu()

        try:
            self.txt_filter.SetValue("")
        except Exception:
            pass
        self.lst_results.Clear()
        # Evita che NVDA dica "sconosciuto" sulla lista vuota durante la scansione
        self.lst_results.Append("Ricerca in corso... attendere prego.")
        self.file_map.clear()
        self.current_matches = []
        self.gauge.SetValue(0)
        self.txt_status_progress.SetValue("Ricerca in corso: 0%...")
        
        self.btn_search.Disable()
        self.btn_cancel.Enable()

        ui.message(f"Ricerca avviata per '{query}'.")
        
        # --- INIZIO EARCONS NVDA (Avvio) ---
        if tones:
            try:
                wx.CallLater(100, lambda: tones.beep(800, 150))
            except Exception:
                pass
        # --- FINE EARCONS ---

        targets = [t.strip() for t in re.split(r"[;,]", target_input) if t.strip()]
        threading.Thread(
            target=self.run_search,
            args=(query, targets, filter_mode, custom_ext, include_feed_raw),
            daemon=True,
        ).start()

    def run_search(self, query, targets, filter_mode, custom_ext, include_feed_raw=False):
        raw_matches = []
        ignored = [
            "$recycle.bin",
            "system volume information",
            "appdata\\local\\temp",
        ]

        norm_query = normalize_search_text(query)
        terms = norm_query.split()
        img_exts = [".jpg", ".jpeg", ".png", ".bmp"]
        media_exts = [".mp4", ".mp3", ".mkv", ".avi", ".wav"]
        doc_exts = [
            ".txt", ".eml", ".log", ".csv", ".docx", ".doc", ".pdf",
            ".mbox", ".mbx", ".rss", ".xml", ".atom", ".opml",
        ]
        feed_file_exts = {".rss", ".xml", ".atom"}

        file_list = []
        rss_sources = []
        opml_files = []

        for folder in targets:
            if self._stop_search:
                break
            if folder.startswith("http://") or folder.startswith("https://"):
                rss_sources.append(folder)
                continue

            if not os.path.exists(folder):
                continue

            if os.path.isfile(folder):
                ext = os.path.splitext(folder)[1].lower()
                if ext == ".opml":
                    opml_files.append(os.path.normpath(folder))
                elif ext in feed_file_exts:
                    rss_sources.append(os.path.normpath(folder))
                else:
                    file_list.append(os.path.normpath(folder))
                continue

            for root, dirs, files in os.walk(folder):
                if self._stop_search:
                    break
                root_lower = root.lower()
                if any(ign in root_lower for ign in ignored):
                    continue

                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    full = os.path.normpath(os.path.join(root, file))
                    if is_thunderbird_junk_file(full):
                        continue
                    is_tb = is_thunderbird_mail_container(full)

                    if filter_mode == 1 and ext not in img_exts:
                        continue
                    elif filter_mode == 2 and ext not in media_exts:
                        continue
                    elif filter_mode == 3 and ext not in doc_exts and not is_tb:
                        continue
                    elif filter_mode == 4 and ext != custom_ext:
                        continue

                    if ext == ".opml":
                        opml_files.append(full)
                    elif ext in feed_file_exts and not is_thunderbird_feeds_path(full):
                        rss_sources.append(full)
                    else:
                        file_list.append(full)

        for opml_path in opml_files:
            if self._stop_search:
                break
            for url in parse_opml_urls(opml_path):
                if url not in rss_sources:
                    rss_sources.append(url)

        work_units = len(file_list) + len(rss_sources)
        if work_units <= 0:
            work_units = 1
        units_done = 0
        last_spoken_percent = -1
        feed_raw_total = 0

        def bump_progress():
            nonlocal units_done, last_spoken_percent
            units_done += 1
            self.scanned_count = units_done
            self.live_matches_count = len(raw_matches)
            percent = int((units_done / work_units) * 100)
            if percent > 100:
                percent = 100
            self.current_percent = percent
            if percent % 5 == 0 and percent != last_spoken_percent:
                last_spoken_percent = percent
                wx.CallAfter(self.update_progress, percent, units_done, work_units, len(raw_matches))

        missing_feedparser_announced = False
        for source in rss_sources:
            if self._stop_search:
                break
            if feedparser is None:
                if not missing_feedparser_announced:
                    missing_feedparser_announced = True
                    wx.CallAfter(
                        ui.message,
                        "Modulo feedparser non installato: ricerca RSS non disponibile.",
                    )
                bump_progress()
                continue
            try:
                raw_matches.extend(search_online_or_local_feed(source, terms))
            except Exception:
                pass
            bump_progress()

        for file_path in file_list:
            if self._stop_search:
                break

            file_name = os.path.basename(file_path)
            ext = os.path.splitext(file_name)[1].lower()
            is_feed = is_thunderbird_feeds_path(file_path)
            prefix = f"[{ext.replace('.', '').upper()}]" if ext else "[FILE]"

            try:
                mtime = os.path.getmtime(file_path)
            except Exception:
                mtime = 0

            try:
                name_matched = text_matches_terms(file_name, terms)
                found_in_content = False

                if ext in img_exts:
                    img_text = normalize_search_text(deep_ocr_jpg_scan(file_path))
                    if all(term in img_text for term in terms):
                        raw_matches.append({
                            "file_path": file_path,
                            "file_name": file_name,
                            "prefix": "[IMG-TEXT]",
                            "mtime": mtime,
                            "line_number": None,
                            "location_info": "Testo visivo",
                            "snippet": f"Trovato testo visivo contenente '{query}'.",
                        })
                        found_in_content = True

                elif is_feed:
                    if is_thunderbird_junk_file(file_path):
                        bump_progress()
                        continue
                    feed_hits, raw_occ = search_thunderbird_feed_file(
                        file_path, terms, mtime, include_raw_lines=include_feed_raw
                    )
                    feed_raw_total += raw_occ
                    if feed_hits:
                        raw_matches.extend(feed_hits)
                        found_in_content = True

                elif ext in [".mbox", ".mbx"] or (is_thunderbird_mail_container(file_path) and not is_feed):
                    try:
                        for msg_idx, msg in iter_mbox_like_messages(file_path, prefer_from_split=True):
                            if self._stop_search:
                                break
                            subject = decode_email_header(str(msg.get("subject", "")))
                            sender = decode_email_header(str(msg.get("from", "")))
                            body = get_clean_email_text(msg)
                            msg_ts = message_date_timestamp(msg, fallback=mtime)
                            date_label = format_email_date_label(msg, fallback_ts=msg_ts)
                            date_suffix = f" {date_label}" if date_label else ""
                            hay = f"{subject}\n{sender}\n{body}"
                            if not text_matches_terms(hay, terms):
                                continue
                            snippet = ""
                            if body:
                                for line in body.split("\n"):
                                    if text_matches_terms(line, terms):
                                        snippet = line.strip()
                                        break
                                if not snippet:
                                    snippet = " ".join(body.split())[:200]
                            if not snippet:
                                snippet = f"{subject} — {sender}".strip(" —")
                            raw_matches.append({
                                "file_path": file_path,
                                "file_name": file_name,
                                "prefix": "[MBOX]",
                                "mtime": msg_ts,
                                "line_number": msg_idx,
                                "location_info": f"Msg {msg_idx + 1}{date_suffix}",
                                "snippet": snippet[:200],
                                "viewer_text": _format_email_viewer_text(msg),
                            })
                            found_in_content = True
                    except Exception:
                        pass

                elif ext in [".txt", ".eml", ".log", ".csv", custom_ext]:
                    try:
                        with open(file_path, "rb") as f:
                            raw_data = f.read()
                        if raw_data.startswith(b"\xff\xfe") or raw_data.startswith(b"\xfe\xff"):
                            text_data = raw_data.decode("utf-16", errors="ignore")
                        else:
                            try:
                                text_data = raw_data.decode("utf-8")
                            except UnicodeDecodeError:
                                text_data = raw_data.decode("latin1", errors="ignore")
                        text_data = text_data.replace("\x00", "")
                        lines = text_data.split("\n")
                        for idx, line in enumerate(lines):
                            cleaned_line = clean_eml_text(line) if ext == ".eml" else line
                            if text_matches_terms(cleaned_line, terms):
                                start_i = max(0, idx - 2)
                                end_i = min(len(lines), idx + 3)
                                raw_snip = "".join(lines[start_i:end_i]).strip()
                                snippet = clean_eml_text(raw_snip) if ext == ".eml" else raw_snip
                                raw_matches.append({
                                    "file_path": file_path,
                                    "file_name": file_name,
                                    "prefix": prefix,
                                    "mtime": mtime,
                                    "line_number": idx + 1,
                                    "location_info": f"Riga {idx + 1}",
                                    "snippet": snippet,
                                })
                                found_in_content = True
                    except Exception:
                        pass
                elif ext in [".docx", ".doc"]:
                    paragraphs = extract_paragraphs_from_docx(file_path)
                    found_doc = False
                    for idx, p_text in enumerate(paragraphs):
                        if text_matches_terms(p_text, terms):
                            found_doc = True
                            start_i = max(0, idx - 1)
                            end_i = min(len(paragraphs), idx + 2)
                            snippet = " \n".join(paragraphs[start_i:end_i])
                            raw_matches.append({
                                "file_path": file_path,
                                "file_name": file_name,
                                "prefix": prefix,
                                "mtime": mtime,
                                "line_number": None,
                                "paragraph_index": idx + 1,
                                "location_info": f"Paragrafo {idx + 1}",
                                "snippet": snippet,
                            })
                            found_in_content = True
                    if not found_doc and ext == ".doc":
                        try:
                            with open(file_path, "rb") as f:
                                raw_data = normalize_search_text(f.read(4194304).decode("latin1", errors="ignore"))
                                if text_matches_terms(raw_data, terms):
                                    raw_matches.append({
                                        "file_path": file_path,
                                        "file_name": file_name,
                                        "prefix": prefix,
                                        "mtime": mtime,
                                        "line_number": None,
                                        "location_info": "Documento Word",
                                        "snippet": f"Trovato testo nel file Word: '{query}'.",
                                    })
                                    found_in_content = True
                        except Exception:
                            pass
                elif ext == ".pdf":
                    pdf_ts = pdf_info_date_timestamp(file_path, fallback=mtime)
                    date_label = format_file_date_label(pdf_ts)
                    date_suffix = f" {date_label}" if date_label else ""
                    pdf_lines = extract_lines_from_pdf(file_path)
                    for idx, line in enumerate(pdf_lines):
                        if text_matches_terms(line, terms):
                            start_i = max(0, idx - 1)
                            end_i = min(len(pdf_lines), idx + 2)
                            snippet = " ".join(pdf_lines[start_i:end_i])
                            raw_matches.append({
                                "file_path": file_path,
                                "file_name": file_name,
                                "prefix": prefix,
                                "mtime": pdf_ts,
                                "line_number": None,
                                "location_info": f"Testo PDF{date_suffix}",
                                "snippet": snippet,
                            })
                            found_in_content = True
                            break
                    if name_matched and not found_in_content:
                        raw_matches.append({
                            "file_path": file_path,
                            "file_name": file_name,
                            "prefix": prefix,
                            "mtime": pdf_ts,
                            "line_number": None,
                            "location_info": f"Nome File{date_suffix}",
                            "snippet": f"Corrispondenza nel nome: '{file_name}'",
                        })
                        found_in_content = True

                if name_matched and not found_in_content:
                    raw_matches.append({
                        "file_path": file_path,
                        "file_name": file_name,
                        "prefix": prefix,
                        "mtime": mtime,
                        "line_number": None,
                        "location_info": "Nome File",
                        "snippet": f"Corrispondenza nel nome: '{file_name}'",
                    })

            except Exception:
                pass

            bump_progress()

        self.current_matches = raw_matches
        self.last_feed_raw_occurrences = feed_raw_total
        wx.CallAfter(self.finish_search, len(raw_matches))

    def sort_and_display_matches(self, sort_type="recent_first"):
        self.current_sort = sort_type
        if sort_type == "recent_first":
            self.current_matches.sort(
                key=lambda x: (x.get("mtime") or 0, x.get("line_number") or 0),
                reverse=True,
            )
        elif sort_type == "oldest_first":
            self.current_matches.sort(
                key=lambda x: (x.get("mtime") or 0, x.get("line_number") or 0),
                reverse=False,
            )
        elif sort_type == "name":
            self.current_matches.sort(key=lambda x: (x.get("file_name") or "").lower())
        self.update_list_display()

    def update_list_display(self):
        filter_text = ""
        try:
            filter_text = self.txt_filter.GetValue().lower().strip()
        except Exception:
            filter_text = ""
        self.lst_results.Clear()
        self.file_map.clear()
        for item in self.current_matches:
            loc = f" ({item['location_info']})" if item.get("location_info") else ""
            display_str = f"{item['prefix']} {item['file_name']}{loc} -- ({item['file_path']})"
            if filter_text:
                searchable = f"{display_str} {item.get('snippet', '')}".lower()
                if filter_text not in searchable:
                    continue
            idx = self.lst_results.Append(display_str)
            self.file_map[idx] = item

    def update_progress(self, percent, current, total, matches):
        self.gauge.SetValue(percent)
        text = f"Avanzamento: {percent}% ({current}/{total} elementi, {matches} risultati)"
        self.txt_status_progress.SetValue(text)
        ui.message(f"Ricerca al {percent} percento")

    def finish_search(self, matches):
        self.gauge.SetValue(100)
        self.current_percent = 100
        feed_raw = getattr(self, "last_feed_raw_occurrences", 0) or 0
        feed_note = ""
        feed_speak = ""
        if feed_raw > 0 and feed_raw != matches:
            feed_note = (
                f" Nei feed: {matches} articoli distinti "
                f"(nel file grezzo la parola compare circa {feed_raw} volte, come in Notepad++)."
            )
            feed_speak = (
                f" Nei feed sono {matches} articoli. "
                f"Nel testo grezzo la parola compare circa {feed_raw} volte."
            )

        if self._stop_search:
            text = (
                f"Ricerca interrotta al {self.current_percent}% ({self.scanned_count} elementi). "
                f"Salvati {matches} risultati.{feed_note}"
            )
            ui.message(f"Ricerca annullata. Conservati {matches} risultati.{feed_speak}")
            if tones:
                try:
                    wx.CallLater(100, lambda: tones.beep(400, 300))
                except Exception:
                    pass
        else:
            text = (
                f"Ricerca completata: 100% ({self.scanned_count} elementi). "
                f"Trovati {matches} risultati.{feed_note}"
            )
            ui.message(f"Ricerca completata. Trovati {matches} risultati ordinati dal più recente.{feed_speak}")
            if tones:
                try:
                    if matches > 0:
                        wx.CallLater(100, lambda: tones.beep(1000, 150))
                        wx.CallLater(300, lambda: tones.beep(1500, 200))
                    else:
                        wx.CallLater(100, lambda: tones.beep(600, 300))
                except Exception:
                    pass
            
        self.txt_status_progress.SetValue(text)
        self.btn_search.Enable()
        self.btn_cancel.Disable()

        self.sort_and_display_matches(sort_type=self.current_sort)
        
        if matches > 0:
            self.lst_results.SetSelection(0)
            self.lst_results.SetFocus()

    def on_list_char_hook(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_RETURN:
            self.open_selected_file()
        elif key in [wx.WXK_SPACE, wx.WXK_F4]:
            self.speak_selected_preview()
        elif key == wx.WXK_WINDOWS_MENU:
            self.on_context_menu(None)
        elif key == wx.WXK_ESCAPE:
            self._stop_search = True
            self.Destroy()
        else:
            event.Skip()

    def on_open_file_event(self, event):
        self.open_selected_file()

    def open_selected_file(self):
        sel = self.lst_results.GetSelection()
        if sel != wx.NOT_FOUND and sel in self.file_map:
            item = self.file_map[sel]
            file_to_open = item["file_path"]
            line_num = item.get("line_number")
            ext = os.path.splitext(file_to_open)[1].lower()
            prefix = item.get("prefix", "")

            if prefix == "[FEED-RIGA]":
                if line_num:
                    ui.message(f"Apertura alla riga {line_num} nel file feed")
                    jump_to_line_in_editor(file_to_open, line_num)
                else:
                    ui.message("Riga non disponibile.")
                return

            if prefix in ("[RSS]", "[FEED]"):
                url = item.get("article_url") or file_to_open
                if url and (str(url).startswith("http://") or str(url).startswith("https://")):
                    ui.message(
                        "Apertura articolo nel browser. "
                        "Se compare un banner sui cookie, accettarlo per leggere la notizia."
                    )
                    webbrowser.open(url)
                    return
                if prefix == "[FEED]" and line_num:
                    ui.message(f"Apertura alla riga {line_num}: {os.path.basename(file_to_open)}")
                    jump_to_line_in_editor(file_to_open, line_num)
                    return
                ui.message("Collegamento articolo non disponibile.")
                return

            if prefix == "[MBOX]":
                ui.message(f"Apertura messaggio {line_num + 1} dall'archivio MBOX")
                viewer = MboxViewerFrame(
                    self,
                    file_to_open,
                    line_num,
                    self.current_query,
                    cached_text=item.get("viewer_text"),
                )
                viewer.Show()
                return

            if ext in [".docx", ".doc"]:
                ui.message(f"Apertura file Word: {os.path.basename(file_to_open)}")
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "open", file_to_open, None, None, 1)
                except Exception:
                    pass
                return
            
            if ext == ".eml":
                ui.message(f"Apertura email nel lettore interno: {os.path.basename(file_to_open)}")
                viewer = EmlViewerFrame(self, file_to_open, self.current_query)
                viewer.Show()
                return

            if line_num:
                ui.message(f"Apertura alla riga {line_num}: {os.path.basename(file_to_open)}")
                jump_to_line_in_editor(file_to_open, line_num)
            else:
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "open", file_to_open, None, None, 1)
                    ui.message(f"Apertura file: {os.path.basename(file_to_open)}")
                except Exception:
                    ui.message("Impossibile aprire il file selezionato.")

    def on_context_menu(self, event):
        sel = self.lst_results.GetSelection()
        if sel == wx.NOT_FOUND or sel not in self.file_map:
            return

        item_data = self.file_map[sel]
        file_path = item_data["file_path"]
        snippet = item_data["snippet"]

        menu = wx.Menu()
        item_open = menu.Append(wx.ID_ANY, "Apri File (alla riga esatta)\tINVIO")
        item_preview = menu.Append(wx.ID_ANY, "Ascolta Anteprima Vocale\tSPAZIO")
        item_copy_snippet = menu.Append(wx.ID_ANY, "Copia Blocco Notizia / Frase con parola chiave")
        item_copy_path = menu.Append(wx.ID_ANY, "Copia Percorso Completo")
        item_copy_text = menu.Append(wx.ID_ANY, "Copia Testo")
        item_copy_image = menu.Append(wx.ID_ANY, "Copia Immagine")
        item_save_image = menu.Append(wx.ID_ANY, "Salva Immagine...")
        item_copy_to = menu.Append(wx.ID_ANY, "Invia / Copia File in un'altra cartella...")
        item_open_folder = menu.Append(wx.ID_ANY, "Apri Cartella Contenitore")

        menu.AppendSeparator()
        sort_submenu = wx.Menu()
        item_sort_recent = sort_submenu.Append(wx.ID_ANY, "Dal Più Recente al Meno Recente")
        item_sort_oldest = sort_submenu.Append(wx.ID_ANY, "Dal Meno Recente al Più Recente")
        item_sort_name = sort_submenu.Append(wx.ID_ANY, "Alfabeticamente per Nome (A-Z)")
        menu.AppendSubMenu(sort_submenu, "Ordinamento Risultati")

        self.Bind(wx.EVT_MENU, lambda e: self.open_selected_file(), item_open)
        self.Bind(wx.EVT_MENU, lambda e: wx.CallLater(250, self.speak_selected_preview), item_preview)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_snippet_to_clipboard(snippet), item_copy_snippet)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_path_to_clipboard(file_path), item_copy_path)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_text_to_clipboard(item_data), item_copy_text)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_image_to_clipboard(item_data), item_copy_image)
        self.Bind(wx.EVT_MENU, lambda e: self.save_image_to_file(item_data), item_save_image)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_file_to_destination(file_path), item_copy_to)
        self.Bind(wx.EVT_MENU, lambda e: self.open_containing_folder(file_path), item_open_folder)

        self.Bind(wx.EVT_MENU, lambda e: self.change_sort_order("recent_first"), item_sort_recent)
        self.Bind(wx.EVT_MENU, lambda e: self.change_sort_order("oldest_first"), item_sort_oldest)
        self.Bind(wx.EVT_MENU, lambda e: self.change_sort_order("name"), item_sort_name)

        self.PopupMenu(menu)
        menu.Destroy()

    def change_sort_order(self, sort_type):
        self.sort_and_display_matches(sort_type)
        save_sort_preference(sort_type)
        if sort_type == "recent_first":
            ui.message("Risultati ordinati dal più recente al meno recente.")
        elif sort_type == "oldest_first":
            ui.message("Risultati ordinati dal meno recente al più recente.")
        elif sort_type == "name":
            ui.message("Risultati ordinati alfabeticamente per nome.")

    def copy_snippet_to_clipboard(self, snippet):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(snippet))
            wx.TheClipboard.Close()
            ui.message("Blocco notizia / frase copiata negli appunti!")

    def copy_path_to_clipboard(self, file_path):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(file_path))
            wx.TheClipboard.Close()
            ui.message("Percorso copiato negli appunti!")

    def copy_text_to_clipboard(self, item_data):
        if isinstance(item_data, str):
            file_path = item_data
            prefix = ""
            item_data = {"file_path": file_path, "prefix": ""}
        else:
            file_path = item_data["file_path"]
            prefix = item_data.get("prefix", "")
        ext = os.path.splitext(file_path)[1].lower()

        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"]:
            ui.message(
                "Questo risultato è un file immagine: usa «Copia Immagine». "
                "Nessun testo estraibile qui."
            )
            return

        if prefix in ("[RSS]", "[FEED]"):
            url = item_data.get("article_url") or file_path
            text_content = (
                f"{item_data.get('file_name', '')}\n"
                f"{item_data.get('snippet', '')}\n"
                f"Link: {url}"
            )
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text_content))
                wx.TheClipboard.Close()
                ui.message("Testo copiato negli appunti!")
            return

        text_content = ""
        if ext in [".docx", ".doc"]:
            paragraphs = extract_paragraphs_from_docx(file_path)
            text_content = "\n".join(paragraphs)
        elif ext == ".pdf":
            lines = extract_lines_from_pdf(file_path)
            text_content = "\n".join(lines)
            if not text_content.strip():
                if get_best_pdf_page_image(file_path):
                    ui.message(
                        "Questo PDF è una scansione: non c’è testo da copiare. "
                        "Usa «Copia Immagine» per la pagina grafica."
                    )
                else:
                    ui.message(
                        "Nessun testo estraibile con il nostro lettore "
                        "(font speciali o PDF protetto). "
                        "Prova «Copia Immagine» oppure Apri file "
                        "(Edge/NVDA spesso lo leggono)."
                    )
                return
        elif ext in [".txt", ".eml", ".log", ".csv"] or prefix == "[FEED-RIGA]":
            try:
                with open(file_path, "rb") as f:
                    raw_data = f.read()
                if raw_data.startswith(b'\xff\xfe') or raw_data.startswith(b'\xfe\xff'):
                    text_content = raw_data.decode("utf-16", errors="ignore")
                else:
                    try:
                        text_content = raw_data.decode("utf-8")
                    except UnicodeDecodeError:
                        text_content = raw_data.decode("latin1", errors="ignore")
                text_content = text_content.replace('\x00', '')
                if ext == ".eml":
                    text_content = clean_eml_text(text_content)
            except Exception:
                pass

        if text_content:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text_content))
                wx.TheClipboard.Close()
                ui.message("Testo copiato negli appunti!")
        else:
            ui.message("Impossibile copiare il testo da questo formato.")

    def copy_image_to_clipboard(self, item_data):
        if isinstance(item_data, str):
            file_path = item_data
            prefix = ""
        else:
            file_path = item_data["file_path"]
            prefix = item_data.get("prefix", "")
        ext = os.path.splitext(file_path)[1].lower()

        if prefix in ("[RSS]", "[FEED]", "[MBOX]", "[FEED-RIGA]"):
            ui.message("Nessuna immagine da copiare per questo risultato.")
            return

        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"]:
            try:
                img = wx.Image(file_path, wx.BITMAP_TYPE_ANY)
                if img.IsOk() and wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.BitmapDataObject(wx.Bitmap(img)))
                    wx.TheClipboard.Close()
                    ui.message("Immagine copiata negli appunti!")
                    return
            except Exception:
                pass
            ui.message("Impossibile copiare l’immagine.")
            return

        if ext == ".pdf":
            ui.message("Estrazione immagine dal PDF in corso…")
            try:
                record = get_best_pdf_page_image(file_path)
                if record is None:
                    logos = extract_images_from_pdf(file_path)
                    if logos:
                        top = logos[0]
                        ui.message(
                            f"Trovato solo logo o icona "
                            f"({top['w']} per {top['h']} pixel), "
                            f"non una pagina intera. "
                            f"Prova «Copia Testo» oppure Apri file."
                        )
                    else:
                        ui.message(
                            "Nessuna pagina grafica in questo PDF "
                            "(spesso è testo vettoriale: usa «Copia Testo» "
                            "oppure Apri file)."
                        )
                    return
                img = pdf_image_record_to_wx_image(record)
                if img is not None and img.IsOk():
                    bmp = wx.Bitmap(img)
                    if bmp.IsOk() and wx.TheClipboard.Open():
                        wx.TheClipboard.SetData(wx.BitmapDataObject(bmp))
                        wx.TheClipboard.Close()
                        ui.message(
                            f"Pagina grafica copiata negli appunti "
                            f"({img.GetWidth()} per {img.GetHeight()} pixel; "
                            f"originale {record['w']}×{record['h']})!"
                        )
                        return
            except Exception:
                pass
            ui.message(
                "Impossibile copiare l’immagine da questo PDF "
                "(file troppo grande o formato non supportato). "
                "Puoi usare «Invia / Copia File in un'altra cartella...» "
                "oppure Apri file."
            )
            return

        ui.message("Nessuna immagine da copiare in questo formato.")

    def save_image_to_file(self, item_data):
        if isinstance(item_data, str):
            file_path = item_data
            prefix = ""
        else:
            file_path = item_data["file_path"]
            prefix = item_data.get("prefix", "")
        ext = os.path.splitext(file_path)[1].lower()
        base_name = os.path.splitext(os.path.basename(file_path))[0] or "immagine"

        if prefix in ("[RSS]", "[FEED]", "[MBOX]", "[FEED-RIGA]"):
            ui.message("Nessuna immagine da salvare per questo risultato.")
            return

        default_dir = get_dynamic_desktop_path()
        wildcard = (
            "JPEG (*.jpg)|*.jpg|"
            "PNG (*.png)|*.png|"
            "Bitmap (*.bmp)|*.bmp|"
            "Tutti i file (*.*)|*.*"
        )

        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"]:
            dlg = wx.FileDialog(
                self,
                "Salva immagine",
                defaultDir=default_dir,
                defaultFile=os.path.basename(file_path),
                wildcard=wildcard,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            )
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                return
            dest = dlg.GetPath()
            dlg.Destroy()
            try:
                shutil.copy2(file_path, dest)
                ui.message(f"Immagine salvata in {dest}")
            except Exception:
                ui.message("Impossibile salvare l’immagine.")
            return

        if ext == ".pdf":
            ui.message("Estrazione immagine dal PDF in corso…")
            record = get_best_pdf_page_image(file_path)
            if record is None:
                logos = extract_images_from_pdf(file_path)
                if logos:
                    ui.message(
                        "Trovato solo logo o icona, non una pagina da salvare. "
                        "Prova «Copia Testo» oppure Apri file."
                    )
                else:
                    ui.message("Nessuna pagina grafica da salvare in questo PDF.")
                return
            default_ext = ".jpg" if record["kind"] == "jpeg" else ".png"
            dlg = wx.FileDialog(
                self,
                "Salva immagine dal PDF",
                defaultDir=default_dir,
                defaultFile=base_name + default_ext,
                wildcard=wildcard,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            )
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                return
            dest = dlg.GetPath()
            dlg.Destroy()
            if not os.path.splitext(dest)[1]:
                dest = dest + default_ext
            if save_pdf_image_record_to_path(record, dest):
                ui.message(
                    f"Immagine salvata "
                    f"({record['w']} per {record['h']} pixel) in {dest}"
                )
            else:
                ui.message("Impossibile salvare l’immagine dal PDF.")
            return

        ui.message("Nessuna immagine da salvare in questo formato.")

    def copy_content_or_image_to_clipboard(self, item_data):
        """Compatibilità: reindirizza a Copia Testo."""
        self.copy_text_to_clipboard(item_data)

    def copy_file_to_destination(self, file_path):
        dlg = wx.DirDialog(
            self,
            "Seleziona la cartella dove copiare il file",
            defaultPath=get_dynamic_desktop_path(),
        )
        if dlg.ShowModal() == wx.ID_OK:
            dest_dir = dlg.GetPath()
            try:
                shutil.copy(file_path, dest_dir)
                ui.message(f"File copiato con successo in {dest_dir}!")
            except Exception:
                ui.message("Impossibile copiare il file nella destinazione.")
        dlg.Destroy()

    def open_containing_folder(self, file_path):
        try:
            subprocess.Popen(f'explorer /select,"{file_path}"')
            ui.message("Apertura cartella contenitore in corso...")
        except Exception:
            ui.message("Impossibile aprire la cartella contenitore.")


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    @scriptHandler.script(
        description="Apri la finestra principale di Ricerca Testuale",
        category="Ricerca Testuale Accesso Digitale",
        gesture="kb:NVDA+shift+control+f",
    )
    def script_openSearch(self, gesture):
        try:
            wx.CallAfter(self.open_search_window)
        except Exception as e:
            ui.message(f"Errore avvio ricerca: {e}")

    @scriptHandler.script(
        description="Mostra la finestra dei comandi rapidi",
        category="Ricerca Testuale Accesso Digitale",
        gesture="kb:NVDA+shift+control+s",
    )
    def script_showShortcuts(self, gesture):
        try:
            wx.CallAfter(self.show_shortcuts_dialog)
        except Exception as e:
            ui.message(f"Errore apertura comandi: {e}")

    @scriptHandler.script(
        description="Apri la pagina delle Donazioni PayPal",
        category="Ricerca Testuale Accesso Digitale",
        gesture="kb:NVDA+shift+control+d",
    )
    def script_openDonation(self, gesture):
        webbrowser.open(DONATION_URL)
        ui.message("Apertura pagina donazioni...")

    def open_search_window(self):
        try:
            frame = SearchFrame()
            frame.Show()
            frame.Raise()
            frame.txt_query.SetFocus()
            if check_first_run_update():
                wx.CallLater(600, frame.show_whats_new_dialog)
        except Exception as e:
            ui.message(f"Impossibile aprire la finestra di ricerca: {e}")

    def show_shortcuts_dialog(self):
        try:
            frame = ShortcutsFrame(None)
            frame.Show()
            frame.Raise()
        except Exception as e:
            ui.message(f"Impossibile aprire i comandi: {e}")
