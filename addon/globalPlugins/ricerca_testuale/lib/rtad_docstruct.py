# -*- coding: utf-8 -*-
"""RTAD — struttura documenti (outline/TOC + link) per DOCX ed EPUB.

Gemello SA/Add-on. Solo stdlib (zipfile + xml.etree).
PDF: per ora messaggio onesto (TOC non ancora estratto); il testo piano resta altrove.
"""

from __future__ import annotations

import logging
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from urllib.parse import unquote

MAX_DOCX_XML_BYTES = 25 * 1024 * 1024
MAX_EPUB_BYTES = 80 * 1024 * 1024
MAX_EPUB_CHAPTERS = 80
MAX_EPUB_CHAPTER_XML_BYTES = 4 * 1024 * 1024
MAX_OUTLINE = 500
MAX_LINKS = 500
MAX_BODY_CHARS = 2_000_000

_HEADING_STYLE_RE = re.compile(
    r"^(?:Heading|Titolo|Title|heading|titolo|title)\s*(\d+)$",
    re.I,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\f\v]+")
_HREF_RE = re.compile(
    r'(?is)<a\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>'
)
_HEADING_HTML_RE = re.compile(
    r"(?is)<h([1-6])\b[^>]*>(.*?)</h\1>"
)


def _local(tag: str) -> str:
    if not tag:
        return ""
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _empty_result(fmt: str = "", message: str = "") -> dict:
    return {
        "ok": False,
        "format": fmt or "",
        "title": "",
        "outline": [],
        "links": [],
        "body": "",
        "plain": "",
        "has_structure": False,
        "message": message or "Nessuna struttura disponibile.",
    }


def _strip_html_text(raw: str) -> str:
    text = _TAG_RE.sub(" ", raw or "")
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return _WS_RE.sub(" ", text).strip()


def _docx_rels_map(zf: zipfile.ZipFile) -> dict:
    """rId -> Target URL/path da word/_rels/document.xml.rels."""
    out = {}
    try:
        raw = zf.read("word/_rels/document.xml.rels")
    except KeyError:
        return out
    try:
        root = ET.fromstring(raw)
    except Exception:
        return out
    for el in root.iter():
        if _local(el.tag) != "Relationship":
            continue
        rid = el.attrib.get("Id") or ""
        target = el.attrib.get("Target") or ""
        if rid and target:
            out[rid] = target.strip()
    return out


def _docx_heading_level(p_el) -> int | None:
    """Livello titolo 1..9 da pStyle o outlineLvl, altrimenti None."""
    for child in list(p_el):
        if _local(child.tag) != "pPr":
            continue
        for sub in child.iter():
            ln = _local(sub.tag)
            if ln == "outlineLvl":
                val = sub.attrib.get(
                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"
                ) or sub.attrib.get("val")
                try:
                    n = int(val) + 1
                    if 1 <= n <= 9:
                        return n
                except (TypeError, ValueError):
                    pass
            if ln == "pStyle":
                style = (
                    sub.attrib.get(
                        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"
                    )
                    or sub.attrib.get("val")
                    or ""
                )
                m = _HEADING_STYLE_RE.match(style.strip())
                if m:
                    try:
                        n = int(m.group(1))
                        if 1 <= n <= 9:
                            return n
                    except ValueError:
                        pass
                low = style.strip().lower()
                if low in ("title", "titolo"):
                    return 1
    return None


def _docx_para_text(p_el) -> str:
    parts = []
    for el in p_el.iter():
        if _local(el.tag) == "t" and el.text:
            parts.append(el.text)
        if _local(el.tag) == "tab":
            parts.append("\t")
    return "".join(parts).strip()


def _docx_collect_links(p_el, rels: dict, links: list) -> None:
    for el in p_el.iter():
        if _local(el.tag) != "hyperlink":
            continue
        rid = el.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ) or el.attrib.get("id")
        anchor = el.attrib.get(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}anchor"
        ) or el.attrib.get("anchor")
        href = ""
        if rid and rid in rels:
            href = rels[rid]
        elif anchor:
            href = f"#{anchor}"
        text = "".join(
            (t.text or "")
            for t in el.iter()
            if _local(t.tag) == "t"
        ).strip()
        if not text and not href:
            continue
        links.append({"text": text or href, "href": href or "(destinazione interna)"})
        if len(links) >= MAX_LINKS:
            return


