# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Piano operativo 1.7.2:** `docs/PIANO_1.7.2.md` (batch media + B0).  
Piano chiuso 1.7.1: `docs/PIANO_1.7.1.md`.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (15/10/2026)
- **Ultima / pronta al rilascio:** `1.7.2` — batch media + B0 + glossario. Vedi `docs/PIANO_1.7.2.md` e `docs/NOTE_RILASCIO_1.7.2.txt`.
- **Precedente pubblicata:** `1.7.1` — PDF-scansione + scheda + focus. **Non hotfixare.**
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, guida
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`

### Cosa c’è in 1.7.2 (pronta)
1. **P0** Batch cartella audio/video → `.rtad.txt` accanto a ogni file.
2. **P1** B0: ricerca mirata nei `.rtad.txt` già salvati ([AV] + timestamp).
3. **P2** Glossario post-trascrizione (accent-fold; rewrite `.rtad.txt` all’apertura).

### Cosa c’è in 1.7.1
1. PDF scansione: dialogo Descrivi / Apri lettore; stem/cartella PDF originale; Stampa testo.
2. Scheda tecnica: Data analisi + Ultima modifica originale (Esplora).
3. Focus freccia lettore dopo iconizza.

### Cosa c’è in 1.7.0 (pubblicata)
1. Lettore documento (cerca/titoli/esterno).
2. Spazi PDF tipici; toast fine-ricerca meno invasivo.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.7.2»)
- Chat separata per YouTube / brand
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«1.7.2: batch media / B0»
Leggere prima questo file, `docs/PIANO_1.7.2.md` e `docs/ROADMAP_DOPO_1.5.0.md`.
