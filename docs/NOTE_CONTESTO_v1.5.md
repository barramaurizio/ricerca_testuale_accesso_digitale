# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.8.6` — piano `docs/PIANO_1.8.6.md` (26/10/2026, GitHub `v1.8.6` / `app-v1.8.6`, commit `b57d02a`, DataStore #12533 chiuso via #12534, accettato). Non hotfixarla.  
**In corso, non pubblicata:** `1.8.7` — piano `docs/PIANO_1.8.7.md`. Provata il 27/10 su Standalone e Add-on: punti di lettura, cifre nei PDF, txt. Manca compilare la Standalone e pubblicare. Papà (22/10, sera) ha tolto le chiavi Gemini e Cloud Vision dal programma e non fa da tester su quei conti: per i testi dei brani gli basta rimettere la chiave Gemini nella Standalone.  
**NVDA:** ultima versione testata sull’Add-on pubblicato: `2026.3.0` (`lastTestedNVDAVersion`).

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (26/10/2026)
- **Ultima pubblicata:** `1.8.6` — Whisper sul PC, opt-in, modello small al primo uso, file fino a 20 minuti o cartella fino a 5, testo in `.rtad.txt`.  
  Pubblicata il 26/10/2026. GitHub `v1.8.6` / `app-v1.8.6`, commit `b57d02a`. DataStore #12533 chiuso via #12534, accettato.  
  **Non hotfixare 1.8.6.**  
  Prima: `1.8.5` il 25/10 (DataStore #12491); `1.8.4` il 24/10; `1.8.3` il 23/10; `1.8.2` il 22/10; `1.8.1` e `1.8.0` il 21/10.
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_whisper.py`, `rtad_epub.py`, `rtad_docstruct.py`, `rtad_reading_mark.py`, `rtad_chat.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.8.7`, non pubblicata. Piano: `docs/PIANO_1.8.7.md`.

Già nel codice: lettere al posto dei codici EPUB; file o cartella da Esplora file restano in elenco; Apri con nell’installer, senza diventare il predefinito; segnalibro di lettura nel lettore (Control+B).

Prova il segnalibro di lettura: il punto in un documento lungo (PDF, EPUB, DOCX), per chiudere e riprendere. È distinto dai Segnalibri di percorso (Ctrl+D). Prova vera: `I:\Libri\Sean Carroll - La fisica dei quanti.epub`, compleanno il 2 novembre.

Lista d’attesa, fuori dalla 1.8.7: confronto tra più file; Gemini su ogni risultato; VIDEO_TS; OneCore; export multipli.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.8.7 in corso, non pubblicata. Già fatti: codici EPUB, file da Esplora file in elenco, Apri con senza diventare il predefinito, segnalibro di lettura Control+B. Da provare prima di pubblicare. Ultima pubblicata 1.8.6, non toccarla. Piano docs/PIANO_1.8.7.md.»
