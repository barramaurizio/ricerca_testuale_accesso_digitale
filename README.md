# Ricerca Testuale Accesso Digitale / Text Search Accesso Digitale (v1.9.0)
**Autore / Author:** Maurizio Barra (Accesso Digitale)

---

## 🇮🇹 Italiano

Uno strumento di ricerca testuale avanzata progettato per facilitare l'accessibilità e il recupero rapido di informazioni all'interno del computer. Disponibile sia come **Componente Aggiuntivo (Add-on) per NVDA** sia come **Applicazione Standalone (.exe)**.

### 🌟 Novità della Versione 1.9.0

- **Chiedi a Gemini…** su ogni risultato che ha un file, un messaggio o un estratto: anche un messaggio dentro una casella Thunderbird, un .eml, un vecchio .doc, uno zip, un feed. In chat, a schermo e a voce: «Punto della ricerca: … Estratto: …». Gemini riceve lo stesso punto. Un messaggio della casella è una chat sua, non tutta la casella. Un allegato PDF già estratto apre la chat su quel PDF. Una riga che è solo un indirizzo dice, a schermo e a voce: «Questa riga è solo un indirizzo. Aprilo nel browser.» Senza la chiave resta: «Per conversare con Gemini serve la chiave personale, da Strumenti.»
- **Ctrl+H e Ctrl+Shift+H** ricordano fino a 200 testi e 200 percorsi. L'ultimo usato sta in cima. I venti già salvati restano: il ventunesimo si aggiunge quando cerchi o scegli un percorso nuovo.
- **Ctrl+Alt+V**, se negli Appunti non c'è un file, prende il testo di un messaggio e lo mette in elenco. A schermo e a voce: «Messaggio incollato. È in elenco: titolo. Da qui puoi fare altre operazioni.» Da lì, Chiedi a Gemini. Un file .eml copiato o trascinato resta un file, come gli altri: «Il file è in elenco: nome. Da qui puoi fare altre operazioni.» Poi chiede: «Apri ora la lettura di questo documento?» Se sì, si apre il lettore.

### 🌟 Novità della Versione 1.8.9

- **Confronta file…:** da due a dodici file, in Strumenti e nel menu del risultato. Confronta, senza chiave, mostra e dice solo le parti diverse, con il nome del file davanti. Le parti uguali non si rileggono. In cima a ogni file, solo se non coincidono in tutti: tipo, dimensione, ultima modifica e, per un audio o un video, la durata. Alt+A aggiunge, anche sull’elenco. Alt+L toglie il file sotto il cursore, anche mentre ne aggiungi altri. Canc sull’elenco fa lo stesso. Nella scelta: i più recenti in cima, riga con nome, data, tipo e dimensione, primo file già selezionato. Shift+freccia giù prende un gruppo di fila. Control+freccia salta e quelli già presi restano. Poi di nuovo Shift+freccia giù: un altro gruppo. Control+Spazio aggiunge o toglie un file solo. Alt+C cambia cartella. La finestra di Windows resta. Sotto, i file già nel confronto: Alt+L ne toglie uno prima di Invio. Senza file: «Nessun file nel confronto.» Con meno di due: «Servono almeno due file.» La stessa lista, con la scritta «Allegati», è nella scelta di Gemini. Senza allegati: «Nessun allegato presente.» Sulla conversazione, Alt+L toglie un allegato già messo. Sulla finestra principale Alt+L resta la chiave Google. Chiedi a Gemini spiega quelle differenze, non i file interi. Senza la chiave il confronto resta: «Per conversare con Gemini serve la chiave personale, da Strumenti.» Se non hai ancora confrontato: «Prima fai Confronta.» Copia e Salva testo. Salva propone Confronto.txt nella cartella del primo file. Se c’è già: Confronto (1).txt, poi Confronto (2).txt. Un nome .chat.txt diventa Confronto (1).chat.txt. Un audio, un video o un’immagine non si trascrivono in questo confronto: se non c’è testo, la riga è «Nessun testo letto.»
- **PDF firmati con DocuSign:** ogni font trova la sua tabella anche se il collegamento sta in uno stream compresso. Il sommario dice «Spett.le» e «PREMESSO». Virgolette, «sub-licenze» e «proporVi» restano a posto. «trascriv iamo» resta con lo spazio.

### 🌟 Novità della Versione 1.8.8

- **Scheda video:** un MP4 con l’indice in fondo dice durata, risoluzione e «Video normale», anche se il nome ha un’emoji o le virgolette curve. Un resoconto già salvato non si ricalcola: per vederla, rifai l’analisi.
- **Glossario nel lettore:** con il glossario acceso, «Leggi documento» su un `.rtad.txt` corregge il file e poi lo legge, a schermo e a voce. «Copia testo del documento» fa la stessa correzione. Cambia la parola intera.
- **Pagine HTML:** «Leggi documento», copia e ricerca tolgono tag, script e style. Titoli, paragrafi e voci di elenco restano righe. Ogni codice come `&#232;` diventa una lettera. Non è un browser.
- **Indirizzo Internet:** nel campo percorso la pagina si scarica. A schermo e a voce: «Scarico la pagina: nome. Attendere.», poi «L'indirizzo è in elenco: nome. Da qui puoi fare altre operazioni.» Il menu è quello del file, più «Apri pagina nel browser». Il lettore non si apre da solo: si apre da «Leggi documento». Da Sfoglia, se la pagina arriva come file, restano le stesse voci di un documento e la domanda di aprirlo nel lettore. YouTube e il filtro Solo Audio e Video aprono ancora l’hub. Un audio o un video già scaricato resta in elenco: «Il file è in elenco: nome. Da qui puoi fare altre operazioni.»
- **Sfoglia, singolo file:** anche nell’Add-on il file resta in elenco, con le stesse voci del menu.

### 🌟 Novità della Versione 1.8.7

- **Lettere al posto dei codici:** nei libri EPUB, i codici come `&#232;` diventano lettere e segni, nel lettore e nel testo copiato.
- **Da Esplora file:** il file o la cartella restano in elenco, anche se il programma era chiuso. A schermo e a voce: «Il file è in elenco: nome. Da qui puoi fare altre operazioni.»
- **Apri con:** dopo l’installazione della Standalone, Apri con può proporre Ricerca Testuale. Se lo scegli, si apre solo questo programma: il file va in elenco e un documento si apre nel lettore. Il doppio clic resta al programma di sempre. «Solo una volta» vale per quel file. «Sempre» lo associa a quell’estensione. Si cambia da Proprietà del file oppure da Impostazioni, App, App predefinite. Su un audio o un video analizza, non lo riproduce.
- **Punti di lettura:** nel lettore, Control+B ne aggiunge uno, quanti ne vuoi. Il precedente resta. Alla riapertura si torna sull’ultimo. Se sono più di uno: «Segnalibro di lettura 2 di 3: ripreso da qui.» Nell’elenco, frecce e Invio scelgono. Vale per Leggi documento, anche un txt o un .rtad.txt. Non è il Segnalibro Ctrl+D.
- **Copia testo del documento:** copia il sommario, i link e poi i capitoli.
- **Cifre nel PDF:** se l’ultima cifra di un anno è disegnata a parte, 202 7 torna 2027. Lo stesso per un importo come 2,8.

### 🌟 Novità della Versione 1.8.6

