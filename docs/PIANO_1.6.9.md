# Piano RTAD 1.6.9

**Ultima pubblicata (da aggiornare al rilascio):** `1.6.8` pronta; lavoro corrente `1.6.9`.  
**Non hotfixare 1.6.8** una volta pubblicata.  
Vedi `docs/NOTE_RILASCIO_1.6.9.txt`.

---

## Obiettivo

1. **PDF strutturati** (TOC/link) — pezzo rimandato da 1.6.8  
2. **Fix titoli lunghi** nei report media (`.rtad.txt`)  
3. **Documentare** la ricerca parole nei video tramite `.rtad.txt` già salvati (B0 step 0 / workflow utente)  
4. *(opzionale se tempo)* batch media; MVP ricerca su transcript in cache

---

## Stato lavoro

| Pezzo | Stato |
|-------|--------|
| Bump etichette `1.6.9` | fatto |
| Fix `max_len` stem report (~200) | fatto |
| `extract_structure_from_pdf` (Outlines + URI) | fatto |
| Wiring SA/Add-on «Leggi documento» per PDF | fatto |
| Guida + README + note + WhatsNew | fatto |
| Batch cartella media | in lista |
| B0 MVP: cerca solo in `.rtad.txt`/cache già presenti | in lista (workflow già documentato) |

---

## Fuori scope (resta in attesa)

- Whisper locale / trascrizione di massa  
- «Trascrivi e cerca» opt-in su cartella intera (costi API)  
- Struttura ODT / `.doc` legacy OLE  

---

*Aggiornato 12/10/2026 all’avvio 1.6.9.*
