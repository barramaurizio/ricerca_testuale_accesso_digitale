_speech_active = True
import ctypes
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
import zipfile
import quopri
import wx
import email
from email import policy
from email.header import decode_header
from email.utils import parsedate_to_datetime
import html
import logging
import traceback
import platform
import winsound
import csv
import mailbox

try:
    import feedparser
except ImportError:
    feedparser = None

APP_TITLE = "Ricerca Testuale Accesso Digitale"
APP_VERSION = "1.5.2"
DONATION_URL = "https://paypal.me/AccessoDigitale"
YOUTUBE_URL = "https://www.youtube.com/@AccessoDigitale"
GITHUB_REPO_URL = "https://github.com/barramaurizio/ricerca_testuale_accesso_digitale/releases"
GITHUB_API_LATEST = "https://api.github.com/repos/barramaurizio/ricerca_testuale_accesso_digitale/releases/latest"
EMAIL_DESTINATARIO = "mauritechstudio@gmail.com"

CONFIG_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "RTAD_Standalone")
if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
LOG_FILE = os.path.join(CONFIG_DIR, "rtad_debug.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    encoding='utf-8'
)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Eccezione non gestita", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception
logging.info(f"=== Avvio {APP_TITLE} v{APP_VERSION} ===")
logging.info(f"Sistema OS: {platform.system()} {platform.release()} - {platform.version()}")
if feedparser is None:
    logging.warning("Modulo feedparser non disponibile: ricerca RSS/Atom non attiva fino all'installazione.")


def normalize_search_text(txt, remove_accents=False):
    if not txt:
        return ""
    for ap in ["’", "‘", "`", "´", "ʼ", "ʻ", "′", "‵", "՚", "Ꞌ"]:
        txt = txt.replace(ap, "'")
    for q in ["“", "”", "«", "»", "„"]:
        txt = txt.replace(q, '"')
    txt = txt.replace(chr(160), " ")
    if remove_accents:
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
        except Exception as e:
            logging.debug(f"Lettura condivisa Windows fallita su {file_path}: {e}")
    with open(file_path, "rb") as f:
        return f.read()


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
        except Exception as e:
            logging.debug(f"open_shared_binary Windows fallita su {file_path}: {e}")
    return open(file_path, "rb")


def load_mbox_message_by_index(file_path, msg_index, should_abort=None, on_progress=None):
    """Carica UN solo messaggio MBOX per indice, senza ricostruire l'indice di tutta la casella.

    Scorre solo fino al messaggio richiesto (From_ lines), poi fa il parse di quel pezzo.
    should_abort: callable → True per interrompere. on_progress(n) ogni ~25000 messaggi.
    """
    if msg_index is None or msg_index < 0:
        raise IndexError("Indice messaggio non valido")

    current = -1
    start_pos = None
    f = open_shared_binary(file_path)
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
                    # Inizia il messaggio successivo → fine del nostro
                    end_pos = line_start
                    f.seek(start_pos)
                    raw = f.read(end_pos - start_pos)
                    return _parse_mbox_raw_message(raw)
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
        raw = f.read()
        return _parse_mbox_raw_message(raw)
    finally:
        try:
            f.close()
        except Exception:
            pass


def _parse_mbox_raw_message(raw):
    if not raw:
        raise ValueError("Messaggio MBOX vuoto")
    # Rimuove la riga From_ iniziale (non fa parte dell'RFC822)
    if raw.startswith(b"From "):
        nl = raw.find(b"\n")
        if nl != -1:
            raw = raw[nl + 1:]
    try:
        return email.message_from_bytes(raw, policy=policy.default)
    except Exception:
        return email.message_from_bytes(raw)


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
                if dt.tzinfo is None:
                    return dt.timestamp()
                return dt.timestamp()
        except Exception:
            pass
    return fallback

_sapi_voice = None
_sapi_lock = threading.Lock()

def get_sapi_voice():
    global _sapi_voice
    with _sapi_lock:
        if _sapi_voice is None:
            try:
                import pythoncom
                import win32com.client
                pythoncom.CoInitialize()
                _sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
            except Exception as e:
                logging.warning(f"SAPI non disponibile: {e}")
                _sapi_voice = False
    return _sapi_voice if _sapi_voice is not False else None

def stop_accessible_speech():
    for dll_name in ("nvdaControllerClient64.dll", "nvdaControllerClient32.dll", "nvdaControllerClient.dll"):
        try:
            client = ctypes.windll.LoadLibrary(dll_name)
            if client.nvdaController_testIfRunning() == 0:
                client.nvdaController_cancelSpeech()
                break
        except Exception:
            pass
    v = get_sapi_voice()
    if v:
        try:
            v.Speak("", 2)
        except Exception:
            pass

def speak_accessible(text, force=False):
    global _speech_active
    if not _speech_active and not force:
        return
    if not text:
        return

    def _worker():
        for dll_name in ("nvdaControllerClient64.dll", "nvdaControllerClient32.dll", "nvdaControllerClient.dll"):
            try:
                client = ctypes.windll.LoadLibrary(dll_name)
                if client.nvdaController_testIfRunning() == 0:
                    client.nvdaController_cancelSpeech()
                    client.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                    client.nvdaController_speakText.restype = ctypes.c_long
                    if client.nvdaController_speakText(str(text)) == 0:
                        return
            except Exception:
                pass

        v = get_sapi_voice()
        if v:
            try:
                v.Speak(str(text), 3)
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()

def decode_email_header(raw_header):
    if not raw_header:
        return ""
    try:
        decoded_parts = decode_header(str(raw_header))
        result = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                result += str(part)
        return " ".join(result.splitlines()).strip()
    except Exception:
        return str(raw_header)

# Limite per parte MIME testuale: evita di gonfiare la UI con PDF/binari decodificati per errore.
MAX_EMAIL_TEXT_PART_BYTES = 1_500_000


def _payload_looks_binary(payload):
    """True se il payload sembra PDF o altro binario (non testo email)."""
    if not payload:
        return False
    head = payload[:8192]
    if head.startswith(b"%PDF"):
        return True
    if b"\x00" in head:
        return True
    return False


def format_email_date_label(msg, fallback_ts=0):
    """Data breve dd/mm/yyyy dall'header Date (come nei risultati Feed)."""
    ts = message_date_timestamp(msg, fallback=fallback_ts or 0)
    if not ts:
        return ""
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%d/%m/%Y")
    except Exception:
        return ""


