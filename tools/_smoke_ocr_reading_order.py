# -*- coding: utf-8 -*-
"""Smoke 1.7.7 — OCR ordine di lettura (tabella TV) + regressione CIAO.

Uso (dalla root del repo):
  python tools/_smoke_ocr_reading_order.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_ocr  # noqa: E402

TV = os.path.join(ROOT, "tools", "fixture_ocr_tv_table.jpeg")
CIAO = os.path.join(ROOT, "tools", "fixture_ocr_vertical_CIAO.png")


def _ok(name: str, cond: bool, detail: str = "") -> bool:
    mark = "OK" if cond else "KO"
    extra = f" — {detail}" if detail else ""
    print(f"[{mark}] {name}{extra}")
    return cond


def main() -> int:
    print(f"OCR_CACHE_VERSION={rtad_ocr.OCR_CACHE_VERSION}")
    print(f"motore={rtad_ocr.active_engine()}")
    fails = 0

    # 1) Unit: rebuild da box sintetici (senza motore)
    words = [
        {"t": "Canale", "x": 12, "y": 9, "w": 40, "h": 18},
        {"t": "Programma", "x": 234, "y": 14, "w": 80, "h": 18},
        {"t": "Orario", "x": 403, "y": 16, "w": 60, "h": 18},
        {"t": "Durata", "x": 553, "y": 17, "w": 50, "h": 18},
        {"t": "LA7", "x": 1, "y": 50, "w": 40, "h": 18},
        {"t": "Film", "x": 200, "y": 51, "w": 40, "h": 18},
        {"t": "21:10", "x": 400, "y": 52, "w": 40, "h": 18},
    ]
    rebuilt = rtad_ocr.rebuild_ocr_reading_order(words)
    lines = [ln for ln in rebuilt.splitlines() if ln.strip()]
    header_ok = bool(lines) and all(
        h in lines[0] for h in ("Canale", "Programma", "Orario", "Durata")
    )
    row_ok = len(lines) >= 2 and "LA7" in lines[1] and "Film" in lines[1]
    if not _ok("unit rebuild header riga 1", header_ok, lines[0] if lines else ""):
        fails += 1
    if not _ok("unit rebuild dati riga 2", row_ok, lines[1] if len(lines) > 1 else ""):
        fails += 1

    ciao_words = [
        {"t": c, "x": 10, "y": 10 + i * 18, "w": 12, "h": 14}
        for i, c in enumerate("CIAO")
    ]
    ciao_box = rtad_ocr.rebuild_ocr_reading_order(ciao_words)
    ciao_ref = rtad_ocr.reflow_ocr_vertical_chars(ciao_box)
    if not _ok(
        "unit CIAO bbox+reflow",
        ciao_ref.strip() == "CIAO",
        repr(ciao_ref),
    ):
        fails += 1

    if not rtad_ocr.engine_available():
        print("OCR Windows non disponibile — unit test bastano per la logica.")
        return 1 if fails else 0

    # 2) Tabella TV reale
    if os.path.isfile(TV):
        text = rtad_ocr._ocr_path_impl(TV) or ""
        text = rtad_ocr.reflow_ocr_vertical_chars(text)
        print("--- TV OCR ---")
        print(text)
        print("--- fine ---")
        low = text.lower()
        # Criterio: header sulla stessa riga (ordine lettura), non colonna-per-colonna
        first = (text.splitlines() or [""])[0]
        header_same_line = (
            "canale" in first.lower()
            and "programma" in first.lower()
            and ("orario" in first.lower() or "orarlo" in first.lower())
        )
        # Vecchio bug: tutto in un blob con Canale… poi tutti i canali… poi Programma
        old_column_blob = (
            "\n" not in text.strip()
            and "canale" in low
            and "programma" in low
            and low.find("canale") < low.find("programma")
            and "iris" in low
            and low.find("iris") < low.find("programma")
        )
        if not _ok(
            "TV header su una riga (Canale+Programma+Orario)",
            header_same_line,
            first[:120],
        ):
            fails += 1
        if not _ok("TV non più blob a colonne", not old_column_blob):
            fails += 1
    else:
        print(f"[SKIP] fixture TV assente: {TV}")

    # 3) Regressione CIAO (non tornare a C/I/A/O su 4 righe)
    if os.path.isfile(CIAO):
        raw = rtad_ocr.ocr_image_file(CIAO) or ""
        print("--- CIAO OCR ---")
        print(raw)
        print("--- fine ---")
        non_empty = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        letters_only = (
            len(non_empty) >= 4
            and all(len(ln) <= 2 for ln in non_empty[:4])
            and "".join(non_empty[:4]).upper().replace(" ", "") == "CIAO"
        )
        has_ciao = "CIAO" in raw.upper().replace(" ", "").replace("\n", "")
        if not _ok("CIAO non spezzato in 4 lettere", not letters_only, f"righe={non_empty[:6]}"):
            fails += 1
        if not _ok("CIAO presente nel testo", has_ciao):
            fails += 1
    else:
        print(f"[SKIP] fixture CIAO assente: {CIAO}")

    print()
    print("Esito:", "FAIL" if fails else "PASS", f"({fails} ko)" if fails else "")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
