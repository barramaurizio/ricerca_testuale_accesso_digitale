#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Impacchetta l'Add-on NVDA leggendo la versione da addon/manifest.ini."""

import os
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
addon_dir = ROOT / "addon"
manifest = addon_dir / "manifest.ini"
skip_dirs = {"__pycache__"}


def read_version() -> str:
    text = manifest.read_text(encoding="utf-8")
    m = re.search(r"^version\s*=\s*([^\s#]+)", text, re.M)
    if not m:
        raise SystemExit("ERRORE: version non trovata in addon/manifest.ini")
    return m.group(1).strip()


version = read_version()
output_name = f"ricerca_testuale_accesso_digitale-{version}.nvda-addon"
output_path = ROOT / output_name

print(f"Creazione del pacchetto NVDA per la versione {version}...")

# Rimuovi pacchetti vecchi dello stesso add-on in root
for old in ROOT.glob("ricerca_testuale_accesso_digitale-*.nvda-addon"):
    if old.resolve() != output_path.resolve():
        try:
            old.unlink()
            print(f"Rimosso vecchio pacchetto: {old.name}")
        except OSError as e:
            print(f"Avviso: non posso rimuovere {old.name}: {e}")

with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(addon_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            if file.endswith(".pyc"):
                continue
            full_path = Path(root) / file
            arcname = full_path.relative_to(addon_dir).as_posix()
            zipf.write(full_path, arcname)
            print(f"Aggiunto: {arcname}")

print(f"\nPacchetto completato con successo: {output_name}")