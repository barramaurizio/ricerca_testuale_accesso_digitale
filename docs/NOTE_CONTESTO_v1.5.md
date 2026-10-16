# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Piano corrente:** `docs/PIANO_1.7.3.md` (sidecar stem + xlsx + Trascrivi e cerca).  
Piano chiuso 1.7.2: `docs/PIANO_1.7.2.md`. Piano chiuso 1.7.1: `docs/PIANO_1.7.1.md`.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (16/10/2026)
- **Ultima pubblicata:** `1.7.2` — batch media + B0 + glossario. Vedi `docs/NOTE_RILASCIO_1.7.2.txt`.
- **In rilascio:** `1.7.3` — sidecar stem + xlsx + Trascrivi e cerca. Vedi `docs/NOTE_RILASCIO_1.7.3.txt`. **Non hotfixare 1.7.2.**
- **Prossima dopo 1.7.3:** `1.7.4` — guida HTML completa (Vision/Gemini).
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, guida
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`

### Priorità 1.7.3 (codice + novità pronti — vedi `docs/PIANO_1.7.3.md`)
1. ~~**P0 sidecar stem locale**~~ + ~~orfani Solo AV~~ — fatti (UI Maurizio OK).
2. ~~**P0 Excel `.xlsx`**~~ — fatto (celle, salto riga COM, date; campione PVR OK).
3. ~~**«Trascrivi e cerca»**~~ — fatto (Ctrl+Shift+T; cache poi Gemini max 30; anche orfani).
4. **PDF papà** — solo se arriva campione “strano”; altrimenti dopo.
5. **Guida HTML completa** → **1.7.4**.
6. Workflow Maurizio: install Add-on → `compila.bat` → Inno → GitHub (NOTE_RILASCIO).

### Cosa c’è in 1.7.2 (pubblicata)
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
- Nuova chat per ogni versione RTAD (es. «RTAD 1.7.3»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.7.3: sidecar stem + Excel xlsx + Trascrivi e cerca»
Leggere prima questo file e `docs/ROADMAP_DOPO_1.5.0.md`; creare `docs/PIANO_1.7.3.md`.
