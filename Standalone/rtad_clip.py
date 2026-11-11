# -*- coding: utf-8 -*-
"""Taglia e unisci audio e video.

Un file nuovo, accanto. Quello di partenza non si tocca.
Stessa finestra nella Standalone e nell'Add-on. A schermo e a voce.
Invio e il clic sullo stesso pulsante. Sull'elenco, Invio e il doppio clic
ascoltano il pezzo. Un clic solo seleziona la riga.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import wave

log = logging.getLogger("rtad.clip")

MSG_NEED_FFMPEG = "Per questo formato serve ffmpeg"
MSG_EMPTY = "Nessun file in elenco."
MSG_WORKING = "Lavoro in corso... attendere prego."
MSG_READING = "Leggo la durata... attendere prego."
MSG_PREPARE = "Preparo l'ascolto... attendere prego."
MSG_STOPPED = "Fermato."
MSG_CONVERT = "I file non sono uguali: li converto, ci vuole più tempo."
MSG_NO_AUDIO_TRACK = "Un file non ha l'audio: in quel tratto non si sente niente."
MSG_FAIL = "Non sono riuscito a creare il file. Il file di partenza resta com'è."
MSG_NO_LISTEN = "In questo pezzo non c'è audio da ascoltare."
MSG_LISTEN_FAIL = "Non riesco ad ascoltare questo pezzo."
MSG_MIXED = (
    "Un audio e un video non si uniscono qui. "
    "Tieni solo audio, oppure solo video."
)
MSG_NEED_RANGE = (
    "Scrivi il tratto sulla riga selezionata, poi Tieni, poi Esegui. "
    "Se scrivi solo la Fine, il tratto parte dall'inizio. "
    "Se scrivi solo l'Inizio, il tratto arriva fino alla fine del file."
)
MSG_DROP_RANGE = (
    "Scrivi il tratto da togliere. "
    "Se scrivi solo la Fine, si toglie dall'inizio. "
    "Se scrivi solo l'Inizio, si toglie fino alla fine del file."
)
MSG_NEED_END = "La durata non è letta: scrivi anche la fine."
MSG_NEED_TWO = (
    "Per unire servono almeno due file. "
    "Aggiungi un altro file, oppure scegli un tratto e premi Esegui."
)
MSG_BAD_CLOCK = (
    "Non è un orario. Due numeri, 1:20, sono un minuto e 20 secondi. "
    "Tre numeri, 01:20:50, sono un'ora, 20 minuti e 50 secondi."
)
MSG_NO_DONE = "Nessun risultato ancora."
MSG_END_BEFORE = "La fine viene prima dell'inizio."
MSG_WHOLE = "Quel tratto è tutto il file. Non resta nulla."
MSG_SELECT = "Seleziona una riga."

_AUDIO_EXTS = {
    ".mp3", ".m4a", ".m4b", ".aac", ".flac", ".ogg", ".opus", ".wav", ".wma", ".aif", ".aiff", ".mka",
}
_VIDEO_EXTS = {
    ".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".mts", ".m2ts",
    ".mpg", ".mpeg", ".3gp",
}
_WILDCARD = (
    "Audio e video|"
    "*.mp3;*.m4a;*.m4b;*.aac;*.flac;*.ogg;*.opus;*.wav;*.wma;*.aif;*.aiff;*.mka;"
    "*.mp4;*.m4v;*.mkv;*.avi;*.mov;*.wmv;*.webm;*.flv;*.mts;*.m2ts;*.mpg;*.mpeg;*.3gp|"
    "Tutti i file|*.*"
)
_INTRO = (
    "Taglia e unisci audio e video. "
    "Invio sul pulsante Aggiungi, o un clic, mette i file in elenco. "
    "Invio sul pulsante Aggiungi cartella, o un clic, mette i file di quella cartella. "
    "Le cartelle che stanno dentro non si aprono. "
    "L'ordine dell'elenco è l'ordine del risultato. "
    "Invio sul pulsante Sposta su o Sposta giù, o un clic, cambia l'ordine. "
    "Invio o doppio clic su una riga ascolta quel pezzo. "
    "Un clic solo seleziona la riga. "
    "Due numeri, 1:20, sono un minuto e 20 secondi. "
    "Tre numeri, 01:20:50, sono un'ora, 20 minuti e 50 secondi. "
    "Se scrivi solo la Fine, il tratto parte dall'inizio. "
    "Se scrivi solo l'Inizio, il tratto arriva fino alla fine del file. "
    "Invio sul pulsante Tieni da qui a qui, o un clic, tiene quel tratto "
    "della riga selezionata. "
    "Invio sul pulsante Togli questo tratto, o un clic, toglie quel tratto "
    "e tiene il prima e il dopo. "
    "Invio sul pulsante Altro tratto, o un clic, aggiunge quel tratto "
    "senza cambiare la riga. "
    "Invio sul pulsante Ferma, o un clic, ferma l'ascolto o il lavoro. "
    "Con un file solo, Invio sul pulsante Esegui, o un clic, taglia la riga "
    "selezionata. "
    "Con almeno due file, Invio sul pulsante Unisci, o un clic, unisce "
    "l'elenco: il file intero, oppure il tratto già scelto. "
    "I file creati restano nell'elenco Fatti. "
    "Il file unito si chiama Unito, poi Unito-2. "
    "Lo Stato, la barra di stato e Fatti dicono la stessa frase, "
    "con il nome di ogni file. "
    "Dall'elenco, Alt e la lettera del pulsante fa la stessa cosa: "
    "A Aggiungi, K Aggiungi cartella, S Sposta su, G Sposta giù, M Rimuovi, C Ascolta, "
    "F Ferma, T Tieni, O Togli, L Altro tratto, E Esegui, U Unisci. "
    "Invio o doppio clic su un fatto lo rimette nell'elenco di lavoro. "
    "Il file di partenza resta com'è. Esc chiude."
)
_CLOCK_HINT = (
    "Due numeri, 1:20, sono un minuto e 20 secondi. "
    "Tre numeri, 01:20:50, sono un'ora, 20 minuti e 50 secondi. "
    "Se scrivi solo la Fine, il tratto parte dall'inizio. "
    "Se scrivi solo l'Inizio, il tratto arriva fino alla fine del file."
)
# Lettere uniche, e diverse da Alt+R: quella la prende NVIDIA.
_ALT_ACTIONS = {
    "A": "add",
    "K": "folder",
    "S": "up",
    "G": "down",
    "M": "remove",
    "C": "listen",
    "F": "stop",
    "T": "keep",
    "O": "drop",
    "L": "another",
    "E": "run",
    "U": "join",
}
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _files_in_folder(folder: str, exts: set) -> list:
    """I file di quella cartella, in ordine di nome. Non le cartelle dentro."""
    found = []
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    for name in names:
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        if os.path.splitext(name)[1].lower() in exts:
            found.append(path)
    found.sort(key=lambda item: os.path.basename(item).casefold())
    return found


def _ffmpeg_exe() -> str:
    try:
        import rtad_media
        found = rtad_media._ffmpeg_exe()
        if found:
            return found
    except Exception:
        pass
    found = shutil.which("ffmpeg") or ""
    if found and os.path.isfile(found):
        return found
    fixed = r"C:\ffmpeg\bin\ffmpeg.exe"
    if os.path.isfile(fixed):
        return fixed
    return ""


def _ffprobe_exe() -> str:
    ff = _ffmpeg_exe()
    if ff:
        probe = os.path.join(os.path.dirname(ff), "ffprobe.exe")
        if os.path.isfile(probe):
            return probe
        probe = os.path.join(os.path.dirname(ff), "ffprobe")
        if os.path.isfile(probe):
            return probe
    found = shutil.which("ffprobe") or ""
    return found if found and os.path.isfile(found) else ""


def speak_duration(seconds: float) -> str:
    if seconds is None or seconds <= 0:
        return "durata non letta"
    try:
        import rtad_media
        text = rtad_media._format_duration(seconds)
        if text:
            return text
    except Exception:
        pass
    total = int(round(float(seconds)))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} h {m:02d} min {s:02d} s"
    if m:
        return f"{m} min {s:02d} s"
    return f"{s} s"


def clock_text(seconds: float) -> str:
    total = int(round(float(seconds)))
    if total < 0:
        total = 0
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def explain_clock(raw: str, name: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    try:
        seconds = parse_clock(text)
    except ValueError:
        return f"{name}: {MSG_BAD_CLOCK}"
    return f"{name}: {text} sono {speak_duration(seconds)}."


def _point_spoken(seconds: float) -> str:
    if seconds is None:
        return "durata non letta"
    if float(seconds) <= 0:
        return "0 s"
    return speak_duration(seconds)


def action_words(piece: "Piece") -> str:
    if piece.mode == "keep" and piece.start is not None and piece.end is not None:
        return (
            f"tieni da {clock_text(piece.start)}, {_point_spoken(piece.start)}, "
            f"a {clock_text(piece.end)}, {_point_spoken(piece.end)}"
        )
    if piece.mode == "drop" and piece.start is not None and piece.end is not None:
        return (
            f"tolto da {clock_text(piece.start)}, {_point_spoken(piece.start)}, "
            f"a {clock_text(piece.end)}, {_point_spoken(piece.end)}"
        )
    return "tutto il file"


def history_label(pieces: list, out_path: str, dur_spoken: str) -> str:
    name = os.path.basename(out_path)
    if len(pieces) == 1:
        return f"{name}, {action_words(pieces[0])}, {dur_spoken}"
    bits = []
    for piece in pieces:
        bit = f"{os.path.basename(piece.path)}, {action_words(piece)}"
        if piece.duration and piece.duration > 0:
            spoken = speak_duration(piece.duration)
            if piece.mode == "all":
                bit += f", {spoken}"
            else:
                bit += f", file di {spoken}"
        bits.append(bit)
    return (
        f"{name}, uniti {len(pieces)} file: {'; '.join(bits)}. "
        f"Risultato {dur_spoken}."
    )


def clone_piece(piece: "Piece") -> "Piece":
    clone = Piece(piece.path)
    clone.mode = piece.mode
    clone.start = piece.start
    clone.end = piece.end
    clone.duration = piece.duration
    clone.has_video = piece.has_video
    clone.has_audio = piece.has_audio
    clone.video_codec = piece.video_codec
    clone.audio_codec = piece.audio_codec
    clone.width = piece.width
    clone.height = piece.height
    clone.sample_rate = piece.sample_rate
    return clone


def parse_clock(raw: str):
    """Secondi, None se il campo è vuoto. ValueError se non è un orario."""
    text = (raw or "").strip().replace("\u200e", "").replace("\u200f", "")
    if not text:
        return None
    if re.fullmatch(r"\d+(?:[.,]\d+)?", text):
        return float(text.replace(",", "."))
    m = re.fullmatch(r"(?:(\d+):)?(\d+):(\d+(?:[.,]\d+)?)", text)
    if not m:
        raise ValueError(MSG_BAD_CLOCK)
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    sec = float(m.group(3).replace(",", "."))
    return h * 3600 + mi * 60 + sec


def _run(args, cancel, timeout=None) -> tuple[bool, str]:
    extra = []
    if "-nostdin" not in args[:4]:
        extra.append("-nostdin")
    if "-loglevel" not in args:
        extra.extend(["-hide_banner", "-loglevel", "error"])
    if extra:
        args = [args[0], *extra, *args[1:]]
    try:
        proc = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=_NO_WINDOW,
        )
    except OSError as exc:
        log.warning("ffmpeg non parte: %s", exc)
        return False, str(exc)
    err_box = []

    def _drain():
        try:
            while True:
                chunk = proc.stderr.read(4096)
                if not chunk:
                    break
                err_box.append(chunk)
        except Exception:
            pass

    threading.Thread(target=_drain, daemon=True).start()
    started = time.monotonic()
    while proc.poll() is None:
        if cancel is not None and cancel.is_set():
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
            return False, "annullato"
        if timeout and (time.monotonic() - started) > timeout:
            proc.kill()
            return False, "tempo"
        time.sleep(0.15)
    text = b"".join(err_box).decode("utf-8", "replace")[-1500:]
    if proc.returncode != 0:
        log.info("ffmpeg %s -> %s", args[:8], text[-400:])
        return False, text
    return True, ""


def _probe_json(path: str) -> dict:
    exe = _ffprobe_exe()
    if not exe:
        return {}
    try:
        proc = subprocess.run(
            [
                exe, "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", "--", path,
            ],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=40,
            creationflags=_NO_WINDOW,
        )
    except Exception as exc:
        log.info("ffprobe: %s", exc)
        return {}
    if proc.returncode != 0 or not (proc.stdout or b"").strip():
        return {}
    try:
        import json
        return json.loads(proc.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}


class Piece:
    def __init__(self, path: str):
        self.path = path
        self.mode = "all"
        self.start = None
        self.end = None
        self.duration = 0.0
        self.has_video = False
        self.has_audio = False
        self.video_codec = ""
        self.audio_codec = ""
        self.width = 0
        self.height = 0
        self.sample_rate = 0

    @property
    def kind(self) -> str:
        if self.has_video:
            return "video"
        if self.has_audio:
            return "audio"
        ext = os.path.splitext(self.path)[1].lower()
        if ext in _VIDEO_EXTS:
            return "video"
        if ext in _AUDIO_EXTS:
            return "audio"
        return ""

    def label(self) -> str:
        name = os.path.basename(self.path)
        kind = self.kind or "file"
        text = f"{name}, {kind}, {speak_duration(self.duration)}"
        if self.mode in ("keep", "drop") and self.start is not None and self.end is not None:
            text += f", {action_words(self)}"
        return text

    def span(self) -> float:
        dur = float(self.duration or 0)
        if self.mode == "keep" and self.start is not None and self.end is not None:
            return max(0.0, float(self.end) - float(self.start))
        if self.mode == "drop" and self.start is not None and self.end is not None:
            if dur <= 0:
                return 0.0
            return max(0.0, dur - (float(self.end) - float(self.start)))
        return dur


def load_piece(path: str) -> tuple[Piece | None, str]:
    path = (path or "").strip().strip('"')
    if not path or not os.path.isfile(path):
        name = os.path.basename(path) or "file"
        return None, f"{name} non c'è."
    ext = os.path.splitext(path)[1].lower()
    data = _probe_json(path)
    piece = Piece(path)
    if data:
        try:
            piece.duration = float((data.get("format") or {}).get("duration") or 0)
        except (TypeError, ValueError):
            piece.duration = 0.0
        for st in data.get("streams") or []:
            ctype = (st.get("codec_type") or "").lower()
            if ctype == "video" and not piece.has_video:
                piece.has_video = True
                piece.video_codec = (st.get("codec_name") or "").strip()
                try:
                    piece.width = int(st.get("width") or 0)
                    piece.height = int(st.get("height") or 0)
                except (TypeError, ValueError):
                    piece.width = piece.height = 0
            elif ctype == "audio" and not piece.has_audio:
                piece.has_audio = True
                piece.audio_codec = (st.get("codec_name") or "").strip()
                try:
                    piece.sample_rate = int(float(st.get("sample_rate") or 0))
                except (TypeError, ValueError):
                    piece.sample_rate = 0
    if not piece.kind and ext not in _AUDIO_EXTS and ext not in _VIDEO_EXTS:
        return None, f"{os.path.basename(path)} non è un audio né un video."
    if ext in _VIDEO_EXTS and not piece.has_video and not piece.has_audio:
        piece.has_video = True
    elif ext in _AUDIO_EXTS and not piece.has_audio and not piece.has_video:
        piece.has_audio = True
    return piece, ""


def _resolve_span(piece: Piece, start, end):
    """Un solo campo basta. Fine sola: dall'inizio. Inizio solo: fino alla fine."""
    if start is None and end is None:
        return None, None, ""
    if start is None:
        start = 0.0
    if end is None:
        dur = float(piece.duration or 0)
        if dur <= 0:
            return None, None, MSG_NEED_END
        end = dur
    err = _range_error(piece, start, end)
    return start, end, err


