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

## Stato attuale (07/10/2026 sera)
- **Ultima pubblicata:** `1.6.5` — GitHub (`v1.6.5` + `app-v1.6.5`) + Add-on Store
  (DataStore #12044 → #12045 accettata). **Non ripubblicare / non hotfixare 1.6.5.**
- **Prossima chat:** `1.6.6` (dialogo unico + batch + PDF ToUnicode + Gemini API)
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale
- Gemello SA ↔ Add-on su OCR/immagini (`rtad_ocr.py`)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc` (check versioni/docs prima di «vai»)

### Cosa c’è in 1.6.5 (riassunto)
- Fix 3BMeteo / SVG-WebP: niente dialogo wx «formato sconosciuto»; fallback cattura
- SA Explorer: sottomenù PDF/documenti (Apri + lista, Leggi testo, Copia testo, Descrivi immagini PDF)
- Restano Shift+G / URL / Appunti / Gemini/Vision 1.6.3, notifica 1.6.2, ZIP 1.6.1

## Scope 1.6.6 (da riprendere)
1. Dialogo unico «Tutto sull’immagine» + batch cartella.
2. **PDF multi-font / ToUnicode per font** (es. `sample-multilingual-text.pdf`):
   oggi CMap unificate → testo spazzatura; Edge OK. Serve CMap per font.
3. **Gemini API (avviso Google AI Studio 07/10/2026):** togliere
   `temperature` da `generationConfig` in `rtad_ocr.py` (noi non usiamo
   `thinking_budget` / `top_p` / `top_k`). Presto i modelli nuovi
   rifiuteranno temperature con `400`. Chiave ok; `generateContent` ok.
   Dettaglio anche in `ROADMAP` Fase M punto 4.
4. Audio/video (priorità Maurizio) — dopo chiusura immagini se possibile.
5. «Apri con» / lettore documenti strutturato — lista d’attesa.

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
