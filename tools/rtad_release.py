#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTAD — tool di preparazione rilascio (Standalone + Add-on NVDA)

Cosa fa lo script (automatico):
  - controlla che i numeri di versione siano allineati
  - aggiorna la versione in tutti i file tecnici
  - genera un modello di note di rilascio bilingue
  - ricostruisce il pacchetto .nvda-addon
  - stampa la checklist di ciò che resta MANUALE

Cosa NON fa (resta a Maurizio / Cursor):
  - scrivere le novità nel codice
  - testare Standalone e Add-on
  - compilare gli .exe (compila.bat / Inno Setup)
  - commit/push su GitHub Desktop
  - creare le Release Web e allegare i binari
  - aprire l'issue sullo store NV Access

Uso (dalla root del repo):
  python tools/rtad_release.py check
  python tools/rtad_release.py bump 1.5.2
  python tools/rtad_release.py notes 1.5.2
  python tools/rtad_release.py addon
  python tools/rtad_release.py summary 1.5.2
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "standalone_app": ROOT / "Standalone" / "app_gui.py",
    "addon_init": ROOT / "addon" / "globalPlugins" / "ricerca_testuale" / "__init__.py",
    "manifest": ROOT / "addon" / "manifest.ini",
    "setup_iss": ROOT / "Standalone" / "setup.iss",
    "version_txt": ROOT / "Standalone" / "version.txt",
    "compila_bat": ROOT / "Standalone" / "compila.bat",
    "make_addon": ROOT / "make_addon.py",
    "readme": ROOT / "README.md",
    "changelog": ROOT / "Standalone" / "changelog.txt",
    "doc_it": ROOT / "addon" / "doc" / "it" / "readme.html",
    "doc_en": ROOT / "addon" / "doc" / "en" / "readme.html",
}

VERSION_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")
GITHUB_REPO = "https://github.com/barramaurizio/ricerca_testuale_accesso_digitale"
DATASTORE_FORM = (
    "https://github.com/nvaccess/addon-datastore/issues/new"
    "?template=registerAddon.yml"
)


def die(msg: str, code: int = 1) -> None:
    print(f"ERRORE: {msg}")
    sys.exit(code)


def read_text(path: Path) -> str:
    if not path.exists():
        die(f"File mancante: {path}")
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def extract_version_from_app(path: Path) -> str | None:
    m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', read_text(path), re.M)
    return m.group(1) if m else None


def extract_version_from_manifest(path: Path) -> str | None:
    m = re.search(r"^version\s*=\s*([^\s#]+)", read_text(path), re.M)
    return m.group(1).strip() if m else None


def extract_version_from_setup(path: Path) -> str | None:
    m = re.search(r"^AppVersion\s*=\s*([^\r\n]+)", read_text(path), re.M)
    return m.group(1).strip() if m else None


def extract_version_from_readme(path: Path) -> str | None:
    m = re.search(r"\(v(\d+\.\d+(?:\.\d+)?)\)", read_text(path))
    return m.group(1) if m else None


def extract_version_from_make_addon(path: Path) -> str | None:
    text = read_text(path)
    m = re.search(
        r'recerca_testuale_accesso_digitale-(\d+\.\d+(?:\.\d+)?)\.nvda-addon',
        text,
    )
    return m.group(1) if m else None


def version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def collect_versions() -> dict[str, str | None]:
    return {
        "Standalone/app_gui.py": extract_version_from_app(FILES["standalone_app"]),
        "addon/.../__init__.py": extract_version_from_app(FILES["addon_init"]),
        "addon/manifest.ini": extract_version_from_manifest(FILES["manifest"]),
        "Standalone/setup.iss": extract_version_from_setup(FILES["setup_iss"]),
        "README.md": extract_version_from_readme(FILES["readme"]),
    }


def cmd_check(_: argparse.Namespace) -> None:
    versions = collect_versions()
    print("=== Verifica allineamento versioni ===\n")
    for name, ver in versions.items():
        print(f"  {name}: {ver or '(non trovata)'}")

    present = [v for v in versions.values() if v]
    if not present:
        die("Nessuna versione trovata.")
    unique = set(present)
    print()
    if len(unique) == 1:
        print(f"OK: tutte allineate a {present[0]}")
        print_manual_checklist(present[0], include_build_hints=False)
    else:
        print("ATTENZIONE: versioni NON allineate.")
        print("Esegui: python tools/rtad_release.py bump X.Y.Z")
        sys.exit(2)


