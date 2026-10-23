# -*- coding: utf-8 -*-
"""Elenco per allegare file: tutta la cartella, i più recenti in cima.

La finestra di Windows, sulle cartelle molto grandi, non carica tutti i file.
Qui l'elenco è nostro. Ogni riga dice nome, data, tipo e dimensione.
Su un audio o un video, fermandosi, si sente anche la durata.
"""

from __future__ import annotations

import os
import threading

import wx

import rtad_chat

_HELP = (
    "I più recenti sono in cima. "
    "Shift+freccia giù prende un gruppo di fila. "
    "Control+freccia salta, e quelli già presi restano. "
    "Poi di nuovo Shift+freccia giù: un altro gruppo di fila, "
    "senza perdere i primi. "
    "Control+Spazio aggiunge o toglie un file solo. "
    "Il numero che senti è il totale. Invio allega. Alt+C cambia cartella."
)
_REMEMBER_NAME = "attach_folder.txt"


def _remember_path(config_dir: str) -> str:
    return os.path.join(config_dir or "", _REMEMBER_NAME)


def remember_folder(config_dir: str, folder: str) -> None:
    if not config_dir or not folder or not os.path.isdir(folder):
        return
    try:
        os.makedirs(config_dir, exist_ok=True)
        with open(_remember_path(config_dir), "w", encoding="utf-8") as handle:
            handle.write(folder)
    except OSError:
        pass


def remembered_folder(config_dir: str) -> str:
    try:
        with open(_remember_path(config_dir), "r", encoding="utf-8") as handle:
            folder = (handle.read() or "").strip()
    except OSError:
        return ""
    if folder and os.path.isdir(folder):
        return folder
    return ""


def move_selection(cursor, anchor, selected, count, delta, shift, ctrl):
    """Nuova posizione, ancora e selezione.

    Control+freccia si sposta e non toglie nulla: il prossimo Shift
    parte da lì. Shift+freccia, anche con Control ancora premuto,
    aggiunge il nuovo gruppo di fila e tiene quelli già presi.
    """
    selected = set(selected or [])
    if count <= 0:
        return cursor, anchor, selected
    if cursor < 0 or cursor >= count:
        cursor = 0
    if delta == "home":
        nxt = 0
    elif delta == "end":
        nxt = count - 1
    else:
        nxt = max(0, min(count - 1, int(cursor) + int(delta)))
    if shift:
        if anchor is None or anchor < 0 or anchor >= count:
            anchor = cursor
        lo, hi = sorted((int(anchor), int(cursor)))
        base = {i for i in selected if i < lo or i > hi}
        lo2, hi2 = sorted((int(anchor), nxt))
        return nxt, anchor, base | set(range(lo2, hi2 + 1))
    if ctrl:
        return nxt, nxt, selected
    return nxt, nxt, {nxt}


def toggle_selection(cursor, anchor, selected, count):
    """Control+Spazio: aggiunge o toglie solo il file sotto il cursore."""
    selected = set(selected or [])
    if count <= 0 or cursor < 0 or cursor >= count:
        return cursor, anchor, selected
    if cursor in selected:
        selected.discard(cursor)
    else:
        selected.add(cursor)
    return cursor, cursor, selected


def initial_folder(config_dir: str = "", hint_path: str = "") -> str:
    saved = remembered_folder(config_dir)
    if saved:
        return saved
    hint = (hint_path or "").strip()
    low = hint.lower()
    if hint and not low.startswith(("http://", "https://")) and os.path.isfile(hint):
        folder = os.path.dirname(os.path.abspath(hint))
        if os.path.isdir(folder):
            return folder
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.isdir(downloads):
        return downloads
    return os.path.expanduser("~") or "."


class _FileList(wx.ListCtrl):
    """Elenco virtuale: il testo di ogni riga arriva solo quando serve."""

    def __init__(self, parent):
        super().__init__(
            parent,
            style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_NO_HEADER,
        )
        self._labels = []
        self.InsertColumn(0, "File")
        self.SetColumnWidth(0, 2500)

    def set_labels(self, labels) -> None:
        self._labels = list(labels or [])
        self.SetItemCount(0)
        self.SetItemCount(len(self._labels))
        if self._labels:
            self.RefreshItems(0, len(self._labels) - 1)

    def OnGetItemText(self, item, column):
        if column == 0 and 0 <= item < len(self._labels):
            return self._labels[item]
        return ""

    def label_at(self, index: int) -> str:
        if 0 <= index < len(self._labels):
            return self._labels[index]
        return ""

    def selected_indexes(self):
        out = []
        idx = self.GetFirstSelected()
        guard = 0
        while idx != -1 and guard < 10000:
            out.append(idx)
            nxt = self.GetNextSelected(idx)
            if nxt == idx or nxt < 0:
                break
            idx = nxt
            guard += 1
        return out


