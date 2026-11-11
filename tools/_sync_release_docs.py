# -*- coding: utf-8 -*-
"""Sincronizza guida pratica + gemelli e riporta lo stato (uso pre-rilascio)."""
from __future__ import annotations

import filecmp
import html as html_lib
import re
import shutil
import sys
from pathlib import Path

_URL_RE = re.compile(r"https?://[^\s<]+")

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "addon" / "globalPlugins" / "ricerca_testuale" / "lib"


def _write_guide_pages(pratica_html: str) -> None:
    """Le due guide del programma, stesso testo, per GitHub Pages."""
    import rtad_guida_html as guida_html

    app = (ROOT / "Standalone" / "app_gui.py").read_text(encoding="utf-8")
    found = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', app, re.M)
    version = found.group(1) if found else ""
    guide = ROOT / "docs" / "guida"
    guide.mkdir(parents=True, exist_ok=True)
    menu = guida_html.build_guida_html(
        "Ricerca Testuale Accesso Digitale",
        version,
    )
    (guide / "guida.html").write_text(menu, encoding="utf-8")
    (guide / "pratica.html").write_text(pratica_html, encoding="utf-8")
    index = (
        "<!DOCTYPE html>\n"
        '<html lang="it">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>Guide di Ricerca Testuale Accesso Digitale {version}</title>\n"
        "</head>\n<body>\n"
        "<h1>Guide di Ricerca Testuale Accesso Digitale</h1>\n"
        f"<p>Versione {version}. Lo stesso testo di chi ha il programma installato.</p>\n"
        "<ul>\n"
        '<li><a href="guida.html" target="_blank" rel="noopener">Guida completa</a>. '
        "È la guida HTML del menu Aiuto. Invio o un clic la apre in una finestra nuova. "
        "Questa pagina resta aperta.</li>\n"
        '<li><a href="pratica.html" target="_blank" rel="noopener">Guida pratica</a>. '
        "Invio o un clic la apre in una finestra nuova. "
        "Questa pagina resta aperta.</li>\n"
        "</ul>\n</body>\n</html>\n"
    )
    (guide / "index.html").write_text(index, encoding="utf-8")
    print(f"pages guida OK, versione {version}")


def main() -> int:
    src_guida = ROOT / "Standalone" / "rtad_guida_pratica.py"
    dst_guida = LIB / "rtad_guida_pratica.py"
    shutil.copy2(src_guida, dst_guida)

    sys.path.insert(0, str(ROOT / "Standalone"))
    import rtad_guida_pratica as g  # noqa: E402

    text = g.get_guide_text()
    (ROOT / "docs" / "GUIDA_PRATICA.txt").write_text(text, encoding="utf-8")
    body = html_lib.escape(text, quote=False)
    body = _URL_RE.sub(
        lambda m: (
            f'<a href="{m.group(0)}" target="_blank" rel="noopener">'
            f"{m.group(0)}</a>"
        ),
        body,
    )
    html = (
        "<!DOCTYPE html><html lang=it><head><meta charset=utf-8>"
        "<title>Guida pratica</title></head><body><pre>\n"
        + body
        + "\n</pre></body></html>\n"
    )
    (ROOT / "addon" / "doc" / "it" / "guida_pratica.html").write_text(
        html, encoding="utf-8"
    )
    _write_guide_pages(html)

    shutil.copy2(
        ROOT / "Standalone" / "rtad_docstruct.py", LIB / "rtad_docstruct.py"
    )
    shutil.copy2(
        ROOT / "Standalone" / "rtad_reading_mark.py",
        LIB / "rtad_reading_mark.py",
    )
    shutil.copy2(ROOT / "Standalone" / "rtad_chat.py", LIB / "rtad_chat.py")
    shutil.copy2(
        ROOT / "Standalone" / "rtad_translate.py", LIB / "rtad_translate.py"
    )
    shutil.copy2(ROOT / "Standalone" / "rtad_media.py", LIB / "rtad_media.py")
    shutil.copy2(
        ROOT / "Standalone" / "rtad_attach_dialog.py",
        LIB / "rtad_attach_dialog.py",
    )
    shutil.copy2(
        ROOT / "Standalone" / "rtad_picker.py",
        LIB / "rtad_picker.py",
    )
    shutil.copy2(
        ROOT / "Standalone" / "rtad_compare.py", LIB / "rtad_compare.py"
    )
    shutil.copy2(
        ROOT / "Standalone" / "rtad_clip.py", LIB / "rtad_clip.py"
    )
    shutil.copy2(
        ROOT / "Standalone" / "rtad_image.py", LIB / "rtad_image.py"
    )
    shutil.copy2(
        ROOT / "Standalone" / "rtad_convert.py", LIB / "rtad_convert.py"
    )
    shutil.copy2(
        ROOT / "Standalone" / "rtad_html_page.py", LIB / "rtad_html_page.py"
    )
    shutil.copy2(
        ROOT / "Standalone" / "rtad_guida_html.py", LIB / "rtad_guida_html.py"
    )

    pairs = [
        ("rtad_ocr.py", ROOT / "Standalone" / "rtad_ocr.py", LIB / "rtad_ocr.py"),
        ("rtad_media.py", ROOT / "Standalone" / "rtad_media.py", LIB / "rtad_media.py"),
        (
            "rtad_translate.py",
            ROOT / "Standalone" / "rtad_translate.py",
            LIB / "rtad_translate.py",
        ),
        ("rtad_guida_pratica.py", src_guida, dst_guida),
        (
            "rtad_docstruct.py",
            ROOT / "Standalone" / "rtad_docstruct.py",
            LIB / "rtad_docstruct.py",
        ),
        ("rtad_epub.py", ROOT / "Standalone" / "rtad_epub.py", LIB / "rtad_epub.py"),
        (
            "rtad_reading_mark.py",
            ROOT / "Standalone" / "rtad_reading_mark.py",
            LIB / "rtad_reading_mark.py",
        ),
        ("rtad_chat.py", ROOT / "Standalone" / "rtad_chat.py", LIB / "rtad_chat.py"),
        (
            "rtad_attach_dialog.py",
            ROOT / "Standalone" / "rtad_attach_dialog.py",
            LIB / "rtad_attach_dialog.py",
        ),
        (
            "rtad_picker.py",
            ROOT / "Standalone" / "rtad_picker.py",
            LIB / "rtad_picker.py",
        ),
        (
            "rtad_guida_html.py",
            ROOT / "Standalone" / "rtad_guida_html.py",
            LIB / "rtad_guida_html.py",
        ),
        (
            "rtad_compare.py",
            ROOT / "Standalone" / "rtad_compare.py",
            LIB / "rtad_compare.py",
        ),
        (
            "rtad_clip.py",
            ROOT / "Standalone" / "rtad_clip.py",
            LIB / "rtad_clip.py",
        ),
        (
            "rtad_image.py",
            ROOT / "Standalone" / "rtad_image.py",
            LIB / "rtad_image.py",
        ),
        (
            "rtad_convert.py",
            ROOT / "Standalone" / "rtad_convert.py",
            LIB / "rtad_convert.py",
        ),
        (
            "rtad_html_page.py",
            ROOT / "Standalone" / "rtad_html_page.py",
            LIB / "rtad_html_page.py",
        ),
    ]
    all_ok = True
    for name, a, b in pairs:
        ok = filecmp.cmp(a, b, shallow=False)
        print(f"{name}: {'OK' if ok else 'DIFF'}")
        all_ok = all_ok and ok
    print(f"GUIDA sync OK, chars={len(text)}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
