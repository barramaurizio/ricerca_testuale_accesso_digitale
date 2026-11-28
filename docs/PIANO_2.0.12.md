# Piano RTAD 2.0.12

**Pubblicata** il 28/11/2026. GitHub `v2.0.12` / `app-v2.0.12`, commit `0f55495`. Vale per Standalone e Add-on. Non si tocca la `2.0.11` pubblicata.

Due cose, nella stessa versione.

## 1. Modificare e scrivere in un PDF

Finestra «Scrivi nel PDF». Strumenti, Invio sulla voce, o un clic. Anche dal menu del risultato, su un PDF. Nella Standalone installata: Esplora file, Cerca con Accesso Digitale, e Invia a «Scrivi nel PDF RTAD». Portable e Add-on: niente menu di Esplora file automatico.

A voce e a schermo, la stessa frase. Pagina 1 è la prima del file. La pagina, in sola lettura, mostra il testo di questa pagina. Le frecce e un clic scelgono la riga. Pagina su e Pagina giù cambiano pagina. Invio sul pulsante Pagina precedente o Pagina successiva, o un clic, fa la stessa cosa. Invio o doppio clic sulla pagina porta sulla pagina in modifica. Tab fa la stessa cosa. La pagina in modifica è la stessa pagina, tutta. Invio va a capo: si può scrivere tra una riga e l'altra. Backspace cancella il carattere prima del cursore, Canc quello dopo. Le frecce e un clic si muovono nel testo. Pagina, riga e carattere non si dicono da soli. La lettera S, fuori dalla pagina in modifica, oppure Alt+P, li legge. Un clic sull'etichetta Stato fa la stessa cosa di Alt+P. Nella pagina in modifica la lettera S scrive la esse. La pagina in sola lettura si aggiorna subito. Maiusc+Tab torna sulla pagina. Se la pagina è modificata e non ancora scritta, lo Stato lo dice. Invio sul pulsante Riscrivi, o un clic, scrive le righe cambiate e le righe aggiunte. Fino a quel momento il file non cambia. Se tra due righe non c'è spazio, lo Stato lo dice.

Nell'elenco Posto, freccia su e giù: sotto la riga, in alto a sinistra, in alto al centro, a metà pagina a sinistra, in basso a sinistra, in basso a destra, oppure su una pagina bianca nuova. Carattere: Helvetica o Times, normale o grassetto, oppure Courier. Misura: piccolo 10, normale 12, grande 16, titolo 22.

Invio sul pulsante, o un clic, fa la stessa cosa di Alt e la lettera. Annotazione, Nota mia, Collegamento e Firma scrivono subito. Alt+E salva sempre questa pagina: lo Stato dice Salvato e il nome del file. Il cursore resta dove hai finito. Se il carattere del PDF lo permette, la riga di prima viene sostituita. Altrimenti un rettangolo bianco la copre e lo Stato lo dice, perché un lettore potrebbe ancora leggere la riga di prima sotto il bianco. Alt+U aggiunge una scritta. Alt+W mette il nome del sito dove sta il cursore. Nome del sito e Indirizzo sono il collegamento, non la firma. Nel PDF salvato quelle parole sono cliccabili. Se non c'è spazio per una riga a sé, il testo sta all'inizio della riga dopo, prima di ciò che c'era. Alt+J scrive Nota dove sta il cursore. Alt+J un'altra volta, senza spostarsi, scrive Fine nota in fondo a questa riga. Se la frase continua, si va sull'ultimo carattere da includere, anche più sotto, anche sul punto, e Alt+J scrive Fine nota dopo quel carattere. Alt+Maiusc+M apre la finestra della nota mia: Invio va a capo, l'ultima riga è Fine nota, e il testo entra dove sta il cursore senza segnare ciò che segue. La firma è in corsivo. Alt+M resta Strumenti. Alt+X, Alt+Y e Alt+Maiusc+Z segnano l'inizio dove sta il cursore e, premuti di nuovo, chiudono sul carattere di arrivo, anche più sotto. Lo Stato dice la prima parola e l'ultimo carattere. Il carattere dopo resta fuori. Per escludere il punto, fermarsi sulla lettera prima. Alt+D scrive nome e cognome dove sta il cursore. Nell'elenco Posto, un punto scelto, per esempio in basso a sinistra, mette la firma lì. Il campo Nome e cognome non è il collegamento. Nella Standalone, Tab sul pulsante Scegli immagine, poi Invio, o un clic, mette l'immagine della firma in basso a destra. Sull'Add-on l'immagine non entra: manca Pillow. Il nome scritto entra lo stesso. Alt+O apre un PDF. Alt+P legge lo Stato, due volte lo copia. Control+Alt+V incolla il PDF copiato. Trascinare il PDF sulla finestra fa la stessa cosa. Esc chiude.

La firma elettronica p7m resta di Aruba Sign. Qui entra il nome scritto, e se si sceglie un'immagine, anche quella. Se il PDF di partenza ha una firma elettronica, il file nuovo non la porta. Il file di partenza resta com'è. Il file nuovo si chiama nome-scritto. Se il nome c'è già, si aggiunge -2. Una scansione senza testo non ha righe: si scrive lo stesso, nel posto scelto o su una pagina bianca. Se un carattere non entra nel font scelto, lo Stato dice quale e non lo scrive.

Glielo hanno chiesto in diversi, e lo vuole anche Maurizio. Acrobat è a pagamento. Firefox modifica i PDF: non è questo programma. RTAD predefinito per i PDF, e un abbonamento per queste funzioni, restano più avanti, se Maurizio vorrà.

## 2. Tutte le foto di un post su X

Dalla 2.0.3 l’elenco del post si ferma a quattro foto. Il 26/11/2026 X ne consegna di più. Il post https://x.com/juventusfc/status/2125892317617725946 («La Coppa Intercontinentale 1996») ne ha 6. La pagina HTML ha già i sei indirizzi `pbs.twimg.com`, in quest’ordine. RTAD ne ha date le prime quattro, in `J:\Juve`, con la descrizione accanto.

1. Del Piero nello spogliatoio, intervistato, coppa a palla d’oro fra le gambe.
2. In aereo: fascia del sol levante, Del Piero col ventaglio.
3. Nello spogliatoio, sorriso, coppa tenuta con due mani.
4. La formazione in campo, undici, di notte.
5. Manca: la festa in pedana, di notte, coppe alzate, fascia «EUROPEAN/SOUTH AMERICAN CUP WINNER», a destra una maglia col 3.
6. Manca: Del Piero di spalle col 10, un avversario in maglia bianca con la fascia rossa è a terra.

Il fermo era `_POST_IMAGE_LIMIT = 4` in `Standalone/rtad_ocr.py`, usato da `image_urls_from_html` nel ramo del post. Ora è 40, come `_PAGE_IMAGE_LIMIT` delle altre pagine. L’elenco ha una casella vera per riga. La frase del post era già pronta per un numero qualsiasi: `post_images_choice_hint`. Spazio sulla casella, o un clic, accende o spegne. Invio sul pulsante Scarica e descrivi, o un clic, prende le selezionate una dopo l’altra. Invio su Solo la prima, o un clic, prende solo la prima. Il nome resta il testo del post, con 1, 2, 3… Il navigatore dell’Add-on resta per la figura sotto il focus. Stessa cosa in Standalone e Add-on. Le caselle sono `wx.CheckBox`, una per riga.
