# Piano RTAD 1.7.6

**Ultima pubblicata (prevista):** `1.7.5` — OCR orizzontale, Trova copie, Incolla Appunti.  
**Questa versione:** `1.7.6` (patch / minore corposa se Whisper opt-in).  
**Non hotfixare 1.7.5.**

Vedi `docs/ROADMAP_DOPO_1.5.0.md` e `docs/NOTE_CONTESTO_v1.5.md`.

---

## Spirito della 1.7.6

Dopo la 1.7.5 «pulizia e comfort», qui entrano i pezzi rimandati e un
arricchimento AV sentito: **Whisper locale opt-in** (se resta leggero),
unità ottiche, marker Installer. Niente major 2.0.

---

## Priorità consigliate (ordine)

### P0 — Feedback 1.7.5 (se arriva)

Bug su OCR reflow, Trova copie, Incolla/drag, guida.  
Se niente di bloccante → P1.

### P1 — Marker Installer più esplicito (SA)

Inno / primo avvio post-setup: marker `install_channel=installer`
(o file accanto all’exe), così l’updater non dipende solo da
Program Files / `unins000.exe`. Rinforzo del canale già in 1.7.4.

### P1b — Unità CD/DVD in «Tutto il PC»

Oggi `get_real_ready_drives()` esclude CDROM (tipo 5).  
Includere unità ottiche **pronte** in «Tutto il PC» / elenco unità;
accettare esplicitamente `D:\` da Sfoglia.  
Nota: DVD commerciali `VIDEO_TS` ≠ cartella mp3/mp4 — avviso chiaro;
ripping-aware resta 1.7.7+ se serve.

### P2 — Whisper locale opt-in (SA + Add-on se leggero)

Trascrizione locale su cartella piccola / file singoli, **opt-in**,
senza bundlare modelli enormi di default. Complemento a Gemini
(«Trascrivi e cerca» / batch). Criterio: installazione esplicita o
download guidato; zero sorprese su spazio disco.

### P2b — Guida / novità

Documentare marker, CD/DVD, Whisper opt-in; ritocchi EN se tempo.

### P3 — Opzionali

- Profilo «solo AV + Trascrivi e cerca» preimpostato  
- Ricerca nei soli `.rtad.txt` (casella opt-in)  
- Cronologia file aperti da Explorer (SA)

---

## Idee buone per dopo (1.7.7+ / pacchetto più corposo)

| Idea | Note |
|------|------|
| DVD / VIDEO_TS conscious | Oltre «unità ottica in Tutto il PC» |
| OneCore native voce SA | Dopo Whisper |
| Export report multipli → un `.rtad.txt` / HTML | Comodo cartelle |
| Add-on: più azioni da focus Explorer | Allineare spiriti al menù SA |
| YouTube / brand | Chat dedicata, non mescolare |

---

## Cosa NON mettere in 1.7.6 di default

- Whisper di massa obbligatorio / modelli giganti bundlati  
- Shell context menu nell’Add-on  
- Major 2.0  

---

## Criterio “1.7.6 pronta”

- [ ] P0 feedback 1.7.5 gestiti  
- [ ] Marker Installer **oppure** CD/DVD **oppure** Whisper MVP chiaro  
- [ ] Guida / novità / bump `1.7.6`  
- [ ] `make_addon` / `compila` / tag `v` + `app-v` + DataStore  

---

## Nuova chat

Titolo suggerito: **«RTAD 1.7.6»**  
Prompt: «leggere NOTE_CONTESTO + PIANO_1.7.6; P0 feedback poi marker/CD/Whisper»

---

*Creato 18/10/2026 dopo chiusura codice 1.7.5.*
