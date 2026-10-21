# Piano RTAD 1.8.0

**Ultima pubblicata:** `1.7.7` — OCR tabelle riga-per-riga (cache v20) + Add-on OCR.  
GitHub `v1.7.7` / `app-v1.7.7`; DataStore #12333 → #12334 (accepted 20/10/2026). Feedback papà: OK.  
**Questa versione:** `1.8.0`. **Non hotfixare 1.7.7.**

Vedi `docs/ROADMAP_DOPO_1.5.0.md` e `docs/NOTE_CONTESTO_v1.5.md`.

---

## Spirito della 1.8.0

Minor corposa: dopo un’analisi o una ricerca, si può **conversare con Gemini
sul quel file**. Domande, approfondimenti, più scambi. Vale per immagini,
audio/video, PDF, documenti, fogli, testo, email: tutto ciò che RTAD sa già
leggere.

Non è una chat vuota «chiedi qualsiasi cosa». Il centro resta il file.
Cursor resta lo strumento di sviluppo, non il motore dentro RTAD.

Tutto questo entra **in 1.8.0**. L’ordine sotto è l’ordine di lavoro e di
prova, non una lista da spezzare su più versioni.

---

## Cosa ha chiesto Maurizio (21/10/2026)

1. Conversare e approfondire a partire da ciò che Gemini (o RTAD) ha già visto.
2. Stessa possibilità su **tutti** i file cercati o analizzati, non solo immagini e audio/video.
3. Cronologia delle conversazioni.
4. Salvare e stampare le chat.
5. Fonti recenti; se serve, consultazione web in tempo reale.
6. Il modello deve sapere **che giorno è** e le date del file che sta guardando.
7. Ogni idea utile per ottenere il massimo, con prove fatte insieme.

---

## Come funziona (decisioni)

### Un dialogo, ancorato al file

Voce **«Chiedi a Gemini…»** da:

- report «Tutto sull’immagine» e «Tutto sull’audio/video»;
- lettore documento;
- menù sul risultato di ricerca (il file trovato, non la ricerca intera).

La ricerca **non** chiama Gemini da sola. Si apre la conversazione sul file
scelto. Se RTAD non ha ancora testo (PDF scansione senza OCR, audio senza
trascrizione), prima si propone l’analisi già esistente, poi la chat.

### Cosa vede Gemini, per tipo

| Tipo | Contesto inviato |
|------|------------------|
| Immagine | L’immagine, a ogni scambio, più OCR e descrizione già prodotti |
| Audio/video | Scheda tecnica + trascrizione con orari. Il file si riallega solo se la trascrizione manca e la domanda non si può fare sul testo |
| PDF, DOCX, EPUB, XLSX, TXT, email | Testo già estratto da RTAD, più titoli/pagine se ci sono |

Documento lungo: si manda un pacchetto ampio (tetto generoso, nell’ordine
delle decine di migliaia di caratteri) con sommario se esiste. Se la domanda
indica una pagina o un titolo fuori da quel pacchetto, RTAD estrae quel pezzo
in locale e lo aggiunge a quello scambio. Non si rimanda l’intero binario a
ogni domanda.

Due piani, sempre visibili nella risposta quando servono:

- **Nel file** — solo ciò che è nel materiale RTAD.
- **Approfondimento** — solo se è stata usata la consultazione web, con i link.

Se un dato non c’è, la risposta lo dice. Non si inventano citazioni.

### Tempo e web

Ogni richiesta porta la **data e l’ora di oggi** e le date già note del file
(nome, modifica, data documento, data nell’OCR). Stessa cautela già usata
sulle immagini: se nel file c’è una data, quella del file vince su un anno
preso da un articolo.

Checkbox **«Consulta anche il web»**, ricordata, **accesa la prima volta**,
con un avviso chiaro: le domande e gli estratti del file vanno a Google;
la cronologia resta sul PC. Il modello usa il web quando la domanda esce
dal file (persone, «è ancora così», notizie, date da verificare), non per
riscrivere ciò che il file già dice. Si spenge quando non serve.

Strumento: Google Search sul `generateContent` già usato. Il nome esatto
del tool si verifica in implementazione (`google_search`). Niente
`temperature`, niente `top_p` / `top_k`, niente migrazione a Interactions API.

### Cronologia, salva, stampa

- Cronologia **sul PC**, per file (si riapre «Continua la conversazione»).
- Elenco delle chat di quel file: riapri, nuova, elimina.
- Tetto (circa 50 conversazioni o una dimensione massima): oltre, si avvisa
  e si tiene le più recenti.
- Nella chat **non** si salva la chiave API.
- **Copia**, **Salva testo…** e **Stampa testo…** come nei report già
  esistenti: testo piano, intestazione con nome file, data, ora, modello.
  Stampa verso la stampante predefinita (anche «Microsoft Print to PDF»).

### Accessibilità

Un solo dialogo:

