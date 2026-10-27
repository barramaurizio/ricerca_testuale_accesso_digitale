# -*- coding: utf-8 -*-
"""RTAD — struttura documenti (outline/TOC + link) per DOCX, EPUB e PDF.

Gemello SA/Add-on. Solo stdlib (zipfile + xml.etree + zlib per PDF).
PDF: sommario (/Outlines) e link URI (/Annot /Link); il testo piano
resta spesso riempito dal chiamante (estrattore PDF di app_gui / add-on).
"""

from __future__ import annotations

import html
import logging
import os
import pathlib
import re
import subprocess
import sys
import webbrowser
import zipfile
import zlib
import xml.etree.ElementTree as ET
from urllib.parse import unquote

MAX_DOCX_XML_BYTES = 25 * 1024 * 1024
MAX_EPUB_BYTES = 80 * 1024 * 1024
MAX_EPUB_CHAPTERS = 80
MAX_EPUB_CHAPTER_XML_BYTES = 4 * 1024 * 1024
MAX_PDF_BYTES = 80 * 1024 * 1024
MAX_PDF_OBJ_INFLATE = 4 * 1024 * 1024
MAX_OUTLINE = 500
MAX_LINKS = 500
MAX_BODY_CHARS = 2_000_000
MAX_PDF_OUTLINE_WALK = 2000

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
    text = html.unescape(text)
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
                chunk = html.unescape(chunk)
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


# Molti PDF (anche 1.4 linearizzati) usano solo \r come fine riga: (?m)^ non basta.
_PDF_OBJ_RE = re.compile(br"(?:[\r\n]|^)(\d+)\s+(\d+)\s+obj\b")
_PDF_STRING_AFTER = br"\s*(\((?:\\.|[^\\)])*\)|<([0-9A-Fa-f\s]+)>)"
_PDF_URI_RE = re.compile(br"/URI" + _PDF_STRING_AFTER, re.I)
_PDF_TITLE_RE = re.compile(br"/Title" + _PDF_STRING_AFTER, re.I)
_PDF_INDEX_DOTS_RE = re.compile(
    r"([^\d\n\r]{2,60}?)\s*\.{2,}\s*(\d{1,4})\b"
)
_PDF_PAGE_DEST_RE = re.compile(r"^p(\d+)$", re.I)


def _pdf_inflate(data: bytes, max_out: int = MAX_PDF_OBJ_INFLATE) -> bytes:
    if not data:
        return b""
    for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
        try:
            dec = zlib.decompressobj(wbits)
            out = dec.decompress(data, max_out)
            try:
                tail = dec.flush()
            except Exception:
                tail = b""
            if tail:
                remain = max_out - len(out)
                if remain > 0:
                    out += tail[:remain]
            return out
        except Exception:
            continue
    return data


def _pdf_unescape_literal(raw: bytes) -> bytes:
    out = bytearray()
    i = 0
    n = len(raw)
    while i < n:
        b = raw[i]
        if b == 0x5C and i + 1 < n:
            nxt = raw[i + 1]
            if nxt == 0x6E:
                out.append(0x0A)
                i += 2
            elif nxt == 0x72:
                out.append(0x0D)
                i += 2
            elif nxt == 0x74:
                out.append(0x09)
                i += 2
            elif nxt == 0x62:
                out.append(0x08)
                i += 2
            elif nxt == 0x66:
                out.append(0x0C)
                i += 2
            elif nxt in (0x28, 0x29, 0x5C):
                out.append(nxt)
                i += 2
            elif 0x30 <= nxt <= 0x37:
                j = i + 1
                octal = bytearray()
                while j < n and len(octal) < 3 and 0x30 <= raw[j] <= 0x37:
                    octal.append(raw[j])
                    j += 1
                try:
                    out.append(int(octal.decode("ascii"), 8) & 0xFF)
                except Exception:
                    pass
                i = j
            else:
                out.append(nxt)
                i += 2
        else:
            out.append(b)
            i += 1
    return bytes(out)


def _pdf_decode_string_token(token: bytes) -> str:
    """Decodifica stringa PDF letterale `(...)` o hex `<...>`. """
    token = (token or b"").strip()
    if not token:
        return ""
    if token.startswith(b"(") and token.endswith(b")"):
        data = _pdf_unescape_literal(token[1:-1])
        if data.startswith(b"\xfe\xff"):
            try:
                return data[2:].decode("utf-16-be", errors="ignore")
            except Exception:
                pass
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin1", errors="ignore")
    if token.startswith(b"<") and token.endswith(b">"):
        hx = re.sub(br"[^0-9A-Fa-f]", b"", token[1:-1])
        if len(hx) % 2:
            hx = hx[:-1]
        if not hx:
            return ""
        try:
            data = bytes.fromhex(hx.decode("ascii"))
        except Exception:
            return ""
        if data.startswith(b"\xfe\xff"):
            try:
                return data[2:].decode("utf-16-be", errors="ignore")
            except Exception:
                pass
        try:
            return data.decode("utf-16-be")
        except Exception:
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data.decode("latin1", errors="ignore")
    return ""