def replace_app_version(path: Path, new_version: str) -> None:
    text = read_text(path)
    new_text, n = re.subn(
        r'^APP_VERSION\s*=\s*"[^"]+"',
        f'APP_VERSION = "{new_version}"',
        text,
        count=1,
        flags=re.M,
    )
    if n != 1:
        die(f"APP_VERSION non aggiornata in {path}")
    write_text(path, new_text)


def bump_manifest(path: Path, new_version: str) -> None:
    text = read_text(path)
    new_text, n = re.subn(
        r"^version\s*=\s*.*$",
        f"version = {new_version}",
        text,
        count=1,
        flags=re.M,
    )
    if n != 1:
        die(f"version non aggiornata in {path}")
    write_text(path, new_text)


def bump_setup_iss(path: Path, new_version: str) -> None:
    text = read_text(path)
    text2, n1 = re.subn(
        r"^AppVersion=.*$",
        f"AppVersion={new_version}",
        text,
        count=1,
        flags=re.M,
    )
    text3, n2 = re.subn(
        r"^OutputBaseFilename=Setup_RicercaTestualeAccessoDigitale_v.*$",
        f"OutputBaseFilename=Setup_RicercaTestualeAccessoDigitale_v{new_version}",
        text2,
        count=1,
        flags=re.M,
    )
    if n1 != 1 or n2 != 1:
        die(f"setup.iss non aggiornato completamente ({path})")
    write_text(path, text3)


def bump_version_txt(path: Path, new_version: str) -> None:
    parts = [int(x) for x in new_version.split(".")]
    while len(parts) < 4:
        parts.append(0)
    filevers = ", ".join(str(x) for x in parts)
    dotted = ".".join(str(x) for x in parts)
    text = read_text(path)
    text = re.sub(
        r"filevers=\([^)]+\)",
        f"filevers=({filevers})",
        text,
        count=1,
    )
    text = re.sub(
        r"prodvers=\([^)]+\)",
        f"prodvers=({filevers})",
        text,
        count=1,
    )
    text = re.sub(
        r'StringStruct\("FileVersion",\s*"[^"]+"\)',
        f'StringStruct("FileVersion", "{dotted}")',
        text,
        count=1,
    )
    text = re.sub(
        r'StringStruct\("ProductVersion",\s*"[^"]+"\)',
        f'StringStruct("ProductVersion", "{dotted}")',
        text,
        count=1,
    )
    write_text(path, text)


def bump_compila_bat(path: Path, new_version: str) -> None:
    text = read_text(path)
    new_text, n = re.subn(
        r"echo Compilazione Ricerca Testuale Accesso Digitale v[\d.]+",
        f"echo Compilazione Ricerca Testuale Accesso Digitale v{new_version}",
        text,
        count=1,
    )
    if n != 1:
        die(f"compila.bat non aggiornato ({path})")
    write_text(path, new_text)


def bump_make_addon(path: Path, new_version: str) -> None:
    """make_addon.py legge la versione dal manifest: nessun edit necessario."""
    return


def bump_readme_title(path: Path, new_version: str) -> None:
    text = read_text(path)
    new_text, n = re.subn(
        r"\(v\d+\.\d+(?:\.\d+)?\)",
        f"(v{new_version})",
        text,
        count=1,
    )
    if n != 1:
        die(f"Titolo versione non aggiornato in README.md")
    write_text(path, new_text)


def bump_doc_html(path: Path, new_version: str) -> None:
    text = read_text(path)
    text = re.sub(
        r"(Ricerca Testuale Accesso Digitale v)\d+\.\d+(?:\.\d+)?",
        rf"\g<1>{new_version}",
        text,
    )
    write_text(path, text)


def prepend_changelog(path: Path, new_version: str) -> None:
    text = read_text(path)
    header = f"v{new_version}\n"
    if text.startswith(header) or text.startswith(f"v{new_version}\r"):
        return
    stub = (
        f"v{new_version}\n"
        f"- (compila qui i punti novità prima del rilascio)\n"
        f"\n"
    )
    write_text(path, stub + text)


