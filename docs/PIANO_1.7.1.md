# Piano RTAD 1.7.1

**Ultima pubblicata:** `1.7.0` (GitHub `v1.7.0` + `app-v1.7.0`, DataStore #12178 → #12179, Store OK).  
**Lavoro corrente:** `1.7.1` (patch dopo lettore/spazi/toast).  
**Non hotfixare 1.7.0.** Vedi anche `docs/ROADMAP_DOPO_1.5.0.md`.

**Stato (14/10/2026):** **pronta al rilascio** — bump `1.7.1`, gemelli OK, guida/WhatsNew/NOTE OK, pacchetto `.nvda-addon` fresco. Resta: install Add-on + `compila.bat` / F9 + tag GitHub.

---

## Priorità proposte (ordine consigliato)

### P0 — PDF scansione / «Descrivi immagine da PDF» (feedback 13/10/2026)

Caso tipico: foglio scannerizzato → PDF senza testo (0 caratteri, 1+ immagini pagina), es. fattura Caffemania.  
RTAD lo tratta correttamente come **immagine da PDF**, non come PDF testuale. Tenere questa linea.

**Già presenti** (non reinventare): Copia testo, Salva testo…, Salva/Copia immagine nel dialogo report.  
**In codice 1.7.1 (da testare):**

1. ~~**Nome file al salvataggio testo**~~ — `source_path` = PDF originale → stem  
   (es. `Caffemania….rtad.txt`), non `rtad_pdf_….jpg`.  
2. ~~**Cartella default**~~ — cartella del PDF originale.  
3. ~~**Stampa testo**~~ — pulsante «Stampa testo…» sul report (Notepad `/p`; Print to PDF di sistema).  
4. ~~**UX onesta**~~ — «Leggi documento» su PDF 0 testo + immagini → dialogo  
   Descrivi / Apri lettore.  
5. **Opzionale:** «Esporta descrizione come PDF» solo se la stampa non basta — **fuori**.

Campione locale (Maurizio):  
`D:\Documenti\Ricevute\Caffemania bonifico effettuato Giovedì 24-09-2026.pdf`

### P1 — Liste lasciate da 1.7.0

1. ~~Focus freccia nel lettore dopo iconizza~~ — Raise + caret kick (da verificare a mano).  
2. Batch cartella media — **rimandato** (1.7.2+).  
3. B0 MVP: ricerca mirata su `.rtad.txt` / cache transcript — **rimandato**.  
4. Piccoli allineamenti SA ↔ Add-on dai test.

### P2 — Opzionali

1. Secondo salto pagina Acrobat.  
2. PDF criptati (fuori MVP: serve copia sbloccata).  
3. Esporta descrizione → file PDF dedicato (solo se P0 stampa non basta).

---

## Cosa NON mettere in 1.7.1 di default

- Whisper / trascrizione ML di massa  
- Trattare le scansioni come PDF strutturati “finti”  
- Motore PDF grafico completo  
- Duplicare Copia/Salva testo se già funzionano: solo stem/cartella/stampa/UX  

---

## Criterio “1.7.1 pronta”

- P0: salvataggio con **nome dal PDF originale** (+ stampa testo e/o UX 0-testo) testato SA + Add-on.  
- Oppure P0 stem + un pezzo P1 (es. focus lettore).  
- Workflow: bump → SA → Add-on → `compila` / `make_addon` → tag `v1.7.1` + `app-v1.7.1`.

---

## Nuova chat

Aprire chat **«RTAD 1.7.1»**; partire da questo file + `docs/NOTE_CONTESTO_v1.5.md`.

---

*Creato 13/10/2026 sera; aggiornato 14/10/2026 (P0 + focus in codice SA/Add-on).*
