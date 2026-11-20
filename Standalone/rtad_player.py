# -*- coding: utf-8 -*-
"""Lettore audio/video interno RTAD (2.0.8).

Riusa LiveListenPlayer e la preparazione wav di Taglia e unisci.
Segnalibri di posizione (media_marks.json), distinti da Ctrl+D e da Ctrl+B.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
import uuid
from datetime import datetime

log = logging.getLogger("rtad.player")

_STORE_NAME = "media_marks.json"
_shared = False

MSG_NEED_FILE = (
    "Serve un audio o un video. "
    "Trascina il file qui col mouse, oppure in Esplora Control+C "
    "e qui Control+Alt+V (stessa cosa del trascinamento), "
    "oppure Invio su Incolla, o un clic. "
    "Oppure Invio su Sfoglia, o un clic."
)
MSG_DROP_BAD = (
    "Trascinato un file che non è audio o video. "
    "Trascina un audio o un video, oppure usa Control+Alt+V."
)
MSG_NEED_FFMPEG = "Per questo formato serve ffmpeg."
MSG_NO_AUDIO = "Questo file non ha una traccia audio da ascoltare."
MSG_LISTEN_FAIL = "Non riesco a preparare l'ascolto."
MSG_ALREADY_IDLE = "La riproduzione è già ferma o in pausa."
MSG_BROWSE = "Apro la finestra di Windows per scegliere l'audio o il video."
MSG_BROWSE_FAIL = "Non sono riuscito ad aprire la finestra di scelta file."
MSG_CLIP_EMPTY = (
    "Negli Appunti non c'è un file audio o video. "
    "In Esplora seleziona il file e premi Control+C, poi qui Control+Alt+V."
)
MSG_PAUSED_AT = "Fermato a {pos}."
MSG_RESUME_AT = "Riparto da {pos}."
MSG_STOPPED_MARK = "Fermo a {pos}. Segnalibro salvato."
MSG_PLAYING = "In riproduzione."
MSG_MARK_RENAMED = "Segnalibro rinominato."
MSG_MARK_REMOVED = "Segnalibro eliminato."
MSG_NO_MARKS = "Nessun segnalibro per questo file."
MSG_RESUME_ASK = (
    "Ti eri fermato a {pos}. "
    "Invio su Riprendi da lì, o un clic, continua da quel punto. "
    "Invio su Dall'inizio, o un clic, riparte da zero."
)
MSG_RESUME_ASK_NAMED = (
    "Ti eri fermato a {pos} ({name}). "
    "Invio su Riprendi da lì, o un clic, continua da quel punto. "
    "Invio su Dall'inizio, o un clic, riparte da zero."
)
HINT = (
    "Per tutti: chi vede trascina il file in questa finestra col mouse; "
    "chi usa la tastiera, in Esplora Control+C e qui Control+Alt+V "
    "(stessa cosa del trascinamento), oppure Invio su Incolla, o un clic. "
    "Invio su Sfoglia, o un clic, apre la finestra di Windows. "
    "Spazio: pausa o ripresa. "
    "Invio o clic su Pausa: mentre suona resta Pausa; in pausa diventa Riprendi. "
    "Invio o clic su Ferma: ferma e salva un segnalibro a quell'orario. "
    "Se è già fermo o in pausa, Ferma lo dice a voce e a schermo. "
    "Frecce destra e sinistra: avanti e indietro di 5 secondi. "
    "Frecce su e giù: volume fino a 200 percento. "
    "Nell'elenco segnalibri: Invio o doppio clic va a quel punto; "
    "un clic solo seleziona la riga. "
    "Ogni avviso sta a voce e a schermo."
)

_MEDIA_EXTS = {
    ".mp3", ".m4a", ".m4b", ".aac", ".flac", ".ogg", ".opus", ".wav", ".wma",
    ".aif", ".aiff", ".mka",
    ".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv",
    ".mts", ".m2ts", ".mpg", ".mpeg", ".3gp",
}

_WILDCARD = (
    "Audio e video|"
    "*.mp3;*.m4a;*.m4b;*.aac;*.flac;*.ogg;*.opus;*.wav;*.wma;*.aif;*.aiff;*.mka;"
    "*.mp4;*.m4v;*.mkv;*.avi;*.mov;*.wmv;*.webm;*.flv;*.mts;*.m2ts;*.mpg;*.mpeg;*.3gp|"
    "Tutti i file|*.*"
)

_SEEK_STEP = 5.0
_VOL_STEP = 5
_VOL_DEFAULT = 100


def store_path(config_dir: str) -> str:
    if _shared:
        root = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "RTAD")
        os.makedirs(root, exist_ok=True)
        return os.path.join(root, _STORE_NAME)
    return os.path.join(config_dir or "", _STORE_NAME)


def enable_shared(local_dir: str) -> None:
    """I segnalibri media vanno nella cartella comune RTAD."""
    global _shared
    _shared = True
    local = os.path.join(local_dir or "", _STORE_NAME)
    root = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "RTAD")
    os.makedirs(root, exist_ok=True)
    shared = os.path.join(root, _STORE_NAME)
    if os.path.isfile(local) and not os.path.isfile(shared):
        try:
            import shutil

            shutil.copy2(local, shared)
        except Exception:
            log.exception("media_marks copy to shared")


def _file_key(path: str) -> str:
    try:
        return os.path.normcase(os.path.abspath(path))
    except Exception:
        return (path or "").lower()


def _load_store(config_dir: str) -> dict:
    path = store_path(config_dir)
    if not os.path.isfile(path):
        return {"marks": {}}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("marks"), dict):
            return data
    except Exception:
        log.exception("media_marks load")
    return {"marks": {}}


def _save_store(config_dir: str, data: dict) -> None:
    path = store_path(config_dir)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def format_clock(seconds: float) -> str:
    """Orario hh:mm:ss o mm:ss per etichette e nomi."""
    total = max(0, int(round(float(seconds or 0))))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def list_marks(config_dir: str, media_path: str) -> list[dict]:
    data = _load_store(config_dir)
    group = data["marks"].get(_file_key(media_path)) or {}
    items = list(group.get("items") or [])
    items.sort(key=lambda it: float(it.get("sec") or 0))
    return items


def last_mark(config_dir: str, media_path: str) -> dict | None:
    data = _load_store(config_dir)
    group = data["marks"].get(_file_key(media_path)) or {}
    resume_id = str(group.get("resume_id") or "")
    items = list(group.get("items") or [])
    if resume_id:
        for item in items:
            if str(item.get("id") or "") == resume_id:
                return item
    if not items:
        return None
    items.sort(key=lambda it: str(it.get("ts") or ""), reverse=True)
    return items[0]


def add_mark(
    config_dir: str,
    media_path: str,
    sec: float,
    name: str = "",
) -> dict:
    data = _load_store(config_dir)
    key = _file_key(media_path)
    group = data["marks"].setdefault(key, {"resume_id": "", "items": []})
    items = list(group.get("items") or [])
    clock = format_clock(sec)
    label = (name or "").strip() or clock
    item = {
        "id": uuid.uuid4().hex[:12],
        "sec": float(max(0.0, sec)),
        "name": label,
        "auto_name": not bool((name or "").strip()),
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    items.append(item)
    group["items"] = items
    group["resume_id"] = item["id"]
    data["marks"][key] = group
    _save_store(config_dir, data)
    return item


def rename_mark(config_dir: str, media_path: str, mark_id: str, name: str) -> bool:
    data = _load_store(config_dir)
    key = _file_key(media_path)
    group = data["marks"].get(key) or {}
    items = list(group.get("items") or [])
    found = False
    for item in items:
        if str(item.get("id") or "") == str(mark_id):
            item["name"] = (name or "").strip() or format_clock(float(item.get("sec") or 0))
            item["auto_name"] = False
            found = True
            break
    if not found:
        return False
    group["items"] = items
    data["marks"][key] = group
    _save_store(config_dir, data)
    return True


def delete_mark(config_dir: str, media_path: str, mark_id: str) -> bool:
    data = _load_store(config_dir)
    key = _file_key(media_path)
    group = data["marks"].get(key) or {}
    items = [it for it in (group.get("items") or []) if str(it.get("id") or "") != str(mark_id)]
    if len(items) == len(group.get("items") or []):
        return False
    group["items"] = items
    if str(group.get("resume_id") or "") == str(mark_id):
        group["resume_id"] = str(items[-1]["id"]) if items else ""
    data["marks"][key] = group
    _save_store(config_dir, data)
    return True


def _build_player():
    import wx

    import rtad_clip as clip

    class _PlayerDialog(wx.Dialog):
        def __init__(self, parent, speaker, path, config_dir, clipboard_paths=None):
            super().__init__(
                parent,
                title="Riproduttore audio/video",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._speaker = speaker or (lambda _t: None)
            self._config_dir = config_dir or ""
            self._clipboard_paths = clipboard_paths
            self._path = path or ""
            self._piece = None
            self._preview = ""
            self._preview_dur = 0.0
            self._playing = False
            self._paused = False
            self._listen_busy = False
            self._listen_vol = _VOL_DEFAULT
            self._play_pos = 0.0
            self._player = clip.LiveListenPlayer()
            self._cancel = threading.Event()
            self._open = True
            self._marks: list[dict] = []

            root = wx.BoxSizer(wx.VERTICAL)
            intro = wx.StaticText(self, label=HINT)
            intro.Wrap(700)
            root.Add(intro, 0, wx.ALL | wx.EXPAND, 10)

            self.lbl_file = wx.StaticText(self, label="Nessun file.")
            self.lbl_file.Wrap(700)
            root.Add(self.lbl_file, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 10)

            path_row = wx.BoxSizer(wx.HORIZONTAL)
            path_row.Add(
                wx.StaticText(self, label="Percorso:"),
                0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6,
            )
            self.txt_path = wx.TextCtrl(self, value=self._path or "")
            self.txt_path.SetName("Percorso")
            path_row.Add(self.txt_path, 1, wx.EXPAND | wx.RIGHT, 6)
            self.btn_paste = wx.Button(self, label="&Incolla…")
            self.btn_browse = wx.Button(self, label="&Sfoglia…")
            self.btn_open = wx.Button(self, label="A&pri")
            path_row.Add(self.btn_paste, 0, wx.RIGHT, 6)
            path_row.Add(self.btn_browse, 0, wx.RIGHT, 6)
            path_row.Add(self.btn_open, 0)
            root.Add(path_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

            self.lbl_status = wx.StaticText(self, label="Fermo.")
            root.Add(self.lbl_status, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 10)

            row = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_pause = wx.Button(self, label="&Pausa")
            self.btn_stop = wx.Button(self, label="&Ferma")
            for btn in (self.btn_pause, self.btn_stop):
                row.Add(btn, 0, wx.RIGHT, 8)
            root.Add(row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

            root.Add(
                wx.StaticText(self, label="Segnalibri di questo file"),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 10,
            )
            self.lst_marks = wx.ListBox(self, style=wx.LB_SINGLE)
            self.lst_marks.SetMinSize((680, 140))
            root.Add(self.lst_marks, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

            row_m = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_rename = wx.Button(self, label="&Rinomina…")
            self.btn_delete = wx.Button(self, label="&Elimina segnalibro")
            self.btn_close = wx.Button(self, wx.ID_CANCEL, "Chiudi")
            for btn in (self.btn_rename, self.btn_delete, self.btn_close):
                row_m.Add(btn, 0, wx.RIGHT, 8)
            root.Add(row_m, 0, wx.ALL, 10)

            self.SetSizerAndFit(root)
            self.SetMinSize((720, 420))

            self.btn_paste.Bind(wx.EVT_BUTTON, lambda e: self._paste_from_clipboard())
            self.btn_open.Bind(wx.EVT_BUTTON, lambda e: self._open_from_path())
            self.btn_browse.Bind(wx.EVT_BUTTON, lambda e: self._browse_file())
            self.txt_path.Bind(wx.EVT_TEXT_ENTER, lambda e: self._open_from_path())
            self.btn_pause.Bind(wx.EVT_BUTTON, lambda e: self._on_pause_toggle())
            self.btn_stop.Bind(wx.EVT_BUTTON, lambda e: self._on_stop())
            self.btn_rename.Bind(wx.EVT_BUTTON, lambda e: self._on_rename())
            self.btn_delete.Bind(wx.EVT_BUTTON, lambda e: self._on_delete())
            self.lst_marks.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._goto_selected_mark())
            self.Bind(wx.EVT_CHAR_HOOK, self._on_char)
            self.Bind(wx.EVT_CLOSE, self._on_close)
            # Ctrl+Alt+V = stesso effetto del trascinamento (per tutti).
            accel = wx.AcceleratorTable(
                [
                    (
                        wx.ACCEL_CTRL | wx.ACCEL_ALT,
                        ord("V"),
                        self.btn_paste.GetId(),
                    ),
                ]
            )
            self.SetAcceleratorTable(accel)
            self._enable_file_drop()

            if self._path and os.path.isfile(self._path):
                wx.CallAfter(self._load_path, self._path, ask_resume=True)
            else:
                self._refresh_marks()
                wx.CallAfter(self.btn_paste.SetFocus)

        def _say(self, text: str):
            self.lbl_status.SetLabel(text)
            try:
                self._speaker(text)
            except Exception:
                pass

        def _on_char(self, event):
            key = event.GetKeyCode()
            focused = None
            try:
                focused = wx.Window.FindFocus()
            except Exception:
                focused = None
            # Come Taglia e unisci: Spazio sui pulsanti li attiva; non rubarlo.
            if isinstance(
                focused, (wx.TextCtrl, wx.Button, wx.CheckBox, wx.RadioButton, wx.Choice)
            ):
                event.Skip()
                return
            if (
                event.ControlDown()
                and event.AltDown()
                and not event.ShiftDown()
                and key in (ord("V"), ord("v"))
            ):
                self._paste_from_clipboard()
                return
            if key == wx.WXK_SPACE:
                self._on_pause_toggle()
                return
            if key == wx.WXK_RIGHT:
                self._seek(+_SEEK_STEP)
                return
            if key == wx.WXK_LEFT:
                self._seek(-_SEEK_STEP)
                return
            if key == wx.WXK_UP:
                self._nudge_vol(+_VOL_STEP)
                return
            if key == wx.WXK_DOWN:
                self._nudge_vol(-_VOL_STEP)
                return
            event.Skip()

        def _clipboard_media_paths(self) -> list:
            paths = []
            if callable(self._clipboard_paths):
                try:
                    paths = list(self._clipboard_paths() or [])
                except Exception:
                    log.exception("clipboard_paths")
                    paths = []
            else:
                paths = _paths_from_clipboard_fallback()
            out = []
            for path in paths:
                path = (path or "").strip().strip('"')
                if not path or not os.path.isfile(path):
                    continue
                ext = os.path.splitext(path)[1].lower()
                if ext in _MEDIA_EXTS:
                    out.append(os.path.normpath(path))
            return out

        def _enable_file_drop(self):
            """Trascinamento col mouse = stesso effetto di Control+Alt+V."""

            class _Drop(wx.FileDropTarget):
                def __init__(self, owner):
                    super().__init__()
                    self._owner = owner

                def OnDropFiles(self, x, y, filenames):
                    try:
                        self._owner._apply_dropped_paths(filenames or [])
                    except Exception:
                        log.exception("OnDropFiles player")
                    return True

            targets = [self, self.txt_path, self.lst_marks, self.lbl_file, self.lbl_status]
            seen = set()
            for win in targets:
                if win is None:
                    continue
                wid = id(win)
                if wid in seen:
                    continue
                seen.add(wid)
                try:
                    win.SetDropTarget(_Drop(self))
                except Exception:
                    pass

        def _first_media_path(self, filenames) -> str:
            for path in filenames or []:
                path = (path or "").strip().strip('"')
                if not path:
                    continue
                try:
                    path = os.path.normpath(path)
                except Exception:
                    continue
                if not os.path.isfile(path):
                    continue
                ext = os.path.splitext(path)[1].lower()
                if ext in _MEDIA_EXTS:
                    return path
            return ""

        def _apply_dropped_paths(self, filenames):
            path = self._first_media_path(filenames)
            if not path:
                self._say(MSG_DROP_BAD)
                return
            try:
                self.txt_path.SetValue(path)
            except Exception:
                pass
            self._say(f"Trascinato: {os.path.basename(path)}.")
            self._load_path(path, ask_resume=True)

        def _paste_from_clipboard(self):
            paths = self._clipboard_media_paths()
            if not paths:
                self._say(MSG_CLIP_EMPTY)
                return
            path = paths[0]
            try:
                self.txt_path.SetValue(path)
            except Exception:
                pass
            self._say(
                f"Appunti: {os.path.basename(path)}. "
                "Come se l'avessi trascinato qui."
            )
            self._load_path(path, ask_resume=True)

        def _typed_path(self) -> str:
            try:
                return self.txt_path.GetValue().strip().strip('"')
            except Exception:
                return ""

        def _open_from_path(self):
            path = self._typed_path()
            if not path:
                self._say(MSG_NEED_FILE)
                try:
                    self.txt_path.SetFocus()
                except Exception:
                    pass
                return
            if not os.path.isfile(path):
                self._say("Quel percorso non è un file. Controlla e riprova.")
                try:
                    self.txt_path.SetFocus()
                except Exception:
                    pass
                return
            self._load_path(path, ask_resume=True)

        def _windows_file_dialog_class(self):
            """Sempre la FileDialog di Windows (non quella RTAD), come chiesto per il lettore."""
            try:
                import rtad_picker as picker

                native = getattr(picker, "_windows_file", None)
                if native is not None:
                    return native
            except Exception:
                log.exception("rtad_picker windows FileDialog")
            return wx.FileDialog

        def _browse_file(self):
            self._say(MSG_BROWSE)
            FileDlg = self._windows_file_dialog_class()
            try:
                dlg = FileDlg(
                    self,
                    message="Scegli audio o video",
                    wildcard=_WILDCARD,
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                )
            except TypeError:
                # Firma wx classica senza nomi.
                dlg = FileDlg(
                    self,
                    "Scegli audio o video",
                    "",
                    "",
                    _WILDCARD,
                    wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                )
            except Exception:
                log.exception("FileDialog create")
                self._say(MSG_BROWSE_FAIL)
                return
            path = ""
            try:
                try:
                    dlg.CentreOnParent()
                except Exception:
                    pass
                try:
                    dlg.Raise()
                except Exception:
                    pass
                if dlg.ShowModal() != wx.ID_OK:
                    return
                path = dlg.GetPath() or ""
            except Exception:
                log.exception("FileDialog ShowModal")
                self._say(MSG_BROWSE_FAIL)
                return
            finally:
                try:
                    dlg.Destroy()
                except Exception:
                    pass
            if not path:
                self._say(MSG_NEED_FILE)
                return
            try:
                self.txt_path.SetValue(path)
            except Exception:
                pass
            self._load_path(path, ask_resume=True)

        def _load_path(self, path: str, ask_resume: bool = False):
            self._halt(clear_preview=True)
            piece, err = clip.load_piece(path)
            if piece is None:
                self._say(err or MSG_NEED_FILE)
                return
            self._path = path
            self._piece = piece
            try:
                self.txt_path.SetValue(path)
            except Exception:
                pass
            self.lbl_file.SetLabel(os.path.basename(path))
            self._refresh_marks()
            start = 0.0
            if ask_resume:
                mark = last_mark(self._config_dir, path)
                if mark and float(mark.get("sec") or 0) > 0.5:
                    start = self._ask_resume(mark)
            self._prepare_and_play(start)

        def _ask_resume(self, mark: dict) -> float:
            import wx

            sec = float(mark.get("sec") or 0)
            pos = clip.speak_position(sec)
            name = str(mark.get("name") or "")
            auto = bool(mark.get("auto_name"))
            if name and not auto and name != format_clock(sec):
                msg = MSG_RESUME_ASK_NAMED.format(pos=pos, name=name)
            else:
                msg = MSG_RESUME_ASK.format(pos=pos)
            dlg = wx.MessageDialog(
                self,
                msg,
                "Riprendere la riproduzione?",
                wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_QUESTION,
            )
            dlg.SetYesNoLabels("Riprendi da lì", "Dall'inizio")
            self._say(msg)
            choice = dlg.ShowModal()
            dlg.Destroy()
            if choice == wx.ID_YES:
                return sec
            return 0.0

        def _prepare_and_play(self, start_sec: float):
            if self._piece is None:
                return
            if self._listen_busy:
                return
            self._listen_busy = True
            self._say("Preparazione ascolto…")
            dest = os.path.join(
                tempfile.gettempdir(),
                f"rtad_player_{os.getpid()}_{int(time.time() * 1000)}.wav",
            )

            def work():
                ok, phrase = clip.preview_wav(
                    self._piece, dest, cancel=self._cancel, head_only=False
                )
                wx.CallAfter(self._after_prepare, ok, phrase, dest, start_sec)

            threading.Thread(target=work, daemon=True).start()

        def _after_prepare(self, ok, phrase, dest, start_sec):
            self._listen_busy = False
            if not self._open:
                try:
                    if os.path.isfile(dest):
                        os.remove(dest)
                except Exception:
                    pass
                return
            if not ok or not os.path.isfile(dest):
                self._say(phrase or MSG_LISTEN_FAIL)
                return
            if self._preview and self._preview != dest:
                try:
                    if os.path.isfile(self._preview):
                        os.remove(self._preview)
                except Exception:
                    pass
            self._preview = dest
            self._preview_dur = clip._wav_duration(dest)
            self._player.set_volume(self._listen_vol)
            start = max(0.0, min(float(start_sec or 0), max(0.0, self._preview_dur - 0.05)))
            if not self._player.play(dest, from_sec=start, vol=self._listen_vol):
                self._say(MSG_LISTEN_FAIL)
                return
            self._playing = True
            self._paused = False
            self._play_pos = start
            self.btn_pause.SetLabel("&Pausa")
            if start > 0.15:
                self._say(MSG_RESUME_AT.format(pos=clip.speak_position(start)))
            else:
                self._say(MSG_PLAYING if not phrase else f"{phrase} {MSG_PLAYING}")

        def _position(self) -> float:
            if self._playing and self._player.is_playing():
                return self._player.position_sec()
            if self._paused:
                return float(self._play_pos or 0)
            return float(self._play_pos or 0)

        def _on_pause_toggle(self):
            if self._listen_busy:
                return
            if self._playing and self._player.is_playing():
                pos = self._player.pause()
                self._play_pos = pos
                self._playing = False
                self._paused = True
                self.btn_pause.SetLabel("&Riprendi")
                self._say(MSG_PAUSED_AT.format(pos=clip.speak_position(pos)))
                return
            if self._paused and self._preview and os.path.isfile(self._preview):
                if self._player.resume():
                    self._playing = True
                    self._paused = False
                    self.btn_pause.SetLabel("&Pausa")
                    self._say(
                        MSG_RESUME_AT.format(pos=clip.speak_position(self._play_pos))
                    )
                return
            if self._path and self._piece is not None and self._preview:
                self._prepare_and_play(0.0)
                return
            if self._path and os.path.isfile(self._path):
                self._load_path(self._path, ask_resume=False)
                return
            self._say(MSG_NEED_FILE)

        def _on_stop(self):
            if self._listen_busy:
                return
            idle = (not self._playing) and (not self._paused)
            if idle and not self._player.is_playing():
                self._say(MSG_ALREADY_IDLE)
                return
            pos = self._position()
            self._player.stop()
            self._playing = False
            self._paused = False
            self._play_pos = 0.0
            self.btn_pause.SetLabel("&Pausa")
            if self._path and pos > 0.2:
                item = add_mark(self._config_dir, self._path, pos)
                self._refresh_marks()
                self._say(
                    MSG_STOPPED_MARK.format(pos=clip.speak_position(float(item["sec"])))
                )
            else:
                self._say("Fermo.")

        def _seek(self, delta: float):
            if not self._preview or not os.path.isfile(self._preview):
                return
            pos = self._position() + float(delta)
            pos = max(0.0, min(pos, max(0.0, self._preview_dur - 0.05)))
            want_play = bool(self._playing and self._player.is_playing())
            if not self._player.seek(pos, play=want_play):
                return
            self._play_pos = pos
            if want_play:
                self._playing = True
                self._paused = False
                self.btn_pause.SetLabel("&Pausa")
            self._say(clip.speak_position(pos))

        def _nudge_vol(self, delta: int):
            self._listen_vol = clip._clamp_listen_vol(self._listen_vol + int(delta))
            self._player.set_volume(self._listen_vol)
            self._say(f"Volume {self._listen_vol} percento.")

        def _refresh_marks(self):
            self._marks = list_marks(self._config_dir, self._path) if self._path else []
            self.lst_marks.Clear()
            if not self._marks:
                self.lst_marks.Append(MSG_NO_MARKS)
                return
            for item in self._marks:
                sec = float(item.get("sec") or 0)
                name = str(item.get("name") or format_clock(sec))
                self.lst_marks.Append(f"{format_clock(sec)} — {name}")

        def _selected_mark(self) -> dict | None:
            if not self._marks:
                return None
            idx = self.lst_marks.GetSelection()
            if idx < 0 or idx >= len(self._marks):
                return None
            return self._marks[idx]

        def _goto_selected_mark(self):
            item = self._selected_mark()
            if item is None:
                self._say(MSG_NO_MARKS)
                return
            sec = float(item.get("sec") or 0)
            if self._preview and os.path.isfile(self._preview):
                if self._player.seek(sec, play=True):
                    self._playing = True
                    self._paused = False
                    self._play_pos = sec
                    self.btn_pause.SetLabel("&Pausa")
                    self._say(MSG_RESUME_AT.format(pos=clip.speak_position(sec)))
                return
            self._prepare_and_play(sec)

        def _on_rename(self):
            item = self._selected_mark()
            if item is None:
                self._say(MSG_NO_MARKS)
                return
            with wx.TextEntryDialog(
                self,
                "Nuovo nome del segnalibro",
                "Rinomina segnalibro",
                str(item.get("name") or ""),
            ) as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                name = dlg.GetValue().strip()
            if rename_mark(self._config_dir, self._path, item["id"], name):
                self._refresh_marks()
                self._say(MSG_MARK_RENAMED)
            else:
                self._say(MSG_NO_MARKS)

        def _on_delete(self):
            item = self._selected_mark()
            if item is None:
                self._say(MSG_NO_MARKS)
                return
            if delete_mark(self._config_dir, self._path, item["id"]):
                self._refresh_marks()
                self._say(MSG_MARK_REMOVED)
            else:
                self._say(MSG_NO_MARKS)

        def _halt(self, clear_preview: bool = False):
            try:
                self._player.stop()
            except Exception:
                pass
            self._playing = False
            self._paused = False
            self._play_pos = 0.0
            self.btn_pause.SetLabel("&Pausa")
            if clear_preview and self._preview:
                try:
                    if os.path.isfile(self._preview):
                        os.remove(self._preview)
                except Exception:
                    pass
                self._preview = ""
                self._preview_dur = 0.0

        def close_work(self):
            self._open = False
            self._cancel.set()
            self._halt(clear_preview=True)

        def _on_close(self, event):
            self.close_work()
            event.Skip()

    return _PlayerDialog


def _paths_from_clipboard_fallback() -> list:
    """Se non arriva la funzione della finestra principale, legge gli Appunti qui."""
    import wx

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
                        if p and os.path.isfile(p):
                            found.append(os.path.normpath(p))
        except Exception:
            pass
        if found:
            return found
        try:
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT)):
                data = wx.TextDataObject()
                if wx.TheClipboard.GetData(data):
                    raw = (data.GetText() or "").strip().strip('"')
                    if raw and os.path.isfile(raw):
                        found.append(os.path.normpath(raw))
        except Exception:
            pass
    finally:
        try:
            wx.TheClipboard.Close()
        except Exception:
            pass
    return found


def open_dialog(
    parent,
    speaker,
    path: str = "",
    config_dir: str = "",
    clipboard_paths=None,
):
    cls = _build_player()
    dialog = cls(
        parent,
        speaker,
        path or "",
        config_dir or "",
        clipboard_paths=clipboard_paths,
    )
    dialog.ShowModal()
    dialog.close_work()
    dialog.Destroy()