def _pdf_read_string_after(blob: bytes, key: bytes) -> str:
    """Legge /Key (string) o /Key <hex> subito dopo la chiave."""
    m = re.search(
        re.escape(key) + br"\s*(\((?:\\.|[^\\)])*\)|<([0-9A-Fa-f\s]+)>)",
        blob,
        re.I,
    )
    if not m:
        return ""
    return _pdf_decode_string_token(m.group(1)).strip()


def _pdf_ref_after(blob: bytes, key: bytes) -> int | None:
    m = re.search(re.escape(key) + br"\s+(\d+)\s+\d+\s+R\b", blob)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _pdf_build_obj_index(raw: bytes) -> dict[int, tuple[int, int]]:
    """obj_num -> (start_after_obj_header, end_before_endobj)."""
    index: dict[int, tuple[int, int]] = {}
    for m in _PDF_OBJ_RE.finditer(raw):
        try:
            num = int(m.group(1))
        except ValueError:
            continue
        start = m.end()
        end = raw.find(b"endobj", start)
        if end < 0:
            continue
        index[num] = (start, end)
    return index


def _pdf_stream_bytes(body: bytes) -> bytes:
    """Estrae e decomprime lo stream di un oggetto (se FlateDecode)."""
    if not body:
        return b""
    head = body[:1200]
    if b"stream" not in head:
        return b""
    m_at = body.find(b"stream")
    after = m_at + 6
    if after + 1 < len(body) and body[after : after + 2] == b"\r\n":
        s0 = after + 2
    elif after < len(body) and body[after : after + 1] in (b"\n", b"\r"):
        s0 = after + 1
    else:
        return b""
    s1 = body.find(b"endstream", s0)
    if s1 < 0:
        return b""
    stream = body[s0:s1]
    if stream.endswith(b"\r\n"):
        stream = stream[:-2]
    elif stream.endswith(b"\n") or stream.endswith(b"\r"):
        stream = stream[:-1]
    if b"/FlateDecode" in head or b"/Fl" in head:
        return _pdf_inflate(stream)
    return stream


def _pdf_expand_objstms(
    raw: bytes, index: dict[int, tuple[int, int]]
) -> dict[int, bytes]:
    """Espande /Type/ObjStm in un dizionario obj_num -> body (PDF 1.5+)."""
    extra: dict[int, bytes] = {}
    for num, (start, end) in index.items():
        body = raw[start:end]
        head = body[:400]
        if b"/ObjStm" not in head:
            continue
        if b"/Type/ObjStm" not in head and b"/Type /ObjStm" not in head:
            continue
        n_m = re.search(br"/N\s+(\d+)", head)
        f_m = re.search(br"/First\s+(\d+)", head)
        if not n_m or not f_m:
            continue
        try:
            n_count = int(n_m.group(1))
            first = int(f_m.group(1))
        except ValueError:
            continue
        data = _pdf_stream_bytes(body)
        if not data or n_count <= 0 or first <= 0 or first > len(data):
            continue
        header = data[:first]
        pairs = re.findall(br"(\d+)\s+(\d+)", header)
        n_count = min(n_count, len(pairs))
        for i in range(n_count):
            try:
                onum = int(pairs[i][0])
                off = int(pairs[i][1])
            except ValueError:
                continue
            ostart = first + off
            if ostart > len(data):
                continue
            oend = first + int(pairs[i + 1][1]) if i + 1 < n_count else len(data)
            if oend < ostart:
                oend = len(data)
            extra[onum] = data[ostart:oend]
    return extra


def _pdf_get(
    raw: bytes,
    index: dict[int, tuple[int, int]],
    extra: dict[int, bytes],
    num: int,
) -> bytes:
    if num in extra:
        return extra[num]
    span = index.get(num)
    if not span:
        return b""
    return raw[span[0] : span[1]]


def _pdf_file_page_from_dest_blob(
    blob: bytes, obj_to_idx: dict[int, int]
) -> int:
    """Da `[pageObj 0 R /XYZ …]` o `<< /D […] >>` → pagina file 1-based."""
    if not blob or not obj_to_idx:
        return 0
    m = re.search(br"\[\s*(\d+)\s+\d+\s+R\b", blob)
    if not m:
        return 0
    try:
        return int(obj_to_idx.get(int(m.group(1)), 0) or 0)
    except ValueError:
        return 0


def _pdf_resolve_outline_dest(
    raw: bytes,
    index: dict[int, tuple[int, int]],
    extra: dict[int, bytes],
    body: bytes,
    dest_to_page: dict[str, int],
    obj_to_idx: dict[int, int],
) -> tuple[str, int]:
    """(/Dest nome|array|ref oppure /A GoTo) → (anchor, page file)."""
    anchor = ""
    page = 0

    # /Dest (NomeDest)
    dname = _pdf_read_string_after(body, b"/Dest")
    if dname:
        anchor = dname
        page = int(dest_to_page.get(dname.lower()) or 0)

    # /Dest [pageObj 0 R /XYZ …]
    if not page:
        m = re.search(br"/Dest\s*\[(.*?)\]", body, re.S)
        if m:
            page = _pdf_file_page_from_dest_blob(
                b"[" + m.group(1) + b"]", obj_to_idx
            )

    # /Dest N 0 R → oggetto destinazione
    if not page:
        dref = _pdf_ref_after(body, b"/Dest")
        if dref:
            db = _pdf_get(raw, index, extra, dref)
            if not anchor:
                anchor = _pdf_read_string_after(db, b"/D") or ""
                if anchor:
                    page = int(dest_to_page.get(anchor.lower()) or 0)
            if not page:
                page = _pdf_file_page_from_dest_blob(db, obj_to_idx)

    # /A << /S /GoTo /D (…) >> oppure ref ad azione
    if not page:
        act_ref = _pdf_ref_after(body, b"/A")
        act = _pdf_get(raw, index, extra, act_ref) if act_ref else b""
        if b"/GoTo" in body or b"/GoTo" in act or b"/D" in body:
            blob = act if act else body
            d2 = _pdf_read_string_after(blob, b"/D")
            if d2:
                anchor = anchor or d2
                page = int(dest_to_page.get(d2.lower()) or 0)
            if not page:
                page = _pdf_file_page_from_dest_blob(blob, obj_to_idx)

    return anchor, page


