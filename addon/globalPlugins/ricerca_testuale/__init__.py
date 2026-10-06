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

# feedparser vendored in lib/ (NVDA non lo include): RSS/Atom senza pip esterno
_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    import rtad_ocr
except ImportError:
    rtad_ocr = None

try:
    import rtad_guida_pratica
except ImportError:
    rtad_guida_pratica = None

try:
    import rtad_epub
except ImportError:
    rtad_epub = None

try:
    import rtad_zip
except ImportError:
    rtad_zip = None

addonHandler.initTranslation()

APP_TITLE = "Ricerca Testuale Accesso Digitale"
APP_VERSION = "1.6.4"
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

OCR_CACHE_DIR = os.path.join(CONFIG_DIR, "ocr_cache")
if rtad_ocr is not None:
    try:
        rtad_ocr.configure(OCR_CACHE_DIR)
    except Exception:
        pass

# Mute annunci RTAD (gemello di F7 Standalone). Voce/velocità = NVDA.
_rtad_speech_active = True
_rtad_speech_settings_loaded = False


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

def normalize_search_targets(target_input):
    """Spezza percorsi multipli e toglie virgolette / spazi (incolla da Esplora risorse)."""
    out = []
    for t in re.split(r"[;,]", target_input or ""):
        t = (t or "").strip().strip('"').strip("'").strip()
        if t:
            out.append(os.path.expandvars(t))
    return out


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


def is_rtad_noise_file(path):
    """File/cartelle di rumore: log interni, cache editor, WinSxS (riempiono i risultati)."""
    if not path:
        return False
    name = os.path.basename(path).lower()
    if name == "rtad_debug.log" or name == "rtad_activity.log":
        return True
    if name.startswith("log_rtad_") and name.endswith(".txt"):
        return True
    low = path.replace("/", "\\").lower()
    if "\\rtad_standalone\\" in low and name.endswith((".log", ".txt")):
        return True
    if "\\ricercatestualeaccessodigitale\\" in low and name.endswith((".log", ".txt")):
        return True
    if "\\rtad_data\\" in low and name.endswith((".log", ".txt")):
        return True
    if "\\appdata\\roaming\\cursor\\" in low:
        return True
    if "\\appdata\\roaming\\code\\" in low:
        return True
    if "indexeddb" in low and name.endswith(".log"):
        return True
    if "\\windows\\winsxs\\" in low:
        return True
    if "\\windows\\installer\\" in low:
        return True
    if "\\windows\\servicing\\" in low:
        return True
    if "\\windows\\system32\\" in low or "\\windows\\syswow64\\" in low:
        return True
    if name == "license.rtf":
        return True
    return False


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


def open_shared_binary(file_path):
    """Apre in sola lettura con condivisione (Thunderbird aperto). Restituisce file binario."""
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


def _parse_mbox_raw_message(raw):
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


def _iter_mbox_from_lines_streaming(file_path, should_abort=None, max_msg_bytes=None):
    """Yield (index, message) scorrendo From_ senza caricare tutta la casella in RAM.

    Messaggi oltre max_msg_bytes: si leggono comunque i primi max_msg_bytes
    (testata + inizio allegati), così le ricette grandi non spariscono del tutto.
    Prima (tetto 12 MB) quei messaggi venivano saltati in silenzio.
    """
    if max_msg_bytes is None:
        max_msg_bytes = MAX_SINGLE_MBOX_MSG_BYTES
    f = open_shared_binary(file_path)
    current = -1
    start_pos = None
    skipped_oversized = 0

    def _emit(msg_idx, start, end):
        nonlocal skipped_oversized
        size = end - start
        if size <= 0:
            return None
        read_size = size
        if max_msg_bytes > 0 and size > max_msg_bytes:
            read_size = max_msg_bytes
            skipped_oversized += 1
            logging.info(
                f"Messaggio MBOX {msg_idx + 1} grande ({size} byte) in {file_path}: "
                f"lettura primi {read_size} byte."
            )
        cur = f.tell()
        f.seek(start)
        raw = f.read(read_size)
        f.seek(cur)
        if not raw:
            return None
        try:
            return _parse_mbox_raw_message(raw)
        except Exception:
            return None

    try:
        while True:
            if should_abort and should_abort():
                break
            line_start = f.tell()
            line = f.readline()
            if not line:
                if start_pos is not None and current >= 0:
                    msg = _emit(current, start_pos, line_start)
                    if msg is not None:
                        yield current, msg
                break
            if line.startswith(b"From "):
                if start_pos is not None and current >= 0:
                    msg = _emit(current, start_pos, line_start)
                    if msg is not None:
                        yield current, msg
                current += 1
                start_pos = line_start
    finally:
        try:
            f.close()
        except Exception:
            pass
        if skipped_oversized:
            logging.info(
                f"Casella {file_path}: {skipped_oversized} messaggi oltre "
                f"{max_msg_bytes} byte (letti in forma troncata)."
            )


def iter_mbox_like_messages(file_path, prefer_from_split=False, should_abort=None):
    """Yield (index, email.message) in streaming From_ (anche caselle enormi).

    Nota: il modulo stdlib ``mailbox`` NON è disponibile in NVDA.
    prefer_from_split resta per compatibilità API.
    """
    try:
        for item in _iter_mbox_from_lines_streaming(file_path, should_abort=should_abort):
            yield item
    except Exception:
        return


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

PROFILES_MAX = 20

# Estensioni per filtri di ricerca (liste uniche, allineate a Standalone e Add-on)
IMG_EXTS = (
    ".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".gif",
    ".tif", ".tiff", ".webp", ".ico",
)
MEDIA_EXTS = (
    ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wav", ".wma",
    ".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".webm",
    ".mpg", ".mpeg", ".3gp",
)
DOC_EXTS = (
    ".txt", ".log", ".csv", ".md", ".rtf",
    ".html", ".htm",
    ".docx", ".doc", ".odt",
    ".pdf",
    ".epub",
    ".eml", ".mbox", ".mbx",
    ".rss", ".xml", ".atom", ".opml",
)
TEXT_LIKE_EXTS = (
    ".txt", ".log", ".csv", ".md", ".rtf", ".html", ".htm",
)


MAX_CONTENT_SCAN_BYTES = 40 * 1024 * 1024  # 40 MB — DOC/testo generico (non posta)
MAX_PDF_SCAN_BYTES = 80 * 1024 * 1024  # 80 MB — PDF
# Caselle Thunderbird / MBOX: nessun tetto (streaming). Un tetto 2 GB saltava
# in silenzio le INBOX/Tutti i messaggi Gmail più grandi.
MAX_MAILBOX_SCAN_BYTES = 0  # 0 = illimitato
# 0 = nessun tetto sul singolo messaggio (streaming un messaggio alla volta).
MAX_SINGLE_MBOX_MSG_BYTES = 0
FILE_CONTENT_SOFT_TIMEOUT_SEC = 12
FILE_CONTENT_SOFT_TIMEOUT_PDF_SEC = 20
MAX_EML_READ_BYTES = 12 * 1024 * 1024
MAX_EMAIL_PDF_ATTACH_BYTES = 20 * 1024 * 1024
MAX_DOCX_XML_BYTES = 25 * 1024 * 1024
_OLE_MAGIC = b"\xD0\xCF\x11\xE0"
_ZIP_LOCAL_MAGIC = b"PK\x03\x04"
_ZIP_EMPTY_MAGIC = b"PK\x05\x06"


def safe_file_size(path):
    try:
        return os.path.getsize(path)
    except Exception:
        return -1


def is_email_mailbox_path(path):
    """True per .eml/.mbox/.mbx e contenitori posta Thunderbird (non indici .msf)."""
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext in (".eml", ".mbox", ".mbx"):
        return True
    return is_thunderbird_mail_container(path)


def content_scan_allowed(path, max_bytes=None):
    """False se il file è troppo grande da leggere per intero in ricerca.

    Le caselle di posta non hanno tetto: streaming messaggio per messaggio.
    Un tetto 2 GB escludeva in silenzio le INBOX/Tutti i messaggi Gmail grandi.
    I PDF hanno un tetto dedicato (più alto del generico).
    Se la dimensione non è leggibile (sz < 0: OneDrive, path lungo, blocco),
    si tenta comunque la lettura invece di saltare.
    """
    if is_email_mailbox_path(path):
        return True
    sz = safe_file_size(path)
    if sz < 0:
        return True
    if max_bytes is not None:
        return sz <= max_bytes
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return sz <= MAX_PDF_SCAN_BYTES
    return sz <= MAX_CONTENT_SCAN_BYTES



def iter_pdf_attachments(msg, max_bytes=None):
    """Yield (filename, pdf_bytes, meta) dagli allegati PDF di un messaggio email.

    meta: empty=True se dichiarato ma senza corpo (IMAP non scaricato);
    external=path se X-Mozilla-External-Attachment-URL punta a un file locale.
    """
    if max_bytes is None:
        max_bytes = MAX_EMAIL_PDF_ATTACH_BYTES
    try:
        parts = msg.walk() if msg.is_multipart() else [msg]
    except Exception:
        return
    for part in parts:
        try:
            if part.is_multipart():
                continue
        except Exception:
            pass
        try:
            ctype = (part.get_content_type() or "").lower()
        except Exception:
            ctype = ""
        filename = ""
        try:
            filename = part.get_filename() or ""
        except Exception:
            filename = ""
        if not filename:
            try:
                cd = part.get("Content-Disposition") or ""
                m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";\r\n]+)"?', str(cd), re.I)
                if m:
                    filename = m.group(1).strip()
            except Exception:
                pass
        try:
            fname = decode_email_header(str(filename)) if filename else ""
        except Exception:
            fname = str(filename or "")
        low_name = fname.lower()
        is_pdf = ctype == "application/pdf" or low_name.endswith(".pdf")

        external_path = ""
        try:
            ext_url = part.get("X-Mozilla-External-Attachment-URL") or ""
            ext_url = str(ext_url).strip()
            if ext_url.lower().startswith("file:"):
                parsed = urllib.parse.urlparse(ext_url)
                external_path = urllib.parse.unquote(parsed.path or "")
                if external_path.startswith("/") and len(external_path) > 2 and external_path[2] == ":":
                    external_path = external_path[1:]
                external_path = external_path.replace("/", "\\")
        except Exception:
            external_path = ""

        payload = None
        try:
            payload = part.get_payload(decode=True)
        except Exception:
            payload = None
        if not payload:
            try:
                raw_pl = part.get_payload(decode=False)
                if isinstance(raw_pl, list):
                    raw_pl = None
                if isinstance(raw_pl, str) and raw_pl.strip():
                    import base64 as _b64
                    cte = (part.get("Content-Transfer-Encoding") or "").lower()
                    if "base64" in cte:
                        payload = _b64.b64decode(re.sub(r"\s+", "", raw_pl), validate=False)
                    elif "quoted-printable" in cte:
                        payload = quopri.decodestring(raw_pl.encode("latin1", errors="ignore"))
                    else:
                        payload = raw_pl.encode("latin1", errors="ignore")
            except Exception:
                payload = None

        if external_path and (not payload or len(payload) < 8):
            try:
                if os.path.isfile(external_path):
                    with open(external_path, "rb") as ef:
                        payload = ef.read(max_bytes)
                    if payload and not is_pdf and payload[:5] == b"%PDF-":
                        is_pdf = True
                    if payload:
                        yield (fname or os.path.basename(external_path) or "allegato.pdf"), payload, {
                            "empty": False,
                            "external": external_path,
                        }
                        continue
            except Exception:
                pass

        if not is_pdf and payload and payload[:5] == b"%PDF-":
            is_pdf = True
            if not fname:
                fname = "allegato.pdf"
        if not is_pdf:
            continue
        if not payload:
            yield (fname or "allegato.pdf"), b"", {"empty": True, "external": external_path or ""}
            continue
        if len(payload) > max_bytes:
            payload = payload[:max_bytes]
        yield (fname or "allegato.pdf"), payload, {"empty": False, "external": ""}


def match_pdf_attachment_hit(terms, att_name, pdf_raw, deadline=None):
    """Restituisce (snippet, via) se l'allegato PDF corrisponde ai termini, altrimenti None.

    Ordine: nome allegato → ricerca grezza veloce nei byte → estrazione testo PDF.
    """
    if text_matches_terms(att_name, terms):
        return f"Allegato: {att_name}", "nome allegato"
    try:
        raw_txt = pdf_raw.decode("latin1", errors="ignore")
        if text_matches_terms(raw_txt, terms):
            n = normalize_search_text(raw_txt, False)
            pos = n.find(terms[0]) if terms else -1
            if pos >= 0:
                a = max(0, pos - 40)
                b = min(len(raw_txt), pos + 80)
                snip = " ".join(raw_txt[a:b].split())
            else:
                snip = att_name or "allegato.pdf"
            return snip[:200], "testo allegato"
    except Exception:
        pass
    lines = extract_lines_from_pdf_bytes(
        pdf_raw,
        deadline=deadline,
        source_label=att_name or "allegato.pdf",
    )
    if not lines:
        return None
    for idx, line in enumerate(lines):
        if text_matches_terms(line, terms):
            start_i = max(0, idx - 1)
            end_i = min(len(lines), idx + 2)
            snip = " ".join(lines[start_i:end_i]).strip()
            return (snip[:200] or att_name), "testo allegato"
    hay = "\n".join(lines)
    if text_matches_terms(hay, terms):
        snippet = ""
        for line in lines:
            if any(t in normalize_search_text(line, False) for t in terms):
                snippet = line.strip()
                break
        if not snippet:
            snippet = " ".join(hay.split())[:200]
        return snippet[:200], "testo allegato"
    return None


_att_pdf_cache_seq = 0


def cache_extracted_pdf_attachment(pdf_raw, att_name, key_hint=""):
    """Scrive l'allegato PDF in %TEMP%\\rtad_pdf_attachments\\ e restituisce il path.

    Così «Apri» / «Copia File altrove» usano il PDF piccolo, non l'intera casella INBOX.
    """
    global _att_pdf_cache_seq
    if not pdf_raw:
        return ""
    try:
        base = os.path.join(tempfile.gettempdir(), "rtad_pdf_attachments")
        os.makedirs(base, exist_ok=True)
        safe = os.path.basename(att_name or "allegato.pdf")
        safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in safe).strip()
        if not safe:
            safe = "allegato.pdf"
        if not safe.lower().endswith(".pdf"):
            safe += ".pdf"
        stem, ext = os.path.splitext(safe)
        _att_pdf_cache_seq += 1
        hint = "".join(c if c.isalnum() else "" for c in str(key_hint))[-8:]
        out_name = f"{stem}_{_att_pdf_cache_seq:05d}_{hint or 'att'}{ext or '.pdf'}"
        out_path = os.path.join(base, out_name)
        with open(out_path, "wb") as f:
            f.write(pdf_raw)
        return out_path
    except Exception as e:
        logging.debug(f"Cache allegato PDF fallita: {e}")
        return ""


def _read_file_magic(path, n=8):
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except Exception:
        return b""


def _is_ooxml_zip_magic(magic):
    return magic.startswith(_ZIP_LOCAL_MAGIC) or magic.startswith(_ZIP_EMPTY_MAGIC)


def _is_ole_compound_magic(magic):
    return magic.startswith(_OLE_MAGIC)


def run_with_timeout(fn, timeout_sec, default=None):
    box = {"result": default, "exc": None}

    def _worker():
        try:
            box["result"] = fn()
        except Exception as exc:
            box["exc"] = exc

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout_sec)
    if t.is_alive():
        return default, True
    if box["exc"] is not None:
        raise box["exc"]
    return box["result"], False


def _filter_choice_labels():
    return [
        "Tutti i tipi di file",
        "Solo Immagini (.jpg, .png, .gif, .webp, .tif, …)",
        "Solo Audio e Video (.mp3, .m4a, .flac, .mp4, .mkv, .mov, …)",
        "Solo Documenti (.txt, .pdf, .docx, .epub, .eml, .html, .md, …)",
        "Estensione Personalizzata...",
    ]

FILTER_MODE_LABELS = (
    "Tutti i tipi di file",
    "Solo Immagini",
    "Solo Audio e Video",
    "Solo Documenti",
    "Estensione personalizzata",
)


def load_search_profiles():
    raw = _load_settings_dict().get("search_profiles", [])
    out = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        try:
            filter_mode = int(item.get("filter_mode", 0))
        except (TypeError, ValueError):
            filter_mode = 0
        if filter_mode < 0 or filter_mode > 4:
            filter_mode = 0
        out.append(
            {
                "name": name,
                "path": str(item.get("path", "") or ""),
                "filter_mode": filter_mode,
                "custom_ext": str(item.get("custom_ext", "") or ""),
                "query": str(item.get("query", "") or ""),
                "include_feed_raw": bool(item.get("include_feed_raw", False)),
                "include_ocr": bool(item.get("include_ocr", False)),
                "include_visual": bool(item.get("include_visual", False)),
                "include_zip": bool(item.get("include_zip", False)),
                "auto_start": bool(item.get("auto_start", False)),
            }
        )
    return out[:PROFILES_MAX]


def save_search_profiles(profiles):
    clean = []
    for item in profiles[:PROFILES_MAX]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        try:
            filter_mode = int(item.get("filter_mode", 0))
        except (TypeError, ValueError):
            filter_mode = 0
        if filter_mode < 0 or filter_mode > 4:
            filter_mode = 0
        clean.append(
            {
                "name": name,
                "path": str(item.get("path", "") or ""),
                "filter_mode": filter_mode,
                "custom_ext": str(item.get("custom_ext", "") or ""),
                "query": str(item.get("query", "") or ""),
                "include_feed_raw": bool(item.get("include_feed_raw", False)),
                "include_ocr": bool(item.get("include_ocr", False)),
                "include_visual": bool(item.get("include_visual", False)),
                "include_zip": bool(item.get("include_zip", False)),
                "auto_start": bool(item.get("auto_start", False)),
            }
        )
    data = _load_settings_dict()
    data["search_profiles"] = clean
    _save_settings_dict(data)


def upsert_search_profile(profile):
    """Inserisce o aggiorna un profilo per nome (casefold)."""
    profiles = load_search_profiles()
    name_key = profile["name"].casefold()
    replaced = False
    for i, p in enumerate(profiles):
        if p["name"].casefold() == name_key:
            profiles[i] = profile
            replaced = True
            break
    if not replaced:
        profiles.insert(0, profile)
    save_search_profiles(profiles)
    return replaced


def delete_search_profile(name):
    profiles = load_search_profiles()
    new_list = [p for p in profiles if p["name"].casefold() != name.casefold()]
    if len(new_list) == len(profiles):
        return False
    save_search_profiles(new_list)
    return True


def rename_search_profile(old_name, new_name):
    new_name = (new_name or "").strip()
    if not new_name:
        return False
    profiles = load_search_profiles()
    if any(p["name"].casefold() == new_name.casefold() and p["name"].casefold() != old_name.casefold() for p in profiles):
        return False
    for p in profiles:
        if p["name"].casefold() == old_name.casefold():
            p["name"] = new_name
            save_search_profiles(profiles)
            return True
    return False


def filter_mode_label(mode):
    try:
        return FILTER_MODE_LABELS[int(mode)]
    except (IndexError, TypeError, ValueError):
        return FILTER_MODE_LABELS[0]

def get_dynamic_desktop_path():
    desktop_path = os.path.expanduser("~\\Desktop")
    if not os.path.exists(desktop_path):
        desktop_path = os.path.expanduser("~\\OneDrive\\Desktop")
        if not os.path.exists(desktop_path):
            desktop_path = os.path.expanduser("~")
    return desktop_path


def _announce(msg, delay_ms=280):
    """Annuncio NVDA differito: la chiusura del menu contestuale altrimenti tronca la frase."""
    def _say(m=msg):
        if not _rtad_speech_active:
            return
        try:
            ui.message(m)
        except Exception:
            pass
    try:
        wx.CallLater(int(delay_ms), _say)
    except Exception:
        try:
            if _rtad_speech_active:
                ui.message(msg)
        except Exception:
            pass


def load_rtad_speech_settings():
    global _rtad_speech_active, _rtad_speech_settings_loaded
    data = _load_settings_dict()
    if "speech_active" in data:
        _rtad_speech_active = bool(data.get("speech_active"))
    _rtad_speech_settings_loaded = True


def save_rtad_speech_settings():
    data = _load_settings_dict()
    data["speech_active"] = bool(_rtad_speech_active)
    _save_settings_dict(data)


def rtad_speak(msg, force=False):
    """Annuncio RTAD rispettando Mute F7 (voce/velocità restano di NVDA)."""
    if not _rtad_speech_settings_loaded:
        try:
            load_rtad_speech_settings()
        except Exception:
            pass
    if not _rtad_speech_active and not force:
        return
    try:
        ui.message(str(msg))
    except Exception:
        pass


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
    """Estrae paragrafi da DOCX/OOXML. I .doc OLE non sono ZIP: restituisce [] subito."""
    try:
        magic = _read_file_magic(file_path, 4)
        if _is_ole_compound_magic(magic):
            return []
        if not _is_ooxml_zip_magic(magic):
            return []
        with zipfile.ZipFile(file_path) as z:
            try:
                info = z.getinfo("word/document.xml")
            except KeyError:
                return []
            if info.file_size > MAX_DOCX_XML_BYTES:
                return []
            xml_content = z.read("word/document.xml")
            if len(xml_content) > MAX_DOCX_XML_BYTES:
                xml_content = xml_content[:MAX_DOCX_XML_BYTES]
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

PDF_READ_MAX_BYTES = 40 * 1024 * 1024

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
# Cap testo da parsare per stream (anti regex/GIL su PDF brochure/scansioni)
_PDF_TEXT_PARSE_MAX = 1 * 1024 * 1024
# Max stream content da esaminare in una sola ricerca
_PDF_MAX_CONTENT_STREAMS = 120
# Non tentare inflate “a caso” su stream non-Flate enormi
_PDF_GUESS_INFLATE_MAX = 256 * 1024
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


def _pdf_bytes_look_like_content(data: bytes) -> bool:
    """True se lo stream sembra contenuto di pagina (operatori testo), non binario grezzo."""
    if not data or len(data) < 4:
        return False
    # troppi null / byte alti → probabilmente immagine decompressa
    sample = data[:8000]
    nul = sample.count(b"\x00")
    if nul > len(sample) // 10:
        return False
    has_text_op = (
        (b"Tj" in data)
        or (b"TJ" in data)
        or (b"'" in data and b"(" in data)
    )
    if not has_text_op:
        return False
    # BT…ET alza la confidenza; senza, solo stream piccoli (evita brochure/binari)
    if b"BT" in data and b"ET" in data:
        return True
    return len(data) <= 64 * 1024


def extract_lines_from_pdf(file_path, deadline=None):
    """Estrae righe di testo da un PDF senza librerie esterne."""
    if deadline is None:
        deadline = time.monotonic() + FILE_CONTENT_SOFT_TIMEOUT_PDF_SEC
    try:
        with open(file_path, "rb") as f:
            raw = f.read(PDF_READ_MAX_BYTES)
    except Exception as e:
        logging.debug(f"Errore lettura PDF {file_path}: {e}")
        return []
    return extract_lines_from_pdf_bytes(raw, deadline=deadline, source_label=file_path)


