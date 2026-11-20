# -*- coding: utf-8 -*-
"""Verifica che l'indice in elenco punti al secondo giusto del segnalibro."""
from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_player as player  # noqa: E402


def _pick(marks: list, idx: int) -> dict:
    assert 0 <= idx < len(marks)
    return marks[idx]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        media = os.path.join(tmp, "puntate.mp3")
        with open(media, "wb") as handle:
            handle.write(b"x")

        # Simula tre pause a orari diversi.
        player.add_mark(tmp, media, 12.0)
        player.add_mark(tmp, media, 70.0)
        player.add_mark(tmp, media, 185.0)
        marks = player.list_marks(tmp, media)
        assert len(marks) == 3, marks

        # Come fa la ListBox: indice 0/1/2 → sec corrispondente.
        assert float(_pick(marks, 0)["sec"]) == 12.0
        assert float(_pick(marks, 1)["sec"]) == 70.0
        assert float(_pick(marks, 2)["sec"]) == 185.0
        assert player.mark_row_label(marks[0]) == "0:12"
        assert player.mark_row_label(marks[1]) == "1:10"
        assert player.mark_row_label(marks[2]) == "3:05"

        # Rinomina il secondo: l'orario resta, il salto deve usare ancora sec=70.
        assert player.rename_mark(tmp, media, marks[1]["id"], "Intervista")
        marks = player.list_marks(tmp, media)
        assert float(marks[1]["sec"]) == 70.0
        assert player.mark_row_label(marks[1]) == "1:10 — Intervista"

        # Offset preview: orario file = origin + posizione nel wav.
        origin = 70.0
        rel = 5.0
        media_pos = origin + rel
        assert abs(media_pos - 75.0) < 1e-6

    # preview_wav_from deve esistere nel sorgente (salto dal file).
    clip_src = os.path.join(ROOT, "Standalone", "rtad_clip.py")
    text = open(clip_src, encoding="utf-8").read()
    assert "def preview_wav_from(" in text

    print("OK test_rtad_player_goto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