def _pdf_walk_outlines(
    raw: bytes,
    index: dict[int, tuple[int, int]],
    extra: dict[int, bytes],
    first_num: int,
    level: int,
    outline: list,
    seen: set,
    dest_to_page: dict[str, int] | None = None,
    obj_to_idx: dict[int, int] | None = None,
) -> None:
    dest_to_page = dest_to_page or {}
    obj_to_idx = obj_to_idx or {}
    num = first_num
    steps = 0
    while (
        num
        and num not in seen
        and len(outline) < MAX_OUTLINE
        and steps < MAX_PDF_OUTLINE_WALK
    ):
        steps += 1
        seen.add(num)
        body = _pdf_get(raw, index, extra, num)
        if not body:
            break
        title = _pdf_read_string_after(body, b"/Title")
        if title:
            anchor, page = _pdf_resolve_outline_dest(
                raw, index, extra, body, dest_to_page, obj_to_idx
            )
            item = {
                "level": max(1, min(level, 9)),
                "title": title,
                "anchor": anchor or "",
            }
            if page:
                item["page"] = page
            outline.append(item)
        child = _pdf_ref_after(body, b"/First")
        if child:
            _pdf_walk_outlines(
                raw,
                index,
                extra,
                child,
                level + 1,
                outline,
                seen,
                dest_to_page=dest_to_page,
                obj_to_idx=obj_to_idx,
            )
        nxt = _pdf_ref_after(body, b"/Next")
        num = nxt or 0


def _pdf_page_tree_order(
    raw: bytes,
    index: dict[int, tuple[int, int]],
    extra: dict[int, bytes],
) -> list[int]:
    """Elenco obj_num delle pagine in ordine (1ª = indice 0)."""
    root = None
    for num, body in list(extra.items()) + [
        (n, raw[s:e]) for n, (s, e) in index.items()
    ]:
        if b"/Catalog" in body[:400] and b"/Type" in body[:400]:
            root = _pdf_ref_after(body, b"/Pages")
            if root:
                break
    if not root:
        m = re.search(br"/Pages\s+(\d+)\s+\d+\s+R\b", raw)
        if m:
            try:
                root = int(m.group(1))
            except ValueError:
                root = None
    if not root:
        return []
    pages: list[int] = []
    stack = [root]
    seen: set[int] = set()
    while stack and len(pages) < 20000:
        num = stack.pop()
        if num in seen:
            continue
        seen.add(num)
        body = _pdf_get(raw, index, extra, num)
        if not body:
            continue
        is_pages = b"/Kids" in body and (
            b"/Type/Pages" in body
            or b"/Type /Pages" in body
            or (b"/Count" in body and b"/Type/Page" not in body[:120])
        )
        if is_pages:
            kids = re.search(br"/Kids\s*\[(.*?)\]", body, re.S)
            if not kids:
                continue
            refs = [int(x) for x in re.findall(br"(\d+)\s+\d+\s+R", kids.group(1))]
            # Kids in ordine: append reverse for stack LIFO → pop preserves order
            for ref in reversed(refs):
                stack.append(ref)
            continue
        if b"/Type/Page" in body or b"/Type /Page" in body:
            pages.append(num)
    return pages


def _pdf_dest_name_to_file_page(
    raw: bytes,
    index: dict[int, tuple[int, int]],
    extra: dict[int, bytes],
    page_objs: list[int],
) -> dict[str, int]:
    """Nome destinazione (p339, G3.763940, …) → pagina file 1-based."""
    if not page_objs:
        return {}
    obj_to_idx = {obj: i + 1 for i, obj in enumerate(page_objs)}
    out: dict[str, int] = {}

    def remember(name: str, page: int) -> None:
        name = (name or "").strip()
        if not name or not page:
            return
        out[name.lower()] = page

    for _num, body in list(extra.items()) + [
        (n, raw[s:e]) for n, (s, e) in index.items()
    ]:
        if b"/Names" not in body:
            continue
        # (nome) [pageObj 0 R /XYZ …]
        for m in re.finditer(
            br"\(((?:\\.|[^\\)])+)\)\s*\[\s*(\d+)\s+\d+\s+R\b", body
        ):
            try:
                name = _pdf_decode_string_token(b"(" + m.group(1) + b")")
                page = obj_to_idx.get(int(m.group(2)), 0)
            except Exception:
                continue
            remember(name, page)
        # (nome) destObj 0 R  →  << /D [pageObj 0 R /XYZ …] >>
        for m in re.finditer(
            br"\(((?:\\.|[^\\)])+)\)\s*(\d+)\s+\d+\s+R\b", body
        ):
            try:
                name = _pdf_decode_string_token(b"(" + m.group(1) + b")")
                dest_obj = int(m.group(2))
            except Exception:
                continue
            if name.lower() in out:
                continue
            db = _pdf_get(raw, index, extra, dest_obj)
            page = _pdf_file_page_from_dest_blob(db, obj_to_idx)
            if not page:
                # destObj è direttamente una pagina
                page = obj_to_idx.get(dest_obj, 0)
            remember(name, page)
    return out


