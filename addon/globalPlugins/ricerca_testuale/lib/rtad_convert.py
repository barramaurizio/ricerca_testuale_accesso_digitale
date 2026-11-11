# -*- coding: utf-8 -*-
"""Converte audio e video in un altro formato.

Un file nuovo, accanto. Quello di partenza non si tocca.
Stessa finestra nella Standalone e nell'Add-on. A schermo e a voce.
Invio e il clic sullo stesso pulsante. Sull'elenco, Invio e il doppio clic
dicono la riga. Un clic solo seleziona la riga.
"""

from __future__ import annotations

import logging
import os
import threading

log = logging.getLogger("rtad.convert")

MSG_EMPTY = "Nessun file in elenco."
MSG_NO_DONE = "Nessun risultato ancora."
MSG_SELECT = "Seleziona una riga."
MSG_FORMAT = "Scegli un formato."
MSG_FFMPEG = "Per questo formato serve ffmpeg."
MSG_FAIL = "Non sono riuscito a creare il file. Il file di partenza resta com'è."
MSG_AUDIO_VIDEO = (
    "Un audio non diventa un video. "
    "Scegli un formato audio: MP3, M4A, WAV, FLAC, OGG, Opus o WMA."
)
MSG_NO_AUDIO = "non ha l'audio."

_FORMATS = (
    ("MP3", ".mp3", "audio"),
    ("M4A", ".m4a", "audio"),
    ("WAV", ".wav", "audio"),
    ("FLAC", ".flac", "audio"),
    ("OGG", ".ogg", "audio"),
    ("Opus", ".opus", "audio"),
    ("WMA", ".wma", "audio"),
    ("MP4", ".mp4", "video"),
    ("MKV", ".mkv", "video"),
)
_INTRO = (
    "Converti audio e video. "
    "Invio sul pulsante Aggiungi file, o un clic, mette i file in elenco. "
    "Invio sul pulsante Aggiungi cartella, o un clic, mette i file di quella cartella. "
    "Le cartelle che stanno dentro non si aprono. "
    "Invio o doppio clic su una riga dice quel file. "
    "Un clic solo seleziona la riga. "
    "Nell'elenco Formato, freccia su e freccia giù scelgono. "
    "Invio sul pulsante Converti la riga, o un clic, scrive il file selezionato "
    "nel formato scelto. "
    "Invio sul pulsante Converti tutti, o un clic, scrive ogni riga. "
    "Da un video a un formato audio si tiene solo l'audio. "
    "Un audio non diventa un video. "
    "Il file di partenza resta com'è. "
    "Il file nuovo sta nella stessa cartella, con la nuova estensione. "
    "Se il nome c'è già, si chiama nome-2. "
    "I file creati restano nell'elenco Fatti. "
    "Invio o doppio clic su un fatto lo rimette nell'elenco di lavoro. "
    "Dall'elenco, Alt e la lettera del pulsante fa la stessa cosa: "
    "A Aggiungi file, K Aggiungi cartella, M Rimuovi, C Converti la riga, T Converti tutti, F Ferma. "
    "Invio sul pulsante Ferma, o un clic, ferma il lavoro. "
    "Esc chiude."
)
_ALT = {
    "A": "add",
    "K": "folder",
    "M": "remove",
    "C": "one",
    "T": "all",
    "F": "stop",
}
_WILDCARD = (
    "Audio e video|"
    "*.mp3;*.m4a;*.m4b;*.aac;*.flac;*.ogg;*.opus;*.wav;*.wma;*.aif;*.aiff;*.mka;"
    "*.mp4;*.m4v;*.mkv;*.avi;*.mov;*.wmv;*.webm;*.flv;*.mts;*.m2ts;*.mpg;*.mpeg;*.3gp|"
    "Tutti i file|*.*"
)


def _unique_beside(folder: str, stem: str, ext: str, source: str) -> str:
    source_key = os.path.normcase(os.path.abspath(source))
    number = 1
    while True:
        name = stem + ext if number == 1 else f"{stem}-{number}{ext}"
        dest = os.path.join(folder, name)
        dest_key = os.path.normcase(os.path.abspath(dest))
        if dest_key != source_key and not os.path.exists(dest):
            return dest
        number += 1