def _range_error(piece: Piece, start, end) -> str:
    if start is None or end is None:
        return MSG_BAD_CLOCK
    if end <= start:
        return MSG_END_BEFORE
    dur = float(piece.duration or 0)
    if dur > 0 and start >= dur - 0.05:
        return f"L'inizio supera la durata del file, {speak_duration(dur)}."
    if dur > 0 and end > dur + 0.35:
        return f"La fine supera la durata del file, {speak_duration(dur)}."
    return ""


def apply_keep(piece: Piece, start, end) -> str:
    if start is None and end is None:
        if piece.mode != "all":
            piece.mode = "all"
            piece.start = None
            piece.end = None
            return f"Tutto il file. {piece.label()}"
        return (
            "Scrivi il tratto, per esempio 00:00:20 nella Fine: "
            "il tratto parte dall'inizio."
        )
    start, end, err = _resolve_span(piece, start, end)
    if err:
        return err
    piece.mode = "keep"
    piece.start = float(start)
    piece.end = float(end)
    return piece.label()


def apply_drop(piece: Piece, start, end) -> str:
    if start is None and end is None:
        return MSG_DROP_RANGE
    start, end, err = _resolve_span(piece, start, end)
    if err:
        return err
    dur = float(piece.duration or 0)
    if dur > 0 and start <= 0.05 and end >= dur - 0.05:
        return MSG_WHOLE
    piece.mode = "drop"
    piece.start = float(start)
    piece.end = float(end)
    return piece.label()


