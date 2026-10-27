# -*- coding: utf-8 -*-
"""Segnalibri di lettura: più punti, l'ultimo resta quello della riapertura."""
import json
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Standalone"))
sys.path.insert(0, ROOT)

import rtad_reading_mark as m  # noqa: E402


def main() -> None:
    text = (
        "Copertina\n\n"
        "Capitolo uno. La fisica dei quanti inizia qui.\n"
        "Nel mezzo del libro c'è un altro punto.\n"
        "Fine.\n"
    )
    with tempfile.TemporaryDirectory() as folder:
        first_pos = text.index("La fisica")
        saved = m.put_mark(folder, r"I:\Libri\Libro.epub", text, first_pos)
        assert saved["anchor"].startswith("La fisica")
        got = m.get_mark(folder, r"i:\libri\libro.epub")
        assert got is not None
        found, kind = m.resolve_mark(text, got)
        assert kind == "exact" and found == first_pos

        second_pos = text.index("Nel mezzo")
        again = m.add_mark(folder, r"I:\Libri\Libro.epub", text, second_pos)
        assert again["status"] == "added"
        assert again["total"] == 2
        rows = m.describe_items(text, m.get_group(folder, r"I:\Libri\Libro.epub"))
        assert rows[0]["excerpt"].startswith("Capitolo")
        assert rows[1]["excerpt"].startswith("Nel mezzo")
        assert rows[1]["resume"] is True
        assert "2 di 2" in m.resume_sentence("exact", text, second_pos, 2, 2)

        same = m.add_mark(folder, r"I:\Libri\Libro.epub", text, second_pos + 8)
        assert same["status"] == "already"
        assert same["total"] == 2
        assert "c'è già" in m.saved_sentence(2, "Nel mezzo", already=True)

        old = {
            "marks": {
                m.mark_key(r"I:\Libri\Vecchio.epub"): {
                    "pos": first_pos,
                    "anchor": text[first_pos : first_pos + 20],
                    "prefix": "",
                    "saved": "2026-10-27T12:00:00",
                }
            }
        }
        with open(m.store_path(folder), "w", encoding="utf-8") as handle:
            json.dump(old, handle)
        # il libro nuovo non va perso: riscrivo solo il vecchio sopra, quindi rifaccio
        # la migrazione su un file a parte
    with tempfile.TemporaryDirectory() as folder:
        legacy_pos = text.index("La fisica")
        path = m.store_path(folder)
        os.makedirs(folder, exist_ok=True)
        legacy = {
            "marks": {
                m.mark_key(r"I:\Libri\Vecchio.epub"): {
                    "pos": legacy_pos,
                    "anchor": text[legacy_pos : legacy_pos + 40],
                    "prefix": text[max(0, legacy_pos - 20) : legacy_pos],
                    "saved": "2026-10-27T12:00:00",
                }
            }
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(legacy, handle)
        group = m.get_group(folder, r"I:\Libri\Vecchio.epub")
        assert len(group["items"]) == 1
        added = m.add_mark(folder, r"I:\Libri\Vecchio.epub", text, text.index("Fine"))
        assert added["status"] == "added"
        assert added["total"] == 2
        kept = m.describe_items(text, m.get_group(folder, r"I:\Libri\Vecchio.epub"))
        assert any("fisica" in row["excerpt"] for row in kept)
        gone = m.delete_item(folder, r"I:\Libri\Vecchio.epub", added["item"]["id"])
        assert gone == 1
        assert "Ne restano 1" in m.removed_sentence(1, "Fine")
        assert m.get_mark(folder, r"I:\Libri\Vecchio.epub")["id"] == "1"

        assert m.delete_mark(folder, r"I:\Libri\Vecchio.epub") is True
        assert m.get_mark(folder, r"I:\Libri\Vecchio.epub") is None
        assert not os.path.exists(os.path.join(folder, "settings.json"))

    assert "quanti ne vuoi" in m.HINT
    assert "Ctrl+D" in m.HINT
    print("OK 1")


if __name__ == "__main__":
    main()
