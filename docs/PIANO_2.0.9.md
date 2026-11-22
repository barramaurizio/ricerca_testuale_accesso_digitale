# Piano RTAD 2.0.9

**Pubblicata** il 22/11/2026. GitHub `v2.0.9` / `app-v2.0.9`, commit `7a8ef52`. Versione `2.0.9`. Vale per Standalone e Add-on. A schermo e a voce. Il tasto e il gesto del mouse che fa la stessa cosa stanno nella stessa frase. Caselle di scelta: `wx.CheckBox` o `wx.RadioButton` vere, non `CheckListBox`.

L’ultima pubblicata prima di questa era la `2.0.8` (20/11/2026, GitHub `v2.0.8` / `app-v2.0.8`, commit `c8512b5`). Non si tocca. Piano `docs/PIANO_2.0.8.md`.

## Perché questa versione

Due porte, una storia: l’immagine che nel programma ancora non arriva dove si legge.

1. **Queste immagini in un solo PDF.** È la frase rimasta del piano 2.0, dopo «questo audio su questo video» (2.0.6 e 2.0.7). Estrarre un’immagine da un PDF c’è già (Descrivi, Copia, Salva, dalla 1.6.4 e dalla 1.7.1).
2. **La figura nel capitolo EPUB.** Dalla 1.9.2 le figure restano nel file e il lettore le salta. Libro di prova: `J:\Libri\Sean Carroll - La fisica dei quanti.epub`. 178 JPEG, 231 richiami, niente MathML: l’equazione è una foto. Testo alternativo pieno: tre (copertina, logo, il grafico delle citazioni di Weinberg). Il resto è muto.

PDF e testo (pagine da-a, più PDF nell’ordine, brano dal lettore) resta la versione dopo.

## Porta 1 — In un PDF

Nella finestra «Taglia e unisci immagini».

- Invio sul pulsante **In un PDF**, o un clic. Dall’elenco, Alt+F fa la stessa cosa.
- L’ordine dell’elenco è l’ordine delle pagine. Una immagine per pagina, su foglio A4, centrata, proporzioni tenute. Se la foto è più larga che alta, la pagina è orizzontale.
- Se sulla riga c’è un taglio o un giro, nel PDF entra quello.
- Una immagine basta: il file si chiama `nome-pdf`. Più immagini: `Unito-pdf`. Se il nome c’è già, si aggiunge `-2`.
- Il file di partenza resta com’è. Il PDF sta nella stessa cartella.
- Stato, barra di stato e Fatti dicono la stessa frase, con il nome e quante pagine. Invio o doppio clic su un fatto lo rimette nell’elenco di lavoro. Un clic solo seleziona la riga.
- L’elenco vuoto dice «Nessun file in elenco.»
- Trascinare un’immagine o una cartella sulla finestra fa la stessa cosa di Control+Alt+V. In Esplora, Control+C sul file o sulla cartella, poi nella finestra Control+Alt+V, oppure Invio sul pulsante Incolla, o un clic. Un percorso inciso negli Appunti vale lo stesso. Una cartella mette le sue immagini. Le cartelle dentro non si aprono.
- Sul risultato immagine, nel menu: «In un PDF…». Invio sulla voce, o un clic. La finestra si apre e scrive il PDF di quel file.
- Nella Standalone installata, non nella Portable e non nell’Add-on: in Esplora, tasto destro o tasto Applicazioni, Cerca con Accesso Digitale, «In un PDF». Su una cartella, «In un PDF (Accesso Digitale)». Invia a, «In un PDF RTAD», anche su più file selezionati insieme. Taglia e unisci resta dov’è.

## Porta 2 — Figura e formula nel capitolo

Nella finestra del capitolo della 1.9.2. Elenco **Figure**, sotto i link. Invio o doppio clic sulla riga. Un clic solo seleziona.

- La foto o la formula che sta da sola nel paragrafo: nel testo e in elenco, «Figura: …» se c’è il testo alternativo, altrimenti «Figura senza didascalia.»
- La formula dentro la frase: nel testo la parola «formula». In elenco: «Formula: …» oppure «Formula senza didascalia.»
- Il segno ripetuto (cappello, indice): nel testo la parola «simbolo». Non entra in elenco.
- Senza figure: «Nessuna figura in questo capitolo.»
- Invio o doppio clic apre **Tutto sull’immagine** su quel file, estratto dal libro. La voce dice la riga e «Apro Tutto sull’immagine.»
- Lo stato del capitolo conta anche le figure: «Capitolo: titolo. N intestazioni, M link, F figure.»

Non è un visualizzatore. Non c’è un motore di formule: le parole arrivano da Tutto sull’immagine, come per una foto.

## Windows 7

Dalla Portable 2.0.8 il programma è costruito con Python 3.13 (su questo PC, 3.13.17). All’avvio, prima del codice di RTAD, Windows carica `python313.dll`. Quella libreria chiede `PssQuerySnapshot` in `KERNEL32.dll`, punto di ingresso presente da Windows 8.1. Su Windows 7 le due finestre sono: «Impossibile trovare il punto di ingresso PssQuerySnapshot» e «Failed to load Python DLL … python313.dll».

La 2.0.7 partiva perché era stata compilata sull’Acer, con un Python precedente. Non è una funzione rotta nella 2.0.8.

Non si ricompila la 2.0.9 con un Python vecchio per farla partire su Windows 7. Chi resta su Windows 7 tiene la Portable 2.0.7. Nella guida, una frase fra i requisiti, non come primo punto delle novità.

## Resta fuori

- PDF e testo: pagine da-a, più PDF nell’ordine, «Salva il brano scelto» nel lettore.
- Dettatura vocale, operatore integrato, confronto del parlato, confronto del testo di un’immagine.

## Criterio «fatto»

- Tre foto in Taglia e unisci immagini: un PDF, la voce e lo stato dicono il nome e le pagine. I file di partenza restano.
- Capitolo 1 di Carroll: la formula a sé è una riga «Figura senza didascalia.»; la frase di Newton resta leggibile e contiene «formula»; un cappello nella frase è «simbolo» e non riempie l’elenco; Invio sulla riga apre Tutto sull’immagine.
- Stesso comportamento nell’Add-on.
- Il numero `2.0.9` e le novità sono allineati.

## File

- `Standalone/rtad_image.py` e il gemello Add-on.
- `Standalone/rtad_html_page.py` e il gemello Add-on.
- `Standalone/app_gui.py` e `addon/globalPlugins/ricerca_testuale/__init__.py`: la figura apre Tutto sull’immagine.
