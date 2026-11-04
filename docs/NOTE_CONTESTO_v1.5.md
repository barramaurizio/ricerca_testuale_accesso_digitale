# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.9.4` — piano `docs/PIANO_1.9.4.md` (3/11/2026, GitHub `v1.9.4` / `app-v1.9.4`, commit `6bd5814`; le guide sul web nei commit `18d09e2` e `ca7f0ee`. DataStore #12743 accettato). Non hotfixarla.  
**In corso:** `1.9.5`, nei sorgenti, non ancora pubblicata. Piano `docs/PIANO_1.9.5.md`. La ricerca, se incontra un DVD video (VIDEO_TS), lo dice a schermo e a voce e non copia il film. La conversazione di Gemini usa il nome del file già salvato. Salva Immagine sull’elenco ricorda l’ultima cartella. Nella Standalone, Salva video o Salva immagine a volte non legge subito il nome: Tab e poi Shift+Tab lo legge sempre, la voce si riattiva. Salva testo di solito lo legge. La frase è nelle guide. Il tentativo di spostare il focus non ha cambiato il video, ed è stato tolto. Menu Aiuto, Standalone e Add-on: «Apri le guide». Invio sulla voce, o un clic, apre https://barramaurizio.github.io/ricerca_testuale_accesso_digitale/guida/ . La pagina con i due link resta quella. Non è una voce dello store NVDA. Il ritorno con Alt+Tab che a volte tace resta così: la finestra non si blocca. I cookie del browser restano per dopo, su scelta dell’utente, e non aprono i flussi protetti. Poi: 1.9.6 OneCore, 1.9.7 export multipli. Papà ha rimesso la chiave Gemini e la usa. Cloud Vision per l’OCR non lo usa: da vedente non lo ritiene indispensabile. Il trascinamento del file `.eml` lo prova lui sull’Installer pubblicato. I procedimenti di FFmpeg, yt-dlp e crediti prepagati sono nelle guide ed escono con la 1.9.1. La 1.9.0 pubblicata non si rifà.  
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

## Stato attuale (3/11/2026)
- **Ultima pubblicata:** `1.9.4` — in Word il link interno va al titolo; in ODT arrivano titoli e link; il nome salvato segue la pagina e Salva testo lo stesso nome; le due guide sono sul web.  
  Pubblicata il 3/11/2026. GitHub `v1.9.4` / `app-v1.9.4`, commit `6bd5814`. Guide: `18d09e2`, `ca7f0ee`. DataStore #12743 accettato.  
  **Non hotfixare 1.9.4.**  
  Prima: `1.9.3` il 2/11 (DataStore #12733); `1.9.2` l’1/11 (DataStore #12681).
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_whisper.py`, `rtad_epub.py`, `rtad_docstruct.py`, `rtad_reading_mark.py`, `rtad_chat.py`, `rtad_attach_dialog.py`, `rtad_compare.py`, `rtad_html_page.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.9.5` nei sorgenti, non ancora pubblicata. Non hotfixare la 1.9.4.

Scritto, da provare. La ricerca, se incontra un DVD video (VIDEO_TS), lo dice a schermo e a voce: «La ricerca ha incontrato un DVD video (VIDEO_TS). RTAD cerca i file dati sul disco (mp3, pdf, foto), non copia il film.» I file dati nelle altre cartelle restano. La frase di quando scegli tu la cartella c’è già dalla 1.7.6.

La conversazione di Gemini usa il nome del file già salvato. Salva Immagine sull’elenco ricorda l’ultima cartella, la stessa della finestra di analisi. Nella Standalone, Salva video o Salva immagine a volte non legge subito il nome: Tab e poi Shift+Tab lo legge sempre, la voce si riattiva. Salva testo di solito lo legge. La frase è nelle guide.

Menu Aiuto, Standalone e Add-on: «Apri le guide». Invio sulla voce, o un clic, apre https://barramaurizio.github.io/ricerca_testuale_accesso_digitale/guida/ . La pagina con i due link resta quella. Non è una voce dello store NVDA. A schermo e a voce: «Apro le guide sul web. La pagina con i due link.»

Il lettore, dopo Alt+Tab, a volte tace un attimo. Non si blocca e non dice «non risponde». Resta così.

Poi, una alla volta: 1.9.6 OneCore; 1.9.7 export multipli. Più avanti: confronto del parlato, confronto del testo di un’immagine, riga sulla figura di un EPUB. I cookie del browser restano per dopo. Un contenuto protetto resta non scaricabile.

La 1.9.2 resta com’è. «trascriv iamo» resta con lo spazio.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD. Ultima pubblicata 1.9.4 il 3/11/2026: GitHub v1.9.4 / app-v1.9.4, commit 6bd5814. Guide sul web: 18d09e2 e ca7f0ee. DataStore #12743 accettato. Non hotfixare la 1.9.4. «trascriv iamo» resta con lo spazio. In corso 1.9.5, nei sorgenti, non ancora pubblicata. La ricerca, se incontra un DVD video (VIDEO_TS), lo dice e non copia il film. La conversazione di Gemini usa il nome del file salvato. Salva Immagine sull’elenco ricorda l’ultima cartella. Nella Standalone Salva video o Salva immagine a volte non legge subito il nome: Tab e poi Shift+Tab, la voce si riattiva. Menu Aiuto: «Apri le guide», stesso indirizzo del collegamento sul desktop. Non è una voce dello store. Alt+Tab che a volte tace resta così. Papà ha rimesso Gemini e la usa. Cloud Vision non lo usa: da vedente non lo ritiene indispensabile. Poi 1.9.6 OneCore; 1.9.7 export multipli. I cookie del browser restano per dopo. I contenuti protetti restano non scaricabili.»
