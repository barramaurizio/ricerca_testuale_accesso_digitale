# Piano RTAD 1.9.9

**In corso.** La 1.9.8 è già pubblicata il 7/11/2026 (GitHub `v1.9.8` / `app-v1.9.8`, commit `771db55`, DataStore #12813 via #12814). Non si rifà.  
**Decisione dell’8/11/2026.** Le finestre di Salva e Sfoglia, l’apertura dentro RTAD, Apri cartella, Ordinamento e lo stato dopo una copia sono della Standalone. L’Add-on resta sulle finestre di Windows e su NVDA. Nell’Add-on, di questa versione, restano i 4 secondi su Solo Audio e Video e il ritorno del focus dopo che la finestra di ricerca è rimasta ferma. A schermo e a voce. Il tasto e il gesto del mouse che fa la stessa cosa stanno nella stessa frase.

## Finestre nostre

Salva e Sfoglia di Windows, con NVDA spento, restano mute. Al loro posto, finestre di RTAD.

In quelle finestre, come nella finestra principale:

- Alt+P legge lo stato. Premerlo due volte di seguito copia lo stato negli appunti.
- La lettera S porta alla casella di sola lettura dello stato e alla barra di avanzamento. Invio non serve: il tasto S raggiunge la casella, come il clic sull’etichetta.

Con NVDA acceso, e con «Solo la voce di questo programma» spento, quelle frasi le dice NVDA. Con la voce di RTAD accesa, le dice RTAD. Ctrl+Shift+S resta com’è: una voce alla volta. I due modi fanno lo stesso gesto.

## Alt+P e i tasti di spostamento

Segnalato il 6/11/2026, sulla Standalone, con le voci di RTAD e senza NVDA.

«Pronuncia i tasti di spostamento» acceso: Alt+P fa sentire solo una «s», l’inizio di «Stato», e la frase si interrompe. L’opzione spenta: Alt+P dice lo stato per intero, e la seconda pressione lo copia.

Il nome del tasto viene detto dopo, e sostituisce la frase appena partita. «Dove sei» già zittisce il nome del tasto prima di parlare. Alt+P e la lettera S fanno lo stesso: prima la frase dello stato, il nome del tasto non la copre.

## «Non sei nel programma?» nello Stato

La voce, mentre si è fuori, resta. Alt+Tab dice «Non sei nel programma?» a ogni finestra, e quando si torna dice dove si era.

Quella frase oggi resta scritta nella casella Stato anche dopo il ritorno, finché un nuovo avanzamento non la sostituisce. Al ritorno la casella riprende la riga che c’era prima di uscire: il download, la ricerca, o l’ultimo esito. La voce dice una volta dove si è. Non si aggiunge una seconda riga fissa del tipo «sei nel programma», perché resterebbe lì allo stesso modo. A icona, la frase utile è quella detta con Alt+Tab. La casella non va aggiornata per chi in quel momento non la legge.