def _same_family(pieces: list[Piece]) -> bool:
    if len(pieces) < 2:
        return True
    kinds = {p.kind for p in pieces}
    if kinds != {"video"} and kinds != {"audio"}:
        return False
    if "video" in kinds:
        marks = {
            (
                p.video_codec,
                p.audio_codec,
                p.width,
                p.height,
                p.sample_rate,
                p.has_audio,
            )
            for p in pieces
        }
        return len(marks) == 1
    marks = {(p.audio_codec, p.sample_rate) for p in pieces}
    return len(marks) == 1


def _job_error(pieces: list[Piece]) -> str:
    if not pieces:
        return MSG_EMPTY
    if not _ffmpeg_exe():
        return MSG_NEED_FFMPEG
    kinds = {p.kind for p in pieces}
    if "video" in kinds and "audio" in kinds:
        return MSG_MIXED
    if "" in kinds:
        return MSG_MIXED
    if len(pieces) == 1 and pieces[0].mode == "all":
        return MSG_NEED_RANGE
    return ""


def _notices(pieces: list[Piece]) -> list[str]:
    notes = []
    if len(pieces) >= 2 and not _same_family(pieces):
        notes.append(MSG_CONVERT)
    elif any(p.mode != "all" for p in pieces) and len(pieces) >= 2 and not _same_family(pieces):
        notes.append(MSG_CONVERT)
    if (
        len(pieces) >= 2
        and all(p.kind == "video" for p in pieces)
        and any(p.has_audio for p in pieces)
        and any(not p.has_audio for p in pieces)
    ):
        notes.append(MSG_NO_AUDIO_TRACK)
    return notes


def _unique_output(folder: str, stem: str, ext: str) -> str:
    ext = ext if ext.startswith(".") else f".{ext}"
    candidate = os.path.join(folder, stem + ext)
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{stem}-{n}{ext}")
        n += 1
    return candidate


def _concat_line(path: str) -> str:
    text = os.path.abspath(path).replace("\\", "/")
    text = text.replace("'", r"'\''")
    return f"file '{text}'\n"


def _concat_copy(paths: list[str], dest: str, cancel) -> bool:
    folder = tempfile.mkdtemp(prefix="rtad-clip-")
    list_path = os.path.join(folder, "elenco.txt")
    try:
        with open(list_path, "w", encoding="utf-8") as handle:
            handle.writelines(_concat_line(p) for p in paths)
        ff = _ffmpeg_exe()
        ok, _err = _run(
            [
                ff, "-y", "-f", "concat", "-safe", "0",
                "-i", list_path, "-c", "copy", dest,
            ],
            cancel,
        )
        return ok and os.path.isfile(dest) and os.path.getsize(dest) > 0
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def _seek_args(path: str, start: float, duration: float) -> list[str]:
    """duration 0: fino in fondo. L'attacco è preciso, senza rileggere tutto il file."""
    ff = _ffmpeg_exe()
    tail: list[str] = []
    if duration and duration > 0:
        tail = ["-t", f"{duration:.3f}"]
    preroll = 3.0
    if start > preroll:
        return [
            ff, "-y",
            "-ss", f"{start - preroll:.3f}",
            "-i", path,
            "-ss", f"{preroll:.3f}",
            *tail,
        ]
    if start > 0.01:
        return [ff, "-y", "-i", path, "-ss", f"{start:.3f}", *tail]
    return [ff, "-y", "-i", path, *tail]


