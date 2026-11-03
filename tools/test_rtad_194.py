# -*- coding: utf-8 -*-
"""1.9.4: link interno di Word, titoli e link ODT, nome del salvataggio."""
from __future__ import annotations

import os
import sys
import tempfile
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Standalone"))
sys.path.insert(0, ROOT)

import rtad_docstruct  # noqa: E402
import rtad_media  # noqa: E402
import rtad_ocr  # noqa: E402


def _docx(path: str) -> None:
    document = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:bookmarkStart w:id="1" w:name="_Toc1"/>
      <w:r><w:t>Introduzione</w:t></w:r>
      <w:bookmarkEnd w:id="1"/>
    </w:p>
    <w:p><w:r><w:t>Corpo del capitolo.</w:t></w:r></w:p>
    <w:p>
      <w:hyperlink w:anchor="_Toc1">
        <w:r><w:t>Vai all'introduzione</w:t></w:r>
      </w:hyperlink>
    </w:p>
    <w:p>
      <w:hyperlink r:id="rId1">
        <w:r><w:t>Sito</w:t></w:r>
      </w:hyperlink>
    </w:p>
    <w:p>
      <w:r><w:instrText xml:space="preserve"> HYPERLINK \\l "_Toc1" </w:instrText></w:r>
      <w:r><w:t>Campo interno</w:t></w:r>
    </w:p>
  </w:body>
</w:document>
"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
    Target="https://example.com/guida" TargetMode="External"/>
</Relationships>
"""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", document.encode("utf-8"))
        zf.writestr("word/_rels/document.xml.rels", rels.encode("utf-8"))


def _odt(path: str) -> None:
    content = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:xlink="urn:oasis:names:tc:opendocument:xmlns:xlink:1.0">
  <office:body><office:text>
    <text:h text:outline-level="1">
      <text:bookmark-start text:name="Intro"/>
      Introduzione
      <text:bookmark-end text:name="Intro"/>
    </text:h>
    <text:p>Corpo del capitolo.</text:p>
    <text:p><text:a xlink:href="#Intro">Vai all'introduzione</text:a></text:p>
    <text:p><text:a xlink:href="https://example.com/guida">Sito</text:a></text:p>
  </office:text></office:body>
</office:document-content>
"""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("content.xml", content.encode("utf-8"))


def check(cond, msg):
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("OK", msg)


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        docx = os.path.join(folder, "nota.docx")
        odt = os.path.join(folder, "nota.odt")
        _docx(docx)
        _odt(odt)
        word = rtad_docstruct.extract_structure_from_docx(docx)
        check(word.get("ok"), "docx ok")
        titles = [item.get("title") for item in word.get("outline") or []]
        check(titles == ["Introduzione"], "docx titolo")
        check("[H1] Introduzione" in (word.get("body") or ""), "docx marcatore")
        internal = [
            item for item in word.get("links") or []
            if str(item.get("href") or "").startswith("#")
            or item.get("anchor") == "_Toc1"
        ]
        check(internal, "docx link interno")
        check(
            all(item.get("target_title") == "Introduzione" for item in internal),
            "docx salta a Introduzione",
        )
        check(
            all(str(item.get("where") or "").startswith("titolo «") for item in internal),
            "docx dove",
        )
        sites = [
            item for item in word.get("links") or []
            if str(item.get("href") or "").startswith("https://")
        ]
        check(len(sites) == 1 and not sites[0].get("where"), "docx sito esterno")

        od = rtad_docstruct.extract_structure_from_odt(odt)
        check(od.get("ok"), "odt ok")
        check(
            [item.get("title") for item in od.get("outline") or []] == ["Introduzione"],
            "odt titolo",
        )
        od_in = [
            item for item in od.get("links") or []
            if str(item.get("href") or "").startswith("#")
        ]
        check(len(od_in) == 1 and od_in[0].get("target_title") == "Introduzione", "odt link")
        od_site = [
            item for item in od.get("links") or []
            if str(item.get("href") or "").startswith("https://")
        ]
        check(len(od_site) == 1, "odt sito")
        check("Introduzione" in (od.get("plain") or ""), "odt testo piano")

    slug = ("titolo-lungo-della-pagina-" * 8).strip("-")
    name = rtad_ocr.suggest_image_save_stem(
        "https://example.com/articoli/" + slug, ""
    )
    check(len(name) > 70, f"nome immagine lungo ({len(name)})")
    check(len(name) <= 240, "nome immagine entro 240")

    reported = os.path.join("C:\\Video", "Titolo dalla pagina.mp4")
    edited = rtad_media.prefer_dialog_filename(
        reported, ["Titolo dalla pagina.mp4", "Titolo dalla mia pagina.mp4"]
    )
    check(os.path.basename(edited) == "Titolo dalla mia pagina.mp4", "modifica parziale")
    same = rtad_media.prefer_dialog_filename(
        reported, ["Titolo dalla pagina.mp4"]
    )
    check(same == reported, "nome intero invariato")
    hidden = rtad_media.prefer_dialog_filename(
        reported, ["Desktop", "Titolo dalla mia pagina"]
    )
    check(
        os.path.basename(hidden) == "Titolo dalla mia pagina.mp4",
        "modifica senza estensione visibile",
    )
    folder_label = rtad_media.prefer_dialog_filename(reported, ["Desktop"])
    check(folder_label == reported, "etichetta della cartella ignorata")
    print("194 OK")


if __name__ == "__main__":
    main()
