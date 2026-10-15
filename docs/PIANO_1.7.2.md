# Piano RTAD 1.7.2

**Ultima pubblicata:** `1.7.1` (PDF-scansione + scheda + focus).  
**Lavoro corrente / pronta:** `1.7.2` (batch media + B0 + glossario).  
**Non hotfixare 1.7.1.** Vedi anche `docs/ROADMAP_DOPO_1.5.0.md`.

**Stato (15/10/2026):** **pronta al rilascio** — P0/P1/P2 OK, bump `1.7.2`, gemelli OK, guida/WhatsNew/NOTE OK, pacchetto `.nvda-addon` fresco. Resta: install Add-on + `compila.bat` / F9 + tag GitHub.

---

## Priorità (ordine consigliato)

### P0 — Batch cartella media (audio/video)

Come il batch immagini 1.6.6, ma su file audio/video locali.

1. Elenco file media in cartella (+ opzione sottocartelle).
2. Dialogo sezioni (scheda / riassunto / trascrizione / timestamp) + salva `.rtad.txt`.
3. Per ogni file: `format_full_media_report` → salva `{stem}.rtad.txt` accanto al media
   (stesso stile titoli lunghi già usati dall’hub).
4. Entrata: Strumenti → «Analizza cartella audio/video…»; CLI `--batch-media-folder`;
   Explorer (Directory/Drive) dopo install.
5. Gemello SA ↔ Add-on; progresso accessibile (N di M).

**Default sezioni batch:** scheda + riassunto ON; trascrizione/timestamp OFF
(opt-in: costi/tempo Gemini).

### P1 — B0 MVP (ricerca in `.rtad.txt` / cache transcript)

Feedback 10/10/2026 (`PIANO_1.6.8.md`):

1. Durante ricerca su file media, se esiste sidecar `.rtad.txt` (stesso stem o
   `nome.ext.rtad.txt`), cerca anche nel testo del sidecar.
2. Hit con snippet; se presente timestamp `[MM:SS]` vicino al match, segnalarlo.
3. Zero costo se l’utente ha già analizzato (batch o hub singolo).

### P2 — Glossario post-trascrizione (leggero)

Lista editabile (es. Vlahovic → Woltemade) applicata al testo salvato / report
dopo Gemini. Opt-in; non blocca P0/P1.

### P3 — Opzionali (solo se tempo)

1. Avviso soglia se batch grande + trascrizione attiva.
2. Piccoli allineamenti SA ↔ Add-on emersi dai test.

---

## Cosa NON mettere in 1.7.2 di default

- «Trascrivi e cerca» su tutta la cartella (→ 1.7.3)  
- Whisper / trascrizione ML di massa  
- PDF criptati  
- Secondo salto Acrobat / export PDF descrizione  

---

## Criterio “1.7.2 pronta”

- P0 batch media testato SA (+ Add-on gemello).  
- P1 B0: ricerca trova parole in un `.rtad.txt` già esistente.  
- Guida / WhatsNew / NOTE_RILASCIO / bump `1.7.2`.  
- Workflow: bump → SA → Add-on → `compila` / `make_addon` → tag `v1.7.2` + `app-v1.7.2`.

---

## Nuova chat

Questa chat **«RTAD 1.7.2»**; partire da questo file + `docs/NOTE_CONTESTO_v1.5.md`.

---

*Creato 15/10/2026.*
