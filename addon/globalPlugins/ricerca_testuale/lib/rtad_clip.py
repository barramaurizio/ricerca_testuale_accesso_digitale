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
    "Un audio e un video non si uniscono con Unisci. "
    "Per mettere l'audio sul video: Invio sul pulsante Audio sul video, o un clic. "
    "Altrimenti tieni solo audio, oppure solo video."
)
MSG_NEED_AV_PAIR = (
    "Per mettere un audio su un video servono un file video e un file audio in elenco. "
    "Aggiungi entrambi, poi Invio sul pulsante Audio sul video, o un clic. "
    "Vanno bene qualsiasi video e qualsiasi audio: non devono essere dello stesso pezzo. "
    "Puoi sostituire l'audio del video, oppure mischiarlo con volumi regolabili."
)
MSG_AV_PAIR_ONLY = (
    "Per Audio sul video lascia in elenco un solo video e un solo audio. "
    "Rimuovi gli altri, poi riprova."
)
MSG_PAUSED_AT = "Fermato a {pos}."
MSG_RESUME_AT = "Riparto da {pos}."
MSG_SEEK_AT = "Ascolto da {pos}."
MSG_VOL_AT = "Volume ascolto {vol} percento."
MSG_AV_CANCEL = "Audio sul video annullato. Niente è stato scritto."
# Ascolto: freccia ± secondi; volume 0–200 (oltre 100 con soft-limit).
_LISTEN_SEEK_SEC = 5.0
_LISTEN_VOL_MIN = 0
_LISTEN_VOL_MAX = 200
_LISTEN_VOL_STEP = 5
_LISTEN_VOL_DEFAULT = 100
_LISTEN_HEAD_SEC = 20.0
_LISTEN_FULL_MAX_SEC = 3 * 3600.0
MSG_LISTEN_END = "Fine dell'ascolto. Riparto dall'inizio."
MSG_LISTEN_HEAD_ON = (
    "Ascolto solo i primi 20 secondi: attivato."
)
MSG_LISTEN_HEAD_OFF = (
    "Ascolto solo i primi 20 secondi: disattivato. "
    "Si ascolta tutto il pezzo."
)
# Compatibilità testi guida / anteprima
MSG_LISTEN_HEAD = "Ascolto solo i primi 20 secondi."
MSG_LISTEN_FULL = "Si ascolta tutto il pezzo."
_AV_VOL_MIN = 0
_AV_VOL_MAX = 200
_AV_VOL_STEP = 10
_AV_VOL_DEFAULT = 100
MSG_EMPTY_MEDIA = (
    "Un file in elenco è vuoto (0 byte) o non si apre. "
    "Scegli un audio e un video con contenuto, poi riprova. "
    "Il file di partenza resta com'è."
)
MSG_AUDIO_UNREADABLE = (
    "L'audio in elenco non si legge (durata assente o niente traccia audio). "
    "Prova un altro file audio, poi Invio su Audio sul video, o un clic. "
    "Il file di partenza resta com'è."
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
    "Spazio sull'elenco ascolta; Spazio di nuovo mette in pausa e dice l'orario; "
    "Spazio ancora riparte da lì. "
    "Mentre suona o in pausa, freccia destra e sinistra avanti e indietro di 5 secondi, "
    "senza interrompere l'ascolto. "
    "Mentre suona, freccia su e giù regolano il volume fino a 200 percento, in continuo. "
    "In pausa o da fermo, freccia su e giù scorrono l'elenco. "
    "Ogni file ricorda punto e volume finché la finestra resta aperta. "
    "La casella «Solo i primi 20 secondi» accorcia l'ascolto; spenta, si ascolta tutto il pezzo. "
    "Spazio vale sull'elenco; sui pulsanti Spazio attiva il pulsante. "
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
    "Con un video e un audio, Invio sul pulsante Audio sul video, o un clic, "
    "apre le scelte: sostituisci o mix con volumi, e la durata "
    "(il più corto, tutto il video, tutto l'audio). "
    "I file creati restano nell'elenco Fatti. "
    "Il file unito si chiama nome1-unione-nome2, dai nomi dei due file. "
    "Se sono più di due, restano i primi due nomi e si aggiunge e-N. "
    "Il video con l'audio nuovo si chiama nomevideo-con-audio-nomeaudio. "
    "Se il nome c'è già, si aggiunge -2. "
    "Lo Stato, la barra di stato e Fatti dicono la stessa frase, "
    "con il nome di ogni file. "
    "Se il file resta in Temp, dicono il percorso intero. "
    "Dall'elenco, Alt e la lettera del pulsante fa la stessa cosa: "
    "A Aggiungi, K Aggiungi cartella, S Sposta su, G Sposta giù, M Rimuovi, C Ascolta, "
    "F Ferma, T Tieni, O Togli, L Altro tratto, E Esegui, U Unisci, V Audio sul video. "
    "Invio o doppio clic su un fatto lo rimette nell'elenco di lavoro. "
    "Spazio su un fatto ascolta quel risultato; Spazio di nuovo pausa con orario; "
    "poi riparte da lì. Durante l'ascolto valgono le frecce come sopra. "
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
    "V": "audio_on_video",
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


def spoken_result_path(path: str) -> str:
    """Nome del file creato. Se resta in Temp, il percorso intero."""
    full = os.path.abspath(path or "")
    if not full:
        return ""
    try:
        tmp = os.path.normcase(os.path.abspath(tempfile.gettempdir()))
        here = os.path.normcase(full)
        if here == tmp or here.startswith(tmp + os.sep):
            return full
    except Exception:
        pass
    return os.path.basename(full)


def history_label(pieces: list, out_path: str, dur_spoken: str) -> str:
    name = spoken_result_path(out_path)
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


def _stream_is_cover_art(stream: dict) -> bool:
    """True se è solo copertina/foto nel file (mp3 con cover), non un video vero."""
    if not isinstance(stream, dict):
        return False
    disp = stream.get("disposition")
    if not isinstance(disp, dict):
        return False
    try:
        if int(disp.get("attached_pic") or 0):
            return True
    except (TypeError, ValueError):
        pass
    try:
        if int(disp.get("still_image") or 0):
            return True
    except (TypeError, ValueError):
        pass
    return False


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
                # Copertina ID3/embedded: non è un video da unire o da «Audio sul video».
                if _stream_is_cover_art(st):
                    continue
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
    # Estensione audio + traccia audio: resta audio anche se ffprobe ha visto altro rumore.
    if ext in _AUDIO_EXTS and piece.has_audio and piece.has_video:
        piece.has_video = False
        piece.video_codec = ""
        piece.width = 0
        piece.height = 0
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


def _clip_name_piece(text: str, max_len: int) -> str:
    """Accorcia un pezzo di nome sul confine di parola, se serve."""
    raw = (text or "").strip(" .-_")
    if max_len < 8:
        max_len = 8
    if len(raw) <= max_len:
        return raw
    cut = raw[:max_len].rsplit(" ", 1)[0].strip(" .-_")
    return cut or raw[:max_len].strip(" .-_")


def _union_stem(pieces: list[Piece]) -> str:
    """Due nomi: a-unione-b. Da tre in su: a-unione-b-e-N, col tetto del nome file."""
    stems = [
        os.path.splitext(os.path.basename(piece.path))[0] for piece in pieces
    ]
    joiner = "-unione-"
    # ~220: resta spazio per -2 e l'estensione sul percorso intero.
    max_total = 220
    if len(stems) == 2:
        budget = max_total - len(joiner)
        first_room = max(8, budget // 2)
        a = _clip_name_piece(stems[0], first_room)
        b = _clip_name_piece(stems[1], max(8, budget - len(a)))
        return f"{a}{joiner}{b}"
    more = f"-e-{len(stems)}"
    budget = max_total - len(joiner) - len(more)
    first_room = max(8, budget // 2)
    a = _clip_name_piece(stems[0], first_room)
    b = _clip_name_piece(stems[1], max(8, budget - len(a)))
    return f"{a}{joiner}{b}{more}"


def _audio_on_video_stem(video: Piece, audio: Piece) -> str:
    """nomevideo-con-audio-nomeaudio, col tetto del nome file."""
    joiner = "-con-audio-"
    max_total = 220
    v_stem = os.path.splitext(os.path.basename(video.path))[0]
    a_stem = os.path.splitext(os.path.basename(audio.path))[0]
    budget = max_total - len(joiner)
    first_room = max(8, budget // 2)
    v = _clip_name_piece(v_stem, first_room)
    a = _clip_name_piece(a_stem, max(8, budget - len(v)))
    return f"{v}{joiner}{a}"


def _pick_av_pair(pieces: list[Piece]) -> tuple[Piece | None, Piece | None, str]:
    """Un video e un audio, oppure errore."""
    rows = list(pieces or [])
    videos = [p for p in rows if p.kind == "video"]
    audios = [p for p in rows if p.kind == "audio"]
    if len(videos) == 1 and len(audios) == 1 and len(rows) == 2:
        return videos[0], audios[0], ""
    if not videos or not audios:
        return None, None, MSG_NEED_AV_PAIR
    return None, None, MSG_AV_PAIR_ONLY


def _media_file_ok(path: str) -> bool:
    """True se il file esiste e non è vuoto."""
    try:
        return bool(path) and os.path.isfile(path) and os.path.getsize(path) > 0
    except OSError:
        return False


def _clamp_av_vol(pct) -> int:
    try:
        value = int(round(float(pct)))
    except (TypeError, ValueError):
        value = _AV_VOL_DEFAULT
    step = _AV_VOL_STEP
    value = int(round(value / step) * step)
    return max(_AV_VOL_MIN, min(_AV_VOL_MAX, value))


def _vol_af(pct: int) -> str:
    """Filtro volume ffmpeg. Oltre 100%: gain + soft-limiter (niente clip brusco)."""
    gain = max(0.0, float(_clamp_av_vol(pct)) / 100.0)
    if gain > 1.001:
        return (
            f"volume={gain:.4f},"
            "alimiter=limit=0.95:attack=5:release=50:level=false"
        )
    return f"volume={gain:.4f}"


def _length_note(v_dur: float, a_dur: float, length_mode: str) -> str:
    if v_dur <= 0.5 or a_dur <= 0.5 or abs(v_dur - a_dur) <= 0.5:
        return ""
    if length_mode == "both":
        if a_dur > v_dur:
            return (
                f"Il video dura {speak_duration(v_dur)}, "
                f"l'audio {speak_duration(a_dur)}. "
                "Ho tenuto tutti e due; l'immagine resta sull'ultimo fotogramma. "
            )
        return (
            f"L'audio dura {speak_duration(a_dur)}, "
            f"il video {speak_duration(v_dur)}. "
            "Ho tenuto tutti e due; dopo l'audio il video continua. "
        )
    if length_mode == "video":
        if a_dur < v_dur:
            return (
                f"L'audio dura {speak_duration(a_dur)}, "
                f"il video {speak_duration(v_dur)}. "
                "Ho tenuto la durata del video. "
            )
        return (
            f"L'audio dura {speak_duration(a_dur)}, "
            f"il video {speak_duration(v_dur)}. "
            "Ho tenuto la durata del video. "
        )
    if length_mode == "audio":
        if v_dur < a_dur:
            return (
                f"Il video dura {speak_duration(v_dur)}, "
                f"l'audio {speak_duration(a_dur)}. "
                "Ho tenuto la durata dell'audio; l'immagine resta sull'ultimo fotogramma. "
            )
        return (
            f"Il video dura {speak_duration(v_dur)}, "
            f"l'audio {speak_duration(a_dur)}. "
            "Ho tenuto la durata dell'audio. "
        )
    if a_dur < v_dur:
        return (
            f"L'audio dura {speak_duration(a_dur)}, "
            f"il video {speak_duration(v_dur)}. "
            "Il risultato si ferma al più corto. "
        )
    return (
        f"Il video dura {speak_duration(v_dur)}, "
        f"l'audio {speak_duration(a_dur)}. "
        "Il risultato si ferma al più corto. "
    )


def _hms_from_seconds(seconds: float) -> tuple[int, int, int]:
    total = max(0, int(round(float(seconds or 0))))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return h, m, s


def _seconds_from_hms(h: int, m: int, s: int) -> float:
    try:
        return max(0.0, float(int(h) * 3600 + int(m) * 60 + int(s)))
    except (TypeError, ValueError):
        return 0.0


def build_audio_on_video(
    video: Piece,
    audio: Piece,
    cancel=None,
    made_path=None,
    mode: str = "replace",
    video_vol: int = _AV_VOL_DEFAULT,
    audio_vol: int = _AV_VOL_DEFAULT,
    length_mode: str = "shortest",
    video_cap: float = 0.0,
    audio_cap: float = 0.0,
) -> tuple[bool, str]:
    """Scrive un video nuovo: immagini del video + audio (sostituisci o mix).

    mode: replace | mix
    length_mode: shortest | video | audio | both
    video_vol / audio_vol: 0–200 (oltre 100 con soft-limiter).
    video_cap / audio_cap: tetto in secondi su quel pezzo (0 = intero).
    """
    if not _ffmpeg_exe():
        return False, MSG_NEED_FFMPEG
    if video is None or audio is None:
        return False, MSG_NEED_AV_PAIR
    if cancel is not None and cancel.is_set():
        return False, MSG_STOPPED
    mode = (mode or "replace").strip().lower()
    if mode not in ("replace", "mix"):
        mode = "replace"
    length_mode = (length_mode or "shortest").strip().lower()
    if length_mode not in ("shortest", "video", "audio", "both"):
        length_mode = "shortest"
    video_vol = _clamp_av_vol(video_vol)
    audio_vol = _clamp_av_vol(audio_vol)
    try:
        video_cap = float(video_cap or 0)
    except (TypeError, ValueError):
        video_cap = 0.0
    try:
        audio_cap = float(audio_cap or 0)
    except (TypeError, ValueError):
        audio_cap = 0.0
    if not _media_file_ok(video.path) or not _media_file_ok(audio.path):
        empty = []
        if not _media_file_ok(getattr(video, "path", "")):
            empty.append(os.path.basename(video.path) if video else "video")
        if not _media_file_ok(getattr(audio, "path", "")):
            empty.append(os.path.basename(audio.path) if audio else "audio")
        names = " e ".join(empty) if empty else "un file"
        return False, (
            f"«{names}» è vuoto (0 byte) o non si apre. "
            "Scegli un audio e un video con contenuto, poi riprova. "
            "Il file di partenza resta com'è."
        )
    a_dur = float(audio.duration or 0)
    if a_dur <= 0 and not audio.has_audio:
        probed, _err = load_piece(audio.path)
        if probed is not None:
            audio = probed
            a_dur = float(audio.duration or 0)
        if a_dur <= 0 and not getattr(audio, "has_audio", False):
            if os.path.getsize(audio.path) < 1024:
                return False, MSG_EMPTY_MEDIA
            return False, MSG_AUDIO_UNREADABLE
    if not getattr(video, "has_audio", False) and float(video.duration or 0) > 0:
        probed_v, _err = load_piece(video.path)
        if probed_v is not None:
            video = probed_v
    folder = os.path.dirname(os.path.abspath(video.path)) or os.getcwd()
    dest = _unique_output(folder, _audio_on_video_stem(video, audio), ".mp4")
    v_file = float(video.duration or 0)
    a_file = float(a_dur or 0)
    v_dur = v_file
    a_dur = a_file
    if video_cap > 0.1:
        v_dur = min(v_file, video_cap) if v_file > 0.1 else video_cap
    if audio_cap > 0.1:
        a_dur = min(a_file, audio_cap) if a_file > 0.1 else audio_cap
    note = _length_note(v_dur, a_dur, length_mode)
    mix_note = ""
    use_mix = mode == "mix" and bool(getattr(video, "has_audio", False))
    if mode == "mix" and not use_mix:
        mix_note = (
            "Il video non ha audio suo: ho messo solo l'audio scelto "
            "(come in sostituzione). "
        )
        mode = "replace"
    if mode == "mix":
        mix_note = (
            f"Mix: volume video {video_vol} percento, "
            f"volume audio nuovo {audio_vol} percento. "
        )
    elif audio_vol != _AV_VOL_DEFAULT:
        mix_note = f"Volume audio {audio_vol} percento. "
    ff = _ffmpeg_exe()

    def _in_args() -> list[str]:
        """Limita ogni ingresso al tetto scelto, se più corto del file."""
        out = [ff, "-y"]
        if v_dur > 0.1 and (v_file <= 0.1 or v_dur < v_file - 0.05):
            out += ["-t", f"{v_dur:.3f}"]
        out += ["-i", video.path]
        if a_dur > 0.1 and (a_file <= 0.1 or a_dur < a_file - 0.05):
            out += ["-t", f"{a_dur:.3f}"]
        out += ["-i", audio.path]
        return out

    attempts: list[list[str]] = []
    # Caso semplice come 2.0.6: sostituisci, più corto, volume 100, senza tetti.
    if (
        mode == "replace"
        and length_mode == "shortest"
        and audio_vol == 100
        and video_cap <= 0.1
        and audio_cap <= 0.1
    ):
        attempts.append(
            [
                ff, "-y",
                "-i", video.path,
                "-i", audio.path,
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                "-shortest",
                "-movflags", "+faststart",
                dest,
            ]
        )
    a_f = _vol_af(audio_vol)
    v_f = _vol_af(video_vol)
    vf_scale = "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=25,format=yuv420p"
    need_freeze = (
        length_mode in ("audio", "both")
        and a_dur > 0.1
        and v_dur > 0.1
        and a_dur > v_dur + 0.2
    )
    need_apad = (
        length_mode in ("video", "both")
        and v_dur > 0.1
        and a_dur > 0.1
        and v_dur > a_dur + 0.2
    )
    if mode == "replace":
        if need_freeze:
            pad = a_dur - v_dur
            graph = (
                f"[0:v]{vf_scale},tpad=stop_mode=clone:stop_duration={pad:.3f}[v];"
                f"[1:a]{a_f}[a]"
            )
            args = _in_args() + [
                "-filter_complex", graph,
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                "-movflags", "+faststart",
                dest,
            ]
        elif need_apad or (length_mode == "video" and v_dur > 0.1):
            graph = f"[0:v]{vf_scale}[v];[1:a]{a_f},apad[a]"
            args = _in_args() + [
                "-filter_complex", graph,
                "-map", "[v]", "-map", "[a]",
                "-t", f"{v_dur:.3f}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                "-movflags", "+faststart",
                dest,
            ]
        elif length_mode == "audio" and a_dur > 0.1:
            graph = f"[0:v]{vf_scale}[v];[1:a]{a_f}[a]"
            args = _in_args() + [
                "-filter_complex", graph,
                "-map", "[v]", "-map", "[a]",
                "-t", f"{a_dur:.3f}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                "-movflags", "+faststart",
                dest,
            ]
        else:
            graph = f"[0:v]{vf_scale}[v];[1:a]{a_f}[a]"
            args = _in_args() + [
                "-filter_complex", graph,
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                "-shortest",
                "-movflags", "+faststart",
                dest,
            ]
        attempts.append(args)
    else:
        # mix: audio video + audio nuovo
        aformat = "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"
        limit = "alimiter=limit=0.95:attack=5:release=50:level=false"
        if need_freeze:
            pad = a_dur - v_dur
            graph = (
                f"[0:v]{vf_scale},tpad=stop_mode=clone:stop_duration={pad:.3f}[v];"
                f"[0:a]{v_f},{aformat}[a0];"
                f"[1:a]{a_f},{aformat}[a1];"
                f"[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
                f"{limit}[a]"
            )
            args = _in_args() + [
                "-filter_complex", graph,
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                "-movflags", "+faststart",
                dest,
            ]
        elif need_apad or (length_mode == "video" and v_dur > 0.1):
            graph = (
                f"[0:v]{vf_scale}[v];"
                f"[0:a]{v_f},{aformat}[a0];"
                f"[1:a]{a_f},{aformat}[a1];"
                f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
                f"{limit}[a]"
            )
            args = _in_args() + [
                "-filter_complex", graph,
                "-map", "[v]", "-map", "[a]",
                "-t", f"{v_dur:.3f}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                "-movflags", "+faststart",
                dest,
            ]
        else:
            amix_dur = "longest" if length_mode in ("audio", "both") else "shortest"
            graph = (
                f"[0:v]{vf_scale}[v];"
                f"[0:a]{v_f},{aformat}[a0];"
                f"[1:a]{a_f},{aformat}[a1];"
                f"[a0][a1]amix=inputs=2:duration={amix_dur}:dropout_transition=0:normalize=0,"
                f"{limit}[a]"
            )
            args = _in_args() + [
                "-filter_complex", graph,
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                "-shortest",
                "-movflags", "+faststart",
                dest,
            ]
        attempts.append(args)

    ok = False
    last_err = ""
    for args in attempts:
        if cancel is not None and cancel.is_set():
            return False, MSG_STOPPED
        try:
            if os.path.isfile(dest):
                os.remove(dest)
        except OSError:
            pass
        ok_run, err = _run(args, cancel)
        last_err = (err or "").strip()
        ok = ok_run and os.path.isfile(dest) and os.path.getsize(dest) > 0
        if ok:
            break
    if not ok:
        if last_err:
            log.warning("Audio sul video: %s", last_err[:400])
        return False, MSG_FAIL
    if made_path is not None:
        made_path.append(dest)
    dur = _duration_of(dest)
    # «Usato» = dopo i tetti ore/min/s; se diverso dal file, lo diciamo chiaro.
    if abs(v_file - v_dur) > 0.5 or abs(a_file - a_dur) > 0.5:
        src_note = (
            f"File video {speak_duration(v_file)}, "
            f"file audio {speak_duration(a_file)}. "
            f"Usati: video {speak_duration(v_dur)}, "
            f"audio {speak_duration(a_dur)}. "
        )
    else:
        src_note = (
            f"Video usato {speak_duration(v_dur)}, "
            f"audio usato {speak_duration(a_dur)}. "
        )
    return True, (
        f"{mix_note}{note}{src_note}"
        f"Creato {spoken_result_path(dest)}, risultato {speak_duration(dur)}, "
        "nella stessa cartella. Il file di partenza resta com'è."
    )


def _output_for(pieces: list[Piece], reencode: bool) -> str:
    first = pieces[0]
    folder = os.path.dirname(os.path.abspath(first.path)) or os.getcwd()
    if len(pieces) > 1:
        stem = _union_stem(pieces)
    else:
        base = os.path.splitext(os.path.basename(first.path))[0]
        stem = f"{base}-taglio"
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
                    f"Creato {spoken_result_path(dest)}, {speak_duration(dur)}, "
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
            f"Creato {spoken_result_path(dest)}, {speak_duration(dur)}, "
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


def speak_position(seconds: float) -> str:
    """Orario breve per pausa/ripresa (es. «6 s», «1 min 20 s»)."""
    if seconds is None or seconds < 0:
        seconds = 0.0
    total = int(round(float(seconds)))
    if total < 60:
        return f"{total} s"
    m, s = divmod(total, 60)
    if m < 60:
        return f"{m} min {s} s" if s else f"{m} min"
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min {s:02d} s"


def _clamp_listen_vol(pct) -> int:
    try:
        value = int(round(float(pct)))
    except (TypeError, ValueError):
        value = _LISTEN_VOL_DEFAULT
    step = _LISTEN_VOL_STEP
    value = int(round(value / step) * step)
    return max(_LISTEN_VOL_MIN, min(_LISTEN_VOL_MAX, value))


def _soft_gain_pcm(raw: bytes, sampwidth: int, vol_pct: int) -> bytes:
    """Applica volume 0–200. Oltre 100: soft-clip (tanh), senza taglio a dente di sega."""
    vol_pct = _clamp_listen_vol(vol_pct)
    if not raw or sampwidth != 2 or vol_pct == 100:
        return raw
    import array
    import math

    samples = array.array("h")
    samples.frombytes(raw)
    if vol_pct == 0:
        for i in range(len(samples)):
            samples[i] = 0
        return samples.tobytes()
    gain = vol_pct / 100.0
    peak = 32767.0
    for i, sample in enumerate(samples):
        x = float(sample) * gain
        if x > peak or x < -peak:
            x = peak * math.tanh(x / peak)
        if x >= peak:
            samples[i] = 32767
        elif x <= -peak:
            samples[i] = -32768
        else:
            samples[i] = int(round(x))
    return samples.tobytes()


def slice_wav_for_play(
    src: str, dest: str, start_sec: float, vol_pct: int = 100
) -> tuple[bool, float]:
    """Copia un wav da start_sec in poi. Ritorna (ok, secondi rimasti)."""
    try:
        with wave.open(src, "rb") as reader:
            rate = reader.getframerate() or 0
            channels = reader.getnchannels() or 1
            width = reader.getsampwidth() or 2
            total = reader.getnframes() or 0
            if rate <= 0 or total <= 0:
                return False, 0.0
            start_frame = max(0, int(float(start_sec or 0) * rate))
            if start_frame >= total:
                return False, 0.0
            remain_frames = total - start_frame
            remain_sec = remain_frames / float(rate)
            if remain_sec < 0.12:
                return False, remain_sec
            reader.setpos(start_frame)
            raw = reader.readframes(remain_frames)
            raw = _soft_gain_pcm(raw, width, vol_pct)
            with wave.open(dest, "wb") as writer:
                writer.setnchannels(channels)
                writer.setsampwidth(width)
                writer.setframerate(rate)
                writer.writeframes(raw)
        ok = os.path.isfile(dest) and os.path.getsize(dest) > 44
        return ok, remain_sec
    except Exception:
        log.exception("slice_wav_for_play")
        return False, 0.0


def _restore_wave_out_volume() -> None:
    """Ripristina il wave del processo a pieno (uscita / recovery).

    Non usarlo per l'ascolto: waveOutSetVolume(0) nell'Add-on abbassa anche
    la sintesi di NVDA (stesso processo). In Standalone è un processo a parte.
    """
    try:
        import ctypes

        ctypes.windll.winmm.waveOutSetVolume(0, 0xFFFFFFFF)
    except Exception:
        pass


def _listen_volume_af(user_vol: int) -> str:
    """Filtro ffmpeg per volume ascolto 0–200 (oltre 100 con soft-limiter)."""
    vol = _clamp_listen_vol(user_vol)
    gain = max(0.0, float(vol) / 100.0)
    if gain > 1.0:
        return (
            f"volume={gain:.4f},"
            "alimiter=limit=0.95:attack=5:release=50:level=false"
        )
    return f"volume={gain:.4f}"


def _bake_listen_volume_pcm(src: str, dest: str, vol: int) -> bool:
    """Fallback: volume in PCM (pezzi corti; sui lunghi può impiegare)."""
    with wave.open(src, "rb") as reader:
        rate = reader.getframerate() or 22050
        channels = reader.getnchannels() or 1
        width = reader.getsampwidth() or 2
        raw = reader.readframes(reader.getnframes() or 0)
    raw = _soft_gain_pcm(raw, width, vol)
    with wave.open(dest, "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(width)
        writer.setframerate(rate)
        writer.writeframes(raw)
    return os.path.isfile(dest) and os.path.getsize(dest) > 44


def bake_listen_volume(src: str, dest: str, user_vol: int) -> bool:
    """Scrive dest con il volume utente. A 100% copia il base (niente ricodifica)."""
    if not src or not os.path.isfile(src):
        return False
    vol = _clamp_listen_vol(user_vol)
    try:
        if vol == 100:
            if os.path.abspath(src) == os.path.abspath(dest):
                return True
            import shutil

            shutil.copy2(src, dest)
            return os.path.isfile(dest) and os.path.getsize(dest) > 44
        ff = _ffmpeg_exe()
        if ff:
            af = _listen_volume_af(vol)
            ok, _err = _run(
                [ff, "-y", "-i", src, "-af", af, "-ac", "1", "-ar", "22050", dest],
                None,
                timeout=600,
            )
            if bool(ok) and os.path.isfile(dest) and os.path.getsize(dest) > 44:
                return True
        return _bake_listen_volume_pcm(src, dest, vol)
    except Exception:
        log.exception("bake_listen_volume")
        try:
            return _bake_listen_volume_pcm(src, dest, vol)
        except Exception:
            log.exception("bake_listen_volume_pcm")
            return False


class LiveListenPlayer:
    """Ascolto wav con volume 0–200 sui campioni (niente waveOutSetVolume / NVDA).

    Seek e pausa ripartono il thread dal punto giusto (affidabile).
    Il volume cambia in tempo reale mentre suona, senza ricuocere il file.
    """

    _BUF_MS = 50

    def __init__(self):
        self._lock = threading.RLock()
        self._vol = _LISTEN_VOL_DEFAULT
        self._path = ""
        self._rate = 22050
        self._channels = 1
        self._width = 2
        self._nframes = 0
        self._frame = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._playing = False

    def set_volume(self, pct: int) -> None:
        with self._lock:
            self._vol = _clamp_listen_vol(pct)

    def volume(self) -> int:
        with self._lock:
            return int(self._vol)

    def is_playing(self) -> bool:
        with self._lock:
            return bool(self._playing) and bool(self._thread and self._thread.is_alive())

    def is_open(self) -> bool:
        with self._lock:
            return bool(self._thread and self._thread.is_alive())

    def position_sec(self) -> float:
        with self._lock:
            rate = float(self._rate or 1)
            return max(0.0, float(self._frame) / rate)

    def duration_sec(self) -> float:
        with self._lock:
            rate = float(self._rate or 1)
            return max(0.0, float(self._nframes) / rate)

    def _halt(self, clear_path: bool = False) -> None:
        self._stop.set()
        thread = None
        with self._lock:
            thread = self._thread
            self._playing = False
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.5)
        with self._lock:
            self._thread = None
            self._playing = False
            if clear_path:
                self._path = ""
                self._frame = 0

    def stop(self) -> None:
        self._halt(clear_path=True)

    def pause(self) -> float:
        with self._lock:
            path = self._path
            pos = self.position_sec()
            vol = self._vol
            rate = self._rate
            channels = self._channels
            width = self._width
            nframes = self._nframes
        self._halt(clear_path=False)
        with self._lock:
            # Conserva i metadati per resume/seek anche a thread fermo.
            self._path = path
            self._vol = vol
            self._rate = rate
            self._channels = channels
            self._width = width
            self._nframes = nframes
            self._frame = int(max(0.0, pos) * float(rate or 1))
            self._playing = False
        return max(0.0, pos)

    def resume(self) -> bool:
        with self._lock:
            path = self._path
            pos = float(self._frame) / float(self._rate or 1)
            vol = self._vol
        if not path or not os.path.isfile(path):
            return False
        return self.play(path, from_sec=pos, vol=vol)

    def seek(self, sec: float, play: bool = True) -> bool:
        with self._lock:
            path = self._path
            vol = self._vol
            rate = float(self._rate or 1)
            nframes = int(self._nframes)
        if not path or not os.path.isfile(path):
            return False
        frame = int(max(0.0, float(sec)) * rate)
        if nframes > 0:
            frame = min(frame, max(0, nframes - 1))
        pos = float(frame) / rate
        if play:
            return self.play(path, from_sec=pos, vol=vol)
        self._halt(clear_path=False)
        with self._lock:
            self._path = path
            self._vol = vol
            self._frame = frame
            self._playing = False
        return True

    def play(self, path: str, from_sec: float = 0.0, vol: int | None = None) -> bool:
        if not path or not os.path.isfile(path):
            return False
        try:
            with wave.open(path, "rb") as reader:
                rate = int(reader.getframerate() or 0)
                channels = int(reader.getnchannels() or 1)
                width = int(reader.getsampwidth() or 2)
                nframes = int(reader.getnframes() or 0)
        except Exception:
            log.exception("LiveListenPlayer.play open")
            return False
        if rate <= 0 or nframes <= 0 or width != 2:
            return False
        start = int(max(0.0, float(from_sec or 0)) * rate)
        # Oltre la fine: resta sull'ultimo frame (non ripartire da zero).
        if nframes > 0 and start >= nframes:
            start = max(0, nframes - 1)
        self._halt(clear_path=False)
        with self._lock:
            self._path = path
            self._rate = rate
            self._channels = max(1, channels)
            self._width = width
            self._nframes = nframes
            self._frame = start
            if vol is not None:
                self._vol = _clamp_listen_vol(vol)
            self._stop = threading.Event()
            self._playing = True
            self._thread = threading.Thread(
                target=self._run, args=(path, start), daemon=True
            )
            self._thread.start()
        return True

    def _run(self, path: str, start_frame: int) -> None:
        import ctypes
        from ctypes import wintypes

        class WAVEFORMATEX(ctypes.Structure):
            _fields_ = [
                ("wFormatTag", wintypes.WORD),
                ("nChannels", wintypes.WORD),
                ("nSamplesPerSec", wintypes.DWORD),
                ("nAvgBytesPerSec", wintypes.DWORD),
                ("nBlockAlign", wintypes.WORD),
                ("wBitsPerSample", wintypes.WORD),
                ("cbSize", wintypes.WORD),
            ]

        class WAVEHDR(ctypes.Structure):
            _fields_ = [
                ("lpData", ctypes.c_void_p),
                ("dwBufferLength", wintypes.DWORD),
                ("dwBytesRecorded", wintypes.DWORD),
                ("dwUser", ctypes.c_void_p),
                ("dwFlags", wintypes.DWORD),
                ("dwLoops", wintypes.DWORD),
                ("lpNext", ctypes.c_void_p),
                ("reserved", ctypes.c_void_p),
            ]

        winmm = ctypes.windll.winmm
        WAVE_MAPPER = 0xFFFFFFFF  # -1 as DWORD
        WAVE_FORMAT_PCM = 1
        WHDR_DONE = 0x00000001
        CALLBACK_NULL = 0

        with self._lock:
            rate = int(self._rate)
            channels = int(self._channels)
            width = int(self._width)
            nframes = int(self._nframes)

        hwo = wintypes.HANDLE()
        fmt = WAVEFORMATEX()
        fmt.wFormatTag = WAVE_FORMAT_PCM
        fmt.nChannels = channels
        fmt.nSamplesPerSec = rate
        fmt.wBitsPerSample = width * 8
        fmt.nBlockAlign = channels * width
        fmt.nAvgBytesPerSec = rate * fmt.nBlockAlign
        fmt.cbSize = 0
        err = int(
            winmm.waveOutOpen(
                ctypes.byref(hwo),
                WAVE_MAPPER,
                ctypes.byref(fmt),
                0,
                0,
                CALLBACK_NULL,
            )
            or 0
        )
        if err:
            log.warning("waveOutOpen err=%s", err)
            with self._lock:
                self._playing = False
                self._thread = None
            return

        frames_per_buf = max(1, int(rate * (self._BUF_MS / 1000.0)))
        byte_len = frames_per_buf * channels * width
        # Due buffer: i bytes devono restare vivi finché WHDR_DONE.
        bufs = [ctypes.create_string_buffer(byte_len) for _ in range(2)]
        hdrs = [WAVEHDR() for _ in range(2)]
        reader = None
        try:
            reader = wave.open(path, "rb")
            reader.setpos(min(max(0, int(start_frame)), max(0, nframes - 1)))
            with self._lock:
                self._frame = reader.tell()

            def _wait_done(hdr: WAVEHDR) -> bool:
                while not (int(hdr.dwFlags) & WHDR_DONE):
                    if self._stop.is_set():
                        return False
                    time.sleep(0.005)
                return True

            def _queue(idx: int) -> bool:
                if self._stop.is_set():
                    return False
                frame_pos = reader.tell()
                if frame_pos >= nframes:
                    return False
                raw = reader.readframes(frames_per_buf)
                if not raw:
                    return False
                with self._lock:
                    vol = int(self._vol)
                gained = _soft_gain_pcm(raw, width, vol)
                n = min(len(gained), byte_len)
                bufs[idx][:n] = gained[:n]
                if n < byte_len:
                    bufs[idx][n:byte_len] = b"\x00" * (byte_len - n)
                hdr = hdrs[idx]
                hdr.lpData = ctypes.addressof(bufs[idx])
                hdr.dwBufferLength = n
                hdr.dwBytesRecorded = 0
                hdr.dwUser = 0
                hdr.dwFlags = 0
                hdr.dwLoops = 0
                hdr.lpNext = 0
                hdr.reserved = 0
                if winmm.waveOutPrepareHeader(hwo, ctypes.byref(hdr), ctypes.sizeof(hdr)):
                    return False
                if winmm.waveOutWrite(hwo, ctypes.byref(hdr), ctypes.sizeof(hdr)):
                    winmm.waveOutUnprepareHeader(
                        hwo, ctypes.byref(hdr), ctypes.sizeof(hdr)
                    )
                    return False
                got = n // max(1, channels * width)
                with self._lock:
                    self._frame = min(nframes, frame_pos + got)
                return True

            active: list[int] = []
            for i in range(2):
                if not _queue(i):
                    break
                active.append(i)
            while active and not self._stop.is_set():
                idx = active.pop(0)
                if not _wait_done(hdrs[idx]):
                    break
                winmm.waveOutUnprepareHeader(
                    hwo, ctypes.byref(hdrs[idx]), ctypes.sizeof(hdrs[idx])
                )
                hdrs[idx].dwFlags = 0
                if _queue(idx):
                    active.append(idx)
            for idx in list(active):
                _wait_done(hdrs[idx])
                try:
                    winmm.waveOutUnprepareHeader(
                        hwo, ctypes.byref(hdrs[idx]), ctypes.sizeof(hdrs[idx])
                    )
                except Exception:
                    pass
        except Exception:
            log.exception("LiveListenPlayer._run")
        finally:
            try:
                winmm.waveOutReset(hwo)
            except Exception:
                pass
            try:
                winmm.waveOutClose(hwo)
            except Exception:
                pass
            if reader is not None:
                try:
                    reader.close()
                except Exception:
                    pass
            with self._lock:
                self._playing = False
                self._thread = None


def preview_wav_from(
    piece: Piece, dest: str, start_sec: float, cancel=None
) -> tuple[bool, str]:
    """Wav dal secondo start_sec in poi (salto a segnalibro / ripresa precisa)."""
    if not piece.has_audio and piece.kind == "video":
        probed, _err = load_piece(piece.path)
        if probed is not None and probed.has_audio:
            piece.has_audio = True
    if not piece.has_audio:
        return False, MSG_NO_LISTEN
    ff = _ffmpeg_exe()
    if not ff:
        return False, MSG_NEED_FFMPEG
    start = max(0.0, float(start_sec or 0))
    span = piece.span() or float(piece.duration or 0)
    if span > start:
        remain = max(0.1, span - start)
    else:
        remain = _LISTEN_FULL_MAX_SEC
    take = min(remain, _LISTEN_FULL_MAX_SEC)
    ok, _err = _run(
        _seek_args(piece.path, start, take)
        + ["-vn", "-ac", "1", "-ar", "22050", dest],
        cancel,
        timeout=600,
    )
    if not ok or not os.path.isfile(dest):
        return False, MSG_LISTEN_FAIL
    heard = _wav_duration(dest) or take
    return True, f"Ascolto da {speak_position(start)}, {speak_duration(heard)}."


def preview_wav(
    piece: Piece, dest: str, cancel=None, head_only: bool = False
) -> tuple[bool, str]:
    """Wav del pezzo per l'ascolto. head_only=True: solo i primi 20 secondi."""
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
        # Volume ascolto 0–200: sul pezzo in riproduzione (bake), non sul wave di sistema
        # (nell'Add-on waveOutSetVolume abbassa anche la voce di NVDA).
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
    head = _LISTEN_HEAD_SEC
    full_max = _LISTEN_FULL_MAX_SEC
    if head_only:
        take = head if span <= 0 else min(head, span)
        phrase_head = True
    elif span > 0:
        take = min(span, full_max)
        phrase_head = span > full_max
    else:
        take = full_max
        phrase_head = False
    # Base a volume naturale; frecce su/giù cuociono il volume sul wav di play.
    ok, _err = _run(
        _seek_args(piece.path, start, take)
        + ["-vn", "-ac", "1", "-ar", "22050", dest],
        cancel,
        timeout=600,
    )
    if not ok or not os.path.isfile(dest):
        return False, MSG_LISTEN_FAIL
    heard = _wav_duration(dest) or take
    if head_only:
        return True, f"{MSG_LISTEN_HEAD} {speak_duration(heard)}."
    if phrase_head:
        return True, f"Ascolto i primi {speak_duration(heard)}."
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

    class AudioOnVideoDialog(wx.Dialog):
        """Scelte: sostituisci/mix, volumi, caselle durata indipendenti, ore/min/s."""

        def __init__(self, parent, speaker, video: Piece, audio: Piece):
            super().__init__(
                parent,
                title="Audio sul video",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._speaker = speaker or (lambda _text: None)
            self.result = None
            self._v_dur = float(video.duration or 0)
            self._a_dur = float(audio.duration or 0)
            v_name = os.path.basename(video.path)
            a_name = os.path.basename(audio.path)
            root = wx.BoxSizer(wx.VERTICAL)
            intro = wx.StaticText(
                self,
                label=(
                    f"Video: {v_name}. Audio: {a_name}. "
                    "Scegli come metterli insieme. "
                    "Spazio sulle caselle le accende o le spegne. "
                    "Se una casella «Tutto» è spenta, regola ore, minuti e secondi "
                    "con le frecce su e giù. "
                    "I volumi arrivano a 200 percento, in modo pulito. "
                    "Invio sul pulsante Crea, o un clic, scrive il file nuovo. "
                    "Esc o Annulla non scrive nulla."
                ),
            )
            intro.Wrap(560)
            root.Add(intro, 0, wx.ALL | wx.EXPAND, 10)

            root.Add(wx.StaticText(self, label="Modo"), 0, wx.LEFT | wx.RIGHT, 10)
            self.radio_replace = wx.RadioButton(
                self,
                label="&Sostituisci l'audio del video (solo l'audio scelto)",
                style=wx.RB_GROUP,
            )
            self.radio_mix = wx.RadioButton(
                self, label="&Mix: tieni l'audio del video e aggiungi l'audio scelto"
            )
            self.radio_replace.SetValue(True)
            root.Add(self.radio_replace, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
            root.Add(self.radio_mix, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

            vol_box = wx.BoxSizer(wx.HORIZONTAL)
            vol_box.Add(
                wx.StaticText(self, label="Volume &video %"),
                0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6,
            )
            self.spin_v = wx.SpinCtrl(
                self, min=_AV_VOL_MIN, max=_AV_VOL_MAX, initial=_AV_VOL_DEFAULT
            )
            try:
                self.spin_v.SetIncrement(_AV_VOL_STEP)
            except Exception:
                pass
            vol_box.Add(self.spin_v, 0, wx.RIGHT, 16)
            vol_box.Add(
                wx.StaticText(self, label="Volume &audio nuovo %"),
                0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6,
            )
            self.spin_a = wx.SpinCtrl(
                self, min=_AV_VOL_MIN, max=_AV_VOL_MAX, initial=_AV_VOL_DEFAULT
            )
            try:
                self.spin_a.SetIncrement(_AV_VOL_STEP)
            except Exception:
                pass
            vol_box.Add(self.spin_a, 0)
            root.Add(vol_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            root.Add(
                wx.StaticText(
                    self,
                    label=(
                        "In Sostituisci conta il volume dell'audio nuovo. "
                        "In Mix contano tutti e due. Da 0 a 200."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10,
            )

            root.Add(
                wx.StaticText(self, label="Durata (caselle indipendenti)"),
                0, wx.LEFT | wx.RIGHT, 10,
            )
            hint = wx.StaticText(
                self,
                label=(
                    "Spente tutte e due: risultato al più corto (dei tempi impostati). "
                    "Accesa solo Tutto il video: dura quanto il video; "
                    "se l'audio impostato è più lungo, freeze. "
                    "Accesa solo Tutto l'audio: dura quanto l'audio; "
                    "se il video impostato è più lungo, il video continua. "
                    "Accese tutte e due: restano tutti e due (freeze o silenzio se serve). "
                    "Casella spenta: scegli tu dove fermare quel pezzo."
                ),
            )
            hint.Wrap(560)
            root.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

            # Predefinito: come 2.0.6 = più corto (entrambe spente).
            # Ordine Tab: casella video → campi video → casella audio → campi audio.
            vh, vm, vs = _hms_from_seconds(self._v_dur if self._v_dur > 0 else 0)
            ah, am, as_ = _hms_from_seconds(self._a_dur if self._a_dur > 0 else 0)
            self.chk_full_video = wx.CheckBox(self, label="Tutto il &video")
            self.chk_full_video.SetValue(False)
            root.Add(self.chk_full_video, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
            root.Add(
                wx.StaticText(
                    self,
                    label="Durata video da usare (se «Tutto il video» è spenta)",
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 6,
            )
            self.spin_vh, self.spin_vm, self.spin_vs, row_v = self._make_hms_row(
                vh, vm, vs
            )
            root.Add(row_v, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

            self.chk_full_audio = wx.CheckBox(self, label="Tutto l'a&udio")
            self.chk_full_audio.SetValue(False)
            root.Add(self.chk_full_audio, 0, wx.LEFT | wx.RIGHT | wx.TOP, 4)
            root.Add(
                wx.StaticText(
                    self,
                    label="Durata audio da usare (se «Tutto l'audio» è spenta)",
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 6,
            )
            self.spin_ah, self.spin_am, self.spin_as, row_a = self._make_hms_row(
                ah, am, as_
            )
            root.Add(row_a, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

            row = wx.BoxSizer(wx.HORIZONTAL)
            btn_ok = wx.Button(self, wx.ID_OK, "&Crea")
            btn_cancel = wx.Button(self, wx.ID_CANCEL, "Annulla")
            btn_ok.SetDefault()
            row.Add(btn_ok, 0, wx.RIGHT, 8)
            row.Add(btn_cancel, 0)
            root.Add(row, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

            self.radio_replace.Bind(wx.EVT_RADIOBUTTON, self._on_mode)
            self.radio_mix.Bind(wx.EVT_RADIOBUTTON, self._on_mode)
            self.chk_full_video.Bind(wx.EVT_CHECKBOX, self._on_dur_toggle)
            self.chk_full_audio.Bind(wx.EVT_CHECKBOX, self._on_dur_toggle)
            self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
            self.SetSizer(root)
            self.Fit()
            self.CentreOnParent()
            self._on_mode()
            self._on_dur_toggle()
            wx.CallAfter(self._announce)

        def _make_hms_row(self, h: int, m: int, s: int):
            row = wx.BoxSizer(wx.HORIZONTAL)
            row.Add(wx.StaticText(self, label="Ore"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
            spin_h = wx.SpinCtrl(self, min=0, max=99, initial=h)
            row.Add(spin_h, 0, wx.RIGHT, 10)
            row.Add(wx.StaticText(self, label="Minuti"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
            spin_m = wx.SpinCtrl(self, min=0, max=59, initial=m)
            row.Add(spin_m, 0, wx.RIGHT, 10)
            row.Add(wx.StaticText(self, label="Secondi"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
            spin_s = wx.SpinCtrl(self, min=0, max=59, initial=s)
            row.Add(spin_s, 0)
            return spin_h, spin_m, spin_s, row

        def _announce(self):
            try:
                self._speaker(
                    "Audio sul video. Scegli sostituisci o mix, i volumi, "
                    "le caselle di durata e se serve ore minuti secondi, "
                    "poi Invio su Crea, o un clic."
                )
            except Exception:
                pass

        def _on_mode(self, _event=None):
            mix = self.radio_mix.GetValue()
            self.spin_v.Enable(mix)
            if not mix:
                self.spin_v.SetValue(_AV_VOL_DEFAULT)

        def _on_dur_toggle(self, _event=None):
            use_v = not self.chk_full_video.GetValue()
            use_a = not self.chk_full_audio.GetValue()
            for spin in (self.spin_vh, self.spin_vm, self.spin_vs):
                spin.Enable(use_v)
            for spin in (self.spin_ah, self.spin_am, self.spin_as):
                spin.Enable(use_a)
            if self.chk_full_video.GetValue() and self._v_dur > 0:
                h, m, s = _hms_from_seconds(self._v_dur)
                self.spin_vh.SetValue(h)
                self.spin_vm.SetValue(m)
                self.spin_vs.SetValue(s)
            if self.chk_full_audio.GetValue() and self._a_dur > 0:
                h, m, s = _hms_from_seconds(self._a_dur)
                self.spin_ah.SetValue(h)
                self.spin_am.SetValue(m)
                self.spin_as.SetValue(s)

        def _on_ok(self, _event):
            mode = "mix" if self.radio_mix.GetValue() else "replace"
            full_v = bool(self.chk_full_video.GetValue())
            full_a = bool(self.chk_full_audio.GetValue())
            video_cap = 0.0
            audio_cap = 0.0
            if not full_v:
                video_cap = _seconds_from_hms(
                    self.spin_vh.GetValue(),
                    self.spin_vm.GetValue(),
                    self.spin_vs.GetValue(),
                )
                if video_cap < 0.2:
                    self._speaker(
                        "La durata video è troppo corta. "
                        "Regola ore, minuti e secondi, oppure accendi Tutto il video."
                    )
                    return
            if not full_a:
                audio_cap = _seconds_from_hms(
                    self.spin_ah.GetValue(),
                    self.spin_am.GetValue(),
                    self.spin_as.GetValue(),
                )
                if audio_cap < 0.2:
                    self._speaker(
                        "La durata audio è troppo corta. "
                        "Regola ore, minuti e secondi, oppure accendi Tutto l'audio."
                    )
                    return
            # Durate effettive (dopo tetti) per capire se il video deve continuare
            # o se l'immagine deve restare ferma oltre l'audio.
            v_use = float(self._v_dur or 0) if full_v else float(video_cap)
            a_use = float(self._a_dur or 0) if full_a else float(audio_cap)
            if self._v_dur > 0.1 and v_use > self._v_dur:
                v_use = float(self._v_dur)
            if self._a_dur > 0.1 and a_use > self._a_dur:
                a_use = float(self._a_dur)
            if full_v and full_a:
                length_mode = "both"
            elif full_v and not full_a:
                # Video intero + audio impostato più lungo: freeze oltre il video.
                if a_use > v_use + 0.2:
                    length_mode = "both"
                else:
                    length_mode = "video"
            elif full_a and not full_v:
                # Audio intero + video impostato più lungo: il video continua dopo l'audio.
                if v_use > a_use + 0.2:
                    length_mode = "both"
                else:
                    length_mode = "audio"
            else:
                # Tutte e due spente: come 2.0.6, al più corto (dei tetti impostati).
                length_mode = "shortest"
            self.result = {
                "mode": mode,
                "video_vol": _clamp_av_vol(self.spin_v.GetValue()),
                "audio_vol": _clamp_av_vol(self.spin_a.GetValue()),
                "length_mode": length_mode,
                "video_cap": video_cap,
                "audio_cap": audio_cap,
            }
            self.EndModal(wx.ID_OK)

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
            self._preview_phrase = ""
            self._preview_key = ""
            self._preview_dur = 0.0
            self._playing = False
            self._listen_busy = False
            self._listen_gen = 0
            self._listen_vol = _LISTEN_VOL_DEFAULT
            self._play_pos = 0.0
            self._play_t0 = 0.0
            self._paused_at = None
            self._player = LiveListenPlayer()
            self._listen_mem: dict = {}
            self._announce_gen = 0
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
                        "Spazio ascolta; Spazio di nuovo pausa con orario; "
                        "Spazio ancora riparte da lì. "
                        "Mentre suona o in pausa: freccia destra/sinistra avanti/indietro di 5 s, "
                        "senza interrompere l'ascolto. "
                        "Mentre suona: freccia su/giù volume fino a 200 percento, in continuo. "
                        "In pausa o da fermo: freccia su/giù scorrono l'elenco. "
                        "Ogni file ricorda punto e volume finché la finestra resta aperta. "
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
            # Alt+S (non Alt+2: il &20 faceva leggere «Alt+2» a NVDA).
            self.chk_listen_head = wx.CheckBox(
                self, label="Ascolto &solo i primi 20 secondi"
            )
            self.chk_listen_head.SetValue(False)
            vbox.Add(self.chk_listen_head, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            self.chk_listen_head.Bind(wx.EVT_CHECKBOX, self._on_listen_head_toggle)

            row3 = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_run = wx.Button(self, label="&Esegui")
            self.btn_join = wx.Button(self, label="&Unisci")
            self.btn_audio_on_video = wx.Button(self, label="Audio sul &video")
            self.btn_close = wx.Button(self, wx.ID_CANCEL, "Chiudi")
            row3.Add(self.btn_run, 0, wx.RIGHT, 6)
            row3.Add(self.btn_join, 0, wx.RIGHT, 6)
            row3.Add(self.btn_audio_on_video, 0, wx.RIGHT, 6)
            row3.Add(self.btn_close, 0)
            vbox.Add(row3, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Fatti. Invio o doppio clic rimette il file nell'elenco di lavoro. "
                        "Spazio ascolta il risultato; Spazio di nuovo pausa con orario; "
                        "poi riparte da lì. Stesse frecce dell'elenco di lavoro. "
                        "Un clic solo seleziona la riga."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )
            self.lst_done = wx.ListBox(self, style=wx.LB_SINGLE)
            self.lst_done.SetMinSize((680, 110))
            vbox.Add(self.lst_done, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.lst_done.Bind(wx.EVT_LISTBOX, self._on_select_done)
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
            self.btn_audio_on_video.Bind(wx.EVT_BUTTON, self._on_audio_on_video)
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
            self._announce_gen += 1
            self._stop_sound()
            self._clear_listen_session()
            self._listen_mem.clear()
            # Recovery se una build precedente aveva abbassato il wave del processo.
            _restore_wave_out_volume()

        def _on_close(self, event):
            self.close_work()
            event.Skip()

        def _on_listen_head_toggle(self, _event=None):
            # Cambia la prossima preparazione; la sessione corrente si invalida.
            self._save_listen_mem()
            self._preview = ""
            self._preview_key = ""
            self._preview_phrase = ""
            self._preview_dur = 0.0
            if self._playing or self._paused_at is not None:
                self._stop_sound()
                self._clear_listen_session()
            on = bool(self.chk_listen_head.GetValue())
            self._say(MSG_LISTEN_HEAD_ON if on else MSG_LISTEN_HEAD_OFF)

        def _show_status(self, text: str):
            """Solo a schermo (Stato + barra), senza interrompere l'ascolto con la voce."""
            text = (text or "").strip()
            if not text or not self._open:
                return
            try:
                self.txt_status.SetValue(text)
            except Exception:
                pass
            try:
                self._status_bar.SetStatusText(text)
            except Exception:
                pass

        def _say(self, text: str):
            text = (text or "").strip()
            if not text:
                return
            self._show_status(text)
            try:
                self._speaker(text)
            except Exception:
                log.info("voce: %s", text)

        def _live_feedback(self, text: str):
            """A schermo subito; a voce dopo un attimo (ultimo valore se premi di fila).

            Così chi ascolta sa sempre punto e volume, come a schermo, senza
            una frase per ogni freccia se si tiene premuto.
            """
            text = (text or "").strip()
            if not text:
                return
            self._show_status(text)
            self._announce_gen += 1
            gen = self._announce_gen

            def _speak_later():
                if not self._open or gen != self._announce_gen:
                    return
                try:
                    self._speaker(text)
                except Exception:
                    log.info("voce: %s", text)

            # ~0,4 s: abbastanza corto da seguire il gesto, evita coda di annunci.
            try:
                wx.CallLater(400, _speak_later)
            except Exception:
                _speak_later()

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
            # Cambiando riga: memorizza dove eri, ferma in silenzio il pezzo precedente.
            if self._playing or self._listen_busy or self._paused_at is not None:
                key = self._piece_listen_key(self._rows[index])
                if key != self._preview_key:
                    self._save_listen_mem()
                    self._listen_gen += 1
                    self._announce_gen += 1
                    if self._listen_busy:
                        self._cancel.set()
                    self._listen_busy = False
                    self._set_busy(False)
                    self._stop_sound()
                    self._clear_listen_session()

        def _on_select_done(self, _event=None):
            if not self._done:
                return
            index = self.lst_done.GetSelection()
            if index < 0 or index >= len(self._done):
                return
            if self._playing or self._listen_busy or self._paused_at is not None:
                _label, path = self._done[index]
                piece, _err = load_piece(path)
                key = self._piece_listen_key(piece) if piece is not None else ""
                if key != self._preview_key:
                    self._save_listen_mem()
                    self._listen_gen += 1
                    self._announce_gen += 1
                    if self._listen_busy:
                        self._cancel.set()
                    self._listen_busy = False
                    self._set_busy(False)
                    self._stop_sound()
                    self._clear_listen_session()

        def _clocks(self):
            try:
                start = parse_clock(self.txt_start.GetValue())
                end = parse_clock(self.txt_end.GetValue())
            except ValueError:
                return None, None, MSG_BAD_CLOCK
            return start, end, ""

        def _on_char(self, event):
            key = event.GetKeyCode()
            if key == wx.WXK_ESCAPE and (
                self._busy
                or self._playing
                or self._listen_busy
                or self._paused_at is not None
            ):
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
            if key == wx.WXK_SPACE:
                focused = self.FindFocus()
                # Solo sugli elenchi: altrimenti Spazio attiva il pulsante (Audio sul video, ecc.).
                if focused is self.lst or focused is self.lst_done:
                    self._on_space()
                    return
            # Sinistra/destra: seek solo con sessione di ascolto (elenco non le usa).
            # Su/giù volume solo mentre suona; in pausa o fermo scorrono l'elenco.
            self._sync_listen_playing()
            if key in (wx.WXK_LEFT, wx.WXK_RIGHT):
                if self._playing or self._paused_at is not None:
                    self._seek_listen(
                        _LISTEN_SEEK_SEC if key == wx.WXK_RIGHT else -_LISTEN_SEEK_SEC
                    )
                    return
            if key in (wx.WXK_UP, wx.WXK_DOWN) and self._playing:
                self._nudge_listen_vol(
                    _LISTEN_VOL_STEP if key == wx.WXK_UP else -_LISTEN_VOL_STEP
                )
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

        def _piece_listen_key(self, piece) -> str:
            head_flag = "20" if self._listen_head_only() else "full"
            return "|".join(
                (
                    os.path.normcase(os.path.abspath(piece.path or "")),
                    str(piece.mode),
                    str(piece.start),
                    str(piece.end),
                    head_flag,
                )
            )

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
            elif name == "audio_on_video":
                self._on_audio_on_video()

        def _set_busy(self, busy: bool):
            if busy:
                # Se spegniamo il pulsante col focus, wx perde il focus e Spazio muore.
                try:
                    focused = self.FindFocus()
                    if focused is not None and focused is not self.lst and focused is not self.lst_done:
                        self.lst.SetFocus()
                except Exception:
                    pass
            self._busy = busy
            for btn in (
                self.btn_add, self.btn_folder, self.btn_up, self.btn_down, self.btn_remove,
                self.btn_listen, self.btn_keep, self.btn_drop, self.btn_another,
                self.btn_run, self.btn_join, self.btn_audio_on_video,
            ):
                btn.Enable(not busy)

        def _stop_sound(self):
            self._playing = False
            try:
                self._player.stop()
            except Exception:
                pass
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass

        def _sync_listen_playing(self) -> None:
            """Se il pezzo è finito da solo, allinea lo stato (Spazio non deve «pausare» il vuoto)."""
            if self._playing and not self._player.is_open() and self._paused_at is None:
                self._playing = False
                self._play_pos = float(self._preview_dur or self._play_pos or 0)

        def _listen_position(self) -> float:
            self._sync_listen_playing()
            if self._paused_at is not None:
                return max(0.0, float(self._paused_at))
            if self._playing or self._player.is_open():
                pos = float(self._player.position_sec())
                dur = float(self._preview_dur or 0)
                if dur > 0:
                    return max(0.0, min(dur, pos))
                return max(0.0, pos)
            return max(0.0, float(self._play_pos or 0))

        def _clear_listen_session(self):
            self._paused_at = None
            self._play_pos = 0.0
            self._play_t0 = 0.0

        def _save_listen_mem(self):
            key = self._preview_key
            if not key:
                return
            self._listen_mem[key] = {
                "pos": float(self._listen_position()),
                "vol": int(self._listen_vol),
                "paused": self._paused_at is not None or not self._playing,
            }

        def _restore_listen_mem(self, key: str) -> tuple[float, int]:
            data = self._listen_mem.get(key) or {}
            try:
                pos = float(data.get("pos") or 0)
            except (TypeError, ValueError):
                pos = 0.0
            vol = _clamp_listen_vol(data.get("vol", self._listen_vol))
            return max(0.0, pos), vol

        def _stop_listen_only(self):
            """Ferma solo l'ascolto (preparazione), senza annullare Unisci/Esegui."""
            self._listen_gen += 1
            self._announce_gen += 1
            if self._listen_busy:
                self._cancel.set()
            self._listen_busy = False
            self._set_busy(False)
            self._save_listen_mem()
            self._stop_sound()
            self._clear_listen_session()
            self._say(MSG_STOPPED)

        def _pause_listen(self):
            try:
                pos = float(self._player.pause())
            except Exception:
                pos = self._listen_position()
                self._stop_sound()
            self._playing = False
            self._paused_at = pos
            self._play_pos = pos
            self._play_t0 = 0.0
            self._save_listen_mem()
            self._say(MSG_PAUSED_AT.format(pos=speak_position(pos)))

        def _resume_listen(self):
            if not self._preview or not os.path.isfile(self._preview):
                self._clear_listen_session()
                self._say(MSG_LISTEN_FAIL)
                return
            pos = float(self._paused_at if self._paused_at is not None else self._play_pos or 0)
            phrase = MSG_RESUME_AT.format(pos=speak_position(pos))
            self._paused_at = None
            if self._player.is_open() and self._player.resume():
                self._playing = True
                self._play_pos = pos
                self._play_t0 = time.monotonic()
                self._save_listen_mem()
                self._say(phrase)
                return
            self._play_from(pos, phrase, live=False)

        def _seek_listen(self, delta: float):
            if not self._preview or not os.path.isfile(self._preview):
                self._say(MSG_LISTEN_FAIL)
                return
            dur = float(self._preview_dur or _wav_duration(self._preview) or 0)
            if dur <= 0:
                dur = float(self._player.duration_sec() or 0)
            self._preview_dur = dur
            pos = self._listen_position() + float(delta)
            if dur > 0:
                pos = max(0.0, min(dur, pos))
            else:
                pos = max(0.0, pos)
            phrase = MSG_SEEK_AT.format(pos=speak_position(pos))
            was_playing = self._playing
            if self._player.is_open():
                if not self._player.seek(pos, play=was_playing):
                    self._say(MSG_LISTEN_FAIL)
                    return
                if was_playing:
                    self._playing = True
                    self._paused_at = None
                    self._play_pos = pos
                    self._play_t0 = time.monotonic()
                else:
                    self._paused_at = pos
                    self._play_pos = pos
                    self._playing = False
                self._save_listen_mem()
                self._live_feedback(phrase)
                return
            if was_playing:
                self._play_from(pos, phrase, live=True)
                return
            self._paused_at = pos
            self._play_pos = pos
            self._save_listen_mem()
            self._live_feedback(phrase)

        def _nudge_listen_vol(self, delta: int):
            self._listen_vol = _clamp_listen_vol(self._listen_vol + int(delta))
            phrase = MSG_VOL_AT.format(vol=self._listen_vol)
            # Guadagno sui campioni in tempo reale: niente bake, NVDA indipendente.
            self._player.set_volume(self._listen_vol)
            self._save_listen_mem()
            if self._playing:
                self._live_feedback(phrase)
            else:
                self._say(phrase)

        def _play_from(self, start_sec: float, phrase: str, live: bool = False):
            """Parte (o riparte) dal secondo indicato, volume in tempo reale."""
            if not self._preview or not os.path.isfile(self._preview):
                self._say(MSG_LISTEN_FAIL)
                return
            dur = float(self._preview_dur or _wav_duration(self._preview) or 0)
            self._preview_dur = dur
            start = float(start_sec or 0)
            if dur > 0 and start >= max(0.0, dur - 0.15):
                start = 0.0
                phrase = MSG_LISTEN_END
            if not self._player.play(
                self._preview, from_sec=start, vol=self._listen_vol
            ):
                self._say(MSG_LISTEN_FAIL)
                return
            self._playing = True
            self._paused_at = None
            self._play_pos = float(start)
            self._play_t0 = time.monotonic()
            self._save_listen_mem()
            if live:
                self._live_feedback(phrase)
            else:
                self._say(phrase)

        def _on_stop(self, _event=None):
            self._listen_gen += 1
            self._announce_gen += 1
            self._listen_busy = False
            self._cancel.set()
            self._save_listen_mem()
            self._stop_sound()
            self._clear_listen_session()
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

        def _current_listen_piece(self):
            """Pezzo della riga selezionata (elenco di lavoro o Fatti)."""
            focused = self.FindFocus()
            if focused is self.lst_done:
                if not self._done:
                    return None, MSG_NO_DONE
                index = self.lst_done.GetSelection()
                if index < 0 or index >= len(self._done):
                    return None, MSG_SELECT
                _label, path = self._done[index]
                piece, err = load_piece(path)
                if piece is None:
                    return None, err or f"{os.path.basename(path)} non c'è più."
                return piece, ""
            index = self._selected()
            if index < 0:
                return None, MSG_EMPTY if not self._rows else MSG_SELECT
            return self._rows[index], ""

        def _on_space(self):
            """Spazio: ascolta, pausa con orario, ripresa, o altro pezzo."""
            if self._listen_busy:
                self._stop_listen_only()
                return
            if self._busy:
                self._say(MSG_WORKING)
                return
            piece, err = self._current_listen_piece()
            if piece is None:
                self._say(err or MSG_SELECT)
                return
            key = self._piece_listen_key(piece)
            if self._playing and key == self._preview_key:
                self._pause_listen()
                return
            if (
                self._paused_at is not None
                and key == self._preview_key
                and self._preview
                and os.path.isfile(self._preview)
            ):
                self._resume_listen()
                return
            if self._playing or self._paused_at is not None:
                # Altro file: ricorda dove eri, poi ascolta questo (dalla sua memoria).
                self._save_listen_mem()
                self._listen_gen += 1
                self._announce_gen += 1
                self._stop_sound()
                self._clear_listen_session()
            self._start_listen(piece)

        def _on_listen_done_row(self):
            """Ascolta il risultato selezionato nei Fatti, senza rimetterlo in elenco."""
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
            piece, err = load_piece(path)
            if piece is None:
                self._say(err or f"{os.path.basename(path)} non c'è più.")
                return
            self._clear_listen_session()
            self._start_listen(piece)

        def _on_listen(self):
            if self._busy:
                self._say(MSG_WORKING)
                return
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            self._clear_listen_session()
            self._start_listen(self._rows[index])

        def _listen_head_only(self) -> bool:
            try:
                return bool(self.chk_listen_head.GetValue())
            except Exception:
                return False

        def _start_listen(self, piece):
            key = self._piece_listen_key(piece)
            start_pos, start_vol = self._restore_listen_mem(key)
            self._listen_vol = start_vol
            # Stesso pezzo già preparato: riparti dalla memoria (non da zero).
            if (
                self._preview
                and key == self._preview_key
                and os.path.isfile(self._preview)
            ):
                self._cancel.clear()
                self._stop_sound()
                self._paused_at = None
                self._preview_dur = _wav_duration(self._preview)
                if start_pos > 0.15:
                    phrase = MSG_RESUME_AT.format(pos=speak_position(start_pos))
                else:
                    phrase = self._preview_phrase or "Ascolto."
                self._play_from(start_pos, phrase)
                return
            self._cancel.clear()
            self._stop_sound()
            self._clear_listen_session()
            self._listen_busy = True
            self._say(MSG_PREPARE)
            self._listen_gen += 1
            gen = self._listen_gen
            dest = os.path.join(
                tempfile.gettempdir(),
                f"rtad-ascolto-{os.getpid()}-{gen}.wav",
            )
            head_only = self._listen_head_only()

            def work():
                ok, phrase = preview_wav(
                    piece, dest, self._cancel, head_only=head_only
                )
                wx.CallAfter(self._listen_done, ok, phrase, dest, gen, key)

            threading.Thread(target=work, daemon=True).start()

        def _listen_done(self, ok, phrase, dest, gen=0, key=""):
            if not self._open:
                return
            self._listen_busy = False
            if gen != self._listen_gen:
                return
            if self._cancel.is_set() or not ok:
                self._say(MSG_STOPPED if self._cancel.is_set() else phrase)
                return
            if not dest or not os.path.isfile(dest):
                self._say(MSG_LISTEN_FAIL)
                return
            self._preview = dest
            self._preview_phrase = phrase
            self._preview_key = key
            self._preview_dur = _wav_duration(dest)
            start_pos, start_vol = self._restore_listen_mem(key)
            self._listen_vol = start_vol
            if start_pos > 0.15:
                phrase = MSG_RESUME_AT.format(pos=speak_position(start_pos))
            self._play_from(start_pos, phrase)

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

        def _on_audio_on_video(self, _event=None):
            if self._busy:
                self._say(MSG_WORKING)
                return
            video, audio, err = _pick_av_pair(self._rows)
            if err or video is None or audio is None:
                self._say(err or MSG_NEED_AV_PAIR)
                return
            if not _ffmpeg_exe():
                self._say(MSG_NEED_FFMPEG)
                return
            if not _media_file_ok(video.path) or not _media_file_ok(audio.path):
                empty = []
                if not _media_file_ok(video.path):
                    empty.append(os.path.basename(video.path))
                if not _media_file_ok(audio.path):
                    empty.append(os.path.basename(audio.path))
                names = " e ".join(empty) if empty else "un file"
                self._say(
                    f"«{names}» è vuoto (0 byte) o non si apre. "
                    "Scegli un audio e un video con contenuto, poi riprova. "
                    "Il file di partenza resta com'è."
                )
                return
            # Ferma l'ascolto: Spazio sui pulsanti non deve riprendere il pezzo.
            self._announce_gen += 1
            self._save_listen_mem()
            self._stop_sound()
            self._clear_listen_session()
            choices = AudioOnVideoDialog(self, self._speaker, video, audio)
            modal = choices.ShowModal()
            opts = choices.result
            choices.Destroy()
            if modal != wx.ID_OK or not opts:
                self._say(MSG_AV_CANCEL)
                return
            self._cancel.clear()
            self._stop_sound()
            self._clear_listen_session()
            self._set_busy(True)
            self._say(MSG_WORKING)
            v_piece = clone_piece(video)
            a_piece = clone_piece(audio)
            mode = opts.get("mode", "replace")
            video_vol = opts.get("video_vol", _AV_VOL_DEFAULT)
            audio_vol = opts.get("audio_vol", _AV_VOL_DEFAULT)
            length_mode = opts.get("length_mode", "shortest")
            video_cap = float(opts.get("video_cap") or 0)
            audio_cap = float(opts.get("audio_cap") or 0)

            def work():
                made = []
                ok, phrase = build_audio_on_video(
                    v_piece,
                    a_piece,
                    self._cancel,
                    made,
                    mode=mode,
                    video_vol=video_vol,
                    audio_vol=audio_vol,
                    length_mode=length_mode,
                    video_cap=video_cap,
                    audio_cap=audio_cap,
                )
                path = made[0] if made else ""
                # label vuota: _run_done usa phrase (già con duree video/audio + risultato).
                wx.CallAfter(self._run_done, ok, phrase, path, "")

            threading.Thread(target=work, daemon=True).start()

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
            if ok and path and os.path.isfile(path):
                if label:
                    self._done.append((label, path))
                    self._refresh_done()
                    text = label if label.endswith(".") else f"{label}."
                    self._say(f"Creato {text} Nella stessa cartella.")
                    return
                if phrase:
                    # Audio sul video: riepilogo già completo (duree + risultato).
                    line = phrase
                    for cut in (
                        " Nella stessa cartella.",
                        " Il file di partenza resta com'è.",
                    ):
                        line = line.replace(cut, "")
                    self._done.append((line.strip().rstrip("."), path))
                    self._refresh_done()
                    self._say(phrase)
                    return
            self._say(phrase)

    globals()["ClipDialog"] = ClipDialog


_install_dialog()
