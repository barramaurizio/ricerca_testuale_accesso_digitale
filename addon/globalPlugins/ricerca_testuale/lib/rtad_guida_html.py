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
      (anche <a href="#chat">conversazione sul file</a>)</li>
    <li><a href="#immagini">Descrivere immagini e «Tutto sull’immagine»</a></li>
    <li><a href="#media">Audio e video</a>
      (anche <a href="#media-ricerca">cercare parole nel parlato</a>)</li>
    <li><a href="#documenti">Documenti, PDF, Excel, lettore</a></li>
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
    <li><strong>Whisper sul mio PC:</strong> nell’analisi audio/video, insieme a
      «Trascrizione parlato», la casella «Sul mio PC (Whisper)» è spenta.
      Se la accendi, al primo uso scarica il modello e trascrive anche
      senza chiave Gemini. Un file fino a 20 minuti. In una cartella,
      fino a 5 file: «Whisper: 5 file su N. Non entrati: …».
      Il testo diventa <code>nome.rtad.txt</code> se accanto non c’era già.
      Se c’era, resta com’era. Un secondo avvio mentre lavora interrompe,
      a voce e a schermo: «Interruzione richiesta. Attendi la chiusura.»
      Gemini resta la trascrizione quando la casella è spenta.</li>
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
    (vedi <a href="#sfoglia">Sfoglia</a>). Oppure «Tutto il PC».</li>
  <li>Scrivi <strong>cosa</strong> cercare nel campo testo.</li>
  <li>(Facoltativo) Scegli il tipo di file: tutti, immagini, audio/video, documenti…</li>
  <li>Premi <strong>Avvia ricerca</strong> oppure Invio nel campo testo.</li>
</ol>
<p>Durante la ricerca puoi seguire lo stato (Alt+P, Tab o S). Esc annulla la ricerca
in corso senza chiudere il programma.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="sfoglia">4. Sfoglia: cartella o singolo file</h2>
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
<p>Solo Standalone: puoi anche <strong>trascinare</strong> un file o una cartella
sulla finestra del programma (stesso effetto). Dalla 1.7.6 il rilascio funziona
in qualunque punto della finestra (non solo sul titolo).</p>
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
si cercano solo eventuali file dati presenti sul disco.</p>
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
  <strong>Aprire un link.</strong> L’elenco Fonti e link non apre il browser
  con Invio né con il doppio clic. Per aprirne una: Tab fino al pulsante
  <strong>Apri fonte</strong>, poi Invio. Alt+F fa lo stesso, anche se sei
  sull’elenco. Finché non c’è un link, l’elenco dice
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
Il modello usato è Flash.</p>
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
  <li><strong>Tutto sull’audio/video</strong>: scheda tecnica, riassunto, trascrizione
    (opt-in, con Gemini). «Sul mio PC (Whisper)» è un’altra casella, spenta:
    al primo uso scarica il modello e trascrive senza chiave Gemini,
    un file fino a 20 minuti, in una cartella fino a 5 file.
    La casella «Traduci la trascrizione» è spenta:
    se la accendi, sotto la trascrizione compare la traduzione,
    con gli stessi timestamp. Salva testo propone lo stesso
    <code>nome.rtad.txt</code>: sovrascrivendo, l’originale resta
    e la traduzione si aggiunge sotto.</li>
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
  <strong>Differenza utile:</strong> sul <em>nome file</em> di un video
  la ricerca può funzionare subito (come per qualsiasi file).
  Sul <em>contenuto parlato</em> serve il <code>.rtad.txt</code>.
  I report «orfani» (testo senza il media gemello nella stessa cartella)
  restano cercabili con il filtro Solo Audio/Video.
</div>
<p>Per scaricare da URL (YouTube e simili) serve <strong>yt-dlp</strong> aggiornato;
il programma può segnalarlo e proporti l’aggiornamento.</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="documenti">10. Documenti, PDF, Excel, lettore</h2>
<ul>
  <li>PDF con testo, Word, EPUB, HTML, testo, Excel <code>.xlsx</code>: ricerca nel contenuto.</li>
  <li><strong>Leggi documento…</strong> / lettore interno: cerca e titoli, dove supportato.</li>
  <li>PDF solo immagine (scansione): usa Descrivi / OCR come per le immagini.</li>
  <li>Su risultato Excel: Invio può aprire Excel alla riga del risultato.</li>
</ul>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="explorer">11. Menù contestuale di Esplora file (solo Standalone)</h2>
<p>Dopo l’installazione con Setup, sul tasto destro (o tasto Applicazioni)
appare <strong>Cerca con Accesso Digitale</strong>:</p>
<ul>
  <li>su <strong>cartelle</strong>: cerca in quella cartella; batch immagini o audio/video;</li>
  <li>su <strong>immagini</strong>: Apri/analizza, Descrivi, OCR, etichette, scheda, Chiedi a Gemini…;</li>
  <li>su <strong>audio/video</strong>: Apri/analizza, Tutto sull’AV, scheda, Chiedi a Gemini…;</li>
  <li>su <strong>documenti/PDF/xlsx</strong>: Apri, Leggi testo, Copia testo, Chiedi a Gemini…</li>
</ul>
<p>Se il programma è già aperto, il comando arriva alla finestra esistente
(niente seconda copia dispersiva).</p>
<p class="note">L’Add-on NVDA non scrive voci nel registro di Windows:
usa le scorciatoie NVDA (es. NVDA+Shift+G dove previsto) e i menu dell’Add-on.</p>
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
  <li><kbd>Ctrl</kbd>+<kbd>H</kbd> / <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>H</kbd> — cronologia testi / percorsi</li>
  <li><kbd>Ctrl</kbd>+<kbd>F</kbd> — filtro risultati</li>
  <li><kbd>Alt</kbd>+<kbd>T</kbd> — tutto il PC</li>
  <li><kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>V</kbd> — Incolla percorso dagli Appunti</li>
  <li><kbd>Ctrl</kbd>+<kbd>U</kbd> — verifica aggiornamenti</li>
  <li><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>T</kbd> — Trascrivi e cerca…</li>
  <li><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>G</kbd> — Conversazioni Gemini</li>
  <li><kbd>Alt</kbd>+<kbd>B</kbd> — Conversazioni Gemini (finestra principale)</li>
  <li><kbd>Alt</kbd>+<kbd>Q</kbd> — Nuova conversazione Gemini, anche senza un file</li>
  <li><kbd>Alt</kbd>+<kbd>A</kbd> — Allega file: elenco per data, i più recenti in cima</li>
  <li><kbd>Shift</kbd>+<kbd>Invio</kbd> — nella domanda della chat, va a capo</li>
  <li><kbd>Alt</kbd>+<kbd>L</kbd> — Chiave Google Vision</li>
  <li><kbd>Alt</kbd>+<kbd>H</kbd> — Chiave Gemini</li>
  <li><kbd>Alt</kbd>+<kbd>G</kbd> — Segnalibri. Sul report o nel lettore: Chiedi a Gemini</li>
  <li><kbd>Alt</kbd>+<kbd>U</kbd> — Traduci il testo già aperto (report o lettore)</li>
  <li><kbd>Alt</kbd>+<kbd>F</kbd> — Apri la fonte selezionata</li>
  <li><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> / <kbd>L</kbd> — salva / carica profilo</li>
  <li><kbd>F4</kbd> / Spazio — anteprima vocale del risultato</li>
  <li><kbd>F7</kbd> — Mute</li>
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
  <li>Voce e velocità seguono NVDA; c’è comunque il Mute (F7) per gli annunci RTAD.</li>
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