def _audio_ext(pieces: list[Piece]) -> str:
    """Stessa estensione se i file coincidono. Se no, m4a."""
    exts = []
    for piece in pieces:
        ext = os.path.splitext(piece.path)[1].lower()
        if ext not in _AUDIO_EXTS:
            ext = ".m4a"
        exts.append(ext)
    if len(set(exts)) == 1:
        return exts[0]
    return ".m4a"


def _audio_out_args(ext: str) -> list[str]:
    ext = (ext or "").lower()
    if ext == ".mp3":
        codec = ["-c:a", "libmp3lame", "-b:a", "192k"]
    elif ext in (".wav", ".aif", ".aiff"):
        codec = ["-c:a", "pcm_s16le"]
    elif ext == ".flac":
        codec = ["-c:a", "flac"]
    elif ext == ".ogg":
        codec = ["-c:a", "libvorbis", "-q:a", "5"]
    elif ext == ".opus":
        codec = ["-c:a", "libopus", "-b:a", "128k"]
        return [*codec, "-ar", "48000", "-ac", "2"]
    elif ext == ".wma":
        codec = ["-c:a", "wmav2", "-b:a", "192k"]
    else:
        codec = ["-c:a", "aac", "-b:a", "160k"]
    return [*codec, "-ar", "44100", "-ac", "2"]


def _audio_encode(path: str, dest: str, start: float, duration: float, cancel) -> bool:
    args = _seek_args(path, start, duration)
    ext = os.path.splitext(dest)[1].lower()
    args += ["-vn", *_audio_out_args(ext), dest]
    ok, _err = _run(args, cancel)
    return ok and os.path.isfile(dest) and os.path.getsize(dest) > 0


def _audio_drop(piece: Piece, dest: str, cancel) -> bool:
    ff = _ffmpeg_exe()
    start = float(piece.start or 0)
    end = float(piece.end or 0)
    dur = float(piece.duration or 0)
    if start <= 0.05:
        return _audio_encode(piece.path, dest, end, max(0.1, dur - end), cancel)
    if dur > 0 and end >= dur - 0.05:
        return _audio_encode(piece.path, dest, 0.0, start, cancel)
    graph = (
        f"[0:a]atrim=end={start:.3f},asetpts=PTS-STARTPTS[a0];"
        f"[0:a]atrim=start={end:.3f},asetpts=PTS-STARTPTS[a1];"
        f"[a0][a1]concat=n=2:v=0:a=1[a]"
    )
    ok, _err = _run(
        [
            ff, "-y", "-i", piece.path,
            "-filter_complex", graph,
            "-map", "[a]",
            *_audio_out_args(os.path.splitext(dest)[1]),
            dest,
        ],
        cancel,
    )
    return ok and os.path.isfile(dest) and os.path.getsize(dest) > 0


def _video_encode(path: str, dest: str, start: float, duration: float, cancel, with_audio: bool) -> bool:
    args = _seek_args(path, start, duration)
    args += [
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=25,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-movflags", "+faststart",
    ]
    if with_audio:
        args += ["-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2"]
    else:
        args += ["-an"]
    args.append(dest)
    ok, _err = _run(args, cancel)
    return ok and os.path.isfile(dest) and os.path.getsize(dest) > 0


def _video_pad_encode(piece: Piece, dest: str, cancel, width: int, height: int, with_silence: bool) -> bool:
    """Un video, portato alla misura del primo, con l'audio o col silenzio."""
    ff = _ffmpeg_exe()
    start = 0.0
    dur = float(piece.duration or 0)
    if piece.mode == "keep":
        start = float(piece.start or 0)
        dur = float(piece.end) - start
    w = width if width % 2 == 0 else width - 1
    h = height if height % 2 == 0 else height - 1
    if w < 2 or h < 2:
        w, h = 1280, 720
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1,fps=25,format=yuv420p"
    )
    if piece.mode == "drop":
        return _video_drop(piece, dest, cancel, vf, with_silence)
    if piece.mode == "all":
        args = [ff, "-y", "-i", piece.path]
    else:
        args = _seek_args(piece.path, start, max(0.1, dur))
    if with_silence or not piece.has_audio:
        graph = f"[0:v]{vf}[v];anullsrc=channel_layout=stereo:sample_rate=44100[a]"
        args = [ff, "-y", "-i", piece.path]
        if piece.mode == "keep":
            args = _seek_args(piece.path, start, max(0.1, float(piece.end) - start))
        args += [
            "-filter_complex", graph,
            "-map", "[v]", "-map", "[a]",
            "-shortest",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart",
            dest,
        ]
    else:
        args += [
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart",
            dest,
        ]
    ok, _err = _run(args, cancel)
    return ok and os.path.isfile(dest) and os.path.getsize(dest) > 0


