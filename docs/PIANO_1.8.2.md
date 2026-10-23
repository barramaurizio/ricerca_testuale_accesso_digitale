# Piano RTAD 1.8.2

**Ultima pubblicata:** `1.8.1` — correzione Gemini a schermo + «Chiedi a Gemini» in Esplora file (solo Standalone installata).  
Pubblicata il 21/10/2026, lo stesso giorno della 1.8.0. Prove Maurizio OK (Standalone e Add-on).  
**Non hotfixare 1.8.1.**

**Questa versione:** due cose, nient’altro. Il feedback di papà (21/10, sera) e i tasti doppi (22/10, notte). La chat da un `.rtad.txt` già salvato resta per la versione dopo.

**Stato 22/10/2026:** pubblicata. GitHub `v1.8.2` e `app-v1.8.2`, commit `d6e7806`. DataStore accettato. Pacchetto: `ricerca_testuale_accesso_digitale-1.8.2.nvda-addon`.

## Cosa fare

Standalone prima. Add-on dopo la prova. Gemelli: `rtad_chat.py`, `rtad_ocr.py`, `rtad_media.py`.

Papà ha ancora circa 100 € di credito. Da lui Gemini non risponde da ore. Nel log di stasera (letto a voce, file non inviato) la riga `Chat Gemini fallita` è un HTTP 429 o un HTTP 503. Nel log del pomeriggio (`Log_RTAD_20261021_163413.txt`, esportato alle 16:34, finisce alle 16:33) non c’è la chat: la 1.8.0 non la scriveva. Ci sono solo due descrizioni immagine:

- 17/10 21:47 e 20/10 18:15 — `HTTP 503 (gemini-3.5-flash)`: «This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.» Stato `UNAVAILABLE`. Nessuna parola su quota, billing o credito.

Il primo modello provato è `gemini-3.5-flash`. Su 404 e 429 il programma passa al successivo. Su 503 si ferma e mostra l’errore. Per questo da lui fallisce sempre e da Maurizio no.

### 1. Dopo un 503, provare il modello successivo

Stesso comportamento già usato per 404 e 429. I tre punti, Standalone e gemello Add-on:

- `Standalone/rtad_chat.py` — `ask()`, intorno alla riga del `code in (404, 429)`
- `Standalone/rtad_ocr.py` — `_gemini_generate_description`, `e.code in (404, 429)`
- `Standalone/rtad_media.py` — stesso controllo sull’HTTP della chiamata Gemini

Ordine modelli invariato (`_GEMINI_MODELS_PREFERRED` in `rtad_ocr.py`): 3.5-flash, poi 3.8-flash, lite, flash-latest, 2.5-flash. Nessun selettore di modello in interfaccia.

Se tutti rispondono 503, allora sì il messaggio di servizio occupato.

### 2. La frase a schermo non deve parlare di credito

`_readable_error` in `rtad_chat.py` oggi traduce ogni 429, `resource_exhausted` o `quota` in «le richieste disponibili sono esaurite». Suona come se i soldi fossero finiti. Non lo sono.

- **503**, `UNAVAILABLE`, «high demand»: «Gemini non ha risposto: il servizio è occupato. Si riprova più tardi.»
- **429** senza parole di pagamento: «Gemini non ha risposto: per questa chiave c’è un limite temporaneo di richieste. Si riprova più tardi.» Non citare il credito.
- Se nel testo di Google compaiono billing, payment o credito insufficiente, quella frase si mostra com’è, così si distingue dal tetto temporaneo. Il dettaglio tecnico resta nel log, riga `Chat Gemini fallita`.

La descrizione immagine e il media usano lo stesso criterio, nel punto in cui già mostrano l’errore Gemini.

### Prova

Con una chiave che riceve 503 su `gemini-3.5-flash`: una domanda in chat e una descrizione immagine. Deve arrivare la risposta di un modello successivo, oppure, se falliscono tutti, la frase «servizio occupato», mai «richieste esaurite» e mai un accenno ai soldi. Poi lo stesso sull’Add-on.

## Tasti: una lettera, una azione

Maurizio, 22/10: Alt+G sembra servire sia alla chiave Gemini sia alla cronologia delle conversazioni. Controllo sul codice della 1.8.1 (Standalone e Add-on, stesse etichette).