- **Whisper sul mio PC:** nell’analisi audio/video, insieme a «Trascrizione parlato», la casella «Sul mio PC (Whisper)» è spenta. Se la accendi, al primo uso scarica il modello e trascrive anche senza chiave Gemini. Un file fino a 20 minuti. In una cartella, fino a 5 file: «Whisper: 5 file su N. Non entrati: …».
- Il testo diventa `nome.rtad.txt` se accanto non c’era già. Se c’era, resta com’era. Da lì valgono Chiedi a Gemini e Traduci.
- Un secondo avvio mentre lavora interrompe, a voce e a schermo: «Interruzione richiesta. Attendi la chiusura.»
- Standalone e Add-on insieme. Gemini resta la trascrizione quando la casella è spenta. `lastTestedNVDAVersion` = 2026.3.0.

### 🌟 Novità della Versione 1.8.5

- **Traduci** il testo già aperto: trascrizione di un video, resoconto `.rtad.txt`, testo di un documento nel lettore. Pulsante Traduci (Alt+U). L’originale resta e la traduzione si aggiunge sotto. Nel video restano i timestamp.
- La lingua di arrivo si sceglie. L’italiano è già selezionato. Gemini riconosce la lingua di partenza. Si usa la chiave Gemini già presente.
- Un testo lungo va a pezzi fino alla fine, a schermo e a voce. Alla fine: «Traduzione completa.» Non parte da sola. Nell’analisi audio/video la casella «Traduci la trascrizione» è spenta.
- Standalone e Add-on insieme. Per un testo lungo si usa Traduci, non una domanda «traduci tutto» in chat.
- **Salva testo:** dal video propone lo stesso `nome.rtad.txt`. Se si sovrascrive, l’originale resta e sotto c’è la traduzione. Dal resoconto già salvato propone `nome.rtad.rtad.txt`: il primo file resta com’era. Il nome si può cambiare, anche con un (1).

### 🌟 Novità della Versione 1.8.4

- **Dal resoconto già salvato:** su un `.rtad.txt`, Chiedi a Gemini usa quel testo e non rifà l’analisi. Se la foto, il video o il documento con lo stesso nome è ancora accanto, quello resta il file di partenza. Se non c’è più, la chat resta sul testo salvato e lo dice, a voce e a schermo.
- **Elenchi vuoti:** una riga vera, a schermo e in voce. Prima di cercare: «Nessuna ricerca avviata.» Filtro senza esiti: «Nessun risultato con questo filtro.» Fonti ancora senza link: «Ancora nessuna fonte.» Glossario senza regole: «Nessuna correzione nel glossario.»
- **Add-on:** NVDA dice anche il percorso impostato, il testo salvato e i risultati esportati. Prima la frase spariva alla chiusura della finestra.
- Poi valgono Alt+A, il tetto di 12 e Shift+Invio. Standalone e Add-on insieme. In Esplora file (solo il programma Windows) la voce c’è anche sul `.rtad.txt`.

### 🌟 Novità della Versione 1.8.3

- **Conversazione senza file:** Alt+Q, oppure Strumenti → Nuova conversazione Gemini. Non serve aprire prima una foto o un documento.
- **Allegati in chat:** Alt+A apre l’elenco della cartella, i più recenti in cima (nome, data, tipo, dimensione; su un video, fermandosi, la durata). Fino a 12: immagini, documenti, audio e video. Le e-mail .eml no. Shift+freccia giù e Control+Spazio per scegliere. La finestra di Windows resta per le cartelle piccole. Vale anche sulla chat nata da un file: quello di partenza resta.
- **Shift+Invio** nella domanda va a capo e non invia. Invio da solo invia.
- **Crediti finiti:** HTTP 402 in italiano. I crediti prepagati di quella chiave sono finiti e si ricaricano in Google AI Studio. Non si prova un altro modello. Vale per chat, descrizione immagine e audio/video.
- Standalone e Add-on insieme. Le cronologie restano separate.

### 🌟 Novità della Versione 1.8.2

- **Modello successivo:** se Gemini risponde «servizio occupato» (HTTP 503) sul primo modello, RTAD prova i modelli dopo, come già faceva per 404 e 429. Chat, descrizione immagine e audio/video.
- **Frase chiara:** un tetto temporaneo di richieste non viene più scritto come credito finito. Il servizio occupato ha una frase sua. Se Google parla di pagamento, si mostra la frase di Google. Il dettaglio tecnico resta nel log.
- **Una lettera, una azione:** sulla finestra principale Alt+L è la chiave Google, Alt+H la chiave Gemini, Alt+B le conversazioni. Alt+G resta i Segnalibri. Alt+M resta Strumenti. «Chiedi a Gemini» sul report resta Alt+G. Ctrl+Shift+G resta. Stessi tasti sull’Add-on. Sistemate anche le lettere doppie dentro gli stessi menu e dialoghi.
- Le cronologie di Standalone e Add-on restano separate.

### 🌟 Novità della Versione 1.8.1

- **Gemini a schermo:** se non arriva un testo, la domanda e il motivo restano scritti nel riquadro Conversazione, anche senza voce. La stessa frase finisce nel log.
- **Esplora file** (Standalone installata): dentro «Cerca con Accesso Digitale» c’è «Chiedi a Gemini» sul file scelto. La domanda la scrivi tu. L’Add-on non aggiunge voci in Esplora file.
- Resta la conversazione sul file della 1.8.0.

### 🌟 Novità della Versione 1.8.0

- **Conversazione con Gemini** sul file già aperto: immagine, documento (PDF, Word, EPUB…) e audio/video sul report già prodotto. Più domande, data di oggi, cronologia sul PC. Copia, Salva, Stampa.
- **Dove:** pulsante «Conversazioni Gemini» e Strumenti (**Ctrl+Shift+G**); «Chiedi a Gemini» (**Alt+G**) sul report e nel lettore; dal menu di un risultato, Chiedi oppure Riprendi. Stesso sull’Add-on. Le cronologie di Standalone e Add-on restano separate.
- **Web** acceso di default: risposte divise in «Nel file» e «Approfondimento». Per aprire un link: Tab fino a **Apri fonte**, poi Invio. **Alt+F** fa lo stesso, anche se il focus è sull’elenco. Invio sull’elenco non apre il browser.
- La domanda va a capo mentre si scrive; Invio invia. Da un URL la chat resta col **titolo del video**, non col nome temporaneo; Salva propone l’ultima cartella usata.
- Resta l’OCR tabelle riga-per-riga della 1.7.7. Chiave Gemini personale (AI Studio); il programma non addebita nulla.

### 🌟 Novità della Versione 1.7.7

- **OCR tabelle / colonne**: «Leggi testo nell'immagine» e la sezione OCR di «Tutto sull'immagine» ricostruiscono l'ordine **riga per riga** quando il motore espone le posizioni delle parole (tipico: programmazione TV, griglie). Non inventa testo: solo riordina.
- **Add-on**: voce «Leggi testo nell'immagine (OCR)» in Strumenti e nel menù risultati; casella Testo OCR anche in «Tutto sull'immagine» (dopo Incolla → Sì), come nello Standalone.
- Cache OCR aggiornata (v20) così non resta un risultato «a colonne» in cache; riordino anche con motore Google Vision.
- Restano drop/updater/CD/report 1.7.6 e OCR «una lettera per riga» 1.7.5.

### 🌟 Novità della Versione 1.7.6

*(Pubblicata.)*

