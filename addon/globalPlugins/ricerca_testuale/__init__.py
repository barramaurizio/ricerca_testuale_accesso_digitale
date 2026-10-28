import addonHandler
import ctypes
import datetime
import globalPluginHandler
import globalVars
import json
import logging
import os
import re
import shutil
import scriptHandler
import subprocess
import sys
import tempfile
import textwrap
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
    import rtad_media
except ImportError:
    rtad_media = None

try:
    import rtad_guida_pratica
except ImportError:
    rtad_guida_pratica = None

try:
    import rtad_guida_html
except ImportError:
    rtad_guida_html = None

try:
    import rtad_epub
except ImportError:
    rtad_epub = None

try:
    import rtad_docstruct
except ImportError:
    rtad_docstruct = None
try:
    import rtad_reading_mark
except ImportError:
    rtad_reading_mark = None

try:
    import rtad_chat
except ImportError:
    rtad_chat = None

try:
    import rtad_translate
except ImportError:
    rtad_translate = None

try:
    import rtad_attach_dialog
except ImportError:
    rtad_attach_dialog = None

try:
    import rtad_zip
except ImportError:
    rtad_zip = None

addonHandler.initTranslation()

APP_TITLE = "Ricerca Testuale Accesso Digitale"
APP_VERSION = "1.8.8"
DONATION_URL = "https://paypal.me/AccessoDigitale"
YOUTUBE_URL = "https://www.youtube.com/@AccessoDigitale"
GITHUB_URL = "https://github.com/barramaurizio/ricerca_testuale_accesso_digitale/releases"
GITHUB_API_LATEST = "https://api.github.com/repos/barramaurizio/ricerca_testuale_accesso_digitale/releases/latest"
GITHUB_API_RELEASES = (
    "https://api.github.com/repos/barramaurizio/"
    "ricerca_testuale_accesso_digitale/releases?per_page=30"
)
EMAIL_DESTINATARIO = "mauritechstudio@gmail.com"

CONFIG_DIR = os.path.join(globalVars.appArgs.configPath, "rtad_data")
if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass
CONFIG_FILE = os.path.join(CONFIG_DIR, "rtad_settings.json")

OCR_CACHE_DIR = os.path.join(CONFIG_DIR, "ocr_cache")
MEDIA_CACHE_DIR = os.path.join(CONFIG_DIR, "media_cache")
if rtad_ocr is not None:
    try:
        rtad_ocr.configure(OCR_CACHE_DIR)
    except Exception:
        pass
if rtad_media is not None:
    try:
        rtad_media.configure(MEDIA_CACHE_DIR)
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
    """Spezza percorsi multipli e toglie virgolette / spazi (incolla da Esplora risorse).

    Accetta cartelle, unità (es. I:\\) e singoli file su qualsiasi unità.
    """
    out = []
    for t in re.split(r"[;,]", target_input or ""):
        t = (t or "").strip()
        for ch in ('"', "'", "\u201c", "\u201d", "\u2018", "\u2019", "`"):
            t = t.strip(ch)
        t = (
            t.replace("\u200b", "")
            .replace("\ufeff", "")
            .replace("\u00a0", " ")
            .strip()
        )
        if t.lower().startswith("percorso:"):
            t = t.split(":", 1)[1].strip()
            for ch in ('"', "'", "\u201c", "\u201d"):
                t = t.strip(ch)
        if t.lower().startswith("file:"):
            try:
                from urllib.parse import unquote, urlparse
                parsed = urlparse(t)
                path = unquote(parsed.path or "")
                if re.match(r"^/[A-Za-z]:", path):
                    path = path[1:]
                t = path.replace("/", "\\") if path else t
            except Exception:
                pass
        if t:
            t = os.path.expandvars(os.path.expanduser(t))
            try:
                t = os.path.normpath(t)
            except Exception:
                pass
            out.append(t)
    return out


def browse_start_dir(current_path: str) -> str:
    """Cartella di partenza per Sfoglia: se il percorso attuale è un file → genitore."""
    targets = normalize_search_targets(current_path or "")
    raw = targets[0] if targets else ""
    if not raw:
        return os.path.expanduser("~")
    try:
        if os.path.isfile(raw):
            parent = os.path.dirname(raw)
            return parent if parent and os.path.isdir(parent) else os.path.expanduser("~")
        if os.path.isdir(raw):
            return raw
        parent = os.path.dirname(raw)
        if parent and os.path.isdir(parent):
            return parent
    except Exception:
        pass
    return os.path.expanduser("~")


def paths_from_windows_clipboard():
    """Path da Appunti: file CF_HDROP (Esplora) oppure testo percorso."""
    found = []
    if not wx.TheClipboard.Open():
        return found
    try:
        try:
            fmt = wx.DataFormat(wx.DF_FILENAME)
            if wx.TheClipboard.IsSupported(fmt):
                data = wx.FileDataObject()
                if wx.TheClipboard.GetData(data):
                    for name in data.GetFilenames() or []:
                        p = (name or "").strip()
                        if p and (os.path.isfile(p) or os.path.isdir(p)):
                            found.append(os.path.normpath(p))
        except Exception:
            pass
        if found:
            return found
        try:
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT)):
                data = wx.TextDataObject()
                if wx.TheClipboard.GetData(data):
                    raw = (data.GetText() or "").strip()
                    if raw:
                        if "\n" in raw and ";" not in raw and "," not in raw:
                            raw = raw.splitlines()[0].strip()
                        for line in raw.splitlines():
                            line = line.strip().strip('"').strip("'")
                            low_line = line.lower()
                            if low_line.startswith("http://") or low_line.startswith("https://"):
                                found.append(line)
                        for t in normalize_search_targets(raw):
                            if t and (os.path.isfile(t) or os.path.isdir(t)):
                                found.append(t)
        except Exception:
            pass
    finally:
        try:
            wx.TheClipboard.Close()
        except Exception:
            pass
    out, seen = [], set()
    for p in found:
        key = os.path.normcase(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
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
    """Testo leggibile da HTML: niente script, style e tag; le entità diventano lettere."""
    if not html_content:
        return ""
    text = str(html_content)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(
        r"</(?:h[1-6]|p|title|blockquote)>",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"</(?:li|tr|div|dt|dd)>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


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
    ".xlsx",
    ".pdf",
    ".epub",
    ".eml", ".mbox", ".mbx",
    ".rss", ".xml", ".atom", ".opml",
)
TEXT_LIKE_EXTS = (
    ".txt", ".log", ".csv", ".md", ".rtf", ".html", ".htm",
)

_URL_TYPE_EXT = {
    "text/html": ".html",
    "application/xhtml+xml": ".html",
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tif",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/flac": ".flac",
    "audio/ogg": ".ogg",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "text/plain": ".txt",
    "application/epub+zip": ".epub",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/msword": ".doc",
    "application/vnd.oasis.opendocument.text": ".odt",
}


def _known_result_exts():
    return set(DOC_EXTS) | set(IMG_EXTS) | set(MEDIA_EXTS)


def internet_shortcut_target(path):
    """Collegamento Windows .url → indirizzo http(s), altrimenti stringa vuota."""
    if not path or os.path.splitext(path)[1].lower() != ".url":
        return ""
    text = ""
    for enc in ("utf-8", "mbcs", "latin-1"):
        try:
            with open(path, "r", encoding=enc, errors="replace") as handle:
                text = handle.read(4000)
            break
        except Exception:
            text = ""
    for line in text.splitlines():
        if line.lower().startswith("url="):
            return line.split("=", 1)[1].strip()
    return ""


def _ext_from_content_type(content_type):
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype in _URL_TYPE_EXT:
        return _URL_TYPE_EXT[ctype]
    return ""


def _ext_from_body(head, url_ext):
    if head.startswith(b"%PDF"):
        return ".pdf"
    if head.startswith(b"\x89PNG"):
        return ".png"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"GIF8"):
        return ".gif"
    if head.startswith(b"PK\x03\x04") and url_ext in (".docx", ".xlsx", ".epub", ".odt"):
        return url_ext
    sample = head[:500].lstrip().lower()
    if (
        sample.startswith(b"<!doctype html")
        or sample.startswith(b"<html")
        or sample.startswith(b"<?xml")
        or b"<html" in sample[:400]
    ):
        return ".html"
    if url_ext in _known_result_exts():
        return url_ext
    return ".html" if b"<" in sample[:200] else (url_ext or "")


def _safe_download_name(url, ext):
    parsed = urllib.parse.urlparse(url)
    name = urllib.parse.unquote(os.path.basename(parsed.path or "") or "")
    name = re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .")
    if not name:
        name = (parsed.netloc or "pagina").replace(":", "_")
    base, old = os.path.splitext(name)
    if old.lower() in _known_result_exts() or (ext and old.lower() == ext):
        name = base or name
    if ext and not name.lower().endswith(ext):
        name += ext
    if len(name) > 80:
        stem, suf = os.path.splitext(name)
        name = stem[:70] + suf
    return name or ("pagina" + (ext or ""))


def save_internet_url_locally(url):
    """Scarica l'URL in un file temporaneo con l'estensione giusta. (percorso, errore)."""
    url = (url or "").strip()
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36 RTAD"
                ),
                "Accept": "*/*",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            ctype = resp.headers.get("Content-Type", "")
            length = resp.headers.get("Content-Length")
            try:
                if length and int(length) > MAX_CONTENT_SCAN_BYTES:
                    return "", (
                        "Il file in rete supera 40 MB. "
                        "Puoi aprirlo nel browser."
                    )
            except ValueError:
                pass
            raw = resp.read(MAX_CONTENT_SCAN_BYTES + 1)
            final = resp.geturl() or url
    except Exception:
        return "", "Impossibile scaricare la pagina. Puoi aprirla nel browser."
    if len(raw) > MAX_CONTENT_SCAN_BYTES:
        return "", "Il file in rete supera 40 MB. Puoi aprirlo nel browser."
    parsed = urllib.parse.urlparse(final)
    url_ext = os.path.splitext(urllib.parse.unquote(parsed.path or ""))[1].lower()
    if len(url_ext) > 8:
        url_ext = ""
    ext = _ext_from_content_type(ctype) or _ext_from_body(raw[:800], url_ext)
    if not ext:
        ext = ".bin"
    folder = os.path.join(tempfile.gettempdir(), "rtad_url")
    try:
        os.makedirs(folder, exist_ok=True)
        dest = os.path.join(folder, _safe_download_name(final, ext))
        if os.path.exists(dest):
            stem, suf = os.path.splitext(os.path.basename(dest))
            dest = os.path.join(folder, f"{stem}_{int(time.time())}{suf}")
        with open(dest, "wb") as handle:
            handle.write(raw)
    except Exception:
        return "", "Impossibile salvare la pagina scaricata."
    return dest, ""


def copy_with_sniffed_extension(path):
    """Se il file non ha un tipo noto ma il contenuto sì, ne fa una copia col suffisso giusto."""
    if not path or not os.path.isfile(path):
        return path
    ext = os.path.splitext(path)[1].lower()
    if ext in _known_result_exts():
        return path
    try:
        with open(path, "rb") as handle:
            head = handle.read(800)
    except Exception:
        return path
    sniffed = _ext_from_body(head, "")
    if not sniffed or sniffed == ext:
        return path
    folder = os.path.join(tempfile.gettempdir(), "rtad_url")
    try:
        os.makedirs(folder, exist_ok=True)
        base = os.path.splitext(os.path.basename(path))[0] or "pagina"
        base = re.sub(r'[<>:"/\\|?*]', "_", base).strip(" .") or "pagina"
        dest = os.path.join(folder, base[:70] + sniffed)
        if os.path.exists(dest):
            dest = os.path.join(folder, f"{base[:60]}_{int(time.time())}{sniffed}")
        shutil.copyfile(path, dest)
    except Exception:
        return path
    return dest


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
        "Solo Documenti (.txt, .pdf, .docx, .xlsx, .epub, .eml, .html, .md, …)",
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


def rtad_speak(msg, force=False, delay_ms=400):
    """Annuncio RTAD rispettando Mute F7 (voce/velocità restano di NVDA).

    Parte dopo un attimo: la chiusura di un menu o di una finestra di scelta
    fa leggere a NVDA il controllo che riceve il cursore e taglia ui.message
    immediato. delay_ms=0 resta per l'elenco file, dove la riga va detta subito.
    """
    if not _rtad_speech_settings_loaded:
        try:
            load_rtad_speech_settings()
        except Exception:
            pass
    if not _rtad_speech_active and not force:
        return
    text = str(msg or "").strip()
    if not text:
        return
    try:
        wait = int(delay_ms or 0)
    except Exception:
        wait = 400
    if wait > 0:
        def _later(m=text, forced=force):
            rtad_speak(m, force=forced, delay_ms=0)
        try:
            wx.CallLater(wait, _later)
            return
        except Exception:
            pass
    if not _rtad_speech_active and not force:
        return
    try:
        ui.message(text)
    except Exception:
        pass


def speak_accessible(text, force=False, delay_ms=400):
    """Stesso annuncio di rtad_speak: lo usa anche la conversazione Gemini."""
    rtad_speak(text, force=force, delay_ms=delay_ms)


def wrap_report_text(s, width=72):
    """Righe standard per report/descrizioni (UI, copia, salva)."""
    if s is None:
        return ""
    text = str(s).replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        return ""
    out = []
    for line in text.split("\n"):
        if len(line) <= width:
            out.append(line)
            continue
        stripped = line.strip()
        if " " not in stripped and (
            "://" in line
            or "\\" in line
            or (len(stripped) > 1 and stripped[1:3] == ":\\")
        ):
            out.append(line)
            continue
        chunks = textwrap.wrap(
            line,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
            replace_whitespace=False,
            drop_whitespace=False,
        )
        out.extend(chunks if chunks else [""])
    return "\n".join(out)


def get_real_ready_drives():
    """Unità pronte: rimovibili (2), fisse (3), CD/DVD (5)."""
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if bitmask & 1:
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                try:
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    if drive_type in (2, 3, 5):
                        os.listdir(drive_path)
                        drives.append(drive_path)
                except Exception:
                    pass
        bitmask >>= 1
    return drives


def _path_looks_like_video_ts(path):
    if not path:
        return False
    low = os.path.normpath(path).lower().replace("/", "\\")
    if low.rstrip("\\").endswith("\\video_ts") or "\\video_ts\\" in low + "\\":
        return True
    try:
        if os.path.isdir(path):
            return os.path.isdir(os.path.join(path, "VIDEO_TS"))
    except Exception:
        pass
    return False


def message_for_cda_path(path):
    name = os.path.basename(path or "") or "traccia.cda"
    return (
        f"«{name}» non è un file audio sul disco: "
        "è un collegamento di Windows a una traccia del CD audio. "
        "RTAD non può riprodurre né trascrivere le tracce .cda. "
        "Se sul CD/DVD ci sono cartelle con mp3, pdf o foto, "
        "imposta quella cartella (o l’intera unità) e cerca lì."
    )

def extract_document_text(file_path):
    """Testo leggibile da PDF/DOCX/EPUB/testo per «Leggi documento»."""
    if not file_path or not os.path.isfile(file_path):
        return ""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            return "\n".join(extract_lines_from_pdf(file_path)).strip()
        if ext in (".docx", ".doc"):
            return "\n".join(extract_paragraphs_from_docx(file_path)).strip()
        if ext == ".xlsx":
            return "\n".join(
                (row.get("text") or "") for row in extract_rows_from_xlsx(file_path)
            ).strip()
        if ext == ".epub":
            if rtad_epub is None:
                return ""
            return "\n".join(rtad_epub.extract_paragraphs_from_epub(file_path) or []).strip()
        if ext in (".html", ".htm"):
            try:
                with open(file_path, "rb") as f:
                    raw_data = f.read()
            except Exception:
                return ""
            if raw_data.startswith(b"\xff\xfe") or raw_data.startswith(b"\xfe\xff"):
                text = raw_data.decode("utf-16", errors="ignore")
            else:
                try:
                    text = raw_data.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw_data.decode("latin1", errors="ignore")
            return strip_html_to_text(text.replace("\x00", "")).strip()
        if ext in TEXT_LIKE_EXTS:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read().strip()
            except Exception:
                return ""
    except Exception:
        return ""
    return ""


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


def _xlsx_local_tag(tag):
    return (tag or "").rsplit("}", 1)[-1]


def _xlsx_cell_shared_text(si_el):
    parts = []
    for el in si_el.iter():
        if _xlsx_local_tag(el.tag) == "t" and el.text:
            parts.append(el.text)
    return "".join(parts)


def _xlsx_format_cell_value(raw):
    """Rende leggibili seriali data/ora Excel (es. 46175.02 → gg/mm/aaaa hh:mm)."""
    s = (raw or "").strip()
    if not s:
        return s
    try:
        num = float(s.replace(",", "."))
    except Exception:
        return s
    if s.lower() in ("nan", "inf", "-inf"):
        return s
    try:
        if 0 < num < 1:
            total_sec = int(round(num * 86400))
            hh = total_sec // 3600
            mm = (total_sec % 3600) // 60
            ss = total_sec % 60
            if ss:
                return f"{hh:02d}:{mm:02d}:{ss:02d}"
            return f"{hh:02d}:{mm:02d}"
        if 20000 <= num < 100000:
            base = datetime.datetime(1899, 12, 30)
            dt = base + datetime.timedelta(days=num)
            if abs(num - int(num)) < 1e-9:
                return dt.strftime("%d/%m/%Y")
            return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return s
    if abs(num - int(num)) < 1e-9 and abs(num) < 1e12:
        return str(int(num))
    return s


def extract_rows_from_xlsx(file_path, max_rows=50000):
    """Estrae righe di testo da .xlsx (OOXML, senza openpyxl).

    Restituisce lista di dict: sheet, row (1-based), text.
    """
    out = []
    if not file_path or not os.path.isfile(file_path):
        return out
    try:
        magic = _read_file_magic(file_path, 4)
        if not _is_ooxml_zip_magic(magic):
            return out
        with zipfile.ZipFile(file_path) as z:
            names = set(z.namelist())
            shared = []
            if "xl/sharedStrings.xml" in names:
                raw = z.read("xl/sharedStrings.xml")
                if len(raw) > MAX_DOCX_XML_BYTES:
                    raw = raw[:MAX_DOCX_XML_BYTES]
                tree = ET.fromstring(raw)
                for si in tree.iter():
                    if _xlsx_local_tag(si.tag) == "si":
                        shared.append(_xlsx_cell_shared_text(si))

            sheet_metas = []  # (name, path)
            if "xl/workbook.xml" in names:
                wb_raw = z.read("xl/workbook.xml")
                if len(wb_raw) > MAX_DOCX_XML_BYTES:
                    wb_raw = wb_raw[:MAX_DOCX_XML_BYTES]
                wb = ET.fromstring(wb_raw)
                rid_to_target = {}
                if "xl/_rels/workbook.xml.rels" in names:
                    rel_raw = z.read("xl/_rels/workbook.xml.rels")
                    rel_root = ET.fromstring(rel_raw)
                    for rel in rel_root.iter():
                        if _xlsx_local_tag(rel.tag) != "Relationship":
                            continue
                        rid = rel.attrib.get("Id") or ""
                        target = (rel.attrib.get("Target") or "").replace("\\", "/")
                        if rid and target:
                            if not target.startswith("xl/"):
                                target = "xl/" + target.lstrip("/")
                            rid_to_target[rid] = target
                for sh in wb.iter():
                    if _xlsx_local_tag(sh.tag) != "sheet":
                        continue
                    name = (sh.attrib.get("name") or "Foglio").strip() or "Foglio"
                    rid = (
                        sh.attrib.get(
                            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                        )
                        or sh.attrib.get("r:id")
                        or ""
                    )
                    target = rid_to_target.get(rid) or ""
                    if target and target in names:
                        sheet_metas.append((name, target))
            if not sheet_metas:
                for n in sorted(names):
                    if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"):
                        sheet_metas.append((os.path.basename(n), n))

            limit = max(1, int(max_rows or 50000))
            for sheet_name, sheet_path in sheet_metas:
                if len(out) >= limit:
                    break
                try:
                    info = z.getinfo(sheet_path)
                except KeyError:
                    continue
                if info.file_size > MAX_DOCX_XML_BYTES:
                    continue
                sheet_raw = z.read(sheet_path)
                if len(sheet_raw) > MAX_DOCX_XML_BYTES:
                    sheet_raw = sheet_raw[:MAX_DOCX_XML_BYTES]
                sheet_tree = ET.fromstring(sheet_raw)
                for row_el in sheet_tree.iter():
                    if _xlsx_local_tag(row_el.tag) != "row":
                        continue
                    try:
                        row_num = int(row_el.attrib.get("r") or 0)
                    except Exception:
                        row_num = 0
                    cells = []
                    for c in row_el:
                        if _xlsx_local_tag(c.tag) != "c":
                            continue
                        ctype = c.attrib.get("t") or ""
                        val = ""
                        if ctype == "s":
                            v_el = None
                            for child in c:
                                if _xlsx_local_tag(child.tag) == "v":
                                    v_el = child
                                    break
                            try:
                                idx = int((v_el.text if v_el is not None else "") or -1)
                            except Exception:
                                idx = -1
                            if 0 <= idx < len(shared):
                                val = shared[idx]
                        elif ctype == "inlineStr":
                            for child in c.iter():
                                if _xlsx_local_tag(child.tag) == "t" and child.text:
                                    val += child.text
                        else:
                            v_el = None
                            for child in c:
                                if _xlsx_local_tag(child.tag) == "v":
                                    v_el = child
                                    break
                            if v_el is not None and v_el.text:
                                val = _xlsx_format_cell_value(v_el.text)
                        val = (val or "").strip()
                        if val:
                            cells.append(val)
                    if not cells:
                        continue
                    if row_num <= 0:
                        row_num = len(out) + 1
                    text = " | ".join(cells)
                    out.append({
                        "sheet": sheet_name,
                        "row": row_num,
                        "text": text,
                    })
                    if len(out) >= limit:
                        break
        return out
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
# Gap TJ (millesimi di text-space): sopra soglia ≈ spazio tra parole (CID senza glyph space)
_PDF_TJ_SPACE_THRESHOLD = 120
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


def _pdf_piece_needs_space(prev: str, nxt: str) -> bool:
    """Spazio tra due pezzi solo se sono parole diverse.

    Un PDF giustificato stacca spesso l'ultima cifra o l'ultima lettera:
    «202» + «7», «2» + «,» + «8», «milion» + «i», «T» + «ale».
    """
    if not prev or not nxt:
        return False
    if prev.endswith("\n") or nxt.startswith("\n"):
        return False
    if prev[-1].isspace() or nxt[0].isspace():
        return False
    left = prev.rstrip()
    right = nxt.lstrip()
    if not left or not right:
        return False
    end_char = left[-1]
    start_char = right[0]
    if end_char.isdigit() and start_char.isdigit():
        return False
    if end_char.isdigit() and start_char in ",.":
        return False
    if end_char in ",." and start_char.isdigit():
        return False
    if start_char in ",.;:!?":
        return False
    if len(left) == 1 and end_char.isupper() and start_char.islower():
        return False
    if end_char.isalpha() and right.isalpha() and right.islower() and len(right) <= 2:
        return False
    return True


def extract_lines_from_pdf_bytes(raw, deadline=None, source_label=""):
    """Estrae righe di testo da byte PDF (file o allegato email)."""
    if deadline is None:
        deadline = time.monotonic() + FILE_CONTENT_SOFT_TIMEOUT_PDF_SEC
    if not raw:
        return []
    label = source_label or "pdf-bytes"

    if not raw.startswith(b"%PDF"):
        return _pdf_fallback_crude_lines(raw)

    font_cmaps, default_cmap = _pdf_build_font_cmaps(raw, deadline=deadline)

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
                _pdf_text_from_content_stream(
                    data,
                    default_cmap,
                    font_cmaps=font_cmaps,
                    deadline=deadline,
                )
            )
            content_used += 1
        stream_count += 1
        if stream_count % 4 == 0:
            time.sleep(0)
        pos = end + 9

    # Unisci pezzi preservando \n da ' / " / T*; spazio solo tra pezzi sulla stessa riga
    blob_parts = []
    for p in pieces:
        if not p:
            continue
        if blob_parts and _pdf_piece_needs_space(blob_parts[-1], p):
            blob_parts.append(" ")
        blob_parts.append(p)
    blob = "".join(blob_parts)
    blob = blob.replace("\r\n", "\n").replace("\r", "\n")
    blob = _pdf_normalize_control_spaces(blob)
    blob = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", blob)
    blob = _pdf_trim_binary_tail(blob)
    blob = _pdf_soften_camel_glued(blob)
    lines = []
    for part in blob.split("\n"):
        part = re.sub(r"[ \t]+", " ", part).strip()
        if not part:
            continue
        chunks = []
        if len(part) <= 240:
            chunks.append(part)
        else:
            while part:
                if len(part) <= 240:
                    chunks.append(part)
                    break
                cut = part.rfind(" ", 0, 240)
                if cut < 40:
                    cut = 240
                chunks.append(part[:cut].strip())
                part = part[cut:].strip()
        for chunk in chunks:
            if not chunk or _pdf_looks_like_garbage(chunk):
                continue
            lines.append(chunk)

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


def _pdf_cmap_from_tounicode_data(data):
    """Parsa beginbfchar/beginbfrange → codice CID (int) → carattere."""
    cmap = {}
    if not data:
        return cmap
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
    return cmap


def _pdf_obj_num_before(raw, pos, lookback=2500):
    """Numero oggetto più vicino prima di pos (`N 0 obj`), o -1.

    lookback ampio: i font con /Widths lunghi mettono /ToUnicode a >240 byte
    dall'intestazione oggetto (es. sample-multilingual-text.pdf).
    """
    window = raw[max(0, pos - max(240, int(lookback))):pos]
    matches = list(re.finditer(br"(\d+)\s+0\s+obj", window))
    if not matches:
        return -1
    try:
        return int(matches[-1].group(1))
    except Exception:
        return -1


def _pdf_build_font_cmaps(raw, deadline=None):
    """ToUnicode per font (1.6.6).

    Prima le CMap venivano fuse in una sola: su PDF multi-font lo stesso CID
    mappa a caratteri diversi → testo spazzatura. Ora:
      - cmap per oggetto ToUnicode
      - associazione nome risorsa (/F1, /TT0, …) → cmap del font
      - default solo se c'è una sola CMap (PDF mono-font)

    Restituisce (font_cmaps, default_cmap).
    """
    obj_cmaps = {}
    orphan_cmaps = []
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
        stream_pos = pos
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
        cmap = _pdf_cmap_from_tounicode_data(data)
        if not cmap:
            continue
        obj_n = _pdf_obj_num_before(raw, stream_pos if dict_start < 0 else dict_start)
        if obj_n >= 0:
            obj_cmaps[obj_n] = cmap
        else:
            orphan_cmaps.append(cmap)

    font_obj_to_tu = {}
    for m in re.finditer(br"/ToUnicode\s+(\d+)\s+0\s+R", raw):
        try:
            tu = int(m.group(1))
        except Exception:
            continue
        fobj = _pdf_obj_num_before(raw, m.start())
        if fobj >= 0:
            font_obj_to_tu[fobj] = tu

    def _map_font_resource_body(body, into):
        for fm in re.finditer(
            br"/([A-Za-z][#A-Za-z0-9._+\-]*)\s+(\d+)\s+0\s+R", body
        ):
            try:
                name = fm.group(1).decode("latin1")
                fobj = int(fm.group(2))
            except Exception:
                continue
            tu = font_obj_to_tu.get(fobj)
            if tu is not None and tu in obj_cmaps:
                into[name] = obj_cmaps[tu]
            elif fobj in obj_cmaps:
                into[name] = obj_cmaps[fobj]

    font_cmaps = {}
    for m in re.finditer(br"/Font\s*<<((?:[^>]|>(?!>)){0,4000})>>", raw):
        _map_font_resource_body(m.group(1), font_cmaps)
    for m in re.finditer(br"/Font\s+(\d+)\s+0\s+R", raw):
        try:
            dict_obj = int(m.group(1))
        except Exception:
            continue
        body = _pdf_object_dict_body(raw, dict_obj)
        if body:
            _map_font_resource_body(body, font_cmaps)

    all_cmaps = list(obj_cmaps.values()) + orphan_cmaps
    if len(all_cmaps) == 1:
        default_cmap = all_cmaps[0]
    elif len(font_cmaps) == 1:
        default_cmap = next(iter(font_cmaps.values()))
    else:
        default_cmap = {}
    return font_cmaps, default_cmap


def _pdf_object_dict_body(raw, obj_num):
    """Restituisce i byte interni di `N 0 obj << … >>` (best-effort, no xref)."""
    if obj_num < 0:
        return b""
    m = re.search(
        rb"(?:^|\n)" + str(obj_num).encode("ascii") + rb"\s+0\s+obj\b",
        raw,
    )
    if not m:
        return b""
    start = raw.find(b"<<", m.end())
    if start < 0 or start - m.end() > 80:
        return b""
    depth = 0
    i = start
    n = len(raw)
    while i < n - 1 and i - start < 8000:
        if raw[i:i + 2] == b"<<":
            depth += 1
            i += 2
            continue
        if raw[i:i + 2] == b">>":
            depth -= 1
            i += 2
            if depth <= 0:
                return raw[start + 2:i - 2]
            continue
        i += 1
    return b""


def _pdf_parse_tounicode_cmaps(raw, deadline=None):
    """Compat: CMap di default (mono-font) oppure vuota se multi-font."""
    _fonts, default_cmap = _pdf_build_font_cmaps(raw, deadline=deadline)
    return default_cmap


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


