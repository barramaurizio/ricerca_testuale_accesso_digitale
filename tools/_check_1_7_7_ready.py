# -*- coding: utf-8 -*-
"""Controllo pre-rilascio 1.7.7 (contenuti + gemelli + pacchetto)."""
from __future__ import annotations

import filecmp
import re
from pathlib import Path

R = Path(__file__).resolve().parents[1]
L = R / "addon" / "globalPlugins" / "ricerca_testuale" / "lib"
ko = 0


def ok(cond: bool, msg: str) -> None:
    global ko
    print(("OK" if cond else "KO"), msg)
    if not cond:
        ko += 1


print("=== GEMELLI ===")
for n in (
    "rtad_ocr.py",
    "rtad_guida_pratica.py",
    "rtad_guida_html.py",
    "rtad_media.py",
    "rtad_docstruct.py",
):
    a, b = R / "Standalone" / n, L / n
    ok(a.exists() and b.exists() and filecmp.cmp(a, b, shallow=False), n)

print("=== CONTENUTI ===")
checks = {
    "Standalone/app_gui.py": [
        r'APP_VERSION = "1\.7\.7"',
        r"OCR tabelle / colonne",
    ],
    "addon/globalPlugins/ricerca_testuale/__init__.py": [
        r'APP_VERSION = "1\.7\.7"',
        r"OCR tabelle / colonne",
    ],
    "addon/manifest.ini": [r"version = 1\.7\.7"],
    "Standalone/setup.iss": [r"AppVersion=1\.7\.7"],
    "Standalone/version.txt": [r"1\.7\.7"],
    "Standalone/compila.bat": [r"v1\.7\.7"],
    "Standalone/changelog.txt": [r"Versione 1\.7\.7", r"riga-per-riga"],
    "Standalone/rtad_ocr.py": [
        r"OCR_CACHE_VERSION = 20",
        r"rebuild_ocr_reading_order",
    ],
    "Standalone/rtad_guida_pratica.py": [r"versione 1\.7\.7", r"tabelle"],
    "Standalone/rtad_guida_html.py": [
        r"OCR tabelle / colonne",
        r"Dalla 1\.7\.7",
    ],
    "README.md": [
        r"\(v1\.7\.7\)",
        r"Novità della Versione 1\.7\.7",
        r"What's New in Version 1\.7\.7",
    ],
    "docs/GUIDA_PRATICA.txt": [r"versione 1\.7\.7"],
    "addon/doc/it/guida_pratica.html": [r"versione 1\.7\.7"],
    "addon/doc/it/readme.html": [r"v1\.7\.7", r"Novità Versione 1\.7\.7"],
    "addon/doc/en/readme.html": [
        r"v1\.7\.7",
        r"What's New in Version 1\.7\.7",
    ],
    "docs/NOTE_RILASCIO_1.7.7.txt": [r"v1\.7\.7", r"OCR tabelle"],
}
for path, pats in checks.items():
    t = (R / path).read_text(encoding="utf-8", errors="replace")
    for pat in pats:
        ok(bool(re.search(pat, t)), f"{path} :: {pat}")

print("=== ADDON / WHATSNEW ===")
addons = list(R.glob("ricerca_testuale_accesso_digitale-1.7.7.nvda-addon"))
ok(bool(addons), "pacchetto .nvda-addon 1.7.7")
if addons:
    print("   ", addons[0].name, addons[0].stat().st_size, "bytes")

stale = (
    "Restano OCR orizzontale / copie / Incolla 1.7.5",
    "Restano OCR orizzontale / Incolla 1.7.5",
)
for p in (
    "Standalone/app_gui.py",
    "addon/globalPlugins/ricerca_testuale/__init__.py",
):
    t = (R / p).read_text(encoding="utf-8", errors="replace")
    ok(not any(s in t for s in stale), f"WhatsNew fresco: {p}")

print("=== ESITO ===", "FAIL" if ko else "PASS", f"({ko} ko)" if ko else "")
raise SystemExit(1 if ko else 0)