def write_notes_template(version: str) -> Path:
    notes_dir = ROOT / "docs"
    notes_dir.mkdir(exist_ok=True)
    path = notes_dir / f"NOTE_RILASCIO_{version}.txt"
    body = f"""🌟 Novità della Versione {version}
(Copia questo testo nelle release GitHub — completa i bullet con le novità reali)

🇮🇹 Italiano

- (punto 1)
- (punto 2)
- (punto 3)

🇬🇧 English

- (point 1)
- (point 2)
- (point 3)

---

Titoli release consigliati

Add-on:
Ricerca Testuale Accesso Digitale - NVDA Add-on v{version}
Tag: v{version}
Asset: ricerca_testuale_accesso_digitale-{version}.nvda-addon

Standalone:
Ricerca Testuale Accesso Digitale Standalone v{version}
Tag: app-v{version}
Asset: Setup_RicercaTestualeAccessoDigitale_v{version}.exe
       RicercaTestualeAccessoDigitale_Portable_v{version}.exe

---

GitHub Desktop — Commit

Summary:
Aggiornamento Standalone e Add-on alla v{version}

Description:
(scrivi 2-4 righe sulle novità)

---

Store NVDA (addon-datastore)

Form: {DATASTORE_FORM}
Download URL:
{GITHUB_REPO}/releases/download/v{version}/ricerca_testuale_accesso_digitale-{version}.nvda-addon
Source URL: {GITHUB_REPO}
Publisher: Maurizio Barra
Channel: stable
License Name: GPL v2
License URL: https://www.gnu.org/licenses/gpl-2.0.html
"""
    write_text(path, body)
    return path


def print_manual_checklist(version: str, include_build_hints: bool = True) -> None:
    print("\n=== Checklist MANUALE (sempre tua) ===")
    print("1. Completare i testi novità (WhatsNew / changelog / note rilascio).")
    print("2. Testare Standalone (python app_gui.py o exe).")
    print("3. Testare Add-on (installa .nvda-addon, smoke test).")
    if include_build_hints:
        print("4. Standalone\\compila.bat → Inno Setup → rinomina Portable.")
        print("5. Eliminare build/ e *.spec; NON committare dist/InstallerOutput.")
        print("6. GitHub Desktop: solo sorgenti + .nvda-addon → Commit → Push.")
        print(f"7. Due Release Web: v{version} (Add-on) e app-v{version} (Standalone).")
        print("8. Issue addon-datastore con Download URL del .nvda-addon.")
    print("\nNON automatico (di proposito): il contenuto delle novità e i test.")


def cmd_bump(args: argparse.Namespace) -> None:
    new_version = args.version.strip()
    if not VERSION_RE.match(new_version):
        die("Versione non valida. Usa forma X.Y o X.Y.Z (es. 1.5.2)")

    current = extract_version_from_app(FILES["standalone_app"])
    if current and version_tuple(new_version) < version_tuple(current):
        die(f"La nuova versione {new_version} è inferiore a quella attuale {current}")

    print(f"=== Bump versione → {new_version} ===\n")
    replace_app_version(FILES["standalone_app"], new_version)
    print("  OK Standalone/app_gui.py")
    replace_app_version(FILES["addon_init"], new_version)
    print("  OK addon/.../__init__.py")
    bump_manifest(FILES["manifest"], new_version)
    print("  OK addon/manifest.ini")
    bump_setup_iss(FILES["setup_iss"], new_version)
    print("  OK Standalone/setup.iss")
    bump_version_txt(FILES["version_txt"], new_version)
    print("  OK Standalone/version.txt")
    bump_compila_bat(FILES["compila_bat"], new_version)
    print("  OK Standalone/compila.bat")
    bump_make_addon(FILES["make_addon"], new_version)
    print("  OK make_addon.py (legge version dal manifest)")
    bump_readme_title(FILES["readme"], new_version)
    print("  OK README.md (titolo)")
    bump_doc_html(FILES["doc_it"], new_version)
    bump_doc_html(FILES["doc_en"], new_version)
    print("  OK addon/doc it+en (titoli)")
    prepend_changelog(FILES["changelog"], new_version)
    print("  OK Standalone/changelog.txt (stub in cima)")

    notes = write_notes_template(new_version)
    print(f"  OK note template: {notes.relative_to(ROOT)}")

    print("\nRicostruzione pacchetto Add-on...")
    build_addon()
    print("\nBump completato.")
    print_manual_checklist(new_version)


