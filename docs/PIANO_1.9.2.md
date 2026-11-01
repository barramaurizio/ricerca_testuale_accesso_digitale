# Piano RTAD 1.9.2

**In corso.** Il numero nel programma diventa `1.9.2` con il capitolo EPUB.  
La 1.9.0 resta pubblicata. La 1.9.1 è scritta e non è uscita da sola: la pagina HTML entra in questa build.

## Questa versione: un capitolo EPUB nello stesso lettore

`Leggi documento` su un file `.epub` apre un capitolo nella finestra della pagina HTML. Vale per l’Installer e per l’Add-on.

A schermo e a voce: «Capitolo: titolo. N intestazioni, M link. Passo 1 di 1.»

- Il sommario del libro è nella finestra. Invio apre quel capitolo, qui, sul punto indicato.
- Invio su un’intestazione va a quel punto, qui.
- Invio su un link interno resta nel libro.
- Indietro e Avanti tornano al capitolo di prima. Anche Alt+freccia sinistra e Alt+freccia destra.
- Un link `http` esce nel browser di Windows: «Apertura sito web esterno: titolo.»
- Senza sommario: «Nessuna voce di sommario.»
- Senza intestazioni: «Nessuna intestazione in questa pagina.»
- Senza link: «Nessun link in questa pagina.»

Word e PDF restano sul lettore di prima. La ricerca di una frase nel libro resta quella di sempre.

Le figure restano nel file. In questo libro sono formule senza didascalia: non si descrivono in questa versione.

## Dopo, una versione alla volta

1. **`1.9.3` — la stessa finestra da tre porte.** Il corpo HTML di un’e-mail, l’articolo di un feed, e una fonte della chat.
2. **`1.9.4` — struttura, senza una finestra nuova.** In Word, un link interno salta al titolo. In ODT arrivano titoli e link.
3. **`1.9.5` — VIDEO_TS.** Un avviso quando la ricerca incontra un DVD commerciale. Niente copia del film.
4. **`1.9.6` — OneCore.** La voce di Windows nella Standalone.
5. **`1.9.7` — export multipli.** Più di un formato nello stesso passaggio.

Più avanti, non in questa lista: il confronto del parlato, il confronto del testo di un’immagine, e una riga onesta sulla figura di un EPUB quando il libro ha una didascalia. Se la figura è muta, la frase lo dice. Non è un visualizzatore di immagini.
