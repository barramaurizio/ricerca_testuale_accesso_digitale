# Piano RTAD 1.9.1

**In corso.** Il numero nel programma diventa `1.9.1` con queste novità.  
La 1.9.0 resta pubblicata (30/10/2026, GitHub `v1.9.0` / `app-v1.9.0`, commit `8365774`). Non si rifà.

## Questa versione: il lettore di una pagina HTML

`Leggi documento` su un file `.html` o `.htm`, e su un indirizzo Internet già scaricato come pagina, apre il lettore dentro RTAD. Vale per l’Installer e per l’Add-on.

A schermo e a voce: «Pagina: titolo. N intestazioni, M link. Passo 1 di 1.»

- Invio su un’intestazione, o su un link della stessa pagina, va a quel punto, qui.
- Invio su un link di un altro sito apre quella pagina, qui.
- Indietro e Avanti tornano al punto di prima: un’altra intestazione, o un altro sito. Anche Alt+freccia sinistra e Alt+freccia destra. Se non c’è un punto, la frase lo dice.
- «Apri nel browser di Windows» apre il link selezionato. Per un’intestazione, prima Invio nel lettore, poi lo stesso pulsante: il browser si apre su quel punto. Invio resta nel lettore. I tasti H e K di NVDA si usano in quel browser.
- Senza intestazioni: «Nessuna intestazione in questa pagina.»
- Senza link: «Nessun link in questa pagina.»
- Da una pagina Internet non si apre un file del computer.

Word, EPUB e PDF restano sul lettore di prima: sommario, link e salto nel testo.

Nelle guide, già nei sorgenti: FFmpeg, yt-dlp e i crediti prepagati di Gemini. Escono con questa build.

## Dopo, una versione alla volta

Ogni voce è abbastanza da fare in una chat, e abbastanza corta da chiuderla.

1. **`1.9.2` — un capitolo EPUB nello stesso lettore.** Il sommario e i link interni restano nel libro. Un link `http` esce come oggi. Si riusa la finestra della 1.9.1.
2. **`1.9.3` — la stessa finestra da tre porte.** Il corpo HTML di un’e-mail, l’articolo di un feed, e una fonte della chat. Tre ingressi, una finestra già fatta.
3. **`1.9.4` — struttura, senza una finestra nuova.** In Word, un link interno che oggi dice «destinazione interna» salta al titolo. In ODT arrivano titoli e link, come nel Word. Il testo piano c’è già.
4. **`1.9.5` — VIDEO_TS.** Un avviso chiaro quando la ricerca incontra un DVD commerciale, anche se non hai scelto tu la cartella. Niente copia del film. La frase di quando scegli la cartella c’è già dalla 1.7.6. Versione corta, di proposito: è un avviso, non una funzione.
5. **`1.9.6` — OneCore.** La voce di Windows nella Standalone, oltre alle voci già registrate come SAPI.
6. **`1.9.7` — export multipli.** Più di un formato nello stesso passaggio.

Più avanti, non in questa lista:

- Confrontare il parlato di un audio o di un video. Prima la trascrizione che c’è già.
- Confrontare il testo di un’immagine. L’OCR che c’è già, oppure una descrizione con Gemini.

Un feedback vero, o un altro file che si comporta male, passa davanti a questa lista.

## Cosa non entra

- Un hotfix della 1.9.0 già pubblicata.
- Un visualizzatore PDF dentro RTAD.
- Un secondo browser per moduli, login e siti video. YouTube per la trascrizione resta yt-dlp.
- Copiare il film da un DVD commerciale.
- Qualsiasi ritocco a Whisper. La 1.8.6 resta com’è.