def convert_file(piece, ext: str, kind: str, cancel) -> tuple[bool, str, str]:
    """Scrive il file nuovo. Ritorna ok, frase, percorso."""
    from rtad_clip import (
        _audio_out_args,
        _ffmpeg_exe,
        _run,
        speak_duration,
    )

    name = os.path.basename(piece.path)
    if kind == "video" and not piece.has_video:
        return False, MSG_AUDIO_VIDEO, ""
    if kind == "audio" and not piece.has_audio:
        return False, f"{name} {MSG_NO_AUDIO}", ""
    ff = _ffmpeg_exe()
    if not ff:
        return False, MSG_FFMPEG, ""
    folder = os.path.dirname(os.path.abspath(piece.path)) or os.getcwd()
    stem = os.path.splitext(name)[0]
    dest = _unique_beside(folder, stem, ext, piece.path)
    only_audio = kind == "audio" and piece.has_video
    if kind == "audio":
        args = [ff, "-y", "-i", piece.path, "-vn", *_audio_out_args(ext), dest]
    else:
        args = [
            ff, "-y", "-i", piece.path,
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=25,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        ]
        if ext == ".mp4":
            args += ["-movflags", "+faststart"]
        if piece.has_audio:
            args += ["-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2"]
        else:
            args += ["-an"]
        args.append(dest)
    ok, _err = _run(args, cancel)
    if cancel is not None and cancel.is_set():
        return False, "Fermato.", dest if os.path.isfile(dest) else ""
    if not ok or not os.path.isfile(dest) or os.path.getsize(dest) <= 0:
        return False, MSG_FAIL, ""
    duration = speak_duration(piece.duration)
    extra = ", solo l'audio" if only_audio else ""
    phrase = (
        f"Creato {os.path.basename(dest)}, {duration}{extra}, "
        "nella stessa cartella."
    )
    return True, phrase, dest


def open_dialog(parent, speaker, paths=None):
    import wx
    dialog = ConvertDialog(parent, speaker, paths or [])
    dialog.ShowModal()
    dialog.close_work()
    dialog.Destroy()


class ConvertDialog:
    """La classe vera è sotto: wx va importato a finestra aperta."""


