# -*- coding: utf-8 -*-
"""Confronto tra più file: solo le parti che non stanno in tutti.

Senza chiave. Gemini, se c'è, riceve questo stesso testo, non i file interi.
"""

from __future__ import annotations

import os
import re
import threading

import wx

EMPTY_ROW = "Nessun file nel confronto."
NEED_TWO = "Servono almeno due file."
WORKING = "Confronto in corso. Attendere."
BEFORE_ASK = "Prima fai Confronta."
MAX_FILES = 12
MAX_PARTS = 80

INSTRUCTIONS = (
    "Aggiungi almeno due file, fino a 12. "
    "Alt+A aggiunge, anche se sei sull'elenco. "
    "Alt+L toglie il file sotto il cursore, anche mentre ne aggiungi altri. "
    "Nell'elenco: Shift+freccia giù prende un gruppo, Control+freccia salta, "
    "Control+Spazio aggiunge o toglie un file, Alt+C cambia cartella. "
    "Sotto, i file già nel confronto: Alt+L ne toglie uno prima di Invio. "
    "Confronta mostra solo le parti diverse, a schermo e a voce. "
    "Chiedi a Gemini spiega quelle differenze. "
    "Senza la chiave il confronto resta."
)

PICK_HELP = (
    "I più recenti sono in cima. "
    "Shift+freccia giù prende un gruppo di fila. "
    "Control+freccia salta, e quelli già presi restano. "
    "Poi di nuovo Shift+freccia giù: un altro gruppo di fila, "
    "senza perdere i primi. "
    "Control+Spazio aggiunge o toglie un file solo. "
    "Il numero che senti è il totale. Invio li aggiunge al confronto. "
    "Sotto, i file già nel confronto: Alt+L ne toglie uno prima di Invio. "
    "Alt+C cambia cartella."
)


_ENVELOPE_MARK = "docusign envelope id:"


def _take_envelope(flat: str, start: int) -> tuple[str, int] | None:
    """Un codice busta DocuSign: 32 cifre esadecimali, spazi e trattini inclusi."""
    key = _ENVELOPE_MARK
    if flat[start : start + len(key)].lower() != key:
        return None
    k = start + len(key)
    hexes = []
    end = k
    while end < len(flat) and len(hexes) < 32:
        c = flat[end]
        if c in " \t-":
            end += 1
            continue
        if c in "0123456789ABCDEFabcdef":
            hexes.append(c.upper())
            end += 1
            continue
        break
    if len(hexes) < 32:
        return None
    h = "".join(hexes)
    shown = (
        "Docusign Envelope ID: "
        + f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    )
    return shown, end


def _without_envelopes(flat: str) -> tuple[str, list[str]]:
    ids = []
    pieces = []
    i = 0
    lower = flat.lower()
    while True:
        j = lower.find(_ENVELOPE_MARK, i)
        if j < 0:
            pieces.append(flat[i:])
            break
        found = _take_envelope(flat, j)
        if not found:
            pieces.append(flat[i : j + len(_ENVELOPE_MARK)])
            i = j + len(_ENVELOPE_MARK)
            continue
        shown, end = found
        if shown not in ids:
            ids.append(shown)
        pieces.append(flat[i:j])
        pieces.append(" ")
        i = end
    return "".join(pieces), ids


def _clauses(flat: str) -> list[str]:
    """Frasi, non righe: l’a capo del lettore non è una differenza."""
    text = flat.replace("S.p.A.", "S\x00p\x00A\x00").replace("S.r.l.", "S\x00r\x00l\x00")
    text = re.sub(r"(?<=\d)\.(?=\d)", "\x00", text)
    chunks = re.split(r"(?<=[.;!?])\s+", text)
    out = []
    for chunk in chunks:
        piece = chunk.replace("\x00", ".").strip(" -")
        piece = re.sub(r"^\d{1,2}\s+(?=\d+\))", "", piece)
        piece = " ".join(piece.split())
        if piece:
            out.append(piece)
    return out


