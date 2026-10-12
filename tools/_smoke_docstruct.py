# -*- coding: utf-8 -*-
"""Smoke test rapido per rtad_docstruct (DOCX + EPUB + PDF campione)."""
import os
import sys
import zipfile
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))
import rtad_docstruct as d  # noqa: E402

epub = os.path.join(ROOT, "docs", "campioni", "prova_rtad_epub.epub")
if os.path.isfile(epub):
    r = d.extract_document_structure(epub)
    print("EPUB", r["ok"], r["has_structure"], r["message"])
    print("outline", r["outline"])
    print("links", len(r["links"]))
else:
    print("EPUB skip (manca campione)")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def p_with_style(text, style=None):
    p = Element(W + "p")
    if style:
        pPr = SubElement(p, W + "pPr")
        ps = SubElement(pPr, W + "pStyle")
        ps.set(W + "val", style)
    run = SubElement(p, W + "r")
    t = SubElement(run, W + "t")
    t.text = text
    return p


def p_with_link(text, rid):
    p = Element(W + "p")
    h = SubElement(p, W + "hyperlink")
    h.set(R + "id", rid)
    run = SubElement(h, W + "r")
    t = SubElement(run, W + "t")
    t.text = text
    return p


body = Element(W + "body")
body.append(p_with_style("Introduzione", "Heading1"))
body.append(p_with_style("Paragrafo normale senza stile titolo."))
body.append(p_with_style("Dettagli", "Heading2"))
body.append(p_with_link("Sito Accesso Digitale", "rId99"))
doc = Element(W + "document")
doc.append(body)
xml = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + tostring(doc)

rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId99" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.com/accesso" TargetMode="External"/>
</Relationships>"""
ct = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

path = os.path.join(ROOT, "docs", "campioni", "prova_rtad_struttura.docx")
os.makedirs(os.path.dirname(path), exist_ok=True)
with zipfile.ZipFile(path, "w") as z:
    z.writestr("[Content_Types].xml", ct)
    z.writestr("_rels/.rels", root_rels)
    z.writestr("word/document.xml", xml)
    z.writestr("word/_rels/document.xml.rels", rels)

r2 = d.extract_document_structure(path)
print("DOCX", r2["ok"], r2["has_structure"], r2["message"])
print("outline", r2["outline"])
print("links", r2["links"])
print(d.format_structure_report(r2)[:400])

# PDF minimo con Outlines + URI link
pdf_path = os.path.join(ROOT, "docs", "campioni", "prova_rtad_toc.pdf")
objs = []


def _obj(n, body: bytes) -> bytes:
    return f"{n} 0 obj\n".encode("ascii") + body + b"\nendobj\n"


objs.append(_obj(1, b"<< /Type /Catalog /Pages 2 0 R /Outlines 3 0 R >>"))
objs.append(_obj(2, b"<< /Type /Pages /Kids [4 0 R] /Count 1 >>"))
objs.append(_obj(3, b"<< /Type /Outlines /First 5 0 R /Last 6 0 R /Count 2 >>"))
objs.append(
    _obj(
        4,
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 7 0 R /Annots [8 0 R] >>",
    )
)
objs.append(_obj(5, b"<< /Title (Capitolo Uno) /Parent 3 0 R /Next 6 0 R /Dest [4 0 R /Fit] >>"))
objs.append(_obj(6, b"<< /Title (Capitolo Due) /Parent 3 0 R /Prev 5 0 R /Dest [4 0 R /Fit] >>"))
content = b"BT /F1 24 Tf 100 700 Td (Hello) Tj ET"
objs.append(_obj(7, f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream"))
objs.append(
    _obj(
        8,
        b"<< /Type /Annot /Subtype /Link /Rect [100 700 200 720] "
        b"/Border [0 0 0] /A << /S /URI /URI (https://example.com/accesso) >> >>",
    )
)

parts = [b"%PDF-1.4\n"]
offsets = [0]
for chunk in objs:
    offsets.append(sum(len(p) for p in parts))
    parts.append(chunk)
xref_pos = sum(len(p) for p in parts)
xref = [b"xref\n0 9\n", b"0000000000 65535 f \n"]
for i in range(1, 9):
    xref.append(f"{offsets[i]:010d} 00000 n \n".encode("ascii"))
parts.extend(xref)
parts.append(b"trailer\n<< /Size 9 /Root 1 0 R >>\n")
parts.append(f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii"))
os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
with open(pdf_path, "wb") as f:
    f.write(b"".join(parts))

r3 = d.extract_document_structure(pdf_path)
print("PDF", r3["ok"], r3["has_structure"], r3["message"])
print("outline", r3["outline"])
print("links", r3["links"])
assert r3["has_structure"], "PDF TOC/link attesi"
assert any("Capitolo Uno" in (x.get("title") or "") for x in r3["outline"])
assert any("example.com" in (x.get("href") or "") for x in r3["links"])

# Stem titoli lunghi: verifica la costante nel sorgente (evita import wx di app_gui)
app_src = open(
    os.path.join(ROOT, "Standalone", "app_gui.py"), encoding="utf-8"
).read()
assert "max_len=200" in app_src, "app_gui deve usare max_len=200 sullo stem"
addon_src = open(
    os.path.join(ROOT, "addon", "globalPlugins", "ricerca_testuale", "__init__.py"),
    encoding="utf-8",
).read()
assert "max_len=200" in addon_src, "add-on deve usare max_len=200 sullo stem"
long_title = (
    'KOLO SEGNA MA DIVIDE GASP DI RABBIA, IL ROSSO DA "FOTOGRAMMA" '
    "LAZIO COL MAL DI TESTA."
)
# Replica minima della sanificazione (stessa regola di _safe_filename_stem)
cleaned = []
for ch in long_title.strip():
    if ch in '<>:"/\\|?*' or ord(ch) < 32:
        cleaned.append("_")
    else:
        cleaned.append(ch)
stem = "".join(cleaned)
stem = " ".join(stem.split()).strip(" .")
if len(stem) > 200:
    stem = stem[:200].rstrip(" .")
print("STEM_LEN", len(stem), stem)
assert len(stem) > 80, "stem non deve restare tagliato a 80"
assert "LAZIO COL MAL DI TESTA" in stem
print("REPORT_OK")
