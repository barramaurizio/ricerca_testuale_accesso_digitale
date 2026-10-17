# Piano RTAD 1.7.4

**Ultima pubblicata (attesa / in rilascio):** `1.7.3` (sidecar stem + xlsx + Trascrivi e cerca).  
**Questa chat / versione:** `1.7.4`.  
**Non hotfixare 1.7.3** se già pubblicata. Vedi `docs/ROADMAP_DOPO_1.5.0.md` e `docs/NOTE_CONTESTO_v1.5.md`.

**Stato (17/10/2026):** piano concordato + nuova richiesta menù contestuale SA.

---

## Priorità (ordine consigliato)

### P0 — Updater SA: Installer vs Portable (feedback papà 17/10)

**Bug attuale** (`on_check_updates` in `Standalone/app_gui.py`):
1. Chiama `/releases/latest` → spesso è la release **Add-on** (`vX.Y.Z`), non `app-vX.Y.Z`.
2. Prende il **primo** asset `.exe` → spesso la **Portable**.
3. Lo salva come `Ricerca_Testuale_v….exe` generico e lo avvia.
4. Nessuna distinzione Installer / Portable → utenti con entrambe possono aggiornare «l’altra» copia.

**Voluto**
1. Interrogare le release GitHub e usare la più recente con tag `app-v*` (o asset SA noti), **non** confondere con Latest Add-on.
2. Rilevare il canale di installazione corrente:
   - **Installer:** exe sotto `Program Files` / percorso Inno, o marker (es. `unins000.exe` accanto, o flag scritto da setup).
   - **Portable:** tutto il resto (cartella scaricata, USB, ecc.).
3. Download:
   - Installer → solo `Setup_RicercaTestualeAccessoDigitale_vX.Y.Z.exe`
   - Portable → solo `RicercaTestualeAccessoDigitale_Portable_vX.Y.Z.exe`
4. Nome file salvato = nome asset reale (non generico).
5. Stesso comportamento per verifica **manuale** (Ctrl+U / menu) e **silenziosa** all’avvio.
6. Se manca l’asset atteso → messaggio chiaro + apri pagina release `app-v…` (non un exe sbagliato).

**Criterio fatto:** PC con Setup aggiorna solo Setup; PC con Portable aggiorna solo Portable; niente doppia installazione «per sbaglio».

---

### P0 — Guida HTML completa (cercabile, indice, API)

Sostituire / ampliare la guida F1 attuale (`create_html_help_file`: novità bloccate a 1.6.4, pochi paragrafi).

**Contenuto minimo**
1. Indice (anchor) + titoli H2/H3 navigabili; Ctrl+F del browser = ricerca.
2. Procedure passo-passo **chiave API Google Cloud Vision** (console, abilita API, crea chiave, dove incollarla in RTAD).
3. Procedure passo-passo **chiave API Gemini / Google AI Studio**.
4. Percorsi d’uso: ricerca file, OCR, descrizione immagini, media/AV, lettore, profili, Explorer.
5. Scorciatoie aggiornate; sezione «Novità recenti» allineata a ogni release (come guida pratica).
6. IT obbligatorio; EN se c’è tempo (o scheletro EN).
7. Apertura da Aiuto → Guida (F1) e, se utile, voce dedicata «Guida completa (HTML)»; guida pratica resta il ingresso semplice.
8. Manutenzione: a ogni novità, aggiornare HTML + `rtad_guida_pratica.py` + `docs/GUIDA_PRATICA.txt` + addon `guida_pratica.html` (checklist pre-rilascio).

**Criterio fatto:** utente cieco può, solo con la guida HTML, ottenere e inserire Vision e Gemini senza chiedere supporto.

---

### P1 — Menù contestuale Explorer: «Apri» apre davvero il file (solo SA)

**Problema (feedback Maurizio 17/10)**  
Voce «Apri in Ricerca Testuale» / prima voce del sottomenù: per **immagini** e **audio/video** lancia solo l’exe con `"%1"`. In `main()` quel path diventa la **cartella** (immagini/media) o al massimo il path nel campo — **non** apre/analizza il file. Le voci sotto (Descrivi, Tutto su…, OCR, media-all, …) funzionano perché usano flag CLI.

Documenti/PDF con `--open-doc` sono già più a posto (`prepare_shell_document`).

**Voluto (programma chiuso o aperto — stesso comportamento)**
1. Prima voce = azione **diretta sul file** in base al tipo:
   - Immagine → dialogo «Tutto sull’immagine» (o Descrivi, se preferiamo più leggero; default proposto: `--image-all`).
   - Audio/video → «Tutto sull’audio/video» (`--media-all`).
   - Documento/PDF/xlsx/testo → lettore / prepare shell (`--open-doc` o `--read-doc`; allineare etichetta).
   - Altro file generico (`*\shell`) → path = file o cartella sensata + focus ricerca (comportamento attuale migliorato).
2. Lasciare intatte le altre voci specifiche (OCR, etichette, scheda, copia, batch cartella, …).
3. **Istanze:** se RTAD è già aperto, idealmente **non** aprire una seconda finestra dispersiva: passare il comando all’istanza esistente (mutex / IPC / file di comando). Se IPC risulta troppo lungo per 1.7.4, minimo accettabile: con programma chiuso l’apertura smart funziona; con programma già aperto documentare «si apre una seconda istanza» e rimandare IPC a 1.7.5 — ma obiettivo preferito = stesso flusso in entrambi i casi.
4. Aggiungere sottomenù **`.xlsx`** (manca in `setup.iss` dopo 1.7.3): Apri / Leggi / Copia come gli altri documenti.
5. Solo Standalone (Inno `setup.iss` + CLI `app_gui.py`). Add-on: niente voci di registro Explorer (come già concordato).

**Criterio fatto:** tasto destro su JPG/MP4/PDF/DOCX/XLSX → prima voce interagisce con **quel** file; resto del menu invariato.

---

### P2 — Opzionali (solo se tempo / campione)

1. PDF papà — solo con campione «strano» e fix mirato.
2. Guida EN parallela (se IT completa).
3. Marker esplicito Installer in `settings.json` scritto al primo avvio post-setup (rinforzo detection).

---

## Cosa NON mettere in 1.7.4 di default

- Whisper / trascrizione ML di massa  
- Shell context menu nell’Add-on NVDA  
- OneCore native (voce)  
- Riscrittura architettura major  

---

## Criterio “1.7.4 pronta”

- [x] Bump etichette `1.7.4`  
- [x] Updater: Setup ↔ Portable + release `app-v*` (codice; test Maurizio)  
- [x] Shell «Apri» smart + `.xlsx` in `setup.iss` + auto-tipo in `main()`  
- [x] Singola istanza + IPC per comandi Explorer  
- [x] Sfoglia singolo file qualsiasi tipo + offerta apertura (test Maurizio)  
- [x] Guida HTML IT completa (indice + Vision + Gemini + novità)  
- [x] WhatsNew / NOTE_RILASCIO / guida pratica / README  
- [ ] `make_addon` / `compila` / Inno / tag `v` + `app-v` + DataStore (Maurizio)  

---

## Nuova chat

Chat **«RTAD 1.7.4»**; partire da questo file + `docs/NOTE_CONTESTO_v1.5.md`.

---

*Creato 17/10/2026.*
