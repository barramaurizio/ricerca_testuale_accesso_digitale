# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.9.3` — piano `docs/PIANO_1.9.3.md` (2/11/2026, GitHub `v1.9.3` / `app-v1.9.3`, commit `08832c4`, DataStore #12733 chiuso via #12734, accettato). Non hotfixarla.  
**In corso:** `1.9.4`, non ancora pubblicata. In Word, un link interno salta al titolo. In ODT arrivano titoli e link. Salva immagine, audio o video propone il nome della pagina il più lungo che Windows accetta; se lo cambi, anche solo qualche carattere, Salva testo propone lo stesso nome. Le due guide del programma (la HTML del menu e la pratica) si pubblicano su GitHub Pages, stesso testo di chi ha il programma installato, e si rigenerano a ogni versione. Non il file del profilo NVDA e non `docs/GUIDA_COMPLETA.html`. Le novità di ogni versione stanno già in quelle due guide. I cookie del browser restano per dopo, su scelta dell’utente, e non aprono i flussi protetti. Poi: 1.9.5 VIDEO_TS (avviso, niente copia del film), 1.9.6 OneCore, 1.9.7 export multipli. Papà ha rimesso la chiave Gemini e la usa. Cloud Vision per l’OCR non lo usa: da vedente non lo ritiene indispensabile. Il trascinamento del file `.eml` lo prova lui sull’Installer pubblicato. I procedimenti di FFmpeg, yt-dlp e crediti prepagati sono nelle guide ed escono con la 1.9.1. La 1.9.0 pubblicata non si rifà.  
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

## Stato attuale (2/11/2026)
- **Ultima pubblicata:** `1.9.3` — lettore di pagina per e-mail HTML, feed e fonte della chat; Salva immagine, audio e video.  
  Pubblicata il 2/11/2026. GitHub `v1.9.3` / `app-v1.9.3`, commit `08832c4`. DataStore #12733 chiuso via #12734, accettato.  
  **Non hotfixare 1.9.3.**  
  Prima: `1.9.2` l’1/11 (DataStore #12681); `1.9.0` il 30/10 (DataStore #12641).
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_whisper.py`, `rtad_epub.py`, `rtad_docstruct.py`, `rtad_reading_mark.py`, `rtad_chat.py`, `rtad_attach_dialog.py`, `rtad_compare.py`, `rtad_html_page.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.9.4` scritta nei sorgenti, non ancora pubblicata. Piano: `docs/PIANO_1.9.4.md`. Non hotfixare la 1.9.3.

`1.9.3` pubblicata il 2/11/2026. GitHub `v1.9.3` / `app-v1.9.3`, commit `08832c4`. DataStore #12733 chiuso via #12734, accettato. Piano: `docs/PIANO_1.9.3.md`.

In Word, Invio o doppio clic su un link interno va a quel titolo, qui. In un ODT, Leggi documento mostra titoli e link. Salva immagine, audio o video propone il nome della pagina il più lungo che Windows accetta; una modifica anche di pochi caratteri passa a Salva testo. Le due guide, HTML del menu e pratica, stanno in `docs/guida/` e si pubblicano su GitHub Pages: stesso testo del programma, aggiornate a ogni versione. Non il file del profilo NVDA e non `docs/GUIDA_COMPLETA.html`.

La 1.9.3 resta com’è: lettore di pagina per e-mail, feed e fonte della chat; Salva immagine, audio e video. I cookie del browser restano per dopo e non aprono i flussi protetti. Un contenuto protetto resta non scaricabile.

Poi, una alla volta: 1.9.5 VIDEO_TS (avviso, niente copia del film); 1.9.6 OneCore; 1.9.7 export multipli. Più avanti: confronto del parlato, confronto del testo di un’immagine, riga sulla figura di un EPUB.

La 1.9.2 resta com’è. «trascriv iamo» resta con lo spazio.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD. Ultima pubblicata 1.9.3 il 2/11/2026: GitHub v1.9.3 / app-v1.9.3, commit 08832c4. DataStore #12733 chiuso via #12734, accettato. Non hotfixare la 1.9.3. «trascriv iamo» resta con lo spazio. In corso 1.9.4, non ancora pubblicata: in Word il link interno salta al titolo, in ODT arrivano titoli e link, il nome salvato di immagine audio e video è quello della pagina il più lungo possibile e Salva testo lo segue anche se cambi solo qualche carattere, e le due guide del programma (HTML del menu e pratica) si pubblicano su GitHub Pages, stesso testo di chi ha il programma, aggiornate a ogni versione. Non il file del profilo NVDA e non docs/GUIDA_COMPLETA.html. Papà ha rimesso Gemini e la usa. Cloud Vision non lo usa: da vedente non lo ritiene indispensabile. Poi 1.9.5 VIDEO_TS; 1.9.6 OneCore; 1.9.7 export multipli. I cookie del browser restano per dopo. I contenuti protetti restano non scaricabili.»