- **Drag & drop SA**: rilascio file/cartella in qualunque punto della finestra (offerta «Apri ora» quando ha senso). Restano Incolla (Ctrl+Alt+V) e menù Esplora.
- **Updater SA**: download in `%LocalAppData%\RTAD_Standalone\updates\` (non più in Download); pulizia automatica. Trova copie non propone quella cartella come «sicura».
- **CD/DVD**: unità ottiche in «Tutto il PC»; messaggio chiaro sui `.cda`. Per analizzare un CD audio: estrarre con Windows Media Player in mp3/wma, poi aprire in RTAD.
- **Report a righe standard**: descrizioni/OCR/documenti senza riga unica orizzontale (più comodi da leggere e incollare in Word).
- Marker Installer più esplicito; guida aggiornata. Restano OCR/copie/Incolla 1.7.5.

### 🌟 Novità della Versione 1.7.5

*(Pubblicata.)*

- **OCR orizzontale**: se il motore metteva una lettera per riga, il testo viene ricomposto prima di lettura/copia («Leggi testo nell'immagine»).
- **Trova altre copie sul PC** (SA, Strumenti): elenco Installer/exe/scorciatoie, rapporto sul Desktop, rimozione solo Setup/Portable in Download/Desktop con consenso; avviso amichevole all’avvio se serve.
- **Incolla percorso dagli Appunti** (SA + Add-on): Ctrl+C su un file in Esplora → Incolla… / Ctrl+Alt+V / Strumenti; offerta «Apri ora» come Sfoglia. Solo SA: trascinamento sulla finestra.
- **Guida HTML**: ricerca parole in audio/video tramite `.rtad.txt`; sezione copie; Incolla.
- Restano updater/shell/Sfoglia/guida 1.7.4, sidecar/xlsx/Trascrivi 1.7.3.

### 🌟 Novità della Versione 1.7.4

*(Pubblicata.)*

- **Aggiornamenti Standalone**: Installer → solo Setup; Portable → solo Portable (release `app-v…`).
- **Menù Esplora file (SA)**: «Apri / analizza» apre davvero quel file; se RTAD è già aperto, niente seconda finestra.
- **Sfoglia → Singolo file**: qualsiasi tipo; può aprire subito l’analisi (immagine / audio-video / documento).
- **Guida HTML completa** (Aiuto): indice, cercabile con Ctrl+F, passi per chiavi Google Vision e Gemini.
- Restano sidecar/xlsx/Trascrivi e cerca 1.7.3, batch/B0/glossario 1.7.2, PDF scansione 1.7.1.

### 🌟 Novità della Versione 1.7.3

*(Pubblicata.)*

- **Sidecar `.rtad.txt`**: su media **locale**, «Salva testo…» usa lo **stem del file** sul disco; da URL/temp resta titolo/ID del download.
- **Solo Audio/Video**: trova anche i `.rtad.txt` **orfani** (senza media gemello) con snippet e timestamp `[MM:SS]`.
- **Excel `.xlsx`**: ricerca nel contenuto delle celle; **Invio** apre Excel alla riga del risultato; date e ore seriali rese leggibili.
- **Trascrivi e cerca…** (Strumenti / **Ctrl+Shift+T**): cerca parole nel parlato usando i `.rtad.txt` già presenti; altrimenti trascrive con Gemini (max 30 file).
- Restano batch/B0/glossario 1.7.2, PDF scansione 1.7.1, lettore/spazi/toast 1.7.0, TOC PDF 1.6.9, hub media 1.6.7.

### 🌟 Novità della Versione 1.7.2

*(Pubblicata.)*

- **Analizza cartella audio/video…**: batch su media locali → file `.rtad.txt` accanto a ciascuno (scheda/riassunto di default; trascrizione e timestamp a richiesta).
- **Ricerca [AV]**: con filtro «Solo Audio e Video», cerca anche nei `.rtad.txt` già salvati; snippet e timestamp `[MM:SS]` se presenti (zero costi extra dopo l’analisi).
- **Glossario trascrizioni** (Strumenti): correzioni dopo Gemini; confronto senza accenti; può aggiornare il `.rtad.txt` all’apertura del report.
- Restano PDF scansione 1.7.1, lettore/spazi/toast 1.7.0, TOC PDF 1.6.9, documenti 1.6.8, hub media 1.6.7.

### 🌟 Novità della Versione 1.7.1

*(Pubblicata.)*

- **PDF scansione**: se «Leggi documento…» non trova testo ma trova immagini → dialogo **Descrivi immagine** / **Apri lettore**.
- **Descrivi immagine da PDF**: «Salva testo…» con **nome e cartella del PDF originale**; nuovo **«Stampa testo…»** (stampante Windows / Print to PDF).
- **Scheda tecnica** (immagini e audio/video): **Data analisi** + **Ultima modifica originale** (come in Esplora file).
- **Lettore**: focus frecce dopo iconizza migliorato.
- Restano lettore/spazi/toast 1.7.0, TOC PDF 1.6.9, documenti 1.6.8, hub media 1.6.7.

### 🌟 Novità della Versione 1.7.0

*(Pubblicata.)*

- **Lettore documento RTAD**: «Leggi documento…» diventa un lettore accessibile (sommario, link, testo). **Ctrl+F** / F3 / Shift+F3 cerca nel corpo; **Ctrl+H** / **Ctrl+Shift+H** salta i titoli `[Hn]`; «Apri file esterno» è opzionale. Se dopo iconizza le frecce non rispondono: Tab poi Shift+Tab.
- **Spazi PDF**: riconoscimento dei placeholder spazio tipici (es. Acer, manuali braille) → testo più leggibile. I PDF criptati restano fuori portata (Acrobat sì, RTAD no senza copia sbloccata).
- **Toast fine-ricerca** meno invasivi (banner breve; restano nel Centro notifiche). Con il lettore aperto: solo annuncio.
- Restano PDF TOC/link 1.6.9, documenti 1.6.8, hub audio/video 1.6.7, dialogo immagine 1.6.6.

### 🌟 Novità della Versione 1.6.9

*(Pubblicata.)*

- **PDF strutturati**: sommario/TOC e link URI in «Leggi documento (struttura e testo)» (insieme a DOCX/EPUB). Con Invio: testo accessibile in RTAD (anche se Acrobat riparte dall’inizio) + app predefinita Windows alla pagina (salto se Acrobat/Sumatra). Guida pratica: escamotage Acrobat/NVDA.
- **Report media**: titoli lunghi quasi interi nel nome `.rtad.txt` (stem fino a ~220 caratteri; non più tagliati a ~80).
- **Ricerca parole nei video**: dopo «Salva testo…», cerca nei `.rtad.txt` come file di testo (stesso contenuto della trascrizione/descrizione, zero costi extra).
- Restano documenti strutturati 1.6.8, hub audio/video 1.6.7, dialogo immagine 1.6.6.

### 🌟 Novità della Versione 1.6.8

*(Pubblicata.)*

- **Documenti strutturati**: DOCX (titoli + link) ed EPUB (sommario/capitoli); PDF con testo piano e messaggio onesto se il TOC non è ancora disponibile.
- Menu **«Leggi documento (struttura e testo)»** (Standalone e Add-on): sommario, link (Invio / Apri link), testo con marcatori `[H1]`…
- **Report media**: ricorda l’ultima cartella; nome da titolo/ID URL o dal file locale; default nella cartella del media.
- **Salvataggio automatico risultati** a fine ricerca (Strumenti + scelta cartella); stesso ordine della lista.
- **Sfoglia**: cartella/unità oppure singolo file (PDF/DOCX/…).
- Restano hub audio/video 1.6.7 e dialogo immagine 1.6.6.

### 🌟 Novità della Versione 1.6.7

*(Pubblicata.)*

- **Tutto sull'audio/video**: scheda (Short/verticale), riassunto, trascrizione e timestamp progressivi opt-in (Gemini).
- **Hub audio/video**: il filtro «Solo Audio e Video» apre URL, file e sezioni; stesso dialogo da Strumenti.
- **Audio/video da URL** (`Ctrl+Shift+M`): link diretti o YouTube/Vimeo con yt-dlp; verifica/aggiorna yt-dlp in-app; scheda con Titolo/ID/URL sorgente; evita video muti (ffmpeg consigliato); File API Gemini oltre 20 MB (tetti Google ~2 GB / ~3 h); trascrizioni lunghe con ripresa; **Salva testo…** nel report; avanzamento (barra + stato Alt+S) come in ricerca.
- **Limiti** = tetti Google File API; niente trascrizione di massa su tutto il PC.
- **Explorer Standalone** + menu contestuale / Strumenti (gemello Add-on) sui file media.
- Restano dialogo immagine, batch cartella e PDF multi-font (1.6.6).

### 🌟 Novità della Versione 1.6.6

*(Pubblicata.)*

- **Tutto sull'immagine**: dialogo unico con alt-text, descrizione, etichette e scheda tecnica.
- **Batch cartella**: analizza tutte le immagini e può salvare `.rtad.txt` accanto a ciascuna.
- **PDF multi-font**: ToUnicode per font (niente testo spazzatura su PDF multilingue).
- **Gemini API**: rimosso `temperature` da `generationConfig` (modelli nuovi Google AI Studio).
- Restano fix web SVG/WebP e sottomenù Explorer PDF/documenti (1.6.5).

### 🌟 Novità della Versione 1.6.5

*(Pubblicata.)*

- **Fix icone/grafici web** (es. 3BMeteo): niente dialogo wx «formato immagine sconosciuto» su SVG/WebP; fallback cattura area (`NVDA+Shift+G`).
- **Standalone Explorer**: sottomenù **PDF** / **documenti** (Apri con app predefinita + voce in lista, Leggi testo, Copia testo; sui PDF anche Descrivi immagini).
- Restano descrivi URL/Appunti/cattura, Shift+G, alt-text, `[ELENCO]`, sottomenù immagini.

### 🌟 Novità della Versione 1.6.4

*(Pubblicata.)*

- **Descrivi da URL / Appunti / cattura schermo** (gemello SA + Add-on); scorciatoie SA a finestra attiva.
- **Add-on NVDA**: `NVDA+Shift+G` su figura web o file immagine in Esplora file/Desktop.
- **Alt-text** breve e Alt-text + descrizione; **Descrivi immagine da PDF**.
- **Elenco per tipo** senza parola chiave (documenti/immagini/media): risultati `[ELENCO]`.
- Fix: `NVDA+Shift+G` non riusa più un file selezionato in Explorer in secondo piano.
- Restano Gemini/Vision/Explorer 1.6.3, notifica 1.6.2, ZIP 1.6.1.

### 🌟 Novità della Versione 1.6.3

*(Pubblicata.)*

- **Descrivi immagine (Gemini)**: descrizione immersiva (layout, testi, contesto); chiave personale Google AI Studio.
- **Scheda tecnica** + etichette Vision; ricerca contenuto visivo opt-in `[IMG-VIS]`.
- **Standalone**: sottomenù Explorer sulle immagini (Descrivi, OCR, Etichette, Scheda, Copia).
- Restano notifica fine ricerca / cache OCR 1.6.2, ZIP 1.6.1, OCR Vision 1.6.0.

### 🌟 Novità della Versione 1.6.2

*(Pubblicata.)*

- **Notifica a fine ricerca**: resta nel Centro notifiche Windows (Windows+N) finché non la apri (Strumenti, attiva di default); restano bip e annuncio vocale.
- **Svuota cache OCR** dal menu Strumenti.
- **Google Vision**: ritentativi anche su fasce basse/margini (byline) e unione pezzi OCR; cache OCR v17.
- Restano ZIP / arrivi ultimo minuto 1.6.1, OCR Vision 1.6.0, guida/EPUB 1.5.9.

### 🌟 Novità della Versione 1.6.1

*(Pubblicata.)*

- **Arrivi dell’ultimo minuto**, **ZIP opt-in**, lista stabile durante la ricerca; reset voce SAPI se Id non valido.
- Restano OCR Vision 1.6.0, guida/EPUB 1.5.9, OCR locale 1.5.8.

### 🌟 Novità della Versione 1.6.0

*(Pubblicata.)*

- **OCR Google Cloud Vision** (opt-in): chiave API **personale** di ciascun utente (Strumenti / pulsante Chiave Google); gemello Standalone + Add-on.
- Correzione lista: a fine ricerca con 0 risultati non resta più «Ricerca in corso…».
- Restano guida pratica + EPUB 1.5.9, OCR locale 1.5.8, voce 1.5.7, posta 1.5.6.

### 🌟 Novità della Versione 1.5.9

*(Pubblicata.)*

- **Guida pratica** (menu Aiuto): linguaggio semplice; a ogni release le novità sono aggiornate lì, in parallelo alla guida tecnica.
- Ricerca nei libri **EPUB** (`.epub`), risultati `[EPUB]`; nel filtro Documenti.
- Restano OCR 1.5.8, voce 1.5.7, posta 1.5.6, date, profili.

### 🌟 Novità della Versione 1.5.8

*(Pubblicata.)*

- **OCR opt-in:** testo in immagini e PDF scansionati; risultati `[IMG-OCR]` / `[PDF-OCR]`; cache e profili.
- Motori: **Windows.Media.Ocr** (predefinito) oppure **EasyOCR** opzionale (Standalone consigliata per EasyOCR).
- Preprocess + match fuzzy; sinonimi birthday↔compleanno; **Copia Testo pulito** / **Copia OCR completo**.
- OCR senza parola chiave (OCR attivo + testo vuoto → Avvia). Restano voce 1.5.7, posta 1.5.6, date, profili.

### 🌟 Novità della Versione 1.5.7

- **Voce Standalone:** velocità SAPI (Ctrl++ / Ctrl+-), tono, scelta voce (anche OneCore), menu Voce, salvataggio.
- Annunci RTAD con SAPI regolabile (oppure NVDA). **F7** Mute persistente.
- **Add-on gemello:** Mute annunci RTAD (F7); velocità/voce = impostazioni NVDA.
- Restano posta completa 1.5.6, date, profili e filtri.

### 🌟 Novità della Versione 1.5.6

- **Posta completa:** caselle Thunderbird/MBOX senza tetto di dimensione (streaming); anche messaggi con allegati PDF grandi.
- Filtro **`.pdf`**: include caselle posta/.eml e cerca negli allegati; **Apri/Salva allegato PDF** (non l’INBOX intera).
- Meno rumore: esclusi WinSxS, cache Cursor e log RTAD; stato con messaggi posta e hit allegati.
- Tetto ~40 MB per DOC/testi; **PDF ~80 MB**. Restano stabilità 1.5.5, feedparser, date e profili.

### 🌟 Novità della Versione 1.5.5

- **Stabilità / anti-blocco:** niente «Non risponde» su cartelle grandi e PDF/DOC difficili (es. G:\), **senza ridurre** le ricerche normali.
- Tetto decompressione PDF; timeout soft solo sui file che si bloccano; `.doc` OLE senza ZipFile inutile.
- **Data (gg/mm/aaaa) su tutti i risultati:** txt, Word, media, immagini, nome file… come già per email e PDF.
- File molto grandi (> ~40 MB): ricerca sul **nome**; Alt+S/avanzamento più leggeri; indicizzazione cartelle visibile.
- Add-on: **feedparser incluso** (RSS/Atom in NVDA); **`.eml`/MBOX** come nello Standalone (un risultato per messaggio).
- Restano i **profili** e i filtri della 1.5.4.

### 🌟 Novità della Versione 1.5.4

- **Profili di ricerca:** salva percorso, tipo file, opzioni e (opzionale) testo; menu Profili; Ctrl+Shift+P / Ctrl+Shift+L.
- Gestisci profili: rinomina o elimina.
- **Filtri tipologici più ricchi:** più estensioni in Immagini, Audio/Video e Documenti (es. m4a, flac, webp, html, md…).
- **Scorciatoie Alt senza conflitti:** una sola azione per lettera (T/P/N/I/S/K); Avvia con INVIO nel campo testo.
- Restano le novità 1.5.3 (PDF testo/immagini, Copia/Salva Immagine).

### 🌟 What's New in Version 1.9.0

- **Ask Gemini…** on every result that has a file, a message or an excerpt: a message inside a Thunderbird mailbox, an .eml, an old .doc, a zip, a feed. In the chat, on screen and by voice: «Punto della ricerca: … Estratto: …». Gemini receives that same point. A mailbox message is its own chat, not the whole mailbox. An extracted PDF attachment opens the chat on that PDF. A row that is only an address says, on screen and by voice: «Questa riga è solo un indirizzo. Aprilo nel browser.» Without the key, the sentence stays: «Per conversare con Gemini serve la chiave personale, da Strumenti.»
- **Ctrl+H and Ctrl+Shift+H** remember up to 200 search texts and 200 paths. The latest is at the top. The twenty already stored stay: the twenty-first is added when you search or choose a new path.
- **Ctrl+Alt+V**, when the clipboard has no file, takes the text of a message and puts it in the list. On screen and by voice: «Messaggio incollato. È in elenco: titolo. Da qui puoi fare altre operazioni.» From there, Ask Gemini. A copied or dropped .eml stays a file, like the others: «Il file è in elenco: nome. Da qui puoi fare altre operazioni.» Then it asks: «Apri ora la lettura di questo documento?» If you answer yes, the reader opens.

### 🌟 What's New in Version 1.8.9

- **Compare files…:** from two to twelve files, in Tools and in the result menu. Compare, without a key, shows and speaks only the parts that differ, with the file name in front. Shared parts are not read again. At the top of each file, only when they are not the same in every file: type, size, last modified and, for an audio or a video, the duration. Alt+A adds, even from the list. Alt+L removes the file under the cursor, also while you are still adding. Delete on the list does the same. In the chooser: newest first, a row with name, date, type and size, the first file already selected. Shift+Down takes a contiguous group. Control+arrow moves and keeps what is already selected. Shift+Down again takes another group. Control+Space toggles one file. Alt+C changes folder. The Windows dialog stays. Below, the files already in the comparison: Alt+L removes one before Enter. With no file: «Nessun file nel confronto.» With fewer than two: «Servono almeno due file.» The same list, titled «Allegati», is in Gemini’s chooser. With no attachment: «Nessun allegato presente.» In the conversation, Alt+L still removes an attachment already added. On the main window Alt+L remains the Google key. Ask Gemini explains those differences, not the whole files. Without the key the comparison stays: «Per conversare con Gemini serve la chiave personale, da Strumenti.» If you have not compared yet: «Prima fai Confronta.» Copy and Save text. Save proposes Confronto.txt in the first file’s folder. If it exists: Confronto (1).txt, then Confronto (2).txt. A .chat.txt name becomes Confronto (1).chat.txt. An audio, a video or an image is not transcribed in this comparison: if there is no text, the line is «Nessun testo letto.»
- **DocuSign-signed PDFs:** each font finds its table even when the link sits in a compressed stream. The outline reads «Spett.le» and «PREMESSO». Quotes, «sub-licenze» and «proporVi» stay intact. «trascriv iamo» keeps its space.

### 🌟 What's New in Version 1.8.8

- **Video details:** an MP4 whose index is at the end reports duration, resolution and “Video normale”, even when the file name has an emoji or curly quotes. A report already saved is not recalculated: run the analysis again to see the new details.
- **Glossary in the reader:** with the glossary on, “Leggi documento” on a `.rtad.txt` corrects the file and then reads it, on screen and by voice. “Copia testo del documento” does the same correction. A whole word changes.
- **HTML pages:** Read document, copy and search drop tags, scripts and styles. Headings, paragraphs and list items stay on their own lines. A code such as `&#232;` becomes a letter. It is not a browser.
- **Internet address:** in the path field the page is downloaded. On screen and by voice: «Scarico la pagina: nome. Attendere.», then «L'indirizzo è in elenco: nome. Da qui puoi fare altre operazioni.» The menu is that of the file, plus «Apri pagina nel browser». The reader does not open by itself: open it from «Leggi documento». From Browse, when the page arrives as a file, the menu matches a document and the usual question offers the reader. YouTube and the Audio and Video only filter still open the hub. A downloaded audio or video stays in the list: «Il file è in elenco: nome. Da qui puoi fare altre operazioni.»
- **Browse, single file:** in the add-on too, the file stays in the list, with the same menu items.

