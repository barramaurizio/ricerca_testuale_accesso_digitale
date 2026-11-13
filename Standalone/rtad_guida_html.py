# -*- coding: utf-8 -*-
"""Guida HTML completa RTAD — cercabile nel browser, con indice.

Manutenzione (ogni rilascio):
  1) Aggiorna la sezione «Novità di questa versione» in build_guida_html().
  2) Se aggiungi funzioni, inserisci un paragrafo con id= e voce nell'indice.
  3) Gemello opzionale: copia in addon/.../lib/ se serve anche all'Add-on.
"""

from __future__ import annotations


def build_guida_html(
    app_title: str,
    app_version: str,
    donation_url: str = "https://paypal.me/AccessoDigitale",
    github_url: str = "https://github.com/barramaurizio/ricerca_testuale_accesso_digitale",
) -> str:
    """Restituisce HTML UTF-8 completo (IT) della guida."""
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guida completa — {app_title} v{app_version}</title>
<style>
  body {{
    font-family: "Segoe UI", Tahoma, sans-serif;
    line-height: 1.55;
    margin: 0 auto;
    padding: 1.25rem 1.5rem 3rem;
    max-width: 52rem;
    color: #1a1a1a;
    background: #f7f8fa;
  }}
  h1 {{ color: #005a9c; border-bottom: 2px solid #005a9c; padding-bottom: .4rem; }}
  h2 {{ color: #003d6b; margin-top: 2rem; scroll-margin-top: 1rem; }}
  h3 {{ color: #222; margin-top: 1.25rem; scroll-margin-top: 1rem; }}
  nav#indice {{
    background: #eef6fc;
    border: 1px solid #b8d4ea;
    border-radius: 6px;
    padding: 1rem 1.25rem;
    margin: 1.25rem 0 1.75rem;
  }}
  nav#indice ol {{ margin: .5rem 0 0 1.2rem; padding: 0; }}
  nav#indice li {{ margin: .25rem 0; }}
  a {{ color: #005a9c; }}
  code, kbd {{
    background: #e8e8e8;
    padding: .1rem .35rem;
    border-radius: 3px;
    font-size: .95em;
  }}
  .box {{
    background: #eef6fc;
    border-left: 5px solid #005a9c;
    padding: .85rem 1rem;
    margin: 1rem 0;
  }}
  .note {{
    background: #fff8e6;
    border-left: 5px solid #c90;
    padding: .85rem 1rem;
    margin: 1rem 0;
  }}
  .ok {{
    background: #e8f5e9;
    border-left: 5px solid #2e7d32;
    padding: .85rem 1rem;
    margin: 1rem 0;
  }}
  ol.passi > li {{ margin: .55rem 0; }}
  ul {{ margin-left: 1.2rem; }}
  footer {{
    margin-top: 2.5rem;
    padding-top: 1rem;
    border-top: 1px solid #ccc;
    font-size: .95em;
    color: #444;
  }}
  .top {{ font-size: .9em; margin-top: .5rem; }}
</style>
</head>
<body>

<h1>{app_title}</h1>
<p><strong>Guida completa</strong> (versione {app_version}) — Maurizio Barra (Accesso Digitale)</p>
<p>Puoi <strong>cercare in questa pagina</strong> in due modi tipici:</p>
<ul>
  <li><kbd>Ctrl</kbd>+<kbd>F</kbd> — ricerca del browser (comoda soprattutto
    se si vede lo schermo; con lo screen reader i risultati si sentono, ma
    spesso è meno agevole leggerli uno per uno);</li>
  <li>con <strong>NVDA</strong>: <kbd>NVDA</kbd>+<kbd>Ctrl</kbd>+<kbd>F</kbd>
    (di solito il tasto NVDA è <kbd>Insert</kbd>, quindi
    <kbd>Insert</kbd>+<kbd>Ctrl</kbd>+<kbd>F</kbd>) — ricerca nel testo della
    pagina più pratica da navigare con lo screen reader.</li>
</ul>
<p>Altri screen reader possono avere un comando simile di «trova» nella pagina.
Usa anche l’indice qui sotto per saltare alle sezioni.</p>

<nav id="indice" aria-label="Indice della guida">
  <h2 style="margin-top:0;font-size:1.15rem;">Indice</h2>
  <ol>
    <li><a href="#novita">Novità di questa versione</a></li>
    <li><a href="#cos-e">Cos’è e a chi serve</a></li>
    <li><a href="#prima-ricerca">Prima ricerca in quattro passi</a></li>
    <li><a href="#sfoglia">Sfoglia: cartella o singolo file</a>
      (anche <a href="#incolla-percorso">Incolla dagli Appunti</a>)</li>
    <li><a href="#ocr">Testo nelle immagini (OCR)</a></li>
    <li><a href="#vision">Chiave API Google Cloud Vision (passo-passo)</a></li>
    <li><a href="#gemini">Chiave API Gemini / Google AI Studio (passo-passo)</a>
      (anche <a href="#crediti">crediti prepagati finiti</a>,
      <a href="#chat">conversazione sul file</a>
      e <a href="#confronto">confronto tra più file</a>)</li>
    <li><a href="#immagini">Descrivere immagini e «Tutto sull’immagine»</a></li>
    <li><a href="#media">Audio e video</a>
      (anche <a href="#media-ricerca">cercare parole nel parlato</a>,
      <a href="#ffmpeg">FFmpeg per un file già sul computer</a>
      e <a href="#ytdlp">yt-dlp per un indirizzo Internet</a>)</li>
    <li><a href="#documenti">Documenti, PDF, Excel, lettore</a>
      (anche <a href="#pagina-html">pagina HTML nel lettore</a>
      e <a href="#capitolo-epub">capitolo EPUB nel lettore</a>)</li>
    <li><a href="#explorer">Menù contestuale di Esplora file (solo Standalone)</a></li>
    <li><a href="#cd-audio">CD audio, DVD e file .cda</a></li>
    <li><a href="#aggiornamenti">Aggiornamenti: Installer e Portable</a></li>
    <li><a href="#copie">Trova altre copie sul PC (evitare doppioni)</a></li>
    <li><a href="#scorciatoie">Scorciatoie principali</a></li>
    <li><a href="#addon">Differenze con l’Add-on NVDA</a></li>
    <li><a href="#aiuto">Altre voci di Aiuto e supporto</a></li>
  </ol>
</nav>

<div class="box" id="novita">
  <h2 style="margin-top:0;">1. Novità di questa versione ({app_version})</h2>
  <ul>
    <li>Salva immagine, se la pagina consegna il testo del post, propone un pezzo breve di quel testo come nome del file. Invio sul pulsante Salva immagine, o un clic, salva con quel nome. Se la pagina non consegna il testo, il nome resta quello di oggi. Il testo disegnato dentro la foto resta fuori. Con Ctrl+Alt+V, o Descrivi da URL, puoi incollare l'indirizzo del post oppure l'indirizzo della foto: con il post, il nome è il commento; con solo la foto, se l'hai già descritta con la pagina, il nome resta quello del post. Vale per X e per le altre pagine che consegnano il commento, nella Standalone e nell'Add-on.</li>
    <li>Le chat di Gemini, i punti di lettura e i profili di ricerca della Standalone e dell'Add-on stanno nella cartella comune %AppData%\Roaming\RTAD. Portable, Installer e Add-on leggono la stessa cartella. Se la stessa conversazione è stata cambiata in tutte e due, a schermo e a voce: «Questa conversazione è stata cambiata anche nell'altra copia. Non l'ho sovrascritta. Restano tutte e due.» Se all'avvio le due copie erano diverse, a schermo e a voce: «Due copie di una conversazione sono diverse. Le tengo tutte e due. Non ne ho sovrascritta una.»</li>
    <li>Resta dalla 2.0.1: Taglia e unisci immagini: l'anteprima è più alta, così la foto si vede meglio mentre si lavora. Il file scritto resta a misura intera: una foto 900 per 900 resta 900 per 900. Invio sul pulsante Un quarto a destra, o un clic, gira l'immagine di un quarto verso destra. Invio sul pulsante Un quarto a sinistra, o un clic, la gira dall'altra parte. Invio sul pulsante Mezzo giro, o un clic, la capovolge. Il file di partenza resta com'è. Invio sul pulsante Esegui, o un clic, scrive il file nuovo: si chiama nome-giro-un-quarto-a-destra, nome-giro-un-quarto-a-sinistra o nome-giro-mezzo-giro. Il file unito si chiama Unito-uno-sotto-l-altro oppure Unito-uno-accanto-all-altro. Se il nome c'è già, si aggiunge -2. Dall'elenco, Alt e la lettera: B un quarto a destra, J un quarto a sinistra, N mezzo giro. Nella Standalone installata, in Esplora file, tasto destro o tasto Applicazioni, Cerca con Accesso Digitale: su un'immagine c'è Taglia e unisci; su un audio o un video ci sono Taglia e unisci e Converti. Invio sulla voce, o un clic, apre la finestra con quel file già in elenco. L'Add-on non aggiunge voci in Esplora file. Nella cronologia di Gemini, Invio sul pulsante Rinomina, o un clic, dà un nome nuovo alla conversazione. Il contenuto resta com'è. Vale nella Standalone e nell'Add-on.</li>
    <li>Resta dalla 2.0.0: Strumenti, Taglia e unisci audio/video. Invio sulla voce, o un clic, apre la finestra. Anche dal menu del risultato, su un audio o un video: Taglia e unisci. Invio sul pulsante Aggiungi, o un clic, mette i file in elenco. Invio sul pulsante Aggiungi cartella, o un clic, mette gli audio e i video di quella cartella. Le cartelle dentro non si aprono. L'ordine dell'elenco è l'ordine del risultato. Invio sul pulsante Sposta su o Sposta giù, o un clic, cambia l'ordine. Invio o doppio clic su una riga ascolta quel pezzo. Un clic solo seleziona la riga. Due numeri, 1:20, sono un minuto e 20 secondi. Tre numeri, 01:20:50, sono un'ora, 20 minuti e 50 secondi. Se scrivi solo la Fine, il tratto parte dall'inizio. Se scrivi solo l'Inizio, il tratto arriva fino alla fine del file. Il file unito si chiama Unito, poi Unito-2. Lo Stato, la barra di stato e Fatti dicono la stessa frase, con il nome di ogni file. Dall'elenco, Alt e la lettera del pulsante fa la stessa cosa: A Aggiungi, K Aggiungi cartella, S Sposta su, G Sposta giù, M Rimuovi, C Ascolta, F Ferma, T Tieni, O Togli, L Altro tratto, E Esegui, U Unisci. Invio sul pulsante Tieni da qui a qui, o un clic, tiene quel tratto. Invio sul pulsante Togli questo tratto, o un clic, toglie quel tratto e tiene il prima e il dopo. Invio sul pulsante Ferma, o un clic, ferma l'ascolto o il lavoro. Invio sul pulsante Altro tratto, o un clic, aggiunge quel tratto senza cambiare la riga. Con un file solo, Invio sul pulsante Esegui, o un clic, taglia la riga selezionata e scrive un file nuovo. Con almeno due file, Invio sul pulsante Unisci, o un clic, unisce l'elenco: il file intero, oppure il tratto già scelto. I file creati restano nell'elenco Fatti. Invio o doppio clic su un fatto lo rimette nell'elenco di lavoro. Un clic solo seleziona la riga. Il file di partenza resta com'è. Se i file non sono uguali, a schermo e a voce: «I file non sono uguali: li converto, ci vuole più tempo.» Se manca ffmpeg: «Per questo formato serve ffmpeg». A schermo e a voce: «Creato nome, durata, nella stessa cartella.»</li></li>
    <li>Resta dalla 2.0.0: Strumenti, Taglia e unisci immagini. Invio sulla voce, o un clic, apre la finestra. Anche dal menu del risultato, su un'immagine: Taglia e unisci. Invio sul pulsante Aggiungi file, o un clic, mette le immagini in elenco. Invio sul pulsante Aggiungi cartella, o un clic, mette le immagini di quella cartella. Le cartelle dentro non si aprono. L'ordine dell'elenco è l'ordine del risultato. Invio sul pulsante Sposta su o Sposta giù, o un clic, cambia l'ordine. Invio o doppio clic su una riga dice quel taglio. Un clic solo seleziona la riga. I quattro numeri sono sinistra, alto, larghezza e altezza. Invio sul pulsante Metà sinistra, Metà destra, Metà sopra, Metà sotto o Centro, o un clic, scrive quei numeri e li tiene sulla riga. Col mouse, trascina un rettangolo sull'immagine: al rilascio i quattro numeri si riempiono e il taglio è sulla riga. Invio sul pulsante Tieni questo taglio, o un clic, tiene i quattro numeri sulla riga selezionata. Invio sul pulsante Esegui, o un clic, scrive il taglio di quella riga. Il file si chiama nome-taglio, poi nome-taglio-2. Con almeno due immagini, Invio sul pulsante Uno sotto l'altro, o un clic, le mette una sotto l'altra. Invio sul pulsante Uno accanto all'altro, o un clic, le mette una accanto all'altra. Si unisce l'immagine intera, oppure il taglio già scelto. Il file unito si chiama Unito, poi Unito-2. I file creati restano nell'elenco Fatti. Invio o doppio clic su un fatto lo rimette nell'elenco di lavoro. Dall'elenco, Alt e la lettera del pulsante fa la stessa cosa: A Aggiungi file, K Aggiungi cartella, S Sposta su, G Sposta giù, M Rimuovi, I metà sinistra, D metà destra, P metà sopra, O metà sotto, C centro, T tieni questo taglio, E esegui, V uno sotto l'altro, Q uno accanto all'altro. Il file di partenza resta com'è. A schermo e a voce: «Creato nome, nella stessa cartella.»</li>
    <li>Resta dalla 2.0.0: Strumenti, Converti audio e video. Invio sulla voce, o un clic, apre la finestra. Anche dal menu del risultato, su un audio o un video: Converti. Invio sul pulsante Aggiungi file, o un clic, mette i file in elenco. Invio sul pulsante Aggiungi cartella, o un clic, mette gli audio e i video di quella cartella. Le cartelle dentro non si aprono. In lettura entrano anche M4B, AIFF, MKA, FLV, MTS e M2TS. Invio o doppio clic su una riga dice quel file. Un clic solo seleziona la riga. Nell'elenco Formato, freccia su e freccia giù scelgono: MP3, M4A, WAV, FLAC, OGG, Opus, WMA, MP4 e MKV. Vale per Converti la riga e per Converti tutti. Invio sul pulsante Converti la riga, o un clic, scrive il file selezionato. Invio sul pulsante Converti tutti, o un clic, scrive ogni riga. Da un video a un formato audio si tiene solo l'audio. Un audio non diventa un video. Il file di partenza resta com'è. Il file nuovo sta nella stessa cartella, con la nuova estensione. Se il nome c'è già, si chiama nome-2. I file creati restano nell'elenco Fatti. Invio o doppio clic su un fatto lo rimette nell'elenco di lavoro. Un clic solo seleziona la riga. Dall'elenco, Alt e la lettera del pulsante fa la stessa cosa: A Aggiungi file, K Aggiungi cartella, M Rimuovi, C Converti la riga, T Converti tutti, F Ferma. Invio sul pulsante Ferma, o un clic, ferma il lavoro. A schermo e a voce: «Creato nome, durata, nella stessa cartella.» Se manca ffmpeg: «Per questo formato serve ffmpeg».</li>
    <li>Resta dalla 1.9.10: Ctrl+E, oppure Invio sul pulsante Esporta Risultati, o un clic, apre la finestra. Spazio sulla casella, o un clic, sceglie il formato: testo, pagina web, tabella. Puoi accenderne più di una. Invio sul pulsante Esporta, o un clic, scrive tutti i file scelti, con lo stesso nome, nella cartella. Invio sul pulsante Sfoglia cartella, o un clic, cambia la cartella. Nella Standalone, con la voce di RTAD accesa, Salva e Sfoglia sono finestre di RTAD. Con la voce di RTAD spenta, sono le finestre di Windows, come nell'Add-on: le legge NVDA. La cartella proposta è quella da cui hai preso i file. La ricerca successiva non rilegge quei file di risultati: in elenco restano i documenti. Se quei file ci sono già, una domanda ha tre pulsanti. Invio sul pulsante Sì a tutti, o un clic, li sostituisce. Invio sul pulsante No a tutti, o un clic, torna alla finestra. A schermo e a voce: «Niente è stato scritto. I file già presenti restano.» Invio sul pulsante Scegli uno per uno, o un clic, chiede per ogni file: Invio sul pulsante Sì, o un clic, lo sostituisce; Invio sul pulsante No, o un clic, lo lascia. Esc annulla. Con la voce di RTAD, sull'elenco si sente il posto, per esempio «1 di 65». Su un pulsante si sente la parola Pulsante. Con la voce di RTAD, Ctrl+E dice «Esporta risultati, finestra di dialogo». La tabella si apre in Excel con lettere e simboli al loro posto. Esc annulla. A schermo e a voce: «Esportati 3 file: testo, pagina web e tabella. Cartella: nome.»</li>
    <li>Nell'Add-on, se la finestra di ricerca è ridotta a icona, Alt+Tab la riapre e il focus torna sul campo.</li>
    <li>Resta dalla 1.9.9, con la voce di RTAD accesa: Nella Standalone, Salva e Sfoglia sono finestre di RTAD, al posto di quelle di Windows. L'elenco Unità scorre solo i dischi, con freccia su e freccia giù oppure con la lettera iniziale. Invio o un doppio clic apre il disco e il focus resta su quell'elenco. Tab mostra solo le cartelle di quel disco: la lettera iniziale porta alla cartella, Invio o un doppio clic la apre. Shift+Tab torna all'elenco delle unità. I file della cartella aperta sono i più recenti in cima: Home va al primo, la lettera iniziale porta al file, Invio o un doppio clic lo sceglie. Il tipo di file si sente col nome prima: Immagini casella combinata. Freccia giù cambia. Alt+freccia giù apre l'elenco e le frecce restano sui tipi. Su Solo Audio e Video, il campo in cui incollare l'URL si apre dopo 4 secondi: se prima scegli un altro tipo, non si apre. Invio sul filtro già su Audio e Video lo apre subito. Invio sul pulsante Indietro, o un clic, oppure Alt+freccia sinistra, torna al percorso precedente. Invio sul pulsante Apri, Salva o Seleziona, o un clic, conferma. Alt+P legge lo stato: premuto due volte di seguito lo copia. Un clic sull'etichetta Stato porta allo stato. Con la voce di RTAD le dice RTAD. Con NVDA acceso e la voce di RTAD spenta, le dice NVDA. Nell'Add-on, Salva e Sfoglia restano le finestre di Windows. I 4 secondi su Solo Audio e Video ci sono anche lì: Freccia su o freccia giù, prima, sceglie un altro tipo e il campo non si apre. Invio sul filtro già su Audio e Video lo apre subito.</li>
    <li>Nella Standalone, Alt+P e la lettera S dicono lo stato per intero, anche con «Pronuncia i tasti di spostamento» acceso: il nome del tasto non copre la frase. Dopo una copia, la frase resta circa 2 secondi, a schermo e a voce, poi la barra torna alla riga della ricerca. S, F8 e Alt+P rileggono quella riga. Nell'Add-on la lettera S e Alt+P restano come nella 1.9.8.</li>
    <li>Nella Standalone, se esci con Alt+Tab, la voce dice «Non sei nel programma?». Quando torni e rilasci Alt, già sulla finestra di ricerca, dice il controllo, per esempio Elenco. Se ti fermi sul lettore, quello resta davanti. La casella Stato riprende la riga di prima: il download, la ricerca o l'ultimo esito. Se Alt+Tab si ferma sull'Add-on aperto accanto, dice «Add-on di NVDA, versione» e il numero di quella finestra. Nell'Add-on, se la finestra di ricerca resta aperta e ferma per alcuni minuti, al ritorno con Alt+Tab il focus torna su un campo.</li>
    <li>Nella Standalone, Invio su un risultato, o un doppio clic, resta nel programma quando RTAD può aprirlo. Un documento: «Apro «nome» nel lettore di Ricerca Testuale. La voce resta qui.» Se c'è un numero di riga, il cursore va lì. Un'immagine: «Apro «nome» in Tutto sull'immagine. La voce di RTAD resta in questa finestra.» Se accanto al testo c'è un video, la domanda dice Apri testo, che resta nel lettore, oppure Apri nel lettore di Windows, che fa partire il video: da lì segue NVDA. Esc chiude la domanda. Nell'Add-on, Invio apre il file come prima: l'editor, Word, il lettore di Windows, e NVDA segue quella finestra. Se accanto al testo c'è un video, la domanda dice Apri testo, che apre il testo come prima, oppure Apri nel lettore di Windows, che fa partire il video: da lì segue NVDA. Esc chiude la domanda.</li>
    <li>Nella Standalone, Apri cartella apre i file in RTAD: «Cartella di «nome». I file sono nell'elenco Elementi, i più recenti in cima. Freccia su e freccia giù scorrono. Invio o un doppio clic apre il file. Esc o Annulla torna ai risultati. La voce resta qui.» Nell'Add-on, Apri Cartella Contenitore apre Esplora file, come prima.</li>
    <li>Nella Standalone, Ordinamento è una voce del menu. Invio sulla voce, o un clic, apre l'elenco: Dal più recente, Dal meno recente, Alfabeticamente (A-Z). «Ordinamento dei risultati. Freccia su e freccia giù scelgono. Invio o un doppio clic applica. Esc chiude.» Nell'Add-on, Ordinamento Risultati resta il sottomenù di prima: lo legge NVDA.</li>
    <li>Resta dalla 1.9.8: In «Tutto sull'audio/video», Spazio sulla casella «Usa il login del browser», o un clic, la accende. All'avvio, Invio o un clic su «Autorizza» legge i cookie, solo per questo download. I cookie restano sul tuo PC. Su Windows la chiave di Edge, Chrome, Brave, Opera e Vivaldi spesso non si decifra, anche a programma chiuso. Firefox, se è aperto e sei entrato nel sito, si legge con la finestra aperta. Se il sito consegna video e audio separati, ffmpeg li unisce. Un flusso con protezione DRM resta non scaricabile: Netflix, Sky, DAZN, Prime e gli altri con Widevine, PlayReady o FairPlay restano chiusi.</li>
    <li>Una pagina audio di RaiPlay Sound, come il GR1, porta al file e lo mette in elenco. Il file resta nel formato consegnato da Rai, anche se il nome finisce in .mp4 e dentro c'è solo l'audio. A schermo e a voce si dice che è l'audio.</li>
    <li>Resta dalla 1.9.7: In «Tutto sull'audio/video», il riassunto breve è già scelto.
      Freccia giù, o un clic, passa alla descrizione dettagliata:
      in cima resta il riassunto e sotto il racconto scena per scena,
      una sola richiesta a Gemini. I timestamp del racconto sono spenti.
      Spazio sulla casella, o un clic, li accende. Se accesi, avanzano
      con le scene, sullo stesso orologio del video.
      Solo ciò che si vede o si sente. A schermo e a voce.
      Su una pagina che tiene video e audio separati, per esempio RaiPlay,
      si scaricano entrambi e ffmpeg li unisce.
      Il file scaricato da un indirizzo resta in vista nell'elenco.
      Insert+Tab dice quella riga, senza «invisibile» e senza «fuori schermo».</li>
    <li>Resta dalla 1.9.6: Nella Standalone, menu Voce, «Solo la voce di questo programma»:
      Ctrl+Shift+S, oppure Invio sulla voce, o un clic, accende o spegne la modalità. Tab e Shift li dice la voce in uso.
      Dentro RTAD questa voce dice anche dove sei: la casella, il pulsante,
      la riga dell'elenco con le frecce, la casella combinata, la voce di menu, e il simbolo che scrivi. Con Alt e le frecce dice il menu: Menu File, Menu Segnalibri, Menu Cronologia, Menu Profili, Menu Voce, Menu Strumenti, Menu Aiuto. «Pronuncia i tasti di spostamento» è spento. Invio sulla voce, o un clic, lo accende: allora dice anche Tab, Shift Tab, Shift, Control, Control A, Alt, le frecce, Inizio, Fine, Pagina su, Pagina giù, Insert, Canc, Backspace, Esc, Invio, i tasti da F1 a F12, e il tastierino numerico. Blocca maiuscole e Num Lock dicono attivato o disattivato. Se esci con Alt+Tab, o con un clic fuori dalla finestra, oppure un comando apre un'altra finestra, la voce dice: Non sei nel programma? Tieni premuto Alt e premi Tab: lo ripete a ogni finestra. Quando Tab torna sul programma, dice dove eri. Lo ripete anche a ogni clic fuori, finché non torni. Stampa schermo, Blocco scorrimento e Pausa si dicono se arrivano al programma. Stampa schermo spesso resta a Windows. Con le frecce sul menu, insieme al nome dice la scorciatoia scritta accanto. Invio sulla voce, o un clic, esegue quel comando. F8, oppure menu Voce, Dove sei: Invio sulla voce, o un clic. Dice la finestra in primo piano e il controllo: pulsante, campo di testo, elenco. «Pronuncia le lettere mentre scrivi» è spento. Invio sulla voce, o un clic, lo accende. I simboli si dicono lo stesso: punto, virgola, punto interrogativo.
      Se NVDA è acceso, spegni il sintetizzatore con NVDA+S, altrimenti senti due voci. Se la spegni con Ctrl+Shift+S, oppure Invio sulla voce, o un clic, Spazio, F4 e gli esiti li dice NVDA. F7, oppure Invio sulla voce, o un clic, mette in pausa la voce di RTAD: quelle frasi le dice NVDA. F7 di nuovo, oppure Invio sulla voce, o un clic, la riaccende.
      Le domande del programma, come Sì e No e le copie sul PC, le dice questa voce: il testo, i pulsanti, e su quale sei. Se la finestra è già aperta, Ctrl+Shift+S accende la voce e legge la domanda. Invio sul pulsante, o un clic, risponde. Tab passa all'altro. Esc chiude e viene detto. Nel menu del tasto applicazioni, insieme al nome dice il posto, per esempio 1 di 15. Esc, uscendo da un menu, viene detto. Nella Standalone, Salva e Sfoglia sono finestre di RTAD, dall'elenco Unità. Alt+P legge lo stato: premuto due volte di seguito lo copia. Un clic sull'etichetta Stato porta allo stato. Nell'Add-on, Salva e Sfoglia restano le finestre di Windows.
      L'Add-on resta sulla voce di NVDA.</li>
    <li>Nella Standalone, menu Voce, «Scegli voce»: Invio sulla voce, o un clic,
      oppure Ctrl+Shift+V, apre l'elenco. Ci sono le voci di Windows (OneCore)
      e quelle già registrate come SAPI. Invio sul pulsante OK, o un clic,
      imposta la voce. Doppio clic sulla riga fa la stessa cosa.
      Un clic solo seleziona la riga. Velocità e tono del menu valgono
      anche per le voci di Windows. L'Add-on resta sulla voce di NVDA.</li>
    <li>Resta dalla 1.9.5: La ricerca, se incontra un DVD video (VIDEO_TS), lo dice a schermo e a voce:
      «La ricerca ha incontrato un DVD video (VIDEO_TS).
      RTAD cerca i file dati sul disco (mp3, pdf, foto), non copia il film.»
      I file dati nelle altre cartelle restano.</li>
    <li>La conversazione di Gemini usa il nome del file già salvato.
      Salva conversazione propone quello stesso nome.
      Invio sul pulsante, e un clic.</li>
    <li>Salva Immagine sull'elenco ricorda l'ultima cartella,
      la stessa della finestra di analisi.
      Invio sul pulsante, e un clic.</li>
    <li>Nella Standalone, aprendo Salva video o Salva immagine, a volte il nome
      non viene letto subito. Tab e poi Shift+Tab lo legge sempre:
      la voce si riattiva. Salva testo di solito lo legge da solo.
      Nell'Add-on il nome si sente subito.</li>
    <li>Nel menu Aiuto, «Apri le guide»: Invio sulla voce, o un clic,
      apre le guide sul web, la pagina con i due link.
      L'indirizzo è
      <a href="https://barramaurizio.github.io/ricerca_testuale_accesso_digitale/guida/">https://barramaurizio.github.io/ricerca_testuale_accesso_digitale/guida/</a>.</li>
    <li>Resta dalla 1.9.4: In Word, Invio o doppio clic su un link interno va a quel titolo, qui.
      A schermo e a voce: «Titolo “nome”, qui nel testo.»
      Se il titolo non c'è: «Il titolo di destinazione non c'è.»
      Un clic solo seleziona la riga.</li>
    <li>In un file ODT, Leggi documento mostra i titoli e i link, come in Word.
      Invio o doppio clic su un titolo del sommario, o su un link interno,
      va a quel titolo, qui. Un clic solo seleziona la riga.
      Un sito web si apre fuori.</li>
    <li>Salva immagine, se la pagina consegna il testo del post, propone un pezzo breve di quel testo. Se non lo consegna, propone il nome della pagina, il più lungo che Windows accetta. Con Ctrl+Alt+V, o Descrivi da URL, l'indirizzo del post oppure l'indirizzo della foto: con il post, il nome è il commento; con solo la foto, se l'hai già descritta con la pagina, il nome resta quello del post. Salva audio o Salva video propone il nome della pagina,
      il più lungo che Windows accetta per un file.
      Se lo cambi, anche solo qualche carattere, Salva testo propone
      lo stesso nome, con .rtad.txt. Invio sul pulsante, e un clic.</li>
    <li>La guida del menu e la guida pratica sono anche sul web,
      lo stesso testo di chi ha il programma, aggiornate a ogni versione.
      L'indirizzo è
      <a href="https://barramaurizio.github.io/ricerca_testuale_accesso_digitale/guida/">https://barramaurizio.github.io/ricerca_testuale_accesso_digitale/guida/</a>.</li>
    <li>Resta dalla 1.9.3: Il corpo HTML di un'e-mail, l'articolo di un feed e una fonte
      della chat si aprono nel lettore di pagina.
      Invio o doppio clic su un'intestazione o su un link
      della stessa pagina va a quel punto, qui.
      Invio su Apri nel browser di Windows apre la pagina anche lì,
      e un clic sullo stesso pulsante.
      Word e PDF restano sul lettore di prima.</li>
    <li>Se l'immagine viene da Internet, la scheda tecnica
      e la descrizione avanzata dicono
      «Indirizzo immagine: https://….».
      Se la pagina è un altro indirizzo, anche «Pagina: https://….».
      Solo un'area dello schermo:
      «Immagine dallo schermo. Un indirizzo non c'è.»
      Invio su Salva immagine, e un clic, tengono la copia.
      A schermo e a voce il punto in cui il file è stato scritto.</li>
    <li>Salva video, o Salva audio se è arrivata solo la traccia,
      tiene il file già scaricato per l'analisi.
      Se video e audio sono due tracce, salva entrambi.
      Invio sul pulsante, e un clic.
      A schermo e a voce il punto in cui il file è stato scritto.
      Un link diretto scrive «Indirizzo file: https://….».
      Su YouTube, X e le altre pagine l'indirizzo temporaneo
      non si scrive. Ogni pagina passa da yt-dlp,
      anche una playlist .m3u8 o .mpd.
      Un contenuto protetto resta non scaricabile.
      Il login del browser, con il consenso, è in questa versione.</li>
    <li><strong>Resta dalla 1.9.2 — Leggi documento</strong> su un EPUB apre un capitolo
      nel lettore dentro RTAD. A schermo e a voce:
      «Capitolo: titolo. N intestazioni, M link. Passo 1 di 1.»
      Il sommario del libro è nella finestra: Invio apre quel capitolo, qui.
      Invio su un’intestazione va a quel punto, qui.
      Invio su un link interno resta nel libro.
      Indietro e Avanti tornano al capitolo di prima.
      Anche Alt+freccia sinistra e Alt+freccia destra.
      Un link http esce nel browser di Windows:
      «Apertura sito web esterno: titolo.»
      Senza intestazioni: «Nessuna intestazione in questa pagina.»
      Senza link: «Nessun link in questa pagina.»
      Senza sommario: «Nessuna voce di sommario.»
      Word e PDF restano sul lettore di prima.</li>
    <li><strong>Leggi documento</strong> su una pagina HTML, o su un
      indirizzo Internet già scaricato come pagina, apre il lettore
      dentro RTAD. A schermo e a voce:
      «Pagina: titolo. N intestazioni, M link. Passo 1 di 1.»
      Invio su un’intestazione va a quel punto, qui.
      Invio su un link della stessa pagina va a quel punto.
      Invio su un link di un altro sito apre quella pagina, qui.
      Indietro e Avanti tornano al punto di prima:
      un’altra intestazione della stessa pagina, o un altro sito.
      Anche Alt+freccia sinistra e Alt+freccia destra.
      «Apri nel browser di Windows» apre il link selezionato.
      Per un’intestazione, prima Invio nel lettore, poi lo stesso pulsante:
      il browser si apre su quel punto. Invio resta nel lettore.
      Senza intestazioni: «Nessuna intestazione in questa pagina.»
      Senza link: «Nessun link in questa pagina.»
      Word e PDF restano sul lettore di prima.</li>
    <li><strong>Nelle guide,</strong> il procedimento per FFmpeg
      (un file già sul computer), per yt-dlp (un indirizzo Internet)
      e per i crediti prepagati di Gemini.</li>
    <li><strong>Resta dalla 1.9.0 — Chiedi a Gemini…</strong> su ogni risultato che ha un file,
      un messaggio o un estratto: anche un messaggio dentro
      una casella Thunderbird, un .eml, un vecchio .doc,
      uno zip, un feed. In chat, a schermo e a voce:
      «Punto della ricerca: … Estratto: …».
      Gemini riceve lo stesso punto.
      Un messaggio della casella è una chat sua,
      non tutta la casella. Un allegato PDF già estratto
      apre la chat su quel PDF.
      Una riga che è solo un indirizzo dice, a schermo e a voce:
      «Questa riga è solo un indirizzo. Aprilo nel browser.»
      Senza la chiave resta:
      «Per conversare con Gemini serve la chiave personale, da Strumenti.»</li>
    <li><strong>Ctrl+H e Ctrl+Shift+H</strong> ricordano fino a 200 testi
      e 200 percorsi. L'ultimo usato sta in cima.
      I venti già salvati restano: il ventunesimo si aggiunge
      quando cerchi o scegli un percorso nuovo.</li>
    <li><strong>Ctrl+Alt+V</strong>, se negli Appunti non c'è un file,
      prende il testo di un messaggio, lo mette in elenco
      e lo apre nel lettore di pagina.
      A schermo e a voce:
      «Messaggio incollato. È in elenco: titolo.
      Si apre ora. Invio o doppio clic sulla riga lo riapre.»
      Da lì, Chiedi a Gemini.
      Un file .eml copiato o trascinato resta un file, come gli altri:
      «Il file è in elenco: nome. Da qui puoi fare altre operazioni.»
      Poi chiede: «Apri ora questo messaggio nel lettore di pagina?»
      Invio sul pulsante Sì, oppure un clic.
      Se il messaggio non ha un corpo HTML resta il lettore della posta.
      La stessa voce sta nel menu del tasto destro, o del tasto applicazioni:
      «Apri nel lettore di pagina». Invio sulla voce, oppure un clic.</li>
    <li><strong>Resta dalla 1.8.9. Confronta file…:</strong> da due a dodici file, in Strumenti
      e nel menu del risultato. Confronta, senza chiave, mostra e dice
      solo le parti diverse, con il nome del file davanti.
      Le parti uguali non si rileggono.
      In cima a ogni file, solo se non coincidono in tutti: tipo,
      dimensione, ultima modifica e, per un audio o un video, la durata.
      Alt+A aggiunge, anche sull’elenco. Alt+L toglie il file sotto
      il cursore, anche mentre ne aggiungi altri. Canc sull’elenco
      fa lo stesso. Nella scelta: i più recenti in cima, riga con
      nome, data, tipo e dimensione, primo file già selezionato.
      Shift+freccia giù prende un gruppo di fila. Control+freccia
      salta e quelli già presi restano. Poi di nuovo Shift+freccia giù:
      un altro gruppo. Control+Spazio aggiunge o toglie un file solo.
      Alt+C cambia cartella. La finestra di Windows resta.
      Sotto, i file già nel confronto: Alt+L ne toglie uno prima di Invio.
      Senza file: «Nessun file nel confronto.»
      Con meno di due: «Servono almeno due file.»
      La stessa lista, con la scritta «Allegati», è nella scelta di Gemini.
      Senza allegati: «Nessun allegato presente.»
      Sulla conversazione, Alt+L toglie un allegato già messo.
      Sulla finestra principale Alt+L resta la chiave Google.
      Chiedi a Gemini spiega quelle differenze, non i file interi.
      Senza la chiave il confronto resta:
      «Per conversare con Gemini serve la chiave personale, da Strumenti.»
      Se non hai ancora confrontato: «Prima fai Confronta.»
      Copia e Salva testo. Salva propone Confronto.txt nella cartella
      del primo file. Se c’è già: Confronto (1).txt, poi Confronto (2).txt.
      Un nome .chat.txt diventa Confronto (1).chat.txt.
      Un audio, un video o un’immagine non si trascrivono in questo
      confronto: se non c’è testo, la riga è «Nessun testo letto.»</li>
    <li><strong>PDF firmati con DocuSign:</strong> ogni font trova la sua
      tabella anche se il collegamento sta in uno stream compresso.
      Il sommario dice «Spett.le» e «PREMESSO». Virgolette, «sub-licenze»
      e «proporVi» restano a posto. «trascriv iamo» resta con lo spazio.</li>
    <li><strong>Resta dalla 1.8.8:</strong> scheda video anche con l’indice
      in fondo, glossario nel lettore, pagine HTML senza tag,
      indirizzo Internet in elenco.</li>
    <li><strong>Resta dalla 1.8.7:</strong> punti di lettura con Control+B,
      «Copia testo del documento» copia sommario, link e capitoli,
      nel PDF 202 7 torna 2027, negli EPUB i codici diventano lettere,
      il file aperto da Esplora file resta in elenco, Apri con apre solo
      questo programma.</li>
    <li><strong>Resta dalla 1.8.6 — Whisper sul mio PC:</strong> nell’analisi audio/video, insieme a
      «Trascrizione parlato», la casella «Sul mio PC (Whisper)» è spenta.
      Se la accendi, al primo uso scarica il modello e trascrive anche
      senza chiave Gemini. Un file fino a 20 minuti. In una cartella,
      fino a 5 file: «Whisper: 5 file su N. Non entrati: …».
      Il testo diventa <code>nome.rtad.txt</code> se accanto non c’era già.
      Se c’era, resta com’era. Un secondo avvio mentre lavora interrompe,
      a voce e a schermo: «Interruzione richiesta. Attendi la chiusura.»
      Gemini resta la trascrizione quando la casella è spenta.
      Un file già sul disco, come un m4a, può chiedere FFmpeg:
      <a href="#ffmpeg">come si installa</a>.
      Un indirizzo Internet, come YouTube, chiede yt-dlp:
      <a href="#ytdlp">è un altro programma</a>.</li>
    <li><strong>Resta dalla 1.8.5 — Traduci</strong> il testo già aperto:
      trascrizione, resoconto o documento nel lettore. Pulsante Traduci
      (Alt+U). L’originale resta, la traduzione si aggiunge sotto e nel
      video restano i timestamp. La lingua di arrivo si sceglie,
      l’italiano è già selezionato. Un testo lungo va a pezzi fino
      alla fine, a schermo e a voce. Non parte da sola: nell’analisi
      audio/video la casella «Traduci la trascrizione» è spenta.
      Salva testo propone lo stesso <code>nome.rtad.txt</code>:
      se si sovrascrive, l’originale resta e sotto c’è la traduzione.
      Dal resoconto già salvato propone <code>nome.rtad.rtad.txt</code>.</li>
    <li><strong>Resta dalla 1.8.4 — dal resoconto già salvato:</strong> su un
      .rtad.txt, Chiedi a Gemini usa quel testo e non rifà l’analisi. Se la
      foto, il video o il documento con lo stesso nome è ancora accanto,
      quello resta il file di partenza. Se non c’è più, la chat resta sul
      testo salvato e lo dice, a voce e a schermo.</li>
    <li><strong>Resta dalla 1.8.4 — elenchi vuoti:</strong> una riga vera,
      a schermo e in voce. «Nessuna ricerca avviata.», «Nessun risultato
      con questo filtro.», «Ancora nessuna fonte.», «Nessuna correzione
      nel glossario.» NVDA dice anche il percorso impostato, il testo
      salvato e i risultati esportati.</li>
    <li>Restano Alt+A, fino a 12 allegati, e Shift+Invio. In Esplora file,
      solo nel programma Windows, la voce c’è anche sul .rtad.txt.</li>
  </ul>
  <p class="top"><a href="#indice">↑ Indice</a></p>
</div>

<h2 id="cos-e">2. Cos’è e a chi serve</h2>
<p>Ricerca Testuale Accesso Digitale ti aiuta a trovare parole e frasi nei file
del computer e, se lo attivi, a leggere o descrivere immagini, PDF scansionati,
audio e video.</p>
<p>Esiste in due forme:</p>
<ul>
  <li><strong>Standalone</strong> — programma Windows a sé (Installer o Portable);</li>
  <li><strong>Add-on NVDA</strong> — le stesse ricerche dentro lo screen reader.</li>
</ul>
<p>Le funzioni principali sono allineate. Questa guida descrive soprattutto
lo Standalone; le differenze con l’Add-on sono in fondo.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="prima-ricerca">3. Prima ricerca in quattro passi</h2>
<ol class="passi">
  <li>Indica <strong>dove</strong> cercare: cartella, unità, oppure un singolo file
    (vedi <a href="#sfoglia">Sfoglia</a>). Oppure «Tutto il PC».
    Più posti insieme si scrivono nel campo percorso: un percorso, poi il punto e virgola attaccato, poi l'altro.
    Per esempio I:\\Juve;C:\\Documenti.
    Uno spazio prima o dopo il punto e virgola non dà fastidio: viene tolto.</li>
  <li>Scrivi <strong>cosa</strong> cercare nel campo testo.</li>
  <li>(Facoltativo) Scegli il tipo di file: tutti, immagini, audio/video, documenti…</li>
  <li>Premi <strong>Avvia ricerca</strong> oppure Invio nel campo testo.</li>
</ol>
<p>Durante la ricerca puoi seguire lo stato (Alt+P, Tab o S). Esc annulla la ricerca
in corso senza chiudere il programma.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="sfoglia">4. Sfoglia: cartella o singolo file</h2>
<p>Nella Standalone, Sfoglia e Salva aprono una finestra di RTAD.
L'elenco Unità scorre solo i dischi, con freccia su e freccia giù oppure con la lettera iniziale.
Invio o un doppio clic apre il disco e il focus resta su quell'elenco.
Tab mostra solo le cartelle di quel disco. La lettera iniziale porta alla cartella, Invio o un doppio clic la apre.
Shift+Tab torna all'elenco delle unità.
I file della cartella aperta sono i più recenti in cima: Home va al primo, la lettera iniziale porta al file, Invio o un doppio clic lo sceglie.
Il tipo di file si sente col nome prima: Immagini casella combinata. Freccia giù cambia. Alt+freccia giù apre l'elenco e le frecce restano sui tipi.
Invio sul pulsante Apri, Salva o Seleziona, o un clic, conferma.
Alt+P legge lo stato: premuto due volte di seguito lo copia. Un clic sull'etichetta Stato porta allo stato.
Nell'Add-on, Sfoglia e Salva restano le finestre di Windows: le legge NVDA.</p>
<p>Il pulsante <strong>Sfoglia…</strong> chiede:</p>
<ol>
  <li><strong>Cartella o unità</strong> — cerca in tutta la cartella;</li>
  <li><strong>Singolo file (qualsiasi tipo)</strong> — PDF, Word, Excel, immagini,
    audio/video, testo, oppure «Tutti i file».</li>
</ol>
<p>Se scegli un’immagine, un media o un documento, il programma può chiederti
se aprirlo subito (stesso spirito del menù contestuale di Esplora file).</p>
<h3 id="incolla-percorso">4.1 Incolla dagli Appunti e trascinamento</h3>
<p>In Esplora file seleziona un file (o una cartella) e premi <kbd>Ctrl</kbd>+<kbd>C</kbd>.
Poi in Ricerca Testuale:</p>
<ul>
  <li>pulsante <strong>Incolla…</strong> accanto a Sfoglia, oppure</li>
  <li>menu <strong>Strumenti</strong> → <strong>Incolla percorso dagli Appunti…</strong>, oppure</li>
  <li>scorciatoia <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>V</kbd>.</li>
</ul>
<p>Funziona anche se negli Appunti c’è un <strong>percorso testo</strong>
(«Copia come percorso» / Ctrl+V nel campo). Se il file è immagine, audio/video
o documento, può offrirti di aprirlo subito come con Sfoglia.</p>
<p>Se negli Appunti c’è il testo di un messaggio, non un file,
<strong>Ctrl+Alt+V</strong> lo mette in elenco e lo apre nel lettore di pagina.
A schermo e a voce:
«Messaggio incollato. È in elenco: titolo. Si apre ora. Invio o doppio clic sulla riga lo riapre.»
Da lì puoi chiedere a Gemini. Un testo di due parole non basta: senti e leggi
«Negli Appunti non c’è un file, un percorso o un messaggio.»</p>
<p>Solo Standalone: puoi anche <strong>trascinare</strong> un file o una cartella
sulla finestra del programma (stesso effetto). Dalla 1.7.6 il rilascio funziona
in qualunque punto della finestra (non solo sul titolo).</p>
<p>Se il file è un <strong>.eml</strong>, dopo la riga in elenco il programma chiede:
«Apri ora questo messaggio nel lettore di pagina?» Invio sul pulsante Sì, oppure un clic.
Se il messaggio ha un corpo HTML si apre nel lettore di pagina.
Se non ce l’ha, resta il lettore della posta.
Se rispondi no, la riga resta e da lì fai le altre operazioni.
Nel menu del tasto destro, o del tasto applicazioni, la voce è
«Apri nel lettore di pagina»: Invio sulla voce, oppure un clic.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="cd-audio">4.2 CD audio, DVD e file .cda</h2>
<p>«Tutto il PC» e Sfoglia accettano anche le unità CD/DVD quando il disco
è pronto. I file dati sul disco (mp3, pdf, foto nelle cartelle) si cercano
come su una chiavetta USB.</p>
<p>Un <strong>CD audio</strong> mostra tracce <code>Track01.cda</code>, ecc.:
non sono file audio veri sul disco, ma collegamenti di Windows alle tracce.
RTAD lo spiega con un messaggio e non può riprodurle né trascriverle da lì.</p>
<p><strong>Cosa fare per analizzare i brani del CD</strong> (senza installare
programmi extra, se hai Windows Media Player):</p>
<ol class="passi">
  <li>Inserisci il CD audio.</li>
  <li>Apri <strong>Windows Media Player</strong> (a volte «Lettore Windows Media
    classico» / Legacy).</li>
  <li>Usa <strong>Estrai</strong> / <strong>Copia da CD</strong> / <strong>Rip</strong>
    e salva i file (meglio mp3; altrimenti wma) nella cartella Musica.</li>
  <li>In RTAD apri quei file (Sfoglia, Incolla, trascinamento) e usa
    «Tutto sull’audio/video» come per qualsiasi altro brano.</li>
</ol>
<p>Non serve masterizzare un altro CD: i file sul disco fisso bastano.
Un DVD video commerciale (<code>VIDEO_TS</code>) non viene «rippato» da RTAD:
si cercano solo eventuali file dati presenti sul disco.
Se la ricerca incontra quella cartella, anche dentro un percorso più grande,
a schermo e a voce:
«La ricerca ha incontrato un DVD video (VIDEO_TS).
RTAD cerca i file dati sul disco (mp3, pdf, foto), non copia il film.»
I file dati nelle altre cartelle restano.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="ocr">5. Testo nelle immagini (OCR)</h2>
<p>Dalla 1.7.7, su tabelle e layout a colonne il testo OCR viene
riordinato <strong>riga per riga</strong> (quando il motore espone le
posizioni delle parole), così a schermo e con NVDA si legge in modo
più naturale. Dalla 1.7.5, se il motore grezzo restituisce una lettera
per riga (testo «in verticale»), il programma lo ricompone in parole
<strong>orizzontali</strong> prima di mostrarlo o leggerlo
(anche da «Leggi testo nell’immagine» nel menù Esplora / risultati).
La descrizione dell’immagine (Gemini) resta un percorso diverso e
di solito già in prosa naturale.</p>
<p>Per leggere testo «disegnato» in foto, screenshot o PDF scansionati:</p>
<ol>
  <li>Attiva la casella <em>Includi testo in immagini e PDF scansionati</em>.</li>
  <li>Scegli il motore OCR (Windows, EasyOCR se disponibile, oppure Google Vision).</li>
  <li>Avvia la ricerca come al solito.</li>
</ol>
<p>Google Cloud Vision è in genere il più forte sulle grafiche difficili, ma
richiede Internet e la <strong>tua</strong> chiave API (vedi sotto). Non c’è una
chiave condivisa nel programma: ognuno usa la propria.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="vision">6. Chiave API Google Cloud Vision (passo-passo)</h2>
<p>Serve per OCR avanzato e per il contenuto visivo (etichette/scene) quando
attivi le relative opzioni.</p>

<div class="note">
  <strong>Nota:</strong> serve un account Google. Google può chiedere una carta
  per attivare la fatturazione sul progetto Cloud; di solito Vision ha una
  quota gratuita mensile generosa per uso personale. Controlla sempre i costi
  sulla console Google. La chiave resta salvata solo su questo PC, in locale.
</div>

<ol class="passi">
  <li>Apri nel browser:
    <a href="https://console.cloud.google.com/" target="_blank" rel="noopener">
    Google Cloud Console</a>.</li>
  <li>Accedi con il tuo account Google.</li>
  <li>Crea un <strong>progetto</strong> (o selezionane uno esistente):
    menu progetto in alto → Nuovo progetto → nome a piacere (es. «RTAD») → Crea.</li>
  <li>Assicurati che il progetto sia selezionato (nome in alto nella barra).</li>
  <li>Vai su <strong>API e servizi</strong> → <strong>Libreria</strong>
    (oppure cerca «API Library»).</li>
  <li>Cerca <strong>Cloud Vision API</strong> → apri la scheda →
    <strong>Abilita</strong> / Enable.</li>
  <li>Vai su <strong>API e servizi</strong> → <strong>Credenziali</strong>.</li>
  <li>Clicca <strong>Crea credenziali</strong> → <strong>Chiave API</strong>.</li>
  <li>Copia la chiave (stringa lunga). Puoi anche limitarla solo a «Cloud Vision API»
    dalle opzioni della chiave (consigliato).</li>
  <li>In Ricerca Testuale Accesso Digitale:
    menu <strong>Strumenti</strong> → <strong>Chiave API Google Vision…</strong>
    (oppure il pulsante «Chiave Google» vicino al motore OCR).</li>
  <li>Incolla la chiave e conferma. Il programma può impostare da solo
    il motore OCR su Google Cloud Vision.</li>
</ol>

<div class="ok">
  <strong>Verifica:</strong> attiva OCR + (se vuoi) contenuto visivo, cerca
  qualcosa in una cartella con immagini. Se compare un messaggio sulla chiave
  mancante o non valida, ricontrolla di aver abilitato Cloud Vision API
  sul progetto giusto e di aver incollato tutta la chiave.
</div>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="gemini">7. Chiave API Gemini / Google AI Studio (passo-passo)</h2>
<p>Serve per la descrizione avanzata delle immagini, riassunti e trascrizioni
audio/video, e — dalla 1.8.0 — per la
<a href="#chat">conversazione sul file già aperto</a>.</p>

<div class="note">
  <strong>Importante:</strong> l’abbonamento Gemini Plus/Pro dell’app chat
  <em>non</em> sostituisce la chiave API. Serve una chiave creata in
  Google AI Studio. Usa una chiave dedicata a questo programma, se possibile.
</div>

<ol class="passi">
  <li>Apri:
    <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">
    https://aistudio.google.com/apikey</a>.</li>
  <li>Accedi con il tuo account Google.</li>
  <li>Clicca <strong>Create API key</strong> / Crea chiave API.</li>
  <li>Scegli un progetto Google Cloud (può essere lo stesso usato per Vision)
    oppure creane uno nuovo quando richiesto.</li>
  <li>Copia la chiave generata.</li>
  <li>In Ricerca Testuale Accesso Digitale:
    menu <strong>Strumenti</strong> →
    <strong>Chiave API Gemini (descrizione avanzata)…</strong>
    (oppure il pulsante «Chiave Gemini»).</li>
  <li>Incolla la chiave e conferma. Lascia vuoto e conferma per rimuoverla.</li>
</ol>

<div class="ok">
  <strong>Verifica:</strong> su un’immagine usa «Tutto sull’immagine» o
  «Descrivi» (serve connessione). Su un audio/video puoi provare riassunto
  o trascrizione (opt-in) dall’hub «Tutto sull’audio/video».
</div>

<h3 id="crediti">Crediti prepagati finiti</h3>
<p>Se compare questa frase:</p>
<div class="note">
  «Gemini non ha risposto: i crediti prepagati di questa chiave
  sono finiti. Si ricaricano in Google AI Studio.»
</div>
<p>Quella frase è del programma, non di Gemini.
La chiave è accettata e la domanda è arrivata a Google.
Google ha risposto che i crediti prepagati di questa chiave sono finiti.
In quel caso non si prova un altro modello.</p>
<p>Il tetto, per esempio da 25 euro, è un altro conteggio ed è ancora a zero.
Alzarlo non mette soldi nei crediti prepagati.
La carta e il tetto non li mettono da soli.
Vanno comprati i crediti prepagati, in Google AI Studio,
con lo stesso account Google della chiave.</p>
<ol class="passi">
  <li>Apri:
    <a href="https://aistudio.google.com/billing" target="_blank" rel="noopener">
    https://aistudio.google.com/billing</a>.</li>
  <li>Scegli <strong>Buy credits</strong>. In italiano può chiamarsi
    <strong>Acquista crediti</strong>. Il minimo è 5 dollari.</li>
  <li>Paga con la carta e attendi che il saldo dei crediti
    sia sopra zero.</li>
</ol>
<div class="note">
  <strong>Modifica limite di spesa</strong> è il tetto, non la ricarica.
</div>
<p>Poi chiudi Ricerca Testuale, riaprilo e rifai la domanda.
Se il pulsante non c’è, nella lista dei progetti cerca la scritta
<strong>No credits</strong> o <strong>Set up Prepay</strong> e cliccaci sopra:
è il collegamento per la stessa ricarica.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h3 id="chat">Conversazione con Gemini (dalla 1.8.0, ampliata in 1.8.4)</h3>
<p>Si può partire da un file già aperto, da zero, oppure da un
resoconto <code>.rtad.txt</code> già salvato. Il file, se c’è, resta.
In qualunque momento si allegano altri file.</p>
<ul>
  <li>Da un <code>.rtad.txt</code> già salvato: Chiedi a Gemini usa quel
    testo, senza rifare l’analisi. Se la foto, il video o il documento
    con lo stesso nome è ancora accanto, quello resta il file di partenza.
    Se non c’è più, la chat resta sul testo salvato e lo dice, a voce
    e a schermo.</li>
  <li>Pulsante <strong>Nuova conversazione</strong> (<kbd>Alt</kbd>+<kbd>Q</kbd>)
    e menù Strumenti → Nuova conversazione Gemini: nessuna foto
    e nessun documento aperti prima.</li>
  <li>Pulsante <strong>Conversazioni Gemini</strong> accanto ad Avvia ricerca,
    e menù Strumenti (<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>G</kbd>).</li>
  <li>Sul resoconto immagine o audio/video, e nel lettore documento:
    <strong>Chiedi a Gemini</strong> (<kbd>Alt</kbd>+<kbd>G</kbd>).</li>
  <li>Nella chat, <strong>Allega file</strong> (<kbd>Alt</kbd>+<kbd>A</kbd>):
    elenco della cartella, i più recenti in cima. Ogni riga dice
    nome, data, tipo e dimensione. Su un audio o un video, fermandosi,
    si sente la durata. Il primo è già selezionato.
    Shift+freccia giù prende un gruppo di fila.
    Control+freccia salta, e quelli già presi restano.
    Poi di nuovo Shift+freccia giù: un altro gruppo, senza perdere i primi.
    Control+Spazio aggiunge o toglie un file solo.
    Il numero è a voce e a schermo. Invio allega, fino a 12:
    immagini, documenti, audio e video. Le e-mail .eml no.
    Se qualcuno non entra, la frase dice quanti su quanti, e il motivo.
    Senza allegati, l’elenco dice «Nessun allegato presente».
    Sotto, gli allegati già messi: Alt+L ne toglie uno prima di Invio.
    Sulla conversazione, Alt+L toglie un allegato già messo,
    prima della domanda. Sulla finestra principale Alt+L resta
    la chiave Google.
    Alt+C cambia cartella. La finestra di Windows resta per le
    cartelle piccole. <strong>Togli allegato</strong> ne leva uno.</li>
  <li>Tasto Applicazioni su un risultato: Chiedi, oppure Riprendi se
    la conversazione c’è già. Un file <code>.chat.txt</code> salvato
    si riapre qui, se il titolo coincide.</li>
</ul>
<p>Shift+Invio va a capo. Invio invia.
Esc annulla la richiesta in corso; a riposo chiude la finestra.
Ci sono domande pronte, Copia, Salva, Stampa, Nuova conversazione
e Cronologia.</p>
<p>La casella <strong>Consulta anche il web</strong> è accesa: puoi spegnerla.
Quando è accesa, la risposta separa «Nel file» da «Approfondimento».</p>
<div class="note">
  <strong>Aprire un link.</strong> L’elenco Fonti e link non apre la pagina
  con Invio né con il doppio clic. Per aprirne una: Tab fino al pulsante
  <strong>Apri fonte</strong>, poi Invio, oppure un clic sullo stesso pulsante.
  Alt+F fa lo stesso, anche se sei sull’elenco.
  La fonte si apre nel lettore di pagina.
  Invio o doppio clic su un’intestazione o su un link della stessa pagina
  va a quel punto, qui.
  Invio su Apri nel browser di Windows apre la pagina anche lì,
  e un clic sullo stesso pulsante.
  Finché non c’è un link, l’elenco dice
  «Ancora nessuna fonte.»
</div>
<p>Se il file arriva da un indirizzo Internet, la conversazione resta
col <strong>titolo del video</strong> e con quell’indirizzo, non col nome
del file temporaneo. Salva propone l’ultima cartella che hai usato.</p>
<p>La cronologia sta su questo PC e non contiene la chiave API.
Il programma Windows e l’Add-on NVDA fanno la stessa cosa, ma
le conversazioni già fatte in uno non compaiono nell’altro.</p>
<p>Serve la tua chiave di Google AI Studio (sopra). RTAD non addebita
nulla: eventuali costi sono quelli del tuo account Google.
Il modello usato è Flash.
Se la frase dice che i crediti prepagati sono finiti, il procedimento
è in <a href="#crediti">Crediti prepagati finiti</a>.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h3 id="confronto">Confrontare più file (dalla 1.8.9)</h3>
<p>Strumenti → <strong>Confronta file…</strong>, oppure la stessa voce nel menu
del risultato (tasto Applicazioni). Da due a dodici file.
Il pulsante <strong>Confronta</strong> non usa la chiave: mostra e dice
solo le parti che non stanno in tutti i file, con il nome davanti.
Le parti uguali non si rileggono.</p>
<ul>
  <li><strong>Aggiungi file…</strong> (Alt+A), anche se sei sull’elenco.
    <strong>Togli</strong> (Alt+L) leva il file sotto il cursore,
    anche mentre ne aggiungi altri. Canc sull’elenco fa lo stesso.
    Sulla finestra principale Alt+L resta la chiave Google.</li>
  <li>Nella scelta i più recenti sono in cima. Ogni riga dice nome,
    data, tipo e dimensione. Il primo è già selezionato.
    Shift+freccia giù prende un gruppo di fila.
    Control+freccia salta, e quelli già presi restano.
    Poi di nuovo Shift+freccia giù: un altro gruppo, senza perdere i primi.
    Control+Spazio aggiunge o toglie un file solo.
    Il numero è a voce e a schermo. Invio conferma.
    Alt+C cambia cartella. La finestra di Windows resta.</li>
  <li>Sotto, i file già nel confronto: Alt+L ne toglie uno prima di Invio.
    Si può confermare anche solo una rimozione.
    Senza file, la riga selezionata dice «Nessun file nel confronto.»
    Con meno di due: «Servono almeno due file.»
    Mentre lavora: «Confronto in corso. Attendere.»</li>
  <li>La stessa lista, con la scritta «Allegati», è nella scelta di Gemini.
    Senza allegati: «Nessun allegato presente.»
    Sulla conversazione, Alt+L toglie un allegato già messo,
    prima della domanda.</li>
  <li>In cima a ogni file, solo se non coincidono in tutti:
    tipo, dimensione, ultima modifica e, per un audio o un video,
    la durata. Se sono uguali, quelle righe non si rileggono
    e non si mescolano alle frasi.</li>
  <li><strong>Chiedi a Gemini</strong> spiega quelle differenze, non i file interi.
    Senza la chiave il confronto resta, a schermo e a voce:
    «Per conversare con Gemini serve la chiave personale, da Strumenti.»
    Se non hai ancora confrontato: «Prima fai Confronta.»</li>
  <li><strong>Copia</strong> e <strong>Salva testo…</strong>. Salva propone
    Confronto.txt nella cartella del primo file. Se c’è già:
    Confronto (1).txt, poi Confronto (2).txt.
    Un nome .chat.txt diventa Confronto (1).chat.txt.
    Lo stesso nome libero vale quando salvi una chat.</li>
  <li>Si legge il testo di PDF, Word, ODT, Excel, EPUB, HTML e file di testo.
    Un audio, un video o un’immagine non si trascrivono in questo confronto.
    Se non c’è testo: «Nessun testo letto.»</li>
</ul>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="immagini">8. Descrivere immagini e «Tutto sull’immagine»</h2>
<ul>
  <li>Da Esplora file (Standalone): sottomenù
    <em>Cerca con Accesso Digitale</em> → Descrivi / Tutto sull’immagine / OCR…</li>
  <li>Dalla finestra: Strumenti o scorciatoie (URL, Appunti, cattura schermo).</li>
  <li>Il dialogo <strong>Tutto sull’immagine</strong> lascia scegliere cosa includere
    (alt-text, descrizione, etichette, scheda tecnica) prima di avviare.</li>
</ul>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="media">9. Audio e video</h2>
<ul>
  <li>Hub analisi da Strumenti / pulsante dedicato / menù Esplora file.</li>
  <li><strong>Tutto sull’audio/video</strong>: scheda tecnica, riassunto, trascrizione.
    Il riassunto breve è già scelto. Freccia giù, o un clic, passa alla
    descrizione dettagliata: in cima resta il riassunto e sotto il racconto
    scena per scena, una sola richiesta. I timestamp del racconto sono spenti.
    Spazio sulla casella, o un clic, li accende. Se accesi, avanzano con le scene,
    sullo stesso orologio del video. Solo ciò che si vede o si sente.
    Su una pagina che tiene video e audio separati, per esempio RaiPlay,
    si scaricano entrambi e ffmpeg li unisce.     Un contenuto protetto resta
    non scaricabile.
    Spazio sulla casella «Usa il login del browser», o un clic, la accende.
    Invio o un clic su «Autorizza» legge i cookie del browser già aperto
    su questo PC, solo per questo download. I cookie restano sul tuo PC.
    Una pagina audio di RaiPlay Sound, come il GR1, porta al file
    e lo mette in elenco. Anche se il nome finisce in .mp4 e dentro
    c'è solo l'audio, a schermo e a voce si dice che è l'audio.
    La trascrizione è opt-in, con Gemini. «Sul mio PC (Whisper)» è un’altra casella, spenta:
    al primo uso scarica il modello e trascrive senza chiave Gemini,
    un file fino a 20 minuti, in una cartella fino a 5 file.
    La casella «Traduci la trascrizione» è spenta:
    se la accendi, sotto la trascrizione compare la traduzione,
    con gli stessi timestamp. Salva testo propone lo stesso
    <code>nome.rtad.txt</code>: sovrascrivendo, l’originale resta
    e la traduzione si aggiunge sotto.
    Un file già sul disco, come un m4a, può chiedere FFmpeg:
    <a href="#ffmpeg">come si installa</a>.
    Un indirizzo Internet chiede yt-dlp:
    <a href="#ytdlp">è un altro programma</a>.</li>
  <li>Batch cartella: analizza più file e salva i report <code>.rtad.txt</code> accanto.</li>
  <li><strong>Trascrivi e cerca…</strong> (Ctrl+Shift+T): cerca parole nel parlato
    usando i report già fatti, oppure trascrive con Gemini (limite per sessione).</li>
  <li>Con filtro «Solo Audio e Video» trovi anche i <code>.rtad.txt</code> «orfani».</li>
</ul>

<h3 id="media-ricerca">9.1 Cercare parole nel parlato: come funziona davvero</h3>
<p>Quando cerchi una parola «dentro» un audio o un video, il programma
<strong>non ascolta di nuovo tutti i file a ogni ricerca</strong>
(sarebbe lentissimo e costoso). Cerca invece nel testo già salvato
nei file <code>.rtad.txt</code> accanto al media (la trascrizione / report).</p>
<div class="box">
  <strong>In pratica:</strong>
  <ol class="passi">
    <li>Prima crei i report (una sola volta per file), con una di queste vie:
      <ul>
        <li>«Tutto sull’audio/video» → trascrizione e salvataggio;</li>
        <li>«Analizza cartella audio/video…» (batch su una cartella);</li>
        <li>«Trascrivi e cerca…» (Ctrl+Shift+T): usa i
          <code>.rtad.txt</code> già presenti; se mancano, trascrive con Gemini
          (c’è un limite per sessione).</li>
      </ul>
    </li>
    <li>Poi cerchi la parola come fai con i documenti.</li>
  </ol>
</div>
<div class="ok">
  <strong>«Tutto il PC» funziona anche per audio/video?</strong>
  Sì, <em>se</em> i file <code>.rtad.txt</code> esistono già da qualche parte
  sul computer. Non serve conoscere la cartella: con percorso «tutto il PC»
  (o Alt+T) e filtro «Solo Audio e Video» (o tutti i tipi), le parole
  nei report vengono trovate ovunque siano.
  Se invece hai solo i file mp3/mp4 <em>senza</em> report accanto,
  la ricerca sul parlato non può inventare la trascrizione da sola:
  usa prima «Trascrivi e cerca…» o il batch sulla cartella che ti interessa.
</div>
<div class="note">
  <strong>Nome nel salvataggio, Standalone:</strong> aprendo Salva video
  o Salva immagine, a volte il nome non viene letto subito.
  Tab e poi Shift+Tab lo legge sempre: la voce si riattiva.
  Il nome proposto è già quello.
  Salva testo, la descrizione, di solito lo legge da solo.
  Nell'Add-on il nome si sente subito.
</div>
<div class="note">
  <strong>Differenza utile:</strong> sul <em>nome file</em> di un video
  la ricerca può funzionare subito (come per qualsiasi file).
  Sul <em>contenuto parlato</em> serve il <code>.rtad.txt</code>.
  I report «orfani» (testo senza il media gemello nella stessa cartella)
  restano cercabili con il filtro Solo Audio/Video.
</div>
<h3 id="ffmpeg">9.2 FFmpeg: un file audio già sul computer</h3>
<p>FFmpeg serve quando il file è già sul computer, per esempio
un m4a in Musica. Serve a Whisper, e anche a unire audio e video
scaricati da Internet. Non è yt-dlp.</p>
<p>La frase del programma, se manca, inizia con
«Per questo formato serve ffmpeg».
L’esempio che il programma scrive è
<code>winget install Gyan.FFmpeg</code>.
Quel comando e il file zip qui sotto sono lo stesso pacchetto.
Non prendere un ffmpeg.exe singolo da un altro sito.</p>
<ol class="passi">
  <li>Dal browser apri
    <a href="https://www.gyan.dev/ffmpeg/builds/" target="_blank" rel="noopener">
    https://www.gyan.dev/ffmpeg/builds/</a>
    e scarica <code>ffmpeg-release-essentials.zip</code>.</li>
  <li>Apri lo zip. Dentro c’è una sola cartella.
    Il nome cambia con la data: per esempio
    <code>ffmpeg-2026-10-25-git-46f23be8b1-essentials_build</code>.
    Dentro quella ci sono altre cartelle. Quella che serve si chiama
    <code>bin</code>.
    Lì ci sono <code>ffmpeg.exe</code> e <code>ffprobe.exe</code>.
    Servono tutti e due.
    Se c’è anche <code>ffplay.exe</code>, si copia insieme e non dà fastidio.</li>
  <li>In Esplora file, sul disco C:, crea la cartella <code>ffmpeg</code>
    e, dentro, la cartella <code>bin</code>.
    Copia in <code>C:\\ffmpeg\\bin</code> tutto il contenuto di quel bin,
    i file .exe.</li>
  <li>Tasto Windows, scrivi <strong>variabili d'ambiente</strong>.
    La voce che appare è
    «Modifica le variabili di ambiente relative al sistema,
    Pannello di controllo».
    Apre le proprietà del sistema. Nella scheda Avanzate
    c’è il pulsante <strong>Variabili d’ambiente</strong>.
    Le liste sono due. Si lavora su quella in alto,
    «Variabili utente» dell’account.
    Seleziona <strong>Path</strong>, poi <strong>Modifica</strong>, poi <strong>Nuovo</strong>,
    e incolla <code>C:\\ffmpeg\\bin</code>.
    Conferma con OK fino a chiudere tutte le finestre.</li>
  <li>Chiudi l’Installer di Ricerca Testuale Accesso Digitale e riaprilo.</li>
</ol>
<div class="box">
  <strong>Per capire se Windows lo vede:</strong> Tasto Windows e R insieme.
  Nella casella scrivi <code>ffmpeg</code> e premi Invio.
  <ul>
    <li>Se compare «Windows non trova il file», il percorso non è attivo.
      La finestra di Esegui non dà dettagli: non dice in quali cartelle
      ha cercato.
      In <code>C:\\ffmpeg\\bin</code> devono esserci
      <code>ffmpeg.exe</code> e <code>ffprobe.exe</code>.
      In Path, nella lista in alto, una riga sola con
      <code>C:\\ffmpeg\\bin</code>.
      Poi esci da Windows e rientra, e riapri l’Installer.</li>
    <li>Se lampeggia una finestra nera e si chiude, Windows lo ha trovato.
      Chiudi l’Installer con la X, riaprilo e riprova l’m4a
      o il file che vuoi.</li>
  </ul>
</div>
<p>Se Esegui non lo trova, con Internet acceso apri PowerShell,
incolla solo questa riga e dai Invio. Attendi la fine.
Poi chiudi PowerShell, chiudi l’Installer e riaprilo:</p>
<p><code>winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements</code></p>
<p>Aver messo FFmpeg e aver riavviato Windows non fa sparire
una frase che parla di yt-dlp. Quella è la sezione successiva.</p>

<h3 id="ytdlp">9.3 yt-dlp: scaricare da un indirizzo Internet</h3>
<p>yt-dlp serve per scaricare da un indirizzo Internet, come YouTube.
Un m4a già sul disco non ne ha bisogno.
Il programma può segnalare che yt-dlp manca e proporti l’aggiornamento.</p>
<p>La frase del programma inizia con «yt-dlp non trovato»
oppure dice «serve yt-dlp nel PATH».
Nello stesso testo il programma cita anche
<code>winget install Gyan.FFmpeg</code>.
Per questo i due nomi sembrano la stessa cosa.
Non lo sono. Prima di installare altro, la prova è Esegui con
<code>ffmpeg</code>, come nella sezione
<a href="#ffmpeg">FFmpeg</a>.
Poi si guarda la prima riga del programma:</p>
<ul>
  <li>se inizia con «Per questo formato serve ffmpeg», è FFmpeg;</li>
  <li>se inizia con «yt-dlp non trovato» o «serve yt-dlp nel PATH»,
    è il programma per i link Internet.</li>
</ul>
<p>Solo in quel secondo caso, con Internet acceso, in PowerShell
incolla solo questa riga e dai Invio. Attendi la fine.
Poi chiudi PowerShell, chiudi l’Installer e riaprilo:</p>
<p><code>winget install --id yt-dlp.yt-dlp -e --accept-source-agreements --accept-package-agreements</code></p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="documenti">10. Documenti, PDF, Excel, lettore</h2>
<h3 id="pagina-html">Pagina HTML nel lettore</h3>
<p>Su un file <code>.html</code> o <code>.htm</code>, e su un indirizzo
Internet già scaricato come pagina, <strong>Leggi documento</strong>
apre il lettore dentro RTAD. A schermo e a voce:
«Pagina: titolo. N intestazioni, M link. Passo 1 di 1.»</p>
<ul>
  <li>Invio su un’intestazione va a quel punto, qui.
    Invio su un link della stessa pagina va a quel punto.
    Invio su un link di un altro sito apre quella pagina, qui.</li>
  <li><strong>Indietro</strong> e <strong>Avanti</strong> tornano
    al punto di prima: un’altra intestazione della stessa pagina,
    o un altro sito. Anche Alt+freccia sinistra e Alt+freccia destra.
    Se non c’è un punto, la frase lo dice:
    «Non c’è un punto precedente.»
    «Non c’è un punto successivo.»</li>
  <li><strong>Apri nel browser di Windows</strong> apre il link
    selezionato nell’elenco Link.
    Per un’intestazione, prima Invio nel lettore, poi lo stesso pulsante:
    il browser si apre su quel punto.
    Invio resta nel lettore.
    Nel testo, un indirizzo https si attiva con Invio.
    Maiusc+Tab dal testo seleziona quel link nell’elenco.
    I tasti H e K di NVDA si usano in quel browser:
    qui si usano gli elenchi Intestazioni e Link.</li>
  <li>Senza intestazioni, la riga selezionata dice
    «Nessuna intestazione in questa pagina.»
    Senza link: «Nessun link in questa pagina.»</li>
  <li>Word e PDF restano sul lettore di prima:
    sommario, link e salto nel testo.</li>
</ul>
<h3 id="capitolo-epub">Capitolo EPUB nel lettore</h3>
<p>Su un file <code>.epub</code>, <strong>Leggi documento</strong>
apre un capitolo nella stessa finestra. A schermo e a voce:
«Capitolo: titolo. N intestazioni, M link. Passo 1 di 1.»</p>
<ul>
  <li>Il sommario del libro è nella finestra.
    Invio apre quel capitolo, qui, sul punto indicato.</li>
  <li>Invio su un’intestazione va a quel punto, qui.
    Invio su un link interno resta nel libro.</li>
  <li><strong>Indietro</strong> e <strong>Avanti</strong> tornano
    al capitolo di prima. Anche Alt+freccia sinistra e Alt+freccia destra.</li>
  <li>Un link http esce nel browser di Windows:
    «Apertura sito web esterno: titolo.»</li>
  <li>Senza sommario: «Nessuna voce di sommario.»
    Senza intestazioni: «Nessuna intestazione in questa pagina.»
    Senza link: «Nessun link in questa pagina.»</li>
  <li>La ricerca di una frase nel libro resta quella di sempre.
    Le figure restano nel file: questa versione legge il testo del capitolo.</li>
</ul>
<ul>
  <li>PDF con testo, Word, EPUB, HTML, testo, Excel <code>.xlsx</code>: ricerca nel contenuto.</li>
  <li><strong>Leggi documento…</strong> / lettore interno: cerca e titoli, dove supportato.</li>
  <li><strong>Punti di lettura:</strong> Control+B ne aggiunge uno, quanti ne vuoi.
    Control+Shift+B torna all’ultimo. Nell’elenco, Invio sceglie un altro.
    Vale per ogni documento aperto con Leggi documento, anche un txt.
    Non è il Segnalibro Ctrl+D.</li>
  <li>PDF solo immagine (scansione): usa Descrivi / OCR come per le immagini.</li>
  <li>Su risultato Excel: Invio può aprire Excel alla riga del risultato.</li>
</ul>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="explorer">11. Menù contestuale di Esplora file (solo Standalone)</h2>
<p>Dopo l’installazione con Setup, sul tasto destro (o tasto Applicazioni)
appare <strong>Cerca con Accesso Digitale</strong>:</p>
<ul>
  <li>su <strong>cartelle</strong>: cerca in quella cartella; batch immagini o audio/video;</li>
  <li>su <strong>immagini</strong>: Apri/analizza, Descrivi, OCR, etichette, scheda, Taglia e unisci. Invio sulla voce, o un clic, apre la finestra con quel file già in elenco. Chiedi a Gemini…;</li>
  <li>su <strong>audio/video</strong>: Apri/analizza, Tutto sull’AV, scheda, Taglia e unisci e Converti. Invio sulla voce, o un clic, apre la finestra con quel file già in elenco. Chiedi a Gemini…;</li>
  <li>su <strong>documenti/PDF/xlsx</strong>: Apri, Leggi testo, Copia testo, Chiedi a Gemini…</li>
</ul>
<p>Se il programma è già aperto, il comando arriva alla finestra esistente
(niente seconda copia dispersiva).</p>
<p class="note">L’Add-on NVDA non scrive voci nel registro di Windows:
usa le scorciatoie NVDA (es. NVDA+Shift+G dove previsto) e i menu dell’Add-on.</p>
<p><strong>Invia a</strong>, nella Standalone installata. Tasto Windows e R, scrivi
<code>shell:sendto</code>, Invio: si apre la cartella Invia a. È la stessa di
<code>AppData\Roaming\Microsoft\Windows\SendTo</code>. Il modo semplice: sul
Desktop, sul collegamento del programma, <kbd>Ctrl</kbd>+<kbd>C</kbd>. Nella
cartella Invia a, <kbd>Ctrl</kbd>+<kbd>V</kbd>. Se c’era l’exe intero,
cancellalo. Il file giusto finisce in <code>.lnk</code>, per esempio
<code>Ricerca Testuale Accesso Digitale.lnk</code>. Su un file, tasto destro
o tasto Applicazioni, Invia a, Ricerca Testuale Accesso Digitale: il file si
apre nel programma. Il collegamento punta all’Installer e segue gli
aggiornamenti. Incollare l’exe intero funziona, ma è una copia ferma a quella
versione e pesa quanto il programma. Su Windows 11, «Crea collegamento»
sull’exe in Program Files spesso non fa nulla: Windows prova a scriverlo lì e
non può. Non si apre una finestra. Usa il collegamento del Desktop.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="aggiornamenti">12. Aggiornamenti: Installer e Portable</h2>
<p>Menu <strong>Strumenti</strong> → verifica aggiornamenti (<kbd>Ctrl</kbd>+<kbd>U</kbd>),
anche in automatico all’avvio in modo silenzioso.</p>
<ul>
  <li>Se hai installato con il <strong>Setup</strong> (di solito in Program Files):
    viene proposto il file <code>Setup_RicercaTestualeAccessoDigitale_v…exe</code>.</li>
  <li>Se usi la <strong>Portable</strong>: viene proposto solo
    <code>RicercaTestualeAccessoDigitale_Portable_v…exe</code>.</li>
</ul>
<p>Dalla 1.7.6 il download automatico non va più in Download: usa
<code>%LocalAppData%\\RTAD_Standalone\\updates\\</code> e il programma ripulisce
i vecchi Setup/Portable lì. I file scaricati a mano in Download restano
affare tuo (Trova copie può proporli come «sicuri» da rimuovere).</p>
<p>Così si evita di aggiornare «l’altra» copia se sullo stesso PC ce ne sono due.
Consiglio: tienine una sola (Setup <em>oppure</em> Portable) e aggiorna quella.</p>
<p>L’Add-on si aggiorna dallo store NVDA o scaricando il file
<code>.nvda-addon</code> dalla release GitHub con tag <code>v…</code> (non <code>app-v…</code>).</p>
<p>Se sospetti di avere più copie (Installer vecchio + Portable in Download,
scorciatoie diverse, ecc.), vedi la sezione successiva.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="copie">12b. Trova altre copie sul PC (evitare doppioni)</h2>
<p>A volte sul computer restano più versioni: Setup in Program Files,
un vecchio Installer non disinstallato, una Portable in Download,
un exe di aggiornamento scaricato e aperto per sbaglio.
Il risultato tipico: si aprono due finestre o si aggiorna «la copia sbagliata».</p>
<p>Menu <strong>Strumenti</strong> → <strong>Trova altre copie sul PC…</strong>:</p>
<ol class="passi">
  <li>Il programma <strong>elenca</strong> (non cancella da solo) cosa trova:
    voci Installer nel Registro, exe tipici in Download/Desktop/Documenti/
    Program Files, scorciatoie sul Desktop che puntano a RTAD.</li>
  <li>Puoi <strong>salvare un rapporto</strong> sul Desktop
    (<code>RTAD_copie_trovate.txt</code>) da rileggere con calma.</li>
  <li>Se vuoi ripulire: «Rimuovi copie sicure» propone solo pacchetti
    <em>Setup / Portable</em> lasciati direttamente in Download o Desktop
    (i file scaricati per aggiornare).
    <strong>Non</strong> tocca l’Installer installato, né le cartelle
    di compilazione del progetto (<code>build</code> / <code>dist</code>),
    né le chiavi API in
    <code>%AppData%\\Roaming\\RTAD_Standalone</code>.
    Serve sempre il tuo consenso esplicito.</li>
  <li>Un Installer registrato in Windows si disinstalla da
    Impostazioni → App (o da «Disinstalla» nel rapporto), non in silenzio
    dal programma.</li>
</ol>
<div class="ok">
  <strong>Amico, non demone:</strong> all’avvio può avvisarti se sembra
  ci siano più copie confuse, e proporti di aprire questo strumento.
  Puoi declinare e, se vuoi, chiedere di non ripetere l’avviso.
  L’istanza unica (già dalla 1.7.4) evita una seconda finestra se il
  programma è già aperto; questo strumento aiuta a capire <em>quale</em>
  copia stai usando e a tenere pulito il PC.
</div>
<div class="note">
  Esiste anche lo script di supporto
  <code>tools/rtad_trova_copie.ps1</code> (stesso spirito: elenca;
  cancellazione solo con conferma). Utile se il programma non parte.
</div>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="scorciatoie">13. Scorciatoie principali (Standalone)</h2>
<ul>
  <li><kbd>Ctrl</kbd>+<kbd>H</kbd> / <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>H</kbd> — cronologia testi / percorsi, fino a 200, l’ultimo in cima</li>
  <li>Nel lettore: <kbd>Ctrl</kbd>+<kbd>B</kbd> aggiunge un punto di lettura, quanti ne vuoi.
    <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>B</kbd> torna all’ultimo. Invio sull’elenco sceglie. Non è Ctrl+D.</li>
  <li><kbd>Ctrl</kbd>+<kbd>F</kbd> — filtro risultati</li>
  <li><kbd>Alt</kbd>+<kbd>T</kbd> — tutto il PC</li>
  <li><kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>V</kbd> — Incolla dagli Appunti un file, un percorso o il testo di un messaggio</li>
  <li><kbd>Ctrl</kbd>+<kbd>U</kbd> — verifica aggiornamenti</li>
  <li><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>T</kbd> — Trascrivi e cerca…</li>
  <li><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>G</kbd> — Conversazioni Gemini</li>
  <li><kbd>Alt</kbd>+<kbd>B</kbd> — Conversazioni Gemini (finestra principale)</li>
  <li><kbd>Alt</kbd>+<kbd>Q</kbd> — Nuova conversazione Gemini, anche senza un file</li>
  <li><kbd>Alt</kbd>+<kbd>A</kbd> — Allega file: elenco per data, i più recenti in cima</li>
  <li>Strumenti → Confronta file…, anche nel menu del risultato.
    Nella finestra: Alt+A aggiunge, Alt+L toglie, anche prima di Invio.
    Canc sull’elenco toglie. Nella scelta: Shift+freccia giù,
    Control+freccia, Control+Spazio, Alt+C cambia cartella.
    Sotto, Alt+L toglie un file già scelto prima di Invio.
    Sulla finestra principale Alt+L resta la chiave Google.
    Nella scelta allegati di Gemini la lista sotto si chiama Allegati.
    Sulla conversazione, Alt+L toglie un allegato già messo.</li>
  <li><kbd>Shift</kbd>+<kbd>Invio</kbd> — nella domanda della chat, va a capo</li>
  <li><kbd>Alt</kbd>+<kbd>L</kbd> — Chiave Google Vision</li>
  <li><kbd>Alt</kbd>+<kbd>H</kbd> — Chiave Gemini</li>
  <li><kbd>Alt</kbd>+<kbd>G</kbd> — Segnalibri. Sul report o nel lettore: Chiedi a Gemini</li>
  <li><kbd>Alt</kbd>+<kbd>U</kbd> — Traduci il testo già aperto (report o lettore)</li>
  <li><kbd>Alt</kbd>+<kbd>F</kbd> — Apri la fonte selezionata</li>
  <li><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> / <kbd>L</kbd> — salva / carica profilo</li>
  <li><kbd>F4</kbd> / Spazio — anteprima vocale del risultato</li>
  <li><kbd>F7</kbd> — Nella Standalone, oppure Invio sulla voce, o un clic: mette in pausa la voce di RTAD. Spazio, F4 e gli esiti li dice NVDA. F7 di nuovo, oppure Invio sulla voce, o un clic, la riaccende. Nell'Add-on silenzia gli annunci di RTAD: la voce resta quella di NVDA.</li>
  <li><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>V</kbd> — Scegli voce, solo Standalone.
    Ci sono le voci di Windows (OneCore) e quelle SAPI.
    Invio sul pulsante OK, o un clic, imposta la voce.
    Doppio clic sulla riga fa la stessa cosa. Un clic solo seleziona la riga.
    Velocità e tono del menu valgono anche per le voci di Windows.</li>
  <li>Menu Voce, «Solo la voce di questo programma»: Invio sulla voce, o un clic.
    Dentro RTAD questa voce dice anche dove sei: la casella, il pulsante,
    la riga dell'elenco con le frecce, la casella combinata, la voce di menu, e il simbolo che scrivi. Con Alt e le frecce dice il menu: Menu File, Menu Segnalibri, Menu Cronologia, Menu Profili, Menu Voce, Menu Strumenti, Menu Aiuto. «Pronuncia i tasti di spostamento» è spento. Invio sulla voce, o un clic, lo accende: allora dice anche Tab, Shift Tab, Shift, Control, Control A, Alt, le frecce, Inizio, Fine, Pagina su, Pagina giù, Insert, Canc, Backspace, Esc, Invio, i tasti da F1 a F12, e il tastierino numerico. Blocca maiuscole e Num Lock dicono attivato o disattivato. Se esci con Alt+Tab, o con un clic fuori dalla finestra, oppure un comando apre un'altra finestra, la voce dice: Non sei nel programma? Tieni premuto Alt e premi Tab: lo ripete a ogni finestra. Quando Tab torna sul programma, dice dove eri. Lo ripete anche a ogni clic fuori, finché non torni. Stampa schermo, Blocco scorrimento e Pausa si dicono se arrivano al programma. Stampa schermo spesso resta a Windows. Con le frecce sul menu, insieme al nome dice la scorciatoia scritta accanto. Invio sulla voce, o un clic, esegue quel comando. F8, oppure menu Voce, Dove sei: Invio sulla voce, o un clic. Dice la finestra in primo piano e il controllo: pulsante, campo di testo, elenco. «Pronuncia le lettere mentre scrivi» è spento. Invio sulla voce, o un clic, lo accende. I simboli si dicono lo stesso: punto, virgola, punto interrogativo.
    Se NVDA è acceso, spegni il sintetizzatore con NVDA+S, altrimenti senti due voci. Se la spegni con Ctrl+Shift+S, oppure Invio sulla voce, o un clic, Spazio, F4 e gli esiti li dice NVDA. F7, oppure Invio sulla voce, o un clic, mette in pausa la voce di RTAD: quelle frasi le dice NVDA. F7 di nuovo, oppure Invio sulla voce, o un clic, la riaccende.
    Le domande del programma, come Sì e No e le copie sul PC, le dice questa voce: il testo, i pulsanti, e su quale sei. Se la finestra è già aperta, Ctrl+Shift+S accende la voce e legge la domanda. Invio sul pulsante, o un clic, risponde. Tab passa all'altro. Esc chiude e viene detto. Nel menu del tasto applicazioni, insieme al nome dice il posto, per esempio 1 di 15. Esc, uscendo da un menu, viene detto. Nella Standalone, Salva e Sfoglia sono finestre di RTAD, dall'elenco Unità. Alt+P legge lo stato: premuto due volte di seguito lo copia. Un clic sull'etichetta Stato porta allo stato. Nell'Add-on, Salva e Sfoglia restano le finestre di Windows. L'Add-on resta sulla voce di NVDA. Nell'Add-on, Salva e Sfoglia restano le finestre di Windows.</li>
  <li><kbd>F1</kbd> — Guida ai Comandi; Aiuto → Guida completa HTML</li>
  <li>Nella guida HTML: <kbd>Ctrl</kbd>+<kbd>F</kbd> oppure, con NVDA,
    <kbd>NVDA</kbd>+<kbd>Ctrl</kbd>+<kbd>F</kbd></li>
  <li><kbd>Alt</kbd>+<kbd>F4</kbd> / <kbd>Ctrl</kbd>+<kbd>Q</kbd> — esci</li>
  <li>Tasto Applicazioni — menu contestuale sui risultati</li>
</ul>
<p>Elenco più lungo: Aiuto → Guida ai Comandi.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="addon">14. Differenze con l’Add-on NVDA</h2>
<ul>
  <li>Voce e velocità seguono NVDA. Il Mute (F7) riguarda gli annunci RTAD.
    «Solo la voce di questo programma» è solo nella Standalone:
    Invio sulla voce del menu, o un clic.
    Nella Standalone, Salva e Sfoglia sono finestre di RTAD, dall'elenco Unità. Alt+P legge lo stato, due volte di seguito lo copia. Un clic sull'etichetta Stato porta allo stato.
    Nell'Add-on, Salva e Sfoglia restano le finestre di Windows.
    Su Solo Audio e Video, il campo per incollare l'URL aspetta 4 secondi, nella Standalone e nell'Add-on. Freccia su o freccia giù, prima, sceglie un altro tipo e il campo non si apre. Invio sul filtro già su Audio e Video lo apre subito.
    Nell'Add-on, se la finestra di ricerca resta aperta e ferma per alcuni minuti, al ritorno con Alt+Tab il focus torna su un campo.
    Nella Standalone, menu Voce, «Scegli voce»: Invio sulla voce, o un clic,
    oppure Ctrl+Shift+V. Ci sono le voci di Windows (OneCore) e quelle SAPI.
    Invio sul pulsante OK, o un clic, imposta la voce.
    Doppio clic sulla riga fa la stessa cosa. Un clic solo seleziona la riga.</li>
  <li>Niente menù contestuale nel registro di Esplora file.</li>
  <li>Scorciatoie tipiche NVDA (es. NVDA+Shift+G su figura/file, dove previsto).</li>
  <li>Installazione e aggiornamento tramite Gestore componenti aggiuntivi / DataStore.</li>
</ul>
<p>C’è anche la <strong>Guida pratica</strong> in linguaggio semplice
(Aiuto → Guida pratica), aggiornata a ogni versione.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="aiuto">15. Altre voci di Aiuto e supporto</h2>
<ul>
  <li>Aiuto → Guida pratica (ingresso semplice)</li>
  <li>Aiuto → Apri le guide: Invio sulla voce, o un clic, apre le guide sul web, la pagina con i due link. Non è una voce dello store NVDA.</li>
  <li>Aiuto → Guida ai Comandi / questa guida HTML</li>
  <li>Aiuto → Novità della Versione</li>
  <li>Pagina GitHub: <a href="{github_url}">{github_url}</a></li>
  <li>Sostieni il progetto: <a href="{donation_url}">{donation_url}</a></li>
</ul>

<footer>
  <p><strong>{app_title}</strong> v{app_version} — Maurizio Barra (Accesso Digitale)</p>
  <p>Documento generato dal programma. Per cercare: <kbd>Ctrl</kbd>+<kbd>F</kbd>
  (browser) oppure, con NVDA, <kbd>NVDA</kbd>+<kbd>Ctrl</kbd>+<kbd>F</kbd>.</p>
  <p class="top"><a href="#indice">↑ Torna all’indice</a></p>
</footer>

</body>
</html>
"""


def write_guida_html(path: str, **kwargs) -> str:
    """Scrive la guida su path e restituisce path. kwargs → build_guida_html."""
    html = build_guida_html(**kwargs)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
