# Piano RTAD 2.0

**Pubblicata** l’11/11/2026. Versione `2.0.0`. GitHub `v2.0.0` / `app-v2.0.0`, commit `b70e333`. DataStore #12942 via #12943 accettato. Vale per Standalone e Add-on. A schermo e a voce. Il tasto e il gesto del mouse che fa la stessa cosa stanno nella stessa frase. Non si rifà.

L’ultima pubblicata è la `2.0.0`. Prima: `1.9.10` (9/11/2026, GitHub `v1.9.10` / `app-v1.9.10`, commit `2f1d38c`, DataStore #12896 via #12898). Non si rifà.

Il 7/11/2026 Maurizio ha chiesto di unire e di tagliare, scegliendo le parti da tenere o da togliere, su video, audio e immagini. Il 10/11/2026 ha confermato l’ordine qui sotto: prima l’orologio, poi le immagini, poi i documenti, poi il passaggio da un formato all’altro.

Il file di partenza non si tocca. Si scrive un file nuovo, nella stessa cartella. L’esito sta a schermo e lo dice la voce.

## Primo punto — in corso

Finestra «Taglia e unisci», menu Strumenti, e sul risultato audio o video la voce «Taglia e unisci».

Un elenco ordinato. L’elenco vuoto dice «Nessun file in elenco.» Invio o doppio clic su una riga ascolta quel pezzo. Un clic solo seleziona la riga.

- **Tieni da qui a qui.** Due numeri, `1:20`, sono un minuto e 20 secondi. Tre numeri, `01:20:50`, sono un'ora, 20 minuti e 50 secondi. Se si scrive solo la Fine, il tratto parte dall'inizio. Se si scrive solo l'Inizio, il tratto arriva fino alla fine del file. Poi Tieni memorizza il tratto su quella riga.
- **Togli questo tratto.** Tiene il prima e il dopo. In elenco si legge «tolto da». Vale lo stesso: solo la Fine toglie dall'inizio, solo l'Inizio toglie fino alla fine.
- **Altro tratto.** Aggiunge quel tratto come riga nuova. La riga già scelta resta. Una riga è un tratto. Più tratti dello stesso file sono più righe.
- **Esegui.** Taglia la riga selezionata, se un tratto è già scelto.
- **Unisci.** Con almeno due file, unisce l'elenco: il file intero, oppure il tratto già scelto con Tieni. Il file si chiama Unito, poi Unito-2. Non prende il nome di uno dei file.
- **Fatti.** Ogni file creato resta in elenco, con l'operazione e la durata di ogni file. Lo Stato, la barra di stato e Fatti dicono la stessa frase. Invio o doppio clic rimette il file nell'elenco di lavoro. Un clic solo seleziona la riga.
- **Scorciatoie.** Dall'elenco, Alt e la lettera del pulsante: A Aggiungi, S Sposta su, G Sposta giù, M Rimuovi, C Ascolta, F Ferma, T Tieni, O Togli, L Altro tratto, E Esegui, U Unisci. Sono diverse tra loro. Alt+R resta a NVIDIA.
- Se i file non sono uguali: «I file non sono uguali: li converto, ci vuole più tempo.»
- Se manca FFmpeg: «Per questo formato serve ffmpeg».
- A lavoro finito: «Creato nome, durata, nella stessa cartella.»

Audio e video usano lo stesso orologio e lo stesso FFmpeg già cercato dal programma. Un audio e un video, in questo punto, non si uniscono tra loro.

## Immagini — in corso

Finestra «Taglia e unisci immagini», menu Strumenti, e sul risultato immagine la voce «Taglia e unisci». Il file di partenza non si tocca.

- **Metà.** Sinistra, destra, sopra, sotto, centro. Il pulsante scrive i quattro numeri e li tiene sulla riga.
- **Quattro numeri.** Sinistra, alto, larghezza, altezza. Invio sul pulsante Tieni questo taglio, o un clic, li tiene sulla riga.
- **Mouse.** Trascinare un rettangolo riempie gli stessi quattro numeri. Al rilascio il taglio è sulla riga.
- **Esegui.** Scrive il taglio della riga selezionata.
- **Uno sotto l'altro** e **Uno accanto all'altro.** Con almeno due immagini. L'immagine intera, oppure il taglio già scelto.
- **Fatti.** Ogni file creato resta in elenco. Invio o doppio clic lo rimette nell'elenco di lavoro. Un clic solo seleziona la riga.

## Poi, se l’elenco regge

1. **PDF e testo.** Pagine da-a, più PDF nell’ordine. I testi si uniscono con il nome del file come titolo. Nel lettore, «Salva il brano scelto» scrive un file nuovo. Dentro un solo file: l’intervallo di pagine, oppure quel brano.
2. **Da un formato all’altro**, ognuno con la sua frase: questo audio su questo video; queste immagini in un solo PDF.
3. **Convertitore audio e video.** Provato nella Standalone l’11/11/2026: da MP4 a MP3, da MP3 a M4A, e una cartella intera da MP4 e M4A a MP3. Finestra «Converti audio e video». Un formato per tutte le righe. Converti la riga, oppure Converti tutti. Da un video a un formato audio si tiene solo l'audio. Un audio non diventa un video. Il file di partenza resta com'è. Aggiungi cartella, nelle tre finestre, legge solo quella cartella. La scelta di più file nella finestra di Windows, con NVDA, non resta: entra un file solo. Un file alla volta, e Aggiungi cartella, sì.
4. **Ruotare un’immagine.** Un quarto di giro, o mezzo giro, per raddrizzare una foto storta. Maurizio l’ha chiesto il 10/11/2026. È un passo a parte, dopo il taglio e l’unione.
5. **Altre estensioni, solo in lettura.** Dall'11/11/2026: M4B, AIFF, MKA, FLV, MTS e M2TS. La ricerca, Aggiungi file e Aggiungi cartella le vedono. Non sono formati nuovi in uscita: in uscita restano MP3, M4A, WAV, FLAC, OGG, Opus, WMA, MP4 e MKV.

## Resta fuori

Mettere le immagini in diagonale, o affiancate ma non allineate, o in una posizione libera. Dissolvenze, titoli sopra il filmato, più tracce una sull’altra, il montaggio da studio. Un contenuto con protezione DRM resta non scaricabile.
