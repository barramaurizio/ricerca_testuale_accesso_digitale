# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `2.0.11` — fotocamera in tempo reale, scatto e ripresa, e il giudizio su foto e video già salvati, senza spendere la chiave. Standalone e Add-on. NVDA testata 2026.3.1 (26/11/2026, GitHub `v2.0.11` / `app-v2.0.11`, commit `7b9f3e1`, DataStore #13290 via #13291 accettato). Piano `docs/PIANO_2.0.11.md`. Prima: `2.0.10` il 24/11/2026, GitHub `v2.0.10` / `app-v2.0.10`, commit `046f0cd`. Non hotfixare la 1.9.5 né le successive fino alla 2.0.11 inclusa. Una versione già su GitHub si scrive pubblicata, con la data e i tag. Il numero DataStore si aggiunge quando lo store l’accetta.

**Prossima da pubblicare:** `2.0.12` (non iniziata) — due cose, piano `docs/PIANO_2.0.12.md`. Modificare e scrivere in un PDF, a voce e a schermo: il testo che c’è, le pagine. Glielo hanno chiesto in diversi, e lo vuole anche lui. E, sui post di X, l’elenco mostra tutte le foto che la pagina consegna, con le caselle, come per gli altri siti. Il 26/11/2026 il post https://x.com/juventusfc/status/2125892317617725946 ne ha 6; la pagina ha già i sei indirizzi; RTAD, fermo a quattro dalla 2.0.3 (`_POST_IMAGE_LIMIT` in `Standalone/rtad_ocr.py`), ne ha date le prime quattro, in `J:\Juve`. La quinta è la festa in pedana, la sesta è Del Piero di spalle col 10. Dopo: dettatura vocale; operatore integrato; confronto del parlato; confronto del testo di un’immagine; scrivere e modificare un testo qui, come in Blocco note. Acrobat è a pagamento. Firefox modifica i PDF: da provare, non è il programma. RTAD predefinito per i PDF quando le figure le riconosce bene, se Maurizio vorrà. Un abbonamento per queste funzioni, più avanti, se vorrà. Chat Desktop della prima stesura 2.0.8 persa col PC Acer (20/11/2026); ricostruita da piano + 2.0.7. Papà l’11/11/2026 ha provato il mouse: taglio e unione riusciti, il quadratino bianco gli è piaciuto. Il ritorno con Alt+Tab che a volte tace resta così. Papà ha rimesso Gemini e la usa. Cloud Vision non lo usa. «trascriv iamo» resta con lo spazio.

