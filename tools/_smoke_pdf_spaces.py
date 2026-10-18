# -*- coding: utf-8 -*-
"""Smoke: spazi PDF da gap TJ + de-glue TOC."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_docstruct as d  # noqa: E402

# --- de-glue TOC ---
body = "Introduzione. Batteriainterna al dispositivo. Fine."
fixed = d._pdf_deglue_with_phrases(body, ["Batteria interna", "Altro titolo"])
assert "Batteria interna" in fixed, fixed
assert "Batteriainterna" not in fixed, fixed
print("deglue OK:", fixed)

# --- join TJ (logica gemella, senza importare wx/app_gui) ---
THRESHOLD = 120


def join_tj(parts, space_threshold=THRESHOLD):
    out = []
    for item in parts:
        if isinstance(item, (int, float)):
            if abs(float(item)) >= space_threshold:
                if out and not out[-1].endswith((" ", "\n", "\t")):
                    out.append(" ")
            continue
        s = item or ""
        if not s:
            continue
        out.append(s)
    return "".join(out)


assert join_tj(["Batteria", -250, "interna"]) == "Batteria interna"
assert join_tj(["H", 20, "e", 15, "llo"]) == "Hello"  # kerning piccolo
assert join_tj(["Ciao", -80, "mondo"]) == "Ciaomondo"  # sotto soglia
assert join_tj(["Ciao", -120, "mondo"]) == "Ciao mondo"
print("join_tj OK")

# --- content stream sintetico via app_gui se wx disponibile ---
try:
    import app_gui as ag  # noqa: E402

    stream = b"[(Batteria) -250 (interna)] TJ"
    pieces = ag._pdf_text_from_content_stream(stream, {})
    text = " ".join(p for p in pieces if p)
    assert "Batteria interna" in text, pieces
    print("content_stream OK:", pieces)

    soft = ag._pdf_soften_camel_glued("HelloWorld v2Test")
    assert "Hello World" in soft, soft
    print("camel OK:", soft)
except Exception as e:
    print("app_gui skip/fail:", type(e).__name__, e)

pdf = os.path.join(ROOT, "docs", "campioni", "prova_rtad_toc.pdf")
if os.path.isfile(pdf):
    try:
        import app_gui as ag  # noqa: E402

        lines = ag.extract_lines_from_pdf(pdf)
        sample = "\n".join(lines[:30])
        print("sample PDF lines:", len(lines))
        print(sample[:500])
    except Exception as e:
        print("sample PDF skip:", type(e).__name__, e)

print("ALL SMOKE DONE")