### 🌟 What's New in Version 1.8.7

- **Letters instead of codes:** in EPUB books, codes such as `&#232;` become letters and signs, in the reader and in copied text.
- **From File Explorer:** the file or folder stays in the list, even when the program was closed. On screen and by voice.
- **Open with:** after installing the Standalone, Open with can offer Ricerca Testuale. Choosing it opens only this program: the file goes into the list and a document opens in the reader. A double-click stays with the usual program. “Just once” is for that file. “Always” associates that extension. Change it from the file Properties, or from Settings, Apps, Default apps. On audio or video it analyses, it does not play.
- **Reading places:** in the reader, Control+B adds one, as many as you want. The previous ones stay. Reopening returns to the last one. If there are several: “Segnalibro di lettura 2 di 3: ripreso da qui.” The list chooses another with the arrows and Enter. It applies to Read document, including a txt or a .rtad.txt. It is not the Ctrl+D bookmark.
- **Copy document text:** copies the outline, the links, then the chapters.
- **Digits in a PDF:** when the last digit of a year is drawn separately, 202 7 becomes 2027. The same applies to an amount such as 2,8.

### 🌟 What's New in Version 1.8.6

- **Whisper on this PC:** in audio/video analysis, next to “Trascrizione parlato”, the box “Sul mio PC (Whisper)” is off. Turn it on and, the first time, the model is downloaded and the file is transcribed without a Gemini key. One file up to 20 minutes. In a folder, up to 5 files: “Whisper: 5 file su N. Non entrati: …”.
- The text becomes `name.rtad.txt` when that file is not already beside the media. If it is, it stays as it was. Ask Gemini and Translate already work from there.
- Starting again while it is working stops it, on screen and by voice: “Interruzione richiesta. Attendi la chiusura.”
- Standalone and add-on together. Gemini stays the transcription when the box is off. Last tested NVDA version: 2026.3.

