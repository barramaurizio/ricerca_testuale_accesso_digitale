# -*- coding: utf-8 -*-
"""Smoke test rapido per rtad_docstruct (DOCX + EPUB campione)."""
import os
import sys
import zipfile
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))
import rtad_docstruct as d  # noqa: E402

epub = os.path.join(ROOT, "docs", "campioni", "prova_rtad_epub.epub")
r = d.extract_document_structure(epub)
print("EPUB", r["ok"], r["has_structure"], r["message"])
print("outline", r["outline"])
print("links", len(r["links"]))

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
print("REPORT_OK")
