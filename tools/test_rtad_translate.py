# -*- coding: utf-8 -*-
"""Prove della traduzione a pezzi, senza chiamare Gemini."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Standalone"))

import rtad_translate as tr  # noqa: E402


def _fake_ok(piece, language_en, forma, api_key, should_abort=None):
    lines = []
    for line in piece.splitlines():
        matched = tr._TS_LINE_RE.match(line)
        if matched:
            rest = line[matched.end() :].strip()
            lines.append(f"{matched.group(0).strip()} {forma}:{rest}")
        elif line.strip():
            lines.append(f"{forma}:{line.strip()}")
    return "\n".join(lines), "STOP", ""


def test_transcript_keeps_summary_and_timestamps():
    original = (
        "Video: partita.mp4\n\n"
        "=== Riassunto accessibile ===\n\n"
        "Sintesi già in italiano.\n\n"
        "=== Trascrizione (con timestamp) ===\n\n"
        "[00:01] Hello brothers\n"
        "[00:43] The coach is confused\n"
    )
    result = tr.translate_text(original, "it", "key", generate=_fake_ok, max_chars=40)
    assert result["ok"], result
    assert "Sintesi già in italiano." in result["text"]
    assert "=== Traduzione della trascrizione in italiano ===" in result["text"]
    assert "[00:01] italiano:Hello brothers" in result["text"]
    assert "[00:43] italiano:The coach is confused" in result["text"]
    assert result["text"].index("Sintesi") < result["text"].index("Traduzione")
    assert "Hello brothers" in result["text"].split("=== Traduzione")[0]


def test_long_transcript_is_chunked_and_complete():
    lines = [f"[00:{i:02d}] Sentence number {i} about the match" for i in range(30)]
    original = "=== Trascrizione ===\n\n" + "\n".join(lines)
    result = tr.translate_text(original, "it", "key", generate=_fake_ok, max_chars=180)
    assert result["ok"], result
    assert result["status"] == tr.MSG_DONE
    for i in range(30):
        assert f"[00:{i:02d}]" in result["text"]


def test_truncation_splits_and_finishes():
    calls = {"n": 0}

    def generate(piece, language_en, forma, api_key, should_abort=None):
        calls["n"] += 1
        if len(piece) > 80:
            return "solo inizio", "MAX_TOKENS", ""
        return f"{forma}:{piece}", "STOP", ""

    original = "Hello world. " * 40
    result = tr.translate_text(original, "en", "key", generate=generate, max_chars=500)
    assert result["ok"], result
    assert "inglese:" in result["text"]
    assert calls["n"] > 1
    assert "=== Traduzione in inglese ===" in result["text"]


def test_abort_keeps_original_and_partial():
    state = {"n": 0}

    def generate(piece, language_en, forma, api_key, should_abort=None):
        state["n"] += 1
        return f"fatto {state['n']}", "STOP", ""

    def abort():
        return state["n"] >= 1

    original = (
        ("Alpha paragraph is long enough to stand alone. " * 8)
        + "\n\n"
        + ("Beta paragraph is also long enough here. " * 8)
    )
    result = tr.translate_text(
        original, "it", "key", generate=generate, should_abort=abort, max_chars=250
    )
    assert result["aborted"]
    assert result["status"] == tr.MSG_ABORT
    assert "Alpha paragraph is long enough" in result["text"]
    assert "fatto 1" in result["text"]
    assert "fatto 2" not in result["text"]


def test_replace_existing_translation():
    original = "Hello\n\n=== Traduzione in francese ===\n\nBonjour\n"
    assert tr.has_translation(original)
    fresh = tr.strip_translation(original)
    assert "Bonjour" not in fresh
    result = tr.translate_text(original, "it", "key", generate=_fake_ok, max_chars=500)
    assert result["ok"]
    assert "Bonjour" not in result["text"]
    assert "italiano:Hello" in result["text"]


def test_no_transcript_section_body():
    original = "=== Trascrizione ===\n\n(Non disponibile: errore)\n"
    result = tr.translate_text(original, "it", "key", generate=_fake_ok)
    assert result["skipped"]
    assert result["status"] == tr.MSG_NO_TRANSCRIPT
    assert "italiano:" not in result["text"]


def test_missing_key():
    result = tr.translate_text("Hello there", "it", "")
    assert not result["ok"]
    assert result["status"] == tr.MSG_NO_KEY
    assert tr.MSG_NO_KEY in result["text"]


def test_chunk_does_not_split_timestamp_line():
    line = "[00:10] " + ("word " * 80)
    chunks = tr.chunk_text(line + "\n" + "[00:11] next", max_chars=50)
    assert all("[00:10]" not in c or c.startswith("[00:10]") or "\n[00:10]" not in c for c in chunks)
    assert any(c.startswith("[00:10]") for c in chunks)
    assert any("[00:11]" in c for c in chunks)


if __name__ == "__main__":
    test_transcript_keeps_summary_and_timestamps()
    test_long_transcript_is_chunked_and_complete()
    test_truncation_splits_and_finishes()
    test_abort_keeps_original_and_partial()
    test_replace_existing_translation()
    test_no_transcript_section_body()
    test_missing_key()
    test_chunk_does_not_split_timestamp_line()
    print("OK", 8)
