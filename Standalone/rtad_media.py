# -*- coding: utf-8 -*-
"""RTAD media — scheda tecnica + descrizione/trascrizione audio-video (1.6.7).

Gemello Standalone ↔ Add-on. Metadati locali sempre; Gemini opt-in (chiave utente).
Niente Whisper di massa né scansione «tutto il PC».
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import wave

MEDIA_EXTS = (
    ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wav", ".wma",
    ".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".webm",
    ".mpg", ".mpeg", ".3gp",
)

AUDIO_EXTS = {
    ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wav", ".wma",
}
VIDEO_EXTS = {
    ".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".webm",
    ".mpg", ".mpeg", ".3gp",
}

# Limiti = tetti Google File API (docs ai.google.dev), non tetti artificiali RTAD.
# Inline ≤20 MB; oltre → File API. Per-file max 2 GB; video fino a ~3 h (1M ctx, low res).
MAX_MEDIA_INLINE_BYTES = 20 * 1024 * 1024
MAX_MEDIA_AI_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB = max per file File API
MAX_MEDIA_BYTES = MAX_MEDIA_AI_BYTES  # alias (yt-dlp, HTTP diretti, download)
MAX_MEDIA_DURATION_SEC = 3 * 60 * 60  # 3 ore (doc video understanding Gemini)
MEDIA_CACHE_VERSION = 7
# Short tipici (Reels / Shorts / TikTok): durata breve e spesso verticali
SHORT_MAX_DURATION_SEC = 60
SHORT_VERTICAL_MAX_DURATION_SEC = 180
_GEMINI_TIMEOUT_SEC = 120
_GEMINI_TIMEOUT_FILE_API_SEC = 900  # analisi lunghe / file grandi
_GEMINI_FILE_POLL_SEC = 600
_GEMINI_UPLOAD_TIMEOUT_SEC = 1800  # fino a ~2 GB
_GEMINI_UPLOAD_BASE = (
    "https://generativelanguage.googleapis.com/upload/v1beta/files"
)
_GEMINI_FILES_BASE = "https://generativelanguage.googleapis.com/v1beta"
_GEMINI_MODELS_PREFERRED = (
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)

_MIME_BY_EXT = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
    ".wma": "audio/x-ms-wma",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".wmv": "video/x-ms-wmv",
    ".webm": "video/webm",
    ".mpg": "video/mpeg",
    ".mpeg": "video/mpeg",
    ".3gp": "video/3gpp",
}

_FORMAT_LABEL = {
    ".mp3": "MP3", ".m4a": "M4A", ".aac": "AAC", ".flac": "FLAC",
    ".ogg": "OGG", ".opus": "Opus", ".wav": "WAV", ".wma": "WMA",
    ".mp4": "MP4", ".m4v": "M4V", ".mkv": "MKV", ".avi": "AVI",
    ".mov": "MOV", ".wmv": "WMV", ".webm": "WebM",
    ".mpg": "MPEG", ".mpeg": "MPEG", ".3gp": "3GP",
}

_cache_dir = ""
_cache_lock = threading.Lock()
_gemini_api_key = ""
_gemini_last_error = ""
_gemini_models_cache = None
_gemini_models_cache_key = ""
_stats = {
    "tech_reads": 0,
    "gemini_calls": 0,
    "cache_hits": 0,
    "failures": 0,
}

_DESCRIBE_PROMPT_VIDEO = """\
Sei un assistente per persone non vedenti o ipovedenti.
Guarda e ascolta questo VIDEO e produci un RIASSUNTO accessibile in italiano.

Regole:
- Scrivi in italiano chiaro, frasi complete.
- Indica: tipo di contenuto (intervista, sport, musica con video, tutorial, short, ecc.),
  cosa si vede e cosa si sente, tono, lingue/voci.
- Se c'è musica: genere, atmosfera, se ci sono parole cantate (senza inventare testi).
- Se c'è parlato: di cosa si parla, senza inventare nomi o fatti non udibili/visibili.
- Non inventare. Se qualcosa non è chiaro, dillo.
- Niente markdown, elenchi con asterischi o titoli con cancelletto.
- Lunghezza utile: circa 8-20 frasi.
"""

_DESCRIBE_PROMPT_AUDIO = """\
Sei un assistente per persone non vedenti o ipovedenti.
Ascolta questo file AUDIO (non è un video) e produci un RIASSUNTO accessibile in italiano.

Regole:
- Scrivi in italiano chiaro, frasi complete.
- NON parlare di immagini, schermo, video musicale o grafiche: è solo audio.
- Indica: tipo (canzone, podcast, intervista, messaggio vocale, ecc.),
  genere/atmosfera, voci (uomo/donna/coro), lingua, argomenti del testo se udibile.
- Se è musica: struttura (strofa/ritornello), tono emotivo; non inventare testi.
- Se c'è parlato: di cosa si parla, senza inventare.
- Non inventare. Se qualcosa non è chiaro, dillo.
- Niente markdown, elenchi con asterischi o titoli con cancelletto.
- Lunghezza utile: circa 8-20 frasi.
"""

_TRANSCRIBE_PROMPT = """\
Trascrivi in italiano (o nella lingua originale se non è italiano) il contenuto
parlato o cantato di questo file audio/video.

Regole:
- Solo testo parlato/cantato udibile; non inventare.
- Se non c'è parlato: scrivi esattamente «Nessun parlato rilevato.»
- Se il parlato è parziale o poco chiaro, indica [incerto] vicino alle parti dubbie.
- Niente markdown. Usa a capo tra turni o paragrafi naturali.
- Non aggiungere un riassunto: solo trascrizione.
- NON inserire timestamp o tempi.
"""

_TRANSCRIBE_PROMPT_TIMESTAMPS = """\
Trascrivi in italiano (o nella lingua originale se non è italiano) il contenuto
parlato o cantato di questo file audio/video, CON TIMESTAMP PROGRESSIVI.

OBBLIGATORIO — formato (una riga per battuta):
[MM:SS] testo della battuta
oppure [H:MM:SS] se supera un'ora.

Regole rigorose:
- Solo testo parlato/cantato udibile; non inventare.
- Se non c'è parlato: scrivi esattamente «Nessun parlato rilevato.»
- Se poco chiaro: [incerto] vicino alle parti dubbie.
- VIETATO mettere tutto il testo sotto un solo [00:00].
- Ogni cambio di parlante, ogni frase o ogni ~2-4 secondi: NUOVO timestamp
  sulla riga successiva, con tempo maggiore del precedente.
- I tempi devono avanzare lungo il file (es. [00:00], [00:03], [00:07], [00:12]…).
- Allinea i tempi a quando le parole vengono davvero dette.
- Niente markdown, niente riassunto: solo righe «[tempo] testo».
"""


def configure(cache_dir: str) -> None:
    """Cartella cache media (es. CONFIG_DIR/media_cache)."""
    global _cache_dir
    _cache_dir = cache_dir or ""
    if _cache_dir:
        try:
            os.makedirs(_cache_dir, exist_ok=True)
        except Exception:
            pass


def set_gemini_api_key(key: str) -> None:
    global _gemini_api_key, _gemini_last_error
    global _gemini_models_cache, _gemini_models_cache_key
    _gemini_api_key = (key or "").strip()
    _gemini_last_error = ""
    _gemini_models_cache = None
    _gemini_models_cache_key = ""


def get_gemini_api_key() -> str:
    return _gemini_api_key or ""


def has_gemini_api_key() -> bool:
    return bool((_gemini_api_key or "").strip())


def gemini_last_error() -> str:
    return _gemini_last_error or ""


def is_media_path(path: str) -> bool:
    if not path:
        return False
    return os.path.splitext(path)[1].lower() in MEDIA_EXTS


def media_kind(path: str) -> str:
    ext = os.path.splitext(path or "")[1].lower()
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    return "media"


def mime_for_media_path(path: str) -> str:
    ext = os.path.splitext(path or "")[1].lower()
    return _MIME_BY_EXT.get(ext, "application/octet-stream")


def _format_size(size_b: int) -> str:
    if size_b < 1024:
        return f"{size_b} byte"
    if size_b < 1024 * 1024:
        return f"{size_b / 1024:.1f} KB"
    if size_b < 1024 * 1024 * 1024:
        return f"{size_b / (1024 * 1024):.2f} MB"
    return f"{size_b / (1024 * 1024 * 1024):.2f} GB"


def _format_duration(seconds: float) -> str:
    if seconds is None or seconds <= 0:
        return ""
    total = int(round(float(seconds)))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} h {m:02d} min {s:02d} s"
    if m:
        return f"{m} min {s:02d} s"
    return f"{s} s"


def _parse_duration_to_seconds(raw: str) -> float:
    """Interpreta durata da Shell (es. '00:03:21' o '3:21' o '00:03:21.5')."""
    text = (raw or "").strip()
    if not text:
        return 0.0
    # A volte Windows mette caratteri strani
    text = text.replace("\u200e", "").replace("\u200f", "").strip()
    m = re.match(
        r"^(?:(\d+):)?(\d{1,2}):(\d{2})(?:\.(\d+))?$",
        text,
    )
    if m:
        h = int(m.group(1) or 0)
        mi = int(m.group(2) or 0)
        s = int(m.group(3) or 0)
        return float(h * 3600 + mi * 60 + s)
    # Solo secondi numerici
    try:
        return float(text.replace(",", "."))
    except Exception:
        return 0.0


def _wav_tech(path: str) -> dict:
    out = {}
    try:
        with wave.open(path, "rb") as w:
            ch = int(w.getnchannels() or 0)
            rate = int(w.getframerate() or 0)
            frames = int(w.getnframes() or 0)
            width = int(w.getsampwidth() or 0)
            out["channels"] = ch
            out["sample_rate"] = rate
            out["bit_depth"] = width * 8 if width else 0
            if rate > 0 and frames > 0:
                out["duration_sec"] = frames / float(rate)
    except Exception as e:
        out["error"] = str(e)
    return out


def _webm_tech(path: str) -> dict:
    """Durata (e hint audio) da WebM/Matroska senza dipendenze esterne.

    Cerca l'elemento EBML Duration (0x4489) nei primi MB del file.
    Serve per gli scarichi yt-dlp (.webm/.opus in container WebM) dove
    Shell Windows spesso non espone la durata → «non rilevata».
    """
    out = {}
    try:
        with open(path, "rb") as f:
            data = f.read(4 * 1024 * 1024)
    except Exception as e:
        out["error"] = str(e)
        return out
    if len(data) < 16 or not (
        data.startswith(b"\x1a\x45\xdf\xa3") or b"webm" in data[:64].lower()
        or b"matroska" in data[:128].lower()
    ):
        # Alcuni .webm partono comunque con EBML; se manca header, prova lo stesso
        if b"\x44\x89" not in data[: 512 * 1024]:
            return out

    # TimestampScale (0x2AD7B1), default Matroska = 1_000_000
    scale = 1_000_000.0
    idx = 0
    while True:
        i = data.find(b"\x2a\xd7\xb1", idx)
        if i < 0 or i + 4 >= len(data):
            break
        # size VINT spesso 0x83 (3 byte) o 0x84
        sz_b = data[i + 3]
        if sz_b in (0x81, 0x82, 0x83, 0x84) and i + 4 + (sz_b & 0x0F) <= len(data):
            n = sz_b & 0x0F
            raw = data[i + 4 : i + 4 + n]
            try:
                scale = float(int.from_bytes(raw, "big"))
                if scale > 0:
                    break
            except Exception:
                pass
        idx = i + 3

    # Duration (0x4489) — float64 big-endian tipico (size 0x88)
    idx = 0
    duration_sec = 0.0
    while True:
        i = data.find(b"\x44\x89", idx)
        if i < 0:
            break
        if i + 3 >= len(data):
            break
        sz_b = data[i + 2]
        if sz_b == 0x88 and i + 11 <= len(data):
            try:
                val = struct.unpack(">d", data[i + 3 : i + 11])[0]
            except Exception:
                val = 0.0
            if val > 0:
                # Duration * TimestampScale / 1e9 → secondi
                sec = (val * scale) / 1_000_000_000.0
                # Alcuni file mettono già i millisecondi nel float
                if sec > 24 * 3600 and val < 1e8:
                    sec = val / 1000.0
                elif sec <= 0 and val > 1:
                    sec = val if val < 1e6 else val / 1000.0
                if 0.2 < sec < 24 * 3600:
                    duration_sec = sec
                    break
        idx = i + 2

    if duration_sec > 0:
        out["duration_sec"] = float(duration_sec)
    # Hint: molti scarichi yt-dlp «bestaudio» sono solo Opus in WebM
    if b"OpusHead" in data or b"A_OPUS" in data:
        out["audio_codec"] = out.get("audio_codec") or "Opus"
    return out


def _read_mp4_boxes(data: bytes, start: int = 0, end: int | None = None):
    """Itera box MP4 (size, type, payload_start, payload_end)."""
    if end is None:
        end = len(data)
    pos = start
    while pos + 8 <= end:
        size = struct.unpack(">I", data[pos : pos + 4])[0]
        typ = data[pos + 4 : pos + 8]
        hdr = 8
        if size == 1:
            if pos + 16 > end:
                break
            size = struct.unpack(">Q", data[pos + 8 : pos + 16])[0]
            hdr = 16
        elif size == 0:
            size = end - pos
        if size < hdr or pos + size > end:
            break
        yield typ, pos + hdr, pos + size
        pos += size


def _locate_mp4_moov_bytes(path: str) -> bytes:
    """Trova e legge l'atomo moov anche se non è in testa/coda (file grandi)."""
    try:
        size = os.path.getsize(path)
    except Exception:
        return b""
    if size < 16:
        return b""
    # 1) Testa + coda (casi comuni)
    try:
        with open(path, "rb") as f:
            head = f.read(min(size, 32 * 1024 * 1024))
            tail = b""
            if size > len(head):
                f.seek(max(0, size - 16 * 1024 * 1024))
                tail = f.read()
    except Exception:
        return b""
    blob = head + (tail if tail and tail not in head else b"")
    # 2) Se moov non c'è, scansiona indici ogni 1 MB cercando il fourcc
    if b"moov" not in blob and size > len(blob):
        try:
            with open(path, "rb") as f:
                step = 1024 * 1024
                pos = 0
                while pos + 8 <= size:
                    f.seek(pos)
                    hdr = f.read(8)
                    if len(hdr) < 8:
                        break
                    box_size = struct.unpack(">I", hdr[:4])[0]
                    typ = hdr[4:8]
                    hdr_len = 8
                    if box_size == 1:
                        more = f.read(8)
                        if len(more) < 8:
                            break
                        box_size = struct.unpack(">Q", more)[0]
                        hdr_len = 16
                    elif box_size == 0:
                        box_size = size - pos
                    if box_size < hdr_len:
                        pos += 1
                        continue
                    if typ == b"moov":
                        f.seek(pos)
                        return f.read(min(box_size, 64 * 1024 * 1024))
                    pos += box_size if box_size >= hdr_len else step
        except Exception:
            pass
    return blob


