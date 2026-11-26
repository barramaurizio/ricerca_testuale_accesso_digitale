# -*- coding: utf-8 -*-
"""Prove della 2.0.11: mano su foto, video e parametri fotocamera."""
from __future__ import annotations

import os
import struct
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_ripresa as ripresa


def solid(w, h, color):
    r, g, b = color
    return bytes([r, g, b]) * (w * h), w, h


def paint(rgb, w, h, x, y, color):
    buf = bytearray(rgb)
    if 0 <= x < w and 0 <= y < h:
        i = (y * w + x) * 3
        buf[i:i + 3] = bytes(color)
    return bytes(buf)


def fill_rect(rgb, w, h, x0, y0, x1, y1, color):
    buf = bytearray(rgb)
    for y in range(max(0, y0), min(h, y1)):
        for x in range(max(0, x0), min(w, x1)):
            i = (y * w + x) * 3
            buf[i:i + 3] = bytes(color)
    return bytes(buf)


def checker(w, h, x0, y0, x1, y1, a=(20, 20, 20), b=(210, 210, 210), step=2):
    rgb, _, _ = solid(w, h, (120, 120, 120))
    buf = bytearray(rgb)
    for y in range(y0, y1):
        for x in range(x0, x1):
            color = a if ((x // step) + (y // step)) % 2 == 0 else b
            i = (y * w + x) * 3
            buf[i:i + 3] = bytes(color)
    return bytes(buf)


def blur(rgb, w, h, passes=3):
    buf = bytearray(rgb)
    for _ in range(passes):
        nxt = bytearray(buf)
        for y in range(h):
            for x in range(w):
                acc = [0, 0, 0]
                for dy in (-1, 0, 1):
                    yy = min(h - 1, max(0, y + dy))
                    for dx in (-1, 0, 1):
                        xx = min(w - 1, max(0, x + dx))
                        i = (yy * w + xx) * 3
                        acc[0] += buf[i]
                        acc[1] += buf[i + 1]
                        acc[2] += buf[i + 2]
                o = (y * w + x) * 3
                nxt[o] = acc[0] // 9
                nxt[o + 1] = acc[1] // 9
                nxt[o + 2] = acc[2] // 9
        buf = nxt
    return bytes(buf)


def draw_face(w, h, cx, cy, fw, fh):
    rgb, _, _ = solid(w, h, (70, 90, 120))
    buf = bytearray(rgb)
    skin = (210, 160, 130)
    eye = (15, 15, 15)
    rx = max(4, fw / 2)
    ry = max(4, fh / 2)
    for y in range(h):
        for x in range(w):
            dx = (x - cx) / rx
            dy = (y - cy) / ry
            if dx * dx + dy * dy <= 1:
                i = (y * w + x) * 3
                buf[i:i + 3] = bytes(skin)
    er = max(2, int(min(fw, fh) * 0.08))
    for ex in (cx - fw * 0.18, cx + fw * 0.18):
        ey = cy - fh * 0.12
        for y in range(int(ey - er), int(ey + er) + 1):
            for x in range(int(ex - er), int(ex + er) + 1):
                if 0 <= x < w and 0 <= y < h:
                    if (x - ex) ** 2 + (y - ey) ** 2 <= er * er:
                        i = (y * w + x) * 3
                        buf[i:i + 3] = bytes(eye)
    return bytes(buf)


def text_of(rgb, w, h, **kw):
    info = ripresa.analyze_rgb(rgb, w, h, **kw)
    return ripresa.report_text(info), info


def must(cond, label, text=""):
    if not cond:
        raise SystemExit(f"FALLITA: {label}\n{text}")


def test_stills():
    text, info = text_of(*solid(80, 60, (0, 0, 0)))
    must(info["verdict"] == "Non si vede niente. Luce assente.", "nera", text)

    text, info = text_of(*solid(80, 60, (255, 255, 255)))
    must(info["verdict"] == "Tutto bruciato. Troppa luce.", "bianca", text)

    text, info = text_of(*solid(80, 60, (128, 128, 128)))
    must("Luce giusta" in text and "Contrasto piatto" in text and "Nessun volto" in text, "grigio", text)

    sharp = checker(96, 96, 0, 0, 96, 96)
    text, info = text_of(sharp, 96, 96)
    must(info["sharp"] == "nitido" and info["ready_photo"], "griglia nitida", f"{text}\nvar={info['sharp_var']}")

    soft = blur(sharp, 96, 96, passes=6)
    text, info = text_of(soft, 96, 96)
    must(info["sharp"] == "sfocato", "griglia sfocata", f"{text}\nvar={info['sharp_var']}")

    center = checker(96, 96, 32, 32, 64, 64)
    text, info = text_of(center, 96, 96)
    must("al centro" in text and "Il centro è sfocato" not in text, "nitido al centro", f"{text}\nwhere={info['sharp_where']} var={info['sharp_var']}")

    left = checker(96, 96, 0, 0, 32, 96)
    text, info = text_of(left, 96, 96)
    must("sinistra" in text and "Il centro è sfocato" in text, "nitido a sinistra", f"{text}\nwhere={info['sharp_where']} var={info['sharp_var']} center_soft={info['center_soft']}")

    face = draw_face(180, 180, 90, 115, 70, 110)
    text, info = text_of(face, 180, 180)
    must(info["face_count"] == 1 and info["face_place"] == "centro" and info["face_distance"] == "vicino", "volto centro", text)
    own = {
        "light": "giusta",
        "face_count": 1,
        "face_place": "centro",
        "face_cropped": False,
        "face_distance": "medio",
        "ready_photo": True,
    }
    own["face_cx"], own["face_cy"] = 0.50, 0.54
    must(
        ripresa._frame_phrase(own) == "Il volto è proprio al centro. Puoi scattare.",
        "proprio al centro",
        ripresa._frame_phrase(own),
    )
    own["face_cx"] = 0.475
    left_phrase = ripresa._frame_phrase(own)
    must("un filo a sinistra" in left_phrase and "un filo a destra" in left_phrase, "filo a sinistra", left_phrase)
    own["face_cx"], own["face_cy"] = 0.510, 0.54
    must("proprio al centro" in ripresa._frame_phrase(own), "il seduto resta al centro", ripresa._frame_phrase(own))
    own["face_cx"] = 0.521
    right_phrase = ripresa._frame_phrase(own)
    must("un filo a destra" in right_phrase, "filo a destra", right_phrase)
    own["face_cx"], own["face_cy"] = 0.50, 0.575
    low_phrase = ripresa._frame_phrase(own)
    must("un filo in basso" in low_phrase and "un filo più su" in low_phrase, "filo in basso", low_phrase)
    own["face_cx"], own["face_cy"], own["face_aspect"] = 0.51, 0.54, 1.40
    up_phrase = ripresa._frame_phrase(own)
    must("un filo in alto" in up_phrase and "un filo più giù" in up_phrase, "filo in alto", up_phrase)
    own["face_aspect"] = 1.62
    must("proprio al centro" in ripresa._frame_phrase(own), "volto lungo resta al centro", ripresa._frame_phrase(own))
    own.pop("face_aspect", None)

    small = draw_face(180, 180, 24, 22, 20, 22)
    text, info = text_of(small, 180, 180)
    must(info["face_count"] == 1 and "lontano" in text and "sinistra" in text, "volto lontano", text)

    cut = draw_face(200, 180, 28, 90, 90, 100)
    text, info = text_of(cut, 200, 180)
    must(info["face_cropped"] and "tagliato" in text and "sinistra" in text, "volto tagliato", text)

    text, _ = text_of(*solid(60, 40, (200, 100, 40)))
    must("troppo caldo" in text, "caldo", text)
    text, _ = text_of(*solid(60, 40, (40, 80, 200)))
    must("troppo freddo" in text, "freddo", text)
    text, _ = text_of(*solid(60, 40, (40, 180, 40)))
    must("Tinta verde" in text, "verde", text)

    back, w, h = solid(120, 90, (240, 240, 240))
    back = fill_rect(back, w, h, 36, 27, 84, 63, (20, 20, 20))
    text, info = text_of(back, w, h)
    must(info["light"] == "controluce", "controluce", text)
    must(info["shadow"] and "Sagoma in ombra" in text and "al centro" in text, "sagoma al centro", text)
    must(info["coach"] == "Sei al centro. Controluce.", "coach controluce al centro", info["coach"])

    side, w, h = solid(160, 120, (235, 235, 230))
    side = fill_rect(side, w, h, 4, 28, 52, 100, (18, 18, 22))
    text, info = text_of(side, w, h)
    must(info["shadow"] and info["shadow_place"] == "sinistra", "sagoma a sinistra", text)
    must(info["coach"] == "Più a destra.", "coach sagoma", info["coach"])
    framed = ripresa._frame_phrase(info)
    must(framed == "Il soggetto è a sinistra. Spostati più a destra.", "frase di spostamento", framed)

    black = ripresa.analyze_rgb(*solid(40, 30, (0, 0, 0)))
    ready = ripresa.analyze_rgb(sharp, 96, 96)
    said = ripresa.live_speech(None, black)
    must("Non si vede niente" in said, "prima voce", said)
    said = ripresa.live_speech(black, ready)
    must("Pronto" in said or "Nitido" in said, "diventa pronto", said)
    again = ripresa.live_speech(ready, ready)
    must(again == "", "niente se non cambia", again)

    muted = ripresa.with_live(ready, motion="ferma", audio="giusto")
    must(muted["ready_record"] and "registrare" in muted["verdict"], "pronto a registrare", muted["verdict"])
    shaky = ripresa.with_live(ready, motion="traballa", audio="giusto")
    must(shaky["ready_photo"] and not shaky["ready_record"] and "fermo" in shaky["verdict"].lower(), "foto sì video no", shaky["verdict"])


def test_names_and_exif():
    folder = tempfile.mkdtemp(prefix="rtad-ripresa-")
    try:
        first = ripresa.unique_file(folder, ripresa.capture_base("vacanza", "scatto"), ".jpg")
        must(os.path.basename(first) == "vacanza-scatto.jpg", "nome scatto", first)
        open(first, "wb").close()
        second = ripresa.unique_file(folder, ripresa.capture_base("vacanza", "scatto"), ".jpg")
        must(os.path.basename(second) == "vacanza-scatto-2.jpg", "nome -2", second)
        plain = ripresa.unique_file(folder, ripresa.capture_base("", "scatto"), ".jpg")
        must(os.path.basename(plain) == "Scatto.jpg", "nome senza file", plain)
    finally:
        for name in os.listdir(folder):
            os.remove(os.path.join(folder, name))
        os.rmdir(folder)

    must("1,5 metri" in ripresa._format_meters(1.5), "metri")
    must("50 centimetri" in ripresa._format_meters(0.5), "centimetri")
    ctrl = {"name": "Fuoco", "article": "il fuoco", "delivered": False}
    must(
        ripresa.missing_phrase(ctrl) == "Questa fotocamera non consegna il fuoco.",
        "parametro assente",
        ripresa.missing_phrase(ctrl),
    )
    ctrl = {
        "name": "Fuoco", "article": "il fuoco", "delivered": True, "auto": True,
        "value": 220, "min": 0, "max": 1023, "unit": "",
    }
    line = ripresa.control_line(ctrl)
    must("automatico" in line and "220" in line and "1023" in line, "fuoco automatico", line)

    ff = ripresa.ffmpeg_exe()
    must(bool(ff), "ffmpeg presente")
    folder = tempfile.mkdtemp(prefix="rtad-exif-")
    try:
        bmp = os.path.join(folder, "x.bmp")
        jpg = os.path.join(folder, "x.jpg")
        rgb, w, h = solid(16, 16, (80, 80, 80))
        ripresa.write_bmp(bmp, rgb, w, h)
        proc = ripresa._run([ff, "-y", "-i", bmp, "-q:v", "3", jpg], timeout=20)
        must(proc.returncode == 0 and os.path.isfile(jpg), "jpeg di prova", proc.stderr.decode("utf-8", "replace")[:300])
        _inject_distance(jpg, 3, 2)
        lines = ripresa.read_exif_lines(jpg)
        joined = " ".join(lines)
        must("1,5 metri" in joined, "exif distanza", joined)
        loaded = ripresa.load_rgb(jpg)
        must(loaded is not None and loaded[1] == 16, "leggo jpeg", str(loaded[:1] if not loaded else (loaded[1], loaded[2])))
    finally:
        for name in os.listdir(folder):
            os.remove(os.path.join(folder, name))
        os.rmdir(folder)


def _inject_distance(path, num, den):
    """APP1 con SubjectDistance dopo il SOI."""
    tiff = bytearray(b"II*\x00")
    tiff += struct.pack("<I", 8)
    tiff += struct.pack("<H", 1)
    tiff += struct.pack("<HHI", 0x8769, 4, 1)
    tiff += struct.pack("<I", 26)
    tiff += struct.pack("<I", 0)
    tiff += struct.pack("<H", 1)
    tiff += struct.pack("<HHI", 0x9206, 5, 1)
    tiff += struct.pack("<I", 44)
    tiff += struct.pack("<I", 0)
    tiff += struct.pack("<II", num, den)
    payload = b"Exif\x00\x00" + bytes(tiff)
    segment = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    with open(path, "rb") as handle:
        blob = handle.read()
    if blob[:2] != b"\xff\xd8":
        raise SystemExit("jpeg non valido")
    with open(path, "wb") as handle:
        handle.write(blob[:2] + segment + blob[2:])


def _encode(path, frames, w, h, fps, audio):
    ff = ripresa.ffmpeg_exe()
    cmd = [
        ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
        "-r", str(fps), "-i", "pipe:0",
    ]
    if audio == "none":
        cmd += ["-an"]
    elif audio == "tone":
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-filter:a", "volume=0.35", "-shortest"]
    elif audio == "loud":
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-filter:a", "volume=18dB", "-shortest"]
    elif audio == "silence":
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac"] if audio != "none" else ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio == "none":
        cmd = cmd  # già senza audio
    cmd.append(path)
    raw = b"".join(frames)
    proc = ripresa._run(cmd, timeout=40, input_bytes=raw)
    if proc.returncode != 0 or not os.path.isfile(path):
        raise SystemExit((proc.stderr or b"").decode("utf-8", "replace")[-500:])


def test_videos():
    w, h, fps = 160, 120, 10
    folder = tempfile.mkdtemp(prefix="rtad-video-")
    try:
        sharp = checker(w, h, 0, 0, w, h)
        frames = [sharp] * 12
        path = os.path.join(folder, "fermo.mp4")
        _encode(path, frames, w, h, fps, "silence")
        info = ripresa.analyze_video_file(path)
        text = info["verdict"]
        must("ferma" in text and "nitido" in text and "silenzio" in text, "video fermo", text)

        moved = []
        for i in range(12):
            shift = (i % 5) * 18
            frame = checker(w, h, 0, 0, w, h)
            buf = bytearray(frame)
            # sposta una banda chiara, così i fotogrammi non coincidono
            buf = bytearray(fill_rect(bytes(buf), w, h, shift, 10, min(w, shift + 30), 100, (250, 250, 250)))
            moved.append(bytes(buf))
        path = os.path.join(folder, "mosso.mp4")
        _encode(path, moved, w, h, fps, "none")
        info = ripresa.analyze_video_file(path)
        must(info["motion"] in ("si muove", "traballa"), "video mosso", info["verdict"] + " " + info["motion"])

        dark, _, _ = solid(w, h, (30, 30, 30))
        bright, _, _ = solid(w, h, (200, 200, 200))
        dropped = [bright] * 8 + [dark] * 8
        path = os.path.join(folder, "cala.mp4")
        _encode(path, dropped, w, h, fps, "none")
        info = ripresa.analyze_video_file(path)
        must("cala" in info["verdict"], "luce cala", info["verdict"])

        flick = []
        for i in range(16):
            flick.append(bright if (i // 4) % 2 == 0 else dark)
        path = os.path.join(folder, "sfarfalla.mp4")
        _encode(path, flick, w, h, fps, "none")
        info = ripresa.analyze_video_file(path)
        must("sfarfalla" in info["verdict"], "sfarfalla", info["verdict"])

        soft = blur(sharp, w, h, passes=6)
        path = os.path.join(folder, "morbido.mp4")
        _encode(path, [sharp] * 6 + [soft] * 6, w, h, fps, "none")
        info = ripresa.analyze_video_file(path)
        must("sfocato" in info["verdict"], "diventa sfocato", info["verdict"])

        path = os.path.join(folder, "tono.mp4")
        _encode(path, [sharp] * 10, w, h, fps, "tone")
        info = ripresa.analyze_video_file(path)
        must(info["audio"] == "giusto", "audio giusto", f"{info['audio']} {info['verdict']}")

        path = os.path.join(folder, "forte.mp4")
        _encode(path, [sharp] * 10, w, h, fps, "loud")
        info = ripresa.analyze_video_file(path)
        must(info["audio"] in ("saturo", "troppo alto"), "audio forte", f"{info['audio']} {info['verdict']}")

        path = os.path.join(folder, "muto.mp4")
        _encode(path, [sharp] * 8, w, h, fps, "none")
        info = ripresa.analyze_video_file(path)
        must(info["audio"] == "muto" and "muto" in info["verdict"].lower(), "video muto", info["verdict"])
    finally:
        for name in os.listdir(folder):
            try:
                os.remove(os.path.join(folder, name))
            except Exception:
                pass
        try:
            os.rmdir(folder)
        except Exception:
            pass


def test_camera_if_present():
    videos, audios = ripresa.list_dshow_devices()
    if not videos:
        print("nessuna webcam, salto i parametri dal vivo")
        return
    name = videos[0]
    rows = ripresa.read_camera_controls(name)
    delivered = [row for row in rows if row.get("delivered")]
    must(bool(rows), "elenco parametri", str(rows))
    missing = [row for row in rows if not row.get("delivered")]
    if missing:
        phrase = ripresa.missing_phrase(missing[0])
        must(phrase.startswith("Questa fotocamera non consegna"), "frase parametro", phrase)
    if not delivered:
        print(f"webcam {name} non consegna parametri, elenco comunque presente")
        return
    light = next((row for row in delivered if row["name"] == "Luminosità"), delivered[0])
    original = int(light["value"])
    original_auto = bool(light.get("auto"))
    try:
        if light.get("manual_ok", True) and int(light["max"]) > int(light["min"]):
            nxt, phrase = ripresa.adjust_camera_control(name, light, 1)
            must(nxt.get("delivered"), "regolo", phrase)
            if not nxt.get("auto"):
                must(int(nxt["value"]) != original or phrase in (ripresa.MSG_AT_MAX, ripresa.MSG_FIXED), "valore nuovo", phrase)
    finally:
        restore_flags = ripresa._AUTO_FLAG if original_auto else ripresa._MANUAL_FLAG
        ripresa._apply(name, light, original, restore_flags)
    print(f"webcam {name}: {len(delivered)} parametri, microfoni {len(audios)}")


def test_record_command():
    ff = "ffmpeg"
    camera = "FHD Camera"
    same = ripresa.build_record_command(ff, camera, "Microphone (FHD Camera Microphone)", "a.mp4")
    must("video=FHD Camera:audio=Microphone (FHD Camera Microphone)" in same, "stesso ingresso", " ".join(same))
    must(same.count("-i") == 1, "un ingresso", " ".join(same))
    other = ripresa.build_record_command(ff, camera, "Microfono (Realtek(R) Audio)", "a.mp4")
    must(other.count("-i") == 1, "video da solo", " ".join(other))
    must("audio=" not in " ".join(other), "senza audio nel video", " ".join(other))
    heard = ripresa.build_audio_command(ff, "Microfono (Realtek(R) Audio)", "a.wav")
    must(heard.count("-i") == 1 and "audio=Microfono (Realtek(R) Audio)" in heard, "audio a parte", " ".join(heard))
    must("pcm_s16le" in heard, "sonoro intero", " ".join(heard))
    silent = ripresa.build_record_command(ff, camera, ripresa.MIC_NONE, "a.mp4")
    must("audio=" not in " ".join(silent), "nessun microfono", " ".join(silent))


def main():
    test_record_command()
    test_stills()
    test_names_and_exif()
    test_videos()
    test_camera_if_present()
    print("tutte le prove 2.0.11 ok")


if __name__ == "__main__":
    main()