def extract_structure_from_docx(file_path: str) -> dict:
    """Outline (titoli) + hyperlink da DOCX OOXML."""
    res = _empty_result("docx")
    try:
        if not file_path or not os.path.isfile(file_path):
            res["message"] = "File non trovato."
            return res
        with open(file_path, "rb") as f:
            magic = f.read(4)
        if magic[:2] != b"PK":
            res["message"] = (
                "Questo .doc non è OOXML (formato Word vecchio). "
                "Convertilo in .docx per la struttura, oppure apri con Word."
            )
            return res
        with zipfile.ZipFile(file_path, "r") as zf:
            try:
                info = zf.getinfo("word/document.xml")
            except KeyError:
                res["message"] = "DOCX senza document.xml leggibile."
                return res
            if info.file_size > MAX_DOCX_XML_BYTES:
                res["message"] = "Documento troppo grande per l'analisi struttura."
                return res
            raw = zf.read("word/document.xml")
            if len(raw) > MAX_DOCX_XML_BYTES:
                raw = raw[:MAX_DOCX_XML_BYTES]
            try:
                tree = ET.fromstring(raw)
            except Exception as e:
                res["message"] = f"XML DOCX non valido: {e}"
                return res
            rels = _docx_rels_map(zf)
            outline = []
            links = []
            body_lines = []
            plain_lines = []
            for p in tree.iter():
                if _local(p.tag) != "p":
                    continue
                text = _docx_para_text(p)
                if not text:
                    _docx_collect_links(p, rels, links)
                    continue
                level = _docx_heading_level(p)
                if level:
                    outline.append({"level": level, "title": text, "anchor": ""})
                    body_lines.append(f"[H{level}] {text}")
                else:
                    body_lines.append(text)
                plain_lines.append(text)
                _docx_collect_links(p, rels, links)
                if len(outline) >= MAX_OUTLINE:
                    break
            body = "\n".join(body_lines)
            if len(body) > MAX_BODY_CHARS:
                body = body[:MAX_BODY_CHARS] + "\n…"
            plain = "\n".join(plain_lines)
            has_struct = bool(outline or links)
            res.update(
                {
                    "ok": True,
                    "title": os.path.basename(file_path),
                    "outline": outline[:MAX_OUTLINE],
                    "links": links[:MAX_LINKS],
                    "body": body,
                    "plain": plain,
                    "has_structure": has_struct,
                    "message": (
                        f"DOCX: {len(outline)} titoli, {len(links)} link."
                        if has_struct
                        else (
                            "DOCX senza titoli/stile Heading né link rilevati. "
                            "Mostro il testo piano."
                        )
                    ),
                }
            )
            return res
    except Exception as e:
        logging.debug(f"extract_structure_from_docx: {e}")
        res["message"] = f"Errore lettura DOCX: {e}"
        return res


def _find_opf_path(zf: zipfile.ZipFile) -> str | None:
    try:
        raw = zf.read("META-INF/container.xml")
    except KeyError:
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
            full = el.attrib.get("full-path")
            if full:
                return full.replace("\\", "/")
    return None


def _join_opf(opf_path: str, href: str) -> str:
    href = (href or "").replace("\\", "/").split("#", 1)[0]
    if not href:
        return ""
    opf_dir = opf_path.rsplit("/", 1)[0] if "/" in opf_path else ""
    full = f"{opf_dir}/{href}" if opf_dir else href
    parts = []
    for p in full.split("/"):
        if p in ("", "."):
            continue
        if p == "..":
            if parts:
                parts.pop()
            continue
        parts.append(p)
    return "/".join(parts)


def _opf_spine_hrefs(zf: zipfile.ZipFile, opf_path: str) -> list[str]:
    try:
        root = ET.fromstring(zf.read(opf_path))
    except Exception:
        return []
    id_to_href = {}
    for el in root.iter():
        if _local(el.tag) != "item":
            continue
        iid = el.attrib.get("id")
        href = el.attrib.get("href")
        if not iid or not href:
            continue
        media = (el.attrib.get("media-type") or "").lower()
        low = href.lower()
        if media and not any(x in media for x in ("xhtml", "html", "xml", "dtbook")):
            if not low.endswith((".xhtml", ".html", ".htm", ".xml")):
                continue
        id_to_href[iid] = href.replace("\\", "/")
    hrefs = []
    for el in root.iter():
        if _local(el.tag) != "itemref":
            continue
        href = id_to_href.get(el.attrib.get("idref") or "")
        if not href:
            continue
        hrefs.append(_join_opf(opf_path, href))
        if len(hrefs) >= MAX_EPUB_CHAPTERS:
            break
    return hrefs