def _lines_of(text: str) -> list[str]:
    flat = " ".join((text or "").split())
    if not flat:
        return []
    body, ids = _without_envelopes(flat)
    return ids + _clauses(body)


_FACT_KEYS = ("Tipo", "Dimensione", "Ultima modifica", "Durata")


def file_facts(path: str) -> dict[str, str]:
    """Tipo, dimensione, data. Durata solo per un audio o un video."""
    facts: dict[str, str] = {}
    name = os.path.basename(path or "")
    try:
        import rtad_chat

        facts["Tipo"] = rtad_chat.attach_type_label(name)
        st = os.stat(path)
        facts["Dimensione"] = rtad_chat._size_it(int(st.st_size or 0))
        facts["Ultima modifica"] = rtad_chat._mtime_it(float(st.st_mtime or 0))
    except Exception:
        if name:
            facts["Tipo"] = name
    try:
        import rtad_media

        if rtad_media.is_media_path(path):
            info = rtad_media.get_media_tech_info(path) or {}
            duration = (info.get("duration_label") or "").strip()
            if duration:
                facts["Durata"] = duration
    except Exception:
        pass
    return facts


def _fact_lines(all_facts: list[dict]) -> list[list[str]]:
    """Solo i valori che non stanno in tutti i file."""
    any_duration = any((item.get("Durata") or "").strip() for item in all_facts)
    rows = []
    for facts in all_facts:
        lines = []
        for key in _FACT_KEYS:
            if key == "Durata" and not any_duration:
                continue
            values = []
            for other in all_facts:
                value = (other.get(key) or "").strip()
                if key == "Durata" and not value:
                    value = "non disponibile"
                values.append(value)
            if len(set(values)) <= 1:
                continue
            own = (facts.get(key) or "").strip()
            if key == "Durata" and not own:
                own = "non disponibile"
            if own:
                lines.append(f"{key}: {own}.")
        rows.append(lines)
    return rows


def compare_named_texts(named: list) -> tuple[str, str]:
    """Ritorna (frase da dire, testo completo). La frase è la prima riga."""
    n = len(named)
    if n < 2:
        return NEED_TWO, NEED_TWO

    parsed = []
    for item in named:
        label = ((item[0] if item else "") or "File").strip() or "File"
        text = item[1] if len(item) > 1 else ""
        facts = item[2] if len(item) > 2 and isinstance(item[2], dict) else {}
        parsed.append((label, _lines_of(text), facts))

    fact_rows = _fact_lines([facts for _label, _lines, facts in parsed])
    readable = [lines for _label, lines, _facts in parsed if lines]
    common = set()
    if len(readable) >= 2:
        counts: dict[str, int] = {}
        for lines in readable:
            for line in set(lines):
                counts[line] = counts.get(line, 0) + 1
        common = {line for line, c in counts.items() if c == len(readable)}

    blocks = []
    files_with_diff = 0
    hidden = 0
    for index, (label, lines, _facts) in enumerate(parsed):
        facts = fact_rows[index] if index < len(fact_rows) else []
        if not lines:
            parts = list(facts)
            parts.append("Nessun testo letto.")
            blocks.append(label + "\n" + "\n".join(parts))
            files_with_diff += 1
            continue
        shown = []
        seen = set()
        extra = 0
        if len(readable) >= 2:
            for line in lines:
                if line in common or line in seen:
                    continue
                seen.add(line)
                if len(shown) < MAX_PARTS:
                    shown.append(line)
                else:
                    extra += 1
        else:
            shown = []
        if not shown and not facts:
            blocks.append(f"{label}\nNessuna parte diversa.")
            continue
        files_with_diff += 1
        hidden += extra
        parts = list(facts) + shown
        body = "\n".join(parts)
        if extra:
            body += f"\nAltre {extra} parti non mostrate."
        blocks.append(f"{label}\n{body}")

    if files_with_diff == 0:
        summary = f"Confronto di {n} file. I testi coincidono."
        return summary, summary

    summary = f"Confronto di {n} file. Parti diverse in {files_with_diff} file."
    if hidden:
        summary += f" Alcune parti non sono in elenco: {hidden}."
    report = summary + "\n\n" + "\n\n".join(blocks)
    return summary, report


