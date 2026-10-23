_speech_active = True
import ctypes
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
import zipfile
import quopri
import zlib
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
    import rtad_zip
except ImportError:
    rtad_zip = None

try:
    import rtad_copie
except ImportError:
    rtad_copie = None

try:
    import rtad_chat
except ImportError:
    rtad_chat = None

try:
    import rtad_attach_dialog
except ImportError:
    rtad_attach_dialog = None

APP_TITLE = "Ricerca Testuale Accesso Digitale"
APP_VERSION = "1.8.3"
DONATION_URL = "https://paypal.me/AccessoDigitale"
YOUTUBE_URL = "https://www.youtube.com/@AccessoDigitale"
GITHUB_REPO_URL = "https://github.com/barramaurizio/ricerca_testuale_accesso_digitale/releases"
GITHUB_API_LATEST = "https://api.github.com/repos/barramaurizio/ricerca_testuale_accesso_digitale/releases/latest"
GITHUB_API_RELEASES = (
    "https://api.github.com/repos/barramaurizio/"
    "ricerca_testuale_accesso_digitale/releases?per_page=30"
)
EMAIL_DESTINATARIO = "mauritechstudio@gmail.com"

CONFIG_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "RTAD_Standalone")
if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
LOG_FILE = os.path.join(CONFIG_DIR, "rtad_debug.log")
OCR_CACHE_DIR = os.path.join(CONFIG_DIR, "ocr_cache")
MEDIA_CACHE_DIR = os.path.join(CONFIG_DIR, "media_cache")
# Aggiornamenti SA: Local (binari), non Download utente (1.7.6)
_LOCAL_APPDATA = os.environ.get("LOCALAPPDATA") or os.path.join(
    os.path.expanduser("~"), "AppData", "Local"
)
UPDATES_DIR = os.path.join(_LOCAL_APPDATA, "RTAD_Standalone", "updates")
INSTALL_CHANNEL_MARKER = "rtad_install_channel.txt"

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

def normalize_search_targets(target_input):
    """Spezza percorsi multipli e toglie virgolette / spazi (incolla da Esplora risorse).

    Accetta cartelle, unità (es. I:\\) e singoli file su qualsiasi unità.
    """
    out = []
    for t in re.split(r"[;,]", target_input or ""):
        t = (t or "").strip()
        # Virgolette tipografiche / zero-width / NBSP da copia-incolla chat o Word
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
        # file:///I:/cartella/file.pdf → I:\cartella\file.pdf
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
                # Su Windows preserva le unità tipo I:\ anche se non ancora montate
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
    """Path da Appunti Windows: file copiati (CF_HDROP) oppure testo percorso.

    Restituisce lista di path esistenti (file o cartella). Vuota se niente di utile.
    """
    found = []
    if not wx.TheClipboard.Open():
        return found
    try:
        # 1) File/cartelle copiati da Esplora (Ctrl+C sul file)
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
        # 2) Testo: un path o più separati da ; o ,
        try:
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT)):
                data = wx.TextDataObject()
                if wx.TheClipboard.GetData(data):
                    raw = (data.GetText() or "").strip()
                    if raw:
                        # Una sola riga tipica da «Copia come percorso»
                        if "\n" in raw and ";" not in raw and "," not in raw:
                            raw = raw.splitlines()[0].strip()
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
    # Dedup preservando ordine
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
_speech_queue = None
_speech_thread_started = False
_speech_thread_lock = threading.Lock()
_nvda_client = None

# Impostazioni voce Standalone (SAPI). Rate/Pitch tipici SAPI: -10 … +10.
SAPI_RATE_MIN, SAPI_RATE_MAX = -10, 10
SAPI_PITCH_MIN, SAPI_PITCH_MAX = -10, 10
_speech_rate = 0
_speech_pitch = 0
_speech_voice_id = ""  # token Id SAPI; vuoto = voce predefinita
# True = annunci RTAD via SAPI (velocità/voce regolabili); False = NVDA se presente, poi SAPI
_speech_use_sapi = True
_speech_settings_loaded = False

# Evita di leggere in RAM file enormi (blocco UI / «Non risponde» su dischi esterni).
# Non si applica alle caselle di posta: quelle si scansionano in streaming (vedi sotto).
MAX_CONTENT_SCAN_BYTES = 40 * 1024 * 1024  # 40 MB — DOC/testo generico
MAX_PDF_SCAN_BYTES = 80 * 1024 * 1024  # 80 MB — PDF (spesso brochure/ricette)
# Caselle Thunderbird / MBOX: nessun tetto di dimensione file.
# La scansione è in streaming (un messaggio alla volta): un INBOX da 5–10 GB
# resta ricercabile. Un tetto (es. 2 GB) saltava in silenzio le caselle Gmail
# principali (INBOX / Tutti i messaggi) con tutte le ricette recenti.
MAX_MAILBOX_SCAN_BYTES = 0  # 0 = illimitato per i contenitori posta
# 0 = nessun tetto sul singolo messaggio (legge tutto; un messaggio alla volta in streaming).
# Prima 12 MB poi 80 MB: i PDF ricette in base64 venivano tagliati/saltati.
MAX_SINGLE_MBOX_MSG_BYTES = 0
# Budget soft per singolo file: non riduce le ricerche normali, evita blocchi
FILE_CONTENT_SOFT_TIMEOUT_SEC = 12
FILE_CONTENT_SOFT_TIMEOUT_PDF_SEC = 20  # PDF lineari: un po' più di tempo senza bloccare l'UI
# Cap lettura .eml in ricerca (allegati grandi restano esclusi da get_clean_email_text)
MAX_EML_READ_BYTES = 12 * 1024 * 1024
# Cap dimensione word/document.xml decompressa
MAX_DOCX_XML_BYTES = 25 * 1024 * 1024
_OLE_MAGIC = b"\xD0\xCF\x11\xE0"
_ZIP_LOCAL_MAGIC = b"PK\x03\x04"
_ZIP_EMPTY_MAGIC = b"PK\x05\x06"


def _get_nvda_client():
    global _nvda_client
    if _nvda_client is False:
        return None
    if _nvda_client is not None:
        return _nvda_client
    for dll_name in ("nvdaControllerClient64.dll", "nvdaControllerClient32.dll", "nvdaControllerClient.dll"):
        try:
            client = ctypes.windll.LoadLibrary(dll_name)
            if client.nvdaController_testIfRunning() == 0:
                client.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                client.nvdaController_speakText.restype = ctypes.c_long
                _nvda_client = client
                return client
        except Exception:
            pass
    _nvda_client = False
    return None


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


def load_speech_settings():
    """Carica velocità/tono/voce/motore da settings.json (una volta + su richiesta)."""
    global _speech_rate, _speech_pitch, _speech_voice_id, _speech_use_sapi
    global _speech_active, _speech_settings_loaded
    data = _load_settings_dict()
    try:
        rate = int(data.get("speech_rate", 0))
    except Exception:
        rate = 0
    try:
        pitch = int(data.get("speech_pitch", 0))
    except Exception:
        pitch = 0
    _speech_rate = max(SAPI_RATE_MIN, min(SAPI_RATE_MAX, rate))
    _speech_pitch = max(SAPI_PITCH_MIN, min(SAPI_PITCH_MAX, pitch))
    _speech_voice_id = str(data.get("speech_voice_id", "") or "")
    if "speech_use_sapi" in data:
        _speech_use_sapi = bool(data.get("speech_use_sapi"))
    else:
        _speech_use_sapi = True
    if "speech_active" in data:
        _speech_active = bool(data.get("speech_active"))
    _speech_settings_loaded = True
    apply_sapi_voice_settings(get_sapi_voice())


def save_speech_settings():
    data = _load_settings_dict()
    data["speech_rate"] = int(_speech_rate)
    data["speech_pitch"] = int(_speech_pitch)
    data["speech_voice_id"] = str(_speech_voice_id or "")
    data["speech_use_sapi"] = bool(_speech_use_sapi)
    data["speech_active"] = bool(_speech_active)
    _save_settings_dict(data)


def list_sapi_voices():
    """Elenco voci SAPI: [{id, name}, …]."""
    v = get_sapi_voice()
    if not v:
        return []
    out = []
    try:
        tokens = v.GetVoices()
        for i in range(int(tokens.Count)):
            tok = tokens.Item(i)
            try:
                out.append({"id": str(tok.Id), "name": str(tok.GetDescription())})
            except Exception:
                continue
    except Exception as e:
        logging.debug(f"Elenco voci SAPI fallito: {e}")
    return out


def _clear_invalid_sapi_voice_id(reason):
    """Id voce salvato non più utilizzabile: torna alla voce predefinita e persiste."""
    global _speech_voice_id
    if not _speech_voice_id:
        return
    logging.info(
        f"Voce SAPI salvata non valida ({reason}); ripristino voce predefinita."
    )
    _speech_voice_id = ""
    try:
        save_speech_settings()
    except Exception:
        pass


def apply_sapi_voice_settings(voice=None):
    """Applica rate e token voce all'oggetto SpVoice (pitch via markup in Speak)."""
    v = voice if voice is not None else get_sapi_voice()
    if not v:
        return False
    try:
        v.Rate = int(_speech_rate)
    except Exception:
        pass
    if _speech_voice_id:
        matched = False
        try:
            tokens = v.GetVoices()
            wanted = str(_speech_voice_id)
            for i in range(int(tokens.Count)):
                tok = tokens.Item(i)
                if str(tok.Id) == wanted:
                    v.Voice = tok
                    matched = True
                    break
            if not matched:
                _clear_invalid_sapi_voice_id("token assente dall'elenco SAPI")
        except Exception as e:
            logging.debug(f"Impostazione voce SAPI fallita: {e}")
            _clear_invalid_sapi_voice_id(str(e))
    return True


