# -*- coding: utf-8 -*-
"""Prove di Whisper sul PC, senza scaricare il modello."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Standalone"))

import rtad_whisper as wh  # noqa: E402


def test_folder_cap_sentence():
    kept, left = wh.cap_folder(["a", "b", "c", "d", "e", "f", "g"])
    assert kept == ["a", "b", "c", "d", "e"]
    assert len(left) == 2
    assert wh.msg_folder_cap(len(kept), 7) == "Whisper: 5 file su 7. Non entrati: 2."
    same, none = wh.cap_folder(["a", "b"])
    assert same == ["a", "b"] and none == []


def test_duration_stops_before_download():
    called = {"n": 0}

    def ensure(**_k):
        called["n"] += 1
        return {"ok": True, "cli": "x", "model": "y", "error": ""}

    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        long = wh.transcribe_file(path, duration_sec=21 * 60, ensure=ensure)
        unknown = wh.transcribe_file(path, duration_sec=0, ensure=ensure)
    finally:
        os.remove(path)
    assert long["error"] == wh.MSG_TOO_LONG
    assert unknown["error"] == wh.MSG_NO_DURATION
    assert called["n"] == 0


def test_json_timestamps_match_translate_lines():
    data = {
        "transcription": [
            {
                "timestamps": {"from": "00:00:01,200", "to": "00:00:04,000"},
                "offsets": {"from": 120, "to": 400},
                "text": " La fisica dei quanti",
            },
            {
                "timestamps": {"from": "00:01:03,000", "to": "00:01:08,000"},
                "offsets": {"from": 6300, "to": 6800},
                "text": " continua qui",
            },
        ]
    }
    text = wh.format_segments(wh.segments_from_json(data), True)
    assert text == "[00:01] La fisica dei quanti\n[01:03] continua qui"
    plain = wh.format_segments(wh.segments_from_json(data), False)
    assert "[" not in plain
    assert "La fisica dei quanti" in plain


def test_transcribe_uses_runner_not_network():
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        def ensure(**_k):
            return {"ok": True, "error": "", "cli": "whisper-cli", "model": "ggml-small.bin"}

        def converter(src, tmp_dir):
            return "", src

        def runner(cmd, should_abort=None):
            assert "-l" in cmd and "auto" in cmd
            assert "-oj" in cmd
            return {
                "code": 0,
                "aborted": False,
                "stdout": "",
                "json": {
                    "transcription": [
                        {"timestamps": {"from": "00:00:02,000"}, "text": "ciao"}
                    ]
                },
            }

        result = wh.transcribe_file(
            path,
            duration_sec=12,
            include_timestamps=True,
            ensure=ensure,
            converter=converter,
            runner=runner,
        )
    finally:
        os.remove(path)
    assert result["ok"], result
    assert result["text"] == "[00:02] ciao"
    assert result["source"] == "whisper"


def test_abort_and_missing_ffmpeg_phrase():
    err, wav = wh._prepare_audio("", "brano.mp3", "out.wav", None)
    assert err == wh.MSG_NEED_FFMPEG and wav == ""
    err_wav, kept = wh._prepare_audio("", "brano.wav", "out.wav", None)
    assert err_wav == "" and kept == "brano.wav"

    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        def ensure(**_k):
            return {"ok": True, "error": "", "cli": "whisper-cli", "model": "m"}

        def runner(cmd, should_abort=None):
            return {"code": -1, "aborted": True, "stdout": ""}

        result = wh.transcribe_file(
            path,
            duration_sec=8,
            ensure=ensure,
            converter=lambda src, tmp: ("", src),
            runner=runner,
        )
    finally:
        os.remove(path)
    assert result["error"] == wh.MSG_INTERRUPTED


def test_sidecar_does_not_overwrite():
    folder = tempfile.mkdtemp()
    media = os.path.join(folder, "libro.mp3")
    side = os.path.join(folder, "libro.rtad.txt")
    with open(media, "wb") as handle:
        handle.write(b"x")
    with open(side, "w", encoding="utf-8") as handle:
        handle.write("gia presente\n")
    body, msg = wh.attach_sidecar("nuovo", media, delete_after=False)
    assert msg == wh.MSG_SIDECAR_KEPT
    assert "gia presente" in Path(side).read_text(encoding="utf-8")
    assert msg in body
    os.remove(side)
    body2, msg2 = wh.attach_sidecar("trascrizione\n", media, delete_after=False)
    assert msg2 == "Testo salvato: libro.rtad.txt"
    assert Path(side).read_text(encoding="utf-8").startswith("trascrizione")
    assert msg2 in body2


if __name__ == "__main__":
    test_folder_cap_sentence()
    test_duration_stops_before_download()
    test_json_timestamps_match_translate_lines()
    test_transcribe_uses_runner_not_network()
    test_abort_and_missing_ffmpeg_phrase()
    test_sidecar_does_not_overwrite()
    print("OK", 6)