def _ffprobe_tech(path: str) -> dict:
    """Metadati via ffprobe (se nel PATH, tipico dopo winget FFmpeg)."""
    out = {}
    if not path or not shutil.which("ffprobe"):
        return out
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                "--",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=45,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return out
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return out
    try:
        data = json.loads(proc.stdout)
    except Exception:
        return out
    fmt = data.get("format") or {}
    try:
        dur = float(fmt.get("duration") or 0)
        if dur > 0:
            out["duration_sec"] = dur
    except Exception:
        pass
    for st in data.get("streams") or []:
        codec_type = (st.get("codec_type") or "").lower()
        if codec_type == "video" and not out.get("frame_width"):
            try:
                w = int(st.get("width") or 0)
                h = int(st.get("height") or 0)
            except Exception:
                w = h = 0
            if w > 0 and h > 0:
                out["frame_width"] = w
                out["frame_height"] = h
                out["frame_size_raw"] = f"{w} x {h}"
                out["has_video"] = True
            cname = (st.get("codec_name") or "").strip()
            if cname:
                out["video_codec"] = cname
        elif codec_type == "audio":
            out["has_audio"] = True
            cname = (st.get("codec_name") or "").strip()
            if cname and not out.get("audio_codec"):
                out["audio_codec"] = cname
            try:
                ch = int(st.get("channels") or 0)
                if ch > 0:
                    out["channels"] = ch
            except Exception:
                pass
            try:
                rate = int(float(st.get("sample_rate") or 0))
                if rate > 0:
                    out["sample_rate"] = rate
            except Exception:
                pass
    return out


def _mp4_tech(path: str) -> dict:
    """Durata/risoluzione da atomi MP4/M4A/MOV (senza dipendenze esterne).

    Serve soprattutto nell'Add-on NVDA, dove Shell/pywin32 spesso non espone
    durata e dimensioni → altrimenti «Durata: non rilevata» e forma non classificata.
    """
    out = {}
    data = _locate_mp4_moov_bytes(path)
    if len(data) < 16:
        return out

    def walk(start, end, depth=0):
        if depth > 12:
            return
        for typ, ps, pe in _read_mp4_boxes(data, start, end):
            if typ in (b"moov", b"trak", b"mdia", b"minf", b"stbl"):
                walk(ps, pe, depth + 1)
            elif typ == b"mvhd" and "duration_sec" not in out:
                try:
                    version = data[ps]
                    if version == 1 and pe - ps >= 32:
                        timescale = struct.unpack(">I", data[ps + 20 : ps + 24])[0]
                        duration = struct.unpack(">Q", data[ps + 24 : ps + 32])[0]
                    elif pe - ps >= 20:
                        timescale = struct.unpack(">I", data[ps + 12 : ps + 16])[0]
                        duration = struct.unpack(">I", data[ps + 16 : ps + 20])[0]
                    else:
                        continue
                    if timescale > 0 and duration > 0:
                        out["duration_sec"] = float(duration) / float(timescale)
                except Exception:
                    pass
            elif typ == b"tkhd":
                try:
                    # width/height: ultimi 8 byte del tkhd (16.16 fixed)
                    if pe - ps >= 8:
                        w_fp, h_fp = struct.unpack(">II", data[pe - 8 : pe])
                        w = int(w_fp >> 16)
                        h = int(h_fp >> 16)
                        if w > 0 and h > 0 and (
                            out.get("frame_width", 0) * out.get("frame_height", 0)
                            < w * h
                        ):
                            # Preferisci la track con area maggiore (video vs audio)
                            out["frame_width"] = w
                            out["frame_height"] = h
                            out["frame_size_raw"] = f"{w} x {h}"
                except Exception:
                    pass
            elif typ == b"hdlr":
                # version+flags(4) + pre_defined(4) + handler_type(4)
                try:
                    if pe - ps >= 12:
                        handler = data[ps + 8 : ps + 12]
                        if handler == b"soun":
                            out["has_audio"] = True
                        elif handler == b"vide":
                            out["has_video"] = True
                except Exception:
                    pass

    try:
        walk(0, len(data))
    except Exception as e:
        out["error"] = str(e)
    # Fallback: sample entry types audio tipici
    if not out.get("has_audio"):
        for marker in (b"mp4a", b" Opus", b"Opus", b"ac-3", b"ec-3", b"sowt", b"raw "):
            if marker in data:
                out["has_audio"] = True
                break
    return out


def _shell_media_props(path: str) -> dict:
    """Metadati via Shell.Application (pywin32). Best-effort."""
    out = {}
    try:
        import win32com.client  # type: ignore
    except Exception:
        return out
    try:
        folder_path = os.path.dirname(os.path.abspath(path))
        name = os.path.basename(path)
        sh = win32com.client.Dispatch("Shell.Application")
        ns = sh.NameSpace(folder_path)
        if ns is None:
            return out
        item = ns.ParseName(name)
        if item is None:
            return out

        # Indici tipici Windows (possono variare leggermente per locale)
        # 27 durata, 28 bitrate, 16 artista, 21 titolo, 288/316 a volte sample rate
        labels_wanted = {
            "durata": "duration_raw",
            "length": "duration_raw",
            "bitrate": "bitrate_raw",
            "bit rate": "bitrate_raw",
            "data rate": "bitrate_raw",
            "frequenza": "sample_rate_raw",
            "sample rate": "sample_rate_raw",
            "canali": "channels_raw",
            "channels": "channels_raw",
            "artisti": "artist",
            "artists": "artist",
            "artista": "artist",
            "collaborazione": "contributing_artists",
            "contributing artists": "contributing_artists",
            "album": "album",
            "titolo": "title",
            "title": "title",
            "genere": "genre",
            "genre": "genre",
            "anno": "year",
            "year": "year",
            "compositori": "composer",
            "composers": "composer",
            "autore": "composer",
            "copyright": "copyright",
            "editore": "publisher",
            "publisher": "publisher",
            "commento": "comment",
            "comments": "comment",
            "frame rate": "frame_rate_raw",
            "frequenza fotogrammi": "frame_rate_raw",
            "dimensioni fotogramma": "frame_size_raw",
            "frame width": "frame_width_raw",
            "frame height": "frame_height_raw",
            "larghezza": "frame_width_raw",
            "width": "frame_width_raw",
            "altezza": "frame_height_raw",
            "height": "frame_height_raw",
            "totale bitrate": "total_bitrate_raw",
            "total bitrate": "total_bitrate_raw",
            "codec video": "video_codec",
            "video codec": "video_codec",
            "compressione": "compression",
            "compression": "compression",
            "codec audio": "audio_codec",
            "audio codec": "audio_codec",
            "sottotitoli": "subtitle",
            "protected": "protected",
        }
        # Scansiona le colonne disponibili (fino a ~320)
        for idx in range(0, 320):
            try:
                header = (ns.GetDetailsOf(None, idx) or "").strip().lower()
            except Exception:
                continue
            if not header:
                continue
            key = labels_wanted.get(header)
            if not key:
                continue
            try:
                val = (ns.GetDetailsOf(item, idx) or "").strip()
            except Exception:
                val = ""
            if val and key not in out:
                out[key] = val
        if out.get("duration_raw"):
            out["duration_sec"] = _parse_duration_to_seconds(out["duration_raw"])
    except Exception as e:
        logging.debug(f"Shell media props: {e}")
    return out


