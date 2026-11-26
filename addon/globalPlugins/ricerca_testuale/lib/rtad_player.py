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
MSG_ALREADY_IDLE = "Già fermo."
MSG_ALREADY_PAUSED = "Già in pausa. Invio su Riprendi, o un clic, per ripartire."
MSG_GOTO_MARK = "Riparto dal segnalibro {n} di {total}: {label}."
MSG_BROWSE = "Apro la finestra di Windows per scegliere l'audio o il video."
MSG_BROWSE_FAIL = "Non sono riuscito ad aprire la finestra di scelta file."
MSG_CLIP_EMPTY = (
    "Negli Appunti non c'è un file audio o video. "
    "In Esplora seleziona il file e premi Control+C, poi qui Control+Alt+V."
)
MSG_PAUSED_AT = "In pausa a {pos}."
MSG_PAUSED_MARK = (
    "In pausa a {pos}. Segnalibro salvato. Il pulsante è Riprendi."
)
MSG_RESUME_AT = "Riparto da {pos}."
MSG_STOPPED_MARK = "Fermo a {pos}. Segnalibro salvato."
MSG_PLAYING = (
    "In riproduzione. Pulsante Pausa. "
    "Spazio mette in pausa; frecce destra e sinistra avanti e indietro; "
    "frecce su e giù volume."
)
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
    "Per tutti: chi vede trascina il file qui col mouse; "
    "chi usa la tastiera, in Esplora Control+C e qui Control+Alt+V "
    "(stessa cosa del trascinamento), oppure Invio su Incolla, o un clic. "
    "Invio su Sfoglia, o un clic, apre la finestra di Windows. "
    "In riproduzione il pulsante è Pausa; in pausa diventa Riprendi "
    "(Ferma resta Ferma). Il focus resta sul pulsante usato: "
    "dopo Pausa resta su Riprendi; dopo Ferma resta su Ferma. "
    "Con Tab si arriva all'elenco Segnalibri: frecce su e giù scorrono; "
    "Sull'elenco: frecce su/giù scelgono; Invio, Spazio o un clic "
    "(o Vai al segnalibro) riparte da quel punto, senza crearne di nuovi. "
    "Segnalibri nuovi solo con Pausa o Ferma, oppure dopo frecce sinistra/destra. "
    "Se Ferma è già fermo, Invio o clic dice solo Già fermo. "
    "Ripartire dopo la pausa: Invio o clic su Riprendi. "
    "Ogni avviso sta a voce e a schermo."
)


def mark_row_label(item: dict) -> str:
    """Orario sempre; se rinominato, anche il nome."""
    sec = float(item.get("sec") or 0)
    clock = format_clock(sec)
    name = str(item.get("name") or "").strip()
    auto = bool(item.get("auto_name"))
    if auto or not name or name == clock:
        return clock
    return f"{clock} — {name}"

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