def _video_drop(piece: Piece, dest: str, cancel, vf: str, with_silence: bool) -> bool:
    ff = _ffmpeg_exe()
    start = float(piece.start or 0)
    end = float(piece.end or 0)
    dur = float(piece.duration or 0)
    if start <= 0.05 and not with_silence:
        return _video_encode(piece.path, dest, end, max(0.1, dur - end), cancel, piece.has_audio)
    if dur > 0 and end >= dur - 0.05 and not with_silence:
        return _video_encode(piece.path, dest, 0.0, start, cancel, piece.has_audio)
    if piece.has_audio and not with_silence:
        graph = (
            f"[0:v]trim=end={start:.3f},setpts=PTS-STARTPTS[v0];"
            f"[0:a]atrim=end={start:.3f},asetpts=PTS-STARTPTS[a0];"
            f"[0:v]trim=start={end:.3f},setpts=PTS-STARTPTS[v1];"
            f"[0:a]atrim=start={end:.3f},asetpts=PTS-STARTPTS[a1];"
            f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[vc][ac];"
            f"[vc]{vf}[v];"
            f"[ac]aresample=44100,aformat=channel_layouts=stereo[a]"
        )
        maps = ["-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "160k"]
    else:
        graph = (
            f"[0:v]trim=end={start:.3f},setpts=PTS-STARTPTS[v0];"
            f"[0:v]trim=start={end:.3f},setpts=PTS-STARTPTS[v1];"
            f"[v0][v1]concat=n=2:v=1:a=0[vc];"
            f"[vc]{vf}[v]"
        )
        maps = ["-map", "[v]", "-an"]
        if with_silence:
            graph = (
                f"[0:v]trim=end={start:.3f},setpts=PTS-STARTPTS[v0];"
                f"[0:v]trim=start={end:.3f},setpts=PTS-STARTPTS[v1];"
                f"[v0][v1]concat=n=2:v=1:a=0[vc];"
                f"[vc]{vf}[v];"
                f"anullsrc=channel_layout=stereo:sample_rate=44100[a]"
            )
            maps = [
                "-map", "[v]", "-map", "[a]", "-shortest",
                "-c:a", "aac", "-b:a", "160k",
            ]
    ok, _err = _run(
        [
            ff, "-y", "-i", piece.path,
            "-filter_complex", graph,
            *maps,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-movflags", "+faststart",
            dest,
        ],
        cancel,
    )
    return ok and os.path.isfile(dest) and os.path.getsize(dest) > 0


def _render_simple(piece: Piece, dest: str, cancel) -> bool:
    """Un pezzo solo, senza doverlo allineare a un altro."""
    if piece.kind == "audio":
        if piece.mode == "drop":
            return _audio_drop(piece, dest, cancel)
        start = float(piece.start or 0)
        dur = float(piece.end) - start
        return _audio_encode(piece.path, dest, start, dur, cancel)
    if piece.mode == "drop":
        vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=25,format=yuv420p"
        return _video_drop(piece, dest, cancel, vf, False)
    start = float(piece.start or 0)
    dur = float(piece.end) - start
    return _video_encode(piece.path, dest, start, dur, cancel, piece.has_audio)


def _output_for(pieces: list[Piece], reencode: bool) -> str:
    first = pieces[0]
    folder = os.path.dirname(os.path.abspath(first.path)) or os.getcwd()
    if len(pieces) > 1:
        stem = "Unito"
    else:
        stem = os.path.splitext(os.path.basename(first.path))[0]
        stem = f"{stem}-taglio"
    if first.kind == "video" and (reencode or any(p.mode != "all" for p in pieces)):
        ext = ".mp4"
    elif reencode or any(p.mode != "all" for p in pieces):
        ext = _audio_ext(pieces)
    else:
        ext = os.path.splitext(first.path)[1].lower() or ".mp4"
    return _unique_output(folder, stem, ext)


def _duration_of(path: str) -> float:
    piece, _err = load_piece(path)
    if piece is None:
        return 0.0
    return float(piece.duration or 0)


def build(pieces: list[Piece], cancel=None, made_path=None) -> tuple[bool, str]:
    err = _job_error(pieces)
    if err:
        return False, err
    if cancel is not None and cancel.is_set():
        return False, MSG_STOPPED
    reencode = any(p.mode != "all" for p in pieces) or not _same_family(pieces)
    dest = _output_for(pieces, reencode)
    folder = tempfile.mkdtemp(prefix="rtad-clip-")
    try:
        if not reencode:
            ok = _concat_copy([p.path for p in pieces], dest, cancel)
            if not ok and not (cancel is not None and cancel.is_set()):
                reencode = True
                try:
                    if os.path.isfile(dest):
                        os.remove(dest)
                except OSError:
                    pass
                dest = _output_for(pieces, True)
            elif ok:
                if made_path is not None:
                    made_path.append(dest)
                dur = _duration_of(dest)
                return True, (
                    f"Creato {os.path.basename(dest)}, {speak_duration(dur)}, "
                    "nella stessa cartella."
                )
        if cancel is not None and cancel.is_set():
            return False, MSG_STOPPED
        if len(pieces) == 1:
            ok = _render_simple(pieces[0], dest, cancel)
        else:
            made = []
            video = pieces[0].kind == "video"
            width = pieces[0].width or 1280
            height = pieces[0].height or 720
            silence = video and any(p.has_audio for p in pieces) and any(not p.has_audio for p in pieces)
            for index, piece in enumerate(pieces):
                if cancel is not None and cancel.is_set():
                    return False, MSG_STOPPED
                ext = ".mp4" if video else os.path.splitext(dest)[1].lower()
                part = os.path.join(folder, f"parte-{index}{ext}")
                if video:
                    ok_part = _video_pad_encode(piece, part, cancel, width, height, silence and not piece.has_audio)
                    if piece.mode == "drop" and not ok_part:
                        return False, MSG_FAIL
                    if piece.mode != "drop" and not ok_part:
                        return False, MSG_FAIL
                else:
                    if piece.mode == "drop":
                        ok_part = _audio_drop(piece, part, cancel)
                    elif piece.mode == "keep":
                        ok_part = _audio_encode(
                            piece.path, part,
                            float(piece.start or 0),
                            float(piece.end) - float(piece.start or 0),
                            cancel,
                        )
                    else:
                        ok_part = _audio_encode(
                            piece.path, part, 0.0, float(piece.duration or 0), cancel,
                        )
                if not ok_part:
                    if cancel is not None and cancel.is_set():
                        return False, MSG_STOPPED
                    return False, MSG_FAIL
                made.append(part)
            if len(made) == 1:
                shutil.copy2(made[0], dest)
                ok = True
            else:
                ok = _concat_copy(made, dest, cancel)
        if cancel is not None and cancel.is_set():
            try:
                if os.path.isfile(dest):
                    os.remove(dest)
            except OSError:
                pass
            return False, MSG_STOPPED
        if not ok:
            return False, MSG_FAIL
        if made_path is not None:
            made_path.append(dest)
        dur = _duration_of(dest)
        return True, (
            f"Creato {os.path.basename(dest)}, {speak_duration(dur)}, "
            "nella stessa cartella."
        )
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def _wav_duration(path: str) -> float:
    try:
        with wave.open(path, "rb") as handle:
            rate = handle.getframerate() or 0
            frames = handle.getnframes() or 0
            if rate <= 0:
                return 0.0
            return frames / float(rate)
    except Exception:
        return 0.0


def preview_wav(piece: Piece, dest: str, cancel=None) -> tuple[bool, str]:
    """Un wav corto del pezzo. La frase dice che cosa si sta per sentire."""
    if not piece.has_audio and piece.kind == "video":
        probed, _err = load_piece(piece.path)
        if probed is not None and probed.has_audio:
            piece.has_audio = True
    if not piece.has_audio:
        return False, MSG_NO_LISTEN
    ff = _ffmpeg_exe()
    if not ff:
        return False, MSG_NEED_FFMPEG
    if piece.mode == "drop" and piece.start is not None and piece.end is not None:
        before = max(0.0, float(piece.start) - 5.0)
        head = float(piece.start) - before
        tail = 5.0
        graph = (
            f"[0:a]atrim=start={before:.3f}:end={float(piece.start):.3f},"
            f"asetpts=PTS-STARTPTS[a0];"
            f"[0:a]atrim=start={float(piece.end):.3f}:duration={tail:.3f},"
            f"asetpts=PTS-STARTPTS[a1];"
            f"[a0][a1]concat=n=2:v=0:a=1[a]"
        )
        phrase = "Ascolto 5 secondi prima del taglio e 5 dopo."
        if head < 0.2:
            graph = (
                f"[0:a]atrim=start={float(piece.end):.3f}:duration={tail:.3f},"
                f"asetpts=PTS-STARTPTS[a]"
            )
            phrase = "Ascolto 5 secondi dopo il taglio."
        ok, _err = _run(
            [
                ff, "-y", "-i", piece.path,
                "-filter_complex", graph,
                "-map", "[a]", "-ac", "1", "-ar", "22050", dest,
            ],
            cancel,
            timeout=120,
        )
        if not ok:
            return False, MSG_LISTEN_FAIL
        heard = _wav_duration(dest)
        return True, f"{phrase} {speak_duration(heard)}."
    start = 0.0
    if piece.mode == "keep" and piece.start is not None:
        start = float(piece.start)
    span = piece.span() or float(piece.duration or 0)
    take = min(20.0, span if span > 0 else 20.0)
    ok, _err = _run(
        _seek_args(piece.path, start, take) + ["-vn", "-ac", "1", "-ar", "22050", dest],
        cancel,
        timeout=120,
    )
    if not ok or not os.path.isfile(dest):
        return False, MSG_LISTEN_FAIL
    heard = _wav_duration(dest) or take
    if span > 20:
        return True, f"Ascolto l'inizio, {speak_duration(heard)}."
    return True, f"Ascolto il pezzo, {speak_duration(heard)}."


def open_dialog(parent, speaker, paths=None):
    import wx

    dialog = ClipDialog(parent, speaker, paths or [])
    dialog.ShowModal()
    dialog.close_work()
    dialog.Destroy()


class ClipDialog:
    """La classe vera è sotto: wx va importato a finestra aperta."""


def _install_dialog():
    import winsound
    import wx

    class ClipDialog(wx.Dialog):
        def __init__(self, parent, speaker, paths):
            super().__init__(
                parent,
                title="Taglia e unisci",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._speaker = speaker or (lambda _text: None)
            self._rows: list[Piece] = []
            self._done: list[tuple[str, str]] = []
            self._cancel = threading.Event()
            self._busy = False
            self._open = True
            self._preview = ""
            self._playing = False
            self._initial = list(paths or [])

            vbox = wx.BoxSizer(wx.VERTICAL)
            intro = wx.StaticText(self, label=_INTRO)
            intro.Wrap(680)
            vbox.Add(intro, 0, wx.ALL | wx.EXPAND, 10)

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "File, nell'ordine. "
                        "Invio o doppio clic ascolta il pezzo. "
                        "Un clic solo seleziona la riga."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )
            self.lst = wx.ListBox(self, style=wx.LB_SINGLE)
            self.lst.SetMinSize((680, 180))
            vbox.Add(self.lst, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.lst.Bind(wx.EVT_LISTBOX, self._on_select)
            self.lst.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._on_listen())

            times = wx.BoxSizer(wx.HORIZONTAL)
            times.Add(wx.StaticText(self, label="Inizio"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            self.txt_start = wx.TextCtrl(self)
            times.Add(self.txt_start, 1, wx.RIGHT, 12)
            times.Add(wx.StaticText(self, label="Fine"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            self.txt_end = wx.TextCtrl(self)
            times.Add(self.txt_end, 1)
            vbox.Add(times, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.lbl_clock = wx.StaticText(self, label=_CLOCK_HINT)
            self.lbl_clock.Wrap(680)
            vbox.Add(self.lbl_clock, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            self.txt_start.Bind(wx.EVT_TEXT, lambda e: self._update_clock_label())
            self.txt_end.Bind(wx.EVT_TEXT, lambda e: self._update_clock_label())

            row1 = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_add = wx.Button(self, label="&Aggiungi file…")
            self.btn_folder = wx.Button(self, label="Aggiungi cartella (&K)")
            self.btn_up = wx.Button(self, label="Sposta &su")
            self.btn_down = wx.Button(self, label="Sposta &giù")
            self.btn_remove = wx.Button(self, label="Ri&muovi")
            for btn in (self.btn_add, self.btn_folder, self.btn_up, self.btn_down, self.btn_remove):
                row1.Add(btn, 0, wx.RIGHT, 6)
            vbox.Add(row1, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            row2 = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_listen = wx.Button(self, label="As&colta il pezzo")
            self.btn_stop = wx.Button(self, label="&Ferma")
            self.btn_keep = wx.Button(self, label="&Tieni da qui a qui")
            self.btn_drop = wx.Button(self, label="T&ogli questo tratto")
            self.btn_another = wx.Button(self, label="A&ltro tratto")
            for btn in (self.btn_listen, self.btn_stop, self.btn_keep, self.btn_drop, self.btn_another):
                row2.Add(btn, 0, wx.RIGHT, 6)
            vbox.Add(row2, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            row3 = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_run = wx.Button(self, label="&Esegui")
            self.btn_join = wx.Button(self, label="&Unisci")
            self.btn_close = wx.Button(self, wx.ID_CANCEL, "Chiudi")
            row3.Add(self.btn_run, 0, wx.RIGHT, 6)
            row3.Add(self.btn_join, 0, wx.RIGHT, 6)
            row3.Add(self.btn_close, 0)
            vbox.Add(row3, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Fatti. Invio o doppio clic rimette il file nell'elenco di lavoro. "
                        "Un clic solo seleziona la riga."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )
            self.lst_done = wx.ListBox(self, style=wx.LB_SINGLE)
            self.lst_done.SetMinSize((680, 110))
            vbox.Add(self.lst_done, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.lst_done.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._on_use_done())

            vbox.Add(wx.StaticText(self, label="Stato"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.txt_status = wx.TextCtrl(
                self,
                value=MSG_EMPTY,
                style=wx.TE_READONLY | wx.TE_MULTILINE,
            )
            self.txt_status.SetMinSize((680, 120))
            vbox.Add(self.txt_status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

            self._status_bar = wx.StatusBar(self)
            self._status_bar.SetMinSize((680, 28))
            self._status_bar.SetStatusText(MSG_EMPTY)
            vbox.Add(self._status_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

            self.btn_add.Bind(wx.EVT_BUTTON, self._on_add)
            self.btn_folder.Bind(wx.EVT_BUTTON, self._on_add_folder)
            self.btn_up.Bind(wx.EVT_BUTTON, lambda e: self._move(-1))
            self.btn_down.Bind(wx.EVT_BUTTON, lambda e: self._move(1))
            self.btn_remove.Bind(wx.EVT_BUTTON, self._on_remove)
            self.btn_listen.Bind(wx.EVT_BUTTON, lambda e: self._on_listen())
            self.btn_stop.Bind(wx.EVT_BUTTON, self._on_stop)
            self.btn_keep.Bind(wx.EVT_BUTTON, self._on_keep)
            self.btn_drop.Bind(wx.EVT_BUTTON, self._on_drop)
            self.btn_another.Bind(wx.EVT_BUTTON, self._on_another)
            self.btn_run.Bind(wx.EVT_BUTTON, self._on_run)
            self.btn_join.Bind(wx.EVT_BUTTON, self._on_join)
            self.Bind(wx.EVT_CHAR_HOOK, self._on_char)
            self.Bind(wx.EVT_CLOSE, self._on_close)
            self.SetEscapeId(wx.ID_CANCEL)

            self.SetSizer(vbox)
            self.SetInitialSize((780, 860))
            self.CentreOnParent()
            self._refresh(0)
            self._refresh_done()
            self.lst.SetFocus()
            if self._initial:
                wx.CallAfter(self._load_initial)
            elif not _ffmpeg_exe():
                wx.CallAfter(self._say, MSG_NEED_FFMPEG)

        def close_work(self):
            self._open = False
            self._cancel.set()
            self._stop_sound()

        def _on_close(self, event):
            self.close_work()
            event.Skip()

        def _say(self, text: str):
            text = (text or "").strip()
            if not text:
                return
            if self._open:
                try:
                    self.txt_status.SetValue(text)
                except Exception:
                    pass
                try:
                    self._status_bar.SetStatusText(text)
                except Exception:
                    pass
            try:
                self._speaker(text)
            except Exception:
                log.info("voce: %s", text)

        def _done_label(self, path: str) -> str:
            key = os.path.normcase(os.path.abspath(path))
            for label, done in self._done:
                try:
                    if os.path.normcase(os.path.abspath(done)) == key:
                        return label
                except Exception:
                    continue
            return ""

        def _selected(self) -> int:
            if not self._rows:
                return -1
            index = self.lst.GetSelection()
            if index < 0 or index >= len(self._rows):
                return -1
            return index

        def _refresh(self, select: int):
            self.lst.Clear()
            if not self._rows:
                self.lst.Append(MSG_EMPTY)
                self.lst.SetSelection(0)
                self.txt_start.ChangeValue("")
                self.txt_end.ChangeValue("")
                return
            for piece in self._rows:
                self.lst.Append(piece.label())
            select = max(0, min(select, len(self._rows) - 1))
            self.lst.SetSelection(select)
            self._fill_times(select)

        def _fill_times(self, index: int):
            piece = self._rows[index]
            if piece.mode in ("keep", "drop") and piece.start is not None:
                self.txt_start.ChangeValue(clock_text(piece.start))
                self.txt_end.ChangeValue(clock_text(piece.end or 0))
            else:
                self.txt_start.ChangeValue("")
                self.txt_end.ChangeValue("")

        def _on_select(self, _event=None):
            index = self._selected()
            if index < 0:
                return
            self._fill_times(index)

        def _clocks(self):
            try:
                start = parse_clock(self.txt_start.GetValue())
                end = parse_clock(self.txt_end.GetValue())
            except ValueError:
                return None, None, MSG_BAD_CLOCK
            return start, end, ""

        def _on_char(self, event):
            key = event.GetKeyCode()
            if key == wx.WXK_ESCAPE and (self._busy or self._playing):
                self._on_stop()
                return
            if (
                event.AltDown()
                and not event.ControlDown()
                and not event.ShiftDown()
                and key not in (wx.WXK_F4, wx.WXK_TAB)
            ):
                letter = ""
                if ord("A") <= key <= ord("Z") or ord("a") <= key <= ord("z"):
                    letter = chr(key).upper()
                name = _ALT_ACTIONS.get(letter)
                if name:
                    self._alt_do(name)
                    return
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                focused = self.FindFocus()
                if focused is self.lst:
                    self._on_listen()
                    return
                if focused is self.lst_done:
                    self._on_use_done()
                    return
            event.Skip()

        def _alt_do(self, name: str):
            if name == "add":
                self._on_add()
            elif name == "folder":
                self._on_add_folder()
            elif name == "up":
                self._move(-1)
            elif name == "down":
                self._move(1)
            elif name == "remove":
                self._on_remove()
            elif name == "listen":
                self._on_listen()
            elif name == "stop":
                self._on_stop()
            elif name == "keep":
                self._on_keep()
            elif name == "drop":
                self._on_drop()
            elif name == "another":
                self._on_another()
            elif name == "run":
                self._on_run()
            elif name == "join":
                self._on_join()

        def _set_busy(self, busy: bool):
            self._busy = busy
            for btn in (
                self.btn_add, self.btn_folder, self.btn_up, self.btn_down, self.btn_remove,
                self.btn_listen, self.btn_keep, self.btn_drop, self.btn_another,
                self.btn_run, self.btn_join,
            ):
                btn.Enable(not busy)

        def _stop_sound(self):
            self._playing = False
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass

        def _on_stop(self, _event=None):
            self._cancel.set()
            self._stop_sound()
            self._say(MSG_STOPPED)

        def _on_add(self, _event=None):
            if self._busy:
                self._say(MSG_WORKING)
                return
            with wx.FileDialog(
                self,
                "Scegli audio o video",
                wildcard=_WILDCARD,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
            ) as fd:
                if fd.ShowModal() != wx.ID_OK:
                    return
                paths = list(fd.GetPaths() or [])
            self._ingest(paths)

        def _on_add_folder(self, _event=None):
            if self._busy:
                self._say(MSG_WORKING)
                return
            with wx.DirDialog(
                self,
                "Scegli la cartella",
                style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
            ) as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                folder = dlg.GetPath()
            paths = _files_in_folder(folder, _AUDIO_EXTS | _VIDEO_EXTS)
            if not paths:
                self._say(
                    "Nessun audio o video in questa cartella. "
                    "Le cartelle dentro non si aprono."
                )
                return
            self._ingest(paths)

        def _load_initial(self):
            paths = [p for p in self._initial if p]
            self._initial = []
            if paths:
                self._ingest(paths)
            elif not _ffmpeg_exe():
                self._say(MSG_NEED_FFMPEG)

        def _ingest(self, paths: list[str]):
            if not paths:
                return
            self._cancel.clear()
            self._set_busy(True)
            self._say(MSG_READING)

            def work():
                added = []
                skipped = []
                for path in paths:
                    if self._cancel.is_set():
                        wx.CallAfter(self._ingest_done, [], [], True)
                        return
                    piece, err = load_piece(path)
                    if piece is None:
                        skipped.append(err or os.path.basename(path))
                    else:
                        added.append(piece)
                wx.CallAfter(self._ingest_done, added, skipped, False)

            threading.Thread(target=work, daemon=True).start()

        def _ingest_done(self, added, skipped, cancelled):
            if not self._open:
                return
            self._set_busy(False)
            if cancelled:
                self._say(MSG_STOPPED)
                return
            if added:
                self._rows.extend(added)
                self._refresh(len(self._rows) - len(added))
            if len(added) == 1 and not skipped:
                known = self._done_label(added[0].path)
                if known:
                    self._say(f"Aggiunto {known}")
                else:
                    self._say(f"Aggiunto {added[0].label()}.")
                return
            if added and skipped:
                names = ", ".join(skipped)
                self._say(f"Aggiunti {len(added)} su {len(added) + len(skipped)}. Non entrati: {names}.")
                return
            if added:
                self._say(f"Aggiunti {len(added)} file.")
                return
            if skipped:
                self._say("Nessun audio o video. Non entrati: " + ", ".join(skipped) + ".")
                return
            self._say(MSG_EMPTY)

        def _move(self, delta: int):
            if self._busy:
                self._say(MSG_WORKING)
                return
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            nxt = index + delta
            if nxt < 0 or nxt >= len(self._rows):
                self._say(self._rows[index].label())
                return
            self._rows[index], self._rows[nxt] = self._rows[nxt], self._rows[index]
            self._refresh(nxt)
            self._say(self._rows[nxt].label())

        def _on_remove(self, _event=None):
            if self._busy:
                self._say(MSG_WORKING)
                return
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            name = os.path.basename(self._rows[index].path)
            del self._rows[index]
            self._refresh(min(index, len(self._rows) - 1))
            if self._rows:
                self._say(f"Rimosso {name}.")
            else:
                self._say(f"Rimosso {name}. {MSG_EMPTY}")

        def _update_clock_label(self):
            parts = [
                explain_clock(self.txt_start.GetValue(), "Inizio"),
                explain_clock(self.txt_end.GetValue(), "Fine"),
            ]
            phrase = " ".join(part for part in parts if part)
            start_raw = (self.txt_start.GetValue() or "").strip()
            end_raw = (self.txt_end.GetValue() or "").strip()
            if phrase and MSG_BAD_CLOCK not in phrase:
                if not start_raw and end_raw:
                    phrase += " Il tratto parte dall'inizio."
                elif start_raw and not end_raw:
                    phrase += " Il tratto arriva fino alla fine del file."
            shown = phrase or _CLOCK_HINT
            self.lbl_clock.SetLabel(shown)
            self.lbl_clock.Wrap(680)

        def _refresh_done(self):
            self.lst_done.Clear()
            if not self._done:
                self.lst_done.Append(MSG_NO_DONE)
                self.lst_done.SetSelection(0)
                return
            for label, _path in self._done:
                self.lst_done.Append(label)
            self.lst_done.SetSelection(len(self._done) - 1)

        def _on_another(self, _event=None):
            if self._busy:
                self._say(MSG_WORKING)
                return
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            start, end, err = self._clocks()
            if err:
                self._say(err)
                return
            if start is None and end is None:
                self._say(MSG_NEED_RANGE)
                return
            clone = clone_piece(self._rows[index])
            clone.mode = "all"
            phrase = apply_keep(clone, start, end)
            if clone.mode != "keep":
                self._say(phrase)
                return
            self._rows.append(clone)
            self._refresh(len(self._rows) - 1)
            self._say(f"Aggiunto un altro tratto. {clone.label()}")

        def _on_use_done(self):
            if self._busy:
                self._say(MSG_WORKING)
                return
            if not self._done:
                self._say(MSG_NO_DONE)
                return
            index = self.lst_done.GetSelection()
            if index < 0 or index >= len(self._done):
                self._say(MSG_SELECT)
                return
            _label, path = self._done[index]
            if not os.path.isfile(path):
                self._say(f"{os.path.basename(path)} non c'è più.")
                return
            self._ingest([path])

        def _on_keep(self, _event=None):
            self._apply(apply_keep)

        def _on_drop(self, _event=None):
            self._apply(apply_drop)

        def _apply(self, fn):
            if self._busy:
                self._say(MSG_WORKING)
                return
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            start, end, err = self._clocks()
            if err:
                self._say(err)
                return
            phrase = fn(self._rows[index], start, end)
            self._refresh(index)
            self._say(phrase)

        def _on_listen(self):
            if self._busy:
                self._say(MSG_WORKING)
                return
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            piece = self._rows[index]
            self._cancel.clear()
            self._stop_sound()
            self._set_busy(True)
            self._say(MSG_PREPARE)
            dest = os.path.join(tempfile.gettempdir(), "rtad-ascolto.wav")

            def work():
                ok, phrase = preview_wav(piece, dest, self._cancel)
                wx.CallAfter(self._listen_done, ok, phrase, dest)

            threading.Thread(target=work, daemon=True).start()

        def _listen_done(self, ok, phrase, dest):
            if not self._open:
                return
            self._set_busy(False)
            if self._cancel.is_set() or not ok:
                self._say(MSG_STOPPED if self._cancel.is_set() else phrase)
                return
            try:
                winsound.PlaySound(
                    dest,
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
                self._playing = True
                self._preview = dest
            except Exception:
                self._say(MSG_LISTEN_FAIL)
                return
            self._say(phrase)

        def _on_run(self, _event=None):
            if self._busy:
                self._say(MSG_WORKING)
                return
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            piece = self._rows[index]
            if piece.mode == "all":
                self._say(MSG_NEED_RANGE)
                return
            self._start_job([piece])

        def _on_join(self, _event=None):
            if self._busy:
                self._say(MSG_WORKING)
                return
            if len(self._rows) < 2:
                self._say(MSG_NEED_TWO)
                return
            self._start_job(list(self._rows))

        def _start_job(self, pieces):
            rows = [clone_piece(piece) for piece in pieces]
            err = _job_error(rows)
            if err:
                self._say(err)
                return
            notes = _notices(rows)
            self._cancel.clear()
            self._stop_sound()
            self._set_busy(True)
            self._say(" ".join(notes + [MSG_WORKING]))

            def work():
                made = []
                ok, phrase = build(rows, self._cancel, made)
                path = made[0] if made else ""
                label = ""
                if ok and path and os.path.isfile(path):
                    label = history_label(rows, path, speak_duration(_duration_of(path)))
                wx.CallAfter(self._run_done, ok, phrase, path, label)

            threading.Thread(target=work, daemon=True).start()

        def _run_done(self, ok, phrase, path, label):
            if not self._open:
                return
            self._set_busy(False)
            if ok and path and label and os.path.isfile(path):
                self._done.append((label, path))
                self._refresh_done()
                text = label if label.endswith(".") else f"{label}."
                self._say(f"Creato {text} Nella stessa cartella.")
                return
            self._say(phrase)

    globals()["ClipDialog"] = ClipDialog


_install_dialog()
