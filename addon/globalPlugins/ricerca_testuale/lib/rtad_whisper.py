# -*- coding: utf-8 -*-
"""Trascrizione sul PC con whisper.cpp. Il modello non sta nel programma.

Si scarica al primo uso, in una cartella dell'utente condivisa da
Standalone e Add-on. Gemini resta il motore quando questa via è spenta.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
import zipfile

WHISPER_TAG = "b5454"
WHISPER_ZIP_URL = (
    "https://github.com/ggml-org/whisper.cpp/releases/download/"
    f"{WHISPER_TAG}/whisper-bin-x64.zip"
)
WHISPER_ZIP_BYTES = 8928640
MODEL_NAME = "ggml-small.bin"
MODEL_URL = (
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/" + MODEL_NAME
)
# Il file pubblicato pesa 487 MB. Sotto questa soglia è uno scaricamento rotto.
MODEL_MIN_BYTES = 400_000_000
MAX_FILE_SEC = 20 * 60
MAX_FOLDER_FILES = 5
RUN_TIMEOUT_SEC = 40 * 60

MSG_TOO_LONG = "Questo file dura più di 20 minuti. Whisper si ferma qui."
MSG_NO_DURATION = (
    "Non riesco a leggere la durata. Whisper accetta un file fino a 20 minuti."
)
MSG_NEED_FFMPEG = (
    "Per questo formato serve ffmpeg nel PATH. "
    "Esempio: winget install Gyan.FFmpeg."
)
MSG_NO_BIN = "Manca il programma Whisper e non sono riuscito a scaricarlo."
MSG_NO_MODEL = "Manca il modello Whisper e non sono riuscito a scaricarlo."
MSG_DOWNLOAD_BIN = "Scaricamento del programma Whisper in corso."
MSG_DOWNLOAD_MODEL = "Scaricamento del modello Whisper in corso."
MSG_BIN_READY = "Programma Whisper pronto."
MSG_MODEL_READY = "Modello Whisper pronto."
MSG_RUNNING = "Trascrizione Whisper in corso."
MSG_INTERRUPTED = "Trascrizione Whisper interrotta."
MSG_TIMEOUT = (
    "La trascrizione sul PC ha superato il tempo previsto. Whisper si ferma qui."
)
MSG_NO_AUDIO = "Questo video non ha audio: non si può trascrivere."
MSG_EMPTY = "Nessun parlato rilevato."
MSG_FAIL = "Trascrizione Whisper non riuscita."
MSG_SAVED = "Testo salvato: {name}"
MSG_SIDECAR_KEPT = "Il resoconto accanto c'era già. Resta com'era."

SPOKEN_RESULTS = (
    MSG_TOO_LONG,
    MSG_NO_DURATION,
    MSG_NEED_FFMPEG,
    MSG_NO_BIN,
    MSG_NO_MODEL,
    MSG_INTERRUPTED,
    MSG_TIMEOUT,
    MSG_NO_AUDIO,
    MSG_EMPTY,
    MSG_FAIL,
)

_CREATE_NO_WINDOW = 0x08000000
_UA = "RTAD"


def attach_sidecar(body: str, file_path: str, delete_after: bool = False):
    """Scrive nome.rtad.txt se manca. Non sovrascrive un resoconto già presente."""
    text = body or ""
    if delete_after or not file_path or not os.path.isfile(file_path):
        return text, ""
    if os.path.basename(file_path).lower().startswith("rtad_media_"):
        return text, ""
    dest = os.path.splitext(os.path.abspath(file_path))[0] + ".rtad.txt"
    if os.path.isfile(dest):
        msg = MSG_SIDECAR_KEPT
        if msg not in text:
            text = text.rstrip() + "\n\n" + msg
        return text, msg
    try:
        with open(dest, "w", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
    except OSError as exc:
        msg = f"Testo non salvato: {exc}"
        return text.rstrip() + "\n\n" + msg, msg
    msg = MSG_SAVED.format(name=os.path.basename(dest))
    return text.rstrip() + "\n\n" + msg, msg


def msg_folder_cap(kept: int, total: int) -> str:
    left = max(0, int(total) - int(kept))
    return f"Whisper: {int(kept)} file su {int(total)}. Non entrati: {left}."


def cap_folder(paths, limit: int = MAX_FOLDER_FILES):
    items = list(paths or [])
    if len(items) <= limit:
        return items, []
    return items[:limit], items[limit:]


def duration_error(duration_sec) -> str:
    try:
        dur = float(duration_sec or 0)
    except (TypeError, ValueError):
        dur = 0.0
    if dur <= 0:
        return MSG_NO_DURATION
    if dur > MAX_FILE_SEC:
        return MSG_TOO_LONG
    return ""


def whisper_home() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "RTAD", "whisper")
    os.makedirs(path, exist_ok=True)
    return path


def _emit(on_progress, percent, message: str) -> None:
    if not callable(on_progress):
        return
    try:
        on_progress(int(percent), message)
    except Exception:
        pass


def _download(url: str, dest: str, *, on_progress, should_abort, label: str, min_bytes: int) -> None:
    part = dest + ".part"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    got = 0
    last_pct = -1
    last_t = 0.0
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            with open(part, "wb") as handle:
                while True:
                    if should_abort and should_abort():
                        raise InterruptedError(MSG_INTERRUPTED)
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    got += len(chunk)
                    now = time.time()
                    if total > 0:
                        pct = int(min(99, round(100.0 * got / total)))
                    else:
                        pct = 10
                    if pct != last_pct and (pct - last_pct >= 2 or now - last_t >= 0.4):
                        last_pct = pct
                        last_t = now
                        _emit(on_progress, pct, label)
        if got < min_bytes:
            raise OSError(MSG_FAIL)
        os.replace(part, dest)
    except Exception:
        try:
            if os.path.isfile(part):
                os.remove(part)
        except OSError:
            pass
        raise


def _safe_extract(zip_path: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    root = os.path.normpath(dest_dir)
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            name = (info.filename or "").replace("\\", "/")
            if not name or name.endswith("/"):
                continue
            if name.startswith("/") or ".." in name.split("/"):
                continue
            target = os.path.normpath(os.path.join(dest_dir, name))
            if not target.startswith(root):
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with archive.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
    for dirpath, _dirs, files in os.walk(dest_dir):
        for name in files:
            if name.lower() == "whisper-cli.exe":
                return os.path.join(dirpath, name)
    return ""


def ensure_runtime(*, on_progress=None, should_abort=None) -> dict:
    """Programma e modello small. Scarica solo ciò che manca."""
    home = whisper_home()
    bin_dir = os.path.join(home, "bin")
    cli = ""
    if os.path.isdir(bin_dir):
        for dirpath, _dirs, files in os.walk(bin_dir):
            for name in files:
                if name.lower() == "whisper-cli.exe":
                    cli = os.path.join(dirpath, name)
                    break
            if cli:
                break
    if not cli:
        _emit(on_progress, 2, MSG_DOWNLOAD_BIN)
        zip_path = os.path.join(home, "whisper-bin.zip")
        try:
            _download(
                WHISPER_ZIP_URL,
                zip_path,
                on_progress=on_progress,
                should_abort=should_abort,
                label=MSG_DOWNLOAD_BIN,
                min_bytes=1_000_000,
            )
            cli = _safe_extract(zip_path, bin_dir)
        except InterruptedError:
            return {"ok": False, "error": MSG_INTERRUPTED, "cli": "", "model": ""}
        except Exception:
            return {"ok": False, "error": MSG_NO_BIN, "cli": "", "model": ""}
        finally:
            try:
                if os.path.isfile(zip_path):
                    os.remove(zip_path)
            except OSError:
                pass
        if not cli:
            return {"ok": False, "error": MSG_NO_BIN, "cli": "", "model": ""}
        _emit(on_progress, 8, MSG_BIN_READY)
    model = os.path.join(home, MODEL_NAME)
    try:
        have = os.path.getsize(model) if os.path.isfile(model) else 0
    except OSError:
        have = 0
    if have < MODEL_MIN_BYTES:
        try:
            if os.path.isfile(model):
                os.remove(model)
        except OSError:
            pass
        _emit(on_progress, 10, MSG_DOWNLOAD_MODEL)
        try:
            _download(
                MODEL_URL,
                model,
                on_progress=on_progress,
                should_abort=should_abort,
                label=MSG_DOWNLOAD_MODEL,
                min_bytes=MODEL_MIN_BYTES,
            )
        except InterruptedError:
            return {"ok": False, "error": MSG_INTERRUPTED, "cli": cli, "model": ""}
        except Exception:
            return {"ok": False, "error": MSG_NO_MODEL, "cli": cli, "model": ""}
        _emit(on_progress, 30, MSG_MODEL_READY)
    return {"ok": True, "error": "", "cli": cli, "model": model}


def _parse_clock(raw: str) -> float:
    text = (raw or "").strip().replace(",", ".")
    if not text:
        return 0.0
    parts = text.split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return 0.0
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 1:
        return nums[0]
    return 0.0


def _segment_start(item: dict) -> float:
    stamps = item.get("timestamps") or {}
    if isinstance(stamps, dict):
        clock = stamps.get("from")
        if isinstance(clock, str) and clock.strip():
            return _parse_clock(clock)
    offsets = item.get("offsets") or {}
    if isinstance(offsets, dict) and offsets.get("from") is not None:
        try:
            # whisper.cpp conta in decimi di secondo
            return float(offsets["from"]) / 100.0
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(item.get("start") or 0)
    except (TypeError, ValueError):
        return 0.0


def segments_from_json(data) -> list:
    if isinstance(data, dict):
        items = data.get("transcription") or data.get("segments") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = (item.get("text") or "").strip()
        if not text:
            continue
        out.append({"start": _segment_start(item), "text": text})
    return out


def format_segments(segments, include_timestamps: bool) -> str:
    lines = []
    for seg in segments or []:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        if include_timestamps:
            sec = max(0, int(seg.get("start") or 0))
            minutes, seconds = divmod(sec, 60)
            lines.append(f"[{minutes:02d}:{seconds:02d}] {text}")
        else:
            lines.append(text)
    return "\n".join(lines).strip()


def _cache_file(path: str, include_timestamps: bool) -> str:
    try:
        size = os.path.getsize(path)
        mtime = int(os.path.getmtime(path))
    except OSError:
        size, mtime = 0, 0
    raw = f"{path}|{size}|{mtime}|{int(bool(include_timestamps))}|{MODEL_NAME}|{WHISPER_TAG}"
    key = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()
    folder = os.path.join(whisper_home(), "cache")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, key + ".json")


def _cache_get(path: str, include_timestamps: bool):
    try:
        with open(_cache_file(path, include_timestamps), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        text = (data.get("text") or "").strip()
        if text:
            return text
    except Exception:
        return ""
    return ""


def _cache_put(path: str, include_timestamps: bool, text: str) -> None:
    try:
        with open(_cache_file(path, include_timestamps), "w", encoding="utf-8") as handle:
            json.dump({"text": text}, handle, ensure_ascii=False)
    except Exception:
        pass


def _prepare_audio(ffmpeg: str, src: str, dest: str, should_abort):
    """(errore, percorso wav). Senza ffmpeg passa solo un wav già pronto."""
    if not ffmpeg:
        if os.path.splitext(src)[1].lower() == ".wav":
            return "", src
        return MSG_NEED_FFMPEG, ""
    cmd = [
        ffmpeg, "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000",
        "-f", "wav", dest,
    ]
    result = _run_process(cmd, cwd=None, should_abort=should_abort, timeout_sec=5 * 60)
    if result.get("aborted"):
        return MSG_INTERRUPTED, ""
    if result.get("timeout"):
        return MSG_TIMEOUT, ""
    if result.get("code") != 0 or not os.path.isfile(dest) or os.path.getsize(dest) < 44:
        return MSG_FAIL, ""
    return "", dest


def _run_process(cmd, cwd, should_abort, timeout_sec: int) -> dict:
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd or None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=_CREATE_NO_WINDOW,
        )
    except OSError as exc:
        return {"code": 1, "stdout": str(exc), "aborted": False, "timeout": False}
    chunks = []

    def _read():
        try:
            chunks.append(proc.stdout.read() if proc.stdout else b"")
        except Exception:
            chunks.append(b"")

    reader = threading.Thread(target=_read, daemon=True)
    reader.start()
    started = time.time()
    while reader.is_alive():
        reader.join(0.3)
        if should_abort and should_abort():
            try:
                proc.kill()
            except OSError:
                pass
            reader.join(2)
            return {"code": -1, "stdout": "", "aborted": True, "timeout": False}
        if time.time() - started > timeout_sec:
            try:
                proc.kill()
            except OSError:
                pass
            reader.join(2)
            return {"code": -1, "stdout": "", "aborted": False, "timeout": True}
    try:
        code = proc.wait(timeout=10)
    except Exception:
        code = proc.poll()
    text = b"".join(chunks).decode("utf-8", errors="replace")
    return {"code": code, "stdout": text, "aborted": False, "timeout": False}


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def transcribe_file(
    path: str,
    *,
    duration_sec: float = 0,
    include_timestamps: bool = False,
    should_abort=None,
    on_progress=None,
    ffmpeg: str = "",
    ensure=None,
    runner=None,
    converter=None,
) -> dict:
    """Trascrive un file già sul disco. Non chiama Gemini."""
    result = {"ok": False, "text": "", "error": "", "source": "whisper"}
    if not path or not os.path.isfile(path):
        result["error"] = "File non trovato."
        return result
    err = duration_error(duration_sec)
    if err:
        result["error"] = err
        return result
    cached = _cache_get(path, include_timestamps)
    if cached:
        result["ok"] = True
        result["text"] = cached
        result["source"] = "whisper+cache"
        _emit(on_progress, 100, "Trascrizione Whisper pronta.")
        return result
    if should_abort and should_abort():
        result["error"] = MSG_INTERRUPTED
        return result

    getter = ensure or ensure_runtime
    runtime = getter(on_progress=on_progress, should_abort=should_abort)
    if not runtime.get("ok"):
        result["error"] = runtime.get("error") or MSG_NO_BIN
        return result

    tmp_dir = tempfile.mkdtemp(prefix="rtad_whisper_")
    try:
        _emit(on_progress, 35, "Preparazione audio per Whisper.")
        if converter is not None:
            conv_err, wav = converter(path, tmp_dir)
        else:
            conv_err, wav = _prepare_audio(
                ffmpeg or "", path, os.path.join(tmp_dir, "audio.wav"), should_abort
            )
        if conv_err:
            result["error"] = conv_err
            return result
        if should_abort and should_abort():
            result["error"] = MSG_INTERRUPTED
            return result
        outbase = os.path.join(tmp_dir, "out")
        cmd = [
            runtime["cli"],
            "-m", runtime["model"],
            "-f", wav,
            "-l", "auto",
            "-oj",
            "-of", outbase,
            "-np",
            "-t", str(max(1, min(4, os.cpu_count() or 2))),
        ]
        _emit(on_progress, 45, MSG_RUNNING)
        if runner is not None:
            run = runner(cmd, should_abort=should_abort)
        else:
            run = _run_process(
                cmd,
                cwd=os.path.dirname(runtime["cli"]),
                should_abort=should_abort,
                timeout_sec=RUN_TIMEOUT_SEC,
            )
        if run.get("aborted"):
            result["error"] = MSG_INTERRUPTED
            return result
        if run.get("timeout"):
            result["error"] = MSG_TIMEOUT
            return result
        json_path = run.get("json_path") or (outbase + ".json")
        segments = []
        if run.get("json") is not None:
            segments = segments_from_json(run.get("json"))
        elif json_path and os.path.isfile(json_path):
            try:
                segments = segments_from_json(_load_json(json_path))
            except Exception:
                segments = []
        text = format_segments(segments, include_timestamps)
        if not text:
            plain = (run.get("stdout") or "").strip()
            if plain and run.get("code") == 0 and not plain.lower().startswith("error"):
                text = plain
        if not text:
            result["error"] = MSG_EMPTY if run.get("code") == 0 else MSG_FAIL
            return result
        _cache_put(path, include_timestamps, text)
        result["ok"] = True
        result["text"] = text
        _emit(on_progress, 100, "Trascrizione Whisper pronta.")
        return result
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
