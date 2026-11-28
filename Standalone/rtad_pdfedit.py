# -*- coding: utf-8 -*-
"""Scrivi nel PDF.

Il file di partenza resta com'è. Il file nuovo si chiama nome-scritto.
A schermo e a voce, la stessa frase: pagina, riga, punto sulla pagina,
e dov'è il cursore.
La firma elettronica p7m resta di Aruba Sign. Qui entra il nome scritto,
e se si sceglie un'immagine, anche quella.
"""

from __future__ import annotations

import logging
import os
import re
import time

log = logging.getLogger("rtad.pdfedit")

MSG_EMPTY = "Nessuna riga di testo. Puoi scrivere su una pagina bianca."
MSG_SELECT = "Seleziona una riga."
MSG_READ = "Non sono riuscito a leggere questo PDF. Il file di partenza resta com'è."
MSG_LOCKED = "Questo PDF è protetto. Il file di partenza resta com'è."
MSG_NOT_PDF = "non è un PDF."
MSG_NO_TEXT = "Scrivi il testo nella pagina in modifica, poi Invio sul pulsante, o un clic."
MSG_NO_MODULE = "Modulo Scrivi nel PDF non disponibile."
MSG_FAIL = "Non sono riuscito a scrivere il file. Il file di partenza resta com'è."
MSG_NO_ROOM = (
    "Sotto questa riga non c'è spazio. "
    "Nell'elenco Posto scegli un altro punto, oppure una pagina bianca nuova."
)
MSG_NO_GAP = (
    "Tra la riga {a} e la riga {b} non c'è spazio per un'altra riga. "
    "Si può scrivere dove c'è un vuoto, oppure nell'elenco Posto, con Scritta nuova."
)
MSG_NO_GAP_ABOVE = (
    "Sopra la prima riga non c'è spazio per un'altra riga. "
    "Nell'elenco Posto, Scritta nuova la mette in un altro punto."
)
MSG_NO_GAP_BELOW = (
    "Sotto l'ultima riga non c'è spazio per un'altra riga. "
    "Nell'elenco Posto, Scritta nuova la mette in un altro punto."
)
MSG_BLANK_LINE = (
    "Una riga vuota non entra nel PDF. "
    "Scrivi il testo su quella riga, poi Invio sul pulsante Riscrivi, o un clic."
)
MSG_NOTHING_NEW = (
    "Questa pagina è già scritta nel file. Non c'è altro da aggiungere. "
    "Annotazione, Nota mia, Collegamento e Firma scrivono subito: quello che hai messo c'è già. "
    "Se cambi ancora il testo nella pagina in modifica, "
    "Alt+E, oppure Invio sul pulsante Riscrivi, o un clic, scrive anche quello."
)
MSG_NEW_LINE = (
    "Il cursore è su una riga non ancora scritta nel file. "
    "Invio sul pulsante Riscrivi, o un clic, la scrive. "
    "Evidenzia, Sottolinea e Barra partono dal carattere su cui stai. "
    "Lo stesso tasto, un'altra volta, chiude sul carattere dove arrivi."
)
MSG_NEED_ROW = (
    "Seleziona una riga, oppure nell'elenco Posto scegli un punto della pagina."
)
MSG_BAD_LINK = (
    "Nel campo Indirizzo serve un http o https, "
    "per esempio https://www.juventus.com/it/news/. "
    "Nel campo Nome del sito si scrive il nome, per esempio Juventus. "
    "Poi Alt+W, oppure Invio sul pulsante Collegamento web, o un clic. "
    "Il campo Nome e cognome è la firma, non il collegamento."
)
MSG_BAD_PAGE = "Questa pagina non c'è."
MSG_NEED_NAME = (
    "Scrivi nome e cognome nel campo Nome e cognome, "
    "oppure scegli un'immagine della firma."
)
MSG_NAME_IS_URL = (
    "Nel campo Nome e cognome c'è un indirizzo web. "
    "Quel campo è la firma: nome e cognome, per esempio Maurizio Barra. "
    "Non è il collegamento. "
    "Il collegamento ha due campi suoi, più sopra: Nome del sito, per esempio Juventus, "
    "e Indirizzo, per esempio https://www.juventus.com/it/news/. "
    "Poi Alt+W, oppure Invio sul pulsante Collegamento web, o un clic."
)
MSG_CHAR = "Questi caratteri non entrano nel carattere scelto: {chars}. Non ho scritto."
MSG_NO_IMAGE = "Non sono riuscito a leggere questa immagine."
MSG_NO_PILLOW = (
    "Per mettere l'immagine della firma serve Pillow. "
    "Il nome scritto entra lo stesso, se il campo Nome non è vuoto."
)
MSG_CLIP_EMPTY = (
    "Negli Appunti non c'è un PDF. "
    "In Esplora, Control+C sul file, poi qui Control+Alt+V."
)

_WILDCARD = "PDF|*.pdf|Tutti i file|*.*"
_IMAGE_WILDCARD = (
    "Immagini|*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tif;*.tiff;*.webp|Tutti i file|*.*"
)

_INTRO = (
    "Scrivi nel PDF. "
    "Il file di partenza resta com'è. Il file scritto si chiama nome-scritto. "
    "Se c'è già, si aggiorna quello: non ne nasce un altro. "
    "Esc non scrive. "
    "Pagina 1 è la prima del file. "
    "La pagina, in sola lettura, mostra il testo di questa pagina. "
    "Le frecce e un clic scelgono la riga. "
    "Pagina su e Pagina giù cambiano pagina. "
    "Invio sul pulsante Pagina precedente o Pagina successiva, o un clic, fa la stessa cosa. "
    "Invio o doppio clic sulla pagina porta sulla pagina in modifica. Tab fa la stessa cosa. "
    "La pagina in modifica è la stessa pagina, tutta. "
    "Invio va a capo: si può scrivere tra una riga e l'altra. "
    "Backspace cancella il carattere prima del cursore, Canc quello dopo. "
    "Le frecce e un clic si muovono nel testo. "
    "Pagina, riga e carattere non si dicono da soli. "
    "La lettera S, fuori dalla pagina in modifica, oppure Alt+P, li legge. "
    "Un clic sull'etichetta Stato fa la stessa cosa di Alt+P. "
    "Nella pagina in modifica la lettera S scrive la esse. "
    "La pagina in sola lettura si aggiorna subito, a schermo. "
    "Maiusc+Tab torna sulla pagina. "
    "Se la pagina è modificata e non ancora scritta, lo Stato lo dice. "
    "La stessa frase è a schermo e a voce. "
    "Nell'elenco Posto, freccia su e giù scelgono dove scrivere. "
    "Nell'elenco Carattere, freccia su e giù scelgono il carattere. "
    "Nell'elenco Misura, freccia su e giù scelgono la misura. "
    "Alt+E, oppure Invio sul pulsante Riscrivi, o un clic, salva sempre questa pagina. "
    "Lo Stato dice Salvato, e il nome del file. C'è tutto quello che è in questa pagina. "
    "Dopo una nota, un segno o la firma, il cursore resta dove hai finito. Lo Stato dice prima quello che hai appena fatto, poi la pagina e la riga. "
    "Chiudi non scrive: se c'è qualcosa da scrivere, la prima volta lo dice. "
    "Se tra due righe non c'è spazio per una riga a sé, il testo sta all'inizio della riga dopo, "
    "prima di ciò che c'era, e lo Stato lo dice. "
    "Il collegamento, la nota, la firma, evidenzia, sottolinea e barra usano il punto "
    "dove hai lasciato il cursore nella pagina in modifica, anche dopo Tab o un clic su un pulsante. "
    "Se il carattere del PDF lo permette, la riga di prima viene sostituita. "
    "Altrimenti un rettangolo bianco la copre e sopra resta la scritta nuova: "
    "lo Stato lo dice, perché un lettore potrebbe ancora leggere la riga di prima, sotto. "
    "Invio sul pulsante Scritta nuova, o un clic, aggiunge la riga del cursore nel posto scelto nell'elenco Posto. "
    "Il posto di partenza è sotto la riga selezionata. "
    "Nel campo Nome del sito si scrive il nome, per esempio Juventus, o Juventus Football Club. "
    "Nel campo Indirizzo si scrive l'http, per esempio https://www.juventus.com/it/news/. "
    "Sono due campi del collegamento, non della firma. "
    "Alt+W, oppure Invio sul pulsante Collegamento web, o un clic, mette quel nome dove sta il cursore, "
    "nella pagina in modifica. "
    "Se quel nome è già sulla riga, resta lì e diventa il collegamento. "
    "Nel PDF salvato quelle parole sono cliccabili. "
    "Invio sul pulsante Apri collegamento, o un clic, apre l'indirizzo nel browser. Questa finestra resta aperta. "
    "Alt+J, oppure Invio sul pulsante Annotazione, o un clic, scrive Nota dove sta il cursore, "
    "davanti al testo già scritto. "
    "Se il cursore è su una riga vuota, Nota sta prima di quel testo, e non spezza una parola. "
    "Alt+J un'altra volta, senza spostarsi, oppure Invio sul pulsante Annotazione, o un clic, "
    "scrive Fine nota in fondo a questa riga. "
    "Se la frase continua, si va sull'ultimo carattere da includere, anche più sotto, anche sul punto, "
    "e Alt+J, oppure Invio sul pulsante Annotazione, o un clic, scrive Fine nota dopo quel carattere. "
    "Il cursore resta dopo Fine nota. "
    "Alt+Maiusc+M, oppure Invio sul pulsante Nota mia, o un clic, apre una finestra. "
    "Invio va a capo, così la nota sta su più righe e con le frecce si scorre. "
    "L'ultima riga è Fine nota. "
    "Invio sul pulsante Inserisci, o un clic, la mette dove sta il cursore. "
    "È una nota tua, senza segnare il testo che segue. "
    "Nella pagina in modifica si può cambiare, poi Alt+E la riscrive. "
    "Alt+M resta Strumenti, nella finestra principale. Questa combinazione vale solo qui. "
    "Alt+X, oppure Invio sul pulsante Evidenzia, o un clic, segna l'inizio dove sta il cursore. "
    "Alt+X un'altra volta, sul carattere dove vuoi arrivare, anche più sotto, "
    "colora di giallo da quella parola fino a quel carattere, incluso. "
    "Se non ti sposti, il giallo arriva in fondo a questa riga. "
    "Il carattere dopo resta fuori. "
    "Per escludere il punto, fermati sulla lettera prima del punto. "
    "Alt+Y Sottolinea e Alt+Maiusc+Z Barra fanno lo stesso. "
    "Alt+Z la prende NVIDIA, la sovrapposizione. "
    "Lo Stato dice la prima parola e l'ultimo carattere. "
    "Nella pagina in sola lettura la stessa parola sta in fondo alla riga, così si legge anche scorrendo. "
    "Nel campo Nome e cognome si scrive la firma, per esempio Maurizio Barra. Non è il collegamento. "
    "Invio sul pulsante Firma, o un clic, la scrive dove sta il cursore, in corsivo. "
    "Nell'elenco Posto, se si sceglie un punto, per esempio in basso a sinistra, la firma va lì. "
    "Se una firma c'è già, lo Stato la dice. "
    "Nella Standalone, Tab sul pulsante Scegli immagine, poi Invio, o un clic, "
    "sceglie un'immagine della firma e la mette in basso a destra. "
    "Sull'Add-on l'immagine non entra: manca Pillow. Il nome scritto entra lo stesso. "
    "La firma elettronica p7m resta di Aruba Sign. "
    "Se il PDF di partenza ha una firma elettronica, il file nuovo non la porta. "
    "Alt+P legge lo Stato di questa finestra: premuto due volte di seguito lo copia. "
    "Nella finestra, Alt e la lettera del pulsante fa la stessa cosa: "
    "O Apri documento, E Riscrivi, U Scritta nuova, W Collegamento web, "
    "J Annotazione, X Evidenzia, Y Sottolinea, D Firma. "
    "Alt+Maiusc+Z è Barra. Alt+Z la prende NVIDIA. "
    "Alt+Maiusc+M è Nota mia. "
    "In Esplora, Control+C sul PDF, poi qui Control+Alt+V. "
    "Trascinare il PDF sulla finestra fa la stessa cosa. "
    "Esc chiude. Se la pagina non è ancora scritta, la prima volta lo dice."
)

_ALT = {
    "O": "open",
    "E": "replace",
    "U": "insert",
    "W": "link",
    "J": "note",
    "X": "highlight",
    "Y": "underline",
    "D": "sign",
}

_MARK_UI = {
    "highlight": ("evidenzia", "Evidenziato", "Alt+X", "Evidenzia"),
    "underline": ("sottolinea", "Sottolineato", "Alt+Y", "Sottolinea"),
    "strike": ("barra", "Barrato", "Alt+Maiusc+Z", "Barra"),
}

PLACES = (
    ("sotto", "Sotto la riga selezionata"),
    ("alto-sinistra", "In alto a sinistra"),
    ("alto-centro", "In alto al centro"),
    ("meta-sinistra", "A metà pagina, a sinistra"),
    ("basso-sinistra", "In basso a sinistra"),
    ("basso-destra", "In basso a destra"),
    ("nuova", "Su una pagina bianca nuova, in alto a sinistra"),
)

FONTS = (
    ("Helvetica", "Helvetica, normale"),
    ("Helvetica-Bold", "Helvetica, grassetto"),
    ("Times-Roman", "Times, normale"),
    ("Times-Bold", "Times, grassetto"),
    ("Courier", "Courier, a spaziatura fissa"),
)

SIZES = (
    (10, "piccolo, 10"),
    (12, "normale, 12"),
    (16, "grande, 16"),
    (22, "titolo, 22"),
)

_STANDARD = {
    "Helvetica",
    "Helvetica-Bold",
    "Helvetica-Oblique",
    "Helvetica-BoldOblique",
    "Times-Roman",
    "Times-Bold",
    "Times-Italic",
    "Times-BoldItalic",
    "Courier",
    "Courier-Bold",
    "Courier-Oblique",
    "Courier-BoldOblique",
}

_MAX_LINES = 4000


