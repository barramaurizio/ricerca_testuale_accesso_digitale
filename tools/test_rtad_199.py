# -*- coding: utf-8 -*-
"""Prove della 1.9.9: finestre Salva e Sfoglia, senza aprirle a schermo."""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import wx
import rtad_picker


def test_wildcard():
    filters = rtad_picker.parse_wildcard("Testo (*.txt)|*.txt|Tutti i file|*.*")
    assert filters[0] == ("Testo (*.txt)", ["*.txt"]), filters
    assert rtad_picker.ensure_extension("relazione", ["*.txt"]) == "relazione.txt"
    assert rtad_picker.ensure_extension("relazione.doc", ["*.txt"]) == "relazione.doc"
    assert rtad_picker.ensure_extension("relazione", ["*.*"]) == "relazione"
    assert rtad_picker.name_matches("Uno.TXT", ["*.txt"])
    assert not rtad_picker.name_matches("due.pdf", ["*.txt"])
    assert rtad_picker.name_matches("due.pdf", ["*.*"])


def test_file_and_dir():
    app = wx.App(False)
    folder = tempfile.mkdtemp(prefix="rtad199_")
    try:
        open(os.path.join(folder, "uno.txt"), "w", encoding="utf-8").close()
        open(os.path.join(folder, "due.pdf"), "w", encoding="utf-8").close()
        os.mkdir(os.path.join(folder, "Sottocartella"))
        dlg = rtad_picker.RTADFileDialog(
            None,
            "Apri un file",
            defaultDir=folder,
            wildcard="Testo (*.txt)|*.txt|Tutti i file|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        labels = [row.label for row in dlg._rows]
        folder_names = dlg._child_labels(dlg.tree.GetSelection())
        assert "Sottocartella" in folder_names, folder_names
        assert all(not name.startswith("Cartella ") for name in folder_names)
        assert "uno.txt" in labels
        assert "due.pdf" not in labels
        assert "Sottocartella" not in labels
        assert "Nessun file in questa cartella." not in labels
        for drive in dlg._child_labels(dlg._root):
            letter = len(drive) >= 2 and drive[1] == ":"
            named = "(" in drive and drive.rstrip().endswith(")")
            assert letter or named, drive
        status = dlg.txt_status_progress.GetValue()
        assert "uno" not in status or "file" in status
        assert dlg.txt_status_progress.IsEditable() is False
        dlg.choice.SetSelection(1)
        dlg._on_filter(None)
        labels = [row.label for row in dlg._rows]
        assert "due.pdf" in labels
        dlg._accept_named("manca.txt")
        assert dlg.GetPath() == ""
        assert "non trovato" in dlg.txt_status_progress.GetValue().casefold()
        dlg._accept_named("uno.txt")
        assert os.path.basename(dlg.GetPath()).casefold() == "uno.txt"
        assert dlg.GetPaths() == [dlg.GetPath()]
        dlg.Destroy()

        save = rtad_picker.RTADFileDialog(
            None,
            "Salva",
            defaultDir=folder,
            defaultFile="Nuovo",
            wildcard="Testo (*.txt)|*.txt",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        assert save.txt_name.GetValue() == "Nuovo"
        save._accept_named("Nuovo")
        assert save.GetPath().casefold().endswith("nuovo.txt")
        save.Destroy()

        empty = tempfile.mkdtemp(prefix="rtad199e_")
        opened = rtad_picker.RTADFileDialog(
            None,
            "Apri",
            defaultDir=empty,
            wildcard="Tutti|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        assert opened._rows[0].label == "Nessun file in questa cartella."
        assert opened.lst.GetSelection() == 0
        opened.Destroy()

        picked = rtad_picker.RTADDirDialog(
            None,
            "Scegli la cartella",
            defaultPath=folder,
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        chosen = picked.tree.GetSelection()
        node = picked.tree.GetItemData(chosen)
        assert node.kind == "dir"
        assert os.path.normcase(node.path) == os.path.normcase(folder)
        assert "Sottocartella" in picked._child_labels(chosen)
        picked._on_ok()
        assert os.path.normcase(picked.GetPath()) == os.path.normcase(folder)
        picked.Destroy()

        multi = rtad_picker.RTADFileDialog(
            None,
            "Scegli i file",
            defaultDir=folder,
            wildcard="Tutti|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        )
        indexes = [
            i for i, row in enumerate(multi._rows) if row.kind == "file"
        ]
        assert len(indexes) >= 2
        multi.lst.SetSelection(indexes[0])
        multi.lst.SetSelection(indexes[1]) if False else None
        # LB_EXTENDED: seleziona i file uno per uno.
        multi.lst.DeselectAll() if hasattr(multi.lst, "DeselectAll") else None
        for index in indexes:
            multi.lst.SetSelection(index)
        # SetSelection su extended sostituisce. Si usa Select.
        for index in indexes:
            try:
                multi.lst.Select(index)
            except Exception:
                multi.lst.SetSelection(index)
        multi._accept_many()
        names = {os.path.basename(path).casefold() for path in multi.GetPaths()}
        assert "uno.txt" in names and "due.pdf" in names, multi.GetPaths()
        multi.Destroy()
        os.rmdir(empty)
    finally:
        app.Destroy()
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if os.path.isdir(path):
                os.rmdir(path)
            else:
                os.remove(path)
        os.rmdir(folder)


if __name__ == "__main__":
    test_wildcard()
    test_file_and_dir()
    print("test_rtad_199 OK")