def extract_lines_from_pdf_bytes(raw, deadline=None, source_label=""):
    """Estrae righe di testo da byte PDF (file o allegato email)."""
    if deadline is None:
        deadline = time.monotonic() + FILE_CONTENT_SOFT_TIMEOUT_PDF_SEC
    if not raw:
        return []
    label = source_label or "pdf-bytes"

    if not raw.startswith(b"%PDF"):
        return _pdf_fallback_crude_lines(raw)

    cmap = _pdf_parse_tounicode_cmaps(raw, deadline=deadline)

    pieces = []
    pos = 0
    stream_count = 0
    content_used = 0
    while True:
        if time.monotonic() > deadline:
            logging.warning(f"PDF interrotto per tempo massimo: {label}")
            break
        if content_used >= _PDF_MAX_CONTENT_STREAMS:
            break
        # find senza regex su tutto il residuo (più sicuro su brochure enormi)
        m_at = raw.find(b"stream", pos)
        if m_at < 0:
            break
        after = m_at + 6
        if after + 1 < len(raw) and raw[after:after + 2] == b"\r\n":
            start = after + 2
        elif after < len(raw) and raw[after:after + 1] in (b"\n", b"\r"):
            start = after + 1
        else:
            pos = after
            continue
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

        if _pdf_dict_is_image(dict_blob):
            pos = end + 9
            continue

        is_flate = _pdf_dict_has_flate(dict_blob)
        if is_flate:
            if len(stream) > _PDF_CONTENT_INFLATE_MAX:
                pos = end + 9
                continue
            data = _pdf_inflate_stream(stream)
        else:
            data = stream
            if (
                not _pdf_bytes_look_like_content(data)
                and len(stream) <= _PDF_GUESS_INFLATE_MAX
            ):
                inflated = _pdf_inflate_stream(stream)
                if _pdf_bytes_look_like_content(inflated):
                    data = inflated

        if _pdf_bytes_look_like_content(data):
            pieces.extend(
                _pdf_text_from_content_stream(data, cmap, deadline=deadline)
            )
            content_used += 1
        stream_count += 1
        if stream_count % 4 == 0:
            time.sleep(0)
        pos = end + 9

    blob = " ".join(pieces)
    blob = blob.replace("\r\n", "\n").replace("\r", "\n")
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


def _pdf_parse_tounicode_cmaps(raw, deadline=None):
    """Unisce tutte le CMap ToUnicode del PDF: codice CID (int) → carattere."""
    merged = {}
    pos = 0
    while True:
        if deadline is not None and time.monotonic() > deadline:
            break
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
            if (
                b"beginbfchar" not in stream
                and b"beginbfrange" not in stream
                and len(stream) <= _PDF_GUESS_INFLATE_MAX
            ):
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


def _pdf_text_from_content_stream(data: bytes, cmap: dict = None, deadline=None) -> list:
    """Estrae stringhe Tj/TJ con scansione lineare (niente regex catastrofiche sul binario)."""
    if cmap is None:
        cmap = {}
    if not data:
        return []
    if len(data) > _PDF_TEXT_PARSE_MAX:
        data = data[:_PDF_TEXT_PARSE_MAX]
    pieces = []
    n = len(data)
    i = 0

    def _read_literal(start_paren):
        """Legge (...) bilanciato con escape; restituisce (bytes_interni, indice_dopo_chiusura)."""
        j = start_paren + 1
        out = bytearray()
        while j < n:
            b = data[j]
            if b == 0x5C and j + 1 < n:  # backslash
                out.append(data[j + 1])
                j += 2
                continue
            if b == 0x29:  # )
                return bytes(out), j + 1
            out.append(b)
            j += 1
            if len(out) > 8192:
                return bytes(out), j
        return bytes(out), j

    def _skip_ws(j):
        while j < n and data[j] in b" \t\r\n\f\0":
            j += 1
        return j

    while i < n:
        if deadline is not None and (i & 0xFFFF) == 0 and time.monotonic() > deadline:
            break
        b = data[i]
        if b == 0x28:  # (
            lit, j = _read_literal(i)
            k = _skip_ws(j)
            if k + 1 < n and data[k:k + 2] == b"Tj":
                pieces.append(_pdf_bytes_to_text(lit, cmap))
                i = k + 2
                continue
            if k < n and data[k:k + 1] in (b"'", b'"'):
                pieces.append(_pdf_bytes_to_text(lit, cmap))
                i = k + 1
                continue
            i = j
            continue
        if b == 0x3C:  # < hex >
            j = i + 1
            hx = bytearray()
            while j < n and data[j] != 0x3E:
                c = data[j]
                if (0x30 <= c <= 0x39) or (0x41 <= c <= 0x46) or (0x61 <= c <= 0x66) or c in b" \t\r\n":
                    hx.append(c)
                    j += 1
                    if len(hx) > 16384:
                        break
                else:
                    break
            if j < n and data[j] == 0x3E:
                j += 1
                k = _skip_ws(j)
                if k + 1 < n and data[k:k + 2] == b"Tj":
                    pieces.append(_pdf_hex_to_str(bytes(hx), cmap))
                    i = k + 2
                    continue
            i += 1
            continue
        if b == 0x5B:  # [ ... ] TJ
            j = i + 1
            parts = []
            depth = 1
            while j < n and depth:
                if deadline is not None and (j & 0xFFFF) == 0 and time.monotonic() > deadline:
                    depth = 0
                    break
                if data[j] == 0x28:  # (
                    lit, j2 = _read_literal(j)
                    parts.append(_pdf_bytes_to_text(lit, cmap))
                    j = j2
                    continue
                if data[j] == 0x3C:  # <
                    j2 = j + 1
                    hx = bytearray()
                    while j2 < n and data[j2] != 0x3E:
                        c = data[j2]
                        if (0x30 <= c <= 0x39) or (0x41 <= c <= 0x46) or (0x61 <= c <= 0x66) or c in b" \t\r\n":
                            hx.append(c)
                            j2 += 1
                            if len(hx) > 16384:
                                break
                        else:
                            break
                    if j2 < n and data[j2] == 0x3E:
                        parts.append(_pdf_hex_to_str(bytes(hx), cmap))
                        j = j2 + 1
                        continue
                if data[j] == 0x5B:
                    depth += 1
                elif data[j] == 0x5D:
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
                if j - i > _PDF_TEXT_PARSE_MAX:
                    break
            k = _skip_ws(j)
            if k + 1 < n and data[k:k + 2] == b"TJ" and parts:
                pieces.append("".join(parts))
                i = k + 2
                continue
            i += 1
            continue
        i += 1
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