def _pdf_collect_annots_and_dests(
    raw: bytes,
    index: dict[int, tuple[int, int]],
    extra: dict[int, bytes],
) -> tuple[list, list[int], list, dict[str, int]]:
    """URI + GoTo interni, pagine stampate, outline grezzo, mappa dest→pagina file."""
    page_objs = _pdf_page_tree_order(raw, index, extra)
    dest_to_page = _pdf_dest_name_to_file_page(raw, index, extra, page_objs)

    uri_links: list = []
    internal_links: list = []
    seen_href: set[str] = set()
    printed_pages: set[int] = set()

    def add_uri(href: str) -> None:
        href = (href or "").strip()
        if not href:
            return
        key = "uri:" + href.lower()
        if key in seen_href:
            return
        seen_href.add(key)
        uri_links.append(
            {
                "text": f"Sito web (esterno): {href}",
                "href": href,
            }
        )

    def add_internal(dest_name: str) -> None:
        name = (dest_name or "").strip()
        if not name:
            return
        m = _PDF_PAGE_DEST_RE.match(name)
        printed = None
        if m:
            try:
                printed = int(m.group(1))
                printed_pages.add(printed)
            except ValueError:
                printed = None
        file_page = dest_to_page.get(name.lower())
        if not file_page and printed is not None:
            # fallback grezzo: etichetta ≈ pagina file (spesso off-by-N)
            file_page = printed
        if not file_page:
            return
        key = f"rtad-pdf-page:{file_page}"
        if key in seen_href:
            return
        seen_href.add(key)
        label = (
            f"Sezione p. {printed} (pagina file {file_page})"
            if printed is not None
            else f"Pagina file {file_page}"
        )
        internal_links.append(
            {
                "text": label,
                "href": key,
                "page": file_page,
                "anchor": name.lower(),
            }
        )

    # Named dests in /Names
    for _num, body in list(extra.items()) + [
        (n, raw[s:e]) for n, (s, e) in index.items()
    ]:
        if b"/Names" not in body or b"(p" not in body:
            continue
        for m in re.finditer(br"\((p\d+)\)\s*\[", body):
            try:
                add_internal(m.group(1).decode("ascii", errors="ignore"))
            except Exception:
                continue

    # Link annots → /A
    for _num, body in list(extra.items()) + [
        (n, raw[s:e]) for n, (s, e) in index.items()
    ]:
        if b"/Subtype/Link" not in body and b"/Subtype /Link" not in body:
            continue
        act_ref = _pdf_ref_after(body, b"/A")
        act = _pdf_get(raw, index, extra, act_ref) if act_ref else body
        href = _pdf_read_string_after(act, b"/URI")
        if href:
            add_uri(href)
            continue
        dname = _pdf_read_string_after(act, b"/D")
        if not dname and b"/D(" in act:
            m = re.search(br"/D\s*(\([^)]+\))", act)
            if m:
                dname = _pdf_decode_string_token(m.group(1)).strip()
        if dname:
            add_internal(dname)

    # Interni prima (sezioni PDF), URI esterni dopo — evita Tab sul solo samsung.com
    links = (internal_links + uri_links)[:MAX_LINKS]

    dest_outline: list = []
    for p in sorted(printed_pages):
        anchor = f"p{p}"
        file_page = dest_to_page.get(anchor)
        dest_outline.append(
            {
                "level": 1,
                "title": f"Pagina {p}",
                "anchor": anchor,
                "page": file_page,
            }
        )
        if len(dest_outline) >= MAX_OUTLINE:
            break

    return links, sorted(printed_pages), dest_outline[:MAX_OUTLINE], dest_to_page


def _pdf_outline_from_index_text(plain: str, prefer_pages: list[int] | None = None) -> list:
    """Ricostruisce voci tipo «English ...... 3» dall'indice testuale."""
    text = plain or ""
    if len(text) > 120_000:
        # L'indice lingue/capitoli sta di solito all'inizio
        text = text[:120_000]
    hits = _PDF_INDEX_DOTS_RE.findall(text)
    if not hits:
        return []
    prefer = set(prefer_pages or [])
    outline = []
    seen_pages: set[int] = set()
    for label, page_s in hits:
        try:
            page = int(page_s)
        except ValueError:
            continue
        if page in seen_pages:
            continue
        if prefer and page not in prefer:
            continue
        title = re.sub(r"\s+", " ", (label or "").strip(" .\t"))
        if not title or len(title) < 2:
            continue
        # Scarta residui numerici / troppo corti inutili
        if title.replace(".", "").strip().isdigit():
            continue
        seen_pages.add(page)
        outline.append(
            {
                "level": 1,
                "title": f"{title} (p. {page})",
                "anchor": f"p{page}",
            }
        )
        if len(outline) >= MAX_OUTLINE:
            break
    # Se il filtro prefer_pages ha vuotato tutto, riprova senza filtro
    if prefer and len(outline) < 3:
        return _pdf_outline_from_index_text(plain, prefer_pages=None)
    return outline


