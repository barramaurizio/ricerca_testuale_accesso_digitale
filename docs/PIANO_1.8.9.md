# Piano RTAD 1.8.9

**Ultima pubblicata:** `1.8.8` — 28/10/2026. Non hotfixarla.  
GitHub `v1.8.8` / `app-v1.8.8`, commit `93faddb`. DataStore #12565 chiuso via #12566, accettato.  
Commit `ee28948`: finestra di benvenuto e guida HTML allineate. Gli exe della Standalone sulla release sono stati sostituiti. Il pacchetto Add-on dello store resta quello accettato.  
**Questa versione:** `1.8.9`, testi scritti il 29/10/2026. Il pacchetto Add-on locale è pronto. I due exe li compila Maurizio. Non è ancora su GitHub né sullo store.

## Prima cosa: lettore sui PDF DocuSign firmati

Tre accordi in Download:

- `Completa_con_Docusign_Raccontidoc_Eredi_Po.pdf`
- `Completa_con_Docusign_Eredi_Polledro_x_Dosto.pdf`
- `Completa_con_Docusign_Eredi_Polledro_x_Puški.pdf`

Sul web si leggono. Nel lettore di RTAD le parole dei font Identity-H uscivano mescolate (`WUDGXWWRUH` per «traduttore»). Apostrofo, virgolette e trattino erano lo stesso buco.

Le tabelle delle lettere sono stream normali e il lettore le sapeva già aprire. Il collegamento `/ToUnicode` e l’elenco `/Font` stanno in un object stream compresso. Con più tabelle il lettore non ne sceglie una a caso, quindi senza quel collegamento restavano i codici del font. I font WinAnsi, nello stesso file, si leggevano già.

Nel codice del 29/10, Standalone e Add-on aprono l’object stream e agganciano ogni nome (`F4`, `F5`, `F6`) alla sua tabella. Lettore, copia e ricerca passano dallo stesso estrattore. Maurizio ha riletto i tre testi salvati dal lettore: Cechov, Dostoevskij e Puškin sono a posto.

Il sommario in cima diceva `印整琮汥` e, nel file di Puškin, anche `偒䕍䕓协`. Sono «Spett.le» e «PREMESSO», letti due lettere alla volta perché l’hex senza BOM veniva preso per UTF-16. Nel codice si legge il titolo come lettere. Stesso passaggio: la virgoletta di chiusura resta attaccata («Racconti»”), «sub-licenze» non ha spazi intorno al trattino, e «proporVi» resta una parola. «trascriv iamo» resta con lo spazio: il PDF spezza la parola in due pezzi e togliere quello spazio incollerebbe parole vere in altri file.

## Subito dopo: confronto tra più file

Nel codice il 29/10, Standalone e Add-on. Voce di menu «Confronta file…», in Strumenti e nel menu contestuale del risultato. Finestra unica: Aggiungi, Togli, Confronta, Chiedi a Gemini. Aggiungi apre lo stesso elenco degli allegati: Shift, Control e Alt+C. Sull’elenco del confronto, Alt+A aggiunge e Alt+L toglie il file sotto il cursore. Nella finestra di scelta, sotto la cartella, c’è l’elenco dei file già nel confronto: Alt+L ne toglie uno prima di Invio. La stessa lista, con la scritta «Allegati», è anche nella finestra di scelta di Gemini: Alt+L toglie prima di Invio. Sulla conversazione, Alt+L toglie ancora un allegato già messo, prima della domanda. Il tetto è 12, come gli allegati in chat. Salva propone Confronto.txt e, se c’è già, Confronto (1).txt. Maurizio ha confrontato i tre accordi, in locale e con Gemini: opera, compenso e codice busta tornano. Il «3» in mezzo a una frase è il numero di pagina, non una clausola. Su Dostoevskij la chiusura resta «PER»: la pagina taglia «ACCETTAZIONE». Si lasciano, non si nascondono.

Confronta lavora sul testo, senza chiave. In cima a ogni file, solo se non coincidono in tutti: tipo, dimensione, ultima modifica e, per un audio o un video, la durata. Mostra e dice solo le parti che non stanno in tutti i file, con il nome del file davanti. Le parti uguali non si rileggono. Senza almeno due file: «Servono almeno due file.» Elenco vuoto: «Nessun file nel confronto.»

Chiedi a Gemini, nella stessa finestra, parte da quelle differenze. Senza la chiave il confronto resta e la frase è «Per conversare con Gemini serve la chiave personale, da Strumenti.»

Il numero nel programma è `1.8.9`. Maurizio ha provato il confronto sulla Standalone, compresi i quattro valori quando non coincidono. Il pacchetto è `ricerca_testuale_accesso_digitale-1.8.9.nvda-addon`. Il numero è nuovo: si installa come gli altri aggiornamenti e NVDA chiede il riavvio.

## Dopo la 1.8.9, non iniziati

Quattro, in quest’ordine, quando la 1.8.9 è pubblicata:

1. Gemini su ogni risultato della ricerca.
2. VIDEO_TS: un avviso chiaro su un DVD commerciale. Niente copia del film.
3. OneCore: la voce di Windows nella Standalone, oltre a SAPI.
4. Export multipli: più di un formato nello stesso passaggio.

Più avanti, non in quelle quattro:

- Confrontare il parlato di un audio o di un video. Prima la trascrizione che c’è già (Whisper sul PC, oppure Gemini se c’è la chiave), poi lo stesso confronto delle frasi. Non è un ritocco a Whisper.
- Confrontare il testo di un’immagine. L’OCR che c’è già, oppure una descrizione con Gemini. Il confronto locale resta sul testo già letto.
- Un browser che segua i link.

Un feedback vero, o un altro file che si comporta male, passa davanti a questa lista.

## Cosa non entra

- Un hotfix della 1.8.8 già pubblicata.
- Un secondo motore di traduzione. La traduzione automatica su ogni video.
- Qualsiasi ritocco a Whisper. La 1.8.6 resta com’è.
