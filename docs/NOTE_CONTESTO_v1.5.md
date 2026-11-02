# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.9.2` — piano `docs/PIANO_1.9.2.md` (1/11/2026, GitHub `v1.9.2` / `app-v1.9.2`, commit `d381367`, DataStore #12681 chiuso via #12682, accettato). Non hotfixarla. La 1.9.1 (pagina HTML) non è uscita da sola: è in questa build.  
**Prossima:** `1.9.3`, codice scritto, in prova da papà, non pubblicata. Tre porte sulla stessa finestra (corpo HTML di un’e-mail, articolo di un feed, fonte della chat) e, se l’immagine viene da Internet, l’indirizzo diretto in scheda e in descrizione, più Salva immagine. L’audio o il video già scaricato per l’analisi si può salvare; se le tracce sono due, si salvano entrambe. Ogni pagina passa da yt-dlp, anche `.m3u8` e `.mpd`. I cookie del browser restano per dopo, su scelta dell’utente, e non aprono i flussi protetti. Piano: `docs/PIANO_1.9.3.md`. Poi: 1.9.4 link interno Word e struttura ODT, 1.9.5 VIDEO_TS (avviso, niente copia del film), 1.9.6 OneCore, 1.9.7 export multipli. Papà (22/10, sera) ha tolto le chiavi Gemini e Cloud Vision dal programma e non fa da tester su quei conti. Il trascinamento del file `.eml` lo prova lui sull’Installer pubblicato. I procedimenti di FFmpeg, yt-dlp e crediti prepagati sono nelle guide ed escono con la 1.9.1. La 1.9.0 pubblicata non si rifà.  
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

## Stato attuale (1/11/2026)
- **Ultima pubblicata:** `1.9.2` — capitolo EPUB nel lettore della pagina HTML. Un link http esce nel browser di Windows.  
  Pubblicata l’1/11/2026. GitHub `v1.9.2` / `app-v1.9.2`, commit `d381367`. DataStore #12681 chiuso via #12682, accettato.  
  **Non hotfixare 1.9.2.** La 1.9.1 è in questa build.  
  Prima: `1.9.0` il 30/10 (DataStore #12641); `1.8.9` il 29/10 (DataStore #12598).
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_whisper.py`, `rtad_epub.py`, `rtad_docstruct.py`, `rtad_reading_mark.py`, `rtad_chat.py`, `rtad_attach_dialog.py`, `rtad_compare.py`, `rtad_html_page.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.9.3`, codice scritto, in prova. Non pubblicata. Piano: `docs/PIANO_1.9.3.md`.

Tre pezzi, stessa versione. La finestra già fatta si apre anche sul corpo HTML di un’e-mail, sull’articolo di un feed e su una fonte della chat. Se l’immagine analizzata viene da Internet, scheda tecnica e descrizione avanzata mostrano e dicono l’indirizzo diretto del file; Salva immagine tiene la copia. L’audio o il video già scaricato per l’analisi si salva con Salva video o Salva audio; se le tracce sono due, si salvano entrambe. Su YouTube e X l’indirizzo temporaneo del file non si scrive in scheda: scade. Ogni pagina passa da yt-dlp, anche `.m3u8` e `.mpd`. I cookie del browser restano per dopo. Vale per Standalone e Add-on. Un file già sul disco non si risalva.

Poi, una alla volta: 1.9.4 link interno di Word e titoli/link ODT; 1.9.5 VIDEO_TS (avviso, niente copia del film); 1.9.6 OneCore; 1.9.7 export multipli. Più avanti: confronto del parlato, confronto del testo di un’immagine, riga sulla figura di un EPUB.

La 1.9.2 resta com’è. «trascriv iamo» resta con lo spazio.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD. Ultima pubblicata 1.9.2 l’1/11/2026: GitHub v1.9.2 / app-v1.9.2, commit d381367. DataStore #12681 chiuso via #12682, accettato. Non hotfixare la 1.9.2. La 1.9.1 non è uscita da sola ed è in quella build. «trascriv iamo» resta con lo spazio. Prossima 1.9.3, piano docs/PIANO_1.9.3.md: la stessa finestra per e-mail HTML, articolo di un feed e fonte della chat; se l’immagine viene da Internet, indirizzo diretto in scheda e descrizione, e Salva immagine; Salva video o Salva audio sul file già scaricato per l’analisi. Su YouTube e X l’indirizzo temporaneo del file non si scrive: scade. Standalone e Add-on. Poi 1.9.4 link interno Word e ODT; 1.9.5 VIDEO_TS; 1.9.6 OneCore; 1.9.7 export multipli. Il trascinamento del file .eml lo prova papà sull’Installer.»