- cronologia in sola lettura, frecce per leggere, annuncio della risposta nuova;
- campo domanda e Invia;
- Esc annulla la richiesta in corso (come le analisi lunghe);
- domande pronte, gratuite, scelte in base al tipo di file
  (riassumi, cosa c’è scritto, i passaggi con orario, i punti principali,
  questa data è coerente con oggi);
- avanzamento parlato, niente finestra che ruba il focus al lettore.

Lingua della risposta: quella della domanda; se la domanda è in italiano,
italiano.

### Motore

Nuovo modulo gemello `rtad_chat.py` (SA e, a SA provata, Add-on).
Chiamata multi-turno: l’API non ricorda nulla da sola; RTAD rimanda
lo storico `user` / `model` più il contesto del file.
Stessi modelli e lo stesso fallback già in `rtad_ocr.py` / `rtad_media.py`.
Chiave Gemini personale, opt-in, invariata.

---

## Ordine di lavoro (tutto in 1.8.0)

### P0 — Dialogo su immagine e su documento di testo

Contesto, più scambi, annulla, domande pronte, data di oggi.
Prova: una foto già descritta e un PDF/DOCX di testo.

**Codice SA 21/10:** dialogo pronto su immagine, lettore documento e report
audio/video (sul testo già prodotto). Cronologia sul PC, copia, salva, stampa,
web con checkbox. Smoke senza rete: `python tools/_smoke_chat_context.py` (PASS).
Gemello `rtad_chat.py` copiato nell’Add-on; la voce nell’Add-on arriva dopo la prova SA.
Manca ancora «Chiedi a Gemini» dal menù di un risultato di ricerca.

### P1 — Audio/video e risultato di ricerca

Trascrizione come contesto; menù «Chiedi a Gemini…» sul risultato.
Prova: un media con `.rtad.txt` e un hit di ricerca su PDF/email.

### P2 — Cronologia, salva, stampa

Riapri la stessa chat dopo aver chiuso RTAD. Salva un `.txt`. Stampa
(o Print to PDF) e rileggi l’intestazione.

### P3 — Web e date del file

Checkbox web, risposte con link, spegnimento della checkbox.
Prova con una domanda che **non** è nel file («è ancora attuale?»)
e una che **è** nel file (non deve andare a cercare fuori per riscriverla).

### P4 — Guida e novità

Guida pratica, novità IT/EN, bump `1.8.0` solo a funzione provata.
Add-on gemello dopo la SA.

---

## Cosa non entra in 1.8.0

- Chat senza alcun file aperto o scelto.
- Una conversazione sola su **più file** («confronta questi tre»):
  candidata alla versione successiva, se 1.8.0 regge all’uso.
- Chiamare Gemini su ogni file della ricerca.
- Whisper, modelli bundlati, major 2.0.

`1.7.8` solo se arriva un bug sulla 1.7.7. Non si riempie per arrivare a 1.8.

---

## Criterio “1.8.0 pronta”

Prove Maurizio 21/10/2026: SA (documento, immagine, video, URL) e Add-on (file locale e URL). Guide e bump nello stesso giorno. Non ancora su GitHub.

- [x] Immagine: più domande di seguito, Gemini rivede l’immagine e l’analisi già fatta
- [x] PDF/DOCX/EPUB/XLSX/TXT/email: domande sul testo estratto; pagina o titolo fuori pacchetto recuperati in locale
- [x] Audio/video: domande sulla trascrizione (orari citabili)
- [x] Risultato di ricerca: si apre la chat su quel file, senza scansione di massa
- [x] Data di oggi presente nel contesto; data nel file non sostituita da una data web
- [x] Web acceso: link in «Approfondimento»; web spento: niente consultazione esterna
- [x] Cronologia riaperta a RTAD chiuso e riaperto; chiave API assente dal file salvato
- [x] Copia, salva, stampa (testo piano, intestazione)
- [x] Esc annulla; dialogo usabile solo con tastiera e NVDA
- [x] Guida / novità / gemello / bump `1.8.0`

---

## Prove insieme (Maurizio)

1. Foto già analizzata: seconda e terza domanda, non solo la prima descrizione.
2. PDF di testo lungo: domanda su una pagina non all’inizio.
3. PDF scansione: la chat parte dopo l’OCR, non al posto dell’OCR.
4. Video con trascrizione: «a che minuto si parla di …».
5. Risultato di una ricerca normale: «Chiedi a Gemini» su quel hit.
6. Chiudi RTAD, riapri, la chat c’è ancora. Salva e stampa.
7. Una domanda da web e una domanda che deve restare nel file.
8. Stessa prova essenziale sull’Add-on, dopo la SA.

---

## Nuova chat

Titolo: **«RTAD 1.8.0»**  
Prompt:  
«leggere NOTE_CONTESTO + PIANO_1.8.0; partire da P0 dialogo Gemini su immagine e documento»

---

*Creato 21/10/2026 (dopo 1.7.7 pubblicata e feedback papà OK). Ambito concordato in chat con Maurizio.*