def _opf_nav_ncx_paths(zf: zipfile.ZipFile, opf_path: str) -> tuple[str, str]:
    """Ritorna (nav_xhtml, ncx_path) se presenti nell'OPF."""
    nav = ""
    ncx = ""
    try:
        root = ET.fromstring(zf.read(opf_path))
    except Exception:
        return "", ""
    for el in root.iter():
        if _local(el.tag) != "item":
            continue
        href = el.attrib.get("href") or ""
        props = (el.attrib.get("properties") or "").lower()
        media = (el.attrib.get("media-type") or "").lower()
        full = _join_opf(opf_path, href)
        if "nav" in props and not nav:
            nav = full
        if "ncx" in media or href.lower().endswith(".ncx"):
            if not ncx:
                ncx = full
    return nav, ncx


def _parse_ncx_outline(zf: zipfile.ZipFile, ncx_path: str) -> tuple[str, list]:
    title = ""
    outline = []
    try:
        raw = zf.read(ncx_path)
        root = ET.fromstring(raw)
    except Exception:
        return title, outline

    def walk(el, level: int):
        for child in list(el):
            if _local(child.tag) == "navPoint":
                label = ""
                for sub in child:
                    if _local(sub.tag) == "navLabel":
                        label = "".join(sub.itertext()).strip()
                        break
                if label:
                    outline.append({"level": level, "title": label, "anchor": ""})
                if len(outline) < MAX_OUTLINE:
                    walk(child, level + 1)

    for el in root.iter():
        if _local(el.tag) == "docTitle" and not title:
            title = "".join(el.itertext()).strip()
        if _local(el.tag) == "navMap":
            walk(el, 1)
            break
    return title, outline


def _parse_nav_xhtml_outline(zf: zipfile.ZipFile, nav_path: str) -> list:
    outline = []
    try:
        raw = zf.read(nav_path).decode("utf-8", errors="ignore")
    except Exception:
        return outline
    # Lista toc: <li><a …>titolo</a> — livello grezzo da nesting ol/ul non necessario
    for m in re.finditer(r"(?is)<a\b[^>]*>(.*?)</a>", raw):
        label = _strip_html_text(m.group(1))
        if label:
            outline.append({"level": 1, "title": label, "anchor": ""})
        if len(outline) >= MAX_OUTLINE:
            break
    return outline


def _read_zip_member(zf: zipfile.ZipFile, href: str) -> bytes:
    try:
        return zf.read(href)
    except KeyError:
        low = href.lower()
        match = next((n for n in zf.namelist() if n.lower() == low), None)
        if not match:
            return b""
        return zf.read(match)


def extract_structure_from_epub(file_path: str) -> dict:
    """TOC (NCX/nav) + titoli HTML + link da EPUB."""
    res = _empty_result("epub")
    try:
        if not file_path or not os.path.isfile(file_path):
            res["message"] = "File non trovato."
            return res
        try:
            size = os.path.getsize(file_path)
        except OSError:
            size = 0
        if size > MAX_EPUB_BYTES:
            res["message"] = "EPUB troppo grande per l'analisi struttura."
            return res
        with zipfile.ZipFile(file_path, "r") as zf:
            opf = _find_opf_path(zf)
            if not opf:
                res["message"] = "EPUB senza OPF leggibile."
                return res
            nav_path, ncx_path = _opf_nav_ncx_paths(zf, opf)
            title = ""
            outline: list = []
            if ncx_path:
                title, outline = _parse_ncx_outline(zf, ncx_path)
            if not outline and nav_path:
                outline = _parse_nav_xhtml_outline(zf, nav_path)
            # Fallback: cerca toc.ncx nel package
            if not outline:
                for name in zf.namelist():
                    if name.lower().endswith("toc.ncx"):
                        title, outline = _parse_ncx_outline(zf, name)
                        break

            hrefs = _opf_spine_hrefs(zf, opf)
            if not hrefs:
                hrefs = [
                    n
                    for n in zf.namelist()
                    if n.lower().endswith((".xhtml", ".html", ".htm"))
                ][:MAX_EPUB_CHAPTERS]

            links = []
            body_lines = []
            plain_lines = []
            heading_from_html = []
            for href in hrefs:
                raw_b = _read_zip_member(zf, href)
                if not raw_b:
                    continue
                if len(raw_b) > MAX_EPUB_CHAPTER_XML_BYTES:
                    raw_b = raw_b[:MAX_EPUB_CHAPTER_XML_BYTES]
                raw = raw_b.decode("utf-8", errors="ignore")
                for hm in _HEADING_HTML_RE.finditer(raw):
                    level = int(hm.group(1))
                    htxt = _strip_html_text(hm.group(2))
                    if htxt:
                        heading_from_html.append(
                            {"level": level, "title": htxt, "anchor": ""}
                        )
                        body_lines.append(f"[H{level}] {htxt}")
                        plain_lines.append(htxt)
                for am in _HREF_RE.finditer(raw):
                    href_u = unquote((am.group(1) or "").strip())
                    atxt = _strip_html_text(am.group(2))
                    if href_u.startswith("#") and not atxt:
                        continue
                    if href_u.lower().startswith("javascript:"):
                        continue
                    links.append({"text": atxt or href_u, "href": href_u})
                    if len(links) >= MAX_LINKS:
                        break
                # Paragrafi residuali (senza ridoppiare i soli heading già presi)
                chunk = re.sub(
                    r"(?i)</(p|div|li|tr|br\s*/?)>",
                    "\n",
                    raw,
                )
                chunk = re.sub(r"(?is)<h[1-6]\b[^>]*>.*?</h[1-6]>", "\n", chunk)
                chunk = _TAG_RE.sub(" ", chunk)
                chunk = (
                    chunk.replace("&nbsp;", " ")
                    .replace("&amp;", "&")
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
                )
                chunk = _WS_RE.sub(" ", chunk)
                for line in chunk.splitlines():
                    s = line.strip()
                    if s:
                        body_lines.append(s)
                        plain_lines.append(s)
                if len(body_lines) > 20000:
                    break

            if not outline and heading_from_html:
                outline = heading_from_html[:MAX_OUTLINE]

            body = "\n".join(body_lines)
            if len(body) > MAX_BODY_CHARS:
                body = body[:MAX_BODY_CHARS] + "\n…"
            plain = "\n".join(plain_lines)
            has_struct = bool(outline or links)
            if not title:
                title = os.path.basename(file_path)
            res.update(
                {
                    "ok": True,
                    "title": title,
                    "outline": outline[:MAX_OUTLINE],
                    "links": links[:MAX_LINKS],
                    "body": body,
                    "plain": plain,
                    "has_structure": has_struct,
                    "message": (
                        f"EPUB: {len(outline)} voci di sommario/titoli, {len(links)} link."
                        if has_struct
                        else (
                            "EPUB senza sommario/titoli né link rilevati. "
                            "Mostro il testo piano."
                        )
                    ),
                }
            )
            return res
    except Exception as e:
        logging.debug(f"extract_structure_from_epub: {e}")
        res["message"] = f"Errore lettura EPUB: {e}"
        return res


