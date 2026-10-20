# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Piano corrente:** `docs/PIANO_1.7.7.md` (P0 OCR ordine lettura tabelle / colonne).  
Piano chiuso 1.7.6: `docs/PIANO_1.7.6.md`. Piano chiuso 1.7.5: `docs/PIANO_1.7.5.md`.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (20/10/2026)
- **In pubblicazione:** `1.7.7` — OCR tabelle riga-per-riga (cache v19) + guida/novità.  
  Codice+doc OK; smoke `tools/_smoke_ocr_reading_order.py` PASS; prova Maurizio OK.  
  Piano: `docs/PIANO_1.7.7.md`. Testi tag/store: `docs/NOTE_RILASCIO_1.7.7.txt`.
- **Ultima pubblicata (finché 1.7.7 non è live):** `1.7.6`. **Non hotfixare 1.7.6.**
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Idea futura (Maurizio 20/10) — chat post-analisi
Dopo aver analizzato immagine / audio / video / documento: **dialogo** con Gemini
(chiave già opt-in) per domande, curiosità, approfondimenti sul contenuto analizzato.
Non Cursor-as-chat nel prodotto (Cursor è per lo sviluppo). Dettaglio in roadmap «dopo 1.7.7».

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.7.8» dopo pubblicazione 1.7.7)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.7.7 pubblicata: aggiornare NOTE_CONTESTO; idea chat post-analisi Gemini»