def _pdf_cmap_mostly_bytes(cmap):
    """True se la CMap è tipica di font semplici (codici 0–255), non CID."""
    if not cmap:
        return False
    keys = list(cmap.keys())
    sample = keys if len(keys) <= 64 else keys[:: max(1, len(keys) // 64)]
    if not sample:
        return False
    return sum(1 for k in sample if 0 <= int(k) < 256) >= max(1, int(len(sample) * 0.85))


def _pdf_decode_byte_cmap(data, cmap):
    """Decodifica stringa a 1 byte con ToUnicode (TrueType/Type1 semplici)."""
    if not data:
        return ""
    chars = []
    for b in data:
        ch = cmap.get(b)
        if ch:
            chars.append(ch)
        elif 32 <= b < 127:
            chars.append(chr(b))
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
    if cmap:
        if _pdf_cmap_mostly_bytes(cmap) and not _pdf_looks_like_cid_bytes(data):
            mapped = _pdf_decode_byte_cmap(data, cmap)
            if mapped.strip():
                return mapped
        if _pdf_looks_like_cid_bytes(data) or (
            len(data) % 2 == 0 and len(data) >= 2 and b"\x00" in data
        ):
            mapped = _pdf_decode_cid_bytes(data, cmap)
            if mapped.strip():
                return mapped
        if _pdf_cmap_mostly_bytes(cmap):
            mapped = _pdf_decode_byte_cmap(data, cmap)
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
        if _pdf_cmap_mostly_bytes(cmap) and not _pdf_looks_like_cid_bytes(data):
            mapped = _pdf_decode_byte_cmap(data, cmap)
            if mapped.strip():
                return mapped
        if len(cleaned) % 4 == 0 or _pdf_looks_like_cid_bytes(data):
            mapped = _pdf_decode_cid_bytes(data, cmap)
            if mapped.strip():
                return mapped
        if _pdf_cmap_mostly_bytes(cmap):
            mapped = _pdf_decode_byte_cmap(data, cmap)
            if mapped.strip():
                return mapped
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin1", errors="ignore")


def _pdf_join_tj_parts(parts, space_threshold=None):
    """Unisce operandi TJ: numeri grandi = gap → spazio (es. Batteria[-250]interna)."""
    if space_threshold is None:
        space_threshold = _PDF_TJ_SPACE_THRESHOLD
    out = []
    for item in parts:
        if isinstance(item, (int, float)):
            if abs(float(item)) >= space_threshold:
                if out and not out[-1].endswith((" ", "\n", "\t")):
                    out.append(" ")
            continue
        s = item or ""
        if not s:
            continue
        out.append(s)
    return "".join(out)


def _pdf_soften_camel_glued(text):
    """Inserisce spazi su confini lower→Upper / lettera↔cifra (titoli stilizzati).

    Non tocca sequenze tutte minuscole (quelle dipendono dai gap TJ).
    """
    if not text or len(text) < 4:
        return text
    text = re.sub(
        r"([a-zàèéìòù])([A-ZÀÈÉÌÒÙ])",
        r"\1 \2",
        text,
    )
    text = re.sub(
        r"([A-Za-zÀ-ÿ])(\d)",
        r"\1 \2",
        text,
    )
    text = re.sub(
        r"(\d)([A-Za-zÀ-ÿ])",
        r"\1 \2",
        text,
    )
    return text


def _pdf_normalize_control_spaces(text):
    """Converte placeholder spazio (ToUnicode/custom) in spazi veri.

    Ogni PDF può mappare lo spazio diversamente (Acer \\x00\\x03, Focus \\x06…).
    I controlli vanno sostituiti con spazio, non solo cancellati.
    """
    if not text:
        return text
    text = text.replace("\x00\x03", " ")
    text = text.replace("\x00\x20", " ")
    text = text.replace("\x00\x02", " ")
    text = text.replace("\x00\xa0", " ")
    text = text.replace("\x01\x8e", " • ")
    text = text.replace("\x8e", " • ")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
    text = text.replace("\x00", "")
    return text


def _pdf_text_from_content_stream(
    data: bytes, cmap: dict = None, font_cmaps: dict = None, deadline=None
) -> list:
    """Estrae stringhe Tj/TJ; rispetta /Nome size Tf per la CMap del font.

    Nei TJ i numeri di posizionamento grandi diventano spazi tra parole
    (tipico CID senza glyph dello spazio → «Batteriainterna»).
    """
    if cmap is None:
        cmap = {}
    if font_cmaps is None:
        font_cmaps = {}
    if not data:
        return []
    if len(data) > _PDF_TEXT_PARSE_MAX:
        data = data[:_PDF_TEXT_PARSE_MAX]
    pieces = []
    n = len(data)
    i = 0
    current_cmap = cmap

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

    def _read_number(j):
        """Legge numero PDF (gap TJ); ritorna (float|None, nuovo_indice)."""
        start = j
        if j < n and data[j] in b"+-":
            j += 1
        if j >= n or data[j] not in b"0123456789.":
            return None, start
        saw_digit = False
        while j < n and data[j] in b"0123456789.":
            if data[j] != 0x2E:
                saw_digit = True
            j += 1
        if not saw_digit:
            return None, start
        try:
            return float(data[start:j]), j
        except ValueError:
            return None, start

    while i < n:
        if deadline is not None and (i & 0xFFFF) == 0 and time.monotonic() > deadline:
            break
        b = data[i]
        if b == 0x2F and font_cmaps:  # /Nome … Tf → cambia font/CMap
            j = i + 1
            while j < n and data[j] not in b" \t\r\n\f\0<>[]()/":
                j += 1
            if j > i + 1:
                try:
                    fname = data[i + 1:j].decode("latin1")
                except Exception:
                    fname = ""
                k = _skip_ws(j)
                num = k
                if num < n and data[num] in b"+-.0123456789":
                    num += 1
                    while num < n and data[num] in b"0123456789.":
                        num += 1
                    k2 = _skip_ws(num)
                    if k2 + 1 < n and data[k2:k2 + 2] == b"Tf":
                        current_cmap = font_cmaps.get(fname, cmap)
                        i = k2 + 2
                        continue
            i = j if j > i else i + 1
            continue
        if b == 0x54 and i + 1 < n and data[i + 1] == 0x2A:  # T* = nuova riga
            pieces.append("\n")
            i += 2
            continue
        if b == 0x28:  # (
            lit, j = _read_literal(i)
            k = _skip_ws(j)
            if k + 1 < n and data[k:k + 2] == b"Tj":
                pieces.append(_pdf_bytes_to_text(lit, current_cmap))
                i = k + 2
                continue
            if k < n and data[k:k + 1] in (b"'", b'"'):
                # ' e " = vai a capo e mostra testo
                pieces.append("\n" + _pdf_bytes_to_text(lit, current_cmap))
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
                    pieces.append(_pdf_hex_to_str(bytes(hx), current_cmap))
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
                    parts.append(_pdf_bytes_to_text(lit, current_cmap))
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
                        parts.append(_pdf_hex_to_str(bytes(hx), current_cmap))
                        j = j2 + 1
                        continue
                if data[j] in b"+-.0123456789" and depth == 1:
                    num, j2 = _read_number(j)
                    if num is not None:
                        parts.append(num)
                        j = j2
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
                pieces.append(_pdf_join_tj_parts(parts))
                i = k + 2
                continue
            i += 1
            continue
        i += 1
    return [p for p in pieces if p]


def _pdf_trim_binary_tail(text):
    """Taglia solo la coda binaria finale (non a metà documento)."""
    if not text or len(text) < 200:
        return text
    window = min(2500, len(text) // 5)
    start = len(text) - window
    tail = text[start:]
    m = re.search(
        r"""["']\s*[bB]\s*&\s*["']|"""
        r"ÿ{2,}|"
        r"[\x80-\x9f]{3,}|"
        r"(?:\ufffd){2,}",
        tail,
    )
    if m:
        return text[: start + m.start()].rstrip()
    letters = sum(1 for c in text[-120:] if c.isalpha())
    if letters < 15:
        cut = text.rfind(". ", 0, len(text) - 40)
        if cut > len(text) * 0.7:
            return text[: cut + 1]
    return text


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
    if s in (
        "True",
        "False",
        "Standard",
        "it",
        "en",
        "Identity",
        "stream",
        "obj",
        "Macintosh",
        "Mac OS",
    ):
        return True
    if "ÿÿÿ" in s or "\ufffd\ufffd" in s or s.count("ÿ") >= 3:
        return True
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", s):
        return True
    alnum = sum(1 for c in s if c.isalnum() or c.isspace())
    if alnum < max(3, len(s) // 2):
        return True
    letters = sum(1 for c in s if c.isalpha())
    if len(s) >= 40 and letters < len(s) // 5:
        return True
    bad = sum(
        1
        for c in s
        if ord(c) < 9 or c in "\x00\ufffdþÿÎÔ" or (0x80 <= ord(c) <= 0x9F)
    )
    if bad and bad >= max(1, len(s) // 8):
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
                        img = (
                            rtad_ocr.load_wx_image_silent(tmp)
                            if rtad_ocr is not None
                            else None
                        )
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


def load_transcript_glossary():
    """(enabled, rules[{find, replace}])."""
    data = _load_settings_dict()
    enabled = bool(data.get("transcript_glossary_enabled", False))
    raw = data.get("transcript_glossary", [])
    if rtad_media is not None and hasattr(rtad_media, "normalize_glossary_rules"):
        rules = rtad_media.normalize_glossary_rules(raw)
    else:
        rules = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and str(item.get("find") or "").strip():
                    rules.append({
                        "find": str(item.get("find") or "").strip(),
                        "replace": str(item.get("replace") or ""),
                    })
    return enabled, rules


def save_transcript_glossary(enabled, rules):
    data = _load_settings_dict()
    data["transcript_glossary_enabled"] = bool(enabled)
    if rtad_media is not None and hasattr(rtad_media, "normalize_glossary_rules"):
        clean = rtad_media.normalize_glossary_rules(rules)
    else:
        clean = list(rules or [])
    data["transcript_glossary"] = clean
    _save_settings_dict(data)
    sync_transcript_glossary_to_media()


def sync_transcript_glossary_to_media():
    """Applica a rtad_media le regole attive (lista vuota se disattivato)."""
    if rtad_media is None or not hasattr(rtad_media, "set_transcript_glossary"):
        return
    try:
        enabled, rules = load_transcript_glossary()
        rtad_media.set_transcript_glossary(rules if enabled else [])
    except Exception as e:
        logging.debug(f"Sync glossario media: {e}")


def apply_glossary_to_rtad_txt_file(file_path):
    """Riscrive un .rtad.txt con il glossario attivo. True se il file è cambiato."""
    path = (file_path or "").strip()
    if not path or not os.path.isfile(path):
        return False
    if not path.lower().endswith(".rtad.txt"):
        return False
    if rtad_media is None or not hasattr(rtad_media, "apply_transcript_glossary"):
        return False
    try:
        sync_transcript_glossary_to_media()
        if not rtad_media.get_transcript_glossary():
            return False
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            original = f.read()
        updated = rtad_media.apply_transcript_glossary(original)
        if updated == original:
            return False
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(updated)
        logging.info(f"Glossario applicato al file: {path}")
        return True
    except Exception as e:
        logging.warning(f"Glossario su file non applicato ({path}): {e}")
        return False


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
    if rtad_media is not None:
        try:
            rtad_media.set_gemini_api_key(key)
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


def _safe_filename_stem(text, fallback="rtad_report", max_len=220):
    """Riduce titolo/query a stem di nome file Windows-safe.

    max_len~220: titoli lunghi (YouTube ecc.) restano quasi interi;
    sotto i ~255 del solo nome file (+ .rtad.txt). Il percorso intero
    resta soggetto al MAX_PATH (~260) se LongPaths non è attivo.
    """
    raw = (text or "").strip()
    if not raw:
        return fallback
    cleaned = []
    for ch in raw:
        if ch in '<>:"/\\|?*' or ord(ch) < 32:
            cleaned.append("_")
        else:
            cleaned.append(ch)
    s = re.sub(r"\s+", " ", "".join(cleaned)).strip(" .")
    if not s:
        return fallback
    if len(s) > max_len:
        s = s[:max_len].rstrip(" .")
    return s or fallback


def _looks_like_temp_dir(path):
    """True per Temp Windows o cartelle download media RTAD (non usarle come default)."""
    if not path:
        return True
    try:
        p = os.path.normcase(os.path.abspath(path))
        tmp = os.path.normcase(os.path.abspath(tempfile.gettempdir()))
        if p == tmp or p.startswith(tmp + os.sep):
            return True
        base = os.path.basename(p).lower()
        if base.startswith("rtad_media_dl_") or "rtad_media" in base:
            return True
    except Exception:
        return False
    return False


def load_last_media_report_dir():
    data = _load_settings_dict()
    p = str(data.get("last_media_report_dir", "") or "").strip()
    return p if p and os.path.isdir(p) else ""


def save_last_media_report_dir(path):
    try:
        if path and os.path.isfile(path):
            d = os.path.dirname(os.path.abspath(path))
        elif path and os.path.isdir(path):
            d = os.path.abspath(path)
        else:
            return
    except Exception:
        return
    if not d or not os.path.isdir(d):
        return
    data = _load_settings_dict()
    data["last_media_report_dir"] = d
    _save_settings_dict(data)


def report_save_stem_for_path(file_path):
    """Stem per «Salva testo»: stem del file locale; titolo/ID solo su temp URL.

    File sul disco (es. partita_juve.mp4) → partita_juve.rtad.txt.
    Scarico temp yt-dlp/HTTP (rtad_media_* in Temp) → titolo o ID sorgente.
    """
    base = os.path.basename(file_path) if file_path else "rtad_report"
    stem = os.path.splitext(base)[0] or "rtad_report"
    # Titolo/ID solo per scarichi RTAD (prefisso rtad_media_*).
    # Un file locale rinominato (anche con .rtad_src.json) tiene lo stem disco.
    use_source_meta = (base or "").lower().startswith("rtad_media_")
    if use_source_meta:
        try:
            if rtad_media is not None and file_path:
                meta = rtad_media.read_media_source_meta(file_path)
                title = str(meta.get("title") or "").strip()
                src_id = str(meta.get("id") or "").strip()
                if title:
                    return _safe_filename_stem(title, fallback=stem)
                if src_id:
                    return _safe_filename_stem(src_id, fallback=stem)
        except Exception:
            pass
    return _safe_filename_stem(stem, fallback="rtad_report")


def load_auto_save_results_preference():
    """False di default: salvataggio automatico risultati a fine ricerca."""
    data = _load_settings_dict()
    return bool(data.get("auto_save_results", False))


def save_auto_save_results_preference(enabled):
    data = _load_settings_dict()
    data["auto_save_results"] = bool(enabled)
    _save_settings_dict(data)


def load_last_export_dir():
    data = _load_settings_dict()
    p = str(data.get("last_export_dir", "") or "").strip()
    return p if p and os.path.isdir(p) else ""


def save_last_export_dir(path):
    try:
        if path and os.path.isfile(path):
            d = os.path.dirname(os.path.abspath(path))
        elif path and os.path.isdir(path):
            d = os.path.abspath(path)
        else:
            return
    except Exception:
        return
    if not d or not os.path.isdir(d):
        return
    data = _load_settings_dict()
    data["last_export_dir"] = d
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
    """Toast WinRT breve (duration=short); non sticky reminder (rispetta il lettore documento)."""
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
        "$xmlText = \"<toast duration='short'><visual><binding template='ToastGeneric'>"
        "<text>$t</text><text>$b</text></binding></visual></toast>\"; "
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


def open_excel_at_row(file_path, row_number, sheet_name=""):
    """Apre Excel e seleziona la riga del risultato (come Word sul paragrafo)."""

    def _worker():
        opened = False
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import win32com.client

            try:
                excel = win32com.client.GetActiveObject("Excel.Application")
            except Exception:
                excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = True
            excel.DisplayAlerts = False
            abs_path = os.path.abspath(file_path)
            wb = None
            try:
                for i in range(1, excel.Workbooks.Count + 1):
                    try:
                        wbi = excel.Workbooks(i)
                        if os.path.normcase(os.path.abspath(wbi.FullName)) == os.path.normcase(
                            abs_path
                        ):
                            wb = wbi
                            break
                    except Exception:
                        continue
            except Exception:
                wb = None
            if wb is None:
                wb = excel.Workbooks.Open(abs_path)
            time.sleep(0.35)

            ws = None
            wanted = (sheet_name or "").strip()
            if wanted:
                try:
                    ws = wb.Worksheets(wanted)
                except Exception:
                    ws = None
            if ws is None:
                try:
                    ws = wb.Worksheets(1)
                except Exception:
                    ws = wb.ActiveSheet
            try:
                ws.Activate()
            except Exception:
                pass

            row_n = int(row_number or 0)
            if row_n > 0:
                target = None
                for col in range(1, 9):
                    try:
                        cell = ws.Cells(row_n, col)
                        val = cell.Value
                        if val is not None and str(val).strip():
                            target = cell
                            break
                    except Exception:
                        continue
                if target is None:
                    target = ws.Cells(row_n, 1)
                try:
                    target.Select()
                except Exception:
                    try:
                        ws.Rows(row_n).Select()
                    except Exception:
                        pass

            try:
                excel.Activate()
            except Exception:
                pass
            try:
                hwnd = ctypes.windll.user32.FindWindowW(None, excel.Caption)
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 3)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
            opened = True
        except Exception as e:
            logging.error(f"Fallita apertura COM di Excel per {file_path}: {e}")

        if not opened:
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "open", file_path, None, None, 1)
            except Exception as e:
                logging.error(f"Fallita apertura Excel fallback: {e}")

    threading.Thread(target=_worker, daemon=True).start()


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

        self.txt_display = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
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

        self.txt_display = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
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
    """Carica chiavi Vision/Gemini in rtad_ocr / rtad_media (best-effort)."""
    if rtad_ocr is None and rtad_media is None:
        return
    try:
        gkey = load_google_vision_api_key()
        if gkey and rtad_ocr is not None:
            rtad_ocr.set_google_api_key(gkey)
    except Exception:
        pass
    try:
        gemkey = load_gemini_api_key()
        if gemkey:
            if rtad_ocr is not None:
                rtad_ocr.set_gemini_api_key(gemkey)
            if rtad_media is not None:
                rtad_media.set_gemini_api_key(gemkey)
    except Exception:
        pass
    try:
        sync_transcript_glossary_to_media()
    except Exception:
        pass


def run_image_analysis(
    host,
    file_path,
    mode="describe",
    copy_only=False,
    delete_after=False,
    speak=None,
    sections=None,
    *,
    source_path="",
):
    """Analisi immagine riusabile da SearchFrame e GlobalPlugin (1.6.4).

    source_path: PDF/originale se file_path è un temp estratto (stem/cartella).
    """
    speak = speak or rtad_speak
    if not file_path or not os.path.isfile(file_path):
        speak("File immagine non trovato.")
        return
    if rtad_ocr is None:
        speak("Modulo immagini non disponibile.")
        return
    _ensure_ocr_keys()
    src_path = (source_path or "").strip()

    if mode in ("describe", "copy-describe", "alt", "alt-long", "all") and not load_gemini_api_key():
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
            if mode == "all":
                title = "Tutto sull'immagine"
                sec = sections or {}
                body = rtad_ocr.format_full_image_report(
                    file_path,
                    include_alt=sec.get("include_alt", True),
                    include_describe=sec.get("include_describe", True),
                    include_labels=sec.get("include_labels", True),
                    include_tech=sec.get("include_tech", True),
                    include_ocr=sec.get("include_ocr", False),
                    source_path=src_path,
                )
            elif mode == "tech":
                title = "Scheda tecnica immagine"
                body = rtad_ocr.format_tech_sheet(
                    rtad_ocr.get_image_tech_info(file_path, source_path=src_path)
                )
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
                body = rtad_ocr.format_alt_and_long_description(
                    file_path, source_path=src_path
                )
            else:
                title = "Descrizione immagine"
                body = rtad_ocr.describe_image(file_path, source_path=src_path)
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
            frm = ImageInfoFrame(
                None,
                title,
                body,
                image_path=file_path,
                source_path=src_path,
            )

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

    def _url_looks_svg(u):
        try:
            path = (urllib.parse.urlparse(u or "").path or "").lower()
        except Exception:
            path = (u or "").lower()
        return path.endswith(".svg") or "image/svg" in (u or "").lower()

    # Raster prima; SVG (es. icone 3BMeteo) → cattura area, non download finto .jpg
    raster_urls = [u for u in urls if u and not _url_looks_svg(u)]
    only_svg = bool(urls) and not raster_urls
    rect = snap.get("rect")

    if only_svg and rect and len(rect) == 4:
        left, top, width, height = rect
        cap = rtad_ocr.materialize_image_from_screen_rect(left, top, width, height)
        if cap.get("ok") and cap.get("path"):
            result["ok"] = True
            result["path"] = cap["path"]
            result["method"] = "capture"
            return result

    for u in raster_urls or urls:
        if _url_looks_svg(u):
            continue
        dl = rtad_ocr.materialize_image_from_url(u)
        if dl.get("ok") and dl.get("path"):
            result["ok"] = True
            result["path"] = dl["path"]
            result["method"] = "url"
            return result

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


class TranscriptGlossaryDialog(wx.Dialog):
    """Editor glossario post-trascrizione (1.7.2)."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title="Glossario trascrizioni",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        enabled, rules = load_transcript_glossary()
        self._rules = [dict(r) for r in (rules or [])]
        vbox = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self,
            label=(
                "Correzioni dopo Gemini su riassunto/trascrizione "
                "(e in ricerca nei .rtad.txt se il glossario è attivo).\n"
                "Esempio: Vlahovic → Woltemade (vale anche Vlahović).\n"
                "Non richiama l’API. Con glossario attivo, aprendo un .rtad.txt "
                "da un risultato la correzione viene anche scritta nel file."
            ),
        )
        vbox.Add(intro, 0, wx.ALL | wx.EXPAND, 10)
        self.chk_enabled = wx.CheckBox(
            self, label="&Attiva glossario sulle prossime analisi"
        )
        self.chk_enabled.SetValue(bool(enabled))
        vbox.Add(self.chk_enabled, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.lst = wx.ListBox(self, style=wx.LB_SINGLE)
        self.lst.SetMinSize((-1, 160))
        vbox.Add(self.lst, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._reload_list()

        grid = wx.FlexGridSizer(2, 2, 6, 8)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self, label="&Trova:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_find = wx.TextCtrl(self)
        grid.Add(self.txt_find, 1, wx.EXPAND)
        grid.Add(
            wx.StaticText(self, label="&Sostituisci con:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.txt_repl = wx.TextCtrl(self)
        grid.Add(self.txt_repl, 1, wx.EXPAND)
        vbox.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        h_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_add = wx.Button(self, label="A&ggiungi / aggiorna")
        btn_add.Bind(wx.EVT_BUTTON, self._on_add)
        h_btns.Add(btn_add, 0, wx.RIGHT, 6)
        btn_del = wx.Button(self, label="&Rimuovi selezionata")
        btn_del.Bind(wx.EVT_BUTTON, self._on_remove)
        h_btns.Add(btn_del, 0)
        vbox.Add(h_btns, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        h_ok = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(self, wx.ID_OK, label="Sal&va")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Annulla")
        btn_ok.SetDefault()
        h_ok.Add(btn_ok, 0, wx.ALL, 5)
        h_ok.Add(btn_cancel, 0, wx.ALL, 5)
        vbox.Add(h_ok, 0, wx.ALIGN_CENTER | wx.BOTTOM, 8)

        self.SetSizerAndFit(vbox)
        self.SetMinSize((480, 420))
        self.CentreOnParent()
        self.lst.Bind(wx.EVT_LISTBOX, self._on_select)
        self.Bind(wx.EVT_BUTTON, self._on_ok, btn_ok)
        self.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CANCEL), btn_cancel)
        self.txt_find.SetFocus()

    def _label(self, rule):
        find = rule.get("find") or ""
        repl = rule.get("replace") or ""
        return f"{find} → {repl}"

    def _reload_list(self):
        self.lst.Clear()
        if not self._rules:
            self.lst.Append("Nessuna correzione nel glossario.")
        else:
            for r in self._rules:
                self.lst.Append(self._label(r))
        self.lst.SetSelection(0)

    def _on_select(self, event=None):
        sel = self.lst.GetSelection()
        if sel == wx.NOT_FOUND or sel < 0 or sel >= len(self._rules):
            return
        r = self._rules[sel]
        self.txt_find.SetValue(r.get("find") or "")
        self.txt_repl.SetValue(r.get("replace") or "")

    def _on_add(self, event=None):
        find = (self.txt_find.GetValue() or "").strip()
        repl = self.txt_repl.GetValue() or ""
        if not find:
            rtad_speak("Scrivi la parola da trovare.")
            self.txt_find.SetFocus()
            return
        key = find.casefold()
        updated = False
        for r in self._rules:
            if (r.get("find") or "").casefold() == key:
                r["find"] = find
                r["replace"] = repl
                updated = True
                break
        if not updated:
            self._rules.append({"find": find, "replace": repl})
        if rtad_media is not None and hasattr(rtad_media, "normalize_glossary_rules"):
            self._rules = rtad_media.normalize_glossary_rules(self._rules)
        self._reload_list()
        rtad_speak("Regola aggiornata." if updated else "Regola aggiunta.")
        self.txt_find.SetValue("")
        self.txt_repl.SetValue("")
        self.txt_find.SetFocus()

    def _on_remove(self, event=None):
        sel = self.lst.GetSelection()
        if sel == wx.NOT_FOUND or sel < 0 or sel >= len(self._rules):
            rtad_speak("Seleziona una regola da rimuovere.")
            return
        removed = self._rules.pop(sel)
        self._reload_list()
        rtad_speak(f"Rimossa: {removed.get('find') or ''}")

    def _on_ok(self, event=None):
        pending = (self.txt_find.GetValue() or "").strip()
        if pending:
            self._on_add()
        self.EndModal(wx.ID_OK)

    def result(self):
        return bool(self.chk_enabled.GetValue()), list(self._rules)


class ImageSectionsDialog(wx.Dialog):
    """Scelta sezioni per «Tutto sull'immagine» / batch cartella (1.6.6).

    Pulsanti sul Dialog (non CreateButtonSizer su Panel): altrimenti OK/Invio
    sembrava premuto ma non chiudeva.
    """

    def __init__(
        self,
        parent,
        title="Tutto sull'immagine",
        *,
        batch_mode=False,
        default_labels=True,
        context_label="",
        image_count=None,
    ):
        super().__init__(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.batch_mode = bool(batch_mode)
        vbox = wx.BoxSizer(wx.VERTICAL)
        if self.batch_mode:
            intro = "Analisi di tutte le immagini nella cartella."
            if context_label:
                intro += f"\nCartella: {context_label}"
            if image_count is not None:
                intro += f"\nImmagini trovate: {image_count}."
            intro += "\n\nScegli le sezioni, poi Invio o «Avvia analisi»."
        else:
            intro = "Scegli cosa includere nel report, poi Invio o «Avvia analisi»."
            if context_label:
                intro += f"\nImmagine: {context_label}"
        vbox.Add(wx.StaticText(self, label=intro), 0, wx.ALL | wx.EXPAND, 10)

        self.chk_alt = wx.CheckBox(self, label="&Alt-text breve")
        self.chk_alt.SetValue(True)
        vbox.Add(self.chk_alt, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.chk_describe = wx.CheckBox(self, label="&Descrizione dettagliata")
        self.chk_describe.SetValue(True)
        vbox.Add(self.chk_describe, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.chk_labels = wx.CheckBox(self, label="&Etichette e oggetti")
        self.chk_labels.SetValue(bool(default_labels) and not self.batch_mode)
        vbox.Add(self.chk_labels, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.chk_tech = wx.CheckBox(self, label="&Scheda tecnica")
        self.chk_tech.SetValue(True)
        vbox.Add(self.chk_tech, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        # Stesso percorso di «Leggi testo nell'immagine» (OCR) — gemello SA
        self.chk_ocr = wx.CheckBox(self, label="&Testo OCR (leggi testo nell'immagine)")
        self.chk_ocr.SetValue(False)
        vbox.Add(self.chk_ocr, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.chk_save = None
        self.chk_recursive = None
        if self.batch_mode:
            self.chk_save = wx.CheckBox(
                self, label="Salva un file &.rtad.txt accanto a ogni immagine"
            )
            self.chk_save.SetValue(True)
            vbox.Add(self.chk_save, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.chk_recursive = wx.CheckBox(
                self, label="Includi anche le sott&ocartelle"
            )
            self.chk_recursive.SetValue(False)
            vbox.Add(self.chk_recursive, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        hint = wx.StaticText(
            self,
            label=(
                "Le caselle deselezionate non compaiono nel report. "
                "Le voci singole del menu contestuale restano disponibili."
            ),
        )
        vbox.Add(hint, 0, wx.ALL | wx.EXPAND, 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(self, wx.ID_OK, label="A&vvia analisi")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Annulla")
        btn_ok.SetDefault()
        hbox.Add(btn_ok, 0, wx.ALL, 5)
        hbox.Add(btn_cancel, 0, wx.ALL, 5)
        vbox.Add(hbox, 0, wx.ALIGN_CENTER | wx.BOTTOM | wx.TOP, 8)

        self.SetSizerAndFit(vbox)
        self.CentreOnParent()
        self.Bind(wx.EVT_BUTTON, self._on_ok, btn_ok)
        self.Bind(wx.EVT_BUTTON, self._on_cancel, btn_cancel)
        self.chk_alt.SetFocus()

    def _on_ok(self, event=None):
        if not any(
            [
                self.chk_alt.GetValue(),
                self.chk_describe.GetValue(),
                self.chk_labels.GetValue(),
                self.chk_tech.GetValue(),
                self.chk_ocr.GetValue(),
            ]
        ):
            rtad_speak("Seleziona almeno una sezione.")
            return
        self.EndModal(wx.ID_OK)

    def _on_cancel(self, event=None):
        self.EndModal(wx.ID_CANCEL)

    def selections(self):
        return {
            "include_alt": self.chk_alt.GetValue(),
            "include_describe": self.chk_describe.GetValue(),
            "include_labels": self.chk_labels.GetValue(),
            "include_tech": self.chk_tech.GetValue(),
            "include_ocr": self.chk_ocr.GetValue(),
            "save_txt": bool(self.chk_save and self.chk_save.GetValue()),
            "recursive": bool(self.chk_recursive and self.chk_recursive.GetValue()),
        }


def _saved_translate_code():
    data = _load_settings_dict()
    code = str(data.get("translate_target") or "it").strip().lower()
    if rtad_translate is None or not rtad_translate.language_by_code(code):
        return "it"
    return code


def _save_translate_code(code):
    if rtad_translate is None or not rtad_translate.language_by_code(code):
        return
    data = _load_settings_dict()
    data["translate_target"] = code
    _save_settings_dict(data)


def _media_translate_lang(dialog):
    codes = list(getattr(dialog, "_lang_codes", None) or ["it"])
    try:
        sel = dialog.choice_lang.GetSelection()
    except Exception:
        sel = 0
    code = codes[sel] if 0 <= sel < len(codes) else "it"
    _save_translate_code(code)
    return code


class TranslationLanguageDialog(wx.Dialog):
    """Lingua di arrivo. L'italiano è già selezionato."""

    def __init__(self, parent, current="it"):
        super().__init__(
            parent,
            title="Traduci",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._codes = list(rtad_translate.language_codes()) if rtad_translate else ["it"]
        labels = list(rtad_translate.language_labels()) if rtad_translate else ["Italiano"]
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(
            wx.StaticText(
                self,
                label=(
                    "Si traduce il testo già aperto. L'originale resta.\n"
                    "La traduzione si aggiunge sotto. In un video restano i timestamp.\n"
                    "La lingua di partenza la riconosce Gemini."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            10,
        )
        vbox.Add(
            wx.StaticText(self, label="&Lingua di arrivo:"),
            0,
            wx.LEFT | wx.RIGHT,
            10,
        )
        self.choice = wx.Choice(self, choices=labels)
        try:
            self.choice.SetSelection(self._codes.index(current))
        except ValueError:
            self.choice.SetSelection(0)
        vbox.Add(self.choice, 0, wx.EXPAND | wx.ALL, 10)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(self, wx.ID_OK, label="&Traduci")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Annulla")
        btn_ok.SetDefault()
        hbox.Add(btn_ok, 0, wx.ALL, 5)
        hbox.Add(btn_cancel, 0, wx.ALL, 5)
        vbox.Add(hbox, 0, wx.ALIGN_CENTER | wx.BOTTOM, 8)
        self.SetSizerAndFit(vbox)
        self.CentreOnParent()
        self.choice.SetFocus()

    def chosen_code(self):
        sel = self.choice.GetSelection()
        if 0 <= sel < len(self._codes):
            return self._codes[sel]
        return "it"


def ask_translation_language(parent, speak):
    if rtad_translate is None:
        speak("Traduzione non disponibile.")
        return ""
    dlg = TranslationLanguageDialog(parent, _saved_translate_code())
    try:
        if dlg.ShowModal() != wx.ID_OK:
            speak("Traduzione annullata.")
            return ""
        code = dlg.chosen_code()
    finally:
        dlg.Destroy()
    _save_translate_code(code)
    return code


def _frame_alive(frame) -> bool:
    try:
        return bool(frame) and not frame.IsBeingDeleted()
    except Exception:
        return False


def start_frame_translation(frame, speak):
    """Traduci sul testo del riquadro. Un secondo clic interrompe."""
    if rtad_translate is None:
        speak("Traduzione non disponibile.")
        return
    if getattr(frame, "_translate_busy", False):
        if not getattr(frame, "_translate_abort", False):
            frame._translate_abort = True
            frame.lbl_translate.SetLabel(rtad_translate.MSG_ABORT)
            speak(rtad_translate.MSG_ABORT)
        return
    text = frame.txt_display.GetValue() or ""
    if not text.strip():
        speak(rtad_translate.MSG_EMPTY)
        if hasattr(frame, "lbl_translate"):
            frame.lbl_translate.SetLabel(rtad_translate.MSG_EMPTY)
        return
    if rtad_translate.has_translation(text):
        ask = wx.MessageDialog(
            frame,
            "C'è già una traduzione. Vuoi sostituirla?",
            "Traduci",
            wx.YES_NO | wx.ICON_QUESTION,
        )
        try:
            yes = ask.ShowModal() == wx.ID_YES
        finally:
            ask.Destroy()
        if not yes:
            speak("Traduzione annullata.")
            return
        text = rtad_translate.strip_translation(text)
        frame.txt_display.SetValue(text)
    key = ""
    try:
        key = load_gemini_api_key() or ""
    except Exception:
        key = ""
    if not key:
        speak(rtad_translate.MSG_NO_KEY)
        frame.lbl_translate.SetLabel(rtad_translate.MSG_NO_KEY)
        return
    code = ask_translation_language(frame, speak)
    if not code:
        return
    if rtad_ocr is not None:
        try:
            rtad_ocr.set_gemini_api_key(key)
        except Exception:
            pass
    frame._translate_busy = True
    frame._translate_abort = False
    frame.btn_translate.SetLabel("Annulla tradu&zione")
    frame.lbl_translate.SetLabel("Traduzione in corso.")

    def _abort():
        return bool(getattr(frame, "_translate_abort", False))

    def _on_progress(index, total, message):
        def _ui():
            if not _frame_alive(frame):
                return
            frame.lbl_translate.SetLabel(message)
            try:
                frame.lbl_translate.Wrap(640)
                frame.Layout()
            except Exception:
                pass
            say = index <= 1 or index >= total or total <= 12 or index % 4 == 0
            if say:
                speak(message)

        wx.CallAfter(_ui)

    def _work():
        result = rtad_translate.translate_text(
            text,
            code,
            key,
            should_abort=_abort,
            on_progress=_on_progress,
        )

        def _done():
            if not _frame_alive(frame):
                return
            frame._translate_busy = False
            frame.btn_translate.SetLabel("Trad&uci…")
            shown = result.get("text") or text
            if not result.get("skipped"):
                frame.txt_display.SetValue(shown)
            status = result.get("status") or ""
            if not status:
                status = (
                    rtad_translate.MSG_DONE
                    if result.get("ok")
                    else "Traduzione non riuscita."
                )
            frame.lbl_translate.SetLabel(status)
            try:
                frame.lbl_translate.Wrap(640)
                frame.Layout()
            except Exception:
                pass
            if not result.get("aborted"):
                speak(status)

        wx.CallAfter(_done)

    threading.Thread(target=_work, daemon=True, name="rtad-translate").start()


def _translate_report_body(body, lang, on_progress=None):
    """Dopo l'analisi audio/video, se la casella è accesa."""
    if rtad_translate is None:
        note = "Traduzione non disponibile."
        if on_progress:
            try:
                on_progress(100, note)
            except Exception:
                pass
        return (body or "").rstrip() + "\n\n" + note + "\n"
    key = ""
    try:
        key = load_gemini_api_key() or ""
    except Exception:
        key = ""
    if rtad_ocr is not None and key:
        try:
            rtad_ocr.set_gemini_api_key(key)
        except Exception:
            pass

    def _prog(index, total, message):
        if not on_progress:
            return
        try:
            pct = 90
            if total:
                pct = min(99, 80 + int(19 * int(index) / int(total)))
            on_progress(pct, message)
        except Exception:
            pass

    result = rtad_translate.translate_text(
        body or "",
        lang or "it",
        key,
        on_progress=_prog,
    )
    text = result.get("text") or (body or "")
    status = result.get("status") or ""
    if result.get("skipped") and status:
        text = (body or "").rstrip() + "\n\n" + status + "\n"
    if status and on_progress:
        try:
            on_progress(100, status)
        except Exception:
            pass
    return text


class MediaSectionsDialog(wx.Dialog):
    """Hub «Tutto sull'audio/video» / batch cartella (1.6.7 / 1.7.2)."""

    def __init__(
        self,
        parent,
        title="Tutto sull'audio/video",
        *,
        context_label="",
        show_source=True,
        initial_path="",
        initial_url="",
        preset_sections=None,
        batch_mode=False,
        media_count=None,
    ):
        super().__init__(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.batch_mode = bool(batch_mode)
        self.show_source = bool(show_source) and not self.batch_mode
        self._picked_path = (initial_path or "").strip()
        preset = preset_sections if isinstance(preset_sections, dict) else {}
        vbox = wx.BoxSizer(wx.VERTICAL)
        if self.batch_mode:
            intro = "Analisi di tutti i file audio/video nella cartella."
            if context_label:
                intro += f"\nCartella: {context_label}"
            if media_count is not None:
                intro += f"\nFile media trovati: {media_count}."
            intro += (
                "\n\nScegli le sezioni, poi Invio o «Avvia analisi».\n"
                "Scheda tecnica: locale. Riassunto/trascrizione: Gemini opt-in.\n"
                "La trascrizione non è attiva di default (tempo e costi API)."
            )
        else:
            intro = (
                "Scegli la sorgente (file locale e/o URL), le sezioni del report,\n"
                "poi Invio o «Avvia analisi».\n"
                "Scheda tecnica: locale. Riassunto/trascrizione: Gemini opt-in.\n"
                "Dal report usa «Nuova analisi» per riprendere l'hub "
                "(stesse opzioni, URL vuoto). Oppure Strumenti."
            )
            if context_label and not self.show_source:
                intro += f"\nFile: {context_label}"
        lbl = wx.StaticText(self, label=intro)
        vbox.Add(lbl, 0, wx.ALL | wx.EXPAND, 10)

        self.txt_url = None
        self.txt_file = None
        self.lbl_ytdlp = None
        if self.show_source:
            vbox.Add(
                wx.StaticText(self, label="URL audio/video (opzionale):"),
                0,
                wx.LEFT | wx.RIGHT | wx.TOP,
                8,
            )
            self.txt_url = wx.TextCtrl(self, value=(initial_url or "").strip())
            vbox.Add(self.txt_url, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            vbox.Add(
                wx.StaticText(self, label="Oppure file locale:"),
                0,
                wx.LEFT | wx.RIGHT | wx.TOP,
                8,
            )
            h_file = wx.BoxSizer(wx.HORIZONTAL)
            self.txt_file = wx.TextCtrl(self, value=self._picked_path)
            h_file.Add(self.txt_file, 1, wx.EXPAND | wx.RIGHT, 5)
            btn_browse = wx.Button(self, label="&Sfoglia…")
            btn_browse.Bind(wx.EVT_BUTTON, self._on_browse)
            h_file.Add(btn_browse, 0)
            vbox.Add(h_file, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

            self.lbl_ytdlp = wx.StaticText(self, label="yt-dlp: verifica in corso…")
            vbox.Add(self.lbl_ytdlp, 0, wx.ALL | wx.EXPAND, 8)
            h_yt = wx.BoxSizer(wx.HORIZONTAL)
            btn_yt_check = wx.Button(self, label="&Verifica yt-dlp")
            btn_yt_check.Bind(wx.EVT_BUTTON, self._on_ytdlp_check)
            h_yt.Add(btn_yt_check, 0, wx.RIGHT, 5)
            btn_yt_up = wx.Button(self, label="A&ggiorna yt-dlp")
            btn_yt_up.Bind(wx.EVT_BUTTON, self._on_ytdlp_update)
            h_yt.Add(btn_yt_up, 0)
            vbox.Add(h_yt, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            wx.CallAfter(self._refresh_ytdlp_label)

        self.chk_tech = wx.CheckBox(self, label="Sche&da tecnica")
        self.chk_tech.SetValue(bool(preset.get("include_tech", True)))
        vbox.Add(self.chk_tech, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.chk_describe = wx.CheckBox(self, label="&Riassunto accessibile (Gemini)")
        self.chk_describe.SetValue(bool(preset.get("include_describe", True)))
        vbox.Add(self.chk_describe, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.chk_transcript = wx.CheckBox(
            self, label="&Trascrizione parlato (Gemini, opt-in)"
        )
        self.chk_transcript.SetValue(bool(preset.get("include_transcript", False)))
        vbox.Add(self.chk_transcript, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.chk_whisper = wx.CheckBox(
            self, label="Sul mio &PC (Whisper, opt-in)"
        )
        self.chk_whisper.SetValue(
            (preset.get("transcript_engine") or "") == "whisper"
            and bool(preset.get("include_transcript", False))
        )
        vbox.Add(self.chk_whisper, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.chk_timestamps = wx.CheckBox(
            self, label="Timestamp &nella trascrizione ([MM:SS], opt-in)"
        )
        self.chk_timestamps.SetValue(
            bool(preset.get("include_timestamps", False)) and self.chk_transcript.GetValue()
        )
        vbox.Add(self.chk_timestamps, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.chk_translate = wx.CheckBox(
            self, label="Trad&uci la trascrizione"
        )
        self.chk_translate.SetValue(
            bool(preset.get("translate_transcript", False))
            and self.chk_transcript.GetValue()
        )
        vbox.Add(self.chk_translate, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        vbox.Add(
            wx.StaticText(self, label="&Lingua di arrivo:"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        self._lang_codes = (
            list(rtad_translate.language_codes()) if rtad_translate is not None else ["it"]
        )
        lang_labels = (
            list(rtad_translate.language_labels()) if rtad_translate is not None else ["Italiano"]
        )
        self.choice_lang = wx.Choice(self, choices=lang_labels)
        wanted = (preset.get("translate_lang") or _saved_translate_code() or "it")
        try:
            self.choice_lang.SetSelection(self._lang_codes.index(wanted))
        except ValueError:
            self.choice_lang.SetSelection(0)
        vbox.Add(self.choice_lang, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self.chk_save = None
        self.chk_recursive = None
        if self.batch_mode:
            self.chk_save = wx.CheckBox(
                self, label="Salva un file &.rtad.txt accanto a ogni media"
            )
            self.chk_save.SetValue(True)
            vbox.Add(self.chk_save, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.chk_recursive = wx.CheckBox(
                self, label="Includi anche le sott&ocartelle"
            )
            self.chk_recursive.SetValue(False)
            vbox.Add(self.chk_recursive, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        def _sync_ts(_evt=None):
            en = self.chk_transcript.GetValue()
            self.chk_timestamps.Enable(en)
            self.chk_translate.Enable(en)
            self.chk_whisper.Enable(en)
            if not en:
                self.chk_timestamps.SetValue(False)
                self.chk_translate.SetValue(False)
                self.chk_whisper.SetValue(False)
            self.choice_lang.Enable(en and self.chk_translate.GetValue())

        def _sync_translate(_evt=None):
            en = self.chk_transcript.GetValue() and self.chk_translate.GetValue()
            self.choice_lang.Enable(en)

        self.chk_transcript.Bind(wx.EVT_CHECKBOX, _sync_ts)
        self.chk_translate.Bind(wx.EVT_CHECKBOX, _sync_translate)
        _sync_ts()

        whisper_hint = (
            "Whisper, sul mio PC, è spento. Si accende insieme alla trascrizione: "
            "al primo uso scarica il modello e lavora anche senza chiave Gemini. "
            "Un file fino a 20 minuti. In una cartella, fino a 5 file."
        )
        if self.batch_mode:
            hint_txt = (
                "Accanto a ogni file viene creato «nome.rtad.txt» "
                "(stesso stem del media). "
                "Trascrizione e traduzione sono spente: si accendono solo se servono. "
                "File oltre i limiti: resta la scheda tecnica. "
                + whisper_hint
            )
        else:
            hint_txt = (
                "Se compili l'URL ha priorità sul file. "
                "Trascrizione e traduzione sono spente: si accendono solo se servono. "
                "File oltre i limiti: resta la scheda tecnica. "
                + whisper_hint
            )
        hint = wx.StaticText(self, label=hint_txt)
        vbox.Add(hint, 0, wx.ALL | wx.EXPAND, 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_ok = wx.Button(self, wx.ID_OK, label="&Avvia analisi")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Annulla")
        btn_ok.SetDefault()
        hbox.Add(btn_ok, 0, wx.ALL, 5)
        hbox.Add(btn_cancel, 0, wx.ALL, 5)
        vbox.Add(hbox, 0, wx.ALIGN_CENTER | wx.BOTTOM | wx.TOP, 8)

        self.SetSizerAndFit(vbox)
        self.CentreOnParent()
        self.Bind(wx.EVT_BUTTON, self._on_ok, btn_ok)
        self.Bind(wx.EVT_BUTTON, self._on_cancel, btn_cancel)
        if self.txt_url is not None:
            self.txt_url.SetFocus()
        else:
            self.chk_tech.SetFocus()

    def _on_browse(self, event=None):
        with wx.FileDialog(
            self,
            "Scegli un file audio o video",
            wildcard=(
                "Audio/Video|"
                "*.mp3;*.m4a;*.aac;*.flac;*.ogg;*.opus;*.wav;*.wma;"
                "*.mp4;*.m4v;*.mkv;*.avi;*.mov;*.wmv;*.webm;*.mpg;*.mpeg;*.3gp|"
                "Tutti i file|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fd:
            if fd.ShowModal() != wx.ID_OK:
                return
            path = fd.GetPath()
        self._picked_path = path
        if self.txt_file is not None:
            self.txt_file.SetValue(path)
        rtad_speak(f"File selezionato: {os.path.basename(path)}")

    def _refresh_ytdlp_label(self):
        if self.lbl_ytdlp is None or rtad_media is None:
            return
        try:
            st = rtad_media.check_ytdlp_status()
            self.lbl_ytdlp.SetLabel(st.get("message") or "yt-dlp: stato sconosciuto.")
            self.Layout()
            self.Fit()
        except Exception as e:
            self.lbl_ytdlp.SetLabel(f"yt-dlp: errore verifica ({e})")

    def _on_ytdlp_check(self, event=None):
        rtad_speak("Verifica yt-dlp…")
        self._refresh_ytdlp_label()
        if self.lbl_ytdlp is not None:
            rtad_speak(self.lbl_ytdlp.GetLabel())

    def _on_ytdlp_update(self, event=None):
        if rtad_media is None:
            rtad_speak("Modulo media non disponibile.")
            return
        rtad_speak("Aggiornamento yt-dlp in corso…")

        def _work():
            try:
                res = rtad_media.update_ytdlp()
            except Exception as e:
                res = {"ok": False, "message": str(e)}

            def _done():
                msg = res.get("message") or "Aggiornamento terminato."
                if self.lbl_ytdlp is not None:
                    self.lbl_ytdlp.SetLabel(msg)
                    self.Layout()
                    self.Fit()
                rtad_speak(msg)

            wx.CallAfter(_done)

        threading.Thread(target=_work, daemon=True).start()

    def _on_ok(self, event=None):
        if not any(
            [
                self.chk_tech.GetValue(),
                self.chk_describe.GetValue(),
                self.chk_transcript.GetValue(),
            ]
        ):
            rtad_speak("Seleziona almeno una sezione.")
            return
        if self.show_source and not self.batch_mode:
            url = (self.txt_url.GetValue() if self.txt_url else "") or ""
            url = url.strip().strip('"').strip("'")
            path = ""
            if self.txt_file is not None:
                path = (self.txt_file.GetValue() or "").strip().strip('"')
            if not path:
                path = self._picked_path
            if not url and not (path and os.path.isfile(path)):
                rtad_speak(
                    "Inserisci un URL oppure scegli un file audio/video."
                )
                return
        self.EndModal(wx.ID_OK)

    def _on_cancel(self, event=None):
        self.EndModal(wx.ID_CANCEL)

    def selections(self):
        want_tr = self.chk_transcript.GetValue()
        url = ""
        path = self._picked_path
        if self.show_source:
            if self.txt_url is not None:
                url = (self.txt_url.GetValue() or "").strip().strip('"').strip("'")
            if self.txt_file is not None:
                path = (self.txt_file.GetValue() or "").strip().strip('"') or path
        return {
            "include_tech": self.chk_tech.GetValue(),
            "include_describe": self.chk_describe.GetValue(),
            "include_transcript": want_tr,
            "transcript_engine": (
                "whisper" if want_tr and self.chk_whisper.GetValue() else "gemini"
            ),
            "include_timestamps": bool(want_tr and self.chk_timestamps.GetValue()),
            "translate_transcript": bool(want_tr and self.chk_translate.GetValue()),
            "translate_lang": _media_translate_lang(self),
            "url": url,
            "file_path": path,
            "save_txt": bool(self.chk_save and self.chk_save.GetValue()),
            "recursive": bool(
                self.chk_recursive and self.chk_recursive.GetValue()
            ),
        }


def _gemini_chat_use_web():
    data = _load_settings_dict()
    if "gemini_chat_use_web" not in data:
        return True
    return bool(data.get("gemini_chat_use_web"))


def _gemini_chat_set_use_web(enabled):
    data = _load_settings_dict()
    data["gemini_chat_use_web"] = bool(enabled)
    _save_settings_dict(data)


def _gemini_chat_privacy_ok(parent):
    data = _load_settings_dict()
    if data.get("gemini_chat_privacy_ack"):
        return True
    dlg = wx.MessageDialog(
        parent,
        "Le domande e gli estratti del file vengono inviati a Google (Gemini).\n"
        "La cronologia resta su questo PC e non contiene la chiave API.\n\n"
        "La consultazione web è accesa: Gemini può cercare fonti aggiornate "
        "e le separa da ciò che è nel file. Puoi spegnerla nella conversazione.\n\n"
        "Vuoi continuare?",
        "Conversazione con Gemini",
        wx.YES_NO | wx.ICON_INFORMATION,
    )
    try:
        ok = dlg.ShowModal() == wx.ID_YES
    finally:
        dlg.Destroy()
    if not ok:
        speak_accessible("Conversazione annullata.")
        return False
    data = _load_settings_dict()
    data["gemini_chat_privacy_ack"] = True
    if "gemini_chat_use_web" not in data:
        data["gemini_chat_use_web"] = True
    _save_settings_dict(data)
    return True


def _track_gemini_chat(frm):
    frames = getattr(_track_gemini_chat, "frames", None)
    if frames is None:
        frames = []
        _track_gemini_chat.frames = frames
    frames.append(frm)

    def _on_close(evt, frame=frm):
        try:
            frames.remove(frame)
        except ValueError:
            pass
        evt.Skip()

    frm.Bind(wx.EVT_CLOSE, _on_close)


def open_gemini_chat(
    kind,
    path,
    *,
    struct=None,
    displayed="",
    prior_report="",
    source_path="",
    parent=None,
):
    """Apre la conversazione sul file. kind: image | document."""
    if rtad_chat is None:
        speak_accessible("Modulo conversazione non disponibile.")
        return
    path = (path or "").strip()
    if not path or not os.path.isfile(path):
        speak_accessible("File non trovato. La conversazione resta sul file aperto.")
        return
    key = ""
    try:
        key = load_gemini_api_key()
    except Exception:
        key = ""
    if not key:
        speak_accessible(
            "Per conversare con Gemini serve la chiave personale, da Strumenti."
        )
        return
    if rtad_ocr is not None:
        try:
            rtad_ocr.set_gemini_api_key(key)
        except Exception:
            pass
    if not _gemini_chat_privacy_ok(parent):
        return
    session = None
    resumed = False
    try:
        session = rtad_chat.load_current(
            CONFIG_DIR,
            path,
            struct=struct,
            displayed=displayed,
            prior_report=prior_report,
        )
    except Exception as exc:
        logging.warning(f"Chat: cronologia non caricata: {exc}")
        session = None
    if session and session.get("turns"):
        resumed = True
        if source_path and not session.get("source_path"):
            session["source_path"] = source_path
    else:
        session = rtad_chat.new_session(
            kind,
            path,
            struct=struct,
            displayed=displayed,
            prior_report=prior_report,
            source_path=source_path,
        )
    frm = GeminiChatFrame(
        session,
        struct=struct,
        displayed=displayed,
        prior_report=prior_report,
        resumed=resumed,
    )
    _track_gemini_chat(frm)
    frm.Show()
    frm.Raise()


def open_gemini_chat_from_report(path, parent=None):
    """Dal .rtad.txt già salvato. Non rifà la descrizione né la trascrizione."""
    if rtad_chat is None:
        speak_accessible("Modulo conversazione non disponibile.")
        return
    path = (path or "").strip()
    if not path or not os.path.isfile(path):
        speak_accessible("File non trovato. La conversazione resta sul file aperto.")
        return
    key = ""
    try:
        key = load_gemini_api_key()
    except Exception:
        key = ""
    if not key:
        speak_accessible(
            "Per conversare con Gemini serve la chiave personale, da Strumenti."
        )
        return
    if rtad_ocr is not None:
        try:
            rtad_ocr.set_gemini_api_key(key)
        except Exception:
            pass
    if not _gemini_chat_privacy_ok(parent):
        return
    try:
        fresh = rtad_chat.new_session_from_report(path)
    except Exception as exc:
        speak_accessible(f"Conversazione non avviata: {exc}")
        return
    anchor = fresh.get("path") or path
    notice = fresh.get("report_notice") or ""
    resumed = False
    loaded = None
    try:
        loaded = rtad_chat.load_current(
            CONFIG_DIR,
            anchor,
            struct=fresh.get("_struct"),
            displayed=fresh.get("_displayed") or "",
            prior_report=fresh.get("_prior") or "",
        )
    except Exception as exc:
        logging.warning(f"Chat: cronologia del resoconto non caricata: {exc}")
        loaded = None
    if loaded and loaded.get("turns"):
        resumed = True
        loaded["report_path"] = fresh.get("report_path") or path
        loaded["report_orphan"] = bool(fresh.get("report_orphan"))
        loaded["report_notice"] = notice
        if fresh.get("report_orphan"):
            loaded["path"] = path
            loaded["title"] = os.path.basename(path)
            loaded["context_note"] = rtad_chat.NOTICE_REPORT_ORPHAN
        else:
            loaded["path"] = anchor
        try:
            rtad_chat.refresh_context(loaded)
        except Exception:
            logging.debug("Chat: rilettura resoconto non riuscita", exc_info=True)
        loaded["report_notice"] = notice
        if loaded.get("report_orphan"):
            loaded["context_note"] = rtad_chat.NOTICE_REPORT_ORPHAN
        session = loaded
    else:
        session = fresh
    frm = GeminiChatFrame(session, resumed=resumed)
    _track_gemini_chat(frm)
    frm.Show()
    frm.Raise()


def open_free_gemini_chat(parent=None):
    """Conversazione senza un file già aperto. Gli allegati si aggiungono dopo."""
    if rtad_chat is None:
        speak_accessible("Modulo conversazione non disponibile.")
        return
    key = ""
    try:
        key = load_gemini_api_key()
    except Exception:
        key = ""
    if not key:
        speak_accessible(
            "Per conversare con Gemini serve la chiave personale, da Strumenti."
        )
        return
    if rtad_ocr is not None:
        try:
            rtad_ocr.set_gemini_api_key(key)
        except Exception:
            pass
    if not _gemini_chat_privacy_ok(parent):
        return
    try:
        session = rtad_chat.new_free_session()
    except Exception as exc:
        speak_accessible(f"Conversazione non avviata: {exc}")
        return
    frm = GeminiChatFrame(session, resumed=False)
    _track_gemini_chat(frm)
    frm.Show()
    frm.Raise()


def open_saved_gemini_chat(json_path, parent=None):
    """Riapre una conversazione già salvata, con le fonti, senza rianalizzare."""
    if rtad_chat is None:
        speak_accessible("Modulo conversazione non disponibile.")
        return
    if not json_path or not os.path.isfile(json_path):
        speak_accessible("Conversazione non trovata.")
        return
    if not _gemini_chat_privacy_ok(parent):
        return
    try:
        key = load_gemini_api_key()
    except Exception:
        key = ""
    if key and rtad_ocr is not None:
        try:
            rtad_ocr.set_gemini_api_key(key)
        except Exception:
            pass
    try:
        session = rtad_chat.load_saved(json_path, do_refresh=False)
    except Exception as exc:
        speak_accessible(f"Conversazione non leggibile: {exc}")
        return
    if not session or not session.get("turns"):
        speak_accessible("Questa conversazione non ha scambi.")
        return
    frm = GeminiChatFrame(session, resumed=True)
    _track_gemini_chat(frm)
    frm.Show()
    frm.Raise()


class GeminiChatHistoryDialog(wx.Dialog):
    """Elenco conversazioni di un file: apri o elimina."""

    def __init__(self, parent, rows, title="Conversazioni di questo file"):
        super(GeminiChatHistoryDialog, self).__init__(
            parent,
            title=title,
            size=(640, 420),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.rows = list(rows or [])
        self.choice = None
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(
            wx.StaticText(panel, label="&Conversazioni salvate su questo PC"),
            0,
            wx.ALL,
            8,
        )
        self.lst = wx.ListBox(panel, style=wx.LB_SINGLE)
        try:
            self.lst.SetName("Conversazioni salvate")
        except Exception:
            pass
        for row in self.rows:
            self.lst.Append(row.get("label") or "Conversazione")
        if self.lst.GetCount():
            self.lst.SetSelection(0)
        vbox.Add(self.lst, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_open = wx.Button(panel, label="&Apri")
        btn_open.Bind(wx.EVT_BUTTON, self._on_open)
        hbox.Add(btn_open, 0, wx.ALL, 5)
        btn_del = wx.Button(panel, label="&Elimina")
        btn_del.Bind(wx.EVT_BUTTON, self._on_delete)
        hbox.Add(btn_del, 0, wx.ALL, 5)
        btn_cancel = wx.Button(panel, wx.ID_CANCEL, "Annulla")
        hbox.Add(btn_cancel, 0, wx.ALL, 5)
        vbox.Add(hbox, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(vbox)
        self.lst.Bind(wx.EVT_LISTBOX_DCLICK, self._on_open)
        if self.lst.GetCount():
            self.lst.SetFocus()
        speak_accessible(
            f"{self.lst.GetCount()} conversazioni. Invio o Apri per continuare."
        )

    def _selected(self):
        idx = self.lst.GetSelection()
        if idx == wx.NOT_FOUND or idx >= len(self.rows):
            return None
        return self.rows[idx]

    def _on_open(self, event=None):
        row = self._selected()
        if not row:
            speak_accessible("Nessuna conversazione selezionata.")
            return
        self.choice = ("open", row)
        self.EndModal(wx.ID_OK)

    def _on_delete(self, event=None):
        row = self._selected()
        if not row:
            speak_accessible("Nessuna conversazione selezionata.")
            return
        ask = wx.MessageDialog(
            self,
            "Eliminare questa conversazione da questo PC?",
            "Elimina conversazione",
            wx.YES_NO | wx.ICON_WARNING,
        )
        try:
            if ask.ShowModal() != wx.ID_YES:
                speak_accessible("Eliminazione annullata.")
                return
        finally:
            ask.Destroy()
        self.choice = ("delete", row)
        self.EndModal(wx.ID_OK)


class GeminiChatFrame(wx.Frame):
    """Dialogo accessibile: domanda, risposta, cronologia, salva e stampa."""

    def __init__(
        self,
        session,
        *,
        struct=None,
        displayed="",
        prior_report="",
        resumed=False,
    ):
        title_name = (session or {}).get("title") or "File"
        super(GeminiChatFrame, self).__init__(
            None,
            title=f"Chiedi a Gemini — {title_name}",
            size=(780, 680),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.session = session
        try:
            rtad_chat.set_text_extractor(extract_document_text)
        except Exception:
            pass
        self.struct = struct
        self.displayed = displayed or ""
        self.prior_report = prior_report or ""
        self._busy = False
        self._abort = False
        self._gen = 0
        self._live = None

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        notice = ((session or {}).get("report_notice") or "").strip()
        self.lbl_status = wx.StaticText(
            panel,
            label=(
                notice
                or (
                    "Domande ed estratti vanno a Google. La cronologia resta sul PC. "
                    "Esc annulla la richiesta in corso."
                )
            ),
        )
        vbox.Add(self.lbl_status, 0, wx.ALL | wx.EXPAND, 8)

        vbox.Add(wx.StaticText(panel, label="Conversazione"), 0, wx.LEFT | wx.RIGHT, 8)
        self.txt_history = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        try:
            self.txt_history.SetName("Conversazione")
        except Exception:
            pass
        vbox.Add(self.txt_history, 1, wx.EXPAND | wx.ALL, 8)

        vbox.Add(
            wx.StaticText(
                panel,
                label="Fonti e link. Per aprirne una: pulsante Apri fonte, poi Invio. Alt+F.",
            ),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        self.lst_links = wx.ListBox(panel, style=wx.LB_SINGLE)
        try:
            self.lst_links.SetName("Fonti e link")
        except Exception:
            pass
        self._links = []
        vbox.Add(self.lst_links, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.btn_open_link = wx.Button(panel, label="Apri &fonte")
        self.btn_open_link.Bind(wx.EVT_BUTTON, self.on_open_link)
        vbox.Add(self.btn_open_link, 0, wx.LEFT | wx.BOTTOM, 8)

        vbox.Add(wx.StaticText(panel, label="La tua &domanda"), 0, wx.LEFT | wx.RIGHT, 8)
        self.txt_q = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER | wx.TE_RICH2,
        )
        self.txt_q.SetMinSize((-1, 72))
        try:
            self.txt_q.SetName("La tua domanda")
        except Exception:
            pass
        # Invio lo gestisce on_char_hook. Qui non si lega TEXT_ENTER:
        # su Windows anche Shift+Invio lo farebbe scattare, e la domanda partirebbe.
        vbox.Add(self.txt_q, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vbox.Add(
            wx.StaticText(
                panel,
                label="Allegati. Alt+A apre l'elenco, i più recenti in cima.",
            ),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        self.lst_attach = wx.ListBox(panel, style=wx.LB_SINGLE)
        try:
            self.lst_attach.SetName("Allegati")
        except Exception:
            pass
        vbox.Add(self.lst_attach, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        row_att = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_attach = wx.Button(panel, label="&Allega file…")
        self.btn_attach.Bind(wx.EVT_BUTTON, self.on_attach)
        row_att.Add(self.btn_attach, 0, wx.ALL, 5)
        self.btn_detach = wx.Button(panel, label="Tog&li allegato")
        self.btn_detach.Bind(wx.EVT_BUTTON, self.on_detach)
        row_att.Add(self.btn_detach, 0, wx.ALL, 5)
        vbox.Add(row_att, 0, wx.LEFT | wx.RIGHT, 8)

        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_send = wx.Button(panel, label="&Invia")
        self.btn_send.Bind(wx.EVT_BUTTON, self.on_send)
        row1.Add(self.btn_send, 0, wx.ALL, 5)
        self.chk_web = wx.CheckBox(panel, label="Consulta anche il &web")
        self.chk_web.SetValue(_gemini_chat_use_web())
        self.chk_web.Bind(wx.EVT_CHECKBOX, self.on_web_toggle)
        row1.Add(self.chk_web, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        vbox.Add(row1, 0, wx.LEFT | wx.RIGHT, 8)

        vbox.Add(wx.StaticText(panel, label="Domande pronte"), 0, wx.LEFT | wx.RIGHT, 8)
        self.lst_suggest = wx.ListBox(panel, style=wx.LB_SINGLE)
        try:
            self.lst_suggest.SetName("Domande pronte")
        except Exception:
            pass
        for q in rtad_chat.suggested_questions(session.get("kind")):
            self.lst_suggest.Append(q)
        if self.lst_suggest.GetCount():
            self.lst_suggest.SetSelection(0)
        vbox.Add(self.lst_suggest, 0, wx.EXPAND | wx.ALL, 8)
        self.lst_suggest.Bind(wx.EVT_LISTBOX_DCLICK, self.on_send_suggested)

        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_suggested = wx.Button(panel, label="Invia domanda &pronta")
        self.btn_suggested.Bind(wx.EVT_BUTTON, self.on_send_suggested)
        row2.Add(self.btn_suggested, 0, wx.ALL, 5)
        self.btn_copy = wx.Button(panel, label="&Copia")
        self.btn_copy.Bind(wx.EVT_BUTTON, self.on_copy)
        row2.Add(self.btn_copy, 0, wx.ALL, 5)
        self.btn_save = wx.Button(panel, label="&Salva…")
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        row2.Add(self.btn_save, 0, wx.ALL, 5)
        self.btn_print = wx.Button(panel, label="S&tampa…")
        self.btn_print.Bind(wx.EVT_BUTTON, self.on_print)
        row2.Add(self.btn_print, 0, wx.ALL, 5)
        vbox.Add(row2, 0, wx.ALIGN_CENTER)

        row3 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_new = wx.Button(panel, label="&Nuova conversazione")
        self.btn_new.Bind(wx.EVT_BUTTON, self.on_new)
        row3.Add(self.btn_new, 0, wx.ALL, 5)
        self.btn_hist = wx.Button(panel, label="Cronolo&gia…")
        self.btn_hist.Bind(wx.EVT_BUTTON, self.on_history)
        row3.Add(self.btn_hist, 0, wx.ALL, 5)
        btn_close = wx.Button(panel, label="Chiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        row3.Add(btn_close, 0, wx.ALL, 5)
        vbox.Add(row3, 0, wx.ALIGN_CENTER | wx.BOTTOM, 6)

        panel.SetSizer(vbox)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_CLOSE, self._on_close_frame)
        self._render()
        n_links = len(getattr(self, "_links", []) or [])
        link_note = ""
        if n_links:
            voci = "fonte" if n_links == 1 else "fonti"
            link_note = (
                f" {n_links} {voci}. "
                "Per aprirne una: Tab fino al pulsante Apri fonte, poi Invio. "
                "Alt+F fa lo stesso, anche se sei sull'elenco."
            )
        heard = (notice + " ") if notice else ""
        if resumed and (session.get("turns") or []):
            opening = (
                heard
                + f"Conversazione precedente caricata, {title_name}. "
                "Puoi continuare o iniziarne una nuova. "
                "Alt+A apre l'elenco dei file, i più recenti in cima. "
                "Frecce per leggere."
                + link_note
            )
        elif (session.get("kind") == "free") and not (session.get("path") or ""):
            opening = (
                "Conversazione con Gemini, senza un file di partenza. "
                "Scrivi la domanda e premi Invio. Shift+Invio va a capo. "
                "Alt+A apre l'elenco dei file, i più recenti in cima. Esc annulla."
            )
        else:
            opening = (
                heard
                + f"Conversazione con Gemini su {title_name}. "
                "Scrivi la domanda e premi Invio. Shift+Invio va a capo. "
                "Alt+A apre l'elenco dei file, i più recenti in cima. Esc annulla."
            )
        if notice:
            self.txt_history.SetFocus()
            try:
                self.txt_history.SetInsertionPoint(0)
                self.txt_history.ShowPosition(0)
            except Exception:
                pass
        elif resumed and (session.get("turns") or []):
            self.txt_history.SetFocus()
        else:
            self.txt_q.SetFocus()
        # Il menu contestuale, chiudendosi, tronca ui.message se parte subito.
        _announce(opening, delay_ms=700)

    def _render(self):
        text = ""
        try:
            text = rtad_chat.transcript(self.session)
        except Exception:
            text = ""
        live = getattr(self, "_live", None)
        if live:
            question, body = live
            if not (self.session.get("turns") or []):
                text = (text or "").replace("(Nessuno scambio ancora.)", "")
            text = (text or "").rstrip() + f"\n\nTu:\n{question}\n\nGemini:\n{body}\n"
        notice = ((self.session or {}).get("report_notice") or "").strip()
        if notice and not (text or "").startswith(notice):
            text = notice + "\n\n" + (text or "")
        self.txt_history.SetValue(text or "")
        idx = (text or "").rfind("\nGemini:\n")
        if idx < 0:
            idx = 0
        try:
            self.txt_history.SetInsertionPoint(idx)
            self.txt_history.ShowPosition(idx)
        except Exception:
            pass
        self._refresh_links(text or "")
        self._refresh_attach_list()

    def _refresh_links(self, text):
        try:
            self._links = rtad_chat.extract_links(text)
        except Exception:
            self._links = []
        self.lst_links.Clear()
        if not self._links:
            self.lst_links.Append("Ancora nessuna fonte.")
        else:
            for item in self._links:
                self.lst_links.Append(rtad_chat.link_label(item))
        self.lst_links.SetSelection(0)

    def on_open_link(self, event=None):
        if not self._links:
            speak_accessible("Ancora nessuna fonte.")
            return
        idx = self.lst_links.GetSelection()
        if idx == wx.NOT_FOUND or idx >= len(self._links):
            speak_accessible("Nessun link selezionato.")
            return
        item = self._links[idx]
        url = (item.get("url") or "").strip()
        if not url:
            speak_accessible("Questo link non ha un indirizzo.")
            return
        try:
            webbrowser.open(url)
        except Exception as exc:
            speak_accessible(f"Impossibile aprire il browser: {exc}")
            return
        speak_accessible(f"Apro nel browser: {rtad_chat.link_label(item)}")

    def _set_busy(self, busy):
        self._busy = busy
        for ctrl in (
            self.btn_send,
            self.btn_suggested,
            self.txt_q,
            self.lst_suggest,
            self.lst_links,
            self.btn_open_link,
            self.btn_new,
            self.btn_hist,
            self.btn_attach,
            self.btn_detach,
            self.lst_attach,
            self.chk_web,
        ):
            ctrl.Enable(not busy)
        if busy:
            self.lbl_status.SetLabel("Gemini sta rispondendo. Esc annulla.")
        else:
            self.lbl_status.SetLabel(
                "Domande ed estratti vanno a Google. La cronologia resta sul PC. "
                "Esc chiude. Durante una richiesta, Esc annulla."
            )

    def on_web_toggle(self, event=None):
        enabled = bool(self.chk_web.GetValue())
        _gemini_chat_set_use_web(enabled)
        if enabled:
            speak_accessible("Consultazione web accesa.")
        else:
            speak_accessible("Consultazione web spenta.")

    def _refresh_attach_list(self):
        if not hasattr(self, "lst_attach"):
            return
        atts = (self.session or {}).get("attachments") or []
        self.lst_attach.Clear()
        shown = 0
        for att in atts:
            if not isinstance(att, dict):
                continue
            name = att.get("title") or "allegato"
            kind = ""
            try:
                kind = rtad_chat._kind_it(att.get("kind") or "")
            except Exception:
                kind = att.get("kind") or ""
            self.lst_attach.Append(f"{name} ({kind})" if kind else name)
            shown += 1
        if not shown:
            self.lst_attach.Append("Nessun allegato presente.")
        self.lst_attach.SetSelection(0)

    def _show_notice(self, text):
        """Stessa frase a schermo e in voce."""
        text = (text or "").strip()
        if not text:
            return
        try:
            self.lbl_status.SetLabel(text)
            self.lbl_status.Wrap(max(200, self.GetClientSize().width - 24))
        except Exception:
            pass
        speak_accessible(text)

    def _fill_suggestions(self):
        kind = (self.session or {}).get("kind") or "document"
        atts = (self.session or {}).get("attachments") or []
        if kind == "free" and atts:
            kinds = {a.get("kind") for a in atts if isinstance(a, dict)}
            if kinds == {"image"}:
                kind = "image"
            else:
                kind = "document"
        self.lst_suggest.Clear()
        for q in rtad_chat.suggested_questions(kind):
            self.lst_suggest.Append(q)
        if self.lst_suggest.GetCount():
            self.lst_suggest.SetSelection(0)

    def on_attach(self, event=None):
        if self._busy:
            return
        if rtad_attach_dialog is None:
            speak_accessible("Non riesco ad aprire l'elenco dei file.")
            return
        try:
            paths = rtad_attach_dialog.choose_attachment_paths(
                self,
                config_dir=CONFIG_DIR,
                hint_path=(self.session.get("path") or ""),
                speak=lambda text: speak_accessible(text, delay_ms=0),
                session=self.session,
            )
        except Exception as exc:
            logging.debug(f"Chat: scelta allegati: {exc}")
            speak_accessible("Non riesco ad aprire l'elenco dei file.")
            return
        if not paths:
            speak_accessible("Nessun file allegato.")
            return
        added = []
        refused = []
        for path in paths:
            try:
                ok, msg = rtad_chat.add_attachment(self.session, path)
            except Exception as exc:
                ok, msg = False, str(exc)
            if ok:
                added.append(msg)
            else:
                refused.append(msg)
        try:
            rtad_chat.save_current(CONFIG_DIR, self.session)
        except Exception as exc:
            logging.debug(f"Chat: allegati non salvati: {exc}")
        title = (self.session.get("title") or "").strip()
        if title:
            self.SetTitle(f"Chiedi a Gemini — {title}")
        self._fill_suggestions()
        self._render()
        n_scelti = len(paths)
        n_ok = len(added)
        if n_ok == n_scelti and n_ok:
            msg = f"Allegati {n_ok}." if n_ok != 1 else f"Allegato: {added[0]}."
        elif n_ok and refused:
            msg = (
                f"Allegati {n_ok} su {n_scelti}. Non entrati: "
                + " ".join(refused)
            )
        elif refused:
            msg = f"Nessuno allegato, su {n_scelti}. " + " ".join(refused)
        else:
            msg = "Nessun file allegato."
        self._show_notice(msg)
        self.txt_q.SetFocus()

    def on_detach(self, event=None):
        if self._busy:
            return
        if not (self.session.get("attachments") or []):
            self._show_notice("Nessun allegato presente.")
            return
        idx = self.lst_attach.GetSelection()
        if idx == wx.NOT_FOUND:
            self._show_notice("Scegli un allegato da togliere.")
            return
        try:
            name = rtad_chat.remove_attachment(self.session, idx)
        except Exception as exc:
            self._show_notice(f"Non posso togliere l'allegato: {exc}")
            return
        if not name:
            self._show_notice("Allegato non trovato.")
            return
        try:
            rtad_chat.save_current(CONFIG_DIR, self.session)
        except Exception:
            pass
        self._fill_suggestions()
        self._render()
        msg = f"Allegato tolto: {name}"
        if not (self.session.get("attachments") or []):
            msg += " Nessun allegato presente."
        self._show_notice(msg)

    def on_send_suggested(self, event=None):
        idx = self.lst_suggest.GetSelection()
        if idx == wx.NOT_FOUND:
            speak_accessible("Scegli una domanda pronta.")
            return
        self.on_send(question=self.lst_suggest.GetString(idx))

    def on_send(self, event=None, question=None):
        if self._busy:
            if (self.txt_q.GetValue() or "").strip():
                speak_accessible("Richiesta già in corso. Esc annulla.")
            return
        if question is None:
            question = self.txt_q.GetValue() or ""
        question = question.strip()
        if not question:
            speak_accessible("Scrivi una domanda.")
            self.txt_q.SetFocus()
            return
        key = ""
        try:
            key = load_gemini_api_key()
        except Exception:
            key = ""
        if key and rtad_ocr is not None:
            try:
                rtad_ocr.set_gemini_api_key(key)
            except Exception:
                pass
        self._abort = False
        self._gen += 1
        gen = self._gen
        use_web = bool(self.chk_web.GetValue())
        session = self.session
        self._set_busy(True)
        self.txt_q.SetValue("")
        self._live = (question, "In attesa della risposta…")
        self._render()
        speak_accessible("Gemini sta rispondendo. Esc annulla.")

        def _work():
            try:
                rtad_chat.refresh_context(session)
            except Exception as exc:
                logging.debug(f"Chat: rilettura file non riuscita: {exc}")
            try:
                result = rtad_chat.ask(
                    session,
                    question,
                    use_web=use_web,
                    should_abort=lambda: self._abort,
                )
            except Exception as exc:
                result = {
                    "ok": False,
                    "text": "",
                    "model": "",
                    "error": str(exc),
                    "aborted": False,
                }
            wx.CallAfter(self._on_answer, gen, question, result)

        threading.Thread(target=_work, daemon=True).start()

    def _on_answer(self, gen, question, result):
        if gen != self._gen:
            return
        result = result or {}
        if result.get("aborted") or self._abort:
            if question:
                self._live = (question, "Richiesta annullata.")
            else:
                self._live = None
            self._set_busy(False)
            self.lbl_status.SetLabel("Richiesta annullata.")
            self._render()
            speak_accessible("Richiesta annullata.")
            self.txt_q.SetFocus()
            return
        if not result.get("ok"):
            err = (result.get("error") or "Gemini non ha risposto.").strip()
            self._live = (question, err)
            self._set_busy(False)
            shown = err if len(err) <= 220 else err[:220] + "…"
            self.lbl_status.SetLabel(shown)
            self._render()
            self.txt_history.SetFocus()
            speak_accessible(err)
            self.txt_q.SetValue(question)
            return
        self._live = None
        self._set_busy(False)
        try:
            rtad_chat.append_exchange(
                self.session,
                question,
                result.get("text") or "",
                result.get("model") or "",
            )
            rtad_chat.save_current(CONFIG_DIR, self.session)
        except Exception as exc:
            logging.warning(f"Chat: salvataggio cronologia non riuscito: {exc}")
            speak_accessible(f"Risposta ricevuta, cronologia non salvata: {exc}")
        title = (self.session.get("title") or "").strip()
        if title:
            self.SetTitle(f"Chiedi a Gemini — {title}")
        self._render()
        self.txt_history.SetFocus()
        speak_accessible("Risposta pronta. Usa le frecce per leggere.")

    def on_new(self, event=None):
        if self._busy:
            return
        if self.session.get("turns"):
            ask = wx.MessageDialog(
                self,
                "Archivio questa conversazione e ne apro una vuota?",
                "Nuova conversazione",
                wx.YES_NO | wx.ICON_INFORMATION,
            )
            try:
                if ask.ShowModal() != wx.ID_YES:
                    speak_accessible("Nuova conversazione annullata.")
                    return
            finally:
                ask.Destroy()
            try:
                rtad_chat.archive_current(CONFIG_DIR, self.session)
            except Exception as exc:
                speak_accessible(f"Archivio non riuscito: {exc}")
                return
        self._live = None
        for att in list(self.session.get("attachments") or []):
            try:
                rtad_chat._discard_media_cache(att)
            except Exception:
                pass
        self.session["attachments"] = []
        if (self.session.get("kind") == "free") and not (self.session.get("path") or ""):
            self.session["title"] = "Conversazione"
            self.SetTitle("Chiedi a Gemini — Conversazione")
        try:
            rtad_chat.save_current(CONFIG_DIR, self.session)
        except Exception as exc:
            logging.debug(f"Chat: nuova conversazione non salvata: {exc}")
        self._fill_suggestions()
        self._render()
        self.txt_q.SetFocus()
        speak_accessible("Nuova conversazione. Scrivi la domanda.")

    def on_history(self, event=None):
        if self._busy:
            return
        try:
            rows = rtad_chat.list_saved(
                CONFIG_DIR, self.session.get("path") or "", self.session
            )
        except Exception as exc:
            speak_accessible(f"Cronologia non disponibile: {exc}")
            return
        rows = [r for r in rows if r]
        if not rows:
            speak_accessible("Nessuna conversazione salvata per questo file.")
            return
        dlg = GeminiChatHistoryDialog(self, rows)
        try:
            if dlg.ShowModal() != wx.ID_OK or not dlg.choice:
                return
            action, row = dlg.choice
        finally:
            dlg.Destroy()
        if action == "delete":
            self._delete_saved_row(row)
            return
        if row.get("current"):
            speak_accessible("Questa è già la conversazione aperta.")
            self.txt_history.SetFocus()
            return
        try:
            if self.session.get("turns"):
                rtad_chat.archive_current(CONFIG_DIR, self.session)
            loaded = rtad_chat.load_saved(
                row.get("path") or "",
                struct=self.struct,
                displayed=self.displayed,
                prior_report=self.prior_report,
            )
        except Exception as exc:
            speak_accessible(f"Apertura non riuscita: {exc}")
            return
        if not loaded:
            speak_accessible("Conversazione non leggibile.")
            return
        self.session = loaded
        try:
            rtad_chat.save_current(CONFIG_DIR, self.session)
        except Exception as exc:
            logging.warning(f"Chat: non posso rendere corrente l'archivio: {exc}")
        self._render()
        self.txt_history.SetFocus()
        speak_accessible("Conversazione aperta. Frecce per leggere.")

    def _delete_saved_row(self, row):
        path_json = row.get("path") or ""
        try:
            if row.get("current"):
                self.session["turns"] = []
                rtad_chat.delete_saved(path_json)
            else:
                rtad_chat.delete_saved(path_json)
        except Exception as exc:
            speak_accessible(f"Eliminazione non riuscita: {exc}")
            return
        self._render()
        speak_accessible("Conversazione eliminata.")

    def on_copy(self, event=None):
        text = ""
        try:
            text = rtad_chat.transcript(self.session)
        except Exception:
            text = self.txt_history.GetValue() or ""
        if not text.strip():
            speak_accessible("Niente da copiare.")
            return
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
            speak_accessible("Conversazione copiata negli appunti.")
        else:
            speak_accessible("Impossibile aprire gli appunti.")

    def on_save(self, event=None):
        text = ""
        try:
            text = rtad_chat.transcript(self.session)
        except Exception:
            text = ""
        if not text.strip():
            speak_accessible("Niente da salvare.")
            return
        ref = self.session.get("path") or ""
        title = (self.session.get("title") or "").strip()
        if title and not os.path.splitext(title)[0].lower().startswith("rtad_media_"):
            stem = _safe_filename_stem(title, fallback="conversazione")
        else:
            stem = report_save_stem_for_path(ref) or "conversazione"
        folder = os.path.dirname(ref) if ref else ""
        if folder and os.path.isdir(folder) and not _looks_like_temp_dir(folder):
            default_dir = folder
        else:
            default_dir = load_last_media_report_dir() or os.path.expanduser("~")
        dlg = wx.FileDialog(
            self,
            "Salva conversazione",
            defaultDir=default_dir,
            defaultFile=f"{stem}.chat.txt",
            wildcard="Testo (*.txt)|*.txt|Tutti i file (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            dest = dlg.GetPath()
        finally:
            dlg.Destroy()
        try:
            with open(dest, "w", encoding="utf-8") as handle:
                handle.write(text)
            speak_accessible(f"Conversazione salvata: {os.path.basename(dest)}")
        except Exception as exc:
            speak_accessible(f"Salvataggio non riuscito: {exc}")

    def on_print(self, event=None):
        text = ""
        try:
            text = rtad_chat.transcript(self.session)
        except Exception:
            text = ""
        if not text.strip():
            speak_accessible("Niente da stampare.")
            return
        temp_print_path = os.path.join(CONFIG_DIR, "stampa_chat_gemini.txt")
        try:
            with open(temp_print_path, "w", encoding="utf-8") as handle:
                handle.write(
                    "Data stampa: "
                    f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
                )
                handle.write(text)
            notepad_path = os.path.join(
                os.environ.get("WINDIR", "C:\\Windows"), "System32", "notepad.exe"
            )
            if not os.path.exists(notepad_path):
                notepad_path = "notepad.exe"
            subprocess.Popen([notepad_path, "/p", temp_print_path])
            speak_accessible(
                "Conversazione inviata alla stampante predefinita. "
                "Puoi scegliere «Microsoft Print to PDF» se serve un PDF."
            )
        except Exception as exc:
            logging.error(f"Stampa conversazione fallita: {exc}")
            speak_accessible(
                "Impossibile stampare. Assicurati di avere una stampante configurata."
            )

    def _on_close_frame(self, event):
        self._abort = True
        self._gen += 1
        event.Skip()

    def on_char_hook(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            if self._busy:
                self._abort = True
                self._gen += 1
                question = self._live[0] if self._live else ""
                self._live = (question, "Richiesta annullata.") if question else None
                self._set_busy(False)
                self.lbl_status.SetLabel("Richiesta annullata.")
                self._render()
                speak_accessible("Richiesta annullata.")
                self.txt_q.SetFocus()
                return
            self.Close()
            return
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            focused = self.FindFocus()
            if focused is self.txt_q and not event.AltDown() and not event.ControlDown():
                if event.ShiftDown():
                    self.txt_q.WriteText("\n")
                    return
                self.on_send()
                return
        event.Skip()


class ImageInfoFrame(wx.Frame):
    """Finestra descrizione / etichette / scheda tecnica immagine (1.6.3).

    parent=None di proposito: resta aperta e consultabile anche se si
    iconizza/cambia finestra; si chiude solo con Chiudi o ESC.

    source_path: file originale per stem/cartella «Salva testo» (es. PDF
    da cui è stata estratta l'immagine temp in image_path).
    """

    def __init__(
        self,
        parent,
        title,
        body_text,
        image_path="",
        *,
        source_path="",
        action_label="",
        action_cb=None,
        after_close_cb=None,
    ):
        # Ignora parent: top-level indipendente (non si chiude col dialogo padre)
        super(ImageInfoFrame, self).__init__(
            None,
            title=title,
            size=(720, 520),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.image_path = image_path or ""
        self.source_path = source_path or ""
        self.body_text = wrap_report_text(body_text or "")
        self._action_cb = action_cb
        self._after_close_cb = after_close_cb
        self._after_close_done = False

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        label_path = self._save_ref_path() or self.image_path
        lbl = wx.StaticText(
            panel,
            label=os.path.basename(label_path) if label_path else "Immagine",
        )
        vbox.Add(lbl, 0, wx.ALL, 8)

        self.txt_display = wx.TextCtrl(
            panel,
            value=self.body_text,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        self.lbl_translate = wx.StaticText(panel, label="")
        try:
            self.lbl_translate.SetName("Stato traduzione")
        except Exception:
            pass
        vbox.Add(self.lbl_translate, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_copy = wx.Button(panel, label="&Copia testo")
        btn_copy.Bind(wx.EVT_BUTTON, self.on_copy)
        hbox.Add(btn_copy, 0, wx.ALL, 5)
        btn_save = wx.Button(panel, label="&Salva testo…")
        btn_save.Bind(wx.EVT_BUTTON, self.on_save_text)
        hbox.Add(btn_save, 0, wx.ALL, 5)
        btn_print = wx.Button(panel, label="S&tampa testo…")
        btn_print.Bind(wx.EVT_BUTTON, self.on_print_text)
        hbox.Add(btn_print, 0, wx.ALL, 5)
        self.btn_translate = None
        if rtad_translate is not None:
            self.btn_translate = wx.Button(panel, label="Trad&uci…")
            self.btn_translate.Bind(wx.EVT_BUTTON, self.on_translate)
            hbox.Add(self.btn_translate, 0, wx.ALL, 5)
        file_ext = os.path.splitext(self.image_path or "")[1].lower()
        if rtad_chat is not None and file_ext in IMG_EXTS + MEDIA_EXTS:
            btn_chat = wx.Button(panel, label="Chiedi a &Gemini…")
            btn_chat.Bind(wx.EVT_BUTTON, self.on_ask_gemini)
            hbox.Add(btn_chat, 0, wx.ALL, 5)
        if action_label and callable(action_cb):
            btn_action = wx.Button(panel, label=action_label)
            btn_action.Bind(wx.EVT_BUTTON, self._on_action)
            hbox.Add(btn_action, 0, wx.ALL, 5)
        btn_close = wx.Button(panel, label="Chiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        hbox.Add(btn_close, 0, wx.ALL, 5)
        vbox.Add(hbox, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        panel.SetSizer(vbox)
        self.Centre()
        self.txt_display.SetFocus()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_CLOSE, self._on_close_frame)
        _trad = " Alt+U: traduci." if rtad_translate is not None else ""
        rtad_speak(f"{title}. Usa le frecce per leggere.{_trad}")

    def _save_ref_path(self):
        """Percorso per stem/cartella: PDF/originale se valido, altrimenti image_path."""
        src = (self.source_path or "").strip()
        if src and (os.path.isfile(src) or os.path.isdir(src)):
            return src
        return (self.image_path or "").strip()

    def _on_action(self, event=None):
        self._after_close_cb = None
        self._after_close_done = True
        cb = self._action_cb
        if callable(cb):
            try:
                cb()
            except Exception:
                pass

    def _run_after_close(self):
        if self._after_close_done:
            return
        self._after_close_done = True
        cb = self._after_close_cb
        self._after_close_cb = None
        if callable(cb):
            try:
                cb()
            except Exception:
                pass

    def _on_close_frame(self, event):
        if callable(self._after_close_cb):
            wx.CallLater(150, self._run_after_close)
        event.Skip()

    def on_translate(self, event=None):
        start_frame_translation(self, rtad_speak)

    def on_ask_gemini(self, event=None):
        body = self.txt_display.GetValue() or self.body_text
        ext = os.path.splitext(self.image_path or "")[1].lower()
        if ext in IMG_EXTS:
            open_gemini_chat(
                "image",
                self.image_path,
                prior_report=body,
                source_path=self.source_path,
                parent=self,
            )
            return
        open_gemini_chat(
            "document",
            self.image_path,
            struct={
                "body": body,
                "plain": body,
                "outline": [],
                "message": "Report audio/video già prodotto in RTAD.",
            },
            displayed=body,
            parent=self,
        )

    def on_copy(self, event=None):
        text = self.txt_display.GetValue()
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
            rtad_speak("Testo copiato negli appunti.")
        else:
            rtad_speak("Impossibile aprire gli appunti.")

    def on_save_text(self, event=None):
        text = self.txt_display.GetValue() or ""
        if not text.strip():
            rtad_speak("Niente da salvare.")
            return
        ref = self._save_ref_path()
        stem = report_save_stem_for_path(ref)
        # Locale: cartella del PDF/media originale; temp → ultima cartella scelta
        default_dir = ""
        if ref:
            cand = os.path.dirname(os.path.abspath(ref)) if os.path.isfile(ref) else (
                os.path.abspath(ref) if os.path.isdir(ref) else ""
            )
            if cand and os.path.isdir(cand) and not _looks_like_temp_dir(cand):
                default_dir = cand
        if not default_dir:
            default_dir = load_last_media_report_dir() or os.path.expanduser("~")
        dlg = wx.FileDialog(
            self,
            "Salva testo report",
            defaultDir=default_dir,
            defaultFile=f"{stem}.rtad.txt",
            wildcard="Testo (*.txt)|*.txt|Tutti i file (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            path = dlg.GetPath()
        finally:
            dlg.Destroy()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            save_last_media_report_dir(path)
            rtad_speak(f"Testo salvato: {os.path.basename(path)}")
        except Exception as e:
            rtad_speak(f"Salvataggio non riuscito: {e}")

    def on_print_text(self, event=None):
        """Stampa il report (Notepad /p → stampante predefinita o Print to PDF)."""
        text = self.txt_display.GetValue() or ""
        if not text.strip():
            rtad_speak("Niente da stampare.")
            return
        ref = self._save_ref_path()
        name = os.path.basename(ref) if ref else "report"
        temp_print_path = os.path.join(CONFIG_DIR, "stampa_report_immagine.txt")
        try:
            with open(temp_print_path, "w", encoding="utf-8") as f:
                f.write(f"=== {APP_TITLE} — Report immagine ===\n")
                f.write(f"Sorgente: {name}\n")
                f.write(
                    f"Data stampa: "
                    f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
                )
                f.write(text)
            notepad_path = os.path.join(
                os.environ.get("WINDIR", "C:\\Windows"), "System32", "notepad.exe"
            )
            if not os.path.exists(notepad_path):
                notepad_path = "notepad.exe"
            subprocess.Popen([notepad_path, "/p", temp_print_path])
            rtad_speak(
                "Testo inviato alla stampante predefinita. "
                "Puoi scegliere «Microsoft Print to PDF» se serve un PDF."
            )
        except Exception as e:
            logging.error(f"Stampa report immagine fallita: {e}")
            rtad_speak(
                "Impossibile stampare. Assicurati di avere una stampante configurata."
            )

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
        else:
            event.Skip()


class DocumentStructureFrame(wx.Frame):
    """Lettore documenti RTAD: sommario, link, testo, cerca e navigazione titoli."""

    _HEADING_MARK_RE = re.compile(r"\[H([1-9])\]\s*([^\n]*)")

    def __init__(self, parent, file_path, struct):
        name = os.path.basename(file_path) if file_path else "Documento"
        super(DocumentStructureFrame, self).__init__(
            None,
            title=f"Lettore documento — {name}",
            size=(780, 700),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.file_path = file_path or ""
        self.struct = struct or {}
        self.outline = list(self.struct.get("outline") or [])
        self.links = list(self.struct.get("links") or [])
        self._find_needle = ""
        self._last_focus_ctrl = None
        self._saved_insert = 0
        self._ignore_enter_until = 0.0
        report = ""
        if rtad_docstruct is not None:
            try:
                report = rtad_docstruct.format_structure_report(self.struct)
            except Exception:
                report = (self.struct.get("body") or self.struct.get("plain") or "")
        else:
            report = (self.struct.get("body") or self.struct.get("plain") or "")
        report = wrap_report_text(report)

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        summary = (self.struct.get("message") or "").strip() or "Lettura documento."
        self.lbl_summary = wx.StaticText(panel, label=summary)
        vbox.Add(self.lbl_summary, 0, wx.ALL | wx.EXPAND, 8)

        if self.outline:
            vbox.Add(
                wx.StaticText(panel, label="S&ommario / titoli"),
                0,
                wx.LEFT | wx.RIGHT,
                8,
            )
            self.lst_outline = wx.ListBox(panel, style=wx.LB_SINGLE)
            try:
                self.lst_outline.SetName("Sommario titoli")
            except Exception:
                pass
            for i, item in enumerate(self.outline, 1):
                level = int(item.get("level") or 1)
                indent = "  " * max(0, level - 1)
                title = item.get("title") or ""
                page = item.get("page")
                page_bit = f" — pag. PDF {int(page)}" if page else ""
                self.lst_outline.Append(
                    f"{i}. {indent}[H{level}] {title}{page_bit}"
                )
            vbox.Add(self.lst_outline, 0, wx.EXPAND | wx.ALL, 8)
            self.lst_outline.Bind(wx.EVT_LISTBOX_DCLICK, self.on_outline_activate)
        else:
            self.lst_outline = None

        if self.links:
            vbox.Add(
                wx.StaticText(panel, label="Lin&k nel documento"),
                0,
                wx.LEFT | wx.RIGHT,
                8,
            )
            self.lst_links = wx.ListBox(panel, style=wx.LB_SINGLE)
            for i, item in enumerate(self.links, 1):
                self.lst_links.Append(
                    f"{i}. {item.get('text') or ''} -> {item.get('href') or ''}"
                )
            vbox.Add(self.lst_links, 0, wx.EXPAND | wx.ALL, 8)
            self.lst_links.Bind(wx.EVT_LISTBOX_DCLICK, self.on_link_activate)
        else:
            self.lst_links = None

        vbox.Add(
            wx.StaticText(panel, label="&Testo (con marcatori titolo [H1]…)"),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        self.txt_display = wx.TextCtrl(
            panel,
            value=report,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        try:
            self.txt_display.SetName("Testo del documento")
        except Exception:
            pass
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        self.lbl_translate = wx.StaticText(panel, label="")
        try:
            self.lbl_translate.SetName("Stato traduzione")
        except Exception:
            pass
        vbox.Add(self.lbl_translate, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)

        self._pending_reading_pos = None
        self._reading_sentence = ""
        self._reading_rows = []
        self.lbl_reading = None
        self.lst_reading = None
        self.btn_mark_save = None
        if rtad_reading_mark is not None:
            idle = (
                rtad_reading_mark.MSG_NONE
                if (self.file_path or "").strip()
                else rtad_reading_mark.MSG_NOFILE
            )
            self.lbl_reading = wx.StaticText(panel, label=idle)
            try:
                self.lbl_reading.SetName("Segnalibro di lettura")
            except Exception:
                pass
            vbox.Add(self.lbl_reading, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
            vbox.Add(
                wx.StaticText(panel, label=rtad_reading_mark.HINT),
                0,
                wx.LEFT | wx.RIGHT | wx.EXPAND,
                8,
            )
            vbox.Add(
                wx.StaticText(panel, label="Punti di lettura"),
                0,
                wx.LEFT | wx.RIGHT,
                8,
            )
            self.lst_reading = wx.ListBox(panel, style=wx.LB_SINGLE)
            try:
                self.lst_reading.SetName("Punti di lettura")
                self.lst_reading.SetMinSize((-1, 80))
            except Exception:
                pass
            self.lst_reading.Bind(wx.EVT_LISTBOX_DCLICK, self.on_reading_mark_activate)
            vbox.Add(self.lst_reading, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            hbox_mark = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_mark_save = wx.Button(panel, label="Segna punto di lettura")
            self.btn_mark_save.Bind(wx.EVT_BUTTON, self.on_save_reading_mark)
            hbox_mark.Add(self.btn_mark_save, 0, wx.ALL, 5)
            btn_mark_go = wx.Button(panel, label="Riprendi ultimo punto")
            btn_mark_go.Bind(wx.EVT_BUTTON, self.on_resume_reading_mark)
            hbox_mark.Add(btn_mark_go, 0, wx.ALL, 5)
            btn_mark_del = wx.Button(panel, label="Elimina punto di lettura")
            btn_mark_del.Bind(wx.EVT_BUTTON, self.on_delete_reading_mark)
            hbox_mark.Add(btn_mark_del, 0, wx.ALL, 5)
            can_mark = bool((self.file_path or "").strip())
            self.btn_mark_save.Enable(can_mark)
            btn_mark_go.Enable(can_mark)
            btn_mark_del.Enable(can_mark)
            vbox.Add(hbox_mark, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 5)
            self._reload_reading_list(report)
            self._arm_reading_resume(report)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        if self.links:
            btn_open_link = wx.Button(panel, label="Apri &link selezionato")
            btn_open_link.Bind(wx.EVT_BUTTON, self.on_link_activate)
            hbox.Add(btn_open_link, 0, wx.ALL, 5)
        btn_find = wx.Button(panel, label="Ce&rca nel testo…")
        btn_find.Bind(wx.EVT_BUTTON, self.on_find)
        hbox.Add(btn_find, 0, wx.ALL, 5)
        btn_copy = wx.Button(panel, label="&Copia testo")
        btn_copy.Bind(wx.EVT_BUTTON, self.on_copy)
        hbox.Add(btn_copy, 0, wx.ALL, 5)
        btn_save = wx.Button(panel, label="&Salva testo…")
        btn_save.Bind(wx.EVT_BUTTON, self.on_save_text)
        hbox.Add(btn_save, 0, wx.ALL, 5)
        self.btn_translate = None
        if rtad_translate is not None:
            self.btn_translate = wx.Button(panel, label="Trad&uci…")
            self.btn_translate.Bind(wx.EVT_BUTTON, self.on_translate)
            hbox.Add(self.btn_translate, 0, wx.ALL, 5)
        if rtad_chat is not None and self.file_path:
            btn_chat = wx.Button(panel, label="Chiedi a &Gemini…")
            btn_chat.Bind(wx.EVT_BUTTON, self.on_ask_gemini)
            hbox.Add(btn_chat, 0, wx.ALL, 5)
        if self.file_path and os.path.isfile(self.file_path):
            btn_ext = wx.Button(panel, label="Apri file &esterno")
            btn_ext.Bind(wx.EVT_BUTTON, self.on_open_external)
            hbox.Add(btn_ext, 0, wx.ALL, 5)
        btn_close = wx.Button(panel, label="Chiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        hbox.Add(btn_close, 0, wx.ALL, 5)
        vbox.Add(hbox, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        panel.SetSizer(vbox)
        if self.lbl_reading is not None:
            try:
                self.lbl_reading.Wrap(720)
            except Exception:
                pass
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_ACTIVATE, self._on_reader_activate)
        self.Bind(wx.EVT_ICONIZE, self._on_reader_iconize)
        for ctrl in (
            self.lst_outline,
            self.lst_links,
            self.lst_reading,
            self.txt_display,
        ):
            if ctrl is not None:
                ctrl.Bind(wx.EVT_SET_FOCUS, self._on_reader_child_focus)
        resume_lead = ""
        if self._pending_reading_pos is not None:
            self._apply_reading_pos(self._pending_reading_pos)
            wx.CallAfter(self._apply_reading_pos, self._pending_reading_pos)
            resume_lead = (self._reading_sentence or "").strip()
        elif self.lst_outline is not None and self.lst_outline.GetCount() > 0:
            self.lst_outline.SetSelection(0)
            self.lst_outline.SetFocus()
        else:
            self.txt_display.SetFocus()
        rtad_speak(
            ((resume_lead + " ") if resume_lead else "")
            + summary
            + " Lettore documento RTAD. Tab: sommario, link e testo. "
            "Invio sul sommario: sezione qui in RTAD. "
            "Control+F: cerca. F3: ripeti (prossima occorrenza). "
            "Control+H / Control+Shift+H: titolo successivo o precedente. "
            "Control+B: segna un punto di lettura, quanti ne vuoi. "
            "Control+Shift+B: torna all'ultimo. Invio sull'elenco: scegli un altro. "
            "I link «Sito web» sono esterni."
            + (" Alt+U: traduci." if rtad_translate is not None else "")
        )

    def _outline_text_needles(self, title, level=1):
        """Candidate di ricerca nel testo per una voce di sommario."""
        title = (title or "").strip()
        needles = []
        if title:
            needles.append(f"[H{int(level) or 1}] {title}")
            needles.append(title)
            short = re.sub(r"\s*\(p\.\s*\d+\)\s*$", "", title, flags=re.I).strip()
            if short and short != title:
                needles.append(short)
            short2 = re.sub(r"^\s*Pagina\s+\d+\s*$", "", title, flags=re.I).strip()
            if short2 and short2 not in needles:
                needles.append(short2)
            compact = re.sub(r"\s+", "", title)
            if compact and compact != title:
                needles.append(compact)
            if short:
                c2 = re.sub(r"\s+", "", short)
                if c2 and c2 not in needles:
                    needles.append(c2)
        return [n for n in needles if n]

    def _jump_outline_in_text(self, item):
        """Posiziona il cursore sul corpo sezione (es. «English 3»), non sull'indice a puntini.

        Ritorna: 'section' | 'index_only' | False
        """
        title = (item.get("title") or "").strip()
        level = int(item.get("level") or 1)
        content = self.txt_display.GetValue() or ""
        if not content:
            return False
        body_mark = "=== Testo ==="
        body_at = content.find(body_mark)
        search_from = body_at + len(body_mark) if body_at >= 0 else 0

        label = title
        printed = None
        m_tp = re.match(r"^(.*?)\s*\(p\.\s*(\d+)\)\s*$", title, flags=re.I)
        if m_tp:
            label = m_tp.group(1).strip() or title
            printed = m_tp.group(2)

        if label and printed:
            pat = re.compile(
                re.escape(label) + r"([^\w\n]{1,30})" + re.escape(printed) + r"\b",
                re.I,
            )
            for m in pat.finditer(content, search_from):
                if re.search(r"\.{2,}", m.group(1) or ""):
                    continue
                chosen = m.start()
                chosen_len = len(m.group(0))
                self.txt_display.SetFocus()
                self.txt_display.SetInsertionPoint(chosen)
                try:
                    self.txt_display.ShowPosition(chosen)
                    self.txt_display.SetSelection(chosen, chosen + chosen_len)
                except Exception:
                    pass
                return "section"

        index_hit = None
        index_len = 0
        for needle in self._outline_text_needles(title, level):
            start = search_from
            while True:
                p = content.find(needle, start)
                if p < 0:
                    break
                after = content[p + len(needle) : p + len(needle) + 40]
                is_index = bool(re.match(r"\s*\.{2,}\s*\d*", after))
                before = content[max(0, p - 12) : p]
                if re.search(r"\[H\d+\]\s*$", before):
                    is_index = True
                if is_index:
                    if index_hit is None:
                        index_hit, index_len = p, len(needle)
                else:
                    self.txt_display.SetFocus()
                    self.txt_display.SetInsertionPoint(p)
                    try:
                        self.txt_display.ShowPosition(p)
                        self.txt_display.SetSelection(p, p + len(needle))
                    except Exception:
                        pass
                    return "section"
                start = p + max(1, len(needle))

        if index_hit is not None:
            self.txt_display.SetFocus()
            self.txt_display.SetInsertionPoint(index_hit)
            try:
                self.txt_display.ShowPosition(index_hit)
                self.txt_display.SetSelection(index_hit, index_hit + index_len)
            except Exception:
                pass
            return "index_only"
        return False

    def _open_pdf_page_from_item(self, item):
        """Apre il PDF con l'app predefinita Windows (ritorna 'page'|'file'|'')."""
        if not item or not self.file_path:
            return ""
        if os.path.splitext(self.file_path)[1].lower() != ".pdf":
            return ""
        if rtad_docstruct is None:
            return ""
        page = item.get("page")
        if not page:
            href = str(item.get("href") or "")
            m = re.match(r"rtad-pdf-page:(\d+)$", href, re.I)
            if m:
                page = int(m.group(1))
        if not page:
            try:
                os.startfile(self.file_path)
                return "file"
            except Exception:
                return ""
        named = str(item.get("anchor") or "").strip()
        try:
            mode = rtad_docstruct.open_pdf_at_page(
                self.file_path, int(page), named_dest=named
            )
        except Exception:
            mode = ""
        return mode or ""

    def _refocus_doc_frame(self, prefer_text=False):
        """Riporta focus su RTAD dopo che Acrobat ha rubato la finestra."""
        try:
            self.Iconize(False)
            self.Raise()
            self.Show()
            if prefer_text and self.txt_display is not None:
                self.txt_display.SetFocus()
            elif self.lst_outline is not None:
                self.lst_outline.SetFocus()
            elif self.txt_display is not None:
                self.txt_display.SetFocus()
        except Exception:
            pass

    def on_outline_activate(self, event=None):
        if self.lst_outline is None:
            return
        sel = self.lst_outline.GetSelection()
        if sel == wx.NOT_FOUND or sel < 0 or sel >= len(self.outline):
            return
        item = self.outline[sel]
        title = (item.get("title") or "").strip()
        jumped = self._jump_outline_in_text(item)
        is_pdf = bool(
            self.file_path
            and os.path.splitext(self.file_path)[1].lower() == ".pdf"
        )
        prefer_text = jumped in ("section", "index_only")

        def _after_open(open_mode=""):
            if open_mode == "page" and jumped == "section":
                rtad_speak(
                    f"Sezione «{title}» nel testo RTAD e PDF aperto alla pagina. "
                    f"Focus sul testo del documento."
                )
            elif open_mode == "page":
                rtad_speak(
                    f"Apro il PDF alla pagina con l'app predefinita («{title}»). "
                    + (
                        "In RTAD c'è solo l'indice di questa lingua. "
                        if jumped == "index_only"
                        else "Per leggere usa il testo qui in RTAD. "
                    )
                )
            elif open_mode == "file" and jumped == "section":
                rtad_speak(
                    f"Testo sulla sezione «{title}»; PDF aperto con l'app predefinita "
                    f"(senza salto pagina garantito)."
                )
            elif open_mode == "file":
                rtad_speak(
                    f"PDF aperto con l'app predefinita («{title}»). "
                    + (
                        "In RTAD c'è solo l'indice; vai alla pagina stampata nel visualizzatore."
                        if jumped == "index_only"
                        else ""
                    )
                )
            elif jumped == "section":
                rtad_speak(f"Testo sulla sezione «{title}».")
            elif jumped == "index_only":
                rtad_speak(
                    f"Per «{title}» in RTAD c'è solo l'indice (corpo non estraibile). "
                    f"Controlla l'app predefinita per i PDF in Windows e riprova Invio."
                )
            else:
                rtad_speak(f"Titolo in sommario: {title}")
            # Acrobat/preparazione tag rubano spesso il focus → «solo riquadro»
            wx.CallLater(500, lambda: self._refocus_doc_frame(prefer_text))

        if is_pdf:
            # Apri PDF dopo il salto testo, senza bloccare l'UI
            def _open():
                mode = ""
                try:
                    mode = self._open_pdf_page_from_item(item)
                except Exception:
                    mode = ""
                _after_open(mode)

            wx.CallAfter(_open)
        else:
            _after_open("")

    def on_link_activate(self, event=None):
        if not self.links:
            rtad_speak("Nessun link in questo documento.")
            return
        sel = 0
        if self.lst_links is not None:
            sel = self.lst_links.GetSelection()
            if sel == wx.NOT_FOUND:
                sel = 0
                self.lst_links.SetSelection(0)
        if sel < 0 or sel >= len(self.links):
            return
        item = self.links[sel]
        href = (item.get("href") or "").strip()
        text = (item.get("text") or "").strip()
        if href.lower().startswith("rtad-pdf-page:") or item.get("page"):
            mode = self._open_pdf_page_from_item(item)
            if mode == "page":
                rtad_speak("PDF aperto alla pagina con l'app.")
                return
            if mode == "file":
                rtad_speak("PDF aperto con l'app predefinita.")
                return
            rtad_speak("Impossibile aprire il PDF con l'app di sistema.")
            return
        if href.lower().startswith(("http://", "https://")):
            opened = False
            try:
                if sys.platform.startswith("win"):
                    os.startfile(href)
                    opened = True
                else:
                    opened = bool(webbrowser.open(href))
            except Exception:
                try:
                    opened = bool(webbrowser.open(href))
                except Exception:
                    opened = False
            if opened:
                rtad_speak(f"Apertura sito web esterno: {text or href}")
                return
            rtad_speak(f"Impossibile aprire il link. Destinazione: {href}")
            return
        if href.lower().startswith("mailto:"):
            try:
                webbrowser.open(href)
                rtad_speak(f"Apertura link: {text or href}")
                return
            except Exception:
                pass
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(href or text))
            wx.TheClipboard.Close()
            rtad_speak(f"Link copiato: {href or text}")
        else:
            rtad_speak(f"Link: {href or text}")

    def _select_in_text(self, start, end, announce=""):
        """Focus sul testo, seleziona [start, end) e annuncia."""
        try:
            self.txt_display.SetFocus()
            self.txt_display.SetInsertionPoint(start)
            self.txt_display.ShowPosition(start)
            self.txt_display.SetSelection(start, end)
            self._saved_insert = start
            self._last_focus_ctrl = self.txt_display
        except Exception:
            pass
        if announce:
            rtad_speak(announce)

    def _on_reader_child_focus(self, event):
        try:
            self._last_focus_ctrl = event.GetEventObject()
            if self._last_focus_ctrl is self.txt_display:
                self._saved_insert = self.txt_display.GetInsertionPoint()
        except Exception:
            pass
        event.Skip()

    def _remember_text_pos(self):
        try:
            if self.txt_display is not None:
                self._saved_insert = self.txt_display.GetInsertionPoint()
                self._last_focus_ctrl = self.txt_display
        except Exception:
            pass

    def _reader_known_ctrls(self):
        known = set()
        for c in (self.txt_display, self.lst_outline, self.lst_links, self.lst_reading):
            if c is not None:
                known.add(c)
        return known

    def _kick_text_caret(self, pos):
        """Secondo passaggio focus: dopo iconizza le frecce a volte restano mute."""
        try:
            if self.IsIconized() or not self.IsShown():
                return
            if self.txt_display is None:
                return
            self.txt_display.SetFocus()
            end = self.txt_display.GetLastPosition()
            pos = max(0, min(int(pos or 0), end))
            self.txt_display.SetInsertionPoint(pos)
            self.txt_display.SetSelection(pos, pos)
            try:
                self.txt_display.ShowPosition(pos)
            except Exception:
                pass
        except Exception:
            pass

    def _restore_reader_focus(self):
        """Dopo iconizza/Alt-Tab: torna sul controllo e sulla posizione testo.

        Dopo ripristino da iconizza, SetFocus da solo non basta sempre perché
        le frecce riprendano (serve Tab/Shift+Tab): Raise + caret kick.
        """
        try:
            if not self.IsShown() or self.IsIconized():
                return
            try:
                self.Raise()
            except Exception:
                pass
            known = self._reader_known_ctrls()
            ctrl = self._last_focus_ctrl
            if ctrl not in known:
                ctrl = self.txt_display
            try:
                self.SetFocus()
            except Exception:
                pass
            try:
                ctrl.SetFocus()
            except Exception:
                if self.txt_display is not None:
                    self.txt_display.SetFocus()
                    ctrl = self.txt_display
            if ctrl is self.txt_display and self.txt_display is not None:
                pos = max(0, int(self._saved_insert or 0))
                end = self.txt_display.GetLastPosition()
                if pos > end:
                    pos = end
                self.txt_display.SetInsertionPoint(pos)
                self.txt_display.SetSelection(pos, pos)
                try:
                    self.txt_display.ShowPosition(pos)
                except Exception:
                    pass
                wx.CallLater(50, self._kick_text_caret, pos)
            elif ctrl is not None:
                try:
                    sel = ctrl.GetSelection()
                    if sel != wx.NOT_FOUND:
                        ctrl.SetSelection(sel)
                except Exception:
                    pass
                try:
                    ctrl.SetFocus()
                except Exception:
                    pass
        except Exception:
            pass

    def _on_reader_activate(self, event):
        if event.GetActive():
            wx.CallLater(100, self._restore_reader_focus)
        else:
            self._remember_text_pos()
        event.Skip()

    def _on_reader_iconize(self, event):
        if event.IsIconized():
            self._remember_text_pos()
        else:
            wx.CallLater(220, self._restore_reader_focus)
        event.Skip()

    def on_find(self, event=None):
        dlg = wx.TextEntryDialog(
            self,
            "Parola o frase da cercare nel testo del documento:\n"
            "(OK = prossima occorrenza dalla posizione del cursore; F3 ripete)",
            "Cerca nel testo",
            self._find_needle or "",
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            needle = (dlg.GetValue() or "").strip()
        finally:
            dlg.Destroy()
        self._ignore_enter_until = time.monotonic() + 0.4
        try:
            self.txt_display.SetFocus()
        except Exception:
            pass
        if not needle:
            rtad_speak("Ricerca annullata.")
            return
        self._find_needle = needle
        if not self._find_in_text(needle, forward=True, from_start=False):
            rtad_speak(f"Nessuna occorrenza di «{needle}».")

    def _find_in_text(self, needle, forward=True, from_start=False):
        content = self.txt_display.GetValue() or ""
        if not needle or not content:
            return False
        needle_l = needle.lower()
        content_l = content.lower()
        sel_start, sel_end = self.txt_display.GetSelection()
        if from_start:
            pos = 0
        elif forward:
            pos = sel_end if sel_end > sel_start else self.txt_display.GetInsertionPoint()
            if sel_end > sel_start and content[sel_start:sel_end].lower() == needle_l:
                pos = sel_end
        else:
            pos = sel_start if sel_end > sel_start else self.txt_display.GetInsertionPoint()
            if sel_end > sel_start and content[sel_start:sel_end].lower() == needle_l:
                pos = sel_start
        if forward:
            p = content_l.find(needle_l, pos)
            if p < 0:
                p = content_l.find(needle_l)  # wrap
            if p < 0:
                return False
        else:
            p = content_l.rfind(needle_l, 0, max(0, pos))
            if p < 0:
                p = content_l.rfind(needle_l)  # wrap
            if p < 0:
                return False
        self._select_in_text(
            p, p + len(needle), announce=f"Trovato: {content[p:p + len(needle)]}"
        )
        return True

    def on_find_next(self, event=None):
        if not self._find_needle:
            self.on_find()
            return
        if not self._find_in_text(self._find_needle, forward=True):
            rtad_speak(f"Nessuna altra occorrenza di «{self._find_needle}».")

    def on_find_prev(self, event=None):
        if not self._find_needle:
            self.on_find()
            return
        if not self._find_in_text(self._find_needle, forward=False):
            rtad_speak(f"Nessuna altra occorrenza di «{self._find_needle}».")

    def on_next_heading(self, event=None):
        self._goto_heading(forward=True)

    def on_prev_heading(self, event=None):
        self._goto_heading(forward=False)

    def _goto_heading(self, forward=True):
        content = self.txt_display.GetValue() or ""
        matches = list(self._HEADING_MARK_RE.finditer(content))
        if not matches:
            rtad_speak("Nessun titolo [H] nel testo.")
            return
        pos = self.txt_display.GetInsertionPoint()
        sel_start, sel_end = self.txt_display.GetSelection()
        if sel_end > sel_start:
            pos = sel_start
        chosen = None
        if forward:
            for m in matches:
                if m.start() > pos:
                    chosen = m
                    break
            if chosen is None:
                chosen = matches[0]
        else:
            for m in reversed(matches):
                if m.start() < pos:
                    chosen = m
                    break
            if chosen is None:
                chosen = matches[-1]
        level = chosen.group(1)
        title = (chosen.group(2) or "").strip() or f"H{level}"
        line_end = content.find("\n", chosen.start())
        if line_end < 0:
            line_end = chosen.end()
        self._select_in_text(
            chosen.start(),
            line_end,
            announce=f"Titolo livello {level}: {title}",
        )

    def on_open_external(self, event=None):
        """Apre il file con l'app predefinita Windows (azione secondaria)."""
        if not self.file_path or not os.path.isfile(self.file_path):
            rtad_speak("File non disponibile.")
            return
        try:
            os.startfile(self.file_path)
            rtad_speak(
                f"Aperto con l'app predefinita: {os.path.basename(self.file_path)}"
            )
        except Exception as e:
            rtad_speak(f"Apertura esterna non riuscita: {e}")

    def on_translate(self, event=None):
        start_frame_translation(self, rtad_speak)

    def on_ask_gemini(self, event=None):
        open_gemini_chat(
            "document",
            self.file_path,
            struct=self.struct,
            displayed=self.txt_display.GetValue(),
            parent=self,
        )

    def on_copy(self, event=None):
        text = self.txt_display.GetValue()
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
            rtad_speak("Testo copiato negli appunti.")
        else:
            rtad_speak("Impossibile aprire gli appunti.")

    def on_save_text(self, event=None):
        text = self.txt_display.GetValue() or ""
        if not text.strip():
            rtad_speak("Niente da salvare.")
            return
        stem = report_save_stem_for_path(self.file_path)
        default_dir = ""
        if self.file_path:
            cand = os.path.dirname(os.path.abspath(self.file_path))
            if cand and os.path.isdir(cand) and not _looks_like_temp_dir(cand):
                default_dir = cand
        if not default_dir:
            default_dir = load_last_media_report_dir() or os.path.expanduser("~")
        dlg = wx.FileDialog(
            self,
            "Salva testo documento",
            defaultDir=default_dir,
            defaultFile=f"{stem}.rtad.txt",
            wildcard="Testo (*.txt)|*.txt|Tutti i file (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            path = dlg.GetPath()
        finally:
            dlg.Destroy()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            save_last_media_report_dir(path)
            rtad_speak(f"Testo salvato: {os.path.basename(path)}")
        except Exception as e:
            rtad_speak(f"Salvataggio non riuscito: {e}")

    def _show_reading_status(self, sentence, speak=True):
        sentence = (sentence or "").strip()
        if self.lbl_reading is not None and sentence:
            self.lbl_reading.SetLabel(sentence)
            try:
                self.lbl_reading.Wrap(720)
            except Exception:
                pass
            try:
                self.Layout()
            except Exception:
                pass
        if speak and sentence:
            rtad_speak(sentence)

    def _reading_caret(self):
        try:
            start, end = self.txt_display.GetSelection()
        except Exception:
            return 0
        if start != end:
            return min(start, end)
        try:
            return self.txt_display.GetInsertionPoint()
        except Exception:
            return min(start, end)

    def _apply_reading_pos(self, pos, focus=True):
        try:
            if self.txt_display is None:
                return
            end = self.txt_display.GetLastPosition()
            pos = max(0, min(int(pos or 0), end))
            self._saved_insert = pos
            self._last_focus_ctrl = self.txt_display
            if focus:
                self.txt_display.SetFocus()
            self.txt_display.SetInsertionPoint(pos)
            self.txt_display.SetSelection(pos, pos)
            try:
                self.txt_display.ShowPosition(pos)
            except Exception:
                pass
        except Exception:
            pass

    def _reload_reading_list(self, text=None, select_id=None):
        if self.lst_reading is None or rtad_reading_mark is None:
            self._reading_rows = []
            return []
        if text is None and self.txt_display is not None:
            text = self.txt_display.GetValue() or ""
        text = text or ""
        self.lst_reading.Clear()
        self._reading_rows = []
        if not (self.file_path or "").strip():
            self.lst_reading.Append(rtad_reading_mark.MSG_NOFILE)
            self.lst_reading.SetSelection(0)
            return []
        group = rtad_reading_mark.get_group(CONFIG_DIR, self.file_path)
        rows = rtad_reading_mark.describe_items(text, group)
        if not rows:
            self.lst_reading.Append(rtad_reading_mark.MSG_NONE)
            self.lst_reading.SetSelection(0)
            return []
        want = str(select_id or group.get("resume_id") or "")
        selected = 0
        for index, row in enumerate(rows):
            self.lst_reading.Append(row["label"])
            if row["id"] == want:
                selected = index
        self._reading_rows = rows
        self.lst_reading.SetSelection(selected)
        return rows

    def _arm_reading_resume(self, text):
        rows = self._reading_rows or []
        chosen = None
        for row in rows:
            if row.get("resume"):
                chosen = row
                break
        if chosen is None and rows:
            chosen = rows[-1]
        if not chosen or chosen.get("kind") == "empty":
            return
        self._pending_reading_pos = chosen["pos"]
        self._saved_insert = chosen["pos"]
        sentence = rtad_reading_mark.resume_sentence(
            chosen["kind"],
            text or "",
            chosen["pos"],
            chosen["index"],
            chosen["total"],
        )
        self._reading_sentence = sentence
        if self.lbl_reading is not None:
            self.lbl_reading.SetLabel(sentence)

    def _selected_reading_row(self):
        rows = self._reading_rows or []
        if not rows or self.lst_reading is None:
            return None
        sel = self.lst_reading.GetSelection()
        if sel == wx.NOT_FOUND or sel < 0 or sel >= len(rows):
            return None
        return rows[sel]

    def on_reading_mark_activate(self, event=None):
        if rtad_reading_mark is None:
            return
        if not (self.file_path or "").strip():
            self._show_reading_status(rtad_reading_mark.MSG_NOFILE)
            return
        row = self._selected_reading_row()
        if row is None:
            self._show_reading_status(rtad_reading_mark.MSG_NONE)
            return
        try:
            rtad_reading_mark.touch_resume(CONFIG_DIR, self.file_path, row["id"])
        except Exception:
            pass
        self._apply_reading_pos(row["pos"])
        text = self.txt_display.GetValue() or ""
        self._show_reading_status(
            rtad_reading_mark.resume_sentence(
                row["kind"], text, row["pos"], row["index"], row["total"]
            )
        )

    def on_save_reading_mark(self, event=None):
        if rtad_reading_mark is None:
            return
        if not (self.file_path or "").strip():
            self._show_reading_status(rtad_reading_mark.MSG_NOFILE)
            return
        text = self.txt_display.GetValue() or ""
        if not text.strip():
            self._show_reading_status(rtad_reading_mark.MSG_EMPTY)
            return
        pos = self._reading_caret()
        try:
            result = rtad_reading_mark.add_mark(CONFIG_DIR, self.file_path, text, pos)
        except Exception:
            self._show_reading_status("Segnalibro di lettura non salvato.")
            return
        status = result.get("status")
        if status == "full":
            self._show_reading_status(rtad_reading_mark.MSG_FULL)
            return
        item = result.get("item") or {}
        self._reload_reading_list(text, select_id=item.get("id"))
        self._saved_insert = pos
        excerpt = rtad_reading_mark.excerpt_at(text, pos)
        self._show_reading_status(
            rtad_reading_mark.saved_sentence(
                result.get("total") or 0,
                excerpt,
                already=(status == "already"),
            )
        )

    def on_resume_reading_mark(self, event=None):
        if rtad_reading_mark is None:
            return
        if not (self.file_path or "").strip():
            self._show_reading_status(rtad_reading_mark.MSG_NOFILE)
            return
        text = self.txt_display.GetValue() or ""
        rows = self._reload_reading_list(text)
        chosen = None
        for row in rows:
            if row.get("resume"):
                chosen = row
                break
        if chosen is None:
            self._show_reading_status(rtad_reading_mark.MSG_NONE)
            return
        self._apply_reading_pos(chosen["pos"])
        self._show_reading_status(
            rtad_reading_mark.resume_sentence(
                chosen["kind"], text, chosen["pos"], chosen["index"], chosen["total"]
            )
        )

    def on_delete_reading_mark(self, event=None):
        if rtad_reading_mark is None:
            return
        if not (self.file_path or "").strip():
            self._show_reading_status(rtad_reading_mark.MSG_NOFILE)
            return
        row = self._selected_reading_row()
        if row is None:
            self._show_reading_status(rtad_reading_mark.MSG_NONE)
            return
        try:
            remaining = rtad_reading_mark.delete_item(
                CONFIG_DIR, self.file_path, row["id"]
            )
        except Exception:
            remaining = -1
        if remaining < 0:
            self._show_reading_status(rtad_reading_mark.MSG_NONE)
            return
        self._reload_reading_list(self.txt_display.GetValue() or "")
        self._show_reading_status(
            rtad_reading_mark.removed_sentence(remaining, row.get("excerpt") or "")
        )

    def on_char_hook(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self.Close()
            return
        if event.ControlDown() and not event.AltDown():
            if key in (ord("b"), ord("B")):
                if event.ShiftDown():
                    self.on_resume_reading_mark()
                else:
                    self.on_save_reading_mark()
                return
            if key in (ord("f"), ord("F")):
                self.on_find()
                return
            if key in (ord("h"), ord("H")):
                if event.ShiftDown():
                    self.on_prev_heading()
                else:
                    self.on_next_heading()
                return
        if key == wx.WXK_F3:
            if event.ShiftDown():
                self.on_find_prev()
            else:
                self.on_find_next()
            return
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            if time.monotonic() < float(self._ignore_enter_until or 0):
                return
            focused = self.FindFocus()
            if self.lst_reading is not None and focused is self.lst_reading:
                self.on_reading_mark_activate()
                return
            if self.lst_links is not None and focused is self.lst_links:
                self.on_link_activate()
                return
            if self.lst_outline is not None and focused is self.lst_outline:
                self.on_outline_activate()
                return
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
            "• Nel lettore, Control+B aggiunge un punto di lettura. Quanti ne vuoi.\n"
            "  Vale anche per un txt aperto con Leggi documento.\n"
            "  Il precedente resta. Alla riapertura torni sull'ultimo.\n"
            "  Se sono più di uno, a schermo e a voce:\n"
            "  «Segnalibro di lettura 2 di 3: ripreso da qui.»\n"
            "  Nell'elenco, frecce e Invio scelgono. Control+Shift+B torna all'ultimo.\n"
            "  Non è il Segnalibro Ctrl+D, che salva un percorso.\n"
            "• «Copia testo del documento» copia sommario, link e capitoli.\n"
            "• In un PDF, se l'ultima cifra è disegnata a parte,\n"
            "  202 7 torna 2027. Lo stesso per un importo come 2,8.\n"
            "• Nei libri EPUB, i codici come &#232; diventano lettere e segni.\n"
            "  Vale nel lettore e nel testo copiato.\n"
            "• Resta dalla 1.8.6: Whisper sul mio PC, casella spenta.\n"
            "• Ultima versione NVDA testata: 2026.3.\n"
            "• Le chat dell'Add-on restano nel profilo NVDA.\n"
            "--------------------------------------------------\n"
            "Grazie per usare Ricerca Testuale Accesso Digitale!\n"
        )

        lbl_info = wx.StaticText(panel, label="Leggi tutte le novità dell'ultimo aggiornamento:")
        vbox.Add(lbl_info, 0, wx.ALL, 8)

        self.txt_display = wx.TextCtrl(panel, value=text_content, style=wx.TE_MULTILINE | wx.TE_READONLY)
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
            style=wx.TE_MULTILINE | wx.TE_READONLY,
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
            "  - Ctrl + Shift + G : Conversazioni Gemini già salvate\n"
            "  - Alt + B : Conversazioni Gemini (finestra principale)\n"
            "  - Alt + Q : Nuova conversazione Gemini, anche senza un file\n"
            "  - Alt + A : Allega file. Elenco per data, i più recenti in cima\n"
            "  - Shift + Invio : nella domanda della chat, va a capo\n"
            "  - Alt + L : Chiave Google Vision\n"
            "  - Alt + H : Chiave Gemini\n"
            "  - Alt + G : Chiedi a Gemini (sul report o nel lettore documento)\n"
            "  - Alt + U : Traduci il testo già aperto (report o lettore)\n"
            "  - Sul file .rtad.txt: Chiedi a Gemini usa il resoconto già salvato\n"
            "  - Alt + F : Apri la fonte selezionata (anche se sei sull'elenco)\n"
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
            "  - Ctrl + D : Aggiunge percorso attuale ai Segnalibri\n"
            "  - Nel lettore, Ctrl + B: aggiunge un punto di lettura, quanti ne vuoi. Ctrl + Shift + B: ultimo. Invio sull'elenco: scegli. Non è Ctrl + D.\n"            "  - Ctrl + Shift + P : Salva profilo di ricerca attuale\n"            "  - Ctrl + Shift + L : Carica un profilo di ricerca\n"
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
            style=wx.TE_MULTILINE | wx.TE_READONLY,
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
        self._results_ready = False
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
        self.combo_filter.Bind(wx.EVT_KEY_DOWN, self.on_filter_key_down)
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

        lbl_path = wx.StaticText(
            panel,
            label=(
                "Percorso di ricerca (cartella, unità, singolo file, o URL Feed RSS; "
                "memoria automatica):"
            ),
        )
        vbox.Add(lbl_path, 0, wx.ALL, 5)

        hbox_path = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_path = wx.TextCtrl(panel, value=load_last_path())
        hbox_path.Add(self.txt_path, 1, wx.EXPAND | wx.ALL, 5)

        btn_browse = wx.Button(panel, label="Sfoglia...")
        btn_browse.Bind(wx.EVT_BUTTON, self.on_browse)
        hbox_path.Add(btn_browse, 0, wx.ALL, 5)

        btn_paste_path = wx.Button(panel, label="Incolla…")
        btn_paste_path.SetToolTip(
            "Incolla dagli Appunti un file/cartella copiati in Esplora "
            "oppure un percorso testo (Ctrl+Alt+V)"
        )
        btn_paste_path.Bind(wx.EVT_BUTTON, self.on_paste_path_from_clipboard)
        hbox_path.Add(btn_paste_path, 0, wx.ALL, 5)

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
        btn_gkey = wx.Button(panel, label="Chiave Goog&le…")
        btn_gkey.SetName("Chiave API Google Vision")
        btn_gkey.Bind(wx.EVT_BUTTON, self.on_set_google_vision_key)
        hbox_ocr_eng.Add(btn_gkey, 0, wx.LEFT, 8)
        btn_gem = wx.Button(panel, label="C&hiave Gemini…")
        btn_gem.SetName("Chiave API Gemini")
        btn_gem.Bind(wx.EVT_BUTTON, self.on_set_gemini_api_key)
        hbox_ocr_eng.Add(btn_gem, 0, wx.LEFT, 8)
        vbox.Add(hbox_ocr_eng, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        hbox_actions = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_search = wx.Button(panel, label="Avvia Ricerca")
        self.btn_search.Bind(wx.EVT_BUTTON, lambda e: self.start_search_thread())
        hbox_actions.Add(self.btn_search, 0, wx.ALL, 5)
        self.btn_gemini_chats = wx.Button(panel, label="Conversazioni Gemini (Alt+&B)…")
        self.btn_gemini_chats.SetName("Conversazioni Gemini")
        self.btn_gemini_chats.Bind(wx.EVT_BUTTON, self.on_gemini_conversations)
        hbox_actions.Add(self.btn_gemini_chats, 0, wx.ALL, 5)
        self.btn_gemini_new = wx.Button(panel, label="Nuova conversazione (&Q)…")
        self.btn_gemini_new.SetName("Nuova conversazione Gemini")
        self.btn_gemini_new.Bind(wx.EVT_BUTTON, lambda e: open_free_gemini_chat(self))
        hbox_actions.Add(self.btn_gemini_new, 0, wx.ALL, 5)

        self.btn_media_hub = wx.Button(panel, label="Analisi &audio/video…")
        self.btn_media_hub.SetToolTip(
            "Apre l'hub per URL o file (scheda, riassunto, trascrizione). "
            "Visibile con filtro Solo Audio e Video."
        )
        self.btn_media_hub.Bind(wx.EVT_BUTTON, self.on_media_hub_button)
        hbox_actions.Add(self.btn_media_hub, 0, wx.ALL, 5)
        self.btn_media_hub.Enable(False)

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
        self.lst_results.Append("Nessuna ricerca avviata.")
        self.lst_results.SetSelection(0)
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

    def on_open_html_guide(self, event=None):
        """Aiuto → Guida completa HTML (indice, Vision/Gemini)."""
        if rtad_guida_html is None:
            wx.CallLater(
                200,
                lambda: rtad_speak("Guida HTML non disponibile in questa build."),
            )
            return
        try:
            path = os.path.join(CONFIG_DIR, "guida_ricerca_testuale.html")
            rtad_guida_html.write_guida_html(
                path,
                app_title=APP_TITLE,
                app_version=APP_VERSION,
                donation_url=DONATION_URL,
                github_url="https://github.com/barramaurizio/ricerca_testuale_accesso_digitale",
            )
            webbrowser.open("file:///" + path.replace("\\", "/"))
            wx.CallLater(
                200,
                lambda: rtad_speak(
                    "Guida completa aperta nel browser. "
                    "Con NVDA: NVDA Control F per cercare; altrimenti Control F."
                ),
            )
        except Exception:
            wx.CallLater(
                200, lambda: rtad_speak("Impossibile aprire la guida HTML.")
            )

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
        """Verifica aggiornamenti Add-on dalla release v* (non app-v Standalone)."""
        def _check():
            try:
                if not silent:
                    wx.CallAfter(rtad_speak, "Verifica aggiornamenti in corso...")
                req = urllib.request.Request(
                    GITHUB_API_RELEASES,
                    headers={"User-Agent": "RTAD-Addon-Updater"},
                )
                with urllib.request.urlopen(req, timeout=12) as response:
                    releases = json.loads(response.read().decode("utf-8"))
                if not isinstance(releases, list):
                    if not silent:
                        wx.CallAfter(rtad_speak, "Nessuna informazione di versione online.")
                    return

                best = None
                best_ver = None
                for rel in releases:
                    if not isinstance(rel, dict):
                        continue
                    if rel.get("draft") or rel.get("prerelease"):
                        continue
                    tag = str(rel.get("tag_name", "")).strip()
                    # Solo tag Add-on vX.Y.Z (non app-v…)
                    if not tag.startswith("v") or tag.startswith("app-"):
                        continue
                    ver_s = tag[1:].strip()
                    try:
                        ver_t = tuple(int(x) for x in ver_s.split("."))
                    except Exception:
                        continue
                    if best_ver is not None and ver_t <= best_ver:
                        continue
                    addon_url = None
                    addon_name = None
                    for asset in rel.get("assets") or []:
                        if not isinstance(asset, dict):
                            continue
                        name = str(asset.get("name", ""))
                        if name.endswith(".nvda-addon"):
                            addon_url = asset.get("browser_download_url")
                            addon_name = name
                            break
                    best_ver = ver_t
                    best = {
                        "version": ver_s,
                        "html_url": rel.get("html_url") or GITHUB_URL,
                        "addon_url": addon_url,
                        "addon_name": addon_name,
                    }

                if not best:
                    if not silent:
                        wx.CallAfter(rtad_speak, "Nessuna release Add-on trovata online.")
                    return

                latest_tag = best["version"]
                html_url = best["html_url"]
                try:
                    v_online = [int(x) for x in latest_tag.split(".")]
                    v_local = [int(x) for x in APP_VERSION.split(".")]
                    is_newer = v_online > v_local
                except Exception:
                    is_newer = latest_tag != APP_VERSION

                if is_newer:
                    addon_url = best.get("addon_url")

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
        item_print = file_menu.Append(wx.ID_ANY, "Stam&pa Risultati...\tCtrl+P")
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
        item_clear_queries = self.history_menu.Append(wx.ID_ANY, "S&vuota cronologia testi")
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
        item_paste_path = tools_menu.Append(
            wx.ID_ANY, "Incolla pe&rcorso dagli Appunti…\tCtrl+Alt+V"
        )
        self.Bind(wx.EVT_MENU, self.on_paste_path_from_clipboard, item_paste_path)
        tools_menu.AppendSeparator()
        item_gkey = tools_menu.Append(
            wx.ID_ANY, "Chiave API Goog&le Vision…"
        )
        self.Bind(wx.EVT_MENU, self.on_set_google_vision_key, item_gkey)
        item_gemkey = tools_menu.Append(
            wx.ID_ANY, "C&hiave API Gemini (descrizione avanzata)…"
        )
        self.Bind(wx.EVT_MENU, self.on_set_gemini_api_key, item_gemkey)
        item_gemini_new = tools_menu.Append(
            wx.ID_ANY, "Nuova conversazione Gemini (&Q)…"
        )
        self.Bind(wx.EVT_MENU, lambda e: open_free_gemini_chat(self), item_gemini_new)
        item_gemini_chats = tools_menu.Append(
            wx.ID_ANY, "Conversazioni Gemini (Alt+&B)…\tCtrl+Shift+G"
        )
        self.Bind(wx.EVT_MENU, self.on_gemini_conversations, item_gemini_chats)
        item_glossary = tools_menu.Append(
            wx.ID_ANY, "&Glossario trascrizioni…"
        )
        self.Bind(wx.EVT_MENU, self.on_transcript_glossary, item_glossary)
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
            wx.ID_ANY, "Descrivi &immagine dagli Appunti\tCtrl+Shift+I"
        )
        self.Bind(wx.EVT_MENU, self.on_describe_from_clipboard, item_desc_clip)
        item_desc_cap = tools_menu.Append(
            wx.ID_ANY, "Cattura schermo e &descrivi\tAlt+Shift+K"
        )
        self.Bind(wx.EVT_MENU, self.on_describe_from_screenshot, item_desc_cap)
        item_desc_pdf = tools_menu.Append(
            wx.ID_ANY, "Descrivi immagine da PD&F…"
        )
        self.Bind(wx.EVT_MENU, self.on_describe_pdf_dialog, item_desc_pdf)
        item_all_img = tools_menu.Append(
            wx.ID_ANY, "&Tutto sull'immagine…"
        )
        self.Bind(wx.EVT_MENU, self.on_image_all_dialog, item_all_img)
        item_ocr_img = tools_menu.Append(
            wx.ID_ANY, "Leggi testo nell'immagine (&OCR)…"
        )
        self.Bind(wx.EVT_MENU, self.on_image_ocr_dialog, item_ocr_img)
        item_batch_img = tools_menu.Append(
            wx.ID_ANY, "Analizza cartella i&mmagini…"
        )
        self.Bind(wx.EVT_MENU, self.on_batch_images_folder, item_batch_img)
        item_all_media = tools_menu.Append(
            wx.ID_ANY, "Tutto sull'audio/video (&J)…"
        )
        self.Bind(wx.EVT_MENU, self.on_media_all_dialog, item_all_media)
        item_batch_media = tools_menu.Append(
            wx.ID_ANY, "Anali&zza cartella audio/video…"
        )
        self.Bind(wx.EVT_MENU, self.on_batch_media_folder, item_batch_media)
        item_tr_search = tools_menu.Append(
            wx.ID_ANY, "Trascrivi e c&erca…\tCtrl+Shift+T"
        )
        self.Bind(wx.EVT_MENU, self.on_transcribe_and_search, item_tr_search)
        item_media_url = tools_menu.Append(
            wx.ID_ANY, "Audio/video da &web (URL)…\tCtrl+Shift+M"
        )
        self.Bind(wx.EVT_MENU, self.on_media_from_url, item_media_url)
        item_ytdlp = tools_menu.Append(
            wx.ID_ANY, "Verifica / aggiorna &yt-dlp…"
        )
        self.Bind(wx.EVT_MENU, self.on_ytdlp_tools, item_ytdlp)
        tools_menu.AppendSeparator()
        self.item_notify_end = tools_menu.AppendCheckItem(
            wx.ID_ANY, "&Notifica a fine ricerca (Centro notifiche Windows)"
        )
        try:
            self.item_notify_end.Check(load_notify_search_end_preference())
        except Exception:
            self.item_notify_end.Check(True)
        self.Bind(wx.EVT_MENU, self.on_toggle_notify_search_end, self.item_notify_end)
        self.item_auto_save = tools_menu.AppendCheckItem(
            wx.ID_ANY, "&Salva automaticamente i risultati a fine ricerca"
        )
        try:
            self.item_auto_save.Check(load_auto_save_results_preference())
        except Exception:
            self.item_auto_save.Check(False)
        self.Bind(wx.EVT_MENU, self.on_toggle_auto_save_results, self.item_auto_save)
        item_auto_save_dir = tools_menu.Append(
            wx.ID_ANY, "Cartella salvataggio automatico risultati (Alt+&K)…"
        )
        self.Bind(wx.EVT_MENU, self.on_choose_auto_save_dir, item_auto_save_dir)
        self.item_escape_closes = tools_menu.AppendCheckItem(
            wx.ID_ANY, "Esc chiude l'a&pplicazione (altrimenti Alt+F4 / Ctrl+Q / Chiudi)"
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
        item_html = help_menu.Append(
            wx.ID_ANY, "Guida completa (&HTML, cercabile)…"
        )
        item_guide = help_menu.Append(wx.ID_ANY, "&Guida ai Comandi\tF1")
        item_print_guide = help_menu.Append(wx.ID_ANY, "Stampa guida ai co&mandi")
        item_github = help_menu.Append(wx.ID_ANY, "Pagina &ufficiale GitHub")
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
        self.Bind(wx.EVT_MENU, self.on_open_html_guide, item_html)
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

    def on_transcript_glossary(self, event=None):
        """Strumenti → Glossario trascrizioni (correzioni post-Gemini)."""
        if rtad_media is None:
            rtad_speak("Modulo media non disponibile.")
            return
        dlg = TranscriptGlossaryDialog(self)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                rtad_speak("Glossario non modificato.")
                return
            enabled, rules = dlg.result()
        finally:
            dlg.Destroy()
        try:
            save_transcript_glossary(enabled, rules)
        except Exception as e:
            rtad_speak(f"Impossibile salvare il glossario: {e}", force=True)
            return
        n = len(rules or [])
        if enabled and n:
            rtad_speak(
                f"Glossario attivo: {n} regole. "
                "Si applicherà alle prossime analisi audio/video."
            )
        elif enabled:
            rtad_speak(
                "Glossario attivo ma senza regole. Aggiungine almeno una."
            )
        else:
            rtad_speak("Glossario disattivato.")

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

    def on_toggle_auto_save_results(self, event=None):
        enabled = False
        try:
            enabled = bool(self.item_auto_save.IsChecked())
        except Exception:
            enabled = not load_auto_save_results_preference()
        dest_note = ""
        if enabled and not load_last_export_dir():
            chosen = self._prompt_auto_save_dir()
            dest_note = f" Cartella: {chosen}." if chosen else ""
        try:
            save_auto_save_results_preference(enabled)
        except Exception:
            pass
        if enabled:
            rtad_speak(
                "Salvataggio automatico dei risultati a fine ricerca attivato."
                + dest_note
                + " Per cambiare cartella: Strumenti, Cartella salvataggio automatico risultati.",
                force=True,
            )
        else:
            rtad_speak(
                "Salvataggio automatico dei risultati disattivato.",
                force=True,
            )

    def _prompt_auto_save_dir(self):
        """Chiede/aggiorna la cartella di auto-salvataggio. Ritorna il path o ''."""
        start = load_last_export_dir() or get_dynamic_desktop_path()
        dlg = wx.DirDialog(
            self,
            "Cartella per il salvataggio automatico dei risultati",
            defaultPath=start,
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        try:
            if dlg.ShowModal() == wx.ID_OK:
                save_last_export_dir(dlg.GetPath())
        finally:
            dlg.Destroy()
        if not load_last_export_dir():
            save_last_export_dir(start)
        return load_last_export_dir() or start

    def on_choose_auto_save_dir(self, event=None):
        chosen = self._prompt_auto_save_dir()
        if chosen:
            rtad_speak(
                f"Cartella salvataggio automatico: {chosen}.",
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
        """Notifica Windows a fine ricerca (toast breve; non ruba il lettore documento)."""
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

        reader_active = False
        try:
            for w in wx.GetTopLevelWindows():
                if isinstance(w, DocumentStructureFrame) and w.IsShown():
                    reader_active = True
                    break
        except Exception:
            reader_active = False
        if reader_active:
            try:
                rtad_speak(body)
            except Exception:
                pass
            return

        try:
            self.RequestUserAttention(wx.USER_ATTENTION_INFO)
        except Exception:
            pass

        def _refocus():
            try:
                for w in wx.GetTopLevelWindows():
                    if isinstance(w, DocumentStructureFrame) and w.IsShown():
                        return
                self.Raise()
                if self.lst_results.GetCount() > 0:
                    if self.lst_results.GetSelection() == wx.NOT_FOUND:
                        self.lst_results.SetSelection(0)
                    self.lst_results.SetFocus()
            except Exception:
                pass

        wx.CallLater(350, _refocus)
        wx.CallLater(1200, _refocus)

        def _fallback_wx():
            try:
                import wx.adv
                n = wx.adv.NotificationMessage(APP_TITLE, body, parent=self)
                try:
                    n.SetFlags(wx.ICON_INFORMATION)
                except Exception:
                    pass
                n.Show(timeout=5)
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
        self._suppress_media_hub = True
        try:
            self.combo_filter.SetSelection(mode)
        finally:
            self._suppress_media_hub = False
        self._update_media_hub_button()
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

    def _update_media_hub_button(self):
        """Abilita «Analisi audio/video…» solo col filtro media."""
        btn = getattr(self, "btn_media_hub", None)
        if btn is None:
            return
        try:
            btn.Enable(self.combo_filter.GetSelection() == 2)
        except Exception:
            pass

    def on_media_hub_button(self, event=None):
        """Pulsante principale → hub; se il percorso è un URL http, lo riusa."""
        path_val = (self.txt_path.GetValue() or "").strip()
        url = ""
        low = path_val.lower()
        if low.startswith("http://") or low.startswith("https://"):
            url = path_val
        self.open_media_hub_dialog(
            initial_url=url, clear_source=True
        )

    def on_filter_changed(self, event):
        sel = self.combo_filter.GetSelection()
        self.txt_custom_ext.Enable(sel == 4)
        if sel != 4:
            self.txt_custom_ext.SetValue("")
        self._update_media_hub_button()
        # Index 2 = Solo Audio e Video → hub analisi (file/URL/sezioni)
        if sel == 2 and not getattr(self, "_suppress_media_hub", False):
            wx.CallAfter(self.open_media_hub_dialog)

    def on_filter_key_down(self, event):
        """Invio/Spazio sul filtro già «Audio e Video» → riapre l'hub."""
        key = event.GetKeyCode()
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE):
            if (
                self.combo_filter.GetSelection() == 2
                and not getattr(self, "_suppress_media_hub", False)
                and not getattr(self, "_media_hub_open", False)
            ):
                wx.CallAfter(self.open_media_hub_dialog)
                return
        event.Skip()

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
        elif ctrl and event.ShiftDown() and key in (ord("M"), ord("m")):
            self.on_media_from_url(None)
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
        elif ctrl and alt and key in (ord("V"), ord("v")):
            self.on_paste_path_from_clipboard(None)
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
        """Sfoglia: cartella/unità OPPURE singolo file (qualsiasi tipo)."""
        choice_dlg = wx.SingleChoiceDialog(
            self,
            "Cosa vuoi impostare come percorso di ricerca?\n"
            "(Per un solo file — PDF, immagine, audio/video o altro — "
            "scegli «Singolo file».)",
            "Sfoglia percorso",
            [
                "Cartella o unità (cerca in tutta la cartella)",
                "Singolo file (qualsiasi tipo: documenti, immagini, audio/video, …)",
            ],
        )
        try:
            choice_dlg.SetSelection(0)
            if choice_dlg.ShowModal() != wx.ID_OK:
                return
            mode = choice_dlg.GetSelection()
        finally:
            choice_dlg.Destroy()

        start = browse_start_dir(self.txt_path.GetValue())
        selected_path = ""
        if mode == 1:
            fd = wx.FileDialog(
                self,
                "Seleziona un file (documenti, immagini, audio/video, …)",
                defaultDir=start,
                wildcard=(
                    "Tutti i file (*.*)|*.*|"
                    "Documenti|*.pdf;*.docx;*.doc;*.odt;*.xlsx;*.epub;*.txt;*.md;"
                    "*.html;*.htm;*.rtf;*.csv;*.log|"
                    "Immagini|*.jpg;*.jpeg;*.png;*.gif;*.bmp;*.tif;*.tiff;*.webp;*.jfif|"
                    "Audio e video|*.mp3;*.m4a;*.wav;*.flac;*.ogg;*.mp4;*.mkv;"
                    "*.webm;*.avi;*.mov;*.m4v|"
                    "PDF (*.pdf)|*.pdf|"
                    "Word (*.docx;*.doc)|*.docx;*.doc|"
                    "Excel (*.xlsx)|*.xlsx|"
                    "EPUB (*.epub)|*.epub"
                ),
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            )
            try:
                if fd.ShowModal() != wx.ID_OK:
                    return
                selected_path = fd.GetPath()
            finally:
                fd.Destroy()
        else:
            dd = wx.DirDialog(
                self,
                "Seleziona cartella o unità",
                defaultPath=start,
                style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
            )
            try:
                if dd.ShowModal() != wx.ID_OK:
                    return
                selected_path = dd.GetPath()
            finally:
                dd.Destroy()

        if not selected_path:
            return
        if selected_path.lower().startswith("file:"):
            norms = normalize_search_targets(selected_path)
            if norms:
                selected_path = norms[0]
        self.apply_search_path(
            selected_path, offer_open=(mode == 1 and os.path.isfile(selected_path))
        )

    def show_shell_target_in_list(
        self, file_path, announce=True, source_url="", keep_fetch_gen=False
    ):
        """Il file scelto con Sfoglia resta una riga dell'elenco, come in Standalone."""
        if not keep_fetch_gen:
            self._url_fetch_gen = getattr(self, "_url_fetch_gen", 0) + 1
        if not file_path or not os.path.exists(file_path):
            return False
        if hasattr(self, "_release_listed_url_media"):
            self._release_listed_url_media(keep_path=file_path)
        file_path = os.path.normpath(file_path)
        is_dir = os.path.isdir(file_path)
        name = os.path.basename(file_path.rstrip("\\/")) or file_path
        ext = "" if is_dir else os.path.splitext(name)[1].lower()
        shown_path = source_url or file_path
        self.txt_path.SetValue(shown_path)
        save_last_path(shown_path)
        try:
            mtime = os.path.getmtime(file_path)
        except Exception:
            mtime = 0
        try:
            sz = os.path.getsize(file_path)
        except Exception:
            sz = 0
        if is_dir:
            size_s = "cartella"
        elif sz >= 1024 * 1024:
            size_s = f"{sz / (1024 * 1024):.1f} MB"
        elif sz >= 1024:
            size_s = f"{sz / 1024:.0f} KB"
        else:
            size_s = f"{sz} byte"
        date_lbl = format_file_date_label(mtime)
        date_suffix = f" {date_lbl}" if date_lbl else ""
        if is_dir:
            prefix = "[CARTELLA]"
            kind = "cartella"
        else:
            prefix = f"[{(ext or '.file').lstrip('.').upper() or 'FILE'}]"
            kind = "file"
        item = {
            "file_path": file_path,
            "file_name": name,
            "prefix": prefix,
            "mtime": mtime,
            "line_number": None,
            "paragraph_index": None,
            "location_info": f"Scelto con Sfoglia{date_suffix}",
            "snippet": f"{kind.capitalize()} scelto con Sfoglia · {size_s}",
        }
        if source_url:
            item["source_url"] = source_url
            item["location_info"] = "Indirizzo Internet"
            item["snippet"] = source_url
        self.current_matches = [item]
        self.current_query = "(Indirizzo Internet)" if source_url else "(File scelto)"
        self._results_ready = True
        try:
            self.txt_filter.ChangeValue("")
        except Exception:
            pass
        self.update_list_display()
        if self.lst_results.GetCount() > 0:
            self.lst_results.SetSelection(0)
            self.lst_results.SetFocus()
        if not announce:
            return True
        if source_url and not is_dir:
            msg = (
                f"L'indirizzo è in elenco: {name}. "
                "Da qui puoi fare altre operazioni."
            )
        elif is_dir:
            msg = (
                f"La cartella è in elenco: {name}. "
                "Da qui puoi fare altre operazioni."
            )
        else:
            msg = (
                f"Il file è in elenco: {name}. "
                "Da qui puoi fare altre operazioni."
            )
        try:
            self.txt_status_progress.SetValue(msg)
        except Exception:
            pass
        rtad_speak(msg)
        return True

    def show_internet_url_in_list(self, url, announce=True, fetch=True):
        """Qualunque URL http(s) resta una riga dell'elenco, come un file scelto."""
        url = (url or "").strip().strip('"').strip("'")
        low = url.lower()
        if not (low.startswith("http://") or low.startswith("https://")):
            return False
        try:
            parsed = urllib.parse.urlparse(url)
            name = urllib.parse.unquote(os.path.basename(parsed.path or "") or "")
            if not name or name in ("/", "."):
                name = parsed.netloc or url
        except Exception:
            name = url
        if len(name) > 80:
            name = name[:77] + "…"
        self.txt_path.SetValue(url)
        save_last_path(url)
        if fetch:
            self._url_fetch_gen = getattr(self, "_url_fetch_gen", 0) + 1
            gen = self._url_fetch_gen
            snippet = "Scaricamento in corso, attendere."
            pending = True
        else:
            gen = 0
            snippet = url
            pending = False
        item = {
            "file_path": url,
            "file_name": name,
            "prefix": "[URL]",
            "mtime": 0,
            "line_number": None,
            "paragraph_index": None,
            "location_info": "Indirizzo Internet",
            "snippet": snippet,
            "internet_url": True,
            "pending_fetch": pending,
            "source_url": url,
        }
        self.current_matches = [item]
        self.current_query = "(Indirizzo Internet)"
        self._results_ready = True
        try:
            self.txt_filter.ChangeValue("")
        except Exception:
            pass
        self.update_list_display()
        if self.lst_results.GetCount() > 0:
            self.lst_results.SetSelection(0)
            self.lst_results.SetFocus()
        if fetch:
            wait = f"Scarico la pagina: {name}. Attendere."
            try:
                self.txt_status_progress.SetValue(wait)
            except Exception:
                pass
            if announce:
                rtad_speak(wait)
            threading.Thread(
                target=self._fetch_internet_url_worker,
                args=(gen, url),
                daemon=True,
            ).start()
            return True
        if not announce:
            return True
        msg = (
            f"L'indirizzo è in elenco: {name}. "
            "Da qui puoi fare altre operazioni."
        )
        try:
            self.txt_status_progress.SetValue(msg)
        except Exception:
            pass
        rtad_speak(msg)
        return True

    def _fetch_internet_url_worker(self, gen, url):
        path, err = save_internet_url_locally(url)
        wx.CallAfter(self._finish_internet_url, gen, url, path, err)

    def _finish_internet_url(self, gen, url, path, err):
        if gen != getattr(self, "_url_fetch_gen", 0):
            return
        if not path or not os.path.isfile(path):
            self.show_internet_url_in_list(url, announce=False, fetch=False)
            msg = err or "Impossibile scaricare la pagina. Puoi aprirla nel browser."
            try:
                self.txt_status_progress.SetValue(msg)
            except Exception:
                pass
            rtad_speak(msg)
            return
        self.show_shell_target_in_list(
            path, announce=True, source_url=url, keep_fetch_gen=True
        )

    def apply_search_path(self, selected_path, *, offer_open=True):
        """Imposta il percorso (Sfoglia / Appunti) e offre apertura se file."""
        if not selected_path:
            return
        if isinstance(selected_path, (list, tuple)):
            paths = [p for p in selected_path if p]
            if not paths:
                return
            if len(paths) == 1:
                selected_path = paths[0]
            else:
                joined = ";".join(paths)
                self.txt_path.SetValue(joined)
                save_last_path(joined)
                rtad_speak(
                    f"Impostati {len(paths)} percorsi dagli Appunti."
                )
                return
        if isinstance(selected_path, str) and selected_path.lower().startswith("file:"):
            norms = normalize_search_targets(selected_path)
            if norms:
                selected_path = norms[0]
        if isinstance(selected_path, str) and selected_path.lower().startswith(
            ("http://", "https://")
        ):
            self.show_internet_url_in_list(selected_path)
            return
        if isinstance(selected_path, str) and os.path.isfile(selected_path):
            jumped = internet_shortcut_target(selected_path)
            if str(jumped).lower().startswith(("http://", "https://")):
                self.show_internet_url_in_list(jumped)
                return
            sniffed = copy_with_sniffed_extension(selected_path)
            if sniffed and sniffed != selected_path:
                selected_path = sniffed
        self.txt_path.SetValue(selected_path)
        save_last_path(selected_path)
        kind = "file" if os.path.isfile(selected_path) else "cartella"
        rtad_speak(f"Percorso impostato ({kind}): {selected_path}.")
        if os.path.isfile(selected_path):
            self.show_shell_target_in_list(selected_path, announce=True)

        ext = (
            os.path.splitext(selected_path)[1].lower()
            if os.path.isfile(selected_path)
            else ""
        )
        if ext == ".cda":
            msg = message_for_cda_path(selected_path)
            rtad_speak(msg)
            dlg = wx.MessageDialog(
                self, msg, "Traccia CD audio (.cda)", wx.OK | wx.ICON_INFORMATION
            )
            dlg.ShowModal()
            dlg.Destroy()
            return

        if _path_looks_like_video_ts(selected_path):
            msg = (
                "Questa cartella sembra un DVD video (VIDEO_TS). "
                "In questa versione RTAD cerca i file dati sul disco "
                "(mp3, pdf, foto, ecc.), non estrae i film dal DVD commerciale."
            )
            rtad_speak(msg)
            dlg = wx.MessageDialog(
                self, msg, "DVD video", wx.OK | wx.ICON_INFORMATION
            )
            dlg.ShowModal()
            dlg.Destroy()
            return

        if not offer_open or not os.path.isfile(selected_path):
            return
        ask = None
        if ext in IMG_EXTS:
            ask = ("image", "Apri ora «Tutto sull'immagine» per questo file?")
        elif ext in MEDIA_EXTS:
            ask = ("media", "Apri ora «Tutto sull'audio/video» per questo file?")
        elif ext in DOC_EXTS:
            ask = ("doc", "Apri ora la lettura di questo documento?")
        if not ask:
            return
        action, msg = ask
        dlg = wx.MessageDialog(
            self, msg, "File selezionato", wx.YES_NO | wx.ICON_QUESTION
        )
        if dlg.ShowModal() == wx.ID_YES:
            dlg.Destroy()
            if action == "image":
                self.show_image_all_dialog(selected_path)
            elif action == "media":
                self.show_media_all_dialog(selected_path)
            else:
                self.read_document_file(selected_path)
        else:
            dlg.Destroy()

    def on_paste_path_from_clipboard(self, event=None):
        """Strumenti / Incolla… / Ctrl+Alt+V: file o path dagli Appunti."""
        paths = paths_from_windows_clipboard()
        if not paths:
            rtad_speak(
                "Negli Appunti non c’è un file o un percorso utilizzabile. "
                "In Esplora seleziona un file e premi Ctrl+C, oppure copia il percorso."
            )
            return
        if len(paths) == 1:
            self.apply_search_path(paths[0], offer_open=os.path.isfile(paths[0]))
        else:
            self.apply_search_path(paths, offer_open=False)

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

    def _write_results_export_txt(self, export_file):
        """Scrive l'elenco risultati in testo (export manuale e auto-salvataggio)."""
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

    def _auto_save_results_if_enabled(self):
        """A fine ricerca completa: salva elenco se l'opzione è attiva. Ritorna il path o ''."""
        if self._stop_search or not load_auto_save_results_preference():
            return ""
        dest_dir = load_last_export_dir() or get_dynamic_desktop_path()
        if not dest_dir or not os.path.isdir(dest_dir):
            dest_dir = get_dynamic_desktop_path()
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        qstem = _safe_filename_stem(
            self.current_query or "ricerca", fallback="ricerca", max_len=40
        )
        path = os.path.join(dest_dir, f"RTAD_risultati_{stamp}_{qstem}.txt")
        if os.path.exists(path):
            stamp2 = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(dest_dir, f"RTAD_risultati_{stamp2}_{qstem}.txt")
        try:
            self._write_results_export_txt(path)
            save_last_export_dir(path)
            return path
        except Exception:
            return ""

    def on_export_results(self, event):
        if not self.current_matches:
            rtad_speak("Nessun risultato da esportare.")
            return

        wildcard_filters = "File di Testo (*.txt)|*.txt|Pagina Web HTML (*.html)|*.html|File CSV per Tabelle (*.csv)|*.csv"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_dir = load_last_export_dir() or get_dynamic_desktop_path()
        dlg = wx.FileDialog(self, message="Esporta Risultati", 
                            defaultDir=default_dir,
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
                    self._write_results_export_txt(export_file)
                
                save_last_export_dir(export_file)
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
        if sel == wx.NOT_FOUND:
            rtad_speak("Nessun elemento selezionato nella lista.")
            return
        if sel not in self.file_map:
            rtad_speak(self.lst_results.GetString(sel))
            return
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
        # URL YouTube/social nel percorso: non è una cartella → hub, non ricerca file
        low_path = target_input.lower()
        if low_path.startswith("http://") or low_path.startswith("https://"):
            is_media_page = False
            try:
                if rtad_media is not None:
                    is_media_page = bool(rtad_media.is_page_media_url(target_input))
            except Exception:
                is_media_page = False
            if filter_mode == 2 or is_media_page:
                self.show_internet_url_in_list(target_input, fetch=False)
                rtad_speak(
                    "Questo URL non va nel percorso di ricerca. "
                    "Apro l'hub analisi audio/video."
                )
                self.open_media_hub_dialog(
                    initial_url=target_input, clear_source=True
                )
                return
            self.show_internet_url_in_list(target_input)
            return
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
        self._results_ready = False
        self.lst_results.Clear()
        # Evita che NVDA dica "sconosciuto" sulla lista vuota durante la scansione
        self.lst_results.Append("Ricerca in corso... attendere prego.")
        self.file_map.clear()
        self._release_listed_url_media()
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
        # Glossario attivo → anche la ricerca nei .rtad.txt (Vlahović ↔ Woltemade)
        try:
            sync_transcript_glossary_to_media()
        except Exception:
            pass
        ocr_dump_all = bool(include_ocr and not terms and filter_mode in (0, 1))
        list_files_only = bool(
            not terms and not ocr_dump_all and filter_mode in (1, 2, 3, 4)
        )
        img_exts = list(IMG_EXTS)
        media_exts = list(MEDIA_EXTS)
        doc_exts = list(DOC_EXTS)
        feed_file_exts = {".rss", ".xml", ".atom"}
        # B0: con filtro Solo AV (o estensione media personalizzata) cerca nei
        # .rtad.txt già salvati accanto ai media, e anche negli orfani
        # (report salvato con altro nome / media assente). Su «Tutti» i
        # .rtad.txt sono già file di testo → evita doppioni.
        b0_wanted = filter_mode == 2 or (
            filter_mode == 4 and custom_ext in media_exts
        )
        b0_reported_sidecars = set()
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

                    is_rtad_sidecar = (file or "").lower().endswith(".rtad.txt")
                    if filter_mode == 1 and ext not in img_exts:
                        continue
                    elif filter_mode == 2 and ext not in media_exts:
                        # P1: Solo AV include anche .rtad.txt orfani (B0)
                        if not (b0_wanted and is_rtad_sidecar):
                            continue
                    elif filter_mode == 3 and ext not in doc_exts and not is_tb:
                        if not (include_zip and ext == ".zip"):
                            continue
                    elif filter_mode == 4 and ext != custom_ext and not mail_for_pdf:
                        # Estensione media: anche .rtad.txt orfani per B0
                        if not (b0_wanted and is_rtad_sidecar):
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
                        is_rtad_sidecar = full.lower().endswith(".rtad.txt")
                        if filter_mode == 1 and ext not in img_exts:
                            continue
                        elif filter_mode == 2 and ext not in media_exts:
                            if not (b0_wanted and is_rtad_sidecar):
                                continue
                        elif filter_mode == 3 and ext not in doc_exts and not is_tb:
                            if not (include_zip and ext == ".zip"):
                                continue
                        elif filter_mode == 4 and ext != custom_ext and not mail_for_pdf:
                            if not (b0_wanted and is_rtad_sidecar):
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
                            is_rtad_sidecar = (file or "").lower().endswith(".rtad.txt")
                            if filter_mode == 1 and ext not in img_exts:
                                continue
                            elif filter_mode == 2 and ext not in media_exts:
                                if not (b0_wanted and is_rtad_sidecar):
                                    continue
                            elif filter_mode == 3 and ext not in doc_exts and not is_tb:
                                if not (include_zip and ext == ".zip"):
                                    continue
                            elif filter_mode == 4 and ext != custom_ext and not mail_for_pdf:
                                if not (b0_wanted and is_rtad_sidecar):
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
                is_rtad_sidecar = (file_name or "").lower().endswith(".rtad.txt")
                # B0: i video grandi non vanno letti, ma il sidecar .rtad.txt sì
                b0_candidate = bool(
                    b0_wanted
                    and terms
                    and ext in media_exts
                    and rtad_media is not None
                )
                # P1 orfani: .rtad.txt in coda Solo AV (nome diverso dal media / media assente)
                if (
                    b0_wanted
                    and terms
                    and is_rtad_sidecar
                    and rtad_media is not None
                    and hasattr(rtad_media, "search_rtad_txt_file")
                ):
                    side_key = os.path.normcase(os.path.normpath(file_path))
                    if side_key not in b0_reported_sidecars:
                        try:
                            orphan_hits = rtad_media.search_rtad_txt_file(
                                file_path,
                                terms,
                                text_matches_fn=text_matches_terms,
                            )
                        except Exception as e:
                            logging.debug(f"B0 orfano fallito su {file_path}: {e}")
                            orphan_hits = []
                        for h in orphan_hits or []:
                            loc = h.get("location_label") or "Report media"
                            raw_matches.append({
                                "file_path": file_path,
                                "file_name": file_name,
                                "prefix": "[AV]",
                                "mtime": mtime,
                                "line_number": h.get("line_number"),
                                "paragraph_index": None,
                                "location_info": f"{loc}{file_date_suffix}",
                                "snippet": h.get("snippet") or "",
                            })
                            found_in_content = True
                        if found_in_content:
                            b0_reported_sidecars.add(side_key)
                    if name_matched and not found_in_content:
                        raw_matches.append({
                            "file_path": file_path,
                            "file_name": file_name,
                            "prefix": "[AV]",
                            "mtime": mtime,
                            "line_number": None,
                            "paragraph_index": None,
                            "location_info": f"Nome File{file_date_suffix}",
                            "snippet": f"Corrispondenza: '{file_name}'",
                        })
                    bump_progress()
                    continue
                if not allow_content and not name_matched and not b0_candidate:
                    # Le caselle di posta non arrivano qui (content_scan_allowed=True)
                    skipped_large_files += 1
                    logging.info(
                        f"File troppo grande per scansione contenuto "
                        f"({safe_file_size(file_path)} byte): {file_path}"
                    )
                    bump_progress()
                    continue
                if not allow_content and not b0_candidate:
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
                        if ext in (".html", ".htm"):
                            text_data = strip_html_to_text(text_data)
                        lines = text_data.split("\n")
                        use_glossary = bool(
                            (file_name or "").lower().endswith(".rtad.txt")
                            and rtad_media is not None
                            and hasattr(rtad_media, "text_matches_with_glossary")
                        )
                        for idx, line in enumerate(lines):
                            if use_glossary:
                                line_hit = rtad_media.text_matches_with_glossary(
                                    line, terms, text_matches_terms
                                )
                            else:
                                line_hit = text_matches_terms(line, terms)
                            if line_hit:
                                start_i = max(0, idx - 2)
                                end_i = min(len(lines), idx + 3)
                                snippet = "".join(lines[start_i:end_i]).strip()
                                loc_info = f"Riga {idx + 1}{file_date_suffix}"
                                if use_glossary:
                                    try:
                                        glossed_snip = rtad_media.apply_transcript_glossary(
                                            snippet
                                        )
                                        if glossed_snip != snippet:
                                            snippet = glossed_snip
                                            loc_info = (
                                                f"Riga {idx + 1} (glossario)"
                                                f"{file_date_suffix}"
                                            )
                                    except Exception:
                                        pass
                                raw_matches.append({
                                    "file_path": file_path,
                                    "file_name": file_name,
                                    "prefix": prefix,
                                    "mtime": mtime,
                                    "line_number": idx + 1,
                                    "location_info": loc_info,
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
                elif ext == ".xlsx" and allow_content:
                    rows, timed_out = run_with_timeout(
                        lambda: extract_rows_from_xlsx(file_path),
                        FILE_CONTENT_SOFT_TIMEOUT_SEC,
                        default=[],
                    )
                    if timed_out:
                        rows = []
                    for row in rows or []:
                        p_text = (row.get("text") or "").strip()
                        if not p_text or not text_matches_terms(p_text, terms):
                            continue
                        sheet = (row.get("sheet") or "Foglio").strip() or "Foglio"
                        row_n = int(row.get("row") or 0) or None
                        if row_n:
                            loc = f"Foglio «{sheet}» riga {row_n}{file_date_suffix}"
                        else:
                            loc = f"Foglio «{sheet}»{file_date_suffix}"
                        raw_matches.append({
                            "file_path": file_path,
                            "file_name": file_name,
                            "prefix": "[XLSX]",
                            "mtime": mtime,
                            "line_number": row_n,
                            "paragraph_index": row_n,
                            "xlsx_sheet": sheet,
                            "location_info": loc,
                            "snippet": p_text[:400],
                        })
                        found_in_content = True
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

                # B0 (1.7.2+): parole dette già trascritte nel .rtad.txt accanto al media
                if (
                    not found_in_content
                    and b0_candidate
                ):
                    try:
                        media_hits = rtad_media.search_media_sidecar(
                            file_path,
                            terms,
                            text_matches_fn=text_matches_terms,
                        )
                    except Exception as e:
                        logging.debug(f"B0 sidecar fallito su {file_path}: {e}")
                        media_hits = []
                    for h in media_hits or []:
                        side = h.get("sidecar_path") or ""
                        if not side:
                            continue
                        side_key = os.path.normcase(os.path.normpath(side))
                        if side_key in b0_reported_sidecars:
                            continue
                        loc = h.get("location_label") or "Report media"
                        raw_matches.append({
                            "file_path": side,
                            "file_name": file_name,
                            "prefix": "[AV]",
                            "mtime": mtime,
                            "line_number": h.get("line_number"),
                            "paragraph_index": None,
                            "location_info": f"{loc}{file_date_suffix}",
                            "snippet": h.get("snippet") or "",
                            "media_path": file_path,
                        })
                        b0_reported_sidecars.add(side_key)
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

    def _apply_results_sort(self, sort_type=None):
        """Ordina current_matches come in lista (stesso criterio dell'auto-salvataggio)."""
        if sort_type is None:
            sort_type = getattr(self, "current_sort", None) or "recent_first"
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

    def sort_and_display_matches(self, sort_type="recent_first"):
        self._apply_results_sort(sort_type)
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
        # Lista vuota: una riga vera, così NVDA non dice «sconosciuto».
        if self.lst_results.GetCount() == 0:
            if searching:
                msg = "Ricerca in corso... attendere prego."
            elif not getattr(self, "_results_ready", False):
                msg = "Nessuna ricerca avviata."
            elif filter_text:
                msg = "Nessun risultato con questo filtro."
            elif self._stop_search:
                msg = "Ricerca interrotta: nessun risultato conservato."
            else:
                msg = "Nessun risultato trovato."
            self.lst_results.Append(msg)
            self.lst_results.SetSelection(0)

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
        # Ordina prima del salvataggio: il .txt replica l'ordine della lista risultati
        try:
            self._apply_results_sort(getattr(self, "current_sort", None) or "recent_first")
        except Exception:
            pass
        saved_note = ""
        if not self._stop_search:
            try:
                saved_path = self._auto_save_results_if_enabled()
                if saved_path:
                    saved_note = f" Risultati salvati in {saved_path}."
            except Exception:
                pass
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
                f"{saved_note}"
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
            rtad_speak(
                f"Ricerca completata. Trovati {matches} risultati ordinati dal più recente."
                f"{feed_speak}{saved_note}"
            )
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
        self._results_ready = True

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

    def on_gemini_conversations(self, event=None):
        """Elenco di tutte le chat Gemini, anche a programma appena aperto."""
        if rtad_chat is None:
            speak_accessible("Modulo conversazione non disponibile.")
            return
        try:
            rows = rtad_chat.list_all_saved(CONFIG_DIR)
        except Exception as exc:
            speak_accessible(f"Cronologia non disponibile: {exc}")
            return
        if not rows:
            speak_accessible(
                "Nessuna conversazione Gemini salvata. "
                "Alt+Q ne apre una senza file, oppure Chiedi a Gemini su un file."
            )
            return
        dlg = GeminiChatHistoryDialog(
            self, rows, title="Conversazioni Gemini"
        )
        try:
            if dlg.ShowModal() != wx.ID_OK or not dlg.choice:
                return
            action, row = dlg.choice
        finally:
            dlg.Destroy()
        if action == "delete":
            try:
                rtad_chat.delete_saved(row.get("path") or "")
            except Exception as exc:
                speak_accessible(f"Eliminazione non riuscita: {exc}")
                return
            speak_accessible("Conversazione eliminata.")
            return
        open_saved_gemini_chat(row.get("path") or "", parent=self)

    def on_result_gemini(self, file_path):
        """Dal risultato: riprende la chat salvata, oppure ne apre una sul file."""
        if rtad_chat is None:
            speak_accessible("Modulo conversazione non disponibile.")
            return
        path = (file_path or "").strip()
        if not path:
            return
        if path.lower().endswith(".chat.txt"):
            found = ""
            try:
                found = rtad_chat.find_export(CONFIG_DIR, path)
            except Exception:
                found = ""
            if found:
                open_saved_gemini_chat(found, parent=self)
                return
            speak_accessible(
                "Nessuna conversazione collegata a questo testo. "
                "Apri Conversazioni Gemini dal menù Strumenti."
            )
            return
        if path.lower().endswith(".rtad.txt"):
            open_gemini_chat_from_report(path, parent=self)
            return
        if rtad_chat.has_saved(CONFIG_DIR, path):
            open_saved_gemini_chat(
                rtad_chat.saved_json_path(CONFIG_DIR, path), parent=self
            )
            return
        ext = os.path.splitext(path)[1].lower()
        if ext in IMG_EXTS:
            open_gemini_chat("image", path, parent=self)
            return
        if ext in MEDIA_EXTS:
            open_gemini_chat(
                "document",
                path,
                struct={
                    "body": "",
                    "plain": "",
                    "outline": [],
                    "message": (
                        "Nessuna trascrizione già aperta. "
                        "Per il parlato, genera prima il report audio/video "
                        "e poi chiedi da quella finestra."
                    ),
                },
                parent=self,
            )
            return
        open_gemini_chat("document", path, parent=self)

    def open_selected_file(self):
        sel = self.lst_results.GetSelection()
        if sel == wx.NOT_FOUND or sel not in self.file_map:
            if sel != wx.NOT_FOUND:
                speak_accessible(self.lst_results.GetString(sel))
            return
        if sel != wx.NOT_FOUND and sel in self.file_map:
            item = self.file_map[sel]
            if item.get("pending_download"):
                rtad_speak(item.get("file_name") or "Download audio/video in corso…")
                return
            file_to_open = item["file_path"]
            if item.get("internet_url") or str(file_to_open).lower().startswith(
                ("http://", "https://")
            ):
                try:
                    webbrowser.open(file_to_open)
                    rtad_speak("Pagina aperta nel browser.")
                except Exception:
                    rtad_speak("Impossibile aprire la pagina nel browser.")
                return
            line_num = item.get("line_number")
            ext = os.path.splitext(file_to_open)[1].lower()
            prefix = item.get("prefix", "")

            if (
                file_to_open.lower().endswith(".chat.txt")
                and rtad_chat is not None
            ):
                found = ""
                try:
                    found = rtad_chat.find_export(CONFIG_DIR, file_to_open)
                except Exception:
                    found = ""
                if found:
                    open_saved_gemini_chat(found, parent=self)
                    return

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

            if ext == ".xlsx":
                loc = item.get("location_info") or "foglio Excel"
                sheet = (item.get("xlsx_sheet") or "").strip()
                row_n = item.get("line_number") or item.get("paragraph_index")
                rtad_speak(
                    f"Apertura Excel su {loc}: {os.path.basename(file_to_open)}"
                )
                open_excel_at_row(file_to_open, row_n, sheet)
                return
            
            if ext == ".eml":
                rtad_speak(f"Apertura email nel lettore interno: {os.path.basename(file_to_open)}")
                viewer = EmlViewerFrame(self, file_to_open, self.current_query)
                viewer.Show()
                return

            # Report media: con glossario attivo corregge il .rtad.txt prima di aprirlo
            gloss_note = ""
            if (file_to_open or "").lower().endswith(".rtad.txt"):
                try:
                    if apply_glossary_to_rtad_txt_file(file_to_open):
                        gloss_note = " File aggiornato con il glossario."
                except Exception as e:
                    logging.debug(f"Glossario in apertura: {e}")

            if line_num:
                rtad_speak(
                    f"Apertura alla riga {line_num}: "
                    f"{os.path.basename(file_to_open)}.{gloss_note}"
                )
                jump_to_line_in_editor(file_to_open, line_num)
            else:
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "open", file_to_open, None, None, 1)
                    rtad_speak(
                        f"Apertura file: {os.path.basename(file_to_open)}.{gloss_note}"
                    )
                except Exception:
                    rtad_speak("Impossibile aprire il file selezionato.")

    def open_page_in_browser(self, url):
        try:
            webbrowser.open(url)
            rtad_speak("Pagina aperta nel browser.")
        except Exception:
            rtad_speak("Impossibile aprire la pagina nel browser.")

    def on_context_menu(self, event):
        sel = self.lst_results.GetSelection()
        if sel == wx.NOT_FOUND or sel not in self.file_map:
            if sel != wx.NOT_FOUND:
                speak_accessible(self.lst_results.GetString(sel))
            return

        item_data = self.file_map[sel]
        if item_data.get("pending_download"):
            rtad_speak(item_data.get("file_name") or "Download audio/video in corso…")
            return
        if item_data.get("pending_fetch"):
            rtad_speak("Scaricamento in corso, attendere.")
            return
        file_path = item_data["file_path"]
        if item_data.get("internet_url") or str(file_path).lower().startswith(
            ("http://", "https://")
        ):
            menu = wx.Menu()
            item_open = menu.Append(wx.ID_ANY, "Apri pagina nel browser\tINVIO")
            menu.Bind(wx.EVT_MENU, lambda e: self.open_selected_file(), item_open)
            self.PopupMenu(menu)
            menu.Destroy()
            return
        snippet = item_data["snippet"]

        menu = wx.Menu()
        item_open = menu.Append(wx.ID_ANY, "Apri File (alla riga esatta)\tINVIO")
        item_browser = None
        source_url = item_data.get("source_url") or ""
        if source_url:
            item_browser = menu.Append(wx.ID_ANY, "Apri pagina nel browser")
        item_gemini = None
        if rtad_chat is not None and file_path and os.path.isfile(file_path):
            ext_g = os.path.splitext(file_path)[1].lower()
            chatable = (
                ext_g in IMG_EXTS
                or ext_g in MEDIA_EXTS
                or ext_g in (
                    ".pdf", ".docx", ".odt", ".xlsx",
                    ".txt", ".md", ".csv", ".log", ".rtf",
                    ".html", ".htm", ".epub",
                )
                or file_path.lower().endswith(".chat.txt")
            )
            if chatable:
                if file_path.lower().endswith(".chat.txt"):
                    linked = ""
                    try:
                        linked = rtad_chat.find_export(CONFIG_DIR, file_path)
                    except Exception:
                        linked = ""
                    if linked:
                        item_gemini = menu.Append(
                            wx.ID_ANY, "Apri conversazione &Gemini…"
                        )
                elif rtad_chat.has_saved(
                    CONFIG_DIR,
                    rtad_chat.chat_anchor_for_report(file_path)
                    if file_path.lower().endswith(".rtad.txt")
                    else file_path,
                ):
                    item_gemini = menu.Append(
                        wx.ID_ANY, "Riprendi conversazione &Gemini…"
                    )
                else:
                    item_gemini = menu.Append(wx.ID_ANY, "Chiedi a &Gemini…")
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
        item_all = None
        item_ocr = None
        item_media_all = None
        item_media_tech = None
        item_media_desc = None
        media_for_actions = (
            item_data.get("media_path")
            if item_data.get("media_path")
            and os.path.isfile(item_data.get("media_path") or "")
            else file_path
        )
        media_ext_for_actions = os.path.splitext(media_for_actions)[1].lower()
        is_media_result = (
            ext_sel in MEDIA_EXTS
            or media_ext_for_actions in MEDIA_EXTS
            or str(item_data.get("prefix", "")).startswith("[MEDIA")
            or str(item_data.get("prefix", "")) == "[AV]"
        )
        if is_img_result:
            menu.AppendSeparator()
            item_all = menu.Append(wx.ID_ANY, "Tutto sull'immagine…")
            item_ocr = menu.Append(wx.ID_ANY, "Leggi testo nell'immagine (OCR)")
            item_alt = menu.Append(wx.ID_ANY, "Alt-text breve")
            item_describe = menu.Append(wx.ID_ANY, "Descrivi immagine (dettagliata)")
            item_alt_long = menu.Append(wx.ID_ANY, "Alt-text + descrizione")
            item_labels = menu.Append(wx.ID_ANY, "Etichette e oggetti")
            item_tech = menu.Append(wx.ID_ANY, "Scheda tecnica immagine")
        elif is_media_result:
            menu.AppendSeparator()
            item_media_all = menu.Append(wx.ID_ANY, "Tutto sull'audio/video…")
            item_media_desc = menu.Append(wx.ID_ANY, "Riassunto audio/video")
            item_media_tech = menu.Append(wx.ID_ANY, "Scheda tecnica audio/video")
        elif is_pdf_result:
            menu.AppendSeparator()
            item_pdf_describe = menu.Append(
                wx.ID_ANY, "Descrivi immagine da PDF"
            )
        item_read_doc = None
        item_copy_doc = None
        is_shell_doc = ext_sel in (
            ".pdf",
            ".docx",
            ".odt",
            ".txt",
            ".md",
            ".csv",
            ".log",
            ".rtf",
            ".html",
            ".htm",
            ".epub",
        ) or is_pdf_result
        if is_shell_doc and not is_img_result:
            if not is_pdf_result:
                menu.AppendSeparator()
            item_read_doc = menu.Append(
                wx.ID_ANY, "Leggi documento (struttura e testo)"
            )
            item_copy_doc = menu.Append(
                wx.ID_ANY, "Copia testo del documento"
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
        if item_browser is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e, u=source_url: self.open_page_in_browser(u),
                item_browser,
            )
        if item_gemini is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e, p=file_path: self.on_result_gemini(p),
                item_gemini,
            )
        if item_open_msg is not None:
            self.Bind(wx.EVT_MENU, lambda e: self.open_selected_mail_message(), item_open_msg)
        if item_save_att is not None:
            self.Bind(wx.EVT_MENU, lambda e: self.save_attachment_pdf(item_data), item_save_att)
        self.Bind(wx.EVT_MENU, lambda e: wx.CallLater(250, self.speak_selected_preview), item_preview)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_snippet_to_clipboard(snippet), item_copy_snippet)
        path_to_copy = source_url or file_path
        self.Bind(wx.EVT_MENU, lambda e: self.copy_path_to_clipboard(path_to_copy), item_copy_path)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_text_to_clipboard(item_data, mode="clean"), item_copy_text)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_text_to_clipboard(item_data, mode="full"), item_copy_ocr_full)
        if item_all is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.show_image_all_dialog(file_path),
                item_all,
            )
        if item_ocr is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.show_image_analysis(file_path, mode="ocr"),
                item_ocr,
            )
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
        if item_media_all is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e, p=media_for_actions: self.show_media_all_dialog(p),
                item_media_all,
            )
        if item_media_desc is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e, p=media_for_actions: self.show_media_analysis(
                    p, mode="describe"
                ),
                item_media_desc,
            )
        if item_media_tech is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e, p=media_for_actions: self.show_media_analysis(
                    p, mode="tech"
                ),
                item_media_tech,
            )
        if item_pdf_describe is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.describe_image_from_pdf(file_path),
                item_pdf_describe,
            )
        if item_read_doc is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e: self.read_document_file(file_path),
                item_read_doc,
            )
        if item_copy_doc is not None:
            self.Bind(
                wx.EVT_MENU,
                lambda e, p=file_path: self.copy_document_text_file(p),
                item_copy_doc,
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

    def _show_document_structure_frame(self, file_path, struct):
        """Mostra il lettore strutturato (tiene riferimento anti-GC)."""
        if not hasattr(self, "_doc_struct_frames") or self._doc_struct_frames is None:
            self._doc_struct_frames = []
        frm = DocumentStructureFrame(None, file_path, struct)

        def _cleanup(evt, frame=frm):
            try:
                if frame in self._doc_struct_frames:
                    self._doc_struct_frames.remove(frame)
            except Exception:
                pass
            evt.Skip()

        frm.Bind(wx.EVT_CLOSE, _cleanup)
        self._doc_struct_frames.append(frm)
        frm.Show()
        frm.Raise()

    def _offer_pdf_scan_describe(self, file_path, struct=None):
        """PDF senza testo ma con immagini: proponi Descrivi, altrimenti lettore."""
        name = os.path.basename(file_path) if file_path else "PDF"
        extra = ""
        if struct and (struct.get("message") or "").strip():
            extra = (struct.get("message") or "").strip() + "\n\n"
        dlg = wx.MessageDialog(
            self,
            f"{extra}"
            f"«{name}» non contiene testo estraibile ma contiene immagini "
            f"(probabile scansione).\n\n"
            f"Vuoi descrivere ora l'immagine principale?\n"
            f"Sì = Descrivi immagine da PDF\n"
            f"No = apri comunque il lettore documento",
            "PDF scansione",
            wx.YES_NO | wx.ICON_QUESTION,
        )
        try:
            dlg.SetYesNoLabels("&Descrivi immagine", "&Apri lettore")
        except Exception:
            pass
        try:
            choice = dlg.ShowModal()
        finally:
            dlg.Destroy()
        if choice == wx.ID_YES:
            self.describe_image_from_pdf(file_path, mode="describe")
            return
        if struct is not None:
            self._show_document_structure_frame(file_path, struct)
            rtad_speak(
                "Lettore aperto senza testo. "
                "Puoi usare Strumenti → Descrivi immagine da PDF in qualsiasi momento."
            )
        else:
            rtad_speak(
                "Nessun testo estraibile. "
                "Usa Strumenti → Descrivi immagine da PDF."
            )

    def read_document_file(self, file_path):
        """Apre lettore strutturato (DOCX/EPUB/PDF) o testo piano (altro)."""
        if not file_path or not os.path.isfile(file_path):
            rtad_speak("File non trovato.")
            return
        name = os.path.basename(file_path)
        rtad_speak(f"Lettura di «{name}» in corso…")

        def _work():
            if file_path.lower().endswith(".rtad.txt"):
                apply_glossary_to_rtad_txt_file(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            if rtad_docstruct is not None and ext in (".docx", ".epub", ".doc", ".pdf"):
                try:
                    struct = rtad_docstruct.extract_document_structure(file_path)
                except Exception as e:
                    struct = {
                        "ok": False,
                        "has_structure": False,
                        "outline": [],
                        "links": [],
                        "body": "",
                        "plain": "",
                        "message": f"Errore analisi struttura: {e}",
                    }
                body = (struct.get("body") or struct.get("plain") or "").strip()
                if not body and ext in (".docx", ".epub", ".pdf"):
                    plain = extract_document_text(file_path)
                    if plain:
                        struct["body"] = plain
                        struct["plain"] = plain
                        struct["ok"] = True
                        body = plain
                if ext == ".pdf" and body and hasattr(
                    rtad_docstruct, "enrich_pdf_structure_with_text"
                ):
                    try:
                        struct = rtad_docstruct.enrich_pdf_structure_with_text(
                            struct, body
                        )
                        body = (
                            struct.get("body") or struct.get("plain") or body
                        ).strip()
                    except Exception:
                        pass
                if body or struct.get("has_structure") or (
                    struct.get("message") and ext in (".doc", ".pdf")
                ):
                    if (
                        not body
                        and not struct.get("has_structure")
                        and ext == ".pdf"
                        and get_best_pdf_page_image(file_path)
                    ):
                        wx.CallAfter(
                            self._offer_pdf_scan_describe, file_path, struct
                        )
                        return
                    wx.CallAfter(
                        self._show_document_structure_frame, file_path, struct
                    )
                    if not body and not struct.get("has_structure"):
                        wx.CallAfter(
                            rtad_speak,
                            struct.get("message") or "Nessun testo estraibile.",
                        )
                    return

            text = extract_document_text(file_path)
            if not (text or "").strip():
                if ext == ".pdf" and get_best_pdf_page_image(file_path):
                    wx.CallAfter(self._offer_pdf_scan_describe, file_path, None)
                    return
                msg = (
                    "Nessun testo estraibile da questo file "
                    "(formato non supportato, protetto o vuoto)."
                )
                wx.CallAfter(rtad_speak, msg)
                return

            def _show():
                self._show_document_structure_frame(
                    file_path,
                    {
                        "ok": True,
                        "has_structure": False,
                        "outline": [],
                        "links": [],
                        "body": text,
                        "plain": text,
                        "message": "Testo del documento.",
                    },
                )

            wx.CallAfter(_show)

        threading.Thread(target=_work, daemon=True).start()

    def copy_document_text_file(self, file_path):
        """Copia negli appunti il testo estratto dal documento."""
        if not file_path or not os.path.isfile(file_path):
            rtad_speak("File non trovato.")
            return
        name = os.path.basename(file_path)
        rtad_speak(f"Estrazione testo da «{name}»…")

        def _work():
            if file_path.lower().endswith(".rtad.txt"):
                apply_glossary_to_rtad_txt_file(file_path)
            text = extract_document_text(file_path)
            if rtad_docstruct is not None and hasattr(
                rtad_docstruct, "format_document_copy"
            ):
                try:
                    text = rtad_docstruct.format_document_copy(file_path, text)
                except Exception:
                    pass
            if not (text or "").strip():
                ext = os.path.splitext(file_path)[1].lower()
                if ext == ".pdf" and get_best_pdf_page_image(file_path):
                    msg = (
                        "PDF scansionato: nessun testo da copiare. "
                        "Usa «Descrivi immagini del PDF» o Copia Immagine dai risultati."
                    )
                else:
                    msg = "Nessun testo da copiare da questo file."

                def _say(m=msg):
                    try:
                        self.txt_status_progress.SetValue(m)
                    except Exception:
                        pass
                    rtad_speak(m)

                wx.CallAfter(_say)
                return

            def _copy():
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.TextDataObject(text))
                    wx.TheClipboard.Close()
                    done = "Testo del documento copiato negli appunti."
                    try:
                        self.txt_status_progress.SetValue(done)
                    except Exception:
                        pass
                    rtad_speak(done)
                else:
                    fail = "Impossibile aprire gli appunti."
                    try:
                        self.txt_status_progress.SetValue(fail)
                    except Exception:
                        pass
                    rtad_speak(fail)

            wx.CallAfter(_copy)

        threading.Thread(target=_work, daemon=True).start()

    def show_image_analysis(
        self,
        file_path,
        mode="describe",
        copy_only=False,
        delete_after=False,
        sections=None,
        *,
        source_path="",
    ):
        """Descrivi / etichette / scheda tecnica su un file immagine."""
        run_image_analysis(
            self,
            file_path,
            mode=mode,
            copy_only=copy_only,
            delete_after=delete_after,
            speak=rtad_speak,
            sections=sections,
            source_path=source_path,
        )

    def show_image_all_dialog(self, file_path):
        """Dialogo unico «Tutto sull'immagine» → subito analisi dopo Avvia."""
        if not file_path or not os.path.isfile(file_path):
            rtad_speak("File immagine non trovato.")
            return
        dlg = ImageSectionsDialog(
            self,
            title="Tutto sull'immagine",
            context_label=os.path.basename(file_path),
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            sel = dlg.selections()
        finally:
            dlg.Destroy()
        # Solo OCR → stessa finestra dedicata (gemello SA / percorso papà)
        only_ocr = bool(sel.get("include_ocr")) and not any(
            [
                sel.get("include_alt"),
                sel.get("include_describe"),
                sel.get("include_labels"),
                sel.get("include_tech"),
            ]
        )
        if only_ocr:
            self.show_image_analysis(file_path, mode="ocr")
        else:
            self.show_image_analysis(file_path, mode="all", sections=sel)

    def _pick_image_path_for_tools(self):
        """Risultato selezionato se immagine, altrimenti FileDialog."""
        path = ""
        sel = self.lst_results.GetSelection()
        if sel != wx.NOT_FOUND and sel in self.file_map:
            cand = self.file_map[sel].get("file_path") or ""
            ext = os.path.splitext(cand)[1].lower()
            if cand and os.path.isfile(cand) and ext in IMG_EXTS:
                path = cand
        if path:
            return path
        with wx.FileDialog(
            self,
            "Scegli un'immagine",
            wildcard=(
                "Immagini|"
                "*.jpg;*.jpeg;*.png;*.gif;*.bmp;*.tif;*.tiff;*.webp;*.jfif|"
                "Tutti i file|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fd:
            if fd.ShowModal() != wx.ID_OK:
                return ""
            return fd.GetPath()

    def on_image_all_dialog(self, event=None):
        """Strumenti → Tutto sull'immagine."""
        path = self._pick_image_path_for_tools()
        if path:
            self.show_image_all_dialog(path)

    def on_image_ocr_dialog(self, event=None):
        """Strumenti → Leggi testo nell'immagine (OCR) — gemello SA."""
        path = self._pick_image_path_for_tools()
        if path:
            self.show_image_analysis(path, mode="ocr")

    def open_media_hub_dialog(
        self,
        initial_path="",
        initial_url="",
        preset_sections=None,
        *,
        clear_source=False,
    ):
        """Hub unificato: filtro Audio/Video, Strumenti, scorciatoia URL."""
        if getattr(self, "_media_hub_open", False):
            return
        path = "" if clear_source else (initial_path or "").strip()
        if not clear_source and not path:
            sel = self.lst_results.GetSelection()
            if sel != wx.NOT_FOUND and sel in self.file_map:
                cand = self.file_map[sel].get("file_path") or ""
                ext = os.path.splitext(cand)[1].lower()
                if cand and os.path.isfile(cand) and ext in MEDIA_EXTS:
                    path = cand
        presets = preset_sections
        if presets is None:
            presets = getattr(self, "_last_media_sections", None)
        self.show_media_all_dialog(
            path if path and os.path.isfile(path) else "",
            delete_after=False,
            initial_url=initial_url,
            show_source=True,
            preset_sections=presets,
        )

    def show_media_all_dialog(
        self,
        file_path,
        delete_after=False,
        initial_url="",
        show_source=True,
        preset_sections=None,
    ):
        """Dialogo hub «Tutto sull'audio/video» → analisi dopo Avvia."""
        if getattr(self, "_media_hub_open", False):
            return
        self._media_hub_open = True
        dlg = MediaSectionsDialog(
            self,
            title="Tutto sull'audio/video",
            context_label=os.path.basename(file_path) if file_path else "",
            show_source=show_source,
            initial_path=file_path or "",
            initial_url=initial_url or "",
            preset_sections=preset_sections,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                if delete_after and file_path and rtad_media is not None:
                    try:
                        rtad_media.cleanup_temp_media(file_path)
                    except Exception:
                        pass
                if self.combo_filter.GetSelection() == 2:
                    rtad_speak(
                        "Hub chiuso. Per riaprirlo: Strumenti → "
                        "Tutto sull'audio/video, oppure Invio sul filtro."
                    )
                return
            sel = dlg.selections()
        finally:
            dlg.Destroy()
            self._media_hub_open = False

        self._last_media_sections = {
            "include_tech": bool(sel.get("include_tech", True)),
            "include_describe": bool(sel.get("include_describe", True)),
            "include_transcript": bool(sel.get("include_transcript", False)),
            "transcript_engine": sel.get("transcript_engine") or "gemini",
            "include_timestamps": bool(sel.get("include_timestamps", False)),
            "translate_transcript": bool(sel.get("translate_transcript", False)),
            "translate_lang": sel.get("translate_lang") or "it",
        }
        url = (sel.get("url") or "").strip()
        path = (sel.get("file_path") or file_path or "").strip()
        if url:
            if rtad_media is None:
                rtad_speak("Modulo media non disponibile.")
                return
            if getattr(self, "_media_analysis_busy", False):
                rtad_speak(
                    "Analisi già in corso. Attendi il risultato, "
                    "poi potrai avviarne un'altra."
                )
                self.open_media_hub_dialog(
                    initial_url=url, preset_sections=self._last_media_sections
                )
                return
            rtad_speak("Download audio/video in corso…")
            self._set_media_progress(3, "Download audio/video…")

            def _work():
                res = rtad_media.materialize_media_from_url(
                    url, on_progress=self._media_progress_cb
                )
                if not res.get("ok") or not res.get("path"):
                    err = res.get("error") or "Download media non riuscito."

                    def _fail():
                        self._set_media_progress(0, err)
                        rtad_speak(err)
                        self.open_media_hub_dialog(
                            initial_url=url,
                            preset_sections=self._last_media_sections,
                        )

                    wx.CallAfter(_fail)
                    return
                def _open_downloaded(path=res["path"], sections=sel):
                    self.show_media_analysis(
                        path, mode="all", sections=sections, delete_after=True
                    )

                wx.CallAfter(_open_downloaded)

            threading.Thread(target=_work, daemon=True).start()
            return

        if not path or not os.path.isfile(path):
            rtad_speak("File audio/video non trovato.")
            self.open_media_hub_dialog(
                initial_url=url, preset_sections=self._last_media_sections
            )
            return
        if getattr(self, "_media_analysis_busy", False):
            rtad_speak(
                "Analisi già in corso. Attendi il risultato, "
                "poi potrai avviarne un'altra."
            )
            self.open_media_hub_dialog(preset_sections=self._last_media_sections)
            return
        self.show_media_analysis(
            path, mode="all", sections=sel, delete_after=delete_after
        )

    def on_media_all_dialog(self, event=None):
        """Strumenti → hub audio/video (file e/o URL + sezioni)."""
        self.open_media_hub_dialog()

    def on_ytdlp_tools(self, event=None):
        """Strumenti → verifica / aggiorna yt-dlp."""
        if rtad_media is None:
            rtad_speak("Modulo media non disponibile.")
            return
        st = rtad_media.check_ytdlp_status()
        msg = st.get("message") or "Stato yt-dlp sconosciuto."
        buttons = wx.YES_NO | wx.CANCEL | wx.ICON_INFORMATION
        dlg = wx.MessageDialog(
            self,
            msg
            + "\n\nSì = aggiorna ora (yt-dlp -U)\n"
            "No = chiudi senza aggiornare\n"
            "Annulla = chiudi",
            "yt-dlp",
            buttons,
        )
        dlg.SetYesNoLabels("&Aggiorna", "&Chiudi")
        choice = dlg.ShowModal()
        dlg.Destroy()
        if choice != wx.ID_YES:
            rtad_speak(msg)
            return
        rtad_speak("Aggiornamento yt-dlp in corso…")

        def _work():
            res = rtad_media.update_ytdlp()
            wx.CallAfter(rtad_speak, res.get("message") or "Fatto.")

        threading.Thread(target=_work, daemon=True).start()

    def on_media_from_url(self, event=None):
        """Scorciatoia → stesso hub, focus sul campo URL."""
        self.open_media_hub_dialog()

    def _media_progress_cb(self, percent, message):
        """Callback thread-safe da rtad_media → UI principale."""
        wx.CallAfter(self._set_media_progress, percent, message)

    def _set_media_progress(self, percent, message):
        """Aggiorna gauge + stato (come la ricerca); annuncia solo le fasi chiave."""
        try:
            pct = int(max(0, min(100, int(percent or 0))))
        except Exception:
            pct = 0
        msg = (message or "").strip() or "In corso…"
        text = f"Audio/video: {msg} ({pct}%)"
        try:
            if hasattr(self, "gauge") and self.gauge:
                self.gauge.SetValue(pct)
            if hasattr(self, "txt_status_progress") and self.txt_status_progress:
                self.txt_status_progress.SetValue(text)
        except Exception:
            pass
        key = msg.split("…")[0].split("(")[0].strip().lower()
        last = getattr(self, "_media_progress_announced", "")
        milestones = (
            "download",
            "scheda tecnica",
            "riassunto",
            "trascrizione",
            "traduzione",
            "upload file api",
            "analisi gemini",
            "ripresa trascrizione",
            "analisi audio/video completata",
            "download completato",
            "scaricamento",
            "programma whisper",
            "modello whisper",
            "preparazione audio",
            "trascrizione whisper",
        )
        if key != last and any(m in key for m in milestones):
            self._media_progress_announced = key
            rtad_speak(f"{msg}, {pct} percento")

    def _release_listed_url_media(self, keep_path=""):
        """Toglie il file temp di un URL precedente, se l'elenco non lo usa più."""
        prev = getattr(self, "_listed_url_media_path", "") or ""
        if not prev:
            return
        keep = os.path.normcase(os.path.normpath(keep_path)) if keep_path else ""
        prev_n = os.path.normcase(os.path.normpath(prev))
        if keep and prev_n == keep:
            return
        self._listed_url_media_path = ""
        if rtad_media is not None:
            try:
                rtad_media.cleanup_temp_media(prev)
            except Exception:
                pass

    def _log_url_list(self, line):
        text = str(line)
        try:
            from logHandler import log
            log.info("RTAD %s", text)
        except Exception:
            pass
        try:
            folder = os.environ.get("TEMP") or os.environ.get("TMP") or "."
            path = os.path.join(folder, "rtad_url_list.log")
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(text.rstrip() + "\n")
        except Exception:
            pass

    def _url_download_item(self, url, file_name, location_info):
        shown = (url or "").strip()
        if len(shown) > 120:
            shown = shown[:117] + "..."
        return {
            "file_path": url,
            "file_name": file_name,
            "prefix": "[URL]",
            "mtime": 0,
            "line_number": None,
            "paragraph_index": None,
            "location_info": location_info,
            "snippet": shown,
            "media_path": "",
            "pending_download": True,
        }

    def _force_results_row(self, item, take_focus=False):
        """Sostituisce l'elenco con una riga sola. Non lascia «Nessuna ricerca avviata»."""
        self.current_matches = [item]
        self.current_query = "(File da URL)"
        self._results_ready = True
        loc = f" ({item['location_info']})" if item.get("location_info") else ""
        display = (
            f"{item.get('prefix', '')} {item.get('file_name', '')}{loc}"
            f" -- ({item.get('file_path', '')})"
        )
        lst = self.lst_results
        try:
            lst.SetSelection(wx.NOT_FOUND)
        except Exception:
            pass
        try:
            lst.Clear()
        except Exception:
            pass
        safety = 0
        while lst.GetCount() > 0 and safety < 30:
            safety += 1
            try:
                lst.Delete(0)
            except Exception:
                break
        idx = lst.Append(display)
        self.file_map.clear()
        if idx is None or idx < 0:
            idx = 0
        self.file_map[idx] = item
        safety = 0
        while lst.GetCount() > 1 and safety < 10:
            safety += 1
            try:
                first = lst.GetString(0) or ""
            except Exception:
                break
            if "Nessuna ricerca avviata" in first:
                lst.Delete(0)
                continue
            break
        if lst.GetCount() >= 1:
            self.file_map.clear()
            self.file_map[0] = item
            try:
                lst.SetSelection(0)
            except Exception:
                pass
        shown = ""
        try:
            if lst.GetCount() > 0:
                sel = lst.GetSelection()
                shown = lst.GetString(0 if sel in (wx.NOT_FOUND, -1) else sel) or ""
        except Exception:
            shown = ""
        self._log_url_list(f"riga elenco: {shown}")
        if take_focus:
            try:
                self.Raise()
                if lst.GetCount() > 0:
                    lst.SetSelection(0)
                lst.SetFocus()
            except Exception:
                pass
        return shown

    def _clear_pending_url_row(self):
        """Hub chiuso senza Avvia: togli la riga di attesa."""
        try:
            matches = getattr(self, "current_matches", None) or []
            if len(matches) != 1 or not matches[0].get("pending_download"):
                return
            self.current_matches = []
            self._results_ready = False
            self.current_query = ""
            self.update_list_display()
        except Exception:
            pass

    def _list_contains_path(self, file_path):
        try:
            count = self.lst_results.GetCount()
        except Exception:
            return False
        for index in range(count):
            try:
                text = self.lst_results.GetString(index) or ""
            except Exception:
                continue
            if "Nessuna ricerca avviata" in text:
                continue
            if file_path and file_path in text:
                return True
        return False

    def _renew_results_list(self):
        """Nuovo ListBox: NVDA, nello stesso processo, conserva la riga iniziale."""
        old = getattr(self, "lst_results", None)
        if old is None:
            return None
        try:
            parent = old.GetParent()
        except Exception:
            return None
        sizer = None
        try:
            sizer = old.GetContainingSizer()
        except Exception:
            sizer = None
        new = wx.ListBox(parent, style=wx.LB_SINGLE)
        new.Bind(wx.EVT_CHAR_HOOK, self.on_list_char_hook)
        new.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open_file_event)
        new.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        replaced = False
        if sizer is not None:
            try:
                replaced = bool(sizer.Replace(old, new))
            except Exception:
                replaced = False
            if not replaced:
                try:
                    sizer.Add(new, 1, wx.EXPAND | wx.ALL, 5)
                    replaced = True
                except Exception:
                    replaced = False
        self.lst_results = new
        try:
            old.Hide()
        except Exception:
            pass
        try:
            wx.CallLater(0, old.Destroy)
        except Exception:
            try:
                old.Destroy()
            except Exception:
                pass
        try:
            parent.Layout()
            self.Layout()
        except Exception:
            pass
        return new

    def _nvda_drop_list_cache(self, lst):
        try:
            import winUser
            from NVDAObjects.IAccessible import getNVDAObjectFromEvent
            import eventHandler
            hwnd = lst.GetHandle()
            obj = getNVDAObjectFromEvent(hwnd, winUser.OBJID_CLIENT, 0)
            if obj is None:
                return
            obj.invalidateCache()
            try:
                for child in list(getattr(obj, "children", None) or []):
                    try:
                        child.invalidateCache()
                    except Exception:
                        pass
            except Exception:
                pass
            eventHandler.queueEvent("reorder", obj)
        except Exception:
            pass

    def show_url_media_in_list(self, file_path, take_focus=True):
        """Il file scaricato da un URL resta una riga dell'elenco, come gli altri."""
        if not file_path or not os.path.isfile(file_path):
            self._log_url_list(f"skip missing {file_path!r}")
            return False
        file_path = os.path.normpath(file_path)
        self._release_listed_url_media(keep_path=file_path)
        self._listed_url_media_path = file_path
        meta = {}
        if rtad_media is not None and hasattr(rtad_media, "read_media_source_meta"):
            try:
                meta = rtad_media.read_media_source_meta(file_path) or {}
            except Exception:
                meta = {}
        url = str(meta.get("webpage_url") or meta.get("url") or "").strip()
        title = str(meta.get("title") or "").strip()
        ext = os.path.splitext(file_path)[1].lower()
        name = title
        if not name and url:
            name = urllib.parse.unquote(
                os.path.basename(urllib.parse.urlparse(url).path) or ""
            )
        if not name or name.lower().startswith("rtad_media_"):
            name = f"File da URL{ext or ''}"
        try:
            mtime = os.path.getmtime(file_path)
        except Exception:
            mtime = 0
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
        date_lbl = format_file_date_label(mtime)
        date_suffix = f" {date_lbl}" if date_lbl else ""
        prefix = f"[{(ext or '.file').lstrip('.').upper() or 'FILE'}]"
        snippet = f"File scaricato da URL · {size_s}"
        if url:
            snippet = f"{snippet} · {url}"
        item = {
            "file_path": file_path,
            "file_name": name,
            "prefix": prefix,
            "mtime": mtime,
            "line_number": None,
            "paragraph_index": None,
            "location_info": f"Scaricato da URL{date_suffix}",
            "snippet": snippet,
            "media_path": file_path,
        }
        try:
            self.txt_filter.ChangeValue("")
        except Exception:
            try:
                self.txt_filter.SetValue("")
            except Exception:
                pass
        shown = self._force_results_row(item, take_focus=False)
        row_ok = bool(shown) and "Nessuna ricerca avviata" not in shown
        msg = (
            f"Il file è in elenco: {name}. "
            "Da qui puoi fare altre operazioni."
        )
        try:
            self.txt_status_progress.SetValue(msg)
        except Exception:
            pass
        if not take_focus:
            return row_ok
        if row_ok:
            rtad_speak(msg)
            try:
                self.lst_results.SetSelection(0)
                self.lst_results.SetFocus()
            except Exception:
                pass
        else:
            rtad_speak(
                "Elenco non aggiornato. La riga del file non è comparsa.",
                force=True,
            )
        return row_ok

    def show_media_analysis(
        self, file_path, mode="describe", sections=None, delete_after=False
    ):
        """Scheda / riassunto / report completo su audio-video."""
        if not file_path or not os.path.isfile(file_path):
            rtad_speak("File audio/video non trovato.")
            return
        if rtad_media is None:
            rtad_speak("Modulo media non disponibile.")
            return
        if getattr(self, "_media_analysis_busy", False):
            self._media_abort = True
            self._set_media_progress(
                0, "Interruzione richiesta. Attendi la chiusura."
            )
            rtad_speak("Interruzione richiesta. Attendi la chiusura.")
            return
        self._media_abort = False
        self._media_analysis_busy = True
        self._media_analysis_gen = int(getattr(self, "_media_analysis_gen", 0) or 0) + 1
        gen = self._media_analysis_gen
        self._media_progress_announced = ""
        if isinstance(sections, dict):
            self._last_media_sections = {
                "include_tech": bool(sections.get("include_tech", True)),
                "include_describe": bool(sections.get("include_describe", True)),
                "include_transcript": bool(sections.get("include_transcript", False)),
                "transcript_engine": sections.get("transcript_engine") or "gemini",
                "include_timestamps": bool(sections.get("include_timestamps", False)),
                "translate_transcript": bool(sections.get("translate_transcript", False)),
                "translate_lang": sections.get("translate_lang") or "it",
            }
        _ensure_ocr_keys()
        sec0 = sections if isinstance(sections, dict) else {}
        engine0 = sec0.get("transcript_engine") or "gemini"
        need_gemini = mode == "describe" or bool(sec0.get("include_describe")) or (
            bool(sec0.get("include_transcript")) and engine0 != "whisper"
        ) or bool(sec0.get("translate_transcript"))
        if mode == "transcript" and engine0 != "whisper":
            need_gemini = True
        tech_only = mode == "tech" or (
            mode == "all"
            and sec0.get("include_tech")
            and not sec0.get("include_describe")
            and not sec0.get("include_transcript")
        )
        if tech_only:
            rtad_speak("Scheda tecnica audio/video in corso…")
        elif need_gemini and not load_gemini_api_key():
            rtad_speak(
                "Per riassunto o trascrizione serve la chiave Gemini "
                "(Strumenti). Procedo comunque con le sezioni possibili."
            )
        else:
            rtad_speak("Analisi audio/video in corso…")
        self._set_media_progress(8, "Analisi audio/video…")
        from_url = bool(delete_after) or os.path.basename(file_path).lower().startswith(
            "rtad_media_"
        )
        if from_url:
            try:
                self.show_url_media_in_list(file_path)
            except Exception as exc:
                try:
                    self._log_url_list(f"show_url failed {exc!r}")
                except Exception:
                    pass
                rtad_speak(
                    "Elenco non aggiornato. La riga del file non è comparsa.",
                    force=True,
                )

        def _abort():
            return bool(getattr(self, "_media_abort", False))

        def _work():
            title = "Audio/video"
            body = ""
            try:
                if mode == "all":
                    title = "Tutto sull'audio/video"
                    sec = sections or {}
                    body = rtad_media.format_full_media_report(
                        file_path,
                        include_tech=sec.get("include_tech", True),
                        include_describe=sec.get("include_describe", True),
                        include_transcript=sec.get("include_transcript", False),
                        include_timestamps=sec.get("include_timestamps", False),
                        transcript_engine=sec.get("transcript_engine") or "gemini",
                        should_abort=_abort,
                        on_progress=self._media_progress_cb,
                    )
                elif mode == "tech":
                    title = "Scheda tecnica audio/video"
                    self._media_progress_cb(20, "Scheda tecnica…")
                    body = rtad_media.format_media_tech_sheet(
                        rtad_media.get_media_tech_info(file_path)
                    )
                    self._media_progress_cb(100, "Analisi audio/video completata.")
                elif mode == "transcript":
                    title = "Trascrizione audio/video"
                    sec = sections or {}
                    if (sec.get("transcript_engine") or "gemini") == "whisper":
                        tr = rtad_media._transcribe_with_whisper(
                            file_path,
                            include_timestamps=bool(sec.get("include_timestamps", False)),
                            should_abort=_abort,
                            on_progress=self._media_progress_cb,
                        )
                    else:
                        tr = rtad_media.transcribe_media_gemini(
                            file_path,
                            include_timestamps=bool(sec.get("include_timestamps", False)),
                            should_abort=_abort,
                            on_progress=self._media_progress_cb,
                        )
                    if tr.get("ok") and (tr.get("text") or "").strip():
                        body = (tr.get("text") or "").strip()
                    else:
                        body = tr.get("error") or "Trascrizione non disponibile."
                    self._media_progress_cb(100, "Analisi audio/video completata.")
                else:
                    title = "Riassunto audio/video"
                    desc = rtad_media.describe_media_gemini(
                        file_path, on_progress=self._media_progress_cb
                    )
                    if desc.get("ok") and (desc.get("text") or "").strip():
                        body = (desc.get("text") or "").strip()
                    else:
                        body = desc.get("error") or "Riassunto non disponibile."
                    self._media_progress_cb(100, "Analisi audio/video completata.")
            except Exception as e:
                title = "Errore analisi audio/video"
                body = str(e)

            if (
                mode == "all"
                and isinstance(sections, dict)
                and sections.get("translate_transcript")
                and not str(title).startswith("Errore")
            ):
                body = _translate_report_body(
                    body,
                    sections.get("translate_lang") or "it",
                    on_progress=self._media_progress_cb,
                )

            saved_msg = ""
            if (
                mode == "all"
                and isinstance(sections, dict)
                and (sections.get("transcript_engine") or "") == "whisper"
                and sections.get("include_transcript")
                and body
                and not str(title).startswith("Errore")
            ):
                try:
                    import rtad_whisper
                    body, saved_msg = rtad_whisper.attach_sidecar(
                        body, file_path, delete_after=delete_after
                    )
                except Exception:
                    saved_msg = ""

            def _show():
                self._media_analysis_busy = False
                if gen != getattr(self, "_media_analysis_gen", 0):
                    return
                if not hasattr(self, "_image_info_frames") or self._image_info_frames is None:
                    self._image_info_frames = []
                # Solo pulsante esplicito: niente hub automatico (rubava focus dopo Avvia)
                frm = ImageInfoFrame(
                    None,
                    title,
                    body,
                    image_path=file_path,
                    action_label="&Nuova analisi…",
                    action_cb=self._reopen_media_hub_ready_for_next,
                    after_close_cb=None,
                )

                def _cleanup_and_list(evt, frame=frm, path=file_path, do_del=delete_after):
                    try:
                        if frame in self._image_info_frames:
                            self._image_info_frames.remove(frame)
                    except Exception:
                        pass
                    if do_del and rtad_media is not None:
                        listed = getattr(self, "_listed_url_media_path", "") or ""
                        same = False
                        if listed:
                            try:
                                same = (
                                    os.path.normcase(os.path.normpath(listed))
                                    == os.path.normcase(os.path.normpath(path))
                                )
                            except Exception:
                                same = False
                        if not same:
                            try:
                                rtad_media.cleanup_temp_media(path)
                            except Exception:
                                pass
                    evt.Skip()

                frm.Bind(wx.EVT_CLOSE, _cleanup_and_list)
                self._image_info_frames.append(frm)
                if from_url:
                    try:
                        self.show_url_media_in_list(file_path, take_focus=False)
                    except Exception:
                        pass
                frm.Show()
                frm.Raise()
                rtad_speak("Report pronto. Per un altro URL: Nuova analisi.")
                if saved_msg:
                    rtad_speak(saved_msg)
                try:
                    import rtad_whisper
                    for phrase in rtad_whisper.SPOKEN_RESULTS:
                        if phrase and phrase in (body or "") and phrase != saved_msg:
                            rtad_speak(phrase)
                except Exception:
                    pass

            wx.CallAfter(_show)

        threading.Thread(target=_work, daemon=True).start()

    def _reopen_media_hub_ready_for_next(self):
        """Hub di nuovo: stesse opzioni, sorgente vuota (nuovo URL)."""
        if getattr(self, "_media_hub_open", False):
            return
        if getattr(self, "_media_analysis_busy", False):
            rtad_speak(
                "Analisi ancora in corso. Attendi, poi Nuova analisi."
            )
            return
        rtad_speak(
            "Hub audio/video: stesse opzioni, incolla un nuovo URL oppure Annulla."
        )
        self.open_media_hub_dialog(
            initial_url="",
            preset_sections=getattr(self, "_last_media_sections", None),
            clear_source=True,
        )

    def on_batch_images_folder(self, event=None, folder=None):
        """Strumenti → Analizza cartella immagini (batch 1.6.6)."""
        if rtad_ocr is None:
            rtad_speak("Modulo immagini non disponibile.")
            return
        if not folder or not os.path.isdir(folder):
            start_dir = ""
            try:
                cur = (self.txt_path.GetValue() or "").strip()
                if cur and os.path.isdir(cur):
                    start_dir = cur
                elif cur and os.path.isfile(cur):
                    start_dir = os.path.dirname(cur)
            except Exception:
                pass
            with wx.DirDialog(
                self,
                "Scegli la cartella con le immagini da analizzare",
                defaultPath=start_dir or "",
                style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
            ) as dd:
                if dd.ShowModal() != wx.ID_OK:
                    return
                folder = dd.GetPath()
        self.start_batch_images_folder(folder)

    def on_batch_media_folder(self, event=None, folder=None):
        """Strumenti → Analizza cartella audio/video (batch 1.7.2)."""
        if rtad_media is None:
            rtad_speak("Modulo media non disponibile.")
            return
        if not folder or not os.path.isdir(folder):
            start_dir = ""
            try:
                cur = (self.txt_path.GetValue() or "").strip()
                if cur and os.path.isdir(cur):
                    start_dir = cur
                elif cur and os.path.isfile(cur):
                    start_dir = os.path.dirname(cur)
            except Exception:
                pass
            with wx.DirDialog(
                self,
                "Scegli la cartella con i file audio/video da analizzare",
                defaultPath=start_dir or "",
                style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
            ) as dd:
                if dd.ShowModal() != wx.ID_OK:
                    return
                folder = dd.GetPath()
        self.start_batch_media_folder(folder)

    def start_batch_media_folder(self, folder):
        """Mostra sezioni (con conteggio) e avvia il batch media."""
        if rtad_media is None:
            rtad_speak("Modulo media non disponibile.")
            return
        if getattr(self, "_media_analysis_busy", False):
            self._media_abort = True
            self._set_media_progress(
                0, "Interruzione richiesta. Attendi la chiusura."
            )
            rtad_speak("Interruzione richiesta. Attendi la chiusura.")
            return
        folder = os.path.abspath(folder or "")
        if not folder or not os.path.isdir(folder):
            rtad_speak("Cartella non trovata.")
            return
        preview = rtad_media.list_media_files_in_folder(folder, recursive=False)
        dlg = MediaSectionsDialog(
            self,
            title="Analizza cartella audio/video",
            batch_mode=True,
            context_label=folder,
            media_count=len(preview),
            preset_sections={
                "include_tech": True,
                "include_describe": True,
                "include_transcript": False,
                "include_timestamps": False,
            },
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            sel = dlg.selections()
        finally:
            dlg.Destroy()
        files = rtad_media.list_media_files_in_folder(
            folder, recursive=sel.get("recursive", False)
        )
        if not files:
            rtad_speak("Nessun file audio/video trovato in questa cartella.")
            return
        engine = sel.get("transcript_engine") or "gemini"
        if (
            sel.get("include_transcript")
            and engine == "whisper"
            and len(files) > 5
        ):
            try:
                import rtad_whisper
                cap_msg = rtad_whisper.msg_folder_cap(5, len(files))
            except Exception:
                cap_msg = (
                    f"Whisper: 5 file su {len(files)}. "
                    f"Non entrati: {len(files) - 5}."
                )
            rtad_speak(cap_msg)
        elif (
            sel.get("include_transcript")
            and engine != "whisper"
            and len(files) >= 5
        ):
            ask = wx.MessageDialog(
                self,
                (
                    f"Hai selezionato la trascrizione su {len(files)} file.\n"
                    "Può richiedere molto tempo e consumare quota Gemini.\n"
                    + (
                        "È accesa anche la traduzione della trascrizione.\n"
                        if sel.get("translate_transcript")
                        else ""
                    )
                    + "\nContinuare?"
                ),
                "Conferma batch con trascrizione",
                wx.YES_NO | wx.ICON_WARNING,
            )
            choice = ask.ShowModal()
            ask.Destroy()
            if choice != wx.ID_YES:
                rtad_speak("Batch annullato.")
                return
        if engine == "whisper" and sel.get("include_transcript"):
            rtad_speak(
                f"Avvio analisi: {min(len(files), 5)} file audio/video. "
                "Whisper sul mio PC."
            )
        else:
            rtad_speak(
                f"Avvio analisi: {len(files)} file audio/video. "
                "Può richiedere tempo se usi Gemini."
            )
        _ensure_ocr_keys()
        self._media_abort = False
        self._media_analysis_busy = True
        self._set_media_progress(2, "Batch audio/video…")

        def _work():
            def _prog(i, total, path, ok):
                name = os.path.basename(path)
                wx.CallAfter(
                    rtad_speak,
                    f"Media {i} di {total}: {name}. "
                    + ("Ok." if ok else "Problema."),
                )
                try:
                    pct = int(max(2, min(99, round(100.0 * i / max(1, total)))))
                except Exception:
                    pct = 50
                wx.CallAfter(
                    self._set_media_progress,
                    pct,
                    f"Batch {i}/{total}: {name}",
                )

            try:
                summary = rtad_media.batch_analyze_folder(
                    folder,
                    include_tech=sel.get("include_tech", True),
                    include_describe=sel.get("include_describe", True),
                    include_transcript=sel.get("include_transcript", False),
                    include_timestamps=sel.get("include_timestamps", False),
                    transcript_engine=sel.get("transcript_engine") or "gemini",
                    save_txt=sel.get("save_txt", True),
                    recursive=sel.get("recursive", False),
                    should_abort=lambda: bool(getattr(self, "_media_abort", False)),
                    on_progress=_prog,
                    translate_transcript=bool(sel.get("translate_transcript")),
                    translate_lang=sel.get("translate_lang") or "it",
                    translate_key=load_gemini_api_key() or "",
                    on_translate=lambda message: wx.CallAfter(
                        self._set_media_progress, 90, message
                    ),
                )
            except Exception as e:
                summary = {"total": 0, "ok": 0, "results": [], "error": str(e)}

            lines = []
            if summary.get("whisper_note"):
                lines.append(summary["whisper_note"])
            lines.extend([
                f"Cartella: {folder}",
                f"File media trovati: {summary.get('total', 0)}",
                f"Completati: {summary.get('ok', 0)}",
            ])
            if summary.get("error"):
                lines.append(f"Errore: {summary['error']}")
            if sel.get("save_txt"):
                lines.append(
                    "Accanto a ogni media è stato creato un file .rtad.txt "
                    "(stesso stem del file, se l'analisi è riuscita)."
                )
            fails = [
                r for r in (summary.get("results") or []) if not r.get("ok")
            ]
            if fails:
                lines.append("")
                lines.append("Con problemi:")
                for r in fails[:30]:
                    lines.append(
                        f"- {os.path.basename(r.get('path') or '')}: "
                        f"{r.get('error') or 'sconosciuto'}"
                    )
            body = "\n".join(lines)

            def _show():
                self._media_analysis_busy = False
                self._set_media_progress(100, "Batch audio/video completato.")
                if not hasattr(self, "_image_info_frames") or self._image_info_frames is None:
                    self._image_info_frames = []
                frm = ImageInfoFrame(
                    None, "Batch cartella audio/video", body, image_path=folder
                )
                self._image_info_frames.append(frm)
                frm.Show()
                frm.Raise()
                done_n = summary.get("analyzed")
                if done_n is None:
                    done_n = summary.get("total", 0)
                end_msg = (
                    f"Batch terminato: {summary.get('ok', 0)} di "
                    f"{done_n} completati."
                )
                if summary.get("whisper_note"):
                    end_msg = summary["whisper_note"] + " " + end_msg
                rtad_speak(end_msg)

            wx.CallAfter(_show)

        threading.Thread(target=_work, daemon=True).start()

    def on_transcribe_and_search(self, event=None):
        """Strumenti → Trascrivi e cerca (B0 + Gemini solo senza sidecar)."""
        if rtad_media is None:
            rtad_speak("Modulo media non disponibile.")
            return
        if getattr(self, "_media_analysis_busy", False):
            rtad_speak(
                "Analisi audio/video già in corso. Attendi il risultato."
            )
            return
        start = ""
        try:
            start = (self.txt_path.GetValue() or "").strip()
        except Exception:
            start = ""
        if start and os.path.isfile(start):
            start = os.path.dirname(os.path.abspath(start))
        if not start or not os.path.isdir(start):
            start = load_last_media_report_dir() or os.path.expanduser("~")
        dd = wx.DirDialog(
            self,
            "Cartella audio/video per Trascrivi e cerca",
            defaultPath=start,
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        try:
            if dd.ShowModal() != wx.ID_OK:
                return
            folder = dd.GetPath()
        finally:
            dd.Destroy()
        self.start_transcribe_and_search(folder)

    def start_transcribe_and_search(self, folder):
        """Chiede termini e avvia Trascrivi e cerca sulla cartella."""
        if rtad_media is None:
            rtad_speak("Modulo media non disponibile.")
            return
        folder = os.path.abspath(folder or "")
        if not folder or not os.path.isdir(folder):
            rtad_speak("Cartella non trovata.")
            return
        files = rtad_media.list_media_files_in_folder(folder, recursive=False)
        rtad_txts = []
        if hasattr(rtad_media, "list_rtad_txt_files_in_folder"):
            rtad_txts = rtad_media.list_rtad_txt_files_in_folder(
                folder, recursive=False
            )
        missing = sum(
            1 for p in files if not rtad_media.resolve_media_sidecar_path(p)
        )
        q_default = ""
        try:
            q_default = (self.txt_query.GetValue() or "").strip()
        except Exception:
            q_default = ""
        dlg = wx.TextEntryDialog(
            self,
            (
                f"Cartella: {folder}\n"
                f"Media: {len(files)} (senza .rtad.txt: {missing}); "
                f"report testo già presenti: {len(rtad_txts)}.\n\n"
                "Parole da cercare nel parlato.\n"
                "Se c’è già il .rtad.txt (anche da solo): ricerca a zero costo.\n"
                "Se c’è solo audio/video senza testo: trascrizione Gemini.\n"
                "Massimo 30 nuove trascrizioni per avvio."
            ),
            "Trascrivi e cerca",
            q_default,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            query = (dlg.GetValue() or "").strip()
        finally:
            dlg.Destroy()
        if not query:
            rtad_speak("Serve almeno una parola da cercare.")
            return
        recursive = False
        if files or rtad_txts:
            ask_rec = wx.MessageDialog(
                self,
                "Includere anche le sottocartelle?",
                "Trascrivi e cerca",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            )
            recursive = ask_rec.ShowModal() == wx.ID_YES
            ask_rec.Destroy()
            if recursive:
                files = rtad_media.list_media_files_in_folder(
                    folder, recursive=True
                )
                if hasattr(rtad_media, "list_rtad_txt_files_in_folder"):
                    rtad_txts = rtad_media.list_rtad_txt_files_in_folder(
                        folder, recursive=True
                    )
                missing = sum(
                    1
                    for p in files
                    if not rtad_media.resolve_media_sidecar_path(p)
                )
        if not files and not rtad_txts:
            rtad_speak(
                "Nella cartella non ci sono audio/video né file .rtad.txt."
            )
            return
        if missing:
            ask = wx.MessageDialog(
                self,
                (
                    f"Verranno trascritti fino a {min(missing, 30)} file "
                    f"senza .rtad.txt (su {missing} senza sidecar).\n"
                    "Serve la chiave Gemini e consuma quota API.\n\n"
                    "Continuare?"
                ),
                "Conferma Trascrivi e cerca",
                wx.YES_NO | wx.ICON_WARNING,
            )
            choice = ask.ShowModal()
            ask.Destroy()
            if choice != wx.ID_YES:
                rtad_speak("Operazione annullata.")
                return
        _ensure_ocr_keys()
        try:
            sync_transcript_glossary_to_media()
        except Exception:
            pass
        norm_query = normalize_search_text(query)
        terms = norm_query.split() if norm_query else []
        if not terms:
            rtad_speak("Serve almeno una parola da cercare.")
            return
        rtad_speak(
            f"Trascrivi e cerca: {len(files)} media, "
            f"{len(rtad_txts)} report testo. "
            "Può richiedere tempo se serve Gemini."
        )
        self._media_analysis_busy = True
        self._stop_search = False
        self._set_media_progress(2, "Trascrivi e cerca…")
        try:
            self.txt_query.SetValue(query)
        except Exception:
            pass

        def _work():
            def _prog(i, total, path, phase):
                name = os.path.basename(path)
                if phase == "transcribe":
                    msg = f"{i}/{total}: trascrivo {name}…"
                elif phase == "cache":
                    msg = f"{i}/{total}: cache {name}"
                elif phase == "skip":
                    msg = f"{i}/{total}: salto (limite) {name}"
                else:
                    msg = f"{i}/{total}: {name}"
                try:
                    pct = int(max(2, min(99, round(100.0 * i / max(1, total)))))
                except Exception:
                    pct = 50
                wx.CallAfter(self._set_media_progress, pct, msg)

            try:
                summary = rtad_media.transcribe_and_search_folder(
                    folder,
                    terms,
                    text_matches_fn=text_matches_terms,
                    recursive=recursive,
                    max_transcribe=30,
                    should_abort=lambda: self._stop_search,
                    on_progress=_prog,
                )
            except Exception as e:
                summary = {
                    "total": 0,
                    "hits": [],
                    "errors": [{"error": str(e)}],
                    "cache_hits": 0,
                    "transcribed": 0,
                    "skipped_limit": 0,
                    "aborted": False,
                }

            def _show():
                self._media_analysis_busy = False
                self._set_media_progress(100, "Trascrivi e cerca completato.")
                raw = []
                for h in summary.get("hits") or []:
                    side = h.get("sidecar_path") or ""
                    media = h.get("media_path") or ""
                    try:
                        mtime = os.path.getmtime(side or media) if (side or media) else 0
                    except Exception:
                        mtime = 0
                    date_suffix = ""
                    try:
                        lab = format_file_date_label(mtime)
                        date_suffix = f" {lab}" if lab else ""
                    except Exception:
                        pass
                    via = h.get("via") or ""
                    loc = h.get("location_label") or "Report media"
                    if via == "transcript":
                        loc = f"{loc} (nuova trascrizione)"
                    raw.append({
                        "file_path": side or media,
                        "file_name": h.get("file_name") or os.path.basename(media),
                        "prefix": "[AV]",
                        "mtime": mtime,
                        "line_number": h.get("line_number"),
                        "paragraph_index": None,
                        "location_info": f"{loc}{date_suffix}",
                        "snippet": h.get("snippet") or "",
                        "media_path": media,
                    })
                self.current_matches = raw
                self.current_query = query
                self.update_list_display()
                n_hit = len(raw)
                n_tr = int(summary.get("transcribed") or 0)
                n_cache = int(summary.get("cache_hits") or 0)
                parts = [
                    f"Trascrivi e cerca: {n_hit} occorrenze.",
                    f"Sidecar già presenti con match: {n_cache}.",
                    f"Nuove trascrizioni: {n_tr}.",
                ]
                if summary.get("skipped_limit"):
                    parts.append(
                        f"Saltati per limite: {summary.get('skipped_limit')}."
                    )
                if summary.get("aborted"):
                    parts.append("Interrotto.")
                errs = summary.get("errors") or []
                if errs:
                    parts.append(f"Problemi: {len(errs)}.")
                rtad_speak(" ".join(parts))
                if self.lst_results.GetCount() > 0:
                    self.lst_results.SetSelection(0)
                    self.lst_results.SetFocus()

            wx.CallAfter(_show)

        threading.Thread(target=_work, daemon=True).start()

    def start_batch_images_folder(self, folder):
        """Mostra sezioni (con conteggio) e avvia subito il batch."""
        if rtad_ocr is None:
            rtad_speak("Modulo immagini non disponibile.")
            return
        folder = os.path.abspath(folder or "")
        if not folder or not os.path.isdir(folder):
            rtad_speak("Cartella non trovata.")
            return
        preview = rtad_ocr.list_image_files_in_folder(folder, recursive=False)
        dlg = ImageSectionsDialog(
            self,
            title="Analizza cartella immagini",
            batch_mode=True,
            default_labels=False,
            context_label=folder,
            image_count=len(preview),
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            sel = dlg.selections()
        finally:
            dlg.Destroy()
        files = rtad_ocr.list_image_files_in_folder(
            folder, recursive=sel.get("recursive", False)
        )
        if not files:
            rtad_speak("Nessuna immagine trovata in questa cartella.")
            return
        rtad_speak(
            f"Avvio analisi: {len(files)} immagini. "
            "Può richiedere tempo se usi Gemini."
        )
        _ensure_ocr_keys()

        def _work():
            def _prog(i, total, path, ok):
                name = os.path.basename(path)
                wx.CallAfter(
                    rtad_speak,
                    f"Immagine {i} di {total}: {name}. "
                    + ("Ok." if ok else "Problema."),
                )

            try:
                summary = rtad_ocr.batch_describe_folder(
                    folder,
                    include_alt=sel["include_alt"],
                    include_describe=sel["include_describe"],
                    include_labels=sel["include_labels"],
                    include_tech=sel["include_tech"],
                    save_txt=sel.get("save_txt", True),
                    recursive=sel.get("recursive", False),
                    on_progress=_prog,
                )
            except Exception as e:
                summary = {"total": 0, "ok": 0, "results": [], "error": str(e)}

            lines = [
                f"Cartella: {folder}",
                f"Immagini trovate: {summary.get('total', 0)}",
                f"Completate: {summary.get('ok', 0)}",
            ]
            if summary.get("error"):
                lines.append(f"Errore: {summary['error']}")
            if sel.get("save_txt"):
                lines.append(
                    "Accanto a ogni immagine è stato creato un file .rtad.txt "
                    "(se l'analisi è riuscita)."
                )
            fails = [
                r for r in (summary.get("results") or []) if not r.get("ok")
            ]
            if fails:
                lines.append("")
                lines.append("Con problemi:")
                for r in fails[:30]:
                    lines.append(
                        f"- {os.path.basename(r.get('path') or '')}: "
                        f"{r.get('error') or 'sconosciuto'}"
                    )
            body = "\n".join(lines)

            def _show():
                if not hasattr(self, "_image_info_frames") or self._image_info_frames is None:
                    self._image_info_frames = []
                frm = ImageInfoFrame(
                    None, "Batch cartella immagini", body, image_path=folder
                )
                self._image_info_frames.append(frm)
                frm.Show()
                frm.Raise()
                rtad_speak(
                    f"Batch terminato: {summary.get('ok', 0)} di "
                    f"{summary.get('total', 0)} ok."
                )

            wx.CallAfter(_show)

        threading.Thread(target=_work, daemon=True).start()

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
        """Estrae immagine dal PDF e avvia analisi (temp + delete_after).

        Passa source_path=PDF originale così «Salva testo» usa stem/cartella del PDF.
        """
        if not file_path or not os.path.isfile(file_path):
            rtad_speak("File PDF non trovato.")
            return
        rtad_speak("Estrazione immagine dal PDF…")
        pdf_path = os.path.normpath(file_path)

        def _work():
            tmp = self.materialize_pdf_image_temp(pdf_path)
            if not tmp:
                wx.CallAfter(
                    rtad_speak,
                    "Nessuna immagine utilizzabile in questo PDF "
                    "(solo loghi piccoli o nessuna grafica).",
                )
                return

            def _go(p=tmp, m=mode, src=pdf_path):
                self.show_image_analysis(
                    p, mode=m, delete_after=True, source_path=src
                )

            wx.CallAfter(_go)

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
        elif ext == ".xlsx":
            text_content = "\n".join(
                (row.get("text") or "") for row in extract_rows_from_xlsx(file_path)
            )
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
                img = (
                    rtad_ocr.load_wx_image_silent(file_path)
                    if rtad_ocr is not None
                    else None
                )
                if img is not None and img.IsOk() and wx.TheClipboard.Open():
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
            live = None
            for window in list(wx.GetTopLevelWindows()):
                try:
                    if isinstance(window, SearchFrame) and not window.IsBeingDeleted():
                        live = window
                        break
                except Exception:
                    continue
            if live is not None:
                live.Show()
                live.Raise()
                live.txt_query.SetFocus()
                return
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
