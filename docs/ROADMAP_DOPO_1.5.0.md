# Roadmap RTAD — dopo la 1.5.0

Autore progetto: Maurizio Barra (Accesso Digitale)  
Stato: piano di lavoro (niente date di calendario: solo ordine e criteri)

---

## Versionamento (accordo)

| Tipo | Esempio | Quando |
|------|---------|--------|
| **Patch / minore** | `1.5.1`, `1.5.2`, … | Fix, lucidature, una feature snella, allineamento Standalone ↔ Add-on |
| **Minor “corposa”** | `1.6.0` | Più arricchimenti insieme, o un modulo nuovo che cambia in modo sensibile l’uso |
| **Major** | `2.0.0` | Solo se cambia architettura o esperienza in modo radicale (non ora) |

**Come alla 1.4.x → 1.5.0:** si resta su `1.5.x` finché gli arricchimenti sono utili ma non “salto di prodotto”. Il numero `1.6` segnala un pacchetto sostanzioso (come i feed nella 1.5).

**Prima della 1.5.1:** qualche giorno di uso reale della 1.5.0 (store + utenti), poi rilascio piccolo. Non serve aspettare mesi; serve feedback, non frettolosità.

Regola Zero invariata: **Standalone → Add-on → compile → due tag** (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store se serve.

---

## Cosa NON entrare nel nucleo (per ora)

- Whisper / trascrizione ML su audio-video in massa  
- OCR pesante bundlato nell’Add-on NVDA  
- Scansione “tutto il PC” con motori lenti  

Queste idee restano valide come **pista separata** (opzionale Standalone, o progetto gemello “media”), non come default RTAD.

---

## Piano per fasi (testabili una alla volta)

### Fase A — `1.5.1` (cronologia) — FATTA ✅

Obiettivo: rilascio piccolo, rischio basso, subito testabile.

1. Cronologia ricerche (testi + percorsi), Ctrl+H / Ctrl+Shift+H, menu, Add-on allineato.  
2. Accessibilità: placeholder «Ricerca in corso…»; stato con Tab/Alt+S/S.  
3. Release + datastore completati; tool automazione rilascio in repo.

---

### Fase B — `1.5.2` (profili di ricerca) — PROSSIMA

1. **Profili salvati** (es. «solo Feed Thunderbird», «solo EML», «cartella X + parole Y»).  
2. Scorciatoia o menu per caricare/salvare/eliminare.  
3. Stessa UX su Standalone e Add-on.  
4. *(Lucidatura leggera, se c’è spazio)* un solo pulsante Cronologia: etichetta tipo «Cronologia (Ctrl+H)» e/o piccola scelta Testi/Percorsi — **niente** altri bottoni in UI; Svuota resta nel sottomenù.

*Criterio “fatto”:* tre profili di prova persistono dopo chiusura; annunci NVDA chiari.

---

### Fase C — `1.5.3` (anteprima + avvisi a fine ricerca)

1. **Anteprima più ricca** in lista: 2–3 righe intorno al match, navigabili senza aprire il file.  
2. Coerente con Spazio/F4 già presenti; non appesantire la UI.  
3. **Notifica a fine ricerca** (Standalone prima): se la finestra non è in primo piano, avviso Windows / area notifiche (utile su scansioni lunghe). I beep restano; pin alla barra applicazioni = azione utente Windows (nessun codice dedicato).

*Criterio “fatto”:* anteprima leggibile con frecce; feed `[FEED]` restano aperti nel browser con Invio; avviso a fine ricerca anche in secondo piano (Standalone).

---

### Fase D — lucidatura export/stampa (solo se serve, anche dentro una 1.5.x)

Già esistono: non reinventare. Eventuale HTML accessibile / meno rumore / più contesto. Priorità bassa.

---

### Fase E — media “leggeri” (candidato tardo `1.5.x` oppure pezzo della `1.6`)

Senza Whisper:

1. Cercare anche **file collegati**: `.srt`, `.vtt`, `.txt` accanto a audio/video.  
2. Metadati utili già presenti (dove economici).  
3. Sempre **opt-in** o limitati al percorso scelto — mai default su tutto il disco.

OCR vero (Windows OCR / Tesseract esterno): solo **opzionale Standalone**, mai bundlato nell’Add-on, mai su “tutto il PC”.

---

### Fase F — `1.6.0` (salto sostanzioso)

Quando almeno **due** tra B/C/E (o un modulo media opt-in solido) sono stabili e allineati sui gemelli, si raggruppa in **1.6.0** con note di rilascio che spiegano il salto (come i feed in 1.5).

Se le fasi A–C bastano come pacchetto “si sente diverso”, si può fare 1.6 già lì; se ogni pezzo esce da solo, si resta su 1.5.1 / .2 / .3 e si salta dopo.

---

## Decisioni UX (settembre 2026)

- **Niente** secondo/terzo pulsante Cronologia in interfaccia: scorciatoie + menu bastano; al massimo etichetta/scelta sul pulsante esistente.  
- **Pin barra applicazioni / Windows+N:** gestiti da Windows; RTAD non reinventa il pin.  
- **Notifiche fine ricerca** in secondo piano: sì, ma dopo i profili (Fase C / Standalone prima).

---

## Ordine di lavoro consigliato (per Cursor / Maurizio)

1. ~~1.5.0 / 1.5.1~~ fatte.  
2. **Prossima: Fase B → 1.5.2 (profili).**  
3. Poi Fase C (anteprima + notifiche).  
4. Media leggeri quando A–C sono solide.  
5. Decidere insieme il momento del tag **1.6.0**.

Per ogni fase: prototipo Standalone → porting Add-on →  
`python tools\rtad_release.py bump X.Y.Z` (allinea numeri + `.nvda-addon`) →  
test tastiera/NVDA → `compila.bat` → GitHub Desktop → release → (store se Add-on).  
Vedi `docs/AUTOMAZIONE_RILASCIO.md`.

---

## Idee in lista d’attesa (non schedule)

- Migliorie export/stampa  
- **EPUB:** fattibile in modo snello (è uno ZIP di XHTML, simile a DOCX) → dopo profili  
- **ZIP generici:** più delicati (tanti formati, archivi enormi) → più avanti, opt-in  
- **PDF migliorato:** decompressione stream zlib senza librerie pesanti  
- OCR opt-in Standalone  
- Progetto gemello media / Whisper (separato)  
- Altro che emergerà dagli utenti dello store  

---

*Documento di piano: si aggiorna quando una fase è chiusa o cambia priorità.*
