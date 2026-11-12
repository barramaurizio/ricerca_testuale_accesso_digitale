# -*- coding: utf-8 -*-
"""Taglia e unisci immagini.

Un file nuovo, accanto. Quello di partenza non si tocca.
Stessa finestra nella Standalone e nell'Add-on. A schermo e a voce.
Invio e il clic sullo stesso pulsante. Sull'elenco, Invio e il doppio clic
dicono la riga. Un clic solo seleziona la riga.
"""

from __future__ import annotations

import logging
import os
import shutil

log = logging.getLogger("rtad.image")

MSG_EMPTY = "Nessun file in elenco."
MSG_NO_DONE = "Nessun risultato ancora."
MSG_SELECT = "Seleziona una riga."
MSG_FAIL = "Non sono riuscito a creare il file. Il file di partenza resta com'è."
MSG_NEED_TWO = (
    "Per unire servono almeno due immagini. "
    "Aggiungi un'altra immagine, oppure scegli un taglio e premi Esegui."
)
MSG_NEED_CROP = (
    "Nessun taglio e nessun giro: i campi sono ancora l'immagine intera. "
    "Invio sul pulsante Metà sinistra, Metà destra, Metà sopra, Metà sotto o Centro, "
    "o un clic. Oppure cambia un numero e Invio sul pulsante Tieni questo taglio, "
    "o un clic. Oppure Invio sul pulsante Un quarto a destra, Un quarto a sinistra "
    "o Mezzo giro, o un clic. Poi Esegui."
)
MSG_BAD_NUM = "Servono quattro numeri: sinistra, alto, larghezza, altezza."
MSG_NOT_IMAGE = "non è un'immagine."

_EXTS = {
    ".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".gif",
    ".tif", ".tiff", ".webp", ".ico",
}
_WILDCARD = (
    "Immagini|*.jpg;*.jpeg;*.jfif;*.png;*.bmp;*.gif;*.tif;*.tiff;*.webp;*.ico|"
    "Tutti i file|*.*"
)
_INTRO = (
    "Taglia e unisci immagini. "
    "Invio sul pulsante Aggiungi file, o un clic, mette le immagini in elenco. "
    "Invio sul pulsante Aggiungi cartella, o un clic, mette le immagini di quella cartella. "
    "Le cartelle che stanno dentro non si aprono. "
    "L'ordine dell'elenco è l'ordine del risultato. "
    "Invio sul pulsante Sposta su o Sposta giù, o un clic, cambia l'ordine. "
    "Invio o doppio clic su una riga rilegge i quattro campi rispetto all'immagine intera. "
    "Un clic solo seleziona la riga. "
    "I quattro numeri sono sinistra, alto, larghezza e altezza. "
    "Prima di un taglio, i campi mostrano l'immagine intera: "
    "sinistra 0, alto 0, larghezza e altezza originali. "
    "Invio sul pulsante Metà sinistra, Metà destra, Metà sopra, Metà sotto o Centro, "
    "o un clic, scrive quei numeri e li tiene sulla riga. "
    "Lo Stato dice ogni campo: come l'originale, oppure il numero nuovo e quello di prima. "
    "La casella della parte scelta resta attivata sulla riga selezionata. "
    "Se passi all'altra immagine, la casella segue quella riga. "
    "Tornando sulla prima, la sua casella si riattiva. "
    "Spazio, Invio o un clic tengono la parte: lo Stato dice la frase. "
    "Col mouse, trascina un rettangolo sull'immagine: al rilascio i quattro numeri "
    "si riempiono e il taglio è sulla riga. "
    "Invio sul pulsante Tieni questo taglio, o un clic, tiene i quattro numeri "
    "sulla riga selezionata. "
    "L'anteprima è più alta, per vederci meglio. Il file scritto resta a misura intera. "
    "Invio sul pulsante Un quarto a destra, o un clic, gira di un quarto verso destra. "
    "Invio sul pulsante Un quarto a sinistra, o un clic, gira dall'altra parte. "
    "Invio sul pulsante Mezzo giro, o un clic, capovolge. "
    "Il giro toglie il taglio già scelto su quella riga. "
    "Invio sul pulsante Esegui, o un clic, scrive il taglio di quella riga, "
    "oppure il giro se non c'è un taglio. Il file del giro si chiama "
    "nome-giro-un-quarto-a-destra, nome-giro-un-quarto-a-sinistra o "
    "nome-giro-mezzo-giro. Se il nome c'è già, si aggiunge -2. "
    "Con almeno due immagini, Invio sul pulsante Uno sotto l'altro, o un clic, "
    "le mette una sotto l'altra. "
    "Invio sul pulsante Uno accanto all'altro, o un clic, le mette una accanto all'altra. "
    "Si unisce l'immagine intera, il taglio già scelto, oppure il giro già scelto su quella riga. "
    "Il file unito si chiama Unito-uno-sotto-l-altro oppure "
    "Unito-uno-accanto-all-altro. Se il nome c'è già, si aggiunge -2. "
    "I file creati restano nell'elenco Fatti. "
    "Invio o doppio clic su un fatto lo rimette nell'elenco di lavoro. "
    "Dall'elenco, Alt e la lettera del pulsante fa la stessa cosa: "
    "A Aggiungi file, K Aggiungi cartella, S Sposta su, G Sposta giù, M Rimuovi, "
    "I metà sinistra, D metà destra, P metà sopra, O metà sotto, C centro, "
    "B un quarto a destra, J un quarto a sinistra, N mezzo giro, "
    "T tieni questo taglio, E esegui, V uno sotto l'altro, Q uno accanto all'altro. "
    "Il file di partenza resta com'è. Esc chiude."
)
_ALT = {
    "A": "add",
    "K": "folder",
    "S": "up",
    "G": "down",
    "M": "remove",
    "I": "left",
    "D": "right",
    "P": "top",
    "O": "bottom",
    "C": "center",
    "T": "keep",
    "E": "run",
    "V": "down_join",
    "Q": "side_join",
    "B": "turn_right",
    "J": "turn_left",
    "N": "turn_half",
}


