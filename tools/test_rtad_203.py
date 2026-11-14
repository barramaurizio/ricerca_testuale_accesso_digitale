# -*- coding: utf-8 -*-
"""Prove della 2.0.3: più immagini da un post."""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_ocr


def check(ok, label):
    if not ok:
        raise SystemExit("FALLITA: " + label)
    print("OK", label)


def main():
    html = """
    <html><head>
    <meta property="og:description" content="Ci siamo! Inaugurate CASA TENNIS e CASA GUSTO oggi">
    <meta property="og:image" content="https://pbs.twimg.com/media/HXA0JYsWEAAudlY?format=webp&amp;name=large">
    </head><body>
    https://pbs.twimg.com/media/HXA0JYsWEAAudlY
    https://pbs.twimg.com/media/HXA0LfmWAAAQq9L
    https://pbs.twimg.com/media/HXA0Lf5XcAA8A-y
    https://pbs.twimg.com/media/HXA0LfpWMAA_Nff
    </body></html>
    """
    urls = rtad_ocr.image_urls_from_html(html)
    check(len(urls) == 4, "quattro immagini dal post")
    check("format=jpg" in urls[0] and "name=large" in urls[0], "jpeg large sulla prima")
    check(urls[0] != urls[1], "indirizzi diversi")
    check(rtad_ocr.image_url_from_html(html) == urls[0], "la prima resta image_url_from_html")
    stem = rtad_ocr.suggest_image_save_stem(
        "https://x.com/a/status/1",
        urls[1],
        "Ci siamo! Inaugurate CASA TENNIS e CASA GUSTO oggi",
        image_index=2,
        image_count=4,
    )
    check(stem.endswith(" 2"), "nome con numero: " + stem)
    hint = rtad_ocr.post_images_choice_hint(4)
    check("4 immagini" in hint and "Scarica e descrivi" in hint, "hint con conteggio")
    print("203 OK")


if __name__ == "__main__":
    main()