def _pdf_find_title_in_body(body: str, title: str, start: int = 0):
    """Trova titolo nel corpo; anche senza spazi (Tj attaccati: Batteriainterna).

    Ritorna (pos, matched_len) oppure None.
    """
    title = (title or "").strip()
    if not title or not body:
        return None
    p = body.find(title, start)
    if p >= 0:
        return p, len(title)
    compact = re.sub(r"\s+", "", title)
    if compact and compact != title:
        p = body.find(compact, start)
        if p >= 0:
            return p, len(compact)
    return None


def _pdf_deglue_with_phrases(text: str, phrases) -> str:
    """Sostituisce «Batteriainterna» con «Batteria interna» usando frasi note (TOC).

    Utile quando il gap TJ non c'è e il titolo nel sommario ha già gli spazi.
    """
    if not text or not phrases:
        return text
    items = []
    for ph in phrases:
        ph = (ph or "").strip()
        if not ph or " " not in ph or len(ph) < 4:
            continue
        # Solo etichetta, senza « (p. 12)»
        ph = re.sub(r"\s*\(p\.\s*\d+\)\s*$", "", ph, flags=re.I).strip()
        if not ph or " " not in ph:
            continue
        compact = re.sub(r"\s+", "", ph)
        if len(compact) < 4 or compact == ph:
            continue
        items.append((len(compact), compact, ph))
    if not items:
        return text
    items.sort(key=lambda x: x[0], reverse=True)
    for _, compact, spaced in items:
        out = []
        i = 0
        while True:
            p = text.find(compact, i)
            if p < 0:
                out.append(text[i:])
                break
            before_ok = p == 0 or not text[p - 1].isalpha()
            after = p + len(compact)
            after_ok = after >= len(text) or not text[after].isalpha()
            out.append(text[i:p])
            out.append(spaced if (before_ok and after_ok) else compact)
            i = after
        text = "".join(out)
    return text


def _pdf_annotate_body_with_outline_headings(body: str, outline: list) -> str:
    """Inserisce «\\n[Hn] Titolo» sulle occorrenze nel corpo (non sull'indice a puntini).

    Così Invio sul sommario atterra sul titolo, non sulla coda della riga precedente.
    Gestisce anche testo PDF senza spazi tra parole (font CID).
    """
    if not body or not outline:
        return body
    # (pos, level, title_display, matched_len)
    hits: list[tuple[int, int, str, int]] = []
    seen_pos: set[int] = set()
    for item in outline:
        title = (item.get("title") or "").strip()
        if len(title) < 3:
            continue
        level = max(1, min(int(item.get("level") or 1), 9))
        start = 0
        while True:
            found = _pdf_find_title_in_body(body, title, start)
            if not found:
                break
            p, mlen = found
            after = body[p + mlen : p + mlen + 48]
            if re.match(r"\s*\.{2,}\s*\d*", after):
                start = p + max(1, mlen)
                continue
            before = body[max(0, p - 16) : p]
            if re.search(r"\[H\d+\]\s*$", before):
                start = p + max(1, mlen)
                continue
            if p not in seen_pos:
                hits.append((p, level, title, mlen))
                seen_pos.add(p)
            break
    if not hits:
        return body
    hits.sort(key=lambda x: x[0])
    parts: list[str] = []
    last = 0
    for pos, level, title, mlen in hits:
        if pos < last:
            continue
        parts.append(body[last:pos])
        # Paragrafo proprio sul titolo: NVDA/copia non ripartono dalla coda precedente
        prev = parts[-1] if parts else ""
        if prev and not prev.endswith("\n\n"):
            if prev.endswith("\n"):
                parts.append("\n")
            else:
                parts.append("\n\n")
        parts.append(f"[H{level}] {title}\n")
        last = pos + mlen
    parts.append(body[last:])
    return "".join(parts)


