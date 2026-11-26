# -*- coding: utf-8 -*-
"""Mano sulla ripresa (2.0.11).

Luce, contrasto, colore, nitidezza, volto, distanza, stabilità, audio.
Sul PC, senza chiave. La fotocamera usa ffmpeg e, se Windows li consegna,
i parametri del driver (fuoco, esposizione, zoom, luminosità, colore).
"""
from __future__ import annotations

import logging
import os
import shutil
import struct
import subprocess
import threading
import time
import uuid
import ctypes
from ctypes import (
    POINTER,
    WINFUNCTYPE,
    byref,
    c_long,
    c_ubyte,
    c_ulong,
    c_ulonglong,
    c_ushort,
    c_void_p,
    c_wchar_p,
)

log = logging.getLogger("rtad.ripresa")

MSG_NEED_FFMPEG = "Per la fotocamera serve ffmpeg."
MSG_NO_CAMERA = "Nessuna fotocamera. Collega la webcam e riapri."
MSG_CAMERA_BUSY = "La fotocamera è già in uso."
MSG_CAMERA_LOST = "La fotocamera si è staccata."
MSG_NOT_MEDIA = (
    "Questo file è solo audio. La mano sulla ripresa vale per una foto o un video."
)
MSG_READ_FAIL = "Non riesco a leggere questa immagine."
MSG_VIDEO_FAIL = "Non riesco a leggere questo video."
MSG_READING_VIDEO = "Leggo il video."
MSG_FIXED = "Questo valore è fisso."
MSG_AT_MAX = "Sei al massimo."
MSG_AT_MIN = "Sei al minimo."
MSG_RECORDING = "Registro. La mano non parla da sola. Alt+O dice dov'è il volto."
MSG_PHOTO_FAIL = "Non riesco a scattare."
MSG_RECORD_FAIL = "Non riesco a registrare."

_CREATE_NO_WINDOW = 0x08000000
_SHARP_BLUR = 45.0
_SHARP_SOFT = 220.0
_PREVIEW_W = 320
_PREVIEW_H = 240

_VIDEO_EXTS = {
    ".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv",
    ".mts", ".m2ts", ".mpg", ".mpeg", ".3gp",
}
_AUDIO_EXTS = {
    ".mp3", ".m4a", ".m4b", ".aac", ".flac", ".ogg", ".opus", ".wav",
    ".wma", ".aif", ".aiff", ".mka",
}
_IMAGE_EXTS = {
    ".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".gif", ".tif", ".tiff",
    ".webp", ".ico",
}

_WHERE_PHRASE = {
    "centro": "al centro",
    "sinistra": "a sinistra",
    "destra": "a destra",
    "poco a sinistra": "un po' a sinistra",
    "poco a destra": "un po' a destra",
    "sopra": "in alto",
    "sotto": "in basso",
    "poco sopra": "un po' in alto",
    "poco sotto": "un po' in basso",
    "alto a sinistra": "in alto a sinistra",
    "alto a destra": "in alto a destra",
    "basso a sinistra": "in basso a sinistra",
    "basso a destra": "in basso a destra",
    "poco alto a sinistra": "un po' in alto a sinistra",
    "poco alto a destra": "un po' in alto a destra",
    "poco basso a sinistra": "un po' in basso a sinistra",
    "poco basso a destra": "un po' in basso a destra",
    "sinistra e poco alto": "a sinistra e un po' in alto",
    "destra e poco alto": "a destra e un po' in alto",
    "sinistra e poco basso": "a sinistra e un po' in basso",
    "destra e poco basso": "a destra e un po' in basso",
    "alto e poco sinistra": "in alto e un po' a sinistra",
    "alto e poco destra": "in alto e un po' a destra",
    "basso e poco sinistra": "in basso e un po' a sinistra",
    "basso e poco destra": "in basso e un po' a destra",
}
_H_CUTS = (0.30, 0.47, 0.53, 0.60)
_V_CUTS = (0.28, 0.40, 0.66, 0.80)
# Fronte del volto: alzare il mento la porta in alto, abbassare la testa la porta in basso.
# Il centro del riquadro resta fermo anche con la testa inclinata.
_CROWN_CUTS = (0.24, 0.42, 0.58, 0.70)
_H_NAMES = ("sinistra", "poco sinistra", "centro", "poco destra", "destra")
_V_NAMES = ("alto", "poco alto", "centro", "poco basso", "basso")
_PLACE_ORDER = (
    "centro",
    "sinistra",
    "destra",
    "sopra",
    "sotto",
    "alto a sinistra",
    "alto a destra",
    "basso a sinistra",
    "basso a destra",
)

# (nome, articolo, interfaccia amp|cam, proprietà, unità, sempre in elenco)
_CORE_CONTROLS = (
    ("Luminosità", "la luminosità", "amp", 0, "", True),
    ("Contrasto", "il contrasto", "amp", 1, "", True),
    ("Saturazione", "la saturazione", "amp", 3, "", True),
    ("Nitidezza della fotocamera", "la nitidezza della fotocamera", "amp", 4, "", True),
    ("Gamma", "la gamma", "amp", 5, "", False),
    ("Bilanciamento del bianco", "il bilanciamento del bianco", "amp", 7, " kelvin", True),
    ("Controluce della fotocamera", "il controluce della fotocamera", "amp", 8, "", False),
    ("Guadagno", "il guadagno", "amp", 9, "", False),
    ("Panoramica", "la panoramica", "cam", 0, "", False),
    ("Inclinazione", "l'inclinazione", "cam", 1, "", False),
    ("Zoom", "lo zoom", "cam", 3, "", True),
    ("Esposizione", "l'esposizione", "cam", 4, "", True),
    ("Fuoco", "il fuoco", "cam", 6, "", True),
)
_AUTO_FLAG = 0x0001
_MANUAL_FLAG = 0x0002


def ffmpeg_exe() -> str:
    try:
        import rtad_media

        found = rtad_media._ffmpeg_exe()
        if found:
            return found
    except Exception:
        pass
    found = shutil.which("ffmpeg") or ""
    if found and os.path.isfile(found):
        return found
    fixed = r"C:\ffmpeg\bin\ffmpeg.exe"
    if os.path.isfile(fixed):
        return fixed
    return ""


def ffprobe_exe() -> str:
    ff = ffmpeg_exe()
    if ff:
        probe = os.path.join(os.path.dirname(ff), "ffprobe.exe")
        if os.path.isfile(probe):
            return probe
        probe = os.path.join(os.path.dirname(ff), "ffprobe")
        if os.path.isfile(probe):
            return probe
    found = shutil.which("ffprobe") or ""
    return found if found and os.path.isfile(found) else ""


def _run(cmd, timeout=40, input_bytes=None):
    try:
        return subprocess.run(
            cmd,
            input=input_bytes,
            capture_output=True,
            timeout=timeout,
            creationflags=_CREATE_NO_WINDOW,
        )
    except Exception as exc:
        log.exception("ffmpeg")
        proc = subprocess.CompletedProcess(cmd, 1, b"", str(exc).encode("utf-8", "replace"))
        return proc


def write_bmp(path: str, rgb: bytes, width: int, height: int) -> None:
    data = _bmp_bytes(rgb, width, height)
    with open(path, "wb") as handle:
        handle.write(data)


def _bmp_bytes(rgb: bytes, width: int, height: int) -> bytes:
    row_stride = (width * 3 + 3) & ~3
    pixels = bytearray()
    for y in range(height - 1, -1, -1):
        row = bytearray(row_stride)
        src = y * width * 3
        for x in range(width):
            i = src + x * 3
            row[x * 3] = rgb[i + 2]
            row[x * 3 + 1] = rgb[i + 1]
            row[x * 3 + 2] = rgb[i]
        pixels.extend(row)
    header = struct.pack("<2sIHHI", b"BM", 54 + len(pixels), 0, 0, 54)
    info = struct.pack(
        "<IiiHHIIiiII",
        40, width, height, 1, 24, 0, len(pixels), 2835, 2835, 0, 0,
    )
    return header + info + bytes(pixels)