def _sapi_speak_text(text):
    """Parla con SAPI applicando rate/voce/pitch."""
    v = get_sapi_voice()
    if not v:
        return False
    apply_sapi_voice_settings(v)
    payload = str(text)
    pitch = int(_speech_pitch)
    if pitch != 0:
        # Markup SAPI: pitch absmiddle -10…+10
        safe = (
            payload.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        payload = f'<pitch absmiddle="{pitch}">{safe}</pitch>'
    try:
        flags = 3  # SVSFlagsAsync | SVSFPurgeBeforeSpeak
        if pitch != 0:
            flags = 1 | 2 | 8  # + SVSFIsXML
        v.Speak(payload, flags)
        return True
    except Exception:
        try:
            v.Speak(str(text), 3)
            return True
        except Exception:
            return False


def _speech_loop():
    """Un solo worker: evita Speak/NVDA concorrenti che bloccano la UI."""
    import queue as _q
    global _speech_queue
    while True:
        try:
            item = _speech_queue.get()
        except Exception:
            continue
        if item is None:
            continue
        kind, payload = item
        try:
            if kind == "stop":
                client = _get_nvda_client()
                if client is not None:
                    try:
                        client.nvdaController_cancelSpeech()
                    except Exception:
                        pass
                v = get_sapi_voice()
                if v:
                    try:
                        v.Speak("", 2)
                    except Exception:
                        pass
            elif kind == "speak":
                text = payload
                spoken = False
                prefer_sapi = bool(_speech_use_sapi)
                if prefer_sapi:
                    spoken = _sapi_speak_text(text)
                if not spoken:
                    client = _get_nvda_client()
                    if client is not None:
                        try:
                            client.nvdaController_cancelSpeech()
                            if client.nvdaController_speakText(str(text)) == 0:
                                spoken = True
                        except Exception:
                            pass
                if not spoken and not prefer_sapi:
                    spoken = _sapi_speak_text(text)
        except Exception:
            pass
        finally:
            try:
                _speech_queue.task_done()
            except Exception:
                pass


def _ensure_speech_thread():
    global _speech_queue, _speech_thread_started
    with _speech_thread_lock:
        if _speech_thread_started:
            return
        import queue as _q
        _speech_queue = _q.Queue(maxsize=32)
        t = threading.Thread(target=_speech_loop, daemon=True, name="rtad-speech")
        t.start()
        _speech_thread_started = True


def stop_accessible_speech():
    try:
        _ensure_speech_thread()
        # svuota coda e richiedi stop
        try:
            while True:
                _speech_queue.get_nowait()
                _speech_queue.task_done()
        except Exception:
            pass
        try:
            _speech_queue.put_nowait(("stop", None))
        except Exception:
            pass
    except Exception:
        pass


def speak_accessible(text, force=False):
    global _speech_active
    if not _speech_settings_loaded:
        try:
            load_speech_settings()
        except Exception:
            pass
    if not _speech_active and not force:
        return
    if not text:
        return
    try:
        _ensure_speech_thread()
        # Se la coda è piena, scarta i vecchi annunci automatici (tieni l'ultimo)
        try:
            _speech_queue.put_nowait(("speak", str(text)))
        except Exception:
            try:
                while not _speech_queue.empty():
                    try:
                        _speech_queue.get_nowait()
                        _speech_queue.task_done()
                    except Exception:
                        break
                _speech_queue.put_nowait(("speak", str(text)))
            except Exception:
                pass
    except Exception:
        pass


def set_speech_rate(delta=0, absolute=None):
    """Regola velocità SAPI; restituisce il nuovo valore."""
    global _speech_rate
    if absolute is not None:
        _speech_rate = int(absolute)
    else:
        _speech_rate = int(_speech_rate) + int(delta)
    _speech_rate = max(SAPI_RATE_MIN, min(SAPI_RATE_MAX, _speech_rate))
    apply_sapi_voice_settings()
    save_speech_settings()
    return _speech_rate


def set_speech_pitch(delta=0, absolute=None):
    global _speech_pitch
    if absolute is not None:
        _speech_pitch = int(absolute)
    else:
        _speech_pitch = int(_speech_pitch) + int(delta)
    _speech_pitch = max(SAPI_PITCH_MIN, min(SAPI_PITCH_MAX, _speech_pitch))
    save_speech_settings()
    return _speech_pitch


def set_speech_voice_id(voice_id):
    global _speech_voice_id
    _speech_voice_id = str(voice_id or "")
    apply_sapi_voice_settings()
    save_speech_settings()


def set_speech_use_sapi(enabled):
    global _speech_use_sapi
    _speech_use_sapi = bool(enabled)
    save_speech_settings()


def speech_rate_label(rate=None):
    r = _speech_rate if rate is None else rate
    if r == 0:
        return "normale"
    if r > 0:
        return f"più veloce ({r})"
    return f"più lenta ({r})"


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

    Le caselle di posta non hanno tetto: la scansione è in streaming
    (un messaggio alla volta), così Inbox/Sent/Tutti i messaggi da vari GB
    restano ricercabili. Un tetto fisso (es. 2 GB) escludeva in silenzio
    le caselle Gmail più grandi — proprio dove stanno le ricette recenti.

    I PDF hanno un tetto dedicato (più alto del generico) perché molte ricette
    e brochure superano i 40 MB pur restando gestibili in estrazione lineare.

    Se la dimensione non è leggibile (sz < 0: OneDrive non idratato, path lungo,
    file bloccato), si tenta comunque la lettura: meglio un open che fallisce
    in modo controllato che saltare silenziosamente contenuto utile.
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
    """Esegue fn in un thread daemon; se supera timeout restituisce default.

    Non uccide il lavoro in corso (Python non può interrompere I/O/GIL nativo),
    ma permette alla ricerca di proseguire sul file successivo. I tetti su
    inflate/XML evitano che il thread orfano resti bloccato a lungo.
    """
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
# Allegati PDF nelle email (ricette ecc.): cerca testo/nome senza caricare PDF enormi
MAX_EMAIL_PDF_ATTACH_BYTES = 20 * 1024 * 1024


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


def iter_pdf_attachments(msg, max_bytes=MAX_EMAIL_PDF_ATTACH_BYTES):
    """Yield (filename, pdf_bytes, meta) dagli allegati PDF di un messaggio email.

    meta flags:
      - empty: True se l'allegato è dichiarato ma senza corpo (tipico IMAP non scaricato)
      - external: path locale se X-Mozilla-External-Attachment-URL punta a un file

    Riconosce anche application/octet-stream / senza nome se il payload inizia con %PDF.
    """
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

        # Thunderbird a volte stacca l'allegato su disco
        external_path = ""
        try:
            ext_url = part.get("X-Mozilla-External-Attachment-URL") or ""
            ext_url = str(ext_url).strip()
            if ext_url.lower().startswith("file:"):
                # file:///C:/path or file://localhost/C:/path
                from urllib.parse import unquote, urlparse
                parsed = urlparse(ext_url)
                external_path = unquote(parsed.path or "")
                if external_path.startswith("/") and len(external_path) > 2 and external_path[2] == ":":
                    # /C:/Users/... → C:/Users/...
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
            # Fallback: payload grezzo base64/qp non decodificato dal parser
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
                        import quopri
                        payload = quopri.decodestring(raw_pl.encode("latin1", errors="ignore"))
                    else:
                        payload = raw_pl.encode("latin1", errors="ignore")
            except Exception:
                payload = None

        if external_path and (not payload or len(payload) < 8):
            try:
                if os.path.isfile(external_path):
                    with open(external_path, "rb") as ef:
                        payload = ef.read(max_bytes if max_bytes else MAX_EMAIL_PDF_ATTACH_BYTES)
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
            # Dichiarato PDF ma corpo assente: messaggio IMAP non scaricato offline
            yield (fname or "allegato.pdf"), b"", {"empty": True, "external": external_path or ""}
            continue
        if len(payload) > max_bytes:
            payload = payload[:max_bytes]
        yield (fname or "allegato.pdf"), payload, {"empty": False, "external": ""}


def iter_pdf_attachments_compat(msg, max_bytes=MAX_EMAIL_PDF_ATTACH_BYTES):
    """Compat: yield (filename, pdf_bytes) saltando gli stub vuoti."""
    for fname, payload, meta in iter_pdf_attachments(msg, max_bytes=max_bytes):
        if meta.get("empty"):
            continue
        if not payload:
            continue
        yield fname, payload


def match_pdf_attachment_hit(terms, att_name, pdf_raw, deadline=None):
    """Restituisce (snippet, via) se l'allegato PDF corrisponde ai termini, altrimenti None.

    Ordine: nome allegato → ricerca grezza veloce nei byte → estrazione testo PDF.
    La ricerca grezza trova «prescrizione»/«cardura» anche quando l'estrattore Tj/TJ fallisce.
    """
    if text_matches_terms(att_name, terms):
        return f"Allegato: {att_name}", "nome allegato"
    # Grezza veloce (latin1) su tutto il PDF: copre molti PDF «difficili» e gli OCR embedded
    try:
        raw_txt = pdf_raw.decode("latin1", errors="ignore")
        if text_matches_terms(raw_txt, terms):
            # prova a estrarre uno snippet leggibile intorno al primo termine
            n = normalize_search_text(raw_txt, False)
            pos = -1
            term0 = terms[0] if terms else ""
            if term0:
                pos = n.find(term0)
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
    # Cache/log di Cursor/VS Code e indici IndexedDB
    if "\\appdata\\roaming\\cursor\\" in low:
        return True
    if "\\appdata\\roaming\\code\\" in low:
        return True
    if "indexeddb" in low and name.endswith(".log"):
        return True
    # Componenti Windows: migliaia di license.rtf irrilevanti
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
                    end_pos = line_start
                    msg = _emit(current, start_pos, end_pos)
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
    """Yield (index, email.message) from mailbox — streaming su From_ (anche file enormi).

    prefer_from_split è mantenuto per compatibilità API (Feed Thunderbird).
    should_abort: callable → True per interrompere la scansione.
    """
    yielded = False
    try:
        for item in _iter_mbox_from_lines_streaming(file_path, should_abort=should_abort):
            yielded = True
            yield item
    except Exception as e:
        logging.debug(f"Streaming From_ fallito su {file_path}: {e}")
    if yielded:
        return

    # Fallback: mailbox.mbox solo se lo streaming non ha trovato messaggi (file piccoli/atipici)
    sz = safe_file_size(file_path)
    if sz > MAX_CONTENT_SCAN_BYTES:
        return
    mb = None
    try:
        mb = mailbox.mbox(file_path)
        count = 0
        for msg in mb:
            if should_abort and should_abort():
                break
            yield count, msg
            count += 1
    except Exception as e:
        logging.debug(f"mailbox.mbox fallito su {file_path}: {e}")
    finally:
        try:
            if mb:
                mb.close()
        except Exception:
            pass


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
    """Scrive la guida HTML completa (indice + Vision/Gemini) e ne restituisce il path."""
    help_path = os.path.join(CONFIG_DIR, "guida_ricerca_testuale.html")
    try:
        if rtad_guida_html is not None:
            rtad_guida_html.write_guida_html(
                help_path,
                app_title=APP_TITLE,
                app_version=APP_VERSION,
                donation_url=DONATION_URL,
                github_url="https://github.com/barramaurizio/ricerca_testuale_accesso_digitale",
            )
            return help_path
    except Exception as e:
        logging.error(f"Scrittura guida HTML completa fallita: {e}")
    # Fallback minimo se il modulo manca
    html_content = (
        f"<!DOCTYPE html><html lang='it'><head><meta charset='UTF-8'>"
        f"<title>{APP_TITLE}</title></head><body>"
        f"<h1>{APP_TITLE} v{APP_VERSION}</h1>"
        f"<p>Guida completa non disponibile in questa build. "
        f"Usa Aiuto → Guida pratica oppure Guida ai Comandi.</p>"
        f"<p><a href='{DONATION_URL}'>{DONATION_URL}</a></p>"
        f"</body></html>"
    )
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


def _parse_version_tuple(version_str):
    """Converte '1.7.4' in tupla di int, o None se non valida."""
    try:
        parts = [int(x) for x in str(version_str).strip().split(".")]
        if not parts:
            return None
        return tuple(parts)
    except Exception:
        return None


def wrap_report_text(s, width=72):
    """Righe standard per report/descrizioni (UI, copia, salva).

    Spezza a spazio senza rompere URL/path lunghi in modo aggressivo.
    Non cambia il contenuto semantico: solo presentazione a riga.
    """
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
        # Path/URL senza spazi: non spezzare a metà carattere
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


def get_sa_updates_dir():
    """Cartella download aggiornamenti SA (%LocalAppData%\\RTAD_Standalone\\updates)."""
    try:
        os.makedirs(UPDATES_DIR, exist_ok=True)
    except Exception as e:
        logging.debug(f"get_sa_updates_dir: {e}")
    return UPDATES_DIR


def cleanup_sa_update_downloads(keep_path=None):
    """Rimuove Setup/Portable vecchi dalla cartella updates (gestita dal programma)."""
    updates = get_sa_updates_dir()
    keep = None
    if keep_path:
        try:
            keep = os.path.normcase(os.path.normpath(keep_path))
        except Exception:
            keep = None
    markers = (
        "setup_ricercatestualeaccessodigitale",
        "ricercatestualeaccessodigitale_portable",
    )
    try:
        for name in os.listdir(updates):
            if not name.lower().endswith(".exe"):
                continue
            low = name.lower()
            if not any(m in low for m in markers):
                continue
            full = os.path.join(updates, name)
            try:
                if keep and os.path.normcase(os.path.normpath(full)) == keep:
                    continue
            except Exception:
                pass
            try:
                os.remove(full)
                logging.info(f"Cleanup aggiornamento SA: rimosso {full}")
            except OSError as e:
                logging.debug(f"Cleanup aggiornamento SA non riuscito ({full}): {e}")
    except OSError as e:
        logging.debug(f"cleanup_sa_update_downloads: {e}")


def detect_sa_install_channel():
    """Canale Standalone: 'installer' oppure 'portable'.

    Heuristics:
    - Marker file rtad_install_channel.txt (Inno) → installer
    - Marker Inno (unins000.exe) o percorso sotto Program Files → installer
    - Altrimenti portable (anche da sorgente Python)
    - Se il percorso attuale contraddice chiaramente il canale salvato, si aggiorna
      (es. da Portable a Setup in Program Files).
    """
    data = _load_settings_dict()
    saved = str(data.get("install_channel", "")).strip().lower()

    channel = "portable"
    strong_installer = False
    try:
        if getattr(sys, "frozen", False):
            exe_path = os.path.abspath(sys.executable)
        else:
            exe_path = os.path.abspath(__file__)
        exe_dir = os.path.dirname(exe_path)
        low = exe_dir.lower()
        # Marker Inno solo su build frozen (il file esiste anche nel tree sorgente)
        if getattr(sys, "frozen", False):
            marker = os.path.join(exe_dir, INSTALL_CHANNEL_MARKER)
            if os.path.isfile(marker):
                try:
                    with open(marker, "r", encoding="utf-8", errors="ignore") as f:
                        marker_raw = (f.read() or "").strip().lower()
                    if "installer" in marker_raw or marker_raw == "installer":
                        strong_installer = True
                        channel = "installer"
                except Exception as e:
                    logging.debug(f"Lettura marker canale: {e}")
        has_uninstaller = os.path.isfile(os.path.join(exe_dir, "unins000.exe"))
        in_program_files = (
            "\\program files\\" in low
            or "\\program files (x86)\\" in low
            or low.startswith("c:\\program files")
            or low.startswith("c:\\program files (x86)")
        )
        if has_uninstaller or in_program_files:
            strong_installer = True
            channel = "installer"
        elif strong_installer:
            channel = "installer"
    except Exception as e:
        logging.debug(f"detect_sa_install_channel: {e}")

    if saved in ("installer", "portable"):
        # Non restare «portable» se ora si gira chiaramente dall'installer
        if saved == "portable" and strong_installer:
            channel = "installer"
        elif saved == "installer" and not strong_installer and getattr(sys, "frozen", False):
            # Exe fuori da Program Files senza unins → probabilmente Portable
            channel = "portable"
        else:
            channel = saved

    if data.get("install_channel") != channel:
        try:
            data["install_channel"] = channel
            _save_settings_dict(data)
        except Exception:
            pass
    logging.info(f"Canale installazione SA rilevato: {channel}")
    return channel


def fetch_latest_standalone_release():
    """Trova la release GitHub più recente con tag app-v*.

    Restituisce dict con version, html_url, setup_*, portable_* oppure None.
    Non usa /releases/latest (spesso è l'Add-on v*).
    """
    req = urllib.request.Request(
        GITHUB_API_RELEASES,
        headers={"User-Agent": "RTAD-Updater"},
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        releases = json.loads(response.read().decode("utf-8"))
    if not isinstance(releases, list):
        return None

    best = None
    best_ver = None
    for rel in releases:
        if not isinstance(rel, dict):
            continue
        if rel.get("draft") or rel.get("prerelease"):
            continue
        tag = str(rel.get("tag_name", "")).strip()
        if not tag.startswith("app-v"):
            continue
        ver_s = tag[len("app-v") :].strip()
        ver_t = _parse_version_tuple(ver_s)
        if ver_t is None:
            continue
        if best_ver is not None and ver_t <= best_ver:
            continue
        setup_url = setup_name = None
        portable_url = portable_name = None
        for asset in rel.get("assets") or []:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", ""))
            url = asset.get("browser_download_url")
            if not name or not url:
                continue
            low = name.lower()
            if low.startswith("setup_ricerca") and low.endswith(".exe"):
                setup_url, setup_name = url, name
            elif "portable" in low and low.endswith(".exe"):
                portable_url, portable_name = url, name
        best_ver = ver_t
        best = {
            "version": ver_s,
            "version_tuple": ver_t,
            "tag": tag,
            "html_url": rel.get("html_url") or GITHUB_REPO_URL,
            "setup_url": setup_url,
            "setup_name": setup_name,
            "portable_url": portable_url,
            "portable_name": portable_name,
        }
    return best


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
# File per cui Explorer apre RTAD sul FILE stesso (non solo la cartella)
# e che hanno (o avranno) sottomenù shell documento.
SHELL_DOCUMENT_EXTS = (
    ".pdf",
    ".docx", ".odt", ".xlsx",
    ".txt", ".md", ".csv", ".log", ".rtf",
    ".html", ".htm",
    ".epub",
)

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
                    # 2=REMOVABLE, 3=FIXED, 5=CDROM
                    if drive_type in (2, 3, 5):
                        os.listdir(drive_path)
                        drives.append(drive_path)
                except Exception:
                    pass
        bitmask >>= 1
    return drives


def _path_looks_like_video_ts(path):
    """True se il percorso è (o contiene) una cartella VIDEO_TS da DVD video."""
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
    """Messaggio accessibile: .cda non è un file audio sul disco."""
    name = os.path.basename(path or "") or "traccia.cda"
    return (
        f"«{name}» non è un file audio sul disco: "
        "è un collegamento di Windows a una traccia del CD audio. "
        "RTAD non può riprodurre né trascrivere le tracce .cda. "
        "Se sul CD/DVD ci sono cartelle con mp3, pdf o foto, "
        "imposta quella cartella (o l’intera unità) e cerca lì."
    )

def extract_plain_text_file(file_path):
    """Legge un file di testo (txt/md/html/…) in Unicode."""
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
    except Exception as e:
        logging.debug(f"Errore lettura testo {file_path}: {e}")
        return ""
    if not raw_data:
        return ""
    try:
        if raw_data.startswith(b"\xff\xfe") or raw_data.startswith(b"\xfe\xff"):
            text = raw_data.decode("utf-16", errors="ignore")
        else:
            try:
                text = raw_data.decode("utf-8")
            except UnicodeDecodeError:
                text = raw_data.decode("latin1", errors="ignore")
        return text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    except Exception as e:
        logging.debug(f"Errore decode testo {file_path}: {e}")
        return ""


def extract_document_text(file_path):
    """Testo leggibile da PDF/DOCX/EPUB/testo per CLI shell e «Leggi/Copia».

    Restituisce stringa (può essere vuota se scansione/protetto/non supportato).
    """
    if not file_path or not os.path.isfile(file_path):
        return ""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            return "\n".join(extract_lines_from_pdf(file_path)).strip()
        if ext in (".docx", ".doc", ".odt"):
            # odt non è OOXML: extract_paragraphs_from_docx gestisce solo docx zip
            if ext == ".odt":
                return _extract_text_from_odt(file_path)
            return "\n".join(extract_paragraphs_from_docx(file_path)).strip()
        if ext == ".xlsx":
            return "\n".join(
                (row.get("text") or "") for row in extract_rows_from_xlsx(file_path)
            ).strip()
        if ext == ".epub":
            if rtad_epub is None:
                return ""
            return "\n".join(rtad_epub.extract_paragraphs_from_epub(file_path) or []).strip()
        if ext in TEXT_LIKE_EXTS:
            return extract_plain_text_file(file_path).strip()
    except Exception as e:
        logging.debug(f"extract_document_text fallita su {file_path}: {e}")
    return ""


def _extract_text_from_odt(file_path):
    """Estrae testo grezzo da ODT (content.xml in ZIP)."""
    try:
        magic = _read_file_magic(file_path, 4)
        if magic[:2] != b"PK":
            return ""
        with zipfile.ZipFile(file_path) as z:
            try:
                xml_content = z.read("content.xml")
            except KeyError:
                return ""
            if len(xml_content) > MAX_DOCX_XML_BYTES:
                xml_content = xml_content[:MAX_DOCX_XML_BYTES]
            tree = ET.fromstring(xml_content)
            parts = []
            for el in tree.iter():
                if el.tag.rsplit("}", 1)[-1] == "p":
                    t = "".join(el.itertext()).strip()
                    if t:
                        parts.append(t)
            return "\n".join(parts).strip()
    except Exception as e:
        logging.debug(f"Errore estrazione ODT {file_path}: {e}")
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
                logging.debug(
                    f"DOCX XML troppo grande ({info.file_size} byte), salto contenuto: {file_path}"
                )
                return []
            xml_content = z.read("word/document.xml")
            if len(xml_content) > MAX_DOCX_XML_BYTES:
                xml_content = xml_content[:MAX_DOCX_XML_BYTES]
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
    # Solo numeri «puri» (non misti a testo)
    if s.lower() in ("nan", "inf", "-inf"):
        return s
    try:
        # frazione di giorno → durata/orario
        if 0 < num < 1:
            total_sec = int(round(num * 86400))
            hh = total_sec // 3600
            mm = (total_sec % 3600) // 60
            ss = total_sec % 60
            if ss:
                return f"{hh:02d}:{mm:02d}:{ss:02d}"
            return f"{hh:02d}:{mm:02d}"
        # seriale data Excel (epoca 1899-12-30); tipico TV/PVR ~20000–80000
        if 20000 <= num < 100000:
            base = datetime.datetime(1899, 12, 30)
            dt = base + datetime.timedelta(days=num)
            if abs(num - int(num)) < 1e-9:
                return dt.strftime("%d/%m/%Y")
            return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return s
    # Interi / decimali «normali»: evita notazione scientifica inutilmente lunga
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
                # Fallback: sheet1… in ordine
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
                    logging.debug(
                        f"Foglio XLSX troppo grande ({info.file_size} byte), "
                        f"salto: {file_path} / {sheet_name}"
                    )
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
    except Exception as e:
        logging.debug(f"Errore estrazione XLSX {file_path}: {e}")
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


def _pdf_dict_has_flate(dict_blob: bytes) -> bool:
    return bool(dict_blob and _PDF_FILTER_FLATE.search(dict_blob))


def _pdf_dict_has_dct(dict_blob: bytes) -> bool:
    return bool(dict_blob and _PDF_FILTER_DCT.search(dict_blob))


def _pdf_dict_is_image(dict_blob: bytes) -> bool:
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
    """Estrae righe di testo da byte PDF (file o allegato email).

    Decomprime solo stream di contenuto (non Image XObject), poi legge Tj/TJ.
    I PDF solo-immagine restituiscono lista vuota.
    """
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
        if blob_parts and not blob_parts[-1].endswith("\n") and not p.startswith("\n"):
            blob_parts.append(" ")
        blob_parts.append(p)
    blob = "".join(blob_parts)
    blob = blob.replace("\r\n", "\n").replace("\r", "\n")
    # Prima spazi da controlli CID, poi rimuovi altri controlli
    blob = _pdf_normalize_control_spaces(blob)
    blob = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", blob)
    # Solo coda binaria finale: non interrompere a metà documento
    # (altrimenti spariscono sezioni tipo «Batteria interna» a pag. 16).
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


def _pdf_unescape_literal_bytes(raw: bytes) -> bytes:
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


def _pdf_unescape_literal(raw: bytes) -> str:
    out = _pdf_unescape_literal_bytes(raw)
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return out.decode("latin1", errors="ignore")


def _pdf_utf16_hex_to_str(hx: bytes) -> str:
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


def _pdf_cmap_from_tounicode_data(data: bytes) -> dict:
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


def _pdf_obj_num_before(raw: bytes, pos: int, lookback: int = 2500) -> int:
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


def _pdf_build_font_cmaps(raw: bytes, deadline=None):
    """ToUnicode per font (1.6.6).

    Prima le CMap venivano fuse in una sola: su PDF multi-font lo stesso CID
    mappa a caratteri diversi → testo spazzatura. Ora:
      - cmap per oggetto ToUnicode
      - associazione nome risorsa (/F1, /TT0, …) → cmap del font
      - default solo se c'è una sola CMap (PDF mono-font)

    Restituisce (font_cmaps: dict[str, dict], default_cmap: dict).
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

    def _map_font_resource_body(body: bytes, into: dict):
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
    # 1) /Font << /F1 N 0 R … >> inline
    for m in re.finditer(br"/Font\s*<<((?:[^>]|>(?!>)){0,4000})>>", raw):
        _map_font_resource_body(m.group(1), font_cmaps)
    # 2) /Font N 0 R → oggetto dizionario risorse (es. sample-multilingual-text.pdf)
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
        # Non fondere CMap in conflitto: meglio nessuna default che spazzatura.
        default_cmap = {}
    return font_cmaps, default_cmap


def _pdf_object_dict_body(raw: bytes, obj_num: int) -> bytes:
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


def _pdf_parse_tounicode_cmaps(raw: bytes, deadline=None) -> dict:
    """Compat: CMap di default (mono-font) oppure vuota se multi-font."""
    _fonts, default_cmap = _pdf_build_font_cmaps(raw, deadline=deadline)
    return default_cmap


def _pdf_decode_cid_bytes(data: bytes, cmap: dict) -> str:
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


def _pdf_cmap_mostly_bytes(cmap: dict) -> bool:
    """True se la CMap è tipica di font semplici (codici 0–255), non CID."""
    if not cmap:
        return False
    keys = list(cmap.keys())
    sample = keys if len(keys) <= 64 else keys[:: max(1, len(keys) // 64)]
    if not sample:
        return False
    return sum(1 for k in sample if 0 <= int(k) < 256) >= max(1, int(len(sample) * 0.85))


def _pdf_decode_byte_cmap(data: bytes, cmap: dict) -> str:
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


def _pdf_looks_like_cid_bytes(data: bytes) -> bool:
    if not data or len(data) < 2:
        return False
    sample = data[: min(len(data), 200)]
    if len(sample) < 2:
        return False
    nulls = sample.count(b"\x00")
    return nulls >= max(1, len(sample) // 4)


def _pdf_bytes_to_text(data: bytes, cmap: dict) -> str:
    if not data:
        return ""
    if cmap:
        # Font semplici (Liberation/DejaVu…): codici a 1 byte — prima del CID.
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
        # Ultimo tentativo byte-map anche se alcuni codici > 255 in CMap
        if _pdf_cmap_mostly_bytes(cmap):
            mapped = _pdf_decode_byte_cmap(data, cmap)
            if mapped.strip():
                return mapped
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin1", errors="ignore")


def _pdf_hex_to_str(hex_body: bytes, cmap: dict = None) -> str:
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
        # Codici a 2 byte tipici: <0030><0044>...
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


def _pdf_soften_camel_glued(text: str) -> str:
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


def _pdf_normalize_control_spaces(text: str) -> str:
    """Converte placeholder spazio (ToUnicode/custom) in spazi veri.

    Ogni PDF può mappare lo spazio in modo diverso:
    - Acer: spesso U+0000 U+0003
    - Focus Braille / encoding custom: spesso U+0006 (ACK)
    Se i controlli si cancellano senza sostituzione → parole attaccate.
    """
    if not text:
        return text
    # Coppie tipiche (UTF-16BE space / ETX usato come space)
    text = text.replace("\x00\x03", " ")
    text = text.replace("\x00\x20", " ")
    text = text.replace("\x00\x02", " ")
    text = text.replace("\x00\xa0", " ")  # NBSP in forma UTF-16BE spezzata
    # Bullet / elenco spesso \x01\x8e → pallino leggibile
    text = text.replace("\x01\x8e", " • ")
    text = text.replace("\x8e", " • ")
    # Altri C0 usati come glyph «spazio» (es. Focus 40 → \\x06): diventa spazio,
    # non cancellazione (altrimenti Display\\x06braille → Displaybraille).
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
    # Null residui (padding UTF-16): via senza inserire spazi tra lettere
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


def _pdf_trim_binary_tail(text: str) -> str:
    """Taglia solo la coda binaria finale (non a metà documento).

    Es. «…lesioni. "b&"o%#ÿÿ… Macintosh» in fondo. Un match a metà
    testo non va tagliato: altrimenti spariscono le pagine successive.
    """
    if not text or len(text) < 200:
        return text
    # Analizza solo l'ultimo tratto (coda), non tutto il blob
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


def _pdf_looks_like_garbage(line: str) -> bool:
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
    # Residui tipici di stream binari / ICC / font
    if "ÿÿÿ" in s or "\ufffd\ufffd" in s or s.count("ÿ") >= 3:
        return True
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", s):
        return True
    # poca lettera/cifra rispetto alla lunghezza → binario/simboli
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


def _pdf_inflate_stream(stream: bytes, max_out: int = None) -> bytes:
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


def _pdf_fallback_crude_lines(raw: bytes):
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


def _pdf_dict_int(dict_blob: bytes, *keys) -> int:
    for key in keys:
        m = re.search(re.escape(key) + br"\s+(\d+)", dict_blob)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                continue
    return 0


def _pdf_image_colorspace(dict_blob: bytes) -> str:
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


def _pdf_image_filter(dict_blob: bytes) -> str:
    if _pdf_dict_has_dct(dict_blob):
        return "jpeg"
    if b"/JPXDecode" in dict_blob:
        return "jpx"
    if _pdf_dict_has_flate(dict_blob):
        return "flate"
    if b"/CCITTFaxDecode" in dict_blob:
        return "ccitt"
    return "raw"


def _pdf_gray_to_rgb(data: bytes, width: int, height: int) -> bytes:
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


def _pdf_rgb_is_nearly_flat(data: bytes) -> bool:
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
    except Exception as e:
        logging.debug(f"Errore lettura PDF immagini {file_path}: {e}")
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
                        img = rtad_ocr.load_wx_image_silent(tmp)
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
    except Exception as e:
        logging.debug(f"Conversione immagine PDF fallita: {e}")
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
    except Exception as e:
        logging.debug(f"Salvataggio immagine PDF fallito: {e}")
        return False


def format_file_date_label(mtime):
    """Data breve dd/mm/yyyy da mtime file (tutti i tipi di risultato)."""
    if not mtime:
        return ""
    try:
        return datetime.datetime.fromtimestamp(mtime).strftime("%d/%m/%Y")
    except Exception:
        return ""


def pdf_info_date_timestamp(file_path, fallback=0):
    """Prova /ModDate o /CreationDate dal PDF; altrimenti fallback (mtime)."""
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
    except Exception as e:
        logging.debug(f"Estrazione immagini PDF per OCR fallita ({file_path}): {e}")
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
    """Ricerca per contenuto visivo (etichette Vision), opt-in 1.6.3."""
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


def load_copies_tip_dismissed():
    """True se l'utente ha chiesto di non ripetere l'avviso copie multiple."""
    data = _load_settings_dict()
    return bool(data.get("copies_tip_dismissed", False))


def save_copies_tip_dismissed(dismissed=True):
    data = _load_settings_dict()
    data["copies_tip_dismissed"] = bool(dismissed)
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


# Toast WinRT nel Centro notifiche (Windows+N), non il popup wx «Python»
RTAD_TOAST_AUMID = "AccessoDigitale.RTAD.Standalone"


def ensure_rtad_app_user_model_id():
    """Associa il processo Standalone a un AUMID (nome in Centro notifiche)."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(RTAD_TOAST_AUMID)
    except Exception:
        pass
    _register_toast_aumid_display_name(RTAD_TOAST_AUMID, APP_TITLE)


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
    """Mostra un toast WinRT breve (duration=short) in Centro notifiche.

    Non usa scenario=reminder (evita sticky / furto focus dal lettore documento).
    Ritorna True se mostrato.
    """
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

    # PowerShell + WinRT: niente dipendenze extra; reminder resta nel Centro
    ps = (
        "$ErrorActionPreference = 'Stop'; "
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null; "
        f"$raw = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64}')); "
        "$o = $raw | ConvertFrom-Json; "
        "function Esc([string]$s) { if ($null -eq $s) { return '' }; "
        "return (($s -replace '&','&amp;') -replace '<','&lt;' -replace '>','&gt;' -replace '\"','&quot;') }; "
        "$t = Esc ([string]$o.title); $b = Esc ([string]$o.body); "
        # Toast normale (non reminder): non resta sticky né ruba focus al lettore documento
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
    except Exception as e:
        logging.debug(f"Toast WinRT non avviato: {e}")
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
            # Riusa workbook già aperto se possibile
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
                # Preferisci prima colonna con testo (spesso B nei PVR)
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

        self.txt_display = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
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
        btn_close = wx.Button(panel, label="Chiudi (ESC)")
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
        grid.Add(wx.StaticText(self, label="&Sostituisci con:"), 0, wx.ALIGN_CENTER_VERTICAL)
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
        for r in self._rules:
            self.lst.Append(self._label(r))

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
            speak_accessible("Scrivi la parola da trovare.")
            self.txt_find.SetFocus()
            return
        # Aggiorna se già presente (casefold)
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
        speak_accessible(
            "Regola aggiornata." if updated else "Regola aggiunta."
        )
        self.txt_find.SetValue("")
        self.txt_repl.SetValue("")
        self.txt_find.SetFocus()

    def _on_remove(self, event=None):
        sel = self.lst.GetSelection()
        if sel == wx.NOT_FOUND or sel < 0 or sel >= len(self._rules):
            speak_accessible("Seleziona una regola da rimuovere.")
            return
        removed = self._rules.pop(sel)
        self._reload_list()
        speak_accessible(f"Rimossa: {removed.get('find') or ''}")

    def _on_ok(self, event=None):
        # Se c’è testo in Trova non ancora aggiunto, chiedi in silenzio di aggiungerlo
        pending = (self.txt_find.GetValue() or "").strip()
        if pending:
            self._on_add()
        self.EndModal(wx.ID_OK)

    def result(self):
        return bool(self.chk_enabled.GetValue()), list(self._rules)


class FindCopiesDialog(wx.Dialog):
    """Elenco copie RTAD + rapporto Desktop + rimozione sicura con consenso."""

    def __init__(self, parent, report_text: str, safe_paths=None):
        super().__init__(
            parent,
            title="Trova altre copie sul PC",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._safe_paths = list(safe_paths or [])
        self._report_text = report_text or ""
        vbox = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self,
            label=(
                "Qui sotto trovi cosa c’è sul PC. "
                "Niente viene cancellato finché non lo chiedi tu. "
                "Le chiavi API in AppData non vengono mai toccate."
            ),
        )
        intro.Wrap(520)
        vbox.Add(intro, 0, wx.ALL | wx.EXPAND, 10)
        self.txt = wx.TextCtrl(
            self,
            value=wrap_report_text(self._report_text),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        )
        self.txt.SetMinSize((560, 320))
        vbox.Add(self.txt, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 10)

        h = wx.BoxSizer(wx.HORIZONTAL)
        btn_save = wx.Button(self, label="&Salva rapporto sul Desktop")
        btn_save.Bind(wx.EVT_BUTTON, self._on_save)
        h.Add(btn_save, 0, wx.ALL, 5)
        # Sempre presente: se non ci sono pacchetti sicuri, spiega (non sparisce)
        n_safe = len(self._safe_paths)
        self.btn_del = wx.Button(
            self,
            label=(
                f"&Rimuovi copie sicure… ({n_safe})"
                if n_safe
                else "&Rimuovi copie sicure… (nessuna)"
            ),
        )
        self.btn_del.Bind(wx.EVT_BUTTON, self._on_delete_safe)
        self.btn_del.SetToolTip(
            "Cancella solo Setup/Portable lasciati in Download o Desktop, "
            "dopo conferma. Non tocca Installer, progetto né chiavi API."
        )
        h.Add(self.btn_del, 0, wx.ALL, 5)
        btn_close = wx.Button(self, wx.ID_CLOSE, label="&Chiudi")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE))
        h.Add(btn_close, 0, wx.ALL, 5)
        vbox.Add(h, 0, wx.ALIGN_CENTER | wx.BOTTOM, 8)
        self.SetSizerAndFit(vbox)
        self.CentreOnParent()
        self.txt.SetFocus()

    def _on_save(self, event=None):
        if rtad_copie is None:
            speak_accessible("Modulo copie non disponibile.")
            return
        try:
            path = rtad_copie.write_report_to_desktop(self._report_text)
            speak_accessible(f"Rapporto salvato: {os.path.basename(path)}")
            wx.MessageBox(
                f"Rapporto salvato sul Desktop:\n{path}",
                "Rapporto copie",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
        except Exception as e:
            logging.error(f"Salvataggio rapporto copie: {e}")
            speak_accessible("Impossibile salvare il rapporto.")

    def _on_delete_safe(self, event=None):
        if not self._safe_paths:
            speak_accessible("Nessuna copia Portable o in Download da rimuovere.")
            return
        lista = "\n".join(f"• {p}" for p in self._safe_paths)
        msg = (
            "Verranno cancellati SOLO questi file (Portable / Download / Desktop).\n"
            "Non si tocca l’Installer in Program Files né le chiavi API.\n\n"
            f"{lista}\n\n"
            "Confermi la cancellazione?"
        )
        dlg = wx.MessageDialog(
            self, msg, "Conferma rimozione sicura", wx.YES_NO | wx.ICON_WARNING
        )
        if dlg.ShowModal() != wx.ID_YES:
            dlg.Destroy()
            speak_accessible("Rimozione annullata.")
            return
        dlg.Destroy()
        ok, failed = rtad_copie.delete_safe_exes(self._safe_paths)
        self._safe_paths = [p for p in self._safe_paths if p in failed]
        if not self._safe_paths:
            self.btn_del.Enable(False)
        if ok:
            speak_accessible(f"Rimossi {len(ok)} file.")
        if failed:
            speak_accessible(f"Non rimossi: {len(failed)}.")
        extra = ""
        if ok:
            extra += "\nCancellati:\n" + "\n".join(ok)
        if failed:
            extra += "\nNon cancellati:\n" + "\n".join(failed)
        wx.MessageBox(
            "Operazione completata." + extra,
            "Rimozione sicura",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )


class ImageSectionsDialog(wx.Dialog):
    """Scelta sezioni per «Tutto sull'immagine» / batch cartella (1.6.6).

    Pulsanti creati sul Dialog (non su un Panel esterno a CreateButtonSizer):
    altrimenti OK/Invio sembrava premuto ma non chiudeva il dialogo.
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
            intro += (
                "\n\nScegli le sezioni, poi Invio o «Avvia analisi»."
            )
        else:
            intro = "Scegli cosa includere nel report, poi Invio o «Avvia analisi»."
            if context_label:
                intro += f"\nImmagine: {context_label}"
        lbl = wx.StaticText(self, label=intro)
        vbox.Add(lbl, 0, wx.ALL | wx.EXPAND, 10)

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
        # Stesso percorso di «Leggi testo nell'immagine» (OCR) usato da Esplora file
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
            speak_accessible("Seleziona almeno una sezione.")
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
        self.chk_timestamps = wx.CheckBox(
            self, label="Timestamp &nella trascrizione ([MM:SS], opt-in)"
        )
        self.chk_timestamps.SetValue(
            bool(preset.get("include_timestamps", False)) and self.chk_transcript.GetValue()
        )
        vbox.Add(self.chk_timestamps, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

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
            if not en:
                self.chk_timestamps.SetValue(False)

        self.chk_transcript.Bind(wx.EVT_CHECKBOX, _sync_ts)
        _sync_ts()

        if self.batch_mode:
            hint_txt = (
                "Accanto a ogni file viene creato «nome.rtad.txt» "
                "(stesso stem del media). "
                "Trascrizione/timestamp non attivi di default. "
                "File oltre i limiti: resta la scheda tecnica."
            )
        else:
            hint_txt = (
                "Se compili l'URL ha priorità sul file. "
                "Trascrizione/timestamp non attivi di default. "
                "File oltre i limiti: resta la scheda tecnica."
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
        speak_accessible(f"File selezionato: {os.path.basename(path)}")

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
        speak_accessible("Verifica yt-dlp…")
        self._refresh_ytdlp_label()
        if self.lbl_ytdlp is not None:
            speak_accessible(self.lbl_ytdlp.GetLabel())

    def _on_ytdlp_update(self, event=None):
        if rtad_media is None:
            speak_accessible("Modulo media non disponibile.")
            return
        speak_accessible("Aggiornamento yt-dlp in corso…")

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
                speak_accessible(msg)

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
            speak_accessible("Seleziona almeno una sezione.")
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
                speak_accessible(
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
            "include_timestamps": bool(want_tr and self.chk_timestamps.GetValue()),
            "url": url,
            "file_path": path,
            "save_txt": bool(self.chk_save and self.chk_save.GetValue()),
            "recursive": bool(
                self.chk_recursive and self.chk_recursive.GetValue()
            ),
        }


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
        speak_accessible(f"{title}. Usa le frecce per leggere.")

    def _save_ref_path(self):
        """Percorso per stem/cartella: PDF/originale se valido, altrimenti image_path."""
        src = (self.source_path or "").strip()
        if src and (os.path.isfile(src) or os.path.isdir(src)):
            return src
        return (self.image_path or "").strip()

    def _on_action(self, event=None):
        # Evita un secondo hub alla chiusura se già aperto da questo pulsante
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
        # CallLater: lascia chiudere la finestra prima di riaprire l'hub
        if callable(self._after_close_cb):
            wx.CallLater(150, self._run_after_close)
        event.Skip()

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
            speak_accessible("Testo copiato negli appunti.")
        else:
            speak_accessible("Impossibile aprire gli appunti.")

    def on_save_text(self, event=None):
        text = self.txt_display.GetValue() or ""
        if not text.strip():
            speak_accessible("Niente da salvare.")
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
            speak_accessible(f"Testo salvato: {os.path.basename(path)}")
        except Exception as e:
            speak_accessible(f"Salvataggio non riuscito: {e}")

    def on_print_text(self, event=None):
        """Stampa il report (Notepad /p → stampante predefinita o Print to PDF)."""
        text = self.txt_display.GetValue() or ""
        if not text.strip():
            speak_accessible("Niente da stampare.")
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
            speak_accessible(
                "Testo inviato alla stampante predefinita. "
                "Puoi scegliere «Microsoft Print to PDF» se serve un PDF."
            )
        except Exception as e:
            logging.error(f"Stampa report immagine fallita: {e}")
            speak_accessible(
                "Impossibile stampare. Assicurati di avere una stampante configurata."
            )

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
        else:
            event.Skip()


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
        self.lbl_status = wx.StaticText(
            panel,
            label=(
                "Domande ed estratti vanno a Google. La cronologia resta sul PC. "
                "Esc annulla la richiesta in corso."
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
        if resumed and (session.get("turns") or []):
            self.txt_history.SetFocus()
            speak_accessible(
                f"Conversazione precedente caricata, {title_name}. "
                "Puoi continuare o iniziarne una nuova. "
                "Alt+A apre l'elenco dei file, i più recenti in cima. "
                "Frecce per leggere."
                + link_note
            )
        elif (session.get("kind") == "free") and not (session.get("path") or ""):
            self.txt_q.SetFocus()
            speak_accessible(
                "Conversazione con Gemini, senza un file di partenza. "
                "Scrivi la domanda e premi Invio. Shift+Invio va a capo. "
                "Alt+A apre l'elenco dei file, i più recenti in cima. Esc annulla."
            )
        else:
            self.txt_q.SetFocus()
            speak_accessible(
                f"Conversazione con Gemini su {title_name}. "
                "Scrivi la domanda e premi Invio. Shift+Invio va a capo. "
                "Alt+A apre l'elenco dei file, i più recenti in cima. Esc annulla."
            )

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
        for item in self._links:
            self.lst_links.Append(rtad_chat.link_label(item))
        if self._links:
            self.lst_links.SetSelection(0)

    def on_open_link(self, event=None):
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
                speak=speak_accessible,
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


class DocumentStructureFrame(wx.Frame):
    """Lettore documenti RTAD: sommario, link, testo, cerca e navigazione titoli."""

    _HEADING_MARK_RE = re.compile(r"\[H([1-9])\]\s*([^\n]*)")

    def __init__(self, parent, file_path, struct):
        name = os.path.basename(file_path) if file_path else "Documento"
        super(DocumentStructureFrame, self).__init__(
            None,
            title=f"Lettore documento — {name}",
            size=(780, 620),
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
                # «i.» = posizione in lista (non la pagina PDF); la pagina va esplicita
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

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_open_link = None
        if self.links:
            self.btn_open_link = wx.Button(panel, label="Apri &link selezionato")
            self.btn_open_link.Bind(wx.EVT_BUTTON, self.on_link_activate)
            hbox.Add(self.btn_open_link, 0, wx.ALL, 5)
        btn_find = wx.Button(panel, label="Ce&rca nel testo…")
        btn_find.Bind(wx.EVT_BUTTON, self.on_find)
        hbox.Add(btn_find, 0, wx.ALL, 5)
        btn_copy = wx.Button(panel, label="&Copia testo")
        btn_copy.Bind(wx.EVT_BUTTON, self.on_copy)
        hbox.Add(btn_copy, 0, wx.ALL, 5)
        btn_save = wx.Button(panel, label="&Salva testo…")
        btn_save.Bind(wx.EVT_BUTTON, self.on_save_text)
        hbox.Add(btn_save, 0, wx.ALL, 5)
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
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_ACTIVATE, self._on_reader_activate)
        self.Bind(wx.EVT_ICONIZE, self._on_reader_iconize)
        for ctrl in (
            self.lst_outline,
            self.lst_links,
            self.txt_display,
        ):
            if ctrl is not None:
                ctrl.Bind(wx.EVT_SET_FOCUS, self._on_reader_child_focus)
        if self.lst_outline is not None and self.lst_outline.GetCount() > 0:
            self.lst_outline.SetSelection(0)
            self.lst_outline.SetFocus()
        else:
            self.txt_display.SetFocus()
        speak_accessible(
            summary
            + " Lettore documento RTAD. Tab: sommario, link e testo. "
            "Invio sul sommario: sezione qui in RTAD. "
            "Control+F: cerca. F3: ripeti (prossima occorrenza). "
            "Control+H / Control+Shift+H: titolo successivo o precedente. "
            "I link «Sito web» sono esterni."
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
            # PDF CID: parole attaccate («Batteriainterna»)
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
        Su PDF multilingue spesso solo l'inglese ha corpo estraibile; altre lingue
        compaiono solo come «Italiano ...... 339» nell'indice.
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

        # 1) Intestazione sezione: «English 3» / «Italiano 339» SENZA puntini in mezzo
        if label and printed:
            pat = re.compile(
                re.escape(label) + r"([^\w\n]{1,30})" + re.escape(printed) + r"\b",
                re.I,
            )
            for m in pat.finditer(content, search_from):
                if re.search(r"\.{2,}", m.group(1) or ""):
                    continue  # riga indice
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

        # 2) Altri needle, ma mai accontentarsi dell'indice a puntini
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
            # Nessuna pagina nota: apri comunque col predefinito
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

        def _refocus(prefer=prefer_text):
            try:
                self.Iconize(False)
                self.Raise()
                self.Show()
                if prefer and self.txt_display is not None:
                    self.txt_display.SetFocus()
                elif self.lst_outline is not None:
                    self.lst_outline.SetFocus()
                elif self.txt_display is not None:
                    self.txt_display.SetFocus()
            except Exception:
                pass

        def _after_open(open_mode=""):
            if open_mode == "page" and jumped == "section":
                speak_accessible(
                    f"Sezione «{title}» nel testo RTAD e PDF aperto alla pagina. "
                    f"Focus sul testo del documento."
                )
            elif open_mode == "page":
                speak_accessible(
                    f"Apro il PDF alla pagina con l'app predefinita («{title}»). "
                    + (
                        "In RTAD c'è solo l'indice di questa lingua. "
                        if jumped == "index_only"
                        else "Per leggere usa il testo qui in RTAD. "
                    )
                )
            elif open_mode == "file" and jumped == "section":
                speak_accessible(
                    f"Testo sulla sezione «{title}»; PDF aperto con l'app predefinita "
                    f"(senza salto pagina garantito)."
                )
            elif open_mode == "file":
                speak_accessible(
                    f"PDF aperto con l'app predefinita («{title}»). "
                    + (
                        "In RTAD c'è solo l'indice; vai alla pagina stampata nel visualizzatore."
                        if jumped == "index_only"
                        else ""
                    )
                )
            elif jumped == "section":
                speak_accessible(f"Testo sulla sezione «{title}».")
            elif jumped == "index_only":
                speak_accessible(
                    f"Per «{title}» in RTAD c'è solo l'indice (corpo non estraibile). "
                    f"Controlla l'app predefinita per i PDF in Windows e riprova Invio."
                )
            else:
                speak_accessible(f"Titolo in sommario: {title}")
            wx.CallLater(500, _refocus)

        if is_pdf:
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
            speak_accessible("Nessun link in questo documento.")
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
                speak_accessible("PDF aperto alla pagina con l'app.")
                return
            if mode == "file":
                speak_accessible("PDF aperto con l'app predefinita.")
                return
            speak_accessible("Impossibile aprire il PDF con l'app di sistema.")
            return
        if href.lower().startswith(("http://", "https://")):
            opened = False
            try:
                if sys.platform.startswith("win"):
                    os.startfile(href)  # più affidabile di webbrowser su Windows
                    opened = True
                else:
                    opened = bool(webbrowser.open(href))
            except Exception as e:
                logging.debug(f"os.startfile link fallito: {e}")
                try:
                    opened = bool(webbrowser.open(href))
                except Exception:
                    opened = False
            if opened:
                speak_accessible(
                    f"Apertura sito web esterno: {text or href}"
                )
                return
            speak_accessible(f"Impossibile aprire il link. Destinazione: {href}")
            return
        if href.lower().startswith("mailto:"):
            try:
                webbrowser.open(href)
                speak_accessible(f"Apertura link: {text or href}")
                return
            except Exception:
                pass
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(href or text))
            wx.TheClipboard.Close()
            speak_accessible(f"Link copiato: {href or text}")
        else:
            speak_accessible(f"Link: {href or text}")

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
            speak_accessible(announce)

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
        for c in (self.txt_display, self.lst_outline, self.lst_links):
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
        # Evita che Invio del dialogo arrivi al sommario e riapra Acrobat / chiuda focus
        self._ignore_enter_until = time.monotonic() + 0.4
        try:
            self.txt_display.SetFocus()
        except Exception:
            pass
        if not needle:
            speak_accessible("Ricerca annullata.")
            return
        self._find_needle = needle
        # Sempre in avanti dal cursore (non ripartire dall'inizio)
        if not self._find_in_text(needle, forward=True, from_start=False):
            speak_accessible(f"Nessuna occorrenza di «{needle}».")

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
            speak_accessible(f"Nessuna altra occorrenza di «{self._find_needle}».")

    def on_find_prev(self, event=None):
        if not self._find_needle:
            self.on_find()
            return
        if not self._find_in_text(self._find_needle, forward=False):
            speak_accessible(f"Nessuna altra occorrenza di «{self._find_needle}».")

    def on_next_heading(self, event=None):
        self._goto_heading(forward=True)

    def on_prev_heading(self, event=None):
        self._goto_heading(forward=False)

    def _goto_heading(self, forward=True):
        content = self.txt_display.GetValue() or ""
        matches = list(self._HEADING_MARK_RE.finditer(content))
        if not matches:
            speak_accessible("Nessun titolo [H] nel testo.")
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
        end = chosen.end()
        # Seleziona riga titolo se breve
        line_end = content.find("\n", chosen.start())
        if line_end < 0:
            line_end = end
        self._select_in_text(
            chosen.start(),
            line_end,
            announce=f"Titolo livello {level}: {title}",
        )

    def on_open_external(self, event=None):
        """Apre il file con l'app predefinita Windows (azione secondaria)."""
        if not self.file_path or not os.path.isfile(self.file_path):
            speak_accessible("File non disponibile.")
            return
        try:
            os.startfile(self.file_path)
            speak_accessible(
                f"Aperto con l'app predefinita: {os.path.basename(self.file_path)}"
            )
        except Exception as e:
            speak_accessible(f"Apertura esterna non riuscita: {e}")

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
            speak_accessible("Testo copiato negli appunti.")
        else:
            speak_accessible("Impossibile aprire gli appunti.")

    def on_save_text(self, event=None):
        text = self.txt_display.GetValue() or ""
        if not text.strip():
            speak_accessible("Niente da salvare.")
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
            speak_accessible(f"Testo salvato: {os.path.basename(path)}")
        except Exception as e:
            speak_accessible(f"Salvataggio non riuscito: {e}")

    def on_char_hook(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self.Close()
            return
        # Ctrl+F cerca; F3 / Shift+F3 ripeti; Ctrl+H / Ctrl+Shift+H titoli
        if event.ControlDown() and not event.AltDown():
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
        # Invio sulle liste: CHAR_HOOK è più affidabile del KEY_DOWN sul ListBox con NVDA
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            if time.monotonic() < float(self._ignore_enter_until or 0):
                return
            focused = self.FindFocus()
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
            f"Benvenuto nella versione {APP_VERSION}!\n\n"
            "Ecco le novità principali di questo aggiornamento:\n"
            "--------------------------------------------------\n"
            "• Conversazione Gemini anche senza un file già aperto.\n"
            "  Alt+Q, oppure Strumenti → Nuova conversazione Gemini.\n"
            "• Nella chat, Alt+A apre l'elenco della cartella, i più recenti in cima.\n"
            "  Ogni riga dice nome, data, tipo e dimensione. Su un video, fermandosi,\n"
            "  si sente la durata. Shift+freccia giù e Control+Spazio per scegliere.\n"
            "  Shift+Invio nella domanda va a capo e non invia.\n"
            "  Vale anche sulla chat nata da un file: quello di partenza resta.\n"
            "• Se i crediti prepagati della chiave sono finiti (HTTP 402),\n"
            "  la frase lo dice in italiano. Si ricaricano in AI Studio.\n"
            "  Non si prova un altro modello.\n"
            "• Resta dalla 1.8.2: se un modello è occupato, si prova il\n"
            "  successivo. Alt+L, Alt+H, Alt+B. Alt+G è Segnalibri.\n"
            "--------------------------------------------------\n"
            "Grazie per usare Ricerca Testuale Accesso Digitale!\n"
        )

        lbl_info = wx.StaticText(panel, label="Leggi le novità dell'ultimo aggiornamento:")
        vbox.Add(lbl_info, 0, wx.ALL, 8)

        self.txt_display = wx.TextCtrl(
            panel, value=text_content, style=wx.TE_MULTILINE | wx.TE_READONLY
        )
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
        speak_accessible(
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
            "  - Ctrl + Alt + V : Incolla percorso dagli Appunti (file o path)\n"
            "  - Ctrl + Shift + G : Conversazioni Gemini già salvate\n"
            "  - Alt + B : Conversazioni Gemini (finestra principale)\n"
            "  - Alt + Q : Nuova conversazione Gemini, anche senza un file\n"
            "  - Alt + A : Allega file. Elenco per data, i più recenti in cima\n"
            "  - Shift + Invio : nella domanda della chat, va a capo\n"
            "  - Alt + L : Chiave Google Vision\n"
            "  - Alt + H : Chiave Gemini\n"
            "  - Alt + G : Chiedi a Gemini (sul report o nel lettore documento)\n"
            "  - Alt + F : Apri la fonte selezionata (anche se sei sull'elenco)\n"
            "  - INVIO nel campo testo : Avvia ricerca\n"
            "  - Alt + N : Annulla ricerca in corso e mantieni i risultati\n"
            "  - Alt + I : Info Versione e Autore\n"
            "  - Alt + P : Annuncia stato (Premi due volte velocemente per copiare negli appunti)\n"
            "  - TAB oppure Alt+S / S : Raggiunge la casella 'Stato avanzamento'\n"
            "  - Alt + K : Scatta uno screenshot salvato in 'Catture di schermata'\n"
            "  - Alt + Shift + K : Cattura schermo e descrivi l'immagine\n"
            "  - Ctrl + Shift + U : Descrivi immagine da URL\n"
            "  - Ctrl + Shift + I : Descrivi immagine dagli Appunti (o URL)\n"
            "  - Ctrl + P: Stampa rapida risultati di ricerca in lista\n"
            "  - Ctrl + D: Aggiungi percorso ai segnalibri\n"            "  - Ctrl + Shift + P: Salva profilo di ricerca attuale\n"            "  - Ctrl + Shift + L: Carica un profilo di ricerca\n"
            "  - INVIO : Avvia ricerca, apri file alla riga esatta o apri articolo nel Browser\n"
            "  - SPAZIO / F4 : Anteprima vocale immediata del risultato\n"
            "  - F7 : Attiva / Disattiva sintesi vocale (Mute)\n"
            "  - Ctrl + + / Ctrl + - : velocità sintesi più rapida / più lenta\n"
            "  - Ctrl + Shift + V : scegli voce SAPI\n"
            "  - Menu Voce : tono, prova voce, motore SAPI/NVDA\n"
            "  - Casella OCR : Spazio per attivare/disattivare testo in immagini/PDF scansionati\n"
            "  - CONTROL : Zittisce all'istante la lettura in corso\n"
            "  - Pulsante Feed Thunderbird : rileva le cartelle Feeds di Thunderbird\n"
            "  - Supporto OPML / RSS locale : file .opml, .rss, .atom, .xml nel percorso\n"
            "  - Tasto APPLICAZIONI : Menu contestuale completo\n"
            "  - F1 : Guida ai Comandi (questa finestra)\n"
            "  - Aiuto → Guida completa (HTML) : guida cercabile nel browser (Vision/Gemini)\n"
            "  - ESC : annulla ricerca in corso; non chiude (usa Alt+F4 / Ctrl+Q). Opzione in Strumenti.\n"
            "  - Alt+F4 / Ctrl+Q / Chiudi : esci dall'applicazione\n\n"
            "--------------------------------------------------\n"
            "SOSTIENI IL PROGETTO:\n"
            f"{DONATION_URL}\n"
            "--------------------------------------------------"
        )

        lbl_info = wx.StaticText(panel, label="Usa le frecce Su/Giù e Sinistra/Destra per navigare nel testo:")
        vbox.Add(lbl_info, 0, wx.ALL, 8)

        self.txt_display = wx.TextCtrl(
            panel, value=self.text_content, style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_copy = wx.Button(panel, label="&Copia Testo Comandi")
        btn_copy.Bind(wx.EVT_BUTTON, self.on_copy_text)
        hbox_btns.Add(btn_copy, 0, wx.ALL, 5)

        btn_guide = wx.Button(panel, label="Apri guida completa (&HTML)…")
        btn_guide.Bind(wx.EVT_BUTTON, self.on_open_html_guide_btn)
        hbox_btns.Add(btn_guide, 0, wx.ALL, 5)

        btn_close = wx.Button(panel, label="Chiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
        hbox_btns.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_btns, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(vbox)
        self.Centre()
        self.txt_display.SetFocus()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def on_open_html_guide_btn(self, event=None):
        parent = self.GetParent()
        if parent is not None and hasattr(parent, "on_open_html_guide"):
            parent.on_open_html_guide()
            return
        try:
            path = create_html_help_file().replace("\\", "/")
            webbrowser.open(f"file:///{path}")
            speak_accessible("Guida completa aperta nel browser.")
        except Exception:
            speak_accessible("Impossibile aprire la guida HTML.")

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
        self.profile_items = []
        self.history_query_items = []
        self.last_alt_p_time = 0
        self.current_sort = load_sort_preference()
        self.last_feed_raw_occurrences = 0
        try:
            load_speech_settings()
        except Exception:
            pass

        self._init_menu_bar()

        panel = wx.Panel(self)
        self._main_panel = panel
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
        self.txt_custom_ext = wx.TextCtrl(panel, value="")
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
                "EasyOCR (opzionale: pip install -r requirements-ocr-easy.txt)",
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
            if rtad_media is not None:
                rtad_media.set_gemini_api_key(gemkey)
        except Exception:
            pass
        try:
            sync_transcript_glossary_to_media()
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

        lbl_results = wx.StaticText(panel, label="Risultati trovati (INVIO apre file, SPAZIO/F4 anteprima vocale, APPLICAZIONI opzioni):")
        vbox.Add(lbl_results, 0, wx.ALL, 5)
        self.lst_results = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.lst_results.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open_file_event)
        self.lst_results.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.lst_results.Bind(wx.EVT_KEY_DOWN, self.on_list_key_down)
        vbox.Add(self.lst_results, 1, wx.EXPAND | wx.ALL, 5)

        hbox_bottom = wx.BoxSizer(wx.HORIZONTAL)
        btn_open = wx.Button(panel, label="Apri File (Alla Riga)")
        btn_open.Bind(wx.EVT_BUTTON, self.on_open_file_event)
        hbox_bottom.Add(btn_open, 0, wx.ALL, 5)

        btn_preview = wx.Button(panel, label="Anteprima Voce (F4)")
        btn_preview.Bind(wx.EVT_BUTTON, lambda e: self.speak_selected_preview())
        hbox_bottom.Add(btn_preview, 0, wx.ALL, 5)

        btn_close = wx.Button(panel, label="Chiudi")
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        hbox_bottom.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_bottom, 0, wx.ALIGN_CENTER)
        panel.SetSizer(vbox)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_global_char_hook)
        # 1.7.5: drop sui figli (Panel), non solo sul Frame — altrimenti Windows
        # rilascia i file sul pannello e l’evento non arriva mai.
        self._enable_file_drop_targets()

        if check_first_run_update():
            wx.CallLater(600, self.show_whats_new_dialog)

    def _enable_file_drop_targets(self):
        """Abilita trascinamento file/cartella (FileDropTarget, non solo DragAcceptFiles).

        Su Windows i controlli figli coprono il Frame: senza DropTarget su panel e
        campi principali il rilascio non arriva mai (cursore «vietato»).
        """

        class _RTADFileDropTarget(wx.FileDropTarget):
            def __init__(self, owner):
                super().__init__()
                self._owner = owner

            def OnDropFiles(self, x, y, filenames):
                try:
                    self._owner._apply_dropped_paths(filenames or [])
                except Exception as e:
                    logging.error(f"OnDropFiles: {e}")
                return True

        targets = [self]
        panel = getattr(self, "_main_panel", None)
        if panel is not None:
            targets.append(panel)
            try:
                for child in panel.GetChildren():
                    targets.append(child)
            except Exception:
                pass
        for name in ("txt_path", "txt_query", "lst_results"):
            w = getattr(self, name, None)
            if w is not None:
                targets.append(w)

        seen = set()
        for w in targets:
            wid = id(w)
            if wid in seen:
                continue
            seen.add(wid)
            try:
                w.SetDropTarget(_RTADFileDropTarget(self))
            except Exception as e:
                logging.debug(f"SetDropTarget non attivo su {w}: {e}")

    def _apply_dropped_paths(self, filenames):
        """Comune a FileDropTarget / eventuale drop nativo."""
        paths = []
        for p in filenames or []:
            if not p:
                continue
            try:
                p = os.path.normpath(p)
            except Exception:
                continue
            if os.path.isfile(p) or os.path.isdir(p):
                paths.append(p)
        logging.info(f"Drop file ricevuto: n={len(paths)} paths={paths!r}")
        if not paths:
            speak_accessible("Nessun file o cartella riconosciuti nel trascinamento.")
            return
        if len(paths) == 1:
            self.apply_search_path(paths[0], offer_open=os.path.isfile(paths[0]))
        else:
            self.apply_search_path(paths, offer_open=False)

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

        # Menu Voce (Standalone: SAPI velocità/voce; mute condiviso come concetto)
        voice_menu = wx.Menu()
        item_toggle_speech = voice_menu.Append(
            wx.ID_ANY, "Attiva / Disattiva sintesi (Mute)\tF7"
        )
        voice_menu.AppendSeparator()
        item_rate_up = voice_menu.Append(wx.ID_ANY, "Velocità &più rapida\tCtrl++")
        item_rate_down = voice_menu.Append(wx.ID_ANY, "Velocità più &lenta\tCtrl+-")
        item_rate_reset = voice_menu.Append(wx.ID_ANY, "Velocità &normale")
        voice_menu.AppendSeparator()
        item_pitch_up = voice_menu.Append(wx.ID_ANY, "Tono più &alto")
        item_pitch_down = voice_menu.Append(wx.ID_ANY, "Tono più &basso")
        item_pitch_reset = voice_menu.Append(wx.ID_ANY, "Tono n&ormale")
        voice_menu.AppendSeparator()
        item_choose_voice = voice_menu.Append(
            wx.ID_ANY, "Scegli &voce SAPI...\tCtrl+Shift+V"
        )
        item_test_voice = voice_menu.Append(wx.ID_ANY, "Prova vo&ce")
        voice_menu.AppendSeparator()
        self.item_engine_sapi = voice_menu.AppendCheckItem(
            wx.ID_ANY, "Annunci RTAD con &SAPI (velocità/voce regolabili)"
        )
        self.item_engine_sapi.Check(bool(_speech_use_sapi))
        menubar.Append(voice_menu, "&Voce")

        self.Bind(wx.EVT_MENU, self.on_toggle_speech, item_toggle_speech)
        self.Bind(wx.EVT_MENU, lambda e: self.on_speech_rate(+1), item_rate_up)
        self.Bind(wx.EVT_MENU, lambda e: self.on_speech_rate(-1), item_rate_down)
        self.Bind(wx.EVT_MENU, lambda e: self.on_speech_rate(0, reset=True), item_rate_reset)
        self.Bind(wx.EVT_MENU, lambda e: self.on_speech_pitch(+1), item_pitch_up)
        self.Bind(wx.EVT_MENU, lambda e: self.on_speech_pitch(-1), item_pitch_down)
        self.Bind(wx.EVT_MENU, lambda e: self.on_speech_pitch(0, reset=True), item_pitch_reset)
        self.Bind(wx.EVT_MENU, self.on_choose_sapi_voice, item_choose_voice)
        self.Bind(wx.EVT_MENU, self.on_test_sapi_voice, item_test_voice)
        self.Bind(wx.EVT_MENU, self.on_toggle_speech_engine, self.item_engine_sapi)

        # Menu Strumenti
        tools_menu = wx.Menu()
        item_update = tools_menu.Append(wx.ID_ANY, "Verifica &Aggiornamenti...\tCtrl+U")
        item_copie = tools_menu.Append(
            wx.ID_ANY, "Trova altre &copie sul PC…"
        )
        self.Bind(wx.EVT_MENU, self.on_find_other_copies, item_copie)
        item_paste_path = tools_menu.Append(
            wx.ID_ANY, "Incolla pe&rcorso dagli Appunti…\tCtrl+Alt+V"
        )
        self.Bind(wx.EVT_MENU, self.on_paste_path_from_clipboard, item_paste_path)
        item_gemini_new = tools_menu.Append(
            wx.ID_ANY, "Nuova conversazione Gemini (&Q)…"
        )
        self.Bind(wx.EVT_MENU, lambda e: open_free_gemini_chat(self), item_gemini_new)
        item_gemini_chats = tools_menu.Append(
            wx.ID_ANY, "Conversazioni Gemini (Alt+&B)…\tCtrl+Shift+G"
        )
        self.Bind(wx.EVT_MENU, self.on_gemini_conversations, item_gemini_chats)
        tools_menu.AppendSeparator()
        item_gkey = tools_menu.Append(
            wx.ID_ANY, "Chiave API Goog&le Vision…"
        )
        self.Bind(wx.EVT_MENU, self.on_set_google_vision_key, item_gkey)
        item_gemkey = tools_menu.Append(
            wx.ID_ANY, "C&hiave API Gemini (descrizione avanzata)…"
        )
        self.Bind(wx.EVT_MENU, self.on_set_gemini_api_key, item_gemkey)
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
        item_ocr_only = tools_menu.Append(
            wx.ID_ANY, "Leggi testo nell'immagine (&OCR)…"
        )
        self.Bind(wx.EVT_MENU, self.on_image_ocr_dialog, item_ocr_only)
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
        item_log = help_menu.Append(wx.ID_ANY, "Esporta &Log di Diagnostica sul Desktop")
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
        self.Bind(wx.EVT_MENU, lambda e: webbrowser.open(GITHUB_REPO_URL), item_github)
        self.Bind(wx.EVT_MENU, self.on_show_info, item_info)
        self.Bind(wx.EVT_MENU, self.on_export_log, item_log)
        self.Bind(wx.EVT_MENU, self.on_send_feedback, item_feedback)

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
            speak_accessible(f"Impossibile salvare la chiave: {e}", force=True)
            return
        if new_key:
            # Se c’è una chiave, proponi Google come motore
            try:
                self.choice_ocr_engine.SetSelection(2)
                save_ocr_engine_preference("google")
                if rtad_ocr is not None:
                    rtad_ocr.set_engine_preference("google")
            except Exception:
                pass
            speak_accessible(
                "Chiave Google Vision salvata in locale. "
                "Motore OCR impostato su Google Cloud Vision.",
                force=True,
            )
        else:
            speak_accessible("Chiave Google Vision rimossa.", force=True)

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
            speak_accessible(f"Impossibile salvare la chiave Gemini: {e}", force=True)
            return
        if new_key:
            speak_accessible(
                "Chiave Gemini salvata in locale. "
                "Ora «Descrivi immagine» userà la descrizione avanzata.",
                force=True,
            )
        else:
            speak_accessible("Chiave Gemini rimossa.", force=True)

    def on_transcript_glossary(self, event=None):
        """Strumenti → Glossario trascrizioni (correzioni post-Gemini)."""
        if rtad_media is None:
            speak_accessible("Modulo media non disponibile.")
            return
        dlg = TranscriptGlossaryDialog(self)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                speak_accessible("Glossario non modificato.")
                return
            enabled, rules = dlg.result()
        finally:
            dlg.Destroy()
        try:
            save_transcript_glossary(enabled, rules)
        except Exception as e:
            speak_accessible(f"Impossibile salvare il glossario: {e}", force=True)
            return
        n = len(rules or [])
        if enabled and n:
            speak_accessible(
                f"Glossario attivo: {n} regole. "
                "Si applicherà alle prossime analisi audio/video."
            )
        elif enabled:
            speak_accessible(
                "Glossario attivo ma senza regole. Aggiungine almeno una."
            )
        else:
            speak_accessible("Glossario disattivato.")

    def on_ocr_engine_choice(self, event=None):
        eng = ocr_engine_from_choice_index(self.choice_ocr_engine.GetSelection())
        try:
            save_ocr_engine_preference(eng)
        except Exception:
            pass
        if eng == "google" and not load_google_vision_api_key():
            speak_accessible(
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
            speak_accessible("Modulo OCR non disponibile.", force=True)
            return
        try:
            rtad_ocr.set_engine_preference(eng)
            msg = rtad_ocr.engine_status_message()
        except Exception as e:
            msg = f"Impossibile impostare il motore OCR: {e}"
        speak_accessible(msg, force=True)

    def on_ocr_checkbox(self, event=None):
        enabled = bool(self.chk_ocr.GetValue())
        try:
            save_include_ocr_preference(enabled)
        except Exception:
            pass
        if enabled:
            if rtad_ocr is None:
                speak_accessible(
                    "Modulo OCR non disponibile in questa build.",
                    force=True,
                )
                try:
                    self.chk_ocr.SetValue(False)
                    save_include_ocr_preference(False)
                except Exception:
                    pass
                return
            # Allinea motore scelto + recheck (utile dopo pip install easyocr)
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
                speak_accessible(rtad_ocr.engine_status_message(), force=True)
            else:
                try:
                    status = rtad_ocr.engine_status_message()
                except Exception:
                    status = ""
                speak_accessible(
                    "OCR attivato: cercherà il testo dentro immagini e PDF scansionati. "
                    "Può richiedere più tempo. "
                    + (status or ""),
                    force=True,
                )
        else:
            speak_accessible("OCR disattivato: solo nomi file e documenti con testo.", force=True)

    def on_visual_checkbox(self, event=None):
        enabled = bool(self.chk_visual.GetValue())
        try:
            save_include_visual_preference(enabled)
        except Exception:
            pass
        if enabled:
            if rtad_ocr is None:
                speak_accessible(
                    "Modulo immagini non disponibile in questa build.",
                    force=True,
                )
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
                speak_accessible(
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
                    speak_accessible(
                        "Contenuto visivo non attivato: manca la chiave Google.",
                        force=True,
                    )
                    return
            if rtad_ocr is not None:
                try:
                    rtad_ocr.set_google_api_key(load_google_vision_api_key())
                except Exception:
                    pass
            speak_accessible(
                "Contenuto visivo attivato: la ricerca userà anche etichette e scene "
                "nelle immagini (più lento, con cache). "
                + (rtad_ocr.vision_status_message() if rtad_ocr else ""),
                force=True,
            )
        else:
            speak_accessible("Contenuto visivo disattivato.", force=True)

    def on_zip_checkbox(self, event=None):
        enabled = bool(self.chk_zip.GetValue())
        try:
            save_include_zip_preference(enabled)
        except Exception:
            pass
        if enabled:
            if rtad_zip is None:
                speak_accessible(
                    "Modulo ZIP non disponibile in questa build.",
                    force=True,
                )
                try:
                    self.chk_zip.SetValue(False)
                    save_include_zip_preference(False)
                except Exception:
                    pass
                return
            speak_accessible(
                "Ricerca dentro gli archivi ZIP attivata.",
                force=True,
            )
        else:
            speak_accessible("Ricerca dentro ZIP disattivata.", force=True)

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
            speak_accessible(
                "Esc chiude l'applicazione. Durante la ricerca Esc annulla comunque.",
                force=True,
            )
        else:
            speak_accessible(
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
            speak_accessible(
                "Notifica di sistema a fine ricerca attivata. "
                "Resta nel Centro notifiche Windows finché non la apri.",
                force=True,
            )
        else:
            speak_accessible(
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
            speak_accessible(
                "Salvataggio automatico dei risultati a fine ricerca attivato."
                + dest_note
                + " Per cambiare cartella: Strumenti, Cartella salvataggio automatico risultati.",
                force=True,
            )
        else:
            speak_accessible(
                "Salvataggio automatico dei risultati disattivato.",
                force=True,
            )

    def _prompt_auto_save_dir(self):
        """Chiede/aggiorna la cartella di auto-salvataggio. Ritorna il path o ''."""
        start = load_last_export_dir() or self.get_dynamic_desktop_path()
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
            speak_accessible(
                f"Cartella salvataggio automatico: {chosen}.",
                force=True,
            )

    def on_clear_ocr_cache(self, event=None):
        if rtad_ocr is None:
            speak_accessible("Modulo OCR non disponibile.")
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
            speak_accessible("Cache OCR già vuota.")
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
            speak_accessible("Operazione annullata.")
            return
        ask.Destroy()
        try:
            removed = int(rtad_ocr.clear_ocr_cache() or 0)
        except Exception as e:
            logging.error(f"Svuota cache OCR fallita: {e}")
            wx.MessageBox(
                f"Impossibile svuotare la cache OCR.\n{e}",
                "Errore",
                wx.OK | wx.ICON_ERROR,
            )
            return
        msg = f"Cache OCR svuotata: rimossi {removed} file."
        speak_accessible(msg, force=True)
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

        # Se il lettore documento è aperto/attivo: solo annuncio, niente toast invasivo
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
                speak_accessible(body)
            except Exception:
                pass
            return

        try:
            self.RequestUserAttention(wx.USER_ATTENTION_INFO)
        except Exception:
            pass

        def _refocus():
            try:
                # Non sollevare la main se l'utente è sul lettore
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
                # Timeout breve (non Timeout_Never)
                n.Show(timeout=5)
            except Exception as e:
                logging.debug(f"NotificationMessage non disponibile: {e}")

        def _worker():
            ok = False
            try:
                ok = show_persistent_windows_notification(APP_TITLE, body)
            except Exception as e:
                logging.debug(f"Toast fine-ricerca fallito: {e}")
                ok = False
            if not ok:
                wx.CallAfter(_fallback_wx)

        threading.Thread(target=_worker, daemon=True).start()

    def on_save_search_profile(self, event=None):
        fields = self._collect_current_profile_fields()
        if not fields["path"] and fields["filter_mode"] == 0 and not fields["query"]:
            speak_accessible(
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
            speak_accessible("Nome profilo non valido.")
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
            speak_accessible(f"Profilo aggiornato: {name}.")
        else:
            speak_accessible(f"Profilo salvato: {name}.")

    def on_load_search_profile_dialog(self, event=None):
        profiles = load_search_profiles()
        if not profiles:
            speak_accessible("Nessun profilo di ricerca salvato.")
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
            speak_accessible(". ".join(bits) + ".")
        if profile.get("auto_start") and query:
            wx.CallLater(350, self.start_search_thread)

    def on_manage_search_profiles(self, event=None):
        profiles = load_search_profiles()
        if not profiles:
            speak_accessible("Nessun profilo di ricerca salvato.")
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
                    speak_accessible(f"Profilo eliminato: {sel_name}.")
                else:
                    speak_accessible("Impossibile eliminare il profilo.")
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
                    speak_accessible("Nome non valido.")
                elif rename_search_profile(sel_name, new_name):
                    self.update_profiles_menu()
                    speak_accessible(f"Profilo rinominato in {new_name}.")
                else:
                    speak_accessible(
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

    def show_practical_guide_dialog(self):
        dlg = PracticalGuideFrame(self)
        dlg.Show()
        dlg.Raise()

    def on_open_html_guide(self, event=None):
        """Aiuto → Guida completa HTML (indice, Vision/Gemini, Ctrl+F nel browser)."""
        try:
            path = create_html_help_file()
            webbrowser.open("file:///" + path.replace("\\", "/"))
            speak_accessible(
                "Guida completa aperta nel browser. "
                "Con NVDA: NVDA Control F per cercare; altrimenti Control F."
            )
        except Exception as e:
            logging.error(f"Apertura guida HTML: {e}")
            speak_accessible("Impossibile aprire la guida HTML.")

    def show_shortcuts_dialog(self):
        dlg = ShortcutsFrame(self)
        dlg.Show()
        dlg.Raise()

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
        
        try:
            if wx.TheClipboard.Open():
                try:
                    wx.TheClipboard.SetData(wx.TextDataObject(msg))
                finally:
                    wx.TheClipboard.Close()
                speak_accessible("Stato copiato negli appunti.")
            else:
                speak_accessible("Impossibile copiare negli appunti.")
        except Exception:
            speak_accessible("Impossibile copiare negli appunti.")

    def focus_status_progress(self, event=None):
        try:
            self.txt_status_progress.SetFocus()
            self.txt_status_progress.SetInsertionPoint(0)
            msg = self.txt_status_progress.GetValue().strip() or "Stato avanzamento non disponibile."
            # Differisci l'annuncio: SetFocus + Speak nello stesso tick può bloccare la UI
            wx.CallLater(50, speak_accessible, msg)
        except Exception:
            wx.CallLater(50, speak_accessible, "Impossibile raggiungere lo stato di avanzamento.")

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
        elif ctrl and event.ShiftDown() and key in (ord("P"), ord("p")):
            self.on_save_search_profile(None)
            return
        elif ctrl and event.ShiftDown() and key in (ord("L"), ord("l")):
            self.on_load_search_profile_dialog(None)
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
        elif ctrl and alt and key in (ord("V"), ord("v")):
            self.on_paste_path_from_clipboard(None)
            return
        elif alt and key in (ord("K"), ord("k")) and event.ShiftDown():
            self.on_describe_from_screenshot(None)
            return
        elif alt and key in (ord("K"), ord("k")):
            self.on_take_screenshot(None)
            return
        elif ctrl and event.ShiftDown() and key in (ord("U"), ord("u")):
            self.on_describe_from_url(None)
            return
        elif ctrl and event.ShiftDown() and key in (ord("M"), ord("m")):
            self.on_media_from_url(None)
            return
        elif ctrl and event.ShiftDown() and key in (ord("I"), ord("i")):
            self.on_describe_from_clipboard(None)
            return
        elif alt and key in (ord("N"), ord("n")):
            self.on_cancel_search(None)
            return
        elif alt and key in (ord("I"), ord("i")):
            self.on_show_info(None)
            return
        elif alt and key == wx.WXK_F4:
            # Alt+F4 = chiusura Windows standard (non confondere con F4 anteprima).
            self._stop_search = True
            self.Close()
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
        elif ctrl and key in (ord("="), ord("+"), wx.WXK_NUMPAD_ADD):
            self.on_speech_rate(+1)
            return
        elif ctrl and key in (ord("-"), wx.WXK_NUMPAD_SUBTRACT):
            self.on_speech_rate(-1)
            return
        elif ctrl and event.ShiftDown() and key in (ord("V"), ord("v")):
            self.on_choose_sapi_voice()
            return
        elif key == wx.WXK_SHIFT:
            event.Skip()
            return
        elif key == wx.WXK_ESCAPE:
            # Durante la ricerca: annulla. A riposo: chiude solo se abilitato in Strumenti.
            if not self.btn_search.IsEnabled():
                self.on_cancel_search(None)
                return
            if load_escape_closes_preference():
                self._stop_search = True
                self.Destroy()
                return
            speak_accessible(
                "Esc non chiude l'applicazione. Usa Alt+F4, Ctrl+Q oppure Chiudi. "
                "Opzione in Strumenti se preferisci Esc per uscire.",
                force=True,
            )
            return

        focus = wx.Window.FindFocus()
        text_ctrls = (self.txt_query, self.txt_path, self.txt_custom_ext, self.txt_filter)

        # Controlli interattivi: Spazio/Invio devono restare nativi (caselle OCR/feed, ecc.)
        if isinstance(focus, (wx.CheckBox, wx.Choice, wx.ComboBox, wx.RadioButton)):
            event.Skip()
            return

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
        try:
            save_speech_settings()
        except Exception:
            pass
        if _speech_active:
            speak_accessible("Sintesi vocale attivata", force=True)
        else:
            speak_accessible("Sintesi vocale disattivata", force=True)

    def on_speech_rate(self, delta, reset=False):
        if reset:
            rate = set_speech_rate(absolute=0)
        else:
            rate = set_speech_rate(delta=delta)
        speak_accessible(
            f"Velocità {speech_rate_label(rate)}. Valore {rate} su scala da {SAPI_RATE_MIN} a {SAPI_RATE_MAX}.",
            force=True,
        )

    def on_speech_pitch(self, delta, reset=False):
        if reset:
            pitch = set_speech_pitch(absolute=0)
        else:
            pitch = set_speech_pitch(delta=delta)
        if pitch == 0:
            label = "normale"
        elif pitch > 0:
            label = f"più alto ({pitch})"
        else:
            label = f"più basso ({pitch})"
        speak_accessible(f"Tono {label}.", force=True)

    def on_toggle_speech_engine(self, evt=None):
        enabled = True
        try:
            if self.item_engine_sapi:
                enabled = bool(self.item_engine_sapi.IsChecked())
        except Exception:
            enabled = not _speech_use_sapi
        set_speech_use_sapi(enabled)
        if enabled:
            speak_accessible(
                "Annunci RTAD con SAPI: velocità e voce regolabili da questo menu.",
                force=True,
            )
        else:
            speak_accessible(
                "Annunci: NVDA se attivo, altrimenti SAPI. "
                "La velocità del menu Voce vale solo per SAPI.",
                force=True,
            )

    def on_test_sapi_voice(self, evt=None):
        set_speech_use_sapi(True)
        try:
            if self.item_engine_sapi:
                self.item_engine_sapi.Check(True)
        except Exception:
            pass
        speak_accessible(
            f"Prova voce. Velocità {speech_rate_label()}. "
            f"Ricerca Testuale Accesso Digitale versione {APP_VERSION}.",
            force=True,
        )

    def on_choose_sapi_voice(self, evt=None):
        voices = list_sapi_voices()
        if not voices:
            speak_accessible("Nessuna voce SAPI disponibile su questo computer.", force=True)
            return
        # Prima voce = predefinita Windows (svuota speech_voice_id)
        names = ["Voce predefinita di Windows"] + [v["name"] for v in voices]
        sel = 0
        if _speech_voice_id:
            for i, v in enumerate(voices):
                if v["id"] == _speech_voice_id:
                    sel = i + 1
                    break
        dlg = wx.SingleChoiceDialog(
            self,
            "Scegli la voce SAPI per gli annunci RTAD "
            "(OneCore compare qui se installata come token SAPI):",
            "Voce SAPI",
            names,
        )
        try:
            dlg.SetSelection(sel)
        except Exception:
            pass
        if dlg.ShowModal() == wx.ID_OK:
            idx = dlg.GetSelection()
            if idx == 0:
                set_speech_voice_id("")
                set_speech_use_sapi(True)
                try:
                    if self.item_engine_sapi:
                        self.item_engine_sapi.Check(True)
                except Exception:
                    pass
                speak_accessible("Voce predefinita di Windows impostata.", force=True)
            elif 1 <= idx <= len(voices):
                chosen = voices[idx - 1]
                set_speech_voice_id(chosen["id"])
                set_speech_use_sapi(True)
                try:
                    if self.item_engine_sapi:
                        self.item_engine_sapi.Check(True)
                except Exception:
                    pass
                speak_accessible(f"Voce impostata: {chosen['name']}.", force=True)
        dlg.Destroy()

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
        self.apply_search_path(
            selected_path, offer_open=(mode == 1 and os.path.isfile(selected_path))
        )

    def apply_search_path(self, selected_path, *, offer_open=True):
        """Imposta il percorso (Sfoglia / Appunti / drop) e offre apertura se file."""
        if not selected_path:
            return
        # Più path: unisci con ; (ricerca multipla già supportata)
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
                speak_accessible(
                    f"Impostati {len(paths)} percorsi dagli Appunti o dal trascinamento."
                )
                return
        self.txt_path.SetValue(selected_path)
        save_last_path(selected_path)
        kind = "file" if os.path.isfile(selected_path) else "cartella"
        speak_accessible(f"Percorso impostato ({kind}): {selected_path}.")

        ext = (
            os.path.splitext(selected_path)[1].lower()
            if os.path.isfile(selected_path)
            else ""
        )
        if ext == ".cda":
            msg = message_for_cda_path(selected_path)
            speak_accessible(msg)
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
            speak_accessible(msg)
            dlg = wx.MessageDialog(
                self, msg, "DVD video", wx.OK | wx.ICON_INFORMATION
            )
            dlg.ShowModal()
            dlg.Destroy()
            return

        if not offer_open or not os.path.isfile(selected_path):
            return
        offer = None
        if ext in IMG_EXTS:
            offer = ("image-all", "Apri ora «Tutto sull'immagine» per questo file?")
        elif ext in MEDIA_EXTS:
            offer = ("media-all", "Apri ora «Tutto sull'audio/video» per questo file?")
        elif ext in SHELL_DOCUMENT_EXTS:
            offer = ("open-doc", "Apri ora questo documento in Ricerca Testuale?")
        if not offer:
            return
        action, ask = offer
        dlg = wx.MessageDialog(
            self, ask, "File selezionato", wx.YES_NO | wx.ICON_QUESTION
        )
        if dlg.ShowModal() == wx.ID_YES:
            dlg.Destroy()
            _dispatch_cli_action(
                self, action, selected_path, None, selected_path, delay_ms=200
            )
        else:
            dlg.Destroy()

    def on_paste_path_from_clipboard(self, event=None):
        """Strumenti / Incolla… / Ctrl+Alt+V: file o path dagli Appunti → percorso."""
        paths = paths_from_windows_clipboard()
        if not paths:
            speak_accessible(
                "Negli Appunti non c’è un file o un percorso utilizzabile. "
                "In Esplora seleziona un file e premi Ctrl+C, oppure copia il percorso."
            )
            return
        # Un solo file → offerta apertura; più path → solo campo percorso
        if len(paths) == 1:
            self.apply_search_path(paths[0], offer_open=os.path.isfile(paths[0]))
        else:
            self.apply_search_path(paths, offer_open=False)

    def on_drop_files(self, event):
        """Compatibilità EVT_DROP_FILES (se presente); il path principale è FileDropTarget."""
        paths = []
        try:
            n = event.GetNumberOfFiles()
        except Exception:
            n = 0
        for i in range(n):
            try:
                p = event.GetFile(i)
            except Exception:
                p = ""
            if p:
                paths.append(p)
        self._apply_dropped_paths(paths)

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
        dest_dir = load_last_export_dir() or self.get_dynamic_desktop_path()
        if not dest_dir or not os.path.isdir(dest_dir):
            dest_dir = self.get_dynamic_desktop_path()
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
            logging.info(f"Auto-salvati {len(self.current_matches)} risultati in {path}")
            return path
        except Exception as e:
            logging.error(f"Errore auto-salvataggio risultati: {e}")
            return ""

    def on_export_results(self, event):
        if not self.current_matches:
            speak_accessible("Nessun risultato da esportare.")
            return
            
        wildcard_filters = "File di Testo (*.txt)|*.txt|Pagina Web HTML (*.html)|*.html|File CSV per Tabelle (*.csv)|*.csv"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_dir = load_last_export_dir() or self.get_dynamic_desktop_path()
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
                "Ctrl + + / Ctrl + - : velocità sintesi\n"
                "Ctrl + Shift + V : scegli voce SAPI\n"
                "Menu Voce : tono, prova voce, motore SAPI/NVDA\n"
                "CONTROL : Zittisce all'istante la lettura in corso\n"
                "Tasto APPLICAZIONI : Menu contestuale completo\n"
                "F1 : Apri la Guida HTML nel Browser\n"
                "ESC : annulla ricerca; non chiude (Alt+F4 / Ctrl+Q / Chiudi). Opzione in Strumenti.\n"
                "Alt+F4 / Ctrl+Q : chiudi applicazione\n"
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
        if event.AltDown() and key == wx.WXK_F4:
            self._stop_search = True
            self.Close()
            return
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
        """Verifica aggiornamenti SA dalla release app-v* (non Latest Add-on).

        Installer → solo Setup_Ricerca…; Portable → solo …_Portable_….
        """
        def _check():
            try:
                # Pulizia Setup/Portable già scaricati in updates\ (non in Download)
                cleanup_sa_update_downloads()
                if not silent:
                    speak_accessible("Verifica aggiornamenti in corso...")
                channel = detect_sa_install_channel()
                release = fetch_latest_standalone_release()
                if not release:
                    if not silent:
                        wx.CallAfter(
                            lambda: speak_accessible(
                                "Nessuna release Standalone trovata online."
                            )
                        )
                    return

                latest = release["version"]
                v_online = release.get("version_tuple") or _parse_version_tuple(latest)
                v_local = _parse_version_tuple(APP_VERSION)
                if v_online is None or v_local is None:
                    is_newer = latest != APP_VERSION
                else:
                    is_newer = v_online > v_local

                if not is_newer:
                    if not silent:
                        wx.CallAfter(lambda: speak_accessible("Versione aggiornata."))
                    return

                if channel == "installer":
                    exe_url = release.get("setup_url")
                    exe_name = release.get("setup_name") or (
                        f"Setup_RicercaTestualeAccessoDigitale_v{latest}.exe"
                    )
                    kind_lbl = "installer (Setup)"
                else:
                    exe_url = release.get("portable_url")
                    exe_name = release.get("portable_name") or (
                        f"RicercaTestualeAccessoDigitale_Portable_v{latest}.exe"
                    )
                    kind_lbl = "Portable"

                html_url = release.get("html_url") or GITHUB_REPO_URL
                logging.info(
                    f"Nuova versione SA {latest} (canale={channel}, asset={exe_name})"
                )

                def _prompt():
                    msg = (
                        f"Nuova versione {latest} disponibile!\n\n"
                        f"Questo PC usa la versione {kind_lbl}.\n"
                        f"Scarico e avvio {exe_name}?"
                    )
                    dlg = wx.MessageDialog(
                        self,
                        msg,
                        "Aggiornamento",
                        wx.YES_NO | wx.ICON_QUESTION,
                    )
                    if dlg.ShowModal() != wx.ID_YES:
                        dlg.Destroy()
                        return
                    dlg.Destroy()
                    if not exe_url:
                        speak_accessible(
                            f"File {kind_lbl} non trovato nella release. "
                            "Apro la pagina di download."
                        )
                        webbrowser.open(html_url)
                        return

                    def _dl():
                        try:
                            speak_accessible("Download in corso, attendere...")
                            updates = get_sa_updates_dir()
                            cleanup_sa_update_downloads()
                            out = os.path.join(updates, exe_name)
                            req2 = urllib.request.Request(
                                exe_url, headers={"User-Agent": "RTAD-Updater"}
                            )
                            with urllib.request.urlopen(req2, timeout=120) as resp, open(
                                out, "wb"
                            ) as f_out:
                                f_out.write(resp.read())
                            logging.info(
                                f"Download aggiornamento completato ({channel}): {out}"
                            )
                            speak_accessible("Avvio aggiornamento.")
                            subprocess.Popen([out])
                            # Non cancellare subito: Setup/Portable devono leggere l'exe.
                            # Cleanup al prossimo avvio / Verifica aggiornamenti.
                            wx.CallAfter(self.Close)
                        except Exception as e:
                            logging.error(f"Errore download aggiornamento: {e}")
                            wx.CallAfter(lambda: speak_accessible("Errore download."))

                    threading.Thread(target=_dl, daemon=True).start()

                wx.CallAfter(_prompt)
            except Exception as e:
                logging.warning(f"Impossibile verificare aggiornamenti: {e}")
                if not silent:
                    wx.CallAfter(
                        lambda: speak_accessible("Impossibile verificare connessione.")
                    )

        threading.Thread(target=_check, daemon=True).start()

    def on_find_other_copies(self, event=None):
        """Strumenti → Trova altre copie sul PC (elenco + consenso)."""
        if rtad_copie is None:
            speak_accessible("Modulo «Trova copie» non disponibile.")
            return
        speak_accessible("Cerco altre copie sul PC, un momento…")

        def _work():
            try:
                data = rtad_copie.scan_all()
                report = rtad_copie.build_report_text(
                    data.get("registry"), data.get("exes"), data.get("shortcuts")
                )
                safe = [
                    e["path"]
                    for e in (data.get("exes") or [])
                    if rtad_copie.is_safe_to_delete(e.get("path", ""))
                ]

                def _show():
                    dlg = FindCopiesDialog(self, report, safe_paths=safe)
                    dlg.ShowModal()
                    dlg.Destroy()

                wx.CallAfter(_show)
            except Exception as e:
                logging.error(f"Trova copie: {e}")
                wx.CallAfter(
                    lambda: speak_accessible("Errore durante la ricerca delle copie.")
                )

        threading.Thread(target=_work, daemon=True).start()

    def maybe_warn_other_copies(self):
        """All’avvio: avviso amichevole se sembrano esserci più copie confuse."""
        if rtad_copie is None:
            return
        if load_copies_tip_dismissed():
            return

        def _work():
            try:
                data = rtad_copie.scan_all()
                if not rtad_copie.looks_like_confusion(
                    data.get("registry") or [],
                    data.get("exes") or [],
                    data.get("shortcuts") or [],
                ):
                    return

                def _ask():
                    # Dialogo a 3 pulsanti in italiano (evita «Cancel» di Windows)
                    dlg = wx.Dialog(
                        self,
                        title="Più copie sul PC?",
                        style=wx.DEFAULT_DIALOG_STYLE,
                    )
                    vbox = wx.BoxSizer(wx.VERTICAL)
                    msg = (
                        "Sembra che sul PC ci siano più copie di "
                        "Ricerca Testuale Accesso Digitale "
                        "(per esempio Installer e anche un file in Download "
                        "o una Portable).\n\n"
                        "Questo può creare confusione: si apre una versione "
                        "vecchia oppure se ne aggiorna un’altra.\n\n"
                        "Vuoi aprire «Trova altre copie sul PC» per vedere "
                        "l’elenco e, se vuoi, ripulire con il tuo consenso?"
                    )
                    lbl = wx.StaticText(dlg, label=msg)
                    lbl.Wrap(480)
                    vbox.Add(lbl, 0, wx.ALL | wx.EXPAND, 12)
                    h = wx.BoxSizer(wx.HORIZONTAL)
                    btn_yes = wx.Button(dlg, wx.ID_YES, label="&Sì, apri")
                    btn_no = wx.Button(dlg, wx.ID_NO, label="&No, non ora")
                    btn_never = wx.Button(
                        dlg, wx.ID_CANCEL, label="Non &ricordare più"
                    )
                    btn_yes.SetDefault()
                    for b in (btn_yes, btn_no, btn_never):
                        h.Add(b, 0, wx.ALL, 5)
                    vbox.Add(h, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
                    dlg.SetSizerAndFit(vbox)
                    dlg.CentreOnParent()
                    btn_yes.Bind(
                        wx.EVT_BUTTON, lambda e: dlg.EndModal(wx.ID_YES)
                    )
                    btn_no.Bind(
                        wx.EVT_BUTTON, lambda e: dlg.EndModal(wx.ID_NO)
                    )
                    btn_never.Bind(
                        wx.EVT_BUTTON, lambda e: dlg.EndModal(wx.ID_CANCEL)
                    )
                    ans = dlg.ShowModal()
                    dlg.Destroy()
                    if ans == wx.ID_YES:
                        self.on_find_other_copies()
                    elif ans == wx.ID_CANCEL:
                        save_copies_tip_dismissed(True)
                        speak_accessible(
                            "Ok, non ripeterò questo avviso. "
                            "Lo trovi sempre in Strumenti."
                        )

                wx.CallAfter(_ask)
            except Exception as e:
                logging.debug(f"Avviso copie: {e}")

        threading.Thread(target=_work, daemon=True).start()

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
                speak_accessible(
                    "Questo URL non va nel percorso di ricerca. "
                    "Apro l'hub analisi audio/video."
                )
                self.open_media_hub_dialog(
                    initial_url=target_input, clear_source=True
                )
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
                speak_accessible(
                    "Nessun testo di ricerca: OCR completo sulle immagini del percorso. "
                    "Poi puoi usare Copia Testo o Salva Immagine sul risultato."
                )
            elif filter_mode in (1, 2, 3, 4):
                tipo = FILTER_MODE_LABELS[filter_mode] if filter_mode < len(FILTER_MODE_LABELS) else "tipo scelto"
                speak_accessible(
                    f"Nessun testo di ricerca: elenco dei file ({tipo}) "
                    f"nella cartella indicata. Poi puoi aprirli o analizzarli dal menu."
                )
            else:
                speak_accessible(
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
        # ChangeValue non genera EVT_TEXT: evita che on_filter_text svuoti
        # la lista e tolga il messaggio «Ricerca in corso…» (NVDA: «sconosciuto»).
        try:
            self.txt_filter.ChangeValue("")
        except Exception:
            try:
                self.txt_filter.SetValue("")
            except Exception:
                pass
        save_last_path(target_input)
        if query:
            add_query_to_history(query)
        add_path_to_history(target_input)
        self.update_history_menu()

        self.lst_results.Clear()
        
        # --- FIX NVDA SCONOSCIUTO ---
        self.lst_results.Append("Ricerca in corso... attendere prego.")
        
        self.file_map.clear()
        self.current_matches = []
        self.gauge.SetValue(0)
        status_start = "Ricerca in corso: 0%..."
        if include_ocr and not query and filter_mode in (0, 1):
            status_start = "OCR completo sulle immagini: 0%..."
        elif not query and filter_mode in (1, 2, 3, 4):
            status_start = "Elenco file per tipo: 0%..."
        elif include_ocr or include_visual:
            bits = []
            if include_ocr:
                bits.append("OCR")
            if include_visual:
                bits.append("visivo")
            status_start = f"Ricerca in corso ({'+'.join(bits)}): 0%..."
        self.txt_status_progress.SetValue(status_start)
        
        self.btn_search.Disable()
        self.btn_cancel.Enable()

        logging.info(
            f"Avvio ricerca. Testo: '{query or self.current_query}'. Tipo filtro: {filter_mode}. "
            f"OCR: {include_ocr}. Visivo: {include_visual}. ZIP: {include_zip}. Path: {target_input}"
        )
        if include_ocr and not query and filter_mode in (0, 1):
            speak_accessible("OCR completo avviato sulle immagini.")
        elif not query and filter_mode in (1, 2, 3, 4):
            speak_accessible("Elenco file per tipo avviato.")
        elif include_ocr or include_visual:
            extras = []
            if include_ocr:
                extras.append("OCR")
            if include_visual:
                extras.append("contenuto visivo")
            speak_accessible(
                f"Ricerca avviata per '{query}', con {' e '.join(extras)}."
            )
        else:
            speak_accessible(f"Ricerca avviata per '{query}'.")

        # --- INIZIO FEEDBACK ACUSTICO AVVIO ---
        threading.Thread(target=lambda: winsound.Beep(800, 150), daemon=True).start()
        # --- FINE FEEDBACK ACUSTICO ---

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
        # OCR senza query solo su «Tutti» o «Solo Immagini»
        ocr_dump_all = bool(include_ocr and not terms and filter_mode in (0, 1))
        # Elenco file del tipo scelto (senza leggere il contenuto)
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
                logging.warning(f"Percorso non trovato, saltato: {folder}")
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
                # Potatura anticipata: non scendere in cartelle di rumore (WinSxS, cache editor, …)
                dirs[:] = [
                    d for d in dirs
                    if not any(ign in os.path.join(root, d).lower() for ign in ignored)
                ]
                if any(ign in root.lower() for ign in ignored):
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
                        # OCR senza query su «Tutti i tipi»: solo immagini
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
                        speak_accessible,
                        f"Trovati {late_arrivals_count} file aggiunti durante la ricerca. Li esamino.",
                    )
                continue

            file_path = file_queue[queue_i]
            queue_i += 1
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
            file_date_label = format_file_date_label(mtime)
            file_date_suffix = f" {file_date_label}" if file_date_label else ""

            # Elenco per tipo: nessun testo da cercare, solo inventario filtrato
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
                    # Solo nome: file troppo grande, salta lettura contenuto
                    # (le caselle di posta non arrivano qui: content_scan_allowed=True)
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
                                    speak_accessible,
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
                            # Solo match visivo
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
                            "file_path": file_path, "file_name": file_name,
                            "prefix": prefix_img,
                            "mtime": mtime, "line_number": None, "paragraph_index": None,
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

                elif is_mbox and allow_content:
                    # Streaming From_: anche Inbox/Sent da centinaia di MB (niente tetto 40 MB)
                    box_msgs = 0
                    box_hits = 0
                    box_pdf_hits = 0
                    box_pdf_empty = 0
                    box_pdf_seen = 0
                    logging.info(
                        f"Casella posta: inizio scansione "
                        f"({safe_file_size(file_path)} byte): {file_path}"
                    )
                    try:
                        for msg_idx, msg in iter_mbox_like_messages(
                            file_path,
                            prefer_from_split=True,
                            should_abort=lambda: self._stop_search,
                        ):
                            if self._stop_search:
                                break
                            mail_messages_scanned += 1
                            box_msgs += 1
                            subject = decode_email_header(str(msg.get("subject", "")))
                            sender = decode_email_header(str(msg.get("from", "")))
                            msg_ts = message_date_timestamp(msg, fallback=mtime)
                            msg_found = False
                            date_label = format_email_date_label(msg, fallback_ts=msg_ts)
                            date_suffix = f" {date_label}" if date_label else ""
                            # Con filtro solo .pdf: non cercare in corpo/oggetto, solo allegati PDF
                            if not mail_pdf_only:
                                body = get_clean_email_text(msg)
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
                                            box_hits += 1
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
                                    msg_found = True
                                    box_hits += 1
                            # Allegati PDF: anche stub vuoti (IMAP non scaricato) → match sul nome;
                            # payload esterno Thunderbird; altrimenti testo grezzo/estratto.
                            if not msg_found:
                                for att_name, pdf_raw, att_meta in iter_pdf_attachments(msg):
                                    if self._stop_search:
                                        break
                                    box_pdf_seen += 1
                                    pdf_attachment_seen += 1
                                    if att_meta.get("empty"):
                                        pdf_attachment_empty += 1
                                        box_pdf_empty += 1
                                        if text_matches_terms(att_name, terms):
                                            raw_matches.append({
                                                "file_path": file_path, "file_name": file_name,
                                                "prefix": "[MBOX]", "mtime": msg_ts,
                                                "line_number": msg_idx, "paragraph_index": None,
                                                "location_info": f"Allegato PDF (non scaricato) Msg {msg_idx + 1}{date_suffix}",
                                                "snippet": f"nome allegato (corpo assente in locale): {att_name}",
                                                "viewer_text": _format_email_viewer_text(msg),
                                            })
                                            found_in_content = True
                                            msg_found = True
                                            pdf_attachment_hits += 1
                                            box_pdf_hits += 1
                                            box_hits += 1
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
                                        "file_path": file_path, "file_name": file_name,
                                        "prefix": "[MBOX]", "mtime": msg_ts,
                                        "line_number": msg_idx, "paragraph_index": None,
                                        "location_info": f"Allegato PDF Msg {msg_idx + 1}{date_suffix}",
                                        "snippet": f"{via}: {snip}",
                                        "viewer_text": _format_email_viewer_text(msg),
                                        "attachment_name": att_name or "allegato.pdf",
                                        "attachment_export_path": cached_pdf,
                                    })
                                    found_in_content = True
                                    msg_found = True
                                    pdf_attachment_hits += 1
                                    box_pdf_hits += 1
                                    box_hits += 1
                                    break
                    except Exception as e:
                        logging.debug(f"Errore lettura MBOX {file_path}: {e}")
                    logging.info(
                        f"Casella posta: fine {file_name} | messaggi={box_msgs} "
                        f"hit={box_hits} pdf_visti={box_pdf_seen} "
                        f"pdf_hit={box_pdf_hits} pdf_vuoti={box_pdf_empty} | {file_path}"
                    )

                elif ext == ".eml" and allow_content:
                    logging.debug(f"Scansione contenuto: {file_path}")
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

                    if not found_in_content:
                        for att_name, pdf_raw, att_meta in iter_pdf_attachments(msg):
                            pdf_attachment_seen += 1
                            if att_meta.get("empty"):
                                pdf_attachment_empty += 1
                                if text_matches_terms(att_name, terms):
                                    raw_matches.append({
                                        "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                        "mtime": msg_ts, "line_number": 1, "paragraph_index": None,
                                        "location_info": f"Allegato PDF (non scaricato) Email{date_suffix}",
                                        "snippet": f"nome allegato (corpo assente in locale): {att_name}",
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
                                "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                "mtime": msg_ts, "line_number": 1, "paragraph_index": None,
                                "location_info": f"Allegato PDF Email{date_suffix}",
                                "snippet": f"{via}: {snip}",
                                "attachment_name": att_name or "allegato.pdf",
                                "attachment_export_path": cached_pdf,
                            })
                            found_in_content = True
                            pdf_attachment_hits += 1
                            break

                elif (ext in TEXT_LIKE_EXTS or ext == custom_ext) and allow_content:
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
                            start_i, end_i = max(0, idx - 2), min(len(lines), idx + 3)
                            snippet = " ".join([l.strip() for l in lines[start_i:end_i]]).strip()
                            loc_info = f"Riga {idx + 1}{file_date_suffix}"
                            if use_glossary:
                                try:
                                    glossed_snip = rtad_media.apply_transcript_glossary(snippet)
                                    if glossed_snip != snippet:
                                        snippet = glossed_snip
                                        loc_info = (
                                            f"Riga {idx + 1} (glossario){file_date_suffix}"
                                        )
                                except Exception:
                                    pass
                            raw_matches.append({
                                "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                "mtime": mtime, "line_number": idx + 1, "paragraph_index": None,
                                "location_info": loc_info, "snippet": snippet,
                            })
                            found_in_content = True

                elif ext in [".docx", ".doc"] and allow_content:
                    logging.debug(f"Scansione contenuto: {file_path}")
                    magic = _read_file_magic(file_path, 4)
                    paragraphs = []
                    # .doc OLE: niente ZipFile (inutile e lento su USB); solo scansione binaria sotto
                    if ext == ".docx" or _is_ooxml_zip_magic(magic):
                        paragraphs, timed_out = run_with_timeout(
                            lambda: extract_paragraphs_from_docx(file_path),
                            FILE_CONTENT_SOFT_TIMEOUT_SEC,
                            default=[],
                        )
                        if timed_out:
                            logging.warning(
                                f"Timeout estrazione Word, salto contenuto: {file_path}"
                            )
                            paragraphs = []
                    for idx, p_text in enumerate(paragraphs):
                        if text_matches_terms(p_text, terms):
                            start_i, end_i = max(0, idx - 1), min(len(paragraphs), idx + 2)
                            snippet = " \n".join(paragraphs[start_i:end_i])
                            raw_matches.append({
                                "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                "mtime": mtime, "line_number": None, "paragraph_index": idx + 1,
                                "location_info": f"Paragrafo {idx + 1}{file_date_suffix}", "snippet": snippet,
                            })
                            found_in_content = True
                    if not found_in_content and ext == ".doc":
                        with open(file_path, "rb") as f:
                            raw_data = normalize_search_text(f.read(4194304).decode("latin1", errors="ignore"))
                            if text_matches_terms(raw_data, terms):
                                raw_matches.append({
                                    "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                    "mtime": mtime, "line_number": None, "paragraph_index": 1,
                                    "location_info": f"Documento Word{file_date_suffix}",
                                    "snippet": f"Testo nel file Word: '{query}'.",
                                })
                                found_in_content = True

                elif ext == ".xlsx" and allow_content:
                    logging.debug(f"Scansione Excel: {file_path}")
                    rows, timed_out = run_with_timeout(
                        lambda: extract_rows_from_xlsx(file_path),
                        FILE_CONTENT_SOFT_TIMEOUT_SEC,
                        default=[],
                    )
                    if timed_out:
                        logging.warning(
                            f"Timeout estrazione Excel, salto contenuto: {file_path}"
                        )
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
                    logging.debug(f"Scansione EPUB: {file_path}")
                    paragraphs, timed_out = run_with_timeout(
                        lambda: rtad_epub.extract_paragraphs_from_epub(file_path),
                        FILE_CONTENT_SOFT_TIMEOUT_SEC,
                        default=[],
                    )
                    if timed_out:
                        logging.warning(f"Timeout estrazione EPUB, salto contenuto: {file_path}")
                        paragraphs = []
                    for idx, p_text in enumerate(paragraphs):
                        if text_matches_terms(p_text, terms):
                            start_i, end_i = max(0, idx - 1), min(len(paragraphs), idx + 2)
                            snippet = " \n".join(paragraphs[start_i:end_i])
                            raw_matches.append({
                                "file_path": file_path, "file_name": file_name, "prefix": "[EPUB]",
                                "mtime": mtime, "line_number": None, "paragraph_index": idx + 1,
                                "location_info": f"Testo EPUB{file_date_suffix}",
                                "snippet": snippet,
                            })
                            found_in_content = True
                            break

                elif ext == ".zip" and include_zip and allow_content and rtad_zip is not None:
                    logging.debug(f"Scansione ZIP: {file_path}")
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
                        logging.warning(f"Timeout estrazione ZIP, salto contenuto: {file_path}")
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
                            "paragraph_index": None,
                            "location_info": f"{loc}{file_date_suffix}",
                            "snippet": snip,
                            "zip_member": member,
                        })
                        found_in_content = True

                elif ext == ".pdf" and allow_content:
                    logging.info(f"Scansione PDF: {file_path}")
                    try:
                        logging.getLogger().handlers[0].flush()
                    except Exception:
                        pass

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
                        logging.warning(f"Timeout estrazione PDF, salto contenuto: {file_path}")
                        pdf_doc_ts, pdf_lines = 0, []
                    else:
                        pdf_doc_ts, pdf_lines = pdf_result
                    # Ordinamento: data FILE (ricezione/salvataggio). Etichetta: file + eventuale data documento
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
                            start_i, end_i = max(0, idx - 1), min(len(pdf_lines), idx + 2)
                            snippet = " ".join(pdf_lines[start_i:end_i])
                            raw_matches.append({
                                "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                "mtime": sort_ts, "line_number": None, "paragraph_index": idx + 1,
                                "location_info": f"Testo PDF{date_suffix}",
                                "snippet": snippet,
                            })
                            found_in_content = True
                            pdf_hit = True
                            break
                    # Fallback: termini spezzati su più «righe» PDF → cerca nel testo intero
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
                                "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                "mtime": sort_ts, "line_number": None, "paragraph_index": 1,
                                "location_info": f"Testo PDF{date_suffix}",
                                "snippet": snippet[:200],
                            })
                            found_in_content = True
                            pdf_hit = True
                    if not pdf_hit and not pdf_lines and allow_content:
                        logging.debug(
                            f"PDF senza testo estraibile (scansione/protetto?): {file_path}"
                        )
                        # Fallback grezzo: molti PDF «immagine» o con font strani hanno comunque
                        # le stringhe ASCII nel file (OCR embedded, metadata, testo compresso male)
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
                                    "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                    "mtime": sort_ts, "line_number": None, "paragraph_index": 1,
                                    "location_info": f"Testo PDF{date_suffix}",
                                    "snippet": snip[:200],
                                })
                                found_in_content = True
                                pdf_hit = True
                        except Exception:
                            pass
                    # OCR Windows su PDF scansionati (pagine immagine) se opt-in e ancora nessun hit
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
                                    "file_path": file_path, "file_name": file_name,
                                    "prefix": "[PDF-OCR]",
                                    "mtime": sort_ts, "line_number": None, "paragraph_index": 1,
                                    "location_info": f"Testo OCR PDF{date_suffix}",
                                    "snippet": snip,
                                    "ocr_text": ocr_txt,
                                })
                                found_in_content = True
                                pdf_hit = True
                        elif not ocr_unavailable_announced:
                            ocr_unavailable_announced = True
                            wx.CallAfter(
                                speak_accessible,
                                rtad_ocr.engine_status_message(),
                            )
                    if name_matched and not found_in_content:
                        raw_matches.append({
                            "file_path": file_path, "file_name": file_name, "prefix": prefix,
                            "mtime": sort_ts, "line_number": None, "paragraph_index": None,
                            "location_info": f"Nome File{date_suffix}",
                            "snippet": f"Corrispondenza: '{file_name}'",
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
                        "file_path": file_path, "file_name": file_name, "prefix": prefix,
                        "mtime": mtime, "line_number": None, "paragraph_index": None,
                        "location_info": f"Nome File{file_date_suffix}",
                        "snippet": f"Corrispondenza: '{file_name}'",
                    }
                    # Match sul nome: se OCR era attivo e ha prodotto testo, allevalo
                    # così «Copia OCR» funziona anche quando la query non è nel testo immagine.
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

            except Exception as e:
                logging.debug(f"Salto file bloccato o corrotto durante scansione ({file_path}): {e}")

            bump_progress()
            # Cede il GIL ogni pochi file: UI e sintesi restano reattive su dischi lenti
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

    def on_filter_text(self, event):
        # Durante la ricerca i match non sono ancora in lista: non svuotare
        # il messaggio «Ricerca in corso…» (altrimenti NVDA dice «sconosciuto»).
        try:
            if not self.btn_search.IsEnabled():
                if event:
                    event.Skip()
                return
        except Exception:
            pass
        self.update_list_display()

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
        filter_text = self.txt_filter.GetValue().lower().strip()
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
                searchable_content = f"{display_str} {item.get('snippet', '')}".lower()
                if filter_text not in searchable_content:
                    continue
                    
            idx = self.lst_results.Append(display_str)
            self.file_map[idx] = item

        # Ricerca ancora in corso e nessun risultato in lista: tieni il messaggio
        # accessibile (evita lista vuota → NVDA «sconosciuto»).
        if searching and self.lst_results.GetCount() == 0:
            self.lst_results.Append("Ricerca in corso... attendere prego.")

    def update_progress(self, percent, current, total, matches, announce=False):
        self.gauge.SetValue(percent)
        text = f"Avanzamento: {percent}% ({current}/{total} file, {matches} risultati)"
        self.txt_status_progress.SetValue(text)
        # Annuncio automatico solo a 25/50/75: evita coda sintesi e UI «Non risponde»
        if announce or percent in (25, 50, 75):
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

        try:
            self._notify_search_end(matches, stopped=bool(self._stop_search))
        except Exception:
            pass

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
            speak_accessible(f"Ricerca annullata. Conservati {matches} risultati.{feed_speak}")
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
            logging.info(
                f"Ricerca completata. File esaminati: {self.scanned_count}. "
                f"Messaggi posta: {mail_msgs}. Allegati PDF visti: {pdf_att_seen}, "
                f"hit: {pdf_att_hits}, stub vuoti: {pdf_att_empty}. "
                f"Risultati: {matches}. Occorrenze grezze feed: {feed_raw}. "
                f"File grandi saltati (non posta): {skipped_large}. OCR: {ocr_stats}."
                f" Percorsi mancanti: {missing_targets}."
            )
            speak_accessible(
                f"Completata. Trovati {matches} risultati.{feed_speak}{saved_note}"
            )
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

    def on_open_file_event(self, event):
        self.open_selected_file()

    def open_selected_file(self):
        sel = self.lst_results.GetSelection()
        if sel != wx.NOT_FOUND and sel in self.file_map:
            item = self.file_map[sel]
            file_to_open = item["file_path"]
            line_num = item.get("line_number")
            ext = os.path.splitext(file_to_open)[1].lower()

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
                att_path = item.get("attachment_export_path") or ""
                if att_path and os.path.isfile(att_path):
                    att_label = item.get("attachment_name") or os.path.basename(att_path)
                    try:
                        ctypes.windll.shell32.ShellExecuteW(None, "open", att_path, None, None, 1)
                        speak_accessible(f"Apertura allegato PDF: {att_label}")
                    except Exception as e:
                        logging.error(f"Errore apertura allegato PDF {att_path}: {e}")
                        speak_accessible("Errore apertura allegato PDF.")
                    return
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

            if ext == ".eml" and item.get("attachment_export_path"):
                att_path = item.get("attachment_export_path") or ""
                if att_path and os.path.isfile(att_path):
                    att_label = item.get("attachment_name") or os.path.basename(att_path)
                    try:
                        ctypes.windll.shell32.ShellExecuteW(None, "open", att_path, None, None, 1)
                        speak_accessible(f"Apertura allegato PDF: {att_label}")
                    except Exception as e:
                        logging.error(f"Errore apertura allegato PDF {att_path}: {e}")
                        speak_accessible("Errore apertura allegato PDF.")
                    return

            if ext in [".docx", ".doc"]:
                para_idx = item.get("paragraph_index")
                snippet_to_find = item.get("snippet", "")
                speak_accessible(f"Apertura Word su {item.get('location_info', 'documento')}")
                open_word_at_paragraph(file_to_open, para_idx, snippet_to_find)
                return
            if ext == ".xlsx":
                loc = item.get("location_info") or "foglio Excel"
                sheet = (item.get("xlsx_sheet") or "").strip()
                row_n = item.get("line_number") or item.get("paragraph_index")
                speak_accessible(
                    f"Apertura Excel su {loc}: {os.path.basename(file_to_open)}"
                )
                open_excel_at_row(file_to_open, row_n, sheet)
                return
            if ext == ".eml":
                speak_accessible(f"Apertura email nel lettore interno: {os.path.basename(file_to_open)}")
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
                speak_accessible(
                    f"Apertura alla riga {line_num}: "
                    f"{os.path.basename(file_to_open)}.{gloss_note}"
                )
                jump_to_line_in_editor(file_to_open, line_num)
            else:
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "open", file_to_open, None, None, 1)
                    speak_accessible(
                        f"Apertura file: {os.path.basename(file_to_open)}.{gloss_note}"
                    )
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
        item_gemini = None
        if rtad_chat is not None and file_path and os.path.isfile(file_path):
            ext_g = os.path.splitext(file_path)[1].lower()
            chatable = (
                ext_g in IMG_EXTS
                or ext_g in MEDIA_EXTS
                or ext_g in SHELL_DOCUMENT_EXTS
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
                elif rtad_chat.has_saved(CONFIG_DIR, file_path):
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
        item_preview = menu.Append(wx.ID_ANY, "Ascolta Anteprima Vocale\tSPACE")
        item_copy_snippet = menu.Append(wx.ID_ANY, "Copia Blocco Notizia")
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
        is_shell_doc = ext_sel in SHELL_DOCUMENT_EXTS or is_pdf_result
        if is_shell_doc and not is_img_result:
            if not is_pdf_result:
                menu.AppendSeparator()
            item_read_doc = menu.Append(
                wx.ID_ANY, "Leggi documento (struttura e testo)"
            )
        item_copy_image = menu.Append(wx.ID_ANY, "Copia Immagine")
        item_save_image = menu.Append(wx.ID_ANY, "Salva Immagine...")
        if has_att:
            item_copy_to = menu.Append(wx.ID_ANY, "Copia allegato PDF altrove...")
        else:
            item_copy_to = menu.Append(wx.ID_ANY, "Copia File altrove...")
        item_open_folder = menu.Append(wx.ID_ANY, "Apri Cartella")

        menu.AppendSeparator()
        sort_submenu = wx.Menu()
        item_sort_recent = sort_submenu.Append(wx.ID_ANY, "Dal Più Recente")
        item_sort_oldest = sort_submenu.Append(wx.ID_ANY, "Dal Meno Recente")
        item_sort_name = sort_submenu.Append(wx.ID_ANY, "Alfabeticamente (A-Z)")
        menu.AppendSubMenu(sort_submenu, "Ordinamento")

        self.Bind(wx.EVT_MENU, lambda e: self.open_selected_file(), item_open)
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
        self.Bind(wx.EVT_MENU, lambda e: self.copy_path_to_clipboard(file_path), item_copy_path)
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

    def _ensure_image_api_keys(self):
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
                    speak_accessible(
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
            "include_timestamps": bool(sel.get("include_timestamps", False)),
        }
        url = (sel.get("url") or "").strip()
        path = (sel.get("file_path") or file_path or "").strip()
        if url:
            if rtad_media is None:
                speak_accessible("Modulo media non disponibile.")
                return
            if getattr(self, "_media_analysis_busy", False):
                speak_accessible(
                    "Analisi già in corso. Attendi il risultato, "
                    "poi potrai avviarne un'altra."
                )
                self.open_media_hub_dialog(
                    initial_url=url, preset_sections=self._last_media_sections
                )
                return
            speak_accessible("Download audio/video in corso…")
            self._set_media_progress(3, "Download audio/video…")

            def _work():
                res = rtad_media.materialize_media_from_url(
                    url, on_progress=self._media_progress_cb
                )
                if not res.get("ok") or not res.get("path"):
                    err = res.get("error") or "Download media non riuscito."

                    def _fail():
                        self._set_media_progress(0, err)
                        speak_accessible(err)
                        self.open_media_hub_dialog(
                            initial_url=url,
                            preset_sections=self._last_media_sections,
                        )

                    wx.CallAfter(_fail)
                    return
                wx.CallAfter(
                    self.show_media_analysis,
                    res["path"],
                    "all",
                    sel,
                    True,
                )

            threading.Thread(target=_work, daemon=True).start()
            return

        if not path or not os.path.isfile(path):
            speak_accessible("File audio/video non trovato.")
            self.open_media_hub_dialog(
                initial_url=url, preset_sections=self._last_media_sections
            )
            return
        if getattr(self, "_media_analysis_busy", False):
            speak_accessible(
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
            speak_accessible("Modulo media non disponibile.")
            return
        st = rtad_media.check_ytdlp_status()
        msg = st.get("message") or "Stato yt-dlp sconosciuto."
        buttons = wx.YES_NO | wx.CANCEL | wx.ICON_INFORMATION
        # Sì = aggiorna, No = solo ok, Annulla = chiudi
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
            speak_accessible(msg)
            return
        speak_accessible("Aggiornamento yt-dlp in corso…")

        def _work():
            res = rtad_media.update_ytdlp()
            wx.CallAfter(speak_accessible, res.get("message") or "Fatto.")

        threading.Thread(target=_work, daemon=True).start()

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
        # Annunci rare: evita coda sintesi durante upload lunghi
        key = msg.split("…")[0].split("(")[0].strip().lower()
        last = getattr(self, "_media_progress_announced", "")
        milestones = (
            "download",
            "scheda tecnica",
            "riassunto",
            "trascrizione",
            "upload file api",
            "analisi gemini",
            "ripresa trascrizione",
            "analisi audio/video completata",
            "download completato",
        )
        if key != last and any(m in key for m in milestones):
            self._media_progress_announced = key
            speak_accessible(f"{msg}, {pct} percento")

    def show_media_analysis(
        self, file_path, mode="describe", sections=None, delete_after=False
    ):
        """Scheda / riassunto / report completo su audio-video (UI o CLI)."""
        if not file_path or not os.path.isfile(file_path):
            speak_accessible("File audio/video non trovato.")
            return
        if rtad_media is None:
            speak_accessible("Modulo media non disponibile.")
            return
        if getattr(self, "_media_analysis_busy", False):
            speak_accessible(
                "Analisi audio/video già in corso. Attendi il risultato."
            )
            return
        self._media_analysis_busy = True
        self._media_analysis_gen = int(getattr(self, "_media_analysis_gen", 0) or 0) + 1
        gen = self._media_analysis_gen
        self._media_progress_announced = ""
        if isinstance(sections, dict):
            self._last_media_sections = {
                "include_tech": bool(sections.get("include_tech", True)),
                "include_describe": bool(sections.get("include_describe", True)),
                "include_transcript": bool(sections.get("include_transcript", False)),
                "include_timestamps": bool(sections.get("include_timestamps", False)),
            }
        self._ensure_image_api_keys()
        if mode in ("describe", "transcript", "all") and not load_gemini_api_key():
            if mode == "tech" or (
                mode == "all"
                and sections
                and sections.get("include_tech")
                and not sections.get("include_describe")
                and not sections.get("include_transcript")
            ):
                speak_accessible("Scheda tecnica audio/video in corso…")
            else:
                speak_accessible(
                    "Per riassunto o trascrizione serve la chiave Gemini "
                    "(Strumenti). Procedo comunque con le sezioni possibili."
                )
        else:
            speak_accessible("Analisi audio/video in corso…")
        self._set_media_progress(8, "Analisi audio/video…")

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
                    tr = rtad_media.transcribe_media_gemini(
                        file_path,
                        include_timestamps=bool(
                            (sections or {}).get("include_timestamps", False)
                        ),
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

            def _show():
                self._media_analysis_busy = False
                if gen != getattr(self, "_media_analysis_gen", 0):
                    return
                if not hasattr(self, "_image_info_frames") or self._image_info_frames is None:
                    self._image_info_frames = []
                # Solo pulsante esplicito: niente hub automatico (rubava focus dopo Avvia)
                want_hub = True
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
                        try:
                            rtad_media.cleanup_temp_media(path)
                        except Exception:
                            pass
                    evt.Skip()

                frm.Bind(wx.EVT_CLOSE, _cleanup_and_list)
                self._image_info_frames.append(frm)
                frm.Show()
                frm.Raise()
                speak_accessible(
                    "Report pronto. Per un altro URL: Nuova analisi."
                )

            wx.CallAfter(_show)

        threading.Thread(target=_work, daemon=True).start()

    def _reopen_media_hub_ready_for_next(self):
        """Hub di nuovo: stesse opzioni, sorgente vuota (nuovo URL)."""
        if getattr(self, "_media_hub_open", False):
            return
        if getattr(self, "_media_analysis_busy", False):
            speak_accessible(
                "Analisi ancora in corso. Attendi, poi Nuova analisi."
            )
            return
        speak_accessible(
            "Hub audio/video: stesse opzioni, incolla un nuovo URL oppure Annulla."
        )
        self.open_media_hub_dialog(
            initial_url="",
            preset_sections=getattr(self, "_last_media_sections", None),
            clear_source=True,
        )

    def on_media_from_url(self, event=None):
        """Scorciatoia → stesso hub, focus sul campo URL."""
        self.open_media_hub_dialog()

    def show_image_all_dialog(self, file_path):
        """Dialogo unico «Tutto sull'immagine» → subito analisi dopo Avvia."""
        if not file_path or not os.path.isfile(file_path):
            speak_accessible("File immagine non trovato.")
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
        # Solo OCR (percorso papà) → stessa finestra di --ocr-quick / menù Esplora
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
        """Strumenti → Tutto sull'immagine: file picker o risultato selezionato."""
        path = self._pick_image_path_for_tools()
        if path:
            self.show_image_all_dialog(path)

    def on_image_ocr_dialog(self, event=None):
        """Strumenti → Leggi testo nell'immagine (OCR) — stesso percorso Esplora."""
        path = self._pick_image_path_for_tools()
        if path:
            self.show_image_analysis(path, mode="ocr")

    def on_batch_images_folder(self, event=None, folder=None):
        """Strumenti / Explorer → Analizza cartella immagini (batch 1.6.6)."""
        if rtad_ocr is None:
            speak_accessible("Modulo immagini non disponibile.")
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
        """Strumenti / Explorer → Analizza cartella audio/video (batch 1.7.2)."""
        if rtad_media is None:
            speak_accessible("Modulo media non disponibile.")
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
            speak_accessible("Modulo media non disponibile.")
            return
        if getattr(self, "_media_analysis_busy", False):
            speak_accessible(
                "Analisi audio/video già in corso. Attendi il risultato."
            )
            return
        folder = os.path.abspath(folder or "")
        if not folder or not os.path.isdir(folder):
            speak_accessible("Cartella non trovata.")
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
            speak_accessible("Nessun file audio/video trovato in questa cartella.")
            return
        if sel.get("include_transcript") and len(files) >= 5:
            ask = wx.MessageDialog(
                self,
                (
                    f"Hai selezionato la trascrizione su {len(files)} file.\n"
                    "Può richiedere molto tempo e consumare quota Gemini.\n\n"
                    "Continuare?"
                ),
                "Conferma batch con trascrizione",
                wx.YES_NO | wx.ICON_WARNING,
            )
            choice = ask.ShowModal()
            ask.Destroy()
            if choice != wx.ID_YES:
                speak_accessible("Batch annullato.")
                return
        speak_accessible(
            f"Avvio analisi: {len(files)} file audio/video. "
            "Può richiedere tempo se usi Gemini."
        )
        self._ensure_image_api_keys()
        self._media_analysis_busy = True
        self._set_media_progress(2, "Batch audio/video…")

        def _work():
            def _prog(i, total, path, ok):
                name = os.path.basename(path)
                wx.CallAfter(
                    speak_accessible,
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
                    save_txt=sel.get("save_txt", True),
                    recursive=sel.get("recursive", False),
                    on_progress=_prog,
                )
            except Exception as e:
                summary = {"total": 0, "ok": 0, "results": [], "error": str(e)}

            lines = [
                f"Cartella: {folder}",
                f"File media trovati: {summary.get('total', 0)}",
                f"Completati: {summary.get('ok', 0)}",
            ]
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
                speak_accessible(
                    f"Batch terminato: {summary.get('ok', 0)} di "
                    f"{summary.get('total', 0)} completati."
                )

            wx.CallAfter(_show)

        threading.Thread(target=_work, daemon=True).start()

    def on_transcribe_and_search(self, event=None):
        """Strumenti → Trascrivi e cerca (B0 + Gemini solo senza sidecar)."""
        if rtad_media is None:
            speak_accessible("Modulo media non disponibile.")
            return
        if getattr(self, "_media_analysis_busy", False):
            speak_accessible(
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
            speak_accessible("Modulo media non disponibile.")
            return
        folder = os.path.abspath(folder or "")
        if not folder or not os.path.isdir(folder):
            speak_accessible("Cartella non trovata.")
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
            q_default = (self.txt_search.GetValue() or "").strip()
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
            speak_accessible("Serve almeno una parola da cercare.")
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
            speak_accessible(
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
                speak_accessible("Operazione annullata.")
                return
        self._ensure_image_api_keys()
        try:
            sync_transcript_glossary_to_media()
        except Exception:
            pass
        norm_query = normalize_search_text(query)
        terms = norm_query.split() if norm_query else []
        if not terms:
            speak_accessible("Serve almeno una parola da cercare.")
            return
        speak_accessible(
            f"Trascrivi e cerca: {len(files)} media, "
            f"{len(rtad_txts)} report testo. "
            "Può richiedere tempo se serve Gemini."
        )
        self._media_analysis_busy = True
        self._stop_search = False
        self._set_media_progress(2, "Trascrivi e cerca…")
        try:
            self.txt_search.SetValue(query)
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
                speak_accessible(" ".join(parts))
                if self.lst_results.GetCount() > 0:
                    self.lst_results.SetSelection(0)
                    self.lst_results.SetFocus()

            wx.CallAfter(_show)

        threading.Thread(target=_work, daemon=True).start()

    def start_batch_images_folder(self, folder):
        """Mostra sezioni (con conteggio) e avvia subito il batch."""
        if rtad_ocr is None:
            speak_accessible("Modulo immagini non disponibile.")
            return
        folder = os.path.abspath(folder or "")
        if not folder or not os.path.isdir(folder):
            speak_accessible("Cartella non trovata.")
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
            speak_accessible("Nessuna immagine trovata in questa cartella.")
            return
        speak_accessible(
            f"Avvio analisi: {len(files)} immagini. "
            "Può richiedere tempo se usi Gemini."
        )
        self._ensure_image_api_keys()

        def _work():
            def _prog(i, total, path, ok):
                name = os.path.basename(path)
                wx.CallAfter(
                    speak_accessible,
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
                speak_accessible(
                    f"Batch terminato: {summary.get('ok', 0)} di "
                    f"{summary.get('total', 0)} ok."
                )

            wx.CallAfter(_show)

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
        """Descrivi / etichette / scheda tecnica su un file immagine (UI o CLI).

        source_path: PDF/originale se file_path è un temp estratto (stem/cartella).
        """
        if not file_path or not os.path.isfile(file_path):
            speak_accessible("File immagine non trovato.")
            return
        if rtad_ocr is None:
            speak_accessible("Modulo immagini non disponibile.")
            return
        self._ensure_image_api_keys()
        src_path = (source_path or "").strip()

        if mode in ("describe", "copy-describe", "alt", "alt-long", "all") and not load_gemini_api_key():
            speak_accessible(
                "Descrizione avanzata: nessuna chiave Gemini. "
                "Uso etichette Vision se disponibili. "
                "Puoi aggiungere Gemini da Strumenti."
            )
        else:
            speak_accessible("Analisi immagine in corso…")

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
                        txt = (txt or "").strip()
                        if txt and hasattr(rtad_ocr, "ocr_text_for_clipboard"):
                            try:
                                # full = OCR completo ma già in orizzontale (reflow)
                                txt = (
                                    rtad_ocr.ocr_text_for_clipboard(txt, mode="full")
                                    or txt
                                )
                            except Exception:
                                pass
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
                        speak_accessible("Descrizione copiata negli appunti.")
                    else:
                        speak_accessible("Impossibile aprire gli appunti.")
                    if delete_after and rtad_ocr is not None:
                        rtad_ocr.cleanup_temp_image(file_path)
                    return
                # Riferimento forte: evita GC e resta aperta finché non la chiudi
                if not hasattr(self, "_image_info_frames") or self._image_info_frames is None:
                    self._image_info_frames = []
                frm = ImageInfoFrame(
                    None,
                    title,
                    body,
                    image_path=file_path,
                    source_path=src_path,
                )

                def _on_close(evt, frame=frm, path=file_path, do_del=delete_after):
                    try:
                        if frame in self._image_info_frames:
                            self._image_info_frames.remove(frame)
                    except Exception:
                        pass
                    if do_del and rtad_ocr is not None:
                        try:
                            rtad_ocr.cleanup_temp_image(path)
                        except Exception:
                            pass
                    evt.Skip()

                frm.Bind(wx.EVT_CLOSE, _on_close)
                self._image_info_frames.append(frm)
                frm.Show()
                frm.Raise()

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

    def prepare_shell_document(self, file_path, announce=True, open_external=True):
        """Explorer → Apri questo documento/PDF.

        1) Apre il file con l'app predefinita di Windows (es. Edge per PDF).
        2) Lo mette in lista risultati così NVDA non trova «sconosciuto»
           e dal menu contestuale si può Leggi/Copia testo, ecc.
        """
        if not file_path or not os.path.isfile(file_path):
            speak_accessible("File non trovato.")
            return False
        file_path = os.path.normpath(file_path)
        name = os.path.basename(file_path)
        ext = os.path.splitext(name)[1].lower()

        self.txt_path.SetValue(file_path)
        save_last_path(file_path)
        try:
            self.txt_filter.ChangeValue("")
        except Exception:
            try:
                self.txt_filter.SetValue("")
            except Exception:
                pass

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
        item = {
            "file_path": file_path,
            "file_name": name,
            "prefix": prefix,
            "mtime": mtime,
            "line_number": None,
            "paragraph_index": None,
            "location_info": f"Aperto da Explorer{date_suffix}",
            "snippet": f"Documento da sottomenù shell · {size_s}",
        }
        self.current_matches = [item]
        self.current_query = "(Documento da Explorer)"
        self.update_list_display()
        if self.lst_results.GetCount() > 0:
            self.lst_results.SetSelection(0)
            self.lst_results.SetFocus()

        opened_ok = False
        if open_external:
            try:
                ctypes.windll.shell32.ShellExecuteW(
                    None, "open", file_path, None, None, 1
                )
                opened_ok = True
            except Exception as e:
                logging.error(f"Apertura esterna fallita per {file_path}: {e}")
                try:
                    os.startfile(file_path)
                    opened_ok = True
                except Exception as e2:
                    logging.error(f"os.startfile fallito per {file_path}: {e2}")

        if announce:
            if opened_ok:
                speak_accessible(
                    f"Aperto «{name}» con l'app predefinita. "
                    f"Il file è anche in lista in Ricerca Testuale: "
                    f"menu contestuale per Leggi o Copia testo."
                )
            else:
                speak_accessible(
                    f"«{name}» è in lista. "
                    f"Apertura con app predefinita non riuscita; "
                    f"usa INVIO o il menu contestuale."
                )
        return True

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
            speak_accessible(
                "Lettore aperto senza testo. "
                "Puoi usare Strumenti → Descrivi immagine da PDF in qualsiasi momento."
            )
        else:
            speak_accessible(
                "Nessun testo estraibile. "
                "Usa Strumenti → Descrivi immagine da PDF."
            )

    def read_document_file(self, file_path):
        """Apre lettore strutturato (DOCX/EPUB/PDF) o testo piano (altro)."""
        if not file_path or not os.path.isfile(file_path):
            speak_accessible("File non trovato.")
            return
        name = os.path.basename(file_path)
        speak_accessible(f"Lettura di «{name}» in corso…")

        def _work():
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
                            speak_accessible,
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
                wx.CallAfter(speak_accessible, msg)
                return

            def _show():
                frame = ImageInfoFrame(
                    None,
                    title=f"Testo — {name}",
                    body_text=text,
                    image_path=file_path,
                )
                frame.Show()
                frame.Raise()

            wx.CallAfter(_show)

        threading.Thread(target=_work, daemon=True).start()

    def copy_document_text_file(self, file_path):
        """Copia negli appunti il testo estratto dal documento/PDF."""
        if not file_path or not os.path.isfile(file_path):
            speak_accessible("File non trovato.")
            return
        name = os.path.basename(file_path)
        speak_accessible(f"Estrazione testo da «{name}»…")

        def _work():
            text = extract_document_text(file_path)
            if not (text or "").strip():
                ext = os.path.splitext(file_path)[1].lower()
                if ext == ".pdf" and get_best_pdf_page_image(file_path):
                    msg = (
                        "PDF scansionato: nessun testo da copiare. "
                        "Usa «Descrivi immagini del PDF» o Copia Immagine dai risultati."
                    )
                else:
                    msg = "Nessun testo da copiare da questo file."
                wx.CallAfter(speak_accessible, msg)
                return

            def _copy():
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.TextDataObject(text))
                    wx.TheClipboard.Close()
                    speak_accessible("Testo del documento copiato negli appunti.")
                else:
                    speak_accessible("Impossibile aprire gli appunti.")

            wx.CallAfter(_copy)

        threading.Thread(target=_work, daemon=True).start()

    def describe_image_from_pdf(self, file_path, mode="describe"):
        """Estrae immagine dal PDF e avvia analisi (temp + delete_after).

        Passa source_path=PDF originale così «Salva testo» usa stem/cartella del PDF.
        """
        if not file_path or not os.path.isfile(file_path):
            speak_accessible("File PDF non trovato.")
            return
        speak_accessible("Estrazione immagine dal PDF…")
        pdf_path = os.path.normpath(file_path)

        def _work():
            tmp = self.materialize_pdf_image_temp(pdf_path)
            if not tmp:
                wx.CallAfter(
                    speak_accessible,
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
        """Chiede un URL immagine, lo scarica e avvia Descrivi (gemello Add-on)."""
        if rtad_ocr is None:
            speak_accessible("Modulo immagini non disponibile.")
            return
        dlg = wx.TextEntryDialog(
            self,
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
            speak_accessible("URL non inserito.")
            return
        speak_accessible("Download immagine in corso…")

        def _work():
            res = rtad_ocr.materialize_image_from_url(url)
            if not res.get("ok") or not res.get("path"):
                wx.CallAfter(
                    speak_accessible,
                    res.get("error") or "Download immagine non riuscito.",
                )
                return
            wx.CallAfter(
                self.show_image_analysis,
                res["path"],
                "describe",
                False,
                True,
            )

        threading.Thread(target=_work, daemon=True).start()

    def on_describe_from_clipboard(self, event=None):
        """Descrive un'immagine (o URL immagine) presente negli Appunti."""
        if rtad_ocr is None:
            speak_accessible("Modulo immagini non disponibile.")
            return
        path = ""
        delete_after = True
        try:
            if not wx.TheClipboard.Open():
                speak_accessible("Impossibile aprire gli appunti.")
                return
            try:
                # 1) Bitmap negli appunti
                if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
                    data = wx.BitmapDataObject()
                    if wx.TheClipboard.GetData(data):
                        bmp = data.GetBitmap()
                        if bmp and bmp.IsOk():
                            fd, path = tempfile.mkstemp(suffix=".png", prefix="rtad_clip_")
                            os.close(fd)
                            if not bmp.SaveFile(path, wx.BITMAP_TYPE_PNG):
                                path = ""
                # 2) File path negli appunti
                if not path and wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
                    fdo = wx.FileDataObject()
                    if wx.TheClipboard.GetData(fdo):
                        names = fdo.GetFilenames() or []
                        for cand in names:
                            if cand and os.path.isfile(cand) and rtad_ocr.is_image_path(cand):
                                path = cand
                                delete_after = False
                                break
                # 3) Testo = URL immagine
                url_text = ""
                if not path and wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                    tdo = wx.TextDataObject()
                    if wx.TheClipboard.GetData(tdo):
                        url_text = (tdo.GetText() or "").strip().strip('"').strip("'")
            finally:
                wx.TheClipboard.Close()
        except Exception as e:
            logging.error(f"Appunti immagine: {e}")
            speak_accessible("Lettura appunti non riuscita.")
            return

        if path and os.path.isfile(path):
            self.show_image_analysis(path, mode="describe", delete_after=delete_after)
            return
        if url_text and (
            rtad_ocr.is_likely_image_url(url_text)
            or url_text.lower().startswith("http://")
            or url_text.lower().startswith("https://")
        ):
            speak_accessible("Download immagine dall'URL negli appunti…")

            def _work():
                res = rtad_ocr.materialize_image_from_url(url_text)
                if not res.get("ok") or not res.get("path"):
                    wx.CallAfter(
                        speak_accessible,
                        res.get("error") or "Download immagine non riuscito.",
                    )
                    return
                wx.CallAfter(
                    self.show_image_analysis,
                    res["path"],
                    "describe",
                    False,
                    True,
                )

            threading.Thread(target=_work, daemon=True).start()
            return
        speak_accessible(
            "Nessuna immagine negli appunti. "
            "Copia un'immagine, un file immagine o un URL http, poi riprova."
        )

    def on_describe_from_screenshot(self, event=None):
        """Cattura l'intero schermo in temp e avvia Descrivi (gemello istantanea)."""
        if rtad_ocr is None:
            speak_accessible("Modulo immagini non disponibile.")
            return
        speak_accessible("Cattura schermo in corso…")
        try:
            screen = wx.ScreenDC()
            size = screen.GetSize()
            res = rtad_ocr.materialize_image_from_screen_rect(
                0, 0, int(size.width), int(size.height)
            )
        except Exception as e:
            logging.error(f"Cattura+descrivi: {e}")
            speak_accessible("Cattura schermo non riuscita.")
            return
        if not res.get("ok") or not res.get("path"):
            speak_accessible(res.get("error") or "Cattura schermo non riuscita.")
            return
        self.show_image_analysis(res["path"], mode="describe", delete_after=True)

    def change_sort_order(self, sort_type):
        self.sort_and_display_matches(sort_type)
        save_sort_preference(sort_type)
        if sort_type == "recent_first": speak_accessible("Ordinati dal più recente.")
        elif sort_type == "oldest_first": speak_accessible("Ordinati dal meno recente.")
        elif sort_type == "name": speak_accessible("Ordinati alfabeticamente.")

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
        if os.path.splitext(file_to_open)[1].lower() == ".eml":
            speak_accessible(f"Apertura email nel lettore interno: {os.path.basename(file_to_open)}")
            viewer = EmlViewerFrame(self, file_to_open, self.current_query)
            viewer.Show()

    def save_attachment_pdf(self, item_data):
        """Salva l'allegato PDF estratto in una cartella scelta dall'utente."""
        att_path = (item_data or {}).get("attachment_export_path") or ""
        if not att_path or not os.path.isfile(att_path):
            speak_accessible("Allegato PDF non disponibile per questo risultato.")
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
                speak_accessible(f"Allegato PDF salvato: {os.path.basename(dest)}")
            except Exception as e:
                logging.error(f"Errore salvataggio allegato PDF: {e}")
                speak_accessible("Errore nel salvataggio dell'allegato PDF.")
        dlg.Destroy()

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

    def copy_text_to_clipboard(self, item_data, mode="clean"):
        file_path = item_data["file_path"]
        ext = os.path.splitext(file_path)[1].lower()
        prefix = item_data.get("prefix", "")
        msg_index = item_data.get("line_number")
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
                        speak_accessible("OCR completo dell'immagine copiato negli appunti!")
                    else:
                        speak_accessible("Testo pulito dell'immagine copiato negli appunti!")
                else:
                    speak_accessible("Impossibile copiare il testo OCR negli appunti.")
                return
            speak_accessible(
                "Questo risultato è un’immagine: il match è sul nome file e "
                "l’OCR non ha restituito testo da copiare "
                "(grafica/loghi difficili, oppure cache vuota — prova Strumenti → Svuota cache OCR)."
            )
            return

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
                    speak_accessible(
                        "Questo PDF è una scansione: non c’è testo da copiare. "
                        "Usa «Copia Immagine» per la pagina grafica."
                    )
                else:
                    speak_accessible(
                        "Nessun testo estraibile con il nostro lettore "
                        "(font speciali o PDF protetto). "
                        "Prova «Copia Immagine» oppure Apri file "
                        "(Edge/NVDA spesso lo leggono)."
                    )
                return
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
            speak_accessible("Impossibile copiare il testo da questo formato.")

    def copy_image_to_clipboard(self, item_data):
        file_path = item_data["file_path"]
        ext = os.path.splitext(file_path)[1].lower()
        prefix = item_data.get("prefix", "")

        if prefix in ("[RSS]", "[FEED]", "[MBOX]", "[FEED-RIGA]"):
            speak_accessible("Nessuna immagine da copiare per questo risultato.")
            return

        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"]:
            try:
                img = rtad_ocr.load_wx_image_silent(file_path)
                if img is not None and img.IsOk() and wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.BitmapDataObject(wx.Bitmap(img)))
                    wx.TheClipboard.Close()
                    speak_accessible("Immagine copiata negli appunti!")
                    return
            except Exception as e:
                logging.warning(f"Errore copia immagine negli appunti: {e}")
            speak_accessible("Impossibile copiare l’immagine.")
            return

        if ext == ".pdf":
            speak_accessible("Estrazione immagine dal PDF in corso…")
            try:
                record = get_best_pdf_page_image(file_path)
                if record is None:
                    logos = extract_images_from_pdf(file_path)
                    if logos:
                        top = logos[0]
                        speak_accessible(
                            f"Trovato solo logo o icona "
                            f"({top['w']} per {top['h']} pixel), "
                            f"non una pagina intera. "
                            f"Prova «Copia Testo» oppure Apri file."
                        )
                    else:
                        speak_accessible(
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
                        speak_accessible(
                            f"Pagina grafica copiata negli appunti "
                            f"({img.GetWidth()} per {img.GetHeight()} pixel; "
                            f"originale {record['w']}×{record['h']})!"
                        )
                        return
            except Exception as e:
                logging.warning(f"Errore copia immagine PDF: {e}")
            speak_accessible(
                "Impossibile copiare l’immagine da questo PDF "
                "(file troppo grande o formato non supportato). "
                "Puoi usare «Copia File altrove» oppure Apri file."
            )
            return

        speak_accessible("Nessuna immagine da copiare in questo formato.")

    def save_image_to_file(self, item_data):
        file_path = item_data["file_path"]
        ext = os.path.splitext(file_path)[1].lower()
        prefix = item_data.get("prefix", "")
        base_name = os.path.splitext(os.path.basename(file_path))[0] or "immagine"

        if prefix in ("[RSS]", "[FEED]", "[MBOX]", "[FEED-RIGA]"):
            speak_accessible("Nessuna immagine da salvare per questo risultato.")
            return

        default_dir = self.get_dynamic_desktop_path()
        wildcard = (
            "JPEG (*.jpg)|*.jpg|"
            "PNG (*.png)|*.png|"
            "Bitmap (*.bmp)|*.bmp|"
            "Tutti i file (*.*)|*.*"
        )

        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"]:
            default_name = os.path.basename(file_path)
            dlg = wx.FileDialog(
                self,
                "Salva immagine",
                defaultDir=default_dir,
                defaultFile=default_name,
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
                speak_accessible(f"Immagine salvata in {dest}")
            except Exception as e:
                logging.warning(f"Errore salvataggio immagine: {e}")
                speak_accessible("Impossibile salvare l’immagine.")
            return

        if ext == ".pdf":
            speak_accessible("Estrazione immagine dal PDF in corso…")
            record = get_best_pdf_page_image(file_path)
            if record is None:
                logos = extract_images_from_pdf(file_path)
                if logos:
                    speak_accessible(
                        "Trovato solo logo o icona, non una pagina da salvare. "
                        "Prova «Copia Testo» oppure Apri file."
                    )
                else:
                    speak_accessible(
                        "Nessuna pagina grafica da salvare in questo PDF."
                    )
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
            # se l'utente non ha messo estensione, usa quella di default
            if not os.path.splitext(dest)[1]:
                dest = dest + default_ext
            if save_pdf_image_record_to_path(record, dest):
                speak_accessible(
                    f"Immagine salvata "
                    f"({record['w']} per {record['h']} pixel) in {dest}"
                )
            else:
                speak_accessible("Impossibile salvare l’immagine dal PDF.")
            return

        speak_accessible("Nessuna immagine da salvare in questo formato.")

    def copy_content_or_image_to_clipboard(self, item_data):
        """Compatibilità: preferisce testo; se PDF senza testo non tenta più l’immagine."""
        self.copy_text_to_clipboard(item_data)

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

def _parse_cli_image_action(argv):
    """Riconosce flag CLI immagini/documenti da Explorer.

    Restituisce (mode|None, path|None, rest_path_for_search|None, url|None).
    """
    mode = None
    path = None
    url = None
    flags = {
        "--describe": "describe",
        "--alt": "alt",
        "--alt-long": "alt-long",
        "--labels": "labels",
        "--tech": "tech",
        "--ocr-quick": "ocr",
        "--copy-describe": "copy-describe",
        "--describe-url": "describe-url",
        "--describe-pdf": "describe-pdf",
        "--image-all": "image-all",
        "--batch-folder": "batch-folder",
        "--batch-media-folder": "batch-media-folder",
        "--media-all": "media-all",
        "--media-tech": "media-tech",
        "--describe-media": "describe-media",
        "--transcribe-media": "transcribe-media",
        "--media-url": "media-url",
        "--read-doc": "read-doc",
        "--read-pdf": "read-doc",
        "--copy-doc-text": "copy-doc-text",
        "--copy-pdf-text": "copy-doc-text",
        "--open-doc": "open-doc",
        "--ask-gemini": "ask-gemini",
    }
    args = list(argv[1:]) if argv else []
    i = 0
    leftover = []
    while i < len(args):
        a = args[i]
        if a in flags:
            mode = flags[a]
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                if mode in ("describe-url", "media-url"):
                    url = args[i + 1]
                else:
                    path = args[i + 1]
                i += 2
                continue
            i += 1
            continue
        leftover.append(a)
        i += 1
    if path is None and leftover and mode not in ("describe-url", "media-url"):
        # Primo argomento esistente come path
        for cand in leftover:
            if os.path.exists(cand):
                path = cand
                break
    if url is None and mode in ("describe-url", "media-url") and leftover:
        url = leftover[0]
    return mode, path, leftover, url


RTAD_INSTANCE_MUTEX_NAME = "Local\\RTAD_Standalone_SingleInstance_v1"
RTAD_IPC_PATH = os.path.join(CONFIG_DIR, "shell_ipc.json")
_rtad_mutex_handle = None


def _acquire_primary_instance():
    """True se questa è l'istanza primaria (tiene il mutex)."""
    global _rtad_mutex_handle
    if sys.platform != "win32":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, RTAD_INSTANCE_MUTEX_NAME)
        if not handle:
            return True
        ERROR_ALREADY_EXISTS = 183
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False
        _rtad_mutex_handle = handle
        return True
    except Exception as e:
        logging.debug(f"Mutex istanza: {e}")
        return True


def _write_shell_ipc(payload):
    try:
        tmp = RTAD_IPC_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, RTAD_IPC_PATH)
        return True
    except Exception as e:
        logging.error(f"Scrittura IPC shell fallita: {e}")
        return False


def _read_shell_ipc():
    try:
        if not os.path.isfile(RTAD_IPC_PATH):
            return None
        with open(RTAD_IPC_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        try:
            os.remove(RTAD_IPC_PATH)
        except Exception:
            pass
        return data if isinstance(data, dict) else None
    except Exception as e:
        logging.debug(f"Lettura IPC shell: {e}")
        try:
            os.remove(RTAD_IPC_PATH)
        except Exception:
            pass
        return None


def _resolve_cli_from_argv(argv):
    """Parse argv + auto-tipo file (1.7.4) → mode, path, leftover, url, path_for_search."""
    cli_mode, cli_path, leftover, cli_url = _parse_cli_image_action(argv)
    path_for_search = None
    if cli_path and os.path.exists(cli_path):
        path_for_search = cli_path
    elif leftover:
        for cand in leftover:
            if os.path.exists(cand):
                path_for_search = cand
                break
    if not cli_mode and path_for_search and os.path.isfile(path_for_search):
        ext_auto = os.path.splitext(path_for_search)[1].lower()
        if ext_auto in IMG_EXTS:
            cli_mode = "image-all"
            cli_path = path_for_search
        elif ext_auto in MEDIA_EXTS:
            cli_mode = "media-all"
            cli_path = path_for_search
        elif ext_auto in SHELL_DOCUMENT_EXTS:
            cli_mode = "open-doc"
            cli_path = path_for_search
    return cli_mode, cli_path, leftover, cli_url, path_for_search


def _dispatch_cli_action(frame, cli_mode, cli_path, cli_url, path_for_search, delay_ms=400):
    """Esegue l'azione shell/CLI sulla finestra principale (anche da IPC)."""
    try:
        frame.Show()
        frame.Raise()
        try:
            frame.Iconize(False)
        except Exception:
            pass
    except Exception:
        pass

    doc_cli = cli_mode in (
        "read-doc",
        "copy-doc-text",
        "open-doc",
        "describe-pdf",
        "batch-folder",
        "batch-media-folder",
        "image-all",
        "media-all",
        "media-tech",
        "describe-media",
        "transcribe-media",
        "media-url",
        "ask-gemini",
    )
    if path_for_search and not doc_cli:
        if os.path.isfile(path_for_search):
            ext = os.path.splitext(path_for_search)[1].lower()
            if ext in SHELL_DOCUMENT_EXTS:
                frame.txt_path.SetValue(path_for_search)
            else:
                frame.txt_path.SetValue(
                    os.path.dirname(path_for_search) or path_for_search
                )
        else:
            frame.txt_path.SetValue(path_for_search)
        save_last_path(frame.txt_path.GetValue())

    def _later(fn):
        wx.CallLater(delay_ms, fn)

    if cli_mode == "batch-folder" and cli_path and os.path.isdir(cli_path):
        frame.txt_path.SetValue(cli_path)
        save_last_path(cli_path)
        _later(lambda: frame.start_batch_images_folder(cli_path))
    elif cli_mode == "batch-media-folder" and cli_path and os.path.isdir(cli_path):
        frame.txt_path.SetValue(cli_path)
        save_last_path(cli_path)
        _later(lambda: frame.start_batch_media_folder(cli_path))
    elif cli_mode == "image-all" and cli_path and os.path.isfile(cli_path):
        frame.txt_path.SetValue(os.path.dirname(cli_path) or cli_path)
        save_last_path(frame.txt_path.GetValue())
        _later(lambda: frame.show_image_all_dialog(cli_path))
    elif cli_mode == "media-all" and cli_path and os.path.isfile(cli_path):
        frame.txt_path.SetValue(os.path.dirname(cli_path) or cli_path)
        save_last_path(frame.txt_path.GetValue())
        _later(lambda: frame.show_media_all_dialog(cli_path))
    elif cli_mode == "media-tech" and cli_path and os.path.isfile(cli_path):
        frame.txt_path.SetValue(os.path.dirname(cli_path) or cli_path)
        save_last_path(frame.txt_path.GetValue())
        _later(lambda: frame.show_media_analysis(cli_path, mode="tech"))
    elif cli_mode == "describe-media" and cli_path and os.path.isfile(cli_path):
        frame.txt_path.SetValue(os.path.dirname(cli_path) or cli_path)
        save_last_path(frame.txt_path.GetValue())
        _later(lambda: frame.show_media_analysis(cli_path, mode="describe"))
    elif cli_mode == "transcribe-media" and cli_path and os.path.isfile(cli_path):
        frame.txt_path.SetValue(os.path.dirname(cli_path) or cli_path)
        save_last_path(frame.txt_path.GetValue())
        _later(lambda: frame.show_media_analysis(cli_path, mode="transcript"))
    elif cli_mode == "describe-url" and cli_url:
        def _cli_url():
            if rtad_ocr is None:
                speak_accessible("Modulo immagini non disponibile.")
                return
            speak_accessible("Download immagine in corso…")

            def _work():
                res = rtad_ocr.materialize_image_from_url(cli_url)
                if not res.get("ok") or not res.get("path"):
                    wx.CallAfter(
                        speak_accessible,
                        res.get("error") or "Download immagine non riuscito.",
                    )
                    return
                wx.CallAfter(
                    frame.show_image_analysis,
                    res["path"],
                    "describe",
                    False,
                    True,
                )

            threading.Thread(target=_work, daemon=True).start()

        _later(_cli_url)
    elif cli_mode == "media-url" and cli_url:
        def _cli_media_url():
            if rtad_media is None:
                speak_accessible("Modulo media non disponibile.")
                return
            speak_accessible("Download audio/video in corso…")

            def _work():
                res = rtad_media.materialize_media_from_url(cli_url)
                if not res.get("ok") or not res.get("path"):
                    wx.CallAfter(
                        speak_accessible,
                        res.get("error") or "Download media non riuscito.",
                    )
                    return
                wx.CallAfter(frame.show_media_all_dialog, res["path"], True)

            threading.Thread(target=_work, daemon=True).start()

        _later(_cli_media_url)
    elif cli_mode == "open-doc" and cli_path and os.path.isfile(cli_path):
        _later(lambda: frame.prepare_shell_document(cli_path, announce=True))
    elif cli_mode == "read-doc" and cli_path and os.path.isfile(cli_path):
        _later(lambda: frame.read_document_file(cli_path))
    elif cli_mode == "copy-doc-text" and cli_path and os.path.isfile(cli_path):
        _later(lambda: frame.copy_document_text_file(cli_path))
    elif cli_mode == "describe-pdf" and cli_path and os.path.isfile(cli_path):
        _later(lambda: frame.describe_image_from_pdf(cli_path, mode="describe"))
    elif cli_mode == "ask-gemini" and cli_path and os.path.isfile(cli_path):
        def _ask_gemini(path=cli_path):
            ext = os.path.splitext(path)[1].lower()
            if ext in IMG_EXTS:
                open_gemini_chat("image", path, parent=frame)
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
                    parent=frame,
                )
                return
            open_gemini_chat("document", path, parent=frame)

        _later(_ask_gemini)
    elif cli_mode and cli_path and os.path.isfile(cli_path):
        mode = "describe" if cli_mode == "copy-describe" else cli_mode
        copy_only = cli_mode == "copy-describe"
        _later(
            lambda: frame.show_image_analysis(
                cli_path, mode=mode, copy_only=copy_only
            )
        )
    else:
        # Solo porta in primo piano (secondo click su scorciatoia / Explorer cartella)
        try:
            frame.txt_query.SetFocus()
        except Exception:
            pass
        if path_for_search and os.path.isdir(path_for_search):
            frame.txt_path.SetValue(path_for_search)
            save_last_path(path_for_search)


def main():
    try:
        ensure_rtad_app_user_model_id()
    except Exception:
        pass

    cli_mode, cli_path, leftover, cli_url, path_for_search = _resolve_cli_from_argv(
        sys.argv
    )

    # Seconda istanza (Explorer / scorciatoia): inoltra all'istanza già aperta
    if not _acquire_primary_instance():
        payload = {
            "argv": list(sys.argv),
            "mode": cli_mode,
            "path": cli_path,
            "url": cli_url,
            "path_for_search": path_for_search,
        }
        if _write_shell_ipc(payload):
            logging.info("Comando shell inoltrato all'istanza già aperta.")
        else:
            logging.warning("Impossibile inoltrare comando all'istanza aperta.")
        return

    app = wx.App(False)
    frame = MainWindow()
    frame.Show()
    frame.Raise()
    frame.txt_query.SetFocus()
    wx.CallLater(1200, frame.on_check_updates, None, True)
    # Avviso amichevole se sembrano esserci più copie (dopo WhatsNew / update)
    wx.CallLater(3500, frame.maybe_warn_other_copies)

    _dispatch_cli_action(
        frame, cli_mode, cli_path, cli_url, path_for_search, delay_ms=400
    )

    def _poll_ipc(_evt=None):
        data = _read_shell_ipc()
        if not data:
            return
        argv = data.get("argv") or [sys.argv[0]]
        m, p, _leftover, u, pfs = _resolve_cli_from_argv(argv)
        if data.get("mode") and not m:
            m = data.get("mode")
            p = data.get("path") or p
            u = data.get("url") or u
            pfs = data.get("path_for_search") or pfs
        logging.info(f"IPC shell ricevuto: mode={m} path={p}")
        _dispatch_cli_action(frame, m, p, u, pfs, delay_ms=200)

    try:
        frame._ipc_timer = wx.Timer(frame)
        frame.Bind(wx.EVT_TIMER, _poll_ipc, frame._ipc_timer)
        frame._ipc_timer.Start(400)
    except Exception as e:
        logging.debug(f"Timer IPC non avviato: {e}")

    app.MainLoop()

if __name__ == "__main__":
    main()
