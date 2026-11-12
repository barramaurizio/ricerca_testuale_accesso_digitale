# Piano RTAD 2.0.1

**Pubblicata** il 12/11/2026. Versione `2.0.1`. GitHub `v2.0.1` / `app-v2.0.1`. Il commit corto e il numero DataStore si aggiungono prima del push. Vale per Standalone e Add-on, tranne le voci di Esplora file, che sono solo della Standalone installata. A schermo e a voce. Il tasto e il gesto del mouse che fa la stessa cosa stanno nella stessa frase.

L’ultima pubblicata prima di questa è la `2.0.0` (11/11/2026, GitHub `v2.0.0` / `app-v2.0.0`, commit `b70e333`, DataStore #12942 via #12943). Non si rifà.

## Primo punto

Taglia e unisci immagini. L’anteprima è più alta, così la foto si vede meglio mentre si lavora. Il file scritto resta a misura intera: una foto 900 per 900 resta 900 per 900.

Invio sul pulsante Un quarto a destra, o un clic, gira l’immagine di un quarto verso destra. Invio sul pulsante Un quarto a sinistra, o un clic, la gira dall’altra parte. Invio sul pulsante Mezzo giro, o un clic, la capovolge. Il giro toglie il taglio già scelto su quella riga. Il file di partenza resta com’è. Invio sul pulsante Esegui, o un clic, scrive il file nuovo: si chiama nome-giro-un-quarto-a-destra, nome-giro-un-quarto-a-sinistra o nome-giro-mezzo-giro. Il file unito si chiama Unito-uno-sotto-l-altro oppure Unito-uno-accanto-all-altro. Se il nome c'è già, si aggiunge -2. Dall’elenco, Alt e la lettera: B un quarto a destra, J un quarto a sinistra, N mezzo giro.

## Esplora file, solo Standalone installata

Dentro «Cerca con Accesso Digitale»: su un’immagine la voce «Taglia e unisci»; su un audio o un video «Taglia e unisci» e «Converti». Invio sulla voce, o un clic, apre la finestra con quel file già in elenco. L’Add-on non aggiunge voci in Esplora file. La voce compare dopo l’Installer. Da `app_gui.py` si prova con `--image-clip`, `--clip` e `--convert`. Prima dell’Installer, `python tools/rtad_shell_preview.py add` scrive le voci di prova e `remove` le toglie.

## Rinomina, Standalone e Add-on

Nella cronologia di Gemini, Invio sul pulsante Rinomina, o un clic, dà un nome nuovo alla conversazione. Il contenuto resta com’è. Un clic solo seleziona la riga. Invio sul pulsante Apri, o un doppio clic, la apre.

## Resta fuori, per la 2.0.2

Il nome di un’immagine salvata da una pagina, quando il testo del post non sta nell’indirizzo: il video prende il titolo, l’immagine prende il pezzo di indirizzo, spesso il profilo. Non si indovina. La sincronizzazione fra Add-on e Standalone è una versione a parte: le chat della Standalone stanno in `%AppData%\Roaming\RTAD_Standalone`, quelle dell’Add-on nel profilo NVDA. Poi PDF e testo, poi un audio su un video e le immagini in un PDF.
