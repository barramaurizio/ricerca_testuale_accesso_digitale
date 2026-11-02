# Piano RTAD 1.9.3

**Prossima.** Il numero nel programma diventa `1.9.3` con questi due pezzi.  
La 1.9.2 resta pubblicata (1/11/2026, GitHub `v1.9.2` / `app-v1.9.2`, commit `d381367`). Non si rifà.

Vale per l’Installer e per l’Add-on. A schermo e a voce. Invio e il gesto del mouse che fa la stessa cosa stanno nella stessa frase.

## Primo pezzo: la stessa finestra da tre porte

La finestra del lettore di pagina si apre anche da qui.

- Il corpo HTML di un’e-mail.
- L’articolo di un feed.
- Una fonte della chat.

Tre ingressi, una finestra già fatta. Word e PDF restano sul lettore di prima.

## Secondo pezzo: indirizzo dell’immagine, e salvarla

Se l’immagine analizzata viene da Internet, la scheda tecnica e la descrizione avanzata hanno la stessa riga, scritta e detta:

«Indirizzo immagine: https://….»

È l’indirizzo del file, quello che si aprirebbe l’immagine. Se la pagina è un altro indirizzo, una seconda riga: «Pagina: https://….».

- Add-on, NVDA+Maiusc+G sulla figura: il navigatore ha già l’indirizzo. Oggi lo usa per scaricare e poi lo dimentica. Da questa versione resta nel testo.
- Standalone e Add-on, «Descrivi immagine da URL», e un indirizzo immagine incollato dagli Appunti: la stessa riga.
- Solo un’area dello schermo, senza file: «Immagine dallo schermo. Un indirizzo non c’è.»
- Un file già sul disco, scelto in Esplora file: niente riga di indirizzo. La scheda resta quella di oggi.

Salva immagine tiene la copia, che oggi viene cancellata alla chiusura della finestra. Il pulsante c’è quando l’immagine è stata scaricata o catturata per l’analisi. Invio, con il pulsante attivo, e un clic. A schermo e a voce il punto in cui il file è stato scritto. Un file già sul disco non si risalva.

## Terzo pezzo: salvare l’audio o il video già scaricato

L’analisi di un indirizzo ha già il file sul disco, in una copia temporanea che si cancella alla chiusura. Salva video, o Salva audio se è arrivata solo la traccia, tiene quella copia. Invio sul pulsante, e un clic. A schermo e a voce il punto in cui il file è stato scritto. Standalone e Add-on. Un file già sul disco non si risalva. Il tetto di dimensione e di durata resta quello di oggi. Un contenuto protetto resta non scaricabile.

In scheda restano le righe di oggi, più l’indirizzo del file quando è un link diretto (`.mp4`, `.mp3` e gli altri già riconosciuti): «Indirizzo file: https://…». L’indirizzo della pagina resta «URL sorgente».

Su YouTube, X e le altre pagine, yt-dlp riceve un permesso temporaneo del sito, spesso diviso in video e audio, e con ffmpeg ricostruisce il file sul PC. Quell’indirizzo scade. In scheda non si scrive. Il file ricostruito è quello che Salva video tiene. Se le due tracce restano separate, Salva tiene video e audio: il video da solo sarebbe muto.

Ogni indirizzo di pagina passa da yt-dlp, non solo YouTube, Vimeo, TikTok, Instagram, Facebook, X, LinkedIn, Dailymotion, Twitch e Reddit. Anche una playlist `.m3u8` o `.mpd`. Un file diretto (`.mp4`, `.mp3` e gli altri già riconosciuti) resta uno scaricamento HTTP. Stessi tetti di oggi. Un contenuto protetto resta non scaricabile.

## Dopo, non in questa versione

I cookie del browser, solo se l’utente lo chiede: un video pubblico che chiede l’accesso (per esempio un’età su YouTube). Non aprono Netflix, Sky, DAZN, Prime e gli altri flussi protetti. Si leggono i cookie del browser, quindi è una scelta a parte.

## Dopo, una versione alla volta

1. **`1.9.4` — struttura, senza una finestra nuova.** In Word, un link interno salta al titolo. In ODT arrivano titoli e link.
2. **`1.9.5` — VIDEO_TS.** Un avviso quando la ricerca incontra un DVD commerciale. Niente copia del film.
3. **`1.9.6` — OneCore.** La voce di Windows nella Standalone.
4. **`1.9.7` — export multipli.** Più di un formato nello stesso passaggio.

Più avanti, non in questa lista: il confronto del parlato, il confronto del testo di un’immagine, e una riga onesta sulla figura di un EPUB quando il libro ha una didascalia. Se la figura è muta, la frase lo dice. Non è un visualizzatore di immagini.
