# -*- coding: utf-8 -*-
import sys

ROOT = __file__.rsplit("\\", 2)[0]
sys.path.insert(0, ROOT + "\\Standalone")
import wx

app = wx.App(False)
import app_gui as ag


def check(path, goods, bads):
    t = "\n".join(ag.extract_lines_from_pdf(path))
    print("===", path)
    ok = True
    for s in goods:
        f = s in t
        print("OK" if f else "FAIL", "want", repr(s), f)
        ok = ok and f
    for s in bads:
        f = s in t
        print("OK" if not f else "FAIL", "absent", repr(s), f)
        ok = ok and not f
    i = t.find("Display braille")
    if i < 0:
        i = t.find("Display")
    print("sample:", repr(t[i : i + 70] if i >= 0 else t[:100]))
    return ok


a = check(
    r"G:\Documenti PC Fujitsu 2\ManualeBarra Braille  Focus 40 Blue.pdf",
    [
        "Display braille aggiornabile",
        "Guida dell'utente",
        "Le informazioni contenute",
    ],
    [
        "Displaybrailleaggiornabile",
        "Leinformazionicontenuteinquestodocumentosono",
    ],
)
b = check(
    r"D:\Documenti\User Manual_Acer_1.0_A_A.pdf",
    [
        "Dispositivo con batteria rimovibile",
        "Fare riposare gli",
    ],
    [
        "Dispositivoconbatteriarimovibile",
        "Fareriposaregli",
    ],
)
print("ALL", "OK" if a and b else "FAIL")