def _parse_frame_size(raw: str) -> tuple:
    """Estrae (width, height) da stringhe tipo '1920 x 1080'."""
    text = (raw or "").strip().lower().replace("×", "x")
    m = re.search(r"(\d+)\s*[x×]\s*(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


def media_companion_audio_path(video_path: str) -> str:
    """Percorso audio abbinato (download yt-dlp separato senza ffmpeg)."""
    if not video_path:
        return ""
    meta = read_media_source_meta(video_path)
    ap = (meta.get("audio_path") or "").strip()
    if ap and os.path.isfile(ap):
        return ap
    for ext in (".m4a", ".webm", ".opus", ".mp3", ".aac", ".mp4"):
        cand = video_path + ".rtad_audio" + ext
        if os.path.isfile(cand):
            return cand
    return ""


def _classify_clip_form(kind: str, duration_sec: float, width: int, height: int) -> str:
    """Etichetta Short / video normale / traccia audio (euristica accessibile)."""
    if kind == "audio":
        return "Traccia audio"
    dur = float(duration_sec or 0)
    vertical = bool(width > 0 and height > 0 and height > width)
    if dur > 0 and dur <= SHORT_MAX_DURATION_SEC:
        return "Short (clip breve ≤ 60 s)"
    if vertical and dur > 0 and dur <= SHORT_VERTICAL_MAX_DURATION_SEC:
        return "Short verticale (stile Reels/Shorts)"
    if dur > 0:
        return "Video normale"
    if vertical:
        return "Video verticale (durata non rilevata)"
    return "Video (forma non classificata)"


def get_media_tech_info(path: str) -> dict:
    """Scheda tecnica locale audio/video."""
    info = {
        "path": path or "",
        "file_name": os.path.basename(path or "") or "",
        "ext": "",
        "kind": "media",
        "format_label": "",
        "size_bytes": 0,
        "mtime": 0.0,
        "mtime_label": "",
        "duration_sec": 0.0,
        "duration_label": "",
        "channels": 0,
        "sample_rate": 0,
        "bit_depth": 0,
        "bitrate_raw": "",
        "total_bitrate_raw": "",
        "artist": "",
        "contributing_artists": "",
        "album": "",
        "title": "",
        "genre": "",
        "year": "",
        "composer": "",
        "copyright": "",
        "publisher": "",
        "comment": "",
        "frame_size_raw": "",
        "frame_rate_raw": "",
        "frame_width": 0,
        "frame_height": 0,
        "orientation": "",
        "clip_form": "",
        "video_codec": "",
        "audio_codec": "",
        "compression": "",
        "has_audio": False,
        "has_video": False,
        "silent_video": False,
        "ok": False,
        "error": "",
        "within_limits": True,
        "limit_notes": [],
    }
    if not path or not os.path.isfile(path):
        info["error"] = "File non trovato."
        return info
    if not is_media_path(path):
        info["error"] = "Il file non è un audio/video supportato."
        return info

    ext = os.path.splitext(path)[1].lower()
    info["ext"] = ext
    info["kind"] = media_kind(path)
    info["format_label"] = _FORMAT_LABEL.get(
        ext, ext.replace(".", "").upper() or "sconosciuto"
    )
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

    if ext == ".wav":
        wav = _wav_tech(path)
        for k in ("channels", "sample_rate", "bit_depth", "duration_sec"):
            if wav.get(k):
                info[k] = wav[k]
    elif ext in (".mp4", ".m4v", ".m4a", ".mov", ".3gp"):
        mp4 = _mp4_tech(path)
        if mp4.get("duration_sec") and not info.get("duration_sec"):
            info["duration_sec"] = float(mp4["duration_sec"])
        if mp4.get("frame_width") and not info.get("frame_width"):
            info["frame_width"] = int(mp4["frame_width"])
        if mp4.get("frame_height") and not info.get("frame_height"):
            info["frame_height"] = int(mp4["frame_height"])
        if mp4.get("frame_size_raw") and not info.get("frame_size_raw"):
            info["frame_size_raw"] = mp4["frame_size_raw"]
        if mp4.get("has_audio"):
            info["has_audio"] = True
        if mp4.get("has_video"):
            info["has_video"] = True
        # Non declassare .mp4/.mov se il parser atomi è incompleto (file grandi).
        # Solo .m4a è audio per estensione; ffprobe sotto conferma le piste.
        if ext == ".m4a":
            info["kind"] = "audio"
    elif ext in (".webm", ".mkv", ".opus"):
        webm = _webm_tech(path)
        if webm.get("duration_sec") and not info.get("duration_sec"):
            info["duration_sec"] = float(webm["duration_sec"])
        if webm.get("audio_codec") and not info.get("audio_codec"):
            info["audio_codec"] = webm["audio_codec"]
            info["has_audio"] = True
        # Audio-only in container .webm (tipico yt-dlp bestaudio)
        if (
            webm.get("duration_sec")
            and not webm.get("frame_width")
            and info.get("kind") == "video"
            and info["size_bytes"] > 0
            and not info.get("frame_size_raw")
        ):
            # Heuristica soft: senza traccia video nota, etichetta come audio
            if webm.get("audio_codec") and not info.get("video_codec"):
                info["kind"] = "audio"
                info["has_audio"] = True

    shell = _shell_media_props(path)
    # Fallback indici fissi Windows (Length / Frame width / Frame height)
    if shell and not shell.get("duration_raw"):
        try:
            import win32com.client  # type: ignore
            folder_path = os.path.dirname(os.path.abspath(path))
            name = os.path.basename(path)
            ns = win32com.client.Dispatch("Shell.Application").NameSpace(folder_path)
            item = ns.ParseName(name) if ns else None
            if item is not None:
                for idx in (27, 36, 21):  # Length tipico; altri possibili
                    raw = (ns.GetDetailsOf(item, idx) or "").strip()
                    if raw and ":" in raw and not shell.get("duration_raw"):
                        shell["duration_raw"] = raw
                        shell["duration_sec"] = _parse_duration_to_seconds(raw)
                        break
        except Exception:
            pass
    if shell.get("duration_sec") and not info.get("duration_sec"):
        info["duration_sec"] = float(shell["duration_sec"])
    # ffprobe (se installato con ffmpeg): completa durata/piste sui file grossi
    need_probe = (
        not info.get("duration_sec")
        or (
            (info.get("kind") or "") == "video"
            and not info.get("frame_width")
            and not info.get("frame_size_raw")
        )
    )
    if need_probe:
        probe = _ffprobe_tech(path)
        if probe.get("duration_sec") and not info.get("duration_sec"):
            info["duration_sec"] = float(probe["duration_sec"])
        if probe.get("frame_width") and not info.get("frame_width"):
            info["frame_width"] = int(probe["frame_width"])
        if probe.get("frame_height") and not info.get("frame_height"):
            info["frame_height"] = int(probe["frame_height"])
        if probe.get("frame_size_raw") and not info.get("frame_size_raw"):
            info["frame_size_raw"] = probe["frame_size_raw"]
        if probe.get("has_audio"):
            info["has_audio"] = True
        if probe.get("has_video"):
            info["has_video"] = True
        if probe.get("video_codec") and not info.get("video_codec"):
            info["video_codec"] = probe["video_codec"]
        if probe.get("audio_codec") and not info.get("audio_codec"):
            info["audio_codec"] = probe["audio_codec"]
        if probe.get("channels") and not info.get("channels"):
            info["channels"] = int(probe["channels"])
        if probe.get("sample_rate") and not info.get("sample_rate"):
            info["sample_rate"] = int(probe["sample_rate"])
        # Audio-only confermato da ffprobe in container .mp4/.webm
        if (
            probe.get("has_audio")
            and not probe.get("has_video")
            and not probe.get("frame_width")
            and ext in (".mp4", ".m4v", ".webm", ".mkv", ".mov", ".3gp")
        ):
            info["kind"] = "audio"
    for src, dest in (
        ("bitrate_raw", "bitrate_raw"),
        ("total_bitrate_raw", "total_bitrate_raw"),
        ("artist", "artist"),
        ("contributing_artists", "contributing_artists"),
        ("album", "album"),
        ("title", "title"),
        ("genre", "genre"),
        ("year", "year"),
        ("composer", "composer"),
        ("copyright", "copyright"),
        ("publisher", "publisher"),
        ("comment", "comment"),
        ("frame_size_raw", "frame_size_raw"),
        ("frame_rate_raw", "frame_rate_raw"),
        ("video_codec", "video_codec"),
        ("audio_codec", "audio_codec"),
        ("compression", "compression"),
    ):
        if shell.get(src) and not info.get(dest):
            info[dest] = shell[src]
    if shell.get("channels_raw") and not info.get("channels"):
        m = re.search(r"(\d+)", str(shell["channels_raw"]))
        if m:
            info["channels"] = int(m.group(1))
    if shell.get("sample_rate_raw") and not info.get("sample_rate"):
        m = re.search(r"([\d.]+)", str(shell["sample_rate_raw"]).replace(",", "."))
        if m:
            try:
                rate = float(m.group(1))
                # Se in kHz (es. 44,1) scala
                if rate < 1000:
                    rate *= 1000
                info["sample_rate"] = int(rate)
            except Exception:
                pass

    w = int(info.get("frame_width") or 0)
    h = int(info.get("frame_height") or 0)
    if shell.get("frame_width_raw"):
        m = re.search(r"(\d+)", str(shell["frame_width_raw"]))
        if m:
            w = w or int(m.group(1))
    if shell.get("frame_height_raw"):
        m = re.search(r"(\d+)", str(shell["frame_height_raw"]))
        if m:
            h = h or int(m.group(1))
    if (not w or not h) and info.get("frame_size_raw"):
        w2, h2 = _parse_frame_size(info["frame_size_raw"])
        w = w or w2
        h = h or h2
    info["frame_width"] = w
    info["frame_height"] = h
    if w > 0 and h > 0:
        if not info.get("frame_size_raw"):
            info["frame_size_raw"] = f"{w} x {h}"
        if h > w:
            info["orientation"] = "verticale"
        elif w > h:
            info["orientation"] = "orizzontale"
        else:
            info["orientation"] = "quadrata"

    if info.get("audio_codec") or int(info.get("channels") or 0) > 0:
        info["has_audio"] = True
    if info.get("video_codec") or int(info.get("frame_width") or 0) > 0:
        info["has_video"] = True
    if info.get("kind") == "audio":
        info["has_audio"] = True

    info["duration_label"] = _format_duration(info.get("duration_sec") or 0)
    info["clip_form"] = _classify_clip_form(
        info.get("kind") or "media",
        float(info.get("duration_sec") or 0),
        int(info.get("frame_width") or 0),
        int(info.get("frame_height") or 0),
    )
    notes = []
    if info["size_bytes"] > MAX_MEDIA_AI_BYTES:
        notes.append(
            f"File troppo grande per l'analisi AI "
            f"(max {_format_size(MAX_MEDIA_AI_BYTES)})."
        )
        info["within_limits"] = False
    elif info["size_bytes"] > MAX_MEDIA_INLINE_BYTES:
        notes.append(
            f"Oltre {_format_size(MAX_MEDIA_INLINE_BYTES)} inline: "
            "l'analisi userà la File API Gemini (upload temporaneo, "
            f"tetto Google {_format_size(MAX_MEDIA_AI_BYTES)} / "
            f"{_format_duration(MAX_MEDIA_DURATION_SEC)})."
        )
    if info["size_bytes"] > 200 * 1024 * 1024:
        notes.append(
            "File molto grande: upload e analisi possono richiedere diversi "
            "minuti e consumare più quota sulla tua chiave API Gemini."
        )
    dur = float(info.get("duration_sec") or 0)
    if dur > MAX_MEDIA_DURATION_SEC:
        notes.append(
            f"Durata oltre il limite per analisi AI "
            f"(max {_format_duration(MAX_MEDIA_DURATION_SEC)})."
        )
        info["within_limits"] = False
    companion = media_companion_audio_path(path)
    if companion:
        info["has_audio"] = True
        notes.append(
            "Audio abbinato da download separato (YouTube senza merge ffmpeg)."
        )
    elif (
        (info.get("kind") or "") == "video"
        and (info.get("has_video") or int(info.get("frame_width") or 0) > 0)
        and not info.get("has_audio")
    ):
        info["silent_video"] = True
        notes.append(
            "Video senza traccia audio: la trascrizione sarebbe inventata. "
            "Serve ffmpeg nel PATH per unire audio e video da YouTube, "
            "oppure apri un file locale completo."
        )
    info["limit_notes"] = notes
    info["ok"] = True
    _stats["tech_reads"] = int(_stats.get("tech_reads", 0) or 0) + 1
    return info


def format_media_tech_sheet(info: dict) -> str:
    """Testo accessibile della scheda tecnica media."""
    if not info:
        return "Scheda tecnica non disponibile."
    if not info.get("ok"):
        return info.get("error") or "Scheda tecnica non disponibile."
    kind = info.get("kind") or "media"
    kind_it = {"audio": "Audio", "video": "Video"}.get(kind, "Media")
    lines = [
        f"Scheda tecnica: {info.get('file_name') or kind}",
        f"Tipo: {kind_it}.",
        f"Formato: {info.get('format_label') or 'sconosciuto'}.",
    ]
    if info.get("clip_form"):
        lines.append(f"Forma: {info['clip_form']}.")
    if info.get("duration_label"):
        lines.append(f"Durata: {info['duration_label']}.")
    else:
        lines.append("Durata: non rilevata.")
    size_b = int(info.get("size_bytes") or 0)
    if size_b > 0:
        lines.append(f"Dimensione file: {_format_size(size_b)}.")
    if info.get("orientation"):
        lines.append(f"Orientamento: {info['orientation']}.")
    if info.get("frame_size_raw"):
        lines.append(f"Risoluzione video: {info['frame_size_raw']}.")
    if info.get("frame_rate_raw"):
        lines.append(f"Frame rate: {info['frame_rate_raw']}.")
    if info.get("video_codec"):
        lines.append(f"Codec video: {info['video_codec']}.")
    if info.get("audio_codec"):
        lines.append(f"Codec audio: {info['audio_codec']}.")
    if info.get("compression") and info.get("compression") != info.get("video_codec"):
        lines.append(f"Compressione: {info['compression']}.")
    ch = int(info.get("channels") or 0)
    if ch > 0:
        lines.append(f"Canali: {ch}.")
    rate = int(info.get("sample_rate") or 0)
    if rate > 0:
        if rate >= 1000:
            lines.append(f"Frequenza di campionamento: {rate / 1000:g} kHz.")
        else:
            lines.append(f"Frequenza di campionamento: {rate} Hz.")
    depth = int(info.get("bit_depth") or 0)
    if depth > 0:
        lines.append(f"Profondità bit: {depth} bit.")
    if info.get("bitrate_raw"):
        lines.append(f"Bitrate: {info['bitrate_raw']}.")
    if info.get("total_bitrate_raw") and info.get("total_bitrate_raw") != info.get("bitrate_raw"):
        lines.append(f"Bitrate totale: {info['total_bitrate_raw']}.")
    if info.get("title"):
        lines.append(f"Titolo: {info['title']}.")
    if info.get("artist"):
        lines.append(f"Artista: {info['artist']}.")
    if info.get("contributing_artists"):
        lines.append(f"Artisti collaboratori: {info['contributing_artists']}.")
    if info.get("album"):
        lines.append(f"Album: {info['album']}.")
    if info.get("composer"):
        lines.append(f"Autore/compositore: {info['composer']}.")
    if info.get("genre"):
        lines.append(f"Genere: {info['genre']}.")
    if info.get("year"):
        lines.append(f"Anno: {info['year']}.")
    if info.get("publisher"):
        lines.append(f"Editore: {info['publisher']}.")
    if info.get("copyright"):
        lines.append(f"Copyright: {info['copyright']}.")
    if info.get("comment"):
        lines.append(f"Commento: {info['comment']}.")
    if info.get("mtime_label"):
        lines.append(f"Data file: {info['mtime_label']}.")
    src_meta = read_media_source_meta(info.get("path") or "")
    if src_meta.get("title"):
        lines.append(f"Titolo sorgente: {src_meta['title']}.")
    if src_meta.get("id"):
        lines.append(f"ID sorgente: {src_meta['id']}.")
    if src_meta.get("webpage_url") or src_meta.get("url"):
        lines.append(
            f"URL sorgente: {src_meta.get('webpage_url') or src_meta.get('url')}."
        )
    # Scarichi yt-dlp sotto tetto dimensione: spesso solo traccia audio (m4a/webm)
    fname = (info.get("file_name") or "").lower()
    if kind == "audio" and fname.startswith("rtad_media_"):
        lines.append(
            "Nota: dal link è stata presa solo la traccia audio (video troppo "
            f"pesante per il tetto attuale di {_format_size(MAX_MEDIA_AI_BYTES)})."
        )
    for note in info.get("limit_notes") or []:
        lines.append(f"Nota: {note}")
    return "\n".join(lines)


def _cache_key(path: str, size: int, mtime: float, kind: str) -> str:
    raw = f"media{MEDIA_CACHE_VERSION}|{kind}|{path}|{size}|{mtime}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()


def _cache_get(key: str):
    if not _cache_dir or not key:
        return None
    path = os.path.join(_cache_dir, f"{key}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if int(data.get("v", 0)) != MEDIA_CACHE_VERSION:
            return None
        return data.get("payload")
    except Exception:
        return None


def _cache_put(key: str, payload: dict) -> None:
    if not _cache_dir or not key:
        return
    path = os.path.join(_cache_dir, f"{key}.json")
    try:
        with _cache_lock:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {"v": MEDIA_CACHE_VERSION, "payload": payload, "ts": time.time()},
                    f,
                    ensure_ascii=False,
                )
    except Exception:
        pass


def clear_media_cache() -> int:
    """Elimina file cache media. Restituisce quanti file rimossi."""
    if not _cache_dir or not os.path.isdir(_cache_dir):
        return 0
    n = 0
    try:
        for name in os.listdir(_cache_dir):
            if not name.endswith(".json"):
                continue
            try:
                os.remove(os.path.join(_cache_dir, name))
                n += 1
            except Exception:
                pass
    except Exception:
        pass
    return n


def _gemini_list_generate_models(key: str) -> list:
    global _gemini_models_cache, _gemini_models_cache_key
    if not key:
        return []
    if _gemini_models_cache is not None and _gemini_models_cache_key == key:
        return list(_gemini_models_cache)
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models"
        f"?key={urllib.parse.quote(key, safe='')}"
    )
    names = []
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
        for m in data.get("models") or []:
            methods = m.get("supportedGenerationMethods") or []
            if "generateContent" not in methods:
                continue
            name = (m.get("name") or "").replace("models/", "").strip()
            if name:
                names.append(name)
    except Exception as e:
        logging.debug(f"ListModels media Gemini: {e}")
    _gemini_models_cache = names
    _gemini_models_cache_key = key
    return list(names)


