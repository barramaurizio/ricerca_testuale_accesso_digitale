# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.9.5` — piano `docs/PIANO_1.9.5.md` (4/11/2026, GitHub `v1.9.5` / `app-v1.9.5`, commit `6c4e9c6`. DataStore #12756 via #12757 accettato). Non hotfixarla.  
**Prossima da pubblicare:** `1.9.6` — OneCore, la voce di Windows nella Standalone, oltre alle voci già registrate come SAPI. È nei sorgenti dal 5/11/2026, non ancora su GitHub. L’Add-on resta sulla voce di NVDA. Non iniziare la 1.9.7 prima della pubblicazione. Poi `1.9.7`: descrizione del video. Ogni volta si sceglie. Predefinita, il riassunto breve di oggi. Se si chiede la dettagliata, in cima resta il riassunto e sotto il racconto scena per scena, una sola richiesta a Gemini. I timestamp del racconto sono spenti e si accendono se si vuole. Se accesi, avanzano con le scene, sullo stesso orologio del video. Solo ciò che si vede o si sente. Poi 1.9.8: finestre nostre al posto di Salva e Sfoglia. Poi 1.9.9: export multipli. Più avanti: confronto del parlato, confronto del testo di un’immagine, riga sulla figura di un EPUB. Il ritorno con Alt+Tab che a volte tace resta così: la finestra non si blocca. I cookie del browser restano per dopo, su scelta dell’utente, e non aprono i flussi protetti. Papà ha rimesso la chiave Gemini e la usa. Cloud Vision per l’OCR non lo usa: da vedente non lo ritiene indispensabile. Il trascinamento del file `.eml` lo prova lui sull’Installer pubblicato. I procedimenti di FFmpeg, yt-dlp e crediti prepagati sono nelle guide ed escono con la 1.9.1. La 1.9.0 pubblicata non si rifà. «trascriv iamo» resta con lo spazio.  
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
`1.9.6`, nei sorgenti dal 5/11/2026, non ancora pubblicata. Non hotfixare la 1.9.5. Non iniziare la 1.9.7 prima della pubblicazione.

OneCore: la voce di Windows nella Standalone, oltre alle voci già registrate come SAPI. Menu Voce, «Scegli voce»: Invio sulla voce, o un clic, oppure Ctrl+Shift+V. Invio sul pulsante OK, o un clic, imposta la voce. Doppio clic sulla riga fa la stessa cosa. Un clic solo seleziona la riga. Velocità e tono valgono anche per queste voci. L’Add-on resta sulla voce di NVDA. Anche «Solo la voce di questo programma»: Invio sulla voce, o un clic. Dentro RTAD quella voce dice anche dove sei. Con Alt e le frecce dice il menu. «Pronuncia i tasti di spostamento» è spento. «Pronuncia le lettere mentre scrivi» è spento. I simboli si dicono lo stesso. Salva e Sfoglia, con NVDA spento, restano mute. Finestre nostre subito dopo i video.

Il lettore, dopo Alt+Tab, a volte tace un attimo. Non si blocca e non dice «non risponde». Resta così.

Poi `1.9.7`: descrizione del video. Ogni volta si sceglie. Predefinita, il riassunto breve di oggi. Se si chiede la dettagliata, in cima resta il riassunto e sotto il racconto scena per scena, una sola richiesta a Gemini. I timestamp del racconto sono spenti e si accendono se si vuole. Se accesi, avanzano con le scene, sullo stesso orologio del video. Solo ciò che si vede o si sente. Poi 1.9.8: finestre nostre al posto di Salva e Sfoglia. Poi 1.9.9: export multipli. Più avanti: confronto del parlato, confronto del testo di un’immagine, riga sulla figura di un EPUB. I cookie del browser restano per dopo. Un contenuto protetto resta non scaricabile.

«trascriv iamo» resta con lo spazio.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD. Ultima pubblicata 1.9.5 il 4/11/2026: GitHub v1.9.5 / app-v1.9.5, commit 6c4e9c6. DataStore #12756 via #12757 accettato. Non hotfixare la 1.9.5. «trascriv iamo» resta con lo spazio. Prossima da pubblicare 1.9.6, nei sorgenti dal 5/11/2026, non ancora su GitHub: OneCore, la voce di Windows nella Standalone, oltre alle voci già registrate come SAPI. Menu Voce, Scegli voce. L’Add-on resta sulla voce di NVDA. Non iniziare la 1.9.7 prima della pubblicazione. Anche Solo la voce di questo programma. Salva e Sfoglia, con NVDA spento, restano mute. Finestre nostre in 1.9.8. Alt+Tab che a volte tace resta così. Papà ha rimesso Gemini e la usa. Cloud Vision non lo usa: da vedente non lo ritiene indispensabile. Poi 1.9.7: descrizione del video. Ogni volta si sceglie. Predefinita, il riassunto breve. Se si chiede la dettagliata, in cima resta il riassunto e sotto il racconto scena per scena, una sola richiesta a Gemini. I timestamp del racconto sono spenti e si accendono se si vuole. Se accesi, avanzano con le scene, sullo stesso orologio del video. Solo ciò che si vede o si sente. Dopo, 1.9.8 export multipli. I cookie del browser restano per dopo. I contenuti protetti restano non scaricabili.»
