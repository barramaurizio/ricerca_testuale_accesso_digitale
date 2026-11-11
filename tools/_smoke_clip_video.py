# -*- coding: utf-8 -*-
"""Prova breve: tagliare e unire due video generati. Non è un test del rilascio."""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Standalone"))
from rtad_clip import _ffmpeg_exe, apply_keep, build, load_piece

ff = _ffmpeg_exe()
folder = tempfile.mkdtemp(prefix="rtad-vid-")


def make(name, w, h, dur):
    path = os.path.join(folder, name)
    subprocess.run(
        [
            ff, "-nostdin", "-y",
            "-f", "lavfi", "-i", f"testsrc=duration={dur}:size={w}x{h}:rate=25",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={dur}",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            path,
        ],
        check=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
    )
    return path


def main():
    a = make("a.mp4", 320, 240, 4)
    b = make("b.mp4", 320, 240, 2)
    pa, err = load_piece(a)
    print("PROBE", round(pa.duration, 2), pa.kind, pa.has_video, pa.has_audio, pa.width, err)
    size = os.path.getsize(a)
    apply_keep(pa, 1, 3)
    ok, msg = build([pa])
    print("VKEEP", ok, msg)
    got = [n for n in os.listdir(folder) if n.startswith("a-taglio")][0]
    piece, _err = load_piece(os.path.join(folder, got))
    print("VKEEP DUR", round(piece.duration, 2), piece.has_video, piece.has_audio)
    if not ok or abs(piece.duration - 2) >= 0.45:
        raise SystemExit("taglio video non riuscito")
    if os.path.getsize(a) != size:
        raise SystemExit("il file di partenza è cambiato")
    pb, _err = load_piece(b)
    pc, _err = load_piece(a)
    ok, msg = build([pc, pb])
    print("VJOIN", ok, msg)
    joined = [n for n in os.listdir(folder) if "unito" in n][0]
    out, _err = load_piece(os.path.join(folder, joined))
    print("VJOIN DUR", round(out.duration, 2), joined)
    if not ok or abs(out.duration - 6) >= 0.6:
        raise SystemExit("unione video non riuscita")
    wav = os.path.join(folder, "c.wav")
    subprocess.run(
        [ff, "-nostdin", "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=1", wav],
        check=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
    )
    pw, _err = load_piece(wav)
    ok, msg = build([pc, pw])
    print("MIX", ok, msg)
    if ok or "non si uniscono" not in msg:
        raise SystemExit("audio e video uniti, e non dovevano")
    print("VIDEO OK")


if __name__ == "__main__":
    main()
