# -*- coding: utf-8 -*-
"""Salva e Sfoglia di RTAD, al posto delle finestre di Windows.

Stesse chiamate di wx.FileDialog e wx.DirDialog. A schermo e a voce.
L'elenco Unità scorre solo i dischi. Invio o doppio clic apre il disco.
Tab mostra solo le cartelle di quel disco. Shift+Tab torna alle unità.
Alt+P legge lo stato: premuto due volte di seguito lo copia.
"""
from __future__ import annotations

import os
import time

import wx

_THIS_PC = "::{RTAD-QUESTO-PC}"
_MAX_ROWS = 4000

_speaker = None
_before_status = None
_speak_nav = None


def set_speaker(fn):
    global _speaker
    _speaker = fn


def set_before_status(fn):
    """Prima della frase di stato: zittisce il nome del tasto, se c'è."""
    global _before_status
    _before_status = fn


def set_speak_nav(fn):
    """Vero solo quando la voce di RTAD deve dire la riga dell'albero.

    Con NVDA, e la voce di RTAD spenta, l'albero lo legge NVDA.
    """
    global _speak_nav
    _speak_nav = fn


def install(speaker=None, before_status=None, speak_nav=None):
    if speaker is not None:
        set_speaker(speaker)
    if before_status is not None:
        set_before_status(before_status)
    if speak_nav is not None:
        set_speak_nav(speak_nav)
    wx.FileDialog = RTADFileDialog
    wx.DirDialog = RTADDirDialog


def say(text):
    text = str(text or "").strip()
    if not text:
        return
    if _before_status is not None:
        try:
            _before_status()
        except Exception:
            pass
    if _speaker is not None:
        try:
            _speaker(text)
            return
        except Exception:
            pass
    try:
        import ui
        ui.message(text)
    except Exception:
        pass


def parse_wildcard(wildcard):
    """«Descrizione|*.pdf;*.txt|Tutti|*.*» → [(descrizione, [pattern])]."""
    parts = str(wildcard or "").split("|")
    filters = []
    i = 0
    while i + 1 < len(parts):
        desc = parts[i].strip() or "File"
        pats = [p.strip() for p in parts[i + 1].split(";") if p.strip()]
        filters.append((desc, pats or ["*.*"]))
        i += 2
    if not filters:
        filters.append(("Tutti i file", ["*.*"]))
    return filters


def patterns_match_all(patterns):
    if not patterns:
        return True
    return any(p in ("*", "*.*") for p in patterns)


def name_matches(name, patterns):
    if patterns_match_all(patterns):
        return True
    low = str(name or "").casefold()
    for pat in patterns:
        if _glob_match(low, str(pat or "").casefold()):
            return True
    return False


def _glob_match(name, pat):
    if pat in ("*", "*.*"):
        return True
    if pat.startswith("*."):
        ext = pat[1:]
        return name.endswith(ext)
    if pat.startswith("*") and pat.endswith("*") and len(pat) > 2:
        return pat[1:-1] in name
    return name == pat


def ensure_extension(name, patterns):
    """In salvataggio, se manca l'estensione, aggiunge quella del tipo scelto."""
    name = str(name or "").strip()
    if not name or patterns_match_all(patterns):
        return name
    if os.path.splitext(name)[1]:
        return name
    for pat in patterns:
        if pat.startswith("*.") and pat not in ("*.*", "*"):
            ext = pat[1:]
            if ext and all(ch not in ext for ch in "\\/;|*"):
                return name + ext
    return name


def safe_start_dir(path):
    path = os.path.expanduser(str(path or "").strip().strip('"'))
    if path and os.path.isdir(path):
        return os.path.abspath(path)
    if path:
        parent = os.path.dirname(os.path.abspath(path))
        if parent and os.path.isdir(parent):
            return parent
    home = os.path.expanduser("~")
    if home and os.path.isdir(home):
        return home
    return os.path.abspath(os.sep)


class _Row:
    def __init__(self, kind, label, path, mtime=0):
        self.kind = kind
        self.label = label
        self.path = path
        self.mtime = mtime


class _Node:
    def __init__(self, kind, path):
        self.kind = kind
        self.path = path
        self.loaded = False


def _norm_path(path):
    if not path or path == _THIS_PC:
        return _THIS_PC
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def _chain_to(path):
    """Dal disco fino alla cartella."""
    chain = []
    cur = os.path.abspath(path)
    while True:
        chain.append(cur)
        parent = os.path.dirname(cur)
        if os.path.normcase(os.path.normpath(parent)) == os.path.normcase(os.path.normpath(cur)):
            break
        cur = parent
    chain.reverse()
    return chain


def _own_voice_nav():
    if _speak_nav is None:
        return False
    try:
        return bool(_speak_nav())
    except Exception:
        return False


def _files_in(path, patterns):
    files = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if _hidden(entry) or not entry.is_file(follow_symlinks=False):
                        continue
                    if name_matches(entry.name, patterns):
                        try:
                            mtime = entry.stat(follow_symlinks=False).st_mtime
                        except OSError:
                            mtime = 0
                        files.append(_Row("file", entry.name, entry.path, mtime))
                except OSError:
                    continue
    except OSError:
        return [_Row("empty", "Cartella non raggiungibile.", "")], 0, False
    files.sort(key=lambda row: (-row.mtime, row.label.casefold()))
    total = len(files)
    clipped = total > _MAX_ROWS
    if clipped:
        files = files[:_MAX_ROWS]
    if not files:
        files = [_Row("empty", "Nessun file in questa cartella.", "")]
    return files, total, clipped


def _folders_in(path):
    found = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if _hidden(entry) or not entry.is_dir(follow_symlinks=False):
                        continue
                    found.append(_Row("dir", entry.name, entry.path))
                except OSError:
                    continue
    except OSError:
        return [_Row("empty", "Cartella non raggiungibile.", "")], False
    found.sort(key=lambda row: row.label.casefold())
    clipped = len(found) > _MAX_ROWS
    if clipped:
        found = found[:_MAX_ROWS]
    if not found:
        found = [_Row("empty", "Nessuna cartella qui.", "")]
    return found, clipped


def _drive_rows():
    rows = [_Row("drive", _drive_label(drive), drive) for drive in _drives()]
    if not rows:
        rows = [_Row("empty", "Nessun disco trovato.", "")]
    return rows


def _hidden(entry):
    try:
        attrs = int(entry.stat(follow_symlinks=False).st_file_attributes)
    except Exception:
        return False
    return bool(attrs & 0x2)


def _drives():
    found = []
    try:
        import ctypes
        mask = int(ctypes.windll.kernel32.GetLogicalDrives() or 0)
    except Exception:
        mask = 0
    if not mask:
        return found
    for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        if mask & (1 << i):
            found.append(f"{letter}:\\")
    return found