def preview_height(screen_h: int) -> int:
    """Altezza minima dell'anteprima. Il file scritto resta a misura intera."""
    try:
        screen_h = int(screen_h)
    except (TypeError, ValueError):
        screen_h = 900
    if screen_h < 1:
        screen_h = 900
    return max(280, min(480, screen_h - 680))


def normalize_turns(turns) -> int:
    try:
        return int(turns) % 4
    except (TypeError, ValueError):
        return 0


def turn_name(turns) -> str:
    name = {1: "un quarto a destra", 2: "mezzo giro", 3: "un quarto a sinistra"}
    return name.get(normalize_turns(turns), "")


def turn_file_slug(turns) -> str:
    slug = {
        1: "un-quarto-a-destra",
        2: "mezzo-giro",
        3: "un-quarto-a-sinistra",
    }
    return slug.get(normalize_turns(turns), "")


def join_file_slug(side_by_side: bool) -> str:
    if side_by_side:
        return "uno-accanto-all-altro"
    return "uno-sotto-l-altro"


def view_size(width: int, height: int, turns) -> tuple:
    if normalize_turns(turns) % 2:
        return int(height), int(width)
    return int(width), int(height)


def rotate_image(image, turns):
    """Gira una copia. L'immagine di partenza non si modifica."""
    steps = normalize_turns(turns)
    if image is None or steps == 0:
        return image
    if steps == 2 and hasattr(image, "Rotate180"):
        return image.Rotate180()
    clockwise = steps == 1
    if steps == 3:
        clockwise = False
    if hasattr(image, "Rotate90"):
        return image.Rotate90(clockwise)
    return image


def _unique_output(folder: str, stem: str, ext: str) -> str:
    ext = ext if ext.startswith(".") else f".{ext}"
    candidate = os.path.join(folder, stem + ext)
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{stem}-{n}{ext}")
        n += 1
    return candidate


def _save_type(ext: str):
    import wx
    return {
        ".jpg": wx.BITMAP_TYPE_JPEG,
        ".jpeg": wx.BITMAP_TYPE_JPEG,
        ".jfif": wx.BITMAP_TYPE_JPEG,
        ".png": wx.BITMAP_TYPE_PNG,
        ".bmp": wx.BITMAP_TYPE_BMP,
        ".gif": wx.BITMAP_TYPE_GIF,
        ".tif": wx.BITMAP_TYPE_TIFF,
        ".tiff": wx.BITMAP_TYPE_TIFF,
    }.get(ext.lower())


def _flat(image):
    """Immagine a colori, senza trasparenza, su bianco."""
    import wx
    if not image.HasAlpha():
        return image
    width, height = image.GetWidth(), image.GetHeight()
    plate = wx.Bitmap(width, height)
    dc = wx.MemoryDC(plate)
    dc.SetBackground(wx.WHITE_BRUSH)
    dc.Clear()
    dc.DrawBitmap(wx.Bitmap(image), 0, 0, True)
    dc.SelectObject(wx.NullBitmap)
    return plate.ConvertToImage()


def load_image(path: str):
    import wx
    ext = os.path.splitext(path)[1].lower()
    if ext not in _EXTS:
        return None, f"{os.path.basename(path)} {MSG_NOT_IMAGE}"
    image = wx.Image(path)
    if not image.IsOk():
        return None, f"{os.path.basename(path)} {MSG_NOT_IMAGE}"
    image = _flat(image)
    return image, ""


class Shot:
    def __init__(self, path: str, width: int, height: int):
        self.path = path
        self.width = int(width)
        self.height = int(height)
        self.crop = None
        self.turns = 0

    def label(self) -> str:
        name = os.path.basename(self.path)
        view_w, view_h = view_size(self.width, self.height, self.turns)
        text = f"{name}, immagine, {view_w} per {view_h}"
        turned = turn_name(self.turns)
        if turned:
            text += f", {turned}"
        if self.crop:
            left, top, width, height = self.crop
            short, _sentence = crop_kind(
                view_w, view_h, left, top, width, height
            )
            text += (
                f", {short}, sinistra {left}, alto {top}, "
                f"larghezza {width}, altezza {height}"
            )
        else:
            text += ", tutta l'immagine"
        return text


