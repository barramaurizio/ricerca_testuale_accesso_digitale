# Piano RTAD 1.9.4

**In corso.** Il numero nel programma diventa `1.9.4` con questi pezzi.  
La 1.9.3 resta pubblicata (2/11/2026, GitHub `v1.9.3` / `app-v1.9.3`, commit `08832c4`, DataStore #12733 via #12734 accettato). Non si rifà.

Vale per l’Installer e per l’Add-on. A schermo e a voce. Invio e il gesto del mouse che fa la stessa cosa stanno nella stessa frase.

## Primo pezzo: in Word il link interno salta al titolo

Leggi documento su un `.docx`. Un link interno non resta più «destinazione interna» da copiare.

- Nell’elenco: «Vai all’introduzione -> titolo «Introduzione»».
- Invio o doppio clic va a quel titolo, qui nel testo.
- A schermo e a voce: «Titolo «nome», qui nel testo.»
- Se il titolo non c’è: «Il titolo di destinazione non c’è.» e «Link interno. Il titolo di destinazione non c’è.»
- Un clic solo seleziona la riga.
- Un sito web si apre fuori, come oggi: «Apertura sito web esterno: titolo.»

Nella finestra, sopra l’elenco: «Invio o doppio clic: un link interno va a quel titolo, qui. Un sito web si apre fuori. Un clic solo seleziona la riga.»

## Secondo pezzo: in ODT arrivano titoli e link

Leggi documento su un `.odt` mostra titoli e link, come in Word. Il testo piano c’era già.

- Invio o doppio clic su un titolo del sommario va a quel titolo, qui.
- Invio o doppio clic su un link interno fa lo stesso.
- Un clic solo seleziona la riga.
- Un sito web si apre fuori.
- Senza titoli né link: «ODT senza titoli né link rilevati. Mostro il testo piano.»

## Terzo pezzo: il nome del file, e il testo che lo accompagna

Salva immagine, Salva audio o Salva video propone il nome della pagina, il più lungo che Windows accetta per un file. Prima si fermava a poche decine di caratteri.

Se cambi quel nome, anche solo qualche carattere, Salva testo propone lo stesso nome, con `.rtad.txt`, nella stessa cartella. Vale anche quando sostituisci tutto il nome. Invio sul pulsante, e un clic.

Un contenuto protetto resta non scaricabile.

## Quarto pezzo: le due guide sul web

La guida del menu e la guida pratica stanno in `docs/guida/`, lo stesso testo di chi ha il programma, e si rigenerano a ogni versione con `python tools/_sync_release_docs.py`.

- `docs/guida/index.html` — le due guide.
- `docs/guida/guida.html` — la guida del menu.
- `docs/guida/pratica.html` — la guida pratica.

Non il file del profilo NVDA e non `docs/GUIDA_COMPLETA.html`.

Sul web, dopo che GitHub Pages è attivo con il workflow `.github/workflows/pages.yml`:

https://barramaurizio.github.io/ricerca_testuale_accesso_digitale/guida/

## Dopo, non in questa versione

I cookie del browser, solo se l’utente lo chiede: un video pubblico che chiede l’accesso (per esempio un’età su YouTube). Non aprono Netflix, Sky, DAZN, Prime e gli altri flussi protetti.

## Dopo, una versione alla volta

1. **`1.9.5` — VIDEO_TS, nome della conversazione, cartella ricordata, guide dal menu.** Un avviso quando la ricerca incontra un DVD commerciale. Niente copia del film. La conversazione di Gemini usa il nome del file già salvato. Salva Immagine sull’elenco ricorda l’ultima cartella. Nella Standalone, Salva video a volte non legge subito il nome: Tab e poi Shift+Tab. Salva testo di solito lo legge. La frase è nelle guide. Menu Aiuto: «Apri le guide». Invio o un clic apre le guide sul web. Non è una voce dello store NVDA.
2. **`1.9.6` — OneCore.** La voce di Windows nella Standalone.
3. **`1.9.7` — export multipli.** Più di un formato nello stesso passaggio.

Papà ha rimesso la chiave Gemini e la usa. Cloud Vision per l’OCR non lo usa: da vedente non lo ritiene indispensabile.