def _pdf_inflate_stream(stream: bytes, max_out: int = None):
    """Decomprime FlateDecode con tetto di uscita (anti zip-bomb / «Non risponde»)."""
    if max_out is None:
        max_out = _PDF_CONTENT_INFLATE_MAX
    if not stream:
        return b""
    for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
        try:
            dec = zlib.decompressobj(wbits)
            out = dec.decompress(stream, max_out)
            if len(out) >= max_out:
                return out
            try:
                tail = dec.flush()
            except Exception:
                tail = b""
            if tail:
                remain = max_out - len(out)
                if remain > 0:
                    out += tail[:remain]
            return out
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
            data = (
                _pdf_inflate_stream(stream, max_out=_PDF_IMAGE_INFLATE_MAX)
                if filt == "flate"
                else stream
            )
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
    """Legacy: byte grezzi (non OCR). Preferire rtad_ocr.ocr_image_file."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(4194304)
            content_str = header.decode("latin1", errors="ignore")
            words = re.findall(r"[A-Za-z0-9\s]{3,}", content_str)
            return " ".join(words)
    except Exception:
        return ""


def ocr_text_from_pdf_file(file_path, should_abort=None):
    """OCR sulle immagini pagina di un PDF (solo se il motore è disponibile)."""
    if rtad_ocr is None:
        return ""
    try:
        images = extract_images_from_pdf(file_path)
    except Exception:
        return ""
    if not images:
        return ""
    pages = []
    for im in images:
        try:
            if (
                im.get("w", 0) >= _PDF_PAGE_IMAGE_MIN_SIDE
                and im.get("h", 0) >= _PDF_PAGE_IMAGE_MIN_SIDE
                and im.get("w", 0) * im.get("h", 0) >= _PDF_PAGE_IMAGE_MIN_AREA
            ):
                pages.append(im)
        except Exception:
            continue
    if not pages:
        pages = images[: rtad_ocr.MAX_OCR_PDF_PAGES]
    return rtad_ocr.ocr_pdf_image_records(
        pages,
        max_pages=rtad_ocr.MAX_OCR_PDF_PAGES,
        should_abort=should_abort,
    )


def load_include_ocr_preference():
    data = _load_settings_dict()
    return bool(data.get("include_ocr", False))


def save_include_ocr_preference(enabled):
    data = _load_settings_dict()
    data["include_ocr"] = bool(enabled)
    _save_settings_dict(data)


def load_include_visual_preference():
    data = _load_settings_dict()
    return bool(data.get("include_visual", False))


def save_include_visual_preference(enabled):
    data = _load_settings_dict()
    data["include_visual"] = bool(enabled)
    _save_settings_dict(data)


def load_include_zip_preference():
    data = _load_settings_dict()
    return bool(data.get("include_zip", False))


def save_include_zip_preference(enabled):
    data = _load_settings_dict()
    data["include_zip"] = bool(enabled)
    _save_settings_dict(data)


def load_ocr_engine_preference():
    """'windows' (default), 'easyocr' oppure 'google'."""
    data = _load_settings_dict()
    eng = str(data.get("ocr_engine", "windows") or "windows").strip().lower()
    if eng in ("google-vision", "google_vision", "vision", "gcv"):
        eng = "google"
    if eng not in ("windows", "easyocr", "google"):
        eng = "windows"
    return eng


def save_ocr_engine_preference(engine):
    eng = str(engine or "windows").strip().lower()
    if eng in ("google-vision", "google_vision", "vision", "gcv"):
        eng = "google"
    if eng not in ("windows", "easyocr", "google"):
        eng = "windows"
    data = _load_settings_dict()
    data["ocr_engine"] = eng
    _save_settings_dict(data)
    if rtad_ocr is not None:
        try:
            rtad_ocr.set_engine_preference(eng)
        except Exception:
            pass


def load_google_vision_api_key():
    """Chiave API personale Google Vision (locale, solo su questo PC)."""
    data = _load_settings_dict()
    return str(data.get("google_vision_api_key", "") or "").strip()


def save_google_vision_api_key(key):
    key = str(key or "").strip()
    data = _load_settings_dict()
    if key:
        data["google_vision_api_key"] = key
    else:
        data.pop("google_vision_api_key", None)
    _save_settings_dict(data)
    if rtad_ocr is not None:
        try:
            rtad_ocr.set_google_api_key(key)
        except Exception:
            pass


def load_gemini_api_key():
    """Chiave API personale Gemini / Google AI Studio (descrizione avanzata)."""
    data = _load_settings_dict()
    return str(data.get("gemini_api_key", "") or "").strip()


def save_gemini_api_key(key):
    key = str(key or "").strip()
    data = _load_settings_dict()
    if key:
        data["gemini_api_key"] = key
    else:
        data.pop("gemini_api_key", None)
    _save_settings_dict(data)
    if rtad_ocr is not None:
        try:
            rtad_ocr.set_gemini_api_key(key)
        except Exception:
            pass


def ocr_engine_from_choice_index(idx):
    if idx == 2:
        return "google"
    if idx == 1:
        return "easyocr"
    return "windows"


def ocr_choice_index_from_engine(eng):
    eng = str(eng or "windows").strip().lower()
    if eng == "google":
        return 2
    if eng == "easyocr":
        return 1
    return 0


def load_escape_closes_preference():
    """False di default: Esc non chiude la finestra principale (solo annulla ricerca)."""
    data = _load_settings_dict()
    return bool(data.get("escape_closes_app", False))


def save_escape_closes_preference(enabled):
    data = _load_settings_dict()
    data["escape_closes_app"] = bool(enabled)
    _save_settings_dict(data)


def load_notify_search_end_preference():
    """True di default: notifica di sistema a fine ricerca."""
    data = _load_settings_dict()
    if "notify_search_end" not in data:
        return True
    return bool(data.get("notify_search_end", True))


def save_notify_search_end_preference(enabled):
    data = _load_settings_dict()
    data["notify_search_end"] = bool(enabled)
    _save_settings_dict(data)


# Toast WinRT nel Centro notifiche (Windows+N). Non tocca l'AUMID del processo NVDA.
RTAD_TOAST_AUMID = "AccessoDigitale.RTAD.Addon"


def _register_toast_aumid_display_name(aumid: str, display_name: str) -> None:
    try:
        import winreg
        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            rf"Software\Classes\AppUserModelId\{aumid}",
        )
        try:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, display_name)
        finally:
            winreg.CloseKey(key)
    except Exception:
        pass


def show_persistent_windows_notification(title: str, message: str, *, aumid: str = "") -> bool:
    """Toast WinRT scenario=reminder: resta finché non si apre/OK (anche Windows+N)."""
    app_id = (aumid or RTAD_TOAST_AUMID).strip() or RTAD_TOAST_AUMID
    try:
        _register_toast_aumid_display_name(app_id, APP_TITLE)
    except Exception:
        pass
    try:
        payload = json.dumps(
            {
                "title": str(title or APP_TITLE),
                "body": str(message or ""),
                "aumid": app_id,
            },
            ensure_ascii=False,
        )
        b64 = __import__("base64").b64encode(payload.encode("utf-8")).decode("ascii")
    except Exception:
        return False

    ps = (
        "$ErrorActionPreference = 'Stop'; "
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null; "
        f"$raw = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64}')); "
        "$o = $raw | ConvertFrom-Json; "
        "function Esc([string]$s) { if ($null -eq $s) { return '' }; "
        "return (($s -replace '&','&amp;') -replace '<','&lt;' -replace '>','&gt;' -replace '\"','&quot;') }; "
        "$t = Esc ([string]$o.title); $b = Esc ([string]$o.body); "
        "$xmlText = \"<toast scenario='reminder'><visual><binding template='ToastGeneric'>"
        "<text>$t</text><text>$b</text></binding></visual>"
        "<actions><action content='OK' arguments='dismiss' activationType='system'/></actions></toast>\"; "
        "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument; $xml.LoadXml($xmlText); "
        "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); "
        "$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier([string]$o.aumid); "
        "$notifier.Show($toast)"
    )
    try:
        flags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            flags = subprocess.CREATE_NO_WINDOW
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-WindowStyle",
                "Hidden",
                "-Command",
                ps,
            ],
            capture_output=True,
            timeout=12,
            creationflags=flags,
        )
        return completed.returncode == 0
    except Exception:
        return False


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
        btn_close = wx.Button(panel, label="Chiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        hbox_btns.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_btns, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(vbox)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        rtad_speak("Caricamento email in corso.")
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
        rtad_speak("Email caricata.")

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
        btn_close = wx.Button(panel, label="Chiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        hbox_btns.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_btns, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(vbox)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        if cached_text:
            rtad_speak(f"Messaggio {msg_index + 1} dalla ricerca.")
            wx.CallAfter(self._apply_loaded_text, cached_text)
        else:
            rtad_speak(f"Caricamento messaggio {msg_index + 1} dall'archivio. Attendere.")
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
        rtad_speak("Messaggio caricato.")

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
        else:
            event.Skip()

def _ensure_ocr_keys():
    """Carica chiavi Vision/Gemini in rtad_ocr (best-effort)."""
    if rtad_ocr is None:
        return
    try:
        gkey = load_google_vision_api_key()
        if gkey:
            rtad_ocr.set_google_api_key(gkey)
    except Exception:
        pass
    try:
        gemkey = load_gemini_api_key()
        if gemkey:
            rtad_ocr.set_gemini_api_key(gemkey)
    except Exception:
        pass


def run_image_analysis(
    host,
    file_path,
    mode="describe",
    copy_only=False,
    delete_after=False,
    speak=None,
):
    """Analisi immagine riusabile da SearchFrame e GlobalPlugin (1.6.4)."""
    speak = speak or rtad_speak
    if not file_path or not os.path.isfile(file_path):
        speak("File immagine non trovato.")
        return
    if rtad_ocr is None:
        speak("Modulo immagini non disponibile.")
        return
    _ensure_ocr_keys()

    if mode in ("describe", "copy-describe", "alt", "alt-long") and not load_gemini_api_key():
        speak(
            "Descrizione avanzata: nessuna chiave Gemini. "
            "Uso etichette Vision se disponibili. "
            "Puoi aggiungere Gemini da Strumenti."
        )
    else:
        speak("Analisi immagine in corso…")

    def _work():
        title = "Immagine"
        body = ""
        try:
            if mode == "tech":
                title = "Scheda tecnica immagine"
                body = rtad_ocr.format_tech_sheet(rtad_ocr.get_image_tech_info(file_path))
            elif mode == "labels":
                title = "Etichette e oggetti"
                data = rtad_ocr.analyze_image_visual(file_path)
                body = rtad_ocr.format_labels_text(data)
            elif mode == "ocr":
                title = "Testo OCR dell'immagine"
                if rtad_ocr.engine_available():
                    txt = rtad_ocr.ocr_image_file(file_path) or ""
                    body = txt.strip() or "Nessun testo rilevato nell'immagine."
                else:
                    body = rtad_ocr.engine_status_message()
            elif mode == "alt":
                title = "Alt-text breve"
                alt = rtad_ocr.describe_image_alt_text(file_path)
                if alt.get("ok") and (alt.get("text") or "").strip():
                    body = (alt.get("text") or "").strip()
                else:
                    body = alt.get("error") or "Alt-text non disponibile."
            elif mode == "alt-long":
                title = "Alt-text e descrizione"
                body = rtad_ocr.format_alt_and_long_description(file_path)
            else:
                title = "Descrizione immagine"
                body = rtad_ocr.describe_image(file_path)
        except Exception as e:
            title = "Errore analisi immagine"
            body = str(e)

        def _show():
            if copy_only:
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.TextDataObject(body))
                    wx.TheClipboard.Close()
                    speak("Descrizione copiata negli appunti.")
                else:
                    speak("Impossibile aprire gli appunti.")
                if delete_after:
                    rtad_ocr.cleanup_temp_image(file_path)
                return
            if not hasattr(host, "_image_info_frames") or host._image_info_frames is None:
                host._image_info_frames = []
            frm = ImageInfoFrame(None, title, body, image_path=file_path)

            def _on_close(evt, frame=frm, path=file_path, do_del=delete_after):
                try:
                    if frame in host._image_info_frames:
                        host._image_info_frames.remove(frame)
                except Exception:
                    pass
                if do_del:
                    try:
                        rtad_ocr.cleanup_temp_image(path)
                    except Exception:
                        pass
                evt.Skip()

            frm.Bind(wx.EVT_CLOSE, _on_close)
            host._image_info_frames.append(frm)
            frm.Show()
            frm.Raise()

        wx.CallAfter(_show)

    threading.Thread(target=_work, daemon=True).start()


def describe_image_from_url_dialog(host, speak=None):
    speak = speak or rtad_speak
    if rtad_ocr is None:
        speak("Modulo immagini non disponibile.")
        return
    parent = host if isinstance(host, wx.Window) else None
    dlg = wx.TextEntryDialog(
        parent,
        "Incolla l'URL completo dell'immagine da descrivere\n"
        "(http o https, anche da gallerie o articoli web):",
        "Descrivi immagine da URL",
        "",
    )
    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        return
    url = (dlg.GetValue() or "").strip().strip('"').strip("'")
    dlg.Destroy()
    if not url:
        speak("URL non inserito.")
        return
    speak("Download immagine in corso…")

    def _work():
        res = rtad_ocr.materialize_image_from_url(url)
        if not res.get("ok") or not res.get("path"):
            wx.CallAfter(speak, res.get("error") or "Download immagine non riuscito.")
            return
        wx.CallAfter(
            run_image_analysis,
            host,
            res["path"],
            "describe",
            False,
            True,
            speak,
        )

    threading.Thread(target=_work, daemon=True).start()


def describe_image_from_clipboard(host, speak=None):
    speak = speak or rtad_speak
    if rtad_ocr is None:
        speak("Modulo immagini non disponibile.")
        return
    path = ""
    delete_after = True
    url_text = ""
    try:
        if not wx.TheClipboard.Open():
            speak("Impossibile aprire gli appunti.")
            return
        try:
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
                data = wx.BitmapDataObject()
                if wx.TheClipboard.GetData(data):
                    bmp = data.GetBitmap()
                    if bmp and bmp.IsOk():
                        fd, path = tempfile.mkstemp(suffix=".png", prefix="rtad_clip_")
                        os.close(fd)
                        if not bmp.SaveFile(path, wx.BITMAP_TYPE_PNG):
                            path = ""
            if not path and wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
                fdo = wx.FileDataObject()
                if wx.TheClipboard.GetData(fdo):
                    for cand in fdo.GetFilenames() or []:
                        if cand and os.path.isfile(cand) and rtad_ocr.is_image_path(cand):
                            path = cand
                            delete_after = False
                            break
            if not path and wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                tdo = wx.TextDataObject()
                if wx.TheClipboard.GetData(tdo):
                    url_text = (tdo.GetText() or "").strip().strip('"').strip("'")
        finally:
            wx.TheClipboard.Close()
    except Exception:
        speak("Lettura appunti non riuscita.")
        return

    if path and os.path.isfile(path):
        run_image_analysis(
            host, path, mode="describe", delete_after=delete_after, speak=speak
        )
        return
    if url_text and (
        rtad_ocr.is_likely_image_url(url_text)
        or url_text.lower().startswith("http://")
        or url_text.lower().startswith("https://")
    ):
        speak("Download immagine dall'URL negli appunti…")

        def _work():
            res = rtad_ocr.materialize_image_from_url(url_text)
            if not res.get("ok") or not res.get("path"):
                wx.CallAfter(speak, res.get("error") or "Download immagine non riuscito.")
                return
            wx.CallAfter(
                run_image_analysis,
                host,
                res["path"],
                "describe",
                False,
                True,
                speak,
            )

        threading.Thread(target=_work, daemon=True).start()
        return
    speak(
        "Nessuna immagine negli appunti. "
        "Copia un'immagine, un file immagine o un URL http, poi riprova."
    )


def describe_image_from_screenshot(host, speak=None):
    speak = speak or rtad_speak
    if rtad_ocr is None:
        speak("Modulo immagini non disponibile.")
        return
    speak("Cattura schermo in corso…")
    try:
        screen = wx.ScreenDC()
        size = screen.GetSize()
        res = rtad_ocr.materialize_image_from_screen_rect(
            0, 0, int(size.width), int(size.height)
        )
    except Exception:
        speak("Cattura schermo non riuscita.")
        return
    if not res.get("ok") or not res.get("path"):
        speak(res.get("error") or "Cattura schermo non riuscita.")
        return
    run_image_analysis(
        host, res["path"], mode="describe", delete_after=True, speak=speak
    )


def _nvda_role_set():
    """Ruoli grafica/figura compatibili NVDA 2024+ e precedenti."""
    roles = set()
    try:
        from controlTypes import Role

        for name in ("GRAPHIC", "IMAGE", "FIGURE"):
            if hasattr(Role, name):
                roles.add(getattr(Role, name))
    except Exception:
        try:
            import controlTypes as ct

            for name in ("ROLE_GRAPHIC", "ROLE_IMAGE", "ROLE_FIGURE"):
                if hasattr(ct, name):
                    roles.add(getattr(ct, name))
        except Exception:
            pass
    return roles


def _object_location_tuple(obj):
    """(left, top, width, height) o None."""
    try:
        loc = obj.location
        if loc is None:
            return None
        if hasattr(loc, "left"):
            w, h = int(loc.width), int(loc.height)
            if w < 2 or h < 2:
                return None
            return (int(loc.left), int(loc.top), w, h)
        if isinstance(loc, (tuple, list)) and len(loc) >= 4:
            w, h = int(loc[2]), int(loc[3])
            if w < 2 or h < 2:
                return None
            return (int(loc[0]), int(loc[1]), w, h)
    except Exception:
        return None
    return None


def _ia2_attrs(obj):
    """Dict attributi IA2 in modo tollerante (Chrome/Edge/Firefox)."""
    try:
        attrs = obj.IA2Attributes
        if isinstance(attrs, dict):
            return attrs
    except Exception:
        pass
    try:
        attrs = obj._get_IA2Attributes()
        if isinstance(attrs, dict):
            return attrs
    except Exception:
        pass
    return {}


def _normalize_http_url(url, base=""):
    c = (url or "").strip()
    if not c or c.startswith("data:"):
        return ""
    if c.startswith("//"):
        c = "https:" + c
    elif c.startswith("/") and base:
        try:
            c = urllib.parse.urljoin(base, c)
        except Exception:
            return ""
    elif not c.lower().startswith("http") and base:
        try:
            c = urllib.parse.urljoin(base, c)
        except Exception:
            return ""
    if c.lower().startswith("http://") or c.lower().startswith("https://"):
        return c
    return ""


def _document_url_from_obj(obj):
    """URL della pagina (browse mode / documento) best-effort."""
    try:
        import api as _api
    except Exception:
        _api = None

    tried = []
    if obj is not None:
        tried.append(obj)
        try:
            ti = getattr(obj, "treeInterceptor", None)
            if ti is not None:
                tried.append(ti)
                root = getattr(ti, "rootNVDAObject", None)
                if root is not None:
                    tried.append(root)
        except Exception:
            pass
        try:
            p = obj.parent
            hops = 0
            while p is not None and hops < 12:
                tried.append(p)
                p = p.parent
                hops += 1
        except Exception:
            pass
    if _api is not None:
        try:
            tried.append(_api.getFocusObject())
        except Exception:
            pass

    for cand in tried:
        if cand is None:
            continue
        for attr in ("documentUrl", "URL", "url", "statusBarText"):
            try:
                u = getattr(cand, attr, None)
            except Exception:
                u = None
            if isinstance(u, str) and u.startswith("http"):
                return u.split()[0].strip()
        try:
            val = cand.IAccessibleObject.accValue(0)
            if isinstance(val, str) and val.startswith("http"):
                return val.strip()
        except Exception:
            pass
        attrs = _ia2_attrs(cand)
        for key in ("url", "doc-url", "document-url", "href"):
            u = attrs.get(key)
            if isinstance(u, str) and u.startswith("http"):
                return u.strip()
    return ""


def _collect_image_url_from_obj(obj, base=""):
    """Estrae URL immagine da attributi IA2 / value (best-effort)."""
    candidates = []
    attrs = _ia2_attrs(obj)
    for key in (
        "src",
        "data-src",
        "data-lazy-src",
        "data-original",
        "data-url",
        "href",
        "content",
        "poster",
        "current-src",
        "srcset",
    ):
        val = attrs.get(key)
        if not val:
            continue
        val = str(val).strip()
        if key == "srcset":
            # "url1 1x, url2 2x" → prendi l'ultimo (di solito più grande)
            parts = [p.strip().split(" ")[0] for p in val.split(",") if p.strip()]
            candidates.extend(parts)
        else:
            candidates.append(val)
    for k, v in attrs.items():
        kl = str(k).lower()
        if any(tok in kl for tok in ("src", "href", "poster")) and v:
            candidates.append(str(v).strip())
    try:
        val = getattr(obj, "value", None)
        if val and isinstance(val, str):
            candidates.append(val.strip())
    except Exception:
        pass
    try:
        name = getattr(obj, "name", None) or ""
        if isinstance(name, str) and name.strip().lower().startswith("http"):
            candidates.append(name.strip())
    except Exception:
        pass

    out = []
    for c in candidates:
        u = _normalize_http_url(c, base=base)
        if u and u not in out:
            out.append(u)
    return out


def _alt_hint_from_name(name):
    """Da 'Figura _1AG5322 grafico' → '_1AG5322'."""
    n = (name or "").strip()
    if not n:
        return ""
    # togli rumore NVDA IT/EN
    cleaned = n
    for noise in (
        "figura",
        "grafico",
        "graphic",
        "figure",
        "immagine",
        "image",
        "foto",
        "photo",
    ):
        cleaned = re.sub(rf"\b{noise}\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned:
        tokens = [
            t.strip(" .,:;\"'")
            for t in cleaned.replace("\\", "/").split(" ")
            if t.strip(" .,:;\"'")
        ]
        # Preferisci pezzi distintivi (estensione file, id lunghi), non «WhatsApp»
        weak = {
            "whatsapp", "telegram", "facebook", "instagram", "twitter",
            "jpeg", "jpg", "png", "gif", "webp", "at",
        }
        for t in tokens:
            low = t.lower()
            if low in weak:
                continue
            if "." in t and any(low.endswith(ext) for ext in (
                ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
            )):
                return t
            if len(t) >= 8 and any(ch.isdigit() for ch in t):
                return t
        for t in tokens:
            if len(t) >= 3 and t.lower() not in weak and any(ch.isalnum() for ch in t):
                return t
        return cleaned
    return n


def _find_img_url_in_page_html(page_url, alt_hint):
    """Scarica HTML della pagina e cerca <img> con alt/src correlato all'hint."""
    if not page_url or not alt_hint:
        return ""
    hint = alt_hint.strip()
    if len(hint) < 3:
        return ""
    try:
        req = urllib.request.Request(
            page_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36 RTAD/1.6.4"
                ),
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read(2_500_000)
            final = resp.geturl() or page_url
        html = raw.decode("utf-8", "replace")
    except Exception:
        return ""

    hint_l = hint.lower()
    best = ""

    def _pick_from_tag(tag):
        src = ""
        m = re.search(r'\bsrc\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        if m:
            src = m.group(1).strip()
        if not src:
            m = re.search(r'\bdata-src\s*=\s*["\']([^"\']+)["\']', tag, re.I)
            if m:
                src = m.group(1).strip()
        if not src:
            m = re.search(r'\bsrcset\s*=\s*["\']([^"\']+)["\']', tag, re.I)
            if m:
                parts = [p.strip().split(" ")[0] for p in m.group(1).split(",") if p.strip()]
                if parts:
                    src = parts[-1]
        return _normalize_http_url(src, base=final)

    for m in re.finditer(r"<img\b[^>]*>", html, re.I):
        tag = m.group(0)
        tag_l = tag.lower()
        if hint_l in tag_l:
            u = _pick_from_tag(tag)
            if u:
                return u
    # source dentro picture
    for m in re.finditer(r"<source\b[^>]*>", html, re.I):
        tag = m.group(0)
        if hint_l in tag.lower():
            u = _pick_from_tag(tag)
            if u:
                return u
    # fallback: src che contiene l'hint (nome file)
    for m in re.finditer(
        r'(?:src|data-src)\s*=\s*["\']([^"\']+' + re.escape(hint) + r'[^"\']*)["\']',
        html,
        re.I,
    ):
        u = _normalize_http_url(m.group(1), base=final)
        if u:
            return u
    return best


def _is_local_image_file(path):
    """True se path è un file immagine supportato su disco."""
    if not path or not isinstance(path, str):
        return False
    p = path.strip().strip('"').strip("'")
    if not p or not os.path.isfile(p):
        return False
    ext = os.path.splitext(p)[1].lower()
    if ext in IMG_EXTS:
        return True
    if rtad_ocr is not None:
        try:
            return bool(rtad_ocr.is_image_path(p))
        except Exception:
            pass
    return False


def _foreground_window_class():
    """Class name della finestra in primo piano (es. CabinetWClass, Chrome_WidgetWin_1)."""
    try:
        import winUser

        fg = winUser.getForegroundWindow()
        if fg:
            return winUser.getClassName(fg) or ""
    except Exception:
        pass
    try:
        user32 = ctypes.windll.user32
        fg = user32.GetForegroundWindow()
        if not fg:
            return ""
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(fg, buf, 256)
        return buf.value or ""
    except Exception:
        return ""


def _foreground_is_file_manager():
    """True se il focus è Esplora file / Desktop (non un browser)."""
    cls = (_foreground_window_class() or "").lower()
    if not cls:
        return False
    # Explorer classico / moderno, Desktop
    if cls in (
        "cabinetwclass",
        "explorewclass",
        "progman",
        "workerw",
    ):
        return True
    return False


def _object_looks_like_web_context(obj):
    """True se l'oggetto NVDA è in una pagina web / browse mode."""
    if obj is None:
        return False
    try:
        ti = getattr(obj, "treeInterceptor", None)
        if ti is not None:
            return True
    except Exception:
        pass
    try:
        mod = getattr(obj, "appModule", None)
        app = (getattr(mod, "appName", None) or getattr(mod, "productName", None) or "")
        app_l = str(app).lower()
        if any(
            tok in app_l
            for tok in (
                "chrome",
                "msedge",
                "edge",
                "firefox",
                "brave",
                "opera",
                "vivaldi",
                "iexplore",
                "thorium",
            )
        ):
            return True
    except Exception:
        pass
    if _document_url_from_obj(obj):
        return True
    return False


def _shell_foreground_selected_image_path():
    """Percorso immagine selezionata solo se Esplora/Desktop è in primo piano.

    Non usare selezioni di finestre Explorer in secondo piano: altrimenti
    NVDA+Shift+G sul web analizzerebbe ancora un file lasciato selezionato
    in Download (bug «sempre la stessa immagine»).
    """
    if not _foreground_is_file_manager():
        return ""
    try:
        import comtypes.client
    except Exception:
        return ""
    fg = None
    try:
        import winUser

        fg = winUser.getForegroundWindow()
    except Exception:
        try:
            user32 = ctypes.windll.user32
            fg = user32.GetForegroundWindow()
        except Exception:
            fg = None
    try:
        shell = comtypes.client.CreateObject("Shell.Application")
        windows = shell.Windows()
        count = int(windows.Count)
    except Exception:
        return ""

    scored = []
    for i in range(count):
        try:
            w = windows.Item(i)
        except Exception:
            continue
        score = 0
        try:
            hwnd = int(w.HWND)
            if fg and hwnd == fg:
                score = 100
        except Exception:
            pass
        # Solo la finestra Explorer effettivamente in primo piano
        if score < 100:
            continue
        try:
            doc = w.Document
            sel = doc.SelectedItems()
            nsel = int(sel.Count)
        except Exception:
            continue
        for j in range(nsel):
            try:
                item = sel.Item(j)
                path = getattr(item, "Path", None) or ""
            except Exception:
                path = ""
            if _is_local_image_file(path):
                scored.append((score, path))
    if not scored:
        return ""
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def _path_guess_from_nvda_object(obj):
    """Prova a ricavare un path file dall'oggetto NVDA (value/name/attributi)."""
    if obj is None:
        return ""
    texts = []
    for attr in ("value", "name"):
        try:
            v = getattr(obj, attr, None)
        except Exception:
            v = None
        if isinstance(v, str) and v.strip():
            texts.append(v.strip().strip('"').strip("'"))
    attrs = _ia2_attrs(obj)
    for key in (
        "path",
        "filename",
        "fullpath",
        "full-path",
        "url",
        "contentLocation",
    ):
        v = attrs.get(key)
        if isinstance(v, str) and v.strip():
            texts.append(v.strip())
    # UIA Value / FullDescription (Explorer moderno)
    try:
        el = getattr(obj, "UIAElement", None) or getattr(obj, "UIAElement", None)
        if el is not None:
            for prop in ("CurrentValue", "CachedValue", "CurrentFullDescription"):
                try:
                    v = getattr(el, prop, None)
                except Exception:
                    v = None
                if isinstance(v, str) and v.strip():
                    texts.append(v.strip())
    except Exception:
        pass

    for t in texts:
        if t.lower().startswith("file:"):
            try:
                t = urllib.request.url2pathname(t[5:])
            except Exception:
                t = t[5:]
            if t.startswith("///"):
                t = t[3:]
            elif t.startswith("//"):
                t = t[2:]
        if _is_local_image_file(t):
            return t
    # Nome file + cartella del parent (value del contenitore)
    try:
        name = (getattr(obj, "name", None) or "").strip().strip('"')
    except Exception:
        name = ""
    if name and os.path.splitext(name)[1].lower() in IMG_EXTS:
        try:
            parent = obj.parent
        except Exception:
            parent = None
        hops = 0
        while parent is not None and hops < 8:
            try:
                pval = getattr(parent, "value", None) or getattr(parent, "name", None)
            except Exception:
                pval = None
            if isinstance(pval, str):
                folder = pval.strip().strip('"')
                if folder.lower().startswith("file:"):
                    try:
                        folder = urllib.request.url2pathname(folder[5:])
                    except Exception:
                        pass
                if os.path.isdir(folder):
                    cand = os.path.join(folder, name)
                    if _is_local_image_file(cand):
                        return cand
            try:
                parent = parent.parent
            except Exception:
                break
            hops += 1
    return ""


def resolve_local_image_file_path():
    """Path immagine sotto focus/navigatore (Explorer, Desktop, elenchi file).

    Da chiamare sul thread principale NVDA.
    """
    try:
        import api
    except Exception:
        api = None

    objs = []
    if api is not None:
        for getter in (
            getattr(api, "getFocusObject", None),
            getattr(api, "getNavigatorObject", None),
        ):
            if getter is None:
                continue
            try:
                o = getter()
            except Exception:
                o = None
            if o is not None and o not in objs:
                objs.append(o)

    for obj in list(objs):
        p = _path_guess_from_nvda_object(obj)
        if p:
            return p
        # figlio / parent vicini
        try:
            ch = obj.firstChild
            if ch is not None:
                p = _path_guess_from_nvda_object(ch)
                if p:
                    return p
        except Exception:
            pass
        try:
            par = obj.parent
            if par is not None:
                p = _path_guess_from_nvda_object(par)
                if p:
                    return p
        except Exception:
            pass

    # Shell: selezione nella finestra Explorer in primo piano (affidabile)
    return _shell_foreground_selected_image_path() or ""


def snapshot_navigator_image_source():
    """Cattura metadati navigatore sul thread principale NVDA.

    Non scarica né scrive file. Returns dict:
      ok_source, urls, rect, name, page_url, alt_hint, file_path, error
    """
    out = {
        "ok_source": False,
        "urls": [],
        "rect": None,
        "name": "",
        "page_url": "",
        "alt_hint": "",
        "file_path": "",
        "error": "",
    }
    try:
        import api
    except Exception:
        out["error"] = "API NVDA non disponibile."
        return out

    nav = None
    focus = None
    try:
        nav = api.getNavigatorObject()
    except Exception:
        nav = None
    try:
        focus = api.getFocusObject()
    except Exception:
        focus = None
    if nav is None:
        nav = focus
    if nav is None:
        out["error"] = (
            "Nessun oggetto navigatore. "
            "Vai su una figura con la lettera g, oppure su un file "
            "immagine in Esplora file, e riprova."
        )
        return out

    # Web / browse mode: MAI prendere un file ancora selezionato in Explorer
    # in secondo piano (era la causa della descrizione «J medical» ripetuta).
    web_ctx = (
        _object_looks_like_web_context(nav)
        or _object_looks_like_web_context(focus)
        or (not _foreground_is_file_manager() and bool(_document_url_from_obj(nav)))
    )
    if not web_ctx:
        local = resolve_local_image_file_path()
        if local:
            out["ok_source"] = True
            out["file_path"] = local
            out["name"] = os.path.basename(local)
            return out

    # Browse mode: a volte l'oggetto utile è NVDAObjectAtStart
    real = nav
    for attr in ("NVDAObjectAtStart", "objectAtStart"):
        try:
            cand = getattr(nav, attr, None)
            if cand is not None:
                real = cand
                break
        except Exception:
            pass
    try:
        if hasattr(nav, "_get_NVDAObjectAtStart"):
            cand = nav._get_NVDAObjectAtStart()
            if cand is not None:
                real = cand
    except Exception:
        pass

    try:
        out["name"] = (getattr(real, "name", None) or getattr(nav, "name", None) or "") or ""
    except Exception:
        out["name"] = ""
    out["alt_hint"] = _alt_hint_from_name(out["name"])
    out["page_url"] = _document_url_from_obj(real) or _document_url_from_obj(nav)

    graphic_roles = _nvda_role_set()
    candidates = []
    for obj in (real, nav):
        if obj is not None and obj not in candidates:
            candidates.append(obj)
    for root in (real, nav):
        if root is None:
            continue
        try:
            child = root.firstChild
            depth = 0
            while child is not None and depth < 10:
                if child not in candidates:
                    candidates.append(child)
                try:
                    child = child.next
                except Exception:
                    break
                depth += 1
        except Exception:
            pass
        try:
            parent = root.parent
            if parent is not None and parent not in candidates:
                candidates.append(parent)
                ch = parent.firstChild
                d = 0
                while ch is not None and d < 14:
                    if ch not in candidates:
                        candidates.append(ch)
                    try:
                        ch = ch.next
                    except Exception:
                        break
                    d += 1
        except Exception:
            pass

    urls = []
    rect = None
    base = out["page_url"]
    for obj in candidates:
        for u in _collect_image_url_from_obj(obj, base=base):
            if u not in urls:
                urls.append(u)
        try:
            role = getattr(obj, "role", None)
        except Exception:
            role = None
        if graphic_roles and role in graphic_roles and rect is None:
            rect = _object_location_tuple(obj)
    if rect is None:
        rect = _object_location_tuple(real) or _object_location_tuple(nav)

    out["urls"] = urls
    out["rect"] = rect
    if urls or rect or (out["page_url"] and out["alt_hint"]):
        out["ok_source"] = True
    else:
        out["error"] = (
            "Su questo elemento non trovo URL né area da catturare. "
            "Posizionati su una figura con g e riprova."
        )
    return out


def materialize_image_from_snapshot(snap):
    """Da snapshot (thread qualsiasi): file locale / download URL / cattura rect."""
    result = {"ok": False, "path": "", "error": "", "method": ""}
    if rtad_ocr is None:
        result["error"] = "Modulo immagini non disponibile."
        return result
    if not snap:
        result["error"] = "Nessuna immagine da analizzare."
        return result

    # File già su disco (Explorer / Desktop): nessuna copia temp
    file_path = snap.get("file_path") or ""
    if _is_local_image_file(file_path):
        result["ok"] = True
        result["path"] = file_path
        result["method"] = "file"
        return result

    urls = list(snap.get("urls") or [])
    page_url = snap.get("page_url") or ""
    alt_hint = snap.get("alt_hint") or ""

    # Edge/Chrome spesso non espongono src in IA2: recupera dall'HTML via alt
    if page_url and alt_hint:
        found = _find_img_url_in_page_html(page_url, alt_hint)
        if found and found not in urls:
            urls.insert(0, found)

    for u in urls:
        dl = rtad_ocr.materialize_image_from_url(u)
        if dl.get("ok") and dl.get("path"):
            result["ok"] = True
            result["path"] = dl["path"]
            result["method"] = "url"
            return result

    rect = snap.get("rect")
    if rect and len(rect) == 4:
        left, top, width, height = rect
        cap = rtad_ocr.materialize_image_from_screen_rect(left, top, width, height)
        if cap.get("ok") and cap.get("path"):
            result["ok"] = True
            result["path"] = cap["path"]
            result["method"] = "capture"
            return result
        result["error"] = cap.get("error") or "Cattura area non riuscita."
        return result

    result["error"] = (
        "Nessun file immagine, URL o area da catturare. "
        "Su web: lettera g sulla figura. In Esplora file: freccia sul file immagine."
    )
    return result


def capture_navigator_image():
    """Compat: snapshot (main thread) + materialize. Preferire i due passi separati."""
    snap = snapshot_navigator_image_source()
    if not snap.get("ok_source"):
        return {
            "ok": False,
            "path": "",
            "error": snap.get("error") or "Navigatore non disponibile.",
            "method": "",
        }
    return materialize_image_from_snapshot(snap)


class ImageInfoFrame(wx.Frame):
    """Finestra descrizione / etichette / scheda tecnica immagine (1.6.3).

    parent=None di proposito: resta aperta e consultabile anche se si
    iconizza/cambia finestra; si chiude solo con Chiudi o ESC.
    """

    def __init__(self, parent, title, body_text, image_path=""):
        # Ignora parent: top-level indipendente (non si chiude col dialogo padre)
        super(ImageInfoFrame, self).__init__(
            None,
            title=title,
            size=(720, 520),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.image_path = image_path or ""
        self.body_text = body_text or ""

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(
            panel,
            label=os.path.basename(self.image_path) if self.image_path else "Immagine",
        )
        vbox.Add(lbl, 0, wx.ALL, 8)

        self.txt_display = wx.TextCtrl(
            panel,
            value=self.body_text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
        )
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_copy = wx.Button(panel, label="&Copia testo")
        btn_copy.Bind(wx.EVT_BUTTON, self.on_copy)
        hbox.Add(btn_copy, 0, wx.ALL, 5)
        btn_close = wx.Button(panel, label="Chiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        hbox.Add(btn_close, 0, wx.ALL, 5)
        vbox.Add(hbox, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        panel.SetSizer(vbox)
        self.Centre()
        self.txt_display.SetFocus()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        rtad_speak(f"{title}. Usa le frecce per leggere.")

    def on_copy(self, event=None):
        text = self.txt_display.GetValue()
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
            rtad_speak("Testo copiato negli appunti.")
        else:
            rtad_speak("Impossibile aprire gli appunti.")

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
            "• Descrivi con NVDA+Shift+G: figura web (lettera g) oppure\n"
            "  file immagine in Esplora file/Desktop senza aprirlo.\n"
            "• Anche da Strumenti: Descrivi da URL, Appunti, cattura, PDF\n"
            "  (gemello della Standalone).\n"
            "• Senza parola chiave + tipo file: elenco [ELENCO] in cartella.\n"
            "• Alt-text; fix immagine «sempre la stessa» da Explorer in background.\n"
            "• Restano Gemini / Vision 1.6.3, notifica 1.6.2.\n"
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
        
        rtad_speak("Finestra delle novità aperta. Usa le frecce per leggere.")

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            event.Skip()


class PracticalGuideFrame(wx.Frame):
    """Guida in linguaggio semplice (parallela alla guida tecnica F1)."""

    def __init__(self, parent):
        title = (
            rtad_guida_pratica.get_guide_title()
            if rtad_guida_pratica is not None
            else "Guida pratica"
        )
        super(PracticalGuideFrame, self).__init__(
            parent,
            title=title,
            size=(760, 560),
            style=wx.DEFAULT_FRAME_STYLE,
        )

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        if rtad_guida_pratica is not None:
            text_content = rtad_guida_pratica.get_guide_text()
        else:
            text_content = (
                "Guida pratica non disponibile in questa build.\n"
                "Usa Aiuto → Guida ai Comandi (F1)."
            )

        lbl_info = wx.StaticText(
            panel,
            label="Guida semplice per conoscere il programma. Le frecce scorrono il testo.",
        )
        vbox.Add(lbl_info, 0, wx.ALL, 8)

        self.txt_display = wx.TextCtrl(
            panel,
            value=text_content,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
        )
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_close = wx.Button(panel, label="Chiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
        hbox_btns.Add(btn_close, 0, wx.ALL, 5)
        vbox.Add(hbox_btns, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        panel.SetSizer(vbox)
        self.Centre()
        self.txt_display.SetFocus()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        rtad_speak(
            "Guida pratica aperta. Usa le frecce per leggere. Esc per chiudere."
        )

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
            "  - NVDA + Shift + G : Descrivi grafica web (lettera g) oppure file immagine\n"
            "    selezionato in Esplora file / Desktop (senza aprirlo)\n"
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
            "  - Alt + Shift + K : Cattura schermo e descrivi l'immagine\n"
            "  - Ctrl + Shift + U : Descrivi immagine da URL\n"
            "  - Ctrl + Shift + I : Descrivi immagine dagli Appunti (o URL)\n"
            "  - Ctrl + P : Stampa rapida dei risultati di ricerca in lista\n"
            "  - Ctrl + E : Esporta Risultati\n"
            "  - Ctrl + D : Aggiunge percorso attuale ai Segnalibri\n"            "  - Ctrl + Shift + P : Salva profilo di ricerca attuale\n"            "  - Ctrl + Shift + L : Carica un profilo di ricerca\n"
            "  - INVIO (su campo testo) : Avvia subito la ricerca\n"
            "  - INVIO (sui risultati) : Apri file alla riga esatta, oppure articolo feed nel browser\n"
            "  - SPAZIO / F4 : Anteprima vocale immediata del contesto\n"
            "  - F7 : Attiva / Disattiva annunci RTAD (Mute)\n"
            "  - Menu Voce : Mute RTAD (velocità/voce = impostazioni NVDA)\n"
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

        btn_close = wx.Button(panel, label="Chiudi (ESC)")
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
            rtad_speak("Testo dei comandi copiato negli appunti!")

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
        self.profile_items = []
        self.history_query_items = []
        self.last_alt_p_time = 0
        self.last_feed_raw_occurrences = 0
        self.current_sort = load_sort_preference()
        try:
            load_rtad_speech_settings()
        except Exception:
            pass

        self._init_menu_bar()

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        lbl_query = wx.StaticText(panel, label="Testo o frase da cercare (supporta più termini e dialetti):")
        vbox.Add(lbl_query, 0, wx.ALL, 5)
        hbox_query = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_query = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.txt_query.Bind(wx.EVT_TEXT_ENTER, lambda e: self.start_search_thread())
        hbox_query.Add(self.txt_query, 1, wx.EXPAND | wx.ALL, 5)
        btn_query_hist = wx.Button(panel, label="Cronologia")
        btn_query_hist.Bind(wx.EVT_BUTTON, self.on_recall_query_history)
        hbox_query.Add(btn_query_hist, 0, wx.ALL, 5)
        vbox.Add(hbox_query, 0, wx.EXPAND)

        hbox_filter = wx.BoxSizer(wx.HORIZONTAL)
        vbox_filter_choice = wx.BoxSizer(wx.VERTICAL)
        lbl_filter = wx.StaticText(panel, label="Tipo di file da cercare:")
        vbox_filter_choice.Add(lbl_filter, 0, wx.ALL, 5)
        self.combo_filter = wx.Choice(
            panel,
            choices=_filter_choice_labels(),
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

        lbl_path = wx.StaticText(panel, label="Percorso di ricerca (Memoria automatica o inserisci link Feed RSS):")
        vbox.Add(lbl_path, 0, wx.ALL, 5)

        hbox_path = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_path = wx.TextCtrl(panel, value=load_last_path())
        hbox_path.Add(self.txt_path, 1, wx.EXPAND | wx.ALL, 5)

        btn_browse = wx.Button(panel, label="Sfoglia...")
        btn_browse.Bind(wx.EVT_BUTTON, self.on_browse)
        hbox_path.Add(btn_browse, 0, wx.ALL, 5)

        btn_all_pc = wx.Button(panel, label="&Tutto il PC")
        btn_all_pc.Bind(wx.EVT_BUTTON, self.on_search_all_pc)
        hbox_path.Add(btn_all_pc, 0, wx.ALL, 5)

        btn_tb_feeds = wx.Button(panel, label="Feed Thunderbird")
        btn_tb_feeds.Bind(wx.EVT_BUTTON, self.on_detect_thunderbird_feeds)
        hbox_path.Add(btn_tb_feeds, 0, wx.ALL, 5)
        vbox.Add(hbox_path, 0, wx.EXPAND)

        self.chk_feed_raw = wx.CheckBox(
            panel,
            label="Nei feed, elenca anche le occorrenze grezze (oltre agli articoli)",
        )
        self.chk_feed_raw.SetValue(False)
        vbox.Add(self.chk_feed_raw, 0, wx.ALL, 5)

        self.chk_ocr = wx.CheckBox(
            panel,
            label="Includi testo in immagini e PDF scansionati (OCR, più lento)",
        )
        try:
            self.chk_ocr.SetValue(load_include_ocr_preference())
        except Exception:
            self.chk_ocr.SetValue(False)
        self.chk_ocr.Bind(wx.EVT_CHECKBOX, self.on_ocr_checkbox)
        vbox.Add(self.chk_ocr, 0, wx.ALL, 5)

        self.chk_visual = wx.CheckBox(
            panel,
            label="Includi contenuto visivo delle immagini (etichette/scene, richiede Google Vision)",
        )
        try:
            self.chk_visual.SetValue(load_include_visual_preference())
        except Exception:
            self.chk_visual.SetValue(False)
        self.chk_visual.Bind(wx.EVT_CHECKBOX, self.on_visual_checkbox)
        vbox.Add(self.chk_visual, 0, wx.ALL, 5)

        self.chk_zip = wx.CheckBox(
            panel,
            label="Includi contenuti negli archivi ZIP (opt-in, più lento)",
        )
        try:
            self.chk_zip.SetValue(load_include_zip_preference())
        except Exception:
            self.chk_zip.SetValue(False)
        self.chk_zip.Bind(wx.EVT_CHECKBOX, self.on_zip_checkbox)
        vbox.Add(self.chk_zip, 0, wx.ALL, 5)

        hbox_ocr_eng = wx.BoxSizer(wx.HORIZONTAL)
        lbl_ocr_eng = wx.StaticText(panel, label="Motore OCR:")
        hbox_ocr_eng.Add(lbl_ocr_eng, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.choice_ocr_engine = wx.Choice(
            panel,
            choices=[
                "Windows (predefinito, incluso)",
                "EasyOCR (opzionale, se installato nell'ambiente Python)",
                "Google Cloud Vision (chiave API personale)",
            ],
        )
        self.choice_ocr_engine.SetName("Motore OCR")
        try:
            eng = load_ocr_engine_preference()
        except Exception:
            eng = "windows"
        try:
            gkey = load_google_vision_api_key()
            if rtad_ocr is not None:
                rtad_ocr.set_google_api_key(gkey)
        except Exception:
            pass
        try:
            gemkey = load_gemini_api_key()
            if rtad_ocr is not None:
                rtad_ocr.set_gemini_api_key(gemkey)
        except Exception:
            pass
        self.choice_ocr_engine.SetSelection(ocr_choice_index_from_engine(eng))
        if rtad_ocr is not None:
            try:
                rtad_ocr.set_engine_preference(eng)
            except Exception:
                pass
        self.choice_ocr_engine.Bind(wx.EVT_CHOICE, self.on_ocr_engine_choice)
        hbox_ocr_eng.Add(self.choice_ocr_engine, 1, wx.EXPAND)
        btn_gkey = wx.Button(panel, label="Chiave &Google…")
        btn_gkey.SetName("Chiave API Google Vision")
        btn_gkey.Bind(wx.EVT_BUTTON, self.on_set_google_vision_key)
        hbox_ocr_eng.Add(btn_gkey, 0, wx.LEFT, 8)
        btn_gem = wx.Button(panel, label="Chiave Ge&mini…")
        btn_gem.SetName("Chiave API Gemini")
        btn_gem.Bind(wx.EVT_BUTTON, self.on_set_gemini_api_key)
        hbox_ocr_eng.Add(btn_gem, 0, wx.LEFT, 8)
        vbox.Add(hbox_ocr_eng, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        hbox_actions = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_search = wx.Button(panel, label="Avvia Ricerca")
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

        btn_copy_status = wx.Button(panel, label="Copia Stato")
        btn_copy_status.Bind(wx.EVT_BUTTON, lambda e: self.copy_status_to_clipboard())
        hbox_actions.Add(btn_copy_status, 0, wx.ALL, 5)

        btn_screenshot = wx.Button(panel, label="Cattura Schermo (Alt+K)")
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

        lbl_filter_res = wx.StaticText(panel, label="Filtra i risultati nella lista (Ctrl+F):")
        vbox.Add(lbl_filter_res, 0, wx.ALL, 5)
        self.txt_filter = wx.TextCtrl(panel)
        self.txt_filter.Bind(wx.EVT_TEXT, self.on_filter_text)
        vbox.Add(self.txt_filter, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        lbl_results = wx.StaticText(
            panel,
            label="Risultati trovati (INVIO per riga esatta, SPAZIO/F4 anteprima audio, APPLICAZIONI opzioni):",
        )
        vbox.Add(lbl_results, 0, wx.ALL, 5)
        self.lst_results = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.lst_results.Bind(wx.EVT_CHAR_HOOK, self.on_list_char_hook)
        self.lst_results.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open_file_event)
        self.lst_results.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        vbox.Add(self.lst_results, 1, wx.EXPAND | wx.ALL, 5)

        hbox_bottom = wx.BoxSizer(wx.HORIZONTAL)
        btn_open = wx.Button(panel, label="Apri File (Alla Riga)")
        btn_open.Bind(wx.EVT_BUTTON, self.on_open_file_event)
        hbox_bottom.Add(btn_open, 0, wx.ALL, 5)

        btn_preview = wx.Button(panel, label="Anteprima Voce (F4)")
        btn_preview.Bind(wx.EVT_BUTTON, lambda e: self.speak_selected_preview())
        hbox_bottom.Add(btn_preview, 0, wx.ALL, 5)
        
        btn_export = wx.Button(panel, label="Esporta Risultati...")
        btn_export.Bind(wx.EVT_BUTTON, self.on_export_results)
        hbox_bottom.Add(btn_export, 0, wx.ALL, 5)
        
        btn_print = wx.Button(panel, label="Stampa Risultati...")
        btn_print.Bind(wx.EVT_BUTTON, self.on_print_results)
        hbox_bottom.Add(btn_print, 0, wx.ALL, 5)

        btn_github = wx.Button(panel, label="Pagina GitHub")
        btn_github.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open(GITHUB_URL))
        hbox_bottom.Add(btn_github, 0, wx.ALL, 5)

        btn_close = wx.Button(panel, label="Chiudi")
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

    def show_practical_guide_dialog(self):
        dlg = PracticalGuideFrame(self)
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
            rtad_speak("Apertura client di posta per la segnalazione...")
        except Exception:
            rtad_speak("Impossibile aprire il programma di posta.")

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
            rtad_speak("Scheda diagnostica esportata sul Desktop.")
            wx.MessageBox(
                f"File salvato:\n{dest}",
                "Esportazione riuscita",
                wx.OK | wx.ICON_INFORMATION,
            )
        except Exception:
            rtad_speak("Errore nell'esportazione della scheda diagnostica.")

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
                "F7 : Mute annunci RTAD (velocità/voce = NVDA)\n"
            )
            temp = os.path.join(CONFIG_DIR, "stampa_guida_addon.txt")
            with open(temp, "w", encoding="utf-8") as f:
                f.write(guide)
            notepad = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "notepad.exe")
            if not os.path.exists(notepad):
                notepad = "notepad.exe"
            subprocess.Popen([notepad, "/p", temp])
            rtad_speak("Guida inviata alla stampante predefinita.")
        except Exception:
            rtad_speak("Impossibile stampare la guida.")

    def on_check_updates(self, event=None, silent=False):
        def _check():
            try:
                if not silent:
                    wx.CallAfter(rtad_speak, "Verifica aggiornamenti in corso...")
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
                        wx.CallAfter(rtad_speak, "Nessuna informazione di versione online.")
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
                            rtad_speak("Apertura pagina download aggiornamento...")
                        dlg.Destroy()

                    wx.CallAfter(_prompt)
                else:
                    if not silent:
                        wx.CallAfter(rtad_speak, "Versione aggiornata.")
            except Exception:
                if not silent:
                    wx.CallAfter(rtad_speak, "Impossibile verificare la connessione.")

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
        menubar.Append(self.history_menu, "&Cronologia")

        self.Bind(wx.EVT_MENU, self.on_recall_query_history, item_hist_query)
        self.Bind(wx.EVT_MENU, self.on_recall_path_history, item_hist_path)
        self.Bind(wx.EVT_MENU, self.on_clear_query_history, item_clear_queries)
        self.Bind(wx.EVT_MENU, self.on_clear_path_history, item_clear_paths)
        self.update_history_menu()

        # Menu Profili
        self.profiles_menu = wx.Menu()
        item_save_profile = self.profiles_menu.Append(
            wx.ID_ANY, "Salva profilo &attuale...\tCtrl+Shift+P"
        )
        item_load_profile = self.profiles_menu.Append(
            wx.ID_ANY, "&Carica profilo...\tCtrl+Shift+L"
        )
        item_manage_profiles = self.profiles_menu.Append(
            wx.ID_ANY, "&Gestisci profili..."
        )
        self.profiles_menu.AppendSeparator()
        menubar.Append(self.profiles_menu, "P&rofili")

        self.Bind(wx.EVT_MENU, self.on_save_search_profile, item_save_profile)
        self.Bind(wx.EVT_MENU, self.on_load_search_profile_dialog, item_load_profile)
        self.Bind(wx.EVT_MENU, self.on_manage_search_profiles, item_manage_profiles)
        self.update_profiles_menu()

        # Menu Voce (Add-on: Mute RTAD; velocità/voce = NVDA)
        voice_menu = wx.Menu()
        item_toggle_speech = voice_menu.Append(
            wx.ID_ANY, "Attiva / Disattiva annunci RTAD (Mute)\tF7"
        )
        voice_menu.AppendSeparator()
        item_voice_help = voice_menu.Append(
            wx.ID_ANY, "Velocità e voce: usa le impostazioni &NVDA..."
        )
        menubar.Append(voice_menu, "&Voce")

        self.Bind(wx.EVT_MENU, self.on_toggle_rtad_speech, item_toggle_speech)
        self.Bind(wx.EVT_MENU, self.on_nvda_voice_help, item_voice_help)

        # Menu Strumenti
        tools_menu = wx.Menu()
        item_update = tools_menu.Append(wx.ID_ANY, "Verifica &Aggiornamenti...\tCtrl+U")
        tools_menu.AppendSeparator()
        item_gkey = tools_menu.Append(
            wx.ID_ANY, "Chiave API &Google Vision…"
        )
        self.Bind(wx.EVT_MENU, self.on_set_google_vision_key, item_gkey)
        item_gemkey = tools_menu.Append(
            wx.ID_ANY, "Chiave API Ge&mini (descrizione avanzata)…"
        )
        self.Bind(wx.EVT_MENU, self.on_set_gemini_api_key, item_gemkey)
        item_clear_ocr = tools_menu.Append(
            wx.ID_ANY, "S&vuota cache OCR…"
        )
        self.Bind(wx.EVT_MENU, self.on_clear_ocr_cache, item_clear_ocr)
        tools_menu.AppendSeparator()
        item_desc_url = tools_menu.Append(
            wx.ID_ANY, "Descrivi immagine da &URL…\tCtrl+Shift+U"
        )
        self.Bind(wx.EVT_MENU, self.on_describe_from_url, item_desc_url)
        item_desc_clip = tools_menu.Append(
            wx.ID_ANY, "Descrivi immagine dagli &Appunti\tCtrl+Shift+I"
        )
        self.Bind(wx.EVT_MENU, self.on_describe_from_clipboard, item_desc_clip)
        item_desc_cap = tools_menu.Append(
            wx.ID_ANY, "Cattura schermo e &descrivi\tAlt+Shift+K"
        )
        self.Bind(wx.EVT_MENU, self.on_describe_from_screenshot, item_desc_cap)
        item_desc_pdf = tools_menu.Append(
            wx.ID_ANY, "Descrivi immagine da P&DF…"
        )
        self.Bind(wx.EVT_MENU, self.on_describe_pdf_dialog, item_desc_pdf)
        tools_menu.AppendSeparator()
        self.item_notify_end = tools_menu.AppendCheckItem(
            wx.ID_ANY, "&Notifica a fine ricerca (Centro notifiche Windows)"
        )
        try:
            self.item_notify_end.Check(load_notify_search_end_preference())
        except Exception:
            self.item_notify_end.Check(True)
        self.Bind(wx.EVT_MENU, self.on_toggle_notify_search_end, self.item_notify_end)
        self.item_escape_closes = tools_menu.AppendCheckItem(
            wx.ID_ANY, "Esc chiude l'&applicazione (altrimenti Alt+F4 / Ctrl+Q / Chiudi)"
        )
        try:
            self.item_escape_closes.Check(load_escape_closes_preference())
        except Exception:
            self.item_escape_closes.Check(False)
        menubar.Append(tools_menu, "Stru&menti")

        # Menu Aiuto
        help_menu = wx.Menu()
        item_whatsnew = help_menu.Append(wx.ID_ANY, "&Novità della Versione")
        item_practical = help_menu.Append(
            wx.ID_ANY, "Guida &pratica (per avvicinarsi al programma)"
        )
        item_guide = help_menu.Append(wx.ID_ANY, "&Guida ai Comandi\tF1")
        item_print_guide = help_menu.Append(wx.ID_ANY, "Stampa &Guida ai Comandi")
        item_github = help_menu.Append(wx.ID_ANY, "Pagina Ufficiale &GitHub")
        item_info = help_menu.Append(wx.ID_ANY, "&Info Versione\tAlt+I")
        help_menu.AppendSeparator()
        item_diag = help_menu.Append(wx.ID_ANY, "Esporta Info &Diagnostica sul Desktop")
        item_feedback = help_menu.Append(wx.ID_ANY, "Segnala un Problema / Invia &Feedback")
        menubar.Append(help_menu, "Aiuto")

        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self.on_export_results, item_export)
        self.Bind(wx.EVT_MENU, self.on_print_results, item_print)
        self.Bind(wx.EVT_MENU, self.on_close, item_exit)
        self.Bind(wx.EVT_MENU, self.on_check_updates, item_update)
        self.Bind(wx.EVT_MENU, self.on_toggle_escape_closes, self.item_escape_closes)
        self.Bind(wx.EVT_MENU, lambda e: self.show_whats_new_dialog(), item_whatsnew)
        self.Bind(wx.EVT_MENU, lambda e: self.show_practical_guide_dialog(), item_practical)
        self.Bind(wx.EVT_MENU, lambda e: self.show_shortcuts_dialog(), item_guide)
        self.Bind(wx.EVT_MENU, self.on_print_guide, item_print_guide)
        self.Bind(wx.EVT_MENU, lambda e: webbrowser.open(GITHUB_URL), item_github)
        self.Bind(wx.EVT_MENU, self.on_show_info, item_info)
        self.Bind(wx.EVT_MENU, self.on_export_diagnostic, item_diag)
        self.Bind(wx.EVT_MENU, self.on_send_feedback, item_feedback)

    def on_add_bookmark(self, event=None):
        path = self.txt_path.GetValue().strip()
        if not path:
            wx.CallLater(200, lambda: rtad_speak("Nessun percorso da salvare."))
            return
        bms = load_bookmarks()
        if path not in bms:
            bms.append(path)
            save_bookmarks(bms)
            self.update_bookmarks_menu()
            wx.CallLater(200, lambda: rtad_speak("Percorso salvato nei segnalibri."))
        else:
            wx.CallLater(200, lambda: rtad_speak("Percorso già presente nei segnalibri."))

    def on_manage_bookmarks(self, event=None):
        bms = load_bookmarks()
        if not bms:
            wx.CallLater(200, lambda: rtad_speak("Nessun segnalibro salvato."))
            return
        dlg = wx.SingleChoiceDialog(self, "Seleziona il segnalibro da ELIMINARE:", "Gestione Segnalibri", bms)
        if dlg.ShowModal() == wx.ID_OK:
            sel = dlg.GetStringSelection()
            if sel in bms:
                bms.remove(sel)
                save_bookmarks(bms)
                self.update_bookmarks_menu()
                wx.CallLater(200, lambda: rtad_speak("Segnalibro eliminato correttamente."))
        dlg.Destroy()

    def on_select_bookmark(self, path):
        self.txt_path.SetValue(path)
        save_last_path(path)
        wx.CallLater(200, lambda: rtad_speak(f"Segnalibro caricato: {path}"))

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
            wx.CallLater(200, lambda: rtad_speak("Nessun testo nella cronologia."))
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
            wx.CallLater(200, lambda: rtad_speak("Nessun percorso nella cronologia."))
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
                wx.CallLater(200, lambda: rtad_speak(f"Percorso ripreso: {sel}"))
        dlg.Destroy()

    def on_apply_history_query(self, query):
        self.txt_query.SetValue(query)
        self.txt_query.SetFocus()
        self.txt_query.SetInsertionPointEnd()
        wx.CallLater(200, lambda: rtad_speak(f"Testo ripreso: {query}"))

    def on_clear_query_history(self, event=None):
        if not load_query_history():
            wx.CallLater(200, lambda: rtad_speak("La cronologia testi è già vuota."))
            return
        clear_query_history()
        self.update_history_menu()
        wx.CallLater(200, lambda: rtad_speak("Cronologia testi svuotata."))

    def on_clear_path_history(self, event=None):
        if not load_path_history():
            wx.CallLater(200, lambda: rtad_speak("La cronologia percorsi è già vuota."))
            return
        clear_path_history()
        wx.CallLater(200, lambda: rtad_speak("Cronologia percorsi svuotata."))


    def update_profiles_menu(self):
        for item_id in self.profile_items:
            self.profiles_menu.Remove(item_id)
        self.profile_items.clear()
        for profile in load_search_profiles():
            label = profile["name"]
            if profile.get("query"):
                label = f"{label}  [con testo]"
            item = self.profiles_menu.Append(wx.ID_ANY, label)
            self.profile_items.append(item.GetId())
            self.Bind(
                wx.EVT_MENU,
                lambda e, p=profile: self.apply_search_profile(p),
                item,
            )

    def _collect_current_profile_fields(self):
        path = self.txt_path.GetValue().strip()
        filter_mode = self.combo_filter.GetSelection()
        if filter_mode < 0:
            filter_mode = 0
        custom_ext = self.txt_custom_ext.GetValue().strip()
        if custom_ext and not custom_ext.startswith("."):
            custom_ext = "." + custom_ext
        return {
            "path": path,
            "filter_mode": filter_mode,
            "custom_ext": custom_ext if filter_mode == 4 else "",
            "include_feed_raw": bool(self.chk_feed_raw.GetValue()),
            "include_ocr": bool(self.chk_ocr.GetValue()),
            "include_visual": bool(
                getattr(self, "chk_visual", None) and self.chk_visual.GetValue()
            ),
            "include_zip": bool(self.chk_zip.GetValue()),
            "ocr_engine": ocr_engine_from_choice_index(
                self.choice_ocr_engine.GetSelection()
                if getattr(self, "choice_ocr_engine", None)
                else 0
            ),
            "query": self.txt_query.GetValue().strip(),
        }

    def on_set_google_vision_key(self, event=None):
        current = ""
        try:
            current = load_google_vision_api_key()
        except Exception:
            current = ""
        dlg = wx.TextEntryDialog(
            self,
            "Incolla qui la TUA chiave API di Google Cloud Vision.\n"
            "Vale solo per te, su questo PC. Gli altri utenti inseriscono la loro.\n"
            "Lascia vuoto e conferma per rimuovere la chiave salvata.\n\n"
            "Console Google Cloud → API e servizi → Credenziali → Chiave API\n"
            "(abilita anche «Cloud Vision API»).",
            "Chiave API Google Vision",
            current,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            new_key = (dlg.GetValue() or "").strip()
        finally:
            dlg.Destroy()
        try:
            save_google_vision_api_key(new_key)
        except Exception as e:
            rtad_speak(f"Impossibile salvare la chiave: {e}", force=True)
            return
        if new_key:
            try:
                self.choice_ocr_engine.SetSelection(2)
                save_ocr_engine_preference("google")
                if rtad_ocr is not None:
                    rtad_ocr.set_engine_preference("google")
            except Exception:
                pass
            rtad_speak(
                "Chiave Google Vision salvata in locale. "
                "Motore OCR impostato su Google Cloud Vision.",
                force=True,
            )
        else:
            rtad_speak("Chiave Google Vision rimossa.", force=True)

    def on_set_gemini_api_key(self, event=None):
        current = ""
        try:
            current = load_gemini_api_key()
        except Exception:
            current = ""
        dlg = wx.TextEntryDialog(
            self,
            "Incolla qui la TUA chiave API Gemini (Google AI Studio).\n"
            "Serve per la descrizione avanzata delle immagini.\n"
            "Consigliata una chiave dedicata a RTAD (non quella di altri programmi).\n"
            "Vale solo per te, su questo PC. Gli altri utenti inseriscono la loro.\n"
            "Lascia vuoto e conferma per rimuovere la chiave salvata.\n\n"
            "Crea la chiave su: https://aistudio.google.com/apikey\n"
            "(L’abbonamento Gemini Plus/Pro dell’app chat NON serve per l’API.)",
            "Chiave API Gemini",
            current,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            new_key = (dlg.GetValue() or "").strip()
        finally:
            dlg.Destroy()
        try:
            save_gemini_api_key(new_key)
        except Exception as e:
            rtad_speak(f"Impossibile salvare la chiave Gemini: {e}", force=True)
            return
        if new_key:
            rtad_speak(
                "Chiave Gemini salvata in locale. "
                "Ora «Descrivi immagine» userà la descrizione avanzata.",
                force=True,
            )
        else:
            rtad_speak("Chiave Gemini rimossa.", force=True)

    def on_ocr_engine_choice(self, event=None):
        eng = ocr_engine_from_choice_index(self.choice_ocr_engine.GetSelection())
        try:
            save_ocr_engine_preference(eng)
        except Exception:
            pass
        if eng == "google" and not load_google_vision_api_key():
            rtad_speak(
                "Per Google Vision serve la tua chiave API. "
                "Apro la finestra per inserirla.",
                force=True,
            )
            self.on_set_google_vision_key()
            if not load_google_vision_api_key():
                try:
                    self.choice_ocr_engine.SetSelection(0)
                    save_ocr_engine_preference("windows")
                except Exception:
                    pass
                return
        if rtad_ocr is None:
            rtad_speak("Modulo OCR non disponibile.", force=True)
            return
        try:
            rtad_ocr.set_engine_preference(eng)
            msg = rtad_ocr.engine_status_message()
        except Exception as e:
            msg = f"Impossibile impostare il motore OCR: {e}"
        rtad_speak(msg, force=True)

    def on_ocr_checkbox(self, event=None):
        enabled = bool(self.chk_ocr.GetValue())
        try:
            save_include_ocr_preference(enabled)
        except Exception:
            pass
        if enabled:
            if rtad_ocr is None:
                rtad_speak("Modulo OCR non disponibile in questa build.", force=True)
                try:
                    self.chk_ocr.SetValue(False)
                    save_include_ocr_preference(False)
                except Exception:
                    pass
                return
            try:
                eng = ocr_engine_from_choice_index(
                    self.choice_ocr_engine.GetSelection()
                )
                if eng == "google":
                    save_google_vision_api_key(load_google_vision_api_key())
                rtad_ocr.set_engine_preference(eng)
                save_ocr_engine_preference(eng)
            except Exception:
                pass
            ok = False
            try:
                ok = bool(rtad_ocr.engine_available(force_recheck=True))
            except Exception:
                ok = False
            if not ok:
                rtad_speak(rtad_ocr.engine_status_message(), force=True)
            else:
                try:
                    status = rtad_ocr.engine_status_message()
                except Exception:
                    status = ""
                rtad_speak(
                    "OCR attivato: cercherà il testo dentro immagini e PDF scansionati. "
                    "Può richiedere più tempo. "
                    + (status or ""),
                    force=True,
                )
        else:
            rtad_speak("OCR disattivato: solo nomi file e documenti con testo.", force=True)

    def on_visual_checkbox(self, event=None):
        enabled = bool(self.chk_visual.GetValue())
        try:
            save_include_visual_preference(enabled)
        except Exception:
            pass
        if enabled:
            if rtad_ocr is None:
                rtad_speak("Modulo immagini non disponibile in questa build.", force=True)
                try:
                    self.chk_visual.SetValue(False)
                    save_include_visual_preference(False)
                except Exception:
                    pass
                return
            has_key = False
            try:
                has_key = bool(load_google_vision_api_key())
            except Exception:
                has_key = False
            if not has_key:
                rtad_speak(
                    "Per il contenuto visivo serve la chiave API Google Vision. "
                    "Apro la finestra per inserirla.",
                    force=True,
                )
                self.on_set_google_vision_key()
                try:
                    has_key = bool(load_google_vision_api_key())
                except Exception:
                    has_key = False
                if not has_key:
                    try:
                        self.chk_visual.SetValue(False)
                        save_include_visual_preference(False)
                    except Exception:
                        pass
                    rtad_speak(
                        "Contenuto visivo non attivato: manca la chiave Google.",
                        force=True,
                    )
                    return
            if rtad_ocr is not None:
                try:
                    rtad_ocr.set_google_api_key(load_google_vision_api_key())
                except Exception:
                    pass
            status = ""
            try:
                status = rtad_ocr.vision_status_message()
            except Exception:
                status = ""
            rtad_speak(
                "Contenuto visivo attivato: la ricerca userà anche etichette e scene "
                "nelle immagini (più lento, con cache). "
                + (status or ""),
                force=True,
            )
        else:
            rtad_speak("Contenuto visivo disattivato.", force=True)

    def on_zip_checkbox(self, event=None):
        enabled = bool(self.chk_zip.GetValue())
        try:
            save_include_zip_preference(enabled)
        except Exception:
            pass
        if enabled:
            if rtad_zip is None:
                rtad_speak(
                    "Modulo ZIP non disponibile in questa build.",
                    force=True,
                )
                try:
                    self.chk_zip.SetValue(False)
                    save_include_zip_preference(False)
                except Exception:
                    pass
                return
            rtad_speak(
                "Ricerca dentro gli archivi ZIP attivata.",
                force=True,
            )
        else:
            rtad_speak("Ricerca dentro ZIP disattivata.", force=True)

    def on_toggle_escape_closes(self, event=None):
        enabled = False
        try:
            enabled = bool(self.item_escape_closes.IsChecked())
        except Exception:
            enabled = not load_escape_closes_preference()
        try:
            save_escape_closes_preference(enabled)
        except Exception:
            pass
        if enabled:
            rtad_speak(
                "Esc chiude l'applicazione. Durante la ricerca Esc annulla comunque.",
                force=True,
            )
        else:
            rtad_speak(
                "Esc non chiude più l'applicazione: usa Alt+F4, Ctrl+Q o Chiudi. "
                "Durante la ricerca Esc annulla solo la scansione.",
                force=True,
            )

    def on_toggle_notify_search_end(self, event=None):
        enabled = False
        try:
            enabled = bool(self.item_notify_end.IsChecked())
        except Exception:
            enabled = not load_notify_search_end_preference()
        try:
            save_notify_search_end_preference(enabled)
        except Exception:
            pass
        if enabled:
            rtad_speak(
                "Notifica di sistema a fine ricerca attivata. "
                "Resta nel Centro notifiche Windows finché non la apri.",
                force=True,
            )
        else:
            rtad_speak(
                "Notifica di sistema a fine ricerca disattivata. Restano bip e annuncio vocale.",
                force=True,
            )

    def on_clear_ocr_cache(self, event=None):
        if rtad_ocr is None:
            rtad_speak("Modulo OCR non disponibile.")
            return
        try:
            count = int(rtad_ocr.get_ocr_cache_count() or 0)
        except Exception:
            count = 0
        cache_dir = ""
        try:
            cache_dir = rtad_ocr.get_ocr_cache_dir() or OCR_CACHE_DIR
        except Exception:
            cache_dir = OCR_CACHE_DIR
        if count <= 0:
            wx.MessageBox(
                f"La cache OCR è già vuota.\n\nCartella:\n{cache_dir}",
                "Svuota cache OCR",
                wx.OK | wx.ICON_INFORMATION,
            )
            rtad_speak("Cache OCR già vuota.")
            return
        ask = wx.MessageDialog(
            self,
            f"Eliminare {count} file dalla cache OCR?\n\n"
            f"Cartella:\n{cache_dir}\n\n"
            "Utile dopo un aggiornamento o se un’immagine non viene "
            "rilettà correttamente. La prossima ricerca rifarà l’OCR.",
            "Svuota cache OCR",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        if ask.ShowModal() != wx.ID_YES:
            ask.Destroy()
            rtad_speak("Operazione annullata.")
            return
        ask.Destroy()
        try:
            removed = int(rtad_ocr.clear_ocr_cache() or 0)
        except Exception as e:
            wx.MessageBox(
                f"Impossibile svuotare la cache OCR.\n{e}",
                "Errore",
                wx.OK | wx.ICON_ERROR,
            )
            return
        msg = f"Cache OCR svuotata: rimossi {removed} file."
        rtad_speak(msg, force=True)
        wx.MessageBox(msg, "Svuota cache OCR", wx.OK | wx.ICON_INFORMATION)

    def _notify_search_end(self, matches, stopped=False):
        """Notifica Windows persistente (Centro notifiche) a fine ricerca."""
        try:
            if not load_notify_search_end_preference():
                return
        except Exception:
            return
        if stopped:
            body = f"Ricerca interrotta. Conservati {matches} risultati."
        elif matches > 0:
            body = f"Ricerca completata: {matches} risultati."
        else:
            body = "Ricerca completata: nessun risultato."
        try:
            self.RequestUserAttention(wx.USER_ATTENTION_INFO)
        except Exception:
            pass

        def _fallback_wx():
            try:
                import wx.adv
                n = wx.adv.NotificationMessage(APP_TITLE, body, parent=self)
                try:
                    n.SetFlags(wx.ICON_INFORMATION)
                except Exception:
                    pass
                timeout = getattr(wx.adv.NotificationMessage, "Timeout_Never", 0)
                n.Show(timeout=timeout)
            except Exception:
                pass

        def _worker():
            ok = False
            try:
                ok = show_persistent_windows_notification(APP_TITLE, body)
            except Exception:
                ok = False
            if not ok:
                wx.CallAfter(_fallback_wx)

        threading.Thread(target=_worker, daemon=True).start()

    def on_save_search_profile(self, event=None):
        fields = self._collect_current_profile_fields()
        if not fields["path"] and fields["filter_mode"] == 0 and not fields["query"]:
            _announce(
                "Imposta almeno un percorso o un testo di ricerca prima di salvare un profilo."
            )
            return
        dlg = wx.TextEntryDialog(
            self,
            "Nome del profilo (es. Documenti Desktop, Feed Thunderbird):",
            "Salva profilo di ricerca",
            "",
        )
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        name = dlg.GetValue().strip()
        dlg.Destroy()
        if not name:
            _announce("Nome profilo non valido.")
            return

        include_query = False
        auto_start = False
        if fields["query"]:
            ask = wx.MessageDialog(
                self,
                f"Includere anche il testo di ricerca attuale?\n«{fields['query']}»",
                "Testo nel profilo",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            )
            include_query = ask.ShowModal() == wx.ID_YES
            ask.Destroy()
            if include_query:
                ask2 = wx.MessageDialog(
                    self,
                    "All'apertura di questo profilo, avviare subito la ricerca?",
                    "Avvio automatico",
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                )
                auto_start = ask2.ShowModal() == wx.ID_YES
                ask2.Destroy()

        profile = {
            "name": name,
            "path": fields["path"],
            "filter_mode": fields["filter_mode"],
            "custom_ext": fields["custom_ext"],
            "query": fields["query"] if include_query else "",
            "include_feed_raw": fields["include_feed_raw"],
            "include_ocr": fields["include_ocr"],
            "include_visual": fields.get("include_visual", False),
            "include_zip": fields.get("include_zip", False),
            "ocr_engine": fields.get("ocr_engine", "windows"),
            "auto_start": bool(auto_start and include_query),
        }
        replaced = upsert_search_profile(profile)
        self.update_profiles_menu()
        if replaced:
            _announce(f"Profilo aggiornato: {name}.")
        else:
            _announce(f"Profilo salvato: {name}.")

    def on_load_search_profile_dialog(self, event=None):
        profiles = load_search_profiles()
        if not profiles:
            _announce("Nessun profilo di ricerca salvato.")
            return
        names = []
        for p in profiles:
            extra = []
            extra.append(filter_mode_label(p["filter_mode"]))
            if p.get("query"):
                extra.append("con testo")
            if p.get("auto_start"):
                extra.append("avvio automatico")
            names.append(f"{p['name']} — {', '.join(extra)}")
        dlg = wx.SingleChoiceDialog(
            self,
            "Seleziona il profilo da caricare:",
            "Carica profilo di ricerca",
            names,
        )
        if dlg.ShowModal() == wx.ID_OK:
            idx = dlg.GetSelection()
            if 0 <= idx < len(profiles):
                self.apply_search_profile(profiles[idx])
        dlg.Destroy()

    def apply_search_profile(self, profile, announce=True):
        path = profile.get("path", "") or ""
        self.txt_path.SetValue(path)
        if path:
            try:
                save_last_path(path)
            except Exception:
                pass
        mode = int(profile.get("filter_mode", 0) or 0)
        if mode < 0 or mode > 4:
            mode = 0
        self.combo_filter.SetSelection(mode)
        custom = profile.get("custom_ext", "") or ""
        self.txt_custom_ext.SetValue(custom)
        self.txt_custom_ext.Enable(mode == 4)
        self.chk_feed_raw.SetValue(bool(profile.get("include_feed_raw", False)))
        ocr_on = bool(profile.get("include_ocr", False))
        self.chk_ocr.SetValue(ocr_on)
        try:
            save_include_ocr_preference(ocr_on)
        except Exception:
            pass
        vis_on = bool(profile.get("include_visual", False))
        try:
            if getattr(self, "chk_visual", None):
                self.chk_visual.SetValue(vis_on)
            save_include_visual_preference(vis_on)
        except Exception:
            pass
        zip_on = bool(profile.get("include_zip", False))
        try:
            self.chk_zip.SetValue(zip_on)
            save_include_zip_preference(zip_on)
        except Exception:
            pass
        eng = str(profile.get("ocr_engine", "windows") or "windows").strip().lower()
        if eng in ("google-vision", "google_vision", "vision", "gcv"):
            eng = "google"
        if eng not in ("windows", "easyocr", "google"):
            eng = "windows"
        try:
            self.choice_ocr_engine.SetSelection(ocr_choice_index_from_engine(eng))
            save_ocr_engine_preference(eng)
        except Exception:
            pass
        query = profile.get("query", "") or ""
        if query:
            self.txt_query.SetValue(query)
        if announce:
            bits = [f"Profilo caricato: {profile.get('name', '')}"]
            bits.append(filter_mode_label(mode))
            if path:
                bits.append(f"percorso {path}")
            if query:
                bits.append(f"testo {query}")
            if ocr_on:
                bits.append("OCR attivo")
            if zip_on:
                bits.append("ZIP attivo")
            _announce(". ".join(bits) + ".")
        if profile.get("auto_start") and query:
            wx.CallLater(350, self.start_search_thread)

    def on_manage_search_profiles(self, event=None):
        profiles = load_search_profiles()
        if not profiles:
            _announce("Nessun profilo di ricerca salvato.")
            return
        names = [p["name"] for p in profiles]
        dlg = wx.SingleChoiceDialog(
            self,
            "Seleziona un profilo, poi scegli Rinomina o Elimina:",
            "Gestisci profili",
            names,
        )
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        sel_name = dlg.GetStringSelection()
        dlg.Destroy()
        if not sel_name:
            return
        action = wx.SingleChoiceDialog(
            self,
            f"Azione per «{sel_name}»:",
            "Gestisci profilo",
            ["Rinomina", "Elimina"],
        )
        if action.ShowModal() != wx.ID_OK:
            action.Destroy()
            return
        choice = action.GetStringSelection()
        action.Destroy()
        if choice == "Elimina":
            confirm = wx.MessageDialog(
                self,
                f"Eliminare il profilo «{sel_name}»?",
                "Conferma eliminazione",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            if confirm.ShowModal() == wx.ID_YES:
                if delete_search_profile(sel_name):
                    self.update_profiles_menu()
                    _announce(f"Profilo eliminato: {sel_name}.")
                else:
                    _announce("Impossibile eliminare il profilo.")
            confirm.Destroy()
        elif choice == "Rinomina":
            rename_dlg = wx.TextEntryDialog(
                self,
                "Nuovo nome del profilo:",
                "Rinomina profilo",
                sel_name,
            )
            if rename_dlg.ShowModal() == wx.ID_OK:
                new_name = rename_dlg.GetValue().strip()
                if not new_name:
                    _announce("Nome non valido.")
                elif rename_search_profile(sel_name, new_name):
                    self.update_profiles_menu()
                    _announce(f"Profilo rinominato in {new_name}.")
                else:
                    _announce(
                        "Impossibile rinominare: nome già in uso o non trovato."
                    )
            rename_dlg.Destroy()


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
            rtad_speak("Ricerca interrotta dall'utente. Salvataggio risultati parziali in corso...")

    def on_toggle_rtad_speech(self, evt=None):
        global _rtad_speech_active
        _rtad_speech_active = not _rtad_speech_active
        try:
            save_rtad_speech_settings()
        except Exception:
            pass
        if _rtad_speech_active:
            rtad_speak("Annunci RTAD attivati.", force=True)
        else:
            rtad_speak("Annunci RTAD disattivati.", force=True)

    def on_nvda_voice_help(self, evt=None):
        msg = (
            "Nell'Add-on la velocità e la voce sono quelle di NVDA.\n\n"
            "Apri le impostazioni NVDA (NVDA+N → Preferenze → Impostazioni → "
            "Voce) per regolare voce, velocità e tono.\n\n"
            "Il menu Voce di RTAD controlla solo il Mute (F7) degli annunci "
            "dell'Add-on. Nello Standalone trovi invece SAPI regolabile."
        )
        rtad_speak(
            "Velocità e voce: usa le impostazioni NVDA. F7 muta solo gli annunci RTAD.",
            force=True,
        )
        wx.MessageBox(msg, "Voce e NVDA", wx.OK | wx.ICON_INFORMATION)

    def on_show_info(self, event):
        msg = f"{APP_TITLE}\nVersione: {APP_VERSION}\nAutore: Maurizio Barra\nLicenza: GPL v2"
        rtad_speak(f"Versione installata {APP_VERSION}. Autore Maurizio Barra.")
        wx.MessageBox(msg, "Informazioni Versione", wx.OK | wx.ICON_INFORMATION)

    def on_filter_changed(self, event):
        sel = self.combo_filter.GetSelection()
        self.txt_custom_ext.Enable(sel == 4)

    def on_search_all_pc(self, event):
        drives = get_real_ready_drives()
        drives_str = ";".join(drives)
        self.txt_path.SetValue(drives_str)
        save_last_path(drives_str)
        rtad_speak(f"Tutto il PC impostato: {len(drives)} unità attive. Premi Invio per avviare.")
        self.btn_search.SetFocus()

    def on_detect_thunderbird_feeds(self, event):
        dirs = find_thunderbird_feeds_dirs()
        if not dirs:
            rtad_speak(
                "Nessuna cartella Feed Thunderbird trovata. "
                "Verifica che Thunderbird sia installato e che esistano i Feed RSS nel profilo."
            )
            return
        joined = ";".join(dirs)
        self.txt_path.SetValue(joined)
        save_last_path(joined)
        n = len(dirs)
        rtad_speak(
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
        try:
            if wx.TheClipboard.Open():
                try:
                    wx.TheClipboard.SetData(wx.TextDataObject(msg))
                finally:
                    wx.TheClipboard.Close()
                rtad_speak("Stato copiato negli appunti.")
            else:
                rtad_speak("Impossibile copiare negli appunti.")
        except Exception:
            rtad_speak("Impossibile copiare negli appunti.")

    def focus_status_progress(self, event=None):
        try:
            self.txt_status_progress.SetFocus()
            self.txt_status_progress.SetInsertionPoint(0)
            msg = self.txt_status_progress.GetValue().strip() or "Stato avanzamento non disponibile."
            wx.CallLater(50, rtad_speak, msg)
        except Exception:
            wx.CallLater(50, rtad_speak, "Impossibile raggiungere lo stato di avanzamento.")

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
        rtad_speak(msg)

    def on_filter_text(self, event):
        # Durante la ricerca non svuotare «Ricerca in corso…» (NVDA: «sconosciuto»)
        try:
            if not self.btn_search.IsEnabled():
                if event:
                    event.Skip()
                return
        except Exception:
            pass
        self.update_list_display()

    def on_general_char_hook(self, event):
        key = event.GetKeyCode()
        ctrl = event.ControlDown()
        alt = event.AltDown()
        
        if ctrl and key in (ord("F"), ord("f")):
            self.txt_filter.SetFocus()
            rtad_speak("Filtra risultati")
            return
        elif ctrl and key in (ord("H"), ord("h")) and event.ShiftDown():
            self.on_recall_path_history()
            return
        elif ctrl and key in (ord("H"), ord("h")):
            self.on_recall_query_history()
            return
        elif ctrl and event.ShiftDown() and key in (ord("U"), ord("u")):
            self.on_describe_from_url(None)
            return
        elif ctrl and key in (ord("U"), ord("u")):
            self.on_check_updates(None)
            return
        elif ctrl and event.ShiftDown() and key in (ord("I"), ord("i")):
            self.on_describe_from_clipboard(None)
            return
        elif key == wx.WXK_F1:
            self.show_shortcuts_dialog()
            return
        elif key == wx.WXK_F7:
            self.on_toggle_rtad_speech()
            return
        elif ctrl and event.ShiftDown() and key in (ord("P"), ord("p")):
            self.on_save_search_profile(None)
            return
        elif ctrl and event.ShiftDown() and key in (ord("L"), ord("l")):
            self.on_load_search_profile_dialog(None)
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
        elif alt and key in (ord("K"), ord("k")) and event.ShiftDown():
            self.on_describe_from_screenshot(None)
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
            if isinstance(focus, (wx.CheckBox, wx.Choice, wx.ComboBox, wx.RadioButton)):
                event.Skip()
                return
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
            if not self.btn_search.IsEnabled():
                self.on_cancel_search(None)
                return
            if load_escape_closes_preference():
                self._stop_search = True
                self.Destroy()
                return
            rtad_speak(
                "Esc non chiude l'applicazione. Usa Alt+F4, Ctrl+Q oppure Chiudi. "
                "Opzione in Strumenti se preferisci Esc per uscire.",
                force=True,
            )
            return
        elif alt and key == wx.WXK_F4:
            self._stop_search = True
            self.Close()
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
            rtad_speak(f"Percorso impostato: {selected_path}.")
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
            rtad_speak("Screenshot salvato con successo in Catture di schermata.")
        except Exception:
            rtad_speak("Impossibile salvare lo screenshot.")

    def on_export_results(self, event):
        if not self.current_matches:
            rtad_speak("Nessun risultato da esportare.")
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
                
                rtad_speak("Risultati esportati con successo nel formato scelto.")
            except Exception:
                rtad_speak("Errore durante l'esportazione dei risultati.")
        dlg.Destroy()

    def on_print_results(self, event):
        total_matches = len(self.current_matches)
        if total_matches == 0:
            rtad_speak("Nessun risultato da stampare.")
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
                    rtad_speak("Inviati tutti i risultati alla stampante predefinita.")
                else:
                    rtad_speak(f"Inviati i primi {limit} risultati alla stampante predefinita.")
            except Exception:
                rtad_speak("Impossibile stampare. Assicurati di avere una stampante configurata.")
        else:
            dlg.Destroy()
            rtad_speak("Stampa annullata.")


    def speak_selected_preview(self):
        sel = self.lst_results.GetSelection()
        if sel != wx.NOT_FOUND and sel in self.file_map:
            item = self.file_map[sel]
            snippet = item.get("snippet", "")
            loc = item.get("location_info", "")
            if snippet:
                rtad_speak(f"{loc}: {snippet}")
            else:
                rtad_speak(f"{item['file_name']} - Nessuna anteprima di testo disponibile.")

    def start_search_thread(self):
        query = self.txt_query.GetValue().strip()
        target_input = self.txt_path.GetValue().strip()
        filter_mode = self.combo_filter.GetSelection()
        custom_ext = self.txt_custom_ext.GetValue().strip().lower()
        if not custom_ext.startswith(".") and custom_ext:
            custom_ext = "." + custom_ext
        include_feed_raw = bool(self.chk_feed_raw.GetValue())
        include_ocr = bool(self.chk_ocr.GetValue())
        try:
            save_include_ocr_preference(include_ocr)
        except Exception:
            pass
        include_visual = bool(
            getattr(self, "chk_visual", None) and self.chk_visual.GetValue()
        )
        try:
            save_include_visual_preference(include_visual)
        except Exception:
            pass
        include_zip = bool(self.chk_zip.GetValue())
        try:
            save_include_zip_preference(include_zip)
        except Exception:
            pass
        try:
            eng = ocr_engine_from_choice_index(self.choice_ocr_engine.GetSelection())
            if eng == "google" or include_visual:
                save_google_vision_api_key(load_google_vision_api_key())
            save_ocr_engine_preference(eng)
        except Exception:
            pass

        if not query:
            if include_ocr and filter_mode in (0, 1):
                rtad_speak(
                    "Nessun testo di ricerca: OCR completo sulle immagini del percorso. "
                    "Poi puoi usare Copia Testo o Salva Immagine sul risultato."
                )
            elif filter_mode in (1, 2, 3, 4):
                tipo = FILTER_MODE_LABELS[filter_mode] if filter_mode < len(FILTER_MODE_LABELS) else "tipo scelto"
                rtad_speak(
                    f"Nessun testo di ricerca: elenco dei file ({tipo}) "
                    f"nella cartella indicata. Poi puoi aprirli o analizzarli dal menu."
                )
            else:
                rtad_speak(
                    "Inserire un testo da cercare, oppure scegli un tipo di file "
                    "(documenti, immagini…) per elencarli, oppure attiva OCR "
                    "per leggere tutte le immagini senza parola chiave."
                )
                return

        self._stop_search = False
        if query:
            self.current_query = query
        elif include_ocr and filter_mode in (0, 1):
            self.current_query = "(OCR completo)"
        else:
            self.current_query = "(Elenco per tipo)"
        self.current_percent = 0
        self.scanned_count = 0
        self.live_matches_count = 0
        self.last_feed_raw_occurrences = 0
        save_last_path(target_input)
        if query:
            add_query_to_history(query)
        add_path_to_history(target_input)
        self.update_history_menu()

        try:
            # ChangeValue non genera EVT_TEXT (evita lista vuota → «sconosciuto»)
            self.txt_filter.ChangeValue("")
        except Exception:
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
        if include_ocr and not query and filter_mode in (0, 1):
            self.txt_status_progress.SetValue("OCR completo sulle immagini: 0%...")
        elif not query and filter_mode in (1, 2, 3, 4):
            self.txt_status_progress.SetValue("Elenco file per tipo: 0%...")
        elif include_ocr or include_visual:
            bits = []
            if include_ocr:
                bits.append("OCR")
            if include_visual:
                bits.append("visivo")
            self.txt_status_progress.SetValue(
                f"Ricerca in corso ({'+'.join(bits)}): 0%..."
            )
        else:
            self.txt_status_progress.SetValue("Ricerca in corso: 0%...")
        
        self.btn_search.Disable()
        self.btn_cancel.Enable()

        if include_ocr and not query and filter_mode in (0, 1):
            rtad_speak("OCR completo avviato sulle immagini.")
        elif not query and filter_mode in (1, 2, 3, 4):
            rtad_speak("Elenco file per tipo avviato.")
        elif include_ocr or include_visual:
            extras = []
            if include_ocr:
                extras.append("OCR")
            if include_visual:
                extras.append("contenuto visivo")
            rtad_speak(
                f"Ricerca avviata per '{query}', con {' e '.join(extras)}."
            )
        else:
            rtad_speak(f"Ricerca avviata per '{query}'.")
        
        # --- INIZIO EARCONS NVDA (Avvio) ---
        if tones:
            try:
                wx.CallLater(100, lambda: tones.beep(800, 150))
            except Exception:
                pass
        # --- FINE EARCONS ---

        targets = normalize_search_targets(target_input)
        threading.Thread(
            target=self.run_search,
            args=(
                query, targets, filter_mode, custom_ext,
                include_feed_raw, include_ocr, include_zip, include_visual,
            ),
            daemon=True,
        ).start()

    def run_search(
        self,
        query,
        targets,
        filter_mode,
        custom_ext,
        include_feed_raw=False,
        include_ocr=False,
        include_zip=False,
        include_visual=False,
    ):
        raw_matches = []
        ignored = [
            "$recycle.bin",
            "system volume information",
            "appdata\\local\\temp",
            "appdata\\roaming\\rtad_standalone",
            "appdata\\roaming\\cursor",
            "appdata\\roaming\\code",
            "rtad_data",
            "\\windows\\winsxs",
            "\\windows\\installer",
            "\\windows\\servicing",
            "\\windows\\logs",
            "\\windows\\panther",
        ]

        norm_query = normalize_search_text(query) if query else ""
        terms = norm_query.split() if norm_query else []
        ocr_dump_all = bool(include_ocr and not terms and filter_mode in (0, 1))
        list_files_only = bool(
            not terms and not ocr_dump_all and filter_mode in (1, 2, 3, 4)
        )
        img_exts = list(IMG_EXTS)
        media_exts = list(MEDIA_EXTS)
        doc_exts = list(DOC_EXTS)
        feed_file_exts = {".rss", ".xml", ".atom"}
        # Estensione personalizzata .pdf: scansiona anche allegati nelle caselle posta
        mail_pdf_only = filter_mode == 4 and custom_ext == ".pdf"

        file_list = []
        rss_sources = []
        opml_files = []
        walked_dirs = 0

        wx.CallAfter(
            self.txt_status_progress.SetValue,
            "Indicizzazione cartelle in corso… (Alt+P per lo stato)",
        )

        missing_targets = []
        for folder in targets:
            if self._stop_search:
                break
            if folder.startswith("http://") or folder.startswith("https://"):
                rss_sources.append(folder)
                continue

            if not os.path.exists(folder):
                missing_targets.append(folder)
                continue

            if os.path.isfile(folder):
                ext = os.path.splitext(folder)[1].lower()
                if is_rtad_noise_file(folder):
                    continue
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
                dirs[:] = [
                    d for d in dirs
                    if not any(ign in os.path.join(root, d).lower() for ign in ignored)
                ]
                root_lower = root.lower()
                if any(ign in root_lower for ign in ignored):
                    continue
                walked_dirs += 1
                if walked_dirs == 1 or walked_dirs % 25 == 0:
                    wx.CallAfter(
                        self.txt_status_progress.SetValue,
                        f"Indicizzazione… {walked_dirs} cartelle, {len(file_list)} file in coda",
                    )

                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    full = os.path.normpath(os.path.join(root, file))
                    if is_thunderbird_junk_file(full):
                        continue
                    if is_rtad_noise_file(full):
                        continue
                    is_tb = is_thunderbird_mail_container(full)
                    # Filtro .pdf: le caselle posta/.eml/.mbox non hanno estensione .pdf,
                    # ma contengono allegati PDF — includile comunque.
                    mail_for_pdf = (
                        custom_ext == ".pdf"
                        and (is_tb or ext in (".eml", ".mbox", ".mbx"))
                    )

                    if filter_mode == 1 and ext not in img_exts:
                        continue
                    elif filter_mode == 2 and ext not in media_exts:
                        continue
                    elif filter_mode == 3 and ext not in doc_exts and not is_tb:
                        if not (include_zip and ext == ".zip"):
                            continue
                    elif filter_mode == 4 and ext != custom_ext and not mail_for_pdf:
                        continue
                    elif ocr_dump_all and filter_mode == 0 and ext not in img_exts:
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

        wx.CallAfter(
            self.txt_status_progress.SetValue,
            f"Scansione contenuti: {len(file_list)} file…",
        )
        work_units = len(file_list) + len(rss_sources)
        if work_units <= 0:
            work_units = 1
        units_done = 0
        last_spoken_percent = -1
        feed_raw_total = 0
        skipped_large_files = 0
        mail_messages_scanned = 0
        pdf_attachment_hits = 0
        pdf_attachment_empty = 0
        pdf_attachment_seen = 0
        if rtad_ocr is not None:
            try:
                rtad_ocr.reset_stats()
            except Exception:
                pass
        ocr_unavailable_announced = False

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
                        rtad_speak,
                        "Modulo feedparser non installato: ricerca RSS non disponibile.",
                    )
                bump_progress()
                continue
            try:
                raw_matches.extend(search_online_or_local_feed(source, terms))
            except Exception:
                pass
            bump_progress()

        # === Scansione file locali (+ arrivi dell'ultimo minuto a fine coda) ===
        file_queue = list(file_list)
        seen_local_files = set(file_queue)
        queue_i = 0
        late_pass_done = False
        late_arrivals_count = 0

        while not self._stop_search:
            if queue_i >= len(file_queue):
                if late_pass_done:
                    break
                late_pass_done = True
                late_new = []
                for folder in targets:
                    if self._stop_search:
                        break
                    if folder.startswith("http://") or folder.startswith("https://"):
                        continue
                    if not os.path.exists(folder):
                        continue
                    if os.path.isfile(folder):
                        full = os.path.normpath(folder)
                        if full in seen_local_files or is_rtad_noise_file(full):
                            continue
                        ext = os.path.splitext(full)[1].lower()
                        is_tb = is_thunderbird_mail_container(full)
                        mail_for_pdf = (
                            custom_ext == ".pdf"
                            and (is_tb or ext in (".eml", ".mbox", ".mbx"))
                        )
                        if filter_mode == 1 and ext not in img_exts:
                            continue
                        elif filter_mode == 2 and ext not in media_exts:
                            continue
                        elif filter_mode == 3 and ext not in doc_exts and not is_tb:
                            if not (include_zip and ext == ".zip"):
                                continue
                        elif filter_mode == 4 and ext != custom_ext and not mail_for_pdf:
                            continue
                        elif ocr_dump_all and filter_mode == 0 and ext not in img_exts:
                            continue
                        if ext == ".opml" or (ext in feed_file_exts and not is_thunderbird_feeds_path(full)):
                            continue
                        late_new.append(full)
                        continue
                    for root, dirs, files in os.walk(folder):
                        if self._stop_search:
                            break
                        dirs[:] = [
                            d for d in dirs
                            if not any(ign in os.path.join(root, d).lower() for ign in ignored)
                        ]
                        if any(ign in root.lower() for ign in ignored):
                            continue
                        for file in files:
                            ext = os.path.splitext(file)[1].lower()
                            full = os.path.normpath(os.path.join(root, file))
                            if full in seen_local_files:
                                continue
                            if is_thunderbird_junk_file(full) or is_rtad_noise_file(full):
                                continue
                            is_tb = is_thunderbird_mail_container(full)
                            mail_for_pdf = (
                                custom_ext == ".pdf"
                                and (is_tb or ext in (".eml", ".mbox", ".mbx"))
                            )
                            if filter_mode == 1 and ext not in img_exts:
                                continue
                            elif filter_mode == 2 and ext not in media_exts:
                                continue
                            elif filter_mode == 3 and ext not in doc_exts and not is_tb:
                                if not (include_zip and ext == ".zip"):
                                    continue
                            elif filter_mode == 4 and ext != custom_ext and not mail_for_pdf:
                                continue
                            elif ocr_dump_all and filter_mode == 0 and ext not in img_exts:
                                continue
                            if ext == ".opml":
                                continue
                            if ext in feed_file_exts and not is_thunderbird_feeds_path(full):
                                continue
                            late_new.append(full)
                if late_new:
                    late_arrivals_count = len(late_new)
                    work_units += late_arrivals_count
                    file_queue.extend(late_new)
                    seen_local_files.update(late_new)
                    logging.info(
                        f"Arrivi dell'ultimo minuto: {late_arrivals_count} file aggiunti in coda"
                    )
                    wx.CallAfter(
                        self.txt_status_progress.SetValue,
                        f"Arrivi dell'ultimo minuto: {late_arrivals_count} file nuovi…",
                    )
                    wx.CallAfter(
                        rtad_speak,
                        f"Trovati {late_arrivals_count} file aggiunti durante la ricerca. Li esamino.",
                    )
                continue

            file_path = file_queue[queue_i]
            queue_i += 1
            file_name = os.path.basename(file_path)
            ext = os.path.splitext(file_name)[1].lower()
            is_feed = is_thunderbird_feeds_path(file_path)
            prefix = f"[{ext.replace('.', '').upper()}]" if ext else "[FILE]"

            try:
                mtime = os.path.getmtime(file_path)
            except Exception:
                mtime = 0
            file_date_label = format_file_date_label(mtime)
            file_date_suffix = f" {file_date_label}" if file_date_label else ""

            if list_files_only:
                try:
                    sz = os.path.getsize(file_path)
                except Exception:
                    sz = 0
                if sz >= 1024 * 1024:
                    size_s = f"{sz / (1024 * 1024):.1f} MB"
                elif sz >= 1024:
                    size_s = f"{sz / 1024:.0f} KB"
                else:
                    size_s = f"{sz} byte"
                raw_matches.append({
                    "file_path": file_path,
                    "file_name": file_name,
                    "prefix": "[ELENCO]",
                    "mtime": mtime,
                    "line_number": None,
                    "paragraph_index": None,
                    "location_info": f"Elenco per tipo{file_date_suffix}",
                    "snippet": f"{(ext or 'file').lstrip('.').upper() or 'FILE'} · {size_s}",
                })
                bump_progress()
                continue

            try:
                name_matched = text_matches_terms(file_name, terms)
                found_in_content = False
                img_ocr_text = ""
                allow_content = content_scan_allowed(file_path)
                if not allow_content and not name_matched:
                    # Le caselle di posta non arrivano qui (content_scan_allowed=True)
                    skipped_large_files += 1
                    logging.info(
                        f"File troppo grande per scansione contenuto "
                        f"({safe_file_size(file_path)} byte): {file_path}"
                    )
                    bump_progress()
                    continue
                if not allow_content:
                    skipped_large_files += 1
                    logging.info(
                        f"File troppo grande per scansione contenuto "
                        f"({safe_file_size(file_path)} byte): {file_path}"
                    )

                if ext in img_exts and allow_content:
                    ocr_match = False
                    visual_match = False
                    img_text = ""
                    vis_labels = []
                    if include_ocr and rtad_ocr is not None:
                        if not rtad_ocr.engine_available():
                            if not ocr_unavailable_announced:
                                ocr_unavailable_announced = True
                                wx.CallAfter(
                                    rtad_speak,
                                    rtad_ocr.engine_status_message(),
                                )
                        else:
                            img_text = rtad_ocr.ocr_image_file(
                                file_path,
                                should_abort=lambda: self._stop_search,
                                hint_terms=terms or None,
                            )
                            img_ocr_text = img_text or ""
                            if ocr_dump_all:
                                ocr_match = bool((img_text or "").strip())
                            else:
                                try:
                                    ocr_match = rtad_ocr.ocr_text_matches_terms(img_text, terms)
                                except Exception:
                                    ocr_match = text_matches_terms(img_text, terms)
                    if (
                        include_visual
                        and terms
                        and not ocr_dump_all
                        and rtad_ocr is not None
                        and hasattr(rtad_ocr, "get_image_label_strings")
                        and not self._stop_search
                    ):
                        try:
                            if not rtad_ocr.has_google_api_key():
                                gkey = load_google_vision_api_key()
                                if gkey:
                                    rtad_ocr.set_google_api_key(gkey)
                            vis_labels = rtad_ocr.get_image_label_strings(
                                file_path,
                                should_abort=lambda: self._stop_search,
                            ) or []
                            visual_match = rtad_ocr.visual_labels_match_terms(
                                vis_labels, terms
                            )
                        except Exception as e:
                            logging.debug(f"Analisi visiva fallita su {file_path}: {e}")
                            visual_match = False
                    if ocr_match or visual_match:
                        if ocr_match:
                            if ocr_dump_all:
                                try:
                                    snip = rtad_ocr.ocr_text_for_clipboard(img_text) or img_text
                                except Exception:
                                    snip = img_text
                                snip = " ".join((snip or "").split())[:200] or file_name
                            else:
                                snip = (
                                    rtad_ocr.snippet_from_ocr_text(img_text, terms)
                                    if img_text and rtad_ocr is not None
                                    else ""
                                ) or query
                            loc = (
                                f"OCR completo{file_date_suffix}"
                                if ocr_dump_all
                                else (
                                    f"Testo OCR + contenuto visivo{file_date_suffix}"
                                    if visual_match
                                    else f"Testo OCR{file_date_suffix}"
                                )
                            )
                            prefix_img = "[IMG-OCR]"
                        else:
                            shown = []
                            for L in vis_labels:
                                if L and L not in shown:
                                    shown.append(L)
                                if len(shown) >= 6:
                                    break
                            snip = ", ".join(shown) if shown else query
                            loc = f"Contenuto visivo{file_date_suffix}"
                            prefix_img = "[IMG-VIS]"
                        raw_matches.append({
                            "file_path": file_path,
                            "file_name": file_name,
                            "prefix": prefix_img,
                            "mtime": mtime,
                            "line_number": None,
                            "location_info": loc,
                            "snippet": snip,
                            "ocr_text": img_text or "",
                            "visual_labels": vis_labels,
                        })
                        found_in_content = True

                elif is_feed and allow_content:
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

                elif allow_content and (ext in [".mbox", ".mbx"] or (is_thunderbird_mail_container(file_path) and not is_feed)):
                    # Come Standalone: un risultato per messaggio (prima riga body o intestazione)
                    try:
                        for msg_idx, msg in iter_mbox_like_messages(
                            file_path,
                            prefer_from_split=True,
                            should_abort=lambda: self._stop_search,
                        ):
                            if self._stop_search:
                                break
                            mail_messages_scanned += 1
                            subject = decode_email_header(str(msg.get("subject", "")))
                            sender = decode_email_header(str(msg.get("from", "")))
                            msg_ts = message_date_timestamp(msg, fallback=mtime)
                            date_label = format_email_date_label(msg, fallback_ts=msg_ts)
                            date_suffix = f" {date_label}" if date_label else ""
                            msg_found = False
                            # Con filtro solo .pdf: non cercare in corpo/oggetto, solo allegati PDF
                            if not mail_pdf_only:
                                body = get_clean_email_text(msg)
                                if body:
                                    lines = body.split("\n")
                                    for line_idx, line in enumerate(lines):
                                        if text_matches_terms(line, terms):
                                            start_i = max(0, line_idx - 1)
                                            end_i = min(len(lines), line_idx + 2)
                                            snip = " ".join(
                                                [l.strip() for l in lines[start_i:end_i]]
                                            ).strip()
                                            raw_matches.append({
                                                "file_path": file_path,
                                                "file_name": file_name,
                                                "prefix": "[MBOX]",
                                                "mtime": msg_ts,
                                                "line_number": msg_idx,
                                                "location_info": f"Testo Msg {msg_idx + 1}{date_suffix}",
                                                "snippet": snip[:200],
                                                "viewer_text": _format_email_viewer_text(msg),
                                            })
                                            found_in_content = True
                                            msg_found = True
                                            break
                                if not msg_found and (
                                    text_matches_terms(subject, terms)
                                    or text_matches_terms(sender, terms)
                                ):
                                    raw_matches.append({
                                        "file_path": file_path,
                                        "file_name": file_name,
                                        "prefix": "[MBOX]",
                                        "mtime": msg_ts,
                                        "line_number": msg_idx,
                                        "location_info": f"Oggetto Msg {msg_idx + 1}{date_suffix}",
                                        "snippet": f"Trovato nell'intestazione: {subject} da {sender}",
                                        "viewer_text": _format_email_viewer_text(msg),
                                    })
                                    found_in_content = True
                                    msg_found = True
                            if not msg_found:
                                for att_name, pdf_raw, att_meta in iter_pdf_attachments(msg):
                                    if self._stop_search:
                                        break
                                    pdf_attachment_seen += 1
                                    if att_meta.get("empty"):
                                        pdf_attachment_empty += 1
                                        if text_matches_terms(att_name, terms):
                                            raw_matches.append({
                                                "file_path": file_path,
                                                "file_name": file_name,
                                                "prefix": "[MBOX]",
                                                "mtime": msg_ts,
                                                "line_number": msg_idx,
                                                "location_info": f"Allegato PDF (non scaricato) Msg {msg_idx + 1}{date_suffix}",
                                                "snippet": f"nome allegato (corpo assente in locale): {att_name}",
                                                "viewer_text": _format_email_viewer_text(msg),
                                            })
                                            found_in_content = True
                                            msg_found = True
                                            pdf_attachment_hits += 1
                                            break
                                        continue
                                    hit = match_pdf_attachment_hit(
                                        terms,
                                        att_name,
                                        pdf_raw,
                                        deadline=time.monotonic() + FILE_CONTENT_SOFT_TIMEOUT_PDF_SEC,
                                    )
                                    if not hit:
                                        continue
                                    snip, via = hit
                                    cached_pdf = cache_extracted_pdf_attachment(
                                        pdf_raw, att_name, f"{file_name}-{msg_idx}"
                                    )
                                    raw_matches.append({
                                        "file_path": file_path,
                                        "file_name": file_name,
                                        "prefix": "[MBOX]",
                                        "mtime": msg_ts,
                                        "line_number": msg_idx,
                                        "location_info": f"Allegato PDF Msg {msg_idx + 1}{date_suffix}",
                                        "snippet": f"{via}: {snip}",
                                        "viewer_text": _format_email_viewer_text(msg),
                                        "attachment_name": att_name or "allegato.pdf",
                                        "attachment_export_path": cached_pdf,
                                    })
                                    found_in_content = True
                                    msg_found = True
                                    pdf_attachment_hits += 1
                                    break
                    except Exception:
                        pass

                elif ext == ".eml" and allow_content:
                    # Come Standalone: parse email, un risultato per file (non ogni riga grezza)
                    try:
                        try:
                            with open(file_path, "rb") as f:
                                raw_eml = f.read(MAX_EML_READ_BYTES)
                            try:
                                msg = email.message_from_bytes(raw_eml, policy=policy.default)
                            except Exception:
                                msg = email.message_from_string(
                                    raw_eml.decode("utf-8", errors="ignore"),
                                    policy=policy.default,
                                )
                        except Exception:
                            with open(file_path, "r", encoding="latin1", errors="ignore") as f:
                                msg = email.message_from_file(f, policy=policy.default)

                        subject = decode_email_header(str(msg.get("subject", "")))
                        sender = decode_email_header(str(msg.get("from", "")))
                        msg_ts = message_date_timestamp(msg, fallback=mtime)
                        date_label = format_email_date_label(msg, fallback_ts=msg_ts)
                        date_suffix = f" {date_label}" if date_label else ""

                        if not mail_pdf_only:
                            body = get_clean_email_text(msg)
                            if body:
                                lines = body.split("\n")
                                for line_idx, line in enumerate(lines):
                                    if text_matches_terms(line, terms):
                                        start_i = max(0, line_idx - 1)
                                        end_i = min(len(lines), line_idx + 2)
                                        snippet = " ".join(
                                            [l.strip() for l in lines[start_i:end_i]]
                                        ).strip()
                                        raw_matches.append({
                                            "file_path": file_path,
                                            "file_name": file_name,
                                            "prefix": prefix,
                                            "mtime": msg_ts,
                                            "line_number": line_idx + 1,
                                            "location_info": f"Testo Email{date_suffix}",
                                            "snippet": snippet,
                                            "viewer_text": _format_email_viewer_text(msg),
                                        })
                                        found_in_content = True
                                        break

                            if not found_in_content and (
                                text_matches_terms(subject, terms)
                                or text_matches_terms(sender, terms)
                            ):
                                raw_matches.append({
                                    "file_path": file_path,
                                    "file_name": file_name,
                                    "prefix": prefix,
                                    "mtime": msg_ts,
                                    "line_number": 1,
                                    "location_info": f"Intestazione Email{date_suffix}",
                                    "snippet": f"Trovato nell'intestazione: {subject} da {sender}",
                                    "viewer_text": _format_email_viewer_text(msg),
                                })
                                found_in_content = True

                        if not found_in_content:
                            for att_name, pdf_raw, att_meta in iter_pdf_attachments(msg):
                                pdf_attachment_seen += 1
                                if att_meta.get("empty"):
                                    pdf_attachment_empty += 1
                                    if text_matches_terms(att_name, terms):
                                        raw_matches.append({
                                            "file_path": file_path,
                                            "file_name": file_name,
                                            "prefix": prefix,
                                            "mtime": msg_ts,
                                            "line_number": 1,
                                            "location_info": f"Allegato PDF (non scaricato) Email{date_suffix}",
                                            "snippet": f"nome allegato (corpo assente in locale): {att_name}",
                                            "viewer_text": _format_email_viewer_text(msg),
                                        })
                                        found_in_content = True
                                        pdf_attachment_hits += 1
                                        break
                                    continue
                                hit = match_pdf_attachment_hit(
                                    terms,
                                    att_name,
                                    pdf_raw,
                                    deadline=time.monotonic() + FILE_CONTENT_SOFT_TIMEOUT_PDF_SEC,
                                )
                                if not hit:
                                    continue
                                snip, via = hit
                                cached_pdf = cache_extracted_pdf_attachment(
                                    pdf_raw, att_name, f"{file_name}-eml"
                                )
                                raw_matches.append({
                                    "file_path": file_path,
                                    "file_name": file_name,
                                    "prefix": prefix,
                                    "mtime": msg_ts,
                                    "line_number": 1,
                                    "location_info": f"Allegato PDF Email{date_suffix}",
                                    "snippet": f"{via}: {snip}",
                                    "viewer_text": _format_email_viewer_text(msg),
                                    "attachment_name": att_name or "allegato.pdf",
                                    "attachment_export_path": cached_pdf,
                                })
                                found_in_content = True
                                pdf_attachment_hits += 1
                                break
                    except Exception:
                        pass

                elif (ext in TEXT_LIKE_EXTS or ext == custom_ext) and allow_content:
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
                            if text_matches_terms(line, terms):
                                start_i = max(0, idx - 2)
                                end_i = min(len(lines), idx + 3)
                                snippet = "".join(lines[start_i:end_i]).strip()
                                raw_matches.append({
                                    "file_path": file_path,
                                    "file_name": file_name,
                                    "prefix": prefix,
                                    "mtime": mtime,
                                    "line_number": idx + 1,
                                    "location_info": f"Riga {idx + 1}{file_date_suffix}",
                                    "snippet": snippet,
                                })
                                found_in_content = True
                    except Exception:
                        pass
                elif ext in [".docx", ".doc"] and allow_content:
                    magic = _read_file_magic(file_path, 4)
                    paragraphs = []
                    if ext == ".docx" or _is_ooxml_zip_magic(magic):
                        paragraphs, timed_out = run_with_timeout(
                            lambda: extract_paragraphs_from_docx(file_path),
                            FILE_CONTENT_SOFT_TIMEOUT_SEC,
                            default=[],
                        )
                        if timed_out:
                            paragraphs = []
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
                                "location_info": f"Paragrafo {idx + 1}{file_date_suffix}",
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
                                        "location_info": f"Documento Word{file_date_suffix}",
                                        "snippet": f"Trovato testo nel file Word: '{query}'.",
                                    })
                                    found_in_content = True
                        except Exception:
                            pass
                elif ext == ".epub" and allow_content and rtad_epub is not None:
                    paragraphs, timed_out = run_with_timeout(
                        lambda: rtad_epub.extract_paragraphs_from_epub(file_path),
                        FILE_CONTENT_SOFT_TIMEOUT_SEC,
                        default=[],
                    )
                    if timed_out:
                        paragraphs = []
                    for idx, p_text in enumerate(paragraphs):
                        if text_matches_terms(p_text, terms):
                            start_i = max(0, idx - 1)
                            end_i = min(len(paragraphs), idx + 2)
                            snippet = " \n".join(paragraphs[start_i:end_i])
                            raw_matches.append({
                                "file_path": file_path,
                                "file_name": file_name,
                                "prefix": "[EPUB]",
                                "mtime": mtime,
                                "line_number": None,
                                "paragraph_index": idx + 1,
                                "location_info": f"Testo EPUB{file_date_suffix}",
                                "snippet": snippet,
                            })
                            found_in_content = True
                            break
                elif ext == ".zip" and include_zip and allow_content and rtad_zip is not None:
                    zip_hits, timed_out = run_with_timeout(
                        lambda: rtad_zip.search_zip_text_members(
                            file_path,
                            terms,
                            text_matches_terms=text_matches_terms,
                            should_abort=lambda: self._stop_search,
                        ),
                        FILE_CONTENT_SOFT_TIMEOUT_SEC,
                        default=[],
                    )
                    if timed_out:
                        zip_hits = []
                    for zh in zip_hits or []:
                        member = zh.get("member") or "?"
                        line_no = zh.get("line_number")
                        snip = zh.get("snippet") or member
                        loc = f"ZIP {member}"
                        if line_no:
                            loc = f"ZIP {member} riga {line_no}"
                        raw_matches.append({
                            "file_path": file_path,
                            "file_name": file_name,
                            "prefix": "[ZIP]",
                            "mtime": mtime,
                            "line_number": line_no,
                            "location_info": f"{loc}{file_date_suffix}",
                            "snippet": snip,
                            "zip_member": member,
                        })
                        found_in_content = True

                elif ext == ".pdf" and allow_content:
                    def _pdf_job():
                        ts = pdf_info_date_timestamp(file_path, fallback=0)
                        lines = extract_lines_from_pdf(file_path)
                        return ts, lines

                    pdf_result, timed_out = run_with_timeout(
                        _pdf_job,
                        FILE_CONTENT_SOFT_TIMEOUT_PDF_SEC,
                        default=(0, []),
                    )
                    if timed_out:
                        pdf_doc_ts, pdf_lines = 0, []
                    else:
                        pdf_doc_ts, pdf_lines = pdf_result
                    sort_ts = mtime or pdf_doc_ts or 0
                    doc_label = format_file_date_label(pdf_doc_ts) if pdf_doc_ts else ""
                    file_label = format_file_date_label(mtime) if mtime else ""
                    if file_label and doc_label and file_label != doc_label:
                        date_suffix = f" file {file_label} (doc {doc_label})"
                    elif file_label:
                        date_suffix = f" {file_label}"
                    elif doc_label:
                        date_suffix = f" {doc_label}"
                    else:
                        date_suffix = ""
                    pdf_hit = False
                    for idx, line in enumerate(pdf_lines):
                        if text_matches_terms(line, terms):
                            start_i = max(0, idx - 1)
                            end_i = min(len(pdf_lines), idx + 2)
                            snippet = " ".join(pdf_lines[start_i:end_i])
                            raw_matches.append({
                                "file_path": file_path,
                                "file_name": file_name,
                                "prefix": prefix,
                                "mtime": sort_ts,
                                "line_number": None,
                                "location_info": f"Testo PDF{date_suffix}",
                                "snippet": snippet,
                            })
                            found_in_content = True
                            pdf_hit = True
                            break
                    if not pdf_hit and pdf_lines:
                        hay = "\n".join(pdf_lines)
                        if text_matches_terms(hay, terms):
                            snippet = ""
                            for line in pdf_lines:
                                if any(t in normalize_search_text(line, False) for t in terms):
                                    snippet = line.strip()
                                    break
                            if not snippet:
                                snippet = " ".join(hay.split())[:200]
                            raw_matches.append({
                                "file_path": file_path,
                                "file_name": file_name,
                                "prefix": prefix,
                                "mtime": sort_ts,
                                "line_number": None,
                                "location_info": f"Testo PDF{date_suffix}",
                                "snippet": snippet[:200],
                            })
                            found_in_content = True
                            pdf_hit = True
                    if not pdf_hit and not pdf_lines and allow_content:
                        try:
                            with open(file_path, "rb") as f:
                                raw_pdf = f.read(PDF_READ_MAX_BYTES)
                            raw_txt = raw_pdf.decode("latin1", errors="ignore")
                            if text_matches_terms(raw_txt, terms):
                                n = normalize_search_text(raw_txt, False)
                                pos = n.find(terms[0]) if terms else -1
                                if pos >= 0:
                                    a, b = max(0, pos - 40), min(len(raw_txt), pos + 80)
                                    snip = " ".join(raw_txt[a:b].split())
                                else:
                                    snip = file_name
                                raw_matches.append({
                                    "file_path": file_path,
                                    "file_name": file_name,
                                    "prefix": prefix,
                                    "mtime": sort_ts,
                                    "line_number": None,
                                    "location_info": f"Testo PDF{date_suffix}",
                                    "snippet": snip[:200],
                                })
                                found_in_content = True
                                pdf_hit = True
                        except Exception:
                            pass
                    if (
                        include_ocr
                        and not pdf_hit
                        and allow_content
                        and rtad_ocr is not None
                        and (not pdf_lines or len("".join(pdf_lines).strip()) < 40)
                    ):
                        if rtad_ocr.engine_available():
                            ocr_txt = ocr_text_from_pdf_file(
                                file_path,
                                should_abort=lambda: self._stop_search,
                            )
                            if text_matches_terms(ocr_txt, terms) or (
                                hasattr(rtad_ocr, "ocr_text_matches_terms")
                                and rtad_ocr.ocr_text_matches_terms(ocr_txt, terms)
                            ):
                                snip = rtad_ocr.snippet_from_ocr_text(ocr_txt, terms) or query
                                raw_matches.append({
                                    "file_path": file_path,
                                    "file_name": file_name,
                                    "prefix": "[PDF-OCR]",
                                    "mtime": sort_ts,
                                    "line_number": None,
                                    "location_info": f"Testo OCR PDF{date_suffix}",
                                    "snippet": snip,
                                    "ocr_text": ocr_txt,
                                })
                                found_in_content = True
                                pdf_hit = True
                        elif not ocr_unavailable_announced:
                            ocr_unavailable_announced = True
                            wx.CallAfter(
                                rtad_speak,
                                rtad_ocr.engine_status_message(),
                            )
                    if name_matched and not found_in_content:
                        raw_matches.append({
                            "file_path": file_path,
                            "file_name": file_name,
                            "prefix": prefix,
                            "mtime": sort_ts,
                            "line_number": None,
                            "location_info": f"Nome File{date_suffix}",
                            "snippet": f"Corrispondenza nel nome: '{file_name}'",
                        })
                        found_in_content = True

                if name_matched and not found_in_content:
                    entry = {
                        "file_path": file_path,
                        "file_name": file_name,
                        "prefix": prefix,
                        "mtime": mtime,
                        "line_number": None,
                        "location_info": f"Nome File{file_date_suffix}",
                        "snippet": f"Corrispondenza nel nome: '{file_name}'",
                    }
                    if ext in img_exts and (img_ocr_text or "").strip():
                        entry["ocr_text"] = img_ocr_text
                        entry["prefix"] = "[IMG-OCR]"
                        entry["location_info"] = (
                            f"Nome File + OCR{file_date_suffix}"
                        )
                        try:
                            snip = " ".join(img_ocr_text.split())[:200]
                            if snip:
                                entry["snippet"] = (
                                    f"Nome file; anteprima OCR: {snip}"
                                )
                        except Exception:
                            pass
                    raw_matches.append(entry)

            except Exception:
                pass

            bump_progress()
            if units_done % 5 == 0:
                time.sleep(0)

        self.current_matches = raw_matches
        self.last_feed_raw_occurrences = feed_raw_total
        self.last_skipped_large_files = skipped_large_files
        self.last_mail_messages_scanned = mail_messages_scanned
        self.last_pdf_attachment_hits = pdf_attachment_hits
        self.last_pdf_attachment_empty = pdf_attachment_empty
        self.last_pdf_attachment_seen = pdf_attachment_seen
        self.last_mail_pdf_only = mail_pdf_only
        self.last_include_ocr = bool(include_ocr)
        self.last_include_visual = bool(include_visual)
        self.last_include_zip = bool(include_zip)
        self.last_late_arrivals = int(late_arrivals_count)
        self.last_missing_targets = list(missing_targets)
        try:
            self.last_ocr_stats = rtad_ocr.get_stats() if rtad_ocr is not None else {}
        except Exception:
            self.last_ocr_stats = {}
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
        searching = False
        try:
            searching = not self.btn_search.IsEnabled()
        except Exception:
            searching = False
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
        if searching and self.lst_results.GetCount() == 0:
            self.lst_results.Append("Ricerca in corso... attendere prego.")

    def update_progress(self, percent, current, total, matches, announce=False):
        self.gauge.SetValue(percent)
        text = f"Avanzamento: {percent}% ({current}/{total} file, {matches} risultati)"
        self.txt_status_progress.SetValue(text)
        if announce or percent in (25, 50, 75):
            rtad_speak(f"Ricerca al {percent} percento")

    def finish_search(self, matches):
        self.gauge.SetValue(100)
        self.current_percent = 100
        feed_raw = getattr(self, "last_feed_raw_occurrences", 0) or 0
        skipped_large = getattr(self, "last_skipped_large_files", 0) or 0
        mail_msgs = getattr(self, "last_mail_messages_scanned", 0) or 0
        pdf_att_hits = getattr(self, "last_pdf_attachment_hits", 0) or 0
        pdf_att_empty = getattr(self, "last_pdf_attachment_empty", 0) or 0
        pdf_att_seen = getattr(self, "last_pdf_attachment_seen", 0) or 0
        ocr_stats = getattr(self, "last_ocr_stats", {}) or {}
        ocr_note = ""
        if getattr(self, "last_include_ocr", False):
            ocr_note = (
                f" OCR: {ocr_stats.get('images_ocr', 0)} immagini, "
                f"{ocr_stats.get('pdf_pages_ocr', 0)} pagine PDF, "
                f"{ocr_stats.get('cache_hits', 0)} da cache."
            )
        late_n = getattr(self, "last_late_arrivals", 0) or 0
        late_note = ""
        if late_n > 0:
            late_note = f" Arrivi dell'ultimo minuto esaminati: {late_n}."
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
        large_note = ""
        if skipped_large > 0:
            large_note = (
                f" Saltati {skipped_large} file non-posta oltre ~40 MB "
                f"(ricerca solo sul nome; le caselle di posta restano complete)."
            )
        mail_note = ""
        if mail_msgs > 0:
            if getattr(self, "last_mail_pdf_only", False):
                mail_note = (
                    f" Messaggi posta esaminati: {mail_msgs} "
                    f"(filtro PDF: solo allegati PDF nelle caselle, non corpo/oggetto)."
                )
            else:
                mail_note = (
                    f" Messaggi posta esaminati: {mail_msgs} "
                    f"(un risultato per messaggio che contiene il testo, non una riga per ogni occorrenza)."
                )
            if pdf_att_seen > 0 or pdf_att_hits > 0 or pdf_att_empty > 0:
                mail_note += (
                    f" Allegati PDF visti: {pdf_att_seen}, hit: {pdf_att_hits}."
                )
            if pdf_att_empty > 0:
                mail_note += (
                    f" Dichiarati ma non scaricati in locale: {pdf_att_empty} "
                    f"(apri il messaggio in Thunderbird, poi ripeti)."
                )

        missing_targets = getattr(self, "last_missing_targets", None) or []
        if self._stop_search:
            text = (
                f"Ricerca interrotta al {self.current_percent}% ({self.scanned_count} file). "
                f"Salvati {matches} risultati.{mail_note}{feed_note}{large_note}{ocr_note}{late_note}"
            )
            rtad_speak(f"Ricerca annullata. Conservati {matches} risultati.{feed_speak}")
            if tones:
                try:
                    wx.CallLater(100, lambda: tones.beep(400, 300))
                except Exception:
                    pass
        else:
            text = (
                f"Ricerca completata: 100% ({self.scanned_count} file). "
                f"Trovati {matches} risultati.{mail_note}{feed_note}{large_note}{ocr_note}{late_note}"
            )
            if self.scanned_count == 0 and missing_targets:
                text += (
                    " Nessun percorso valido trovato: controlla che la cartella o il file "
                    "esistano (senza virgolette nel campo percorso)."
                )
            elif self.scanned_count == 0 and matches == 0:
                text += (
                    " Nessun file in coda con questi filtri: verifica testo da cercare, "
                    "tipo di file e percorso."
                )
            rtad_speak(f"Ricerca completata. Trovati {matches} risultati ordinati dal più recente.{feed_speak}")
            if tones:
                try:
                    if matches > 0:
                        wx.CallLater(100, lambda: tones.beep(1000, 150))
                        wx.CallLater(300, lambda: tones.beep(1500, 200))
                    else:
                        wx.CallLater(100, lambda: tones.beep(600, 300))
                except Exception:
                    pass

        try:
            self._notify_search_end(matches, stopped=bool(self._stop_search))
        except Exception:
            pass
            
        self.txt_status_progress.SetValue(text)
        self.btn_search.Enable()
        self.btn_cancel.Disable()

        self.sort_and_display_matches(sort_type=self.current_sort)

        # Se non ci sono match, lascia un messaggio leggibile (non «Ricerca in corso…»)
        if self.lst_results.GetCount() == 0:
            empty_msg = (
                "Ricerca interrotta: nessun risultato conservato."
                if self._stop_search
                else "Nessun risultato trovato."
            )
            self.lst_results.Append(empty_msg)

        if self.lst_results.GetCount() > 0:
            self.lst_results.SetSelection(0)
            self.lst_results.SetFocus()

    def on_list_char_hook(self, event):
        key = event.GetKeyCode()
        if event.AltDown() and key == wx.WXK_F4:
            self._stop_search = True
            self.Close()
            return
        if key == wx.WXK_RETURN:
            self.open_selected_file()
        elif key in [wx.WXK_SPACE, wx.WXK_F4]:
            self.speak_selected_preview()
        elif key == wx.WXK_WINDOWS_MENU:
            self.on_context_menu(None)
        elif key == wx.WXK_ESCAPE:
            if not self.btn_search.IsEnabled():
                self.on_cancel_search(None)
            elif load_escape_closes_preference():
                self._stop_search = True
                self.Destroy()
            else:
                rtad_speak(
                    "Esc non chiude l'applicazione. Usa Alt+F4, Ctrl+Q oppure Chiudi.",
                    force=True,
                )
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
                    rtad_speak(f"Apertura alla riga {line_num} nel file feed")
                    jump_to_line_in_editor(file_to_open, line_num)
                else:
                    rtad_speak("Riga non disponibile.")
                return

            if prefix in ("[RSS]", "[FEED]"):
                url = item.get("article_url") or file_to_open
                if url and (str(url).startswith("http://") or str(url).startswith("https://")):
                    rtad_speak(
                        "Apertura articolo nel browser. "
                        "Se compare un banner sui cookie, accettarlo per leggere la notizia."
                    )
                    webbrowser.open(url)
                    return
                if prefix == "[FEED]" and line_num:
                    rtad_speak(f"Apertura alla riga {line_num}: {os.path.basename(file_to_open)}")
                    jump_to_line_in_editor(file_to_open, line_num)
                    return
                rtad_speak("Collegamento articolo non disponibile.")
                return

            if prefix == "[MBOX]":
                att_path = item.get("attachment_export_path") or ""
                if att_path and os.path.isfile(att_path):
                    att_label = item.get("attachment_name") or os.path.basename(att_path)
                    try:
                        ctypes.windll.shell32.ShellExecuteW(None, "open", att_path, None, None, 1)
                        rtad_speak(f"Apertura allegato PDF: {att_label}")
                    except Exception:
                        rtad_speak("Errore apertura allegato PDF.")
                    return
                rtad_speak(f"Apertura messaggio {line_num + 1} dall'archivio MBOX")
                viewer = MboxViewerFrame(
                    self,
                    file_to_open,
                    line_num,
                    self.current_query,
                    cached_text=item.get("viewer_text"),
                )
                viewer.Show()
                return

            if ext == ".eml" and item.get("attachment_export_path"):
                att_path = item.get("attachment_export_path") or ""
                if att_path and os.path.isfile(att_path):
                    att_label = item.get("attachment_name") or os.path.basename(att_path)
                    try:
                        ctypes.windll.shell32.ShellExecuteW(None, "open", att_path, None, None, 1)
                        rtad_speak(f"Apertura allegato PDF: {att_label}")
                    except Exception:
                        rtad_speak("Errore apertura allegato PDF.")
                    return

            if ext in [".docx", ".doc"]:
                rtad_speak(f"Apertura file Word: {os.path.basename(file_to_open)}")
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "open", file_to_open, None, None, 1)
                except Exception:
                    pass
                return
            
            if ext == ".eml":
                rtad_speak(f"Apertura email nel lettore interno: {os.path.basename(file_to_open)}")
                viewer = EmlViewerFrame(self, file_to_open, self.current_query)
                viewer.Show()
                return

            if line_num:
                rtad_speak(f"Apertura alla riga {line_num}: {os.path.basename(file_to_open)}")
                jump_to_line_in_editor(file_to_open, line_num)
            else:
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "open", file_to_open, None, None, 1)
                    rtad_speak(f"Apertura file: {os.path.basename(file_to_open)}")
                except Exception:
                    rtad_speak("Impossibile aprire il file selezionato.")

    def on_context_menu(self, event):
        sel = self.lst_results.GetSelection()
        if sel == wx.NOT_FOUND or sel not in self.file_map:
            return

        item_data = self.file_map[sel]
        file_path = item_data["file_path"]
        snippet = item_data["snippet"]

        menu = wx.Menu()
        item_open = menu.Append(wx.ID_ANY, "Apri File (alla riga esatta)\tINVIO")
        att_path = item_data.get("attachment_export_path") or ""
        has_att = bool(att_path and os.path.isfile(att_path))
        item_open_msg = None
        item_save_att = None
        if has_att:
            att_label = item_data.get("attachment_name") or os.path.basename(att_path)
            item_open.SetItemLabel(f"Apri allegato PDF ({att_label})")
            item_open_msg = menu.Append(wx.ID_ANY, "Apri messaggio posta (testo)")
            item_save_att = menu.Append(wx.ID_ANY, "Salva allegato PDF...")
        item_preview = menu.Append(wx.ID_ANY, "Ascolta Anteprima Vocale\tSPAZIO")
        item_copy_snippet = menu.Append(wx.ID_ANY, "Copia Blocco Notizia / Frase con parola chiave")
        item_copy_path = menu.Append(wx.ID_ANY, "Copia Percorso Completo")
        item_copy_text = menu.Append(wx.ID_ANY, "Copia Testo pulito")
        item_copy_ocr_full = menu.Append(wx.ID_ANY, "Copia OCR completo")
        item_describe = None
        item_alt = None
        item_alt_long = None
        item_labels = None
        item_tech = None
        item_pdf_describe = None
        ext_sel = os.path.splitext(file_path)[1].lower()
        is_img_result = (
            ext_sel in IMG_EXTS
            or str(item_data.get("prefix", "")).startswith("[IMG")
        )
        is_pdf_result = (
            ext_sel == ".pdf"
            or str(item_data.get("prefix", "")).startswith("[PDF")
        )
        if is_img_result:
            menu.AppendSeparator()
            item_alt = menu.Append(wx.ID_ANY, "Alt-text breve")
            item_describe = menu.Append(wx.ID_ANY, "Descrivi immagine (dettagliata)")
            item_alt_long = menu.Append(wx.ID_ANY, "Alt-text + descrizione")
            item_labels = menu.Append(wx.ID_ANY, "Etichette e oggetti")
            item_tech = menu.Append(wx.ID_ANY, "Scheda tecnica immagine")
        elif is_pdf_result:
            menu.AppendSeparator()
            item_pdf_describe = menu.Append(
                wx.ID_ANY, "Descrivi immagine da PDF"
            )
        item_copy_image = menu.Append(wx.ID_ANY, "Copia Immagine")
        item_save_image = menu.Append(wx.ID_ANY, "Salva Immagine...")
        if has_att:
            item_copy_to = menu.Append(wx.ID_ANY, "Copia allegato PDF altrove...")
        else:
            item_copy_to = menu.Append(wx.ID_ANY, "Invia / Copia File in un'altra cartella...")
        item_open_folder = menu.Append(wx.ID_ANY, "Apri Cartella Contenitore")

        menu.AppendSeparator()
        sort_submenu = wx.Menu()
        item_sort_recent = sort_submenu.Append(wx.ID_ANY, "Dal Più Recente al Meno Recente")
        item_sort_oldest = sort_submenu.Append(wx.ID_ANY, "Dal Meno Recente al Più Recente")
        item_sort_name = sort_submenu.Append(wx.ID_ANY, "Alfabeticamente per Nome (A-Z)")
        menu.AppendSubMenu(sort_submenu, "Ordinamento Risultati")

        self.Bind(wx.EVT_MENU, lambda e: self.open_selected_file(), item_open)
        if item_open_msg is not None:
            self.Bind(wx.EVT_MENU, lambda e: self.open_selected_mail_message(), item_open_msg)
        if item_save_att is not None:
            self.Bind(wx.EVT_MENU, lambda e: self.save_attachment_pdf(item_data), item_save_att)
        self.Bind(wx.EVT_MENU, lambda e: wx.CallLater(250, self.speak_selected_preview), item_preview)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_snippet_to_clipboard(snippet), item_copy_snippet)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_path_to_clipboard(file_path), item_copy_path)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_text_to_clipboard(item_data, mode="clean"), item_copy_text)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_text_to_clipboard(item_data, mode="full"), item_copy_ocr_full)
        if item_alt is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.show_image_analysis(file_path, mode="alt"),
                item_alt,
            )
        if item_describe is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.show_image_analysis(file_path, mode="describe"),
                item_describe,
            )
        if item_alt_long is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.show_image_analysis(file_path, mode="alt-long"),
                item_alt_long,
            )
        if item_labels is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.show_image_analysis(file_path, mode="labels"),
                item_labels,
            )
        if item_tech is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.show_image_analysis(file_path, mode="tech"),
                item_tech,
            )
        if item_pdf_describe is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.describe_image_from_pdf(file_path),
                item_pdf_describe,
            )
        self.Bind(wx.EVT_MENU, lambda e: self.copy_image_to_clipboard(item_data), item_copy_image)
        self.Bind(wx.EVT_MENU, lambda e: self.save_image_to_file(item_data), item_save_image)
        if has_att:
            self.Bind(wx.EVT_MENU, lambda e: self.copy_file_to_destination(att_path), item_copy_to)
        else:
            self.Bind(wx.EVT_MENU, lambda e: self.copy_file_to_destination(file_path), item_copy_to)
        self.Bind(wx.EVT_MENU, lambda e: self.open_containing_folder(file_path), item_open_folder)

        self.Bind(wx.EVT_MENU, lambda e: self.change_sort_order("recent_first"), item_sort_recent)
        self.Bind(wx.EVT_MENU, lambda e: self.change_sort_order("oldest_first"), item_sort_oldest)
        self.Bind(wx.EVT_MENU, lambda e: self.change_sort_order("name"), item_sort_name)

        self.PopupMenu(menu)
        menu.Destroy()

    def show_image_analysis(
        self, file_path, mode="describe", copy_only=False, delete_after=False
    ):
        """Descrivi / etichette / scheda tecnica su un file immagine."""
        run_image_analysis(
            self,
            file_path,
            mode=mode,
            copy_only=copy_only,
            delete_after=delete_after,
            speak=rtad_speak,
        )

    def materialize_pdf_image_temp(self, file_path):
        """Estrae la migliore immagine da un PDF su file temp. Path o ''."""
        if not file_path or not os.path.isfile(file_path):
            return ""
        record = get_best_pdf_page_image(file_path)
        if not record:
            logos = extract_images_from_pdf(file_path)
            record = logos[0] if logos else None
        if not record:
            return ""
        suffix = ".jpg" if record.get("kind") == "jpeg" else ".png"
        try:
            fd, tmp = tempfile.mkstemp(suffix=suffix, prefix="rtad_pdf_")
            os.close(fd)
        except Exception:
            return ""
        if save_pdf_image_record_to_path(record, tmp) and os.path.isfile(tmp):
            return tmp
        try:
            os.remove(tmp)
        except Exception:
            pass
        return ""

    def describe_image_from_pdf(self, file_path, mode="describe"):
        """Estrae immagine dal PDF e avvia analisi (temp + delete_after)."""
        if not file_path or not os.path.isfile(file_path):
            rtad_speak("File PDF non trovato.")
            return
        rtad_speak("Estrazione immagine dal PDF…")

        def _work():
            tmp = self.materialize_pdf_image_temp(file_path)
            if not tmp:
                wx.CallAfter(
                    rtad_speak,
                    "Nessuna immagine utilizzabile in questo PDF "
                    "(solo loghi piccoli o nessuna grafica).",
                )
                return
            wx.CallAfter(
                self.show_image_analysis,
                tmp,
                mode,
                False,
                True,
            )

        threading.Thread(target=_work, daemon=True).start()

    def on_describe_pdf_dialog(self, event=None):
        """Scegli un PDF e descrivi la sua immagine principale."""
        dlg = wx.FileDialog(
            self,
            "Scegli un PDF con immagine da descrivere",
            wildcard="PDF (*.pdf)|*.pdf",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        path = dlg.GetPath()
        dlg.Destroy()
        self.describe_image_from_pdf(path, mode="describe")

    def on_describe_from_url(self, event=None):
        describe_image_from_url_dialog(self, speak=rtad_speak)

    def on_describe_from_clipboard(self, event=None):
        describe_image_from_clipboard(self, speak=rtad_speak)

    def on_describe_from_screenshot(self, event=None):
        describe_image_from_screenshot(self, speak=rtad_speak)

    def change_sort_order(self, sort_type):
        self.sort_and_display_matches(sort_type)
        save_sort_preference(sort_type)
        if sort_type == "recent_first":
            _announce("Risultati ordinati dal più recente al meno recente.")
        elif sort_type == "oldest_first":
            _announce("Risultati ordinati dal meno recente al più recente.")
        elif sort_type == "name":
            _announce("Risultati ordinati alfabeticamente per nome.")

    def open_selected_mail_message(self):
        """Apre il testo del messaggio posta (non l'allegato PDF)."""
        sel = self.lst_results.GetSelection()
        if sel == wx.NOT_FOUND or sel not in self.file_map:
            return
        item = self.file_map[sel]
        file_to_open = item["file_path"]
        line_num = item.get("line_number")
        prefix = item.get("prefix", "")
        if prefix == "[MBOX]":
            rtad_speak(f"Apertura messaggio {line_num + 1} dall'archivio MBOX")
            viewer = MboxViewerFrame(
                self,
                file_to_open,
                line_num,
                self.current_query,
                cached_text=item.get("viewer_text"),
            )
            viewer.Show()
            return
        if os.path.splitext(file_to_open)[1].lower() == ".eml":
            rtad_speak(f"Apertura email nel lettore interno: {os.path.basename(file_to_open)}")
            viewer = EmlViewerFrame(self, file_to_open, self.current_query)
            viewer.Show()

    def save_attachment_pdf(self, item_data):
        """Salva l'allegato PDF estratto in una cartella scelta dall'utente."""
        att_path = (item_data or {}).get("attachment_export_path") or ""
        if not att_path or not os.path.isfile(att_path):
            _announce("Allegato PDF non disponibile per questo risultato.")
            return
        default_name = item_data.get("attachment_name") or os.path.basename(att_path)
        if not str(default_name).lower().endswith(".pdf"):
            default_name = f"{default_name}.pdf"
        dlg = wx.FileDialog(
            self,
            "Salva allegato PDF",
            defaultDir=os.path.expanduser("~\\Desktop"),
            defaultFile=default_name,
            wildcard="PDF (*.pdf)|*.pdf",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dlg.ShowModal() == wx.ID_OK:
            dest = dlg.GetPath()
            try:
                shutil.copy2(att_path, dest)
                _announce(f"Allegato PDF salvato: {os.path.basename(dest)}")
            except Exception as e:
                logging.error(f"Errore salvataggio allegato PDF: {e}")
                _announce("Errore nel salvataggio dell'allegato PDF.")
        dlg.Destroy()

    def copy_snippet_to_clipboard(self, snippet):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(snippet))
            wx.TheClipboard.Close()
            _announce("Blocco notizia / frase copiata negli appunti!")

    def copy_path_to_clipboard(self, file_path):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(file_path))
            wx.TheClipboard.Close()
            _announce("Percorso copiato negli appunti!")

    def copy_text_to_clipboard(self, item_data, mode="clean"):
        if isinstance(item_data, str):
            file_path = item_data
            prefix = ""
            item_data = {"file_path": file_path, "prefix": ""}
        else:
            file_path = item_data["file_path"]
            prefix = item_data.get("prefix", "")
        ext = os.path.splitext(file_path)[1].lower()
        mode = (mode or "clean").strip().lower()

        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"]:
            ocr_txt = (item_data.get("ocr_text") or "").strip()
            if ocr_txt:
                if hasattr(rtad_ocr, "ocr_text_for_clipboard"):
                    hint = None
                    try:
                        q = (getattr(self, "current_query", None) or "").strip()
                        if q and q != "(OCR completo)":
                            hint = normalize_search_text(q).split() or None
                    except Exception:
                        hint = None
                    try:
                        ocr_txt = (
                            rtad_ocr.ocr_text_for_clipboard(
                                ocr_txt, mode=mode, hint_terms=hint
                            )
                            or ocr_txt
                        )
                    except TypeError:
                        ocr_txt = rtad_ocr.ocr_text_for_clipboard(ocr_txt) or ocr_txt
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.TextDataObject(ocr_txt))
                    wx.TheClipboard.Close()
                    if mode == "full":
                        _announce("OCR completo dell'immagine copiato negli appunti!")
                    else:
                        _announce("Testo pulito dell'immagine copiato negli appunti!")
                else:
                    _announce("Impossibile copiare il testo OCR negli appunti.")
                return
            _announce(
                "Questo risultato è un’immagine: il match è sul nome file e "
                "l’OCR non ha restituito testo da copiare "
                "(grafica/loghi difficili, oppure cache vuota — prova Strumenti → Svuota cache OCR)."
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
                _announce("Testo copiato negli appunti!")
            return

        text_content = ""
        if ext in [".docx", ".doc"]:
            paragraphs = extract_paragraphs_from_docx(file_path)
            text_content = "\n".join(paragraphs)
        elif ext == ".pdf":
            ocr_txt = (item_data.get("ocr_text") or "").strip()
            lines = extract_lines_from_pdf(file_path)
            text_content = "\n".join(lines)
            if not text_content.strip() and ocr_txt:
                text_content = ocr_txt
                if hasattr(rtad_ocr, "ocr_text_for_clipboard"):
                    text_content = rtad_ocr.ocr_text_for_clipboard(text_content) or text_content
            if not text_content.strip():
                if get_best_pdf_page_image(file_path):
                    _announce(
                        "Questo PDF è una scansione: non c’è testo da copiare. "
                        "Usa Copia Immagine o Salva Immagine."
                    )
                else:
                    _announce(
                        "Nessun testo estraibile da questo PDF. "
                        "Prova Copia Immagine oppure Apri file."
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
                _announce("Testo copiato negli appunti!")
        else:
            _announce("Impossibile copiare il testo da questo formato.")

    def copy_image_to_clipboard(self, item_data):
        if isinstance(item_data, str):
            file_path = item_data
            prefix = ""
        else:
            file_path = item_data["file_path"]
            prefix = item_data.get("prefix", "")
        ext = os.path.splitext(file_path)[1].lower()

        if prefix in ("[RSS]", "[FEED]", "[MBOX]", "[FEED-RIGA]"):
            _announce("Nessuna immagine da copiare per questo risultato.")
            return

        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"]:
            try:
                img = wx.Image(file_path, wx.BITMAP_TYPE_ANY)
                if img.IsOk() and wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.BitmapDataObject(wx.Bitmap(img)))
                    wx.TheClipboard.Close()
                    _announce("Immagine copiata negli appunti!")
                    return
            except Exception:
                pass
            _announce("Impossibile copiare l’immagine.")
            return

        if ext == ".pdf":
            try:
                record = get_best_pdf_page_image(file_path)
                if record is None:
                    logos = extract_images_from_pdf(file_path)
                    if logos:
                        top = logos[0]
                        _announce(
                            f"Trovato solo logo o icona "
                            f"({top['w']} per {top['h']} pixel), "
                            f"non una pagina intera. "
                            f"Prova Copia Testo oppure Apri file."
                        )
                    else:
                        _announce(
                            "Nessuna pagina grafica in questo PDF. "
                            "Prova Copia Testo oppure Apri file."
                        )
                    return
                img = pdf_image_record_to_wx_image(record)
                if img is not None and img.IsOk():
                    bmp = wx.Bitmap(img)
                    if bmp.IsOk() and wx.TheClipboard.Open():
                        wx.TheClipboard.SetData(wx.BitmapDataObject(bmp))
                        wx.TheClipboard.Close()
                        _announce(
                            f"Pagina grafica copiata negli appunti, "
                            f"{img.GetWidth()} per {img.GetHeight()} pixel. "
                            f"Originale {record['w']} per {record['h']}."
                        )
                        return
            except Exception:
                pass
            _announce(
                "Impossibile copiare l’immagine da questo PDF. "
                "Puoi usare Copia File altrove oppure Apri file."
            )
            return

        _announce("Nessuna immagine da copiare in questo formato.")

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
            _announce("Nessuna immagine da salvare per questo risultato.")
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
                _announce(f"Immagine salvata in {dest}")
            except Exception:
                _announce("Impossibile salvare l’immagine.")
            return

        if ext == ".pdf":
            record = get_best_pdf_page_image(file_path)
            if record is None:
                logos = extract_images_from_pdf(file_path)
                if logos:
                    _announce(
                        "Trovato solo logo o icona, non una pagina da salvare. "
                        "Prova Copia Testo oppure Apri file."
                    )
                else:
                    _announce("Nessuna pagina grafica da salvare in questo PDF.")
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
                _announce(
                    f"Immagine salvata, "
                    f"{record['w']} per {record['h']} pixel, in {dest}"
                )
            else:
                _announce("Impossibile salvare l’immagine dal PDF.")
            return

        _announce("Nessuna immagine da salvare in questo formato.")

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
                _announce(f"File copiato con successo in {dest_dir}!")
            except Exception:
                _announce("Impossibile copiare il file nella destinazione.")
        dlg.Destroy()

    def open_containing_folder(self, file_path):
        try:
            subprocess.Popen(f'explorer /select,"{file_path}"')
            _announce("Apertura cartella contenitore in corso...")
        except Exception:
            _announce("Impossibile aprire la cartella contenitore.")


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self):
        super(GlobalPlugin, self).__init__()
        self._image_info_frames = []

    @scriptHandler.script(
        description="Apri la finestra principale di Ricerca Testuale",
        category="Ricerca Testuale Accesso Digitale",
        gesture="kb:NVDA+shift+control+f",
    )
    def script_openSearch(self, gesture):
        try:
            wx.CallAfter(self.open_search_window)
        except Exception as e:
            rtad_speak(f"Errore avvio ricerca: {e}")

    @scriptHandler.script(
        description="Mostra la finestra dei comandi rapidi",
        category="Ricerca Testuale Accesso Digitale",
        gesture="kb:NVDA+shift+control+s",
    )
    def script_showShortcuts(self, gesture):
        try:
            wx.CallAfter(self.show_shortcuts_dialog)
        except Exception as e:
            rtad_speak(f"Errore apertura comandi: {e}")

    @scriptHandler.script(
        description="Apri la pagina delle Donazioni PayPal",
        category="Ricerca Testuale Accesso Digitale",
        gesture="kb:NVDA+shift+control+d",
    )
    def script_openDonation(self, gesture):
        webbrowser.open(DONATION_URL)
        rtad_speak("Apertura pagina donazioni...")

    @scriptHandler.script(
        description=(
            "Descrivi la grafica sotto il navigatore (web) "
            "oppure il file immagine selezionato in Esplora file"
        ),
        category="Ricerca Testuale Accesso Digitale",
        gesture="kb:NVDA+shift+g",
    )
    def script_describeCurrentGraphic(self, gesture):
        # Esegui subito sul thread NVDA (non CallAfter): altrimenti si perde il navigatore.
        try:
            self.describe_current_graphic()
        except Exception as e:
            rtad_speak(f"Errore descrizione grafica: {e}")

    def describe_current_graphic(self):
        """Snapshot navigatore/file (thread NVDA) poi analisi in background."""
        if rtad_ocr is None:
            rtad_speak("Modulo immagini non disponibile.")
            return
        # 1) Leggi navigatore / selezione file QUI (thread principale)
        snap = snapshot_navigator_image_source()
        if not snap.get("ok_source"):
            rtad_speak(
                snap.get("error")
                or "Nessuna figura o file immagine utilizzabile."
            )
            return
        if snap.get("file_path"):
            rtad_speak("Analisi file immagine in corso…")
        else:
            rtad_speak("Preparazione immagine dal navigatore…")

        def _work():
            res = materialize_image_from_snapshot(snap)
            if not res.get("ok") or not res.get("path"):
                wx.CallAfter(
                    rtad_speak,
                    res.get("error")
                    or "Impossibile ottenere l'immagine dal navigatore.",
                )
                return
            method = res.get("method") or ""
            delete_after = method in ("url", "capture")
            base = os.path.basename(res.get("path") or "") or "immagine"
            nav_name = (snap.get("name") or "").strip()
            if method == "file":
                msg = f"Analisi file locale: {base}."
            elif method == "url":
                # Se il nome accessibile differisce dal file CDN, lo diciamo
                if nav_name and nav_name.lower() not in base.lower():
                    msg = (
                        f"Immagine web scaricata ({base}). "
                        f"Figura: {nav_name[:80]}. Analisi in corso…"
                    )
                else:
                    msg = f"Immagine web scaricata ({base}). Analisi in corso…"
            elif method == "capture":
                msg = "Area schermo catturata. Analisi in corso…"
            else:
                msg = "Analisi immagine in corso…"
            wx.CallAfter(rtad_speak, msg)
            wx.CallAfter(
                run_image_analysis,
                self,
                res["path"],
                "describe",
                False,
                delete_after,
                rtad_speak,
            )

        threading.Thread(target=_work, daemon=True).start()

    def open_search_window(self):
        try:
            frame = SearchFrame()
            frame.Show()
            frame.Raise()
            frame.txt_query.SetFocus()
            if check_first_run_update():
                wx.CallLater(600, frame.show_whats_new_dialog)
        except Exception as e:
            rtad_speak(f"Impossibile aprire la finestra di ricerca: {e}")

    def show_shortcuts_dialog(self):
        try:
            frame = ShortcutsFrame(None)
            frame.Show()
            frame.Raise()
        except Exception as e:
            rtad_speak(f"Impossibile aprire i comandi: {e}")
