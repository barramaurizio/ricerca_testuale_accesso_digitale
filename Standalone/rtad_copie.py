# -*- coding: utf-8 -*-
"""RTAD — trova altre copie Standalone sul PC (elenco + pulizia guidata).

Spirito: amico, non demone.
- Di default solo elenca e spiega.
- Rimozione solo Portable / Download / Desktop, e solo con consenso esplicito.
- Mai tocca %AppData%\\Roaming\\RTAD_Standalone (chiavi API).
- Un Installer nel Registro si disinstalla da Impostazioni Windows, non in silenzio.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import winreg  # type: ignore
except ImportError:
    winreg = None  # type: ignore


_EXE_PATTERNS = (
    "Ricerca Testuale Accesso Digitale.exe",
    "RicercaTestualeAccessoDigitale_Portable",
    "Ricerca_Testuale_v",
    "Setup_RicercaTestualeAccessoDigitale",
)

_NAME_RE = re.compile(
    r"Ricerca Testuale|RicercaTestuale|Ricerca_Testuale|Accesso Digitale",
    re.I,
)


def managed_updates_dir() -> str:
    """Cartella aggiornamenti SA gestita dal programma (non «copia sicura»)."""
    local = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local"
    )
    return os.path.normpath(os.path.join(local, "RTAD_Standalone", "updates"))


def is_managed_updates_path(path: str) -> bool:
    """True se il file sta sotto %LocalAppData%\\RTAD_Standalone\\updates\\."""
    prefix = os.path.normcase(managed_updates_dir())
    try:
        low = os.path.normcase(os.path.normpath(path or ""))
    except Exception:
        return False
    return low == prefix or low.startswith(prefix + os.sep)


def _user_roots() -> List[str]:
    home = os.path.expanduser("~")
    roots = [
        os.path.join(home, "Downloads"),
        os.path.join(home, "Desktop"),
        os.path.join(home, "Documents"),
        os.path.join(home, "OneDrive", "Downloads"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
        managed_updates_dir(),
        os.environ.get("ProgramFiles", ""),
        os.environ.get("ProgramFiles(x86)", ""),
    ]
    out = []
    seen = set()
    for r in roots:
        if not r:
            continue
        try:
            r = os.path.normpath(r)
        except Exception:
            continue
        key = r.lower()
        if key in seen:
            continue
        if os.path.isdir(r):
            seen.add(key)
            out.append(r)
    return out


def _desktop_dirs() -> List[str]:
    home = os.path.expanduser("~")
    dirs = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "OneDrive", "Desktop"),
    ]
    try:
        import ctypes.wintypes

        buf = ctypes.create_unicode_buffer(260)
        # CSIDL_DESKTOPDIRECTORY = 0x10
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf) == 0:
            p = buf.value
            if p and os.path.isdir(p):
                dirs.insert(0, p)
    except Exception:
        pass
    out = []
    seen = set()
    for d in dirs:
        key = os.path.normpath(d).lower()
        if key not in seen and os.path.isdir(d):
            seen.add(key)
            out.append(d)
    return out


def scan_registry_installers() -> List[Dict[str, str]]:
    """Voci Uninstall che sembrano RTAD (Installer)."""
    hits: List[Dict[str, str]] = []
    if winreg is None:
        return hits
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, path in roots:
        try:
            with winreg.OpenKey(hive, path) as root:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(root, i)
                        i += 1
                    except OSError:
                        break
                    try:
                        with winreg.OpenKey(root, sub) as k:
                            def _get(name: str) -> str:
                                try:
                                    return str(winreg.QueryValueEx(k, name)[0] or "")
                                except OSError:
                                    return ""

                            display = _get("DisplayName")
                            if not display or not _NAME_RE.search(display):
                                continue
                            hits.append(
                                {
                                    "display": display,
                                    "version": _get("DisplayVersion"),
                                    "location": _get("InstallLocation"),
                                    "uninstall": _get("UninstallString"),
                                }
                            )
                    except OSError:
                        continue
        except OSError:
            continue
    return hits


def _name_matches_exe(name: str) -> bool:
    n = name or ""
    if n == "Ricerca Testuale Accesso Digitale.exe":
        return True
    for pref in _EXE_PATTERNS[1:]:
        if n.startswith(pref) and n.lower().endswith(".exe"):
            return True
    return False


def scan_exe_files(max_depth: int = 4) -> List[Dict[str, str]]:
    """Exe tipici RTAD sotto Download/Desktop/Documenti/Program Files…"""
    found: List[Dict[str, str]] = []
    seen = set()
    for root in _user_roots():
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                rel = os.path.relpath(dirpath, root)
                depth = 0 if rel == "." else rel.count(os.sep) + 1
                if depth > max_depth:
                    dirnames[:] = []
                    continue
                # Evita cartelle enormi / rumore
                skip = {
                    "node_modules",
                    ".git",
                    "Windows",
                    "WinSxS",
                    "$Recycle.Bin",
                }
                dirnames[:] = [d for d in dirnames if d not in skip]
                for fn in filenames:
                    if not _name_matches_exe(fn):
                        continue
                    full = os.path.join(dirpath, fn)
                    key = os.path.normcase(full)
                    if key in seen:
                        continue
                    seen.add(key)
                    try:
                        st = os.stat(full)
                        mtime = datetime.fromtimestamp(st.st_mtime).strftime(
                            "%Y-%m-%d %H:%M"
                        )
                        size = str(st.st_size)
                    except OSError:
                        mtime, size = "?", "?"
                    found.append(
                        {
                            "path": full,
                            "mtime": mtime,
                            "size": size,
                            "name": fn,
                        }
                    )
        except OSError:
            continue
    found.sort(key=lambda x: x["path"].lower())
    return found


def scan_desktop_shortcuts() -> List[Dict[str, str]]:
    """Scorciatoie .lnk sul Desktop che puntano a RTAD."""
    hits: List[Dict[str, str]] = []
    shell = None
    try:
        import win32com.client as w32  # type: ignore

        shell = w32.Dispatch("WScript.Shell")
    except Exception:
        try:
            import comtypes.client  # type: ignore

            shell = comtypes.client.CreateObject("WScript.Shell")
        except Exception:
            shell = None

    if shell is None:
        return hits

    for desk in _desktop_dirs():
        try:
            for fn in os.listdir(desk):
                if not fn.lower().endswith(".lnk"):
                    continue
                full = os.path.join(desk, fn)
                try:
                    sc = shell.CreateShortcut(full)
                    target = str(getattr(sc, "TargetPath", "") or "")
                except Exception:
                    continue
                if target and _NAME_RE.search(target):
                    hits.append({"shortcut": full, "target": target})
        except OSError:
            continue
    return hits


def _is_dev_tree_path(path: str) -> bool:
    """True se sembra output di compilazione / cartella progetto (NON cancellare)."""
    low = os.path.normpath(path or "").lower()
    markers = (
        "\\standalone\\build\\",
        "\\standalone\\dist\\",
        "\\installeroutput\\",
        "\\ricercatestualeaccessodigitalegithub\\",
        "\\.git\\",
        "\\build\\ricerca testuale",
        "\\dist\\ricerca testuale",
    )
    return any(m in low for m in markers)


def _is_user_drop_folder(path: str) -> bool:
    """True se il file sta direttamente in Download/Desktop (non in sottoprogetti)."""
    parent = os.path.normcase(os.path.dirname(os.path.normpath(path or "")))
    if not parent:
        return False
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Downloads"),
        os.path.join(home, "Desktop"),
        os.path.join(home, "OneDrive", "Downloads"),
        os.path.join(home, "OneDrive", "Desktop"),
    ]
    for d in _desktop_dirs():
        candidates.append(d)
    drops = {os.path.normcase(os.path.normpath(c)) for c in candidates if c}
    return parent in drops


def _looks_like_release_package(name: str) -> bool:
    n = (name or "").lower()
    return (
        "portable" in n
        or n.startswith("ricerca_testuale_v")
        or n.startswith("setup_ricercatestuale")
        or n.startswith("setup_ricerca")
    )


def classify_exe(path: str) -> str:
    """'installer_dir' | 'managed_updates' | 'release_download' | 'dev_build' | 'other'."""
    p = os.path.normpath(path or "")
    low = p.lower()
    name = os.path.basename(p)
    if is_managed_updates_path(p):
        return "managed_updates"
    if "\\program files" in low or "\\local\\programs\\" in low:
        return "installer_dir"
    if _is_dev_tree_path(p):
        return "dev_build"
    # Solo pacchetti di rilascio lasciati in Download/Desktop = «sicuri» da rimuovere
    if _looks_like_release_package(name) and _is_user_drop_folder(p):
        return "release_download"
    if "\\downloads\\" in low or "\\desktop\\" in low:
        return "other"
    return "other"


def is_safe_to_delete(path: str) -> bool:
    """True solo per Setup/Portable lasciati in Download/Desktop.

    Mai: Installer in Local\\Programs, cartella updates gestita, chiavi Roaming,
    cartelle build/dist del progetto.
    """
    if not path or not os.path.isfile(path):
        return False
    low = os.path.normpath(path).lower()
    if "\\appdata\\roaming\\rtad" in low:
        return False
    if is_managed_updates_path(path):
        return False
    if classify_exe(path) == "installer_dir":
        return False
    if _is_dev_tree_path(path):
        return False
    return classify_exe(path) == "release_download"


def looks_like_confusion(
    reg_hits: List[Dict[str, str]],
    exe_hits: List[Dict[str, str]],
    lnk_hits: Optional[List[Dict[str, str]]] = None,
) -> bool:
    """True se sembra ci siano più copie «confondibili» per un utente tipico.

    Non conta le cartelle di compilazione del progetto (dev_build).
    Conta: più Installer, Setup/Portable in Download, scorciatoie che
    puntano a exe diversi (es. Installer + vecchia Portable).
    """
    if len(reg_hits) >= 2:
        return True
    safe = [e for e in exe_hits if is_safe_to_delete(e.get("path", ""))]
    has_pf = any(classify_exe(e.get("path", "")) == "installer_dir" for e in exe_hits)
    if has_pf and safe:
        return True
    if len(safe) >= 2:
        return True
    # Due scorciatoie verso exe diversi → tipico caso «quale apro?»
    if lnk_hits and len(lnk_hits) >= 2:
        targets = {
            os.path.normcase(os.path.normpath(L.get("target") or ""))
            for L in lnk_hits
            if L.get("target")
        }
        if len(targets) >= 2:
            return True
    return False


def build_report_text(
    reg_hits: Optional[List[Dict[str, str]]] = None,
    exe_hits: Optional[List[Dict[str, str]]] = None,
    lnk_hits: Optional[List[Dict[str, str]]] = None,
) -> str:
    if reg_hits is None:
        reg_hits = scan_registry_installers()
    if exe_hits is None:
        exe_hits = scan_exe_files()
    if lnk_hits is None:
        lnk_hits = scan_desktop_shortcuts()

    lines = [
        "RTAD - rapporto copie Standalone",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Utente: {os.environ.get('USERNAME', '')}",
        f"PC: {os.environ.get('COMPUTERNAME', '')}",
        "",
        "=== 1) Installazioni nel Registro (Installer) ===",
    ]
    if not reg_hits:
        lines.append("(nessuna voce Installer nel Registro)")
    else:
        for h in reg_hits:
            lines.append(f"- {h.get('display', '')}  (v{h.get('version', '')})")
            if h.get("location"):
                lines.append(f"    Cartella: {h['location']}")
            if h.get("uninstall"):
                lines.append(f"    Disinstalla: {h['uninstall']}")

    lines.extend(["", "=== 2) File .exe tipici ==="])
    if not exe_hits:
        lines.append("(nessun exe tipico trovato)")
    else:
        for e in exe_hits:
            lines.append(f"- {e['path']}")
            lines.append(f"    Modificato: {e.get('mtime', '')}  Byte: {e.get('size', '')}")
            kind = classify_exe(e["path"])
            if kind == "installer_dir":
                lines.append("    Tipo: Installer installato (non cancellare da qui)")
            elif kind == "managed_updates":
                lines.append(
                    "    Tipo: cartella aggiornamenti RTAD (gestita in automatico; "
                    "non «copia sicura»)"
                )
            elif kind == "release_download":
                lines.append(
                    "    Tipo: pacchetto Setup/Portable in Download/Desktop "
                    "(rimozione guidata possibile)"
                )
            elif kind == "dev_build":
                lines.append(
                    "    Tipo: compilazione / cartella progetto "
                    "(NON rimuovere con «copie sicure»)"
                )
            else:
                lines.append("    Tipo: altro (solo elenco; non in rimozione automatica)")

    lines.extend(["", "=== 3) Scorciatoie .lnk sul Desktop ==="])
    if not lnk_hits:
        lines.append("(nessuna scorciatoia RTAD sul Desktop, oppure non leggibile)")
    else:
        for L in lnk_hits:
            lines.append(f"- {L['shortcut']}")
            lines.append(f"    Punta a: {L['target']}")

    lines.extend(
        [
            "",
            "=== Note ===",
            "- NON cancellare: %AppData%\\Roaming\\RTAD_Standalone (chiavi API).",
            "- NON cancellare a mano: %LocalAppData%\\RTAD_Standalone\\updates "
            "(aggiornamenti automatici; il programma la ripulisce).",
            "- Installer: Impostazioni Windows → App → disinstalla, oppure unins000.exe.",
            "- Portable/Download/Desktop (scaricati a mano): si possono cancellare "
            "con consenso (Strumenti).",
            "- Consiglio: tieni UNA sola copia (Setup OPPURE Portable) e aggiorna quella.",
            "",
            "FINE RAPPORTO.",
        ]
    )
    return "\n".join(lines)


def write_report_to_desktop(text: str) -> str:
    """Scrive RTAD_copie_trovate.txt sul Desktop. Restituisce il path."""
    desks = _desktop_dirs()
    desk = desks[0] if desks else os.path.join(os.path.expanduser("~"), "Desktop")
    path = os.path.join(desk, "RTAD_copie_trovate.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")
    return path


def delete_safe_exes(paths: List[str]) -> Tuple[List[str], List[str]]:
    """Cancella solo path classificati sicuri. Ritorna (ok, falliti)."""
    ok, failed = [], []
    for p in paths:
        if not is_safe_to_delete(p):
            failed.append(p)
            continue
        try:
            os.remove(p)
            ok.append(p)
        except OSError:
            failed.append(p)
    return ok, failed


def scan_all() -> Dict[str, list]:
    """Scansione completa (può richiedere qualche secondo)."""
    reg = scan_registry_installers()
    exes = scan_exe_files()
    lnks = scan_desktop_shortcuts()
    return {"registry": reg, "exes": exes, "shortcuts": lnks}