def _display_name(path: str, paths: list[str]) -> str:
    base = os.path.basename(path) or path
    same = [p for p in paths if os.path.basename(p) == base]
    if len(same) < 2:
        return base
    parent = os.path.basename(os.path.dirname(path))
    return f"{base} — {parent}" if parent else base


class CompareFrame(wx.Frame):
    """Finestra: elenco file, differenze, Gemini sulle differenze."""

    def __init__(
        self, speak, extract_text, ask_gemini, initial_path="", config_dir=""
    ):
        super().__init__(
            None,
            title="Confronta file",
            size=(760, 640),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self._speak = speak
        self._extract = extract_text
        self._ask = ask_gemini
        self._config_dir = config_dir or ""
        self._paths: list[str] = []
        self._report = ""
        self._busy = False

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.lbl_help = wx.StaticText(panel, label=INSTRUCTIONS)
        vbox.Add(self.lbl_help, 0, wx.ALL | wx.EXPAND, 8)

        vbox.Add(wx.StaticText(panel, label="File"), 0, wx.LEFT | wx.RIGHT, 8)
        self.lst = wx.ListBox(panel, style=wx.LB_SINGLE)
        try:
            self.lst.SetName("File del confronto")
        except Exception:
            pass
        self.lst.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        vbox.Add(self.lst, 0, wx.EXPAND | wx.ALL, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_add = wx.Button(panel, label="&Aggiungi file…")
        self.btn_remove = wx.Button(panel, label="Tog&li")
        self.btn_run = wx.Button(panel, label="&Confronta")
        self.btn_ask = wx.Button(panel, label="Chiedi a &Gemini")
        for btn, handler in (
            (self.btn_add, self.on_add),
            (self.btn_remove, self.on_remove),
            (self.btn_run, self.on_run),
            (self.btn_ask, self.on_ask),
        ):
            btn.Bind(wx.EVT_BUTTON, handler)
            row.Add(btn, 0, wx.RIGHT, 6)
        vbox.Add(row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.lbl_status = wx.StaticText(panel, label=INSTRUCTIONS)
        try:
            self.lbl_status.SetName("Esito")
        except Exception:
            pass
        vbox.Add(self.lbl_status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        vbox.Add(wx.StaticText(panel, label="Risultato"), 0, wx.LEFT | wx.RIGHT, 8)
        self.txt = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        try:
            self.txt.SetName("Risultato del confronto")
        except Exception:
            pass
        vbox.Add(self.txt, 1, wx.EXPAND | wx.ALL, 8)

        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_copy = wx.Button(panel, label="&Copia")
        self.btn_save = wx.Button(panel, label="&Salva testo…")
        self.btn_close = wx.Button(panel, label="&Chiudi")
        self.btn_copy.Bind(wx.EVT_BUTTON, self.on_copy)
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        self.btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        row2.Add(self.btn_copy, 0, wx.RIGHT, 6)
        row2.Add(self.btn_save, 0, wx.RIGHT, 6)
        row2.Add(self.btn_close, 0)
        vbox.Add(row2, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(vbox)
        self._save_dir = ""
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._show_paths()
        start = (initial_path or "").strip()
        if start and os.path.isfile(start):
            self._paths.append(start)
            self._show_paths()
            self._status(
                f"File nel confronto: {os.path.basename(start)}. {INSTRUCTIONS}"
            )
        else:
            self._status(INSTRUCTIONS)
        self.Show()
        self.Raise()
        wx.CallAfter(self.btn_add.SetFocus)

    def _say(self, text: str) -> None:
        try:
            self._speak(text)
        except Exception:
            pass

    def _status(self, text: str, speak: bool = True) -> None:
        self.lbl_status.SetLabel(text)
        self.lbl_status.Wrap(680)
        if speak:
            self._say(text)

    def _row_label(self, path: str) -> str:
        name = _display_name(path, self._paths)
        try:
            import rtad_chat

            st = os.stat(path)
            return rtad_chat.attach_row_label(name, st.st_mtime, st.st_size)
        except Exception:
            return name

    def _show_paths(self, prefer=None) -> None:
        self.lst.Clear()
        if not self._paths:
            self.lst.Append(EMPTY_ROW)
            self.lst.SetSelection(0)
            return
        for path in self._paths:
            self.lst.Append(self._row_label(path))
        if prefer is None:
            prefer = len(self._paths) - 1
        self.lst.SetSelection(max(0, min(int(prefer), len(self._paths) - 1)))

    def _on_char_hook(self, event):
        if (
            event.AltDown()
            and not event.ControlDown()
            and not event.ShiftDown()
        ):
            key = event.GetKeyCode()
            if key in (ord("A"), ord("a")):
                self.on_add()
                return
            if key in (ord("L"), ord("l")):
                self.on_remove()
                return
        event.Skip()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        for btn in (self.btn_add, self.btn_remove, self.btn_run, self.btn_ask):
            btn.Enable(not busy)

    def on_add(self, _event=None):
        if self._busy:
            return
        before = list(self._paths)
        picked = self._pick_files()
        if picked is None:
            self._status("Nessun file aggiunto.")
            return
        chosen, kept_after = picked
        self._paths = list(kept_after or [])
        added = []
        skipped = []
        extra = False
        known = {os.path.normcase(os.path.abspath(p)) for p in self._paths}
        for path in chosen:
            if len(self._paths) >= MAX_FILES:
                extra = True
                break
            key = os.path.normcase(os.path.abspath(path))
            if key in known:
                skipped.append(os.path.basename(path))
                continue
            known.add(key)
            self._paths.append(path)
            added.append(os.path.basename(path))
        before_keys = {
            os.path.normcase(os.path.abspath(path)) for path in before
        }
        after_keys = {
            os.path.normcase(os.path.abspath(path)) for path in self._paths
        }
        if before_keys == after_keys:
            self._status("Nessun file aggiunto.")
            return
        self._show_paths()
        self._report = ""
        self.txt.SetValue("")
        if added and skipped:
            how = (
                f"Aggiunti {len(added)} file."
                if len(added) != 1
                else f"Aggiunto {added[0]}."
            )
            msg = how + " Già nel confronto: " + ", ".join(skipped) + "."
        elif added:
            msg = f"Aggiunti {len(added)} file." if len(added) != 1 else f"Aggiunto {added[0]}."
        elif skipped:
            msg = "Già nel confronto: " + ", ".join(skipped) + "."
        else:
            removed = [
                os.path.basename(path)
                for path in before
                if os.path.normcase(os.path.abspath(path)) not in known
            ]
            if len(removed) == 1:
                msg = f"File tolto: {removed[0]}."
            elif removed:
                msg = f"Tolti {len(removed)} file."
            else:
                msg = "Nessun file aggiunto."
            if not self._paths and removed:
                msg += " " + EMPTY_ROW
        if extra:
            msg += f" Il confronto arriva a {MAX_FILES} file."
        self._status(msg)

    def _pick_files(self):
        """None se annulli. Altrimenti (nuovi percorsi, file già nel confronto rimasti)."""
        try:
            import rtad_attach_dialog
        except ImportError:
            rtad_attach_dialog = None
        hint = self._paths[-1] if self._paths else ""
        if rtad_attach_dialog is not None:
            try:
                return rtad_attach_dialog.choose_attachment_paths(
                    self,
                    config_dir=self._config_dir,
                    hint_path=hint,
                    speak=self._speak,
                    title="Aggiungi file al confronto",
                    ok_label="Aggiungi al confronto",
                    help_text=PICK_HELP,
                    max_files=MAX_FILES,
                    windows_message="Aggiungi uno o più file",
                    kept_paths=list(self._paths),
                )
            except Exception:
                return None
        dlg = wx.FileDialog(
            self,
            "Aggiungi file al confronto",
            wildcard="Tutti i file|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        )
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return None
        chosen = list(dlg.GetPaths() or [])
        dlg.Destroy()
        return chosen, list(self._paths)

    def on_remove(self, _event=None):
        if self._busy:
            return
        if not self._paths:
            self._status(EMPTY_ROW)
            return
        sel = self.lst.GetSelection()
        if sel == wx.NOT_FOUND or sel >= len(self._paths):
            self._status(EMPTY_ROW)
            return
        name = os.path.basename(self._paths.pop(sel))
        self._report = ""
        self.txt.SetValue("")
        self._show_paths(prefer=sel)
        msg = f"File tolto: {name}."
        if not self._paths:
            msg += " " + EMPTY_ROW
        self._status(msg)
        try:
            self.lst.SetFocus()
        except Exception:
            pass

    def _on_list_key(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.on_remove(None)
            return
        event.Skip()

    def on_run(self, _event):
        if self._busy:
            return
        if len(self._paths) < 2:
            self._status(NEED_TWO)
            return
        paths = list(self._paths)
        self._set_busy(True)
        self._status(WORKING)

        def work():
            named = []
            for path in paths:
                text = ""
                try:
                    text = self._extract(path) or ""
                except Exception:
                    text = ""
                named.append((_display_name(path, paths), text, file_facts(path)))
            summary, report = compare_named_texts(named)
            wx.CallAfter(self._finish, summary, report)

        threading.Thread(target=work, daemon=True).start()

    def _finish(self, summary: str, report: str) -> None:
        if not self:
            return
        self._report = report
        self.txt.SetValue(report)
        self._set_busy(False)
        self._status(summary)
        try:
            self.txt.SetFocus()
            self.txt.SetInsertionPoint(0)
        except Exception:
            pass

    def on_ask(self, _event):
        if self._busy:
            return
        report = (self._report or "").strip()
        if not report or report == NEED_TWO:
            self._status(BEFORE_ASK)
            return
        msg = ""
        try:
            msg = self._ask(report) or ""
        except Exception:
            msg = "Conversazione non disponibile."
        if msg:
            self._status(msg)

    def on_copy(self, _event):
        text = self.txt.GetValue() or ""
        if not text.strip():
            self._status("Niente da copiare.")
            return
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
            self._status("Testo copiato negli appunti.")
        else:
            self._status("Appunti non disponibili.")

    def on_save(self, _event):
        text = self.txt.GetValue() or ""
        if not text.strip():
            self._status("Niente da salvare.")
            return
        folder = self._save_folder()
        filename = "Confronto.txt"
        try:
            import rtad_chat

            filename = rtad_chat.free_save_name(folder, filename)
        except Exception:
            pass
        dlg = wx.FileDialog(
            self,
            "Salva il confronto",
            defaultDir=folder,
            wildcard="Testo|*.txt",
            defaultFile=filename,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        path = dlg.GetPath()
        dlg.Destroy()
        self._save_dir = os.path.dirname(path)
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        except Exception:
            self._status("Salvataggio non riuscito.")
            return
        self._status(f"Confronto salvato: {os.path.basename(path)}.")

    def _save_folder(self) -> str:
        folder = self._save_dir or ""
        if folder and os.path.isdir(folder):
            return folder
        if self._paths:
            folder = os.path.dirname(self._paths[0])
            if folder and os.path.isdir(folder):
                return folder
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.isdir(downloads):
            return downloads
        return os.path.expanduser("~") or "."

    def on_close(self, _event):
        self.Destroy()


def open_compare_frame(
    speak, extract_text, ask_gemini, initial_path="", config_dir=""
):
    return CompareFrame(
        speak,
        extract_text,
        ask_gemini,
        initial_path=initial_path,
        config_dir=config_dir,
    )