def enrich_pdf_structure_with_text(struct: dict, plain: str) -> dict:
    """Dopo l'estrazione testo: completa il sommario da indice «Nome… pagina»."""
    if not struct or (struct.get("format") or "") != "pdf":
        return struct
    plain = (plain or "").strip()
    if not plain:
        return struct
    struct = dict(struct)
    outline = list(struct.get("outline") or [])
    # Prima: spazi dai titoli TOC (Batteriainterna → Batteria interna)
    plain = _pdf_deglue_with_phrases(
        plain, [it.get("title") for it in outline if isinstance(it, dict)]
    )
    plain = _pdf_annotate_body_with_outline_headings(plain, outline)
    struct["body"] = plain
    struct["plain"] = plain
    pages = list(struct.get("_pdf_pages") or [])
    dest_to_page = dict(struct.get("_pdf_dest_to_page") or {})
    # Se c'è solo outline grezzo «Pagina N», preferisci etichette dall'indice
    only_page_labels = outline and all(
        str(it.get("title") or "").startswith("Pagina ") for it in outline
    )
    if (not outline or only_page_labels) and plain:
        synthesized = _pdf_outline_from_index_text(plain, prefer_pages=pages or None)
        if synthesized:
            by_page = {}
            for it in synthesized:
                m = _PDF_PAGE_DEST_RE.match(str(it.get("anchor") or ""))
                if m:
                    by_page[int(m.group(1))] = it
            if pages:
                merged = []
                for p in pages:
                    if p in by_page:
                        item = dict(by_page[p])
                    else:
                        item = {
                            "level": 1,
                            "title": f"Pagina {p}",
                            "anchor": f"p{p}",
                        }
                    anchor = str(item.get("anchor") or f"p{p}").lower()
                    item["page"] = dest_to_page.get(anchor) or item.get("page")
                    merged.append(item)
                outline = merged
            else:
                outline = synthesized
    # Assicura page file su ogni voce outline
    for item in outline:
        anchor = str(item.get("anchor") or "").lower()
        if not item.get("page") and anchor in dest_to_page:
            item["page"] = dest_to_page[anchor]
    struct["outline"] = outline[:MAX_OUTLINE]

    # Solo link web in elenco «Link»: le sezioni stanno nel sommario (Invio = apri pagina).
    # Evita di dover ritrovare due volte la stessa voce (sommario + lista link).
    uri_links = [
        ln
        for ln in (struct.get("links") or [])
        if str(ln.get("href") or "").lower().startswith(("http://", "https://"))
    ]
    struct["links"] = uri_links[:MAX_LINKS]
    links = struct["links"]
    has_struct = bool(outline or links)
    struct["has_structure"] = has_struct
    struct["ok"] = True
    if has_struct:
        n_ext = len(uri_links)
        struct["message"] = (
            f"PDF: {len(outline)} voci di sommario"
            + (f", {n_ext} link web." if n_ext else ".")
            + " Invio sul sommario va al testo della sezione qui in RTAD;"
            " i link «Sito web» sono esterni."
        )
    elif not (struct.get("message") or "").strip():
        struct["message"] = (
            "PDF senza sommario/TOC né link rilevati. Mostro il testo piano."
        )
    struct.pop("_pdf_pages", None)
    struct.pop("_pdf_dest_to_page", None)
    return struct


def extract_structure_from_pdf(file_path: str) -> dict:
    """Sommario PDF (/Outlines o destinazioni) + link URI; body lasciato al chiamante."""
    res = _empty_result("pdf")
    try:
        size = os.path.getsize(file_path)
        if size > MAX_PDF_BYTES:
            res["message"] = (
                f"PDF troppo grande per l'analisi struttura (>{MAX_PDF_BYTES // (1024 * 1024)} MB). "
                "Il testo piano può restare disponibile da «Leggi testo»."
            )
            return res
        with open(file_path, "rb") as f:
            raw = f.read(MAX_PDF_BYTES)
    except Exception as e:
        res["message"] = f"Errore lettura PDF: {e}"
        return res
    if not raw.startswith(b"%PDF"):
        res["message"] = "File non riconosciuto come PDF."
        return res

    index = _pdf_build_obj_index(raw)
    extra = _pdf_expand_objstms(raw, index)
    outline: list = []

    # Pagine + mappa destinazioni PRIMA del walk outlines (serve per /Dest)
    page_objs = _pdf_page_tree_order(raw, index, extra)
    obj_to_idx = {obj: i + 1 for i, obj in enumerate(page_objs)}
    dest_to_page = _pdf_dest_name_to_file_page(raw, index, extra, page_objs)

    # Catalog → /Outlines (anche in ObjStm)
    outlines_ref = None
    for num, body in list(extra.items()) + [
        (n, raw[s:e]) for n, (s, e) in index.items()
    ]:
        if b"/Catalog" in body[:300] and b"/Type" in body[:300]:
            outlines_ref = _pdf_ref_after(body, b"/Outlines")
            if outlines_ref:
                break
    if outlines_ref is None:
        m = re.search(br"/Outlines\s+(\d+)\s+\d+\s+R\b", raw)
        if m:
            try:
                outlines_ref = int(m.group(1))
            except ValueError:
                outlines_ref = None

    if outlines_ref:
        root_body = _pdf_get(raw, index, extra, outlines_ref)
        first = _pdf_ref_after(root_body, b"/First") if root_body else None
        if first:
            _pdf_walk_outlines(
                raw,
                index,
                extra,
                first,
                1,
                outline,
                set(),
                dest_to_page=dest_to_page,
                obj_to_idx=obj_to_idx,
            )

    # Fallback Title in oggetti outline compressi
    if not outline:
        seen_t: set[str] = set()
        for _num, body in extra.items():
            for m in _PDF_TITLE_RE.finditer(body):
                title = _pdf_decode_string_token(m.group(1)).strip()
                if not title or len(title) > 300:
                    continue
                low = title.lower()
                if low in seen_t:
                    continue
                start = max(0, m.start() - 80)
                ctx = body[start : m.end() + 80]
                if (
                    b"/Parent" not in ctx
                    and b"/First" not in ctx
                    and b"/Next" not in ctx
                ):
                    continue
                seen_t.add(low)
                outline.append({"level": 1, "title": title, "anchor": ""})
                if len(outline) >= MAX_OUTLINE:
                    break
            if len(outline) >= MAX_OUTLINE:
                break

    links, pages, dest_outline, dest_to_page2 = _pdf_collect_annots_and_dests(
        raw, index, extra
    )
    # Unisci mappe (collect può aggiungere pN; walk già usa dest_to_page)
    if dest_to_page2:
        dest_to_page.update(dest_to_page2)
    if not outline and dest_outline:
        outline = dest_outline
    for item in outline:
        anchor = str(item.get("anchor") or "").lower()
        if not item.get("page") and anchor in dest_to_page:
            item["page"] = dest_to_page[anchor]
    # In UI i salti pagina stanno nel sommario; in «Link» solo http(s)
    uri_only = [
        ln
        for ln in links
        if str(ln.get("href") or "").lower().startswith(("http://", "https://"))
    ]

    has_struct = bool(outline or uri_only)
    res.update(
        {
            "ok": True,
            "title": os.path.basename(file_path),
            "outline": outline[:MAX_OUTLINE],
            "links": uri_only[:MAX_LINKS],
            "body": "",
            "plain": "",
            "has_structure": has_struct,
            "_pdf_pages": pages,
            "_pdf_dest_to_page": dest_to_page,
            "message": (
                f"PDF: {len(outline)} voci di sommario"
                + (f", {len(uri_only)} link web." if uri_only else ".")
                + " Invio sul sommario apre l'app predefinita alla pagina "
                "(se nota) e, dove possibile, va al testo in RTAD."
                if has_struct
                else (
                    "PDF senza sommario/TOC né link URI rilevati. "
                    "Mostro il testo piano se disponibile; "
                    "oppure apri il file con l'app predefinita."
                )
            ),
        }
    )
    return res


