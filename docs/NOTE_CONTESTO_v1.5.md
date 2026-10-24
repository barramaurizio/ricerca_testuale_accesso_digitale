# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.8.3` — piano chiuso `docs/PIANO_1.8.3.md` (23/10/2026, GitHub `v1.8.3` / `app-v1.8.3`, DataStore accettato).  
**In corso, non pubblicata:** `1.8.4` — piano `docs/PIANO_1.8.4.md`. Non aprire Whisper. Papà (22/10, sera) ha tolto le chiavi Gemini e Cloud Vision dal programma e non fa da tester su quei conti.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (24/10/2026)
- **Ultima pubblicata:** `1.8.3` — conversazione Gemini anche senza un file (Alt+Q); nella chat, allegati uno o più alla volta (Alt+A); HTTP 402 in italiano, senza provare un altro modello.  
  Pubblicata il 23/10/2026. GitHub `v1.8.3` / `app-v1.8.3`. DataStore accettato.  
  **Non hotfixare 1.8.3.**  
  Prima: `1.8.2` il 22/10; `1.8.1` e `1.8.0` il 21/10.
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, `rtad_chat.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.8.4`, codice e guide del 24/10/2026, non pubblicata. L’exe Standalone non è ancora compilato. Piano: `docs/PIANO_1.8.4.md`.

Chiedere a Gemini da un `.rtad.txt` già salvato, senza rifare l’analisi. Se accanto c’è ancora la foto, il video o il documento con lo stesso nome, quello resta il file di partenza. Se non c’è più, la chat resta sul testo salvato e lo dice, a voce e a schermo. Elenco vuoto con una frase vera. Nell’Add-on, NVDA dice anche percorso impostato, testo salvato e risultati esportati.

Prove di Maurizio ok (24/10, pomeriggio): i due casi del `.rtad.txt`, gli elenchi vuoti, Sfoglia e l’esportazione dei risultati.

Lista d’attesa: Whisper opt-in (versione dedicata); confronto tra più file; Gemini su ogni risultato; VIDEO_TS; OneCore; export multipli.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.8.4: codice e guide del 24/10, prove di Maurizio ok. Non pubblicata. Exe Standalone non compilato: compila.bat poi F9. Leggere NOTE_CONTESTO e PIANO_1.8.4. La 1.8.3 è online, non toccarla. Non aprire Whisper. Non togliere Cloud Vision.»
