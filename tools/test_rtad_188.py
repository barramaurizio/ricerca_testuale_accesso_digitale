# -*- coding: utf-8 -*-
"""1.8.8: indice MP4 in fondo, ffprobe UTF-8, HTML nel lettore, glossario."""
import json
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Standalone"))

import rtad_media


def _box(typ: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + typ + payload


def _sample_moov() -> bytes:
    mvhd = bytearray(24)
    struct.pack_into(">I", mvhd, 12, 1000)
    struct.pack_into(">I", mvhd, 16, 1339000)
    tkhd = bytearray(16)
    struct.pack_into(">I", tkhd, 8, 1920 << 16)
    struct.pack_into(">I", tkhd, 12, 1080 << 16)
    hdlr = bytearray(12)
    hdlr[8:12] = b"vide"
    return _box(
        b"moov",
        _box(b"mvhd", bytes(mvhd))
        + _box(b"tkhd", bytes(tkhd))
        + _box(b"hdlr", bytes(hdlr)),
    )


def test_moov_after_large_mdat():
    ftyp = _box(b"ftyp", b"isom\x00\x00\x02\x00isom")
    payload = 33 * 1024 * 1024
    mdat_size = 8 + payload
    moov = _sample_moov()
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(ftyp)
            f.write(struct.pack(">I", mdat_size) + b"mdat")
            f.seek(payload - 1, os.SEEK_CUR)
            f.write(b"\x00")
            f.write(moov)
        info = rtad_media._mp4_tech(path)
    finally:
        os.remove(path)
    assert abs(float(info.get("duration_sec") or 0) - 1339.0) < 0.01, info
    assert info.get("frame_width") == 1920, info
    assert info.get("frame_height") == 1080, info
    assert info.get("has_video") is True, info


def test_moov_at_start_still_works():
    moov = _sample_moov()
    mdat = _box(b"mdat", b"\x00" * 32)
    ftyp = _box(b"ftyp", b"isom\x00\x00\x02\x00isom")
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(ftyp + moov + mdat)
        info = rtad_media._mp4_tech(path)
    finally:
        os.remove(path)
    assert abs(float(info.get("duration_sec") or 0) - 1339.0) < 0.01, info
    assert info.get("frame_width") == 1920, info


def test_ffprobe_utf8_filename():
    payload = {
        "format": {"duration": "90.5", "filename": "A \U0001f602.mp4"},
        "streams": [
            {
                "codec_type": "video",
                "width": 1280,
                "height": 720,
                "codec_name": "h264",
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "channels": 2,
                "sample_rate": "48000",
            },
        ],
    }
    raw = json.dumps(payload).encode("utf-8")

    class _Proc:
        returncode = 0
        stdout = raw
        stderr = b""

    orig_which = rtad_media.shutil.which
    orig_run = rtad_media.subprocess.run
    rtad_media.shutil.which = lambda name: "ffprobe" if name == "ffprobe" else None
    rtad_media.subprocess.run = lambda *a, **k: _Proc()
    try:
        info = rtad_media._ffprobe_tech(r"I:\Juve\A \U0001f602.mp4")
    finally:
        rtad_media.shutil.which = orig_which
        rtad_media.subprocess.run = orig_run
    assert abs(float(info.get("duration_sec") or 0) - 90.5) < 0.01, info
    assert info.get("frame_width") == 1280, info
    assert info.get("frame_height") == 720, info
    assert info.get("has_video") is True, info
    assert info.get("audio_codec") == "aac", info


def test_glossary_whole_word():
    rules = [{"find": "Almqvist", "replace": "Alajbegović"}]
    got = rtad_media.apply_transcript_glossary("parla di Almqvist qui", rules)
    assert got == "parla di Alajbegović qui", got
    same = rtad_media.apply_transcript_glossary("Almqvistian resta", rules)
    assert same == "Almqvistian resta", same


def test_html_reader_text():
    import app_gui

    raw = (
        "<html><head><title>Guida</title>"
        "<style>body{color:red}</style>"
        "<script>alert(1)</script></head><body>"
        "<h1>Titolo</h1>"
        "<p>Ciao &#232; l&#8217;entanglement, &#936;.</p>"
        "<ul><li>Uno</li><li>Due</li></ul>"
        "<!-- nascosto -->"
        "</body></html>"
    )
    got = app_gui.strip_html_to_text(raw)
    assert "alert" not in got, got
    assert "color" not in got, got
    assert "<" not in got, got
    assert "&#" not in got, got
    assert "nascosto" not in got, got
    lines = got.split("\n")
    assert "Guida" in lines, lines
    assert "Titolo" in lines, lines
    assert "Ciao è l\u2019entanglement, \u03a8." in lines, lines
    assert "Uno" in lines and "Due" in lines, lines


if __name__ == "__main__":
    test_moov_after_large_mdat()
    test_moov_at_start_still_works()
    test_ffprobe_utf8_filename()
    test_glossary_whole_word()
    test_html_reader_text()
    print("OK 5")