def _drive_label(path):
    letter = path[:2]
    name = ""
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(256)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            path, buf, 256, None, None, None, None, 0
        )
        if ok:
            name = buf.value or ""
    except Exception:
        name = ""
    if name:
        return f"{name} ({letter})"
    return letter


def _parent_of(path):
    if not path or path == _THIS_PC:
        return None
    abs_path = os.path.abspath(path)
    parent = os.path.dirname(abs_path)
    if not parent or parent == abs_path:
        return _THIS_PC
    return parent


def _folder_title(path):
    if path == _THIS_PC:
        return "Questo PC"
    name = os.path.basename(os.path.normpath(path))
    if not name:
        return path
    return name


def list_place(path, patterns, include_files):
    """Righe della cartella. La prima riga vuota è una frase vera, non muta."""
    if path == _THIS_PC:
        rows = [_Row("drive", _drive_label(drive), drive) for drive in _drives()]
        if not rows:
            rows.append(_Row("empty", "Nessun disco trovato.", ""))
        return rows, 0, False
    dirs = []
    files = []
    total_files = 0
    try:
        entries = list(os.scandir(path))
    except OSError:
        raise
    for entry in entries:
        try:
            if _hidden(entry):
                continue
            if entry.is_dir(follow_symlinks=False):
                dirs.append(_Row("dir", f"Cartella {entry.name}", entry.path))
            elif include_files and entry.is_file(follow_symlinks=False):
                if name_matches(entry.name, patterns):
                    total_files += 1
                    files.append(_Row("file", entry.name, entry.path))
        except OSError:
            continue
    dirs.sort(key=lambda row: row.label.casefold())
    files.sort(key=lambda row: row.label.casefold())
    rows = dirs + files
    clipped = False
    if len(rows) > _MAX_ROWS:
        rows = rows[:_MAX_ROWS]
        clipped = True
    if not rows:
        msg = "Nessun file in questa cartella." if include_files else "Nessuna cartella qui."
        rows.append(_Row("empty", msg, ""))
    return rows, total_files, clipped


_TREE_HOW = (
    "L'elenco Unità scorre solo i dischi: freccia su e freccia giù, oppure la lettera iniziale. "
    "Invio o un doppio clic apre il disco e il focus resta su quell'elenco. "
    "Tab mostra solo le cartelle di quel disco. "
    "La lettera iniziale porta alla cartella. Invio o un doppio clic la apre. "
    "Shift+Tab torna all'elenco delle unità. "
    "I file della cartella aperta sono i più recenti in cima. Home va al primo. "
    "Invio o un doppio clic su un file lo sceglie. "
    "Invio sul pulsante Indietro, o un clic, oppure Alt+freccia sinistra, torna al percorso precedente. "
    "Alt+freccia su sale di una cartella. "
    "Invio sul pulsante Nuova cartella, o un clic, chiede il nome. "
    "Alt+P legge lo stato: premuto due volte di seguito lo copia. Esc annulla."
)
_FILE_HINT = (
    "Il primo campo è Nome file: si incolla un percorso con Control+V. "
    "Poi Tipo di file, casella combinata: freccia giù cambia tipo e la voce lo dice. "
    "Invio sul pulsante Apri o Salva, o un clic, conferma. "
    + _TREE_HOW
    + " Invio o doppio clic su un file lo sceglie."
)
_MULTI_HINT = (
    "Il primo campo è Nome file. "
    "Poi Tipo di file, casella combinata: freccia giù cambia tipo e la voce lo dice. "
    "Ctrl e un clic, oppure Shift e le frecce, aggiungono file alla scelta. "
    "Invio sul pulsante Apri, o un clic, conferma i file selezionati. "
    + _TREE_HOW
)
_DIR_HINT = (
    "Il primo campo è Cartella: si incolla un percorso con Control+V. "
    "Invio sul pulsante Seleziona cartella, o un clic, conferma la cartella aperta. "
    + _TREE_HOW
    + " Elementi mostra i file, così si vede cosa c'è dentro. "
    "La cartella si conferma col pulsante Seleziona cartella."
)


