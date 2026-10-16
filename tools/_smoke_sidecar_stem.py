# -*- coding: utf-8 -*-
"""Smoke: report_save_stem locale vs temp URL; search_rtad_txt_file orfano."""
from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

# Import leggero: solo pezzi necessari senza avviare wx GUI
import rtad_media  # noqa: E402


def _load_stem_helpers():
    sa = os.path.join(ROOT, "Standalone", "app_gui.py")
    src = open(sa, encoding="utf-8").read()
    # Prendi _safe_filename_stem, _looks_like_temp_dir, report_save_stem_for_path
    start = src.index("def _safe_filename_stem(")
    end = src.index("\ndef load_auto_save_results_preference(", start)
    chunk = src[start:end]
    ns = {
        "os": os,
        "re": __import__("re"),
        "tempfile": tempfile,
        "rtad_media": rtad_media,
    }
    exec(chunk, ns)
    return ns


def main() -> int:
    ns = _load_stem_helpers()
    stem_fn = ns["report_save_stem_for_path"]

    with tempfile.TemporaryDirectory() as td:
        local = os.path.join(td, "partita_juve_cross.mp4")
        open(local, "wb").close()
        # Sidecar titolo EN (non deve vincere sul file locale)
        meta = {"title": "Juventus vs Inter English Title", "id": "abc123"}
        rtad_media._write_media_source_sidecar(local, meta)
        got = stem_fn(local)
        assert got == "partita_juve_cross", got
        print("LOCAL_STEM_OK", got)

        # Temp URL: titolo EN
        tmp = os.path.join(tempfile.gettempdir(), "rtad_media_xyz789.mp4")
        try:
            open(tmp, "wb").close()
            rtad_media._write_media_source_sidecar(tmp, meta)
            got_tmp = stem_fn(tmp)
            assert "Juventus" in got_tmp or "English" in got_tmp, got_tmp
            print("TEMP_TITLE_OK", got_tmp)
        finally:
            for p in (tmp, tmp + ".rtad_src.json"):
                try:
                    os.remove(p)
                except OSError:
                    pass

        # Orfano .rtad.txt
        orphan = os.path.join(td, "Juventus vs Inter English Title.rtad.txt")
        with open(orphan, "w", encoding="utf-8") as f:
            f.write("Scheda tecnica\n[01:23] gol di cross dalla destra\n")
        hits = rtad_media.search_rtad_txt_file(
            orphan,
            ["cross"],
            text_matches_fn=lambda text, terms: all(
                t.lower() in (text or "").lower() for t in terms
            ),
        )
        assert hits, hits
        assert hits[0].get("timestamp") == "01:23" or "01:23" in (
            hits[0].get("location_label") or ""
        )
        print("ORPHAN_HIT_OK", hits[0].get("location_label"), hits[0].get("snippet")[:60])

    print("SIDECAR_STEM_SMOKE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
