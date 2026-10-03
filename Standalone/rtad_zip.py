# -*- coding: utf-8 -*-
"""RTAD ZIP — ricerca testo dentro archivi .zip (opt-in), gemello SA/Add-on.

Niente dipendenze esterne: solo zipfile della stdlib.
Cerca in membri di testo (txt, md, html, xml, …); non scompatta su disco.
"""

from __future__ import annotations

import logging
import os
import zipfile

MAX_ZIP_BYTES = 80 * 1024 * 1024  # 80 MB archivio
MAX_ZIP_MEMBERS = 400
MAX_ZIP_MEMBER_BYTES = 4 * 1024 * 1024  # 4 MB per file interno
MAX_ZIP_HITS_PER_ARCHIVE = 40

ZIP_TEXT_EXTS = (
    ".txt",
    ".log",
    ".csv",
    ".md",
    ".rtf",
    ".html",
    ".htm",
    ".xml",
    ".json",
    ".jsonl",
    ".yml",
    ".yaml",
    ".ini",
    ".cfg",
    ".conf",
    ".csv",
    ".tsv",
    ".py",
    ".js",
    ".ts",
    ".css",
    ".sql",
    ".bat",
    ".ps1",
    ".sh",
    ".tex",
    ".bib",
)


def _decode_member_bytes(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin1", errors="ignore")


def search_zip_text_members(
    file_path,
    terms,
    *,
    text_matches_terms,
    should_abort=None,
    max_hits=MAX_ZIP_HITS_PER_ARCHIVE,
):
    """Cerca `terms` nei membri testuali di un .zip.

    Restituisce lista di dict:
      member, line_number, snippet
    """
    hits = []
    if not terms:
        return hits
    try:
        size = os.path.getsize(file_path)
    except OSError:
        return hits
    if size <= 0 or size > MAX_ZIP_BYTES:
        return hits

    try:
        zf = zipfile.ZipFile(file_path, "r")
    except Exception as e:
        logging.debug(f"ZIP non leggibile {file_path}: {e}")
        return hits

    try:
        infos = zf.infolist()
        checked = 0
        for info in infos:
            if should_abort and should_abort():
                break
            if info.is_dir():
                continue
            name = info.filename or ""
            # Evita path traversal / directory entry strane
            base = os.path.basename(name.replace("\\", "/"))
            if not base or base.startswith("."):
                continue
            ext = os.path.splitext(base)[1].lower()
            if ext not in ZIP_TEXT_EXTS:
                continue
            if info.file_size > MAX_ZIP_MEMBER_BYTES:
                continue
            checked += 1
            if checked > MAX_ZIP_MEMBERS:
                break
            try:
                raw = zf.read(info)
            except Exception:
                continue
            if len(raw) > MAX_ZIP_MEMBER_BYTES:
                continue
            text = _decode_member_bytes(raw).replace("\x00", "")
            lines = text.split("\n")
            for idx, line in enumerate(lines):
                if should_abort and should_abort():
                    break
                if not text_matches_terms(line, terms):
                    continue
                start_i = max(0, idx - 2)
                end_i = min(len(lines), idx + 3)
                snippet = " ".join(l.strip() for l in lines[start_i:end_i]).strip()
                hits.append(
                    {
                        "member": name.replace("\\", "/"),
                        "line_number": idx + 1,
                        "snippet": snippet or base,
                    }
                )
                if len(hits) >= max_hits:
                    return hits
                break  # una hit per membro basta (come EPUB)
    finally:
        try:
            zf.close()
        except Exception:
            pass
    return hits
