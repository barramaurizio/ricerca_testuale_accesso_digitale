# Piano RTAD 1.7.0

**Ultima pubblicata:** `1.6.9` (GitHub + DataStore #12149 → #12150, Store OK).  
**Lavoro corrente:** `1.7.0` — **pronta al rilascio** (13/10/2026): lettore + spazi PDF + toast.  
Vedi `docs/NOTE_RILASCIO_1.7.0.txt` e `docs/ROADMAP_DOPO_1.5.0.md` (Fase Q).

---

## Perché 1.7.0 e non 1.6.10

Dopo TOC PDF, app predefinita, escamotage Acrobat/NVDA e titoli lunghi media, il pezzo «documenti strutturati» è maturo.  
Il salto a **1.7** segnala un nuovo pacchetto di prodotto (come da accordo versionamento), non un hotfix.

---

## Priorità proposte (ordine consigliato)

### P0 — Lucidature post-1.6.9 (snelle, alto valore)

1. ~~**Toast «Ricerca completata»**~~ — toast breve (non reminder); se lettore documento aperto → solo annuncio. *(in corso 1.7.0)*  
2. ~~**Spazi nel testo PDF**~~ — gap TJ → spazio; de-glue titoli TOC; soft camelCase (`Batteriainterna` / `HelloWorld`). *(in corso 1.7.0)*  
3. **Secondo salto pagina Acrobat** (opzionale) — se il file è già aperto/preparato, riprovare `/A page=` senza chiudere a mano.  
4. Feedback Store / issue urgenti → entrano qui se arrivano.

### P1 — Completare liste lasciate indietro

1. **Batch cartella media** (da 1.6.8/1.6.9).  
2. **B0 MVP:** ricerca mirata su `.rtad.txt` / cache transcript già presenti (oltre al workflow già documentato).  
3. Piccoli allineamenti SA ↔ Add-on emersi nei test Predator/Samsung.

### P2 — Esperienza «Leggi documento» (senza lettore PDF completo)

1. UX sommario più chiara (pagina PDF già in lista; messaggi se corpo non estraibile).  
2. Guida / WhatsNew: tenere aggiornati gli escamotage Acrobat (Preferenze → Lettura, ecc.).  
3. Eventuale ODT / `.doc` legacy — solo se richiesto e fattibile senza derivare.

### P3 — Lettore documenti interno RTAD (innovazione)

Obiettivo: **viewer accessibile** (testo + struttura + navigazione titoli) per PDF/DOCX/EPUB *dentro* RTAD, riducendo dipendenza da Acrobat per NVDA.

**MVP 1.7.0 (avviato):** evoluzione di `DocumentStructureFrame` → «Lettore documento»:

- ~~Titolo finestra / messaggio guida~~  
- ~~Cerca nel testo (Ctrl+F, F3 / Shift+F3, pulsante)~~  
- ~~Titolo successivo/precedente (Ctrl+H / Ctrl+Shift+H) su marcatori `[Hn]`~~  
- ~~Pulsante «Apri file esterno» (secondario)~~  
- Poi: toast che non ruba focus; eventuale Invio = solo RTAD + Ctrl+Invio = esterno; reflow/bookmark.

**Fuori MVP iniziale:** motore PDF completo tipo Sumatra/Acrobat, annotazioni, form, stampa avanzata.

---

## Cosa NON mettere in 1.7.0 di default

- Whisper / trascrizione ML di massa  
- OCR pesante bundlato nell’Add-on  
- Scansione «tutto il PC» con vision senza opt-in  
- Lettore PDF “completo” grafico come prodotto 1.7 intero  

---

## Criterio “1.7.0 pronta”

- Almeno **P0** chiusa + **un pezzo P1** (o due P0 sostanziosi).  
- Oppure un pezzo P2/P3 MVP chiaro e testato su SA + Add-on.  
- Stesso workflow: SA → Add-on → `compila` / `make_addon` → tag `v1.7.0` + `app-v1.7.0`.

---

## Nuova chat

Aprire chat **«RTAD 1.7.0»** su questo progetto; partire da questo file + roadmap.

---

*Creato 12/10/2026 dopo pubblicazione 1.6.9.*