def extract_document_structure(file_path: str) -> dict:
    """Facade: struttura DOCX/EPUB; PDF e altri con messaggio onesto."""
    if not file_path or not os.path.isfile(file_path):
        return _empty_result(message="File non trovato.")
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".docx":
        return extract_structure_from_docx(file_path)
    if ext == ".doc":
        res = _empty_result("doc")
        res["message"] = (
            "Il formato .doc (Word vecchio) non espone titoli/link in RTAD. "
            "Salva come .docx oppure apri con Word."
        )
        return res
    if ext == ".epub":
        return extract_structure_from_epub(file_path)
    if ext == ".pdf":
        res = _empty_result("pdf")
        res["message"] = (
            "Per i PDF, il sommario/TOC e i link non sono ancora estratti in questa versione. "
            "Qui sotto c'è il testo piano; oppure apri il file in Edge/Acrobat."
        )
        return res
    if ext == ".odt":
        res = _empty_result("odt")
        res["message"] = (
            "Struttura ODT (titoli/link) non ancora supportata. "
            "Il testo piano resta disponibile da «Leggi testo»."
        )
        return res
    return _empty_result(
        message="Formato non supportato per la lettura strutturata (DOCX ed EPUB in 1.6.8)."
    )


def format_structure_report(struct: dict) -> str:
    """Testo unico accessibile: messaggio + sommario + link + corpo."""
    if not struct:
        return "Nessun dato."
    lines = []
    msg = (struct.get("message") or "").strip()
    if msg:
        lines.append(msg)
        lines.append("")
    outline = struct.get("outline") or []
    links = struct.get("links") or []
    if outline:
        lines.append("=== Sommario / titoli ===")
        for i, item in enumerate(outline, 1):
            level = int(item.get("level") or 1)
            indent = "  " * max(0, level - 1)
            lines.append(f"{i}. {indent}[H{level}] {item.get('title') or ''}")
        lines.append("")
    if links:
        lines.append("=== Link ===")
        for i, item in enumerate(links, 1):
            lines.append(
                f"{i}. {item.get('text') or ''} -> {item.get('href') or ''}"
            )
        lines.append("")
    body = (struct.get("body") or struct.get("plain") or "").strip()
    if body:
        lines.append("=== Testo ===")
        lines.append(body)
    elif not outline and not links:
        lines.append("(Nessun testo strutturato da mostrare.)")
    return "\n".join(lines).strip()