def _gemini_model_candidates(key: str) -> list:
    ordered = []
    seen = set()

    def _add(n):
        n = (n or "").strip()
        if n and n not in seen:
            seen.add(n)
            ordered.append(n)

    for n in _GEMINI_MODELS_PREFERRED:
        _add(n)
    for n in _gemini_list_generate_models(key):
        _add(n)
    return ordered


def _analysis_total_bytes(path: str) -> int:
    """Dimensione file principale + eventuale audio abbinato (yt-dlp)."""
    total = 0
    try:
        total = int(os.path.getsize(path))
    except Exception:
        return 0
    comp = media_companion_audio_path(path)
    if comp:
        try:
            total += int(os.path.getsize(comp))
        except Exception:
            pass
    return total


def _emit_progress(on_progress, percent, message: str) -> None:
    """Callback opzionale: on_progress(percent 0-100, message)."""
    if not callable(on_progress):
        return
    try:
        pct = int(max(0, min(100, int(percent))))
    except Exception:
        pct = 0
    try:
        on_progress(pct, (message or "").strip() or "In corso…")
    except Exception:
        pass


def _gemini_files_delete(file_names: list, api_key: str) -> None:
    """Elimina upload temporanei su Google (best-effort)."""
    key = (api_key or "").strip()
    if not key:
        return
    for name in file_names or []:
        n = (name or "").strip()
        if not n:
            continue
        if not n.startswith("files/"):
            n = f"files/{n.lstrip('/')}"
        url = (
            f"{_GEMINI_FILES_BASE}/{urllib.parse.quote(n, safe='/')}"
            f"?key={urllib.parse.quote(key, safe='')}"
        )
        try:
            req = urllib.request.Request(url, method="DELETE")
            urllib.request.urlopen(req, timeout=30)
        except Exception:
            pass


def _gemini_file_wait_active(
    file_name: str,
    api_key: str,
    should_abort=None,
    timeout: int = _GEMINI_FILE_POLL_SEC,
) -> tuple:
    """Attende state ACTIVE. Returns (ok, error)."""
    name = (file_name or "").strip()
    if not name.startswith("files/"):
        name = f"files/{name.lstrip('/')}"
    key = (api_key or "").strip()
    url = (
        f"{_GEMINI_FILES_BASE}/{urllib.parse.quote(name, safe='/')}"
        f"?key={urllib.parse.quote(key, safe='')}"
    )
    deadline = time.time() + max(5, int(timeout or 60))
    last_state = ""
    while time.time() < deadline:
        if should_abort and should_abort():
            return False, "gemini: annullato"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
        except Exception as e:
            return False, f"gemini: stato file ({e})"
        st = (data.get("state") or "").strip().upper()
        last_state = st or last_state
        if st == "ACTIVE":
            return True, ""
        if st == "FAILED":
            err = (data.get("error") or {}).get("message") or "elaborazione fallita"
            return False, f"gemini: file {err}"
        time.sleep(1.5)
    return False, f"gemini: timeout attesa file ({last_state or 'PROCESSING'})"


