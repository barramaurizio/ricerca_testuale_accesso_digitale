# -*- coding: utf-8 -*-
"""Smoke 1.7.6 — prove senza mouse, senza CD/DVD, senza Setup reale.

Cosa verifica (logica pura + filesystem temporaneo):
  P0b  cartella updates\\ + cleanup Setup/Portable
  P0c  Trova copie: updates\\ NON è «copia sicura»
  P1   messaggio .cda, riconoscimento VIDEO_TS, GetDriveType include 5
  P1c  wrap_report_text (righe ~72, path/URL non spezzati)
  P0a  nel sorgente: drop su Frame+Panel+txt_path (strutturale)

Cosa NON può sostituire:
  - trascinamento mouse reale (serve papà o un click)
  - CD/DVD fisico montato
  - download GitHub / Installer Inno end-to-end

Uso:
  python tools/_smoke_1_7_6.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SA = os.path.join(ROOT, "Standalone")
sys.path.insert(0, SA)

import rtad_copie  # noqa: E402


def _load_helpers():
    """Carica pezzi puri da app_gui senza avviare wx."""
    src = open(os.path.join(SA, "app_gui.py"), encoding="utf-8").read()
    start = src.index("def wrap_report_text(")
    # fino a detect_sa_install_channel (escluso) — include wrap + updates helpers
    end = src.index("\ndef detect_sa_install_channel(", start)
    chunk1 = src[start:end]

    start2 = src.index("def get_real_ready_drives(")
    end2 = src.index("\ndef extract_plain_text_file(", start2)
    chunk2 = src[start2:end2]

    ns = {
        "os": os,
        "sys": sys,
        "logging": __import__("logging"),
        "textwrap": textwrap,
        "ctypes": __import__("ctypes"),
        "UPDATES_DIR": os.path.join(
            os.environ.get("LOCALAPPDATA")
            or os.path.join(os.path.expanduser("~"), "AppData", "Local"),
            "RTAD_Standalone",
            "updates",
        ),
    }
    exec(chunk1, ns)
    exec(chunk2, ns)
    return ns


def _ok(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        raise AssertionError(f"FAIL {name}: {detail}")
    print(f"OK  {name}" + (f" — {detail}" if detail else ""))


def test_wrap(ns) -> None:
    wrap = ns["wrap_report_text"]
    long = "parola " * 40
    out = wrap(long)
    lines = out.splitlines()
    _ok("wrap_multiline", len(lines) >= 3, f"{len(lines)} righe")
    _ok(
        "wrap_maxlen",
        max(len(L) for L in lines) <= 72,
        f"max={max(len(L) for L in lines)}",
    )
    path = r"C:\Users\barra\Downloads\Setup_RicercaTestualeAccessoDigitale_v1.7.5.exe"
    _ok("wrap_keeps_path", wrap(path) == path)
    url = "https://example.com/" + ("x" * 80)
    _ok("wrap_keeps_url", wrap(url) == url)
    # preserva newline esistenti
    multi = "riga corta\n" + ("ciao " * 30)
    w2 = wrap(multi)
    _ok("wrap_preserves_break", w2.startswith("riga corta\n"))


def test_updates_cleanup(ns) -> None:
    get_dir = ns["get_sa_updates_dir"]
    cleanup = ns["cleanup_sa_update_downloads"]
    # Usa sottocartella temp sotto updates per non toccare file reali dell'utente
    real = get_dir()
    with tempfile.TemporaryDirectory(dir=real, prefix="smoke_") as td:
        # Monkeypatch UPDATES_DIR nel namespace delle funzioni
        ns["UPDATES_DIR"] = td
        # Ricarica bind: le funzioni chiudono su UPDATES_DIR del ns
        # get_sa_updates_dir usa UPDATES_DIR globale del ns — ok dopo assegnazione
        keep = os.path.join(td, "Setup_RicercaTestualeAccessoDigitale_v9.9.9.exe")
        old = os.path.join(td, "Setup_RicercaTestualeAccessoDigitale_v1.0.0.exe")
        port = os.path.join(td, "RicercaTestualeAccessoDigitale_Portable_v1.0.0.exe")
        junk = os.path.join(td, "nota.txt")
        for p in (keep, old, port, junk):
            with open(p, "wb") as f:
                f.write(b"x")
        cleanup(keep_path=keep)
        _ok("cleanup_keeps_current", os.path.isfile(keep))
        _ok("cleanup_removes_old_setup", not os.path.isfile(old))
        _ok("cleanup_removes_old_portable", not os.path.isfile(port))
        _ok("cleanup_ignores_non_exe", os.path.isfile(junk))
    # ripristina
    ns["UPDATES_DIR"] = real


def test_copie_managed() -> None:
    ud = rtad_copie.managed_updates_dir()
    fake_upd = os.path.join(ud, "Setup_RicercaTestualeAccessoDigitale_v1.7.5.exe")
    _ok("copie_is_managed", rtad_copie.is_managed_updates_path(fake_upd))
    _ok(
        "copie_class_managed",
        rtad_copie.classify_exe(fake_upd) == "managed_updates",
    )
    # is_safe richiede file reale → creiamo temp in updates e verifichiamo False
    os.makedirs(ud, exist_ok=True)
    probe = os.path.join(ud, "_smoke_probe_Setup_RicercaTestualeAccessoDigitale_x.exe")
    try:
        with open(probe, "wb") as f:
            f.write(b"probe")
        _ok("copie_not_safe_updates", not rtad_copie.is_safe_to_delete(probe))
    finally:
        try:
            os.remove(probe)
        except OSError:
            pass

    # Download: pacchetto in cartella Download = release_download (se cartella esiste)
    home = os.path.expanduser("~")
    dl = os.path.join(home, "Downloads")
    if os.path.isdir(dl):
        # classifica senza file reale: release_download solo se _is_user_drop_folder
        name = "Setup_RicercaTestualeAccessoDigitale_v1.7.5.exe"
        path = os.path.join(dl, name)
        kind = rtad_copie.classify_exe(path)
        _ok(
            "copie_download_kind",
            kind in ("release_download", "other"),
            kind,
        )


def test_cda_and_video_ts(ns) -> None:
    msg = ns["message_for_cda_path"](r"E:\Track05.cda")
    _ok("cda_mentions_not_audio", "non è un file audio" in msg.lower() or "non è un file audio" in msg)
    _ok("cda_mentions_windows", "Windows" in msg or "collegamento" in msg.lower())
    _ok("cda_track_name", "Track05.cda" in msg)

    with tempfile.TemporaryDirectory() as td:
        vts = os.path.join(td, "VIDEO_TS")
        os.makedirs(vts)
        _ok("video_ts_dir", ns["_path_looks_like_video_ts"](td))
        _ok("video_ts_sub", ns["_path_looks_like_video_ts"](vts))
        plain = os.path.join(td, "foto")
        os.makedirs(plain)
        _ok("not_video_ts", not ns["_path_looks_like_video_ts"](plain))


def test_drive_type_five_in_source() -> None:
    src = open(os.path.join(SA, "app_gui.py"), encoding="utf-8").read()
    _ok("sa_drive_type_5", "drive_type in (2, 3, 5)" in src)
    addon = os.path.join(
        ROOT, "addon", "globalPlugins", "ricerca_testuale", "__init__.py"
    )
    asrc = open(addon, encoding="utf-8").read()
    _ok("addon_drive_type_5", "drive_type in (2, 3, 5)" in asrc)


def test_drop_structural() -> None:
    src = open(os.path.join(SA, "app_gui.py"), encoding="utf-8").read()
    _ok("drop_helper", "def _enable_file_drop_targets" in src)
    _ok("drop_filedroptarget", "FileDropTarget" in src and "SetDropTarget" in src)
    _ok("drop_apply_paths", "def _apply_dropped_paths" in src)
    _ok("drop_log", "Drop file ricevuto" in src)
    # Nessun HSCROLL residuo nei report SA
    _ok("no_hscroll_sa", "wx.HSCROLL" not in src)
    asrc = open(
        os.path.join(ROOT, "addon", "globalPlugins", "ricerca_testuale", "__init__.py"),
        encoding="utf-8",
    ).read()
    _ok("no_hscroll_addon", "wx.HSCROLL" not in asrc)


def test_updater_not_downloads() -> None:
    src = open(os.path.join(SA, "app_gui.py"), encoding="utf-8").read()
    # Il download aggiornamento deve usare get_sa_updates_dir, non ~\Downloads
    idx = src.index("def on_check_updates")
    chunk = src[idx : idx + 4500]
    _ok("updater_uses_updates_dir", "get_sa_updates_dir()" in chunk)
    _ok(
        "updater_no_downloads_join",
        'os.path.join(\n                                os.path.expanduser("~"), "Downloads"'
        not in chunk
        and 'expanduser("~"), "Downloads"' not in chunk,
    )
    _ok("updater_cleanup_call", "cleanup_sa_update_downloads()" in chunk)


def test_marker_in_iss() -> None:
    iss = open(os.path.join(SA, "setup.iss"), encoding="utf-8").read()
    _ok("iss_marker_file", "rtad_install_channel.txt" in iss)
    _ok(
        "marker_file_exists",
        os.path.isfile(os.path.join(SA, "rtad_install_channel.txt")),
    )


def main() -> int:
    print("=== Smoke RTAD 1.7.6 ===")
    ns = _load_helpers()
    test_wrap(ns)
    test_updates_cleanup(ns)
    test_copie_managed()
    test_cda_and_video_ts(ns)
    test_drive_type_five_in_source()
    test_drop_structural()
    test_updater_not_downloads()
    test_marker_in_iss()
    print("=== TUTTO OK (logica 1.7.6) ===")
    print(
        "Residuo umano: drop col mouse; CD/DVD fisico; "
        "un giro Portable da papà PRIMA dello store."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(1)
