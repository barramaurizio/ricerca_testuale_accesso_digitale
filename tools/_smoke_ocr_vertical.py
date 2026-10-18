# -*- coding: utf-8 -*-
"""Prova OCR «testo in verticale» → orizzontale (1.7.5).

Uso (dalla root del repo):
  python tools/_smoke_ocr_vertical.py
  python tools/_smoke_ocr_vertical.py percorso\\foto.jpg

Cosa ascoltare / leggere:
  - PRIMA (simulato): una lettera per riga → NVDA le dice staccate
  - DOPO (reflow / OCR reale): parola in una riga → NVDA dice «CIAO»
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SA = os.path.join(ROOT, "Standalone")
sys.path.insert(0, SA)

import rtad_ocr  # noqa: E402

FIXTURE = os.path.join(ROOT, "tools", "fixture_ocr_vertical_CIAO.png")


def _show(title: str, text: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)
    lines = (text or "").splitlines()
    print(f"Righe: {len(lines)}")
    print("--- testo ---")
    print(text if text else "(vuoto)")
    print("--- fine ---")
    # Anteprima «come la sente NVDA» (righe lette una dopo l'altra)
    flat = " | ".join(ln.strip() if ln.strip() else "(riga vuota)" for ln in lines)
    print(f"Ascolto tipico NVDA (righe separate da | ): {flat}")


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else FIXTURE
    if not os.path.isfile(path):
        print(f"File non trovato: {path}")
        return 1

    print(f"Immagine: {path}")
    print(f"Motore OCR attivo: {rtad_ocr.active_engine()}")

    # 1) Simulazione del bug (senza OCR): così capisci subito la differenza
    fake_vertical = "\n".join(list("CIAO"))
    _show("1) SIMULAZIONE BUG (una lettera per riga, come prima)", fake_vertical)
    fixed = rtad_ocr.reflow_ocr_vertical_chars(fake_vertical)
    _show("2) STESSO TESTO DOPO reflow (atteso: una riga «CIAO»)", fixed)

    ok_sim = fixed.strip().replace("\n", "") == "CIAO" or fixed.strip() == "CIAO"
    print()
    print("Verifica simulazione:", "OK" if ok_sim else "ATTENZIONE — reflow non ha unito")

    # 2) OCR reale sull'immagine
    if not rtad_ocr.engine_available():
        print()
        print("OCR Windows non disponibile su questo PC — la simulazione basta per il reflow.")
        print(rtad_ocr.engine_status_message())
        return 0 if ok_sim else 2

    print()
    print("Eseguo OCR sull'immagine (può richiedere qualche secondo)…")
    # Svuota eventuale cache su questo file forzando motore fresco:
    # ocr_image_file usa cache; per la prova usiamo path + reflow già interno.
    raw = rtad_ocr.ocr_image_file(path) or ""
    _show("3) OCR REALE (già con reflow interno in 1.7.5)", raw)

    # Mostra anche cosa farebbe ocr_text_for_clipboard(full) come in «Leggi testo»
    if hasattr(rtad_ocr, "ocr_text_for_clipboard"):
        shown = rtad_ocr.ocr_text_for_clipboard(raw, mode="full") or raw
        _show("4) Come in «Leggi testo nell'immagine» (mode=full)", shown)

    print()
    print("COME GIUDICARE OK:")
    print("  - Punto 2 (simulazione): deve esserci CIAO su UNA riga.")
    print("  - Punto 3/4 (OCR reale): se c'e' testo, non devono restare C/I/A/O su 4 righe.")
    print("  - Con NVDA: lettere separate una riga dopo l'altra = KO; parola unica = OK.")
    print()
    print("Cosa incollare in chat se vuoi un controllo:")
    print("  copia l'output di questo script (punti 1-4), oppure")
    print("  in RTAD: Leggi testo OCR e dimmi cosa annuncia NVDA.")
    return 0 if ok_sim else 2


if __name__ == "__main__":
    raise SystemExit(main())
