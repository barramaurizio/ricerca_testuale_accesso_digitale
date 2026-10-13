# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Piano operativo 1.6.9:** `docs/PIANO_1.6.9.md` ← aprire questo in chat nuova.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (13/10/2026)
- **Ultima pubblicata:** `1.6.9` — GitHub + DataStore (#12149 → #12150). **Non hotfixare 1.6.9.**
- **Pronta al rilascio (codice+docs):** `1.7.0` — vedi `docs/PIANO_1.7.0.md` e `docs/NOTE_RILASCIO_1.7.0.txt`.
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, guida
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`

### Cosa c’è in 1.7.0 (pronta)
1. Spazi PDF (TJ + placeholder C0 Acer/braille + de-glue TOC).
2. Lettore documento: cerca Ctrl+F/F3, titoli Ctrl+H, Apri file esterno.
3. Toast fine-ricerca breve; se lettore aperto → solo annuncio.
4. *(dopo 1.7.0)* batch media / B0 cache; focus freccia post-iconizza; PDF criptati.

### Cosa c’è in 1.6.9 (pubblicata)
1. PDF strutturati (TOC/link) + app predefinita.
2. Stem `.rtad.txt` ~220; guida parole nei video via `.rtad.txt`.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.7.0»)
- Chat separata per YouTube / brand
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«1.7.0: rilascio / compila / DataStore»
Leggere prima questo file e `docs/NOTE_RILASCIO_1.7.0.txt`.
