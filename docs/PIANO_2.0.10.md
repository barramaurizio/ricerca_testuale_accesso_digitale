# Piano RTAD 2.0.10

**Pubblicata** il 24/11/2026. GitHub `v2.0.10` / `app-v2.0.10`, commit `046f0cd`. Il numero DataStore si aggiunge quando lo store l’accetta. Versione `2.0.10`. Vale per Standalone e Add-on. A schermo e a voce. Il tasto e il gesto del mouse che fa la stessa cosa stanno nella stessa frase. Caselle di scelta: `wx.CheckBox` o `wx.RadioButton` vere, non `CheckListBox`.

L’ultima pubblicata prima di questa era la `2.0.9` (22/11/2026, GitHub `v2.0.9` / `app-v2.0.9`, commit `7a8ef52`, DataStore #13179 via #13180 accettato). Non si tocca. Piano `docs/PIANO_2.0.9.md`.

## Perché questa versione

Il piano 2.0 lasciava per ultimo PDF e testo. Le immagini in un solo PDF sono la 2.0.9. Qui si prendono pagine da un PDF già fatto, si mettono più PDF nell’ordine, e dal lettore si salva solo il testo selezionato.

## Finestra «PDF e testo»

Menu Strumenti, e sul risultato PDF la voce «PDF e testo…». Invio sulla voce, o un clic.

- Elenco. L’elenco vuoto dice «Nessun file in elenco.» Sulla riga si legge il nome e quante pagine ha il file. Pagina 1 è la prima del file.
- Due campi, Da e A. Solo A: dalla prima fino a quella. Solo Da: da quella fino all’ultima. Invio sul pulsante Tieni queste pagine, o un clic, aggiunge l’intervallo sulla riga. Gli intervalli già tenuti restano. Cancella Da e A, scrivi un altro intervallo, poi Tieni di nuovo.
- Invio sul pulsante Scrivi il PDF, o un clic, scrive le pagine della riga selezionata. Il file si chiama `nome-pagine-3-8`. Se i campi sono vuoti, entra tutto il file.
- Con almeno due intervalli sulla stessa riga, oppure con almeno due PDF, Invio sul pulsante Unisci i PDF, o un clic, li mette insieme. Più intervalli sulla stessa riga entrano tutti, nell’ordine in cui li hai tenuti. Più PDF: nell’ordine dell’elenco. Il nome di più file porta le pagine di ognuno: `nome1-pagine-1-13-unione-nome2-pagine-1-8-9-20`. Da tre in su: i primi due, con le loro pagine, e `e-N`. Un solo file con più intervalli si chiama `nome-pagine-1-8-9-20`.
- Invio sul pulsante Unisci i testi, o un clic, scrive un testo. Ogni file è un titolo, sotto c’è il testo delle pagine tenute. Vale anche con un solo PDF. Il file si chiama `nome-testo`, oppure lo stesso nome dell’unione con `-testo` in coda, pagine comprese.
- Se la pagina non c’è: «La pagina 40 non c’è: questo file ne ha 12.» A schermo e a voce. Non si scrive un file rotto.
- Un PDF di sole scansioni resta un PDF di quelle pagine. Il testo si crea lo stesso, e dentro c'è solo: «Nessun testo in queste pagine.»
- Se il PDF di partenza ha una firma, lo Stato dice: «Il file nuovo non porta la firma.»
- Il file di partenza resta com’è. Il file nuovo sta nella stessa cartella. Se il nome c’è già, si aggiunge `-2`.
- Stato, barra di stato e Fatti dicono la stessa frase. Invio o doppio clic su un fatto lo rimette nell’elenco di lavoro. Un clic solo seleziona la riga.
- Invio sul pulsante Metti da parte, o un clic, toglie la riga dall’elenco di lavoro e la lascia in Da parte. Il file sul disco resta. Invio o doppio clic su una riga di Da parte la rimette nell’elenco, con le pagine tenute se c’erano. Un clic solo seleziona la riga. L’elenco vuoto dice «Nessun file da parte.»
- Aggiungi file, Aggiungi cartella, Incolla. Le cartelle dentro non si aprono. Control+Alt+V fa la stessa cosa di Incolla. Trascinare un PDF o una cartella sulla finestra fa la stessa cosa.
- Dall’elenco, Alt e la lettera: A Aggiungi file, K Aggiungi cartella, H Incolla, S Sposta su, G Sposta giù, D Metti da parte, T Tieni queste pagine, E Scrivi il PDF, U Unisci i PDF, Z Unisci i testi. Alt+P, in questa finestra, legge lo Stato: premuto due volte di seguito lo copia. Alt+R resta a NVIDIA.

Nella Standalone installata, in Esplora file: «PDF e testo». Invia a: «PDF e testo RTAD». Portable e Add-on: niente voce automatica in Esplora.

Le pagine si copiano dal PDF, con `pypdf` nel programma. Il writer della 2.0.9, che disegna foto su un foglio, qui non si usa.

## Lettore

Accanto a Salva testo, Invio sul pulsante Salva la selezione, o un clic, scrive solo il testo selezionato: `nome-selezione.txt`, nella stessa cartella, e lo dice a schermo e a voce. Nel riquadro: Shift e le frecce, oppure NVDA+F9 e poi NVDA+F10 una volta sola. Se non c’è una selezione: «Nessun testo selezionato. Nel riquadro, Shift e le frecce, oppure NVDA+F9 e poi NVDA+F10 una volta sola. Poi Invio sul pulsante Salva la selezione, o un clic.»

Vale per ogni documento aperto con Leggi documento. Salva testo resta tutto il documento, con la finestra di salvataggio.

Invio o doppio clic su una sezione del sommario resta nel lettore: va al testo di quella sezione e non apre l'app predefinita. A schermo e a voce dice la sezione e, se c'è, la pagina di questo file. La figura della pagina si apre qui: scrivi il numero, oppure seleziona una sezione che indica la pagina, poi Invio sul pulsante Figura di questa pagina, o un clic. La pagina si vede nella finestra e il testo disegnato è nel riquadro sotto. Invio sul pulsante Tutto sull'immagine, o un clic, la descrive. Salva testo e Salva immagine scrivono accanto a questo PDF, con il nome del PDF e il numero di pagina: Invio sul pulsante, o un clic. Stampa testo e Stampa immagine mandano alla stampante: Invio sul pulsante, o un clic.

## Dopo questa versione

`2.0.11`, non iniziata: inquadratura con fotocamera e videocamera. Piano `docs/PIANO_2.0.11.md`. Prima di dettatura, operatore e confronti.

## Resta fuori

OCR dentro questa finestra. Una pagina per file. Riordinare le pagine una per una. EPUB e Word nell’elenco di questa finestra. Dettatura, operatore, confronto del parlato, confronto del testo di un’immagine.

## Criterio «fatto»

- Un PDF di 12 pagine, Da 3 A 8: un PDF nuovo di 6 pagine, la voce e lo Stato dicono il nome. Il file di partenza resta.
- Due PDF in elenco: un PDF unito, nell’ordine, nome `nome1-unione-nome2`.
- Unisci i testi: un testo, ogni nome di file è un titolo.
- Nel lettore, una selezione diventa `nome-selezione.txt`. Senza selezione, la frase «Nessun testo selezionato.» sta a schermo e la dice la voce.
- Stesso comportamento nell’Add-on.
- Il numero `2.0.10` e le novità sono allineati.

## File

- `Standalone/rtad_pdfdoc.py` e il gemello Add-on.
- `pypdf` in `addon/.../lib/pypdf` e nei requirements della Standalone.
- `Standalone/app_gui.py` e `addon/.../__init__.py`: menu, lettore, risultato PDF.
- `Standalone/setup.iss`: Esplora e Invia a, solo Installer.
