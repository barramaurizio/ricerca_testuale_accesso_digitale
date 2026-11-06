# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.9.6` — OneCore, la voce di Windows nella Standalone (5/11/2026, GitHub `v1.9.6` / `app-v1.9.6`). Piano `docs/PIANO_1.9.6.md`. Prima: `1.9.5` il 4/11/2026, GitHub `v1.9.5` / `app-v1.9.5`, commit `6c4e9c6`, DataStore #12756 via #12757 accettato. Non hotfixare la 1.9.5 né la 1.9.6.  
**Prossima da pubblicare:** `1.9.7` — descrizione del video. Nei sorgenti dal 6/11/2026, non ancora su GitHub. Le voci OneCore restano, sono già quelle della 1.9.6 pubblicata. Poi 1.9.8: login del browser, con il consenso di chi usa RTAD. I cookie restano sul suo PC. Un flusso con protezione DRM resta non scaricabile. Poi 1.9.9: finestre nostre al posto di Salva e Sfoglia. Poi 1.9.10: export multipli. Poi 2.0, e il primo punto è tagliare e unire un video, e lo stesso per le immagini. Più avanti: confronto del parlato, confronto del testo di un’immagine, riga sulla figura di un EPUB. Il ritorno con Alt+Tab che a volte tace resta così: la finestra non si blocca. Papà ha rimesso la chiave Gemini e la usa. Cloud Vision per l’OCR non lo usa: da vedente non lo ritiene indispensabile. Il trascinamento del file `.eml` lo prova lui sull’Installer pubblicato. I procedimenti di FFmpeg, yt-dlp e crediti prepagati sono nelle guide ed escono con la 1.9.1. La 1.9.0 pubblicata non si rifà. «trascriv iamo» resta con lo spazio.  
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

## Stato attuale (4/11/2026)
- **Ultima pubblicata:** `1.9.5` — la ricerca, se incontra un DVD video (VIDEO_TS), lo dice e non copia il film. La conversazione di Gemini usa il nome del file già salvato. Salva Immagine sull’elenco ricorda l’ultima cartella. Nella Standalone, Salva video o Salva immagine a volte non legge subito il nome: Tab e poi Shift+Tab, la voce si riattiva. Menu Aiuto: «Apri le guide».  
  Pubblicata il 4/11/2026. GitHub `v1.9.5` / `app-v1.9.5`, commit `6c4e9c6`. DataStore #12756 via #12757 accettato.  
  **Non hotfixare 1.9.5.**  
  Prima: `1.9.4` il 3/11 (DataStore #12743); `1.9.3` il 2/11 (DataStore #12733).
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_whisper.py`, `rtad_epub.py`, `rtad_docstruct.py`, `rtad_reading_mark.py`, `rtad_chat.py`, `rtad_attach_dialog.py`, `rtad_compare.py`, `rtad_html_page.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.9.7`, nei sorgenti dal 6/11/2026, non ancora pubblicata. La 1.9.6 è già su GitHub dal 5/11/2026 (`v1.9.6` / `app-v1.9.6`): OneCore resta nel programma, non si rifà. Non hotfixare la 1.9.5 né la 1.9.6.

Descrizione del video. In «Tutto sull'audio/video» il riassunto breve è già scelto. Freccia giù, o un clic, passa alla descrizione dettagliata: in cima resta il riassunto e sotto il racconto scena per scena, una sola richiesta a Gemini. I timestamp del racconto sono spenti. Spazio sulla casella, o un clic, li accende. Se accesi, avanzano con le scene, sullo stesso orologio del video. Solo ciò che si vede o si sente. Su RaiPlay, e sulle pagine che tengono video e audio separati, si scaricano entrambi e ffmpeg li unisce. Un contenuto protetto resta non scaricabile. Il file scaricato da un indirizzo resta in vista nell'elenco.

OneCore è la 1.9.6 già pubblicata: la voce di Windows nella Standalone. L’Add-on resta sulla voce di NVDA. Salva e Sfoglia, con NVDA spento, restano mute. Login del browser in 1.9.8, con il consenso. Finestre nostre in 1.9.9. Export multipli in 1.9.10. Poi 2.0, primo punto: tagliare e unire un video, e lo stesso per le immagini.

Il lettore, dopo Alt+Tab, a volte tace un attimo. Non si blocca e non dice «non risponde». Resta così.

Poi 1.9.8: login del browser, con il consenso di chi usa RTAD. I cookie restano sul suo PC. Un flusso con protezione DRM resta non scaricabile. Poi 1.9.9: finestre nostre al posto di Salva e Sfoglia. Poi 1.9.10: export multipli. Poi 2.0, primo punto: tagliare e unire un video, e lo stesso per le immagini. Più avanti: confronto del parlato, confronto del testo di un’immagine, riga sulla figura di un EPUB.

«trascriv iamo» resta con lo spazio.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD. Ultima pubblicata 1.9.6 il 5/11/2026: GitHub v1.9.6 / app-v1.9.6. OneCore, la voce di Windows nella Standalone. Non hotfixarla. Prima, 1.9.5 il 4/11/2026, commit 6c4e9c6, DataStore #12756 via #12757. «trascriv iamo» resta con lo spazio. Prossima da pubblicare 1.9.7, nei sorgenti dal 6/11/2026, non ancora su GitHub. Descrizione del video: riassunto breve già scelto; freccia giù o un clic per la dettagliata, una sola richiesta, timestamp del racconto spenti. RaiPlay: video e audio insieme. L’Add-on resta sulla voce di NVDA. Salva e Sfoglia, con NVDA spento, restano mute. Login del browser in 1.9.8, con il consenso: i cookie restano sul suo PC e un flusso con DRM resta non scaricabile. Finestre nostre in 1.9.9. Export multipli in 1.9.10. Poi 2.0, primo punto: tagliare e unire un video, e lo stesso per le immagini. Alt+Tab che a volte tace resta così. Papà ha rimesso Gemini e la usa. Cloud Vision non lo usa.»