class AttachFolderDialog(wx.Dialog):
    """Elenco della cartella, selezione multipla, poi i percorsi scelti."""

    def __init__(self, parent, folder, config_dir="", speak=None, session=None):
        super().__init__(
            parent,
            title="Allega file",
            size=(920, 640),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._config_dir = config_dir or ""
        self._speak = speak
        self._session = session
        self._warned = set()
        self._folder = folder or ""
        self._rows = []
        self._load_gen = 0
        self._dur_gen = 0
        self._alive = True
        self._cursor = -1
        self._anchor = -1
        self._selected = set()
        self._last_count = 0
        self.chosen = []

        self.txt_path = wx.TextCtrl(self, style=wx.TE_READONLY)
        try:
            self.txt_path.SetName("Cartella")
        except Exception:
            pass

        self.lst = _FileList(self)
        try:
            self.lst.SetName("File, i più recenti in cima")
        except Exception:
            pass

        self.lbl_help = wx.StaticText(self, label=_HELP)
        self.lbl_count = wx.StaticText(self, label="Nessun file selezionato.")
        try:
            self.lbl_count.SetName("File selezionati")
        except Exception:
            pass
        self.lbl_dur = wx.StaticText(self, label="")
        try:
            self.lbl_dur.SetName("Durata del file evidenziato")
        except Exception:
            pass

        btn_ok = wx.Button(self, label="Allega selezionati")
        btn_dir = wx.Button(self, label="&Cambia cartella")
        btn_win = wx.Button(self, label="Finestra di &Windows")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, "Annulla")
        btn_ok.Bind(wx.EVT_BUTTON, lambda e: self._accept())
        btn_dir.Bind(wx.EVT_BUTTON, self.on_change_folder)
        btn_win.Bind(wx.EVT_BUTTON, self.on_windows)
        self.SetEscapeId(wx.ID_CANCEL)

        row = wx.BoxSizer(wx.HORIZONTAL)
        for btn in (btn_ok, btn_dir, btn_win, btn_cancel):
            row.Add(btn, 0, wx.RIGHT, 6)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.txt_path, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.lst, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.lbl_help, 0, wx.ALL, 8)
        sizer.Add(self.lbl_count, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(self.lbl_dur, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self._load(self._folder)

    def _on_destroy(self, event):
        self._alive = False
        self._load_gen += 1
        self._dur_gen += 1
        event.Skip()

    def _say(self, text: str) -> None:
        if self._speak and text:
            try:
                self._speak(text)
            except Exception:
                pass

    def _load(self, folder: str) -> None:
        self._load_gen += 1
        self._dur_gen += 1
        gen = self._load_gen
        self._folder = folder or ""
        self._rows = []
        self._cursor = -1
        self._anchor = -1
        self._selected = set()
        self._warned = set()
        self._last_count = 0
        self.txt_path.SetValue(self._folder)
        self.lbl_dur.SetLabel("")
        self.lst.set_labels([])
        self.lbl_help.SetLabel("Lettura della cartella…")
        self._say("Lettura della cartella.")

        def work():
            rows = []
            err = ""
            try:
                rows = rtad_chat.list_folder_files(folder)
            except Exception as exc:
                err = str(exc) or "Non riesco a leggere la cartella."
            wx.CallAfter(self._filled, gen, folder, rows, err)

        threading.Thread(target=work, daemon=True).start()

    def _filled(self, gen: int, folder: str, rows: list, err: str) -> None:
        if not self._alive or gen != self._load_gen:
            return
        if err:
            self.lbl_help.SetLabel("Non riesco a leggere la cartella.")
            self._say("Non riesco a leggere la cartella.")
            return
        self._rows = list(rows or [])
        labels = [
            rtad_chat.attach_row_label(row["name"], row["mtime"], row["size"])
            for row in self._rows
        ]
        self.lst.set_labels(labels)
        self.lbl_help.SetLabel(_HELP)
        remember_folder(self._config_dir, folder)
        name = os.path.basename(folder.rstrip("\\/")) or folder
        count = len(self._rows)
        if count == 0:
            try:
                self.lbl_count.SetLabel("Nessun file in questa cartella.")
            except Exception:
                pass
            self._say(f"Cartella {name}. Nessun file.")
            return
        first = self._rows[0]
        when = rtad_chat._mtime_it(first["mtime"])
        self._cursor = 0
        self._anchor = 0
        problem = self._problem_at(0)
        if problem:
            self._selected = set()
            self._last_count = 0
            try:
                self.lbl_count.SetLabel(problem)
                self.lbl_count.Wrap(860)
            except Exception:
                pass
            intro = (
                f"Cartella {name}. {count} file, i più recenti in cima. "
                f"Il primo è {first['name']}, {when}. {problem} {_HELP}"
            )
        else:
            self._selected = {0}
            self._show_selection(self._selected)
            self._last_count = 1
            try:
                self.lbl_count.SetLabel("1 file selezionato.")
            except Exception:
                pass
            intro = (
                f"Cartella {name}. {count} file, i più recenti in cima. "
                f"Il primo è già selezionato: {first['name']}, {when}. {_HELP}"
            )
        self._say(intro)
        self.lst.SetFocus()
        self._arm_duration(0)

    def _problem_at(self, index: int) -> str:
        if not self._session or index < 0 or index >= len(self._rows):
            return ""
        try:
            return rtad_chat.attachment_problem(
                self._session, self._rows[index]["path"]
            )
        except Exception:
            return ""

    def _without_blocked(self, selected):
        """Toglie i file che non possono entrare. Avvisa una volta per file."""
        kept = set()
        fresh = []
        for index in selected:
            problem = self._problem_at(index)
            if not problem:
                kept.add(index)
                continue
            if index not in self._warned:
                self._warned.add(index)
                fresh.append(problem)
        return kept, fresh

    def _show_selection(self, selected) -> None:
        self._selected = {i for i in selected if 0 <= i < len(self._rows)}
        if 0 <= self._cursor < len(self._rows):
            self.lst.EnsureVisible(self._cursor)
            self.lst.Focus(self._cursor)
        current = set(self.lst.selected_indexes())
        for index in current - self._selected:
            self.lst.Select(index, False)
        for index in sorted(self._selected - current):
            self.lst.Select(index, True)

    def _speak_here(self, count_changed: bool, extra: str = "") -> None:
        label = self.lst.label_at(self._cursor)
        n = len(self._selected)
        if count_changed and not (n == 1 and self._last_count == 1):
            if n == 0:
                note = "Nessun file selezionato."
            elif n == 1:
                note = "1 file selezionato."
            else:
                note = f"{n} file selezionati."
            text = f"{label} {note}".strip()
        else:
            text = label
        if extra:
            text = f"{text} {extra}".strip()
        self._last_count = n
        if n == 0:
            visible = "Nessun file selezionato."
        elif n == 1:
            visible = "1 file selezionato."
        else:
            visible = f"{n} file selezionati."
        if extra:
            visible = f"{visible} {extra}".strip()
        try:
            self.lbl_count.SetLabel(visible)
            self.lbl_count.Wrap(860)
            self.Layout()
        except Exception:
            pass
        self._say(text)
        self._arm_duration(self._cursor)

    def _move(self, delta, shift: bool, ctrl: bool) -> None:
        cursor, anchor, selected = move_selection(
            self._cursor,
            self._anchor,
            self._selected,
            len(self._rows),
            delta,
            shift,
            ctrl,
        )
        before = self._last_count
        self._cursor = cursor
        self._anchor = anchor
        selected, blocked = self._without_blocked(selected)
        self._show_selection(selected)
        self._speak_here(len(selected) != before, " ".join(blocked))

    def _toggle(self) -> None:
        cursor, anchor, selected = toggle_selection(
            self._cursor,
            self._anchor,
            self._selected,
            len(self._rows),
        )
        before = self._last_count
        self._cursor = cursor
        self._anchor = anchor
        selected, blocked = self._without_blocked(selected)
        self._show_selection(selected)
        self._speak_here(len(selected) != before, " ".join(blocked))

    def _arm_duration(self, index: int) -> None:
        self._dur_gen += 1
        gen = self._dur_gen
        self.lbl_dur.SetLabel("")
        if index < 0 or index >= len(self._rows):
            return
        wx.CallLater(1000, self._read_duration, gen, index)

    def _read_duration(self, gen: int, index: int) -> None:
        if not self._alive or gen != self._dur_gen:
            return
        if index < 0 or index >= len(self._rows):
            return
        row = self._rows[index]
        kind = ""
        try:
            kind = rtad_chat.attachment_kind(row["path"])
        except Exception:
            kind = ""
        if kind not in ("audio", "video"):
            self.lbl_dur.SetLabel("")
            return
        self.lbl_dur.SetLabel("Durata: lettura…")
        wx.CallAfter(self._read_duration_now, gen, index)

    def _read_duration_now(self, gen: int, index: int) -> None:
        if not self._alive or gen != self._dur_gen:
            return
        if index < 0 or index >= len(self._rows):
            return
        row = self._rows[index]
        label = ""
        try:
            import rtad_media

            info = rtad_media.get_media_tech_info(row["path"])
            label = (info.get("duration_label") or "").strip()
        except Exception:
            label = ""
        if not self._alive or gen != self._dur_gen:
            return
        if label:
            self.lbl_dur.SetLabel(f"Durata: {label}")
            self._say(f"Durata: {label}")
        else:
            self.lbl_dur.SetLabel("Durata: non disponibile")

    def on_change_folder(self, event=None):
        dlg = wx.DirDialog(
            self,
            "Scegli la cartella",
            defaultPath=self._folder or "",
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            folder = dlg.GetPath()
        finally:
            dlg.Destroy()
        if folder and os.path.isdir(folder):
            self._load(folder)

    def on_windows(self, event=None):
        dlg = wx.FileDialog(
            self,
            message="Allega uno o più file",
            defaultDir=self._folder or "",
            wildcard=rtad_chat.attachment_wildcard(),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            paths = [path for path in (dlg.GetPaths() or []) if path]
        finally:
            dlg.Destroy()
        if not paths:
            return
        self.chosen = paths
        folder = os.path.dirname(paths[0])
        remember_folder(self._config_dir, folder)
        self.EndModal(wx.ID_OK)

    def _accept(self) -> None:
        idxs = set(i for i in self._selected if 0 <= i < len(self._rows))
        try:
            idxs.update(
                i
                for i in self.lst.selected_indexes()
                if 0 <= i < len(self._rows)
            )
        except Exception:
            pass
        idxs = sorted(idxs)
        if not idxs:
            self._say("Scegli almeno un file.")
            return
        self.chosen = [self._rows[i]["path"] for i in idxs]
        remember_folder(self._config_dir, self._folder)
        self.EndModal(wx.ID_OK)

    def _list_has_focus(self) -> bool:
        focused = self.FindFocus()
        while focused is not None:
            if focused is self.lst:
                return True
            focused = focused.GetParent()
        return False

    def _on_list_key(self, event) -> bool:
        if event.AltDown():
            return False
        key = event.GetKeyCode()
        ctrl = event.ControlDown()
        shift = event.ShiftDown()
        if key in (wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN):
            self._move(1, shift, ctrl)
            return True
        if key in (wx.WXK_UP, wx.WXK_NUMPAD_UP):
            self._move(-1, shift, ctrl)
            return True
        if key in (wx.WXK_HOME, wx.WXK_NUMPAD_HOME):
            self._move("home", shift, ctrl)
            return True
        if key in (wx.WXK_END, wx.WXK_NUMPAD_END):
            self._move("end", shift, ctrl)
            return True
        if key in (wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN):
            page = self.lst.GetCountPerPage() or 12
            self._move(max(1, page), shift, ctrl)
            return True
        if key in (wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP):
            page = self.lst.GetCountPerPage() or 12
            self._move(-max(1, page), shift, ctrl)
            return True
        if key == wx.WXK_SPACE and ctrl and not shift:
            self._toggle()
            return True
        return False

    def on_char_hook(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        if self._list_has_focus() and self._on_list_key(event):
            return
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            if (
                self._list_has_focus()
                and not event.ShiftDown()
                and not event.AltDown()
                and not event.ControlDown()
            ):
                self._accept()
                return
        event.Skip()


def choose_attachment_paths(
    parent, config_dir="", hint_path="", speak=None, session=None
):
    """Percorsi scelti, oppure lista vuota se si annulla."""
    folder = initial_folder(config_dir, hint_path)
    dlg = AttachFolderDialog(
        parent,
        folder=folder,
        config_dir=config_dir,
        speak=speak,
        session=session,
    )
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return []
        return list(dlg.chosen or [])
    finally:
        dlg.Destroy()
