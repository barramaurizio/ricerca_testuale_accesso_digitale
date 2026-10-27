# -*- coding: utf-8 -*-
"""Segnalibri di lettura: più punti nel testo di uno stesso documento.

Sono distinti dai Segnalibri di percorso (Ctrl+D), che stanno in settings.json.
Qui il file è reading_marks.json. Per ogni documento se ne tengono quanti se ne
segnano, fino a un tetto. Alla riapertura si torna sull'ultimo usato.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime

MSG_NONE = "Nessun segnalibro di lettura per questo documento."
MSG_SAVED = "Segnalibro di lettura salvato. Alla riapertura riprendi da questo."
MSG_REMOVED = "Segnalibro di lettura rimosso."
MSG_EMPTY = "Nessun testo su cui segnare il punto di lettura."
MSG_NOFILE = "Segnalibro di lettura disponibile solo su un file salvato."
MSG_RESUMED = "Segnalibro di lettura: ripreso da qui."
MSG_MOVED = "Segnalibro di lettura: il testo è cambiato, ripreso il punto più vicino."
MSG_ALREADY = "Questo punto di lettura c'è già."
MSG_FULL = (
    "Segnalibri di lettura: massimo 100. Eliminane uno per segnarne un altro."
)
HINT = (
    "Punti di lettura: Control+B ne aggiunge uno, quanti ne vuoi. "
    "Control+Shift+B torna all'ultimo. "
    "Nell'elenco, frecce e Invio scelgono un altro. "
    "Elimina punto di lettura toglie quello selezionato. "
    "Non è il Segnalibro Ctrl+D, che salva un percorso."
)

ANCHOR_LEN = 80
PREFIX_LEN = 40
EXCERPT_LEN = 90
MAX_MARKS = 200
MAX_PER_FILE = 100
SAME_SPOT = 15
_STORE_NAME = "reading_marks.json"


def store_path(config_dir: str) -> str:
    return os.path.join(config_dir, _STORE_NAME)


def mark_key(file_path: str) -> str:
    raw = (file_path or "").strip()
    if not raw:
        return ""
    try:
        return os.path.normcase(os.path.abspath(raw))
    except Exception:
        return os.path.normcase(raw)


def sentence_with_excerpt(base: str, excerpt: str) -> str:
    excerpt = (excerpt or "").strip()
    if excerpt:
        return f"{base} «{excerpt}»"
    return base


def excerpt_at(text: str, pos: int, limit: int = EXCERPT_LEN) -> str:
    text = text or ""
    if not text:
        return ""
    pos = max(0, min(int(pos or 0), len(text)))
    line_start = text.rfind("\n", 0, pos) + 1
    line_end = text.find("\n", pos)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end]
    if not line.strip() and pos < len(text):
        line = text[pos : pos + limit]
    line = re.sub(r"\s+", " ", line).strip()
    if len(line) > limit:
        line = line[: limit - 1].rstrip() + "…"
    return line


def _load(config_dir: str) -> dict:
    path = store_path(config_dir)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("marks"), dict):
            return data
    except Exception:
        pass
    return {"marks": {}}


def _save(config_dir: str, data: dict) -> None:
    os.makedirs(config_dir, exist_ok=True)
    path = store_path(config_dir)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def _stamp(value) -> str:
    if not isinstance(value, dict):
        return ""
    items = value.get("items")
    if isinstance(items, list):
        times = [
            str(item.get("saved") or "")
            for item in items
            if isinstance(item, dict)
        ]
        return max(times) if times else ""
    return str(value.get("saved") or "")


def _trim(marks: dict) -> dict:
    if len(marks) <= MAX_MARKS:
        return marks
    ordered = sorted(marks.items(), key=lambda item: _stamp(item[1]))
    keep = ordered[-MAX_MARKS:]
    return {key: value for key, value in keep}


def _as_group(raw) -> dict:
    """Il formato vecchio era un solo punto. Resta valido e diventa il primo."""
    if not isinstance(raw, dict):
        return {"resume_id": "", "items": []}
    items = raw.get("items")
    if isinstance(items, list):
        clean = []
        for item in items:
            if isinstance(item, dict) and str(item.get("id") or "").strip():
                clean.append(item)
        return {"resume_id": str(raw.get("resume_id") or ""), "items": clean}
    if "pos" in raw or "anchor" in raw:
        item = {
            "id": "1",
            "pos": raw.get("pos") or 0,
            "anchor": raw.get("anchor") or "",
            "prefix": raw.get("prefix") or "",
            "saved": raw.get("saved") or "",
            "excerpt": raw.get("excerpt") or "",
        }
        return {"resume_id": "1", "items": [item]}
    return {"resume_id": "", "items": []}


def get_group(config_dir: str, file_path: str) -> dict:
    key = mark_key(file_path)
    if not key:
        return {"resume_id": "", "items": []}
    return _as_group(_load(config_dir).get("marks", {}).get(key))


def get_mark(config_dir: str, file_path: str):
    """L'ultimo punto usato, per chi riapre il documento."""
    group = get_group(config_dir, file_path)
    items = group.get("items") or []
    if not items:
        return None
    resume = str(group.get("resume_id") or "")
    for item in items:
        if str(item.get("id") or "") == resume:
            return item
    return items[-1]


