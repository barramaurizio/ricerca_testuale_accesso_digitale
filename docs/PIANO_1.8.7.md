# Piano RTAD 1.8.7

**Ultima pubblicata:** `1.8.6` — 26/10/2026. Non hotfixarla.  
**Questa versione:** in corso, non pubblicata. Standalone e Add-on insieme.

Già nel codice, sera del 26/10:

- I codici `&#` degli EPUB diventano lettere e segni, nel lettore e nel testo copiato.
- Un file o una cartella aperti da Esplora file restano in elenco, anche se il programma era chiuso. Frase: «Il file è in elenco: nome. Da qui puoi fare altre operazioni.»
- L’installer registra Apri con, senza diventare il programma predefinito. Su audio e video analizza, non riproduce. Si vede solo dopo `compila.bat` e l’installazione.
- 27/10, provato su Standalone e Add-on: più punti di lettura, anche su txt e PDF. In un PDF, 202 7 torna 2027.

Il segnalibro di lettura è nel codice. Va provato nel lettore prima di pubblicare.

## Cosa fare

1. Segnalibri di lettura, nel codice: Control+B ne aggiunge uno, quanti ne vuoi. Il precedente resta. Alla riapertura si torna sull’ultimo. Se sono più di uno: «Segnalibro di lettura 2 di 3: ripreso da qui.» Nell’elenco, Invio sceglie. Control+Shift+B torna all’ultimo.
2. Vale per PDF, EPUB e gli altri documenti che il lettore già apre.
3. È distinto dai Segnalibri di oggi (Ctrl+D): quelli salvano un percorso di ricerca, non la pagina o il punto nel testo.
4. Stessa frase a schermo e a voce, in Standalone e Add-on.

## Cosa non entra

- Il confronto tra più file, Gemini su ogni risultato, VIDEO_TS, OneCore, export multipli.
- Un secondo motore di traduzione. La traduzione automatica su ogni video.
- Qualsiasi ritocco a Whisper. La 1.8.6 resta com’è.

## Prova

- Aprire un documento lungo, andare avanti, mettere il segnalibro, chiudere, riaprire e trovarsi allo stesso punto. A voce e a schermo.
- Il libro di prova è `I:\Libri\Sean Carroll - La fisica dei quanti.epub`. Compleanno: 2 novembre.
- Un Segnalibro di percorso (Ctrl+D) resta un percorso: non diventa un punto di lettura.
