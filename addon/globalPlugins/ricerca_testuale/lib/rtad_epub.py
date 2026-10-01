# -*- coding: utf-8 -*-
"""RTAD EPUB — estrazione testo da ebook .epub (ZIP+XHTML), gemello SA/Add-on.

Niente dipendenze esterne: zipfile + xml.etree.
Usato nella ricerca documenti come DOC/PDF.
"""

from __future__ import annotations

import logging
import os
import re
import zipfile
import xml.etree.ElementTree as ET

# Anti-blocco (allineato allo spirito DOC/PDF)
MAX_EPUB_BYTES = 80 * 1024 * 1024  # 80 MB file
MAX_EPUB_CHAPTERS = 80
MAX_EPUB_CHAPTER_XML_BYTES = 4 * 1024 * 1024
MAX_EPUB_PARAGRAPHS = 8000

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\f\v]+")
_BLANK_RE = re.compile(r"\n{3,}")


def _local(tag: str) -> str:
    if not tag:
        return ""
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _strip_html_to_paragraphs(raw: bytes | str) -> list[str]:
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="ignore")
    else:
        text = raw or ""
    # Spezza su blocchi tipici prima di togliere i tag
    text = re.sub(
        r"(?i)</(p|div|h[1-6]|li|tr|br\s*/?)>",
        "\n",
        text,
    )
    text = _TAG_RE.sub(" ", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    text = _WS_RE.sub(" ", text)
    text = _BLANK_RE.sub("\n\n", text)
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s:
            out.append(s)
    return out


def _find_opf_path(zf: zipfile.ZipFile) -> str | None:
    try:
        raw = zf.read("META-INF/container.xml")
    except KeyError:
        # Fallback: primo .opf in radice o sottocartelle
        for name in zf.namelist():
            if name.lower().endswith(".opf"):
                return name
        return None
    try:
        root = ET.fromstring(raw)
    except Exception:
        return None
    for el in root.iter():
        if _local(el.tag) == "rootfile":
            full = el.attrib.get("full-path") or el.attrib.get(
                "{urn:oasis:names:tc:opendocument:xmlns:container}full-path"
            )
            if full:
                return full.replace("\\", "/")
    return None


def _opf_spine_hrefs(zf: zipfile.ZipFile, opf_path: str) -> list[str]:
    try:
        raw = zf.read(opf_path)
    except KeyError:
        return []
    try:
        root = ET.fromstring(raw)
    except Exception:
        return []

    opf_dir = opf_path.rsplit("/", 1)[0] if "/" in opf_path else ""
    id_to_href = {}
    for el in root.iter():
        if _local(el.tag) == "item":
            iid = el.attrib.get("id")
            href = el.attrib.get("href")
            media = (el.attrib.get("media-type") or "").lower()
            if not iid or not href:
                continue
            # Solo contenuti testuali tipici
            if media and not any(
                x in media for x in ("xhtml", "html", "xml", "dtbook")
            ):
                # Alcuni EPUB omettono media-type utile: tieni href .xhtml/.html
                low = href.lower()
                if not low.endswith((".xhtml", ".html", ".htm", ".xml")):
                    continue
            id_to_href[iid] = href.replace("\\", "/")

    hrefs = []
    for el in root.iter():
        if _local(el.tag) == "itemref":
            idref = el.attrib.get("idref")
            if not idref:
                continue
            href = id_to_href.get(idref)
            if not href:
                continue
            if opf_dir:
                full = f"{opf_dir}/{href}"
            else:
                full = href
            # normalizza ./
            parts = []
            for p in full.split("/"):
                if p in ("", "."):
                    continue
                if p == "..":
                    if parts:
                        parts.pop()
                    continue
                parts.append(p)
            hrefs.append("/".join(parts))
            if len(hrefs) >= MAX_EPUB_CHAPTERS:
                break
    return hrefs


def extract_paragraphs_from_epub(file_path: str) -> list[str]:
    """Restituisce paragrafi/testo in ordine di lettura (spine), o []."""
    try:
        if not file_path or not os.path.isfile(file_path):
            return []
        try:
            size = os.path.getsize(file_path)
        except OSError:
            size = 0
        if size > MAX_EPUB_BYTES:
            logging.debug(f"EPUB troppo grande, salto: {file_path}")
            return []
        with zipfile.ZipFile(file_path, "r") as zf:
            opf = _find_opf_path(zf)
            if not opf:
                return []
            hrefs = _opf_spine_hrefs(zf, opf)
            if not hrefs:
                # Ultimo tentativo: tutti gli xhtml/html nel pacchetto
                hrefs = [
                    n
                    for n in zf.namelist()
                    if n.lower().endswith((".xhtml", ".html", ".htm"))
                ][:MAX_EPUB_CHAPTERS]
            paragraphs: list[str] = []
            for href in hrefs:
                try:
                    info = zf.getinfo(href)
                except KeyError:
                    # Case-insensitive fallback
                    low = href.lower()
                    match = next((n for n in zf.namelist() if n.lower() == low), None)
                    if not match:
                        continue
                    info = zf.getinfo(match)
                    href = match
                if info.file_size > MAX_EPUB_CHAPTER_XML_BYTES:
                    continue
                try:
                    raw = zf.read(href)
                except Exception:
                    continue
                if len(raw) > MAX_EPUB_CHAPTER_XML_BYTES:
                    raw = raw[:MAX_EPUB_CHAPTER_XML_BYTES]
                for p in _strip_html_to_paragraphs(raw):
                    paragraphs.append(p)
                    if len(paragraphs) >= MAX_EPUB_PARAGRAPHS:
                        return paragraphs
            return paragraphs
    except Exception as e:
        logging.debug(f"Errore estrazione EPUB {file_path}: {e}")
        return []
