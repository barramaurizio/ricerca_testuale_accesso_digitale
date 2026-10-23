# Piano RTAD 1.8.3

**Ultima pubblicata:** `1.8.2` — 22/10/2026. Non hotfixarla.  
**Questa versione:** in corso, non pubblicata. Standalone e Add-on insieme. Cloud Vision resta l’OCR. Whisper non si apre.

## Cosa fare

1. Conversazione Gemini senza un file già aperto. Alt+Q sulla finestra principale, e Strumenti → Nuova conversazione Gemini. Le chat nate da un file restano.
2. Nella chat, anche in quella partita da zero e in quella ripresa dalla cronologia, allegare un file o più file (immagine, documento, audio, video). Si può aggiungere anche più tardi. Il file di partenza, se c’è, resta. Fino a 12 allegati. Alt+A apre l’elenco della cartella, i più recenti in cima (nome, data, tipo, dimensione; durata se ci si ferma su un audio o un video). La finestra di Windows resta per le cartelle piccole. Togli allegato ne leva uno. Shift+Invio nella domanda va a capo e non invia.
3. HTTP 402 in italiano: i crediti prepagati di quella chiave sono finiti, si ricaricano in Google AI Studio. Non si prova un altro modello. Vale per chat, descrizione immagine e audio/video.

## Cosa non entra

- Chat da un `.rtad.txt` già salvato, senza rifare l’analisi.
- Una riga di prompt sui nomi dei giocatori (Woltemade / Koopmeiners). Capita di rado e il glossario non è lo strumento giusto.
- Whisper, confronto tra più file come funzione a sé, VIDEO_TS, OneCore, export multipli.

## Prova

- Alt+Q apre la chat senza un file. Una domanda di solo testo riceve risposta.
- Da lì, Alt+A apre l’elenco (i più recenti in cima). Due file insieme, poi un terzo. La domanda successiva li usa.
- Shift+Invio va a capo e non invia. Invio da solo invia.
- Su una cartella grande (Juve), l’elenco mostra tutti i file, non solo i primi che carica Windows.
- Su una chat già aperta da un documento, Alt+A aggiunge un’immagine. Il documento resta.
- Si riapre dalla cronologia e gli allegati ci sono ancora, se i file sono sul disco.
- Con una chiave che risponde 402, la frase è in italiano e non cambia modello.
