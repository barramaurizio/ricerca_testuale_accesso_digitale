# -*- coding: utf-8 -*-
"""PDF e testo.

Pagine da-a, più PDF nell'ordine, testo con il nome del file come titolo.
Un file nuovo, accanto. Quello di partenza non si tocca.
Stessa finestra nella Standalone e nell'Add-on. A schermo e a voce.
Invio e il clic sullo stesso pulsante. Sull'elenco, Invio e il doppio clic
dicono la riga. Un clic solo seleziona la riga.
"""

from __future__ import annotations

import logging
import os
import tempfile
import threading
import time

log = logging.getLogger("rtad.pdfdoc")

MSG_EMPTY = "Nessun file in elenco."
MSG_NO_DONE = "Nessun risultato ancora."
MSG_NO_ASIDE = "Nessun file da parte."
MSG_SELECT = "Seleziona una riga."
MSG_FAIL = "Non sono riuscito a creare il file. Il file di partenza resta com'è."
MSG_READ = "Non sono riuscito a leggere questo PDF. Il file di partenza resta com'è."
MSG_LOCKED = "Questo PDF è protetto. Il file di partenza resta com'è."
MSG_NO_PAGES = "Questo PDF non ha pagine. Il file di partenza resta com'è."
MSG_NEED_TWO = (
    "Per unire i PDF tieni almeno due intervalli sulla stessa riga, "
    "oppure aggiungi un altro PDF."
)
MSG_BAD_NUM = "Servono numeri di pagina. Pagina 1 è la prima del file."
MSG_ORDER = "La pagina di inizio è dopo la fine."
MSG_NO_TEXT = "Nessun testo in queste pagine."
MSG_NOT_PDF = "non è un PDF."
MSG_CLIP_EMPTY = (
    "Negli Appunti non c'è un PDF né una cartella. "
    "In Esplora, Control+C sul file o sulla cartella, poi qui Control+Alt+V. "
    "Oppure trascina il file o la cartella."
)
MSG_DROP_EMPTY = (
    "Nessun PDF. Trascina un PDF o una cartella, "
    "oppure in Esplora Control+C e qui Control+Alt+V."
)
MSG_FOLDER_EMPTY = (
    "Nessun PDF in questa cartella. Le cartelle dentro non si aprono."
)
MSG_NO_PASSAGE = (
    "Nessun testo selezionato. Nel riquadro, Shift e le frecce, "
    "oppure NVDA+F9 e poi NVDA+F10 una volta sola. "
    "Poi Invio sul pulsante Salva la selezione, o un clic."
)
MSG_BUSY = "Lavoro in corso."
MSG_NO_MODULE = "Modulo PDF non disponibile."

_EXTS = {".pdf"}
_WILDCARD = "PDF|*.pdf|Tutti i file|*.*"
_INTRO = (
    "PDF e testo. "
    "Invio sul pulsante Aggiungi file, o un clic, mette i PDF in elenco. "
    "Invio sul pulsante Aggiungi cartella, o un clic, mette i PDF di quella cartella. "
    "Le cartelle che stanno dentro non si aprono. "
    "Trascinare un PDF o una cartella sulla finestra fa la stessa cosa di Control+Alt+V. "
    "In Esplora, Control+C sul file o sulla cartella, poi qui Control+Alt+V, "
    "oppure Invio sul pulsante Incolla, o un clic. "
    "Pagina 1 è la prima del file. "
    "Da e A sono i numeri di pagina. "
    "Se scrivi solo A, il tratto parte dalla prima. "
    "Se scrivi solo Da, il tratto arriva fino all'ultima. "
    "Invio sul pulsante Tieni queste pagine, o un clic, aggiunge l'intervallo sulla riga. "
    "Gli intervalli già tenuti restano. "
    "Cancella Da e A, scrivi un altro intervallo, poi Tieni di nuovo. "
    "Invio sul pulsante Scrivi il PDF, o un clic, scrive tutti gli intervalli della riga selezionata. "
    "Se non hai tenuto niente, entra tutto il file. "
    "Il file si chiama nome-pagine-1-8, oppure nome-pagine-1-8-9-20. "
    "Con almeno due intervalli sulla stessa riga, oppure con almeno due PDF, "
    "Invio sul pulsante Unisci i PDF, o un clic, li mette insieme. "
    "Se su una riga ci sono più intervalli, entrano tutti, nell'ordine in cui li hai tenuti. "
    "Il file unito si chiama nome1-pagine-1-13-unione-nome2-pagine-1-8-9-20. "
    "Nel nome di ogni file ci sono le pagine entrate. "
    "Da tre file in su: i primi due, con le loro pagine, e e-N. "
    "Invio sul pulsante Unisci i testi, o un clic, scrive un testo: "
    "ogni file è un titolo, sotto ci sono le pagine tenute, per esempio pagine 9-20 di 115. Lo Stato dice le stesse pagine. "
    "Vale anche con un solo PDF. "
    "Il file di partenza resta com'è. "
    "Se il nome c'è già, si aggiunge -2. "
    "Lo Stato, la barra di stato e Fatti dicono la stessa frase. "
    "I file creati restano nell'elenco Fatti, con il nome nuovo. "
    "Nell'elenco PDF, nell'ordine, il nome resta quello del file caricato. "
    "Dopo Scrivi o Unisci, la riga torna il file intero. "
    "Per unire il file nuovo, Invio o doppio clic sul fatto lo rimette nell'elenco. "
    "Invio sul pulsante Metti da parte, o un clic, toglie la riga dall'elenco "
    "e la lascia in Da parte. Il file sul disco resta. "
    "Invio o doppio clic su una riga di Da parte la rimette nell'elenco. "
    "Un clic solo seleziona la riga. "
    "Alt+P legge lo Stato di questa finestra: premuto due volte di seguito lo copia. "
    "Dall'elenco, Alt e la lettera del pulsante fa la stessa cosa: "
    "A Aggiungi file, K Aggiungi cartella, H Incolla, S Sposta su, G Sposta giù, "
    "D Metti da parte, T Tieni queste pagine, E Scrivi il PDF, U Unisci i PDF, "
    "Z Unisci i testi. "
    "Esc chiude."
)
_ALT = {
    "A": "add",
    "K": "folder",
    "H": "paste",
    "S": "up",
    "G": "down",
    "D": "aside",
    "T": "keep",
    "E": "write",
    "U": "merge",
    "Z": "text",
}