def _gemini_upload_file(
    path: str,
    mime: str,
    api_key: str,
    should_abort=None,
    on_progress=None,
    progress_base: int = 40,
) -> dict:
    """Upload resumable File API. Dict: ok, file_uri, name, error."""
    out = {"ok": False, "file_uri": "", "name": "", "error": ""}
    key = (api_key or "").strip()
    if not key:
        out["error"] = "chiave API assente"
        return out
    if not path or not os.path.isfile(path):
        out["error"] = "file non trovato"
        return out
    try:
        size = int(os.path.getsize(path))
    except Exception as e:
        out["error"] = str(e)
        return out
    if size <= 0:
        out["error"] = "file vuoto"
        return out
    if size > MAX_MEDIA_AI_BYTES:
        out["error"] = (
            f"file troppo grande (max {_format_size(MAX_MEDIA_AI_BYTES)})"
        )
        return out
    mime = (mime or mime_for_media_path(path) or "application/octet-stream").strip()
    display = os.path.basename(path) or "rtad_media"
    start_url = f"{_GEMINI_UPLOAD_BASE}?key={urllib.parse.quote(key, safe='')}"
    meta = json.dumps({"file": {"display_name": display[:120]}}).encode("utf-8")
    try:
        _emit_progress(
            on_progress,
            progress_base,
            f"Upload File API ({_format_size(size)})…",
        )
        req = urllib.request.Request(
            start_url,
            data=meta,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "start",
                "X-Goog-Upload-Header-Content-Length": str(size),
                "X-Goog-Upload-Header-Content-Type": mime,
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            upload_url = (
                resp.headers.get("X-Goog-Upload-URL")
                or resp.headers.get("x-goog-upload-url")
                or ""
            ).strip()
        if not upload_url:
            out["error"] = "gemini: URL upload mancante"
            return out
        if should_abort and should_abort():
            out["error"] = "gemini: annullato"
            return out
        with open(path, "rb") as f:
            raw = f.read()
        _emit_progress(on_progress, min(progress_base + 8, 95), "Invio file a Gemini…")
        req2 = urllib.request.Request(
            upload_url,
            data=raw,
            method="POST",
            headers={
                "Content-Length": str(len(raw)),
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "upload, finalize",
                "X-Goog-Upload-Offset": "0",
            },
        )
        with urllib.request.urlopen(req2, timeout=_GEMINI_UPLOAD_TIMEOUT_SEC) as resp2:
            body = resp2.read().decode("utf-8", errors="replace")
        info = json.loads(body or "{}").get("file") or {}
        out["name"] = (info.get("name") or "").strip()
        out["file_uri"] = (info.get("uri") or "").strip()
        if not out["file_uri"] or not out["name"]:
            out["error"] = "gemini: risposta upload incompleta"
            return out
        _emit_progress(
            on_progress, min(progress_base + 12, 96), "Elaborazione file su Gemini…"
        )
        ok, err = _gemini_file_wait_active(out["name"], key, should_abort=should_abort)
        if not ok:
            out["error"] = err or "gemini: file non attivo"
            _gemini_files_delete([out["name"]], key)
            return out
        out["ok"] = True
        return out
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        out["error"] = f"gemini upload HTTP {e.code}" + (
            f": {err_body}" if err_body else ""
        )
        return out
    except Exception as e:
        out["error"] = f"gemini upload: {e}"
        return out


def _gemini_build_media_parts(
    path: str,
    prompt: str,
    api_key: str,
    should_abort=None,
    on_progress=None,
    progress_base: int = 40,
) -> tuple:
    """Costruisce parts inline o File API. Returns (parts, file_names, mode, error)."""
    companion = media_companion_audio_path(path)
    total = _analysis_total_bytes(path)
    if total > MAX_MEDIA_AI_BYTES:
        return (
            None,
            [],
            "",
            (
                f"gemini: media troppo grande "
                f"(max {_format_size(MAX_MEDIA_AI_BYTES)})"
            ),
        )
    use_file_api = total > MAX_MEDIA_INLINE_BYTES
    parts = [{"text": prompt}]
    uploaded_names = []

    def _inline_part(media_path: str) -> dict:
        with open(media_path, "rb") as f:
            raw = f.read()
        return {
            "inline_data": {
                "mime_type": mime_for_media_path(media_path),
                "data": base64.b64encode(raw).decode("ascii"),
            }
        }

    def _file_part(media_path: str, base: int) -> tuple:
        up = _gemini_upload_file(
            media_path,
            mime_for_media_path(media_path),
            api_key,
            should_abort=should_abort,
            on_progress=on_progress,
            progress_base=base,
        )
        if not up.get("ok"):
            return None, up.get("error") or "upload fallito"
        uploaded_names.append(up["name"])
        return (
            {
                "file_data": {
                    "mime_type": mime_for_media_path(media_path),
                    "file_uri": up["file_uri"],
                }
            },
            "",
        )

    if not use_file_api:
        _emit_progress(
            on_progress,
            progress_base,
            f"Preparazione media inline ({_format_size(total)})…",
        )
        if companion:
            try:
                with open(path, "rb") as f:
                    vraw = f.read()
                with open(companion, "rb") as af:
                    araw = af.read()
            except Exception as e:
                return None, [], "", f"gemini: lettura ({e})"
            parts.append(
                {
                    "inline_data": {
                        "mime_type": mime_for_media_path(path),
                        "data": base64.b64encode(vraw).decode("ascii"),
                    }
                }
            )
            parts.append(
                {
                    "text": (
                        "Secondo allegato: traccia audio dello stesso clip "
                        "(da ascoltare insieme al video)."
                    )
                }
            )
            parts.append(
                {
                    "inline_data": {
                        "mime_type": mime_for_media_path(companion),
                        "data": base64.b64encode(araw).decode("ascii"),
                    }
                }
            )
        else:
            parts.append(_inline_part(path))
        return parts, [], "inline", ""

    # File API
    p1, err1 = _file_part(path, progress_base)
    if p1 is None:
        _gemini_files_delete(uploaded_names, api_key)
        return None, [], "", err1 or "upload video fallito"
    parts.append(p1)
    if companion:
        parts.append(
            {
                "text": (
                    "Secondo allegato: traccia audio dello stesso clip "
                    "(da ascoltare insieme al video)."
                )
            }
        )
        p2, err2 = _file_part(companion, min(progress_base + 10, 80))
        if p2 is None:
            _gemini_files_delete(uploaded_names, api_key)
            return None, [], "", err2 or "upload audio fallito"
        parts.append(p2)
    return parts, uploaded_names, "file_api", ""


def _gemini_generate_media(
    path: str,
    prompt: str,
    should_abort=None,
    max_output_tokens: int = 8192,
    on_progress=None,
    progress_base: int = 40,
) -> tuple:
    """Chiama Gemini su audio/video. Restituisce (testo, diag)."""
    global _gemini_last_error
    key = (_gemini_api_key or "").strip()
    if not key:
        _gemini_last_error = "chiave API Gemini assente"
        return "", "gemini: chiave API assente"
    if should_abort and should_abort():
        return "", "gemini: annullato"

    parts, uploaded_files, upload_mode, build_err = _gemini_build_media_parts(
        path,
        prompt,
        key,
        should_abort=should_abort,
        on_progress=on_progress,
        progress_base=progress_base,
    )
    if build_err or not parts:
        _gemini_last_error = build_err or "gemini: allegati non pronti"
        _gemini_files_delete(uploaded_files, key)
        return "", _gemini_last_error

    req_timeout = (
        _GEMINI_TIMEOUT_FILE_API_SEC
        if upload_mode == "file_api"
        else _GEMINI_TIMEOUT_SEC
    )
    _emit_progress(
        on_progress,
        min(progress_base + 20, 90),
        "Analisi Gemini in corso…",
    )
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": parts,
            }
        ],
        # Niente temperature (avviso AI Studio 07/10/2026).
        "generationConfig": {
            "maxOutputTokens": int(max_output_tokens or 8192),
        },
    }
    body = json.dumps(payload).encode("utf-8")
    last_err = ""
    tried = []
    models = _gemini_model_candidates(key) or list(_GEMINI_MODELS_PREFERRED)
    mode_tag = f"+{upload_mode}" if upload_mode else ""
    try:
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
                with urllib.request.urlopen(req, timeout=req_timeout) as resp:
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
                if e.code in (404, 429):
                    continue
                if e.code == 400 and "not found" in (err_body or "").lower():
                    continue
                _gemini_last_error = last_err
                return "", f"gemini: {last_err}"
            except Exception as e:
                last_err = f"{model}: {e}"
                _gemini_last_error = last_err
                return "", f"gemini: {e}"

            try:
                cands = data.get("candidates") or []
                if not cands:
                    pf = data.get("promptFeedback") or {}
                    last_err = f"{model}: nessuna risposta ({pf or 'vuoto'})"
                    continue
                out_parts = (
                    (((cands[0] or {}).get("content") or {}).get("parts")) or []
                )
                texts = []
                for p in out_parts:
                    t = (p.get("text") or "").strip()
                    if t:
                        texts.append(t)
                text = "\n".join(texts).strip()
                if text:
                    _gemini_last_error = ""
                    return text, f"gemini:{model}{mode_tag}"
                last_err = f"{model}: testo vuoto"
            except Exception as e:
                last_err = f"{model} parse: {e}"
                continue
    finally:
        _gemini_files_delete(uploaded_files, key)

    short_tried = ", ".join(tried[:6])
    if len(tried) > 6:
        short_tried += f"… (+{len(tried) - 6})"
    _gemini_last_error = last_err or "nessun modello Gemini disponibile"
    return "", f"gemini: {_gemini_last_error} [provati: {short_tried}]"


def _check_ai_limits(path: str) -> str:
    """Messaggio errore se file fuori limiti AI, altrimenti stringa vuota."""
    info = get_media_tech_info(path)
    if not info.get("ok"):
        return info.get("error") or "File media non valido."
    total = _analysis_total_bytes(path)
    if total <= 0:
        return "File vuoto."
    if total > MAX_MEDIA_AI_BYTES:
        return (
            f"File troppo grande per l'analisi AI "
            f"(max {_format_size(MAX_MEDIA_AI_BYTES)}). "
            "La scheda tecnica resta disponibile."
        )
    dur = float(info.get("duration_sec") or 0)
    if dur > MAX_MEDIA_DURATION_SEC:
        return (
            f"Durata troppo lunga per l'analisi AI "
            f"(max {_format_duration(MAX_MEDIA_DURATION_SEC)}). "
            "La scheda tecnica resta disponibile."
        )
    return ""


def describe_media_gemini(
    path: str,
    should_abort=None,
    use_cache: bool = True,
    on_progress=None,
) -> dict:
    """Riassunto accessibile via Gemini. Dict: ok, text, error, source."""
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
    if not is_media_path(path):
        result["error"] = "Il file non è un audio/video supportato."
        return result
    if not has_gemini_api_key():
        result["error"] = (
            "Per il riassunto serve la chiave API Gemini "
            "(Strumenti → Chiave API Gemini / Google AI Studio)."
        )
        return result
    limit_err = _check_ai_limits(path)
    if limit_err:
        result["error"] = limit_err
        return result
    try:
        size = os.path.getsize(path)
        mtime = os.path.getmtime(path)
    except Exception as e:
        result["error"] = str(e)
        return result

    kind = media_kind(path)
    src_id = (read_media_source_meta(path).get("id") or "").strip()
    companion = media_companion_audio_path(path)
    comp_tag = ""
    if companion:
        try:
            comp_tag = f"{os.path.getsize(companion)}_{int(os.path.getmtime(companion))}"
        except Exception:
            comp_tag = "1"
    cache_key = _cache_key(
        path, size, mtime, f"gemini_media_desc_v4_{kind}_{src_id}_{comp_tag}"
    )
    if use_cache:
        cached = _cache_get(cache_key)
        if isinstance(cached, dict) and cached.get("ok") and cached.get("text"):
            _stats["cache_hits"] = int(_stats.get("cache_hits", 0) or 0) + 1
            out = dict(cached)
            out["source"] = (out.get("source") or "gemini") + "+cache"
            return out

    prompt = (
        _DESCRIBE_PROMPT_AUDIO if kind == "audio" else _DESCRIBE_PROMPT_VIDEO
    )
    _emit_progress(on_progress, 35, "Riassunto accessibile…")
    text, diag = _gemini_generate_media(
        path,
        prompt,
        should_abort=should_abort,
        max_output_tokens=4096,
        on_progress=on_progress,
        progress_base=38,
    )
    if not text:
        result["error"] = diag or (_gemini_last_error or "Riassunto Gemini non riuscito.")
        _stats["failures"] = int(_stats.get("failures", 0) or 0) + 1
        return result
    result["ok"] = True
    result["text"] = text
    result["source"] = diag or "gemini"
    if use_cache:
        _cache_put(cache_key, {
            "ok": True,
            "text": text,
            "error": "",
            "source": result["source"],
            "path": path,
        })
    return result


