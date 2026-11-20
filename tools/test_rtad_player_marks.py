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
    print("OK test_rtad_player_marks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
