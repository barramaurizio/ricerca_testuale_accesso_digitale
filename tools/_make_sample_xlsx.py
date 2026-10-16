# -*- coding: utf-8 -*-
"""Crea docs/campioni/prova_rtad_pvr_salotto.xlsx e smoke-test extract_rows_from_xlsx."""
from __future__ import annotations

import os
import sys
import zipfile
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "campioni", "prova_rtad_pvr_salotto.xlsx")


def _build_xlsx(path: str) -> None:
    strings = [
        "Programma",
        "Orario",
        "Canale",
        "PVR Salotto",
        "21:15",
        "Rai 1",
        "Partita Juve",
        "20:45",
        "Sky Sport",
        "Telegiornale",
        "20:00",
        "Rai 1",
    ]

    def si(s: str) -> str:
        return f"<si><t>{escape(s)}</t></si>"

    shared = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(strings)}" uniqueCount="{len(strings)}">'
        + "".join(si(s) for s in strings)
        + "</sst>"
    )

    def cell(ref: str, idx: int) -> str:
        return f'<c r="{ref}" t="s"><v>{idx}</v></c>'

    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        "<row r=\"1\">" + cell("A1", 0) + cell("B1", 1) + cell("C1", 2) + "</row>"
        "<row r=\"2\">" + cell("A2", 3) + cell("B2", 4) + cell("C2", 5) + "</row>"
        "<row r=\"3\">" + cell("A3", 6) + cell("B3", 7) + cell("C3", 8) + "</row>"
        "<row r=\"4\">" + cell("A4", 9) + cell("B4", 10) + cell("C4", 11) + "</row>"
        "</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Elenco PVR" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/sharedStrings.xml", shared)


def _smoke_extract(path: str) -> None:
    # Evita import wx di app_gui: carica solo le funzioni XLSX via exec mirato.
    sa = os.path.join(ROOT, "Standalone", "app_gui.py")
    src = open(sa, encoding="utf-8").read()
    start = src.index("def _xlsx_local_tag(")
    end = src.index("\nPDF_READ_MAX_BYTES = ", start)
    chunk = src[start:end]
    # Dipendenze minime usate dall'estrattore
    ns = {
        "os": os,
        "zipfile": zipfile,
        "ET": __import__("xml.etree.ElementTree").etree.ElementTree,
        "logging": __import__("logging"),
        "MAX_DOCX_XML_BYTES": 25 * 1024 * 1024,
    }

    def _read_file_magic(p, n=4):
        with open(p, "rb") as f:
            return f.read(n)

    def _is_ooxml_zip_magic(magic):
        return magic[:2] == b"PK"

    ns["_read_file_magic"] = _read_file_magic
    ns["_is_ooxml_zip_magic"] = _is_ooxml_zip_magic
    exec(chunk, ns)
    rows = ns["extract_rows_from_xlsx"](path)
    texts = "\n".join(r.get("text") or "" for r in rows)
    print("ROWS", len(rows))
    for r in rows:
        print(f"  {r.get('sheet')} r{r.get('row')}: {r.get('text')}")
    assert any("PVR Salotto" in (r.get("text") or "") for r in rows), texts
    assert any(r.get("sheet") == "Elenco PVR" for r in rows)
    print("XLSX_EXTRACT_OK")


def main() -> int:
    _build_xlsx(OUT)
    print("WROTE", OUT, os.path.getsize(OUT))
    _smoke_extract(OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
