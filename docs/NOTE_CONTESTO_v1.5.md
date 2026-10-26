# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.8.5` — piano `docs/PIANO_1.8.5.md` (25/10/2026, GitHub `v1.8.5` / `app-v1.8.5`, DataStore #12491 accettato). Non hotfixarla.  
**In corso, non pubblicata:** `1.8.6` — piano `docs/PIANO_1.8.6.md`. È la versione dedicata a Whisper, opt-in, sul PC. Papà (22/10, sera) ha tolto le chiavi Gemini e Cloud Vision dal programma e non fa da tester su quei conti: per i testi dei brani gli basta rimettere la chiave Gemini nella Standalone.  
**NVDA:** da 26/10/2026 l’ultima versione testata da scrivere sull’Add-on è `2026.3.0` (`lastTestedNVDAVersion`). La 1.8.5 gira già su NVDA 2026.3. Il valore nello store cambia al prossimo invio.

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
- **Ultima pubblicata:** `1.8.5` — Traduci il testo già aperto (Alt+U): trascrizione, resoconto `.rtad.txt`, documento nel lettore. L’originale resta.  
  Pubblicata il 25/10/2026. GitHub `v1.8.5` / `app-v1.8.5`. DataStore #12491 accettato.  
  **Non hotfixare 1.8.5.**  
  Prima: `1.8.4` il 24/10; `1.8.3` il 23/10; `1.8.2` il 22/10; `1.8.1` e `1.8.0` il 21/10.
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_whisper.py`, `rtad_docstruct.py`, `rtad_chat.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.8.6`, prove di Maurizio ok il 26/10 (Standalone e Add-on), non pubblicata. Piano: `docs/PIANO_1.8.6.md`.

Whisper sul proprio PC, spento di default. Modello `small` scaricato al primo uso, non dentro l’installer. Un file fino a 20 minuti, oppure una cartella fino a 5 file. Il testo esce come `.rtad.txt`. Funziona anche senza chiave Gemini.

Pacchetto Add-on ricostruito: `ricerca_testuale_accesso_digitale-1.8.6.nvda-addon`, ultima NVDA testata `2026.3.0`. L’exe Standalone non è ancora compilato: `compila.bat` poi F9.

Lista d’attesa: segnalibro di lettura nel lettore (PDF, EPUB, DOCX), distinto dai Segnalibri di percorso (Ctrl+D); confronto tra più file; Gemini su ogni risultato; VIDEO_TS; OneCore; export multipli.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.8.6: prove di Maurizio ok il 26/10, Standalone e Add-on. Non pubblicata. Exe Standalone non compilato: compila.bat poi F9. Pacchetto addon già ricostruito, lastTestedNVDAVersion 2026.3.0. Ultima pubblicata 1.8.5, non toccarla. Non togliere Cloud Vision. Il segnalibro di lettura è la 1.8.7.»
