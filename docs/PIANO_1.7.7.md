# Piano RTAD 1.7.7

**Stato:** **pubblicata** 20/10/2026 — GitHub `v1.7.7` / `app-v1.7.7`; DataStore #12333 → #12334 (accepted). Feedback papà: OK. **Non hotfixare 1.7.7.**  
Cache OCR uscita in **v20** (anche Vision). Nel testo sotto, scritto in bozza, compare ancora «v19»: è la bozza, non il codice pubblicato.  
Prossima: `docs/PIANO_1.8.0.md`.

**All’apertura del piano (19/10):** ultima pubblicata `1.7.6` — drop SA, updater `updates\`, CD/DVD+.cda, wrap report, marker, guide. DataStore #12312 → #12313.

Vedi `docs/ROADMAP_DOPO_1.5.0.md` e `docs/NOTE_CONTESTO_v1.5.md`.

---

## Spirito della 1.7.7

Patch **utile**: chiudere il feedback OCR su tabelle / testo «a colonne»
(foto programmazione TV di papà) e, se resta tempo, un pezzo leggero
dalla lista d’attesa. Niente major 2.0, niente Whisper di massa.

---

## Feedback già raccolti (19/10, papà + Portable prova)

1. **OCR solo-casella su tabella** (immagine programmazione TV): a schermo
   il testo resta «in verticale» / a colonne. Con Gemini (descrizione,
   alt-text…) OK. Non è il bug «una lettera per riga» (già OK in 1.7.5):
   è **ordine di lettura** (colonne invece di righe).
2. Drop, wrap, avviso `.cda`, updater: OK in 1.7.6 (non rifare).
3. CD audio → WMP → file reali: guida già in 1.7.6; riprove utente se vuole.

Campione: WhatsApp immagine programmazione (Canale / Programma / Orario / Durata)
salvata in chat / assets Cursor 19/10.

---

## Priorità consigliate (ordine)

### P0 — OCR: ordine di lettura orizzontale (tabelle / colonne)

**Problema:** Windows OCR (e varianti) su layout a griglia spesso restituisce
testo colonna-per-colonna; a occhio e in NVDA sembra «verticale».

**Obiettivo:** in «Leggi testo nell’immagine» / sezione OCR di «Tutto
sull’immagine», il testo mostrato segua un ordine **riga per riga**
quando il layout lo consente (tabella, elenco a colonne).

**Direzione tecnica (da approfondire in implementazione):**
1. Se l’API OCR espone **bounding box** per parole/righe → ordinare per
   `y` poi `x` e ricostruire le righe (soglia di «stessa riga»).
2. Se solo testo grezzo: euristiche di ripartizione (molte righe corte
   ripetitive / header noti) senza inventare parole.
3. Non peggiorare i casi già buoni (CIAO una lettera per riga resta
   con `reflow_ocr_vertical_chars`; poster HAPPY/BIRTHDAY).
4. Gemello SA ↔ Add-on (`rtad_ocr.py`); bump cache OCR se serve
   (es. v19) così papà non resta su cache «a colonne».
5. Smoke: immagine tabella papà + fixture CIAO (regressione).

**Criterio:** stessa foto TV → OCR-only leggibile per righe
(Canale… Programma… sulla stessa linea logica, o righe tabella chiare);
fixture verticale lettere ancora OK.

### P1 — Guida / novità (breve)

Documentare: OCR tabelle / ordine lettura; EN se tempo.

### P2 — Se P0 chiuso e resta tempo (scegliere uno)

| Candidato | Note |
|-----------|------|
| Whisper locale opt-in | Solo file/cartelle piccoli; niente modelli enormi bundlati |
| VIDEO_TS messaggio + limiti | Già avviso leggero in 1.7.6; approfondire se feedback |
| Ricerca nei soli `.rtad.txt` | Profilo / filtro snello (era P3 in 1.7.6) |

### P3 — Opzionali / dopo

- OneCore native voce SA  
- Export report multipli  
- Add-on: più azioni da focus Explorer  
- YouTube / brand — chat dedicata  

---

## Cosa NON mettere in 1.7.7 di default

- Whisper di massa / modelli giganti  
- Ripping DVD commerciale  
- ffmpeg bundlato nell’exe  
- Major 2.0  

---

## Criterio “1.7.7 pronta”

- [x] OCR tabella campione: ordine riga-per-riga (o netto miglioramento) — smoke OK 20/10  
- [x] Regressione fixture CIAO / una lettera per riga ancora OK  
- [x] Gemello `rtad_ocr` + cache bump (bozza v19, **pubblicato v20**)  
- [x] Guida / novità / bump `1.7.7` (testi)  
- [x] `make_addon` / `compila` / tag `v1.7.7` + `app-v1.7.7` + DataStore #12333 → #12334 (20/10/2026)  

---

## Nuova chat

Titolo: **«RTAD 1.7.7»**  
Prompt:  
«leggere NOTE_CONTESTO + PIANO_1.7.7; partire da P0 OCR ordine lettura tabelle»

---

*Creato 19/10/2026 sera (dopo pubblicazione 1.7.6 / DataStore accepted).*