_STANDARD_TYPES = (
    ("Immagini", ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.webp", "*.tif", "*.tiff"]),
    ("Audio e video", ["*.mp3", "*.wav", "*.m4a", "*.flac", "*.ogg", "*.mp4", "*.mkv", "*.avi", "*.mov", "*.webm"]),
    ("Documenti", ["*.pdf", "*.txt", "*.doc", "*.docx", "*.epub", "*.html", "*.htm", "*.rtf"]),
    ("Tutti i file", ["*.*"]),
)


def with_standard_types(filters):
    """Il tipo chiesto dal programma resta il primo. Poi Immagini, Audio e video, Tutti."""
    out = list(filters or [])
    names = {desc.casefold() for desc, _pats in out}
    has_all = any(patterns_match_all(pats) for _desc, pats in out)
    for desc, pats in _STANDARD_TYPES:
        if desc.casefold() in names:
            continue
        if desc == "Tutti i file" and has_all:
            continue
        out.append((desc, pats))
        names.add(desc.casefold())
    if not out:
        out.append(("Tutti i file", ["*.*"]))
    return out


class _AskNameDialog(wx.Dialog):
    """Nome della cartella nuova. Pulsanti nostri, così la voce li dice."""

    def __init__(self, parent):
        super().__init__(
            parent,
            title="Nuova cartella",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        vbox = wx.BoxSizer(wx.VERTICAL)
        text = wx.StaticText(
            self,
            label=(
                "Scrivi il nome della nuova cartella. "
                "Invio sul pulsante Crea, o un clic, la crea. Esc annulla."
            ),
        )
        text.Wrap(420)
        vbox.Add(text, 0, wx.ALL | wx.EXPAND, 12)
        self.txt = wx.TextCtrl(self)
        self.txt.SetName("Nome della cartella")
        vbox.Add(self.txt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        row = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self, wx.ID_OK, "Pulsante &Crea")
        cancel = wx.Button(self, wx.ID_CANCEL, "Pulsante Annulla")
        ok.SetDefault()
        row.Add(ok, 0, wx.ALL, 5)
        row.Add(cancel, 0, wx.ALL, 5)
        vbox.Add(row, 0, wx.ALIGN_CENTER | wx.ALL, 8)
        self.SetSizerAndFit(vbox)
        self.txt.SetFocus()

    def value(self):
        try:
            return self.txt.GetValue().strip()
        except Exception:
            return ""


class _TypeListDialog(wx.Dialog):
    """Elenco dei tipi, aperto con Alt+freccia giù. Ogni riga si sente."""

    def __init__(self, parent, names, index):
        super().__init__(
            parent,
            title="Tipo di file",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.pick = index if index is not None else 0
        vbox = wx.BoxSizer(wx.VERTICAL)
        text = wx.StaticText(
            self,
            label=(
                "Freccia su e freccia giù scorrono i tipi. "
                "La lettera iniziale porta al tipo. "
                "Invio sceglie, o un doppio clic. Esc chiude."
            ),
        )
        text.Wrap(380)
        vbox.Add(text, 0, wx.ALL | wx.EXPAND, 8)
        self.lst = wx.ListBox(self, choices=list(names or []))
        self.lst.SetName("Tipo di file")
        if names:
            self.lst.SetSelection(max(0, min(self.pick, len(names) - 1)))
        self.lst.Bind(wx.EVT_LISTBOX, self._on_sel)
        self.lst.Bind(wx.EVT_LISTBOX_DCLICK, self._on_ok)
        vbox.Add(self.lst, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self, wx.ID_OK, "Pulsante Scegli")
        cancel = wx.Button(self, wx.ID_CANCEL, "Pulsante Annulla")
        row.Add(ok, 0, wx.ALL, 4)
        row.Add(cancel, 0, wx.ALL, 4)
        vbox.Add(row, 0, wx.ALIGN_CENTER | wx.ALL, 6)
        self.SetSizer(vbox)
        self.SetSize((440, 340))
        self.lst.SetFocus()
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char)
        wx.CallLater(200, self._speak_current)

    def _phrase(self):
        try:
            name = self.lst.GetStringSelection() or ""
        except Exception:
            name = ""
        return f"{name or 'Tipo di file'} casella combinata."

    def _speak_current(self):
        if _own_voice_nav():
            say(self._phrase())

    def _on_sel(self, event):
        self._speak_current()
        if event is not None:
            event.Skip()

    def _on_ok(self, event=None):
        try:
            self.pick = int(self.lst.GetSelection())
        except Exception:
            self.pick = -1
        if self.IsModal():
            self.EndModal(wx.ID_OK)

    def _on_char(self, event):
        try:
            key = event.GetKeyCode()
        except Exception:
            event.Skip()
            return
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_ok()
            return
        event.Skip()


class _PickerBase(wx.Dialog):
    def __init__(self, parent, title, hint):
        super().__init__(
            parent,
            title=str(title or "Scegli"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(760, 560),
        )
        self._accepted = False
        self._result = ""
        self._results = []
        self._directory = safe_start_dir("")
        self._rows = []
        self._alt_p_at = 0.0
        self._hint = hint
        self._silent = False
        self._files_clipped = False
        self._list_kind = "files"
        self.lbl_elements = None
        self._last_nav = ""
        self._last_nav_at = 0.0
        self._root = None
        self._history = []
        self._history_at = -1
        self.txt_path = None
        self.txt_search = None
        self.txt_name = None
        self.choice = None
        self.tree = None
        self.lst_units = None
        self.lst = None
        self._unit_rows = []
        self._filling_units = False
        self.txt_status_progress = None
        self.gauge = None

    def _fields_before_buttons(self, panel, vbox):
        return

    def _build_chrome(self, panel, vbox, list_name):
        self.tree = wx.TreeCtrl(
            panel,
            style=(
                wx.TR_HAS_BUTTONS
                | wx.TR_LINES_AT_ROOT
                | wx.TR_FULL_ROW_HIGHLIGHT
                | wx.TR_SINGLE
            ),
        )
        self.tree.SetName("Albero cartelle")
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_tree_sel)
        self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self._on_expanding)
        self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDED, self._on_toggled)
        self.tree.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self._on_toggled)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_activated)
        self.tree.Hide()
        try:
            self.tree.SetCanFocus(False)
        except Exception:
            pass

        units_help = wx.StaticText(
            panel,
            label=(
                "Unità. Freccia su e freccia giù, o la lettera iniziale, scorrono solo i dischi. "
                "Invio o un doppio clic apre il disco. "
                "Tab mostra solo le cartelle di quel disco. Shift+Tab torna qui."
            ),
        )
        units_help.Wrap(700)
        vbox.Add(units_help, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.lst_units = wx.ListBox(panel, style=wx.LB_SINGLE | wx.LB_NEEDED_SB)
        self.lst_units.SetName("Unità")
        self.lst_units.Bind(wx.EVT_LISTBOX, self._on_unit_sel)
        self.lst_units.Bind(wx.EVT_LISTBOX_DCLICK, self._on_unit_activate)
        vbox.Add(self.lst_units, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self.lbl_elements = wx.StaticText(
            panel, label="File di questa cartella, i più recenti in cima:"
        )
        vbox.Add(self.lbl_elements, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.lst = wx.ListBox(panel, style=self._list_style())
        self.lst.SetName("Elementi")
        self.lst.Bind(wx.EVT_LISTBOX_DCLICK, self._on_dclick)
        self.lst.Bind(wx.EVT_LISTBOX, self._on_select)
        vbox.Add(self.lst, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._init_tree()

        self._fields_before_buttons(panel, vbox)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(panel, label=self._ok_label())
        ok.SetDefault()
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        buttons.Add(ok, 0, wx.ALL, 4)
        cancel = wx.Button(panel, wx.ID_CANCEL, "Pulsante Annulla")
        buttons.Add(cancel, 0, wx.ALL, 4)
        back = wx.Button(panel, label="Pulsante &Indietro")
        back.Bind(wx.EVT_BUTTON, lambda e: self._go_back())
        buttons.Add(back, 0, wx.ALL, 4)
        new = wx.Button(panel, label="Pulsante &Nuova cartella")
        new.Bind(wx.EVT_BUTTON, self._on_new_folder)
        buttons.Add(new, 0, wx.ALL, 4)
        vbox.Add(buttons, 0, wx.ALIGN_LEFT | wx.LEFT | wx.RIGHT, 4)

        if self.txt_path is None:
            path_row = wx.BoxSizer(wx.HORIZONTAL)
            path_row.Add(
                wx.StaticText(panel, label="Cartella:"),
                0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6,
            )
            self.txt_path = wx.TextCtrl(panel)
            self.txt_path.SetName("Cartella")
            path_row.Add(self.txt_path, 1, wx.EXPAND)
            vbox.Add(path_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        search_row.Add(
            wx.StaticText(panel, label="Cerca:"),
            0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6,
        )
        self.txt_search = wx.TextCtrl(panel)
        self.txt_search.SetName("Cerca in questa cartella")
        self.txt_search.Bind(wx.EVT_TEXT, self._on_search)
        search_row.Add(self.txt_search, 1, wx.EXPAND)
        vbox.Add(search_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        label = wx.StaticText(
            panel,
            label="Stato (Alt+P, oppure un clic sull'etichetta):",
        )
        label.Bind(wx.EVT_LEFT_DOWN, self._focus_status)
        vbox.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.txt_status_progress = wx.TextCtrl(panel, style=wx.TE_READONLY)
        self.txt_status_progress.SetName("Stato")
        vbox.Add(self.txt_status_progress, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.gauge = wx.Gauge(panel, range=100)
        self.gauge.SetName("Avanzamento")
        vbox.Add(self.gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        hint = wx.StaticText(panel, label=self._hint)
        hint.Wrap(700)
        vbox.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.Bind(wx.EVT_CHAR_HOOK, self._on_char)

    def _extra_rows(self, panel, vbox):
        return

    def _list_style(self):
        return wx.LB_SINGLE | wx.LB_NEEDED_SB

    def _ok_label(self):
        return "&Apri"

    def _set_status(self, text, speak=False):
        text = str(text or "").strip() or "Stato non disponibile."
        try:
            self.txt_status_progress.SetValue(text)
        except Exception:
            pass
        if speak:
            say(text)

    def _focus_status(self, event=None):
        try:
            self.txt_status_progress.SetFocus()
            self.txt_status_progress.SetInsertionPoint(0)
            msg = self.txt_status_progress.GetValue().strip() or "Stato non disponibile."
            wx.CallLater(50, say, msg)
        except Exception:
            wx.CallLater(50, say, "Impossibile raggiungere lo stato.")

    def _announce_status(self):
        now = time.time()
        double = (now - self._alt_p_at) < 0.6
        self._alt_p_at = now
        if double:
            self._copy_status()
            return
        msg = ""
        try:
            msg = self.txt_status_progress.GetValue().strip()
        except Exception:
            msg = ""
        say(f"Stato: {msg or 'Stato non disponibile.'}")

    def _copy_status(self):
        msg = ""
        try:
            msg = self.txt_status_progress.GetValue().strip()
        except Exception:
            msg = ""
        msg = msg or "Stato non disponibile."
        try:
            if wx.TheClipboard.Open():
                try:
                    wx.TheClipboard.SetData(wx.TextDataObject(msg))
                finally:
                    wx.TheClipboard.Close()
                say("Stato copiato negli appunti.")
                return
        except Exception:
            pass
        say("Impossibile copiare negli appunti.")

    def _on_char(self, event):
        try:
            key = event.GetKeyCode()
            alt = bool(event.AltDown())
            ctrl = bool(event.ControlDown())
            shift = bool(event.ShiftDown())
        except Exception:
            event.Skip()
            return
        if alt and not ctrl and not shift and key in (ord("P"), ord("p")):
            self._announce_status()
            return
        focus = wx.Window.FindFocus()
        if getattr(self, "_type_list_open", False):
            event.Skip()
            return
        if (
            self.choice is not None
            and focus is self.choice
            and not ctrl
            and not shift
        ):
            if alt and key in (wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN):
                if _own_voice_nav():
                    self._open_type_list()
                    return
                event.Skip()
                return
            if (
                not alt
                and key in (wx.WXK_DOWN, wx.WXK_UP, wx.WXK_NUMPAD_DOWN, wx.WXK_NUMPAD_UP)
                and _own_voice_nav()
            ):
                delta = -1 if key in (wx.WXK_UP, wx.WXK_NUMPAD_UP) else 1
                self._cycle_type(delta)
                return
        if alt and not ctrl and not shift and key == wx.WXK_LEFT:
            self._go_back()
            return
        if alt and not ctrl and not shift and key == wx.WXK_UP:
            self._go_parent()
            return
        if (
            self.lst is not None
            and focus is self.lst
            and ctrl
            and not alt
            and key in (wx.WXK_HOME, wx.WXK_NUMPAD_HOME)
        ):
            self._select_first_element()
            return
        # Le lettere restano all'albero e all'elenco: la iniziale porta al nome.
        if key == wx.WXK_BACK and not alt and not ctrl and focus is self.tree:
            self._go_parent()
            return
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and not alt and not ctrl:
            if self.lst_units is not None and focus is self.lst_units:
                self._on_unit_activate()
                return
            if focus is self.tree:
                self._expand_selected()
                return
            if self.lst is not None and focus is self.lst:
                self._activate_row()
                return
            if focus is self.txt_path:
                self._on_go()
                return
            if self.txt_search is not None and focus is self.txt_search:
                self._fill_files(self._directory)
                return
        event.Skip()

    def _selected_indexes(self):
        try:
            if self.lst.GetWindowStyleFlag() & wx.LB_EXTENDED:
                return list(self.lst.GetSelections())
        except Exception:
            pass
        try:
            sel = self.lst.GetSelection()
        except Exception:
            return []
        if sel == wx.NOT_FOUND:
            return []
        return [sel]

    def _current_row(self):
        indexes = self._selected_indexes()
        if not indexes:
            return None
        index = indexes[0]
        if index < 0 or index >= len(self._rows):
            return None
        return self._rows[index]

    def _fill(self, rows):
        self._rows = list(rows)
        if self.lst is None:
            return
        self._filling = True
        self.lst.Freeze()
        try:
            self.lst.Clear()
            for row in self._rows:
                self.lst.Append(row.label)
            if self._rows:
                self.lst.SetSelection(0)
        finally:
            self.lst.Thaw()
            self._filling = False

    def _show_path(self):
        shown = "Questo PC" if self._directory == _THIS_PC else self._directory
        try:
            self.txt_path.ChangeValue(shown)
        except Exception:
            pass

    def _init_tree(self):
        self.tree.DeleteAllItems()
        self._root = self.tree.AddRoot("Questo PC")
        self.tree.SetItemData(self._root, _Node("root", _THIS_PC))
        self._load_children(self._root)
        self.tree.Expand(self._root)

    def _reveal(self, path, speak_error=True, record=True, announce=True):
        """Apre l'albero fino a quella cartella e la seleziona."""
        path = path or _THIS_PC
        if path != _THIS_PC:
            path = os.path.abspath(path)
            if not os.path.isdir(path):
                self._set_status("Cartella non raggiungibile.", speak=speak_error)
                return False
        try:
            focus_back = wx.Window.FindFocus()
        except Exception:
            focus_back = None
        if focus_back not in (self.lst_units, self.lst):
            focus_back = None
        self._silent = True
        item = None
        try:
            item = self._item_for_path(path)
            if item is None:
                self._set_status("Cartella non raggiungibile.", speak=speak_error)
                return False
            self._load_children(item)
            self._expand_ancestors(item)
            if item != self._root:
                self.tree.Expand(item)
            self.tree.SelectItem(item)
            self.tree.EnsureVisible(item)
        finally:
            self._silent = False
        if item is not None:
            self._apply_folder(item)
            if announce:
                self._announce_item(item)
            if record:
                self._push_history(self._directory)
        self._sync_unit_list(self._directory)
        if focus_back is not None:
            wx.CallAfter(self._refocus, focus_back)
        return item is not None

    def _go(self, path, speak_error=True):
        return self._reveal(path, speak_error=speak_error)

    def _item_for_path(self, path):
        if path == _THIS_PC or self._root is None:
            return self._root
        item = self._root
        for step in _chain_to(path):
            nxt = self._ensure_step(item, step)
            if nxt is None:
                return None
            item = nxt
        return item

    def _ensure_step(self, item, step_path):
        """Aggiunge anche la cartella nascosta, se il percorso ci passa dentro."""
        self._load_children(item)
        wanted = _norm_path(step_path)
        found = self._child_by_norm(item, wanted)
        if found is not None:
            return found
        if not step_path or not os.path.isdir(step_path):
            return None
        name = os.path.basename(os.path.normpath(step_path)) or step_path
        kind = "drive" if os.path.normpath(step_path).endswith(":\\") else "dir"
        return self._append_folder(item, name if kind == "dir" else _drive_label(step_path), step_path, kind)

    def _expand_ancestors(self, item):
        parent = self.tree.GetItemParent(item)
        chain = []
        while parent and parent.IsOk():
            chain.append(parent)
            if parent == self._root:
                break
            parent = self.tree.GetItemParent(parent)
        for node in reversed(chain):
            self.tree.Expand(node)

    def _load_children(self, item):
        node = self.tree.GetItemData(item) if item and item.IsOk() else None
        if node is None or node.loaded or node.kind in ("empty", "placeholder"):
            return
        node.loaded = True
        self.tree.DeleteChildren(item)
        if node.kind == "root":
            drives = _drives()
            if not drives:
                self._append_note(item, "Nessun disco trovato.")
                return
            for drive in drives:
                self._append_folder(item, _drive_label(drive), drive, "drive")
            return
        if not node.path or not os.path.isdir(node.path):
            self._append_note(item, "Cartella non raggiungibile.")
            return
        found = []
        try:
            with os.scandir(node.path) as it:
                for entry in it:
                    try:
                        if _hidden(entry):
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            found.append((entry.name, entry.path))
                    except OSError:
                        continue
        except OSError:
            self._append_note(item, "Cartella non raggiungibile.")
            return
        found.sort(key=lambda pair: pair[0].casefold())
        clipped = len(found) > _MAX_ROWS
        if clipped:
            found = found[:_MAX_ROWS]
        if not found:
            self._append_note(item, "Nessuna cartella qui.")
            return
        for name, folder in found:
            self._append_folder(item, name, folder, "dir")
        if clipped:
            self._append_note(item, f"Mostro le prime {_MAX_ROWS} cartelle.")

    def _append_folder(self, parent, label, path, kind):
        item = self.tree.AppendItem(parent, label)
        self.tree.SetItemData(item, _Node(kind, path))
        placeholder = self.tree.AppendItem(item, "")
        self.tree.SetItemData(placeholder, _Node("placeholder", ""))
        return item

    def _append_note(self, parent, text):
        item = self.tree.AppendItem(parent, text)
        self.tree.SetItemData(item, _Node("empty", ""))
        return item

    def _child_by_norm(self, item, wanted):
        child, cookie = self.tree.GetFirstChild(item)
        while child and child.IsOk():
            node = self.tree.GetItemData(child)
            if node is not None and node.kind not in ("empty", "placeholder"):
                if _norm_path(node.path) == wanted:
                    return child
            child, cookie = self.tree.GetNextChild(item, cookie)
        return None

    def _first_child(self, item):
        child, _cookie = self.tree.GetFirstChild(item)
        if child and child.IsOk():
            node = self.tree.GetItemData(child)
            if node is not None and node.kind == "placeholder":
                return None
            return child
        return None

    def _child_labels(self, item):
        labels = []
        child, cookie = self.tree.GetFirstChild(item)
        while child and child.IsOk():
            node = self.tree.GetItemData(child)
            if node is None or node.kind != "placeholder":
                labels.append(self.tree.GetItemText(child))
            child, cookie = self.tree.GetNextChild(item, cookie)
        return labels

    def _on_expanding(self, event):
        self._load_children(event.GetItem())
        event.Skip()

    def _on_toggled(self, event):
        item = event.GetItem()
        sel = self.tree.GetSelection()
        if sel and item and sel == item:
            self._announce_item(item)
        event.Skip()

    def _on_activated(self, event):
        """Doppio clic: apre l'unità o la cartella, senza saltare al figlio."""
        wx.CallAfter(self._expand_selected)

    def _ensure_open(self, item):
        if item is None or not item.IsOk():
            return
        node = self.tree.GetItemData(item)
        if node is None or node.kind in ("empty", "placeholder"):
            return
        if not self.tree.IsExpanded(item):
            self.tree.Expand(item)

    def _expand_selected(self):
        item = self.tree.GetSelection()
        if item is None or not item.IsOk():
            return
        node = self.tree.GetItemData(item)
        if node is None or node.kind in ("empty", "placeholder"):
            return
        if not self.tree.IsExpanded(item):
            self.tree.Expand(item)
        self._apply_folder(item)
        self._announce_item(item)

    def _apply_folder(self, item):
        node = self.tree.GetItemData(item) if item and item.IsOk() else None
        if node is None or node.kind not in ("root", "dir", "drive"):
            return
        path = _THIS_PC if node.kind == "root" else node.path
        self._directory = path
        self._show_path()
        self._fill_for_node(node)

    def _search_query(self):
        try:
            return self.txt_search.GetValue().strip().casefold()
        except Exception:
            return ""

    def _set_list_caption(self, text):
        try:
            self.lbl_elements.SetLabel(text)
        except Exception:
            pass

    def _fill_for_node(self, node):
        if node is None or node.kind == "root":
            self._list_kind = "units"
            self._files_clipped = False
            self._fill(_drive_rows())
            self._set_list_caption(
                "Unità. La lettera iniziale porta al disco. Invio lo apre."
            )
            return
        if node.kind == "drive":
            rows, self._files_clipped = _folders_in(node.path)
            rows = self._filter_named(rows, "Nessuna cartella con questo nome.")
            self._list_kind = "folders"
            self._fill(rows)
            self._set_list_caption(
                "Cartelle. La lettera iniziale porta alla cartella. Invio la apre."
            )
            return
        self._list_kind = "files"
        self._fill_files(node.path)
        self._set_list_caption("File di questa cartella, i più recenti in cima:")

    def _fill_files(self, path):
        if self.lst is None:
            self._files_clipped = False
            return
        if path == _THIS_PC or not path or not os.path.isdir(path):
            rows = [_Row("empty", "Scegli un disco o una cartella.", "")]
            self._files_clipped = False
        else:
            rows, _count, self._files_clipped = _files_in(path, self._patterns())
            query = self._search_query()
            if query:
                rows = [
                    row for row in rows
                    if row.kind == "file" and query in row.label.casefold()
                ]
                if not rows:
                    rows = [_Row("empty", "Nessun file con questo nome.", "")]
        self._fill(rows)

    def _filter_named(self, rows, empty_label):
        query = self._search_query()
        if not query:
            return rows
        kept = [
            row for row in rows
            if row.kind != "empty" and query in row.label.casefold()
        ]
        if not kept:
            return [_Row("empty", empty_label, "")]
        return kept

    def _on_search(self, event=None):
        item = self.tree.GetSelection() if self.tree is not None else None
        if item and item.IsOk():
            self._apply_folder(item)
        else:
            self._fill_files(self._directory)
        if event is not None:
            event.Skip()

    def _file_count(self):
        return sum(1 for row in self._rows if row.kind == "file")

    def _folder_count(self):
        return sum(1 for row in self._rows if row.kind in ("dir", "drive"))

    def _type_phrase(self, name):
        name = str(name or "").strip() or "Tipo di file"
        return f"{name} casella combinata."

    def _tree_on_folder(self):
        if self.tree is None or wx.Window.FindFocus() is not self.tree:
            return False
        item = self.tree.GetSelection()
        node = self.tree.GetItemData(item) if item and item.IsOk() else None
        return node is not None and node.kind == "dir"

    def _refocus(self, win):
        try:
            if win is not None and win:
                win.SetFocus()
        except Exception:
            pass

    def _focus_units(self):
        self._sync_unit_list(self._directory)
        self._refocus(self.lst_units)

    def _current_unit(self):
        if self.lst_units is None:
            return None
        try:
            index = int(self.lst_units.GetSelection())
        except Exception:
            return None
        if index < 0 or index >= len(self._unit_rows):
            return None
        row = self._unit_rows[index]
        if row.kind != "drive" or not row.path:
            return None
        return row

    def _sync_unit_list(self, path):
        if self.lst_units is None:
            return
        drive = ""
        if path and path != _THIS_PC:
            try:
                drive, _tail = os.path.splitdrive(os.path.abspath(path))
            except Exception:
                drive = ""
        want = _norm_path(drive + "\\") if drive else ""
        self._filling_units = True
        try:
            if not self._unit_rows:
                self._unit_rows = _drive_rows()
                self.lst_units.Clear()
                for row in self._unit_rows:
                    self.lst_units.Append(row.label)
            index = 0
            for i, row in enumerate(self._unit_rows):
                if want and row.kind == "drive" and _norm_path(row.path) == want:
                    index = i
                    break
            if self._unit_rows:
                self.lst_units.SetSelection(index)
        finally:
            self._filling_units = False

    def _on_unit_sel(self, event):
        if self._filling_units:
            if event is not None:
                event.Skip()
            return
        row = self._current_unit()
        if row is not None:
            current = _norm_path(self._directory)
            opened = _norm_path(row.path)
            if current != opened and not current.startswith(opened):
                self._reveal(row.path)
        if event is not None:
            event.Skip()

    def _on_unit_activate(self, event=None):
        row = self._current_unit()
        if row is None:
            self._set_status("Nessuna unità da aprire.", speak=True)
            return
        self._reveal(row.path, announce=False)
        self._refocus(self.lst_units)
        self._set_status(
            f"{row.label}. Tab mostra le cartelle. Shift+Tab torna alle unità.",
            speak=True,
        )

    def _focus_drive(self):
        self._focus_units()

    def _open_type_list(self):
        if self.choice is None:
            return
        names = [self.choice.GetString(i) for i in range(self.choice.GetCount())]
        if not names:
            return
        try:
            index = int(self.choice.GetSelection())
        except Exception:
            index = 0
        dlg = _TypeListDialog(self, names, index)
        self._type_list_open = True
        try:
            ok = dlg.ShowModal() == wx.ID_OK
            pick = dlg.pick
        finally:
            self._type_list_open = False
            dlg.Destroy()
        if not ok or pick < 0 or pick >= len(names):
            return
        self.choice.SetSelection(pick)
        self._on_filter(None)
        if _own_voice_nav():
            say(self._type_phrase(names[pick]))

    def _push_history(self, path):
        if not path:
            return
        if 0 <= self._history_at < len(self._history) - 1:
            self._history = self._history[:self._history_at + 1]
        if self._history and _norm_path(self._history[-1]) == _norm_path(path):
            self._history_at = len(self._history) - 1
            return
        self._history.append(path)
        self._history_at = len(self._history) - 1

    def _go_back(self):
        if self._history_at <= 0:
            self._set_status("Non ci sono percorsi precedenti.", speak=True)
            return
        self._history_at -= 1
        self._reveal(self._history[self._history_at], speak_error=True, record=False)

    def _select_first_element(self):
        if self.lst is None or not self._rows:
            return
        try:
            self.lst.SetSelection(0)
        except Exception:
            return
        row = self._rows[0]
        if _own_voice_nav():
            say(row.label)

    def _cycle_type(self, delta):
        if self.choice is None:
            return
        try:
            count = int(self.choice.GetCount())
            index = int(self.choice.GetSelection())
        except Exception:
            return
        if count <= 0:
            return
        if index < 0:
            index = 0
        index = (index + int(delta)) % count
        self.choice.SetSelection(index)
        self._on_filter(None)
        if _own_voice_nav():
            say(self._type_phrase(self.choice.GetStringSelection()))

    def _on_tree_sel(self, event):
        try:
            item = event.GetItem()
            if not self._silent:
                self._apply_folder(item)
                self._announce_item(item)
        finally:
            event.Skip()

    def _announce_item(self, item):
        if item is None or not item.IsOk():
            return
        node = self.tree.GetItemData(item)
        label = self.tree.GetItemText(item) or "Cartella"
        if node is None or node.kind in ("empty", "placeholder"):
            phrase = label
            shown = label
        elif node.kind == "root":
            phrase = f"{label}. {self._folder_count()} unità."
            shown = "Questo PC"
        elif node.kind == "drive":
            phrase = f"{label}. {self._folder_count()} cartelle."
            shown = node.path or label
        else:
            phrase = f"{label}. {self._file_count()} file, i più recenti in cima."
            shown = node.path or label
        extra = ""
        if self._files_clipped:
            extra = f" Mostro i primi {_MAX_ROWS} file."
        self._set_status(f"{phrase}. {shown}.{extra}", speak=False)
        if self._silent or not _own_voice_nav():
            return
        now = time.time()
        if phrase == self._last_nav and (now - self._last_nav_at) < 0.25:
            return
        self._last_nav = phrase
        self._last_nav_at = now
        say(phrase)

    def _patterns(self):
        return ["*.*"]

    def _include_files(self):
        return True

    def _go_parent(self):
        item = self.tree.GetSelection() if self.tree is not None else None
        if item is None or not item.IsOk() or item == self._root:
            if self._root is not None:
                self.tree.SelectItem(self._root)
            self._set_status("Sei già su Questo PC.", speak=True)
            return
        parent = self.tree.GetItemParent(item)
        if parent is None or not parent.IsOk():
            self._set_status("Sei già su Questo PC.", speak=True)
            return
        self.tree.SelectItem(parent)
        self.tree.EnsureVisible(parent)

    def _on_go(self, event=None):
        typed = ""
        try:
            typed = self.txt_path.GetValue().strip().strip('"')
        except Exception:
            typed = ""
        if not typed or typed.casefold() == "questo pc":
            self._reveal(_THIS_PC)
            return
        self._reveal(typed)

    def _on_select(self, event):
        if not getattr(self, "_filling", False):
            row = self._current_row()
            if row is not None and row.kind == "file":
                self._set_typed_name(os.path.basename(row.path))
            elif row is not None and not getattr(self, "_save", False):
                self._set_typed_name("")
        if event is not None:
            event.Skip()

    def _set_typed_name(self, name):
        return

    def _on_dclick(self, event):
        self._activate_row()

    def _activate_row(self):
        row = self._current_row()
        if row is None or row.kind == "empty":
            self._set_status("Nessuna riga da aprire.", speak=True)
            return
        if row.kind in ("dir", "drive"):
            self._reveal(row.path)
            return
        if row.kind != "file":
            self._set_status("Nessun file da aprire.", speak=True)
            return
        self._accept_file_row(row)

    def _accept_file_row(self, row):
        return

    def _on_ok(self, event=None):
        return

    def _on_new_folder(self, event=None):
        if self._directory == _THIS_PC:
            self._set_status("Scegli prima un disco.", speak=True)
            return
        dlg = _AskNameDialog(self)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            name = dlg.value()
        finally:
            dlg.Destroy()
        if not name or any(ch in name for ch in '<>:"/\\|?*'):
            self._set_status("Nome non valido.", speak=True)
            return
        dest = os.path.join(self._directory, name)
        if os.path.exists(dest):
            self._set_status("Quel nome c'è già.", speak=True)
            return
        try:
            os.mkdir(dest)
        except OSError:
            self._set_status("Cartella non creata.", speak=True)
            return
        parent = self.tree.GetSelection()
        node = self.tree.GetItemData(parent) if parent and parent.IsOk() else None
        if node is not None:
            node.loaded = False
            self._load_children(parent)
            self.tree.Expand(parent)
        self._reveal(dest, speak_error=False)
        self._set_status(f"Cartella {name} creata.", speak=True)

    def _finish(self, path, paths=None):
        self._accepted = True
        self._result = path or ""
        self._results = list(paths or ([path] if path else []))
        try:
            if self.IsModal():
                self.EndModal(wx.ID_OK)
        except Exception:
            pass

    def GetPath(self):
        if not self._accepted:
            return ""
        return self._result

    def GetPaths(self):
        if not self._accepted:
            return []
        return list(self._results)

    def GetDirectory(self):
        if self._directory == _THIS_PC:
            return ""
        return self._directory

    def GetFilename(self):
        if not self._accepted:
            return ""
        return os.path.basename(self._result)


class RTADFileDialog(_PickerBase):
    def __init__(
        self,
        parent,
        message=wx.FileSelectorPromptStr,
        defaultDir="",
        defaultFile="",
        wildcard=wx.FileSelectorDefaultWildcardStr,
        style=wx.FD_DEFAULT_STYLE,
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        name=wx.FileDialogNameStr,
    ):
        self._style = int(style or 0)
        self._save = bool(self._style & wx.FD_SAVE)
        self._multiple = bool(self._style & wx.FD_MULTIPLE) and not self._save
        self._must_exist = bool(self._style & wx.FD_FILE_MUST_EXIST) or not self._save
        self._overwrite = bool(self._style & wx.FD_OVERWRITE_PROMPT)
        self._filters = with_standard_types(parse_wildcard(wildcard))
        self._filter_index = 0
        self._default_file = str(defaultFile or "")
        hint = _MULTI_HINT if self._multiple else _FILE_HINT
        title = str(message or ("Salva" if self._save else "Apri"))
        super().__init__(parent, title, hint)
        self.txt_name = None
        self.choice = None
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self._build_chrome(panel, vbox, "Cartelle")
        panel.SetSizer(vbox)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.GetSizer().Add(panel, 1, wx.EXPAND)
        start = safe_start_dir(defaultDir)
        self._go(start, speak_error=False)
        wx.CallAfter(self._focus_start)

    def _fields_before_buttons(self, panel, vbox):
        name_row = wx.BoxSizer(wx.HORIZONTAL)
        name_row.Add(wx.StaticText(panel, label="Nome file:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.txt_name = wx.TextCtrl(panel, value=self._default_file)
        self.txt_name.SetName("Nome file")
        name_row.Add(self.txt_name, 1, wx.EXPAND | wx.RIGHT, 6)
        self.choice = wx.Choice(panel, choices=[desc for desc, _pats in self._filters])
        self.choice.SetName("Tipo di file")
        self.choice.SetSelection(0)
        self.choice.Bind(wx.EVT_CHOICE, self._on_filter)
        self.choice.Bind(wx.EVT_SET_FOCUS, self._on_type_focus)
        type_row = wx.BoxSizer(wx.HORIZONTAL)
        type_row.Add(
            wx.StaticText(panel, label="Tipo di file:"),
            0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6,
        )
        type_row.Add(self.choice, 1, wx.EXPAND)
        vbox.Add(name_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        vbox.Add(type_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

    def _on_type_focus(self, event):
        if _own_voice_nav() and self.choice is not None:
            current = self.choice.GetStringSelection() or "Tipo di file"
            say(
                self._type_phrase(current)
                + " Freccia giù cambia. Alt+freccia giù apre l'elenco."
            )
        if event is not None:
            event.Skip()

    def _focus_start(self):
        self._focus_units()

    def _speak_start_field(self):
        if not _own_voice_nav():
            return
        try:
            if wx.Window.FindFocus() is not self.txt_name:
                return
            value = self.txt_name.GetValue().strip()
        except Exception:
            return
        say("Nome file. " + (value or "Vuoto.") + " Si incolla con Control+V.")

    def _list_style(self):
        if self._multiple:
            return wx.LB_EXTENDED | wx.LB_NEEDED_SB
        return wx.LB_SINGLE | wx.LB_NEEDED_SB

    def _ok_label(self):
        return "Pulsante &Salva" if self._save else "Pulsante &Apri"

    def _patterns(self):
        try:
            return self._filters[self._filter_index][1]
        except Exception:
            return ["*.*"]

    def _include_files(self):
        return True

    def _focus_tree(self):
        self._focus_units()

    def _set_typed_name(self, name):
        try:
            self.txt_name.ChangeValue(name)
        except Exception:
            pass

    def _on_filter(self, event):
        try:
            self._filter_index = int(self.choice.GetSelection())
        except Exception:
            self._filter_index = 0
        if self._filter_index < 0:
            self._filter_index = 0
        self._fill_files(self._directory)
        current = ""
        try:
            current = self.choice.GetStringSelection()
        except Exception:
            current = ""
        self._set_status(
            f"{self._type_phrase(current)} {self._file_count()} file.",
            speak=False,
        )
        if event is not None:
            event.Skip()

    def _typed_name(self):
        try:
            return self.txt_name.GetValue().strip().strip('"')
        except Exception:
            return ""

    def _accept_file_row(self, row):
        if self._multiple:
            self._accept_many()
            return
        self._accept_named(os.path.basename(row.path))

    def _on_ok(self, event=None):
        if self._multiple:
            self._accept_many()
            return
        self._accept_named(self._typed_name())

    def _find_named_dir(self, name):
        want = str(name or "").casefold()
        if not want or self.tree is None:
            return ""
        item = self.tree.GetSelection()
        if item is None or not item.IsOk():
            return ""
        self._load_children(item)
        child, cookie = self.tree.GetFirstChild(item)
        while child and child.IsOk():
            node = self.tree.GetItemData(child)
            if node is not None and node.kind == "dir":
                if os.path.basename(node.path).casefold() == want:
                    return node.path
            child, cookie = self.tree.GetNextChild(item, cookie)
        return ""

    def _accept_many(self):
        paths = []
        for index in self._selected_indexes():
            if index < 0 or index >= len(self._rows):
                continue
            row = self._rows[index]
            if row.kind == "file":
                paths.append(row.path)
        if not paths:
            self._set_status("Scegli almeno un file.", speak=True)
            return
        self._finish(paths[0], paths)

    def _accept_named(self, typed):
        typed = str(typed or "").strip().strip('"')
        if typed and (os.path.isabs(typed) or typed.startswith("\\\\")):
            if os.path.isdir(typed):
                self._go(typed)
                return
            folder, name = os.path.split(typed)
            if folder and os.path.isdir(folder) and name:
                if os.path.normcase(folder) != os.path.normcase(self._directory):
                    self._go(folder, speak_error=False)
                typed = name
        folder_hit = self._find_named_dir(typed)
        if folder_hit:
            self._go(folder_hit)
            return
        if not typed:
            row = self._current_row()
            if row is not None and row.kind == "file":
                typed = os.path.basename(row.path)
        if self._save:
            typed = ensure_extension(typed, self._patterns())
        if not typed:
            self._set_status("Scrivi il nome del file.", speak=True)
            return
        path = typed if os.path.isabs(typed) else os.path.join(self._directory, typed)
        path = os.path.abspath(path)
        if self._save:
            if os.path.isdir(path):
                self._go(path)
                return
            if os.path.exists(path) and self._overwrite:
                if not self._ask_overwrite(path):
                    return
            self._finish(path, [path])
            return
        match = self._find_file(typed)
        if match:
            path = match
        if self._must_exist and not os.path.isfile(path):
            self._set_status("File non trovato.", speak=True)
            return
        self._finish(path, [path])

    def _find_file(self, name):
        want = str(name or "").casefold()
        for row in self._rows:
            if row.kind == "file" and os.path.basename(row.path).casefold() == want:
                return row.path
        return ""

    def _ask_overwrite(self, path):
        name = os.path.basename(path)
        dlg = wx.MessageDialog(
            self,
            f"Il file {name} esiste già. Invio su Sì, o un clic, lo sostituisce. "
            "Invio su No, o un clic, torna al nome.",
            "Sostituire il file?",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        try:
            return dlg.ShowModal() == wx.ID_YES
        finally:
            dlg.Destroy()

    def GetFilterIndex(self):
        return int(self._filter_index)


class RTADDirDialog(_PickerBase):
    def __init__(
        self,
        parent,
        message=wx.DirSelectorPromptStr,
        defaultPath="",
        style=wx.DD_DEFAULT_STYLE,
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        name=wx.DirDialogNameStr,
    ):
        self._style = int(style or 0)
        self._must_exist = bool(self._style & wx.DD_DIR_MUST_EXIST) or True
        title = str(message or "Scegli la cartella")
        super().__init__(parent, title, _DIR_HINT)
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self._build_chrome(panel, vbox, "Cartelle")
        panel.SetSizer(vbox)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(outer)
        self._go(safe_start_dir(defaultPath), speak_error=False)
        wx.CallAfter(self._focus_start)

    def _fields_before_buttons(self, panel, vbox):
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(panel, label="Cartella:"),
            0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6,
        )
        self.txt_path = wx.TextCtrl(panel)
        self.txt_path.SetName("Cartella")
        row.Add(self.txt_path, 1, wx.EXPAND)
        vbox.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

    def _ok_label(self):
        return "Pulsante &Seleziona"

    def _include_files(self):
        return True

    def _focus_start(self):
        self._focus_units()

    def _speak_start_field(self):
        if not _own_voice_nav():
            return
        try:
            if wx.Window.FindFocus() is not self.txt_path:
                return
            value = self.txt_path.GetValue().strip()
        except Exception:
            return
        say("Cartella. " + (value or "Vuota.") + " Si incolla con Control+V.")

    def _accept_file_row(self, row):
        name = os.path.basename(row.path) if row is not None else ""
        self._set_status(
            f"File {name}. Per la cartella, Invio sul pulsante Seleziona cartella, o un clic.",
            speak=True,
        )

    def _on_ok(self, event=None):
        item = self.tree.GetSelection() if self.tree is not None else None
        node = self.tree.GetItemData(item) if item and item.IsOk() else None
        if (
            node is None
            or node.kind not in ("dir", "drive")
            or not node.path
            or node.path == _THIS_PC
        ):
            self._set_status("Scegli un disco o una cartella.", speak=True)
            return
        if self._must_exist and not os.path.isdir(node.path):
            self._set_status("Cartella non raggiungibile.", speak=True)
            return
        self._finish(node.path, [node.path])
