# Piano RTAD 1.7.5

**Ultima pubblicata:** `1.7.4` (updater Setup/Portable, shell Apri, Sfoglia, guida HTML, istanza unica).  
GitHub `v1.7.4` / `app-v1.7.4`; DataStore #12249 → #12250 (accepted 17/10/2026).  
**Questa versione:** `1.7.5`. **Non hotfixare 1.7.4.**

Vedi `docs/ROADMAP_DOPO_1.5.0.md` e `docs/NOTE_CONTESTO_v1.5.md`.

---

## Spirito della 1.7.5

Patch **utile e testabile in un giorno**, dopo una 1.7.4 già corposa.  
Priorità: feedback utenti su 1.7.4 + un arricchimento SA↔Add-on che si sente subito.  
Niente Whisper di massa né riscritture grandi (restano in lista d’attesa).

---

## Priorità consigliate (ordine)

### P0 — Arrivi da feedback 1.7.4 (se ce ne sono)

Qualsiasi bug su updater Setup/Portable, shell «Apri», istanza unica, Sfoglia, guida HTML.  
Se nella notte/mattina non arriva nulla di bloccante → saltare e andare a P1.

**Feedback papà 17/10 (chiuso lato PC):**
- Doppia copia: Installer **1.7.3** + `Downloads\Ricerca_Testuale_v1.7.4.exe` (updater vecchio). Pulito a mano con `tools/rtad_trova_copie.ps1` → disinstalla 1.7.3 + Setup 1.7.4.
- Audio/video: **entusiasta**. Guida HTML: ottimo. Analisi dettagliata immagine: «anche senza OCR ho già tutto».
- OCR «Leggi testo nell'immagine»: testo **in verticale** → fix layout in 1.7.5 (restante).
- Excel: da provare (stanco). Windows Media Player: niente voci RTAD → normale (menù shell solo in **Esplora file**, non dentro WMP).
- DVD: chiede se RTAD vede i file sul disco. Oggi «Tutto il PC» esclude CD/DVD (`GetDriveType` solo fisso/rimovibile). → vedi P2b / futuro.

**P0b — Trova / pulisci copie vecchie (SA)** — in corso / codice base  
Voce Strumenti «Trova altre copie sul PC…» (`rtad_copie.py` + dialogo accessibile):  
elenco + rapporto Desktop + rimozione solo Portable/Download con consenso;  
avviso amichevole all’avvio se sembrano più copie (declinabile / «non ricordare»).  
Mai Roaming chiavi. Script ponte: `tools/rtad_trova_copie.ps1`.  
Guida HTML sezione «Trova altre copie» + nota aggiornamenti.

**P0 OCR verticale** — in corso  
`reflow_ocr_vertical_chars` in `rtad_ocr.py` (cache v18) + «Leggi testo OCR» via `ocr_text_for_clipboard(full)`.

**Guida AV** — fatta (spiegazione `.rtad.txt` / Tutto il PC / non ascolta tutto il disco).

### P1 — Incolla file / percorso dagli Appunti (SA + Add-on) — FATTO (codice)

1. CF_HDROP / path testo → `apply_search_path` + offerta Apri come Sfoglia.  
2. Pulsante **Incolla…**, Strumenti, **Ctrl+Alt+V** (SA + Add-on).  
3. Guida HTML §4.1.

**Criterio fatto:** Ctrl+C su un JPG in Esplora → Incolla → path + eventuale offerta.

### P1b — Trascinamento file sulla finestra (SA) — FATTO (codice)

`DragAcceptFiles` / `EVT_DROP_FILES` → stesso `apply_search_path`.

### P2 — Detection Installer più “esplicita”

Inno Setup può scrivere un marker (`install_channel=installer` o file accanto all’exe) al primo avvio post-setup, così l’updater non dipende solo da Program Files / `unins000.exe`.  
Rinforzo del P0 già fatto in 1.7.4; utile se emerge confusione su qualche PC.

### P2 — Guida HTML: ritocchi + EN leggero

- Eventuali correzioni da feedback lettura.  
- Nota breve: menù RTAD in Esplora, non dentro Windows Media Player.  
- Scheletro **inglese** se c’è tempo; altrimenti solo IT.  
- Manutenzione: solo sezioni nuove / novità — **non** riscrivere tutta la guida.

### P2b — Unità CD/DVD (piccolo, se tempo)

Oggi `get_real_ready_drives()` include solo tipi 2–3 (rimovibile/fisso), **non** CDROM (5).  
In 1.7.5 se resta tempo: includere unità ottiche pronte in «Tutto il PC» / elenco unità, e/o accettare esplicitamente `D:\` da Sfoglia.  
DVD video commerciali (`VIDEO_TS`) ≠ cartella di mp3/mp4: i file “normali” sul DVD sì; menu DVD autorizzati sono un altro discorso (1.7.6+).

### P3 — Opzionali (solo se tempo / campione)

1. **PDF papà** — solo con campione “strano”.  
2. Whisper locale opt-in — **no** in 1.7.5 di default (troppo grosso; candidare 1.7.6+).  
3. OneCore native — idem, dopo.  

---

## Idee buone per subito dopo (1.7.6 / pacchetto più corposo)

Da discutere nella chat 1.7.5 solo se P0–P1 sono chiusi presto:

| Idea | SA | Add-on | Note |
|------|----|--------|------|
| Whisper locale opt-in (cartella piccola) | sì | sì se leggero | Alternativa/complemento a Gemini per trascrizione |
| DVD / VIDEO_TS (ripping-aware o avviso chiaro) | sì | — | Oltre “unità ottica in Tutto il PC” |
| «Cronologia file aperti da Explorer» | sì | — | Ultimi N file shell → ripresa rapida |
| Profilo «solo AV + Trascrivi e cerca» preimpostato | sì | sì | Un click per il flusso tipico |
| Export report multipli → un unico `.rtad.txt` / HTML | sì | sì | Comodo per cartelle |
| Add-on: più azioni da focus Explorer (già Shift+G) | — | sì | Allineare spiriti al menù SA senza registro |
| Ricerca nei soli `.rtad.txt` (senza filtro Solo AV) | sì | sì | Opt-in casella |
| YouTube / brand | — | — | Chat dedicata, non mescolare |

---

## Cosa NON mettere in 1.7.5 di default

- Whisper / ML di massa  
- Shell context menu nell’Add-on (limiti NVDA/registro)  
- Major 2.0 / cambio architettura  
- Hotfix silenzioso della 1.7.4 già pubblicata  

---

## Criterio “1.7.5 pronta”

- [x] P0 feedback 1.7.4 gestiti (OCR verticale + Trova copie)  
- [x] Incolla Appunti file/path (SA + Add-on)  
- [x] drag & drop SA  
- [x] Guida / novità / WhatsNew / NOTE_RILASCIO / bump `1.7.5`  
- [x] `make_addon` (`.nvda-addon` 1.7.5)  
- [ ] `compila` / Inno / tag `v` + `app-v` + DataStore — **Maurizio**  

---

## Prossima chat

Titolo: **«RTAD 1.7.6»** — piano in `docs/PIANO_1.7.6.md`.

---

*Creato 17/10/2026 sera; codice chiuso 18/10/2026.*
