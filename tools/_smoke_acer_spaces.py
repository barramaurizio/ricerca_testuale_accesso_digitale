# -*- coding: utf-8 -*-
"""Verifica spazi sul manuale Acer dopo fix U+0000 U+0003."""
import sys

ROOT = __file__.rsplit("\\", 2)[0]
sys.path.insert(0, ROOT + "\\Standalone")
import wx

app = wx.App(False)
import app_gui as ag

path = r"D:\Documenti\User Manual_Acer_1.0_A_A.pdf"
text = "\n".join(ag.extract_lines_from_pdf(path))
checks = [
    ("Dispositivo con batteria rimovibile", True),
    ("Dispositivoconbatteriarimovibile", False),
    ("Fare riposare gli", True),
    ("Fareriposaregli", False),
    ("scarsa leggibilità dello schermo", True),
    ("scarsalegibilitàdelloschermo", False),
]
ok = True
for s, want in checks:
    found = s in text or s.replace("à", "a") in text.replace("à", "a")
    status = "OK" if found == want else "FAIL"
    if found != want:
        ok = False
    print(status, "want" if want else "absent", repr(s), "->", found)

# sample
i = text.find("Dispositivo con")
print("sample:", repr(text[i : i + 80] if i >= 0 else "n/a"))
i2 = text.lower().find("leggibilit")
print("leggib:", repr(text[i2 - 20 : i2 + 50] if i2 >= 0 else "n/a"))
print("ALL OK" if ok else "SOME FAILED")
