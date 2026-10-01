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
    import rtad_guida_pratica
except ImportError:
    rtad_guida_pratica = None

try:
    import rtad_epub
except ImportError:
    rtad_epub = None

APP_TITLE = "Ricerca Testuale Accesso Digitale"
APP_VERSION = "1.5.9"
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
OCR_CACHE_DIR = os.path.join(CONFIG_DIR, "ocr_cache")

if rtad_ocr is not None:
    try:
        rtad_ocr.configure(OCR_CACHE_DIR)
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
        try:
            tokens = v.GetVoices()
            for i in range(int(tokens.Count)):
                tok = tokens.Item(i)
                if str(tok.Id) == str(_speech_voice_id):
                    v.Voice = tok
                    break
        except Exception as e:
            logging.debug(f"Impostazione voce SAPI fallita: {e}")
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
        <p><strong>Novit&agrave; Versione 1.5.9</strong></p>
        <ul>
            <li><strong>Guida pratica</strong> (menu Aiuto): linguaggio semplice; aggiornata a ogni release.</li>
            <li>Ricerca nei libri <strong>EPUB</strong> (<code>.epub</code>), risultati <code>[EPUB]</code>.</li>
            <li>Restano OCR 1.5.8, voce 1.5.7, posta 1.5.6, profili e filtri.</li>
        </ul>
        <p><code>F7</code>: Mute &middot; OCR: casella + Motore OCR &middot; Aiuto &rarr; Guida pratica.</p>
    </div>
    <h2>Formati supportati</h2>
    <ul>
        <li>Testo (<code>.txt</code>, <code>.log</code>, <code>.csv</code>), Word, PDF, EPUB, EML/MBOX, Feed RSS/Atom/Thunderbird, immagini con OCR di base.</li>
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
        <li><code>INVIO</code> nel campo testo: avvia la ricerca.</li>
        <li><code>Alt + N</code>: annulla ricerca e mantieni i risultati.</li>
        <li><code>Alt + I</code>: info versione e autore.</li>
        <li><code>Alt + P</code>: annuncia lo stato (due volte = copia negli appunti).</li>
        <li><code>TAB</code> / <code>Alt+S</code> / <code>S</code>: campo accessibile di stato/avanzamento.</li>
        <li><code>Alt + K</code>: screenshot in <em>Catture di schermata</em>.</li>
        <li><code>Ctrl + P</code>: stampa risultati in lista.</li>
        <li><code>Ctrl + D</code>: aggiungi percorso ai segnalibri.</li>
        <li><code>Ctrl + Shift + P</code>: Salva profilo di ricerca attuale.</li>
        <li><code>Ctrl + Shift + L</code>: Carica un profilo di ricerca.</li>
        <li><code>SPAZIO</code> / <code>F4</code>: anteprima vocale del contesto.</li>
        <li><code>F7</code>: attiva / disattiva sintesi vocale (Mute).</li>
        <li><code>Ctrl + +</code> / <code>Ctrl + -</code>: velocit&agrave; sintesi pi&ugrave; rapida / pi&ugrave; lenta.</li>
        <li><code>Ctrl + Shift + V</code>: scegli voce SAPI.</li>
        <li>Menu <code>Voce</code>: tono, prova voce, motore SAPI/NVDA.</li>
        <li><code>CONTROL</code>: zittisce all'istante la lettura in corso.</li>
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


def _pdf_parse_tounicode_cmaps(raw: bytes, deadline=None) -> dict:
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
            # Solo se non è già CMap in chiaro: evita inflate inutili su stream grezzi
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


def load_ocr_engine_preference():
    """'windows' (default) oppure 'easyocr'."""
    data = _load_settings_dict()
    eng = str(data.get("ocr_engine", "windows") or "windows").strip().lower()
    if eng not in ("windows", "easyocr"):
        eng = "windows"
    return eng


def save_ocr_engine_preference(engine):
    eng = str(engine or "windows").strip().lower()
    if eng not in ("windows", "easyocr"):
        eng = "windows"
    data = _load_settings_dict()
    data["ocr_engine"] = eng
    _save_settings_dict(data)
    if rtad_ocr is not None:
        try:
            rtad_ocr.set_engine_preference(eng)
        except Exception:
            pass


def load_escape_closes_preference():
    """False di default: Esc non chiude la finestra principale (solo annulla ricerca)."""
    data = _load_settings_dict()
    return bool(data.get("escape_closes_app", False))