### 🌟 What's New in Version 1.8.5

- **Translate** the text already open: a video transcript, a `.rtad.txt` report, or a document in the reader. Translate button (Alt+U). The original stays and the translation is added below. In a video the timestamps stay.
- You choose the target language. Italian is already selected. Gemini recognises the source language. The Gemini key you already have is used.
- A long text is done in pieces, through to the end, on screen and by voice. At the end: “Traduzione completa.” It does not start by itself. In audio/video analysis the “Traduci la trascrizione” box is off.
- Standalone and add-on together. For a long text, use Translate, not a “translate everything” question in the chat.
- **Save text:** from the video it proposes the same `name.rtad.txt`. Overwriting keeps the original and adds the translation below. From an already saved report it proposes `name.rtad.rtad.txt`, so the first file stays as it was. The name can be changed, including with a (1).

### 🌟 What's New in Version 1.8.4

- **From a saved report:** on a `.rtad.txt`, Ask Gemini uses that text and does not run the analysis again. If the photo, video or document with the same name is still beside it, that file stays the starting file. If it is gone, the chat stays on the saved text and says so, on screen and by voice.
- **Empty lists:** a real row, on screen and by voice. Before a search, when a filter has no hits, when there is no source yet, and when the glossary has no rules.
- **Add-on:** NVDA also speaks the path just set, the text just saved, and the exported results. Those sentences used to vanish when the window closed.
- Alt+A, the limit of 12 and Shift+Enter still apply. Standalone and add-on together. In File Explorer (Windows program only) the command is also on the `.rtad.txt`.

