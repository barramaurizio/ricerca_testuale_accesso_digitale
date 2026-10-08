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

## Stato attuale (08/10/2026)
- **Ultima pubblicata:** `1.6.5` — GitHub (`v1.6.5` + `app-v1.6.5`) + Add-on Store
  (DataStore #12044 → #12045 accettata). **Non ripubblicare / non hotfixare 1.6.5.**
- **In corso:** `1.6.6` (codice + docs pronti in locale; da testare / compilare / pubblicare)
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale
- Gemello SA ↔ Add-on su OCR/immagini (`rtad_ocr.py`) + guida
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc` (check versioni/docs prima di «vai»)

### Cosa c’è in 1.6.6 (riassunto)
1. Dialogo unico «Tutto sull’immagine» + batch cartella (`.rtad.txt`).
2. **PDF multi-font / ToUnicode per font** (test `docs/samples/rtad-multifont-tounicode.pdf`).
3. **Gemini API:** tolto `temperature` da `generationConfig` (avviso AI Studio 07/10/2026).
4. Dopo pubblicazione: audio/video (priorità Maurizio); «Apri con» / lettore strutturato in lista.

### Cosa c’è in 1.6.5 (storico)
- Fix 3BMeteo / SVG-WebP; SA Explorer sottomenù PDF/documenti

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Dopo il blocco immagini (voluto da Maurizio)
- Descrizione **audio/video** (anche senza feedback esterni)
- Canale YouTube **Accesso Digitale** — chat Cursor dedicata, stesso workspace OK

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «1.6.5…»)
- Chat separata per YouTube / brand
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«1.6.5: partiamo dal fix 3BMeteo / formato immagine sconosciuto su NVDA+Shift+G»
Leggere prima questo file e `docs/ROADMAP_DOPO_1.5.0.md`.