def get_clean_email_text(msg):
    """Estrae solo testo/HTML dall'email; salta allegati e parti binarie (PDF, ecc.)."""
    body = ""
    body_html = ""
    skipped = []

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
        if _payload_looks_binary(payload):
            skipped.append(label or "binario")
            return
        if len(payload) > MAX_EMAIL_TEXT_PART_BYTES:
            payload = payload[:MAX_EMAIL_TEXT_PART_BYTES]

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
    except Exception as e:
        logging.debug(f"get_clean_email_text: {e}")

    if not body.strip() and body_html:
        body = body_html

    body = re.sub(r'<style.*?>.*?</style>', ' ', body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r'<script.*?>.*?</script>', ' ', body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r'<br\s*/?>', '\n', body, flags=re.IGNORECASE)
    body = re.sub(r'</p>', '\n\n', body, flags=re.IGNORECASE)
    body = re.sub(r'</div>', '\n', body, flags=re.IGNORECASE)
    body = re.sub(r'<[^>]+>', ' ', body)
    body = html.unescape(body)

    lines = [line.strip() for line in body.split('\n')]
    text = '\n'.join([line for line in lines if line])

    if skipped:
        # Dedup preservando ordine; annuncio breve per NVDA / lettore interno
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
    text = re.sub(r'<style.*?>.*?</style>', ' ', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<script.*?>.*?</script>', ' ', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join([line for line in lines if line])


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
        logging.warning(f"feedparser assente: impossibile analizzare {source}")
        return results
    try:
        feed = feedparser.parse(source)
    except Exception as e:
        logging.debug(f"Errore feedparser su {source}: {e}")
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
    except Exception as e:
        logging.debug(f"Errore lettura OPML {path}: {e}")
    # dedupe preserving order
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
        except Exception as e:
            logging.debug(f"Errore scansione profili {profiles_root}: {e}")
    # dedupe
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
    candidates = re.findall(r'https?://[^\s<>"\']+', search_blob)
    preferred = []
    others = []
    for c in candidates:
        url = c.rstrip(").,;]")
        low = url.lower()
        if any(x in low for x in ("facebook.com", "twitter.com", "instagram.com", "mailto:", "javascript:")):
            continue
        if "/news/" in low or re.search(r"/\d{4}/\d{2}/", low):
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
    parts = re.split(br'(?m)^From ', data)
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
    """Yield (index, email.message) from mailbox.mbox and/or From-line split.

    Per i Feed Thunderbird prefer_from_split=True: lo split su From_ è più
    affidabile dei file in Mail\\Feeds rispetto a mailbox.mbox.
    """
    data = None
    try:
        data = read_file_bytes_shared(file_path)
    except Exception as e:
        logging.debug(f"Lettura binaria fallita {file_path}: {e}")

    if prefer_from_split and data:
        yielded = False
        for item in _parse_messages_from_bytes(data):
            yielded = True
            yield item
        if yielded:
            return

    mb = None
    try:
        mb = mailbox.mbox(file_path)
        count = 0
        for msg in mb:
            yield count, msg
            count += 1
        if count > 0:
            return
    except Exception as e:
        logging.debug(f"mailbox.mbox fallito su {file_path}: {e}")
    finally:
        try:
            if mb:
                mb.close()
        except Exception:
            pass

    if data and not prefer_from_split:
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
    # Occorrenze del primo termine (come ricerca semplice in editor);
    # se più termini, conta le righe/blocchi che li contengono tutti.
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
        # fallback senza accenti
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
    # multi-termine: conta le "finestre" per riga
    lines = text.splitlines()
    return sum(1 for line in lines if text_matches_terms(line, terms))


def search_thunderbird_feed_file(file_path, terms, mtime, include_raw_lines=False):
    """Search Thunderbird Feeds file: one result per matching message (cleaned text).

    Se include_raw_lines=True, aggiunge anche risultati [FEED-RIGA] per le occorrenze grezze.
    """
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
    except Exception as e:
        logging.debug(f"Errore parse feed Thunderbird {file_path}: {e}")
        parsed_any = False

    if include_raw_lines:
        try:
            raw = read_file_bytes_shared(file_path)
            try:
                text_data = raw.decode("utf-8")
            except UnicodeDecodeError:
                text_data = raw.decode("latin1", errors="ignore")
            lines = text_data.replace("\x00", "").splitlines()
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
        except Exception as e:
            logging.debug(f"Occorrenze grezze feed fallite {file_path}: {e}")

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
                mlink = re.search(r'https?://[^\s<>"\']+', snippet)
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
    except Exception as e:
        logging.debug(f"Fallback raw feed fallito {file_path}: {e}")
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
    except Exception as e:
        logging.error(f"Errore controllo versione: {e}")
    return False

def create_html_help_file():
    help_path = os.path.join(CONFIG_DIR, "guida_ricerca_testuale.html")
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Guida Ufficiale - {APP_TITLE}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 30px; color: #111; background-color: #f9f9f9; max-width: 900px; }}
        h1 {{ color: #005a9c; border-bottom: 2px solid #005a9c; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 25px; }}
        ul {{ margin-left: 20px; }}
        li {{ margin-bottom: 8px; }}
        code {{ background-color: #eee; padding: 2px 5px; border-radius: 4px; font-weight: bold; }}
        .box {{ background-color: #eef6fc; border-left: 5px solid #005a9c; padding: 15px; margin: 20px 0; }}
        .note {{ background: #fff8e6; border-left: 5px solid #c90; padding: 12px; margin: 16px 0; }}
    </style>
</head>
<body>
    <h1>{APP_TITLE}</h1>
    <p><strong>Autore:</strong> Maurizio Barra (Accesso Digitale)</p>
    <p><em>Applicazione Standalone - Versione {APP_VERSION}</em></p>
    <div class="box">
        <p><strong>Novit&agrave; Versione 1.5.2</strong></p>
        <ul>
            <li><strong>Lettore email/MBOX:</strong> caricamento in secondo piano (niente blocco UI su caselle grandi); allegati PDF/binari esclusi dal testo.</li>
            <li><strong>Data messaggio</strong> (gg/mm/aaaa) anche nei risultati MBOX e .eml.</li>
            <li>Restano le novit&agrave; 1.5.1 (Cronologia) e 1.5.0 (Feed RSS/Thunderbird, filtro <code>Ctrl+F</code>).</li>
        </ul>
        <p><code>F7</code>: attiva/disattiva sintesi &middot; <code>CONTROL</code>: zittisce subito la lettura.</p>
    </div>
    <h2>Formati supportati</h2>
    <ul>
        <li>Testo (<code>.txt</code>, <code>.log</code>, <code>.csv</code>), Word, PDF, EML/MBOX, Feed RSS/Atom/Thunderbird, immagini con OCR di base.</li>
    </ul>
    <h2>Feed RSS e Thunderbird</h2>
    <ul>
        <li>Usa il pulsante <code>Feed Thunderbird</code> oppure inserisci URL/file feed/OPML nel percorso.</li>
        <li><code>[RSS]</code> / <code>[FEED]</code>: Invio apre l'articolo nel browser.</li>
        <li><code>[FEED-RIGA]</code> (se attiva la casella occorrenze grezze): Invio salta alla riga nel file.</li>
    </ul>
    <div class="note">
        <strong>Nota:</strong> articoli distinti = risultati <code>[FEED]</code>; occorrenze grezze nel file = <code>[FEED-RIGA]</code>. Lo stato spiega entrambi i numeri.
    </div>
    <h2>Scorciatoie da tastiera</h2>
    <ul>
        <li><code>Ctrl + H</code>: cronologia testi cercati.</li>
        <li><code>Ctrl + Shift + H</code>: cronologia percorsi usati.</li>
        <li><code>Ctrl + F</code>: salta alla casella filtro risultati.</li>
        <li><code>Alt + T</code>: tutto il PC (unit&agrave; attive).</li>
        <li><code>Alt + N</code>: annulla ricerca e mantieni i risultati.</li>
        <li><code>Alt + I</code>: info versione e autore.</li>
        <li><code>Alt + P</code>: annuncia lo stato (due volte = copia negli appunti).</li>
        <li><code>TAB</code> / <code>Alt+S</code> / <code>S</code>: campo accessibile di stato/avanzamento.</li>
        <li><code>Alt + K</code>: screenshot in <em>Catture di schermata</em>.</li>
        <li><code>Ctrl + P</code>: stampa risultati in lista.</li>
        <li><code>Ctrl + D</code>: aggiungi percorso ai segnalibri.</li>
        <li><code>SPAZIO</code> / <code>F4</code>: anteprima vocale del contesto.</li>
        <li><code>INVIO</code> sui risultati: apre file alla riga o articolo feed nel browser.</li>
        <li><code>Tasto APPLICAZIONI</code> / <code>Shift + F10</code>: menu contestuale.</li>
        <li><code>F1</code>: apre questa guida nel browser.</li>
        <li><code>ESC</code>: chiude la finestra attiva.</li>
    </ul>
    <p>Sostieni il progetto: <a href="{DONATION_URL}">{DONATION_URL}</a></p>
</body>
</html>
"""
    try:
        with open(help_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        logging.error(f"Errore creazione guida HTML: {e}")
    return help_path

def load_last_path():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                path = data.get("last_path", "")
                if path:
                    first_path = path.split(";")[0]
                    if first_path.startswith("http") or os.path.exists(first_path):
                        return path
    except Exception as e:
        logging.error(f"Errore caricamento ultimo percorso: {e}")
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
    except Exception as e:
        logging.error(f"Errore salvataggio ultimo percorso: {e}")

def load_bookmarks():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("bookmarks", [])
    except Exception as e:
        logging.error(f"Errore caricamento segnalibri: {e}")
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
    except Exception as e:
        logging.error(f"Errore salvataggio segnalibri: {e}")

HISTORY_MAX = 20


def _load_settings_dict():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        logging.error(f"Errore lettura impostazioni: {e}")
    return {}


def _save_settings_dict(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"Errore salvataggio impostazioni: {e}")


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
                    p_text = "".join([elem.text for elem in p.iter() if elem.tag.endswith("t") and elem.text])
                    if p_text.strip():
                        paragraphs.append(p_text.strip())
            return paragraphs
    except Exception as e:
        logging.debug(f"Errore estrazione testo DOCX {file_path}: {e}")
        return []

def extract_lines_from_pdf(file_path):
    try:
        with open(file_path, "rb") as f:
            content = f.read(4194304).decode("latin1", errors="ignore")
            matches = re.findall(r"\((.*?)\)", content)
            if not matches:
                matches = re.findall(r"[A-Za-z0-9àèéìòùÀÈÉÌÒÙ\s]{3,}", content)
            return [m.strip() for m in matches if m.strip()]
    except Exception as e:
        logging.debug(f"Errore estrazione PDF {file_path}: {e}")
        return []

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

def open_word_at_paragraph(file_path, paragraph_index, snippet_text):
    def _worker():
        opened = False
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import win32com.client
            try:
                word = win32com.client.GetActiveObject("Word.Application")
            except Exception:
                word = win32com.client.DispatchEx("Word.Application")
            word.Visible = True
            doc = word.Documents.Open(os.path.abspath(file_path))
            time.sleep(0.4)
            
            target_selected = False

            if snippet_text:
                try:
                    lines = [l.strip() for l in snippet_text.split("\n") if l.strip()]
                    for line_to_find in lines:
                        if len(line_to_find) > 12:
                            rng = doc.Content
                            find = rng.Find
                            find.ClearFormatting()
                            find.Text = line_to_find[:40]
                            find.Forward = True
                            find.Wrap = 0
                            if find.Execute():
                                rng.Select()
                                target_selected = True
                                break
                except Exception as e:
                    logging.debug(f"Errore ricerca testo esatto Word: {e}")

            if not target_selected and paragraph_index and paragraph_index > 0:
                try:
                    doc.Paragraphs(paragraph_index).Range.Select()
                    target_selected = True
                except Exception as e:
                    logging.debug(f"Errore selezione paragrafo Word: {e}")

            if not target_selected:
                rng = doc.Content
                rng.Select()

            word.Activate()
            hwnd = ctypes.windll.user32.FindWindowW(None, word.Caption)
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 3)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            opened = True
        except Exception as e:
            logging.error(f"Fallita apertura COM di Word per {file_path}: {e}")
        
        if not opened:
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "open", file_path, None, None, 1)
            except Exception as e:
                logging.error(f"Fallita apertura fallback ShellExecute: {e}")

    threading.Thread(target=_worker, daemon=True).start()

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
    """Restituisce (pos, length) del primo termine trovato, o (-1, 0)."""
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

        speak_accessible("Caricamento email in corso.")
        threading.Thread(target=self._load_worker, daemon=True).start()

    def on_close(self, event):
        self._closed = True
        event.Skip()

    def _load_worker(self):
        logging.info(f"Avvio visualizzazione interna EML: {self.file_path}")
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
        except Exception as e:
            err = e
            logging.error(f"Impossibile leggere file email: {e}")
        if self._closed:
            return
        if err is not None:
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
        speak_accessible("Email caricata.")

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
            self.txt_display.SetValue(
                "Preparazione visualizzazione…\r\n"
            )
        else:
            self.txt_display.SetValue(
                "Caricamento messaggio in corso…\r\n"
                "Su caselle Thunderbird molto grandi può richiedere alcuni secondi.\r\n"
                "La finestra resta utilizzabile: puoi chiudere con ESC."
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
            speak_accessible(f"Messaggio {msg_index + 1} dalla ricerca.")
            wx.CallAfter(self._apply_loaded_text, cached_text)
        else:
            speak_accessible(
                f"Caricamento messaggio {msg_index + 1} dall'archivio. Attendere."
            )
            threading.Thread(target=self._load_worker, daemon=True).start()

    def on_close(self, event):
        self._closed = True
        event.Skip()

    def _load_worker(self):
        logging.info(
            f"Avvio visualizzazione interna MBOX (stream): {self.mbox_file_path} "
            f"(indice {self.msg_index})"
        )
        full_text = None
        err = None

        def _progress(n):
            if self._closed:
                return
            logging.info(f"MBOX stream: scanditi {n} messaggi verso indice {self.msg_index}")
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
            logging.info("Caricamento MBOX interrotto dall'utente.")
            return
        except Exception as e:
            err = e
            logging.error(
                f"Impossibile leggere il messaggio {self.msg_index} "
                f"in {self.mbox_file_path}: {e}"
            )
        if self._closed:
            return
        if err is not None:
            wx.CallAfter(
                self._apply_loaded_text,
                "Errore durante la lettura del messaggio.\r\n"
                "Suggerimento: se hai trovato il messaggio con una ricerca, "
                "riavvia la ricerca e riapri il risultato "
                "(il testo viene tenuto in memoria e si apre subito).\r\n"
                "In alternativa chiudi Thunderbird e riprova.",
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
        speak_accessible("Messaggio caricato.")

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
            f"Benvenuto nella versione {APP_VERSION}!\n\n"
            "Ecco le novità principali di questo aggiornamento:\n"
            "--------------------------------------------------\n"
            "• Lettore email/MBOX: apertura immediata dai risultati di ricerca\n"
            "  (testo già letto in scansione; niente nuovo indice su caselle enormi).\n"
            "• Allegati PDF/binari esclusi dal testo; data messaggio nei risultati.\n"
            "• Ordinamento risultati memorizzato (dal più recente / meno recente / nome).\n"
            "• Caricamento di fallback a streaming se serve rileggere il file.\n\n"
            "• Restano attive le novità della 1.5.1 (Cronologia) e della 1.5.0 (Feed).\n"
            "--------------------------------------------------\n"
            "Grazie per usare Ricerca Testuale Accesso Digitale!\n"
        )

        lbl_info = wx.StaticText(panel, label="Leggi la novità dell'ultimo aggiornamento:")
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
        
        speak_accessible("Finestra delle novità aperta. Usa le frecce per leggere.")

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            event.Skip()

class ShortcutsFrame(wx.Frame):
    def __init__(self, parent):
        super(ShortcutsFrame, self).__init__(
            parent,
            title=f"{APP_TITLE} v{APP_VERSION} - Comandi",
            size=(700, 580),
            style=wx.DEFAULT_FRAME_STYLE,
        )

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.text_content = (
            f"{APP_TITLE} v{APP_VERSION}\n"
            "Autore e Sviluppatore: Maurizio Barra (Accesso Digitale)\n\n"
            "--------------------------------------------------\n"
            "COMANDI E SCORCIATOIE DA TASTIERA (STANDALONE):\n"
            "--------------------------------------------------\n"
            "  - Ctrl + H : Cronologia testi cercati (riprendi una ricerca precedente)\n"
            "  - Ctrl + Shift + H : Cronologia percorsi usati\n"
            "  - Ctrl + F : Salta alla casella per filtrare i risultati trovati\n"
            "  - Alt + T : Seleziona TUTTO IL PC (tutte le unità attive)\n"
            "  - Alt + N : Annulla ricerca in corso e mantieni i risultati\n"
            "  - Alt + I : Info Versione e Autore\n"
            "  - Alt + P : Annuncia stato (Premi due volte velocemente per copiare negli appunti)\n"
            "  - TAB oppure Alt+S / S : Raggiunge la casella 'Stato avanzamento'\n"
            "  - Alt + K : Scatta uno screenshot salvato in 'Catture di schermata'\n"
            "  - Ctrl + P: Stampa rapida risultati di ricerca in lista\n"
            "  - Ctrl + D: Aggiungi percorso ai segnalibri\n"
            "  - INVIO : Avvia ricerca, apri file alla riga esatta o apri articolo nel Browser\n"
            "  - SPAZIO / F4 : Anteprima vocale immediata del risultato\n"
            "  - F7 : Attiva / Disattiva sintesi vocale (Mute)\n"
            "  - CONTROL : Zittisce all'istante la lettura in corso\n"
            "  - Pulsante Feed Thunderbird : rileva le cartelle Feeds di Thunderbird\n"
            "  - Supporto OPML / RSS locale : file .opml, .rss, .atom, .xml nel percorso\n"
            "  - Tasto APPLICAZIONI : Menu contestuale completo\n"
            "  - F1 : Apri la Guida HTML nel Browser\n"
            "  - ESC : Chiudi la finestra\n\n"
            "--------------------------------------------------\n"
            "SOSTIENI IL PROGETTO:\n"
            f"{DONATION_URL}\n"
            "--------------------------------------------------"
        )

        lbl_info = wx.StaticText(panel, label="Usa le frecce Su/Giù e Sinistra/Destra per navigare nel testo:")
        vbox.Add(lbl_info, 0, wx.ALL, 8)

        self.txt_display = wx.TextCtrl(panel, value=self.text_content, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_copy = wx.Button(panel, label="&Copia Testo Comandi")
        btn_copy.Bind(wx.EVT_BUTTON, self.on_copy_text)
        hbox_btns.Add(btn_copy, 0, wx.ALL, 5)

        btn_guide = wx.Button(panel, label="Apri &Guida Browser...")
        btn_guide.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open(f"file:///{create_html_help_file()}"))
        hbox_btns.Add(btn_guide, 0, wx.ALL, 5)

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
            speak_accessible("Testo copiato negli appunti!")

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            event.Skip()

class MainWindow(wx.Frame):
    def __init__(self):
        super(MainWindow, self).__init__(
            None,
            title=f"{APP_TITLE} v{APP_VERSION} - Maurizio Barra",
            size=(880, 800),
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
        self.current_sort = load_sort_preference()
        self.last_feed_raw_occurrences = 0

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
                "Solo Documenti (.txt, .eml, .log, .csv, .docx, .doc, .pdf, .mbox, .rss, .opml)",
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
        self.txt_custom_ext = wx.TextCtrl(panel, value="")
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

        lbl_results = wx.StaticText(panel, label="&Risultati trovati (INVIO apre file, SPAZIO/F4 anteprima vocale, APPLICAZIONI opzioni):")
        vbox.Add(lbl_results, 0, wx.ALL, 5)
        self.lst_results = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.lst_results.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open_file_event)
        self.lst_results.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.lst_results.Bind(wx.EVT_KEY_DOWN, self.on_list_key_down)
        vbox.Add(self.lst_results, 1, wx.EXPAND | wx.ALL, 5)

        hbox_bottom = wx.BoxSizer(wx.HORIZONTAL)
        btn_open = wx.Button(panel, label="&Apri File (Alla Riga)")
        btn_open.Bind(wx.EVT_BUTTON, self.on_open_file_event)
        hbox_bottom.Add(btn_open, 0, wx.ALL, 5)

        btn_preview = wx.Button(panel, label="Anteprima &Voce (F4)")
        btn_preview.Bind(wx.EVT_BUTTON, lambda e: self.speak_selected_preview())
        hbox_bottom.Add(btn_preview, 0, wx.ALL, 5)

        btn_close = wx.Button(panel, label="C&hiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        hbox_bottom.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_bottom, 0, wx.ALIGN_CENTER)
        panel.SetSizer(vbox)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_global_char_hook)
        
        if check_first_run_update():
            wx.CallLater(600, self.show_whats_new_dialog)

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
        item_update = tools_menu.Append(wx.ID_ANY, "Verifica &Aggiornamenti...\tCtrl+U")
        menubar.Append(tools_menu, "&Strumenti")

        # Menu Aiuto
        help_menu = wx.Menu()
        item_whatsnew = help_menu.Append(wx.ID_ANY, "&Novità della Versione")
        item_guide = help_menu.Append(wx.ID_ANY, "&Guida ai Comandi\tF1")
        item_print_guide = help_menu.Append(wx.ID_ANY, "Stampa &Guida ai Comandi")
        item_github = help_menu.Append(wx.ID_ANY, "Pagina Ufficiale &GitHub")
        item_info = help_menu.Append(wx.ID_ANY, "&Info Versione\tAlt+I")
        help_menu.AppendSeparator()
        item_log = help_menu.Append(wx.ID_ANY, "Esporta &Log di Diagnostica sul Desktop")
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
        self.Bind(wx.EVT_MENU, lambda e: webbrowser.open(GITHUB_REPO_URL), item_github)
        self.Bind(wx.EVT_MENU, self.on_show_info, item_info)
        self.Bind(wx.EVT_MENU, self.on_export_log, item_log)
        self.Bind(wx.EVT_MENU, self.on_send_feedback, item_feedback)

    def on_add_bookmark(self, event=None):
        path = self.txt_path.GetValue().strip()
        if not path:
            speak_accessible("Nessun percorso da salvare.")
            return
        bms = load_bookmarks()
        if path not in bms:
            bms.append(path)
            save_bookmarks(bms)
            self.update_bookmarks_menu()
            speak_accessible("Percorso salvato nei segnalibri.")
        else:
            speak_accessible("Percorso già presente nei segnalibri.")

    def on_manage_bookmarks(self, event=None):
        bms = load_bookmarks()
        if not bms:
            speak_accessible("Nessun segnalibro salvato.")
            return
        dlg = wx.SingleChoiceDialog(self, "Seleziona il segnalibro da ELIMINARE:", "Gestione Segnalibri", bms)
        if dlg.ShowModal() == wx.ID_OK:
            sel = dlg.GetStringSelection()
            if sel in bms:
                bms.remove(sel)
                save_bookmarks(bms)
                self.update_bookmarks_menu()
                speak_accessible("Segnalibro eliminato correttamente.")
        dlg.Destroy()

    def on_select_bookmark(self, path):
        self.txt_path.SetValue(path)
        save_last_path(path)
        speak_accessible(f"Segnalibro caricato: {path}")

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
            speak_accessible("Nessun testo nella cronologia.")
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
            speak_accessible("Nessun percorso nella cronologia.")
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
                speak_accessible(f"Percorso ripreso: {sel}")
        dlg.Destroy()

    def on_apply_history_query(self, query):
        self.txt_query.SetValue(query)
        self.txt_query.SetFocus()
        self.txt_query.SetInsertionPointEnd()
        speak_accessible(f"Testo ripreso: {query}")

    def on_clear_query_history(self, event=None):
        if not load_query_history():
            speak_accessible("La cronologia testi è già vuota.")
            return
        clear_query_history()
        self.update_history_menu()
        speak_accessible("Cronologia testi svuotata.")

    def on_clear_path_history(self, event=None):
        if not load_path_history():
            speak_accessible("La cronologia percorsi è già vuota.")
            return
        clear_path_history()
        speak_accessible("Cronologia percorsi svuotata.")

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

    def get_dynamic_desktop_path(self):
        desktop_path = os.path.expanduser("~\\Desktop")
        if not os.path.exists(desktop_path):
            desktop_path = os.path.expanduser("~\\OneDrive\\Desktop")
            if not os.path.exists(desktop_path):
                desktop_path = os.path.expanduser("~")
        return desktop_path

    def on_export_log(self, event):
        try:
            desktop_path = self.get_dynamic_desktop_path()
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            dest = os.path.join(desktop_path, f"Log_RTAD_{timestamp}.txt")
            
            if os.path.exists(LOG_FILE):
                shutil.copy(LOG_FILE, dest)
                msg = f"Log di diagnostica esportato sul Desktop come Log_RTAD_{timestamp}."
                logging.info(msg)
                speak_accessible("Log esportato con successo sul Desktop.")
                wx.MessageBox("File di log salvato correttamente sul Desktop.", "Esportazione Riuscita", wx.OK | wx.ICON_INFORMATION)
            else:
                speak_accessible("Nessun file di log presente.")
        except Exception as e:
            logging.error(f"Errore durante l'esportazione del log: {e}")
            speak_accessible("Errore nell'esportazione del log.")

    def on_send_feedback(self, event):
        try:
            sys_info = f"{platform.system()} {platform.release()} ({platform.version()})"
            subject = urllib.parse.quote(f"Feedback {APP_TITLE} v{APP_VERSION}")
            body = urllib.parse.quote(
                f"Ciao Maurizio,\n\nTi scrivo per segnalarti un suggerimento o un problema riscontrato...\n\n"
                f"[SE SEGNALI UN ERRORE, RICORDATI DI ALLEGARE IL FILE 'Log_RTAD' CHE HAI ESPORTATO SUL DESKTOP]\n\n"
                f"----------------------------------------\n"
                f"Dati Tecnici per Assistenza (non eliminare):\n"
                f"Versione App: {APP_VERSION}\n"
                f"Sistema Operativo: {sys_info}\n"
                f"----------------------------------------\n"
            )
            url = f"mailto:{EMAIL_DESTINATARIO}?subject={subject}&body={body}"
            webbrowser.open(url)
            speak_accessible("Apertura client di posta per la segnalazione...")
            logging.info("Apertura form di feedback via mail.")
        except Exception as e:
            logging.error(f"Impossibile aprire il client di posta per feedback: {e}")
            speak_accessible("Impossibile aprire il programma di posta.")

    def show_whats_new_dialog(self):
        dlg = WhatsNewFrame(self)
        dlg.Show()
        dlg.Raise()

    def show_shortcuts_dialog(self):
        dlg = ShortcutsFrame(self)
        dlg.Show()
        dlg.Raise()

    def on_filter_changed(self, event):
        sel = self.combo_filter.GetSelection()
        self.txt_custom_ext.Enable(sel == 4)
        if sel != 4:
            self.txt_custom_ext.SetValue("")

    def on_search_all_pc(self, event):
        drives = get_real_ready_drives()
        drives_str = ";".join(drives)
        self.txt_path.SetValue(drives_str)
        save_last_path(drives_str)
        speak_accessible(f"Tutto il PC impostato: {len(drives)} unità attive. Premi Invio per avviare.")
        self.btn_search.SetFocus()

    def on_detect_thunderbird_feeds(self, event):
        dirs = find_thunderbird_feeds_dirs()
        if not dirs:
            speak_accessible(
                "Nessuna cartella Feed Thunderbird trovata. "
                "Verifica che Thunderbird sia installato e che esistano i Feed RSS nel profilo."
            )
            logging.warning("Nessuna cartella Feed Thunderbird rilevata.")
            return
        joined = ";".join(dirs)
        self.txt_path.SetValue(joined)
        save_last_path(joined)
        n = len(dirs)
        speak_accessible(
            f"Trovate {n} cartelle Feed Thunderbird. Percorso aggiornato. "
            "Inserisci la parola da cercare e premi Avvia Ricerca."
        )
        self.txt_query.SetFocus()


    def copy_status_to_clipboard(self):
        if not self.btn_search.IsEnabled():
            found = getattr(self, 'live_matches_count', 0)
            msg = f"Avanzamento {self.current_percent} percento. File esaminati {self.scanned_count}. Risultati trovati {found}."
        else:
            found = self.lst_results.GetCount()
            msg = f"Stato: {self.txt_status_progress.GetValue()} Risultati in lista filtrata: {found}."
        
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(msg))
            wx.TheClipboard.Close()
            speak_accessible("Stato copiato negli appunti.")
        else:
            speak_accessible("Impossibile copiare negli appunti.")

    def focus_status_progress(self, event=None):
        try:
            self.txt_status_progress.SetFocus()
            self.txt_status_progress.SetInsertionPoint(0)
            msg = self.txt_status_progress.GetValue().strip() or "Stato avanzamento non disponibile."
            speak_accessible(msg)
        except Exception:
            speak_accessible("Impossibile raggiungere lo stato di avanzamento.")

    def announce_progress(self):
        current_time = time.time()
        is_double_tap = (current_time - self.last_alt_p_time) < 0.6
        self.last_alt_p_time = current_time

        if is_double_tap:
            self.copy_status_to_clipboard()
            return

        if not self.btn_search.IsEnabled():
            found = getattr(self, 'live_matches_count', 0)
            msg = f"Avanzamento {self.current_percent} percento. File esaminati {self.scanned_count}. Risultati trovati {found}."
        else:
            found = self.lst_results.GetCount()
            msg = f"Stato: {self.txt_status_progress.GetValue()} Risultati in lista: {found}."
        
        speak_accessible(msg)

    def on_cancel_search(self, event):
        if not self.btn_search.IsEnabled():
            self._stop_search = True
            self.btn_cancel.Disable()
            logging.info("Ricerca interrotta volontariamente dall'utente.")
            speak_accessible("Ricerca interrotta dall'utente. Salvataggio risultati parziali in corso...")

    def on_show_info(self, event):
        msg = f"{APP_TITLE}\nVersione: {APP_VERSION}\nAutore: Maurizio Barra\nLicenza: GPL v2"
        speak_accessible(f"Versione installata {APP_VERSION}. Autore Maurizio Barra.")
        wx.MessageBox(msg, "Informazioni Versione", wx.OK | wx.ICON_INFORMATION)

    def on_global_char_hook(self, event):
        key = event.GetKeyCode()
        alt = event.AltDown()
        ctrl = event.ControlDown()

        if key == wx.WXK_CONTROL and not alt and not event.ShiftDown():
            stop_accessible_speech()
            event.Skip()
            return

        if ctrl and key in (ord("F"), ord("f")):
            self.txt_filter.SetFocus()
            speak_accessible("Filtra risultati")
            return
        elif ctrl and key in (ord("H"), ord("h")) and event.ShiftDown():
            self.on_recall_path_history()
            return
        elif ctrl and key in (ord("H"), ord("h")):
            self.on_recall_query_history()
            return
        elif ctrl and key in (ord("P"), ord("p")):
            self.on_print_results(None)
            return
        elif ctrl and key in (ord("D"), ord("d")):
            self.on_add_bookmark(None)
            return
        elif alt and key in (ord("P"), ord("p")):
            self.announce_progress()
            return
        elif alt and key in (ord("S"), ord("s")):
            self.focus_status_progress()
            return
        elif alt and key in (ord("T"), ord("t")):
            self.on_search_all_pc(None)
            return
        elif alt and key in (ord("K"), ord("k")):
            self.on_take_screenshot(None)
            return
        elif alt and key in (ord("N"), ord("n")):
            self.on_cancel_search(None)
            return
        elif alt and key in (ord("I"), ord("i")):
            self.on_show_info(None)
            return
        elif key in (wx.WXK_F3, wx.WXK_F4):
            self.speak_selected_preview()
            return
        elif key == wx.WXK_F1:
            self.show_shortcuts_dialog()
            return
        elif key == wx.WXK_F7:
            self.on_toggle_speech()
            return
        elif key == wx.WXK_SHIFT:
            event.Skip()
            return
        elif key == wx.WXK_ESCAPE:
            self._stop_search = True
            self.Destroy()
            return

        focus = wx.Window.FindFocus()
        text_ctrls = (self.txt_query, self.txt_path, self.txt_custom_ext, self.txt_filter)

        if key in (ord("S"), ord("s")) and not ctrl and not alt and not event.ShiftDown():
            if focus not in text_ctrls and not isinstance(focus, wx.TextCtrl):
                self.focus_status_progress()
                return

        if key == wx.WXK_SPACE:
            if focus not in text_ctrls and not isinstance(focus, wx.Button):
                self.speak_selected_preview()
                return

        if focus == self.lst_results or (focus not in text_ctrls and not isinstance(focus, wx.Button)):
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                self.open_selected_file()
                return
            elif key == wx.WXK_WINDOWS_MENU:
                self.on_context_menu(None)
                return

        event.Skip()

    def on_toggle_speech(self, evt=None):
        global _speech_active
        stop_accessible_speech()
        _speech_active = not _speech_active
        if _speech_active:
            speak_accessible("Sintesi vocale attivata", force=True)
        else:
            speak_accessible("Sintesi vocale disattivata", force=True)

    def on_close(self, event):
        self._stop_search = True
        self.Destroy()

    def on_browse(self, event):
        dlg = wx.DirDialog(self, "Seleziona cartella o unità", defaultPath=self.txt_path.GetValue())
        if dlg.ShowModal() == wx.ID_OK:
            selected_path = dlg.GetPath()
            self.txt_path.SetValue(selected_path)
            save_last_path(selected_path)
            speak_accessible(f"Percorso impostato: {selected_path}.")
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
                os.makedirs(pictures_dir, exist_ok=True)
            filename = f"Screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            full_path = os.path.join(pictures_dir, filename)
            bmp.SaveFile(full_path, wx.BITMAP_TYPE_PNG)
            logging.info(f"Screenshot salvato in {full_path}")
            speak_accessible("Screenshot salvato con successo in Catture di schermata.")
        except Exception as e:
            logging.error(f"Fallimento salvataggio screenshot: {e}")
            speak_accessible("Impossibile salvare lo screenshot.")

    def on_export_results(self, event):
        if not self.current_matches:
            speak_accessible("Nessun risultato da esportare.")
            return
            
        wildcard_filters = "File di Testo (*.txt)|*.txt|Pagina Web HTML (*.html)|*.html|File CSV per Tabelle (*.csv)|*.csv"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dlg = wx.FileDialog(self, message="Esporta Risultati", 
                            defaultDir=self.get_dynamic_desktop_path(),
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
                
                logging.info(f"Esportati {len(self.current_matches)} risultati in {export_file}")
                speak_accessible("Risultati esportati con successo nel formato scelto.")
            except Exception as e:
                logging.error(f"Errore esportazione risultati: {e}")
                speak_accessible("Errore durante l'esportazione.")
        dlg.Destroy()

    def on_print_results(self, event):
        total_matches = len(self.current_matches)
        if total_matches == 0:
            speak_accessible("Nessun risultato da stampare.")
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
                    speak_accessible("Inviati tutti i risultati alla stampante predefinita.")
                else:
                    speak_accessible(f"Inviati i primi {limit} risultati alla stampante predefinita.")
            except Exception as e:
                logging.error(f"Errore durante la stampa dei risultati: {e}")
                speak_accessible("Impossibile stampare. Assicurati di avere una stampante configurata.")
        else:
            dlg.Destroy()
            speak_accessible("Stampa annullata.")

    def on_print_guide(self, event):
        temp_guide_path = os.path.join(CONFIG_DIR, "stampa_guida.txt")
        try:
            guide_text = (
                f"{APP_TITLE} v{APP_VERSION}\n"
                "Autore e Sviluppatore: Maurizio Barra (Accesso Digitale)\n\n"
                "--- COMANDI E SCORCIATOIE DA TASTIERA (STANDALONE) ---\n\n"
                "Ctrl + H : Cronologia testi cercati\n"
                "Ctrl + Shift + H : Cronologia percorsi\n"
                "Ctrl + F : Salta alla casella per filtrare i risultati trovati\n"
                "Alt + T : Seleziona TUTTO IL PC (tutte le unità attive)\n"
                "Alt + N : Annulla ricerca in corso e mantieni i risultati\n"
                "Alt + I : Info Versione e Autore\n"
                "Alt + P : Annuncia stato (Premi due volte velocemente per copiare negli appunti)\n"
                "TAB / Alt+S / S : Raggiunge la casella 'Stato avanzamento'\n"
                "Alt + K : Scatta uno screenshot salvato in 'Catture di schermata'\n"
                "Ctrl + P: Stampa rapida risultati di ricerca in lista\n"
                "Ctrl + D: Aggiungi percorso ai segnalibri\n"
                "INVIO : Avvia ricerca o apri file alla riga esatta\n"
                "SPAZIO / F4 : Anteprima vocale immediata del risultato\n"
                "F7 : Attiva / Disattiva sintesi vocale (Mute)\n"
                "CONTROL : Zittisce all'istante la lettura in corso\n"
                "Tasto APPLICAZIONI : Menu contestuale completo\n"
                "F1 : Apri la Guida HTML nel Browser\n"
                "ESC : Chiudi la finestra\n"
            )
            with open(temp_guide_path, "w", encoding="utf-8") as f:
                f.write(guide_text)

            notepad_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "notepad.exe")
            if not os.path.exists(notepad_path):
                notepad_path = "notepad.exe"
                
            subprocess.Popen([notepad_path, "/p", temp_guide_path])
            
            speak_accessible("Guida ai comandi inviata alla stampante predefinita.")
        except Exception as e:
            logging.error(f"Errore durante la stampa della guida: {e}")
            speak_accessible("Impossibile stampare la guida. Assicurati di avere una stampante configurata.")

    def on_list_key_down(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_SPACE, wx.WXK_F3, wx.WXK_F4):
            self.speak_selected_preview()
            return
        elif key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.open_selected_file()
            return
        event.Skip()

    def speak_selected_preview(self):
        sel = self.lst_results.GetSelection()
        if sel == wx.NOT_FOUND:
            speak_accessible("Nessun elemento selezionato nella lista.")
            return
        item = self.file_map.get(sel)
        if item:
            snip = item.get("snippet", "").strip()
            loc = item.get("location_info", "")
            fname = item.get("file_name", "")
            if snip:
                speak_accessible(f"{loc}. {snip}")
            else:
                speak_accessible(f"{fname}. Nessuna riga di anteprima.")
        else:
            riga = self.lst_results.GetString(sel)
            speak_accessible(f"Elemento: {riga}")

    def on_check_updates(self, event=None, silent=False):
        def _check():
            try:
                if not silent:
                    speak_accessible("Verifica aggiornamenti in corso...")
                req = urllib.request.Request(GITHUB_API_LATEST, headers={"User-Agent": "RTAD-Updater"})
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    latest_tag = data.get("tag_name", "").replace("app-", "").replace("v", "").strip()
                    html_url = data.get("html_url", GITHUB_REPO_URL)
                    
                    if latest_tag:
                        try:
                            v_online = [int(x) for x in latest_tag.split('.')]
                            v_local = [int(x) for x in APP_VERSION.split('.')]
                            is_newer = v_online > v_local
                        except Exception:
                            is_newer = latest_tag != APP_VERSION
                            
                        if is_newer:
                            logging.info(f"Nuova versione trovata: {latest_tag}")
                            exe_url = None
                            for asset in data.get("assets", []):
                                if asset.get("name", "").endswith(".exe"):
                                    exe_url = asset.get("browser_download_url")
                                    break
                            def _prompt():
                                dlg = wx.MessageDialog(self, f"Nuova versione {latest_tag} disponibile!\n\nScarico subito?", "Aggiornamento", wx.YES_NO | wx.ICON_QUESTION)
                                if dlg.ShowModal() == wx.ID_YES:
                                    dlg.Destroy()
                                    if exe_url:
                                        def _dl():
                                            try:
                                                speak_accessible("Download in corso, attendere...")
                                                out = os.path.join(os.path.expanduser("~"), "Downloads", f"Ricerca_Testuale_v{latest_tag}.exe")
                                                req2 = urllib.request.Request(exe_url, headers={"User-Agent": "Mozilla/5.0"})
                                                with urllib.request.urlopen(req2) as resp, open(out, "wb") as f_out:
                                                    f_out.write(resp.read())
                                                logging.info("Download aggiornamento completato. Avvio installer.")
                                                speak_accessible("Avvio aggiornamento.")
                                                subprocess.Popen([out])
                                                wx.CallAfter(self.Close)
                                            except Exception as e:
                                                logging.error(f"Errore download aggiornamento: {e}")
                                                wx.CallAfter(lambda: speak_accessible("Errore download."))
                                        threading.Thread(target=_dl, daemon=True).start()
                                    else:
                                        webbrowser.open(html_url)
                                else:
                                    dlg.Destroy()
                            wx.CallAfter(_prompt)
                        else:
                            if not silent:
                                wx.CallAfter(lambda: speak_accessible("Versione aggiornata."))
            except Exception as e:
                logging.warning(f"Impossibile verificare aggiornamenti: {e}")
                if not silent:
                    wx.CallAfter(lambda: speak_accessible("Impossibile verificare connessione."))
        threading.Thread(target=_check, daemon=True).start()

    def start_search_thread(self):
        query = self.txt_query.GetValue().strip()
        target_input = self.txt_path.GetValue().strip()
        filter_mode = self.combo_filter.GetSelection()
        custom_ext = self.txt_custom_ext.GetValue().strip().lower()
        if not custom_ext.startswith(".") and custom_ext:
            custom_ext = "." + custom_ext
        include_feed_raw = bool(self.chk_feed_raw.GetValue())

        if not query:
            speak_accessible("Inserire un testo da cercare.")
            return

        self._stop_search = False
        self.current_query = query
        self.current_percent = 0
        self.scanned_count = 0
        self.live_matches_count = 0
        self.last_feed_raw_occurrences = 0
        self.txt_filter.SetValue("")
        save_last_path(target_input)
        add_query_to_history(query)
        add_path_to_history(target_input)
        self.update_history_menu()

        self.lst_results.Clear()
        
        # --- FIX NVDA SCONOSCIUTO ---
        self.lst_results.Append("Ricerca in corso... attendere prego.")
        
        self.file_map.clear()
        self.current_matches = []
        self.gauge.SetValue(0)
        self.txt_status_progress.SetValue("Ricerca in corso: 0%...")
        
        self.btn_search.Disable()
        self.btn_cancel.Enable()

        logging.info(f"Avvio ricerca. Testo: '{query}'. Tipo filtro: {filter_mode}. Path: {target_input}")
        speak_accessible(f"Ricerca avviata per '{query}'.")

        # --- INIZIO FEEDBACK ACUSTICO AVVIO ---
        threading.Thread(target=lambda: winsound.Beep(800, 150), daemon=True).start()
        # --- FINE FEEDBACK ACUSTICO ---

        targets = [t.strip() for t in re.split(r'[;,]', target_input) if t.strip()]
        threading.Thread(
            target=self.run_search,
            args=(query, targets, filter_mode, custom_ext, include_feed_raw),
            daemon=True,
        ).start()

    def run_search(self, query, targets, filter_mode, custom_ext, include_feed_raw=False):
        raw_matches = []
        ignored = ["$recycle.bin", "system volume information", "appdata\\local\\temp"]
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
                if any(ign in root.lower() for ign in ignored):
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

        # Expand OPML into feed URLs (counted in progress)
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

        # === Feed RSS/Atom (URL o file locali) ===
        missing_feedparser_announced = False
        for source in rss_sources:
            if self._stop_search:
                break
            if feedparser is None:
                if not missing_feedparser_announced:
                    missing_feedparser_announced = True
                    logging.warning("feedparser mancante: impossibile cercare nei feed RSS/Atom.")
                    wx.CallAfter(
                        speak_accessible,
                        "Modulo feedparser non installato: ricerca RSS non disponibile.",
                    )
                bump_progress()
                continue
            try:
                raw_matches.extend(search_online_or_local_feed(source, terms))
            except Exception as e:
                logging.debug(f"Errore lettura Feed {source}: {e}")
            bump_progress()

        # === Scansione file locali ===
        for file_path in file_list:
            if self._stop_search:
                break
            file_name = os.path.basename(file_path)
            ext = os.path.splitext(file_name)[1].lower()

            is_feed = is_thunderbird_feeds_path(file_path)
            is_mbox = False
            if ext in [".mbox", ".mbx"]:
                is_mbox = True
            elif is_thunderbird_mail_container(file_path) and not is_feed:
                is_mbox = True

            if is_mbox:
                ext = ".mbox"

            prefix = f"[{ext.replace('.', '').upper()}]"

            try:
                mtime = os.path.getmtime(file_path)
            except Exception:
                mtime = 0

            try:
                name_matched = text_matches_terms(file_name, terms)
                found_in_content = False

                if ext in img_exts:
                    img_text = normalize_search_text(deep_ocr_jpg_scan(file_path))
                    if all(t in img_text for t in terms):
                        raw_matches.append({
                            "file_path": file_path, "file_name": file_name, "prefix": "[IMG-TEXT]",
                            "mtime": mtime, "line_number": None, "paragraph_index": None,
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

                elif is_mbox:
                    mb = None
                    try:
                        mb = mailbox.mbox(file_path)
                        for msg_idx, msg in enumerate(mb):
                            if self._stop_search:
                                break
                            subject = decode_email_header(str(msg.get("subject", "")))
                            sender = decode_email_header(str(msg.get("from", "")))
                            body = get_clean_email_text(msg)
                            msg_ts = message_date_timestamp(msg, fallback=mtime)
                            msg_found = False
                            date_label = format_email_date_label(msg, fallback_ts=msg_ts)
                            date_suffix = f" {date_label}" if date_label else ""
                            if body:
                                lines = body.split("\n")
                                for line_idx, line in enumerate(lines):
                                    if text_matches_terms(line, terms):
                                        start_i = max(0, line_idx - 1)
                                        end_i = min(len(lines), line_idx + 2)
                                        snip = " ".join([l.strip() for l in lines[start_i:end_i]]).strip()
                                        raw_matches.append({
                                            "file_path": file_path, "file_name": file_name,
                                            "prefix": "[MBOX]", "mtime": msg_ts,
                                            "line_number": msg_idx, "paragraph_index": None,
                                            "location_info": f"Testo Msg {msg_idx + 1}{date_suffix}",
                                            "snippet": snip,
                                            "viewer_text": _format_email_viewer_text(msg),
                                        })
                                        found_in_content = True
                                        msg_found = True
                                        break
                            if not msg_found and (text_matches_terms(subject, terms) or text_matches_terms(sender, terms)):
                                raw_matches.append({
                                    "file_path": file_path, "file_name": file_name,
                                    "prefix": "[MBOX]", "mtime": msg_ts,
                                    "line_number": msg_idx, "paragraph_index": None,
                                    "location_info": f"Oggetto Msg {msg_idx + 1}{date_suffix}",
                                    "snippet": f"Trovato nell'intestazione: {subject} da {sender}",
                                    "viewer_text": _format_email_viewer_text(msg),
                                })
                                found_in_content = True
                    except Exception as e:
                        logging.debug(f"Errore lettura MBOX {file_path}: {e}")
                    finally:
                        try:
                            if mb:
                                mb.close()
                        except Exception:
                            pass

                elif ext == ".eml":
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            msg = email.message_from_file(f, policy=policy.default)
                    except Exception:
                        with open(file_path, "r", encoding="latin1", errors="ignore") as f:
                            msg = email.message_from_file(f, policy=policy.default)

                    subject = decode_email_header(str(msg.get("subject", "")))
                    sender = decode_email_header(str(msg.get("from", "")))
                    body = get_clean_email_text(msg)
                    msg_ts = message_date_timestamp(msg, fallback=mtime)
                    date_label = format_email_date_label(msg, fallback_ts=msg_ts)
                    date_suffix = f" {date_label}" if date_label else ""

                    if body:
                        lines = body.split("\n")
                        for line_idx, line in enumerate(lines):
                            if text_matches_terms(line, terms):
                                start_i = max(0, line_idx - 1)
                                end_i = min(len(lines), line_idx + 2)
                                snippet = " ".join([l.strip() for l in lines[start_i:end_i]]).strip()
                                raw_matches.append({
                                    "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                    "mtime": msg_ts, "line_number": line_idx + 1, "paragraph_index": None,
                                    "location_info": f"Testo Email{date_suffix}", "snippet": snippet,
                                })
                                found_in_content = True
                                break

                    if not found_in_content and (text_matches_terms(subject, terms) or text_matches_terms(sender, terms)):
                        raw_matches.append({
                            "file_path": file_path, "file_name": file_name, "prefix": prefix,
                            "mtime": msg_ts, "line_number": 1, "paragraph_index": None,
                            "location_info": f"Intestazione Email{date_suffix}",
                            "snippet": f"Trovato nell'intestazione: {subject} da {sender}",
                        })
                        found_in_content = True

                elif ext in [".txt", ".log", ".csv", custom_ext]:
                    with open(file_path, "rb") as f:
                        raw_data = f.read()
                    if raw_data.startswith(b'\xff\xfe') or raw_data.startswith(b'\xfe\xff'):
                        text_data = raw_data.decode("utf-16", errors="ignore")
                    else:
                        try:
                            text_data = raw_data.decode("utf-8")
                        except UnicodeDecodeError:
                            text_data = raw_data.decode("latin1", errors="ignore")
                    text_data = text_data.replace('\x00', '')
                    lines = text_data.split('\n')
                    for idx, line in enumerate(lines):
                        if text_matches_terms(line, terms):
                            start_i, end_i = max(0, idx - 2), min(len(lines), idx + 3)
                            snippet = " ".join([l.strip() for l in lines[start_i:end_i]]).strip()
                            raw_matches.append({
                                "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                "mtime": mtime, "line_number": idx + 1, "paragraph_index": None,
                                "location_info": f"Riga {idx + 1}", "snippet": snippet,
                            })
                            found_in_content = True

                elif ext in [".docx", ".doc"]:
                    paragraphs = extract_paragraphs_from_docx(file_path)
                    for idx, p_text in enumerate(paragraphs):
                        if text_matches_terms(p_text, terms):
                            start_i, end_i = max(0, idx - 1), min(len(paragraphs), idx + 2)
                            snippet = " \n".join(paragraphs[start_i:end_i])
                            raw_matches.append({
                                "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                "mtime": mtime, "line_number": None, "paragraph_index": idx + 1,
                                "location_info": f"Paragrafo {idx + 1}", "snippet": snippet,
                            })
                            found_in_content = True
                    if not found_in_content and ext == ".doc":
                        with open(file_path, "rb") as f:
                            raw_data = normalize_search_text(f.read(4194304).decode("latin1", errors="ignore"))
                            if text_matches_terms(raw_data, terms):
                                raw_matches.append({
                                    "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                    "mtime": mtime, "line_number": None, "paragraph_index": 1,
                                    "location_info": "Documento Word",
                                    "snippet": f"Testo nel file Word: '{query}'.",
                                })
                                found_in_content = True

                elif ext == ".pdf":
                    pdf_lines = extract_lines_from_pdf(file_path)
                    for idx, line in enumerate(pdf_lines):
                        if text_matches_terms(line, terms):
                            start_i, end_i = max(0, idx - 1), min(len(pdf_lines), idx + 2)
                            snippet = " ".join(pdf_lines[start_i:end_i])
                            raw_matches.append({
                                "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                "mtime": mtime, "line_number": None, "paragraph_index": None,
                                "location_info": f"Sezione {idx + 1}", "snippet": snippet,
                            })
                            found_in_content = True

                if name_matched and not found_in_content:
                    raw_matches.append({
                        "file_path": file_path, "file_name": file_name, "prefix": prefix,
                        "mtime": mtime, "line_number": None, "paragraph_index": None,
                        "location_info": "Nome File",
                        "snippet": f"Corrispondenza: '{file_name}'",
                    })

            except Exception as e:
                logging.debug(f"Salto file bloccato o corrotto durante scansione ({file_path}): {e}")

            bump_progress()

        self.current_matches = raw_matches
        self.last_feed_raw_occurrences = feed_raw_total
        wx.CallAfter(self.finish_search, len(raw_matches))

    def on_filter_text(self, event):
        self.update_list_display()

    def sort_and_display_matches(self, sort_type="recent_first"):
        self.current_sort = sort_type
        if sort_type == "recent_first":
            self.current_matches.sort(key=lambda x: (x.get("mtime") or 0, x.get("line_number") or 0), reverse=True)
        elif sort_type == "oldest_first":
            self.current_matches.sort(key=lambda x: (x.get("mtime") or 0, x.get("line_number") or 0), reverse=False)
        elif sort_type == "name":
            self.current_matches.sort(key=lambda x: (x.get("file_name") or "").lower())

        self.update_list_display()

    def update_list_display(self):
        filter_text = self.txt_filter.GetValue().lower().strip()
        self.lst_results.Clear()
        self.file_map.clear()
        
        for item in self.current_matches:
            loc = f" ({item['location_info']})" if item.get("location_info") else ""
            display_str = f"{item['prefix']} {item['file_name']}{loc} -- ({item['file_path']})"
            
            if filter_text:
                searchable_content = f"{display_str} {item.get('snippet', '')}".lower()
                if filter_text not in searchable_content:
                    continue
                    
            idx = self.lst_results.Append(display_str)
            self.file_map[idx] = item

    def update_progress(self, percent, current, total, matches):
        self.gauge.SetValue(percent)
        text = f"Avanzamento: {percent}% ({current}/{total} elementi, {matches} risultati)"
        self.txt_status_progress.SetValue(text)
        speak_accessible(f"Ricerca al {percent} percento")

    def finish_search(self, matches):
        # --- INIZIO FEEDBACK ACUSTICO FINE ---
        def _play_end_sound():
            if self._stop_search:
                winsound.Beep(400, 300) 
            elif matches > 0:
                winsound.Beep(1000, 150)
                time.sleep(0.05)
                winsound.Beep(1500, 200)
            else:
                winsound.Beep(600, 300) 

        threading.Thread(target=_play_end_sound, daemon=True).start()
        # --- FINE FEEDBACK ACUSTICO ---

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
            speak_accessible(f"Ricerca annullata. Conservati {matches} risultati.{feed_speak}")
        else:
            text = (
                f"Ricerca completata: 100% ({self.scanned_count} elementi). "
                f"Trovati {matches} risultati.{feed_note}"
            )
            logging.info(
                f"Ricerca completata. Elementi esaminati: {self.scanned_count}. "
                f"Risultati: {matches}. Occorrenze grezze feed: {feed_raw}."
            )
            speak_accessible(f"Completata. Trovati {matches} risultati.{feed_speak}")
        self.txt_status_progress.SetValue(text)
        self.btn_search.Enable()
        self.btn_cancel.Disable()
        
        self.sort_and_display_matches(sort_type=self.current_sort)
        
        if self.lst_results.GetCount() > 0:
            self.lst_results.SetSelection(0)
            self.lst_results.SetFocus()

    def on_open_file_event(self, event):
        self.open_selected_file()

    def open_selected_file(self):
        sel = self.lst_results.GetSelection()
        if sel != wx.NOT_FOUND and sel in self.file_map:
            item = self.file_map[sel]
            file_to_open = item["file_path"]
            line_num = item.get("line_number")
            ext = os.path.splitext(file_to_open)[1].lower()

            if item.get("prefix") == "[FEED-RIGA]":
                if line_num:
                    speak_accessible(f"Apertura alla riga {line_num} nel file feed")
                    jump_to_line_in_editor(file_to_open, line_num)
                else:
                    speak_accessible("Riga non disponibile.")
                return

            if item.get("prefix") in ("[RSS]", "[FEED]"):
                url = item.get("article_url") or file_to_open
                if url and (str(url).startswith("http://") or str(url).startswith("https://")):
                    speak_accessible(
                        "Apertura articolo nel browser. "
                        "Se compare un banner sui cookie, accettarlo per leggere la notizia."
                    )
                    webbrowser.open(url)
                    return
                if item.get("prefix") == "[FEED]":
                    # fallback: editor or mbox viewer
                    if line_num is not None and isinstance(line_num, int) and line_num >= 0:
                        try:
                            viewer = MboxViewerFrame(
                                self,
                                file_to_open,
                                line_num,
                                self.current_query,
                                cached_text=item.get("viewer_text"),
                            )
                            viewer.Show()
                            speak_accessible("Apertura articolo feed nel lettore interno")
                            return
                        except Exception:
                            pass
                    if line_num:
                        speak_accessible(f"Apertura alla riga {line_num}: {os.path.basename(file_to_open)}")
                        jump_to_line_in_editor(file_to_open, line_num)
                        return
                speak_accessible("Collegamento articolo non disponibile.")
                return

            if item.get("prefix") == "[MBOX]":
                speak_accessible(f"Apertura messaggio {line_num + 1} dall'archivio MBOX")
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
                para_idx = item.get("paragraph_index")
                snippet_to_find = item.get("snippet", "")
                speak_accessible(f"Apertura Word su {item.get('location_info', 'documento')}")
                open_word_at_paragraph(file_to_open, para_idx, snippet_to_find)
                return
            if ext == ".eml":
                speak_accessible(f"Apertura email nel lettore interno: {os.path.basename(file_to_open)}")
                viewer = EmlViewerFrame(self, file_to_open, self.current_query)
                viewer.Show()
                return

            if line_num:
                speak_accessible(f"Apertura alla riga {line_num}: {os.path.basename(file_to_open)}")
                jump_to_line_in_editor(file_to_open, line_num)
            else:
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "open", file_to_open, None, None, 1)
                    speak_accessible(f"Apertura file: {os.path.basename(file_to_open)}")
                except Exception as e:
                    logging.error(f"Errore ShellExecute su {file_to_open}: {e}")
                    speak_accessible("Errore apertura.")

    def on_context_menu(self, event):
        sel = self.lst_results.GetSelection()
        if sel == wx.NOT_FOUND or sel not in self.file_map: return
        item_data = self.file_map[sel]
        file_path = item_data["file_path"]
        snippet = item_data["snippet"]

        menu = wx.Menu()
        item_open = menu.Append(wx.ID_ANY, "Apri File (alla riga esatta) / Browser\tRETURN")
        item_preview = menu.Append(wx.ID_ANY, "Ascolta Anteprima Vocale\tSPACE")
        item_copy_snippet = menu.Append(wx.ID_ANY, "Copia Blocco Notizia")
        item_copy_path = menu.Append(wx.ID_ANY, "Copia Percorso Completo")
        item_copy_text = menu.Append(wx.ID_ANY, "Copia Contenuto (o Immagine)")
        item_copy_to = menu.Append(wx.ID_ANY, "Copia File altrove...")
        item_open_folder = menu.Append(wx.ID_ANY, "Apri Cartella")

        menu.AppendSeparator()
        sort_submenu = wx.Menu()
        item_sort_recent = sort_submenu.Append(wx.ID_ANY, "Dal Più Recente")
        item_sort_oldest = sort_submenu.Append(wx.ID_ANY, "Dal Meno Recente")
        item_sort_name = sort_submenu.Append(wx.ID_ANY, "Alfabeticamente (A-Z)")
        menu.AppendSubMenu(sort_submenu, "Ordinamento")

        self.Bind(wx.EVT_MENU, lambda e: self.open_selected_file(), item_open)
        self.Bind(wx.EVT_MENU, lambda e: wx.CallLater(250, self.speak_selected_preview), item_preview)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_snippet_to_clipboard(snippet), item_copy_snippet)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_path_to_clipboard(file_path), item_copy_path)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_content_or_image_to_clipboard(item_data), item_copy_text)
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
        if sort_type == "recent_first": speak_accessible("Ordinati dal più recente.")
        elif sort_type == "oldest_first": speak_accessible("Ordinati dal meno recente.")
        elif sort_type == "name": speak_accessible("Ordinati alfabeticamente.")

    def copy_snippet_to_clipboard(self, snippet):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(snippet))
            wx.TheClipboard.Close()
            speak_accessible("Estratto copiato negli appunti!")

    def copy_path_to_clipboard(self, file_path):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(file_path))
            wx.TheClipboard.Close()
            speak_accessible("Percorso copiato!")

    def copy_content_or_image_to_clipboard(self, item_data):
        file_path = item_data["file_path"]
        ext = os.path.splitext(file_path)[1].lower()
        prefix = item_data.get("prefix", "")
        msg_index = item_data.get("line_number")

        if ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            try:
                img = wx.Image(file_path, wx.BITMAP_TYPE_ANY)
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.BitmapDataObject(wx.Bitmap(img)))
                    wx.TheClipboard.Close()
                    speak_accessible("Immagine copiata negli appunti!")
                    return
            except Exception as e:
                logging.warning(f"Errore copia immagine negli appunti: {e}")

        text_content = ""
        if prefix in ("[RSS]", "[FEED]"):
            url = item_data.get("article_url") or file_path
            text_content = (
                f"{item_data.get('file_name', '')}\n"
                f"{item_data.get('snippet', '')}\n"
                f"Link: {url}"
            )
        elif prefix == "[MBOX]":
            try:
                cached = item_data.get("viewer_text")
                if cached:
                    text_content = cached.replace("\r\n", "\n")
                else:
                    msg = load_mbox_message_by_index(file_path, msg_index)
                    text_content = _format_email_viewer_text(msg).replace("\r\n", "\n")
            except Exception as e:
                logging.warning(f"Errore copia mbox: {e}")
        elif ext == ".eml":
            try:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        msg = email.message_from_file(f, policy=policy.default)
                except Exception:
                    with open(file_path, "r", encoding="latin1", errors="ignore") as f:
                        msg = email.message_from_file(f, policy=policy.default)
                subject = decode_email_header(msg.get("subject", "(Nessun oggetto)"))
                sender = decode_email_header(msg.get("from", "(Sconosciuto)"))
                date = msg.get("date", "(Nessuna data)")
                body = get_clean_email_text(msg)
                text_content = f"Oggetto: {subject}\nDa: {sender}\nData: {date}\n{'-'*60}\n\n{body}"
            except Exception as e:
                logging.warning(f"Errore copia eml: {e}")
        elif ext in [".docx", ".doc"]: 
            text_content = "\n".join(extract_paragraphs_from_docx(file_path))
        elif ext == ".pdf": 
            text_content = "\n".join(extract_lines_from_pdf(file_path))
        elif ext in [".txt", ".log", ".csv"]:
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
            except Exception as e:
                logging.warning(f"Errore copia testo negli appunti: {e}")

        if text_content:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text_content))
                wx.TheClipboard.Close()
                speak_accessible("Testo copiato negli appunti!")
        else: 
            speak_accessible("Impossibile copiare il contenuto.")

    def copy_file_to_destination(self, file_path):
        dlg = wx.DirDialog(self, "Seleziona cartella", defaultPath=os.path.expanduser("~\\Desktop"))
        if dlg.ShowModal() == wx.ID_OK:
            dest_dir = dlg.GetPath()
            try:
                shutil.copy(file_path, dest_dir)
                speak_accessible(f"File copiato in {dest_dir}!")
            except Exception as e:
                logging.error(f"Errore copia file in {dest_dir}: {e}")
                speak_accessible("Errore copia.")
        dlg.Destroy()

    def open_containing_folder(self, file_path):
        try:
            subprocess.Popen(f'explorer /select,"{file_path}"')
            speak_accessible("Apertura cartella con file selezionato...")
        except Exception as e:
            logging.error(f"Impossibile aprire la cartella: {e}")
            speak_accessible("Impossibile aprire la cartella.")

def main():
    app = wx.App(False)
    frame = MainWindow()
    frame.Show()
    frame.Raise()
    frame.txt_query.SetFocus()
    wx.CallLater(1200, frame.on_check_updates, None, True)
    if len(sys.argv) > 1:
        initial_arg = sys.argv[1]
        if os.path.exists(initial_arg):
            frame.txt_path.SetValue(initial_arg)
            save_last_path(initial_arg)
    app.MainLoop()

if __name__ == "__main__":
    main()