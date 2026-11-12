# -*- coding: utf-8 -*-
"""Prova, prima dell'Installer, le voci nuove di Esplora file.

Punta a python e ad app_gui.py. Non sostituisce le voci già installate.
Dopo la prova: python tools/rtad_shell_preview.py remove
Poi l'Installer della 2.0.1 scrive le voci sull'exe.

Esplora file a volte tiene il menu vecchio: se la voce non compare,
chiudi e riapri Esplora file.
"""
from __future__ import annotations

import sys
import winreg
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Standalone" / "app_gui.py"
PY = sys.executable

IMAGES = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff")
MEDIA = (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".mkv", ".webm", ".avi", ".mov")


def _command(flag: str) -> str:
    return f'"{PY}" "{APP}" {flag} "%1"'


def _keys():
    found = []
    for ext in IMAGES:
        base = (
            r"Software\Classes\SystemFileAssociations\%s\shell"
            r"\RicercaTestualeAccessoDigitaleImg\shell\08taglia" % ext
        )
        found.append((base, "Taglia e unisci", _command("--image-clip")))
    for ext in MEDIA:
        base = (
            r"Software\Classes\SystemFileAssociations\%s\shell"
            r"\RicercaTestualeAccessoDigitaleMedia\shell" % ext
        )
        found.append((base + r"\05taglia", "Taglia e unisci", _command("--clip")))
        found.append((base + r"\06converti", "Converti", _command("--convert")))
    return found


def _delete_tree(root, path):
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_READ) as key:
            while True:
                try:
                    name = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_tree(root, path + "\\" + name)
        winreg.DeleteKey(root, path)
    except FileNotFoundError:
        return
    except OSError:
        return


def add():
    if not APP.is_file():
        raise SystemExit("Manca app_gui.py")
    for path, label, command in _keys():
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, label)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path + r"\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
    print("Voci di prova scritte. Puntano a questa cartella, non all'exe installato.")
    print("Per toglierle: python tools/rtad_shell_preview.py remove")


def remove():
    for path, _label, _command in _keys():
        _delete_tree(winreg.HKEY_CURRENT_USER, path)
    print("Voci di prova tolte.")


def main():
    action = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if action == "add":
        add()
    elif action == "remove":
        remove()
    else:
        raise SystemExit("Usa: python tools/rtad_shell_preview.py add   oppure   remove")


if __name__ == "__main__":
    main()
