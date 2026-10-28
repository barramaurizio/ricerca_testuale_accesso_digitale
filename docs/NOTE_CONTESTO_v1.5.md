# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.8.7` — piano `docs/PIANO_1.8.7.md` (27/10/2026, GitHub `v1.8.7` / `app-v1.8.7`, commit `868c9b2`, DataStore #12546 chiuso via #12547, accettato). Non hotfixarla.  
**Provata, non pubblicata:** `1.8.8` — piano `docs/PIANO_1.8.8.md`. Maurizio, 28/10: scheda ok sui due MP4 (Spalletti e Zliani), una analisi con l’Add-on e una con la Standalone; glossario ok in entrambi (Alajbegović); guida HTML ok; indirizzo Internet ok in entrambi, dal percorso e da Sfoglia. Guide allineate. Non ancora compilata: la compilazione la fa Maurizio. Poi la lista d’attesa. Papà (22/10, sera) ha tolto le chiavi Gemini e Cloud Vision dal programma e non fa da tester su quei conti: per i testi dei brani gli basta rimettere la chiave Gemini nella Standalone.  
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

## Stato attuale (27/10/2026)
- **Ultima pubblicata:** `1.8.7` — punti di lettura, cifre nei PDF, lettere EPUB, Apri con apre solo questo programma.  
  Pubblicata il 27/10/2026. GitHub `v1.8.7` / `app-v1.8.7`, commit `868c9b2`. DataStore #12546 chiuso via #12547, accettato.  
  **Non hotfixare 1.8.7.**  
  Prima: `1.8.6` il 26/10 (DataStore #12533); `1.8.5` il 25/10 (DataStore #12491); `1.8.4` il 24/10; `1.8.3` il 23/10; `1.8.2` il 22/10; `1.8.1` e `1.8.0` il 21/10.
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_whisper.py`, `rtad_epub.py`, `rtad_docstruct.py`, `rtad_reading_mark.py`, `rtad_chat.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.8.8`, provata da Maurizio il 28/10, guide allineate, non compilata e non pubblicata. Piano: `docs/PIANO_1.8.8.md`.

Scheda tecnica: analisi rifatta. Spalletti e Zliani («A TUTTO GOL», emoji nel nome) riportano durata, risoluzione e forma. Una analisi è stata fatta con l’Add-on, l’altra con la Standalone.

Glossario: in Standalone e nell’Add-on il lettore dice Alajbegović (`Almqvist` → `Alajbegović`).

HTML: la guida, aperta nell’Add-on incollando il percorso, si legge come testo. Nella Standalone non è stata rifatta: la funzione è la stessa.

Elenco, confermato il 28/10 nel pomeriggio, Add-on e Standalone. Sfoglia su un singolo file, guida compresa: le stesse voci del menu e la domanda di aprirlo nel lettore. Un indirizzo nel campo percorso si scarica: «Scarico la pagina: nome. Attendere.», poi «L'indirizzo è in elenco: nome. Da qui puoi fare altre operazioni.» In più c’è «Apri pagina nel browser». Il lettore non si apre da solo. YouTube e il filtro Solo Audio e Video aprono ancora l’hub. Un audio o un video già scaricato resta in elenco.

Poi, se non arriva altro: confronto tra più file; Gemini su ogni risultato; VIDEO_TS; OneCore; export multipli.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.8.8, provata da Maurizio il 28/10, guide allineate, non compilata e non pubblicata. Ultima pubblicata 1.8.7, non toccarla. Scheda ok su Spalletti e su Zliani (A TUTTO GOL). Glossario ok: il lettore dice Alajbegović. Guida HTML ok. Indirizzo Internet ok in Add-on e Standalone: dal percorso si scarica e non apre il lettore da solo; da Sfoglia ha le voci del documento e chiede il lettore. YouTube resta sull’hub. Lista d’attesa, non iniziata: confronto tra più file, Gemini su ogni risultato, VIDEO_TS, OneCore, export multipli. Un browser che segua i link è un passo successivo. Piano docs/PIANO_1.8.8.md.»
