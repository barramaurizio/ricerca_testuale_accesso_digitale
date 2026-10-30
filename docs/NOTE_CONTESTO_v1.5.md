# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.8.9` — piano `docs/PIANO_1.8.9.md` (29/10/2026, GitHub `v1.8.9` / `app-v1.8.9`, commit `bdc84ff`, DataStore #12598 chiuso via #12599, accettato). Non hotfixarla.  
**In corso:** `1.9.0` nel programma, novità scritte il 30/10, non ancora pubblicata. Piano: `docs/PIANO_1.9.0.md`. Gemini su ogni risultato, elenco fino a 200, incolla di un messaggio. Poi: VIDEO_TS (avviso, niente copia del film), OneCore, export multipli. Nel lettore, anche un browser (link e intestazioni): forse prima di quelle tre, si decide a 1.9.0 pubblicata. Papà (22/10, sera) ha tolto le chiavi Gemini e Cloud Vision dal programma e non fa da tester su quei conti: per i testi dei brani gli basta rimettere la chiave Gemini nella Standalone. Whisper, FFmpeg e l’installer che usa lui stanno in un’altra chat.  
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

## Stato attuale (29/10/2026)
- **Ultima pubblicata:** `1.8.9` — confronto tra più file e PDF DocuSign firmati.  
  Pubblicata il 29/10/2026. GitHub `v1.8.9` / `app-v1.8.9`, commit `bdc84ff`. DataStore #12598 chiuso via #12599, accettato.  
  **Non hotfixare 1.8.9.**  
  Prima: `1.8.8` il 28/10 (DataStore #12565); `1.8.7` il 27/10 (DataStore #12546); `1.8.6` il 26/10 (DataStore #12533).
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_whisper.py`, `rtad_epub.py`, `rtad_docstruct.py`, `rtad_reading_mark.py`, `rtad_chat.py`, `rtad_attach_dialog.py`, `rtad_compare.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.9.0` nel programma. Novità scritte il 30/10, non ancora pubblicata.

Gemini su ogni risultato, elenco fino a 200, incolla di un messaggio. Poi: VIDEO_TS (avviso su un DVD commerciale, niente copia del film); OneCore nella Standalone; export multipli. Nel lettore, anche un browser (link e intestazioni): forse prima di quelle tre. Più avanti: confronto del parlato, confronto del testo di un’immagine.

La 1.8.9 resta com’è: PDF DocuSign e confronto tra più file, provati da Maurizio. «trascriv iamo» resta con lo spazio.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.9.0. Ultima pubblicata 1.8.9 il 29/10/2026: GitHub v1.8.9 / app-v1.8.9, commit bdc84ff. DataStore #12598 chiuso via #12599, accettato. Non hotfixare la 1.8.9. Confronto tra più file e PDF DocuSign firmati. «trascriv iamo» resta con lo spazio. Il numero nel programma è 1.9.0, novità scritte il 30/10, non ancora pubblicata. Gemini su ogni risultato, elenco fino a 200, incolla di un messaggio. Poi: VIDEO_TS (avviso, niente copia del film), OneCore, export multipli. Nel lettore, anche un browser (link e intestazioni): forse prima di quelle tre. Più avanti: confronto del parlato, confronto del testo di un’immagine. Piano: docs/PIANO_1.9.0.md. Whisper, FFmpeg e l’installer di papà stanno in un’altra chat.»
