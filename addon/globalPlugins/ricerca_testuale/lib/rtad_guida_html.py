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
    <li><a href="#sfoglia">Sfoglia: cartella o singolo file</a></li>
    <li><a href="#ocr">Testo nelle immagini (OCR)</a></li>
    <li><a href="#vision">Chiave API Google Cloud Vision (passo-passo)</a></li>
    <li><a href="#gemini">Chiave API Gemini / Google AI Studio (passo-passo)</a></li>
    <li><a href="#immagini">Descrivere immagini e «Tutto sull’immagine»</a></li>
    <li><a href="#media">Audio e video</a></li>
    <li><a href="#documenti">Documenti, PDF, Excel, lettore</a></li>
    <li><a href="#explorer">Menù contestuale di Esplora file (solo Standalone)</a></li>
    <li><a href="#aggiornamenti">Aggiornamenti: Installer e Portable</a></li>
    <li><a href="#scorciatoie">Scorciatoie principali</a></li>
    <li><a href="#addon">Differenze con l’Add-on NVDA</a></li>
    <li><a href="#aiuto">Altre voci di Aiuto e supporto</a></li>
  </ol>
</nav>

<div class="box" id="novita">
  <h2 style="margin-top:0;">1. Novità di questa versione ({app_version})</h2>
  <ul>
    <li><strong>Aggiornamenti più chiari:</strong> se usi l’Installer (Setup),
      il programma propone il file Setup; se usi la Portable, propone la Portable.
      Non scarica più «il primo exe» a caso.</li>
    <li><strong>Menù contestuale Esplora file:</strong> la voce «Apri / analizza…»
      apre davvero quel file (immagine, audio/video o documento), non solo la finestra vuota.</li>
    <li><strong>Una sola finestra:</strong> se il programma è già aperto, il tasto destro
      gli passa il file invece di aprirne un’altra copia.</li>
    <li><strong>Sfoglia → Singolo file:</strong> puoi scegliere qualsiasi tipo
      (documenti, immagini, audio/video, …) e, se vuoi, aprirlo subito per l’analisi.</li>
    <li><strong>Questa guida HTML:</strong> indice, cercabile, con procedure complete
      per le chiavi Vision e Gemini.</li>
  </ul>
  <p class="top"><a href="#indice">↑ Torna all’indice</a></p>
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
<p>Puoi anche <strong>incollare un percorso</strong> (testo) nel campo percorso
con Ctrl+V, se l’hai copiato da Esplora file («Copia come percorso»).</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="ocr">5. Testo nelle immagini (OCR)</h2>
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
audio/video (funzioni che usano Gemini).</p>

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
    (opt-in, con Gemini).</li>
  <li>Batch cartella: analizza più file e salva i report <code>.rtad.txt</code> accanto.</li>
  <li><strong>Trascrivi e cerca…</strong> (Ctrl+Shift+T): cerca parole nel parlato
    usando i report già fatti, oppure trascrive con Gemini (limite per sessione).</li>
  <li>Con filtro «Solo Audio e Video» trovi anche i <code>.rtad.txt</code> «orfani».</li>
</ul>
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
  <li>su <strong>immagini</strong>: Apri/analizza, Descrivi, OCR, etichette, scheda…;</li>
  <li>su <strong>audio/video</strong>: Apri/analizza, Tutto sull’AV, scheda…;</li>
  <li>su <strong>documenti/PDF/xlsx</strong>: Apri, Leggi testo, Copia testo…</li>
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
<p>Così si evita di aggiornare «l’altra» copia se sullo stesso PC ce ne sono due.
Consiglio: tienine una sola (Setup <em>oppure</em> Portable) e aggiorna quella.</p>
<p>L’Add-on si aggiorna dallo store NVDA o scaricando il file
<code>.nvda-addon</code> dalla release GitHub con tag <code>v…</code> (non <code>app-v…</code>).</p>
<p class="top"><a href="#indice">↑ Indice</a></p>

<h2 id="scorciatoie">13. Scorciatoie principali (Standalone)</h2>
<ul>
  <li><kbd>Ctrl</kbd>+<kbd>H</kbd> / <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>H</kbd> — cronologia testi / percorsi</li>
  <li><kbd>Ctrl</kbd>+<kbd>F</kbd> — filtro risultati</li>
  <li><kbd>Alt</kbd>+<kbd>T</kbd> — tutto il PC</li>
  <li><kbd>Ctrl</kbd>+<kbd>U</kbd> — verifica aggiornamenti</li>
  <li><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>T</kbd> — Trascrivi e cerca…</li>
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