def _file_bytes(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return -1


def _mark_epoch(item: dict) -> float:
    raw = str(item.get("ts") or "").strip()
    if not raw:
        return 0.0
    try:
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return 0.0


def _belongs_to_file(item: dict, mtime: float) -> bool:
    """Un segnalibro fatto prima che il file esistesse è di un altro file, stesso nome."""
    stamp = _mark_epoch(item)
    if stamp <= 0 or mtime <= 0:
        return True
    return stamp + 2.0 >= mtime


def _group_for_file(config_dir: str, media_path: str) -> dict:
    """Segnalibri di questo file. Se il file è stato sostituito, quelli vecchi non contano."""
    data = _load_store(config_dir)
    key = _file_key(media_path)
    group = dict(data["marks"].get(key) or {})
    items = list(group.get("items") or [])
    size = _file_bytes(media_path)
    if size < 0 or not items:
        return group
    stored = group.get("bytes")
    changed = False
    if stored is not None and int(stored) != size:
        items = []
        changed = True
    elif stored is None:
        try:
            mtime = os.path.getmtime(media_path)
        except OSError:
            mtime = 0.0
        kept = [it for it in items if _belongs_to_file(it, mtime)]
        if len(kept) != len(items):
            items = kept
            changed = True
    if not changed and stored is not None:
        return group
    group["items"] = items
    group["bytes"] = size
    resume = str(group.get("resume_id") or "")
    ids = {str(it.get("id") or "") for it in items}
    if resume not in ids:
        group["resume_id"] = str(items[-1]["id"]) if items else ""
    data["marks"][key] = group
    _save_store(config_dir, data)
    return group


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
    group = _group_for_file(config_dir, media_path)
    items = list(group.get("items") or [])
    items.sort(key=lambda it: float(it.get("sec") or 0))
    return items


def last_mark(config_dir: str, media_path: str) -> dict | None:
    group = _group_for_file(config_dir, media_path)
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
    _group_for_file(config_dir, media_path)
    data = _load_store(config_dir)
    key = _file_key(media_path)
    group = data["marks"].setdefault(key, {"resume_id": "", "items": []})
    size = _file_bytes(media_path)
    if size >= 0:
        group["bytes"] = size
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
            # 0 = wav del file intero (timeline dei segnalibri). >0 = pezzo tagliato (da evitare).
            self._preview_origin = 0.0
            self._playing = False
            self._paused = False
            self._sel_mark_id = ""
            self._listen_busy = False
            self._suppress_auto_mark = False
            self._listen_vol = _VOL_DEFAULT
            self._play_pos = 0.0
            self._player = clip.LiveListenPlayer()
            self._cancel = threading.Event()
            self._open = True
            self._marks: list[dict] = []
            # Ogni preparazione asincrona ha un generatore: i risultati vecchi si ignorano.
            self._play_gen = 0

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
            self.txt_path = wx.TextCtrl(
                self, value=self._path or "", style=wx.TE_PROCESS_ENTER
            )
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
            self.lst_marks = wx.ListBox(self, style=wx.LB_SINGLE | wx.LB_NEEDED_SB)
            self.lst_marks.SetName("Segnalibri")
            self.lst_marks.SetMinSize((680, 140))
            root.Add(self.lst_marks, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

            row_m = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_goto = wx.Button(self, label="&Vai al segnalibro")
            self.btn_rename = wx.Button(self, label="&Rinomina…")
            self.btn_delete = wx.Button(self, label="&Elimina segnalibro")
            self.btn_close = wx.Button(self, wx.ID_CANCEL, "Chiudi")
            for btn in (self.btn_goto, self.btn_rename, self.btn_delete, self.btn_close):
                row_m.Add(btn, 0, wx.RIGHT, 8)
            root.Add(row_m, 0, wx.ALL, 10)

            self.SetSizerAndFit(root)
            self.SetMinSize((720, 420))

            self.btn_paste.Bind(wx.EVT_BUTTON, lambda e: self._paste_from_clipboard())
            self.btn_open.Bind(wx.EVT_BUTTON, lambda e: self._open_from_path())
            self.btn_browse.Bind(wx.EVT_BUTTON, lambda e: self._browse_file())
            self.txt_path.Bind(wx.EVT_TEXT_ENTER, lambda e: self._open_from_path())
            # Pausa/Ferma da pulsante: segnalibro automatico consentito.
            self.btn_pause.Bind(wx.EVT_BUTTON, lambda e: self._on_pause_from_button())
            self.btn_stop.Bind(wx.EVT_BUTTON, lambda e: self._on_stop_from_button())
            self.btn_goto.Bind(wx.EVT_BUTTON, lambda e: self._goto_selected_mark())
            self.btn_rename.Bind(wx.EVT_BUTTON, lambda e: self._on_rename())
            self.btn_delete.Bind(wx.EVT_BUTTON, lambda e: self._on_delete())
            self.lst_marks.Bind(wx.EVT_LISTBOX, self._on_mark_select)
            self.lst_marks.Bind(wx.EVT_LISTBOX_DCLICK, self._on_mark_activate)
            # Invio/clic sull'elenco: gestiti SULLA lista (più affidabile del solo CHAR_HOOK).
            self.lst_marks.Bind(wx.EVT_KEY_DOWN, self._on_marks_key)
            self.lst_marks.Bind(wx.EVT_LEFT_UP, self._on_marks_click)
            self.Bind(wx.EVT_CHAR_HOOK, self._on_char)
            self.Bind(wx.EVT_CLOSE, self._on_close)
            # Evita che Invio attivi un pulsante "default" diverso da quello col focus.
            try:
                self.SetAffirmativeId(wx.ID_NONE)
            except Exception:
                pass
            try:
                self.SetDefaultItem(None)
            except Exception:
                pass
            # Ctrl+Alt+V: in wx l'accelerator manda EVT_MENU, non EVT_BUTTON.
            try:
                id_ref = wx.NewIdRef()
                paste_id = id_ref.GetId() if hasattr(id_ref, "GetId") else int(id_ref)
            except Exception:
                paste_id = wx.NewId()
            self._id_paste = paste_id
            self.Bind(wx.EVT_MENU, lambda e: self._paste_from_clipboard(), id=paste_id)
            try:
                accel = wx.AcceleratorTable(
                    [(wx.ACCEL_CTRL | wx.ACCEL_ALT, ord("V"), paste_id)]
                )
                self.SetAcceleratorTable(accel)
            except Exception:
                log.exception("AcceleratorTable paste")
            try:
                self._enable_file_drop()
            except Exception:
                log.exception("file drop")

            if self._path and os.path.isfile(self._path):
                wx.CallAfter(self._load_path, self._path, ask_resume=True)
            else:
                self._refresh_marks()
                wx.CallAfter(self._announce_ready)

        def _announce_ready(self):
            try:
                self.btn_paste.SetFocus()
            except Exception:
                pass
            self._say(
                "Riproduttore pronto. "
                "Trascina un audio o un video, oppure Control+Alt+V, "
                "oppure Invio su Incolla o su Sfoglia."
            )

        def _say(self, text: str):
            self.lbl_status.SetLabel(text)
            try:
                self._speaker(text)
            except Exception:
                pass

        def _on_char(self, event):
            key = event.GetKeyCode()
            # Prima di tutto: Control+Alt+V (anche con focus su pulsante o campo).
            if (
                event.ControlDown()
                and event.AltDown()
                and not event.ShiftDown()
                and key in (ord("V"), ord("v"))
            ):
                self._paste_from_clipboard()
                return
            focused = None
            try:
                focused = wx.Window.FindFocus()
            except Exception:
                focused = None
            in_text = isinstance(focused, wx.TextCtrl)
            on_marks = self._focus_is_marks(focused)
            session = bool(self._playing or self._paused)
            actively = bool(self._playing and self._player.is_playing())

            # Invio: SEMPRE sul controllo col focus (mai il default del dialogo).
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                if in_text:
                    event.Skip()
                    return
                if focused is self.btn_stop:
                    self._suppress_auto_mark = False
                    self._on_stop()
                    return
                if focused is self.btn_pause:
                    self._suppress_auto_mark = False
                    self._on_pause_toggle()
                    return
                if focused is self.btn_paste:
                    self._paste_from_clipboard()
                    return
                if focused is self.btn_browse:
                    self._browse_file()
                    return
                if focused is self.btn_open:
                    self._open_from_path()
                    return
                if focused is self.btn_goto:
                    self._goto_selected_mark()
                    return
                if focused is self.btn_rename:
                    self._on_rename()
                    return
                if focused is self.btn_delete:
                    self._on_delete()
                    return
                if focused is self.btn_close:
                    self.Close()
                    return
                if on_marks or isinstance(focused, wx.ListBox):
                    self._goto_selected_mark()
                    return
                # Non Skip: altrimenti wx attiva un altro pulsante.
                return

            # Su/giù sull'elenco: lasciati alla lista (KEY_DOWN) o gestiti qui.
            if key in (wx.WXK_UP, wx.WXK_DOWN) and not in_text:
                if on_marks or isinstance(focused, wx.ListBox):
                    event.Skip()
                    return
                if actively:
                    self._nudge_vol(+_VOL_STEP if key == wx.WXK_UP else -_VOL_STEP)
                    return
                event.Skip()
                return

            # Sinistra/destra: seek = navigazione nel tempo → poi Pausa può salvare.
            if (
                not in_text
                and not on_marks
                and session
                and key in (wx.WXK_LEFT, wx.WXK_RIGHT)
            ):
                self._suppress_auto_mark = False
                self._seek(+_SEEK_STEP if key == wx.WXK_RIGHT else -_SEEK_STEP)
                return

            if key == wx.WXK_SPACE:
                # Sull'elenco segnalibri: Spazio = vai al mark (NON pausa).
                # NVDA spesso manda Spazio per "attivare": non deve creare segnalibri.
                if on_marks or isinstance(focused, wx.ListBox):
                    self._goto_selected_mark()
                    return
                if isinstance(
                    focused,
                    (wx.Button, wx.TextCtrl, wx.CheckBox, wx.RadioButton, wx.Choice),
                ):
                    event.Skip()
                    return
                self._on_pause_toggle()
                return
            if isinstance(
                focused, (wx.TextCtrl, wx.Button, wx.CheckBox, wx.RadioButton, wx.Choice)
            ):
                event.Skip()
                return
            event.Skip()

        def _focus_is_marks(self, focused) -> bool:
            if focused is None:
                return False
            if focused is self.lst_marks:
                return True
            try:
                if isinstance(focused, wx.ListBox) and focused.GetId() == self.lst_marks.GetId():
                    return True
            except Exception:
                pass
            try:
                parent = focused.GetParent() if focused else None
                if parent is self.lst_marks:
                    return True
            except Exception:
                pass
            return False

        def _on_marks_key(self, event):
            """Invio/Spazio sull'elenco = vai al segnalibro (mai Pausa/nuovo mark)."""
            key = event.GetKeyCode()
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE):
                self._goto_selected_mark()
                return
            if key in (wx.WXK_UP, wx.WXK_DOWN):
                # Muoviamo noi la selezione così coincide con ciò che si sente.
                try:
                    idx = int(self.lst_marks.GetSelection())
                except Exception:
                    idx = -1
                n = len(self._marks)
                if n <= 0:
                    event.Skip()
                    return
                if idx < 0:
                    idx = 0
                elif key == wx.WXK_DOWN:
                    idx = min(n - 1, idx + 1)
                else:
                    idx = max(0, idx - 1)
                self.lst_marks.SetSelection(idx)
                self._remember_sel(idx)
                return
            event.Skip()

        def _on_marks_click(self, event):
            """Clic: dopo che wx ha aggiornato la selezione, vai a QUELLA riga."""
            event.Skip()
            # Non usare HitTest (con scroll/NVDA prende spesso la riga sbagliata).
            wx.CallAfter(self._goto_after_list_click)

        def _goto_after_list_click(self):
            try:
                idx = int(self.lst_marks.GetSelection())
            except Exception:
                idx = -1
            if idx < 0 or idx >= len(self._marks):
                return
            self._remember_sel(idx)
            self._goto_selected_mark(force_idx=idx)

        def _set_pause_label(self, paused: bool) -> None:
            # In pausa: Riprendi. In riproduzione (o fermo): Pausa. Ferma non cambia.
            try:
                self.btn_pause.SetLabel("&Riprendi" if paused else "&Pausa")
            except Exception:
                pass

        def _focus_controls(self):
            try:
                self.btn_pause.SetFocus()
            except Exception:
                pass

        def _focus_stop(self) -> None:
            try:
                self.btn_stop.SetFocus()
            except Exception:
                pass

        def _focus_marks(self) -> None:
            try:
                self.lst_marks.SetFocus()
            except Exception:
                pass

        def _remember_sel(self, idx: int) -> None:
            if idx < 0 or idx >= len(self._marks):
                return
            self._sel_mark_id = str(self._marks[idx].get("id") or "")

        def _index_for_mark_id(self, mark_id: str) -> int:
            want = str(mark_id or "")
            if not want:
                return -1
            for i, item in enumerate(self._marks):
                if str(item.get("id") or "") == want:
                    return i
            return -1

        def _selection_index(self) -> int:
            """Indice del segnalibro scelto: prima la riga evidenziata in elenco."""
            if not self._marks:
                return -1
            idx = -1
            try:
                idx = int(self.lst_marks.GetSelection())
            except Exception:
                idx = -1
            if 0 <= idx < len(self._marks):
                self._remember_sel(idx)
                return idx
            by_id = self._index_for_mark_id(self._sel_mark_id)
            if by_id >= 0:
                try:
                    self.lst_marks.SetSelection(by_id)
                except Exception:
                    pass
                return by_id
            return -1

        def _nav_marks(self, delta: int) -> None:
            """Solo con focus sull'elenco: muove la selezione (NVDA legge la riga)."""
            if not self._marks:
                self._say(MSG_NO_MARKS)
                return
            n = len(self._marks)
            try:
                idx = int(self.lst_marks.GetSelection())
            except Exception:
                idx = -1
            if idx < 0 or idx >= n:
                idx = self._selection_index()
            if idx < 0:
                idx = 0 if delta >= 0 else n - 1
            else:
                idx = max(0, min(n - 1, idx + int(delta)))
            try:
                self.lst_marks.SetSelection(idx)
                self._remember_sel(idx)
                label = mark_row_label(self._marks[idx])
                self.lbl_status.SetLabel(f"Segnalibro {idx + 1} di {n}: {label}")
            except Exception:
                pass

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
            # CallAfter: evita conflitti col CHAR_HOOK / focus sul pulsante.
            wx.CallAfter(self._browse_file_now)

        def _browse_file_now(self):
            self._say(MSG_BROWSE)
            FileDlg = self._windows_file_dialog_class()
            parent = self
            try:
                dlg = FileDlg(
                    parent,
                    message="Scegli audio o video",
                    wildcard=_WILDCARD,
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                )
            except TypeError:
                dlg = FileDlg(
                    parent,
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
                    self._say("Scelta file annullata.")
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
            self._say(f"Scelto: {os.path.basename(path)}.")
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

        def _begin_prepare(self) -> tuple[int, threading.Event]:
            """Nuova preparazione: invalida quelle in corso e restituisce (gen, cancel)."""
            try:
                self._cancel.set()
            except Exception:
                pass
            self._cancel = threading.Event()
            self._play_gen += 1
            self._listen_busy = True
            return self._play_gen, self._cancel

        def _prepare_and_play(self, start_sec: float, stay_on_marks: bool = False):
            if self._piece is None:
                return
            gen, cancel = self._begin_prepare()
            self._say("Preparazione ascolto…")
            dest = os.path.join(
                tempfile.gettempdir(),
                f"rtad_player_{os.getpid()}_{int(time.time() * 1000)}.wav",
            )

            def work():
                ok, phrase = clip.preview_wav(
                    self._piece, dest, cancel=cancel, head_only=False
                )
                wx.CallAfter(
                    self._after_prepare,
                    ok,
                    phrase,
                    dest,
                    start_sec,
                    stay_on_marks,
                    gen,
                )

            threading.Thread(target=work, daemon=True).start()

        def _after_prepare(
            self, ok, phrase, dest, start_sec, stay_on_marks=False, gen=0
        ):
            # Risultato vecchio (es. dopo un salto a segnalibro): scarta.
            if gen and gen != self._play_gen:
                try:
                    if os.path.isfile(dest):
                        os.remove(dest)
                except Exception:
                    pass
                return
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
            self._preview_origin = 0.0
            self._player.set_volume(self._listen_vol)
            dur = float(self._preview_dur or 0)
            start = max(0.0, float(start_sec or 0))
            if dur > 0:
                start = min(start, max(0.0, dur - 0.05))
            if not self._player.play(dest, from_sec=start, vol=self._listen_vol):
                self._say(MSG_LISTEN_FAIL)
                return
            self._playing = True
            self._paused = False
            self._play_pos = start
            self._set_pause_label(paused=False)
            # Se eravamo in un salto a segnalibro, NON riabilitare qui i mark automatici:
            # altrimenti uno Spazio di NVDA crea subito un segnalibro nuovo.
            if not stay_on_marks:
                self._suppress_auto_mark = False
            if stay_on_marks:
                self._focus_marks()
            else:
                self._focus_controls()
            if start > 0.15:
                self._say(MSG_RESUME_AT.format(pos=clip.speak_position(start)))
            else:
                self._say(MSG_PLAYING if not phrase else f"{phrase} {MSG_PLAYING}")

        def _position(self) -> float:
            """Orario nel file originale (tiene conto se il wav inizia a un segnalibro)."""
            origin = float(self._preview_origin or 0)
            if self._playing and self._player.is_playing():
                return origin + float(self._player.position_sec() or 0)
            if self._paused:
                return float(self._play_pos or 0)
            return float(self._play_pos or 0)

        def _save_auto_mark(self, pos: float, paused: bool) -> None:
            # Durante un salto tra segnalibri non se ne creano di nuovi.
            if self._suppress_auto_mark:
                return
            if not self._path or pos <= 0.2:
                return
            item = add_mark(self._config_dir, self._path, pos)
            self._refresh_marks(select_id=str(item.get("id") or ""))
            spoken = clip.speak_position(float(item["sec"]))
            if paused:
                self._say(MSG_PAUSED_MARK.format(pos=spoken))
            else:
                self._say(MSG_STOPPED_MARK.format(pos=spoken))

        def _clear_suppress_auto_mark(self) -> None:
            self._suppress_auto_mark = False

        def _stop_audio_no_mark(self) -> None:
            """Ferma l'audio senza creare segnalibri."""
            try:
                if self._player.is_playing() or self._player.is_open():
                    self._player.pause()
            except Exception:
                pass
            self._playing = False
            self._paused = False

        def _full_preview_ready(self, need_sec: float = 0.0) -> bool:
            """True se in cache c'è il wav del FILE INTERO che copre need_sec."""
            if not self._preview or not os.path.isfile(self._preview):
                return False
            if float(self._preview_origin or 0) > 0.01:
                return False
            dur = float(self._preview_dur or 0) or float(
                clip._wav_duration(self._preview) or 0
            )
            self._preview_dur = dur
            if dur <= 1.0:
                return False
            if need_sec >= max(0.05, dur - 0.05):
                return False
            return True

        def _play_full_at(self, sec: float) -> bool:
            """Riproduce dal secondo sec sul wav del file intero (stessa timeline)."""
            sec = max(0.0, float(sec or 0))
            if not self._full_preview_ready(sec):
                return False
            if not self._player.play(
                self._preview, from_sec=sec, vol=self._listen_vol
            ):
                return False
            self._preview_origin = 0.0
            self._playing = True
            self._paused = False
            self._play_pos = sec
            self._set_pause_label(paused=False)
            return True

        def _on_pause_from_button(self):
            """Invio/clic su Pausa/Riprendi: qui sì al segnalibro automatico."""
            self._suppress_auto_mark = False
            self._on_pause_toggle()

        def _on_stop_from_button(self):
            """Invio/clic su Ferma: qui sì al segnalibro automatico (se in play)."""
            self._suppress_auto_mark = False
            self._on_stop()

        def _on_pause_toggle(self, stay_on_list: bool = False):
            if self._listen_busy:
                return
            # Pausa anche se il flag e il thread non coincidono un attimo.
            if self._playing or self._player.is_playing():
                # Orario nel FILE (con offset se si era saltati a un segnalibro).
                pos = float(self._position() or 0)
                try:
                    if self._player.is_playing():
                        self._player.pause()
                    else:
                        self._player.pause()
                except Exception:
                    pass
                self._play_pos = pos
                self._playing = False
                self._paused = True
                self._set_pause_label(paused=True)
                self._save_auto_mark(pos, paused=True)
                if stay_on_list:
                    self._focus_marks()
                else:
                    self._focus_controls()
                return
            if self._paused:
                # Riprendi: solo da qui si riparte dopo una pausa.
                if self._preview and os.path.isfile(self._preview):
                    origin = float(self._preview_origin or 0)
                    # Nel wav in cache l'orario è relativo all'inizio del pezzo.
                    rel = max(0.0, float(self._play_pos or 0) - origin)
                    ok = self._player.resume()
                    if not ok:
                        ok = self._player.play(
                            self._preview,
                            from_sec=rel,
                            vol=self._listen_vol,
                        )
                    if ok:
                        self._playing = True
                        self._paused = False
                        self._set_pause_label(paused=False)
                        self._say(
                            MSG_RESUME_AT.format(
                                pos=clip.speak_position(self._play_pos)
                            )
                        )
                        if stay_on_list:
                            self._focus_marks()
                        else:
                            self._focus_controls()
                        return
                self._say(MSG_LISTEN_FAIL)
                return
            if self._path and self._piece is not None and self._preview:
                self._prepare_and_play(0.0)
                return
            if self._path and os.path.isfile(self._path):
                self._load_path(self._path, ask_resume=False)
                return
            self._say(MSG_NEED_FILE)

        def _soft_halt(self) -> None:
            """Ferma l'audio tenendo il path del preview (serve ai segnalibri)."""
            try:
                if self._player.is_playing():
                    self._player.pause()
                elif getattr(self._player, "is_open", lambda: False)():
                    self._player.pause()
            except Exception:
                try:
                    self._player.stop()
                except Exception:
                    pass

        def _on_stop(self):
            if self._listen_busy:
                return
            # Già fermo (non in pausa): solo avviso, nessun segnalibro nuovo.
            if (not self._playing) and (not self._paused):
                try:
                    if self._player.is_playing():
                        self._soft_halt()
                except Exception:
                    pass
                self._say(MSG_ALREADY_IDLE)
                self._focus_stop()
                return
            pos = self._position()
            was_paused = bool(self._paused)
            was_playing = bool(self._playing or self._player.is_playing())
            self._soft_halt()
            self._playing = False
            self._paused = False
            self._play_pos = 0.0
            self._set_pause_label(paused=False)
            # Segnalibro automatico solo se si ferma dalla riproduzione.
            # In pausa il segnalibro c'è già: non aggiungerne un altro.
            if was_playing and not was_paused and self._path and pos > 0.2:
                self._save_auto_mark(pos, paused=False)
            else:
                self._say("Fermo.")
            # Resta su Ferma: un altro Invio/clic dice «Già fermo».
            self._focus_stop()

        def _seek(self, delta: float):
            # Frecce orizzontali = mi muovo nel tempo: la prossima Pausa può salvare.
            self._suppress_auto_mark = False
            was_paused = bool(self._paused)
            media = max(0.0, self._position() + float(delta))
            # Sempre sulla timeline del file intero.
            if not self._full_preview_ready(media):
                self._prepare_and_play(media, stay_on_marks=False)
                return
            dur = float(self._preview_dur or 0)
            rel = min(media, max(0.0, dur - 0.05)) if dur > 0 else media
            want_play = bool(self._playing and self._player.is_playing())
            if not self._player.seek(rel, play=want_play):
                return
            self._preview_origin = 0.0
            self._play_pos = rel
            if want_play:
                self._playing = True
                self._paused = False
                self._set_pause_label(paused=False)
            elif was_paused:
                self._paused = True
                self._playing = False
                self._set_pause_label(paused=True)
            self._say(clip.speak_position(self._play_pos))

        def _nudge_vol(self, delta: int):
            self._listen_vol = clip._clamp_listen_vol(self._listen_vol + int(delta))
            self._player.set_volume(self._listen_vol)
            self._say(f"Volume {self._listen_vol} percento.")

        def _refresh_marks(self, select_id: str = ""):
            keep_id = str(select_id or self._sel_mark_id or "")
            if not keep_id:
                cur = self._selected_mark()
                if cur:
                    keep_id = str(cur.get("id") or "")
            self._marks = list_marks(self._config_dir, self._path) if self._path else []
            self.lst_marks.Clear()
            if not self._marks:
                self._sel_mark_id = ""
                self.lst_marks.Append(MSG_NO_MARKS)
                return
            select_at = 0
            found = False
            for index, item in enumerate(self._marks):
                self.lst_marks.Append(mark_row_label(item))
                if keep_id and str(item.get("id") or "") == keep_id:
                    select_at = index
                    found = True
            if not found and keep_id:
                # Nuovo segnalibro appena aggiunto: tieni l'id passato.
                select_at = min(select_at, len(self._marks) - 1)
            self.lst_marks.SetSelection(select_at)
            self._remember_sel(select_at)

        def _on_mark_select(self, event=None):
            idx = -1
            if event is not None:
                try:
                    idx = int(event.GetSelection())
                except Exception:
                    idx = -1
                event.Skip()
            if idx < 0:
                try:
                    idx = int(self.lst_marks.GetSelection())
                except Exception:
                    idx = -1
            if 0 <= idx < len(self._marks):
                self._remember_sel(idx)

        def _on_mark_activate(self, event=None):
            """Doppio clic: riparte dal segnalibro cliccato, non dal primo."""
            idx = -1
            if event is not None:
                try:
                    idx = int(event.GetSelection())
                except Exception:
                    idx = -1
                try:
                    event.Skip()
                except Exception:
                    pass
            if 0 <= idx < len(self._marks):
                try:
                    self.lst_marks.SetSelection(idx)
                except Exception:
                    pass
                self._remember_sel(idx)
            self._goto_selected_mark(force_idx=idx if idx >= 0 else None)

        def _selected_mark(self) -> dict | None:
            if not self._marks:
                return None
            idx = self._selection_index()
            if idx < 0 or idx >= len(self._marks):
                return None
            return self._marks[idx]

        def _resolve_mark_index(self, force_idx=None) -> int:
            """Indice della riga da attivare (clic / Invio / selezione)."""
            if not self._marks:
                return -1
            idx = -1
            if force_idx is not None:
                try:
                    idx = int(force_idx)
                except Exception:
                    idx = -1
            if 0 <= idx < len(self._marks):
                return idx
            try:
                idx = int(self.lst_marks.GetSelection())
            except Exception:
                idx = -1
            if 0 <= idx < len(self._marks):
                return idx
            return self._selection_index()

        def _prepare_mark_at(
            self,
            start_sec: float,
            stay_on_marks: bool = True,
            announce: str = "",
            gen: int = 0,
            cancel=None,
        ):
            """Estrae dal file sorgente DAL secondo del segnalibro e riproduce."""
            if self._piece is None:
                self._say(MSG_NEED_FILE)
                return
            if not gen:
                gen, cancel = self._begin_prepare()
            if cancel is None:
                cancel = self._cancel
            if announce:
                self._say(announce + " Preparazione dal file…")
            else:
                self._say("Preparazione ascolto dal segnalibro…")
            dest = os.path.join(
                tempfile.gettempdir(),
                f"rtad_player_mark_{os.getpid()}_{int(time.time() * 1000)}.wav",
            )
            start = max(0.0, float(start_sec or 0))

            def work():
                ok, phrase = clip.preview_wav_from(
                    self._piece, dest, start, cancel=cancel
                )
                wx.CallAfter(
                    self._after_prepare_mark,
                    ok,
                    phrase,
                    dest,
                    start,
                    stay_on_marks,
                    announce,
                    gen,
                )

            threading.Thread(target=work, daemon=True).start()

        def _after_prepare_mark(
            self,
            ok,
            phrase,
            dest,
            mark_sec,
            stay_on_marks=True,
            announce="",
            gen=0,
        ):
            if gen and gen != self._play_gen:
                try:
                    if os.path.isfile(dest):
                        os.remove(dest)
                except Exception:
                    pass
                return
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
            # Il wav INIZIA al segnalibro: offset = mark_sec, play da 0.
            self._preview_origin = float(mark_sec or 0)
            if not self._player.play(dest, from_sec=0.0, vol=self._listen_vol):
                self._say(MSG_LISTEN_FAIL)
                return
            self._playing = True
            self._paused = False
            self._play_pos = float(mark_sec or 0)
            self._set_pause_label(paused=False)
            if stay_on_marks:
                self._focus_marks()
            else:
                self._focus_controls()
            spoken = clip.speak_position(mark_sec)
            parts = []
            if announce:
                parts.append(announce.rstrip("."))
            parts.append(f"Audio da {spoken}")
            if phrase:
                parts.append(phrase)
            self._say(". ".join(parts) + ".")

        def _goto_selected_mark(self, force_idx=None):
            if not self._path:
                self._say(MSG_NEED_FILE)
                return
            # 1) Capire QUALE riga ha scelto l'utente (prima di ricaricare).
            idx_ui = -1
            if force_idx is not None:
                try:
                    idx_ui = int(force_idx)
                except Exception:
                    idx_ui = -1
            if idx_ui < 0:
                try:
                    idx_ui = int(self.lst_marks.GetSelection())
                except Exception:
                    idx_ui = -1
            want_id = ""
            if 0 <= idx_ui < len(self._marks):
                want_id = str(self._marks[idx_ui].get("id") or "")
            elif self._sel_mark_id:
                want_id = str(self._sel_mark_id)

            # 2) Ricarica da disco e riposiziona sulla STESSA id.
            fresh = list_marks(self._config_dir, self._path)
            if not fresh:
                self._marks = []
                self._refresh_marks()
                self._say(MSG_NO_MARKS)
                return
            self._marks = fresh
            idx = self._index_for_mark_id(want_id)
            if idx < 0 and 0 <= idx_ui < len(self._marks):
                idx = idx_ui
            if idx < 0:
                idx = 0
            self._refresh_marks(select_id=str(self._marks[idx].get("id") or ""))
            idx = self._index_for_mark_id(str(self._marks[idx].get("id") or ""))
            if idx < 0:
                idx = 0
            try:
                self.lst_marks.SetSelection(idx)
            except Exception:
                pass
            self._remember_sel(idx)
            item = self._marks[idx]
            sec = float(item.get("sec") or 0)
            label = mark_row_label(item)
            announce = (
                f"Segnalibro {idx + 1} di {len(self._marks)}: {label}. "
                f"Salto a {clip.speak_position(sec)}."
            )

            # Evita doppio avvio (clic + Invio sullo stesso istante).
            now = time.monotonic()
            goto_key = (str(item.get("id") or ""), round(sec, 2))
            last_key = getattr(self, "_last_goto_key", None)
            last_t = float(getattr(self, "_last_goto_t", 0) or 0)
            if goto_key == last_key and (now - last_t) < 0.4:
                return
            self._last_goto_key = goto_key
            self._last_goto_t = now

            # Salto tra segnalibri: resta attivo finché non si usa Pausa/Ferma/frecce ↔.
            # Così Spazio/Invio/clic sull'elenco NON creano segnalibri nuovi.
            self._suppress_auto_mark = True
            self._stop_audio_no_mark()

            # Una sola timeline: wav del FILE INTERO, poi seek al secondo del mark.
            if self._play_full_at(sec):
                self._say(
                    f"{announce} {MSG_RESUME_AT.format(pos=clip.speak_position(sec))}"
                )
                self._focus_marks()
                return

            # Manca il wav intero (o c'era un pezzo tagliato): ricostruiscilo e parti da sec.
            self._say(announce + " Preparazione del file…")
            self._prepare_and_play(sec, stay_on_marks=True)

        def _on_rename(self):
            item = self._selected_mark()
            if item is None:
                self._say(MSG_NO_MARKS)
                return
            sec = float(item.get("sec") or 0)
            clock = format_clock(sec)
            # Campo: orario se non ancora rinominato; altrimenti il nome già dato.
            if bool(item.get("auto_name")):
                initial = clock
            else:
                initial = str(item.get("name") or clock)
            with wx.TextEntryDialog(
                self,
                "Nome del segnalibro. L'orario resta in elenco.",
                "Rinomina segnalibro",
                initial,
            ) as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                name = dlg.GetValue().strip()
            if rename_mark(self._config_dir, self._path, item["id"], name):
                self._refresh_marks(select_id=str(item.get("id") or ""))
                shown = mark_row_label(
                    next(
                        (m for m in self._marks if str(m.get("id")) == str(item["id"])),
                        item,
                    )
                )
                self._say(f"{MSG_MARK_RENAMED} {shown}.")
            else:
                self._say(MSG_NO_MARKS)

        def _on_delete(self):
            item = self._selected_mark()
            if item is None:
                self._say(MSG_NO_MARKS)
                return
            mark_id = str(item.get("id") or "")
            if delete_mark(self._config_dir, self._path, mark_id):
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
            self._set_pause_label(paused=False)
            if clear_preview and self._preview:
                try:
                    if os.path.isfile(self._preview):
                        os.remove(self._preview)
                except Exception:
                    pass
                self._preview = ""
                self._preview_dur = 0.0
                self._preview_origin = 0.0

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
    import wx

    speaker = speaker or (lambda _t: None)
    dialog = None
    try:
        cls = _build_player()
        dialog = cls(
            parent,
            speaker,
            path or "",
            config_dir or "",
            clipboard_paths=clipboard_paths,
        )
        dialog.ShowModal()
    except Exception as exc:
        log.exception("open_dialog riproduttore")
        msg = f"Errore nel riproduttore: {exc}"
        try:
            speaker(msg)
        except Exception:
            pass
        try:
            wx.MessageBox(msg, "Riproduttore audio/video", wx.OK | wx.ICON_ERROR)
        except Exception:
            pass
    finally:
        if dialog is not None:
            try:
                dialog.close_work()
            except Exception:
                pass
            try:
                dialog.Destroy()
            except Exception:
                pass