def parse_bmp(data: bytes):
    if len(data) < 54 or data[:2] != b"BM":
        return None
    offset = struct.unpack_from("<I", data, 10)[0]
    width = struct.unpack_from("<i", data, 18)[0]
    height_raw = struct.unpack_from("<i", data, 22)[0]
    planes, bpp = struct.unpack_from("<HH", data, 26)
    if planes != 1 or bpp not in (24, 32) or width <= 0 or height_raw == 0:
        return None
    top_down = height_raw < 0
    height = abs(height_raw)
    stride = ((width * (bpp // 8) + 3) & ~3)
    rgb = bytearray(width * height * 3)
    px = bpp // 8
    for row in range(height):
        src_row = row if top_down else height - 1 - row
        start = offset + src_row * stride
        if start + width * px > len(data):
            return None
        dst = row * width * 3
        for x in range(width):
            i = start + x * px
            rgb[dst + x * 3] = data[i + 2]
            rgb[dst + x * 3 + 1] = data[i + 1]
            rgb[dst + x * 3 + 2] = data[i]
    return bytes(rgb), width, height


def _downscale(rgb: bytes, width: int, height: int, max_side: int = 160):
    long_side = max(width, height)
    if long_side <= max_side:
        return rgb, width, height
    scale = long_side / float(max_side)
    nw = max(1, int(round(width / scale)))
    nh = max(1, int(round(height / scale)))
    out = bytearray(nw * nh * 3)
    for y in range(nh):
        sy = min(height - 1, int(y * height / nh))
        row = sy * width * 3
        dst = y * nw * 3
        for x in range(nw):
            sx = min(width - 1, int(x * width / nw))
            i = row + sx * 3
            out[dst + x * 3] = rgb[i]
            out[dst + x * 3 + 1] = rgb[i + 1]
            out[dst + x * 3 + 2] = rgb[i + 2]
    return bytes(out), nw, nh


def _luma_of(rgb: bytes, width: int, height: int) -> list:
    out = [0] * (width * height)
    for i in range(width * height):
        o = i * 3
        out[i] = int(0.2126 * rgb[o] + 0.7152 * rgb[o + 1] + 0.0722 * rgb[o + 2])
    return out


def _lap_var(gray: list, width: int, height: int, x0: int, y0: int, x1: int, y1: int) -> float:
    x0 = max(1, x0)
    y0 = max(1, y0)
    x1 = min(width - 1, x1)
    y1 = min(height - 1, y1)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return 0.0
    acc = 0.0
    acc2 = 0.0
    n = 0
    for y in range(y0, y1):
        row = y * width
        for x in range(x0, x1):
            i = row + x
            value = (
                4 * gray[i]
                - gray[i - 1]
                - gray[i + 1]
                - gray[i - width]
                - gray[i + width]
            )
            acc += value
            acc2 += value * value
            n += 1
    if n <= 0:
        return 0.0
    mean = acc / n
    var = acc2 / n - mean * mean
    return var if var > 0 else 0.0


def _skin(r: int, g: int, b: int) -> bool:
    """Pelle anche con la luce di casa: la soglia stretta perdeva il volto."""
    mx = r if r > g else g
    if b > mx:
        mx = b
    mn = r if r < g else g
    if b < mn:
        mn = b
    return (
        r > 60 and g > 28 and b > 12 and r >= g and r >= b
        and (r - g) > 8 and (mx - mn) > 10
    )


def _find_faces(rgb: bytes, width: int, height: int, need_features: bool = True) -> list:
    mask = bytearray(width * height)
    for i in range(width * height):
        o = i * 3
        if _skin(rgb[o], rgb[o + 1], rgb[o + 2]):
            mask[i] = 1
    seen = bytearray(width * height)
    faces = []
    min_area = max(24, int(width * height * 0.004))
    for start in range(width * height):
        if not mask[start] or seen[start]:
            continue
        stack = [start]
        seen[start] = 1
        count = 0
        minx = width
        miny = height
        maxx = 0
        maxy = 0
        while stack:
            cur = stack.pop()
            count += 1
            x = cur % width
            y = cur // width
            if x < minx:
                minx = x
            if y < miny:
                miny = y
            if x > maxx:
                maxx = x
            if y > maxy:
                maxy = y
            if x > 0 and mask[cur - 1] and not seen[cur - 1]:
                seen[cur - 1] = 1
                stack.append(cur - 1)
            if x + 1 < width and mask[cur + 1] and not seen[cur + 1]:
                seen[cur + 1] = 1
                stack.append(cur + 1)
            if y > 0 and mask[cur - width] and not seen[cur - width]:
                seen[cur - width] = 1
                stack.append(cur - width)
            if y + 1 < height and mask[cur + width] and not seen[cur + width]:
                seen[cur + width] = 1
                stack.append(cur + width)
        bw = maxx - minx + 1
        bh = maxy - miny + 1
        if count < min_area or bw < 8 or bh < 8:
            continue
        if bw / float(bh) > 1.8 or bh / float(bw) > 2.2:
            continue
        if count / float(bw * bh) < 0.24:
            continue
        if need_features:
            if not _has_eyes(rgb, width, minx, miny, maxx, maxy) and not _has_profile(rgb, width, minx, miny, maxx, maxy):
                continue
        else:
            # Testa abbassata: gli occhi non si vedono, la pelle resta in basso.
            midy = (miny + maxy) / 2.0 / float(height or 1)
            if midy < 0.52 or bw / float(width or 1) < 0.08:
                continue
        if _looks_like_wood(rgb, width, minx, miny, maxx, maxy):
            continue
        # L'angolo in alto a sinistra di questa stanza è la credenza, non un volto.
        if minx <= 1 and miny <= 1:
            continue
        faces.append({
            "x": minx, "y": miny, "w": bw, "h": bh, "area": count,
        })
    faces.sort(key=lambda item: item["area"], reverse=True)
    kept = []
    for face in faces:
        if kept:
            main = kept[0]
            mcx = (main["x"] + main["w"] / 2.0) / float(width or 1)
            fcx = (face["x"] + face["w"] / 2.0) / float(width or 1)
            fill = face["area"] / float((face["w"] * face["h"]) or 1)
            # Un secondo volto vero sta lontano e ha la pelle piena.
            # La porta, vicina e più vuota, non conta.
            if abs(fcx - mcx) < 0.18 or fill < 0.42:
                continue
        if all(_overlap(face, other) < 0.45 for other in kept):
            kept.append(face)
        if len(kept) >= 4:
            break
    return kept


def _looks_like_wood(rgb, width, minx, miny, maxx, maxy) -> bool:
    """Porta o mobile: rosso e verde vicini, blu più basso. Non è pelle."""
    acc_r = 0.0
    acc_g = 0.0
    acc_b = 0.0
    n = 0
    for y in range(miny, maxy + 1, 2):
        row = y * width * 3
        for x in range(minx, maxx + 1, 2):
            i = row + x * 3
            if i + 2 >= len(rgb):
                continue
            acc_r += rgb[i]
            acc_g += rgb[i + 1]
            acc_b += rgb[i + 2]
            n += 1
    if n < 6:
        return False
    r = acc_r / n
    g = acc_g / n
    b = acc_b / n
    return abs(r - g) < 16 and ((r + g) / 2.0) > b + 14 and r > 60


def _has_eyes(rgb, width, minx, miny, maxx, maxy) -> bool:
    """Due zone scure rispetto alla pelle, non un nero assoluto."""
    bw = maxx - minx + 1
    bh = maxy - miny + 1
    y0 = miny + int(bh * 0.18)
    y1 = miny + int(bh * 0.62)
    if y1 <= y0 or bw < 8:
        return False
    acc = 0.0
    n = 0
    for y in range(y0, y1):
        row = y * width * 3
        for x in range(minx, maxx + 1):
            i = row + x * 3
            if i + 2 >= len(rgb):
                continue
            acc += 0.2126 * rgb[i] + 0.7152 * rgb[i + 1] + 0.0722 * rgb[i + 2]
            n += 1
    if n < 4:
        return False
    limit = min(120.0, (acc / n) - 16.0)
    left = _dark_count(rgb, width, minx + int(bw * 0.08), minx + int(bw * 0.48), y0, y1, limit)
    right = _dark_count(rgb, width, minx + int(bw * 0.52), minx + int(bw * 0.92), y0, y1, limit)
    need = 1 if bw * bh < 500 else 2
    return left >= need and right >= need


def _has_profile(rgb, width, minx, miny, maxx, maxy) -> bool:
    """Volto girato: un occhio solo, l'altro lato è capelli o muro."""
    bw = maxx - minx + 1
    bh = maxy - miny + 1
    y0 = miny + int(bh * 0.18)
    y1 = miny + int(bh * 0.62)
    if y1 <= y0 or bw < 8:
        return False
    acc = 0.0
    n = 0
    for y in range(y0, y1):
        row = y * width * 3
        for x in range(minx, maxx + 1):
            i = row + x * 3
            if i + 2 >= len(rgb):
                continue
            acc += 0.2126 * rgb[i] + 0.7152 * rgb[i + 1] + 0.0722 * rgb[i + 2]
            n += 1
    if n < 4:
        return False
    limit = min(120.0, (acc / n) - 16.0)
    left = _dark_count(rgb, width, minx + int(bw * 0.08), minx + int(bw * 0.48), y0, y1, limit)
    right = _dark_count(rgb, width, minx + int(bw * 0.52), minx + int(bw * 0.92), y0, y1, limit)
    need = 1 if bw * bh < 500 else 2
    strong = left if left > right else right
    weak = right if left > right else left
    return strong >= need and weak * 3 <= strong


def _dark_count(rgb, width, x0, x1, y0, y1, limit: float = 55) -> int:
    count = 0
    x0 = max(0, x0)
    x1 = max(x0, x1)
    for y in range(max(0, y0), y1):
        row = y * width * 3
        for x in range(x0, x1):
            i = row + x * 3
            if i + 2 >= len(rgb):
                continue
            yv = 0.2126 * rgb[i] + 0.7152 * rgb[i + 1] + 0.0722 * rgb[i + 2]
            if yv < limit:
                count += 1
    return count


def _overlap(a, b) -> float:
    ax1 = a["x"] + a["w"]
    ay1 = a["y"] + a["h"]
    bx1 = b["x"] + b["w"]
    by1 = b["y"] + b["h"]
    ix = max(0, min(ax1, bx1) - max(a["x"], b["x"]))
    iy = max(0, min(ay1, by1) - max(a["y"], b["y"]))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    return inter / float(min(a["area"], b["area"]) or 1)


def _color_name(r: int, g: int, b: int) -> str:
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx < 28:
        return "nero"
    if mn > 230:
        return "bianco"
    if mx - mn < 18:
        if mx < 80:
            return "grigio scuro"
        if mx > 190:
            return "grigio chiaro"
        return "grigio"
    if r >= g and r >= b:
        if g > b * 1.25 and g > 80:
            return "arancione" if r < 230 else "giallo"
        if b > g * 1.15 and r > 140:
            return "rosa"
        if b > g and r > 80:
            return "viola"
        return "rosso"
    if g >= r and g >= b:
        if b > r * 1.15:
            return "turchese"
        if r > 140 and g > 140:
            return "giallo"
        return "verde"
    if r > g * 1.25:
        return "viola"
    return "blu"


def _cast_name(r: float, g: float, b: float) -> str:
    if max(r, g, b) - min(r, g, b) < 16:
        return "neutro"
    if g > r + 22 and g > b + 18:
        return "tinta verde"
    if r > g + 22 and b > g + 18 and abs(r - b) < 40:
        return "tinta viola"
    if b > r + 26 and b > g + 10:
        return "troppo freddo"
    if r > b + 26 and g > b + 8 and r + 12 >= g:
        return "troppo caldo"
    return "neutro"


def _dominant_colors(rgb: bytes, width: int, height: int) -> list:
    counts = {}
    step = 1
    total = width * height
    if total > 4000:
        step = 2
    seen = 0
    for i in range(0, total, step):
        o = i * 3
        name = _color_name(rgb[o], rgb[o + 1], rgb[o + 2])
        counts[name] = counts.get(name, 0) + 1
        seen += 1
    if not seen:
        return []
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    out = []
    for name, count in ranked[:3]:
        if count / float(seen) >= 0.16:
            out.append(name)
        if len(out) >= 2:
            break
    return out


def _band(value: float, cuts: tuple, names: tuple, previous: str = "", slack: float = 0.035) -> str:
    """Fascia del punto. Se c'è già una fascia, non cambia per un nulla."""
    index = 0
    for cut in cuts:
        if value >= cut:
            index += 1
        else:
            break
    if previous in names:
        prev = names.index(previous)
    else:
        prev = index
    if index == prev:
        return names[index]
    if index > prev:
        if value < cuts[prev] + slack:
            return names[prev]
    elif value > cuts[prev - 1] - slack:
        return names[prev]
    return names[index]


def _join_place(horizontal: str, vertical: str) -> str:
    if horizontal == "centro" and vertical == "centro":
        return "centro"
    if vertical == "centro":
        return {
            "sinistra": "sinistra",
            "poco sinistra": "poco a sinistra",
            "poco destra": "poco a destra",
            "destra": "destra",
        }.get(horizontal, horizontal)
    if horizontal == "centro":
        return {
            "alto": "sopra",
            "poco alto": "poco sopra",
            "poco basso": "poco sotto",
            "basso": "sotto",
        }.get(vertical, vertical)
    h_word = "sinistra" if "sinistra" in horizontal else "destra"
    v_word = "alto" if "alto" in vertical else "basso"
    h_hard = horizontal in ("sinistra", "destra")
    v_hard = vertical in ("alto", "basso")
    if h_hard and v_hard:
        return f"{v_word} a {h_word}"
    if not h_hard and not v_hard:
        return f"poco {v_word} a {h_word}"
    if h_hard:
        return f"{h_word} e poco {v_word}"
    return f"{v_word} e poco {h_word}"


def _face_story(
    faces: list,
    width: int,
    height: int,
    previous_h: str = "",
    previous_v: str = "",
    crown: bool = False,
) -> dict:
    story = {
        "count": len(faces),
        "place": "",
        "distance": "",
        "cropped": False,
        "crop_side": "",
        "headroom": "",
        "fraction": 0.0,
    }
    if not faces:
        return story
    face = faces[0]
    story["fraction"] = face["area"] / float(width * height or 1)
    cx = (face["x"] + face["w"] / 2.0) / float(width)
    cy = (face["y"] + face["h"] * (0.22 if crown else 0.5)) / float(height)
    horizontal = _band(cx, _H_CUTS, _H_NAMES, previous_h, slack=0.01)
    vertical = _band(cy, _CROWN_CUTS if crown else _V_CUTS, _V_NAMES, previous_v)
    fw = face["w"] / float(width or 1)
    fh = face["h"] / float(height or 1)
    aspect = fh / fw if fw else 1.0
    tilt = ""
    # Il mento verso il soffitto accorcia il volto, ma solo se la fronte è ancora al centro.
    # Se la fronte è già in basso, la testa è abbassata: non chiamarla in alto.
    # Di profilo il volto si accorcia lo stesso, e lì conta solo la destra o la sinistra.
    if (
        crown
        and horizontal == "centro"
        and vertical not in ("poco basso", "basso")
        and fw >= 0.12
        and aspect < 1.32
    ):
        tilt = "alto" if aspect < 1.15 else "poco alto"
        vertical = tilt
    story["cx"] = cx
    story["cy"] = cy
    story["aspect"] = aspect
    story["hband"] = horizontal
    story["vband"] = vertical
    story["tilt"] = tilt
    story["place"] = _join_place(horizontal, vertical)
    ratio = max(fh, fw)
    # Un volto girato o col mento alto occupa meno riquadro: non è più lontano.
    if crown and fw >= 0.12 and aspect < 1.32 and ratio < 0.18:
        ratio = 0.22
    if ratio >= 0.70:
        story["distance"] = "troppo vicino"
    elif ratio >= 0.42:
        story["distance"] = "vicino"
    elif ratio >= 0.18:
        story["distance"] = "medio"
    elif ratio >= 0.10:
        story["distance"] = "lontano"
    else:
        story["distance"] = "troppo lontano"
    sides = []
    if face["x"] <= 1:
        sides.append("sinistra")
    if face["x"] + face["w"] >= width - 2:
        sides.append("destra")
    if face["y"] <= 1:
        sides.append("sopra")
    if face["y"] + face["h"] >= height - 2:
        sides.append("sotto")
    if sides:
        story["cropped"] = True
        story["crop_side"] = sides[0]
    top = face["y"] / float(height or 1)
    if top < 0.04:
        story["headroom"] = "poco"
    elif top < 0.28:
        story["headroom"] = "abbastanza"
    else:
        story["headroom"] = "molto"
    return story


def _region_mean(gray: list, width: int, height: int, x0: float, x1: float, y0: float, y1: float) -> float:
    xa = max(0, int(width * x0))
    xb = min(width, max(xa + 1, int(width * x1)))
    ya = max(0, int(height * y0))
    yb = min(height, max(ya + 1, int(height * y1)))
    acc = 0
    n = 0
    for y in range(ya, yb):
        row = y * width
        for x in range(xa, xb):
            acc += gray[row + x]
            n += 1
    if n < 4:
        return 128.0
    return acc / float(n)


def _bowed_head(gray: list, width: int, height: int) -> dict:
    """Mento sullo sterno: resta il capo in basso, e la credenza non è il volto."""
    empty = {
        "count": 0, "place": "", "distance": "",
        "cropped": False, "crop_side": "", "headroom": "", "fraction": 0.0,
    }
    if width < 8 or height < 8:
        return empty
    wall = _region_mean(gray, width, height, 0.35, 0.65, 0.12, 0.32)
    mid = _region_mean(gray, width, height, 0.35, 0.65, 0.38, 0.58)
    low = _region_mean(gray, width, height, 0.32, 0.68, 0.72, 0.98)
    # Il muro in alto resta chiaro, il posto del volto si svuota, il capo è scuro in basso.
    # Il mezzo vuoto (sopra 165) distingue il mento sullo sterno da un volto seduto.
    if wall < 180 or low > 104 or mid < 165 or mid < low + 60:
        return empty
    return {
        "count": 1,
        "place": "sotto",
        "distance": "medio",
        "cropped": False,
        "crop_side": "",
        "headroom": "molto",
        "fraction": 0.08,
        "cx": 0.50,
        "cy": 0.86,
        "hband": "centro",
        "vband": "basso",
        "tilt": "",
    }


def _shadow_story(gray: list, width: int, height: int) -> dict:
    """Sagoma scura contro uno sfondo chiaro: la persona in controluce."""
    empty = {
        "count": 0, "place": "", "distance": "",
        "cropped": False, "crop_side": "",
    }
    if width < 8 or height < 8:
        return empty
    mx = max(2, int(width * 0.12))
    my = max(2, int(height * 0.12))
    border_acc = 0
    border_n = 0
    for y in range(height):
        row = y * width
        for x in range(width):
            if x < mx or x >= width - mx or y < my or y >= height - my:
                border_acc += gray[row + x]
                border_n += 1
    if border_n < 8:
        return empty
    border_mean = border_acc / float(border_n)
    if border_mean < 110:
        return empty
    limit = border_mean - 30
    mask = bytearray(width * height)
    dark_n = 0
    for i, yv in enumerate(gray):
        if yv < limit:
            mask[i] = 1
            dark_n += 1
    total = width * height
    if dark_n < total * 0.04 or dark_n > total * 0.72:
        return empty
    seen = bytearray(total)
    best = None
    for start in range(total):
        if not mask[start] or seen[start]:
            continue
        stack = [start]
        seen[start] = 1
        count = 0
        minx = width
        miny = height
        maxx = 0
        maxy = 0
        while stack:
            cur = stack.pop()
            count += 1
            x = cur % width
            y = cur // width
            if x < minx:
                minx = x
            if y < miny:
                miny = y
            if x > maxx:
                maxx = x
            if y > maxy:
                maxy = y
            if x > 0 and mask[cur - 1] and not seen[cur - 1]:
                seen[cur - 1] = 1
                stack.append(cur - 1)
            if x + 1 < width and mask[cur + 1] and not seen[cur + 1]:
                seen[cur + 1] = 1
                stack.append(cur + 1)
            if y > 0 and mask[cur - width] and not seen[cur - width]:
                seen[cur - width] = 1
                stack.append(cur - width)
            if y + 1 < height and mask[cur + width] and not seen[cur + width]:
                seen[cur + width] = 1
                stack.append(cur + width)
        bw = maxx - minx + 1
        bh = maxy - miny + 1
        if count < total * 0.04 or bw < 8 or bh < 10:
            continue
        if bw > width * 0.94 and bh > height * 0.94:
            continue
        if bh < bw * 0.45:
            continue
        if count / float(bw * bh) < 0.35:
            continue
        if best is None or count > best["area"]:
            best = {"x": minx, "y": miny, "w": bw, "h": bh, "area": count}
    if not best:
        return empty
    # La posizione segue la testa, la parte alta della sagoma, non la pancia.
    head = dict(best)
    top_end = best["y"] + max(4, int(best["h"] * 0.40))
    accx = 0
    accn = 0
    hx0 = best["x"] + best["w"]
    hx1 = best["x"]
    for y in range(best["y"], min(height, top_end)):
        row = y * width
        for x in range(best["x"], best["x"] + best["w"]):
            if 0 <= row + x < len(mask) and mask[row + x]:
                accx += x
                accn += 1
                if x < hx0:
                    hx0 = x
                if x > hx1:
                    hx1 = x
    if accn >= 8 and hx1 > hx0:
        head["x"] = hx0
        head["w"] = hx1 - hx0 + 1
    story = _face_story([head], width, height)
    ratio = best["h"] / float(height or 1)
    if ratio >= 0.90:
        story["distance"] = "troppo vicino"
    elif ratio >= 0.72:
        story["distance"] = "vicino"
    elif ratio >= 0.22:
        story["distance"] = "medio"
    elif ratio >= 0.12:
        story["distance"] = "lontano"
    else:
        story["distance"] = "troppo lontano"
    story["count"] = 1
    return story


def _subject_story(gray: list, width: int, height: int) -> dict:
    """L'oggetto che si stacca dal muro: un foglio, un libro, una persona di lato."""
    empty = {
        "count": 0, "place": "", "distance": "",
        "cropped": False, "crop_side": "",
    }
    if width < 8 or height < 8:
        return empty
    mx = max(2, int(width * 0.08))
    my = max(2, int(height * 0.08))
    border_acc = 0
    border_n = 0
    for y in range(height):
        row = y * width
        for x in range(width):
            if x < mx or x >= width - mx or y < my or y >= height - my:
                border_acc += gray[row + x]
                border_n += 1
    if border_n < 8:
        return empty
    border_mean = border_acc / float(border_n)
    mask = bytearray(width * height)
    for i, yv in enumerate(gray):
        if abs(yv - border_mean) > 28:
            mask[i] = 1
    seen = bytearray(width * height)
    total = width * height
    best = None
    best_score = 0.0
    for start in range(total):
        if not mask[start] or seen[start]:
            continue
        stack = [start]
        seen[start] = 1
        count = 0
        minx = width
        miny = height
        maxx = 0
        maxy = 0
        while stack:
            cur = stack.pop()
            count += 1
            x = cur % width
            y = cur // width
            if x < minx:
                minx = x
            if y < miny:
                miny = y
            if x > maxx:
                maxx = x
            if y > maxy:
                maxy = y
            if x > 0 and mask[cur - 1] and not seen[cur - 1]:
                seen[cur - 1] = 1
                stack.append(cur - 1)
            if x + 1 < width and mask[cur + 1] and not seen[cur + 1]:
                seen[cur + 1] = 1
                stack.append(cur + 1)
            if y > 0 and mask[cur - width] and not seen[cur - width]:
                seen[cur - width] = 1
                stack.append(cur - width)
            if y + 1 < height and mask[cur + width] and not seen[cur + width]:
                seen[cur + width] = 1
                stack.append(cur + width)
        bw = maxx - minx + 1
        bh = maxy - miny + 1
        if count < total * 0.06 or bw < 8 or bh < 8:
            continue
        if bw > width * 0.92 and bh > height * 0.92:
            continue
        cx = (minx + maxx) / 2.0 / float(width)
        cy = (miny + maxy) / 2.0 / float(height)
        score = count * (1.35 - abs(cx - 0.50) - abs(cy - 0.58))
        if score > best_score:
            best_score = score
            best = {"x": minx, "y": miny, "w": bw, "h": bh, "area": count}
    if not best:
        return empty
    story = _face_story([best], width, height)
    ratio = best["h"] / float(height or 1)
    if ratio >= 0.85:
        story["distance"] = "troppo vicino"
    elif ratio >= 0.55:
        story["distance"] = "vicino"
    elif ratio >= 0.18:
        story["distance"] = "medio"
    elif ratio >= 0.08:
        story["distance"] = "lontano"
    else:
        story["distance"] = "troppo lontano"
    story["count"] = 1
    return story


def _sharp_where(gray, width, height) -> tuple:
    best_name = "centro"
    best_var = -1.0
    center_var = 0.0
    cells = (
        (0, 0, "alto a sinistra"),
        (1, 0, "sopra"),
        (2, 0, "alto a destra"),
        (0, 1, "sinistra"),
        (1, 1, "centro"),
        (2, 1, "destra"),
        (0, 2, "basso a sinistra"),
        (1, 2, "sotto"),
        (2, 2, "basso a destra"),
    )
    for col, row, name in cells:
        x0 = int(col * width / 3)
        x1 = int((col + 1) * width / 3)
        y0 = int(row * height / 3)
        y1 = int((row + 1) * height / 3)
        var = _lap_var(gray, width, height, x0, y0, x1, y1)
        if name == "centro":
            center_var = var
        if best_var < 0:
            best_var = var
            best_name = name
            continue
        margin = max(8.0, best_var * 0.08)
        if var > best_var + margin:
            best_var = var
            best_name = name
            continue
        if abs(var - best_var) <= margin and _PLACE_ORDER.index(name) < _PLACE_ORDER.index(best_name):
            best_var = var
            best_name = name
    whole = _lap_var(gray, width, height, 1, 1, width - 1, height - 1)
    center_soft = (
        best_name != "centro"
        and best_var >= _SHARP_SOFT
        and center_var < max(_SHARP_BLUR, best_var * 0.12)
    )
    return best_name, whole, center_soft


def analyze_rgb(
    rgb: bytes,
    width: int,
    height: int,
    *,
    exif_lines=None,
    motion: str = "",
    audio: str = "",
    flicker: bool = False,
) -> dict:
    if width <= 1 or height <= 1 or len(rgb) < width * height * 3:
        info = _empty_info()
        info["verdict"] = MSG_READ_FAIL
        info["lines"] = [MSG_READ_FAIL]
        return info
    small, sw, sh = _downscale(rgb, width, height, 160)
    gray = _luma_of(small, sw, sh)
    total = sw * sh
    acc = 0
    dark = 0
    white = 0
    acc_r = 0.0
    acc_g = 0.0
    acc_b = 0.0
    for i in range(total):
        yv = gray[i]
        acc += yv
        if yv < 14:
            dark += 1
        elif yv > 244:
            white += 1
        o = i * 3
        acc_r += small[o]
        acc_g += small[o + 1]
        acc_b += small[o + 2]
    mean = acc / float(total)
    var_sum = 0.0
    for yv in gray:
        diff = yv - mean
        var_sum += diff * diff
    std = (var_sum / float(total)) ** 0.5
    light_value = int(round(mean * 100.0 / 255.0))
    if light_value < 0:
        light_value = 0
    if light_value > 100:
        light_value = 100
    # Centro contro i bordi: controluce.
    cx0, cx1 = int(sw * 0.30), int(sw * 0.70)
    cy0, cy1 = int(sh * 0.30), int(sh * 0.70)
    center_acc = 0
    center_n = 0
    border_acc = 0
    border_n = 0
    for y in range(sh):
        row = y * sw
        for x in range(sw):
            yv = gray[row + x]
            if cx0 <= x < cx1 and cy0 <= y < cy1:
                center_acc += yv
                center_n += 1
            else:
                border_acc += yv
                border_n += 1
    center_mean = center_acc / float(center_n or 1)
    border_mean = border_acc / float(border_n or 1)
    controluce = (
        center_mean + 28 < border_mean and border_mean > 150 and center_mean < 120
    )
    dark_pct = dark / float(total)
    white_pct = white / float(total)
    if dark_pct > 0.90 and mean < 22:
        light = "assente"
    elif white_pct > 0.80 and mean > 225:
        light = "bruciata"
    elif controluce:
        light = "controluce"
    elif light_value < 32:
        light = "scarsa"
    elif light_value > 80:
        light = "troppa"
    else:
        light = "giusta"
    if std < 14:
        contrast = "piatto"
    elif std > 72:
        contrast = "duro"
    else:
        contrast = "giusto"
    where, whole_var, center_soft = _sharp_where(gray, sw, sh)
    if whole_var < _SHARP_BLUR:
        sharp = "sfocato"
    elif whole_var < _SHARP_SOFT:
        sharp = "morbido"
    else:
        sharp = "nitido"
    face_rgb, face_w, face_h = _downscale(rgb, width, height, 280)
    faces_small = _find_faces(face_rgb, face_w, face_h)
    if not faces_small:
        faces_small = _find_faces(face_rgb, face_w, face_h, need_features=False)
    scale_x = width / float(face_w)
    scale_y = height / float(face_h)
    faces = []
    for face in faces_small:
        faces.append({
            "x": int(face["x"] * scale_x),
            "y": int(face["y"] * scale_y),
            "w": max(1, int(face["w"] * scale_x)),
            "h": max(1, int(face["h"] * scale_y)),
            "area": max(1, int(face["area"] * scale_x * scale_y)),
        })
    story = _face_story(faces, width, height, crown=True)
    if not story["count"]:
        bowed = _bowed_head(gray, sw, sh)
        if bowed["count"]:
            story = bowed
    shadow = _shadow_story(gray, sw, sh) if not story["count"] else {
        "count": 0, "place": "", "distance": "", "cropped": False, "crop_side": "",
    }
    subject = {
        "count": 0, "place": "", "distance": "", "cropped": False, "crop_side": "",
    }
    if not story["count"] and not shadow["count"]:
        subject = _subject_story(gray, sw, sh)
    # Se il volto grande è caldo perché è pelle, non chiamarlo tinta.
    cast = _cast_name(acc_r / total, acc_g / total, acc_b / total)
    if story["count"] and story["fraction"] > 0.12 and cast == "troppo caldo":
        cast = "neutro"
    colors = _dominant_colors(small, sw, sh)
    if width > height:
        orientation = "orizzontale"
    elif height > width:
        orientation = "verticale"
    else:
        orientation = "quadrata"
    info = {
        "ok": True,
        "width": width,
        "height": height,
        "light": light,
        "light_value": light_value,
        "contrast": contrast,
        "cast": cast,
        "colors": colors,
        "sharp": sharp,
        "sharp_where": where,
        "center_soft": center_soft,
        "sharp_var": whole_var,
        "face_count": story["count"],
        "face_place": story["place"],
        "face_cx": story.get("cx"),
        "face_cy": story.get("cy"),
        "face_aspect": story.get("aspect") or 0.0,
        "face_hband": story.get("hband") or "",
        "face_vband": story.get("vband") or "",
        "face_tilt": story.get("tilt") or "",
        "face_distance": story["distance"],
        "face_cropped": story["cropped"],
        "face_crop_side": story["crop_side"],
        "headroom": story["headroom"],
        "shadow": bool(shadow["count"]),
        "shadow_place": shadow["place"],
        "shadow_cx": shadow.get("cx"),
        "shadow_cy": shadow.get("cy"),
        "shadow_hband": shadow.get("hband") or "",
        "shadow_vband": shadow.get("vband") or "",
        "shadow_distance": shadow["distance"],
        "shadow_cropped": shadow["cropped"],
        "shadow_crop_side": shadow["crop_side"],
        "subject": bool(subject["count"]),
        "subject_place": subject["place"],
        "subject_cx": subject.get("cx"),
        "subject_cy": subject.get("cy"),
        "subject_distance": subject["distance"],
        "subject_cropped": subject["cropped"],
        "subject_crop_side": subject["crop_side"],
        "orientation": orientation,
        "motion": motion or "",
        "audio": audio or "",
        "flicker": bool(flicker),
        "exif_lines": list(exif_lines or []),
    }
    _compose(info)
    return info


def _empty_info() -> dict:
    return {
        "ok": False,
        "width": 0,
        "height": 0,
        "light": "",
        "light_value": 0,
        "contrast": "",
        "cast": "",
        "colors": [],
        "sharp": "",
        "sharp_where": "",
        "center_soft": False,
        "sharp_var": 0.0,
        "face_count": 0,
        "face_place": "",
        "face_distance": "",
        "face_cropped": False,
        "face_crop_side": "",
        "headroom": "",
        "shadow": False,
        "shadow_place": "",
        "shadow_distance": "",
        "shadow_cropped": False,
        "shadow_crop_side": "",
        "orientation": "",
        "motion": "",
        "audio": "",
        "flicker": False,
        "exif_lines": [],
        "ready_photo": False,
        "ready_record": False,
        "verdict": "",
        "lines": [],
        "coach": "",
    }


def _placed_ok(place: str, cropped: bool, distance: str) -> bool:
    if cropped or place != "centro":
        return False
    return distance in ("vicino", "medio")


def _face_ok(info: dict) -> bool:
    if info.get("face_count"):
        return _placed_ok(
            info.get("face_place") or "",
            bool(info.get("face_cropped")),
            info.get("face_distance") or "",
        )
    if info.get("shadow"):
        return _placed_ok(
            info.get("shadow_place") or "",
            bool(info.get("shadow_cropped")),
            info.get("shadow_distance") or "",
        )
    if info.get("subject"):
        return _placed_ok(
            info.get("subject_place") or "",
            bool(info.get("subject_cropped")),
            info.get("subject_distance") or "",
        )
    return True


def _compose(info: dict) -> None:
    lines = []
    light = info.get("light") or ""
    value = int(info.get("light_value") or 0)
    light_word = {
        "assente": "Luce assente",
        "scarsa": "Luce scarsa",
        "giusta": "Luce giusta",
        "troppa": "Troppa luce",
        "bruciata": "Luce bruciata",
        "controluce": "Controluce",
    }.get(light, "Luce")
    shown = int(round(value / 5.0) * 5)
    if shown < 0:
        shown = 0
    if shown > 100:
        shown = 100
    lines.append(f"{light_word}, {shown} su 100.")
    contrast = info.get("contrast") or ""
    if contrast:
        lines.append(f"Contrasto {contrast}.")
    cast = info.get("cast") or "neutro"
    cast_line = {
        "neutro": "Colore neutro.",
        "troppo caldo": "Colore troppo caldo.",
        "troppo freddo": "Colore troppo freddo.",
        "tinta verde": "Tinta verde.",
        "tinta viola": "Tinta viola.",
    }.get(cast, "Colore neutro.")
    colors = info.get("colors") or []
    if colors:
        cast_line = cast_line[:-1] + ". Colori: " + ", ".join(colors) + "."
    lines.append(cast_line)
    sharp = info.get("sharp") or ""
    where = info.get("sharp_where") or "centro"
    where_phrase = _WHERE_PHRASE.get(where, where)
    if sharp == "sfocato":
        sharp_line = "Sfocato."
        if info.get("center_soft"):
            sharp_line = f"Sfocato. Più nitido {where_phrase}."
    elif sharp == "morbido":
        sharp_line = "Poco nitido."
        if info.get("center_soft"):
            sharp_line = f"Poco nitido. Più nitido {where_phrase}."
    else:
        sharp_line = "Nitido, al centro." if where == "centro" else "Nitido."
        if info.get("center_soft"):
            sharp_line = f"Più nitido {where_phrase}. Il centro è sfocato."
    lines.append(sharp_line)
    count = int(info.get("face_count") or 0)
    if count <= 0 and info.get("shadow"):
        place = _WHERE_PHRASE.get(info.get("shadow_place") or "", "")
        distance = info.get("shadow_distance") or ""
        if info.get("light") == "controluce":
            shadow_line = f"Sagoma in ombra, {place}, {distance}."
        else:
            shadow_line = f"Sagoma, {place}, {distance}."
        if info.get("shadow_cropped"):
            shadow_line = shadow_line[:-1] + ", tagliata sul bordo."
        lines.append(shadow_line)
    elif count <= 0 and info.get("subject"):
        place = _WHERE_PHRASE.get(info.get("subject_place") or "", "")
        distance = info.get("subject_distance") or ""
        subject_line = f"Soggetto, {place}, {distance}."
        if info.get("subject_cropped"):
            subject_line = subject_line[:-1] + ", tagliato sul bordo."
        lines.append(subject_line)
    elif count <= 0:
        lines.append("Nessun volto.")
    else:
        place = _WHERE_PHRASE.get(info.get("face_place") or "", info.get("face_place") or "")
        distance = info.get("face_distance") or ""
        if count == 1:
            face_line = f"Un volto, {place}, {distance}."
        else:
            face_line = f"{count} volti. Il più grande è {place}, {distance}."
        if info.get("face_cropped"):
            face_line = face_line[:-1] + ", tagliato sul bordo."
        lines.append(face_line)
        if info.get("headroom"):
            lines.append(f"Spazio sopra la testa: {info['headroom']}.")
    if info.get("orientation"):
        lines.append(f"Inquadratura {info['orientation']}.")
    if info.get("motion"):
        lines.append(f"Stabilità: {info['motion']}.")
    if info.get("flicker"):
        lines.append("La luce sfarfalla.")
    audio = info.get("audio") or ""
    if audio:
        audio_line = {
            "muto": "Video muto.",
            "silenzio": "Audio: silenzio.",
            "basso": "Audio: basso.",
            "giusto": "Audio: giusto.",
            "troppo alto": "Audio: troppo alto.",
            "saturo": "Audio: saturo.",
            "sconosciuto": "Audio: non misurato.",
            "attesa": "Audio: ancora un attimo.",
        }.get(audio, f"Audio: {audio}.")
        lines.append(audio_line)
    for extra in info.get("exif_lines") or []:
        if extra and extra not in lines:
            lines.append(extra if extra.endswith(".") else extra + ".")
    face_ok = _face_ok(info)
    ready_photo = (
        light == "giusta"
        and sharp == "nitido"
        and contrast != "piatto"
        and not info.get("flicker")
        and not info.get("center_soft")
        and face_ok
        and cast == "neutro"
    )
    motion = info.get("motion") or ""
    audio_ok = audio in ("", "giusto", "basso")
    stable = motion in ("", "ferma")
    ready_record = ready_photo and stable and audio in ("giusto", "basso")
    info["ready_photo"] = ready_photo
    info["ready_record"] = ready_record
    info["lines"] = lines
    info["coach"] = _coach(info)
    info["verdict"] = _verdict(info)


def _verdict(info: dict) -> str:
    light = info.get("light")
    if light == "assente":
        return "Non si vede niente. Luce assente."
    if light == "bruciata":
        return "Tutto bruciato. Troppa luce."
    if info.get("ready_record"):
        if info.get("face_count"):
            return (
                "Pronto. Luce giusta, nitido, volto al centro. "
                "Puoi scattare o registrare."
            )
        if info.get("subject") or info.get("shadow"):
            return (
                "Pronto. Luce giusta, nitido, soggetto al centro. "
                "Puoi scattare o registrare."
            )
        return "Pronto. Luce giusta, nitido. Nessun volto. Puoi scattare o registrare."
    if info.get("ready_photo"):
        tail = "Puoi scattare."
        if info.get("audio") == "silenzio":
            tail = "Puoi scattare. Per registrare, non sento l'audio."
        elif info.get("audio") == "saturo":
            tail = "Puoi scattare. Per registrare, l'audio satura."
        elif info.get("audio") == "troppo alto":
            tail = "Puoi scattare. Per registrare, l'audio è troppo alto."
        elif info.get("motion") in ("si muove", "traballa"):
            tail = "Puoi scattare. Per registrare, fermo."
        elif info.get("audio") == "attesa":
            tail = "Puoi scattare."
        if info.get("face_count"):
            return f"Pronto. Luce giusta, nitido, volto al centro. {tail}"
        if info.get("subject") or info.get("shadow"):
            return f"Pronto. Luce giusta, nitido, soggetto al centro. {tail}"
        return f"Pronto. Luce giusta, nitido. Nessun volto. {tail}"
    bits = []
    if info.get("face_count"):
        place = _WHERE_PHRASE.get(info.get("face_place") or "", "")
        if info.get("face_cropped"):
            bits.append(f"Il volto è {place} e tagliato sul bordo.")
        elif info.get("face_place") and info.get("face_place") != "centro":
            bits.append(f"Il volto è {place}.")
        if info.get("face_distance") in ("troppo vicino", "troppo lontano", "lontano"):
            if info["face_distance"] == "troppo vicino":
                bits.append("Troppo vicino.")
            elif info["face_distance"] == "lontano":
                bits.append("Lontano.")
            else:
                bits.append("Troppo lontano.")
    elif info.get("shadow"):
        place = _WHERE_PHRASE.get(info.get("shadow_place") or "", "")
        if info.get("shadow_cropped"):
            bits.append(f"La sagoma è {place} e tagliata sul bordo.")
        elif info.get("shadow_place") and info.get("shadow_place") != "centro":
            bits.append(f"La sagoma è {place}.")
        elif info.get("shadow_place") == "centro":
            bits.append("Sei al centro.")
        if info.get("shadow_distance") in ("troppo vicino", "troppo lontano", "lontano"):
            if info["shadow_distance"] == "troppo vicino":
                bits.append("Troppo vicino.")
            elif info["shadow_distance"] == "lontano":
                bits.append("Lontano.")
            else:
                bits.append("Troppo lontano.")
    elif info.get("subject"):
        place = _WHERE_PHRASE.get(info.get("subject_place") or "", "")
        if info.get("subject_cropped"):
            bits.append(f"Il soggetto è {place} e tagliato sul bordo.")
        elif info.get("subject_place") and info.get("subject_place") != "centro":
            bits.append(f"Il soggetto è {place}.")
        elif info.get("subject_place") == "centro":
            bits.append("Il soggetto è al centro.")
        if info.get("subject_distance") in ("troppo vicino", "troppo lontano", "lontano"):
            if info["subject_distance"] == "troppo vicino":
                bits.append("Troppo vicino.")
            elif info["subject_distance"] == "lontano":
                bits.append("Lontano.")
            else:
                bits.append("Troppo lontano.")
    if light == "scarsa":
        bits.append("Luce scarsa.")
    elif light == "troppa":
        bits.append("Troppa luce.")
    elif light == "controluce":
        bits.append("Controluce.")
    if info.get("sharp") == "sfocato":
        bits.append("Sfocato.")
    elif info.get("sharp") == "morbido":
        bits.append("Poco nitido.")
    if info.get("center_soft") and info.get("sharp") != "sfocato":
        where = _WHERE_PHRASE.get(info.get("sharp_where") or "", "")
        extra = f"Più nitido {where}. Il centro è sfocato."
        if extra not in bits:
            bits.append(extra)
    cast = info.get("cast") or ""
    if cast and cast != "neutro":
        bits.append({
            "troppo caldo": "Colore troppo caldo.",
            "troppo freddo": "Colore troppo freddo.",
            "tinta verde": "Tinta verde.",
            "tinta viola": "Tinta viola.",
        }.get(cast, ""))
    if info.get("contrast") == "piatto" and light == "giusta":
        bits.append("Contrasto piatto.")
    if info.get("flicker"):
        bits.append("La luce sfarfalla.")
    bits = [bit for bit in bits if bit]
    if not bits:
        bits.append("Sistemare.")
    return "Sistemare. " + " ".join(bits)


def _subject_box(info: dict):
    if info.get("face_count"):
        return {
            "place": info.get("face_place") or "",
            "distance": info.get("face_distance") or "",
            "cropped": bool(info.get("face_cropped")),
            "side": info.get("face_crop_side") or "",
        }
    if info.get("shadow"):
        return {
            "place": info.get("shadow_place") or "",
            "distance": info.get("shadow_distance") or "",
            "cropped": bool(info.get("shadow_cropped")),
            "side": info.get("shadow_crop_side") or "",
        }
    if info.get("subject"):
        return {
            "place": info.get("subject_place") or "",
            "distance": info.get("subject_distance") or "",
            "cropped": bool(info.get("subject_cropped")),
            "side": info.get("subject_crop_side") or "",
        }
    return None


def _subject_centered(info: dict) -> bool:
    box = _subject_box(info)
    return bool(box and box["place"] == "centro" and not box["cropped"])


def _place_hint(info: dict) -> str:
    box = _subject_box(info)
    if not box:
        return ""
    if box["cropped"] or box["place"] not in ("", "centro"):
        key = box["side"] if box["cropped"] else box["place"]
        hint = {
            "sinistra": "Più a destra.",
            "destra": "Più a sinistra.",
            "poco a sinistra": "Un po' a destra.",
            "poco a destra": "Un po' a sinistra.",
            "sopra": "Più giù.",
            "alto": "Più giù.",
            "sotto": "Più su.",
            "basso": "Più su.",
            "poco sopra": "Un po' più giù.",
            "poco sotto": "Un po' più su.",
            "alto a sinistra": "Più a destra. Più giù.",
            "alto a destra": "Più a sinistra. Più giù.",
            "basso a sinistra": "Più a destra. Più su.",
            "basso a destra": "Più a sinistra. Più su.",
            "poco alto a sinistra": "Un po' a destra. Un po' più giù.",
            "poco alto a destra": "Un po' a sinistra. Un po' più giù.",
            "poco basso a sinistra": "Un po' a destra. Un po' più su.",
            "poco basso a destra": "Un po' a sinistra. Un po' più su.",
            "sinistra e poco alto": "Più a destra. Un po' più giù.",
            "destra e poco alto": "Più a sinistra. Un po' più giù.",
            "sinistra e poco basso": "Più a destra. Un po' più su.",
            "destra e poco basso": "Più a sinistra. Un po' più su.",
            "alto e poco sinistra": "Più giù. Un po' a destra.",
            "alto e poco destra": "Più giù. Un po' a sinistra.",
            "basso e poco sinistra": "Più su. Un po' a destra.",
            "basso e poco destra": "Più su. Un po' a sinistra.",
        }.get(key or "", "")
        return hint or "Sistemati al centro."
    if box["distance"] == "troppo vicino":
        return "Troppo vicino, allontanati."
    if box["distance"] in ("lontano", "troppo lontano"):
        return "Avvicinati un poco."
    return ""


def _coach(info: dict) -> str:
    light = info.get("light")
    if light == "assente":
        return "Non si vede niente."
    if light == "bruciata":
        return "Troppa luce."
    hint = _place_hint(info)
    if hint:
        return hint
    if light in ("bruciata", "troppa"):
        return "Troppa luce."
    if light == "scarsa":
        return "Più luce."
    if light == "controluce":
        if _subject_centered(info):
            return "Sei al centro. Controluce."
        return "Controluce."
    if info.get("flicker"):
        return "La luce sfarfalla."
    if info.get("motion") == "traballa":
        return "Fermo."
    if info.get("sharp") == "sfocato":
        return "Sfocato. Fermo."
    if info.get("sharp") == "morbido":
        return "Poco nitido. Fermo."
    if info.get("center_soft"):
        return "Il centro è sfocato."
    cast = info.get("cast") or ""
    if cast == "troppo caldo":
        return "Colore troppo caldo."
    if cast == "troppo freddo":
        return "Colore troppo freddo."
    if cast == "tinta verde":
        return "Tinta verde."
    if cast == "tinta viola":
        return "Tinta viola."
    if info.get("contrast") == "piatto":
        return "Contrasto piatto."
    if info.get("audio") == "silenzio" and info.get("ready_photo"):
        return "Pronto per lo scatto. Per registrare, non sento l'audio."
    if info.get("audio") == "saturo" and info.get("ready_photo"):
        return "Pronto per lo scatto. Per registrare, l'audio satura."
    if info.get("motion") == "si muove" and info.get("ready_photo"):
        return "Pronto per lo scatto. Per registrare, fermo."
    if info.get("ready_record"):
        return "Nitido. Puoi scattare o registrare."
    if info.get("ready_photo"):
        return "Nitido. Puoi scattare."
    return "Sistemare."


_MOVE_BIT = {
    "sinistra": "più a destra",
    "destra": "più a sinistra",
    "poco a sinistra": "un po' a destra",
    "poco a destra": "un po' a sinistra",
    "sopra": "più giù",
    "alto": "più giù",
    "sotto": "più su",
    "basso": "più su",
    "poco sopra": "un po' più giù",
    "poco sotto": "un po' più su",
    "alto a sinistra": "più a destra e più giù",
    "alto a destra": "più a sinistra e più giù",
    "basso a sinistra": "più a destra e più su",
    "basso a destra": "più a sinistra e più su",
    "poco alto a sinistra": "un po' a destra e un po' più giù",
    "poco alto a destra": "un po' a sinistra e un po' più giù",
    "poco basso a sinistra": "un po' a destra e un po' più su",
    "poco basso a destra": "un po' a sinistra e un po' più su",
    "sinistra e poco alto": "più a destra e un po' più giù",
    "destra e poco alto": "più a sinistra e un po' più giù",
    "sinistra e poco basso": "più a destra e un po' più su",
    "destra e poco basso": "più a sinistra e un po' più su",
    "alto e poco sinistra": "più giù e un po' a destra",
    "alto e poco destra": "più giù e un po' a sinistra",
    "basso e poco sinistra": "più su e un po' a destra",
    "basso e poco destra": "più su e un po' a sinistra",
}


def _move_order(box: dict | None, verb: str) -> str:
    if not box:
        return ""
    centered = box.get("place") in ("", "centro") and not box.get("cropped")
    if centered and box.get("distance") == "troppo vicino":
        return "Allontanati." if verb == "Spostati" else "Allontanalo."
    if centered and box.get("distance") in ("lontano", "troppo lontano"):
        return "Avvicinati un poco." if verb == "Spostati" else "Avvicinalo un poco."
    if box.get("cropped") or box.get("place") not in ("", "centro"):
        key = box.get("side") if box.get("cropped") else box.get("place")
        bit = _MOVE_BIT.get(key or "")
        if bit:
            return f"{verb} {bit}."
        return f"{verb} al centro."
    return ""


def _fine_offset(cx, cy, aspect=0.0) -> tuple:
    """Dentro «al centro»: proprio al centro, oppure un filo fuori."""
    horizontal = ""
    vertical = ""
    if cx is not None:
        if cx < 0.495:
            horizontal = "sinistra"
        elif cx > 0.516:
            horizontal = "destra"
    if cy is not None:
        if cy < 0.535:
            vertical = "alto"
        elif cy > 0.565:
            vertical = "basso"
    # Il mento verso il soffitto accorcia il volto, e la fronte resta nello stesso punto.
    # Sotto 1,32 la frase è già «un po' in alto». Qui è solo il filo, prima di quel gradino.
    if not vertical and aspect and aspect < 1.48:
        vertical = "alto"
    return horizontal, vertical


def _fine_phrase(who: str, verb: str, cx, cy, aspect=0.0) -> tuple:
    horizontal, vertical = _fine_offset(cx, cy, aspect)
    if not horizontal and not vertical:
        return f"Il {who} è proprio al centro.", ""
    where = []
    moves = []
    if vertical == "alto":
        where.append("un filo in alto")
        moves.append("un filo più giù")
    elif vertical == "basso":
        where.append("un filo in basso")
        moves.append("un filo più su")
    if horizontal == "sinistra":
        where.append("un filo a sinistra")
        moves.append("un filo a destra")
    elif horizontal == "destra":
        where.append("un filo a destra")
        moves.append("un filo a sinistra")
    stated = f"Il {who} è " + " e ".join(where) + "."
    return stated, f"{verb} " + " e ".join(moves) + "."


def _frame_phrase(info: dict) -> str:
    """Dove sta il volto o il soggetto, e dove spostarlo. Una frase sola."""
    if not info:
        return ""
    light = info.get("light") or ""
    if light == "assente":
        return "Non si vede niente."
    if light == "bruciata":
        return "Tutto bruciato. Troppa luce."
    box = _subject_box(info)
    if info.get("face_count"):
        who = "volto" if int(info.get("face_count") or 0) == 1 else "volto più grande"
        verb = "Spostati"
    elif info.get("shadow"):
        who, verb = "soggetto", "Spostati"
    elif info.get("subject"):
        who, verb = "soggetto", "Spostalo"
    else:
        return "Nessun volto."
    place = (box or {}).get("place") or ""
    where = _WHERE_PHRASE.get(place, "")
    if box and box.get("cropped"):
        side = _WHERE_PHRASE.get(box.get("side") or "", "")
        stated = f"Il {who} è tagliato {side}." if side else f"Il {who} è tagliato."
    elif place == "centro" and info.get("face_count") and not (box or {}).get("cropped"):
        stated, fine_move = _fine_phrase(
            who, verb, info.get("face_cx"), info.get("face_cy"), info.get("face_aspect") or 0.0,
        )
        if fine_move:
            return f"{stated} {fine_move}"
    elif place == "centro":
        stated = f"Il {who} è al centro."
    elif where:
        stated = f"Il {who} è {where}."
    else:
        stated = f"Il {who} c'è."
    move = _move_order(box, verb)
    if move:
        return f"{stated} {move}"
    if info.get("ready_record"):
        return f"{stated} Puoi scattare o registrare."
    if info.get("ready_photo"):
        return f"{stated} Puoi scattare."
    if light == "controluce":
        return f"{stated} Controluce."
    if light == "scarsa":
        return f"{stated} Più luce."
    if light == "troppa":
        return f"{stated} Troppa luce."
    if info.get("sharp") == "sfocato":
        return f"{stated} Sfocato."
    if info.get("sharp") == "morbido":
        return f"{stated} Poco nitido."
    return stated


def report_text(info: dict) -> str:
    if not info:
        return MSG_READ_FAIL
    lines = [info.get("verdict") or MSG_READ_FAIL]
    for line in info.get("lines") or []:
        if line and line not in lines:
            lines.append(line)
    return "\n".join(lines)


def live_speech(prev: dict | None, cur: dict) -> str:
    """Prima volta: il giudizio intero. Poi solo ciò che è cambiato."""
    if not cur:
        return ""
    if prev is None:
        return report_text(cur).replace("\n", " ")
    parts = []
    if prev.get("light") != cur.get("light"):
        parts.append(cur["lines"][0] if cur.get("lines") else "")
    if prev.get("contrast") != cur.get("contrast") and cur.get("contrast"):
        parts.append(f"Contrasto {cur['contrast']}.")
    if prev.get("cast") != cur.get("cast"):
        for line in cur.get("lines") or []:
            if line.startswith("Colore") or line.startswith("Tinta"):
                parts.append(line)
                break
    if prev.get("sharp") != cur.get("sharp") or prev.get("center_soft") != cur.get("center_soft"):
        for line in cur.get("lines") or []:
            if line.startswith("Sfocato") or line.startswith("Poco nitido") or line.startswith("Più nitido") or line.startswith("Nitido"):
                parts.append(line)
                break
    face_keys = (
        "face_count", "face_place", "face_distance", "face_cropped",
        "shadow", "shadow_place", "shadow_distance", "shadow_cropped",
        "subject", "subject_place", "subject_distance", "subject_cropped",
    )
    if any(prev.get(key) != cur.get(key) for key in face_keys):
        for line in cur.get("lines") or []:
            low = line.lower()
            if "volto" in low or "sagoma" in low or "soggetto" in low:
                parts.append(line)
                break
    if prev.get("motion") != cur.get("motion") and cur.get("motion"):
        parts.append(f"Stabilità: {cur['motion']}.")
    if prev.get("flicker") != cur.get("flicker") and cur.get("flicker"):
        parts.append("La luce sfarfalla.")
    if prev.get("audio") != cur.get("audio") and cur.get("audio") not in ("", "attesa"):
        for line in cur.get("lines") or []:
            if line.startswith("Audio") or line.startswith("Video muto"):
                parts.append(line)
                break
    coach = cur.get("coach") or ""
    if coach and coach != (prev.get("coach") or "") and coach not in " ".join(parts):
        parts.append(coach)
    if cur.get("ready_photo") and not prev.get("ready_photo"):
        verdict = cur.get("verdict") or ""
        if verdict and verdict not in " ".join(parts):
            parts.insert(0, verdict)
    cleaned = []
    for part in parts:
        part = (part or "").strip()
        if part and part not in cleaned:
            cleaned.append(part)
    return " ".join(cleaned)


def with_live(info: dict, *, motion: str = "", audio: str = "", flicker: bool = False) -> dict:
    nxt = dict(info)
    nxt["motion"] = motion or ""
    nxt["audio"] = audio or ""
    nxt["flicker"] = bool(flicker)
    nxt["colors"] = list(info.get("colors") or [])
    nxt["exif_lines"] = list(info.get("exif_lines") or [])
    nxt["lines"] = list(info.get("lines") or [])
    _compose(nxt)
    return nxt


def mean_abs_diff(rgb_a: bytes, rgb_b: bytes, width: int, height: int) -> float:
    if not rgb_a or not rgb_b or len(rgb_a) != len(rgb_b):
        return 0.0
    acc = 0.0
    n = width * height
    if n <= 0:
        return 0.0
    for i in range(n):
        o = i * 3
        ya = 0.2126 * rgb_a[o] + 0.7152 * rgb_a[o + 1] + 0.0722 * rgb_a[o + 2]
        yb = 0.2126 * rgb_b[o] + 0.7152 * rgb_b[o + 1] + 0.0722 * rgb_b[o + 2]
        acc += abs(ya - yb)
    return acc / float(n)


def motion_label(amount: float) -> str:
    if amount < 6:
        return "ferma"
    if amount < 18:
        return "si muove"
    return "traballa"


def flicker_from_levels(levels: list) -> bool:
    if len(levels) < 4:
        return False
    reversals = 0
    prev_sign = 0
    for a, b in zip(levels, levels[1:]):
        delta = b - a
        if abs(delta) < 12:
            continue
        sign = 1 if delta > 0 else -1
        if prev_sign and sign != prev_sign:
            reversals += 1
        prev_sign = sign
    return reversals >= 2


def classify_volume(mean_db, max_db, has_audio: bool) -> str:
    if not has_audio:
        return "muto"
    if mean_db is None and max_db is None:
        return "sconosciuto"
    mean_db = float(mean_db if mean_db is not None else -99)
    max_db = float(max_db if max_db is not None else mean_db)
    if max_db <= -45 or mean_db <= -50:
        return "silenzio"
    if mean_db <= -32:
        return "basso"
    if max_db >= -1.0:
        return "saturo"
    if mean_db >= -8:
        return "troppo alto"
    return "giusto"


def _format_meters(meters: float) -> str:
    if meters <= 0:
        return ""
    if meters >= 30:
        return "Distanza scritta dalla fotocamera: infinita."
    if meters >= 1:
        text = f"{meters:.1f}".replace(".", ",")
        if text.endswith(",0"):
            text = text[:-2]
        unit = "metro" if abs(meters - 1.0) < 0.05 else "metri"
        return f"Distanza scritta dalla fotocamera: {text} {unit}."
    cm = int(round(meters * 100))
    return f"Distanza scritta dalla fotocamera: {cm} centimetri."


def read_exif_lines(path: str) -> list:
    try:
        with open(path, "rb") as handle:
            blob = handle.read(512 * 1024)
    except Exception:
        return []
    if len(blob) < 4 or blob[:2] != b"\xff\xd8":
        return []
    pos = 2
    tiff = b""
    while pos + 4 <= len(blob):
        if blob[pos] != 0xFF:
            break
        code = blob[pos + 1]
        if code in (0xD8, 0xD9):
            pos += 2
            continue
        if pos + 4 > len(blob):
            break
        length = struct.unpack_from(">H", blob, pos + 2)[0]
        if length < 2 or pos + 2 + length > len(blob):
            break
        chunk = blob[pos + 4:pos + 2 + length]
        if code == 0xE1 and chunk.startswith(b"Exif\x00\x00"):
            tiff = chunk[6:]
            break
        if code == 0xDA:
            break
        pos += 2 + length
    if not tiff:
        return []
    tags = _exif_tags(tiff)
    return _exif_phrases(tags)


def _exif_tags(tiff: bytes) -> dict:
    if len(tiff) < 8:
        return {}
    endian = "<" if tiff[:2] == b"II" else ">"
    if tiff[2:4] not in (b"\x2a\x00", b"\x00\x2a"):
        return {}
    offset = struct.unpack_from(endian + "I", tiff, 4)[0]
    found = {}
    _walk_ifd(tiff, offset, endian, found, depth=0)
    return found


def _walk_ifd(tiff, offset, endian, found, depth) -> None:
    if depth > 3 or offset < 0 or offset + 2 > len(tiff):
        return
    count = struct.unpack_from(endian + "H", tiff, offset)[0]
    pos = offset + 2
    sub = None
    for _ in range(count):
        if pos + 12 > len(tiff):
            break
        tag, typ, ncount = struct.unpack_from(endian + "HHI", tiff, pos)
        raw = tiff[pos + 8:pos + 12]
        pos += 12
        size = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 10: 8}.get(typ, 1)
        nbytes = ncount * size
        if nbytes <= 4:
            data = raw[:nbytes]
        else:
            ptr = struct.unpack_from(endian + "I", raw, 0)[0]
            data = tiff[ptr:ptr + nbytes] if 0 <= ptr < len(tiff) else b""
        if tag == 0x8769 and typ == 4 and len(data) >= 4:
            sub = struct.unpack_from(endian + "I", data, 0)[0]
            continue
        value = _exif_value(data, typ, ncount, endian)
        if value is not None:
            found[tag] = value
    if sub:
        _walk_ifd(tiff, sub, endian, found, depth + 1)


def _exif_value(data: bytes, typ: int, count: int, endian: str):
    if not data:
        return None
    try:
        if typ == 2:
            return data.split(b"\x00")[0].decode("latin1", "ignore").strip()
        if typ == 3 and len(data) >= 2:
            return struct.unpack_from(endian + "H", data, 0)[0]
        if typ == 4 and len(data) >= 4:
            return struct.unpack_from(endian + "I", data, 0)[0]
        if typ in (5, 10) and len(data) >= 8:
            if typ == 5:
                num, den = struct.unpack_from(endian + "II", data, 0)
            else:
                num, den = struct.unpack_from(endian + "ii", data, 0)
            if den:
                return num / float(den)
            return None
    except Exception:
        return None
    return None


def _exif_phrases(tags: dict) -> list:
    lines = []
    exposure = tags.get(0x829A)
    if isinstance(exposure, float) and exposure > 0:
        if exposure >= 1:
            lines.append(f"Tempo di scatto: {exposure:.1f} secondi.".replace(".", ","))
        else:
            den = int(round(1.0 / exposure))
            lines.append(f"Tempo di scatto: 1/{den}.")
    fnumber = tags.get(0x829D)
    if isinstance(fnumber, float) and fnumber > 0:
        text = f"{fnumber:.1f}".replace(".", ",")
        lines.append(f"Diaframma: f/{text}.")
    iso = tags.get(0x8827)
    if isinstance(iso, int) and iso > 0:
        lines.append(f"ISO: {iso}.")
    focal = tags.get(0x920A)
    if isinstance(focal, float) and focal > 0:
        lines.append(f"Focale: {int(round(focal))} millimetri.")
    distance = tags.get(0x9206)
    if isinstance(distance, float):
        phrase = _format_meters(distance)
        if phrase:
            lines.append(phrase)
    wb = tags.get(0xA403)
    if wb == 0:
        lines.append("Bilanciamento del bianco nello scatto: automatico.")
    elif wb == 1:
        lines.append("Bilanciamento del bianco nello scatto: manuale.")
    flash = tags.get(0x9209)
    if isinstance(flash, int):
        if flash & 1:
            lines.append("Flash: scattato.")
        else:
            lines.append("Flash: non scattato.")
    return lines


def load_rgb(path: str):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".bmp":
        try:
            with open(path, "rb") as handle:
                parsed = parse_bmp(handle.read())
            if parsed:
                return parsed
        except Exception:
            log.exception("bmp")
    try:
        import wx

        if wx.GetApp() is not None:
            image = wx.Image(path)
            if image.IsOk() and image.GetWidth() > 0 and image.GetHeight() > 0:
                return bytes(image.GetData()), image.GetWidth(), image.GetHeight()
    except Exception:
        pass
    ff = ffmpeg_exe()
    if not ff:
        return None
    proc = _run([
        ff, "-hide_banner", "-loglevel", "error", "-i", path,
        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "bmp", "pipe:1",
    ], timeout=40)
    if proc.returncode != 0 or not proc.stdout:
        return None
    return parse_bmp(proc.stdout)


def analyze_image_file(path: str) -> dict:
    if not path or not os.path.isfile(path):
        info = _empty_info()
        info["verdict"] = "Il file non c'è più."
        info["lines"] = [info["verdict"]]
        return info
    loaded = load_rgb(path)
    if not loaded:
        info = _empty_info()
        info["verdict"] = MSG_READ_FAIL
        info["lines"] = [MSG_READ_FAIL]
        return info
    rgb, width, height = loaded
    return analyze_rgb(rgb, width, height, exif_lines=read_exif_lines(path))


def _probe_duration(path: str) -> float:
    probe = ffprobe_exe()
    if not probe:
        return 0.0
    proc = _run([
        probe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ], timeout=20)
    try:
        return max(0.0, float((proc.stdout or b"").decode("utf-8", "replace").strip() or 0))
    except Exception:
        return 0.0


def _has_audio_stream(path: str) -> bool:
    probe = ffprobe_exe()
    if not probe:
        return False
    proc = _run([
        probe, "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=codec_type", "-of", "csv=p=0", path,
    ], timeout=20)
    text = (proc.stdout or b"").decode("utf-8", "replace").strip()
    return "audio" in text.lower()


def _volume_db(path: str):
    ff = ffmpeg_exe()
    if not ff:
        return None, None
    proc = _run([
        ff, "-hide_banner", "-i", path, "-af", "volumedetect",
        "-f", "null", "-",
    ], timeout=60)
    text = (proc.stderr or b"").decode("utf-8", "replace")
    mean_db = None
    max_db = None
    for line in text.splitlines():
        if "mean_volume:" in line:
            try:
                mean_db = float(line.split("mean_volume:")[1].split("dB")[0].strip())
            except Exception:
                pass
        if "max_volume:" in line:
            try:
                max_db = float(line.split("max_volume:")[1].split("dB")[0].strip())
            except Exception:
                pass
    return mean_db, max_db


def _grab_video_frame(path: str, second: float, size: int = 160):
    ff = ffmpeg_exe()
    if not ff:
        return None
    proc = _run([
        ff, "-hide_banner", "-loglevel", "error",
        "-ss", f"{max(0.0, second):.3f}", "-i", path,
        "-frames:v", "1", "-vf", f"scale={size}:-2",
        "-f", "image2pipe", "-vcodec", "bmp", "pipe:1",
    ], timeout=30)
    if not proc.stdout:
        return None
    return parse_bmp(proc.stdout)


def analyze_video_file(path: str) -> dict:
    if not path or not os.path.isfile(path):
        info = _empty_info()
        info["verdict"] = "Il file non c'è più."
        info["lines"] = [info["verdict"]]
        return info
    if not ffmpeg_exe():
        info = _empty_info()
        info["verdict"] = "Per questo formato serve ffmpeg."
        info["lines"] = [info["verdict"]]
        return info
    duration = _probe_duration(path)
    if duration <= 0.05:
        duration = 0.4
    marks = [0.0, duration * 0.25, duration * 0.5, duration * 0.75, max(0.0, duration - 0.12)]
    times = []
    for mark in marks:
        if all(abs(mark - old) > 0.08 for old in times):
            times.append(mark)
    frames = []
    infos = []
    for mark in times:
        grabbed = _grab_video_frame(path, mark)
        if not grabbed:
            continue
        rgb, width, height = grabbed
        frames.append(rgb)
        infos.append((mark, analyze_rgb(rgb, width, height)))
    if not infos:
        info = _empty_info()
        info["verdict"] = MSG_VIDEO_FAIL
        info["lines"] = [MSG_VIDEO_FAIL]
        return info
    motions = []
    for left, right in zip(frames, frames[1:]):
        if len(left) == len(right):
            sample = infos[0][1]
            motions.append(mean_abs_diff(left, right, sample["width"], sample["height"]))
    if not motions:
        motion = "ferma"
    else:
        ordered = sorted(motions)
        motion = motion_label(ordered[len(ordered) // 2])
    levels = [item[1]["light_value"] for item in infos]
    flicker = flicker_from_levels(levels)
    has_audio = _has_audio_stream(path)
    if has_audio:
        mean_db, max_db = _volume_db(path)
        audio = classify_volume(mean_db, max_db, True)
    else:
        audio = "muto"
    base = dict(infos[len(infos) // 2][1])
    # Nitidezza: se l'inizio è nitido e la fine no, dillo.
    early = infos[0][1]["sharp"]
    late = infos[-1][1]["sharp"]
    became_soft = early == "nitido" and late == "sfocato"
    light_early = infos[0][1]["light_value"]
    light_late = infos[-1][1]["light_value"]
    drop_at = None
    if not flicker and light_late <= light_early - 12:
        for mark, item in infos:
            if item["light_value"] <= light_early - 12:
                drop_at = mark
                break
    rise_at = None
    if not flicker and light_late >= light_early + 12:
        for mark, item in infos:
            if item["light_value"] >= light_early + 12:
                rise_at = mark
                break
    merged = with_live(base, motion=motion, audio=audio, flicker=flicker)
    # Il giudizio del video racconta l'arco, non un solo fotogramma.
    majority_light = _majority([item["light"] for _, item in infos])
    majority_sharp = _majority([item["sharp"] for _, item in infos])
    bits = []
    bits.append({
        "assente": "non si vede niente",
        "scarsa": "luce scarsa",
        "giusta": "luce giusta",
        "troppa": "troppa luce",
        "bruciata": "luce bruciata",
        "controluce": "controluce",
    }.get(majority_light, "luce"))
    bits.append({
        "sfocato": "sfocato",
        "morbido": "poco nitido",
        "nitido": "nitido",
    }.get(majority_sharp, "nitidezza"))
    bits.append(motion)
    sentence = "Per quasi tutto il video: " + ", ".join(bits) + "."
    extras = []
    if flicker:
        extras.append("La luce sfarfalla.")
    elif drop_at is not None:
        extras.append(f"{_moment(drop_at, duration)} la luce cala.")
    elif rise_at is not None:
        extras.append(f"{_moment(rise_at, duration)} la luce sale.")
    if became_soft:
        extras.append("È diventato sfocato.")
    extras.append({
        "muto": "Video muto.",
        "silenzio": "Audio: silenzio.",
        "basso": "Audio: basso.",
        "giusto": "Audio: giusto.",
        "troppo alto": "Audio: troppo alto.",
        "saturo": "Audio: saturo.",
        "sconosciuto": "Audio: non misurato.",
    }.get(audio, ""))
    merged["verdict"] = " ".join([sentence] + [item for item in extras if item])
    if merged["verdict"] not in merged["lines"]:
        merged["lines"] = [merged["verdict"]] + [
            line for line in merged["lines"] if line != merged["verdict"]
        ]
    merged["duration"] = duration
    return merged


def _majority(values: list) -> str:
    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    best = ""
    best_n = -1
    for value, count in counts.items():
        if count > best_n:
            best = value
            best_n = count
    return best


def _moment(second: float, duration: float) -> str:
    second = max(0.0, second)
    if duration >= 60 or second >= 60:
        minute = int(second // 60)
        if minute <= 0:
            minute = 1
        return f"Dal minuto {minute}"
    whole = int(round(second))
    return f"Dal secondo {whole}"


def capture_work_dir() -> str:
    """La ripresa si scrive qui, non in OneDrive: il cloud, toccando il file, taglia la voce."""
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP") or "."
    folder = os.path.join(root, "RTAD", "riprese")
    os.makedirs(folder, exist_ok=True)
    return folder


def unique_file(folder: str, base: str, ext: str) -> str:
    os.makedirs(folder, exist_ok=True)
    ext = ext if ext.startswith(".") else f".{ext}"
    clean = _safe_stem(base) or "Scatto"
    candidate = os.path.join(folder, clean + ext)
    if not os.path.exists(candidate):
        return candidate
    number = 2
    while True:
        candidate = os.path.join(folder, f"{clean}-{number}{ext}")
        if not os.path.exists(candidate):
            return candidate
        number += 1


def capture_base(stem: str, kind: str) -> str:
    """kind: scatto o ripresa. Senza un nome: Scatto / Ripresa."""
    stem = _safe_stem(stem)
    if not stem:
        return "Scatto" if kind == "scatto" else "Ripresa"
    return f"{stem}-{kind}"


def _safe_stem(text: str) -> str:
    raw = (text or "").strip()
    for char in '<>:"/\\|?*':
        raw = raw.replace(char, " ")
    raw = " ".join(raw.split())
    return raw[:80].strip(" .")


def _prefs_path() -> str:
    root = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "RTAD")
    try:
        os.makedirs(root, exist_ok=True)
    except OSError:
        return ""
    return os.path.join(root, "ripresa.txt")


def load_ripresa_prefs() -> dict:
    path = _prefs_path()
    found = {"folder": "", "mic": ""}
    if not path:
        return found
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key in found:
                    found[key] = value
    except OSError:
        return found
    if found["folder"] and not os.path.isdir(found["folder"]):
        found["folder"] = ""
    return found


def save_ripresa_prefs(folder: str = "", mic: str = "") -> None:
    path = _prefs_path()
    if not path:
        return
    current = load_ripresa_prefs()
    if folder:
        current["folder"] = folder
    if mic:
        current["mic"] = mic
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(f"folder={current['folder']}\nmic={current['mic']}\n")
    except OSError:
        pass


def usable_microphones(audio_names: list) -> list:
    return [
        name for name in audio_names
        if "missaggio" not in name.lower() and "stereo mix" not in name.lower()
    ]


def default_capture_dir() -> str:
    home = os.path.expanduser("~")
    documents = os.path.join(home, "Documents", "RTAD")
    try:
        os.makedirs(documents, exist_ok=True)
        return documents
    except Exception:
        pass
    desktop = os.path.join(home, "Desktop")
    if os.path.isdir(desktop):
        return desktop
    return home


def write_report_beside(media_path: str, info: dict) -> str:
    folder = os.path.dirname(media_path)
    stem = os.path.splitext(os.path.basename(media_path))[0]
    path = os.path.join(folder, stem + ".txt")
    text = report_text(info)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
    return path


def control_line(ctrl: dict) -> str:
    name = ctrl.get("name") or "Parametro"
    if not ctrl.get("delivered"):
        article = ctrl.get("article") or name.lower()
        return f"{name}: questa fotocamera non consegna {article}."
    unit = ctrl.get("unit") or ""
    span = f"da {ctrl.get('min')} a {ctrl.get('max')}"
    if ctrl.get("auto"):
        return f"{name}: automatico, {ctrl.get('value')}{unit}, {span}."
    line = f"{name}: {ctrl.get('value')}{unit}, {span}."
    if ctrl.get("value") == ctrl.get("default"):
        line = line[:-1] + ". È il valore di partenza."
    return line


def missing_phrase(ctrl: dict) -> str:
    article = ctrl.get("article") or "questo parametro"
    return f"Questa fotocamera non consegna {article}."


# --- DirectShow: solo i parametri che il driver consegna davvero. ---

class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", c_ulong),
        ("Data2", c_ushort),
        ("Data3", c_ushort),
        ("Data4", c_ubyte * 8),
    ]


class _VARIANT(ctypes.Structure):
    _fields_ = [
        ("vt", c_ushort),
        ("r1", c_ushort),
        ("r2", c_ushort),
        ("r3", c_ushort),
        ("ll", c_ulonglong),
        ("rest", c_ulonglong),
    ]


def _guid(text: str) -> _GUID:
    value = uuid.UUID(text)
    item = _GUID()
    ctypes.memmove(byref(item), value.bytes_le, 16)
    return item


def _method(ptr, index, restype, argtypes):
    table = ctypes.cast(ptr, POINTER(POINTER(c_void_p))).contents
    proto = WINFUNCTYPE(restype, c_void_p, *argtypes)
    return proto(table[index])


def _release(ptr) -> None:
    if ptr:
        try:
            _method(ptr, 2, c_ulong, [])(ptr)
        except Exception:
            pass


class _DeviceBinder:
    """Apre un attimo il driver, legge o scrive, poi lo lascia."""

    def __init__(self):
        self._ole32 = ctypes.WinDLL("ole32")
        self._oleaut = ctypes.WinDLL("oleaut32")
        self._ole32.CoInitialize.argtypes = [c_void_p]
        self._ole32.CoInitialize.restype = c_long
        self._ole32.CoUninitialize.argtypes = []
        self._ole32.CoCreateInstance.argtypes = [
            POINTER(_GUID), c_void_p, c_ulong, POINTER(_GUID), POINTER(c_void_p),
        ]
        self._ole32.CoCreateInstance.restype = c_long
        self._oleaut.VariantClear.argtypes = [POINTER(_VARIANT)]
        self._oleaut.SysStringLen.argtypes = [c_void_p]
        self._oleaut.SysStringLen.restype = c_ulong
        self._started = False

    def __enter__(self):
        hr = self._ole32.CoInitialize(None)
        self._started = hr in (0, 1)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._started:
            self._ole32.CoUninitialize()
        return False

    def _enum(self):
        device = c_void_p()
        hr = self._ole32.CoCreateInstance(
            byref(_guid("62BE5D10-60EB-11d0-BD3B-00A0C911CE86")),
            None,
            1,
            byref(_guid("29840822-5B84-11D0-BD3B-00A0C911CE86")),
            byref(device),
        )
        if hr != 0 or not device.value:
            return None, None
        enum = c_void_p()
        hr = _method(device, 3, c_long, [POINTER(_GUID), POINTER(c_void_p), c_ulong])(
            device,
            byref(_guid("860BB310-5D01-11d0-BD3B-00A0C911CE86")),
            byref(enum),
            0,
        )
        if hr != 0 or not enum.value:
            _release(device)
            return None, None
        return device, enum

    def for_each(self, callback):
        device, enum = self._enum()
        if not enum:
            return
        try:
            while True:
                moniker = c_void_p()
                fetched = c_ulong()
                hr = _method(enum, 3, c_long, [c_ulong, POINTER(c_void_p), POINTER(c_ulong)])(
                    enum, 1, byref(moniker), byref(fetched),
                )
                if hr != 0:
                    break
                name = self._friendly(moniker)
                try:
                    callback(name, moniker)
                finally:
                    _release(moniker)
        finally:
            _release(enum)
            _release(device)

    def _friendly(self, moniker) -> str:
        bag = c_void_p()
        hr = _method(moniker, 9, c_long, [c_void_p, c_void_p, POINTER(_GUID), POINTER(c_void_p)])(
            moniker, None, None,
            byref(_guid("55272A00-42CB-11CE-8135-00AA004BB851")),
            byref(bag),
        )
        if hr != 0 or not bag.value:
            return ""
        var = _VARIANT()
        try:
            hr = _method(bag, 3, c_long, [c_wchar_p, POINTER(_VARIANT), c_void_p])(
                bag, "FriendlyName", byref(var), None,
            )
            if hr != 0 or var.vt != 8 or not var.ll:
                return ""
            length = self._oleaut.SysStringLen(c_void_p(var.ll))
            return ctypes.wstring_at(var.ll, length)
        finally:
            self._oleaut.VariantClear(byref(var))
            _release(bag)

    def bind_filter(self, moniker):
        filt = c_void_p()
        hr = _method(moniker, 8, c_long, [c_void_p, c_void_p, POINTER(_GUID), POINTER(c_void_p)])(
            moniker, None, None,
            byref(_guid("56a86895-0ad4-11ce-b03a-0020af0ba770")),
            byref(filt),
        )
        if hr != 0 or not filt.value:
            return None
        return filt


def _qi(ptr, iid: str):
    out = c_void_p()
    hr = _method(ptr, 0, c_long, [POINTER(_GUID), POINTER(c_void_p)])(
        ptr, byref(_guid(iid)), byref(out),
    )
    if hr != 0 or not out.value:
        return None
    return out


_AMP_IID = "C6E13360-30AC-11d0-A18C-00A0C9118956"
_CAM_IID = "C6E13370-30AC-11d0-A18C-00A0C9118956"


def _read_prop(ptr, prop: int):
    mn = c_long()
    mx = c_long()
    step = c_long()
    default = c_long()
    caps = c_long()
    hr = _method(
        ptr, 3, c_long,
        [c_long, POINTER(c_long), POINTER(c_long), POINTER(c_long), POINTER(c_long), POINTER(c_long)],
    )(ptr, prop, byref(mn), byref(mx), byref(step), byref(default), byref(caps))
    if hr != 0:
        return None
    value = c_long()
    flags = c_long()
    hr = _method(ptr, 5, c_long, [c_long, POINTER(c_long), POINTER(c_long)])(
        ptr, prop, byref(value), byref(flags),
    )
    if hr != 0:
        return None
    return {
        "min": int(mn.value),
        "max": int(mx.value),
        "step": int(step.value) or 1,
        "default": int(default.value),
        "caps": int(caps.value),
        "value": int(value.value),
        "flags": int(flags.value),
    }


def _set_prop(ptr, prop: int, value: int, flags: int) -> bool:
    hr = _method(ptr, 4, c_long, [c_long, c_long, c_long])(ptr, int(prop), int(value), int(flags))
    return hr == 0


def read_camera_controls(device_name: str) -> list:
    """Elenco parlato. Se il driver non ha il parametro, la riga lo dice."""
    snap = {}
    try:
        with _DeviceBinder() as binder:
            found = {}

            def visit(name, moniker):
                if name != device_name or "snap" in found:
                    return
                filt = binder.bind_filter(moniker)
                if not filt:
                    return
                amp = None
                cam = None
                try:
                    amp = _qi(filt, _AMP_IID)
                    cam = _qi(filt, _CAM_IID)
                    snapshot = {}
                    if amp:
                        for spec in _CORE_CONTROLS:
                            if spec[2] == "amp":
                                snapshot[("amp", spec[3])] = _read_prop(amp, spec[3])
                    if cam:
                        for spec in _CORE_CONTROLS:
                            if spec[2] == "cam":
                                snapshot[("cam", spec[3])] = _read_prop(cam, spec[3])
                    found["snap"] = snapshot
                finally:
                    _release(amp)
                    _release(cam)
                    _release(filt)

            binder.for_each(visit)
            snap = found.get("snap") or {}
    except Exception:
        log.exception("read_camera_controls")
        snap = {}
    rows = []
    for name, article, iface, prop, unit, always in _CORE_CONTROLS:
        got = snap.get((iface, prop))
        if not got:
            if always:
                rows.append({
                    "name": name,
                    "article": article,
                    "iface": iface,
                    "prop": prop,
                    "unit": unit,
                    "delivered": False,
                })
            continue
        rows.append({
            "name": name,
            "article": article,
            "iface": iface,
            "prop": prop,
            "unit": unit,
            "delivered": True,
            "min": got["min"],
            "max": got["max"],
            "step": got["step"] or 1,
            "caps": got["caps"],
            "value": got["value"],
            "default": got["default"],
            "auto": bool(got["flags"] & _AUTO_FLAG) and bool(got["caps"] & _AUTO_FLAG),
            "manual_ok": bool(got["caps"] & _MANUAL_FLAG),
            "auto_ok": bool(got["caps"] & _AUTO_FLAG),
        })
    return rows


def adjust_camera_control(device_name: str, ctrl: dict, delta) -> tuple:
    """delta +1, -1, oppure 'auto'. Ritorna (controllo, frase)."""
    if not ctrl.get("delivered"):
        return ctrl, missing_phrase(ctrl)
    if delta == "auto":
        if not ctrl.get("auto_ok"):
            return ctrl, MSG_FIXED
        ok = _apply(device_name, ctrl, int(ctrl.get("value") or 0), _AUTO_FLAG)
        if not ok:
            return ctrl, MSG_FIXED
        nxt = dict(ctrl)
        nxt["auto"] = True
        return nxt, control_line(nxt)
    if not ctrl.get("manual_ok", True):
        return ctrl, MSG_FIXED
    step = int(ctrl.get("step") or 1)
    new_value = int(ctrl.get("value") or 0) + int(delta) * step
    if new_value > int(ctrl.get("max")):
        return ctrl, MSG_AT_MAX
    if new_value < int(ctrl.get("min")):
        return ctrl, MSG_AT_MIN
    if new_value == int(ctrl.get("value") or 0) and not ctrl.get("auto"):
        return ctrl, MSG_FIXED
    ok = _apply(device_name, ctrl, new_value, _MANUAL_FLAG)
    if not ok:
        return ctrl, MSG_FIXED
    nxt = dict(ctrl)
    nxt["value"] = new_value
    nxt["auto"] = False
    return nxt, control_line(nxt)


def _apply(device_name: str, ctrl: dict, value: int, flags: int) -> bool:
    ok = {"value": False}
    try:
        with _DeviceBinder() as binder:

            def visit(name, moniker):
                if name != device_name or ok["value"]:
                    return
                filt = binder.bind_filter(moniker)
                if not filt:
                    return
                ptr = None
                try:
                    iid = _AMP_IID if ctrl.get("iface") == "amp" else _CAM_IID
                    ptr = _qi(filt, iid)
                    if ptr and _set_prop(ptr, int(ctrl["prop"]), value, flags):
                        ok["value"] = True
                finally:
                    _release(ptr)
                    _release(filt)

            binder.for_each(visit)
    except Exception:
        log.exception("adjust control")
        return False
    return bool(ok["value"])


def list_dshow_devices() -> tuple:
    """(video, audio) dai nomi che ffmpeg riesce ad aprire."""
    ff = ffmpeg_exe()
    if not ff:
        return [], []
    proc = _run([
        ff, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy",
    ], timeout=15)
    text = (proc.stderr or b"").decode("utf-8", "replace")
    if not text.strip():
        text = (proc.stdout or b"").decode("utf-8", "replace")
    video = []
    audio = []
    section = ""
    for line in text.splitlines():
        lower = line.lower()
        if "video devices" in lower:
            section = "video"
            continue
        if "audio devices" in lower:
            section = "audio"
            continue
        if "alternative name" in lower or '"' not in line:
            continue
        name = line.split('"', 2)[1].strip()
        if not name:
            continue
        kind = ""
        if "(video)" in lower:
            kind = "video"
        elif "(audio)" in lower:
            kind = "audio"
        elif section in ("video", "audio"):
            kind = section
        if kind == "video" and name not in video:
            video.append(name)
        elif kind == "audio" and name not in audio:
            audio.append(name)
    return video, audio


MIC_NONE = "Nessun microfono"


def same_capture_device(camera: str, mic: str) -> bool:
    """Il microfono della fotocamera sta nello stesso ingresso del video."""
    token = (camera or "").split()
    if not token or not mic or mic == MIC_NONE:
        return False
    key = token[0].lower()
    return len(key) >= 3 and key in mic.lower()


def build_audio_command(ff: str, mic: str, dest: str) -> list:
    """Solo il microfono, in un processo a parte: il video non lo fa saltare."""
    return [
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "dshow",
        "-rtbufsize", "64M",
        "-thread_queue_size", "2048",
        "-audio_buffer_size", "1000",
        "-i", f"audio={mic}",
        "-ac", "1", "-ar", "48000",
        "-c:a", "pcm_s16le",
        dest,
    ]


def attach_audio(ff: str, video_path: str, wav_path: str) -> bool:
    """Unisce il sonoro al video già chiuso, una volta sola."""
    if not ff or not os.path.isfile(video_path) or not os.path.isfile(wav_path):
        return False
    if os.path.getsize(wav_path) < 1000:
        return False
    dest = video_path + ".mux.mp4"
    proc = _run([
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-i", video_path, "-i", wav_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "160k",
        "-af", "alimiter=limit=0.85:level=0",
        "-shortest", dest,
    ], timeout=180)
    if proc.returncode != 0 or not os.path.isfile(dest) or os.path.getsize(dest) < 1000:
        try:
            os.remove(dest)
        except OSError:
            pass
        return False
    os.replace(dest, video_path)
    return True


def build_record_command(ff: str, camera: str, mic: str, dest: str) -> list:
    """File più anteprima. Il microfono esterno non entra qui: ha un processo suo."""
    mic_name = mic if mic and mic != MIC_NONE and same_capture_device(camera, mic) else ""
    preview = [
        "-map", "0:v", "-an",
        "-vf", f"scale={_PREVIEW_W}:{_PREVIEW_H},fps=6",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
    ]
    head = [ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "dshow", "-rtbufsize", "256M"]
    if mic_name:
        head += [
            "-use_wallclock_as_timestamps", "1",
            "-thread_queue_size", "1024",
            "-audio_buffer_size", "250",
            "-i", f"video={camera}:audio={mic_name}",
            "-map", "0:v", "-map", "0:a",
            "-c:a", "aac", "-b:a", "128k",
            "-af", "aresample=async=1:first_pts=0,alimiter=limit=0.85:level=0",
        ]
    else:
        head += [
            "-use_wallclock_as_timestamps", "1",
            "-thread_queue_size", "1024",
            "-i", f"video={camera}",
            "-map", "0:v", "-an",
            "-fps_mode", "cfr", "-r", "30",
        ]
    head += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", dest]
    head += preview
    return head


def choose_microphone(video_name: str, audio_names: list, remembered: str = "") -> str:
    if remembered and remembered in audio_names:
        return remembered
    usable = usable_microphones(audio_names)
    pool = usable or list(audio_names)
    if not pool:
        return ""
    key = (video_name or "").split()[0].lower()
    for name in pool:
        if key and key in name.lower():
            return name
    return pool[0]


def _busy_text(blob: str) -> bool:
    lower = (blob or "").lower()
    marks = (
        "busy", "in use", "being used", "device is",
        "0x80070020", "0x8007001f", "could not renderstream",
    )
    return any(mark in lower for mark in marks)


def capture_still(device_name: str, dest: str) -> tuple:
    """(ok, messaggio)."""
    ff = ffmpeg_exe()
    if not ff:
        return False, MSG_NEED_FFMPEG
    proc = _run([
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "dshow", "-i", f"video={device_name}",
        "-frames:v", "1", "-q:v", "3", dest,
    ], timeout=12)
    err = (proc.stderr or b"").decode("utf-8", "replace")
    if proc.returncode == 0 and os.path.isfile(dest) and os.path.getsize(dest) > 0:
        return True, ""
    if _busy_text(err):
        return False, MSG_CAMERA_BUSY
    return False, MSG_PHOTO_FAIL


def measure_microphone(device_name: str, seconds: float = 0.45) -> str:
    ff = ffmpeg_exe()
    if not ff or not device_name:
        return "sconosciuto"
    proc = _run([
        ff, "-hide_banner", "-f", "dshow", "-i", f"audio={device_name}",
        "-t", f"{seconds:.2f}", "-af", "volumedetect", "-f", "null", "-",
    ], timeout=8)
    text = (proc.stderr or b"").decode("utf-8", "replace")
    if _busy_text(text):
        return "sconosciuto"
    mean_db = None
    max_db = None
    for line in text.splitlines():
        if "mean_volume:" in line:
            try:
                mean_db = float(line.split("mean_volume:")[1].split("dB")[0].strip())
            except Exception:
                pass
        if "max_volume:" in line:
            try:
                max_db = float(line.split("max_volume:")[1].split("dB")[0].strip())
            except Exception:
                pass
    if mean_db is None and max_db is None:
        return "sconosciuto"
    return classify_volume(mean_db, max_db, True)


def file_kind(path: str) -> str:
    ext = os.path.splitext(path or "")[1].lower()
    if ext in _IMAGE_EXTS:
        return "image"
    if ext in _VIDEO_EXTS:
        return "video"
    if ext in _AUDIO_EXTS:
        return "audio"
    return ""


def open_file_report(parent, speaker, path: str) -> None:
    speaker = speaker or (lambda _text: None)
    ext = os.path.splitext(path or "")[1].lower()
    if ext in _AUDIO_EXTS:
        speaker(MSG_NOT_MEDIA)
        return
    if ext in _VIDEO_EXTS:
        speaker(MSG_READING_VIDEO)

        def work():
            info = analyze_video_file(path)
            try:
                import wx
                wx.CallAfter(_present_report, parent, speaker, "Com'è questo video", info)
            except Exception:
                speaker(report_text(info).replace("\n", " "))

        threading.Thread(target=work, daemon=True).start()
        return
    info = analyze_image_file(path)
    _present_report(parent, speaker, "Com'è questa foto", info)


def _present_report(parent, speaker, title: str, info: dict) -> None:
    text = report_text(info)
    verdict = (info.get("verdict") or text.split("\n", 1)[0]).strip()
    speaker(f"{title}. {verdict} Il resto è nel riquadro. Frecce per leggere.")
    try:
        import wx
    except Exception:
        return
    dialog = wx.Dialog(parent, title=title, size=(720, 520), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    panel = wx.Panel(dialog)
    box = wx.BoxSizer(wx.VERTICAL)
    field = wx.TextCtrl(panel, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY)
    try:
        field.SetName("Giudizio")
    except Exception:
        pass
    box.Add(field, 1, wx.EXPAND | wx.ALL, 8)
    close = wx.Button(panel, wx.ID_CANCEL, "Chiudi (ESC)")
    box.Add(close, 0, wx.ALIGN_CENTER | wx.ALL, 6)
    panel.SetSizer(box)
    dialog.Centre()
    field.SetFocus()
    dialog.ShowModal()
    dialog.Destroy()


def open_camera(parent, speaker, folder: str = "") -> None:
    speaker = speaker or (lambda _text: None)
    if not ffmpeg_exe():
        speaker(MSG_NEED_FFMPEG)
        try:
            import wx
            wx.MessageBox(MSG_NEED_FFMPEG, "Fotocamera", wx.OK | wx.ICON_INFORMATION)
        except Exception:
            pass
        return
    videos, audios = list_dshow_devices()
    if not videos:
        speaker(MSG_NO_CAMERA)
        try:
            import wx
            wx.MessageBox(MSG_NO_CAMERA, "Fotocamera", wx.OK | wx.ICON_INFORMATION)
        except Exception:
            pass
        return
    try:
        import wx
    except Exception as exc:
        speaker(f"Fotocamera non disponibile: {exc}")
        return
    prefs = load_ripresa_prefs()
    dialog = _CameraDialog(
        parent, speaker, videos, audios,
        folder or prefs.get("folder") or default_capture_dir(),
        prefs.get("mic") or "",
    )
    try:
        dialog.ShowModal()
    finally:
        dialog.close_work()
        dialog.Destroy()


class _CameraDialog:
    """Costruita come wx.Dialog solo quando la finestra si apre."""

    def __new__(cls, parent, speaker, videos, audios, folder, remembered_mic=""):
        import wx

        class Dialog(wx.Dialog):
            def __init__(self):
                super().__init__(
                    parent, title="Fotocamera", size=(760, 680),
                    style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                )
                self.speaker = speaker
                self.videos = list(videos)
                self.audios = list(audios)
                self.folder = folder
                self.device = self.videos[0]
                self._mics = [MIC_NONE] + [name for name in self.audios if name]
                self._param_timer = None
                self._param_index = -1
                if remembered_mic == MIC_NONE:
                    self.mic = ""
                else:
                    self.mic = choose_microphone(self.device, self.audios, remembered_mic)
                self._face_hold = 0
                self._face_keep = {}
                self._hband = ""
                self._vband = ""
                self._shband = ""
                self._svband = ""
                self._subh = ""
                self._subv = ""
                self._frame_said = ""
                self._phrase_hold = ""
                self._phrase_n = 0
                self._cx_s = None
                self._cy_s = None
                self._as_s = None
                self._live_phrase = None
                self._record_audio = None
                self._record_wav = ""
                self._record_final = ""
                self._quiet = False
                self._pend_key = None
                self._pend_n = 0
                self._heard_key = None
                self.controls = []
                self._stop = threading.Event()
                self._preview = None
                self._record = None
                self._lock = threading.Lock()
                self._last = None
                self._prev_rgb = b""
                self._levels = []
                self._audio = "attesa"
                self._on = False
                self._recording = False
                self._closed = False
                self._intentional = False
                self._audio_started = False
                self._last_spoken = ""
                panel = wx.Panel(self)
                root = wx.BoxSizer(wx.VERTICAL)
                self.status = wx.TextCtrl(panel, value="", style=wx.TE_READONLY)
                try:
                    self.status.SetName("Stato")
                except Exception:
                    pass
                root.Add(self.status, 0, wx.EXPAND | wx.ALL, 8)
                self.measures = wx.ListBox(panel)
                try:
                    self.measures.SetName("Misure")
                except Exception:
                    pass
                self.measures.Bind(wx.EVT_SET_FOCUS, self._enter_quiet)
                self.measures.Bind(wx.EVT_LISTBOX, self._on_measure)
                root.Add(self.measures, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
                if len(self.videos) > 1:
                    self.combo = wx.Choice(panel, choices=self.videos)
                    self.combo.SetSelection(0)
                    try:
                        self.combo.SetName("Fotocamera")
                    except Exception:
                        pass
                    self.combo.Bind(wx.EVT_CHOICE, self._on_choice)
                    root.Add(self.combo, 0, wx.EXPAND | wx.ALL, 8)
                else:
                    self.combo = None
                if self._mics:
                    self.mic_choice = wx.Choice(panel, choices=self._mics)
                    try:
                        selected = MIC_NONE if not self.mic else self.mic
                        self.mic_choice.SetSelection(max(0, self._mics.index(selected)))
                    except ValueError:
                        self.mic_choice.SetSelection(0)
                    try:
                        self.mic_choice.SetName("Microfono")
                    except Exception:
                        pass
                    self.mic_choice.Bind(wx.EVT_CHOICE, self._on_mic)
                    root.Add(self.mic_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
                else:
                    self.mic_choice = None
                self.params = wx.ListBox(panel)
                try:
                    self.params.SetName("Parametri")
                except Exception:
                    pass
                self.params.Bind(wx.EVT_SET_FOCUS, self._enter_quiet)
                root.Add(self.params, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
                buttons = wx.BoxSizer(wx.HORIZONTAL)
                self.btn_power = wx.Button(panel, label="Spe&gni")
                self.btn_now = wx.Button(panel, label="Com'è &ora")
                self.btn_now.Bind(wx.EVT_SET_FOCUS, self._enter_position)
                self.btn_shot = wx.Button(panel, label="&Scatta")
                self.btn_rec = wx.Button(panel, label="Registra &video")
                self.btn_dir = wx.Button(panel, label="&Cartella")
                self.btn_close = wx.Button(panel, wx.ID_CANCEL, "Chiudi (ESC)")
                for button, handler in (
                    (self.btn_power, self._on_power),
                    (self.btn_now, self._on_now),
                    (self.btn_shot, self._on_shot),
                    (self.btn_rec, self._on_rec),
                    (self.btn_dir, self._on_dir),
                ):
                    button.Bind(wx.EVT_BUTTON, handler)
                    buttons.Add(button, 0, wx.ALL, 4)
                buttons.Add(self.btn_close, 0, wx.ALL, 4)
                root.Add(buttons, 0, wx.ALIGN_CENTER | wx.TOP, 6)
                self.chk_sound = wx.CheckBox(panel, label="Suono quando è &pronto")
                self.chk_sound.SetValue(True)
                root.Add(self.chk_sound, 0, wx.ALL, 8)
                panel.SetSizer(root)
                self.Bind(wx.EVT_CHAR_HOOK, self._on_key)
                self.Bind(wx.EVT_CLOSE, self._on_close)
                self.Centre()
                mic_phrase = self.mic or "nessun microfono"
                intro = (
                    f"Fotocamera. {self.device}. "
                    f"Microfono: {mic_phrase}. "
                    "Nell'elenco Microfono ci sono i dispositivi, il missaggio stereo e Nessun microfono. "
                    "Nessun microfono lascia il video in silenzio. "
                    "Freccia su e giù. "
                    "La mano parla solo mentre questa finestra è davanti. "
                    "Alt+S scatta. Alt+G spegne. Alt+A accende. Alt+V registra e ferma. "
                    "Alt+P è il suono quando è pronto. "
                    "Il suono arriva quando luce, nitidezza e il soggetto al centro vanno bene insieme. "
                    "La voce della posizione parla mentre sei su Com'è ora. "
                    "Dice dove sta il volto e dove spostarti. "
                    "Appena entri in Misure o in Parametri, quella voce si ferma e resta ferma, "
                    "anche se ti muovi e anche se la finestra va dietro. "
                    "Per riascoltarla, torna su Com'è ora con Alt+O. "
                    "Ogni riga parla solo con la freccia o con Alt e il numero. "
                    "Alt+1 è la verifica totale, Alt+2 la riga sotto, e così via. "
                    "Spazio rilegge tutto. "
                    "Sui Parametri, freccia destra alza e freccia sinistra abbassa, "
                    "e dice il valore a ogni freccia. "
                    "Inizio rimette l'automatico, se c'è. "
                    f"Cartella: {self.folder}."
                )
                self.speaker(intro)
                self.status.SetValue(intro)
                wx.CallLater(200, self._start)
                self.btn_now.SetFocus()

            def _say(self, text: str, live: bool = False, replace: bool = False) -> None:
                text = (text or "").strip()
                if not text:
                    return
                if live and not self._foreground():
                    return
                try:
                    self.status.SetValue(text)
                except Exception:
                    pass
                if text == self._last_spoken:
                    return
                self._last_spoken = text
                if replace:
                    try:
                        self.speaker(text, replace=True)
                        return
                    except TypeError:
                        pass
                self.speaker(text)

            def _foreground(self) -> bool:
                try:
                    return bool(self.IsShown() and not self.IsIconized() and self.IsActive())
                except Exception:
                    return False

            def _beep(self) -> None:
                if not self._foreground():
                    return
                if not self.chk_sound.GetValue():
                    return
                try:
                    import winsound
                    winsound.Beep(880, 120)
                except Exception:
                    pass

            def _fill_measures(self, info: dict) -> None:
                lines = []
                verdict = info.get("verdict") or ""
                if verdict:
                    lines.append(verdict)
                for line in info.get("lines") or []:
                    if line not in lines:
                        lines.append(line)
                current = []
                try:
                    current = [self.measures.GetString(i) for i in range(self.measures.GetCount())]
                except Exception:
                    current = []
                if current == lines:
                    return
                if current and len(current) == len(lines):
                    for index, line in enumerate(lines):
                        if current[index] != line:
                            self.measures.SetString(index, line)
                    return
                sel = self.measures.GetSelection()
                self.measures.Set(lines)
                if lines:
                    if sel < 0 or sel >= len(lines):
                        sel = 0
                    self.measures.SetSelection(sel)

            def _fill_params(self) -> None:
                sel = self.params.GetSelection()
                rows = [control_line(ctrl) for ctrl in self.controls]
                self.params.Set(rows or ["Nessun parametro letto."])
                if rows:
                    if sel < 0 or sel >= len(rows):
                        sel = 0
                    self.params.SetSelection(sel)

            def _load_controls(self) -> None:
                self.controls = read_camera_controls(self.device)
                self._fill_params()

            def _start(self) -> None:
                if self._on or self._closed:
                    return
                self._intentional = False
                self._stop.clear()
                self._load_controls()
                self._on = True
                self.btn_power.SetLabel("Spe&gni")
                threading.Thread(target=self._preview_loop, daemon=True).start()
                if not self._audio_started:
                    self._audio_started = True
                    threading.Thread(target=self._audio_loop, daemon=True).start()

            def _stop_preview(self) -> None:
                self._intentional = True
                proc = self._preview
                self._preview = None
                if proc is not None:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    try:
                        proc.wait(timeout=2)
                    except Exception:
                        pass

            def _halt(self) -> None:
                self._stop.set()
                self._on = False
                self._stop_preview()
                self._stop_record(wait=True)
                try:
                    self.btn_power.SetLabel("&Accendi")
                except Exception:
                    pass

            def _resume(self) -> None:
                self._on = False
                self._stop.clear()
                self._start()

            def _preview_loop(self) -> None:
                import wx
                ff = ffmpeg_exe()
                cmd = [
                    ff, "-hide_banner", "-loglevel", "error",
                    "-f", "dshow", "-rtbufsize", "50M",
                    "-i", f"video={self.device}",
                    "-vf", f"scale={_PREVIEW_W}:{_PREVIEW_H},fps=6",
                    "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
                ]
                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.DEVNULL,
                        creationflags=_CREATE_NO_WINDOW,
                    )
                except Exception:
                    wx.CallAfter(self._say, MSG_CAMERA_BUSY)
                    return
                self._preview = proc
                need = _PREVIEW_W * _PREVIEW_H * 3

                def lost(text: str) -> None:
                    if self._intentional or self._stop.is_set() or self._recording or self._closed:
                        return
                    msg = MSG_CAMERA_BUSY if _busy_text(text) else MSG_CAMERA_LOST
                    wx.CallAfter(self._say, msg)

                try:
                    while not self._stop.is_set() and not self._recording:
                        if proc.poll() is not None:
                            err = b""
                            try:
                                err = proc.stderr.read() or b""
                            except Exception:
                                pass
                            lost(err.decode("utf-8", "replace"))
                            return
                        blob = b""
                        while len(blob) < need and not self._stop.is_set():
                            chunk = proc.stdout.read(need - len(blob))
                            if not chunk:
                                lost("")
                                return
                            blob += chunk
                        if self._stop.is_set() or self._recording:
                            break
                        self._on_preview_frame(blob)
                finally:
                    if self._preview is proc:
                        self._preview = None
                    try:
                        proc.kill()
                    except Exception:
                        pass

            def _hold_face(self, info: dict) -> dict:
                keys = (
                    "face_count", "face_place", "face_distance",
                    "face_cropped", "face_crop_side", "headroom",
                    "face_cx", "face_cy", "face_hband", "face_vband", "face_tilt",
                    "shadow", "shadow_place", "shadow_distance",
                    "shadow_cropped", "shadow_crop_side",
                    "shadow_cx", "shadow_cy", "shadow_hband", "shadow_vband",
                    "subject", "subject_place", "subject_distance",
                    "subject_cropped", "subject_crop_side",
                    "subject_cx", "subject_cy",
                )
                if info.get("face_count") or info.get("shadow") or info.get("subject"):
                    self._face_keep = {key: info.get(key) for key in keys}
                    self._face_hold = 2
                    return info
                if self._face_hold > 0 and (
                    self._face_keep.get("face_count") or self._face_keep.get("shadow") or self._face_keep.get("subject")
                ):
                    info = dict(info)
                    info.update(self._face_keep)
                    self._face_hold -= 1
                return info

            def _speech_key(self, live: dict):
                return (
                    live.get("light"), live.get("contrast"), live.get("cast"),
                    live.get("sharp"), live.get("center_soft"),
                    live.get("face_count"), live.get("face_place"),
                    live.get("face_distance"), live.get("face_cropped"),
                    live.get("shadow"), live.get("shadow_place"),
                    live.get("shadow_distance"), live.get("shadow_cropped"),
                    live.get("subject"), live.get("subject_place"),
                    live.get("subject_distance"), live.get("subject_cropped"),
                    live.get("motion"), live.get("audio"), live.get("flicker"),
                    live.get("ready_photo"), live.get("coach"),
                )

            def _steady_place(self, info: dict) -> dict:
                """Una piccola oscillazione non cambia la frase. Uno spostamento vero sì."""
                if info.get("face_count") and info.get("face_cx") is not None:
                    horizontal = _band(info["face_cx"], _H_CUTS, _H_NAMES, self._hband, slack=0.01)
                    if info.get("face_tilt"):
                        vertical = info["face_tilt"]
                    else:
                        vertical = _band(info["face_cy"], _CROWN_CUTS, _V_NAMES, self._vband, slack=0.012)
                    self._hband = horizontal
                    self._vband = vertical
                    place = _join_place(horizontal, vertical)
                    if place != info.get("face_place"):
                        info = dict(info)
                        info["face_place"] = place
                    return info
                if info.get("shadow") and info.get("shadow_cx") is not None:
                    horizontal = _band(info["shadow_cx"], _H_CUTS, _H_NAMES, self._shband)
                    vertical = _band(info["shadow_cy"], _V_CUTS, _V_NAMES, self._svband)
                    self._shband = horizontal
                    self._svband = vertical
                    place = _join_place(horizontal, vertical)
                    if place != info.get("shadow_place"):
                        info = dict(info)
                        info["shadow_place"] = place
                    return info
                if info.get("subject") and info.get("subject_cx") is not None:
                    horizontal = _band(info["subject_cx"], _H_CUTS, _H_NAMES, self._subh)
                    vertical = _band(info["subject_cy"], _V_CUTS, _V_NAMES, self._subv)
                    self._subh = horizontal
                    self._subv = vertical
                    place = _join_place(horizontal, vertical)
                    if place != info.get("subject_place"):
                        info = dict(info)
                        info["subject_place"] = place
                return info

            def _smooth_for_phrase(self, info: dict) -> dict:
                """Il filo non deve cambiare per un pixel del fotogramma."""
                cx = info.get("face_cx")
                cy = info.get("face_cy")
                aspect = info.get("face_aspect") or 0.0
                if not info.get("face_count") or cx is None:
                    self._cx_s = None
                    self._cy_s = None
                    self._as_s = None
                    return info
                if self._cx_s is None:
                    self._cx_s = float(cx)
                    self._cy_s = float(cy or 0.5)
                    self._as_s = float(aspect or 0.0)
                else:
                    self._cx_s = (self._cx_s + float(cx)) / 2.0
                    self._cy_s = (self._cy_s + float(cy or self._cy_s)) / 2.0
                    if aspect:
                        self._as_s = ((self._as_s or float(aspect)) + float(aspect)) / 2.0
                info = dict(info)
                info["face_cx"] = self._cx_s
                info["face_cy"] = self._cy_s
                if self._as_s:
                    info["face_aspect"] = self._as_s
                return info

            def _place_only(self, prev: dict, cur: dict) -> bool:
                place_keys = (
                    "face_count", "face_place", "face_distance", "face_cropped",
                    "shadow", "shadow_place", "shadow_distance", "shadow_cropped",
                    "subject", "subject_place", "subject_distance", "subject_cropped",
                )
                other_keys = (
                    "light", "contrast", "cast", "sharp", "center_soft",
                    "motion", "audio", "flicker",
                )
                moved = any(prev.get(key) != cur.get(key) for key in place_keys)
                other = any(prev.get(key) != cur.get(key) for key in other_keys)
                return moved and not other

            def _on_preview_frame(self, blob: bytes) -> None:
                import wx
                info = self._steady_place(self._hold_face(analyze_rgb(blob, _PREVIEW_W, _PREVIEW_H)))
                motion = ""
                if self._prev_rgb and len(self._prev_rgb) == len(blob):
                    motion = motion_label(mean_abs_diff(self._prev_rgb, blob, _PREVIEW_W, _PREVIEW_H))
                self._prev_rgb = blob
                self._levels.append(info["light_value"])
                self._levels = self._levels[-8:]
                flicker = flicker_from_levels(self._levels)
                live = with_live(info, motion=motion, audio=self._audio, flicker=flicker)
                key = self._speech_key(live)
                if key != self._pend_key:
                    self._pend_key = key
                    self._pend_n = 1
                else:
                    self._pend_n += 1
                speech = ""
                became = False
                first = self._last is None
                if first or (key != self._heard_key and self._pend_n >= 2):
                    became = bool(live.get("ready_photo") and not (self._last or {}).get("ready_photo"))
                    self._last = live
                    self._heard_key = key
                shown = self._smooth_for_phrase(live)
                self._live_phrase = shown
                phrase = _frame_phrase(shown)
                if phrase != self._phrase_hold:
                    self._phrase_hold = phrase
                    self._phrase_n = 1
                else:
                    self._phrase_n += 1
                speech = ""
                if phrase and self._phrase_n >= 3 and phrase != self._frame_said:
                    speech = phrase
                if self._recording:
                    speech = ""
                    became = False

                def publish(speech=speech, became=became, live=live):
                    if self._closed:
                        return
                    if became and self._foreground() and not self._quiet:
                        self._beep()
                    if self._quiet or not self._foreground():
                        return
                    self._fill_measures(self._last or live)
                    if not speech:
                        return
                    self._frame_said = speech
                    self._say(speech, live=True, replace=True)

                wx.CallAfter(publish)

            def _audio_loop(self) -> None:
                while not self._closed:
                    if self._stop.is_set() or self._recording or not self._on or not self.mic:
                        time.sleep(0.3)
                        continue
                    kind = measure_microphone(self.mic, 0.4)
                    if kind != "sconosciuto":
                        self._audio = kind
                    for _ in range(8):
                        if self._closed:
                            return
                        time.sleep(0.4)

            def _on_choice(self, _event):
                if self.combo is None:
                    return
                name = self.combo.GetStringSelection()
                if not name or name == self.device:
                    return
                self._halt()
                self.device = name
                self.mic = choose_microphone(self.device, self.audios, self.mic)
                self._last = None
                self._prev_rgb = b""
                self._levels = []
                self._audio = "attesa"
                self._say(f"Fotocamera: {self.device}.")
                self._start()

            def _on_power(self, _event):
                if self._on:
                    self._halt()
                    self._say("Fotocamera spenta.")
                else:
                    self._last = None
                    self._start()

            def _on_now(self, _event):
                info = self._live_phrase or self._last
                if not info:
                    self._say("Ancora niente da dire. Un attimo.")
                    return
                self._last_spoken = ""
                if self._recording:
                    phrase = _frame_phrase(info) or "Ancora niente da dire. Un attimo."
                    self._frame_said = phrase
                    self._say(phrase, replace=True)
                    return
                self._say(report_text(info).replace("\n", " "))

            def _on_shot(self, _event):
                if self._recording:
                    self._say("Sto registrando. Invio su Ferma video, o Alt+V, prima di scattare.")
                    return
                self._halt()
                base = capture_base("", "scatto")
                dest = unique_file(self.folder, base, ".jpg")
                ok, message = capture_still(self.device, dest)
                if not ok:
                    try:
                        if os.path.isfile(dest):
                            os.remove(dest)
                    except Exception:
                        pass
                    self._say(message or MSG_PHOTO_FAIL)
                    self._resume()
                    return
                info = analyze_image_file(dest)
                write_report_beside(dest, info)
                name = os.path.basename(dest)
                self._last_spoken = ""
                self._say(
                    f"Creato {name}, nella cartella. {info.get('verdict') or ''}"
                )
                self._resume()

            def _on_rec(self, _event):
                if self._recording:
                    self._finish_record()
                    return
                self._recording = True
                self._on = False
                self._stop_preview()
                base = capture_base("", "ripresa")
                final = unique_file(self.folder, base, ".mp4")
                dest = os.path.join(capture_work_dir(), os.path.basename(final))
                ff = ffmpeg_exe()
                external = bool(self.mic) and not same_capture_device(self.device, self.mic)
                cmd = build_record_command(ff, self.device, "" if external else self.mic, dest)
                try:
                    self._record = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        creationflags=_CREATE_NO_WINDOW,
                    )
                except Exception:
                    self._recording = False
                    self._say(MSG_RECORD_FAIL)
                    self._resume()
                    return
                self._record_path = dest
                self._record_final = final
                self._record_audio = None
                self._record_wav = ""
                if external:
                    wav = dest + ".wav"
                    try:
                        self._record_audio = subprocess.Popen(
                            build_audio_command(ff, self.mic, wav),
                            stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=_CREATE_NO_WINDOW | 0x00008000,
                        )
                        self._record_wav = wav
                    except Exception:
                        self._record_audio = None
                threading.Thread(
                    target=self._read_record_frames, args=(self._record,), daemon=True,
                ).start()
                self.btn_rec.SetLabel("Ferma &video")
                self._say(MSG_RECORDING)
                self.btn_rec.SetFocus()

            def _read_record_frames(self, proc) -> None:
                """Legge i fotogrammi mentre il file si scrive, senza fermare ffmpeg."""
                need = _PREVIEW_W * _PREVIEW_H * 3
                latest = {"blob": None}
                done = threading.Event()

                def analyze() -> None:
                    while not done.is_set() or latest["blob"] is not None:
                        blob = latest["blob"]
                        latest["blob"] = None
                        if not blob:
                            time.sleep(0.02)
                            continue
                        try:
                            self._on_preview_frame(blob)
                        except Exception:
                            pass

                threading.Thread(target=analyze, daemon=True).start()
                try:
                    while True:
                        blob = b""
                        while len(blob) < need:
                            chunk = proc.stdout.read(need - len(blob))
                            if not chunk:
                                return
                            blob += chunk
                        latest["blob"] = blob
                except Exception:
                    pass
                finally:
                    done.set()

            def _stop_one(self, proc, wait: bool) -> None:
                if proc is None:
                    return
                try:
                    if proc.stdin:
                        proc.stdin.write(b"q")
                        proc.stdin.flush()
                except Exception:
                    pass
                if wait:
                    try:
                        proc.wait(timeout=8)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass

            def _stop_record(self, wait: bool) -> None:
                video = self._record
                audio = self._record_audio
                wav = self._record_wav
                path = getattr(self, "_record_path", "")
                self._record = None
                self._record_audio = None
                self._record_wav = ""
                self._stop_one(video, wait)
                self._stop_one(audio, wait)
                if wait and wav and path:
                    attach_audio(ffmpeg_exe(), path, wav)
                if wav:
                    try:
                        os.remove(wav)
                    except OSError:
                        pass

            def _publish_recording(self, work: str) -> str:
                final = getattr(self, "_record_final", "") or work
                self._record_final = ""
                if not work or not os.path.isfile(work) or not final:
                    return work
                if os.path.normcase(os.path.abspath(work)) == os.path.normcase(os.path.abspath(final)):
                    return work
                os.makedirs(os.path.dirname(final), exist_ok=True)
                if os.path.exists(final):
                    stem, ext = os.path.splitext(os.path.basename(final))
                    final = unique_file(os.path.dirname(final), stem, ext)
                try:
                    shutil.move(work, final)
                except OSError:
                    return work
                return final

            def _finish_record(self) -> None:
                path = getattr(self, "_record_path", "")
                self._stop_record(wait=True)
                path = self._publish_recording(path)
                self._record_path = path
                self._recording = False
                self.btn_rec.SetLabel("Registra &video")
                if not path or not os.path.isfile(path) or os.path.getsize(path) < 1000:
                    self._say(MSG_RECORD_FAIL)
                else:
                    info = analyze_video_file(path)
                    write_report_beside(path, info)
                    name = os.path.basename(path)
                    self._say(f"Creato {name}, nella cartella. {info.get('verdict') or ''}")
                self.btn_rec.SetFocus()
                if not self._closed:
                    self._resume()

            def _on_mic(self, _event):
                if self.mic_choice is None:
                    return
                name = self.mic_choice.GetStringSelection()
                chosen = "" if name == MIC_NONE else name
                if not name or chosen == self.mic:
                    return
                self.mic = chosen
                self._audio = "attesa"
                self._last = None
                self._heard_key = None
                save_ripresa_prefs(mic=name)
                if name == MIC_NONE:
                    self._say("Nessun microfono. Nel video non entra l'audio. Alt+O lo senti solo tu.")
                else:
                    self._say(f"Microfono: {name}.")

            def _on_dir(self, _event):
                import wx
                dialog = wx.DirDialog(self, "Cartella delle foto e dei video", self.folder)
                if dialog.ShowModal() == wx.ID_OK:
                    self.folder = dialog.GetPath() or self.folder
                    save_ripresa_prefs(folder=self.folder)
                    self._say(f"Cartella: {self.folder}. La ricordo.")
                dialog.Destroy()

            def _enter_quiet(self, event) -> None:
                self._quiet = True
                event.Skip()

            def _enter_position(self, event) -> None:
                self._quiet = False
                if self._last:
                    self._frame_said = _frame_phrase(self._last) or self._frame_said
                event.Skip()

            def _measure_lines(self, info: dict) -> list:
                lines = []
                verdict = info.get("verdict") or ""
                if verdict:
                    lines.append(verdict)
                for line in info.get("lines") or []:
                    if line not in lines:
                        lines.append(line)
                return lines

            def _speak_measure(self, index: int) -> None:
                lines = self._measure_lines(self._last or {})
                if 0 <= index < len(lines) and index < self.measures.GetCount():
                    current = self.measures.GetString(index)
                    if current != lines[index]:
                        self.measures.SetString(index, lines[index])
                if index < 0 or index >= self.measures.GetCount():
                    return
                text = self.measures.GetString(index)
                if text:
                    self._say(text, replace=True)

            def _on_measure(self, event) -> None:
                if not self._quiet:
                    return
                self._speak_measure(event.GetSelection())

            def _focus_measure(self, index: int) -> None:
                count = self.measures.GetCount()
                if count <= 0:
                    self._say("Ancora nessuna misura.")
                    return
                if index >= count:
                    index = count - 1
                already = self.measures.GetSelection() == index
                self.measures.SetFocus()
                self.measures.SetSelection(index)
                if already:
                    self._speak_measure(index)

            def _on_key(self, event):
                import wx
                code = event.GetKeyCode()
                focus = self.FindFocus()
                if code == wx.WXK_ESCAPE:
                    self.Close()
                    return
                if event.AltDown() and not event.ControlDown():
                    number = None
                    if ord("1") <= code <= ord("9"):
                        number = code - ord("1")
                    elif wx.WXK_NUMPAD1 <= code <= wx.WXK_NUMPAD9:
                        number = code - wx.WXK_NUMPAD1
                    if number is not None:
                        self._focus_measure(number)
                        return
                if focus is self.measures and code == wx.WXK_SPACE:
                    self._on_now(None)
                    return
                if focus is self.params and code in (wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_HOME):
                    self._nudge_param(code)
                    return
                event.Skip()

            def _nudge_param(self, code) -> None:
                import wx
                index = self.params.GetSelection()
                if index < 0 or index >= len(self.controls):
                    self._say("Nessun parametro sotto il cursore.", replace=True)
                    return
                ctrl = dict(self.controls[index])
                if not ctrl.get("delivered"):
                    self._say(missing_phrase(ctrl), replace=True)
                    return
                if code == wx.WXK_HOME:
                    if not ctrl.get("auto_ok"):
                        self._say(MSG_FIXED, replace=True)
                        return
                    ctrl["auto"] = True
                    phrase = control_line(ctrl)
                else:
                    if not ctrl.get("manual_ok", True):
                        self._say(MSG_FIXED, replace=True)
                        return
                    step = int(ctrl.get("step") or 1)
                    delta = step if code == wx.WXK_RIGHT else -step
                    new_value = int(ctrl.get("value") or 0) + delta
                    if new_value > int(ctrl.get("max")):
                        self._say(MSG_AT_MAX, replace=True)
                        return
                    if new_value < int(ctrl.get("min")):
                        self._say(MSG_AT_MIN, replace=True)
                        return
                    ctrl["value"] = new_value
                    ctrl["auto"] = False
                    phrase = control_line(ctrl)
                self.controls[index] = ctrl
                self._param_index = index
                self._fill_params()
                self.params.SetSelection(index)
                self._say(phrase, replace=True)
                if self._param_timer is not None:
                    self._param_timer.Stop()
                self._param_timer = wx.CallLater(400, self._flush_param)

            def _flush_param(self) -> None:
                index = self._param_index
                if index < 0 or index >= len(self.controls) or self._closed:
                    return
                ctrl = self.controls[index]
                self._halt()
                time.sleep(0.2)
                if ctrl.get("auto") and ctrl.get("auto_ok"):
                    ok = _apply(self.device, ctrl, int(ctrl.get("value") or 0), _AUTO_FLAG)
                else:
                    ok = _apply(self.device, ctrl, int(ctrl.get("value") or 0), _MANUAL_FLAG)
                if not ok:
                    self._say(MSG_FIXED, replace=True)
                if not self._closed:
                    self._start()
                    try:
                        self.params.SetSelection(index)
                        self.params.SetFocus()
                    except Exception:
                        pass

            def _on_close(self, event):
                self.close_work()
                event.Skip()

            def close_work(self) -> None:
                save_ripresa_prefs(folder=self.folder, mic=self.mic)
                self._closed = True
                self._halt()

        return Dialog()
