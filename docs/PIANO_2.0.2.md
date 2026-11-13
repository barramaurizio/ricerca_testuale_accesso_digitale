# Piano RTAD 2.0.2

**Pubblicata** il 13/11/2026. Versione `2.0.2`. GitHub `v2.0.2` / `app-v2.0.2`. Il commit corto e il numero DataStore si aggiungono prima del push. Vale per Standalone e Add-on. A schermo e a voce. Il tasto e il gesto del mouse che fa la stessa cosa stanno nella stessa frase.

L’ultima pubblicata prima di questa è la `2.0.1` (12/11/2026, GitHub `v2.0.1` / `app-v2.0.1`, commit `c430151`, DataStore #12978 via #12979 accettato). Non si rifà.

## Primo punto

Salva immagine. Se la pagina, nel momento in cui il report è pronto, consegna il testo del post, il file propone un pezzo breve di quel testo. Invio sul pulsante Salva immagine, o un clic, salva con quel nome. Se la pagina non consegna il testo, il nome resta quello di oggi, preso dall’indirizzo. Il testo disegnato dentro la foto resta fuori. Non si inventa un titolo. Il salvataggio, la finestra e il file scritto restano quelli di oggi.

Con Ctrl+Alt+V, o Descrivi da URL, si può incollare l’indirizzo del post oppure l’indirizzo della foto: con il post, il nome è il commento; con solo la foto, se l’hai già descritta con la pagina, il nome resta quello del post. Vale per X e per le altre pagine che mettono il commento nel testo della pagina. Se la pagina non lo consegna, il nome non cambia.

## Secondo punto

Cartella comune `%AppData%\Roaming\RTAD`. Le chat di Gemini, i punti di lettura e i profili di ricerca della Standalone e dell’Add-on si leggono e si scrivono lì. Portable e Installer già condividevano `%AppData%\Roaming\RTAD_Standalone`: da questa versione le chat, i punti e i profili stanno nella cartella comune, insieme all’Add-on. Le copie vecchie restano dov’erano e si copiano una volta. Se le due copie sono diverse, restano tutte e due.

Se la stessa conversazione è stata cambiata in tutte e due, a schermo e a voce: «Questa conversazione è stata cambiata anche nell'altra copia. Non l'ho sovrascritta. Restano tutte e due.» Se all’avvio le due copie erano diverse, a schermo e a voce: «Due copie di una conversazione sono diverse. Le tengo tutte e due. Non ne ho sovrascritta una.» Niente si sovrascrive in silenzio.

La voce, la posizione della finestra e le chiavi restano nel programma che le ha. Le due Standalone continuano a condividere il resto in `RTAD_Standalone`.

## Resta fuori

PDF e testo. Un audio su un video. Le immagini in un PDF. Non entrano nella 2.0.2.