**NVDA:** sull’Add-on 2.0.5 `lastTestedNVDAVersion` resta `2026.3.1`, come sulla 2.0.4 e sulle precedenti dalla 2.0.0. `minimumNVDAVersion` resta `2024.1.0`. La 1.9.9 già accettata resta su `2026.3.0` e non si riscrive. Le già accettate non si riscrivono.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\ricerca_testuale_accesso_digitale`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

Il modulo del DataStore non si modifica dopo l’invio. Si apre un’issue su `nvaccess/addon-datastore`, con un numero. Se i controlli passano, il bot chiude l’issue e l’Add-on entra nello store. Lì non si scrive il commit corto: lo store tiene i campi del modulo e l’indirizzo della release GitHub. Un commento dopo la chiusura non cambia l’invio, e l’issue non si riapre per aggiungerlo. Se i controlli falliscono, l’issue resta aperta con l’errore e si rinvia il modulo. Il numero DataStore si scrive nelle tre note quando l’issue è chiusa. Se la release GitHub è già online, entra con la versione successiva.

## Stato al 4/11/2026
Quel giorno l’ultima pubblicata era la 1.9.5. Oggi l’ultima pubblicata è la 2.0.0, scritta in cima a questo file.
- **Pubblicata quel giorno:** `1.9.5` — la ricerca, se incontra un DVD video (VIDEO_TS), lo dice e non copia il film. La conversazione di Gemini usa il nome del file già salvato. Salva Immagine sull’elenco ricorda l’ultima cartella. Nella Standalone, Salva video o Salva immagine a volte non legge subito il nome: Tab e poi Shift+Tab, la voce si riattiva. Menu Aiuto: «Apri le guide».  
  Pubblicata il 4/11/2026. GitHub `v1.9.5` / `app-v1.9.5`, commit `6c4e9c6`. DataStore #12756 via #12757 accettato.  
  **Non hotfixare 1.9.5.**  
  Prima: `1.9.4` il 3/11 (DataStore #12743); `1.9.3` il 2/11 (DataStore #12733).
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_whisper.py`, `rtad_epub.py`, `rtad_docstruct.py`, `rtad_reading_mark.py`, `rtad_chat.py`, `rtad_attach_dialog.py`, `rtad_compare.py`, `rtad_html_page.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc` e `.cursor/rules/rtad-versione-pubblicata.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Pubblicata
`2.0.0` è pubblicata l’11/11/2026 (GitHub `v2.0.0` / `app-v2.0.0`, commit `b70e333`, DataStore #12942 via #12943). Non si rifà. La `2.0.1` è pubblicata il 12/11/2026, GitHub `v2.0.1` / `app-v2.0.1`. Commit `c430151`. DataStore #12978 via #12979 accettato. Non si rifà. La `1.9.10` è pubblicata il 9/11/2026 (GitHub `v1.9.10` / `app-v1.9.10`, commit `2f1d38c`, DataStore #12896 via #12898). Ctrl+E scrive insieme testo, pagina web e tabella, nella cartella di origine. La ricerca successiva non rilegge quei file. `lastTestedNVDAVersion` = `2026.3.1`. Il ritorno sulla ricerca dell’Add-on, quando è ridotta a icona, è in quel pacchetto. Com’era il buco, prima della 1.9.10: il 9/11/2026, alle 12, la finestra 1.9.9 era viva e non bloccata. Windows la teneva iconizzata (`showCmd` 2), parcheggiata a −21333,−21333, 158×26, fuori dallo schermo. Il posto salvato è 567,249, 573×520. NVDA legge il titolo e poi «riquadro»: è il riquadro cliente, i controlli sono fuori e i tasti non arrivano. Uno screenshot prende Firefox, perché a schermo la finestra non c’è. Alt+Spazio e Ingrandisci la tirano fuori. Subtitle Reader spento non cambia questo stato. Il codice 1.9.9 non la riapre se Alt+Tab le dà il focus restando iconizzata. `ShowWindow` da fuori non la muove. Il comando di sistema SC_RESTORE sì, lo stesso di Alt+Spazio, e l’ha riportata a 567,249, 573×520. Nella 1.9.10, all’attivazione, si riapre così e il focus torna sul campo. Il sorgente ha già questa riapertura; il pacchetto accettato 1.9.9 no. La 1.9.9 è già pubblicata il 9/11/2026 (GitHub `v1.9.9` / `app-v1.9.9`, commit `ed01ac2`, DataStore #12858 via #12859), non si rifà. La 1.9.8 è già pubblicata il 7/11/2026 (GitHub `v1.9.8` / `app-v1.9.8`, commit `771db55`, DataStore #12813 via #12814): login del browser con il consenso, non si rifà. La 1.9.7 è già pubblicata il 6/11/2026 (GitHub `v1.9.7` / `app-v1.9.7`, commit `163464f`): descrizione del video, non si rifà. La 1.9.6 è già su GitHub dal 5/11/2026 (`v1.9.6` / `app-v1.9.6`): OneCore resta nel programma, non si rifà. Non hotfixare la 1.9.5, la 1.9.6, la 1.9.7, la 1.9.8, la 1.9.9, la 1.9.10 né la 2.0.0, né la 2.0.1, né la 2.0.2.

La 1.9.7, già pubblicata il 6/11/2026, è la descrizione del video. In «Tutto sull'audio/video» il riassunto breve è già scelto. Freccia giù, o un clic, passa alla descrizione dettagliata: in cima resta il riassunto e sotto il racconto scena per scena, una sola richiesta a Gemini. I timestamp del racconto sono spenti. Spazio sulla casella, o un clic, li accende. Se accesi, avanzano con le scene, sullo stesso orologio del video. Solo ciò che si vede o si sente. Su RaiPlay, e sulle pagine che tengono video e audio separati, si scaricano entrambi e ffmpeg li unisce. Un contenuto protetto resta non scaricabile. Il file scaricato da un indirizzo resta in vista nell'elenco.

OneCore è la 1.9.6 già pubblicata: la voce di Windows nella Standalone. L’Add-on resta sulla voce di NVDA. Nella 1.9.9 già pubblicata, Salva e Sfoglia sono finestre di RTAD solo nella Standalone. Nell’Add-on restano quelle di Windows. Il login del browser è la 1.9.8 già pubblicata, con il consenso. Piano docs/PIANO_2.0.md. La 2.0.0 è pubblicata. La 2.0.1 è pubblicata il 12/11/2026.

Il lettore, dopo Alt+Tab, a volte tace un attimo. Non si blocca e non dice «non risponde». Resta così.

Il login del browser è la 1.9.8 già pubblicata, con il consenso. I cookie restano sul suo PC. Un flusso con protezione DRM resta non scaricabile. RaiPlay Sound mette l’audio in elenco e dice che è l’audio. La 1.9.9 è già pubblicata il 9/11/2026: nella Standalone, finestre di RTAD al posto di Salva e Sfoglia. Nell’Add-on restano quelle di Windows, con i 4 secondi su Audio e Video e il focus che torna dopo il riposo. Piano `docs/PIANO_1.9.9.md`. Poi 1.9.10: export multipli. La 2.0.0 è pubblicata. La 2.0.1 è pubblicata il 12/11/2026. Più avanti: confronto del parlato, confronto del testo di un’immagine, riga sulla figura di un EPUB.

«trascriv iamo» resta con lo spazio.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD. Ultima pubblicata 1.9.9 il 9/11/2026: GitHub v1.9.9 / app-v1.9.9, commit ed01ac2. DataStore #12858 via #12859 accettato. Nella Standalone, Salva e Sfoglia sono finestre di RTAD. Nell’Add-on restano quelle di Windows: i 4 secondi su Audio e Video, e il focus che torna sul campo dopo il riposo. È online. Non hotfixarla. Prima, 1.9.8 il 7/11/2026: GitHub v1.9.8 / app-v1.9.8, commit 771db55, DataStore #12813 via #12814, login del browser con il consenso. I cookie restano sul suo PC. Su Windows la casella legge Firefox. RaiPlay Sound mette l’audio in elenco, anche se il file si chiama .mp4, e si dice che è l’audio. Un flusso con DRM resta non scaricabile. Prima ancora, 1.9.7 il 6/11/2026: GitHub v1.9.7 / app-v1.9.7, commit 163464f, descrizione del video. 1.9.6 il 5/11/2026: OneCore. 1.9.5 il 4/11/2026, commit 6c4e9c6, DataStore #12756 via #12757. «trascriv iamo» resta con lo spazio. Una versione già su GitHub si scrive pubblicata. Prossima da pubblicare 1.9.10: export multipli. Dal 9/11/2026 NVDA in uso è 2026.3.1: nella 1.9.10 va in manifest, novità, guide, readme, changelog e note di rilascio. La 1.9.9 pubblicata resta su 2026.3.0. Se la ricerca dell’Add-on è ridotta a icona, Alt+Tab le dà il focus e la lascia fuori schermo: NVDA dice il titolo e «riquadro». Nella 1.9.10 si riapre. La 2.0.0 è pubblicata. La 2.0.1 è pubblicata il 12/11/2026. L’Add-on resta sulla voce di NVDA. Alt+Tab che a volte tace resta così. Papà ha rimesso Gemini e la usa. Cloud Vision non lo usa.»