def transcribe_media_gemini(
    path: str,
    should_abort=None,
    use_cache: bool = True,
    include_timestamps: bool = False,
    on_progress=None,
) -> dict:
    """Trascrizione opt-in via Gemini. Dict: ok, text, error, source."""
    result = {
        "ok": False,
        "text": "",
        "error": "",
        "source": "",
        "path": path or "",
        "timestamps": bool(include_timestamps),
    }
    if not path or not os.path.isfile(path):
        result["error"] = "File non trovato."
        return result
    if not is_media_path(path):
        result["error"] = "Il file non è un audio/video supportato."
        return result
    if not has_gemini_api_key():
        result["error"] = (
            "Per la trascrizione serve la chiave API Gemini "
            "(Strumenti → Chiave API Gemini / Google AI Studio)."
        )
        return result
    limit_err = _check_ai_limits(path)
    if limit_err:
        result["error"] = limit_err
        return result
    tech_pre = get_media_tech_info(path)
    if tech_pre.get("silent_video") and not media_companion_audio_path(path):
        result["error"] = (
            "Questo video non ha audio: non si può trascrivere in modo affidabile "
            "(Gemini inventerebbe la telecronaca). Installa ffmpeg nel PATH "
            "(es. winget install Gyan.FFmpeg), aggiorna yt-dlp e riprova l’URL, "
            "oppure usa un file locale con audio."
        )
        return result
    try:
        size = os.path.getsize(path)
        mtime = os.path.getmtime(path)
    except Exception as e:
        result["error"] = str(e)
        return result

    ts_tag = "ts" if include_timestamps else "plain"
    src_id = (read_media_source_meta(path).get("id") or "").strip()
    companion = media_companion_audio_path(path)
    comp_tag = ""
    if companion:
        try:
            comp_tag = f"{os.path.getsize(companion)}_{int(os.path.getmtime(companion))}"
        except Exception:
            comp_tag = "1"
    cache_key = _cache_key(
        path, size, mtime, f"gemini_media_tr_v5_{ts_tag}_{src_id}_{comp_tag}"
    )
    if use_cache:
        cached = _cache_get(cache_key)
        if isinstance(cached, dict) and cached.get("ok") and cached.get("text"):
            _stats["cache_hits"] = int(_stats.get("cache_hits", 0) or 0) + 1
            out = dict(cached)
            out["source"] = (out.get("source") or "gemini") + "+cache"
            out["timestamps"] = bool(include_timestamps)
            return out

    if include_timestamps:
        prompt = _TRANSCRIBE_PROMPT_TIMESTAMPS
        try:
            tech = get_media_tech_info(path)
            dur = float(tech.get("duration_sec") or 0)
            if dur > 0:
                end_label = _format_duration(dur) or f"{int(round(dur))} s"
                # Ancora i tempi alla durata reale del file
                total = int(round(dur))
                h, rem = divmod(total, 3600)
                mi, s = divmod(rem, 60)
                end_ts = f"{h}:{mi:02d}:{s:02d}" if h else f"{mi:02d}:{s:02d}"
                prompt += (
                    f"\n\nDurata nota del file: circa {end_label} "
                    f"(timestamp finale atteso intorno a [{end_ts}]). "
                    "Distribuisci più timestamp da [00:00] fino a quel punto; "
                    "non fermarti a un solo [00:00]."
                )
        except Exception:
            pass
    else:
        prompt = _TRANSCRIBE_PROMPT
    # 65536: i modelli Flash moderni lo supportano; 8192 tagliava le rassegne lunghe.
    _emit_progress(on_progress, 62, "Trascrizione in corso…")
    text, diag = _gemini_generate_media(
        path,
        prompt,
        should_abort=should_abort,
        max_output_tokens=65536,
        on_progress=on_progress,
        progress_base=65,
    )
    if not text:
        result["error"] = diag or (_gemini_last_error or "Trascrizione Gemini non riuscita.")
        _stats["failures"] = int(_stats.get("failures", 0) or 0) + 1
        return result
    # Se i timestamp si fermano prima della fine nota: continua (max 2 riprese)
    if include_timestamps:
        try:
            tech = get_media_tech_info(path)
            dur = float(tech.get("duration_sec") or 0)
        except Exception:
            dur = 0.0
        text, diag = _continue_transcript_if_short(
            path,
            text,
            diag or "",
            duration_sec=dur,
            should_abort=should_abort,
            on_progress=on_progress,
        )
        text = _ensure_progressive_timestamps_note(text)
    result["ok"] = True
    result["text"] = text
    result["source"] = diag or "gemini"
    if use_cache:
        _cache_put(cache_key, {
            "ok": True,
            "text": text,
            "error": "",
            "source": result["source"],
            "path": path,
            "timestamps": bool(include_timestamps),
        })
    return result


def _last_transcript_timestamp_sec(text: str) -> float:
    """Ultimo [MM:SS] / [H:MM:SS] trovato nel testo (secondi), o -1."""
    all_ts = re.findall(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]", text or "")
    if not all_ts:
        return -1.0
    h_s, m_s, s_s = all_ts[-1]
    try:
        if s_s is not None and s_s != "":
            # [H:MM:SS] — groups are H, MM, SS
            return int(h_s) * 3600 + int(m_s) * 60 + int(s_s)
        # [MM:SS]
        return int(h_s) * 60 + int(m_s)
    except Exception:
        return -1.0


def _continue_transcript_if_short(
    path: str,
    text: str,
    diag: str,
    *,
    duration_sec: float,
    should_abort=None,
    max_continues: int = 2,
    on_progress=None,
) -> tuple:
    """Se l'ultimo timestamp è troppo prima della fine, chiede a Gemini di continuare."""
    body = (text or "").strip()
    dur = float(duration_sec or 0)
    if not body or dur <= 0:
        return body, diag
    low = body.lower()
    if "nessun parlato" in low or "no speech" in low:
        return body, diag
    cur_diag = diag or ""
    for n_cont in range(max(0, int(max_continues or 0))):
        if should_abort and should_abort():
            break
        last = _last_transcript_timestamp_sec(body)
        if last < 0:
            break
        # Continua se manca più del 12% o più di 45 s rispetto alla fine
        if last >= dur * 0.88 or (dur - last) <= 45:
            break
        end_total = int(round(dur))
        h, rem = divmod(end_total, 3600)
        mi, s = divmod(rem, 60)
        end_ts = f"{h}:{mi:02d}:{s:02d}" if h else f"{mi:02d}:{s:02d}"
        last_i = int(last)
        lh, lrem = divmod(last_i, 3600)
        lm, ls = divmod(lrem, 60)
        last_ts = f"{lh}:{lm:02d}:{ls:02d}" if lh else f"{lm:02d}:{ls:02d}"
        tail = "\n".join(body.splitlines()[-12:])
        cont_prompt = (
            "Continua la trascrizione dello STESSO audio/video in italiano, "
            "con timestamp progressivi [MM:SS], ESATTAMENTE da dove si è "
            f"interrotta (dopo circa [{last_ts}]). "
            f"Prosegui fino a circa [{end_ts}] (fine del file). "
            "Non ripetere le parti già trascritte. "
            "Solo parlato/cantato; niente riassunto.\n\n"
            "Ultime righe già ottenute (contesto, non ripetere):\n"
            f"{tail}"
        )
        _emit_progress(
            on_progress,
            min(78 + n_cont * 8, 92),
            f"Ripresa trascrizione da [{last_ts}]…",
        )
        more, more_diag = _gemini_generate_media(
            path,
            cont_prompt,
            should_abort=should_abort,
            max_output_tokens=65536,
            on_progress=on_progress,
            progress_base=min(80 + n_cont * 5, 90),
        )
        more = (more or "").strip()
        if not more:
            break
        # Evita doppio inizio identico
        if more[:80] and more[:80] in body:
            # prova a tagliare la prima riga duplicata
            lines = more.splitlines()
            more = "\n".join(lines[1:]).strip() if len(lines) > 1 else more
        if not more:
            break
        body = body.rstrip() + "\n" + more
        if more_diag:
            cur_diag = f"{cur_diag}+cont" if cur_diag else more_diag
        # Se non avanza il timestamp, stop
        new_last = _last_transcript_timestamp_sec(body)
        if new_last <= last + 5:
            break
    return body, cur_diag


def _ensure_progressive_timestamps_note(text: str) -> str:
    """Se c'è un solo [00:00], avvisa: il modello non ha scandito i tempi."""
    body = (text or "").strip()
    if not body:
        return body
    low = body.lower()
    # Niente parlato / niente timestamp: non spaventare con note File API
    if (
        "nessun parlato" in low
        or "no speech" in low
        or "nessuna voce" in low
        or "non rilevato parlato" in low
    ):
        return body
    all_ts = re.findall(r"\[\d{1,2}:\d{2}(?::\d{2})?\]", body)
    if not all_ts:
        return body
    if len(all_ts) <= 1:
        note = (
            "\n\n(Nota: il modello ha restituito un solo timestamp iniziale. "
            "I tempi progressivi non sono stati scanditi in questa passata; "
            "riprova, oppure usa la trascrizione senza timestamp. "
            "La sincronizzazione parola-per-parola precisa arriverà meglio "
            "con motori dedicati / File API sui file lunghi.)"
        )
        return body + note
    # Se tutti uguali a 00:00
    if all(t in ("[00:00]", "[0:00]", "[0:00:00]", "[00:00:00]") for t in all_ts):
        note = (
            "\n\n(Nota: i timestamp non avanzano oltre l'inizio. "
            "Riprova per una scansione progressiva.)"
        )
        return body + note
    return body


def format_full_media_report(
    path: str,
    *,
    include_tech: bool = True,
    include_describe: bool = True,
    include_transcript: bool = False,
    include_timestamps: bool = False,
    should_abort=None,
    on_progress=None,
) -> str:
    """Report unificato «Tutto sull'audio/video»."""
    kind = media_kind(path)
    kind_it = {"audio": "Audio", "video": "Video"}.get(kind, "Media")
    parts = [f"{kind_it}: {os.path.basename(path) or 'file'}"]
    src_meta = read_media_source_meta(path)
    if src_meta.get("title") or src_meta.get("id") or src_meta.get("url"):
        if src_meta.get("title"):
            parts.append(f"Titolo: {src_meta['title']}")
        if src_meta.get("id"):
            parts.append(f"ID: {src_meta['id']}")
        u = src_meta.get("webpage_url") or src_meta.get("url") or ""
        if u:
            parts.append(f"URL: {u}")
    parts.append("")
    if include_tech:
        if should_abort and should_abort():
            return "\n".join(parts).strip() + "\n(Annullato.)"
        _emit_progress(on_progress, 12, "Scheda tecnica…")
        try:
            tech_block = format_media_tech_sheet(get_media_tech_info(path))
            if tech_block:
                parts.extend(["=== Scheda tecnica ===", "", tech_block.strip(), ""])
        except Exception as e:
            parts.extend(["=== Scheda tecnica ===", "", f"(Errore: {e})", ""])
    if include_describe:
        if should_abort and should_abort():
            return "\n".join(parts).strip() + "\n(Annullato.)"
        desc = describe_media_gemini(
            path,
            should_abort=should_abort,
            use_cache=True,
            on_progress=on_progress,
        )
        if desc.get("ok") and (desc.get("text") or "").strip():
            parts.extend([
                "=== Riassunto accessibile ===",
                "",
                (desc.get("text") or "").strip(),
                "",
            ])
        else:
            parts.extend([
                "=== Riassunto accessibile ===",
                f"(Non disponibile: {desc.get('error') or 'errore sconosciuto'})",
                "",
            ])
    if include_transcript:
        if should_abort and should_abort():
            return "\n".join(parts).strip() + "\n(Annullato.)"
        tr = transcribe_media_gemini(
            path,
            should_abort=should_abort,
            use_cache=True,
            include_timestamps=bool(include_timestamps),
            on_progress=on_progress,
        )
        section = (
            "=== Trascrizione (con timestamp) ==="
            if include_timestamps
            else "=== Trascrizione ==="
        )
        if tr.get("ok") and (tr.get("text") or "").strip():
            parts.extend([
                section,
                "",
                (tr.get("text") or "").strip(),
                "",
            ])
        else:
            parts.extend([
                section,
                f"(Non disponibile: {tr.get('error') or 'errore sconosciuto'})",
                "",
            ])
    _emit_progress(on_progress, 100, "Analisi audio/video completata.")
    return "\n".join(parts).strip()


_WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
# Domini dove di solito serve yt-dlp (pagina HTML, non file .mp4 diretto).
# yt-dlp supporta molte altre piattaforme: se manca qui, si prova comunque
# il download HTTP e, se arriva HTML, un messaggio guida l'utente.
_PAGE_MEDIA_HOSTS = (
    "youtube.com", "youtu.be", "m.youtube.com", "music.youtube.com",
    "vimeo.com",
    "tiktok.com", "vm.tiktok.com",
    "instagram.com",
    "facebook.com", "fb.watch", "fb.com", "m.facebook.com",
    "x.com", "twitter.com", "mobile.twitter.com",
    "linkedin.com",
    "dailymotion.com", "dai.ly",
    "twitch.tv", "clips.twitch.tv",
    "reddit.com", "v.redd.it",
)


def is_likely_direct_media_url(url: str) -> bool:
    path = urllib.parse.urlparse(url or "").path.lower()
    return any(path.endswith(ext) for ext in MEDIA_EXTS)


def is_page_media_url(url: str) -> bool:
    host = (urllib.parse.urlparse(url or "").netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return any(host == h or host.endswith("." + h) for h in _PAGE_MEDIA_HOSTS)


def _sniff_media_ext(data: bytes, ctype: str, url: str) -> str:
    ctype_l = (ctype or "").lower()
    path = urllib.parse.urlparse(url or "").path.lower()
    for ext in MEDIA_EXTS:
        if path.endswith(ext):
            return ext
    mime_map = {
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/aac": ".aac",
        "audio/flac": ".flac",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/wave": ".wav",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
        "video/x-matroska": ".mkv",
    }
    for key, ext in mime_map.items():
        if key in ctype_l:
            return ext
    if data.startswith(b"ID3") or (
        len(data) > 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0
    ):
        return ".mp3"
    if len(data) > 12 and data[4:8] == b"ftyp":
        return ".mp4"
    if data.startswith(b"OggS"):
        return ".ogg"
    if data.startswith(b"RIFF") and b"WAVE" in data[:16]:
        return ".wav"
    if data.startswith(b"\x1aE\xdf\xa3"):
        return ".mkv"
    return ""


def cleanup_temp_media(path: str) -> None:
    """Elimina file temp creati da materialize_media_* (prefisso rtad_media_)."""
    if not path:
        return
    base = os.path.basename(path)
    if not base.startswith("rtad_media_"):
        return
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass
    for side in (path + ".rtad_src.json",):
        try:
            if os.path.isfile(side):
                os.remove(side)
        except Exception:
            pass
    for ext in (".m4a", ".webm", ".opus", ".mp3", ".aac", ".mp4"):
        cand = path + ".rtad_audio" + ext
        try:
            if os.path.isfile(cand):
                os.remove(cand)
        except Exception:
            pass


def _save_media_temp(data: bytes, ext: str) -> dict:
    out = {"ok": False, "path": "", "error": ""}
    try:
        fd, tmp = tempfile.mkstemp(suffix=ext or ".bin", prefix="rtad_media_")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        out["ok"] = True
        out["path"] = tmp
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


def ytdlp_available() -> bool:
    """True se yt-dlp è richiamabile dal PATH."""
    try:
        proc = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return proc.returncode == 0
    except Exception:
        return False


def ytdlp_install_hint() -> str:
    """Breve guida installazione yt-dlp (Windows) per messaggi utente."""
    return (
        "Per scaricare da YouTube, TikTok, Instagram, X, Facebook, LinkedIn, "
        "Vimeo, ecc. serve yt-dlp nel PATH. "
        "Su Windows (PowerShell come amministratore o utente): "
        "winget install yt-dlp.yt-dlp "
        "oppure: pip install -U yt-dlp "
        "Per unire video+audio (Shorts/YouTube moderni) serve anche ffmpeg: "
        "winget install Gyan.FFmpeg "
        "Poi chiudi e riapri RTAD/NVDA. "
        "In alternativa usa un link diretto al file (.mp4/.mp3)."
    )


def _ffmpeg_available() -> bool:
    """True se ffmpeg è nel PATH (serve a yt-dlp per il merge)."""
    return bool(shutil.which("ffmpeg"))


def check_ytdlp_status(outdated_after_days: int = 90) -> dict:
    """Stato yt-dlp: available, version, age_days, outdated, message."""
    out = {
        "available": False,
        "version": "",
        "age_days": None,
        "outdated": False,
        "message": "",
    }
    try:
        proc = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        out["message"] = "yt-dlp non trovato. " + ytdlp_install_hint()
        return out
    except Exception as e:
        out["message"] = f"Impossibile verificare yt-dlp: {e}"
        return out
    if proc.returncode != 0:
        out["message"] = "yt-dlp non risponde correttamente. " + ytdlp_install_hint()
        return out
    ver = (proc.stdout or proc.stderr or "").strip().splitlines()[0].strip()
    # Esempi: 2026.08.19 oppure stable@2026.08.19
    m = re.search(r"(20\d{2})\.(\d{1,2})\.(\d{1,2})", ver)
    out["available"] = True
    out["version"] = ver
    if m:
        try:
            import datetime as _dt
            built = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            age = (_dt.date.today() - built).days
            out["age_days"] = age
            if age >= int(outdated_after_days or 90):
                out["outdated"] = True
                out["message"] = (
                    f"yt-dlp {ver}: ha circa {age} giorni "
                    f"(oltre {outdated_after_days}). Consigliato aggiornare."
                )
            else:
                out["message"] = (
                    f"yt-dlp {ver}: ok (circa {age} giorni)."
                )
            return out
        except Exception:
            pass
    out["message"] = f"yt-dlp presente: {ver}."
    return out


def update_ytdlp(timeout: int = 180) -> dict:
    """Esegue «yt-dlp -U». Dict: ok, message, version_before, version_after."""
    before = check_ytdlp_status()
    out = {
        "ok": False,
        "message": "",
        "version_before": before.get("version") or "",
        "version_after": "",
    }
    if not before.get("available"):
        out["message"] = before.get("message") or ytdlp_install_hint()
        return out
    try:
        proc = subprocess.run(
            ["yt-dlp", "-U"],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:
        out["message"] = f"Aggiornamento non riuscito: {e}"
        return out
    after = check_ytdlp_status()
    out["version_after"] = after.get("version") or ""
    log = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        out["message"] = (
            "Aggiornamento yt-dlp non riuscito"
            + (f": {log[:240]}" if log else ".")
        )
        return out
    out["ok"] = True
    if out["version_before"] and out["version_after"] and (
        out["version_before"] != out["version_after"]
    ):
        out["message"] = (
            f"yt-dlp aggiornato: {out['version_before']} → {out['version_after']}."
        )
    else:
        out["message"] = (
            f"yt-dlp già aggiornato ({out['version_after'] or out['version_before']})."
            + (f" {log[:160]}" if log else "")
        )
    return out


def _ytdlp_format_prefer_under_limit() -> str:
    """Muxati se esistono; altrimenti bv+ba (merge ffmpeg o coppia per Gemini).

    Non usare mai «best[filesize]»: su Shorts sceglie spesso solo video muto
    e Gemini inventa la telecronaca.
    """
    lim = int(MAX_MEDIA_BYTES)
    # Lascia margine per la traccia audio (~2 MB) nel tetto combinato.
    vlim = max(int(lim * 0.85), lim - 2 * 1024 * 1024)
    return (
        f"best[vcodec!=none][acodec!=none][filesize<={lim}]/"
        f"best[vcodec!=none][acodec!=none][filesize_approx<={lim}]/"
        f"bv*[filesize<={vlim}]+ba/"
        f"bv*[filesize_approx<={vlim}]+ba/"
        f"bestaudio[ext=m4a][filesize<={lim}]/"
        f"bestaudio[filesize<={lim}]/"
        f"bestaudio[filesize_approx<={lim}]/"
        f"worstaudio/bestaudio"
    )


def _media_role_hint(path: str) -> str:
    """'audio' | 'video' | 'muxed' | '' da container/estensione."""
    ext = os.path.splitext(path)[1].lower()
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in (".mp4", ".m4v", ".mov", ".3gp"):
        tech = _mp4_tech(path)
        ha = bool(tech.get("has_audio"))
        hv = bool(tech.get("has_video") or tech.get("frame_width"))
        if ha and hv:
            return "muxed"
        if ha and not hv:
            return "audio"
        if hv:
            return "video"
    if ext in (".webm", ".mkv"):
        tech = _webm_tech(path)
        if tech.get("audio_codec") and not tech.get("frame_width"):
            return "audio"
        if tech.get("frame_width") or tech.get("duration_sec"):
            # WebM video-only tipico DASH
            if tech.get("audio_codec"):
                return "muxed"
            return "video"
    if ext in VIDEO_EXTS:
        return "video"
    return ""


def _youtube_id_from_url(url: str) -> str:
    """Estrae l'id video da URL YouTube/Shorts (vuoto se non riconosciuto)."""
    try:
        p = urllib.parse.urlparse(url or "")
        host = (p.netloc or "").lower()
        path_u = p.path or ""
        if "youtu.be" in host:
            return (path_u.strip("/").split("/") or [""])[0]
        if "youtube.com" in host or "youtube-nocookie.com" in host:
            if "/shorts/" in path_u:
                return path_u.split("/shorts/")[-1].split("/")[0].split("?")[0]
            qs = urllib.parse.parse_qs(p.query or "")
            vids = qs.get("v") or []
            if vids:
                return (vids[0] or "").strip()
            if "/embed/" in path_u:
                return path_u.split("/embed/")[-1].split("/")[0]
            if "/live/" in path_u:
                return path_u.split("/live/")[-1].split("/")[0]
    except Exception:
        pass
    return ""


_YTDLP_FRAG_RE = re.compile(r"\.f\d+\.", re.IGNORECASE)


def _pick_ytdlp_outputs(tmpdir: str) -> dict:
    """Sceglie muxato, oppure coppia video+audio (senza ffmpeg).

    Returns: {ok, path, audio_path, error}
    """
    out = {"ok": False, "path": "", "audio_path": "", "error": ""}
    media = []
    partials = False
    try:
        for name in os.listdir(tmpdir):
            p = os.path.join(tmpdir, name)
            if not os.path.isfile(p):
                continue
            low = name.lower()
            if low.endswith(".part") or low.endswith(".ytdl"):
                partials = True
                continue
            if low.endswith(".json") or low.endswith(".txt"):
                continue
            if is_media_path(p):
                media.append(p)
    except Exception as e:
        out["error"] = f"Lettura cartella download: {e}"
        return out
    if not media:
        if partials:
            out["error"] = (
                f"Download interrotto: nessun formato entro "
                f"{_format_size(MAX_MEDIA_BYTES)}."
            )
        else:
            out["error"] = "yt-dlp non ha prodotto un file media utilizzabile."
        return out

    # 1) File già completi (nome senza .fXXX.)
    complete = [p for p in media if not _YTDLP_FRAG_RE.search(os.path.basename(p))]
    if complete:
        best = max(complete, key=lambda p: os.path.getsize(p))
        role = _media_role_hint(best)
        if role == "video" and not media_companion_audio_path(best):
            # Un solo «completo» ma muto: cerca audio tra i frammenti
            audios = [p for p in media if _media_role_hint(p) == "audio"]
            if audios:
                out["ok"] = True
                out["path"] = best
                out["audio_path"] = max(audios, key=lambda p: os.path.getsize(p))
                return out
            out["error"] = (
                "Scaricato solo video senza audio. Su molti Shorts YouTube "
                "serve ffmpeg nel PATH (winget install Gyan.FFmpeg) per "
                "unire le tracce, altrimenti la trascrizione sarebbe inventata."
            )
            return out
        out["ok"] = True
        out["path"] = best
        return out

    # 2) Frammenti .fXXX.: abbina video + audio (niente merge)
    videos = []
    audios = []
    muxed_frags = []
    for p in media:
        role = _media_role_hint(p)
        if role == "muxed":
            muxed_frags.append(p)
        elif role == "audio":
            audios.append(p)
        elif role == "video":
            videos.append(p)
    if muxed_frags:
        out["ok"] = True
        out["path"] = max(muxed_frags, key=lambda p: os.path.getsize(p))
        return out
    if videos and audios:
        v = max(videos, key=lambda p: os.path.getsize(p))
        a = max(audios, key=lambda p: os.path.getsize(p))
        try:
            if os.path.getsize(v) + os.path.getsize(a) > MAX_MEDIA_BYTES:
                out["error"] = (
                    f"Video+audio scaricati oltre il limite "
                    f"({_format_size(MAX_MEDIA_BYTES)})."
                )
                return out
        except Exception:
            pass
        out["ok"] = True
        out["path"] = v
        out["audio_path"] = a
        return out
    if audios and not videos:
        out["ok"] = True
        out["path"] = max(audios, key=lambda p: os.path.getsize(p))
        return out
    out["error"] = (
        "Download incompleto: video e audio separati. "
        "Installa ffmpeg nel PATH (winget install Gyan.FFmpeg) "
        "oppure usa un file locale già completo."
    )
    return out


def _write_media_source_sidecar(media_path: str, meta: dict) -> None:
    """Accanto al temp: JSON con URL/titolo/id per la scheda tecnica."""
    if not media_path or not meta:
        return
    side = media_path + ".rtad_src.json"
    try:
        with open(side, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=0)
    except Exception:
        pass


def read_media_source_meta(media_path: str) -> dict:
    """Legge sidecar sorgente URL (se presente)."""
    if not media_path:
        return {}
    side = media_path + ".rtad_src.json"
    try:
        with open(side, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _materialize_via_ytdlp(url: str, timeout: int = 180, on_progress=None) -> dict:
    """Se yt-dlp è nel PATH, scarica il media migliore entro MAX_MEDIA_BYTES."""
    out = {
        "ok": False,
        "path": "",
        "error": "",
        "url": url,
        "via": "yt-dlp",
        "source_id": "",
        "source_title": "",
        "source_webpage": "",
    }
    _emit_progress(on_progress, 5, "Download da pagina (yt-dlp)…")
    try:
        tmpdir = tempfile.mkdtemp(prefix="rtad_media_dl_")
    except Exception as e:
        out["error"] = f"Cartella temporanea: {e}"
        return out
    out_tmpl = os.path.join(tmpdir, "rtad_media_%(id)s.%(ext)s")
    meta_txt = os.path.join(tmpdir, "rtad_meta.txt")
    expect_id = _youtube_id_from_url(url)
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--no-cache-dir",
        "--force-overwrites",
        "--merge-output-format",
        "mp4",
        "-f",
        _ytdlp_format_prefer_under_limit(),
        "--max-filesize",
        str(MAX_MEDIA_BYTES),
        "-o",
        out_tmpl,
        "--print-to-file",
        "%(id)s\t%(title)s\t%(webpage_url)s",
        meta_txt,
        "--",
        url,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        out["error"] = (
            "URL di pagina social/video: yt-dlp non trovato. "
            + ytdlp_install_hint()
        )
        return out
    except subprocess.TimeoutExpired:
        out["error"] = "Download yt-dlp scaduto (timeout)."
        return out
    except Exception as e:
        out["error"] = f"yt-dlp: {e}"
        return out
    err = (proc.stderr or proc.stdout or "").strip()
    low = err.lower()
    try:
        if os.path.isfile(meta_txt):
            line = open(meta_txt, encoding="utf-8", errors="replace").read().strip()
            parts = line.split("\t")
            if parts:
                out["source_id"] = (parts[0] or "").strip()
            if len(parts) > 1:
                out["source_title"] = (parts[1] or "").strip()
            if len(parts) > 2:
                out["source_webpage"] = (parts[2] or "").strip()
    except Exception:
        pass
    # Anche se il merge ffmpeg fallisce, spesso restano video+audio usabili.
    picked = _pick_ytdlp_outputs(tmpdir)
    if not picked.get("ok"):
        if proc.returncode != 0:
            if "max-filesize" in low or "larger than max-filesize" in low:
                tip = (
                    f" Il file supera il limite attuale "
                    f"({_format_size(MAX_MEDIA_BYTES)}). "
                    "Prova un video più corto oppure scaricalo a mano "
                    "e aprilo come file locale (scheda tecnica resta disponibile)."
                )
            elif "sign in" in low or "login" in low or "private" in low:
                tip = (
                    " Il video potrebbe richiedere accesso (account / privato). "
                    "Prova un video pubblico o un link diretto al file."
                )
            elif "drm" in low:
                tip = " Contenuto protetto (DRM) o non scaricabile."
            elif "ffmpeg" in low:
                tip = (
                    " Serve ffmpeg nel PATH per unire video e audio "
                    "(winget install Gyan.FFmpeg)."
                )
            else:
                tip = (
                    f" Limite attuale download/analisi: max "
                    f"{_format_size(MAX_MEDIA_BYTES)} / "
                    f"{_format_duration(MAX_MEDIA_DURATION_SEC)}."
                )
            brief = err[:180].replace("\n", " ") if err else ""
            out["error"] = (
                "Download da pagina non riuscito"
                + (f" ({brief})" if brief else ".")
                + tip
            )
        else:
            out["error"] = (
                picked.get("error")
                or "yt-dlp non ha prodotto un file media utilizzabile."
            )
        return out
    src = picked["path"]
    audio_src = (picked.get("audio_path") or "").strip()
    got_id = (out.get("source_id") or "").strip()
    if expect_id and got_id and expect_id != got_id:
        out["error"] = (
            f"L'URL chiedeva il video «{expect_id}» ma yt-dlp ha restituito "
            f"«{got_id}». Riprova o aggiorna yt-dlp."
        )
        return out
    try:
        size = os.path.getsize(src)
    except Exception:
        size = 0
    audio_size = 0
    if audio_src:
        try:
            audio_size = os.path.getsize(audio_src)
        except Exception:
            audio_size = 0
    if size <= 0 or size > MAX_MEDIA_BYTES:
        out["error"] = (
            f"File scaricato fuori limiti "
            f"(max {_format_size(MAX_MEDIA_BYTES)})."
        )
        return out
    if audio_size and size + audio_size > MAX_MEDIA_BYTES:
        out["error"] = (
            f"Video+audio oltre il limite "
            f"(max {_format_size(MAX_MEDIA_BYTES)})."
        )
        return out
    ext = os.path.splitext(src)[1].lower() or ".mp4"
    try:
        with open(src, "rb") as f:
            data = f.read()
    except Exception as e:
        out["error"] = str(e)
        return out
    saved = _save_media_temp(data, ext)
    saved_audio_path = ""
    if saved.get("ok") and audio_src and audio_size > 0:
        aext = os.path.splitext(audio_src)[1].lower() or ".m4a"
        try:
            with open(audio_src, "rb") as af:
                adata = af.read()
            dest_a = saved["path"] + ".rtad_audio" + aext
            with open(dest_a, "wb") as af:
                af.write(adata)
            saved_audio_path = dest_a
        except Exception:
            saved_audio_path = ""
    try:
        for name in os.listdir(tmpdir):
            try:
                os.remove(os.path.join(tmpdir, name))
            except Exception:
                pass
        os.rmdir(tmpdir)
    except Exception:
        pass
    if not saved.get("ok"):
        out["error"] = saved.get("error") or "Salvataggio non riuscito."
        return out
    out["ok"] = True
    out["path"] = saved["path"]
    _write_media_source_sidecar(
        saved["path"],
        {
            "url": url,
            "id": out.get("source_id") or expect_id,
            "title": out.get("source_title") or "",
            "webpage_url": out.get("source_webpage") or url,
            "via": "yt-dlp",
            "audio_path": saved_audio_path,
            "ffmpeg": _ffmpeg_available(),
        },
    )
    _emit_progress(on_progress, 28, "Download completato.")
    return out



def materialize_media_from_url(url: str, timeout: int = 90, on_progress=None) -> dict:
    """Scarica audio/video da URL http(s) su file temp. Dict: ok, path, error, url.

    - Link diretti (.mp4, .mp3, …): download HTTP.
    - Pagine (YouTube, …): prova yt-dlp se installato; altrimenti messaggio chiaro.
    Limiti = stessi di Gemini inline (dimensione).
    """
    out = {"ok": False, "path": "", "error": "", "url": (url or "").strip()}
    u = out["url"]
    if not u:
        out["error"] = "URL vuoto."
        return out
    if not (u.lower().startswith("http://") or u.lower().startswith("https://")):
        out["error"] = "Serve un URL http o https."
        return out

    if is_page_media_url(u) and not is_likely_direct_media_url(u):
        return _materialize_via_ytdlp(
            u, timeout=max(timeout, 180), on_progress=on_progress
        )

    _emit_progress(on_progress, 5, "Download file diretto…")
    try:
        req = urllib.request.Request(
            u,
            headers={
                "User-Agent": _WEB_UA,
                "Accept": "audio/*,video/*,*/*;q=0.8",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = resp.headers.get("Content-Type", "") or ""
            data = resp.read(MAX_MEDIA_BYTES + 1)
            final_url = resp.geturl() or u
    except urllib.error.HTTPError as e:
        # Pagine che rispondono HTML: prova yt-dlp
        if e.code in (403, 404) and is_page_media_url(u):
            return _materialize_via_ytdlp(
                u, timeout=max(timeout, 180), on_progress=on_progress
            )
        out["error"] = f"HTTP {e.code}: download media non riuscito."
        return out
    except Exception as e:
        out["error"] = f"Download non riuscito: {e}"
        return out

    if not data:
        out["error"] = "Risposta vuota dal server."
        return out
    if len(data) > MAX_MEDIA_BYTES:
        out["error"] = (
            f"File troppo grande da scaricare "
            f"(max {_format_size(MAX_MEDIA_BYTES)})."
        )
        return out
    ctype_l = ctype.lower()
    if "text/html" in ctype_l or data.lstrip()[:15].lower().startswith(b"<!doctype html"):
        if is_page_media_url(final_url) or is_page_media_url(u):
            return _materialize_via_ytdlp(
                u, timeout=max(timeout, 180), on_progress=on_progress
            )
        out["error"] = (
            "L'URL punta a una pagina web, non a un file audio/video. "
            + ytdlp_install_hint()
        )
        return out
    if "application/json" in ctype_l and data.lstrip()[:1] in (b"{", b"["):
        out["error"] = "L'URL non punta a un file media (ricevuto JSON)."
        return out

    ext = _sniff_media_ext(data, ctype, final_url)
    if not ext:
        out["error"] = "Formato audio/video non riconosciuto dall'URL."
        return out
    saved = _save_media_temp(data, ext)
    if not saved.get("ok"):
        out["error"] = saved.get("error") or "Salvataggio media non riuscito."
        return out
    out["ok"] = True
    out["path"] = saved["path"]
    out["url"] = final_url
    _emit_progress(on_progress, 28, "Download completato.")
    return out