### 🌟 What's New in Version 1.8.3

- **Conversation with no file:** Alt+Q, or Tools → New Gemini conversation. No photo or document has to be open first.
- **Attachments in chat:** Alt+A opens the folder list, newest first (name, date, type, size; on a video, the duration when you stop on it). Up to 12: images, documents, audio and video. .eml mail files are not included. Shift+Down and Ctrl+Space to select. The Windows dialog remains for small folders. This also works when the chat started from a file: that file stays.
- **Shift+Enter** in the question inserts a new line and does not send. Enter alone sends.
- **Credits used up:** HTTP 402 in Italian. That key’s prepaid credits are finished and are topped up in Google AI Studio. Another model is not tried. Chat, image description, and audio/video.
- Standalone and add-on together. Histories stay separate.

### 🌟 What's New in Version 1.8.2

- **Next model:** if Gemini says the service is busy (HTTP 503) on the first model, RTAD tries the following models, as it already did for 404 and 429. Chat, image description, and audio/video.
- **Clear sentence:** a temporary request limit is no longer worded as if the credit were gone. A busy service has its own sentence. If Google mentions payment, Google’s sentence is shown. The technical detail stays in the log.
- **One letter, one action:** on the main window Alt+L is the Google key, Alt+H the Gemini key, Alt+B the conversations. Alt+G remains Bookmarks. Alt+M remains Tools. “Ask Gemini” on a report remains Alt+G. Ctrl+Shift+G remains. Same keys in the add-on. Duplicate letters inside the same menu or dialog are fixed too.
- Standalone and add-on histories stay separate.

### 🌟 What's New in Version 1.8.1

- **Gemini on screen:** if no text comes back, the question and the reason stay written in the Conversation box, even with speech off. The same sentence is written to the log.
- **File Explorer** (installed Standalone): inside “Search with Accesso Digitale” there is “Ask Gemini” on the selected file. You still type the question. The add-on does not add Explorer items.
- The 1.8.0 conversation on an open file remains.

### 🌟 What's New in Version 1.8.0

- **Gemini conversation** on a file already open: image, document (PDF, Word, EPUB…) and audio/video using the report already on screen. Follow-up questions, today’s date, history on this PC. Copy, Save, Print.
- **Where:** “Gemini conversations” button and Tools (**Ctrl+Shift+G**); “Ask Gemini” (**Alt+G**) on a report or in the document reader; from a result’s menu, Ask or Resume. Same in the add-on. Standalone and add-on keep separate histories.
- **Web** on by default: answers split into “In the file” and “Further reading”. To open a link: Tab to **Open source**, then Enter. **Alt+F** does the same even when focus is on the list. Enter on the list does not open the browser.
- The question wraps while you type; Enter sends. From a URL the chat keeps the **video title**, not the temporary file name; Save offers the last folder you used.
- Table OCR from 1.7.7 remains. Personal Gemini key (AI Studio); the program does not bill you.

### 🌟 What's New in Version 1.7.7

- **OCR tables / columns**: “Read text in image” and the OCR section of “Everything about the image” rebuild **row-by-row** reading order when the engine provides word positions (e.g. TV program grids). No invented words—reorder only.
- **Add-on**: “Read text in image (OCR)” under Tools and in the results menu; OCR checkbox also in “Everything about the image” (after Paste → Yes), matching Standalone.
- OCR cache bumped (v20) so an old column-order result is not kept; same reorder with Google Vision engine.
- Drop/updater/CD/report 1.7.6 and one-letter-per-line OCR 1.7.5 remain.

### 🌟 What's New in Version 1.7.6

*(Published.)*

