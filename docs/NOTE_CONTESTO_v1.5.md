# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.8.2` — piano chiuso `docs/PIANO_1.8.2.md` (22/10/2026, GitHub `v1.8.2` / `app-v1.8.2`, DataStore accettato).  
**In corso, non pubblicata:** `1.8.3` — piano `docs/PIANO_1.8.3.md`. Non aprire Whisper. Papà (22/10, sera) ha tolto le chiavi Gemini e Cloud Vision dal programma e non fa da tester su quei conti.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (23/10/2026)
- **Ultima pubblicata:** `1.8.2` — dopo un HTTP 503 si prova il modello successivo; la frase a schermo distingue servizio occupato e limite temporaneo; tasti Alt+L / Alt+H / Alt+B, Alt+G Segnalibri, Alt+M Strumenti.  
  Pubblicata il 22/10/2026. Commit `d6e7806`. DataStore accettato. Papà (installer) deve ancora aggiornarsi dalla 1.8.1 e riprovare Gemini.  
  **Non hotfixare 1.8.2.**  
  Prima: `1.8.1` il 21/10; `1.8.0` chat Gemini sul file, DataStore #12370 → #12371.
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, `rtad_chat.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.8.3`, codice del 23/10/2026, non pubblicata e non compilata. Piano: `docs/PIANO_1.8.3.md`.

Conversazione Gemini anche senza un file (Alt+Q). Nella chat, allegati uno o più alla volta, anche più tardi, anche se si era partiti da un file (Alt+A). HTTP 402 in italiano, senza provare un altro modello. Il `.rtad.txt` già salvato resta la candidata successiva.

Lista d’attesa: Whisper opt-in (versione dedicata); chat da un `.rtad.txt` già salvato; confronto tra più file; Gemini su ogni risultato; VIDEO_TS; OneCore; export multipli.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.8.3: codice del 23/10, non pubblicato e non compilato. Leggere NOTE_CONTESTO e PIANO_1.8.3. Provare Alt+Q, Alt+A su una chat da file e su una da zero, e la frase dell’HTTP 402. Non rifare quelle tre cose. Il .rtad.txt già salvato resta per dopo. Non aprire Whisper. Non togliere Cloud Vision.»