def save_escape_closes_preference(enabled):
    data = _load_settings_dict()
    data["escape_closes_app"] = bool(enabled)
    _save_settings_dict(data)


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
            "• Guida pratica (menu Aiuto): spiega il programma in linguaggio\n"
            "  semplice; a ogni versione le novità sono aggiornate lì.\n"
            "• Ricerca nei libri EPUB (.epub): testo dei capitoli, risultati [EPUB].\n"
            "• Restano OCR 1.5.8, voce 1.5.7, posta 1.5.6, profili e filtri.\n"
            "--------------------------------------------------\n"
            "Grazie per usare Ricerca Testuale Accesso Digitale!\n"
        )

        lbl_info = wx.StaticText(panel, label="Leggi le novità dell'ultimo aggiornamento:")
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
            "  - Alt + T : Seleziona TUTTO IL PC (tutte le unità attive)\n"            "  - INVIO nel campo testo : Avvia ricerca\n"
            "  - Alt + N : Annulla ricerca in corso e mantieni i risultati\n"
            "  - Alt + I : Info Versione e Autore\n"
            "  - Alt + P : Annuncia stato (Premi due volte velocemente per copiare negli appunti)\n"
            "  - TAB oppure Alt+S / S : Raggiunge la casella 'Stato avanzamento'\n"
            "  - Alt + K : Scatta uno screenshot salvato in 'Catture di schermata'\n"
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
            "  - F1 : Apri la Guida HTML nel Browser\n"
            "  - ESC : annulla ricerca in corso; non chiude (usa Alt+F4 / Ctrl+Q). Opzione in Strumenti.\n"
            "  - Alt+F4 / Ctrl+Q / Chiudi : esci dall'applicazione\n\n"
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
        self.txt_custom_ext = wx.TextCtrl(panel, value="")
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

        hbox_ocr_eng = wx.BoxSizer(wx.HORIZONTAL)
        lbl_ocr_eng = wx.StaticText(panel, label="Motore OCR:")
        hbox_ocr_eng.Add(lbl_ocr_eng, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.choice_ocr_engine = wx.Choice(
            panel,
            choices=[
                "Windows (predefinito, incluso)",
                "EasyOCR (opzionale: pip install -r requirements-ocr-easy.txt)",
            ],
        )
        self.choice_ocr_engine.SetName("Motore OCR")
        try:
            eng = load_ocr_engine_preference()
        except Exception:
            eng = "windows"
        self.choice_ocr_engine.SetSelection(1 if eng == "easyocr" else 0)
        if rtad_ocr is not None:
            try:
                rtad_ocr.set_engine_preference(eng)
            except Exception:
                pass
        self.choice_ocr_engine.Bind(wx.EVT_CHOICE, self.on_ocr_engine_choice)
        hbox_ocr_eng.Add(self.choice_ocr_engine, 1, wx.EXPAND)
        vbox.Add(hbox_ocr_eng, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        hbox_actions = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_search = wx.Button(panel, label="Avvia Ricerca")
        self.btn_search.Bind(wx.EVT_BUTTON, lambda e: self.start_search_thread())
        hbox_actions.Add(self.btn_search, 0, wx.ALL, 5)

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
        item_test_voice = voice_menu.Append(wx.ID_ANY, "&Prova voce")
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
        tools_menu.AppendSeparator()
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
            "ocr_engine": (
                "easyocr"
                if getattr(self, "choice_ocr_engine", None)
                and self.choice_ocr_engine.GetSelection() == 1
                else "windows"
            ),
            "query": self.txt_query.GetValue().strip(),
        }

    def on_ocr_engine_choice(self, event=None):
        eng = (
            "easyocr"
            if self.choice_ocr_engine.GetSelection() == 1
            else "windows"
        )
        try:
            save_ocr_engine_preference(eng)
        except Exception:
            pass
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
                eng = (
                    "easyocr"
                    if self.choice_ocr_engine.GetSelection() == 1
                    else "windows"
                )
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
        eng = str(profile.get("ocr_engine", "windows") or "windows").strip().lower()
        if eng not in ("windows", "easyocr"):
            eng = "windows"
        try:
            self.choice_ocr_engine.SetSelection(1 if eng == "easyocr" else 0)
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
        elif alt and key in (ord("K"), ord("k")):
            self.on_take_screenshot(None)
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
        names = [v["name"] for v in voices]
        # Preseleziona voce corrente
        sel = 0
        if _speech_voice_id:
            for i, v in enumerate(voices):
                if v["id"] == _speech_voice_id:
                    sel = i
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
            if 0 <= idx < len(voices):
                set_speech_voice_id(voices[idx]["id"])
                set_speech_use_sapi(True)
                try:
                    if self.item_engine_sapi:
                        self.item_engine_sapi.Check(True)
                except Exception:
                    pass
                speak_accessible(f"Voce impostata: {voices[idx]['name']}.", force=True)
        dlg.Destroy()

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
        include_ocr = bool(self.chk_ocr.GetValue())
        try:
            save_include_ocr_preference(include_ocr)
        except Exception:
            pass
        try:
            eng = (
                "easyocr"
                if self.choice_ocr_engine.GetSelection() == 1
                else "windows"
            )
            save_ocr_engine_preference(eng)
        except Exception:
            pass

        if not query:
            if include_ocr:
                speak_accessible(
                    "Nessun testo di ricerca: OCR completo sulle immagini del percorso. "
                    "Poi puoi usare Copia Testo o Salva Immagine sul risultato."
                )
            else:
                speak_accessible(
                    "Inserire un testo da cercare, oppure attiva OCR per leggere "
                    "tutte le immagini senza parola chiave."
                )
                return

        self._stop_search = False
        self.current_query = query or "(OCR completo)"
        self.current_percent = 0
        self.scanned_count = 0
        self.live_matches_count = 0
        self.last_feed_raw_occurrences = 0
        self.txt_filter.SetValue("")
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
        if include_ocr and not query:
            status_start = "OCR completo sulle immagini: 0%..."
        elif include_ocr:
            status_start = "Ricerca in corso (OCR attivo): 0%..."
        self.txt_status_progress.SetValue(status_start)
        
        self.btn_search.Disable()
        self.btn_cancel.Enable()

        logging.info(
            f"Avvio ricerca. Testo: '{query or '(OCR completo)'}'. Tipo filtro: {filter_mode}. "
            f"OCR: {include_ocr}. Path: {target_input}"
        )
        if include_ocr and not query:
            speak_accessible("OCR completo avviato sulle immagini.")
        elif include_ocr:
            speak_accessible(f"Ricerca avviata per '{query}', con OCR.")
        else:
            speak_accessible(f"Ricerca avviata per '{query}'.")

        # --- INIZIO FEEDBACK ACUSTICO AVVIO ---
        threading.Thread(target=lambda: winsound.Beep(800, 150), daemon=True).start()
        # --- FINE FEEDBACK ACUSTICO ---

        targets = normalize_search_targets(target_input)
        threading.Thread(
            target=self.run_search,
            args=(query, targets, filter_mode, custom_ext, include_feed_raw, include_ocr),
            daemon=True,
        ).start()

    def run_search(self, query, targets, filter_mode, custom_ext, include_feed_raw=False, include_ocr=False):
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
        ocr_dump_all = bool(include_ocr and not terms)
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

                    if filter_mode == 1 and ext not in img_exts:
                        continue
                    elif ocr_dump_all and ext not in img_exts:
                        # OCR senza query: solo immagini
                        continue
                    elif filter_mode == 2 and ext not in media_exts:
                        continue
                    elif filter_mode == 3 and ext not in doc_exts and not is_tb:
                        continue
                    elif filter_mode == 4 and ext != custom_ext and not mail_for_pdf:
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
            file_date_label = format_file_date_label(mtime)
            file_date_suffix = f" {file_date_label}" if file_date_label else ""

            try:
                name_matched = text_matches_terms(file_name, terms)
                found_in_content = False
                allow_content = content_scan_allowed(file_path)
                if not allow_content and not name_matched:
                    # Solo nome: file troppo grande, salta lettura contenuto
                    # (le caselle di posta non arrivano qui: content_scan_allowed=True)
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
                            ocr_match = False
                            if ocr_dump_all:
                                # Senza parola chiave: elenca ogni immagine con testo OCR
                                ocr_match = bool((img_text or "").strip())
                            else:
                                try:
                                    ocr_match = rtad_ocr.ocr_text_matches_terms(img_text, terms)
                                except Exception:
                                    ocr_match = text_matches_terms(img_text, terms)
                            if ocr_match:
                                if ocr_dump_all:
                                    try:
                                        snip = rtad_ocr.ocr_text_for_clipboard(img_text) or img_text
                                    except Exception:
                                        snip = img_text
                                    snip = " ".join((snip or "").split())[:200] or file_name
                                else:
                                    snip = rtad_ocr.snippet_from_ocr_text(img_text, terms) or query
                                raw_matches.append({
                                    "file_path": file_path, "file_name": file_name,
                                    "prefix": "[IMG-OCR]",
                                    "mtime": mtime, "line_number": None, "paragraph_index": None,
                                    "location_info": (
                                        f"OCR completo{file_date_suffix}"
                                        if ocr_dump_all
                                        else f"Testo OCR{file_date_suffix}"
                                    ),
                                    "snippet": snip,
                                    "ocr_text": img_text,
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
                    for idx, line in enumerate(lines):
                        if text_matches_terms(line, terms):
                            start_i, end_i = max(0, idx - 2), min(len(lines), idx + 3)
                            snippet = " ".join([l.strip() for l in lines[start_i:end_i]]).strip()
                            raw_matches.append({
                                "file_path": file_path, "file_name": file_name, "prefix": prefix,
                                "mtime": mtime, "line_number": idx + 1, "paragraph_index": None,
                                "location_info": f"Riga {idx + 1}{file_date_suffix}", "snippet": snippet,
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

                if name_matched and not found_in_content:
                    raw_matches.append({
                        "file_path": file_path, "file_name": file_name, "prefix": prefix,
                        "mtime": mtime, "line_number": None, "paragraph_index": None,
                        "location_info": f"Nome File{file_date_suffix}",
                        "snippet": f"Corrispondenza: '{file_name}'",
                    })

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
        try:
            self.last_ocr_stats = rtad_ocr.get_stats() if rtad_ocr is not None else {}
        except Exception:
            self.last_ocr_stats = {}
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

        if self._stop_search:
            text = (
                f"Ricerca interrotta al {self.current_percent}% ({self.scanned_count} file). "
                f"Salvati {matches} risultati.{mail_note}{feed_note}{large_note}{ocr_note}"
            )
            speak_accessible(f"Ricerca annullata. Conservati {matches} risultati.{feed_speak}")
        else:
            text = (
                f"Ricerca completata: 100% ({self.scanned_count} file). "
                f"Trovati {matches} risultati.{mail_note}{feed_note}{large_note}{ocr_note}"
            )
            if self.scanned_count == 0 and missing_targets:
                text += (
                    " Nessun percorso valido trovato: controlla che la cartella o il file "
                    "esistano (senza virgolette nel campo percorso)."
                )
            logging.info(
                f"Ricerca completata. File esaminati: {self.scanned_count}. "
                f"Messaggi posta: {mail_msgs}. Allegati PDF visti: {pdf_att_seen}, "
                f"hit: {pdf_att_hits}, stub vuoti: {pdf_att_empty}. "
                f"Risultati: {matches}. Occorrenze grezze feed: {feed_raw}. "
                f"File grandi saltati (non posta): {skipped_large}. OCR: {ocr_stats}."
                f" Percorsi mancanti: {missing_targets}."
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
        if item_open_msg is not None:
            self.Bind(wx.EVT_MENU, lambda e: self.open_selected_mail_message(), item_open_msg)
        if item_save_att is not None:
            self.Bind(wx.EVT_MENU, lambda e: self.save_attachment_pdf(item_data), item_save_att)
        self.Bind(wx.EVT_MENU, lambda e: wx.CallLater(250, self.speak_selected_preview), item_preview)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_snippet_to_clipboard(snippet), item_copy_snippet)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_path_to_clipboard(file_path), item_copy_path)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_text_to_clipboard(item_data, mode="clean"), item_copy_text)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_text_to_clipboard(item_data, mode="full"), item_copy_ocr_full)
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
                    try:
                        ocr_txt = rtad_ocr.ocr_text_for_clipboard(ocr_txt, mode=mode) or ocr_txt
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
                "Questo risultato è un file immagine senza testo OCR salvato: "
                "usa «Copia Immagine», oppure riesegui la ricerca con OCR attivo."
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
                img = wx.Image(file_path, wx.BITMAP_TYPE_ANY)
                if img.IsOk() and wx.TheClipboard.Open():
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
