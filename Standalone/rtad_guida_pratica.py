# -*- coding: utf-8 -*-
"""Guida pratica RTAD — linguaggio semplice, gemello Standalone / Add-on.

Manutenzione (ogni rilascio):
  1) Aggiorna la sezione «Novità recenti (in parole semplici)» qui sotto.
  2) Lascia intatta la guida tecnica (F1 / README HTML / note di rilascio).
  3) Sincronizza questo file in Standalone/ e in addon/.../lib/.

La documentazione tecnica resta per chi vuole approfondire.
"""

GUIDE_TITLE = "Guida pratica — avvicinarsi al programma"

GUIDE_TEXT = """\
Benvenuto in Ricerca Testuale Accesso Digitale
================================================

Questa è una guida semplice. Ti spiega cosa fa il programma e come usarlo
senza termini difficili. Se poi vuoi i dettagli tecnici e l’elenco completo
dei comandi, restano disponibili la Guida ai Comandi (F1) e le altre voci
del menu Aiuto.

Il progetto esiste in due forme che lavorano allo stesso modo:
• Applicazione Standalone: un programma Windows a sé (file .exe).
• Add-on per NVDA: la stessa ricerca, dentro lo screen reader NVDA.

Le funzioni principali sono le stesse. Cambiano solo qualche scorciatoia
e il modo in cui si apre la finestra.


Novità recenti (in parole semplici) — versione 1.6.4
----------------------------------------------------
• Puoi far descrivere anche immagini dal web o dagli appunti:
  Strumenti → Descrivi da URL, dagli Appunti, oppure cattura
  lo schermo e descrivi (utile anche senza NVDA).
• Nell’Add-on NVDA: NVDA+Shift+G descrive la figura sotto il
  navigatore (lettera g sul web) oppure un file immagine
  selezionato in Esplora file/Desktop, senza aprirlo.
• Alt-text breve e Alt-text + descrizione (menu contestuale);
  Descrivi immagine da PDF (Strumenti o menu sul risultato PDF,
  oppure incolla/apri il PDF dal dialogo).
• Senza parola chiave, se scegli un tipo di file (documenti,
  immagini, audio/video…), il programma elenca i file di quel
  tipo nella cartella: utile per poi aprirli o analizzarli.
  Per cercare DENTRO un PDF serve comunque una parola.
• OCR senza testo (casella OCR attiva) resta sulle immagini,
  con filtro «Tutti» o «Solo Immagini».
• Dove usare cosa per le immagini:
  - Al volo su web / Esplora file sotto il cursore → Add-on
    (NVDA+Shift+G). Nello Standalone non c’è quella gesture.
  - URL, appunti, cattura schermo, PDF, file già nei risultati
    → Standalone e Add-on allo stesso modo (menu Strumenti).
  - In Esplora file, se hai installato il sottomenù shell della
    Standalone, puoi anche descrivere l’immagine col tasto destro.
• Non ci sono tasti globali di sistema nella Standalone (per
  evitare conflitti con NVDA e altri programmi): usa i menu
  o le scorciatoie a finestra attiva (Ctrl+Shift+U / I, ecc.).
• Solo NVDA: la gesture sul navigatore/file. URL / appunti /
  cattura / PDF / elenco per tipo sono gemello Standalone ↔ Add-on.
• Restano descrizione Gemini / Vision (1.6.3), notifica (1.6.2)…


1. A cosa serve
---------------
Ti aiuta a trovare parole o frasi nei file del computer: documenti, PDF,
libri EPUB, email, feed di notizie, e anche (se lo attivi) il testo
scritto dentro le immagini.

Esempi tipici:
• cercare una fattura o una ricevuta;
• ritrovare un messaggio di posta;
• cercare una frase in un libro .epub;
• cercare una notizia nei feed;
• leggere il testo di una cartolina o di un’immagine (con OCR).


2. Prima ricerca in quattro passi
---------------------------------
1) Indica DOVE cercare: cartella, disco, oppure «tutto il PC».
2) Scrivi COSA cercare: la parola o la frase.
3) (Facoltativo) Scegli il tipo di file: tutti, documenti, immagini…
4) Premi Avvia ricerca (oppure Invio nel campo del testo).

Durante la ricerca puoi seguire lo stato di avanzamento.
Per interrompere senza chiudere il programma: Annulla (Alt+N).
Esc, di solito, interrompe la ricerca; non chiude il programma
(a meno che tu non abbia attivato l’opzione in Strumenti).


3. Dove cercare (il «percorso»)
-------------------------------
Il percorso è semplicemente il posto in cui guardare:
• una cartella (Documenti, Download…);
• un’intera unità (per esempio D:);
• più posti insieme, separati da punto e virgola;
• oppure tutto il PC (pulsante / comando dedicato).

Il programma ricorda l’ultimo percorso usato, così non devi
riscriverlo ogni volta.


4. Segnalibri, cronologia e profili
-----------------------------------
Tre strumenti utili, in parole povere:

• Segnalibri: posti che usi spesso, salvati con un nome/elenco rapido
  (come i preferiti del browser). Scorciatoia tipica: Ctrl+D.

• Cronologia: gli ultimi testi e gli ultimi percorsi che hai cercato,
  per ripeterli in fretta (Ctrl+H per i testi, Ctrl+Shift+H per i percorsi).

• Profili: uno «scenario completo» salvato (dove cercare, che tipi di file,
  opzioni, e se vuoi anche il testo). Li carichi quando ti servono
  (Ctrl+Shift+P per salvare, Ctrl+Shift+L per caricare).


5. Tipi di file, posta e libri
------------------------------
Puoi limitare la ricerca a:
• documenti (Word, PDF, EPUB, testo…);
• immagini;
• audio/video (soprattutto sul nome file);
• oppure un’estensione che scegli tu (es. solo .pdf o solo .epub).

Per la posta (Thunderbird e simili): il programma può cercare nei messaggi
e, nei PDF allegati, anche aprire o salvare l’allegato senza dover aprire
tutta la casella di posta.

Per i libri digitali (.epub): cerca nel testo dei capitoli, come in un
documento normale. Non serve scompattare il file a mano.


6. Feed e notizie
-----------------
Se segui siti o feed Thunderbird, puoi cercare nelle notizie.
Il pulsante «Feed Thunderbird» prova a trovare da solo le cartelle giuste.
Nei risultati, Invio su una notizia apre di solito l’articolo nel browser.


7. Leggere il testo nelle immagini (OCR)
----------------------------------------
A volte il testo non è in un documento, ma «disegnato» in una foto
(cartolina, screenshot, manifesto).

• C’è una casella da attivare: «Includi testo in immagini e PDF scansionati».
• Di solito è spenta, perché questa lettura è più lenta.
• Motore predefinito: quello già presente in Windows (leggero).
• Motore facoltativo EasyOCR: spesso meglio sulle scritte stilizzate;
  più comodo nell’applicazione Standalone (installazione a parte).
  Nell’Add-on NVDA resta pratico soprattutto il motore Windows.
• Motore Google Cloud Vision: il più completo sulle grafiche difficili
  (font strani, lettere a strisce, poster). Serve Internet e la TUA
  chiave API: menu Strumenti → «Chiave API Google Vision», oppure il
  pulsante «Chiave Google». Ogni persona usa la propria chiave;
  non c’è una chiave condivisa nel programma.
• La ricerca è tollerante: anche se l’OCR legge male un titolo stilizzato
  (es. «SQUAD ST» al posto di «SQUADLIST»), spesso la trova lo stesso.
  In «Copia Testo pulito» può ripristinare la parola cercata; «Copia OCR
  completo» lascia il testo così come l’ha letto il motore.

Puoi anche attivare l’OCR, lasciare vuoto il testo da cercare e Avviare:
comparirà l’elenco delle immagini in cui è stato trovato del testo.

Sul risultato di un’immagine, col tasto Applicazioni:
• «Copia Testo pulito» — la parte essenziale (es. auguri + nome);
• «Copia OCR completo» — tutto ciò che è stato letto.


8. Voce e silenzio
------------------
• F7: silenzia o riattiva gli annunci del programma (Mute).
• Nell’applicazione Standalone puoi anche regolare velocità e voce.
• Nell’Add-on, velocità e voce seguono le impostazioni di NVDA;
  il Mute riguarda gli annunci di questo strumento.


9. Cosa fare con i risultati
----------------------------
Nella lista risultati:
• Invio: apre il file (o la notizia) nel punto utile, quando possibile.
• Spazio o F4: ascolta un’anteprima del contesto.
• Tasto Applicazioni: menu con Copia, Salva, Apri cartella, ecc.

Puoi filtrare la lista (Ctrl+F), esportare o stampare i risultati
dal menu File.


10. Chiudere in sicurezza
-------------------------
• Alt+F4, Ctrl+Q oppure il pulsante Chiudi: escono dal programma
  (nell’Add-on chiudono la finestra di ricerca; NVDA resta aperto).
• Esc: di regola annulla la ricerca o chiude una finestra secondaria;
  non esce da solo, così si evitano chiusure accidentali.
• Se preferisci che Esc chiuda anche il programma, c’è l’opzione
  in Strumenti.


11. Aggiornamenti
-----------------
Dal menu Strumenti puoi verificare se c’è una versione nuova (Ctrl+U),
anche mentre stai lavorando. Ti verrà proposta una finestra se c’è
qualcosa di più recente. Per applicare l’aggiornamento seguirai
le istruzioni (installer oppure, per l’Add-on, lo Store / il file .nvda-addon).


12. Dove approfondire (guida tecnica)
-------------------------------------
Questa pagina è solo l’ingresso semplice.
Per elenco comandi, dettagli e novità di versione:
• Aiuto → Guida ai Comandi (F1)
• Aiuto → Novità della Versione
• Aiuto → Pagina ufficiale GitHub
• Nell’Add-on: anche la guida HTML dal Gestore componenti aggiuntivi

Autore: Maurizio Barra (Accesso Digitale)
Progetto: Ricerca Testuale Accesso Digitale
"""


def get_guide_title() -> str:
    return GUIDE_TITLE


def get_guide_text() -> str:
    return GUIDE_TEXT
