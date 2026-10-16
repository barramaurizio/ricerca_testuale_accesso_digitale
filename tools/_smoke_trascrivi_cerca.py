# -*- coding: utf-8 -*-
"""Smoke Trascrivi e cerca: solo cache (nessuna chiamata Gemini)."""
from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))
import rtad_media  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        media = os.path.join(td, "clip_locale.mp4")
        open(media, "wb").close()
        side = os.path.join(td, "clip_locale.rtad.txt")
        with open(side, "w", encoding="utf-8") as f:
            f.write("Scheda\n[00:12] gol di cross dalla destra\n")
        # Media senza sidecar: non trascritto (max_transcribe=0)
        orphan_media = os.path.join(td, "senza_sidecar.mp3")
        open(orphan_media, "wb").close()

        summary = rtad_media.transcribe_and_search_folder(
            td,
            ["cross"],
            text_matches_fn=lambda text, terms: all(
                t.lower() in (text or "").lower() for t in terms
            ),
            recursive=False,
            max_transcribe=0,
        )
        assert summary["total"] == 2, summary
        assert summary["cache_hits"] == 1, summary
        assert summary["transcribed"] == 0, summary
        assert summary["skipped_limit"] == 1, summary
        assert len(summary["hits"]) >= 1, summary
        assert summary["hits"][0]["via"] == "cache"
        print("TRASCRIVI_CERCA_CACHE_OK", summary["hits"][0]["location_label"])

        # Solo .rtad.txt orfano (niente media) — caso Downloads di Maurizio
        only = tempfile.mkdtemp()
        try:
            orphan = os.path.join(only, "solo_report.rtad.txt")
            with open(orphan, "w", encoding="utf-8") as f:
                f.write("[00:05] Pronto al cross, si muove\n")
            s2 = rtad_media.transcribe_and_search_folder(
                only,
                ["cross"],
                text_matches_fn=lambda text, terms: all(
                    t.lower() in (text or "").lower() for t in terms
                ),
                recursive=False,
                max_transcribe=0,
            )
            assert s2["total"] == 0, s2
            assert s2.get("rtad_txt_total", 0) == 1, s2
            assert s2["cache_hits"] == 1, s2
            assert len(s2["hits"]) >= 1, s2
            print("TRASCRIVI_CERCA_ORPHAN_ONLY_OK", s2["hits"][0]["file_name"])
        finally:
            try:
                os.remove(orphan)
                os.rmdir(only)
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
