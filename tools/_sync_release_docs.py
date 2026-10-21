# -*- coding: utf-8 -*-
"""Sincronizza guida pratica + gemelli e riporta lo stato (uso pre-rilascio)."""
from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "addon" / "globalPlugins" / "ricerca_testuale" / "lib"


def main() -> int:
    src_guida = ROOT / "Standalone" / "rtad_guida_pratica.py"
    dst_guida = LIB / "rtad_guida_pratica.py"
    shutil.copy2(src_guida, dst_guida)

    sys.path.insert(0, str(ROOT / "Standalone"))
    import rtad_guida_pratica as g  # noqa: E402

    text = g.get_guide_text()
    (ROOT / "docs" / "GUIDA_PRATICA.txt").write_text(text, encoding="utf-8")
    html = (
        "<!DOCTYPE html><html lang=it><head><meta charset=utf-8>"
        "<title>Guida pratica</title></head><body><pre>\n"
        + text
        + "\n</pre></body></html>\n"
    )
    (ROOT / "addon" / "doc" / "it" / "guida_pratica.html").write_text(
        html, encoding="utf-8"
    )

    shutil.copy2(
        ROOT / "Standalone" / "rtad_docstruct.py", LIB / "rtad_docstruct.py"
    )
    shutil.copy2(ROOT / "Standalone" / "rtad_chat.py", LIB / "rtad_chat.py")
    shutil.copy2(
        ROOT / "Standalone" / "rtad_guida_html.py", LIB / "rtad_guida_html.py"
    )

    pairs = [
        ("rtad_ocr.py", ROOT / "Standalone" / "rtad_ocr.py", LIB / "rtad_ocr.py"),
        ("rtad_media.py", ROOT / "Standalone" / "rtad_media.py", LIB / "rtad_media.py"),
        ("rtad_guida_pratica.py", src_guida, dst_guida),
        (
            "rtad_docstruct.py",
            ROOT / "Standalone" / "rtad_docstruct.py",
            LIB / "rtad_docstruct.py",
        ),
        ("rtad_epub.py", ROOT / "Standalone" / "rtad_epub.py", LIB / "rtad_epub.py"),
        ("rtad_chat.py", ROOT / "Standalone" / "rtad_chat.py", LIB / "rtad_chat.py"),
        (
            "rtad_guida_html.py",
            ROOT / "Standalone" / "rtad_guida_html.py",
            LIB / "rtad_guida_html.py",
        ),
    ]
    all_ok = True
    for name, a, b in pairs:
        ok = filecmp.cmp(a, b, shallow=False)
        print(f"{name}: {'OK' if ok else 'DIFF'}")
        all_ok = all_ok and ok
    print(f"GUIDA sync OK, chars={len(text)}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
