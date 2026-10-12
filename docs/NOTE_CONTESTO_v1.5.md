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

## Stato attuale (12/10/2026)
- **Ultima pubblicata:** `1.6.7` — GitHub + DataStore (#12099 → #12100). **Non hotfixare 1.6.7.**
- **1.6.8:** codice/docs pronti (`NOTE_RILASCIO_1.6.8.txt`) — da pubblicare se non ancora online.
- **In corso:** `1.6.9` — PDF TOC/link, titoli lunghi report, guida ricerca via `.rtad.txt`
  (`docs/PIANO_1.6.9.md`, `docs/NOTE_RILASCIO_1.6.9.txt`).
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, guida
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`

### Cosa c’è in 1.6.9 (in corso)
1. PDF strutturati (sommario/TOC + link URI) in «Leggi documento…».
2. Stem nomi `.rtad.txt` fino a ~200 caratteri (titoli YouTube lunghi).
3. Guida: cercare parole nei video nei `.rtad.txt` già salvati.
4. *(opzionale)* batch media / B0 MVP su cache.

### Cosa c’è in 1.6.8 (pronta)
1. Documenti strutturati DOCX/EPUB + PDF onesto; «Leggi documento…» anche Add-on.
2. UX salvataggi: report media + auto-salvataggio risultati.
3. Sfoglia cartella **o** singolo file.
4. Restano hub audio/video 1.6.7.

### Dopo 1.6.9
- Batch media; B0 MVP ricerca su transcript in cache; poi «trascrivi e cerca» opt-in
- Whisper locale opt-in; «Apri con» / associazione Windows
- Canale YouTube **Accesso Digitale** — chat Cursor dedicata, stesso workspace OK

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «1.6.9…»)
- Chat separata per YouTube / brand
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«1.6.9: continuiamo da PDF TOC / titoli report / batch media»
Leggere prima questo file e `docs/PIANO_1.6.9.md`.