def clone_shot(shot: Shot) -> Shot:
    copy = Shot(shot.path, shot.width, shot.height)
    copy.crop = None if shot.crop is None else tuple(shot.crop)
    copy.turns = normalize_turns(getattr(shot, "turns", 0))
    return copy


def _parse_int(raw: str):
    text = (raw or "").strip()
    if not text:
        return None
    if not text.isdigit():
        raise ValueError(MSG_BAD_NUM)
    return int(text)


def check_box(left, top, width, height, image_w: int, image_h: int) -> str:
    if None in (left, top, width, height):
        return MSG_BAD_NUM
    if width < 1 or height < 1:
        return MSG_BAD_NUM
    if left < 0 or top < 0 or left + width > image_w or top + height > image_h:
        return f"Il taglio esce dall'immagine, larga {image_w}, alta {image_h}."
    return ""


def apply_box(shot: Shot, left, top, width, height) -> str:
    view_w, view_h = view_size(shot.width, shot.height, shot.turns)
    err = check_box(left, top, width, height, view_w, view_h)
    if err:
        return err
    shot.crop = (int(left), int(top), int(width), int(height))
    return shot.label()


def preset_numbers(image_w: int, image_h: int, name: str):
    half_w = max(1, image_w // 2)
    half_h = max(1, image_h // 2)
    if name == "left":
        return 0, 0, half_w, image_h
    if name == "right":
        return half_w, 0, image_w - half_w, image_h
    if name == "top":
        return 0, 0, image_w, half_h
    if name == "bottom":
        return 0, half_h, image_w, image_h - half_h
    left = max(0, (image_w - half_w) // 2)
    top = max(0, (image_h - half_h) // 2)
    return left, top, half_w, half_h


def preset_box(shot: Shot, name: str):
    width, height = view_size(shot.width, shot.height, shot.turns)
    return preset_numbers(width, height, name)


_CROP_KIND = {
    "left": ("metà sinistra", "Tieni la fascia di sinistra."),
    "right": ("metà destra", "Tieni la fascia di destra."),
    "top": ("metà sopra", "Tieni la fascia di sopra."),
    "bottom": ("metà sotto", "Tieni la fascia di sotto."),
    "center": ("centro", "Tieni il centro."),
}
_ACTION_TITLE = {
    "left": "Metà sinistra",
    "right": "Metà destra",
    "top": "Metà sopra",
    "bottom": "Metà sotto",
    "center": "Centro",
}


def crop_kind(image_w: int, image_h: int, left, top, width, height):
    """Nome breve per l'elenco, e la frase di cosa resta dell'immagine."""
    box = (int(left), int(top), int(width), int(height))
    if box == (0, 0, int(image_w), int(image_h)):
        return "", "È l'immagine intera. Nessun taglio."
    for name, (short, sentence) in _CROP_KIND.items():
        if box == preset_numbers(image_w, image_h, name):
            return short, sentence
    return "rettangolo", "Tieni questo rettangolo."


def field_clause(label: str, now, original) -> str:
    now = int(now)
    original = int(original)
    if now == original:
        return f"{label} {now}, come l'originale."
    return f"{label} {now}, era {original}."


def compare_phrase(title, left, top, width, height, image_w, image_h) -> str:
    _short, sentence = crop_kind(image_w, image_h, left, top, width, height)
    fields = " ".join((
        field_clause("Sinistra", left, 0),
        field_clause("Alto", top, 0),
        field_clause("Larghezza", width, image_w),
        field_clause("Altezza", height, image_h),
    ))
    return (
        f"{title}. Rispetto all'immagine intera, {image_w} per {image_h}. "
        f"{fields} {sentence}"
    )


def render_shot(shot: Shot):
    image, err = load_image(shot.path)
    if image is None:
        return None, err or MSG_FAIL
    if normalize_turns(shot.turns):
        image = rotate_image(image, shot.turns)
    if shot.crop:
        left, top, width, height = shot.crop
        err = check_box(left, top, width, height, image.GetWidth(), image.GetHeight())
        if err:
            return None, err
        import wx
        image = image.GetSubImage(wx.Rect(left, top, width, height))
    return image, ""


def join_images(images, side_by_side: bool):
    import wx
    if side_by_side:
        width = sum(image.GetWidth() for image in images)
        height = max(image.GetHeight() for image in images)
    else:
        width = max(image.GetWidth() for image in images)
        height = sum(image.GetHeight() for image in images)
    out = wx.Image(width, height)
    out.SetData(b"\xff" * (width * height * 3))
    x = y = 0
    for image in images:
        out.Paste(image, x, y)
        if side_by_side:
            x += image.GetWidth()
        else:
            y += image.GetHeight()
    return out


def _output_ext(shots: list, reencode_png: bool) -> str:
    if reencode_png:
        return ".png"
    exts = [os.path.splitext(shot.path)[1].lower() for shot in shots]
    if len(set(exts)) == 1 and _save_type(exts[0]):
        return exts[0]
    return ".png"


def _output_for(shots: list, several: bool, side_by_side: bool = False) -> str:
    first = shots[0]
    folder = os.path.dirname(os.path.abspath(first.path)) or os.getcwd()
    if several:
        stem = "Unito-" + join_file_slug(side_by_side)
    else:
        base = os.path.splitext(os.path.basename(first.path))[0]
        turned = normalize_turns(getattr(first, "turns", 0))
        if first.crop or not turned:
            stem = base + "-taglio"
        else:
            stem = base + "-giro-" + turn_file_slug(turned)
    ext = _output_ext(shots, False)
    return _unique_output(folder, stem, ext)


def _save(image, dest: str) -> bool:
    ext = os.path.splitext(dest)[1].lower()
    kind = _save_type(ext)
    if kind is None:
        dest_png = os.path.splitext(dest)[0] + ".png"
        import wx
        return image.SaveFile(dest_png, wx.BITMAP_TYPE_PNG)
    ok = image.SaveFile(dest, kind)
    if ok and os.path.isfile(dest) and os.path.getsize(dest) > 0:
        return True
    import wx
    dest_png = os.path.splitext(dest)[0] + ".png"
    return image.SaveFile(dest_png, wx.BITMAP_TYPE_PNG)


def build(shots: list, side_by_side: bool = False) -> tuple:
    if len(shots) == 1:
        image, err = render_shot(shots[0])
        if image is None:
            return False, err or MSG_FAIL, ""
        dest = _output_for(shots, False)
        if not _save(image, dest):
            return False, MSG_FAIL, ""
        if not os.path.isfile(dest):
            dest = os.path.splitext(dest)[0] + ".png"
        width, height = image.GetWidth(), image.GetHeight()
        return True, (
            f"Creato {os.path.basename(dest)}, {width} per {height}, "
            "nella stessa cartella."
        ), dest
    images = []
    for shot in shots:
        image, err = render_shot(shot)
        if image is None:
            return False, err or MSG_FAIL, ""
        images.append(image)
    out = join_images(images, side_by_side)
    dest = _output_for(shots, True, side_by_side)
    if not _save(out, dest):
        return False, MSG_FAIL, ""
    if not os.path.isfile(dest):
        dest = os.path.splitext(dest)[0] + ".png"
    return True, (
        f"Creato {os.path.basename(dest)}, {out.GetWidth()} per {out.GetHeight()}, "
        "nella stessa cartella."
    ), dest


def crop_spoken(shot: Shot) -> str:
    """La parte scelta, poi i quattro numeri con il loro nome."""
    view_w, view_h = view_size(shot.width, shot.height, shot.turns)
    turned = turn_name(shot.turns)
    if not shot.crop:
        if turned:
            return f"{turned}, tutta l'immagine, {view_w} per {view_h}"
        return "tutta l'immagine"
    left, top, width, height = shot.crop
    short, _sentence = crop_kind(view_w, view_h, left, top, width, height)
    numbers = (
        f"sinistra {left}, alto {top}, larghezza {width}, altezza {height}"
    )
    piece = f"{short}, {numbers}" if short else numbers
    if turned:
        return f"{turned}, {piece}"
    return piece


def history_label(shots: list, out_path: str, size: str, side_by_side: bool) -> str:
    name = os.path.basename(out_path)
    if len(shots) == 1:
        return f"{name}, {shots[0].label().split(', ', 1)[-1]}, {size}"
    how = "una accanto all'altra" if side_by_side else "una sotto l'altra"
    bits = []
    for shot in shots:
        bits.append(f"{os.path.basename(shot.path)}, {crop_spoken(shot)}")
    return (
        f"{name}, unite {len(shots)} immagini {how}: {'; '.join(bits)}. "
        f"Risultato {size}."
    )


def open_dialog(parent, speaker, paths=None):
    import wx
    dialog = ImageDialog(parent, speaker, paths or [])
    dialog.ShowModal()
    dialog.close_work()
    dialog.Destroy()


class ImageDialog:
    """La classe vera è sotto: wx va importato a finestra aperta."""


def _install_dialog():
    import wx

    class CropPanel(wx.Panel):
        def __init__(self, parent, on_rect):
            super().__init__(parent)
            self._on_rect = on_rect
            self._image = None
            self._drag = None
            self._rect = None
            self.SetBackgroundColour(wx.Colour(255, 255, 255))
            self.SetMinSize((680, 220))
            self.Bind(wx.EVT_PAINT, self._paint)
            self.Bind(wx.EVT_LEFT_DOWN, self._down)
            self.Bind(wx.EVT_LEFT_UP, self._up)
            self.Bind(wx.EVT_MOTION, self._move)
            self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)

        def set_image(self, image, crop):
            self._image = image
            self._rect = None if not crop else wx.Rect(*crop)
            self._drag = None
            self.Refresh()

        def _placed(self):
            if self._image is None:
                return None
            width, height = self.GetClientSize()
            iw, ih = self._image.GetWidth(), self._image.GetHeight()
            if iw < 1 or ih < 1 or width < 2 or height < 2:
                return None
            scale = min(width / iw, height / ih)
            dw, dh = max(1, int(iw * scale)), max(1, int(ih * scale))
            ox = (width - dw) // 2
            oy = (height - dh) // 2
            return scale, ox, oy, dw, dh

        def _to_image(self, x, y):
            placed = self._placed()
            if not placed or self._image is None:
                return None
            scale, ox, oy, dw, dh = placed
            ix = int((x - ox) / scale)
            iy = int((y - oy) / scale)
            iw, ih = self._image.GetWidth(), self._image.GetHeight()
            ix = max(0, min(iw - 1, ix))
            iy = max(0, min(ih - 1, iy))
            return ix, iy

        def _paint(self, _event):
            dc = wx.PaintDC(self)
            dc.SetBackground(wx.WHITE_BRUSH)
            dc.Clear()
            placed = self._placed()
            if not placed:
                return
            _scale, ox, oy, dw, dh = placed
            shown = self._image.Scale(dw, dh, wx.IMAGE_QUALITY_HIGH)
            dc.DrawBitmap(wx.Bitmap(shown), ox, oy, True)
            rect = self._rect
            if rect and rect.width > 0 and rect.height > 0:
                scale = placed[0]
                rx = ox + int(rect.x * scale)
                ry = oy + int(rect.y * scale)
                rw = max(1, int(rect.width * scale))
                rh = max(1, int(rect.height * scale))
                dc.SetPen(wx.Pen(wx.Colour(0, 80, 180), 2))
                dc.SetBrush(wx.TRANSPARENT_BRUSH)
                dc.DrawRectangle(rx, ry, rw, rh)

        def _down(self, event):
            point = self._to_image(event.GetX(), event.GetY())
            if point is None:
                return
            self._drag = point
            self._rect = wx.Rect(point[0], point[1], 1, 1)
            self.CaptureMouse()
            self.Refresh()

        def _move(self, event):
            if self._drag is None or not event.LeftIsDown():
                return
            point = self._to_image(event.GetX(), event.GetY())
            if point is None:
                return
            x0, y0 = self._drag
            x1, y1 = point
            left, right = sorted((x0, x1))
            top, bottom = sorted((y0, y1))
            self._rect = wx.Rect(left, top, max(1, right - left), max(1, bottom - top))
            self.Refresh()

        def _up(self, event):
            if self.HasCapture():
                self.ReleaseMouse()
            rect = self._rect
            self._drag = None
            if rect and rect.width > 2 and rect.height > 2:
                self._on_rect(rect.x, rect.y, rect.width, rect.height)

    class ImageDialog(wx.Dialog):
        def __init__(self, parent, speaker, paths):
            super().__init__(
                parent,
                title="Taglia e unisci immagini",
                style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            )
            self._speaker = speaker or (lambda _text: None)
            self._rows: list[Shot] = []
            self._done: list[tuple[str, str]] = []
            self._open = True
            self._initial = list(paths or [])
            self._view_image = None

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
                        "Immagini, nell'ordine. "
                        "Invio o doppio clic dice la riga. "
                        "Un clic solo seleziona la riga."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )
            self.lst = wx.ListBox(self, style=wx.LB_SINGLE)
            self.lst.SetMinSize((760, 120))
            vbox.Add(self.lst, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.lst.Bind(wx.EVT_LISTBOX, self._on_select)
            self.lst.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._say_row())

            vbox.Add(
                wx.StaticText(
                    self,
                    label=(
                        "Anteprima, più alta per vederci meglio. "
                        "Il file scritto resta a misura intera."
                    ),
                ),
                0, wx.LEFT | wx.RIGHT | wx.TOP, 8,
            )
            self.view = CropPanel(self, self._on_mouse_rect)
            try:
                screen_h = wx.GetDisplaySize().height
            except Exception:
                screen_h = 900
            self.view.SetMinSize((680, preview_height(screen_h)))
            vbox.Add(self.view, 1, wx.EXPAND | wx.ALL, 8)

            nums = wx.FlexGridSizer(2, 4, 6, 8)
            nums.AddGrowableCol(1, 1)
            nums.AddGrowableCol(3, 1)
            self.txt_left = wx.TextCtrl(self)
            self.txt_top = wx.TextCtrl(self)
            self.txt_width = wx.TextCtrl(self)
            self.txt_height = wx.TextCtrl(self)
            for label, ctrl in (
                ("Sinistra", self.txt_left),
                ("Alto", self.txt_top),
                ("Larghezza", self.txt_width),
                ("Altezza", self.txt_height),
            ):
                nums.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
                nums.Add(ctrl, 1, wx.EXPAND)
            vbox.Add(nums, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

            row1 = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_add = wx.Button(self, label="&Aggiungi file…")
            self.btn_folder = wx.Button(self, label="Aggiungi cartella (&K)")
            self.btn_up = wx.Button(self, label="Sposta &su")
            self.btn_down = wx.Button(self, label="Sposta &giù")
            self.btn_remove = wx.Button(self, label="Ri&muovi")
            for btn in (self.btn_add, self.btn_folder, self.btn_up, self.btn_down, self.btn_remove):
                row1.Add(btn, 0, wx.RIGHT, 6)
            vbox.Add(row1, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

            row2 = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_left = wx.ToggleButton(self, label="Metà s&inistra")
            self.btn_right = wx.ToggleButton(self, label="Metà &destra")
            self.btn_top = wx.ToggleButton(self, label="Metà so&pra")
            self.btn_bottom = wx.ToggleButton(self, label="Metà sott&o")
            self.btn_center = wx.ToggleButton(self, label="&Centro")
            for btn in (
                self.btn_left, self.btn_right, self.btn_top,
                self.btn_bottom, self.btn_center,
            ):
                row2.Add(btn, 0, wx.RIGHT, 6)
            vbox.Add(row2, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

            row_turn = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_turn_right = wx.Button(self, label="Un quarto a destra (&B)")
            self.btn_turn_left = wx.Button(self, label="Un quarto a sinistra (&J)")
            self.btn_turn_half = wx.Button(self, label="Mezzo giro (&N)")
            for btn in (self.btn_turn_right, self.btn_turn_left, self.btn_turn_half):
                row_turn.Add(btn, 0, wx.RIGHT, 6)
            vbox.Add(row_turn, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

            row3 = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_keep = wx.Button(self, label="&Tieni questo taglio")
            self.btn_run = wx.Button(self, label="&Esegui")
            self.btn_under = wx.Button(self, label="Uno sotto l'altro (&V)")
            self.btn_side = wx.Button(self, label="Uno accanto all'altro (&Q)")
            self.btn_close = wx.Button(self, wx.ID_CANCEL, "Chiudi")
            for btn in (self.btn_keep, self.btn_run, self.btn_under, self.btn_side, self.btn_close):
                row3.Add(btn, 0, wx.RIGHT, 6)
            vbox.Add(row3, 0, wx.ALL, 8)

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
            self.lst_done.SetMinSize((760, 80))
            vbox.Add(self.lst_done, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.lst_done.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: self._on_use_done())

            vbox.Add(wx.StaticText(self, label="Stato"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self.txt_status = wx.TextCtrl(
                self, value=MSG_EMPTY, style=wx.TE_READONLY | wx.TE_MULTILINE,
            )
            self.txt_status.SetMinSize((760, 72))
            vbox.Add(self.txt_status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self._status_bar = wx.StatusBar(self)
            self._status_bar.SetMinSize((760, 28))
            self._status_bar.SetStatusText(MSG_EMPTY)
            vbox.Add(self._status_bar, 0, wx.EXPAND | wx.ALL, 4)

            self.btn_add.Bind(wx.EVT_BUTTON, self._on_add)
            self.btn_folder.Bind(wx.EVT_BUTTON, self._on_add_folder)
            self.btn_up.Bind(wx.EVT_BUTTON, lambda e: self._move(-1))
            self.btn_down.Bind(wx.EVT_BUTTON, lambda e: self._move(1))
            self.btn_remove.Bind(wx.EVT_BUTTON, self._on_remove)
            self.btn_left.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self._preset("left"))
            self.btn_right.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self._preset("right"))
            self.btn_top.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self._preset("top"))
            self.btn_bottom.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self._preset("bottom"))
            self.btn_center.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self._preset("center"))
            self.btn_turn_right.Bind(wx.EVT_BUTTON, lambda e: self._on_turn(1, "Un quarto a destra"))
            self.btn_turn_left.Bind(wx.EVT_BUTTON, lambda e: self._on_turn(-1, "Un quarto a sinistra"))
            self.btn_turn_half.Bind(wx.EVT_BUTTON, lambda e: self._on_turn(2, "Mezzo giro"))
            self.btn_keep.Bind(wx.EVT_BUTTON, self._on_keep)
            self.btn_run.Bind(wx.EVT_BUTTON, self._on_run)
            self.btn_under.Bind(wx.EVT_BUTTON, lambda e: self._on_join(False))
            self.btn_side.Bind(wx.EVT_BUTTON, lambda e: self._on_join(True))
            self.Bind(wx.EVT_CHAR_HOOK, self._on_char)
            self.Bind(wx.EVT_CLOSE, self._on_close)
            self.SetEscapeId(wx.ID_CANCEL)
            self.SetSizer(vbox)
            try:
                area = wx.Display(wx.Display.GetFromWindow(parent) if parent else 0).GetClientArea()
                dialog_h = min(area.height - 24, preview_height(area.height) + 760)
                dialog_w = min(area.width - 40, 900)
            except Exception:
                dialog_h, dialog_w = 980, 860
            self.SetInitialSize((max(820, dialog_w), max(860, dialog_h)))
            self.CentreOnParent()
            self._refresh(0)
            self._refresh_done()
            self.lst.SetFocus()
            if self._initial:
                wx.CallAfter(self._load_initial)

        def close_work(self):
            self._open = False

        def _on_close(self, event):
            self.close_work()
            event.Skip()

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
            if not self._rows:
                return -1
            index = self.lst.GetSelection()
            if index < 0 or index >= len(self._rows):
                return -1
            return index

        def _refresh(self, select: int):
            self.lst.Clear()
            if not self._rows:
                self.lst.Append(MSG_EMPTY)
                self.lst.SetSelection(0)
                self._show_row(None)
                return
            for shot in self._rows:
                self.lst.Append(shot.label())
            select = max(0, min(select, len(self._rows) - 1))
            self.lst.SetSelection(select)
            self._show_row(self._rows[select])

        def _show_row(self, shot):
            if shot is None:
                self._view_image = None
                self.view.set_image(None, None)
                for ctrl in (self.txt_left, self.txt_top, self.txt_width, self.txt_height):
                    ctrl.ChangeValue("")
                self._mark_parts(None)
                return
            image, _err = load_image(shot.path)
            if image is not None and normalize_turns(shot.turns):
                image = rotate_image(image, shot.turns)
            self._view_image = image
            self.view.set_image(image, shot.crop)
            view_w, view_h = view_size(shot.width, shot.height, shot.turns)
            if shot.crop:
                left, top, width, height = shot.crop
            else:
                left, top, width, height = 0, 0, view_w, view_h
            self.txt_left.ChangeValue(str(left))
            self.txt_top.ChangeValue(str(top))
            self.txt_width.ChangeValue(str(width))
            self.txt_height.ChangeValue(str(height))
            self._mark_parts(shot)

        def _mark_parts(self, shot):
            kind = ""
            if shot is not None and shot.crop:
                left, top, width, height = shot.crop
                view_w, view_h = view_size(shot.width, shot.height, shot.turns)
                kind, _sentence = crop_kind(view_w, view_h, left, top, width, height)
            for btn, name in (
                (self.btn_left, "metà sinistra"),
                (self.btn_right, "metà destra"),
                (self.btn_top, "metà sopra"),
                (self.btn_bottom, "metà sotto"),
                (self.btn_center, "centro"),
            ):
                btn.SetValue(kind == name)

        def _on_select(self, _event=None):
            index = self._selected()
            if index < 0:
                return
            self._show_row(self._rows[index])

        def _say_row(self):
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            shot = self._rows[index]
            view_w, view_h = view_size(shot.width, shot.height, shot.turns)
            if shot.crop:
                left, top, width, height = shot.crop
            else:
                left, top, width, height = 0, 0, view_w, view_h
            phrase = compare_phrase(
                "Questa riga", left, top, width, height, view_w, view_h
            )
            turned = turn_name(shot.turns)
            if turned:
                phrase = f"{phrase} Giro: {turned}."
            self._say(phrase)

        def _refresh_done(self):
            self.lst_done.Clear()
            if not self._done:
                self.lst_done.Append(MSG_NO_DONE)
                self.lst_done.SetSelection(0)
                return
            for label, _path in self._done:
                self.lst_done.Append(label)
            self.lst_done.SetSelection(len(self._done) - 1)

        def _done_label(self, path: str) -> str:
            key = os.path.normcase(os.path.abspath(path))
            for label, done in self._done:
                try:
                    if os.path.normcase(os.path.abspath(done)) == key:
                        return label
                except Exception:
                    continue
            return ""

        def _load_initial(self):
            paths = [p for p in self._initial if p]
            self._initial = []
            if paths:
                self._ingest(paths)

        def _on_add(self, _event=None):
            with wx.FileDialog(
                self,
                "Scegli immagini",
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
                self._say(
                    "Nessuna immagine in questa cartella. "
                    "Le cartelle dentro non si aprono."
                )
                return
            self._ingest(paths)

        def _ingest(self, paths):
            added = []
            skipped = []
            for path in paths:
                image, err = load_image(path)
                if image is None:
                    skipped.append(err or os.path.basename(path))
                else:
                    added.append(Shot(path, image.GetWidth(), image.GetHeight()))
            if added:
                self._rows.extend(added)
                self._refresh(len(self._rows) - len(added))
            if len(added) == 1 and not skipped:
                known = self._done_label(added[0].path)
                if known:
                    self._say(f"Aggiunto {known}")
                else:
                    self._say(
                        f"Aggiunto {added[0].label()}. "
                        "Nei campi, l'immagine intera: "
                        f"sinistra 0, alto 0, larghezza {added[0].width}, "
                        f"altezza {added[0].height}."
                    )
                return
            if added and skipped:
                self._say(
                    f"Aggiunte {len(added)} su {len(added) + len(skipped)}. "
                    f"Non entrate: {', '.join(skipped)}."
                )
                return
            if added:
                self._say(f"Aggiunte {len(added)} immagini.")
                return
            if skipped:
                self._say("Nessuna immagine. Non entrate: " + ", ".join(skipped) + ".")
                return
            self._say(MSG_EMPTY)

        def _move(self, delta: int):
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            nxt = index + delta
            if nxt < 0 or nxt >= len(self._rows):
                self._say(self._rows[index].label())
                return
            self._rows[index], self._rows[nxt] = self._rows[nxt], self._rows[index]
            self._refresh(nxt)
            self._say(self._rows[nxt].label())

        def _on_remove(self, _event=None):
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            name = os.path.basename(self._rows[index].path)
            del self._rows[index]
            self._refresh(min(index, len(self._rows) - 1))
            if self._rows:
                self._say(f"Rimosso {name}.")
            else:
                self._say(f"Rimosso {name}. {MSG_EMPTY}")

        def _numbers(self):
            try:
                return (
                    _parse_int(self.txt_left.GetValue()),
                    _parse_int(self.txt_top.GetValue()),
                    _parse_int(self.txt_width.GetValue()),
                    _parse_int(self.txt_height.GetValue()),
                    "",
                )
            except ValueError as exc:
                return None, None, None, None, str(exc)

        def _keep_box(self, left, top, width, height, title: str):
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            shot = self._rows[index]
            view_w, view_h = view_size(shot.width, shot.height, shot.turns)
            err = check_box(left, top, width, height, view_w, view_h)
            if err:
                self._say(err)
                return
            box = (int(left), int(top), int(width), int(height))
            if box == (0, 0, view_w, view_h):
                shot.crop = None
            else:
                apply_box(shot, left, top, width, height)
            phrase = compare_phrase(title, left, top, width, height, view_w, view_h)
            turned = turn_name(shot.turns)
            if turned:
                phrase = f"{phrase} Giro: {turned}."
            self._refresh(index)
            self._say(phrase)

        def _on_keep(self, _event=None):
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            left, top, width, height, err = self._numbers()
            if err:
                self._say(err)
                return
            self._keep_box(left, top, width, height, "Tieni questo taglio")

        def _preset(self, name: str):
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            left, top, width, height = preset_box(self._rows[index], name)
            self._keep_box(left, top, width, height, _ACTION_TITLE[name])

        def _on_mouse_rect(self, left, top, width, height):
            self._keep_box(left, top, width, height, "Rettangolo col mouse")

        def _on_run(self, _event=None):
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            shot = self._rows[index]
            if shot.crop is None and not normalize_turns(shot.turns):
                if len(self._rows) >= 2:
                    self._say(
                        "Esegui scrive il taglio di una riga sola. "
                        "Per unire le immagini intere, Invio sul pulsante "
                        "Uno sotto l'altro o Uno accanto all'altro, o un clic."
                    )
                else:
                    self._say(MSG_NEED_CROP)
                return
            self._finish([shot], False)

        def _on_turn(self, delta: int, title: str):
            index = self._selected()
            if index < 0:
                self._say(MSG_EMPTY if not self._rows else MSG_SELECT)
                return
            shot = self._rows[index]
            shot.turns = normalize_turns(shot.turns + delta)
            shot.crop = None
            self._refresh(index)
            view_w, view_h = view_size(shot.width, shot.height, shot.turns)
            turned = turn_name(shot.turns)
            if turned:
                state = f"Ora è {turned}, larga {view_w}, alta {view_h}."
                follow = (
                    "Invio sul pulsante Esegui, o un clic, scrive il file nuovo. "
                    "Il file di partenza resta com'è."
                )
            else:
                state = f"È di nuovo dritta come il file, larga {view_w}, alta {view_h}."
                follow = "Il file di partenza resta com'è."
            self._say(f"{title}. {state} {follow}")

        def _on_join(self, side_by_side: bool):
            if len(self._rows) < 2:
                self._say(MSG_NEED_TWO)
                return
            self._finish(list(self._rows), side_by_side)

        def _finish(self, shots, side_by_side: bool):
            rows = [clone_shot(shot) for shot in shots]
            ok, phrase, dest = build(rows, side_by_side)
            if not ok or not dest or not os.path.isfile(dest):
                self._say(phrase or MSG_FAIL)
                return
            image, _err = load_image(dest)
            if image is None:
                size = "dimensione non letta"
            else:
                size = f"{image.GetWidth()} per {image.GetHeight()}"
            label = history_label(rows, dest, size, side_by_side and len(rows) > 1)
            self._done.append((label, dest))
            self._refresh_done()
            text = phrase if phrase.endswith(".") else phrase + "."
            self._say(f"{text} In Fatti: {label}")

        def _on_use_done(self):
            if not self._done:
                self._say(MSG_NO_DONE)
                return
            index = self.lst_done.GetSelection()
            if index < 0 or index >= len(self._done):
                self._say(MSG_SELECT)
                return
            _label, path = self._done[index]
            if not os.path.isfile(path):
                self._say(f"{os.path.basename(path)} non c'è più.")
                return
            self._ingest([path])

        def _on_char(self, event):
            key = event.GetKeyCode()
            if (
                event.AltDown()
                and not event.ControlDown()
                and not event.ShiftDown()
                and key not in (wx.WXK_F4, wx.WXK_TAB)
            ):
                letter = ""
                if ord("A") <= key <= ord("Z") or ord("a") <= key <= ord("z"):
                    letter = chr(key).upper()
                name = _ALT.get(letter)
                if name:
                    self._alt_do(name)
                    return
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                focused = self.FindFocus()
                if focused is self.lst:
                    self._say_row()
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
            elif name == "up":
                self._move(-1)
            elif name == "down":
                self._move(1)
            elif name == "remove":
                self._on_remove()
            elif name == "left":
                self._preset("left")
            elif name == "right":
                self._preset("right")
            elif name == "top":
                self._preset("top")
            elif name == "bottom":
                self._preset("bottom")
            elif name == "center":
                self._preset("center")
            elif name == "turn_right":
                self._on_turn(1, "Un quarto a destra")
            elif name == "turn_left":
                self._on_turn(-1, "Un quarto a sinistra")
            elif name == "turn_half":
                self._on_turn(2, "Mezzo giro")
            elif name == "keep":
                self._on_keep()
            elif name == "run":
                self._on_run()
            elif name == "down_join":
                self._on_join(False)
            elif name == "side_join":
                self._on_join(True)

    globals()["ImageDialog"] = ImageDialog


_install_dialog()
