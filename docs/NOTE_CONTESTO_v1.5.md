# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor. Piano dettagliato: `docs/ROADMAP_DOPO_1.5.0.md`.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (09/10/2026)
- **Ultima pubblicata:** `1.6.6` — GitHub (`v1.6.6` + `app-v1.6.6`) + Add-on Store
  (DataStore #12055 → #12056 accettata). **Non ripubblicare / non hotfixare 1.6.6.**
- **Lavoro corrente:** `1.6.7` — audio/video MVP (Fase N in roadmap).
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py` (nuovo), guida
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc` (check versioni/docs prima di «vai»)

### Cosa c’è in 1.6.6 (storico / pubblicata)
1. Dialogo unico «Tutto sull’immagine» + batch cartella (`.rtad.txt`).
2. Explorer: «Analizza immagini di questa cartella» + «Tutto sull’immagine» nel sottomenù.
3. **PDF multi-font / ToUnicode per font** (anche `sample-multilingual-text.pdf`).
4. **Gemini API:** tolto `temperature` da `generationConfig` (avviso AI Studio 07/10/2026).

### Obiettivo 1.6.7 (in corso)
1. Modulo gemello `rtad_media.py`.
2. Scheda tecnica audio/video (locale).
3. Dialogo «Tutto sull’audio/video» (scheda + riassunto Gemini opt-in + trascrizione Gemini opt-in).
4. Menu / contestuale / CLI / Explorer sui formati media principali.
5. Guida + novità IT/EN.
6. **No** Whisper di massa; **no** batch cartella media in questo taglio; **no** lettore documenti strutturato.

### Dopo 1.6.7
- Completamenti media (batch, ricerca nel transcript, Whisper locale opt-in) in 1.6.8+
- **Lettore documenti strutturato** (TOC/capitoli, titoli, link — PDF lunghi / libri)
- «Apri con» / associazione Windows — lista d’attesa
- Canale YouTube **Accesso Digitale** — chat Cursor dedicata, stesso workspace OK

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «1.6.7…»)
- Chat separata per YouTube / brand
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«1.6.7: continuiamo dal dialogo Tutto sull’audio/video / scheda tecnica»
Leggere prima questo file e `docs/ROADMAP_DOPO_1.5.0.md` (Fase N).
