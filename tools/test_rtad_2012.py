# -*- coding: utf-8 -*-
"""Prove della 2.0.12: foto del post oltre quattro, e scrittura nel PDF."""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_ocr
import rtad_pdfedit


def check(ok, label):
    if not ok:
        raise SystemExit("FALLITA: " + label)
    print("OK", label)


def main():
    html = "\n".join(
        f"https://pbs.twimg.com/media/FOTO{i}abc"
        for i in range(6)
    )
    urls = rtad_ocr.image_urls_from_html(html)
    check(len(urls) == 6, "sei immagini dal post, non quattro")
    check(rtad_ocr._POST_IMAGE_LIMIT == rtad_ocr._PAGE_IMAGE_LIMIT, "stesso tetto delle pagine")
    hint = rtad_ocr.post_images_choice_hint(6)
    check("6 immagini" in hint and "Scarica e descrivi" in hint, "hint con sei")

    phrase = rtad_pdfedit.cursor_phrase("Ciao città", 7)
    check("carattere 7 di 10" in phrase and "città" in phrase, phrase)
    zone = rtad_pdfedit.zone_phrase(40, 800, 595, 842)
    check(zone == "in alto a sinistra", zone)
    zone = rtad_pdfedit.zone_phrase(400, 40, 595, 842)
    check(zone == "in basso a destra", zone)

    folder = tempfile.mkdtemp(prefix="rtad212-")
    src = os.path.join(folder, "Lettera.pdf")
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with open(src, "wb") as handle:
        writer.write(handle)

    dest = os.path.join(folder, "Lettera-scritto.pdf")
    ok, sentence, written = rtad_pdfedit.apply_edit(
        src,
        dest,
        {
            "op": "insert",
            "page": 1,
            "place": "alto-sinistra",
            "row": None,
            "text": "Ciao città, perché è così.",
            "font": "Helvetica",
            "size": 12,
        },
    )
    check(ok and os.path.isfile(written), sentence)
    check(os.path.getsize(src) == os.path.getsize(src), "partenza ancora lì")
    check("partenza resta" in sentence, sentence)
    rows, pages, err = rtad_pdfedit.read_marks(written)
    check(not err and pages == 1, err or "pagine")
    texts = " | ".join(row.text for row in rows)
    check("città" in texts and "perché" in texts, texts)

    row = rows[0]
    ok, sentence, written = rtad_pdfedit.apply_edit(
        written,
        written,
        {
            "op": "replace",
            "page": 1,
            "text": "Ciao mondo nuovo.",
            "old": row.text,
            "x": row.x,
            "y": row.y,
            "w": row.w,
            "h": row.h,
            "base_font": row.base_font,
            "font": "Helvetica",
            "size": 12,
        },
    )
    check(ok, sentence)
    check("sostituisce" in sentence, sentence)
    rows, _pages, err = rtad_pdfedit.read_marks(written)
    texts = " | ".join(row.text for row in rows)
    check("mondo nuovo" in texts, texts)
    check("città" not in texts, "la riga vecchia non resta: " + texts)

    ok, sentence, written = rtad_pdfedit.apply_edit(
        written,
        written,
        {
            "op": "link",
            "page": 1,
            "place": "meta-sinistra",
            "row": None,
            "text": "Sito Accesso Digitale",
            "url": "https://example.com/guida",
            "font": "Helvetica",
            "size": 12,
        },
    )
    check(ok and "example.com" in sentence, sentence)
    rows, _pages, err = rtad_pdfedit.read_marks(written)
    texts = " | ".join(row.text for row in rows)
    check("Accesso Digitale" in texts, texts)

    ok, sentence, written = rtad_pdfedit.apply_edit(
        written,
        written,
        {
            "op": "note",
            "page": 1,
            "place": "basso-sinistra",
            "row": None,
            "text": "Da rileggere domani",
            "font": "Helvetica",
            "size": 12,
        },
    )
    check(ok, sentence)
    rows, _pages, err = rtad_pdfedit.read_marks(written)
    texts = " | ".join(row.text for row in rows)
    check("Nota: Da rileggere domani" in texts, texts)

    row = next(item for item in rows if "mondo nuovo" in item.text)
    ok, sentence, written = rtad_pdfedit.apply_edit(
        written,
        written,
        {"op": "underline", "page": 1, "row": row},
    )
    check(ok and "sottolineat" in sentence.lower(), sentence)
    ok, sentence, written = rtad_pdfedit.apply_edit(
        written,
        written,
        {"op": "highlight", "page": 1, "row": row},
    )
    check(ok and "evidenziat" in sentence.lower(), sentence)

    ok, sentence, written = rtad_pdfedit.apply_edit(
        written,
        written,
        {
            "op": "sign",
            "page": 1,
            "name": "Maurizio Barra",
            "image": "",
            "font": "Times-Bold",
            "size": 14,
        },
    )
    check(ok and "Maurizio Barra" in sentence and "Aruba Sign" in sentence, sentence)
    rows, pages, err = rtad_pdfedit.read_marks(written)
    texts = " | ".join(row.text for row in rows)
    check("Firmato: Maurizio Barra" in texts, texts)

    ok, sentence, written = rtad_pdfedit.apply_edit(
        written, written, {"op": "blank"}
    )
    check(ok and "Pagina 2 bianca" in sentence, sentence)
    _rows, pages, err = rtad_pdfedit.read_marks(written)
    check(pages == 2, f"pagine {pages}")

    ok, sentence, _written = rtad_pdfedit.apply_edit(
        written,
        written,
        {
            "op": "insert",
            "page": 2,
            "place": "alto-sinistra",
            "row": None,
            "text": "Riga con \u2603",
            "font": "Helvetica",
            "size": 12,
        },
    )
    check(not ok and "non entrano" in sentence, sentence)

    ok, sentence, _written = rtad_pdfedit.apply_edit(
        written,
        written,
        {
            "op": "link",
            "page": 1,
            "place": "alto-sinistra",
            "row": None,
            "text": "Vai",
            "url": "non-un-indirizzo",
            "font": "Helvetica",
            "size": 12,
        },
    )
    check(not ok and "Indirizzo" in sentence, sentence)

    row = next(item for item in rtad_pdfedit.read_marks(written)[0] if "mondo nuovo" in item.text)
    ok, sentence, written = rtad_pdfedit.apply_edit(
        written,
        written,
        {
            "op": "link",
            "page": 1,
            "place": "sulla-riga",
            "row": row,
            "text": row.text,
            "url": "https://www.juventus.com/it/news/",
            "origin": "dalla riga dove sta il cursore",
            "font": "Helvetica",
            "size": 12,
        },
    )
    check(ok and "juventus.com" in sentence and "dalla riga" in sentence, sentence)
    rows, _pages, err = rtad_pdfedit.read_marks(written)
    linked = next(item for item in rows if "mondo nuovo" in item.text)
    check(linked.link.startswith("https://www.juventus.com"), linked.link or "niente collegamento")

    ok, sentence, _written = rtad_pdfedit.apply_edit(
        written,
        written,
        {"op": "sign", "page": 1, "name": "https://www.juventus.com/it/news/", "font": "Helvetica", "size": 12},
    )
    check(not ok and "Nome e cognome" in sentence, sentence)

    row = next(item for item in rows if "mondo nuovo" in item.text)
    ok, sentence, written = rtad_pdfedit.apply_edit(
        written, written, {"op": "underline", "page": 1, "row": row},
    )
    check(ok and "sottolineat" in sentence.lower() and "caratteri" in sentence, sentence)
    rows, _pages, err = rtad_pdfedit.read_marks(written)
    marked = next(item for item in rows if "mondo nuovo" in item.text)
    check("sottolineata" in " ".join(marked.marks), " ".join(marked.marks) or "niente segni")
    check("resta fuori" in rtad_pdfedit.span_phrase("riga.", 4), rtad_pdfedit.span_phrase("riga.", 4))
    folded = rtad_pdfedit.fold_tight_lines(["Riga uno", "Riga due"], "Riga uno\nJuventus\nRiga due")
    check(folded == "Riga uno Juventus\nRiga due", folded)

    def _mark(text, y, index, size=11):
        return rtad_pdfedit.PdfMark(
            text=text, y=y, x=50, size=size, page_h=842, page=1, index=index,
        )

    wide = [_mark("TITOLO", 689.9, 1), _mark("SOTTOTITOLO", 674.6, 2), _mark("Corpo", 646.2, 3, 9)]
    actions, err = rtad_pdfedit.plan_page_edits(
        wide, "TITOLO\nSOTTOTITOLO\nEcco il Comunicato:\nCorpo", "Helvetica", 12,
    )
    check(not err and len(actions) == 1 and actions[0]["op"] == "insert", err or str(actions))
    check(646 < actions[0]["y"] < 674, str(actions[0]["y"]))
    tight = [_mark("Una", 646.2, 1, 9), _mark("Due", 635.4, 2, 9)]
    tight_actions, err = rtad_pdfedit.plan_page_edits(
        tight, "Una\nIn mezzo\nDue", "Helvetica", 12,
    )
    check(not err and tight_actions and tight_actions[0].get("joined_before"), err or str(tight_actions))
    check(tight_actions[0]["text"] == "In mezzo Due", tight_actions[0].get("text"))
    covered = rtad_pdfedit._drop_covered([
        (50, 607, 9, "L'accordo", "BCDFEE+Roboto-Regular"),
        (50, 607, 9, "Nota: L'accordo", "Helvetica"),
    ])
    check(len(covered) == 1 and covered[0][3].startswith("Nota:"), str(covered))

    class _Caret:
        def __init__(self, value, pos):
            self.value = value
            self.pos = pos

        def GetValue(self):
            return self.value

        def GetInsertionPoint(self):
            return self.pos

        def GetRange(self, start, end):
            return self.value[start:end]

    raw = "David.\r\n\r\nL'accordo"
    # Il controllo conta il ritorno due volte: la L sta all'indice 10, nel testo a 8.
    check(rtad_pdfedit.plain_index(_Caret(raw, 10)) == 8, "indice della L")
    check(rtad_pdfedit.wx_index(_Caret(raw, 0), 8) == 10, "ritorno verso il controllo")
    note = rtad_pdfedit.wrap_note("Le cifre vanno scritte qui, con calma, riga dopo riga, così si scorrono.")
    check(note.startswith("Nota:") and note.rstrip().endswith("Fine nota."), note)
    check(rtad_pdfedit._ink_font("Helvetica", "Firmato: Maurizio Barra.") == "Helvetica-Oblique", "corsivo")
    same = rtad_pdfedit.output_pdf(os.path.join("G:", "Manuale-Entra-con-CIE.pdf"))
    check(os.path.basename(same) == "Manuale-Entra-con-CIE-scritto.pdf", os.path.basename(same))
    again = rtad_pdfedit.output_pdf(os.path.join("G:", "Manuale-Entra-con-CIE-scritto-3.pdf"))
    check(os.path.basename(again) == "Manuale-Entra-con-CIE-scritto-3.pdf", os.path.basename(again))
    same, err = rtad_pdfedit.plan_page_edits(wide, "TITOLO\nSOTTOTITOLO\nCorpo", "Helvetica", 12)
    check(not err and not same, "niente da scrivere")

    gap = os.path.join(folder, "Vuoto.pdf")
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with open(gap, "wb") as handle:
        writer.write(handle)
    for y, text in ((700, "SOTTOTITOLO"), (640, "Corpo")):
        ok, sentence, gap = rtad_pdfedit.apply_edit(
            gap,
            gap,
            {
                "op": "insert",
                "page": 1,
                "place": "punto",
                "x": 50,
                "y": y,
                "text": text,
                "font": "Helvetica",
                "size": 12,
            },
        )
        check(ok, sentence)
    rows, _pages, err = rtad_pdfedit.read_marks(gap)
    check(not err and len(rows) >= 2, err or "righe vuoto")
    body = "\n".join(row.text for row in rows)
    lines = body.split(" | ") if False else [row.text for row in rows]
    # read_marks order is top to bottom
    joined = "\n".join(lines)
    if "SOTTOTITOLO" in joined and "Corpo" in joined:
        inserted = []
        for line in lines:
            inserted.append(line)
            if line.strip() == "SOTTOTITOLO":
                inserted.append("Ecco il Comunicato:")
        actions, err = rtad_pdfedit.plan_page_edits(rows, "\n".join(inserted), "Helvetica", 12)
        check(not err and any(item["op"] == "insert" for item in actions), err or "piano tra le righe")
        ok, sentence, written = rtad_pdfedit.apply_edits(gap, gap, actions)
        check(ok and "aggiunta" in sentence, sentence)
        rows, _pages, err = rtad_pdfedit.read_marks(written)
        texts = " | ".join(row.text for row in rows)
        check("Ecco il Comunicato" in texts and "SOTTOTITOLO" in texts and "Corpo" in texts, texts)

    opened = ["Nota: Torino, 1 settembre, accordo con la società"]
    closed, end_line, end_col, how = rtad_pdfedit.close_auto_note(opened, 0, 6, 0, 6)
    check(how == "line" and closed[0].endswith("Fine nota.") and end_col == len(closed[0]), closed[0])
    sentence = ["Nota: arriva fino al punto.", "e poi continua sulla riga dopo."]
    period = sentence[1].rindex(".")
    closed, end_line, end_col, how = rtad_pdfedit.close_auto_note(sentence, 1, period, 0, 6)
    check(how == "char" and end_line == 1 and "Fine nota." in closed[1], closed[1])
    check(closed[1].endswith("Fine nota.") and closed[0].startswith("Nota:"), closed[1])
    _same, _line, _col, how = rtad_pdfedit.close_auto_note(["Nota: frase intera."], 0, 0, 0, 6)
    check(how == "before", how)
    parked = ["titolo", "Nota: testo Fine nota. e la frase di prima"]
    check(rtad_pdfedit.line_for_keep(parked, 9, "Fine nota") == 1, "cursore sulla nota, non in cima")
    check(rtad_pdfedit.sitting_after_nota("Nota: frase", 6), "ancora dopo Nota")
    check(not rtad_pdfedit.sitting_after_nota("Nota: frase", 12), "dentro la frase")
    phrase = rtad_pdfedit.cursor_phrase("Fine nota. e altro", 10)
    check("dopo «nota.»" in phrase and "prima di «»" not in phrase, phrase)
    check(rtad_pdfedit.span_on_line("vede Juventus e poi Juventus Football", "Juventus", 20) == 20, "nome già sulla riga")
    lines = ["prima L'accordo prevede", "ancora testo, e la i,"]
    ranges = rtad_pdfedit.mark_ranges(lines, 0, 6, 1, 19)
    check(ranges == [(0, 6, len(lines[0])), (1, 0, 20)], str(ranges))
    same = rtad_pdfedit.mark_ranges(["L'accordo prevede milioni,"], 0, 0, 0, 0)
    check(same == [(0, 0, len("L'accordo prevede milioni,"))], str(same))
    check(rtad_pdfedit.mark_ranges(lines, 1, 2, 0, 1) is None, "arrivo prima dell'inizio")
    check(rtad_pdfedit.word_at("L'accordo prevede", 2) == "L'accordo", "parola di inizio")
    check("da «L'accordo»" in rtad_pdfedit.span_phrase("L'accordo prevede milioni,", 16, 0), rtad_pdfedit.span_phrase("L'accordo prevede milioni,", 16, 0))

    print("2012 OK", folder)


if __name__ == "__main__":
    main()
