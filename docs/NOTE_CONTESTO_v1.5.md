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

## Stato attuale (07/10/2026)
- **Ultima pubblicata:** `1.6.4` — GitHub (`v1.6.4` + `app-v1.6.4`) + Add-on Store
  (DataStore #12027 → #12028 accettata). **Non ripubblicare / non hotfixare 1.6.4.**
- **Lavoro corrente:** `1.6.5` — chat dedicata (07/10)
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale
- Gemello SA ↔ Add-on su OCR/immagini (`rtad_ocr.py`)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc` (check versioni/docs prima di «vai»)

### Cosa c’è in 1.6.4 (riassunto)
- Descrivi da URL / Appunti / cattura (gemello); CLI `--describe-url` / `--alt` / `--describe-pdf`
- Add-on: `NVDA+Shift+G` su figura web o file in Explorer/Desktop
- Alt-text breve + Alt-text/descrizione; Descrivi da PDF; elenco per tipo `[ELENCO]`
- Fix: Shift+G non riusa file selezionato in Explorer in secondo piano
- Restano Gemini/Vision/Explorer 1.6.3, notifica 1.6.2, ZIP 1.6.1

## Scope 1.6.5 (decisione 07/10 con Maurizio) — codice pronto al re-test SA
1. **Fix 3BMeteo / icone web** — OK (Maurizio: Shift+G ok).
2. **Sottomenù Explorer documenti** — SA:
   - PDF: Apri questo PDF / Leggi testo / Copia testo / Descrivi immagini
   - docx, odt, txt, md, epub, html, htm, rtf, csv, log: Apri / Leggi / Copia
   - «Apri» imposta percorso sul **file** (non solo cartella)
3. NVDA Add-on: **non** registra shell Explorer (limite piattaforma); resta Shift+G / Strumenti.

**Rimandati / dopo 1.6.5:**
- Dialogo unico + batch → `1.6.6`
- **PDF multi-font / ToUnicode** (es. `sample-multilingual-text.pdf`): oggi
  l’estrattore unisce tutte le CMap in una sola → testo «spazzatura» su
  PDF con più font/lingue; Edge/NVDA leggono bene. Serve CMap **per font**
  + codespace 1/2 byte. Candidato forte in `1.6.6` o subito dopo.
- Audio/video (priorità Maurizio)
- «Apri con» / app predefinita Windows (se richiesto)
- **Lettore documenti strutturato** (capitoli/TOC, titoli, link, paragrafi;
  non solo testo piano) — per PDF lunghi / libretti / libri.

**Fix 07/10 pomeriggio:** «Apri questo PDF/documento» apre con app
  predefinita + voce in lista (prima: solo path, lista vuota → NVDA
  «sconosciuto»). Menu risultati: anche «Leggi testo del documento».

**Test Maurizio:** ricompila SA → Apri PDF (deve aprirsi in Edge e
  comparire in lista); Leggi/Copia; stesso su .txt/.docx. Shift+G già OK.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`
  (ultime ~150–200 righe dopo una ricerca pesante).

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