def _next_id(items) -> str:
    nums = []
    for item in items:
        try:
            nums.append(int(item.get("id")))
        except (TypeError, ValueError):
            continue
    return str((max(nums) if nums else 0) + 1)


def _same_spot(text: str, pos: int, item: dict) -> bool:
    found, kind = resolve_mark(text, item)
    if kind == "empty":
        return False
    left = excerpt_at(text, found)
    right = excerpt_at(text, pos)
    if left and left == right:
        return True
    return abs(int(found) - int(pos)) <= SAME_SPOT


def _write_group(config_dir: str, file_path: str, group: dict) -> None:
    key = mark_key(file_path)
    if not key:
        raise ValueError("Percorso vuoto")
    data = _load(config_dir)
    marks = data.setdefault("marks", {})
    if group.get("items"):
        marks[key] = {
            "resume_id": str(group.get("resume_id") or ""),
            "items": list(group.get("items") or []),
        }
    elif key in marks:
        del marks[key]
    data["marks"] = _trim(marks)
    _save(config_dir, data)


def add_mark(config_dir: str, file_path: str, text: str, pos: int) -> dict:
    key = mark_key(file_path)
    if not key:
        raise ValueError("Percorso vuoto")
    text = text or ""
    pos = max(0, min(int(pos or 0), len(text)))
    group = get_group(config_dir, file_path)
    items = list(group.get("items") or [])
    for item in items:
        if _same_spot(text, pos, item):
            group["resume_id"] = str(item.get("id") or "")
            _write_group(config_dir, file_path, group)
            return {"status": "already", "item": item, "total": len(items)}
    if len(items) >= MAX_PER_FILE:
        return {"status": "full", "item": None, "total": len(items)}
    excerpt = excerpt_at(text, pos)
    record = {
        "id": _next_id(items),
        "pos": pos,
        "anchor": text[pos : pos + ANCHOR_LEN],
        "prefix": text[max(0, pos - PREFIX_LEN) : pos],
        "saved": datetime.now().isoformat(timespec="seconds"),
        "excerpt": excerpt,
    }
    items.append(record)
    group["items"] = items
    group["resume_id"] = record["id"]
    _write_group(config_dir, file_path, group)
    return {"status": "added", "item": record, "total": len(items)}


def put_mark(config_dir: str, file_path: str, text: str, pos: int) -> dict:
    result = add_mark(config_dir, file_path, text, pos)
    if result.get("item"):
        return result["item"]
    raise ValueError(result.get("status") or "full")


def delete_item(config_dir: str, file_path: str, item_id: str) -> int:
    """Toglie un punto. Ritorna quanti ne restano, oppure -1 se non c'era."""
    group = get_group(config_dir, file_path)
    items = list(group.get("items") or [])
    target = None
    kept = []
    for item in items:
        if str(item.get("id") or "") == str(item_id or ""):
            target = item
        else:
            kept.append(item)
    if target is None:
        return -1
    resume = str(group.get("resume_id") or "")
    if resume == str(item_id or "") or resume not in {
        str(item.get("id") or "") for item in kept
    }:
        resume = ""
        if kept:
            try:
                origin = int(target.get("pos") or 0)
            except (TypeError, ValueError):
                origin = 0
            nearest = min(
                kept,
                key=lambda item: abs(int(item.get("pos") or 0) - origin),
            )
            resume = str(nearest.get("id") or "")
    group["items"] = kept
    group["resume_id"] = resume
    _write_group(config_dir, file_path, group)
    return len(kept)