def page_missing(number: int, total: int) -> str:
    return f"La pagina {number} non c'è: questo file ne ha {total}."


def parse_range(da: str, a: str, total: int) -> tuple:
    """(inizio, fine) inclusi, da 1, oppure (None, frase)."""
    da = (da or "").strip()
    a = (a or "").strip()
    if total < 1:
        return None, MSG_NO_PAGES

    def _num(text: str):
        if not text:
            return None
        if not text.isdigit():
            return False
        return int(text)

    start = _num(da)
    end = _num(a)
    if start is False or end is False:
        return None, MSG_BAD_NUM
    if start is None:
        start = 1
    if end is None:
        end = total
    if start < 1 or start > total:
        return None, page_missing(start, total)
    if end < 1 or end > total:
        return None, page_missing(end, total)
    if start > end:
        return None, MSG_ORDER
    return (start, end), ""


def _name_piece(text: str, max_len: int) -> str:
    raw = (text or "").strip(" .-_")
    if max_len < 8:
        max_len = 8
    if len(raw) <= max_len:
        return raw
    cut = raw[:max_len].rsplit(" ", 1)[0].strip(" .-_")
    return cut or raw[:max_len].strip(" .-_")


def union_stem(paths: list) -> str:
    """Due nomi: a-unione-b. Da tre in su: a-unione-b-e-N."""
    stems = [os.path.splitext(os.path.basename(path))[0] for path in paths]
    if not stems:
        return "Unito"
    if len(stems) == 1:
        return stems[0]
    joiner = "-unione-"
    max_total = 180
    if len(stems) == 2:
        budget = max_total - len(joiner)
        first_room = max(8, budget // 2)
        a = _name_piece(stems[0], first_room)
        b = _name_piece(stems[1], max(8, budget - len(a)))
        return f"{a}{joiner}{b}"
    more = f"-e-{len(stems)}"
    budget = max_total - len(joiner) - len(more)
    first_room = max(8, budget // 2)
    a = _name_piece(stems[0], first_room)
    b = _name_piece(stems[1], max(8, budget - len(a)))
    return f"{a}{joiner}{b}{more}"


def _pages_bits(row) -> str:
    """Numeri di pagina entrati da questa riga: 1-13, oppure 1-8-9-20."""
    ranges = list(row.blocks()) if hasattr(row, "blocks") else []
    total = int(getattr(row, "pages", 0) or 0)
    if not ranges and total:
        return f"1-{total}"
    if len(ranges) == 1 and total and ranges[0] == (1, total):
        return f"1-{total}"
    return "-".join(f"{start}-{end}" for start, end in ranges)


def _union_piece(row, name_room: int) -> str:
    stem = os.path.splitext(os.path.basename(row.path))[0]
    bits = _pages_bits(row)
    name = _name_piece(stem, max(8, name_room))
    if not bits:
        return name
    return f"{name}-pagine-{bits}"


def union_stem_rows(rows) -> str:
    """Due file: nome-pagine-1-13-unione-altro-pagine-1-8-9-20.
    Da tre: i primi due, con le pagine, e e-N.
    """
    rows = list(rows or [])
    if not rows:
        return "Unito"
    if len(rows) == 1:
        return pages_stem_many(rows[0].path, rows[0].blocks())
    joiner = "-unione-"
    max_total = 180
    more = f"-e-{len(rows)}" if len(rows) > 2 else ""
    tail_a = f"-pagine-{_pages_bits(rows[0])}"
    tail_b = f"-pagine-{_pages_bits(rows[1])}"
    budget = max_total - len(joiner) - len(more) - len(tail_a) - len(tail_b)
    if budget < 16:
        budget = 16
    first_room = max(8, budget // 2)
    second_room = max(8, budget - first_room)
    a = _union_piece(rows[0], first_room)
    b = _union_piece(rows[1], second_room)
    return f"{a}{joiner}{b}{more}"


def unique_output(folder: str, stem: str, ext: str) -> str:
    ext = ext if ext.startswith(".") else f".{ext}"
    candidate = os.path.join(folder, stem + ext)
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{stem}-{n}{ext}")
        n += 1
    return candidate


def pages_stem(path: str, start: int, end: int) -> str:
    stem = os.path.splitext(os.path.basename(path))[0]
    return f"{stem}-pagine-{start}-{end}"


def pages_stem_many(path: str, ranges: list) -> str:
    """Un intervallo: nome-pagine-3-8. Più intervalli: nome-pagine-1-8-9-20."""
    if len(ranges) == 1:
        return pages_stem(path, ranges[0][0], ranges[0][1])
    stem = os.path.splitext(os.path.basename(path))[0]
    bits = "-".join(f"{start}-{end}" for start, end in ranges)
    name = f"{stem}-pagine-{bits}"
    if len(name) > 160:
        start, end = ranges[0]
        name = f"{stem}-pagine-{start}-{end}-e-{len(ranges)}"
    return name


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(str(item) for item in value if str(item).strip())
    return str(value)


def join_text_document(blocks: list) -> tuple:
    """(testo, tutto_vuoto). Ogni blocco è (titolo, corpo)."""
    parts = []
    any_text = False
    for title, body in blocks:
        text = (body or "").strip()
        if text:
            any_text = True
            parts.append(f"{title}\n\n{text}")
        else:
            parts.append(f"{title}\n\n{MSG_NO_TEXT}")
    return "\n\n".join(parts).strip() + "\n", not any_text


def range_phrase(start: int, end: int, total: int) -> str:
    """Quali pagine, da dire e da scrivere sotto il nome del file."""
    if start == 1 and end == total:
        if total == 1:
            return "l'unica pagina"
        return f"tutte le {total} pagine"
    return f"pagine {start}-{end} di {total}"


def ranges_phrase(ranges: list, total: int) -> str:
    """Uno o più intervalli della stessa riga."""
    if not ranges:
        return range_phrase(1, total, total)
    if len(ranges) == 1:
        return range_phrase(ranges[0][0], ranges[0][1], total)
    bits = [f"{start}-{end}" for start, end in ranges]
    if len(bits) == 2:
        body = f"{bits[0]} e {bits[1]}"
    else:
        body = ", ".join(bits[:-1]) + " e " + bits[-1]
    return f"pagine {body} di {total}"


def row_blocks(row) -> list:
    method = getattr(row, "blocks", None)
    if callable(method):
        return list(method())
    return [(int(row.start), int(row.end))]


def _details_sentence(details: list) -> str:
    parts = []
    for name, phrase in details:
        parts.append(f"{name}, {phrase}")
    return ". ".join(parts)


def pages_word(n: int) -> str:
    n = int(n)
    if n == 1:
        return "1 pagina"
    return f"{n} pagine"


def pdf_done_sentence(path: str, pages: int, signed: bool, details=None) -> str:
    name = os.path.basename(path)
    sentence = f"Creato {name}, {pages_word(pages)}, nella stessa cartella."
    extra = _details_sentence(details or [])
    if extra:
        sentence += " " + extra + "."
    if signed:
        sentence += " Il file nuovo non porta la firma."
    return sentence


def text_done_sentence(path: str, empty: bool, details=None) -> str:
    name = os.path.basename(path)
    sentence = f"Creato {name}, nella stessa cartella."
    extra = _details_sentence(details or [])
    if extra:
        sentence += " " + extra + "."
    if empty:
        sentence += " Dentro c'è solo questa frase: " + MSG_NO_TEXT
    return sentence


def passage_sentence(path: str) -> str:
    return f"Selezione salvata: {os.path.basename(path)}"


def save_passage(text: str, folder: str, stem: str) -> tuple:
    """Scrive solo il brano. (ok, frase, percorso)."""
    body = (text or "").strip()
    if not body:
        return False, MSG_NO_PASSAGE, ""
    folder = folder or os.getcwd()
    try:
        os.makedirs(folder, exist_ok=True)
        dest = unique_output(folder, f"{stem}-selezione", ".txt")
        with open(dest, "w", encoding="utf-8") as handle:
            handle.write(body)
            if not body.endswith("\n"):
                handle.write("\n")
    except OSError:
        log.exception("save_passage")
        return False, MSG_FAIL, ""
    return True, passage_sentence(dest), dest


def _load_reader(path: str):
    from pypdf import PdfReader

    reader = PdfReader(path)
    if getattr(reader, "is_encrypted", False):
        try:
            opened = reader.decrypt("")
        except Exception:
            opened = 0
        if not opened:
            raise PermissionError(MSG_LOCKED)
    return reader


def page_count(path: str) -> tuple:
    """(numero, frase di errore)."""
    try:
        reader = _load_reader(path)
        total = len(reader.pages)
    except PermissionError:
        return 0, MSG_LOCKED
    except Exception:
        log.exception("page_count %s", path)
        return 0, MSG_READ
    if total < 1:
        return 0, MSG_NO_PAGES
    return total, ""


def has_signature(path: str) -> bool:
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError:
        return False
    if b"/ByteRange" not in raw:
        return False
    return b"/Type /Sig" in raw or b"/Type/Sig" in raw or b"/FT /Sig" in raw or b"/FT/Sig" in raw


def _write_pages(slices: list, dest: str) -> tuple:
    """slices: (path, start, end) da 1, inclusi. (ok, errore, pagine)."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    total = 0
    details = []
    try:
        for path, start, end in slices:
            reader = _load_reader(path)
            count = len(reader.pages)
            if start < 1 or end > count or start > end:
                return False, page_missing(start if start > count else end, count), 0, []
            for index in range(start - 1, end):
                writer.add_page(reader.pages[index])
                total += 1
            details.append(
                (os.path.basename(path), range_phrase(start, end, count))
            )
        if total < 1:
            return False, MSG_NO_PAGES, 0, []
        with open(dest, "wb") as handle:
            writer.write(handle)
    except PermissionError:
        return False, MSG_LOCKED, 0, []
    except Exception:
        log.exception("write pages")
        try:
            if os.path.isfile(dest):
                os.remove(dest)
        except OSError:
            pass
        return False, MSG_FAIL, 0, []
    return True, "", total, details


def write_pdf(slices: list, dest: str) -> tuple:
    """(ok, frase, percorso)."""
    signed = any(has_signature(path) for path, _start, _end in slices)
    ok, err, pages, details = _write_pages(slices, dest)
    if not ok:
        return False, err or MSG_FAIL, ""
    return True, pdf_done_sentence(dest, pages, signed, details), dest


def text_of_slice(path: str, start: int, end: int, total: int, extract) -> str:
    """Testo delle pagine. extract(path) torna righe o una stringa."""
    source = path
    temp = ""
    try:
        if not (start == 1 and end == total):
            fd, temp = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            ok, err, _pages, _details = _write_pages([(path, start, end)], temp)
            if not ok:
                log.info("testo pagine: %s", err)
                return ""
            source = temp
        if extract is not None:
            return _as_text(extract(source)).strip()
        reader = _load_reader(source)
        chunks = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunk for chunk in chunks if chunk.strip()).strip()
    except Exception:
        log.exception("text_of_slice")
        return ""
    finally:
        if temp:
            try:
                os.remove(temp)
            except OSError:
                pass


def write_text(rows: list, dest: str, extract) -> tuple:
    """rows: oggetti con path, start, end, pages. (ok, frase, percorso)."""
    blocks = []
    try:
        details = []
        for row in rows:
            name = os.path.basename(row.path)
            parts = row_blocks(row)
            phrase = ranges_phrase(parts, row.pages)
            heading = f"{name}\n{phrase[:1].upper()}{phrase[1:]}."
            if len(parts) == 1:
                start, end = parts[0]
                body = text_of_slice(row.path, start, end, row.pages, extract)
                blocks.append((heading, body))
            else:
                chunks = []
                any_body = False
                for start, end in parts:
                    bit = range_phrase(start, end, row.pages)
                    line = f"{bit[:1].upper()}{bit[1:]}."
                    body = text_of_slice(row.path, start, end, row.pages, extract)
                    if body:
                        any_body = True
                        chunks.append(f"{line}\n\n{body}")
                    else:
                        chunks.append(f"{line}\n\n{MSG_NO_TEXT}")
                blocks.append((heading, "\n\n".join(chunks) if any_body else ""))
            details.append((name, phrase))
        document, empty = join_text_document(blocks)
        with open(dest, "w", encoding="utf-8") as handle:
            handle.write(document)
    except OSError:
        log.exception("write_text")
        return False, MSG_FAIL, ""
    return True, text_done_sentence(dest, empty, details), dest


def expand_pdf_inputs(paths) -> list:
    from rtad_clip import _files_in_folder

    found = []
    seen = set()
    for raw in paths or []:
        path = (raw or "").strip().strip('"').strip("'")
        if not path:
            continue
        try:
            path = os.path.normpath(path)
        except Exception:
            continue
        if os.path.isdir(path):
            items = _files_in_folder(path, _EXTS)
        elif os.path.isfile(path) and os.path.splitext(path)[1].lower() in _EXTS:
            items = [path]
        else:
            items = []
        for item in items:
            key = os.path.normcase(os.path.abspath(item))
            if key in seen:
                continue
            seen.add(key)
            found.append(item)
    return found


def paths_on_clipboard() -> list:
    import wx

    found = []
    if not wx.TheClipboard.Open():
        return []
    try:
        if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
            data = wx.FileDataObject()
            if wx.TheClipboard.GetData(data):
                found.extend(data.GetFilenames() or [])
        if not found and wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT)):
            data = wx.TextDataObject()
            if wx.TheClipboard.GetData(data):
                found.extend((data.GetText() or "").splitlines())
    except Exception:
        log.exception("clipboard pdf")
    finally:
        try:
            wx.TheClipboard.Close()
        except Exception:
            pass
    return expand_pdf_inputs(found)


class PdfRow:
    def __init__(self, path: str, pages: int, signed: bool = False):
        self.path = path
        self.pages = int(pages)
        self.signed = bool(signed)
        self.ranges = []

    def blocks(self) -> list:
        if not self.ranges:
            return [(1, self.pages)]
        return list(self.ranges)

    def whole(self) -> bool:
        return not self.ranges

    def kept_sentence(self) -> str:
        return ranges_phrase(self.blocks(), self.pages)

    def label(self) -> str:
        name = os.path.basename(self.path)
        if self.whole():
            return f"{name}, il file caricato, {pages_word(self.pages)}."
        return (
            f"{name}, il file caricato. "
            f"Pagine tenute: {self.kept_sentence()}."
        )

    def slices(self) -> list:
        return [(self.path, start, end) for start, end in self.blocks()]

    def slice(self) -> tuple:
        return self.slices()[0]


def open_dialog(parent, speaker, paths=None, extract_text=None):
    import wx

    dialog = PdfDialog(parent, speaker, paths or [], extract_text)
    dialog.ShowModal()
    dialog.close_work()
    dialog.Destroy()


class PdfDialog:
    """La classe vera è sotto: wx va importato a finestra aperta."""


def _install_dialog():
    import wx

    class PdfDialog(wx.Dialog):
        def __init__(self, parent, speaker, paths, extract_text):
            super().__init__(
                parent,
                title="PDF e testo",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._speaker = speaker or (lambda _text: None)
            self._extract = extract_text
            self._rows: list[PdfRow] = []
            self._aside: list[PdfRow] = []
            self._done: list[tuple[str, str]] = []
            self._open = True
            self._busy = False
            self._initial = list(paths or [])
            self._alt_p_time = 0.0

            vbox = wx.BoxSizer(wx.VERTICAL)
            intro = wx.TextCtrl(
                self,
                value=_INTRO,
                style=wx.TE_MULTILINE | wx.TE_READONLY,
            )
            intro.SetMinSize((760, 88))
            vbox.Add(intro, 0, wx.EXPAND | wx.ALL, 8)

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "PDF, nell'ordine. "
                        "Il nome resta quello del file caricato. "
                        "Le pagine tenute si leggono sulla stessa riga. "
                        "Il nome nuovo sta in Fatti. "
                        "Invio o doppio clic dice la riga. "
                        "Un clic solo seleziona la riga. "
                        "Pagina 1 è la prima del file."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )
            self.lst = wx.ListBox(self, style=wx.LB_SINGLE)
            self.lst.SetName("PDF")
            self.lst.SetMinSize((760, 110))
            vbox.Add(self.lst, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.lst.Bind(wx.EVT_LISTBOX, self._on_select)
            self.lst.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._say_row())

            nums = wx.FlexGridSizer(1, 4, 6, 8)
            nums.AddGrowableCol(1, 1)
            nums.AddGrowableCol(3, 1)
            self.txt_from = wx.TextCtrl(self)
            self.txt_to = wx.TextCtrl(self)
            self.txt_from.SetName("Da")
            self.txt_to.SetName("A")
            nums.Add(wx.StaticText(self, label="Da"), 0, wx.ALIGN_CENTER_VERTICAL)
            nums.Add(self.txt_from, 1, wx.EXPAND)
            nums.Add(wx.StaticText(self, label="A"), 0, wx.ALIGN_CENTER_VERTICAL)
            nums.Add(self.txt_to, 1, wx.EXPAND)
            vbox.Add(nums, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

            row1 = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_add = wx.Button(self, label="&Aggiungi file…")
            self.btn_folder = wx.Button(self, label="Aggiungi cartella (&K)")
            self.btn_paste = wx.Button(self, label="Incolla (&H)")
            self.btn_up = wx.Button(self, label="Sposta &su")
            self.btn_down = wx.Button(self, label="Sposta &giù")
            self.btn_aside = wx.Button(self, label="Metti da parte (&D)")
            for btn in (
                self.btn_add, self.btn_folder, self.btn_paste,
                self.btn_up, self.btn_down, self.btn_aside,
            ):
                row1.Add(btn, 0, wx.RIGHT, 6)
            vbox.Add(row1, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

            row2 = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_keep = wx.Button(self, label="&Tieni queste pagine")
            self.btn_write = wx.Button(self, label="Scrivi il PDF (&E)")
            self.btn_merge = wx.Button(self, label="&Unisci i PDF")
            self.btn_text = wx.Button(self, label="Unisci i testi (&Z)")
            self.btn_close = wx.Button(self, wx.ID_CANCEL, "Chiudi")
            for btn in (
                self.btn_keep, self.btn_write, self.btn_merge,
                self.btn_text, self.btn_close,
            ):
                row2.Add(btn, 0, wx.RIGHT, 6)
            vbox.Add(row2, 0, wx.ALL, 8)

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Da parte. Invio sul pulsante Metti da parte, o un clic, "
                        "toglie la riga dall'elenco e la lascia qui. "
                        "Il file sul disco resta. "
                        "Invio o doppio clic rimette il file nell'elenco. "
                        "Un clic solo seleziona la riga."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT, 8,
            )
            self.lst_aside = wx.ListBox(self, style=wx.LB_SINGLE)
            self.lst_aside.SetName("Da parte")
            self.lst_aside.SetMinSize((760, 64))
            vbox.Add(self.lst_aside, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.lst_aside.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._on_use_aside())

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Fatti. Invio o doppio clic rimette il file nell'elenco di lavoro. "
                        "Un clic solo seleziona la riga."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT, 8,
            )
            self.lst_done = wx.ListBox(self, style=wx.LB_SINGLE)
            self.lst_done.SetName("Fatti")
            self.lst_done.SetMinSize((760, 80))
            vbox.Add(self.lst_done, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.lst_done.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._on_use_done())

            vbox.Add(wx.StaticText(self, label="Stato"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.txt_status = wx.TextCtrl(
                self, value=MSG_EMPTY, style=wx.TE_READONLY | wx.TE_MULTILINE,
            )
            self.txt_status.SetName("Stato")
            self.txt_status.SetMinSize((760, 72))
            vbox.Add(self.txt_status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self._status_bar = wx.StatusBar(self)
            self._status_bar.SetStatusText(MSG_EMPTY)
            vbox.Add(self._status_bar, 0, wx.EXPAND | wx.ALL, 4)

            self.btn_add.Bind(wx.EVT_BUTTON, self._on_add)
            self.btn_folder.Bind(wx.EVT_BUTTON, self._on_add_folder)
            self.btn_paste.Bind(wx.EVT_BUTTON, self._on_paste)
            self._enable_file_drop()
            self.btn_up.Bind(wx.EVT_BUTTON, lambda e: self._move(-1))
            self.btn_down.Bind(wx.EVT_BUTTON, lambda e: self._move(1))
            self.btn_aside.Bind(wx.EVT_BUTTON, self._on_aside)
            self.btn_keep.Bind(wx.EVT_BUTTON, self._on_keep)
            self.btn_write.Bind(wx.EVT_BUTTON, self._on_write)
            self.btn_merge.Bind(wx.EVT_BUTTON, self._on_merge)
            self.btn_text.Bind(wx.EVT_BUTTON, self._on_text)
            self.Bind(wx.EVT_CHAR_HOOK, self._on_char)
            self.SetSizer(vbox)
            self.SetMinSize((820, 760))
            self.Fit()
            self.Centre()
            self._refresh_aside()
            self._refresh_done()
            self._refresh(-1)
            # Subito, non a finestra già aperta: nel menu di NVDA l'attesa
            # restava dopo la chiusura e l'elenco restava «Nessun file in elenco.»
            self._load_initial()

        def close_work(self):
            self._open = False

        def _say(self, text: str):
            text = (text or "").strip()
            if not text:
                return
            if self._open:
                try:
                    self.txt_status.SetValue(text)
                except Exception:
                    pass
                try:
                    self._status_bar.SetStatusText(text)
                except Exception:
                    pass
            try:
                self._speaker(text)
            except Exception:
                log.info("voce: %s", text)

        def _selected(self) -> int:
            index = self.lst.GetSelection()
            if index == wx.NOT_FOUND or not self._rows:
                return -1
            if index >= len(self._rows):
                return -1
            return index

        def _refresh(self, select: int):
            self.lst.Clear()
            if not self._rows:
                self.lst.Append(MSG_EMPTY)
                self.lst.SetSelection(0)
                self.txt_from.ChangeValue("")
                self.txt_to.ChangeValue("")
                return
            for row in self._rows:
                self.lst.Append(row.label())
            if select < 0 or select >= len(self._rows):
                select = 0
            self.lst.SetSelection(select)
            self._show_fields(select)

        def _show_fields(self, index: int):
            if index < 0 or index >= len(self._rows):
                return
            row = self._rows[index]
            if not row.ranges:
                self.txt_from.ChangeValue("")
                self.txt_to.ChangeValue("")
            else:
                start, end = row.ranges[-1]
                self.txt_from.ChangeValue(str(start))
                self.txt_to.ChangeValue(str(end))

        def _refresh_done(self):
            self.lst_done.Clear()
            if not self._done:
                self.lst_done.Append(MSG_NO_DONE)
                self.lst_done.SetSelection(0)
                return
            for label, _path in self._done:
                self.lst_done.Append(label)
            self.lst_done.SetSelection(len(self._done) - 1)

        def _remember(self, sentence: str, path: str):
            self._done.append((sentence, path))
            self._refresh_done()
            self._say(sentence)

        def _on_select(self, _event=None):
            index = self._selected()
            if index < 0:
                return
            self._show_fields(index)

        def _say_row(self):
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            self._say(self._rows[index].label())

        def _load_initial(self):
            paths = [p for p in self._initial if p]
            self._initial = []
            files = expand_pdf_inputs(paths)
            if files:
                self._ingest(files)
            elif paths:
                self._say(MSG_FOLDER_EMPTY)

        def _take_inputs(self, paths, empty_message: str):
            files = expand_pdf_inputs(paths)
            if not files:
                self._say(empty_message)
                return
            self._ingest(files)

        def _on_paste(self, _event=None):
            self._take_inputs(paths_on_clipboard(), MSG_CLIP_EMPTY)

        def _enable_file_drop(self):
            owner = self

            class _Drop(wx.FileDropTarget):
                def OnDropFiles(self, x, y, filenames):
                    try:
                        owner._take_inputs(filenames or [], MSG_DROP_EMPTY)
                    except Exception:
                        log.exception("OnDropFiles pdf")
                    return True

            for win in (self, self.lst, self.lst_aside, self.lst_done):
                try:
                    win.SetDropTarget(_Drop())
                except Exception:
                    pass

        def _on_add(self, _event=None):
            with wx.FileDialog(
                self,
                "Scegli PDF",
                wildcard=_WILDCARD,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
            ) as fd:
                if fd.ShowModal() != wx.ID_OK:
                    return
                paths = list(fd.GetPaths() or [])
            self._ingest(paths)

        def _on_add_folder(self, _event=None):
            from rtad_clip import _files_in_folder

            with wx.DirDialog(
                self,
                "Scegli la cartella",
                style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
            ) as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                folder = dlg.GetPath()
            paths = _files_in_folder(folder, _EXTS)
            if not paths:
                self._say(MSG_FOLDER_EMPTY)
                return
            self._ingest(paths)

        def _ingest(self, paths):
            added = []
            skipped = []
            for path in paths:
                if os.path.splitext(path)[1].lower() not in _EXTS or not os.path.isfile(path):
                    skipped.append(f"{os.path.basename(path)} {MSG_NOT_PDF}")
                    continue
                total, err = page_count(path)
                if err or total < 1:
                    skipped.append(err or MSG_READ)
                    continue
                added.append(PdfRow(path, total, has_signature(path)))
            if added:
                self._rows.extend(added)
                self._refresh(len(self._rows) - len(added))
                if len(added) == 1 and not skipped:
                    self._say(f"Aggiunto {added[0].label()}")
                else:
                    self._say(f"Aggiunti {len(added)} PDF.")
            if skipped:
                self._say(skipped[0])
                if not self._rows:
                    self.lst.Clear()
                    self.lst.Append(skipped[0])
                    self.lst.SetSelection(0)

        def _move(self, step: int):
            index = self._selected()
            if index < 0:
                self._say(MSG_SELECT if self._rows else MSG_EMPTY)
                return
            other = index + step
            if other < 0 or other >= len(self._rows):
                self._say(self._rows[index].label())
                return
            self._rows[index], self._rows[other] = self._rows[other], self._rows[index]
            self._refresh(other)
            self._say(self._rows[other].label())

        def _refresh_aside(self):
            self.lst_aside.Clear()
            if not self._aside:
                self.lst_aside.Append(MSG_NO_ASIDE)
                self.lst_aside.SetSelection(0)
                return
            for row in self._aside:
                self.lst_aside.Append(row.label())
            self.lst_aside.SetSelection(len(self._aside) - 1)

        def _on_aside(self, _event=None):
            index = self._selected()
            if index < 0:
                self._say(MSG_SELECT if self._rows else MSG_EMPTY)
                return
            row = self._rows.pop(index)
            self._aside.append(row)
            self._refresh(min(index, len(self._rows) - 1))
            self._refresh_aside()
            name = os.path.basename(row.path)
            self._say(
                f"{name} è in Da parte. Il file sul disco resta. "
                "Invio o doppio clic su quella riga lo rimette nell'elenco. "
                "Un clic solo seleziona la riga."
            )

        def _on_use_aside(self):
            if not self._aside:
                self._say(MSG_NO_ASIDE)
                return
            index = self.lst_aside.GetSelection()
            if index == wx.NOT_FOUND or index >= len(self._aside):
                self._say(MSG_SELECT)
                return
            row = self._aside.pop(index)
            self._rows.append(row)
            self._refresh(len(self._rows) - 1)
            self._refresh_aside()
            self._say(f"Rimesso nell'elenco. {row.label()}")

        def _apply_fields(self, index: int) -> tuple:
            """Aggiunge Da e A alla riga, se sono compilati. (ok, errore)."""
            row = self._rows[index]
            da = self.txt_from.GetValue().strip()
            a = self.txt_to.GetValue().strip()
            if not da and not a:
                return True, ""
            got, err = parse_range(da, a, row.pages)
            if err:
                return False, err
            if got not in row.ranges:
                row.ranges.append(got)
            return True, ""

        def _on_keep(self, _event=None):
            index = self._selected()
            if index < 0:
                self._say(MSG_SELECT if self._rows else MSG_EMPTY)
                return
            row = self._rows[index]
            da = self.txt_from.GetValue().strip()
            a = self.txt_to.GetValue().strip()
            if not da and not a:
                if row.ranges:
                    self._say(
                        "Scrivi Da e A per un altro intervallo. "
                        f"Su questa riga restano: {row.kept_sentence()}."
                    )
                else:
                    self._say(
                        "Scrivi Da e A. Pagina 1 è la prima del file."
                    )
                return
            got, err = parse_range(da, a, row.pages)
            if err:
                self._say(err)
                return
            if got in row.ranges:
                self._say(
                    f"Pagine {got[0]}-{got[1]} già tenute. "
                    f"Su questa riga restano: {row.kept_sentence()}."
                )
                return
            row.ranges.append(got)
            self._refresh(index)
            self._say(
                f"Tenute pagine {got[0]}-{got[1]} di {row.pages}. "
                f"Su questa riga restano: {row.kept_sentence()}. "
                "Restano finché non scrivi o unisci. "
                "Poi il file caricato torna intero e il file nuovo sta in Fatti. "
                "Cancella Da e A, scrivi un altro intervallo, "
                "poi Invio sul pulsante Tieni queste pagine, o un clic."
            )

        def _folder_of(self) -> str:
            return os.path.dirname(os.path.abspath(self._rows[0].path)) or os.getcwd()

        def _run(self, work, phrase: str, reset_rows=None):
            if self._busy:
                self._say(MSG_BUSY)
                return
            self._busy = True
            self._say(phrase)
            used = list(reset_rows or [])

            def _thread():
                try:
                    ok, sentence, path = work()
                except Exception:
                    log.exception("pdf e testo")
                    ok, sentence, path = False, MSG_FAIL, ""
                wx.CallAfter(self._finished, ok, sentence, path, used)

            threading.Thread(target=_thread, daemon=True).start()

        def _loaded_again(self, rows) -> str:
            if not rows:
                return "Il file nuovo è in Fatti."
            if len(rows) == 1:
                row = rows[0]
                name = os.path.basename(row.path)
                return (
                    f"{name} resta nell'elenco, il file caricato, {pages_word(row.pages)}. "
                    "Il file nuovo è in Fatti."
                )
            names = ", ".join(os.path.basename(row.path) for row in rows)
            return (
                f"Restano nell'elenco i file caricati: {names}. "
                "Il file nuovo è in Fatti."
            )

        def _finished(self, ok: bool, sentence: str, path: str, reset_rows=None):
            self._busy = False
            if not self._open:
                return
            if ok and path:
                for row in reset_rows or []:
                    row.ranges = []
                self._refresh(self._selected())
                sentence = f"{sentence} {self._loaded_again(reset_rows)}"
                self._remember(sentence, path)
            else:
                self._say(sentence or MSG_FAIL)

        def _on_write(self, _event=None):
            index = self._selected()
            if index < 0:
                self._say(MSG_SELECT if self._rows else MSG_EMPTY)
                return
            ok_fields, err = self._apply_fields(index)
            if not ok_fields:
                self._say(err)
                return
            row = self._rows[index]
            self._refresh(index)
            dest = unique_output(
                os.path.dirname(os.path.abspath(row.path)) or os.getcwd(),
                pages_stem_many(row.path, row.blocks()),
                ".pdf",
            )
            slices = row.slices()

            def work():
                return write_pdf(slices, dest)

            self._run(work, "Scrivo il PDF.", [row])

        def _prepared_rows(self) -> tuple:
            if not self._rows:
                return None, MSG_EMPTY
            index = self._selected()
            if index >= 0 and (self.txt_from.GetValue().strip() or self.txt_to.GetValue().strip()):
                ok_fields, err = self._apply_fields(index)
                if not ok_fields:
                    return None, err
                self._refresh(index)
            return list(self._rows), ""

        def _on_merge(self, _event=None):
            rows, err = self._prepared_rows()
            if err:
                self._say(err)
                return
            blocks = sum(len(row.blocks()) for row in rows)
            if len(rows) < 2 and blocks < 2:
                self._say(MSG_NEED_TWO)
                return
            if len(rows) == 1:
                stem = pages_stem_many(rows[0].path, rows[0].blocks())
            else:
                stem = union_stem_rows(rows)
            dest = unique_output(self._folder_of(), stem, ".pdf")
            slices = []
            for row in rows:
                slices.extend(row.slices())

            def work():
                return write_pdf(slices, dest)

            self._run(work, "Unisco i PDF.", rows)

        def _on_text(self, _event=None):
            rows, err = self._prepared_rows()
            if err:
                self._say(err)
                return
            if len(rows) == 1:
                stem = os.path.splitext(os.path.basename(rows[0].path))[0] + "-testo"
            else:
                stem = union_stem_rows(rows) + "-testo"
            dest = unique_output(self._folder_of(), stem, ".txt")
            extract = self._extract

            def work():
                return write_text(rows, dest, extract)

            self._run(work, "Scrivo il testo.", rows)

        def _on_use_done(self):
            if not self._done:
                self._say(MSG_NO_DONE)
                return
            index = self.lst_done.GetSelection()
            if index == wx.NOT_FOUND or index >= len(self._done):
                self._say(MSG_SELECT)
                return
            _label, path = self._done[index]
            if not path or not os.path.isfile(path):
                self._say(MSG_FAIL)
                return
            if os.path.splitext(path)[1].lower() != ".pdf":
                self._say(os.path.basename(path))
                return
            self._ingest([path])

        def _on_status_key(self):
            now = time.time()
            last = self._alt_p_time
            self._alt_p_time = now
            try:
                text = (self.txt_status.GetValue() or "").strip()
            except Exception:
                text = ""
            if not text:
                text = MSG_EMPTY
            if now - last < 0.6:
                self._copy_status(text)
                return
            self._say(text)

        def _copy_status(self, text: str):
            ok = False
            try:
                if wx.TheClipboard.Open():
                    try:
                        wx.TheClipboard.SetData(wx.TextDataObject(text))
                        ok = True
                    finally:
                        wx.TheClipboard.Close()
            except Exception:
                ok = False
            phrase = (
                "Stato copiato negli appunti."
                if ok
                else "Impossibile copiare negli appunti."
            )
            self._say(phrase)

            def _back():
                if not self._open:
                    return
                try:
                    current = (self.txt_status.GetValue() or "").strip()
                except Exception:
                    return
                if current != phrase:
                    return
                self.txt_status.SetValue(text)
                try:
                    self._status_bar.SetStatusText(text)
                except Exception:
                    pass

            wx.CallLater(2000, _back)

        def _on_char(self, event):
            key = event.GetKeyCode()
            if (
                event.ControlDown()
                and event.AltDown()
                and not event.ShiftDown()
                and key in (ord("V"), ord("v"))
            ):
                self._on_paste()
                return
            if (
                event.AltDown()
                and not event.ControlDown()
                and not event.ShiftDown()
                and key not in (wx.WXK_F4, wx.WXK_TAB)
            ):
                letter = ""
                if ord("A") <= key <= ord("Z") or ord("a") <= key <= ord("z"):
                    letter = chr(key).upper()
                if letter == "P":
                    self._on_status_key()
                    return
                name = _ALT.get(letter)
                if name:
                    self._alt_do(name)
                    return
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                focused = self.FindFocus()
                if focused is self.lst:
                    self._say_row()
                    return
                if focused is self.lst_aside:
                    self._on_use_aside()
                    return
                if focused is self.lst_done:
                    self._on_use_done()
                    return
            event.Skip()

        def _alt_do(self, name: str):
            if name == "add":
                self._on_add()
            elif name == "folder":
                self._on_add_folder()
            elif name == "paste":
                self._on_paste()
            elif name == "up":
                self._move(-1)
            elif name == "down":
                self._move(1)
            elif name == "aside":
                self._on_aside()
            elif name == "keep":
                self._on_keep()
            elif name == "write":
                self._on_write()
            elif name == "merge":
                self._on_merge()
            elif name == "text":
                self._on_text()

    globals()["PdfDialog"] = PdfDialog


_install_dialog()