def build_addon() -> Path:
    """Ricostruisce .nvda-addon leggendo la versione da manifest.ini."""
    version = extract_version_from_manifest(FILES["manifest"])
    if not version:
        die("Versione mancante in manifest.ini")

    addon_dir = ROOT / "addon"
    output_name = f"ricerca_testuale_accesso_digitale-{version}.nvda-addon"
    output_path = ROOT / output_name
    skip_dirs = {"__pycache__"}

    # Rimuovi eventuali pacchetti .nvda-addon vecchi in root (stesso progetto)
    for old in ROOT.glob("ricerca_testuale_accesso_digitale-*.nvda-addon"):
        if old.resolve() != output_path.resolve():
            try:
                old.unlink()
                print(f"  Rimosso vecchio pacchetto: {old.name}")
            except OSError as e:
                print(f"  Avviso: non posso rimuovere {old.name}: {e}")

    print(f"Creazione del pacchetto NVDA per la versione {version}...")
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(addon_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if file.endswith(".pyc"):
                    continue
                full_path = Path(root) / file
                arcname = full_path.relative_to(addon_dir).as_posix()
                zipf.write(full_path, arcname)
                print(f"  Aggiunto: {arcname}")

    print(f"Pacchetto completato: {output_name}")
    return output_path


def cmd_addon(_: argparse.Namespace) -> None:
    build_addon()
    version = extract_version_from_manifest(FILES["manifest"])
    print_manual_checklist(version or "?", include_build_hints=False)


def cmd_notes(args: argparse.Namespace) -> None:
    version = args.version.strip() if args.version else extract_version_from_manifest(FILES["manifest"])
    if not version:
        die("Specifica una versione oppure allinea il manifest.")
    if not VERSION_RE.match(version):
        die("Versione non valida.")
    path = write_notes_template(version)
    print(f"Note generate: {path}")
    print("Aprile e completa i bullet IT/EN prima delle Release.")


def cmd_summary(args: argparse.Namespace) -> None:
    version = args.version.strip() if args.version else extract_version_from_app(FILES["standalone_app"])
    if not version:
        die("Versione non trovata.")
    print(f"=== Riepilogo rilascio v{version} ===\n")
    print("Commit GitHub Desktop")
    print(f"  Summary: Aggiornamento Standalone e Add-on alla v{version}")
    print("  Description: (2-4 righe dalle note)\n")
    print("Release Add-on")
    print(f"  Tag: v{version}")
    print(f"  Title: Ricerca Testuale Accesso Digitale - NVDA Add-on v{version}")
    print(f"  Asset: ricerca_testuale_accesso_digitale-{version}.nvda-addon\n")
    print("Release Standalone")
    print(f"  Tag: app-v{version}")
    print(f"  Title: Ricerca Testuale Accesso Digitale Standalone v{version}")
    print(f"  Asset: Setup_RicercaTestualeAccessoDigitale_v{version}.exe")
    print(f"         RicercaTestualeAccessoDigitale_Portable_v{version}.exe\n")
    print("Datastore")
    print(f"  Form: {DATASTORE_FORM}")
    print(
        f"  Download URL: {GITHUB_REPO}/releases/download/v{version}/"
        f"ricerca_testuale_accesso_digitale-{version}.nvda-addon"
    )
    notes = ROOT / "docs" / f"NOTE_RILASCIO_{version}.txt"
    if notes.exists():
        print(f"\nTesto novità: {notes}")
    print_manual_checklist(version)


def main() -> None:
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(
        description="RTAD — preparazione rilascio Standalone + Add-on",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="Verifica allineamento versioni")
    p_check.set_defaults(func=cmd_check)

    p_bump = sub.add_parser("bump", help="Aggiorna versione in tutti i file tecnici")
    p_bump.add_argument("version", help="Nuova versione, es. 1.5.2")
    p_bump.set_defaults(func=cmd_bump)

    p_notes = sub.add_parser("notes", help="Genera/aggiorna template note di rilascio")
    p_notes.add_argument("version", nargs="?", default=None)
    p_notes.set_defaults(func=cmd_notes)

    p_addon = sub.add_parser("addon", help="Ricostruisce il pacchetto .nvda-addon")
    p_addon.set_defaults(func=cmd_addon)

    p_sum = sub.add_parser("summary", help="Stampa testi utili per Desktop/Release/Store")
    p_sum.add_argument("version", nargs="?", default=None)
    p_sum.set_defaults(func=cmd_summary)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()