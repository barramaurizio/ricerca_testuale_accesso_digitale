# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Piano operativo 1.7.1:** `docs/PIANO_1.7.1.md` (pronta al rilascio).

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (14/10/2026)
- **Ultima pubblicata:** `1.7.0` — GitHub + DataStore (#12178 → #12179). **Non hotfixare 1.7.0.**
- **In rilascio:** `1.7.1` — codice + docs OK; pacchetto `ricerca_testuale_accesso_digitale-1.7.1.nvda-addon`. Vedi `docs/NOTE_RILASCIO_1.7.1.txt`.
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, guida
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`

### Cosa c’è in 1.7.1
1. PDF scansione: dialogo Descrivi / Apri lettore; stem/cartella PDF originale; Stampa testo.
2. Scheda tecnica: Data analisi + Ultima modifica originale (Esplora).
3. Focus freccia lettore dopo iconizza.
4. Batch media / B0 → **1.7.2+**.

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
Leggere prima questo file e `docs/ROADMAP_DOPO_1.5.0.md`.