def delete_mark(config_dir: str, file_path: str) -> bool:
    key = mark_key(file_path)
    if not key:
        return False
    data = _load(config_dir)
    marks = data.get("marks") or {}
    if key not in marks:
        return False
    del marks[key]
    data["marks"] = marks
    _save(config_dir, data)
    return True


def touch_resume(config_dir: str, file_path: str, item_id: str) -> bool:
    group = get_group(config_dir, file_path)
    wanted = str(item_id or "")
    if not any(str(item.get("id") or "") == wanted for item in group.get("items") or []):
        return False
    group["resume_id"] = wanted
    _write_group(config_dir, file_path, group)
    return True


def resolve_mark(text: str, mark: dict):
    """Ritorna (posizione, esito). Esito: exact, found, nearest, empty."""
    text = text or ""
    if not text or not isinstance(mark, dict):
        return 0, "empty"
    try:
        pos = int(mark.get("pos") or 0)
    except (TypeError, ValueError):
        pos = 0
    anchor = str(mark.get("anchor") or "")
    prefix = str(mark.get("prefix") or "")
    length = len(text)
    if not anchor:
        return max(0, min(pos, length)), "exact"
    if 0 <= pos <= length and text[pos : pos + len(anchor)] == anchor:
        return pos, "exact"
    hits = []
    start = 0
    while len(hits) < 12:
        found = text.find(anchor, start)
        if found < 0:
            break
        hits.append(found)
        start = found + 1
    if hits:
        if prefix:
            for found in hits:
                before = text[max(0, found - len(prefix)) : found]
                if before == prefix:
                    return found, "found"
        if len(hits) == 1:
            return hits[0], "found"
        return min(hits, key=lambda found: abs(found - pos)), "found"
    return max(0, min(pos, length)), "nearest"


def describe_items(text: str, group: dict) -> list:
    """Punti in ordine di lettura, dal primo nel testo all'ultimo."""
    rows = []
    for item in (group or {}).get("items") or []:
        if not isinstance(item, dict):
            continue
        pos, kind = resolve_mark(text, item)
        excerpt = excerpt_at(text, pos) if text else str(item.get("excerpt") or "")
        rows.append(
            {
                "id": str(item.get("id") or ""),
                "pos": pos,
                "kind": kind,
                "excerpt": excerpt,
                "saved": str(item.get("saved") or ""),
            }
        )
    rows.sort(key=lambda row: (int(row["pos"]), row["id"]))
    resume = str((group or {}).get("resume_id") or "")
    total = len(rows)
    for index, row in enumerate(rows, 1):
        row["index"] = index
        row["total"] = total
        row["resume"] = row["id"] == resume
        shown = row["excerpt"] or "Punto di lettura"
        row["label"] = f"{index}. {shown}"
    return rows


def resume_sentence(kind: str, text: str, pos: int, index: int = 1, total: int = 1) -> str:
    if kind == "empty":
        return MSG_NONE
    if int(total or 1) > 1:
        if kind == "nearest":
            base = (
                f"Segnalibro di lettura {int(index)} di {int(total)}: "
                "il testo è cambiato, ripreso il punto più vicino."
            )
        else:
            base = f"Segnalibro di lettura {int(index)} di {int(total)}: ripreso da qui."
    else:
        base = MSG_MOVED if kind == "nearest" else MSG_RESUMED
    return sentence_with_excerpt(base, excerpt_at(text, pos))


def saved_sentence(total: int, excerpt: str, already: bool = False) -> str:
    total = int(total or 0)
    if already:
        base = MSG_ALREADY if total <= 1 else f"{MSG_ALREADY} Sono {total}."
        return sentence_with_excerpt(base, excerpt)
    if total <= 1:
        return sentence_with_excerpt(MSG_SAVED, excerpt)
    base = (
        f"Segnalibro di lettura salvato. Sono {total}. "
        "Alla riapertura riprendi da questo."
    )
    return sentence_with_excerpt(base, excerpt)


def removed_sentence(remaining: int, excerpt: str = "") -> str:
    remaining = int(remaining or 0)
    if remaining <= 0:
        return MSG_REMOVED
    base = f"{MSG_REMOVED} Ne restano {remaining}."
    return sentence_with_excerpt(base, excerpt)