def _windows_msedge_exe() -> str:
    for p in (
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
    ):
        if p and os.path.isfile(p):
            return p
    return ""


def _windows_acrobat_exe() -> str:
    for p in (
        os.path.expandvars(r"%ProgramFiles%\Adobe\Acrobat DC\Acrobat\Acrobat.exe"),
        os.path.expandvars(
            r"%ProgramFiles%\Adobe\Acrobat Reader DC\Reader\Acrobat.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Adobe\Acrobat Reader DC\Reader\Acrobat.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles%\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Adobe\Acrobat Reader\Reader\AcroRd32.exe"
        ),
    ):
        if p and os.path.isfile(p):
            return p
    # App Paths / predefinita se è Acrobat
    try:
        import winreg

        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for name in ("Acrobat.exe", "AcroRd32.exe"):
                try:
                    with winreg.OpenKey(
                        root,
                        rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{name}",
                    ) as k:
                        val, _ = winreg.QueryValueEx(k, None)
                        if val and os.path.isfile(str(val)):
                            return str(val)
                except OSError:
                    pass
    except Exception:
        pass
    return ""


def _windows_exe_from_command(cmd: str) -> str:
    """Estrae il .exe da una command line di registro («"C:\\App\\x.exe" "%1"»)."""
    cmd = (cmd or "").strip()
    if not cmd:
        return ""
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        if end > 1:
            return cmd[1:end]
    return cmd.split(" ", 1)[0]


def _windows_assoc_query_pdf_exe() -> str:
    """App reale per .pdf via AssocQueryString (Windows 10/11)."""
    try:
        import ctypes
        from ctypes import wintypes

        # ASSOCSTR_EXECUTABLE = 2
        buf = ctypes.create_unicode_buffer(1024)
        pcch = wintypes.DWORD(1024)
        hr = ctypes.windll.shlwapi.AssocQueryStringW(
            0, 2, ".pdf", "open", buf, ctypes.byref(pcch)
        )
        if hr == 0 and buf.value and os.path.isfile(buf.value):
            return buf.value
    except Exception as e:
        logging.debug(f"_windows_assoc_query_pdf_exe: {e}")
    return ""


def _windows_pdf_progid() -> str:
    """ProgId dell'app predefinita .pdf (UserChoiceLatest / UserChoice / HKCR)."""
    try:
        import winreg

        base = r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf"
        # Win11: UserChoiceLatest\ProgId\ProgId
        for path in (
            base + r"\UserChoiceLatest\ProgId",
            base + r"\UserChoice",
        ):
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
                    try:
                        val, _ = winreg.QueryValueEx(k, "ProgId")
                        if val:
                            return str(val)
                    except OSError:
                        pass
                    try:
                        val, _ = winreg.QueryValueEx(k, None)
                        if val:
                            return str(val)
                    except OSError:
                        pass
            except OSError:
                continue
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r".pdf") as k:
            val, _ = winreg.QueryValueEx(k, None)
            return str(val or "")
    except Exception as e:
        logging.debug(f"_windows_pdf_progid: {e}")
        return ""


def _windows_default_pdf_exe() -> str:
    """Eseguibile dell'app predefinita per .pdf (quella che usa davvero Windows)."""
    if not sys.platform.startswith("win"):
        return ""
    # 1) API ufficiale (affidabile su Win11 anche se HKCR\.pdf è ancora Sonarpad)
    exe = _windows_assoc_query_pdf_exe()
    if exe:
        return exe
    try:
        import winreg

        progid = _windows_pdf_progid()
        if not progid:
            return ""
        with winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT, rf"{progid}\shell\open\command"
        ) as k:
            cmd, _ = winreg.QueryValueEx(k, None)
        exe = _windows_exe_from_command(str(cmd or ""))
        return exe if exe and os.path.isfile(exe) else ""
    except Exception as e:
        logging.debug(f"_windows_default_pdf_exe: {e}")
        return ""