def _install_dialog():
    import wx

    class ConvertDialog(wx.Dialog):
        def __init__(self, parent, speaker, paths):
            super().__init__(
                parent,
                title="Converti audio e video",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._speaker = speaker or (lambda _text: None)
            self._rows = []
            self._done = []
            self._open = True
            self._busy = False
            self._cancel = threading.Event()
            self._initial = list(paths or [])

            vbox = wx.BoxSizer(wx.VERTICAL)
            intro = wx.StaticText(self, label=_INTRO)
            intro.Wrap(740)
            vbox.Add(intro, 0, wx.ALL | wx.EXPAND, 8)

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "File da convertire. "
                        "Invio o doppio clic dice la riga. "
                        "Un clic solo seleziona la riga."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )
            self.lst = wx.ListBox(self, style=wx.LB_SINGLE)
            self.lst.SetMinSize((740, 140))
            vbox.Add(self.lst, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.lst.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._say_row())

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Formato. Freccia su e freccia giù scelgono. "
                        "Vale per Converti la riga e per Converti tutti."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )
            self.lst_fmt = wx.ListBox(self, style=wx.LB_SINGLE)
            for label, _ext, _kind in _FORMATS:
                self.lst_fmt.Append(label)
            self.lst_fmt.SetSelection(0)
            self.lst_fmt.SetMinSize((740, 120))
            vbox.Add(self.lst_fmt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

            row = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_add = wx.Button(self, label="&Aggiungi file…")
            self.btn_folder = wx.Button(self, label="Aggiungi cartella (&K)")
            self.btn_remove = wx.Button(self, label="Ri&muovi")
            self.btn_one = wx.Button(self, label="&Converti la riga")
            self.btn_all = wx.Button(self, label="Converti &tutti")
            self.btn_stop = wx.Button(self, label="&Ferma")
            self.btn_close = wx.Button(self, wx.ID_CANCEL, "Chiudi")
            for btn in (
                self.btn_add, self.btn_folder, self.btn_remove, self.btn_one,
                self.btn_all, self.btn_stop, self.btn_close,
            ):
                row.Add(btn, 0, wx.RIGHT, 6)
            vbox.Add(row, 0, wx.ALL, 8)

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Fatti. Invio o doppio clic rimette il file nell'elenco di lavoro. "
                        "Un clic solo seleziona la riga."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT, 8,
            )
            self.lst_done = wx.ListBox(self, style=wx.LB_SINGLE)
            self.lst_done.SetMinSize((740, 80))
            vbox.Add(self.lst_done, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.lst_done.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._on_use_done())

            vbox.Add(wx.StaticText(self, label="Stato"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.txt_status = wx.TextCtrl(
                self, value=MSG_EMPTY, style=wx.TE_READONLY | wx.TE_MULTILINE,
            )
            self.txt_status.SetMinSize((740, 72))
            vbox.Add(self.txt_status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self._status_bar = wx.StatusBar(self)
            self._status_bar.SetMinSize((740, 28))
            self._status_bar.SetStatusText(MSG_EMPTY)
            vbox.Add(self._status_bar, 0, wx.EXPAND | wx.ALL, 4)

            self.btn_add.Bind(wx.EVT_BUTTON, self._on_add)
            self.btn_folder.Bind(wx.EVT_BUTTON, self._on_add_folder)
            self.btn_remove.Bind(wx.EVT_BUTTON, self._on_remove)
            self.btn_one.Bind(wx.EVT_BUTTON, lambda e: self._start(False))
            self.btn_all.Bind(wx.EVT_BUTTON, lambda e: self._start(True))
            self.btn_stop.Bind(wx.EVT_BUTTON, self._on_stop)
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

        def close_work(self):
            self._open = False
            self._cancel.set()

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

        def _selected(self) -> int:
            if not self._rows:
                return -1
            index = self.lst.GetSelection()
            if index < 0 or index >= len(self._rows):
                return -1
            return index

        def _format(self):
            index = self.lst_fmt.GetSelection()
            if index < 0 or index >= len(_FORMATS):
                return None
            return _FORMATS[index]

        def _refresh(self, select: int):
            self.lst.Clear()
            if not self._rows:
                self.lst.Append(MSG_EMPTY)
                self.lst.SetSelection(0)
                return
            for piece in self._rows:
                self.lst.Append(self._row_label(piece))
            select = max(0, min(select, len(self._rows) - 1))
            self.lst.SetSelection(select)

        def _row_label(self, piece) -> str:
            from rtad_clip import speak_duration
            kind = "video" if piece.has_video else "audio"
            return (
                f"{os.path.basename(piece.path)}, {kind}, "
                f"{speak_duration(piece.duration)}"
            )

        def _refresh_done(self):
            self.lst_done.Clear()
            if not self._done:
                self.lst_done.Append(MSG_NO_DONE)
                self.lst_done.SetSelection(0)
                return
            for label, _path in self._done:
                self.lst_done.Append(label)
            self.lst_done.SetSelection(len(self._done) - 1)

        def _load_initial(self):
            paths = [p for p in self._initial if p]
            self._initial = []
            if paths:
                self._ingest(paths)

        def _on_add(self, _event=None):
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
            from rtad_clip import _AUDIO_EXTS, _VIDEO_EXTS, _files_in_folder
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

        def _ingest(self, paths):
            from rtad_clip import load_piece
            added = []
            skipped = []
            was_empty = not self._rows
            for path in paths:
                piece, err = load_piece(path)
                if piece is None:
                    skipped.append(err or os.path.basename(path))
                else:
                    added.append(piece)
            if added:
                self._rows.extend(added)
                self._refresh(len(self._rows) - len(added))
                if was_empty:
                    self.lst_fmt.SetSelection(7 if added[0].has_video else 0)
            if len(added) == 1 and not skipped:
                label, _ext, _kind = _FORMATS[self.lst_fmt.GetSelection()]
                self._say(
                    f"Aggiunto {self._row_label(added[0])}. "
                    f"Formato {label}."
                )
                return
            if added and skipped:
                self._say(
                    f"Aggiunti {len(added)} su {len(added) + len(skipped)}. "
                    f"Non entrati: {', '.join(skipped)}."
                )
                return
            if added:
                self._say(f"Aggiunti {len(added)} file.")
                return
            if skipped:
                self._say("Nessun file. Non entrati: " + ", ".join(skipped) + ".")
                return
            self._say(MSG_EMPTY)

        def _on_remove(self, _event=None):
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

        def _say_row(self):
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            chosen = self._format()
            label = chosen[0] if chosen else "non scelto"
            self._say(f"{self._row_label(self._rows[index])}. Formato {label}.")

        def _on_use_done(self):
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

        def _on_stop(self, _event=None):
            if not self._busy:
                self._say("Nessun lavoro in corso.")
                return
            self._cancel.set()
            self._say("Fermo il lavoro.")

        def _start(self, all_rows: bool):
            if self._busy:
                self._say("Un lavoro è già in corso. Invio sul pulsante Ferma, o un clic, lo ferma.")
                return
            if not self._rows:
                self._say(MSG_EMPTY)
                return
            chosen = self._format()
            if chosen is None:
                self._say(MSG_FORMAT)
                return
            if all_rows:
                pieces = list(self._rows)
            else:
                index = self._selected()
                if index < 0:
                    self._say(MSG_SELECT)
                    return
                pieces = [self._rows[index]]
            label, ext, kind = chosen
            self._busy = True
            self._cancel = threading.Event()
            self._say(f"Converto in {label}. Attendere prego.")
            threading.Thread(
                target=self._work,
                args=(pieces, ext, kind, self._cancel),
                daemon=True,
            ).start()

        def _work(self, pieces, ext, kind, cancel):
            import wx
            made = []
            failed = []
            last = ""
            for piece in pieces:
                if cancel.is_set():
                    break
                ok, phrase, dest = convert_file(piece, ext, kind, cancel)
                last = phrase
                if ok and dest:
                    made.append((phrase, dest))
                else:
                    failed.append(phrase or os.path.basename(piece.path))
                    if cancel.is_set():
                        break
            wx.CallAfter(self._finish_ui, made, failed, last, cancel.is_set())

        def _finish_ui(self, made, failed, last, stopped: bool):
            self._busy = False
            for phrase, dest in made:
                self._done.append((phrase, dest))
            self._refresh_done()
            if stopped and not made:
                self._say("Fermato. Nessun file scritto.")
                return
            if len(made) == 1 and not failed and not stopped:
                self._say(f"{last} In Fatti: {last}")
                return
            parts = []
            if made:
                parts.append(f"Creati {len(made)}.")
            if failed:
                parts.append("Non riusciti: " + "; ".join(failed) + ".")
            if stopped:
                parts.append("Fermato.")
            text = " ".join(parts) or last or MSG_FAIL
            if made:
                text += " I file creati sono in Fatti."
            self._say(text)

        def _on_char(self, event):
            key = event.GetKeyCode()
            if (
                event.AltDown()
                and not event.ControlDown()
                and not event.ShiftDown()
                and key not in (wx.WXK_F4, wx.WXK_TAB)
            ):
                letter = ""
                if ord("A") <= key <= ord("Z") or ord("a") <= key <= ord("z"):
                    letter = chr(key).upper()
                name = _ALT.get(letter)
                if name:
                    self._alt_do(name)
                    return
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                focused = self.FindFocus()
                if focused is self.lst:
                    self._say_row()
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
            elif name == "remove":
                self._on_remove()
            elif name == "one":
                self._start(False)
            elif name == "all":
                self._start(True)
            elif name == "stop":
                self._on_stop()

    globals()["ConvertDialog"] = ConvertDialog


_install_dialog()
