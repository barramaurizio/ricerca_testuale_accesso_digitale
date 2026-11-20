# -*- coding: utf-8 -*-
"""Segnalibri media: Ferma salva il punto; rinomina; last_mark."""
from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_player as player  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        media = os.path.join(tmp, "prova.mp3")
        with open(media, "wb") as handle:
            handle.write(b"x")
        item = player.add_mark(tmp, media, 95.0)
        assert item["name"] == "1:35", item
        assert player.last_mark(tmp, media)["id"] == item["id"]
        assert player.rename_mark(tmp, media, item["id"], "Intervista")
        again = player.last_mark(tmp, media)
        assert again["name"] == "Intervista"
        assert again["auto_name"] is False
        assert player.delete_mark(tmp, media, item["id"])
        assert player.last_mark(tmp, media) is None
        assert player.list_marks(tmp, media) == []

        # Tre segnalibri: l'indice in elenco deve corrispondere al secondo salvato.
        a = player.add_mark(tmp, media, 10.0)
        b = player.add_mark(tmp, media, 65.0)
        c = player.add_mark(tmp, media, 130.0)
        marks = player.list_marks(tmp, media)
        assert [round(float(m["sec"])) for m in marks] == [10, 65, 130], marks
        assert marks[0]["id"] == a["id"]
        assert marks[1]["id"] == b["id"]
        assert marks[2]["id"] == c["id"]
        assert player.mark_row_label(marks[1]) == "1:05"
        assert float(marks[1]["sec"]) == 65.0
        assert player.rename_mark(tmp, media, b["id"], "Capitolo")
        marks = player.list_marks(tmp, media)
        assert player.mark_row_label(marks[1]) == "1:05 — Capitolo"
    print("OK test_rtad_player_marks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