def _windows_sumatra_exe() -> str:
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\SumatraPDF\SumatraPDF.exe"),
        os.path.expandvars(r"%ProgramFiles%\SumatraPDF\SumatraPDF.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\SumatraPDF\SumatraPDF.exe"),
    ]
    # App Paths
    try:
        import winreg

        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(
                    root,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\SumatraPDF.exe",
                ) as k:
                    val, _ = winreg.QueryValueEx(k, None)
                    if val:
                        candidates.insert(0, str(val))
            except OSError:
                pass
    except Exception:
        pass
    # App predefinita .pdf se è Sumatra
    default_exe = _windows_default_pdf_exe()
    if default_exe and "sumatra" in default_exe.lower():
        candidates.insert(0, default_exe)
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    try:
        import shutil

        w = shutil.which("SumatraPDF") or shutil.which("SumatraPDF.exe")
        if w and os.path.isfile(w):
            return w
    except Exception:
        pass
    return ""


def _pdf_launch_ok(cmd: list) -> bool:
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        return True
    except Exception as e:
        logging.debug(f"open_pdf_at_page cmd fallito {cmd[:2]}: {e}")
        return False


def _pdf_exe_kind(exe: str) -> str:
    """'acrobat' | 'sumatra' | '' in base al percorso dell'eseguibile."""
    low = (exe or "").replace("/", "\\").lower()
    if not low:
        return ""
    if "sumatra" in low:
        return "sumatra"
    base = os.path.basename(low)
    if base in ("acrobat.exe", "acrord32.exe", "acrobat_sl.exe"):
        return "acrobat"
    if "adobe\\acrobat" in low or "acrobat reader" in low:
        return "acrobat"
    return ""


def pdf_external_page_jump_reliable() -> bool:
    """True se l'app predefinita .pdf è Sumatra o Acrobat (salto pagina noto)."""
    if not sys.platform.startswith("win"):
        return False
    return bool(_pdf_exe_kind(_windows_default_pdf_exe()))


def open_pdf_at_page(
    file_path: str, page: int, named_dest: str = ""
) -> str:
    """Apre un PDF con l'app predefinita Windows; salto pagina solo se supportato.

    Ritorna: 'page' (salto riuscito), 'file' (aperto senza garanzia pagina), ''.

    Non forza Sumatra/Acrobat se non sono l'app predefinita: ognuno sceglie
    il lettore in Windows. Se la predefinita è Acrobat → /A page=;
    se Sumatra → -page; altrimenti os.startfile (senza pagina).
    """
    if not file_path or not os.path.isfile(file_path):
        return ""
    try:
        page_i = int(page)
    except (TypeError, ValueError):
        page_i = 0
    path = os.path.abspath(file_path)
    dest = (named_dest or "").strip().lstrip("#")
    if dest.lower().startswith("nameddest="):
        dest = dest.split("=", 1)[-1].strip()

    if sys.platform.startswith("win"):
        default_exe = _windows_default_pdf_exe()
        kind = _pdf_exe_kind(default_exe)

        if page_i > 0 and kind == "acrobat" and default_exe:
            open_params = f"page={page_i}"
            if dest:
                open_params = f"page={page_i}|nameddest={dest}"
            if _pdf_launch_ok([default_exe, "/A", open_params, path]):
                return "page"

        if page_i > 0 and kind == "sumatra" and default_exe:
            if _pdf_launch_ok([default_exe, "-page", str(page_i), path]):
                return "page"

        # Qualunque app predefinita (Edge, Acrobat, Sumatra, Foxit, …)
        try:
            os.startfile(path)  # type: ignore[attr-defined]
            return "file"
        except Exception as e:
            logging.debug(f"open_pdf_at_page startfile: {e}")
            return ""

    try:
        uri = pathlib.Path(path).as_uri()
        webbrowser.open(uri + (f"#page={page_i}" if page_i else ""))
        return "page" if page_i else "file"
    except Exception:
        return ""


def extract_document_structure(file_path: str) -> dict:
    """Facade: struttura DOCX/EPUB/PDF; altri formati con messaggio onesto."""
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
        return extract_structure_from_pdf(file_path)
    if ext == ".odt":
        res = _empty_result("odt")
        res["message"] = (
            "Struttura ODT (titoli/link) non ancora supportata. "
            "Il testo piano resta disponibile da «Leggi testo»."
        )
        return res
    return _empty_result(
        message="Formato non supportato per la lettura strutturata (DOCX, EPUB, PDF)."
    )


def format_document_copy(file_path: str, plain_text: str) -> str:
    """Testo da copiare: sommario e link del lettore, poi i capitoli."""
    plain = (plain_text or "").strip()
    ext = os.path.splitext(file_path or "")[1].lower()
    if ext not in (".docx", ".epub", ".pdf", ".doc"):
        return plain
    try:
        struct = extract_document_structure(file_path)
    except Exception:
        return plain
    if not struct or not (struct.get("outline") or struct.get("links")):
        return plain
    merged = dict(struct)
    if plain:
        merged["body"] = plain
        merged["plain"] = plain
    report = format_structure_report(merged).strip()
    return report or plain


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
