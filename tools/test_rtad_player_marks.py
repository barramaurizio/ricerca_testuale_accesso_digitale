# -*- coding: utf-8 -*-
"""Segnalibri media: Ferma salva il punto; rinomina; last_mark."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta

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

        # Stesso nome, file nuovo: i segnalibri del file precedente non si offrono.
        with open(media, "wb") as handle:
            handle.write(b"file-nuovo-piu-lungo")
        assert player.last_mark(tmp, media) is None
        assert player.list_marks(tmp, media) == []
        fresh = player.add_mark(tmp, media, 15.0)
        assert player.last_mark(tmp, media)["id"] == fresh["id"]

        # Senza dimensione salvata: conta solo il segnalibro fatto dopo la scrittura del file.
        player.delete_mark(tmp, media, fresh["id"])
        key = player._file_key(media)
        past = (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds")
        recent = datetime.now().isoformat(timespec="seconds")
        store = {
            "marks": {
                key: {
                    "resume_id": "vecchio",
                    "items": [
                        {
                            "id": "vecchio",
                            "sec": 72.0,
                            "name": "1:12",
                            "auto_name": True,
                            "ts": past,
                        },
                        {
                            "id": "di-questo",
                            "sec": 112.0,
                            "name": "1:52",
                            "auto_name": True,
                            "ts": recent,
                        },
                    ],
                }
            }
        }
        with open(os.path.join(tmp, "media_marks.json"), "w", encoding="utf-8") as handle:
            json.dump(store, handle)
        kept = player.list_marks(tmp, media)
        assert [m["id"] for m in kept] == ["di-questo"], kept
        assert player.last_mark(tmp, media)["id"] == "di-questo"
    print("OK test_rtad_player_marks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
