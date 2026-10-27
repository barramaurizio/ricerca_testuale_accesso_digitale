# -*- coding: utf-8 -*-
"""I codici &# dell'EPUB diventano lettere."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Standalone"))

import rtad_docstruct
import rtad_epub


def test_paragraphs_unescape():
    raw = "<p>l&#8217;entanglement &#232; vero, &#936;.</p>"
    got = rtad_epub._strip_html_to_paragraphs(raw)
    assert got == ["l\u2019entanglement \u00e8 vero, \u03a8."], got
    assert "&#" not in got[0]


def test_reader_unescape():
    raw = "misura e l&#8217;entanglement"
    plain = rtad_docstruct._strip_html_text(raw)
    assert plain == "misura e l\u2019entanglement", plain


if __name__ == "__main__":
    test_paragraphs_unescape()
    test_reader_unescape()
    print("OK 2")
