# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.9.0` — piano `docs/PIANO_1.9.0.md` (30/10/2026, GitHub `v1.9.0` / `app-v1.9.0`, commit `8365774`, DataStore #12641 chiuso via #12642, accettato). Non hotfixarla.  
**In corso:** `1.9.1`. Leggi documento su una pagina HTML apre il lettore dentro RTAD: intestazioni, link, Indietro, «Apri nel browser di Windows». Word, EPUB e PDF restano sul lettore di prima. Piano: `docs/PIANO_1.9.1.md`. Poi: 1.9.2 capitolo EPUB, 1.9.3 e-mail HTML / feed / fonte chat, 1.9.4 link interno Word e struttura ODT, 1.9.5 VIDEO_TS (avviso, niente copia del film), 1.9.6 OneCore, 1.9.7 export multipli. Papà (22/10, sera) ha tolto le chiavi Gemini e Cloud Vision dal programma e non fa da tester su quei conti. Il trascinamento del file `.eml` lo prova lui sull’Installer pubblicato. I procedimenti di FFmpeg, yt-dlp e crediti prepagati sono nelle guide ed escono con la 1.9.1. La 1.9.0 pubblicata non si rifà.  
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

## Stato attuale (30/10/2026)
- **Ultima pubblicata:** `1.9.0` — Gemini su ogni risultato, elenco fino a 200, incolla di un messaggio.  
  Pubblicata il 30/10/2026. GitHub `v1.9.0` / `app-v1.9.0`, commit `8365774`. DataStore #12641 chiuso via #12642, accettato.  
  **Non hotfixare 1.9.0.**  
  Prima: `1.8.9` il 29/10 (DataStore #12598); `1.8.8` il 28/10 (DataStore #12565); `1.8.7` il 27/10 (DataStore #12546).
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_whisper.py`, `rtad_epub.py`, `rtad_docstruct.py`, `rtad_reading_mark.py`, `rtad_chat.py`, `rtad_attach_dialog.py`, `rtad_compare.py`, `rtad_html_page.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.9.1`. Leggi documento su HTML apre il lettore dentro RTAD. Piano: `docs/PIANO_1.9.1.md`.

Poi, una alla volta: 1.9.2 capitolo EPUB; 1.9.3 e-mail HTML, articolo di un feed, fonte della chat; 1.9.4 link interno di Word e titoli/link ODT; 1.9.5 VIDEO_TS (avviso, niente copia del film); 1.9.6 OneCore; 1.9.7 export multipli. Più avanti: confronto del parlato, confronto del testo di un’immagine.

La 1.9.0 resta com’è. «trascriv iamo» resta con lo spazio.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD. Ultima pubblicata 1.9.0 il 30/10/2026: GitHub v1.9.0 / app-v1.9.0, commit 8365774. DataStore #12641 chiuso via #12642, accettato. Non hotfixare la 1.9.0. «trascriv iamo» resta con lo spazio. La 1.9.1 è scritta il 31/10/2026 e non è ancora pubblicata: Leggi documento su una pagina HTML apre il lettore dentro RTAD. Word, EPUB e PDF restano sul lettore di prima. Nelle guide: FFmpeg, yt-dlp, crediti prepagati. Piano: docs/PIANO_1.9.1.md. Dopo la pubblicazione, la prossima è la 1.9.2: un capitolo EPUB nello stesso lettore. Poi 1.9.3 e-mail HTML, feed e fonte chat; 1.9.4 link interno Word e ODT; 1.9.5 VIDEO_TS; 1.9.6 OneCore; 1.9.7 export multipli. Il trascinamento del file .eml lo prova papà sull’Installer.»
