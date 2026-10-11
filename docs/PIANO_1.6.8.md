# Piano RTAD 1.6.8 — chiusura rilascio

**Ultima pubblicata:** `1.6.7` (GitHub Add-on `v1.6.7` + Standalone `app-v1.6.7`; DataStore #12099 → #12100, 10/10/2026).  
**Non hotfixare 1.6.7.**  
**Stato 11/10/2026:** codice + docs 1.6.8 pronti al rilascio (C1+C2 + A documenti; B/B0 → 1.6.9).  
Vedi `docs/NOTE_RILASCIO_1.6.8.txt`.

---

## Obiettivo 1.6.8

Tre filoni (ordine di lavoro consigliato sotto):

1. **Formattazione / struttura documenti** (attesa da tempo)  
2. **Completamenti media** (dopo MVP 1.6.7)  
3. **UX da feedback** (salvataggi intelligenti)

Valutare in corso se il pacchetto è già “sufficiente” per rilasciare, o se aggiungere altro piccolo polish.

---

## A — Formattazione documenti (priorità alta, “da tempo”)

**Problema:** Word/Acrobat espongono struttura; molte app e RTAD oggi leggono soprattutto testo piano. Mancano link, capitoli/TOC, titoli, gerarchia utile a chi usa screen reader.

**Direzione 1.6.8 (MVP lettore strutturato):**

- Per **PDF** e/o **DOCX** (e se fattibile EPUB già in casa):  
  - titoli / outline / TOC se presenti  
  - link (testo + destinazione)  
  - struttura navigabile oltre al “muro di testo”  
- Flusso accessibile in SA + Add-on (gemello dove ha senso)  
- Limiti chiari se il file non ha struttura (messaggio onesto)

*Fuori da 1.6.8 se troppo grosso:* stampa/export fancy, OneCore native, rifacimento totale del visualizzatore.

---

## B — Completamenti media (post 1.6.7)

Da roadmap + uso reale:

- Polish rimanenti audio/video se emergono bug  
- Eventuale batch cartella media (solo se tempo; altrimenti 1.6.9)  
- **Non** Whisper di massa / scansione tutto il PC  

### B0 — Feedback 10/10/2026 sera: ricerca *dentro* audio/video (parole dette)

**Oggi (1.6.7):** **no.** Con filtro «Solo Audio e Video» si apre l’hub analisi (scheda/riassunto/trascrizione *su un file o URL*), non una ricerca full-text nel parlato. Con estensione personalizzata `.mp4` (o filtro media + parola chiave) RTAD include i file e può fare match sul **nome file / percorso**; **non** trascrive né cerca nel contenuto audio/video. Dubbio di Maurizio: corretto.

**Perché non è banale:** ogni file richiederebbe ASR (Gemini File API e/o Whisper locale) → tempo, costo API, limiti durata/size, cache dei transcript, abort, progresso. Non è lo stesso flusso di OCR sulle immagini.

**Direzione (candidata 1.6.8 se fattibile a pezzi, altrimenti 1.6.9):**

1. **MVP opt-in:** a fine (o durante) ricerca su file media, cerca solo in transcript **già in cache** (es. `.rtad.txt` / cache media da «Tutto sull’audio/video»). Zero costo se l’utente ha già analizzato.  
2. **Poi (più grosso):** «Trascrivi e cerca» opt-in su cartella/selezione (limiti chiari, Gemini), hit con snippet + timestamp se disponibili.  
3. Whisper locale bundlato = ancora più avanti / opt-in pesante.

Valutare in chat 1.6.8 se (1) entra nel taglio insieme a formattazione documenti, o se (1)+(2) = pezzo da solo dopo.

Già fatto in 1.6.7 (non rifare): hub URL, File API ~2 GB/3 h, ripresa trascrizione, ffprobe, Salva testo, avanzamento gauge/Alt+S, sidecar Titolo/ID/URL, ffmpeg/mux.

---

## C — Feedback UX (10/10/2026) — da fare in 1.6.8

### C1 — Salva report audio/video (Maurizio)

- Ricordare **ultima cartella** di salvataggio report media (`settings.json`, come altri path).  
- **Nome file** riconducibile all’originale:  
  - file locale → `{stem}.rtad.txt`  
  - temp da URL → titolo sorgente (sidecar) o ID YouTube / basename sensato  
- Dialogo Salva resta; defaultDir = ultima cartella o cartella del media locale.

### C2 — Auto-salvataggio risultati a fine ricerca (utente)

- Casella in **Impostazioni** (non solo al momento del salvataggio):  
  «Salva automaticamente i risultati a fine ricerca».  
- Opzionale: cartella destinazione / riuso ultima cartella export.  
- A ricerca **completata**: file con elenco come in lista (stesso spirito dell’export attuale).  
- Nome es. `RTAD_risultati_YYYYMMDD_HHMM_<query>.txt`.  
- Se chiude a metà: al massimo parziali (già c’è filo); focus = salvataggio a fine completa.  
- Messaggio di stato: «Risultati salvati in …» (utile).

---

## Ordine di lavoro suggerito

1. Bump etichette → `1.6.8`  
2. **C1 + C2** (veloci, alto valore, chiudono feedback)  
3. **A** formattazione documenti (nucleo della release)  
4. **B** solo polish media necessari / batch se resta tempo  
5. Docs + gemelli + `make_addon` + check pre-rilascio

---

## Criterio “abbastanza per pubblicare”

Minimo sensato:

- C1 + C2 fatti  
- A con almeno un percorso solido (es. DOCX outline/link **oppure** PDF TOC/link) usabile in SA e Add-on  
- Documentazione IT/EN + guida aggiornate  

Se A richiede più cicli, si può:  
- **1.6.8** = C1+C2 + primo mattone struttura documenti  
- **1.6.9** = approfondimento struttura + batch media  

Decisione in chat 1.6.8 con Maurizio.

---

## Fuori scope (lista d’attesa)

- Whisper locale bundlato / ricerca transcript di massa  
- OneCore native  
- Canale YouTube Accesso Digitale (chat dedicata)  
- Hotfix 1.6.7  

---

## Riferimenti file

- Roadmap: `docs/ROADMAP_DOPO_1.5.0.md` (Fase O)  
- Contesto: `docs/NOTE_CONTESTO_v1.5.md`  
- Note rilascio 1.6.7 (storico): `docs/NOTE_RILASCIO_1.6.7.txt`  
- Regola pre-rilascio: `.cursor/rules/rtad-pre-release-check.mdc`  

---

*Aggiornato 10/10/2026 dopo feedback Maurizio + pubblicazione 1.6.7.*
