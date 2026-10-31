# -*- coding: utf-8 -*-
"""Pagine HTML: intestazioni, link, ancore, niente script."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_html_page as hp  # noqa: E402


SAMPLE = """<!DOCTYPE html>
<html><head><title>Prova &amp; pagina</title>
<style>body { color: red }</style>
<script>var x = 1 < 2; alert("nascosto");</script>
</head><body>
<h1 id="inizio">Capitolo uno</h1>
<p>Testo del capitolo. <a href="#fine">Vai alla fine</a></p>
<h2 id="fine">Seconda parte</h2>
<p id="nota">Una nota.</p>
<p><a href="altra.html">Altra pagina</a>
<a href="https://example.com/storia">Sul web</a>
<a href="javascript:void(0)">Non seguire</a>
<a href="file:///C:/Windows/win.ini">File locale</a>
<a href="mailto:a@b.it">Posta</a></p>
</body></html>
"""


class HtmlPageTests(unittest.TestCase):
    def test_headings_links_and_no_script(self):
        page = hp.build_page(SAMPLE, "https://example.com/libro/pagina.html")
        self.assertEqual(page["title"], "Prova & pagina")
        titles = [h["title"] for h in page["headings"]]
        self.assertEqual(titles, ["Capitolo uno", "Seconda parte"])
        self.assertIn("[H1] Capitolo uno", page["body"])
        self.assertIn("[H2] Seconda parte", page["body"])
        self.assertNotIn("nascosto", page["body"])
        self.assertNotIn("color: red", page["body"])
        kinds = {item["text"]: item["kind"] for item in page["links"]}
        self.assertEqual(kinds["Vai alla fine"], "anchor")
        self.assertEqual(kinds["Altra pagina"], "http")
        self.assertEqual(kinds["Sul web"], "http")
        self.assertEqual(kinds["File locale"], "blocked")
        self.assertEqual(kinds["Posta"], "mailto")
        self.assertNotIn("Non seguire", kinds)
        altra = next(item for item in page["links"] if item["text"] == "Altra pagina")
        self.assertEqual(altra["target"], "https://example.com/libro/altra.html")
        self.assertEqual(page["anchors"]["inizio"], "[H1] Capitolo uno")
        self.assertIn("Una nota.", page["anchors"]["nota"])

    def test_local_file_roundtrip(self):
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "pagina.html")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("<h1>Ciao</h1><p><a href='due.html'>Due</a></p>")
        page, err = hp.load_page(path)
        self.assertEqual(err, "")
        self.assertEqual(page["headings"][0]["title"], "Ciao")
        link = page["links"][0]
        self.assertEqual(link["kind"], "file")
        self.assertTrue(link["target"].lower().endswith("due.html"))

    def test_missing_file(self):
        page, err = hp.load_page(os.path.join(tempfile.gettempdir(), "rtad-manca.html"))
        self.assertEqual(page, {})
        self.assertEqual(err, hp.MSG_NOT_FOUND)

    def test_entity_in_heading(self):
        page = hp.build_page("<h1>Citt&#224;</h1>", "https://example.com/")
        self.assertEqual(page["headings"][0]["title"], "Città")

    def test_duplicate_heading_keeps_both_occurrences(self):
        page = hp.build_page(
            "<h3>Stessa</h3><p>mezzo</p><h3>Stessa</h3>",
            "https://example.com/",
        )
        self.assertEqual([item["occ"] for item in page["headings"]], [1, 2])
        self.assertEqual(page["body"].count("[H3] Stessa"), 2)
        second = hp._nth_find(page["body"], "[H3] Stessa", 2)
        self.assertGreater(second, page["body"].find("[H3] Stessa"))

    def test_saved_file_resolves_site_links(self):
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "pagina.html")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(
                '<p><a href="/sito/static/faq.html">FAQ</a> '
                '<a href="/nuova_europa/it/">Europa</a> '
                '<a href="https://meteo.ansa.it/">Meteo</a></p>'
            )
        page, err = hp.load_page(path, page_url="https://www.ansa.it/")
        self.assertEqual(err, "")
        targets = {item["text"]: item["target"] for item in page["links"]}
        self.assertEqual(targets["FAQ"], "https://www.ansa.it/sito/static/faq.html")
        self.assertEqual(targets["Europa"], "https://www.ansa.it/nuova_europa/it/")
        self.assertEqual(targets["Meteo"], "https://meteo.ansa.it/")
        self.assertEqual(page["link_base"], "https://www.ansa.it/")

    def test_canonical_resolves_root_link(self):
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "pagina.html")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(
                '<html><head><link rel="canonical" '
                'href="https://www.ansa.it/sito/notizie/"></head>'
                '<body><a href="/sito/static/faq.html">FAQ</a></body></html>'
            )
        page, err = hp.load_page(path)
        self.assertEqual(err, "")
        self.assertEqual(
            page["links"][0]["target"],
            "https://www.ansa.it/sito/static/faq.html",
        )

    def test_ctrl_pos_and_caret_on_heading(self):
        body_lines = [f"riga {i}" for i in range(1, 281)]
        body_lines[265] = "[H3] MotoGP prova"
        body = "\n".join(body_lines)
        pos = body.find("[H3] MotoGP prova")
        start = hp.text_pos_to_ctrl(body, pos)
        self.assertEqual(start, pos)
        import wx

        app = wx.GetApp() or wx.App()
        frame = wx.Frame(None)
        ctrl = wx.TextCtrl(
            frame,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_AUTO_URL,
        )
        ctrl.SetValue(body)
        end = hp.text_pos_to_ctrl(body, pos + len("[H3] MotoGP prova"))
        ctrl.SetInsertionPoint(start)
        ctrl.SetSelection(start, end)
        self.assertTrue(ctrl.GetStringSelection().startswith("[H3] MotoGP prova"))
        frame.Destroy()

    def test_heading_keeps_its_article_address(self):
        page = hp.build_page(
            "<h3><a href='https://www.ansa.it/notizia.html'>Caro voli</a></h3>"
            "<p><a href='#crediti'>crediti prepagati finiti</a></p>"
            "<p><a href='https://example.com/a'>Cronaca</a></p>"
            "<p>Questa frase è lunga abbastanza da citare il sito "
            "<a href='https://example.com/lunga'>nel mezzo</a>.</p>",
            "https://www.ansa.it/",
        )
        head = page["headings"][0]
        self.assertEqual(head["href"], "https://www.ansa.it/notizia.html")
        self.assertNotIn("notizia.html", page["body"].split("\n")[0])
        self.assertIn("#crediti", page["body"])
        self.assertNotIn("example.com/a", page["body"])
        self.assertIn("https://example.com/lunga", page["body"])
        address, sentence = hp.heading_open_address(head, "https://www.ansa.it/")
        self.assertEqual(address, "https://www.ansa.it/notizia.html")
        self.assertIn("Caro voli", sentence)

    def test_browser_keeps_fragment(self):
        argv = hp.windows_browser_argv(
            "file:///C:/guida.html#crediti"
        )
        if os.name != "nt":
            self.assertEqual(argv, [])
            return
        self.assertTrue(argv)
        self.assertIn("file:///C:/guida.html#crediti", argv)
        self.assertTrue(os.path.isfile(argv[0]))


if __name__ == "__main__":
    unittest.main()