Sulla finestra principale Alt+G è di tre cose insieme:

- menu **Se&gnalibri**
- pulsante **Chiave &Google…**
- pulsante **Conversazioni &Gemini…**

La chiave Gemini non è Alt+G. L’etichetta è **Chiave Ge&mini…**, quindi Alt+M, la stessa del menu **Stru&menti**. Dentro Strumenti la lettera G è di nuovo tripla: Conversazioni Gemini, Chiave Google Vision, Glossario.

**Chiedi a Gemini (Alt+G)** sul report e nel lettore resta: quella finestra non ha l’altra G. **Ctrl+Shift+G** per le conversazioni resta. Si spostano solo le lettere che si pestano.

Lettere nuove, uguali sul pulsante e nella voce di Strumenti:

- Chiave Google → **Alt+L** («Chiave Goog&le…»)
- Chiave Gemini → **Alt+H** («C&hiave Gemini…»)
- Conversazioni → **Alt+B** («Conversazioni Gemini (Alt+&B)…»)

I menu in alto non si toccano: File F, Segnalibri G, Cronologia C, Profili R, Voce V, Strumenti M.

### Altri doppioni, stessa finestra o stesso menu

Anche questi, Standalone e Add-on. Una lettera per voce. Non si riusano F, C, G, R, V, M dei menu, né i tasti già presi dal programma (Alt+P, Alt+S, Alt+T, Alt+N, Alt+K, Alt+I).

Menu **Strumenti** (l’Add-on non ha «Trova copie»):

- A: Aggiornamenti, Appunti, Tutto sull’audio/video, Salva automaticamente, Cartella salvataggio automatico, Esc chiude l’applicazione
- U: Descrivi da URL, Analizza cartella audio/video, Audio/video da URL
- D: Cattura e descrivi, Descrivi da PDF
- T: Tutto sull’immagine, Trascrivi e cerca

Menu **Aiuto:** G su Guida ai comandi, Stampa guida, Pagina GitHub.

Menu **Cronologia:** T su Richiama testo e Svuota cronologia testi.

Menu **Voce**, solo Standalone: P su Velocità più rapida e Prova voce.

Dialoghi:

- Chat Gemini: F su «Fonti» e «Apri fonte» (Alt+F deve aprire la fonte, non solo spostare il focus); P su «Domande pronte» e «Invia domanda pronta»; C su «Conversazione» e «Copia».
- Lettore documento: L su «Link» e «Apri link»; S su «Sommario» e «Salva».
- Analisi immagine: A su «Alt-text» e «Avvia»; S su «Scheda» e «sottocartelle».
- Analisi audio/video: S su «Sfoglia», «Scheda» e «sottocartelle».
- Glossario: A su «Attiva» e «Aggiungi»; S su «Sostituisci» e «Salva».

La finestra Comandi (F1) va aggiornata solo se una lettera scritta lì cambia. Alt+G «Chiedi a Gemini» e Ctrl+Shift+G restano scritti così.

Prova: dalla finestra principale, Alt+L apre solo la chiave Google, Alt+H solo la chiave Gemini, Alt+B solo le conversazioni, Alt+G solo i Segnalibri, Alt+M solo Strumenti. Poi, con Strumenti aperto, ogni lettera una voce sola. Stesso sull’Add-on.

## Cosa non entra in 1.8.2

- Chat Gemini da un `.rtad.txt` già salvato, senza rifare l’analisi. Era il piano originale: passa alla versione successiva.
- Whisper, modelli scaricati, trascrizione offline. Resta in lista, versione dedicata.
- Chat senza alcun file.
- Una conversazione su più file.
- Gemini su ogni risultato della ricerca.
- Gemini su un singolo messaggio dentro un archivio Thunderbird, o su un’intera cartella.
- VIDEO_TS, OneCore, export multipli.
- Selettore del modello Gemini nell’interfaccia.

## Come ripartire

Titolo: **«RTAD 1.8.2»**

«leggere NOTE_CONTESTO + PIANO_1.8.2; non toccare la 1.8.1 pubblicata; partire dal 503 che deve provare il modello successivo, dalla frase che non deve parlare di credito, e dai tasti doppi (Alt+G / Alt+M e gli altri elencati)»