- **SA drag & drop**: drop a file/folder anywhere on the window (optional “Open now”). Paste (Ctrl+Alt+V) and Explorer menu remain.
- **SA updater**: downloads to `%LocalAppData%\RTAD_Standalone\updates\` (not Downloads); auto-cleanup. Find copies ignores that folder as “safe to delete”.
- **CD/DVD**: optical drives in “Whole PC”; clear message for `.cda`. For audio CDs: rip with Windows Media Player to mp3/wma, then analyze in RTAD.
- **Wrapped reports**: descriptions/OCR/documents use normal line lengths (easier to read and paste into Word).
- Clearer Installer channel marker; guide updated. OCR/copies/Paste from 1.7.5 remain.

### 🌟 What's New in Version 1.7.5

*(Published.)*

- **Horizontal OCR**: if the engine returned one letter per line, text is reflowed before reading/copy (“Read text in image”).
- **Find other copies on this PC** (SA, Tools): lists Installer/exes/shortcuts, Desktop report, safe removal of Setup/Portable left in Downloads/Desktop only (with consent); friendly startup tip when needed.
- **Paste path from clipboard** (SA + Add-on): Ctrl+C a file in Explorer → Paste… / Ctrl+Alt+V / Tools; optional “Open now” like Browse. SA only: drag-and-drop onto the window.
- **HTML guide**: AV word search via `.rtad.txt`; copies section; Paste.
- Updater/shell/Browse/guide 1.7.4 and sidecar/xlsx/Transcribe 1.7.3 remain.

### 🌟 What's New in Version 1.7.4

*(Published.)*

- **Standalone updates**: Installer → Setup only; Portable → Portable only (`app-v…` release).
- **Explorer menu (SA)**: “Open / analyze” opens that file; if RTAD is already open, no second window.
- **Browse → Single file**: any type; optional immediate analysis (image / AV / document).
- **Full HTML guide** (Help): table of contents, Ctrl+F search, Vision and Gemini API steps.
- Sidecar/xlsx/Transcribe-and-search 1.7.3, batch/B0/glossary 1.7.2, scanned-PDF 1.7.1 remain.

### 🌟 What's New in Version 1.7.3

*(Published.)*

- **`.rtad.txt` sidecar naming**: for **local** media, “Save text…” uses the **on-disk file stem**; URL/temp downloads still use title/ID.
- **Audio/Video only**: also finds **orphan** `.rtad.txt` files (no matching media) with snippets and `[MM:SS]` timestamps.
- **Excel `.xlsx`**: search cell contents; **Enter** opens Excel at the hit row; serial dates/times shown in readable form.
- **Transcribe and search…** (Tools / **Ctrl+Shift+T**): find spoken words via existing `.rtad.txt` first; otherwise Gemini transcription (max 30 files).
- Batch/B0/glossary 1.7.2, scanned-PDF 1.7.1, reader/spacing/toast 1.7.0, PDF TOC 1.6.9, and AV hub 1.6.7 remain.

### 🌟 What's New in Version 1.7.2

*(Published.)*

- **Analyze audio/video folder…**: batch local media → a `.rtad.txt` next to each file (tech sheet/summary by default; transcript and timestamps opt-in).
- **[AV] search**: with “Audio and Video only”, also searches existing `.rtad.txt` sidecars; snippets and `[MM:SS]` timestamps when present (no extra cost after analysis).
- **Transcript glossary** (Tools): post-Gemini corrections; accent-insensitive match; can rewrite `.rtad.txt` when opening a report.
- Scanned-PDF 1.7.1, reader/spacing/toast 1.7.0, PDF TOC 1.6.9, structured docs 1.6.8, and AV hub 1.6.7 remain.

### 🌟 What's New in Version 1.7.1

*(Published.)*

- **Scanned PDFs**: if “Read document…” finds no text but finds images → **Describe image** / **Open reader** dialog.
- **Describe image from PDF**: “Save text…” uses the **original PDF name and folder**; new **“Print text…”** (Windows printer / Print to PDF).
- **Tech sheet** (images and audio/video): **Analysis date** + **Original last modified** (as in File Explorer).
- **Reader**: arrow-key focus after minimize improved.
- Reader/spacing/toast 1.7.0, PDF TOC 1.6.9, structured docs 1.6.8, and AV hub 1.6.7 remain.

### 🌟 What's New in Version 1.7.0

*(Published.)*

- **In-app document reader**: “Read document…” opens an accessible reader (outline, links, body). **Ctrl+F** / F3 / Shift+F3 find in text; **Ctrl+H** / **Ctrl+Shift+H** jump `[Hn]` headings; “Open external file” is optional. After minimize, if arrows do nothing: Tab then Shift+Tab.
- **PDF spacing**: common space placeholders (e.g. Acer, braille manuals) become real spaces. Encrypted PDFs stay out of reach (Acrobat can open them; RTAD needs an unlocked copy).
- **End-of-search toast** less intrusive (short banner; still in Notification Center). With the reader open: speech only.
- PDF TOC/links 1.6.9, structured docs 1.6.8, AV hub 1.6.7, and image dialog 1.6.6 remain.

### 🌟 What's New in Version 1.6.9

*(Published.)*

- **Structured PDFs**: TOC/outline and URI links in “Read document (structure and text)” (alongside DOCX/EPUB).
- **Media reports**: long titles kept almost in full in `.rtad.txt` filenames (no longer cut at ~80 characters).
- **Find words in videos**: after “Save text…”, search the `.rtad.txt` files as normal text (same content as the transcript/description, no extra cost).
- Structured documents 1.6.8, audio/video hub 1.6.7, and image dialog 1.6.6 remain.

### 🌟 What's New in Version 1.6.8

*(Published.)*

- **Structured documents**: DOCX (headings + links) and EPUB (TOC/chapters); PDF plain text with an honest message if TOC is not yet available.
- **“Read document (structure and text)”** menu (Standalone and Add-on): outline, links (Enter / Open link), text with `[H1]` markers…
- **Media reports**: remember last folder; filename from URL title/ID or local stem; default to the media’s folder.
- **Auto-save search results** at end of search (Tools + folder choice); same order as the list.
- **Browse**: folder/drive or a single file (PDF/DOCX/…).
- Audio/video hub from 1.6.7 and image dialog from 1.6.6 remain.

### 🌟 What's New in Version 1.6.7

*(Published.)*

- **Everything about audio/video**: tech sheet (Short/vertical), summary, transcript and optional progressive timestamps (Gemini).
- **Audio/video hub**: the “Audio and Video only” filter opens URL, file and sections; same dialog from Tools.
- **Audio/video from URL** (`Ctrl+Shift+M`): direct links or YouTube/Vimeo with yt-dlp; in-app yt-dlp check/update; tech sheet shows source title/ID/URL; avoids silent video (ffmpeg recommended); Gemini File API above 20 MB (Google caps ~2 GB / ~3 h); long transcripts with continuation; **Save text…** in the report; progress (gauge + Alt+S status) like search.
- Limits = Google File API caps; no mass transcription of the whole PC.
- Standalone Explorer submenu + Tools/context menu (Add-on twin) on media files.
- Image dialog, folder batch and multi-font PDF from 1.6.6 remain.

### 🌟 What's New in Version 1.6.6

*(Published.)*

- **Everything about the image**: single dialog with alt-text, description, labels and tech sheet.
- **Folder batch**: analyse all images and optionally save `.rtad.txt` next to each file.
- **Multi-font PDF**: per-font ToUnicode (no more garbage text on multilingual PDFs).
- **Gemini API**: removed `temperature` from `generationConfig` (new Google AI Studio models).
- Web SVG/WebP fix and Explorer PDF/document submenu from 1.6.5 remain.

### 🌟 What's New in Version 1.6.5

*(Published.)*

- **Web icons/charts fix** (e.g. 3BMeteo): no wx «unknown image format» dialog on SVG/WebP; screen-area capture fallback (`NVDA+Shift+G`).
- **Standalone Explorer**: **PDF** / **documents** submenu (Open with default app + list entry, Read text, Copy text; Describe images on PDF).
- Describe from URL/Clipboard/capture, Shift+G, alt-text, `[ELENCO]`, image submenu remain.

### 🌟 What's New in Version 1.6.4

*(Published.)*

- **Describe from URL / Clipboard / screen capture** (twin SA + Add-on); SA shortcuts when the window is focused.
- **NVDA add-on**: `NVDA+Shift+G` on a web graphic or image file in File Explorer/Desktop.
- **Alt-text** short and Alt-text + description; **Describe image from PDF**.
- **List by type** with empty query (documents/images/media): `[ELENCO]` results.
- Fix: `NVDA+Shift+G` no longer reuses a background Explorer selection.
- Gemini/Vision/Explorer 1.6.3, notification 1.6.2, ZIP 1.6.1 remain.

### 🌟 What's New in Version 1.6.3

*(Published.)*

- **Describe image (Gemini)**: immersive description (layout, text, context); personal Google AI Studio key.
- **Technical sheet** + Vision labels; opt-in visual search `[IMG-VIS]`.
- **Standalone**: Explorer submenu on images (Describe, OCR, Labels, Tech sheet, Copy).
- End-of-search notification / OCR cache 1.6.2, ZIP 1.6.1, Vision OCR 1.6.0 remain.

### 🌟 What's New in Version 1.6.2

*(Published.)*

- **End-of-search notification**: stays in Windows Action Center (Windows+N) until you open it (Tools menu, on by default); beeps and speech remain.
- **Clear OCR cache** from the Tools menu.
- **Google Vision**: retries also cover bottom/side bands (bylines) and merge useful OCR pieces; OCR cache v17.
- ZIP / last-minute arrivals 1.6.1, Vision OCR 1.6.0, guide/EPUB 1.5.9 remain.

### 🌟 What's New in Version 1.6.1

*(Published.)*

- **Last-minute arrivals**, **ZIP opt-in**, stable list while searching; SAPI voice reset if Id is invalid.
- Vision OCR 1.6.0, guide/EPUB 1.5.9, local OCR 1.5.8 remain.

### 🌟 What's New in Version 1.6.0

*(Published.)*

- **Google Cloud Vision OCR** (opt-in): each user enters their **own** API key (Tools / Google Key button); twin Standalone + Add-on.
- List fix: after a search with 0 hits, the list no longer stays on “Search in progress…”.
- 1.5.9 guide + EPUB, 1.5.8 local OCR, 1.5.7 voice, 1.5.6 mail remain.

### 🌟 What's New in Version 1.5.9

*(Published.)*

- **Practical guide** (Help menu): plain language; each release updates the simple “what’s new” there, alongside the technical guide.
- Search inside **EPUB** books (`.epub`), `[EPUB]` results; included in Documents filter.
- 1.5.8 OCR, 1.5.7 voice, 1.5.6 mail, dates and profiles remain.

### 🌟 What's New in Version 1.5.8

*(Published.)*

- **Opt-in OCR:** text in images and scanned PDFs; `[IMG-OCR]` / `[PDF-OCR]`; cache and profiles.
- Engines: **Windows.Media.Ocr** (default) or optional **EasyOCR** (Standalone recommended for EasyOCR).
- Preprocess + fuzzy match; birthday↔compleanno synonyms; **Copy clean text** / **Copy full OCR**.
- OCR without a query (OCR on + empty text → Start). 1.5.7 voice, 1.5.6 mail, dates, profiles remain.

### 🌟 What's New in Version 1.5.7

- **Standalone voice:** SAPI rate (Ctrl++ / Ctrl+-), pitch, voice picker (incl. OneCore), Voice menu, persistence.
- RTAD announcements via adjustable SAPI (or NVDA). **F7** persistent Mute.
- **Twin Add-on:** Mute RTAD announcements (F7); rate/voice = NVDA settings.
- 1.5.6 complete mail search, dates, profiles and filters remain.

### 🌟 What's New in Version 1.5.6

- **Complete mail search:** Thunderbird/MBOX with no mailbox size cap (streaming); large PDF-attachment messages included.
- **`.pdf` filter:** also scans mailboxes/.eml for PDF attachments; **Open/Save extracted PDF** (not the whole INBOX).
- Less noise: WinSxS, Cursor caches and RTAD logs excluded; status reports mail messages and attachment hits.
- ~40 MB for DOC/text; **PDF ~80 MB**. 1.5.5 stability, feedparser, dates and profiles remain.

### 🌟 What's New in Version 1.5.5

- **Stability / anti-freeze:** no “Not responding” on large folders or awkward PDF/DOC (e.g. external drives), **without limiting** normal searches.
- PDF inflate hard cap; soft timeout only for stuck files; legacy OLE `.doc` skips useless ZipFile.
- **Date (dd/mm/yyyy) on every result:** txt, Word, media, images, file name… same as email and PDF.
- Very large files (> ~40 MB): match on **name**; lighter Alt+S/progress; visible folder indexing.
- Add-on: **bundled feedparser** (RSS/Atom in NVDA); **`.eml`/MBOX** match Standalone (one result per message).
- 1.5.4 profiles and filters remain.

### 🌟 What's New in Version 1.5.4

- **Search profiles:** save path, file type, options and (optional) query; Profiles menu; Ctrl+Shift+P / Ctrl+Shift+L.
- Manage profiles: rename or delete.
- **Richer type filters:** more extensions for Images, Audio/Video and Documents (e.g. m4a, flac, webp, html, md…).
- **Conflict-free Alt shortcuts:** one action per key (T/P/N/I/S/K); start search with Enter in the query field.
- 1.5.3 features remain (PDF text/images, Copy/Save Image).


### 🌟 What's New in Version 1.5.2
- **Safer email/MBOX viewer:** background loading; PDF/binary attachments skipped in displayed text.
- **Message date** (dd/mm/yyyy) also in MBOX and `.eml` results.

### 🌟 What's New in Version 1.5.1
- **Search history:** recent queries and paths kept locally; `Ctrl+H` / Cronologia button and `Ctrl+Shift+H`; Cronologia menu.

### 🌟 What's New in Version 1.5.0
- **RSS/Atom feeds:** search http(s) URLs, local `.rss`/`.atom`/`.xml` files and OPML lists; multiple paths separated by `;` or `,`.
- **Thunderbird Feeds:** dedicated button to auto-detect `Mail\Feeds` folders; cleaned-text search (one result per article) and open the original link in the browser.
- **Optional raw occurrences:** checkbox to also list `[FEED-RIGA]` lines besides articles, with jump-to-line in an editor.
- **Sort by article date** for feeds and a status note comparing raw occurrences to distinct articles.

### Key Features
- **Multi-format support**: Search across text files (`.txt`, `.log`, `.csv`), Word documents (`.docx`, `.doc`), PDF files, emails (`.eml` with native reader), RSS/Thunderbird feeds, and images with basic OCR scanning (`.jpg`, `.png`, `.bmp`).
- **Multiple keywords**: Supports flexible searches with multiple terms.
- **Automatic path memory**: Remembers the last searched folder to speed up workflows.
- **Global scan**: Ability to scan the entire PC across all active drives with a single command.

### How to reach the exact text in Word documents
For Microsoft Word documents, the add-on opens the file cleanly and safely. You can instantly reach the exact phrase by following these steps:
1. In the add-on results list, press the **Applications Key** on the desired Word file.
2. Select **"Copy News Block / Phrase with keyword"**.
3. Open the Word document directly from the results.
4. Press the shortcut **`Control + Shift + T`** to trigger targeted search.
5. Paste the copied text with **`Control + V`** and press **Enter**.
6. When the speech synthesizer announces the result and the next button, press **`Esc`**: the cursor will position itself precisely over the searched text, ready for reading (`NVDA + Down Arrow`).

*(Note: For those who prefer instant automatic opening without manual steps, the **Standalone .exe** version is also available).*

### Keyboard Shortcuts (NVDA Add-on)
- `NVDA + Shift + Control + F`: Open the main search window.
- `NVDA + Shift + Control + S`: Open the shortcuts and info dialog.
- `NVDA + Shift + Control + D`: Open the PayPal donation page.
- In the window: `Ctrl+F` filters results, `Alt+P` announces status (twice = copy), `Ctrl+U` checks for updates, **Feed Thunderbird** button for local RSS Feeds.
- Full guide (IT/EN): `addon/doc/it/readme.html` and `addon/doc/en/readme.html` (also via Add-on Manager → Help).

---

## 📦 Download & Install
Scarica l'ultima versione rilasciata (`.nvda-addon` o la versione `.exe` standalone) dalla sezione [Releases di GitHub](https://github.com/barramaurizio/ricerca_testuale_accesso_digitale/releases).

---
*Sostieni il progetto / Support the project:* [PayPal](https://paypal.me/AccessoDigitale) | [YouTube](https://www.youtube.com/@AccessoDigitale)
