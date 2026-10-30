# Piano RTAD 1.9.0

**Ultima pubblicata:** `1.8.9` — 29/10/2026. Non hotfixarla.  
GitHub `v1.8.9` / `app-v1.8.9`, commit `bdc84ff`. DataStore #12598 chiuso via #12599, accettato.  
**Questa versione:** numero `1.9.0` nel programma, novità scritte il 30/10. Non ancora pubblicata: gli exe li compila Maurizio.

## Prima cosa: Gemini su ogni risultato

Nel menu del risultato, «Chiedi a Gemini…» c’era solo per immagini, audio, video e una parte dei documenti. Mancavano la posta, il vecchio `.doc`, un messaggio dentro una casella, uno zip, una notizia. La chat si apriva sul file intero: il punto in cui eri arrivato con la ricerca non entrava.

Nel codice del 30/10, Standalone e Add-on. La voce c’è su ogni riga che ha un file, un messaggio o un estratto. A schermo e a voce, in cima alla conversazione: «Punto della ricerca: … Estratto: …». Gemini riceve lo stesso punto, insieme al testo.

- Un messaggio dentro una casella o un feed è una conversazione a sé. Non si manda l’archivio intero.
- Un `.eml` usa quel messaggio: oggetto, mittente e corpo.
- Un allegato PDF già estratto apre la chat su quel PDF, con il punto della ricerca.
- Un testo, un PDF, un HTML, un foglio, un epub: il testo del file, più il punto.
- Un’immagine resta l’immagine, più il punto (per esempio la riga OCR).
- Un audio o un video senza trascrizione dice ancora di generare prima il report, e intanto tiene il punto.
- Una notizia con un indirizzo e un estratto apre la chat su quell’estratto. Una riga che è solo un indirizzo, a schermo e a voce: «Questa riga è solo un indirizzo. Aprilo nel browser.»
- Se dal risultato non esce un testo intero, la frase nel materiale è: «Da questo risultato non esce un testo intero. La conversazione parte dal punto della ricerca.»

Senza la chiave, la frase resta: «Per conversare con Gemini serve la chiave personale, da Strumenti.»

Prova di Maurizio, 30/10, ricerca interrotta su «qualità rossa» nel profilo Thunderbird, filtro Solo Documenti. L’esportazione in Download ha 216 risultati: Posta inviata e INBOX, un messaggio per riga. Su «Posta inviata», messaggio 3215 del 17/09/2026, Gemini ha distinto l’ordine, la risposta e il ringraziamento. La conversazione è stata salvata in Download, non dentro il profilo.

Anche, nello stesso codice: testi cercati e percorsi ricordati arrivano a 200, non più a 20. Due elenchi di frasi nelle impostazioni. Provato da Maurizio il 30/10: il disco C e «Juventus-Napoli» sono il ventunesimo, in cima. Vale sulla Standalone avviata da `app_gui.py`.

Ctrl+Alt+V, se negli Appunti non c’è un file, prende il testo di un messaggio (almeno un messaggio vero, non due parole) e lo mette in elenco: «Messaggio incollato. È in elenco: … Da qui puoi fare altre operazioni.» Da lì, Chiedi a Gemini. Provato da Maurizio il 30/10: testo copiato da un messaggio, e un `.eml` salvato incollato senza aprirlo. Il trascinamento di un file, compreso un `.eml`, resta quello di prima. Se il file è un `.eml`, dopo la riga in elenco sia la Standalone sia l’Add-on chiedono: «Apri ora la lettura di questo documento?» Se sì, si apre il lettore. La prova col mouse la fa papà sull’Installer pubblicato.

## Poi, non iniziati

In quest’ordine, salvo la scelta sul lettore:

1. VIDEO_TS: un avviso chiaro su un DVD commerciale, anche quando ci arrivi con la ricerca. Niente copia del film. La frase di quando scegli la cartella c’è già dalla 1.7.6.
2. OneCore: la voce di Windows nella Standalone, oltre alle voci già registrate come SAPI.
3. Export multipli: più di un formato nello stesso passaggio.

Nel lettore, anche un browser dentro RTAD: seguire i link e le intestazioni. Ne abbiamo parlato il 28/10: il lettore HTML toglie i tag e tiene titoli e paragrafi, e non segue i link. Non è un browser. Non è deciso se questa entra prima delle tre qui sopra. Si sceglie quando la 1.9.0 è pubblicata.

Più avanti, non in questa lista:

- Confrontare il parlato di un audio o di un video. Prima la trascrizione che c’è già, poi lo stesso confronto delle frasi.
- Confrontare il testo di un’immagine. L’OCR che c’è già, oppure una descrizione con Gemini.

Un feedback vero, o un altro file che si comporta male, passa davanti a questa lista.

## Cosa non entra

- Un hotfix della 1.8.9 già pubblicata.
- Copiare il film da un DVD commerciale.
- Qualsiasi ritocco a Whisper. La 1.8.6 resta com’è.
