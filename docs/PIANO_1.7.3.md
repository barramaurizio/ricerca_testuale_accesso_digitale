# Piano RTAD 1.7.3

**Ultima pubblicata:** `1.7.2` (batch media + B0 + glossario).  
**In rilascio:** `1.7.3` (sidecar stem + Excel `.xlsx` + «Trascrivi e cerca»).  
**Non hotfixare 1.7.2.** Vedi anche `docs/ROADMAP_DOPO_1.5.0.md` e `docs/NOTE_CONTESTO_v1.5.md`.

**Stato (16/10/2026):** codice + novità + bump `1.7.3` pronti; UI Maurizio OK.
Guida HTML completa → **1.7.4**. Restano install Add-on / `compila.bat` / Inno / GitHub.

---

## Priorità (ordine consigliato)

### P0 — Sidecar stem locale (+ P1 orfani Solo AV)

Feedback Juve/cross 16/10.

1. **Stem locale:** «Salva testo…» / default nome `.rtad.txt` per file **locale**
   usa lo stem del file sul disco (`partita_juve.mp4` → `partita_juve.rtad.txt`),
   non il titolo YouTube inglese del sidecar sorgente.
2. **URL / temp:** resta titolo/ID sidecar quando il media è scarico temp da URL
   (nessun nome locale sensato).
3. **P1 orfani:** con filtro «Solo Audio e Video», cercare anche nei `.rtad.txt`
   già presenti nella cartella anche se non c’è (più) il media gemello, o se
   il nome del report non coincide con lo stem del media (es. salvato con
   titolo EN). Hit `[AV]` con snippet/timestamp come B0.
4. Gemello SA ↔ Add-on (`report_save_stem_for_path` + percorso ricerca B0).

### P0 — Excel `.xlsx` (ricerca nel contenuto)

Feedback papà / elenco PVR Salotto 16/10 — **appena possibile** dopo (o in
parallelo stretto a) lo stem sidecar.

1. Inclusione `.xlsx` in documenti / ricerca contenuto (come `.docx`).
2. Estrazione testo celle (fogli + sharedStrings) senza dipendenza pesante
   se possibile (ZIP OOXML, stile già usato per DOCX).
3. Hit con foglio / riga se fattibile in modo semplice; almeno snippet utile.
4. Gemello SA ↔ Add-on; etichette filtro «Solo Documenti» aggiornate.
5. `.xls` binario (OLE) = fuori scope salvo se banale; non bloccare `.xlsx`.

### P1 — «Trascrivi e cerca»

Già in roadmap media (`PIANO_1.6.8` B0 punto 2; rimandato da 1.7.2).

1. Opt-in su cartella/selezione: trascrivi (Gemini) i media senza sidecar,
   poi cerca i termini → hit con snippet + timestamp se disponibili.
2. Limiti chiari (costo/tempo/abort); riuso batch + B0 dove possibile.
3. Non sostituisce Whisper di massa (resta fuori / dopo).

### P2 — Opzionali (solo se tempo / campione)

1. **PDF papà:** solo se arriva campione “strano” e fix mirato.
2. Scheletro guida HTML Vision/Gemini (IT) — altrimenti tutto in **1.7.4**.

---

## Cosa NON mettere in 1.7.3 di default

- Guida HTML completa cercabile (Vision/Gemini passo-passo) → **1.7.4**  
- Whisper / trascrizione ML di massa  
- PDF criptati  
- OneCore native (voce)

---

## Criterio “1.7.3 pronta”

- P0 stem: salva da media locale → nome = stem file; URL temp → titolo/ID.  
- P0/P1 orfani: Solo AV trova parole anche in `.rtad.txt` “orfani”.  
- P0 xlsx: ricerca trova testo in un foglio di esempio.  
- «Trascrivi e cerca» testato SA (+ gemello Add-on).  
- Guida novità / WhatsNew / NOTE_RILASCIO / bump `1.7.3` (guida lunga → 1.7.4).  
- Workflow: bump → SA → Add-on → `compila` / `make_addon` → tag `v1.7.3` + `app-v1.7.3`.

---

## Nuova chat

Chat **«RTAD 1.7.3»**; partire da questo file + `docs/NOTE_CONTESTO_v1.5.md`.

---

*Creato 16/10/2026.*
