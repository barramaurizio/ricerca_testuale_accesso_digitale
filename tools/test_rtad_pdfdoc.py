# -*- coding: utf-8 -*-
"""Prove della 2.0.10: pagine da-a, unione, brano."""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_pdfdoc


def check(ok, label):
    if not ok:
        raise SystemExit("FALLITA: " + label)
    print("OK", label)


def main():
    got, err = rtad_pdfdoc.parse_range("", "", 12)
    check(got == (1, 12) and not err, "vuoti: tutto il file")
    got, err = rtad_pdfdoc.parse_range("", "8", 12)
    check(got == (1, 8) and not err, "solo A")
    got, err = rtad_pdfdoc.parse_range("3", "", 12)
    check(got == (3, 12) and not err, "solo Da")
    got, err = rtad_pdfdoc.parse_range("3", "8", 12)
    check(got == (3, 8) and not err, "da-a")
    got, err = rtad_pdfdoc.parse_range("40", "41", 12)
    check(got is None and err == "La pagina 40 non c'è: questo file ne ha 12.", "pagina assente")
    got, err = rtad_pdfdoc.parse_range("8", "3", 12)
    check(got is None and err == rtad_pdfdoc.MSG_ORDER, "inizio dopo la fine")
    got, err = rtad_pdfdoc.parse_range("a", "2", 12)
    check(got is None and err == rtad_pdfdoc.MSG_BAD_NUM, "non è un numero")

    stem = rtad_pdfdoc.union_stem(
        [r"C:\a\Primo.pdf", r"C:\a\Secondo.pdf", r"C:\a\Terzo.pdf"]
    )
    check(stem == "Primo-unione-Secondo-e-3", "nome unione da tre")
    cie = rtad_pdfdoc.PdfRow(r"C:\a\CIE.pdf", 13)
    acer = rtad_pdfdoc.PdfRow(r"C:\a\Acer.pdf", 115)
    acer.ranges.append((1, 8))
    acer.ranges.append((9, 20))
    check(
        rtad_pdfdoc.union_stem_rows([cie, acer])
        == "CIE-pagine-1-13-unione-Acer-pagine-1-8-9-20",
        "nome unione con le pagine",
    )
    terzo = rtad_pdfdoc.PdfRow(r"C:\a\Terzo.pdf", 4)
    check(
        rtad_pdfdoc.union_stem_rows([cie, acer, terzo])
        == "CIE-pagine-1-13-unione-Acer-pagine-1-8-9-20-e-3",
        "nome unione da tre con le pagine",
    )
    check(
        rtad_pdfdoc.pages_stem(r"C:\a\Fattura.pdf", 3, 8) == "Fattura-pagine-3-8",
        "nome pagine",
    )
    check(
        rtad_pdfdoc.ranges_phrase([(1, 8), (9, 20), (21, 30)], 115)
        == "pagine 1-8, 9-20 e 21-30 di 115",
        "tre intervalli",
    )
    check(
        rtad_pdfdoc.pages_stem_many(r"C:\a\Fattura.pdf", [(1, 8), (9, 20)])
        == "Fattura-pagine-1-8-9-20",
        "nome di due intervalli",
    )
    row = rtad_pdfdoc.PdfRow(r"C:\a\Fattura.pdf", 115)
    row.ranges.append((1, 8))
    row.ranges.append((9, 20))
    check(
        row.label().startswith("Fattura.pdf, il file caricato."),
        "il nome in elenco resta il file caricato",
    )

    text, empty = rtad_pdfdoc.join_text_document(
        [("uno.pdf", "ciao"), ("due.pdf", "")]
    )
    check("uno.pdf" in text and "ciao" in text and "due.pdf" in text, "titoli")
    check(rtad_pdfdoc.MSG_NO_TEXT in text and not empty, "una pagina muta non svuota tutto")
    text, empty = rtad_pdfdoc.join_text_document([("scan.pdf", "")])
    check(empty and rtad_pdfdoc.MSG_NO_TEXT in text, "solo scansione")

    ok, sentence, path = rtad_pdfdoc.save_passage("   ", tempfile.gettempdir(), "libro")
    check(not ok and sentence == rtad_pdfdoc.MSG_NO_PASSAGE and not path, "brano vuoto")

    from pypdf import PdfWriter

    folder = tempfile.mkdtemp(prefix="rtad210-")
    src = os.path.join(folder, "Fattura.pdf")
    writer = PdfWriter()
    for _ in range(12):
        writer.add_blank_page(width=200, height=200)
    with open(src, "wb") as handle:
        writer.write(handle)
    total, err = rtad_pdfdoc.page_count(src)
    check(total == 12 and not err, "conta 12 pagine")

    dest = os.path.join(folder, "Fattura-pagine-3-8.pdf")
    ok, sentence, written = rtad_pdfdoc.write_pdf([(src, 3, 8)], dest)
    check(ok and written == dest, "scrive le pagine")
    check("Fattura-pagine-3-8.pdf" in sentence and "6 pagine" in sentence, "frase pagine")
    check("pagine 3-8 di 12" in sentence, "frase con l'intervallo")
    total, err = rtad_pdfdoc.page_count(dest)
    check(total == 6 and not err, "il nuovo PDF ha 6 pagine")
    check(os.path.getsize(src) > 0, "il file di partenza resta")

    other = os.path.join(folder, "Nota.pdf")
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(other, "wb") as handle:
        writer.write(handle)
    merged = os.path.join(folder, "unito.pdf")
    ok, sentence, written = rtad_pdfdoc.write_pdf([(src, 1, 2), (other, 1, 1)], merged)
    check(ok, "unisce due PDF")
    total, err = rtad_pdfdoc.page_count(merged)
    check(total == 3 and not err, "unione da 3 pagine")

    class Row:
        def __init__(self, path, start, end, pages):
            self.path = path
            self.start = start
            self.end = end
            self.pages = pages

    def extract(path):
        return ["testo delle pagine"]

    text_path = os.path.join(folder, "Fattura-testo.txt")
    ok, sentence, written = rtad_pdfdoc.write_text(
        [Row(src, 3, 8, 12)], text_path, extract
    )
    check(ok and os.path.isfile(text_path), "scrive il testo")
    body = open(text_path, encoding="utf-8").read()
    check("Fattura.pdf" in body and "Pagine 3-8 di 12." in body and "testo delle pagine" in body, "titolo, pagine e corpo")
    check("pagine 3-8 di 12" in sentence, "lo stato dice le pagine del testo")
    mute = rtad_pdfdoc.text_done_sentence(
        r"C:\a\scan-testo.txt", True, [("scan.pdf", "l'unica pagina")]
    )
    check(
        "Dentro c'è solo questa frase: Nessun testo in queste pagine." in mute,
        "il testo vuoto dice che il file c'è",
    )
    check(rtad_pdfdoc.pages_word(1) == "1 pagina", "una pagina")
    check(rtad_pdfdoc.pages_word(8) == "8 pagine", "più pagine")

    ok, sentence, written = rtad_pdfdoc.save_passage(
        "il brano", folder, "Fattura"
    )
    check(ok and os.path.basename(written) == "Fattura-selezione.txt", "nome selezione")
    check(open(written, encoding="utf-8").read().strip() == "il brano", "corpo brano")
    print("tutte le prove 2.0.10 ok")


if __name__ == "__main__":
    main()