def _num(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


class PdfMark:
    """Una riga, con il punto sulla pagina."""

    def __init__(self, **kwargs):
        self.kind = kwargs.get("kind") or "riga"
        self.page = int(kwargs.get("page") or 1)
        self.index = int(kwargs.get("index") or 1)
        self.total = int(kwargs.get("total") or 1)
        self.text = kwargs.get("text") or ""
        self.x = _num(kwargs.get("x"), 50)
        self.y = _num(kwargs.get("y"), 50)
        self.w = _num(kwargs.get("w"), 40)
        self.h = _num(kwargs.get("h"), 12)
        self.size = _num(kwargs.get("size"), 12) or 12
        self.page_w = _num(kwargs.get("page_w"), 595) or 595
        self.page_h = _num(kwargs.get("page_h"), 842) or 842
        self.base_font = kwargs.get("base_font") or ""
        self.field = kwargs.get("field") or ""
        self.preview = None
        self.marks = list(kwargs.get("marks") or [])
        self.link = kwargs.get("link") or ""

    def zone(self) -> str:
        return zone_phrase(self.x, self.y, self.page_w, self.page_h)

    def place_sentence(self) -> str:
        if self.kind == "casella":
            shown = self.text.strip() or "vuota"
            return (
                f"Pagina {self.page}, casella {self.field}, {self.zone()}. "
                f"Valore: {shown}."
            )
        kind = "riga"
        return (
            f"Pagina {self.page}, {kind} {self.index} di {self.total}, "
            f"{self.zone()}."
        )

    def label(self) -> str:
        body = (self.text or "").replace("\n", " ").strip()
        if len(body) > 80:
            body = body[:80].rstrip() + "…"
        if self.kind == "casella":
            return self.place_sentence()
        if not body:
            body = "(vuota)"
        return f"{self.place_sentence()} {body}"


def zone_phrase(x: float, y: float, page_w: float, page_h: float) -> str:
    """Dove sta il punto, in parole."""
    page_w = page_w or 1
    page_h = page_h or 1
    y_ratio = y / page_h
    x_ratio = x / page_w
    if y_ratio >= 0.66:
        vertical = "in alto"
    elif y_ratio >= 0.33:
        vertical = "a metà pagina"
    else:
        vertical = "in basso"
    if x_ratio < 0.33:
        horizontal = "a sinistra"
    elif x_ratio < 0.66:
        horizontal = "al centro"
    else:
        horizontal = "a destra"
    return f"{vertical} {horizontal}"


def looks_web(text: str) -> bool:
    folded = (text or "").strip().lower()
    return folded.startswith("http://") or folded.startswith("https://")


def word_at(text: str, index: int) -> str:
    """La parola che contiene quel carattere."""
    text = text or ""
    if not text:
        return ""
    index = max(0, min(int(index or 0), len(text) - 1))
    left = text.rfind(" ", 0, index)
    right = text.find(" ", index)
    start = 0 if left < 0 else left + 1
    end = len(text) if right < 0 else right
    word = text[start:end].strip(" .,;:!?«»\"'")
    return word or text[index]


def span_phrase(text: str, end=None, start=0) -> str:
    """Dalla parola di inizio fino al carattere di fine, incluso."""
    text = text or ""
    count = len(text)
    start = max(0, min(int(start or 0), count))
    if end is None:
        end = count
    end = max(0, min(int(end), count))
    if end <= start:
        return "nessun carattere"
    last = text[end - 1]
    first = word_at(text, start)
    outside = text[end:end + 1]
    bit = f"{end - start} caratteri su {count}, da «{first}» fino a «{last}»"
    if outside:
        return bit + f". Il carattere dopo, «{outside}», resta fuori"
    return bit + ". Fino all'ultimo carattere, incluso"


def mark_ranges(lines, start_line: int, start_col: int, end_line: int, end_col: int):
    """(riga, inizio, fine esclusa) dal carattere di partenza a quello di arrivo.

    Senza spostarsi, il segno arriva in fondo alla riga. Se l'arrivo è prima
    della partenza, ritorna None.
    """
    lines = list(lines or [])
    if not lines:
        return None
    start_line = max(0, min(int(start_line), len(lines) - 1))
    end_line = max(0, min(int(end_line), len(lines) - 1))
    start_col = max(0, int(start_col))
    end_col = max(0, int(end_col))
    if end_line < start_line or (end_line == start_line and end_col < start_col):
        return None
    ranges = []
    for line in range(start_line, end_line + 1):
        text = lines[line] or ""
        if not text.strip():
            continue
        if line == start_line and end_line == start_line and end_col == start_col:
            ranges.append((line, min(start_col, len(text) - 1), len(text)))
            continue
        if line == start_line and line == end_line:
            begin = min(start_col, max(0, len(text) - 1))
            stop = end_col + 1 if end_col < len(text) else len(text)
            ranges.append((line, begin, max(begin + 1, stop)))
        elif line == start_line:
            begin = min(start_col, max(0, len(text) - 1))
            ranges.append((line, begin, len(text)))
        elif line == end_line:
            stop = end_col + 1 if end_col < len(text) else len(text)
            ranges.append((line, 0, max(1, min(stop, len(text)))))
        else:
            ranges.append((line, 0, len(text)))
    return ranges or None


def wrap_note(text: str, width: int = 78) -> str:
    """Nota su più righe, con Fine nota in fondo. Le frecce possono scorrerle."""
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw.lower().startswith("nota:"):
        raw = "Nota: " + raw
    lines = []
    for para in raw.split("\n"):
        words = para.split()
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            trial = word if not current else current + " " + word
            if current and len(trial) > width:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
    if not lines or lines[-1].strip().lower() != "fine nota.":
        lines.append("Fine nota.")
    return "\n".join(lines)


def sitting_after_nota(text: str, col: int) -> bool:
    """Il cursore è ancora subito dopo Nota:, non dentro la frase."""
    prefix = (text or "")[:max(0, int(col or 0))]
    if "Fine nota" in prefix:
        return False
    folded = prefix.rstrip()
    at = folded.rfind("Nota:")
    if at < 0:
        return False
    return folded[at:].strip() == "Nota:"


def note_caret_find(text: str, col: int) -> str:
    """Un pezzo che si ritrova dopo il salvataggio, per non tornare in cima."""
    text = text or ""
    col = max(0, min(int(col or 0), len(text)))
    if "Fine nota" in text[max(0, col - 24): col + 16] or (
        col >= len(text) and "Fine nota" in text[-24:]
    ):
        return "Fine nota"
    window = text[max(0, col - 24): min(len(text), col + 8)].strip()
    return window or text[:24]


def line_for_keep(lines, keep_line: int, find: str) -> int:
    """La riga del cursore. Se il numero non c'è più, si cerca il testo lasciato lì."""
    lines = list(lines or [])
    count = len(lines)
    if count == 0:
        return 0
    keep_line = int(keep_line or 0)
    if find:
        hits = [index for index, line in enumerate(lines) if find in (line or "")]
        if hits:
            if 0 <= keep_line < count and find in (lines[keep_line] or ""):
                return keep_line
            return min(hits, key=lambda index: (abs(index - keep_line), index))
    if 0 <= keep_line < count:
        return keep_line
    return count - 1


def close_auto_note(lines, line: int, col: int, anchor_line: int, anchor_col: int):
    """(righe, riga, colonna, come). come è line, char o before.

    Senza spostarsi, Fine nota va in fondo alla riga. Spostandosi, dopo il
    carattere su cui sta il cursore, anche righe più sotto.
    """
    lines = list(lines or [""])
    count = len(lines)
    line = max(0, min(int(line), count - 1))
    col = max(0, min(int(col), len(lines[line])))
    anchor_line = int(anchor_line)
    anchor_col = int(anchor_col)
    anchor_intact = (
        0 <= anchor_line < count
        and sitting_after_nota(lines[anchor_line], anchor_col)
    )
    if anchor_intact and (
        line < anchor_line
        or (line == anchor_line and col < anchor_col and not sitting_after_nota(lines[line], col))
    ):
        return lines, line, col, "before"
    if sitting_after_nota(lines[line], col):
        current = lines[line].rstrip()
        if current.endswith("Fine nota."):
            lines[line] = current
            return lines, line, len(current), "line"
        gap = "" if (not current or current[-1].isspace()) else " "
        lines[line] = current + gap + "Fine nota."
        return lines, line, len(lines[line]), "line"
    current = lines[line]
    at = col + 1 if col < len(current) else len(current)
    left, right = current[:at], current[at:]
    if left.rstrip().endswith("Fine nota.") or right.lstrip().startswith("Fine nota."):
        return lines, line, len(left), "char"
    gap = "" if (not left or left[-1].isspace()) else " "
    extra = " " if right and not right[0].isspace() else ""
    lines[line] = left + gap + "Fine nota." + extra + right
    return lines, line, len(left) + len(gap) + len("Fine nota."), "char"


def slice_box(row, start, end, size):
    """Il rettangolo del testo, dal carattere start fino a end, escluso end."""
    text = row.text or ""
    start = max(0, min(int(start or 0), len(text)))
    end = int(end if end is not None else len(text))
    end = max(start + 1, min(end, len(text) or (start + 1)))
    full = text_width(text, size) or max(len(text), 1)
    full_w = max(float(row.w or 0), full, 12)
    scale = full_w / full if full else 1
    x = float(row.x) + text_width(text[:start], size) * scale
    width = max(8.0, text_width(text[start:end] or " ", size) * scale)
    return x, float(row.y), width


def fold_tight_lines(old_lines, new_text: str) -> str:
    """Se una riga nuova non ha spazio, la unisce alla riga precedente."""
    import difflib

    old = list(old_lines or [])
    new = (new_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    folded = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            folded.extend(new[j1:j2])
            continue
        if tag == "delete":
            continue
        if tag == "replace":
            span = min(i2 - i1, j2 - j1)
            chunk = list(new[j1:j1 + span])
            extra = [line.strip() for line in new[j1 + span:j2] if line.strip()]
        else:
            chunk = []
            extra = [line.strip() for line in new[j1:j2] if line.strip()]
        if extra:
            joined = " ".join(extra)
            if chunk:
                chunk[-1] = (chunk[-1].rstrip() + " " + joined).strip()
            elif folded:
                folded[-1] = (folded[-1].rstrip() + " " + joined).strip()
            else:
                chunk.append(joined)
        folded.extend(chunk)
    return "\n".join(folded)


def mark_span(row, end=None, start=0) -> str:
    """Quanto copre il segno, dalla parola di inizio fino al carattere di fine."""
    return f"riga {row.index} di {row.total}, {span_phrase(row.text or '', end, start)}"


def plain_index(ctrl) -> int:
    """Indice nel testo con a-capo semplici. Su Windows il controllo conta anche il ritorno."""
    try:
        value = ctrl.GetValue() or ""
    except Exception:
        return 0
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    try:
        pos = int(ctrl.GetInsertionPoint() or 0)
    except Exception:
        return 0
    if pos <= 0:
        return 0
    try:
        raw = ctrl.GetRange(0, pos) or ""
    except Exception:
        raw = ""
    if raw:
        norm = raw.replace("\r\n", "\n").replace("\r", "\n")
        return max(0, min(len(norm), len(value)))
    return max(0, min(pos, len(value)))


def wx_index(ctrl, plain_pos: int) -> int:
    """L'indice che il controllo si aspetta, con il ritorno contato due volte su Windows."""
    try:
        value = ctrl.GetValue() or ""
    except Exception:
        return int(plain_pos or 0)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    plain_pos = max(0, min(int(plain_pos or 0), len(value)))
    return plain_pos + value.count("\n", 0, plain_pos)


def span_on_line(text: str, name: str, col: int) -> int:
    """Dove sta già il nome su questa riga, vicino al cursore. -1 se non c'è."""
    text = text or ""
    name = name or ""
    if not name or name not in text:
        return -1
    best = -1
    pos = 0
    while True:
        at = text.find(name, pos)
        if at < 0:
            break
        if best < 0 or abs(at - int(col or 0)) < abs(best - int(col or 0)):
            best = at
        pos = at + max(1, len(name))
    return best


def cursor_phrase(text: str, pos: int) -> str:
    """Dov'è il cursore, carattere e parola."""
    text = text or ""
    n = len(text)
    pos = max(0, min(int(pos or 0), n))
    if n == 0:
        return "Cursore all'inizio. La riga è vuota. Carattere 0 di 0."
    left = text.rfind(" ", 0, max(pos, 0))
    right = text.find(" ", pos)
    word_start = 0 if left < 0 else left + 1
    word_end = n if right < 0 else right
    word = text[word_start:word_end].strip() or text[max(0, pos - 1):pos + 1]
    if pos == 0:
        spot = f"all'inizio della riga, prima di «{text[:12]}»"
    elif pos == n:
        spot = f"alla fine della riga, dopo «{text[max(0, n - 12):]}»"
    else:
        before = text[word_start:pos]
        after = text[pos:word_end]
        if before and after:
            spot = f"nella parola «{word}», dopo «{before}» e prima di «{after}»"
        elif before:
            spot = f"dopo «{before}»"
        elif after:
            spot = f"prima di «{after}»"
        else:
            spot = f"nella parola «{word}»"
    return f"Cursore sul carattere {pos} di {n}, {spot}."


def encode_win(text: str) -> tuple:
    """(byte cp1252, caratteri che non entrano)."""
    missing = []
    out = bytearray()
    for ch in text or "":
        if ch == "\n":
            continue
        try:
            out.extend(ch.encode("cp1252"))
        except UnicodeEncodeError:
            missing.append(ch)
    return bytes(out), missing


def pdf_literal(text: str) -> bytes:
    """Stringa PDF fra parentesi, pronta da mettere nello stream."""
    raw, _missing = encode_win(text)
    out = bytearray(b"(")
    for byte in raw:
        if byte in (0x28, 0x29, 0x5C):
            out.extend(b"\\" + bytes((byte,)))
        elif byte < 32 or byte > 126:
            out.extend(f"\\{byte:03o}".encode("ascii"))
        else:
            out.append(byte)
    out.append(0x29)
    return bytes(out)


def text_width(text: str, size: float) -> float:
    return max(8.0, len(text or "") * float(size or 12) * 0.52)


_WRITTEN_RE = re.compile(r"-scritto(?:-\d+)?$")


def output_pdf(src: str) -> str:
    """Il file scritto di questo PDF. Se è già un -scritto, si aggiorna quello."""
    folder = os.path.dirname(src)
    stem = os.path.splitext(os.path.basename(src))[0]
    if _WRITTEN_RE.search(stem):
        return src
    return os.path.join(folder, stem + "-scritto.pdf")


def free_pdf(folder: str, stem: str) -> str:
    path = os.path.join(folder, stem + ".pdf")
    if not os.path.exists(path):
        return path
    n = 2
    while n < 200 and os.path.exists(os.path.join(folder, f"{stem}-{n}.pdf")):
        n += 1
    return os.path.join(folder, f"{stem}-{n}.pdf")


def has_signature(path: str) -> bool:
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError:
        return False
    if b"/ByteRange" not in raw:
        return False
    return (
        b"/Type /Sig" in raw
        or b"/Type/Sig" in raw
        or b"/FT /Sig" in raw
        or b"/FT/Sig" in raw
    )


def _base_font(font_dict) -> str:
    if not isinstance(font_dict, dict):
        return ""
    try:
        base = font_dict.get("/BaseFont")
    except Exception:
        return ""
    if base is None:
        return ""
    return str(base).lstrip("/")


def _page_size(page) -> tuple:
    try:
        box = page.mediabox
        return float(box.width), float(box.height)
    except Exception:
        return 595.0, 842.0


def _drop_covered(frags: list) -> list:
    """Se sulla stessa riga c'è la scritta nuova, non si rilegge quella vecchia sotto il bianco."""
    fonts = [(frag[4] or "") for frag in frags]
    ours = [font for font in fonts if font in _STANDARD]
    old = [font for font in fonts if "+" in font]
    if ours and old:
        return [frag for frag in frags if (frag[4] or "") in _STANDARD]
    return frags


def _join_fragments(frags: list) -> tuple:
    """frags ordinati per x: testo, x, y, w, size, font."""
    if not frags:
        return "", 0, 0, 0, 12, ""
    frags = sorted(frags, key=lambda item: item[0])
    parts = [frags[0][3]]
    x0 = frags[0][0]
    y0 = frags[0][1]
    size = frags[0][2] or 12
    font = frags[0][4] or ""
    end = x0 + text_width(frags[0][3], size)
    for frag in frags[1:]:
        gap = frag[0] - end
        piece = frag[3]
        if gap > max(2.0, size * 0.2) and parts[-1] and not parts[-1].endswith(" ") and not piece.startswith(" "):
            parts.append(" ")
        parts.append(piece)
        size = max(size, frag[2] or size)
        end = max(end, frag[0] + text_width(piece, frag[2] or size))
        if not font:
            font = frag[4] or ""
    text = "".join(parts)
    return text, x0, y0, max(8.0, end - x0), size, font


def read_marks(path: str) -> tuple:
    """(righe, pagine, errore)."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            try:
                if reader.decrypt("") == 0:
                    return [], 0, MSG_LOCKED
            except Exception:
                return [], 0, MSG_LOCKED
    except Exception:
        log.exception("lettura %s", path)
        return [], 0, MSG_READ
    rows = []
    try:
        pages = list(reader.pages)
    except Exception:
        log.exception("pagine %s", path)
        return [], 0, MSG_READ
    for page_index, page in enumerate(pages):
        page_w, page_h = _page_size(page)
        frags = []

        def visitor(text, _cm, tm, font_dict, font_size):
            piece = text or ""
            if not piece.strip():
                return
            try:
                x = float(tm[4])
                y = float(tm[5])
            except Exception:
                return
            frags.append(
                (x, y, _num(font_size, 12) or 12, piece, _base_font(font_dict))
            )

        try:
            page.extract_text(visitor_text=visitor)
        except Exception:
            log.exception("testo pagina %s", page_index + 1)
        frags.sort(key=lambda item: (-item[1], item[0]))
        lines = []
        current = []
        current_y = None
        for frag in frags:
            y = frag[1]
            size = frag[2] or 12
            if current_y is None or abs(y - current_y) > max(2.0, size * 0.45):
                if current:
                    lines.append(current)
                current = [frag]
                current_y = y
            else:
                current.append(frag)
        if current:
            lines.append(current)
        page_rows = []
        for line in lines:
            line = _drop_covered(line)
            text, x, y, width, size, font = _join_fragments(line)
            text = " ".join(text.split())
            if not text:
                continue
            page_rows.append(
                {
                    "text": text,
                    "x": x,
                    "y": y,
                    "w": width,
                    "h": size,
                    "size": size,
                    "font": font,
                    "page_w": page_w,
                    "page_h": page_h,
                }
            )
            if len(rows) + len(page_rows) >= _MAX_LINES:
                break
        _attach_annots(page, page_rows)
        total = len(page_rows)
        for index, item in enumerate(page_rows, start=1):
            rows.append(
                PdfMark(
                    kind="riga",
                    page=page_index + 1,
                    index=index,
                    total=total,
                    text=item["text"],
                    x=item["x"],
                    y=item["y"],
                    w=item["w"],
                    h=item["h"],
                    size=item["size"],
                    page_w=item["page_w"],
                    page_h=item["page_h"],
                    base_font=item["font"],
                    marks=item.get("marks") or [],
                    link=item.get("link") or "",
                )
            )
        if len(rows) >= _MAX_LINES:
            break
        _append_fields(reader, page, page_index, page_w, page_h, rows)
    return rows, len(pages), ""


def _attach_annots(page, page_rows) -> None:
    """Segni e collegamenti della pagina, da ridire nello Stato."""
    try:
        annots = page.get("/Annots") or []
    except Exception:
        return
    words = {
        "/Highlight": "evidenziata",
        "/Underline": "sottolineata",
        "/StrikeOut": "barrata",
    }
    remembered = {"evidenziata", "sottolineata", "barrata"}
    for ref in annots:
        try:
            obj = ref.get_object()
        except Exception:
            continue
        subtype = str(obj.get("/Subtype") or "")
        rect = obj.get("/Rect")
        if rect is None or len(rect) < 4:
            continue
        try:
            bottom = float(rect[1])
            top = float(rect[3])
        except (TypeError, ValueError):
            continue
        word = words.get(subtype, "")
        url = ""
        if subtype == "/Link":
            try:
                action = obj.get("/A")
                if action is not None:
                    url = str(action.get("/URI") or "").strip()
            except Exception:
                url = ""
            if url:
                word = "collegamento"
        if subtype == "/Text":
            try:
                contents = str(obj.get("/Contents") or "").strip().lower()
            except Exception:
                contents = ""
            for remembered_word in remembered:
                if contents == remembered_word or contents.startswith(remembered_word + " "):
                    word = contents
                    break
        if not word:
            continue
        for item in page_rows:
            y = float(item["y"])
            height = float(item["h"] or 12)
            if bottom <= y + height and top >= y - height * 0.4:
                found = item.setdefault("marks", [])
                if word not in found:
                    found.append(word)
                if url:
                    item["link"] = url


def _field_value(field) -> str:
    value = None
    try:
        value = field.get("/V")
    except Exception:
        value = None
    if value is None:
        return ""
    return str(value).strip()


def _field_rect(field):
    rect = None
    try:
        rect = field.get("/Rect")
    except Exception:
        rect = None
    if rect is None:
        kids = []
        try:
            kids = list(field.get("/Kids") or [])
        except Exception:
            kids = []
        for kid in kids:
            try:
                obj = kid.get_object() if hasattr(kid, "get_object") else kid
                rect = obj.get("/Rect")
            except Exception:
                rect = None
            if rect is not None:
                break
    if not rect or len(rect) < 4:
        return None
    try:
        x1, y1, x2, y2 = (float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3]))
    except (TypeError, ValueError):
        return None
    return min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)


def _append_fields(reader, page, page_index: int, page_w: float, page_h: float, rows: list) -> None:
    try:
        fields = reader.get_fields() or {}
    except Exception:
        return
    if not isinstance(fields, dict):
        return
    page_ref = None
    try:
        page_ref = page.indirect_reference
    except Exception:
        page_ref = None
    for name, field in fields.items():
        if not isinstance(field, dict):
            continue
        kind = str(field.get("/FT") or "")
        if kind in ("/Btn", "/Sig"):
            continue
        if kind and kind not in ("/Tx", "/Ch"):
            continue
        rect = _field_rect(field)
        if rect is None:
            continue
        on_page = True
        if page_ref is not None:
            try:
                parent_page = field.get("/P")
                if parent_page is not None and parent_page != page_ref:
                    on_page = False
            except Exception:
                on_page = True
        if not on_page:
            continue
        x, y, w, h = rect
        rows.append(
            PdfMark(
                kind="casella",
                page=page_index + 1,
                index=1,
                total=1,
                text=_field_value(field),
                x=x,
                y=y,
                w=w or 80,
                h=h or 14,
                size=12,
                page_w=page_w,
                page_h=page_h,
                field=str(name),
            )
        )


def _load_writer(path: str):
    from pypdf import PdfReader, PdfWriter

    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            try:
                if reader.decrypt("") == 0:
                    return None, MSG_LOCKED
            except Exception:
                return None, MSG_LOCKED
        writer = PdfWriter()
        writer.append(reader)
    except Exception:
        log.exception("scrittura da %s", path)
        return None, MSG_READ
    return writer, ""


def _save_writer(writer, dest: str) -> str:
    folder = os.path.dirname(dest) or "."
    os.makedirs(folder, exist_ok=True)
    tmp = dest + ".rtad-tmp"
    with open(tmp, "wb") as handle:
        writer.write(handle)
    os.replace(tmp, dest)
    return ""


def _resources(page):
    from pypdf.generic import DictionaryObject, NameObject

    resources = page.get("/Resources")
    if resources is None:
        resources = DictionaryObject()
        page[NameObject("/Resources")] = resources
        return resources
    return resources.get_object()


def _font_alias(page, base_font: str) -> str:
    from pypdf.generic import DictionaryObject, NameObject

    resources = _resources(page)
    fonts = resources.get("/Font")
    if fonts is None or not isinstance(fonts, dict):
        fonts = DictionaryObject()
        resources[NameObject("/Font")] = fonts
    else:
        fonts = fonts.get_object()
    alias = "/RTAD" + (base_font or "Helvetica").replace("-", "")
    key = NameObject(alias)
    if key not in fonts:
        fonts[key] = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/" + (base_font or "Helvetica")),
                NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
            }
        )
    return alias


def _merge(writer, page, ops: str) -> None:
    writer._merge_content_stream_to_page(page, ops.encode("latin-1", "replace"))


def _text_ops(alias: str, x: float, y: float, size: float, text: str, color: str = "0 0 0") -> str:
    literal = pdf_literal(text).decode("latin-1")
    return (
        "q\nBT\n"
        f"/{alias[1:]} {size:.2f} Tf\n"
        f"{color} rg\n"
        f"1 0 0 1 {x:.2f} {y:.2f} Tm\n"
        f"{literal} Tj\n"
        "ET\nQ\n"
    )


def _cover_ops(x: float, y: float, w: float, h: float) -> str:
    pad = 1.2
    left = x - pad
    bottom = y - (h * 0.28) - pad
    width = max(w, 8) + pad * 2
    height = max(h, 8) * 1.3 + pad * 2
    return f"q\n1 1 1 rg\n{left:.2f} {bottom:.2f} {width:.2f} {height:.2f} re\nf\nQ\n"


def _line_ops(x1: float, y1: float, x2: float, y2: float, width: float = 0.9) -> str:
    return (
        f"q\n0 0 0 RG\n{width:.2f} w\n"
        f"{x1:.2f} {y1:.2f} m\n{x2:.2f} {y2:.2f} l\nS\nQ\n"
    )


def _content_bytes(page) -> bytes:
    try:
        contents = page.get_contents()
    except Exception:
        return b""
    if contents is None:
        return b""
    try:
        if isinstance(contents, list):
            return b"\n".join(item.get_data() for item in contents)
        return contents.get_data()
    except Exception:
        return b""


def _try_replace_literal(page, writer, old: str, new: str) -> bool:
    from pypdf.generic import NameObject, StreamObject

    if not old:
        return False
    data = _content_bytes(page)
    if not data:
        return False
    needle = pdf_literal(old)
    if data.count(needle) != 1:
        return False
    replaced = data.replace(needle, pdf_literal(new), 1)
    stream = StreamObject()
    stream.set_data(replaced)
    page[NameObject("/Contents")] = writer._add_object(stream)
    return True


def _ink_font(font: str, line: str) -> str:
    """La firma è in corsivo, così si distingue dal resto del testo."""
    if (line or "").strip().startswith("Firmato:"):
        return "Helvetica-Oblique"
    return font


def _draw_lines(writer, page, x: float, y: float, lines: list, font: str, size: float, color: str = "0 0 0") -> float:
    ops = []
    cursor_y = y
    for line in lines:
        alias = _font_alias(page, _ink_font(font, line))
        ops.append(_text_ops(alias, x, cursor_y, size, line, color))
        cursor_y -= size * 1.35
    _merge(writer, page, "".join(ops))
    return cursor_y


def _split_lines(text: str) -> list:
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return raw.split("\n")


def _missing_in(lines: list) -> list:
    missing = []
    for line in lines:
        _raw, bad = encode_win(line)
        for ch in bad:
            if ch not in missing:
                missing.append(ch)
    return missing


def _page(writer, index: int):
    if index < 0 or index >= len(writer.pages):
        return None
    return writer.pages[index]


def _point(place: str, row, page_w: float, page_h: float, size: float):
    if place == "sotto":
        if row is None or row.kind != "riga":
            return None, MSG_NEED_ROW
        y = row.y - max(size, row.size) * 1.45
        if y < 36:
            return None, MSG_NO_ROOM
        return (row.x, y), ""
    spots = {
        "alto-sinistra": (50, page_h - 72),
        "alto-centro": (page_w * 0.33, page_h - 72),
        "meta-sinistra": (50, page_h * 0.5),
        "basso-sinistra": (50, 56),
        "basso-destra": (max(50, page_w * 0.45), 56),
        "nuova": (50, page_h - 72),
    }
    if place not in spots:
        return None, MSG_NEED_ROW
    return spots[place], ""


def _done(path: str, what: str, signed: bool) -> str:
    name = os.path.basename(path)
    sentence = (
        f"{what} Scritto in {name}, nella stessa cartella. "
        "Il file di partenza resta com'è."
    )
    if signed:
        sentence += " Il file nuovo non porta la firma elettronica."
    return sentence


def _stamp_image(writer, page, image_path: str, page_w: float) -> str:
    try:
        from PIL import Image
    except ImportError:
        return MSG_NO_PILLOW
    try:
        image = Image.open(image_path)
        if image.mode in ("RGBA", "LA") or (
            image.mode == "P" and "transparency" in image.info
        ):
            image = image.convert("RGBA")
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")
        image.thumbnail((900, 400))
        import io

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        jpeg = buffer.getvalue()
        px_w, px_h = image.size
    except Exception:
        log.exception("immagine firma")
        return MSG_NO_IMAGE
    if px_w < 1 or px_h < 1:
        return MSG_NO_IMAGE
    draw_w = 160.0
    draw_h = draw_w * (px_h / px_w)
    if draw_h > 70:
        draw_h = 70.0
        draw_w = draw_h * (px_w / px_h)
    x = max(36.0, page_w - draw_w - 36)
    y = 36.0
    from pypdf.generic import (
        BooleanObject,
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        NumberObject,
    )

    stream = DecodedStreamObject()
    stream.set_data(jpeg)
    stream.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(int(px_w)),
            NameObject("/Height"): NumberObject(int(px_h)),
            NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"): NumberObject(8),
            NameObject("/Filter"): NameObject("/DCTDecode"),
            NameObject("/Interpolate"): BooleanObject(True),
        }
    )
    ref = writer._add_object(stream)
    resources = _resources(page)
    xobjects = resources.get("/XObject")
    if xobjects is None or not isinstance(xobjects, dict):
        xobjects = DictionaryObject()
        resources[NameObject("/XObject")] = xobjects
    else:
        xobjects = xobjects.get_object()
    name = "/RTADFirma"
    n = 1
    while NameObject(name) in xobjects:
        n += 1
        name = f"/RTADFirma{n}"
    xobjects[NameObject(name)] = ref
    ops = f"q\n{draw_w:.2f} 0 0 {draw_h:.2f} {x:.2f} {y:.2f} cm\n{name} Do\nQ\n"
    _merge(writer, page, ops)
    return ""


def _line_plain(text: str) -> str:
    return (text or "").replace("\r", " ").replace("\n", " ")


def _slot_ys(anchor, nxt, count: int, size: float):
    """Quote y per le righe nuove, dall'alto verso il basso. None se non c'entrano."""
    step = max(float(size or 12) * 1.2, 11.0)
    margin = max(2.0, float(size or 12) * 0.25)
    if anchor is not None and nxt is not None:
        top = anchor.y - margin
        bottom = nxt.y + max(float(nxt.size or size), float(size or 12)) * 0.85
        room = top - bottom
        if room < float(size or 12) * 0.8:
            return None
        if count == 1:
            return [top - min(step, room) * 0.45]
        if room < step * (count - 1) + float(size or 12) * 0.5:
            return None
        gap = room / (count + 1)
        return [top - gap * (i + 1) for i in range(count)]
    if anchor is not None:
        ys = []
        y = anchor.y - step
        for _index in range(count):
            if y < 36:
                return None
            ys.append(y)
            y -= step
        return ys
    if nxt is not None:
        page_h = float(nxt.page_h or 842)
        ys = []
        for index in range(count):
            y = nxt.y + step * (count - index)
            if y > page_h - 36:
                return None
            ys.append(y)
        return ys
    page_h = 842.0
    y = page_h - 72
    ys = []
    for _index in range(count):
        if y < 36:
            return None
        ys.append(y)
        y -= step
    return ys


def _gap_error(anchor, nxt) -> str:
    if anchor is not None and nxt is not None:
        return MSG_NO_GAP.format(a=anchor.index, b=nxt.index)
    if nxt is not None:
        return MSG_NO_GAP_ABOVE
    return MSG_NO_GAP_BELOW


def _replace_action(row, text: str, font: str, size) -> dict:
    return {
        "op": "replace",
        "page": row.page,
        "text": text,
        "old": row.text or "",
        "x": row.x,
        "y": row.y,
        "w": row.w,
        "h": row.h,
        "base_font": row.base_font,
        "font": font,
        "size": size,
    }


def _insert_at(row_anchor, row_next, text: str, y: float, font: str, size) -> dict:
    anchor = row_anchor or row_next
    return {
        "op": "insert",
        "page": anchor.page if anchor is not None else 1,
        "place": "punto",
        "text": text,
        "x": anchor.x if anchor is not None else 50,
        "y": y,
        "font": font,
        "size": size,
    }


def _queue_inserts(actions, rows, anchor_i, next_i, lines, font, size):
    """None se ok, altrimenti la frase di errore. Le righe vuote non si disegnano."""
    useful = [line for line in lines if line.strip()]
    if not useful:
        return "blank" if any(not line.strip() for line in lines) else None
    anchor = rows[anchor_i] if anchor_i is not None and anchor_i >= 0 else None
    nxt = rows[next_i] if next_i is not None and 0 <= next_i < len(rows) else None
    ys = _slot_ys(anchor, nxt, len(useful), float(size or 12))
    if not ys:
        joined = " ".join(line.strip() for line in useful)
        if nxt is not None:
            action = _replace_action(
                nxt, (joined + " " + (nxt.text or "")).strip(), font, size,
            )
            action["joined_before"] = True
            actions.append(action)
            return None
        if anchor is not None:
            action = _replace_action(
                anchor, ((anchor.text or "").rstrip() + " " + joined).strip(), font, size,
            )
            action["joined_after"] = True
            actions.append(action)
            return None
        return _gap_error(anchor, nxt)
    for line, y in zip(useful, ys):
        actions.append(_insert_at(anchor, nxt, line, y, font, size))
    return None


def plan_page_edits(rows, new_text: str, font: str, size) -> tuple:
    """(azioni, errore). Le azioni riscrivono, tolgono o aggiungono righe di una pagina."""
    import difflib

    rows = [row for row in rows if getattr(row, "kind", "riga") == "riga"]
    old = [_line_plain(row.text) for row in rows]
    new = (new_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if old == new:
        return [], ""
    missing = _missing_in(new)
    if missing:
        return [], MSG_CHAR.format(chars=" ".join(missing))
    actions = []
    blank = False
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            for row in rows[i1:i2]:
                actions.append(_replace_action(row, "", font, size))
            continue
        if tag == "replace":
            span = min(i2 - i1, j2 - j1)
            for offset in range(span):
                if new[j1 + offset] != old[i1 + offset]:
                    actions.append(_replace_action(rows[i1 + offset], new[j1 + offset], font, size))
            if j2 - j1 > span:
                err = _queue_inserts(
                    actions, rows, i1 + span - 1, i1 + span, new[j1 + span:j2], font, size,
                )
                if err == "blank":
                    blank = True
                elif err:
                    return [], err
            if i2 - i1 > span:
                for row in rows[i1 + span:i2]:
                    actions.append(_replace_action(row, "", font, size))
            continue
        if tag == "insert":
            err = _queue_inserts(actions, rows, i1 - 1, i1, new[j1:j2], font, size)
            if err == "blank":
                blank = True
            elif err:
                return [], err
    if not actions and blank:
        return [], MSG_BLANK_LINE
    return actions, ""


def _edit_summary(actions) -> str:
    changed = 0
    added = 0
    removed = 0
    for action in actions:
        if action.get("op") == "insert":
            added += 1
        elif not (action.get("text") or "").strip():
            removed += 1
        else:
            changed += 1

    def _piece(count, one, many):
        if count == 1:
            return one
        return f"{count} {many}"

    parts = []
    if changed:
        parts.append(_piece(changed, "1 riga cambiata", "righe cambiate"))
    if added:
        parts.append(_piece(added, "1 riga aggiunta", "righe aggiunte"))
    if removed:
        parts.append(_piece(removed, "1 riga tolta", "righe tolte"))
    if not parts:
        sentence = "Scritte le modifiche di questa pagina."
    else:
        sentence = "Scritte le modifiche di questa pagina: " + ", ".join(parts) + "."
    if any(action.get("joined_before") for action in actions):
        sentence += (
            " Non c'era spazio per una riga a sé: "
            "il testo sta all'inizio della riga dopo, prima di ciò che c'era."
        )
    if any(action.get("joined_after") for action in actions):
        sentence += (
            " Non c'era spazio per una riga a sé: "
            "il testo sta in fondo alla riga prima."
        )
    return sentence


def apply_edits(src: str, dest: str, actions) -> tuple:
    """(ok, frase, percorso). Tutte le azioni, poi un solo file."""
    if not src or not os.path.isfile(src):
        return False, MSG_READ, ""
    if os.path.splitext(src)[1].lower() != ".pdf":
        return False, os.path.basename(src) + " " + MSG_NOT_PDF, ""
    if not actions:
        return False, MSG_NOTHING_NEW, ""
    signed = has_signature(src)
    writer, err = _load_writer(src)
    if writer is None:
        return False, err or MSG_READ, ""
    white = False
    try:
        for action in actions:
            bit, err = _run(writer, action, len(writer.pages))
            if err:
                return False, err, ""
            if "rettangolo bianco" in (bit or ""):
                white = True
    except Exception:
        log.exception("modifiche pagina")
        return False, MSG_FAIL, ""
    try:
        save_err = _save_writer(writer, dest)
    except Exception:
        log.exception("salvataggio %s", dest)
        return False, MSG_FAIL, ""
    if save_err:
        return False, save_err, ""
    summary = _edit_summary(actions)
    if white:
        summary += (
            " Dove il carattere del PDF non si può sostituire, "
            "un rettangolo bianco copre la riga di prima."
        )
    return True, _done(dest, summary, signed), dest


def apply_edit(src: str, dest: str, action: dict) -> tuple:
    """(ok, frase, percorso). Il file src non si tocca se dest è un altro."""
    if not src or not os.path.isfile(src):
        return False, MSG_READ, ""
    if os.path.splitext(src)[1].lower() != ".pdf":
        return False, os.path.basename(src) + " " + MSG_NOT_PDF, ""
    signed = has_signature(src)
    writer, err = _load_writer(src)
    if writer is None:
        return False, err or MSG_READ, ""
    op = (action or {}).get("op") or ""
    try:
        sentence_bit, err = _run(writer, action, len(writer.pages))
    except Exception:
        log.exception("operazione %s", op)
        return False, MSG_FAIL, ""
    if err:
        return False, err, ""
    try:
        save_err = _save_writer(writer, dest)
    except Exception:
        log.exception("salvataggio %s", dest)
        return False, MSG_FAIL, ""
    if save_err:
        return False, save_err, ""
    return True, _done(dest, sentence_bit, signed), dest


def apply_mark_spans(src: str, dest: str, actions, lead: str) -> tuple:
    """(ok, frase, percorso). Più segni sulla stessa pagina, una frase sola."""
    if not src or not os.path.isfile(src):
        return False, MSG_READ, ""
    if os.path.splitext(src)[1].lower() != ".pdf":
        return False, os.path.basename(src) + " " + MSG_NOT_PDF, ""
    if not actions:
        return False, MSG_SELECT, ""
    signed = has_signature(src)
    writer, err = _load_writer(src)
    if writer is None:
        return False, err or MSG_READ, ""
    try:
        for action in actions:
            _bit, err = _run(writer, action, len(writer.pages))
            if err:
                return False, err, ""
    except Exception:
        log.exception("segni")
        return False, MSG_FAIL, ""
    try:
        save_err = _save_writer(writer, dest)
    except Exception:
        log.exception("salvataggio %s", dest)
        return False, MSG_FAIL, ""
    if save_err:
        return False, save_err, ""
    return True, _done(dest, lead, signed), dest


def _run(writer, action: dict, page_count: int) -> tuple:
    op = action.get("op") or ""
    if op == "blank":
        width, height = 595.0, 842.0
        if writer.pages:
            width, height = _page_size(writer.pages[-1])
        writer.add_blank_page(width=width, height=height)
        return f"Pagina {len(writer.pages)} bianca, in fondo.", ""
    page_index = int(action.get("page") or 1) - 1
    if op == "sign":
        if page_index < 0 or page_index >= len(writer.pages):
            page_index = max(0, len(writer.pages) - 1)
    page = _page(writer, page_index)
    if page is None:
        return "", MSG_BAD_PAGE
    page_w, page_h = _page_size(page)
    font = action.get("font") or "Helvetica"
    if font not in {item[0] for item in FONTS}:
        font = "Helvetica"
    size = _num(action.get("size"), 12) or 12
    if op == "replace":
        return _op_replace(writer, page, action, font, size)
    if op == "field":
        return _op_field(writer, page, action)
    if op == "insert":
        return _op_insert(writer, page, action, page_w, page_h, font, size, "0 0 0")
    if op == "link":
        return _op_link(writer, page, action, page_w, page_h, font, size, page_count)
    if op == "note":
        return _op_note(writer, page, action, page_w, page_h, font, size, page_index)
    if op == "highlight":
        return _op_highlight(writer, page, action, page_index)
    if op == "underline":
        return _op_rule(writer, page, action, through=False)
    if op == "strike":
        return _op_rule(writer, page, action, through=True)
    if op == "sign":
        return _op_sign(writer, page, action, page_w, font, size)
    return "", MSG_FAIL


def _op_replace(writer, page, action, font, size) -> tuple:
    lines = _split_lines(action.get("text") or "")
    if not any(line.strip() for line in lines):
        lines = [""]
    missing = _missing_in(lines)
    if missing:
        return "", MSG_CHAR.format(chars=" ".join(missing))
    old = action.get("old") or ""
    base = action.get("base_font") or ""
    new = lines[0]
    replaced = False
    if base in _STANDARD and "\n" not in (action.get("text") or "") and len(lines) == 1:
        replaced = _try_replace_literal(page, writer, old, new)
    x = _num(action.get("x"), 50)
    y = _num(action.get("y"), 50)
    w = _num(action.get("w"), text_width(old, size))
    h = _num(action.get("h"), size)
    if not replaced:
        _merge(writer, page, _cover_ops(x, y, max(w, text_width(new, size)), h))
    ops = []
    cursor_y = y
    for line in lines:
        alias = _font_alias(page, _ink_font(font, line))
        ops.append(_text_ops(alias, x, cursor_y, size, line))
        cursor_y -= size * 1.35
    if not replaced or len(lines) > 1:
        if replaced and len(lines) > 1:
            ops = ops[1:]
            cursor_y = y - size * 1.35
            extra = []
            for line in lines[1:]:
                alias = _font_alias(page, _ink_font(font, line))
                extra.append(_text_ops(alias, x, cursor_y, size, line))
                cursor_y -= size * 1.35
            ops = extra
        if ops:
            _merge(writer, page, "".join(ops))
    if replaced and len(lines) == 1:
        return "Riga riscritta. Il testo nuovo sostituisce quello di prima.", ""
    return (
        "Riga coperta con un rettangolo bianco e riscritta sopra. "
        "Un lettore potrebbe ancora leggere la riga di prima, sotto il bianco. "
        "La scritta che si vede è quella nuova.",
        "",
    )


def _op_field(writer, page, action) -> tuple:
    name = (action.get("field") or "").strip()
    value = action.get("text") or ""
    if not name:
        return "", MSG_SELECT
    missing = _missing_in([value])
    if missing:
        return "", MSG_CHAR.format(chars=" ".join(missing))
    try:
        writer.update_page_form_field_values(
            page,
            {name: value},
            auto_regenerate=True,
        )
    except Exception:
        log.exception("casella %s", name)
        return "", MSG_FAIL
    return f"Casella {name} aggiornata.", ""


def _op_insert(writer, page, action, page_w, page_h, font, size, color) -> tuple:
    lines = _split_lines(action.get("text") or "")
    if not any(line.strip() for line in lines):
        return "", MSG_NO_TEXT
    missing = _missing_in(lines)
    if missing:
        return "", MSG_CHAR.format(chars=" ".join(missing))
    if (action.get("place") or "") == "punto":
        point, err = (_num(action.get("x"), 50), _num(action.get("y"), 50)), ""
    else:
        point, err = _point(action.get("place") or "", action.get("row"), page_w, page_h, size)
    if err:
        return "", err
    x, y = point
    _draw_lines(writer, page, x, y, lines, font, size, color)
    where = zone_phrase(x, y, page_w, page_h)
    return f"Scritta aggiunta, {where}.", ""


def _remember_mark(writer, page, row, word: str) -> None:
    """Un'annotazione nascosta, così lo Stato può ridire il segno."""
    from pypdf.annotations import Text
    from pypdf.generic import NameObject, NumberObject

    annot = Text(
        rect=(row.x, row.y, row.x + 8, row.y + 8),
        text=word,
        open=False,
    )
    try:
        annot[NameObject("/F")] = NumberObject(2)
    except Exception:
        pass
    writer.add_annotation(page_number=page, annotation=annot)


def _op_link(writer, page, action, page_w, page_h, font, size, page_count: int) -> tuple:
    from pypdf.annotations import Link

    address = (action.get("url") or "").strip()
    url = ""
    target = None
    if looks_web(address):
        url = address
    else:
        digits = address.lower().replace("pagina", "").strip()
        if digits.isdigit():
            number = int(digits)
            if number < 1 or number > page_count:
                return "", page_missing(number, page_count)
            target = number - 1
        else:
            return "", MSG_BAD_LINK
    text = (action.get("text") or "").strip()
    if not text:
        text = url or (f"Pagina {target + 1}" if target is not None else "")
    place = action.get("place") or ""
    row = action.get("row")
    drawn = ""
    if place == "sulla-riga" and row is not None:
        start = int(action.get("start") or 0)
        end = action.get("end")
        x, y, width = slice_box(row, start, end if end is not None else len(row.text or ""), size)
        shown = (row.text or "")[start:int(end if end is not None else len(row.text or ""))]
        bit = (
            f"Collegamento su «{shown or row.text}», "
            f"{span_phrase(row.text or '', end)}. "
            "Nel PDF salvato quelle parole sono cliccabili."
        )
    else:
        action = dict(action)
        action["text"] = text
        drawn, err = _op_insert(writer, page, action, page_w, page_h, font, size, "0 0 1")
        if err:
            return "", err
        if place == "punto":
            x, y = _num(action.get("x"), 50), _num(action.get("y"), 50)
        else:
            point, err = _point(place, row, page_w, page_h, size)
            if err:
                return "", err
            x, y = point
        width = max(text_width(text.split("\n")[0], size), 12)
        bit = drawn
    height = size * 1.2
    rect = (x, y - size * 0.25, x + width, y + height)
    if url:
        annot = Link(rect=rect, url=url)
    else:
        annot = Link(rect=rect, target_page_index=target)
    writer.add_annotation(page_number=page, annotation=annot)
    _merge(writer, page, _line_ops(x, y - 1.5, x + width, y - 1.5, 0.7))
    origin = (action.get("origin") or "").strip()
    origin_bit = f" Indirizzo preso {origin}." if origin else ""
    if url:
        return (
            f"{bit}{origin_bit} Verso {url}. "
            "Invio sul pulsante Apri collegamento, o un clic, apre il browser. "
            "Questa finestra resta aperta.",
            "",
        )
    return (
        f"{bit}{origin_bit} Verso la pagina {target + 1} di questo PDF.",
        "",
    )


def page_missing(number: int, total: int) -> str:
    return f"La pagina {number} non c'è: questo file ne ha {total}."


def _op_note(writer, page, action, page_w, page_h, font, size, page_index: int) -> tuple:
    from pypdf.annotations import Text

    raw = (action.get("text") or "").strip()
    if not raw:
        return "", MSG_NO_TEXT
    shown = raw if raw.lower().startswith("nota:") else f"Nota: {raw}"
    action = dict(action)
    action["text"] = shown
    bit, err = _op_insert(writer, page, action, page_w, page_h, font, max(10, size - 1), "0 0 0")
    if err:
        return "", err
    if (action.get("place") or "") == "punto":
        x, y = _num(action.get("x"), 50), _num(action.get("y"), 50)
    else:
        point, _err = _point(action.get("place") or "", action.get("row"), page_w, page_h, size)
        x, y = point or (50, page_h - 72)
    rect = (x, y, x + 24, y + 24)
    writer.add_annotation(
        page_number=page,
        annotation=Text(rect=rect, text=raw, open=False),
    )
    return (
        f"Nota scritta sulla pagina {page_index + 1}. {bit} "
        "È una riga che inizia con Nota: si legge spostandosi su quella riga, a schermo e a voce.",
        "",
    )


def _op_highlight(writer, page, action, page_index: int) -> tuple:
    from pypdf.annotations import Highlight
    from pypdf.generic import ArrayObject, FloatObject

    row = action.get("row")
    if row is None:
        return "", MSG_SELECT
    end = action.get("end")
    start = int(action.get("start") or 0)
    x, y, w = slice_box(row, start, end if end is not None else len(row.text or ""), row.size or 12)
    h = max(row.h, 10)
    top = y + h * 0.85
    bottom = y - h * 0.25
    quad = ArrayObject(
        [
            FloatObject(x), FloatObject(top),
            FloatObject(x + w), FloatObject(top),
            FloatObject(x), FloatObject(bottom),
            FloatObject(x + w), FloatObject(bottom),
        ]
    )
    writer.add_annotation(
        page_number=page,
        annotation=Highlight(
            rect=(x, bottom, x + w, top),
            quad_points=quad,
            highlight_color="ffff00",
            printing=True,
        ),
    )
    phrase = span_phrase(row.text or "", end, start)
    _remember_mark(writer, page, row, f"evidenziata {phrase}")
    return (
        f"Evidenziato, {phrase}. "
        "La lettera S, o Alt+P, lo ridice.",
        "",
    )


def _op_rule(writer, page, action, through: bool) -> tuple:
    row = action.get("row")
    if row is None or row.kind not in ("riga", "casella"):
        return "", MSG_SELECT
    end = action.get("end")
    start = int(action.get("start") or 0)
    x, y, width = slice_box(row, start, end if end is not None else len(row.text or ""), row.size or 12)
    y = y + (row.h * 0.35 if through else -1.6)
    _merge(writer, page, _line_ops(x, y, x + width, y, 1.0 if through else 0.8))
    word = "barrata" if through else "sottolineata"
    phrase = span_phrase(row.text or "", end, start)
    _remember_mark(writer, page, row, f"{word} {phrase}")
    if through:
        return (
            f"Barrato, {phrase}. "
            "La lettera S, o Alt+P, lo ridice.",
            "",
        )
    return (
        f"Sottolineato, {phrase}. "
        "La lettera S, o Alt+P, lo ridice.",
        "",
    )


def _op_sign(writer, page, action, page_w, font, size) -> tuple:
    name = " ".join((action.get("name") or "").split())
    image = (action.get("image") or "").strip()
    bits = []
    already = (action.get("already") or "").strip()
    if already:
        bits.append(already)
    if name:
        if looks_web(name):
            return "", MSG_NAME_IS_URL
        when = time.strftime("%d/%m/%Y")
        line = f"Firmato: {name}, {when}."
        missing = _missing_in([line])
        if missing:
            return "", MSG_CHAR.format(chars=" ".join(missing))
        place = action.get("place") or ""
        page_h = _page_size(page)[1]
        if place == "punto":
            x = _num(action.get("x"), 50)
            y = _num(action.get("y"), 48)
            where = zone_phrase(x, y, page_w, page_h)
        elif place and place != "sotto":
            point, err = _point(place, action.get("row"), page_w, page_h, size)
            if err:
                return "", err
            x, y = point
            where = zone_phrase(x, y, page_w, page_h)
        else:
            x, y = 50, 48
            where = "in basso a sinistra"
        _merge(writer, page, _text_ops(_font_alias(page, _ink_font(font, line)), x, y, size, line))
        bits.append(f"Firma scritta {where}: {line}")
    if image:
        if not os.path.isfile(image):
            return "", MSG_NO_IMAGE
        err = _stamp_image(writer, page, image, page_w)
        if err == MSG_NO_PILLOW and name:
            bits.append(MSG_NO_PILLOW)
        elif err:
            return "", err
        else:
            bits.append("Immagine della firma in basso a destra.")
    if not bits:
        return "", MSG_NEED_NAME
    bits.append("La firma elettronica p7m resta di Aruba Sign.")
    return " ".join(bits), ""


def open_dialog(parent, speaker, paths=None):
    import wx

    dialog = PdfDialog(parent, speaker, paths or [])
    dialog.ShowModal()
    dialog.close_work()
    dialog.Destroy()


class PdfDialog:
    """La classe vera è sotto: wx va importato a finestra aperta."""


def _install_dialog():
    import wx

    class _FieldAccess(wx.Accessible):
        def __init__(self, window, name):
            super().__init__(window)
            self._acc_name = name

        def GetName(self, childId=0):
            return (wx.ACC_OK, self._acc_name)

    class PdfDialog(wx.Dialog):
        def __init__(self, parent, speaker, paths):
            super().__init__(
                parent,
                title="Scrivi nel PDF",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._speaker = speaker or (lambda _text: None)
            self._rows: list[PdfMark] = []
            self._src = ""
            self._dest = ""
            self._signed = False
            self._page_count = 0
            self._page = 1
            self._line = -1
            self._filling = False
            self._page_draft = {}
            self._open = True
            self._close_warned = False
            self._pending_note = ""
            self._saved_line = 0
            self._saved_col = 0
            self._keep_find = ""
            self._note_open = False
            self._note_line = 0
            self._note_col = 0
            self._note_page = 0
            self._mark_open = False
            self._mark_op = ""
            self._mark_page = 0
            self._mark_line = 0
            self._mark_col = 0
            self._acc_keep = []
            self._alt_p_time = 0.0
            self._initial = [p for p in (paths or []) if p]

            vbox = wx.BoxSizer(wx.VERTICAL)
            intro = wx.TextCtrl(
                self,
                value=_INTRO,
                style=wx.TE_MULTILINE | wx.TE_READONLY,
            )
            intro.SetMinSize((780, 96))
            vbox.Add(intro, 0, wx.EXPAND | wx.ALL, 8)

            nav = wx.BoxSizer(wx.HORIZONTAL)
            self.lbl_page = wx.StaticText(self, label="Nessun PDF aperto.")
            self.lbl_page.SetName("Pagina")
            self.btn_prev = wx.Button(self, label="Pagina precedente")
            self.btn_next = wx.Button(self, label="Pagina successiva")
            nav.Add(self.lbl_page, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
            nav.Add(self.btn_prev, 0, wx.RIGHT, 6)
            nav.Add(self.btn_next, 0)
            vbox.Add(nav, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Pagina, sola lettura. Le frecce e un clic si muovono nel testo. "
                        "Pagina su e Pagina giù cambiano pagina. "
                        "Invio o doppio clic, oppure Tab, porta sulla pagina in modifica. "
                        "La lettera S, oppure Alt+P, legge i dettagli."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )
            self.page_view = wx.TextCtrl(
                self, style=wx.TE_MULTILINE | wx.TE_READONLY,
            )
            self.page_view.SetName("Pagina, sola lettura")
            self.page_view.SetMinSize((780, 160))
            vbox.Add(self.page_view, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.page_view.Bind(wx.EVT_KEY_UP, self._on_page_key)
            self.page_view.Bind(wx.EVT_LEFT_UP, self._on_page_click)
            self.page_view.Bind(wx.EVT_LEFT_DCLICK, self._on_page_dclick)

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Pagina in modifica, tutta. Invio va a capo: si può scrivere tra una riga e l'altra. "
                        "Backspace cancella il carattere prima del cursore, Canc quello dopo. "
                        "Le frecce e un clic si muovono nel testo. "
                        "Qui la lettera S scrive la esse. "
                        "La pagina sopra si aggiorna subito. Maiusc+Tab torna sulla pagina. "
                        "Alt+P legge i dettagli."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )
            self.txt = wx.TextCtrl(self, style=wx.TE_MULTILINE)
            self.txt.SetName("Pagina in modifica")
            self.txt.SetMinSize((780, 140))
            vbox.Add(self.txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.txt.Bind(wx.EVT_KEY_UP, self._on_editor_key)
            self.txt.Bind(wx.EVT_LEFT_UP, self._on_editor_click)
            self.txt.Bind(wx.EVT_TEXT, self._on_editor_text)
            self.txt.Bind(wx.EVT_KILL_FOCUS, self._on_editor_leave)

            grid = wx.FlexGridSizer(2, 4, 6, 8)
            grid.AddGrowableCol(1, 1)
            grid.AddGrowableCol(3, 1)
            self.place = wx.Choice(self, choices=[label for _key, label in PLACES])
            self.place.SetName("Posto")
            self.place.SetSelection(0)
            self.font = wx.Choice(self, choices=[label for _key, label in FONTS])
            self.font.SetName("Carattere")
            self.font.SetSelection(0)
            self.size = wx.Choice(self, choices=[label for _key, label in SIZES])
            self.size.SetName("Misura")
            self.size.SetSelection(1)
            grid.Add(wx.StaticText(self, label="Posto"), 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(self.place, 1, wx.EXPAND)
            grid.Add(wx.StaticText(self, label="Carattere"), 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(self.font, 1, wx.EXPAND)
            grid.Add(wx.StaticText(self, label="Misura"), 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(self.size, 1, wx.EXPAND)
            grid.Add((1, 1), 0)
            grid.Add((1, 1), 0)
            vbox.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

            link_box = wx.BoxSizer(wx.HORIZONTAL)
            name_box, self.txt_link_name = self._named_field("Nome del sito")
            url_box, self.txt_url = self._named_field("Indirizzo")
            link_box.Add(name_box, 1, wx.EXPAND | wx.RIGHT, 12)
            link_box.Add(url_box, 1, wx.EXPAND)
            vbox.Add(link_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Collegamento. Nel primo campo il nome del sito, per esempio Juventus. "
                        "Nel secondo l'indirizzo, per esempio https://www.juventus.com/it/news/. "
                        "Alt+W, oppure Invio sul pulsante Collegamento web, o un clic. "
                        "Se quel nome è già sulla riga, resta lì e diventa il collegamento. "
                        "Il nome entra dove sta il cursore, nella pagina in modifica."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )
            link_buttons = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_link = wx.Button(self, label="Collegamento &web")
            self.btn_open_link = wx.Button(self, label="Apri collegamento")
            link_buttons.Add(self.btn_link, 0, wx.RIGHT, 6)
            link_buttons.Add(self.btn_open_link, 0)
            vbox.Add(link_buttons, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Nota. Alt+J, oppure Invio sul pulsante Annotazione, o un clic, "
                        "scrive Nota dove sta il cursore, davanti al testo già scritto. "
                        "Se il cursore è su una riga vuota, Nota sta prima di quel testo. "
                        "Alt+J un'altra volta, senza spostarsi, oppure Invio sul pulsante Annotazione, o un clic, "
                        "scrive Fine nota in fondo a questa riga. "
                        "Se la frase continua, vai sull'ultimo carattere da includere, anche più sotto, anche sul punto, "
                        "e Alt+J, oppure Invio sul pulsante Annotazione, o un clic, scrive Fine nota dopo quel carattere. "
                        "Alt+Maiusc+M, oppure Invio sul pulsante Nota mia, o un clic, apre una finestra. "
                        "Invio va a capo. L'ultima riga è Fine nota. "
                        "Invio sul pulsante Inserisci, o un clic, la mette dove sta il cursore. "
                        "Alt+M resta Strumenti, nella finestra principale."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )

            sign = wx.BoxSizer(wx.HORIZONTAL)
            name_sign, self.txt_name = self._named_field("Nome e cognome")
            self.txt_image = wx.TextCtrl(self, style=wx.TE_READONLY)
            self.txt_image.SetName("Immagine della firma")
            self.btn_image = wx.Button(self, label="Scegli immagine…")
            sign.Add(name_sign, 1, wx.EXPAND | wx.RIGHT, 8)
            sign.Add(self.txt_image, 1, wx.ALIGN_BOTTOM | wx.RIGHT, 6)
            sign.Add(self.btn_image, 0, wx.ALIGN_BOTTOM)
            vbox.Add(sign, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Firma. Nome e cognome, per esempio Maurizio Barra. "
                        "Non è il collegamento. "
                        "Alt+D, oppure Invio sul pulsante Firma, o un clic, la scrive dove sta il cursore, in corsivo. "
                        "Nell'elenco Posto, se si sceglie un punto, per esempio in basso a sinistra, la firma va lì. "
                        "Nella Standalone l'immagine della firma va in basso a destra. "
                        "Sull'Add-on l'immagine non entra: manca Pillow. "
                        "Il nome scritto entra lo stesso."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )

            row1 = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_open = wx.Button(self, label="Apri d&ocumento…")
            self.btn_replace = wx.Button(self, label="Riscrivi (&E)")
            self.btn_insert = wx.Button(self, label="Scritta n&uova")
            self.btn_note = wx.Button(self, label="Annotazione (&J)")
            self.btn_note_mine = wx.Button(self, label="Nota mia")
            for btn in (
                self.btn_open, self.btn_replace, self.btn_insert, self.btn_note,
                self.btn_note_mine,
            ):
                row1.Add(btn, 0, wx.RIGHT, 6)
            vbox.Add(row1, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

            row2 = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_hi = wx.Button(self, label="Evidenzia (&X)")
            self.btn_under = wx.Button(self, label="Sottolinea (&Y)")
            self.btn_strike = wx.Button(self, label="Barra")
            self.btn_sign = wx.Button(self, label="Firma (&D)")
            self.btn_close = wx.Button(self, wx.ID_ANY, "Chiudi")
            for btn in (
                self.btn_hi, self.btn_under, self.btn_strike,
                self.btn_sign, self.btn_close,
            ):
                row2.Add(btn, 0, wx.RIGHT, 6)
            vbox.Add(row2, 0, wx.ALL, 8)

            self.lbl_stato = wx.StaticText(
                self,
                label=(
                    "Stato. Un clic, la lettera S, o Alt+P, legge i dettagli. "
                    "Alt+P due volte lo copia."
                ),
            )
            self.lbl_stato.Bind(wx.EVT_LEFT_UP, lambda e: self._say(self._cursor_status()))
            vbox.Add(self.lbl_stato, 0, wx.LEFT | wx.RIGHT, 8)
            self.txt_status = wx.TextCtrl(
                self, value=MSG_EMPTY, style=wx.TE_READONLY | wx.TE_MULTILINE,
            )
            self.txt_status.SetName("Stato")
            self.txt_status.SetMinSize((780, 72))
            vbox.Add(self.txt_status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self._status_bar = wx.StatusBar(self)
            self._status_bar.SetStatusText(MSG_EMPTY)
            vbox.Add(self._status_bar, 0, wx.EXPAND | wx.ALL, 4)

            self.btn_prev.Bind(wx.EVT_BUTTON, lambda e: self._change_page(-1))
            self.btn_next.Bind(wx.EVT_BUTTON, lambda e: self._change_page(1))
            self.btn_open.Bind(wx.EVT_BUTTON, self._on_open)
            self.btn_replace.Bind(wx.EVT_BUTTON, self._on_replace)
            self.btn_insert.Bind(wx.EVT_BUTTON, self._on_insert)
            self.btn_link.Bind(wx.EVT_BUTTON, self._on_link)
            self.btn_open_link.Bind(wx.EVT_BUTTON, self._on_open_link)
            self.btn_note.Bind(wx.EVT_BUTTON, self._on_note)
            self.btn_note_mine.Bind(wx.EVT_BUTTON, self._on_note_manual)
            self.btn_close.Bind(wx.EVT_BUTTON, self._on_close_ask)
            self.Bind(wx.EVT_CLOSE, self._on_close_ask)
            self.btn_hi.Bind(wx.EVT_BUTTON, lambda e: self._mark("highlight"))
            self.btn_under.Bind(wx.EVT_BUTTON, lambda e: self._mark("underline"))
            self.btn_strike.Bind(wx.EVT_BUTTON, lambda e: self._mark("strike"))
            self.btn_sign.Bind(wx.EVT_BUTTON, self._on_sign)
            self.btn_image.Bind(wx.EVT_BUTTON, self._on_image)
            self._enable_file_drop()
            self.Bind(wx.EVT_CHAR_HOOK, self._on_char)
            self.SetSizer(vbox)
            self.SetMinSize((860, 820))
            self.Fit()
            self.Centre()
            self._show_page(speak=False)
            self._load_initial()
            wx.CallAfter(self._focus_page)

        def _named_field(self, caption: str):
            label = wx.StaticText(self, label=caption)
            label.SetName(caption)
            ctrl = wx.TextCtrl(self, size=(280, -1))
            ctrl.SetName(caption)
            try:
                ctrl.SetHint(caption)
            except Exception:
                pass
            try:
                access = _FieldAccess(ctrl, caption)
                ctrl.SetAccessible(access)
                self._acc_keep.append(access)
            except Exception:
                pass
            box = wx.BoxSizer(wx.VERTICAL)
            box.Add(label, 0, wx.BOTTOM, 2)
            box.Add(ctrl, 0, wx.EXPAND)
            return box, ctrl

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

        def _focus_editor(self):
            try:
                self.txt.SetFocus()
            except Exception:
                return

        def _show_status(self, text: str):
            text = (text or "").strip()
            if not text or not self._open:
                return
            try:
                self.txt_status.SetValue(text)
            except Exception:
                pass
            try:
                self._status_bar.SetStatusText(text)
            except Exception:
                pass

        def _rows_on_page(self, page=None):
            page = self._page if page is None else page
            return [row for row in self._rows if row.page == page]

        def _text_rows(self):
            return [row for row in self._rows_on_page() if row.kind == "riga"]

        def _original_page_text(self) -> str:
            rows = self._text_rows()
            if not rows:
                return ""
            return "\n".join(_line_plain(row.text) for row in rows)

        def _shown_page_text(self) -> str:
            if self._page in self._page_draft:
                return self._page_draft[self._page]
            return self._original_page_text()

        def _page_line_texts(self):
            shown = self._shown_page_text()
            if not shown:
                return []
            return shown.split("\n")

        def _mark_suffix(self, row) -> str:
            words = []
            for word in list(row.marks or []):
                if word and word not in words:
                    words.append(word)
            if row.link and "collegamento" not in words:
                words.append("collegamento")
            folded = (row.text or "").strip().lower()
            if folded.startswith("nota:") and "nota" not in words:
                words.append("nota")
            if folded.startswith("firmato:") and "firma" not in words:
                words.append("firma")
            if not words:
                return ""
            return " — " + ", ".join(words)

        def _reading_text(self) -> str:
            shown = self._shown_page_text()
            if not shown or not self._src:
                return shown
            lines = shown.split("\n")
            rows = self._text_rows()
            mapping = self._line_map()
            out = []
            for index, line in enumerate(lines):
                mapped = mapping.get(index)
                suffix = ""
                if mapped is not None and 0 <= mapped < len(rows):
                    suffix = self._mark_suffix(rows[mapped])
                out.append(line + suffix if suffix else line)
            return "\n".join(out)

        def _plain_pos(self, line: int, col: int) -> int:
            shown = self._shown_page_text()
            lines = shown.split("\n") if shown else []
            if not lines:
                return 0
            line = max(0, min(line, len(lines) - 1))
            col = max(0, min(col, len(lines[line])))
            return sum(len(lines[i]) + 1 for i in range(line)) + col

        def _page_dirty(self) -> bool:
            if self._page not in self._page_draft:
                return False
            return self._page_draft[self._page] != self._original_page_text()

        def _focus_text(self):
            try:
                focus = self.FindFocus()
            except Exception:
                focus = None
            if focus is self.page_view or focus is self.txt:
                return focus
            return self.txt

        def _caret_bits_from(self, ctrl):
            try:
                text = ctrl.GetValue() or ""
            except Exception:
                text = ""
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            if text == MSG_EMPTY:
                text = ""
            pos = plain_index(ctrl) if text else 0
            lines = text.split("\n") if text else []
            if not lines:
                return 0, 0, "", 0
            pos = max(0, min(pos, len(text)))
            line = min(text.count("\n", 0, pos), len(lines) - 1)
            start = text.rfind("\n", 0, pos) + 1
            return line, pos - start, lines[line], len(lines)

        def _caret_bits(self):
            return self._caret_bits_from(self._focus_text())

        def _remember_editor_caret(self):
            line, col, _text, _total = self._caret_bits_from(self.txt)
            self._saved_line = line
            self._saved_col = col

        def _line_map(self):
            import difflib

            rows = self._text_rows()
            old = [_line_plain(row.text) for row in rows]
            shown = self._shown_page_text()
            new = shown.split("\n") if shown else []
            mapping = {}
            matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "equal" or tag == "replace":
                    span = min(i2 - i1, j2 - j1)
                    for offset in range(span):
                        mapping[j1 + offset] = i1 + offset
            return mapping

        def _row(self):
            rows = self._text_rows()
            line, _col, _text, _total = self._caret_bits()
            mapped = self._line_map().get(line)
            if mapped is None or mapped < 0 or mapped >= len(rows):
                return None
            return rows[mapped]

        def _added_where(self, line: int) -> str:
            mapping = self._line_map()
            prev = None
            nxt = None
            for index in range(line - 1, -1, -1):
                if index in mapping:
                    prev = mapping[index] + 1
                    break
            shown = self._shown_page_text()
            total = len(shown.split("\n")) if shown else 0
            for index in range(line + 1, total):
                if index in mapping:
                    nxt = mapping[index] + 1
                    break
            if prev and nxt:
                return f"Riga aggiunta, tra la riga {prev} e la riga {nxt}."
            if prev:
                return f"Riga aggiunta, dopo la riga {prev}."
            if nxt:
                return f"Riga aggiunta, prima della riga {nxt}."
            return "Riga aggiunta."

        def _page_label(self) -> str:
            if not self._src:
                return "Nessun PDF aperto."
            pages = self._page_count or 0
            if pages <= 0:
                return "Nessuna pagina."
            shown = self._shown_page_text()
            count = len(shown.split("\n")) if shown else 0
            return f"Pagina {self._page} di {pages}, {count} righe."

        def _focus_page(self):
            if not self._open:
                return
            try:
                self.page_view.SetFocus()
            except Exception:
                pass

        def _refresh_page_view(self):
            if not self._src:
                text = ""
            else:
                text = self._reading_text()
                if not text and self._page not in self._page_draft:
                    text = MSG_EMPTY
            try:
                if self.page_view.GetValue() != text:
                    self.page_view.ChangeValue(text)
            except Exception:
                pass
            try:
                self.lbl_page.SetLabel(self._page_label())
            except Exception:
                pass

        def _set_page_caret(self, line: int, col: int):
            try:
                text = self.page_view.GetValue() or ""
            except Exception:
                return
            if not text or text == MSG_EMPTY:
                return
            lines = text.split("\n")
            if line < 0 or line >= len(lines):
                return
            pos = sum(len(lines[i]) + 1 for i in range(line))
            pos += max(0, min(col, len(lines[line])))
            try:
                self.page_view.SetInsertionPoint(wx_index(self.page_view, pos))
            except Exception:
                pass

        def _caret_line_col(self):
            line, col, _text, _total = self._caret_bits_from(self.page_view)
            return line, col

        def _show_page(self, speak: bool):
            shown = self._shown_page_text()
            lines = shown.split("\n") if shown else []
            if lines and not (0 <= self._line < len(lines)):
                self._line = len(lines) - 1
            if not lines:
                self._line = 0
            self._refresh_page_view()
            col = int(getattr(self, "_keep_col", 0) or 0)
            self._keep_col = 0
            if lines:
                col = max(0, min(col, len(lines[self._line])))
            else:
                col = 0
            self._set_page_caret(self._line if lines else 0, col)
            pos = col
            if lines and self._line > 0:
                pos = sum(len(lines[i]) + 1 for i in range(min(self._line, len(lines)))) + col
            self._fill_editor(pos, speak=speak)

        def _fill_editor(self, pos: int, speak: bool):
            text = self._shown_page_text()
            self._filling = True
            try:
                self.txt.ChangeValue(text)
                plain = max(0, min(int(pos or 0), len(text)))
                self.txt.SetInsertionPoint(wx_index(self.txt, plain))
                line = text.count("\n", 0, plain) if text else 0
                start = text.rfind("\n", 0, plain) + 1 if text else 0
                self._saved_line = line
                self._saved_col = plain - start
            finally:
                self._filling = False
            phrase = self._cursor_status()
            if speak:
                self._say(phrase)
            else:
                self._show_status(phrase)

        def _cursor_status(self) -> str:
            line, col, line_text, _total = self._caret_bits()
            plain = self._current_line_text()
            if plain:
                line_text = plain
                col = min(col, len(plain))
            row = self._row()
            if not self._src:
                head = self._page_label()
            elif not self._shown_page_text() and not self._text_rows():
                head = f"{self._page_label()} {MSG_EMPTY}"
            elif row is not None:
                head = f"{self._page_label()} {row.place_sentence()}"
            else:
                head = f"{self._page_label()} {self._added_where(line)}"
            phrase = f"{head} {cursor_phrase(line_text, col)}"
            extra = []
            if self._mark_open and self._mark_page == self._page:
                verb, _done, keys, button = _MARK_UI.get(
                    self._mark_op, ("segna", "Segnato", "Alt+X", "Evidenzia"),
                )
                extra.append(
                    f"Inizio {verb}, non ancora chiuso. "
                    f"{keys} un'altra volta, senza spostarti, "
                    f"oppure Invio sul pulsante {button}, o un clic, "
                    f"arriva in fondo a questa riga. "
                    f"Se ti sposti, anche più sotto, {keys} chiude sul carattere su cui stai."
                )
            folded = (line_text or "").strip().lower()
            if "fine nota" in folded:
                extra.append("La nota finisce qui, con Fine nota.")
            elif self._note_open and self._note_page == self._page:
                extra.append(
                    "Nota partita, non ancora chiusa. "
                    "Alt+J un'altra volta, senza spostarti, "
                    "oppure Invio sul pulsante Annotazione, o un clic, "
                    "scrive Fine nota in fondo a questa riga. "
                    "Se ti sposti, anche più sotto, anche sul punto, "
                    "Alt+J scrive Fine nota dopo il carattere su cui stai."
                )
            elif folded.startswith("nota:"):
                extra.append(
                    "Nota dall'inizio di questa riga. "
                    "Finisce all'ultimo carattere della riga."
                )
            if folded.startswith("firmato:"):
                extra.append("Questa riga è la firma, in corsivo.")
            if row is not None and row.marks:
                extra.append("Segni: " + ". ".join(row.marks) + ".")
            if row is not None and row.link:
                extra.append(
                    f"Collegamento verso {row.link}. "
                    "Invio sul pulsante Apri collegamento, o un clic, apre il browser."
                )
            name = (self.txt_link_name.GetValue() or "").strip() if hasattr(self, "txt_link_name") else ""
            if name and row is not None and row.link:
                extra.append(f"Nome del sito: {name}.")
            signed = [
                item.text for item in self._text_rows()
                if (item.text or "").startswith("Firmato:")
            ]
            if signed and not folded.startswith("firmato:"):
                extra.append("Firma già in questa pagina: " + signed[0])
            if extra:
                phrase = " ".join(extra) + " " + phrase
            if self._page_dirty():
                phrase += (
                    " Non ancora scritta nel file. "
                    "Invio sul pulsante Riscrivi, o un clic, la scrive. "
                    "Il file di partenza resta com'è."
                )
            return phrase

        def _capture_drafts(self):
            saved = []
            for row in self._rows:
                if row.preview is not None and row.preview != (row.text or ""):
                    saved.append(
                        (row.page, row.text or "", row.kind, row.field or "", row.preview)
                    )
            return saved

        def _restore_drafts(self, saved):
            used = set()
            for page, original, kind, field, preview in saved:
                for index, row in enumerate(self._rows):
                    if index in used:
                        continue
                    if (
                        row.page == page
                        and (row.text or "") == original
                        and row.kind == kind
                        and (row.field or "") == field
                    ):
                        row.preview = preview
                        used.add(index)
                        break

        def _find_prefer(self, prefer_text: str):
            pages = self._page_count or 1
            page = self._page if 1 <= self._page <= pages else 1
            if not prefer_text:
                rows = [row for row in self._rows if row.page == page]
                if rows and 0 <= self._line < len(rows):
                    return page, self._line
                return page, 0
            for row in self._rows:
                shown = row.preview if row.preview is not None else (row.text or "")
                if prefer_text not in (row.text or "") and prefer_text not in shown:
                    continue
                line = 0
                for other in self._rows:
                    if other.page != row.page:
                        continue
                    if other is row:
                        return row.page, line
                    line += 1
            return page, 0

        def _change_page(self, delta: int):
            if not self._src or self._page_count <= 0:
                self._say("Apri un PDF. Invio sul pulsante Apri documento, o un clic.")
                return
            new = self._page + delta
            if new < 1:
                self._say(f"Sei già sulla prima pagina. {self._page_label()}")
                return
            if new > self._page_count:
                self._say(f"Sei già sull'ultima pagina. {self._page_label()}")
                return
            self._page = new
            self._line = 0
            self._show_page(speak=False)
            try:
                self._speaker(f"Pagina {self._page} di {self._page_count}.")
            except Exception:
                pass

        def _on_page_key(self, event):
            event.Skip()
            wx.CallAfter(self._after_page_caret, False)

        def _on_page_click(self, event):
            event.Skip()
            wx.CallAfter(self._after_page_caret, False)

        def _on_page_dclick(self, event):
            event.Skip()
            wx.CallAfter(self._enter_editor)

        def _after_page_caret(self, _speak: bool):
            if not self._open:
                return
            line, col = self._caret_line_col()
            pos = self._plain_pos(line, col)
            shown = self._shown_page_text()
            if (self.txt.GetValue() or "") != shown:
                self._fill_editor(pos, speak=False)
            else:
                self._filling = True
                try:
                    plain = max(0, min(pos, len(shown)))
                    self.txt.SetInsertionPoint(wx_index(self.txt, plain))
                    line_no = shown.count("\n", 0, plain) if shown else 0
                    start = shown.rfind("\n", 0, plain) + 1 if shown else 0
                    self._saved_line = line_no
                    self._saved_col = plain - start
                finally:
                    self._filling = False
                self._show_status(self._cursor_status())
            line, _col, _text, _total = self._caret_bits()
            self._line = line

        def _enter_editor(self):
            self._after_page_caret(False)
            try:
                self.txt.SetFocus()
            except Exception:
                return

        def _on_editor_text(self, event):
            if self._filling or not self._open:
                return
            value = (self.txt.GetValue() or "").replace("\r\n", "\n").replace("\r", "\n")
            if value == self._original_page_text():
                self._page_draft.pop(self._page, None)
            else:
                self._page_draft[self._page] = value
            self._close_warned = False
            self._refresh_page_view()
            self._remember_editor_caret()
            try:
                self._set_page_caret(self._saved_line, self._saved_col)
            except Exception:
                pass
            self._line = self._saved_line
            self._show_status(self._cursor_status())

        def _on_editor_leave(self, event):
            self._remember_editor_caret()
            event.Skip()

        def _on_editor_key(self, event):
            event.Skip()
            wx.CallAfter(self._after_caret)

        def _on_editor_click(self, event):
            event.Skip()
            wx.CallAfter(self._after_caret)

        def _after_caret(self):
            if not self._open:
                return
            self._remember_editor_caret()
            try:
                self._set_page_caret(self._saved_line, self._saved_col)
            except Exception:
                pass
            self._line = self._saved_line
            self._show_status(self._cursor_status())

        def _choices(self) -> tuple:
            place = PLACES[max(0, self.place.GetSelection())][0]
            font = FONTS[max(0, self.font.GetSelection())][0]
            size = SIZES[max(0, self.size.GetSelection())][0]
            return place, font, size

        def _work_paths(self):
            if not self._src:
                return "", ""
            return self._src, output_pdf(self._src)

        def _reload(self, prefer_text: str = ""):
            drafts = self._capture_drafts()
            rows, pages, err = read_marks(self._src)
            self._page_count = pages
            if err:
                self._rows = []
                self._show_page(speak=False)
                self._say(err)
                return
            self._rows = rows
            self._restore_drafts(drafts)
            keep_line = getattr(self, "_keep_line", None)
            find = getattr(self, "_keep_find", "") or ""
            self._keep_line = None
            self._keep_find = ""
            if keep_line is not None:
                pages = self._page_count or 1
                self._page = self._page if 1 <= self._page <= pages else 1
                texts = self._page_line_texts()
                self._line = line_for_keep(texts, int(keep_line), find)
                if texts and find and find in (texts[self._line] or ""):
                    if find == "Fine nota":
                        at = texts[self._line].find("Fine nota")
                        self._keep_col = min(len(texts[self._line]), at + len("Fine nota."))
                    elif not (0 <= int(keep_line) < len(texts)):
                        at = texts[self._line].find(find)
                        self._keep_col = min(len(texts[self._line]), at + len(find))
            else:
                self._keep_col = 0
                page, line = self._find_prefer(prefer_text)
                self._page = page
                self._line = line
            self._show_page(speak=False)

        def _load_path(self, path: str):
            path = (path or "").strip().strip('"')
            if not path or not os.path.isfile(path):
                self._say(MSG_READ)
                return
            if os.path.splitext(path)[1].lower() != ".pdf":
                self._say(os.path.basename(path) + " " + MSG_NOT_PDF)
                return
            written = output_pdf(path)
            opened_written = False
            if (
                os.path.abspath(written) != os.path.abspath(path)
                and os.path.isfile(written)
            ):
                path = written
                opened_written = True
            self._src = path
            self._dest = ""
            self._signed = has_signature(path)
            self._page = 1
            self._line = 0
            self._page_draft = {}
            self.SetTitle("Scrivi nel PDF — " + os.path.basename(path))
            rows, pages, err = read_marks(path)
            self._page_count = pages
            if err:
                self._rows = []
                self._show_page(speak=False)
                self._say(err)
                return
            self._rows = rows
            self._show_page(speak=False)
            if opened_written:
                sentence = (
                    f"Aperto {os.path.basename(path)}, il file già scritto di questo PDF. "
                    f"{pages} pagine, {len(rows)} righe. "
                    "Non ne apro un altro. Il file di partenza resta com'è."
                )
            else:
                sentence = (
                    f"Aperto {os.path.basename(path)}, "
                    f"{pages} pagine, {len(rows)} righe. "
                    "Il file di partenza resta com'è."
                )
            if self._signed:
                sentence += (
                    " C'è una firma elettronica. Il file nuovo non la porta. "
                    "La firma p7m resta di Aruba Sign."
                )
            if not rows:
                sentence += " " + MSG_EMPTY
            self._say(sentence)

        def _load_initial(self):
            paths = []
            for path in self._initial:
                if path and os.path.isfile(path):
                    paths.append(path)
            self._initial = []
            if not paths:
                return
            if len(paths) > 1:
                self._say(
                    "Apro il primo PDF. Gli altri restano fuori: "
                    "questa finestra lavora su un PDF."
                )
            self._load_path(paths[0])

        def _on_open(self, _event=None):
            dlg = wx.FileDialog(
                self,
                "Apri un PDF",
                wildcard=_WILDCARD,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            )
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                return
            path = dlg.GetPath()
            dlg.Destroy()
            self._load_path(path)

        def _on_image(self, _event=None):
            dlg = wx.FileDialog(
                self,
                "Immagine della firma",
                wildcard=_IMAGE_WILDCARD,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            )
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                return
            path = dlg.GetPath()
            dlg.Destroy()
            self.txt_image.SetValue(path)
            try:
                import PIL.Image  # noqa: F401
                pillow = True
            except Exception:
                pillow = False
            if pillow:
                self._say(
                    f"Immagine della firma: {os.path.basename(path)}. "
                    "Invio sul pulsante Firma, o un clic, la mette in basso a destra."
                )
            else:
                self._say(
                    f"Immagine scelta: {os.path.basename(path)}. "
                    "Sull'Add-on l'immagine non entra: manca Pillow. "
                    "Il nome scritto entra lo stesso."
                )

        def _apply(self, action: dict, prefer: str = ""):
            if not self._src:
                self._say("Apri un PDF. Invio sul pulsante Apri documento, o un clic.")
                return
            src, dest = self._work_paths()
            if not dest:
                self._say(MSG_FAIL)
                return
            if os.path.abspath(src) == os.path.abspath(dest) and os.path.isfile(dest):
                pass
            ok, sentence, written = apply_edit(src, dest, action)
            if not ok:
                self._say(sentence or MSG_FAIL)
                return
            self._dest = written
            self._src = written
            self._reload(prefer)
            lead = (self._pending_note or "").strip()
            self._pending_note = ""
            body = (sentence or "").strip()
            if lead.startswith("Collegamento"):
                sentence = (lead + " " + body).strip()
            elif lead:
                sentence = (body + " " + lead).strip()
            else:
                sentence = body
            self._focus_editor()
            self._say(sentence)

        def _editor_text(self) -> str:
            try:
                return self.txt.GetValue()
            except Exception:
                return ""

        def _current_line_text(self) -> str:
            line, _col, _text, _total = self._caret_bits()
            shown = self._shown_page_text()
            lines = shown.split("\n") if shown else []
            if 0 <= line < len(lines):
                return lines[line]
            return ""

        def _saved_name(self) -> str:
            return os.path.basename(self._src or self._dest or "")

        def _confirm_saved(self):
            """Alt+E salva sempre nello stesso nome-scritto. Non crea -2."""
            src, dest = self._work_paths()
            if not dest:
                self._say(MSG_FAIL)
                return
            name = os.path.basename(dest)
            if os.path.abspath(src) == os.path.abspath(dest):
                if os.path.isfile(dest):
                    os.utime(dest, None)
                self._say(
                    f"Salvato in {name}. C'è tutto quello che è in questa pagina. "
                    "Non ho fatto un altro file."
                )
                return
            if os.path.isfile(dest):
                self._say(
                    f"Salvato in {name}. È il file di questo PDF. "
                    "Non ne ho fatto un altro. Il file di partenza resta com'è."
                )
                return
            import shutil

            shutil.copy2(src, dest)
            self._dest = dest
            self._src = dest
            self._reload("")
            self._say(
                f"Salvato in {name}. C'è tutto quello che è in questa pagina."
            )

        def _on_replace(self, _event=None):
            if not self._need_pdf():
                return
            lines, line, col = self._editor_caret()
            self._keep_line = line
            self._keep_col = col
            self._keep_find = note_caret_find(lines[line] if lines else "", col)
            kept = self._current_line_text().strip()
            ok, sentence = self._commit_text(self._editor_text(), kept[:40])
            if not ok:
                return
            self._pending_note = ""
            if sentence == MSG_NOTHING_NEW:
                self._confirm_saved()
                return
            self._say("Salvato. " + (sentence or ""))

        def _insert_action(self, op: str) -> dict:
            place, font, size = self._choices()
            row = self._row()
            page = 1
            if place == "nuova":
                src, dest = self._work_paths()
                if not src:
                    return {}
                ok, sentence, written = apply_edit(src, dest, {"op": "blank"})
                if not ok:
                    self._say(sentence or MSG_FAIL)
                    return {}
                self._dest = written
                self._src = written
                _rows, pages, err = read_marks(written)
                if err:
                    self._say(err)
                    return {}
                page = pages
                place = "alto-sinistra"
                row = None
            elif row is not None:
                page = row.page
            elif self._page_count:
                page = self._page_count
            action = {
                "op": op,
                "page": page,
                "place": place,
                "row": row,
                "text": self._current_line_text(),
                "font": font,
                "size": size,
                "url": (self.txt_url.GetValue() or "").strip(),
            }
            return action

        def _on_insert(self, _event=None):
            if not self._src:
                self._say("Apri un PDF. Invio sul pulsante Apri documento, o un clic.")
                return
            action = self._insert_action("insert")
            if not action:
                return
            self._apply(action, prefer=(action.get("text") or "").split("\n")[0])

        def _need_pdf(self) -> bool:
            if self._src:
                return True
            self._say("Apri un PDF. Invio sul pulsante Apri documento, o un clic.")
            return False

        def _editor_caret(self):
            text = (self._editor_text() or "").replace("\r\n", "\n").replace("\r", "\n")
            lines = text.split("\n") if text else [""]
            if not lines:
                lines = [""]
            try:
                if self.FindFocus() is self.txt:
                    self._remember_editor_caret()
            except Exception:
                pass
            line = max(0, min(int(self._saved_line or 0), len(lines) - 1))
            col = max(0, min(int(self._saved_col or 0), len(lines[line])))
            return lines, line, col

        def _where_words(self, lines, line, col) -> str:
            current = lines[line] if lines else ""
            if not current.strip():
                prev = next((item.strip() for item in reversed(lines[:line]) if item.strip()), "")
                nxt = next((item.strip() for item in lines[line + 1:] if item.strip()), "")
            else:
                prev = current[:col].strip()
                nxt = current[col:].strip()
            bits = []
            if prev:
                bits.append("dopo «" + prev[-50:] + "»")
            if nxt:
                bits.append("prima di «" + nxt[:60] + "»")
            return ", ".join(bits)

        def _following_text(self, lines, line, col):
            current = lines[line] if lines else ""
            rest = current[col:].strip()
            if rest:
                return rest, "fino alla fine di questa riga"
            nxt = next((item.strip() for item in lines[line + 1:] if item.strip()), "")
            if nxt:
                return nxt, "è il testo che segue"
            return "", ""

        def _splice(self, piece: str) -> str:
            """Mette il testo dove sta il cursore, sulla stessa riga."""
            lines, line, col = self._editor_caret()
            current = lines[line]
            piece_lines = (piece or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
            if not piece_lines:
                piece_lines = [""]
            if not current.strip():
                lines[line:line + 1] = piece_lines
                end_line = line + len(piece_lines) - 1
                end_col = len(piece_lines[-1])
            else:
                left, right = current[:col], current[col:]
                if left and not left[-1].isspace():
                    left += " "
                gap = ""
                if right and not right[0].isspace() and piece and not piece.endswith((" ", "\n")):
                    gap = " "
                if len(piece_lines) == 1:
                    lines[line] = left + piece_lines[0] + gap + right
                    end_line = line
                    end_col = len(left) + len(piece_lines[0]) + len(gap)
                else:
                    lines[line] = left + piece_lines[0]
                    last = piece_lines[-1] + gap + right
                    lines[line + 1:line + 1] = piece_lines[1:-1] + [last]
                    end_line = line + len(piece_lines) - 1
                    end_col = len(piece_lines[-1]) + len(gap)
            self._keep_line = end_line
            self._keep_col = end_col
            self._keep_find = note_caret_find(lines[end_line] if lines else "", end_col)
            return "\n".join(lines)

        def _commit_text(self, text: str, prefer: str) -> tuple:
            _place, font, size = self._choices()
            rows = self._text_rows()
            actions, err = plan_page_edits(rows, text, font, size)
            if err:
                self._say(err)
                return False, ""
            if not actions:
                self._page_draft.pop(self._page, None)
                self._reload(prefer)
                return True, MSG_NOTHING_NEW
            src, dest = self._work_paths()
            if not dest:
                self._say(MSG_FAIL)
                return False, ""
            ok, sentence, written = apply_edits(src, dest, actions)
            if not ok:
                self._say(sentence or MSG_FAIL)
                return False, ""
            self._dest = written
            self._src = written
            self._page_draft.pop(self._page, None)
            self._reload(prefer)
            return True, sentence

        def _commit_draft(self) -> bool:
            if not self._page_dirty():
                return True
            kept = self._current_line_text().strip()
            ok, sentence = self._commit_text(self._editor_text(), kept[:40])
            if not ok:
                return False
            if sentence and sentence != MSG_NOTHING_NEW:
                self._pending_note = sentence
            return True

        def _link_address(self):
            field = (self.txt_url.GetValue() or "").strip()
            folded = field.lower().replace("pagina", "").strip()
            if looks_web(field) or folded.isdigit():
                return field, "dal campo Indirizzo"
            row = self._row()
            if row is not None and row.link:
                return row.link, "dal collegamento di questa riga"
            line = self._current_line_text().strip()
            if looks_web(line):
                return line, "dalla riga dove sta il cursore"
            return "", ""

        def _gap_below(self, row, size):
            """Un punto sotto la riga del cursore, se ci sta."""
            if row is None:
                return 50, 48, "", False
            rows = [item for item in self._text_rows() if item.page == row.page]
            nxt = None
            for item in rows:
                if item.index == row.index + 1:
                    nxt = item
                    break
            ys = _slot_ys(row, nxt, 1, size)
            if not ys:
                if nxt is not None:
                    return 0, 0, MSG_NO_GAP.format(a=row.index, b=nxt.index), False
                return 0, 0, MSG_NO_GAP_BELOW, False
            return row.x, ys[0], "", True

        def _on_link(self, _event=None):
            if not self._need_pdf():
                return
            name = (self.txt_link_name.GetValue() or "").strip()
            url, origin = self._link_address()
            if looks_web(name):
                self._say(
                    "Nel campo Nome del sito va il nome, per esempio Juventus. "
                    "L'indirizzo http sta nel campo Indirizzo."
                )
                return
            if not name:
                self._say(
                    "Nel campo Nome del sito scrivi il nome, per esempio Juventus, "
                    "o Juventus Football Club. Nel campo Indirizzo l'indirizzo. "
                    "Poi Alt+W, oppure Invio sul pulsante Collegamento web, o un clic."
                )
                return
            if not url:
                self._say(MSG_BAD_LINK)
                return
            lines, line, col = self._editor_caret()
            where = self._where_words(lines, line, col)
            current = lines[line] if lines else ""
            already = span_on_line(current, name, col)
            if already >= 0:
                self._keep_line = line
                self._keep_col = already + len(name)
                self._keep_find = name
                self._pending_note = (
                    f"Collegamento «{name}» verso {url}. "
                    "Il nome era già sulla riga, non l'ho riscritto. "
                    "Il cursore resta dopo il nome."
                )
            else:
                text = self._splice(name)
                keep_line, keep_col = self._keep_line, self._keep_col
                keep_find = self._keep_find or name
                ok, sentence = self._commit_text(text, name[:40])
                if not ok:
                    return
                self._keep_line = keep_line
                self._keep_col = keep_col
                self._keep_find = keep_find
                landed = (
                    f"Collegamento «{name}» verso {url}. "
                    "Il nome è stato scritto dove sta il cursore"
                    + (f", {where}" if where else "")
                    + ". Il cursore resta dopo il nome."
                )
                self._pending_note = landed
            row = None
            rows = self._text_rows()
            mapped = self._line_map().get(line)
            if mapped is not None and 0 <= mapped < len(rows) and name in (rows[mapped].text or ""):
                row = rows[mapped]
            if row is None:
                for item in rows:
                    if name in (item.text or ""):
                        row = item
                        break
            if row is None:
                self._say(self._pending_note or MSG_NEW_LINE)
                self._pending_note = ""
                return
            start = span_on_line(row.text or "", name, self._keep_col or 0)
            if start < 0:
                start = 0
            _place, font, size = self._choices()
            self._apply(
                {
                    "op": "link",
                    "page": row.page,
                    "place": "sulla-riga",
                    "row": row,
                    "text": name,
                    "url": url,
                    "origin": origin,
                    "start": start,
                    "end": start + len(name),
                    "font": font,
                    "size": size,
                },
                prefer=name[:40],
            )

        def _on_open_link(self, _event=None):
            import webbrowser

            url, origin = self._link_address()
            if not looks_web(url):
                self._say(
                    "Non c'è un indirizzo da aprire. "
                    "Scrivilo nel campo Indirizzo, "
                    "oppure metti il cursore sulla riga del collegamento. "
                    "Poi Invio sul pulsante Apri collegamento, o un clic. "
                    "Il campo Nome e cognome è la firma, non si apre."
                )
                return
            try:
                webbrowser.open(url)
            except Exception:
                self._say("Non sono riuscito ad aprire il browser.")
                return
            self._say(
                f"Apro {url} nel browser, {origin}. "
                "Questa finestra resta aperta. Il PDF resta qui."
            )

        def _on_note(self, _event=None):
            if not self._need_pdf():
                return
            if self._note_open and self._note_page == self._page:
                self._close_auto_note()
                return
            lines, line, col = self._editor_caret()
            referred, _reach = self._following_text(lines, line, col)
            if not referred:
                self._say(
                    "Non c'è testo dopo il cursore da annotare. "
                    "Metti il cursore prima delle parole già scritte, poi Alt+J, "
                    "oppure Invio sul pulsante Annotazione, o un clic. "
                    "Per una nota tua, Alt+Maiusc+M, oppure Invio sul pulsante Nota mia, o un clic."
                )
                return
            where = self._where_words(lines, line, col)
            text = self._splice("Nota:")
            note_line = self._keep_line
            note_col = self._keep_col
            ok, sentence = self._commit_text(text, "Nota")
            if not ok:
                self._note_open = False
                return
            self._note_open = True
            self._note_page = self._page
            self._note_line = note_line
            self._note_col = note_col
            written = sentence if sentence and sentence != MSG_NOTHING_NEW else ""
            detail = (
                "Nota dove sta il cursore"
                + (f", {where}" if where else "")
                + ". Riguarda il testo già scritto che segue. "
                "Alt+J un'altra volta, senza spostarti, "
                "oppure Invio sul pulsante Annotazione, o un clic, "
                "scrive Fine nota in fondo a questa riga. "
                "Se la frase continua, vai sull'ultimo carattere da includere, "
                "anche più sotto, anche sul punto, "
                "e premi Alt+J, oppure Invio sul pulsante Annotazione, o un clic: "
                "Fine nota si scrive dopo quel carattere. Il cursore resta lì."
            )
            self._say(detail + ((" " + written) if written else ""))
            self._focus_editor()

        def _close_auto_note(self):
            lines, line, col = self._editor_caret()
            new_lines, end_line, end_col, how = close_auto_note(
                lines, line, col, self._note_line, self._note_col,
            )
            if how == "before":
                self._say(
                    "Sei prima di Nota. "
                    "Per chiudere in fondo a questa riga, torna dopo Nota e premi Alt+J, "
                    "oppure Invio sul pulsante Annotazione, o un clic. "
                    "Per chiudere più avanti, vai sull'ultimo carattere da includere, "
                    "anche più sotto, anche sul punto, e premi Alt+J."
                )
                return
            self._keep_line = end_line
            self._keep_col = end_col
            self._keep_find = "Fine nota"
            ok, sentence = self._commit_text("\n".join(new_lines), "Fine nota")
            if not ok:
                return
            self._note_open = False
            finished = new_lines[end_line] if new_lines else ""
            cut = finished.rfind("Fine nota.")
            prev = finished[:cut].rstrip() if cut >= 0 else finished.rstrip()
            last = prev[-1] if prev else ""
            written = sentence if sentence and sentence != MSG_NOTHING_NEW else ""
            if how == "line":
                detail = (
                    "Fine nota in fondo a questa riga"
                    + (f", dopo «{last}»" if last else "")
                    + ". La nota copre questa riga, fino a Fine nota. "
                    "Il cursore resta dopo Fine nota."
                )
            else:
                detail = (
                    "Fine nota dopo "
                    + (f"«{last}». " if last else "quel carattere. ")
                    + "La nota arriva fin qui, anche se la frase occupa più righe. "
                    "Il cursore resta dopo Fine nota."
                )
            self._say(detail + ((" " + written) if written else ""))
            self._focus_editor()

        def _on_note_manual(self, _event=None):
            if not self._need_pdf():
                return
            lines, line, col = self._editor_caret()
            where = self._where_words(lines, line, col)
            message = (
                "Nota mia. Il testo entra dove sta il cursore"
                + (f", {where}" if where else "")
                + ". Invio va a capo: la nota può stare su più righe, e con le frecce si scorre. "
                "L'ultima riga sarà Fine nota, così si sa dove termina. "
                "Non segna il testo che segue. "
                "Invio sul pulsante Inserisci, o un clic, la mette. Annulla non scrive. "
                "Poi, nella pagina in modifica, si può cambiare. Alt+E la riscrive nel file."
            )
            dlg = wx.Dialog(
                self,
                title="Nota mia",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            box = wx.BoxSizer(wx.VERTICAL)
            box.Add(wx.StaticText(dlg, label=message), 0, wx.ALL, 8)
            field = wx.TextCtrl(dlg, style=wx.TE_MULTILINE)
            field.SetName("Testo della nota")
            box.Add(field, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
            buttons = wx.BoxSizer(wx.HORIZONTAL)
            ok = wx.Button(dlg, wx.ID_OK, "Inserisci")
            cancel = wx.Button(dlg, wx.ID_CANCEL, "Annulla")
            buttons.Add(ok, 0, wx.RIGHT, 6)
            buttons.Add(cancel, 0)
            box.Add(buttons, 0, wx.ALL, 8)
            dlg.SetSizer(box)
            dlg.SetMinSize((560, 280))
            dlg.Fit()
            self._note_dialog = True
            try:
                code = dlg.ShowModal()
                extra = field.GetValue() if code == wx.ID_OK else ""
            finally:
                self._note_dialog = False
                dlg.Destroy()
            if code != wx.ID_OK:
                self._say("Nota mia annullata. Il cursore resta dov'era.")
                return
            if not (extra or "").strip():
                self._say("Il testo della nota è vuoto. Non ho scritto.")
                return
            piece = wrap_note(extra)
            text = self._splice(piece)
            ok, sentence = self._commit_text(text, "Nota")
            if not ok:
                return
            written = sentence if sentence and sentence != MSG_NOTHING_NEW else ""
            count = len([line for line in piece.split("\n") if line.strip()])
            detail = (
                f"Nota mia scritta. {count} righe. L'ultima è Fine nota. "
                "Il cursore resta dopo Fine nota."
            )
            tail = ""
            if written and "spazio" in written:
                tail = " " + written
            self._say(detail + tail)
            self._focus_editor()

        def _mark_end(self) -> int:
            """Il carattere su cui sta la freccia è incluso. Quello dopo resta fuori."""
            lines, line, col = self._editor_caret()
            current = lines[line] if lines else ""
            if col < len(current):
                return col + 1
            return len(current)

        def _mark(self, op: str):
            if not self._need_pdf():
                return
            lines, line, col = self._editor_caret()
            if (
                self._mark_open
                and self._mark_op == op
                and self._mark_page == self._page
            ):
                self._close_mark(lines, line, col)
                return
            current = lines[line] if lines else ""
            verb, _done, keys, button = _MARK_UI.get(
                op, ("segna", "Segnato", "Alt+X", "Evidenzia"),
            )
            if not current or col >= len(current):
                self._say(
                    f"Vai sul carattere da cui far partire {verb}, incluso. "
                    f"Poi {keys}, oppure Invio sul pulsante {button}, o un clic, "
                    "un'altra volta sull'ultimo carattere da includere. "
                    "Per escludere il punto, fermati sulla lettera prima del punto."
                )
                return
            self._mark_open = True
            self._mark_op = op
            self._mark_page = self._page
            self._mark_line = line
            self._mark_col = col
            word = word_at(current, col)
            self._say(
                f"Inizio {verb} sul carattere «{current[col]}», nella parola «{word}». "
                f"{keys} un'altra volta, senza spostarti, "
                f"oppure Invio sul pulsante {button}, o un clic, "
                "arriva in fondo a questa riga. "
                "Se la frase continua, vai sull'ultimo carattere da includere, "
                "anche più sotto, anche sul punto, "
                f"e {keys}, oppure Invio sul pulsante {button}, o un clic. "
                "Quel carattere entra. Quello dopo resta fuori."
            )

        def _close_mark(self, lines, line, col):
            verb, done, keys, button = _MARK_UI.get(
                self._mark_op, ("segna", "Segnato", "Alt+X", "Evidenzia"),
            )
            ranges = mark_ranges(lines, self._mark_line, self._mark_col, line, col)
            if not ranges:
                self._say(
                    f"Sei prima dell'inizio di {verb}. "
                    f"Vai avanti, sul carattere dove vuoi chiudere, "
                    f"e premi {keys}, oppure Invio sul pulsante {button}, o un clic. "
                    "Quel carattere entra. Quello dopo resta fuori."
                )
                return
            self._keep_line = line
            self._keep_col = col
            current = lines[line] if lines else ""
            self._keep_find = note_caret_find(current, col)
            if not self._commit_draft():
                return
            lines, line, col = self._editor_caret()
            ranges = mark_ranges(lines, self._mark_line, self._mark_col, line, col)
            if not ranges:
                self._mark_open = False
                self._say(
                    f"{done} non è stato scritto: la riga di partenza non c'è più. "
                    f"Rimetti il cursore sul carattere di inizio e premi {keys}."
                )
                return
            actions = []
            for eline, start, end in ranges:
                row = self._row_at(eline)
                if row is None:
                    continue
                actions.append({
                    "op": self._mark_op,
                    "page": row.page,
                    "row": row,
                    "start": start,
                    "end": min(end, len(row.text or "")),
                })
            if not actions:
                self._mark_open = False
                self._say(MSG_NEW_LINE)
                return
            first_line, first_start, _first_end = ranges[0]
            last_line, _last_start, last_end = ranges[-1]
            first_text = lines[first_line] if first_line < len(lines) else ""
            last_text = lines[last_line] if last_line < len(lines) else ""
            first_word = word_at(first_text, first_start)
            last_ch = last_text[last_end - 1] if 0 < last_end <= len(last_text) else ""
            outside = last_text[last_end:last_end + 1] if last_end < len(last_text) else ""
            count = sum(max(0, end - start) for _line, start, end in ranges)
            lead = (
                f"{done} da «{first_word}» fino a «{last_ch}». {count} caratteri."
            )
            if len(ranges) > 1:
                lead += f" Su {len(ranges)} righe."
            if outside:
                lead += f" Il carattere dopo, «{outside}», resta fuori."
            else:
                lead += " Fino all'ultimo carattere, incluso."
            lead += " Il cursore resta lì."
            src, dest = self._work_paths()
            ok, sentence, written = apply_mark_spans(src, dest, actions, lead)
            if not ok:
                self._say(sentence or MSG_FAIL)
                return
            self._mark_open = False
            self._dest = written
            self._src = written
            self._keep_line = line
            self._keep_col = col
            self._keep_find = note_caret_find(last_text, col)
            self._reload("")
            self._focus_editor()
            pending = (self._pending_note or "").strip()
            self._pending_note = ""
            if pending:
                sentence = (sentence or "").strip() + " " + pending
            self._say(sentence)

        def _row_at(self, line: int):
            rows = self._text_rows()
            mapped = self._line_map().get(line)
            if mapped is None or mapped < 0 or mapped >= len(rows):
                return None
            return rows[mapped]

        def _on_sign(self, _event=None):
            if not self._need_pdf():
                return
            name = (self.txt_name.GetValue() or "").strip()
            image = (self.txt_image.GetValue() or "").strip()
            if looks_web(name):
                self._say(MSG_NAME_IS_URL)
                return
            if not name and not image:
                self._say(MSG_NEED_NAME)
                return
            place, font, size = self._choices()
            already = [
                item.text for item in self._rows
                if (item.text or "").startswith("Firmato:")
            ]
            already_bit = ("Firma già presente: " + already[0] + ".") if already else ""
            if name and place == "sotto":
                when = time.strftime("%d/%m/%Y")
                piece = f"Firmato: {name}, {when}."
                lines, line, col = self._editor_caret()
                place_words = self._where_words(lines, line, col)
                text = self._splice(piece)
                ok, sentence = self._commit_text(text, piece[:40])
                if not ok:
                    return
                written = sentence if sentence and sentence != MSG_NOTHING_NEW else ""
                spoken = (
                    (already_bit + " " if already_bit else "")
                    + "Nome e cognome scritti dove sta il cursore"
                    + (f", {place_words}" if place_words else "")
                    + f": {piece} "
                    + written
                ).strip()
                if image:
                    self._pending_note = spoken
                    self._keep_line = self._saved_line
                    self._keep_col = self._saved_col
                    row = self._row()
                    page = row.page if row is not None else (self._page_count or 1)
                    self._apply(
                        {
                            "op": "sign",
                            "page": page,
                            "name": "",
                            "image": image,
                            "font": font,
                            "size": size,
                        },
                        prefer=piece[:40],
                    )
                    return
                self._say(spoken + " La firma elettronica p7m resta di Aruba Sign.")
                return
            row = self._row()
            page = row.page if row is not None else (self._page_count or 1)
            self._apply(
                {
                    "op": "sign",
                    "page": page,
                    "place": place,
                    "row": row,
                    "name": name,
                    "image": image,
                    "font": font,
                    "size": size,
                    "already": already_bit,
                    "page_h": row.page_h if row is not None else 842,
                },
                prefer=(f"Firmato: {name}")[:40] if name else "",
            )

        def _on_close_ask(self, event=None):
            dirty = False
            try:
                dirty = bool(self._src) and self._page_dirty()
            except Exception:
                dirty = False
            if dirty and not self._close_warned:
                self._close_warned = True
                self._say(
                    "Ci sono modifiche non scritte nel file. "
                    "Invio sul pulsante Riscrivi, o un clic, le scrive: il file si chiama nome-scritto. "
                    "Se c'è già, si aggiorna quello. Esc non scrive. "
                    "Chiudi un'altra volta esce senza scriverle. Il file di partenza resta com'è."
                )
                if event is not None and hasattr(event, "Veto"):
                    try:
                        event.Veto()
                    except Exception:
                        pass
                return
            self._open = False
            self.EndModal(wx.ID_CANCEL)

        def _on_paste(self):
            paths = _paths_on_clipboard()
            pdfs = [
                path for path in paths
                if os.path.splitext(path)[1].lower() == ".pdf" and os.path.isfile(path)
            ]
            if not pdfs:
                self._say(MSG_CLIP_EMPTY)
                return
            self._load_path(pdfs[0])

        def _enable_file_drop(self):
            owner = self

            class _Drop(wx.FileDropTarget):
                def OnDropFiles(self, x, y, filenames):
                    pdfs = [
                        path for path in (filenames or [])
                        if os.path.splitext(path)[1].lower() == ".pdf"
                    ]
                    if not pdfs:
                        owner._say(MSG_CLIP_EMPTY)
                        return True
                    owner._load_path(pdfs[0])
                    return True

            self.SetDropTarget(_Drop())

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
                key in (ord("S"), ord("s"))
                and not event.ControlDown()
                and not event.AltDown()
                and not event.ShiftDown()
            ):
                focused = self.FindFocus()
                if focused is not self.txt:
                    self._say(self._cursor_status())
                    return
            if (
                event.AltDown()
                and event.ShiftDown()
                and not event.ControlDown()
                and key in (ord("M"), ord("m"))
            ):
                if not getattr(self, "_note_dialog", False):
                    self._on_note_manual()
                return
            if (
                event.AltDown()
                and event.ShiftDown()
                and not event.ControlDown()
                and key in (ord("Z"), ord("z"))
            ):
                self._mark("strike")
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
            if (
                key in (wx.WXK_PAGEUP, wx.WXK_PAGEDOWN)
                and not event.ControlDown()
                and not event.AltDown()
            ):
                focused = self.FindFocus()
                if focused is self.page_view or focused is self.txt:
                    self._change_page(-1 if key == wx.WXK_PAGEUP else 1)
                    return
            if key == wx.WXK_ESCAPE and not event.ControlDown() and not event.AltDown():
                self._on_close_ask(None)
                return
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                focused = self.FindFocus()
                if focused is self.page_view and not event.ControlDown() and not event.AltDown():
                    self._enter_editor()
                    return
            event.Skip()

        def _alt_do(self, name: str):
            if name == "open":
                self._on_open()
            elif name == "replace":
                self._on_replace()
            elif name == "insert":
                self._on_insert()
            elif name == "link":
                self._on_link()
            elif name == "note":
                self._on_note()
            elif name == "highlight":
                self._mark("highlight")
            elif name == "underline":
                self._mark("underline")
            elif name == "strike":
                self._mark("strike")
            elif name == "sign":
                self._on_sign()

    globals()["PdfDialog"] = PdfDialog


def _paths_on_clipboard() -> list:
    try:
        import wx
    except ImportError:
        return []
    paths = []
    try:
        if not wx.TheClipboard.Open():
            return []
        try:
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
                data = wx.FileDataObject()
                if wx.TheClipboard.GetData(data):
                    paths.extend(list(data.GetFilenames() or []))
            if not paths and wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                data = wx.TextDataObject()
                if wx.TheClipboard.GetData(data):
                    for line in (data.GetText() or "").splitlines():
                        line = line.strip().strip('"')
                        if line:
                            paths.append(line)
        finally:
            wx.TheClipboard.Close()
    except Exception:
        log.exception("appunti")
    return paths


try:
    _install_dialog()
except Exception:
    log.exception("finestra Scrivi nel PDF")
