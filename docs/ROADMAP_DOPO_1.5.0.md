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

### Fase A — `1.5.1` (cronologia) — STANDALONE OK, ADD-ON IN TEST

Obiettivo: rilascio piccolo, rischio basso, subito testabile.

1. **Fix / lucidature** dalla 1.5.0 (segnalazioni store, testi guida, piccoli bug).  
2. **Cronologia ricerche** ✅ Standalone testata da Maurizio; ✅ Add-on portato (da testare).  
3. Allineamento gemelli + note bilingue + datastore dopo OK Add-on.

*Idee accodate (non in 1.5.1):* EPUB (zip di XHTML, fattibile snello in una 1.5.x successiva); ricerca dentro ZIP generici (più delicata); miglioramento PDF con decompressione stream zlib (senza librerie pesanti).

*Criterio “fatto”:* cronologia usabile a tastiera su entrambi i gemelli; nessuna regressione su feed/Thunderbird/Alt+P/Ctrl+F.

---

### Fase B — `1.5.2` (profili di ricerca)

1. **Profili salvati** (es. «solo Feed Thunderbird», «solo EML», «cartella X + parole Y»).  
2. Scorciatoia o menu per caricare/salvare/eliminare.  
3. Stessa UX su Standalone e Add-on.

*Criterio “fatto”:* tre profili di prova persistono dopo chiusura; annunci NVDA chiari.

---

### Fase C — `1.5.3` (anteprima contesto)

1. **Anteprima più ricca** in lista: 2–3 righe intorno al match, navigabili senza aprire il file.  
2. Coerente con Spazio/F4 già presenti; non appesantire la UI.

*Criterio “fatto”:* anteprima leggibile con frecce; feed `[FEED]` restano aperti nel browser con Invio.

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

## Ordine di lavoro consigliato (per Cursor / Maurizio)

1. Lasciar sedimentare la **1.5.0** (feedback).  
2. Implementare e testare **solo Fase A → 1.5.1**.  
3. Poi B → C, una release ciascuna (o unite se piccole).  
4. Media leggeri quando A–C sono solide.  
5. Decidere insieme il momento del tag **1.6.0**.

Per ogni fase: prototipo Standalone → porting Add-on →  
`python tools\rtad_release.py bump X.Y.Z` (allinea numeri + `.nvda-addon`) →  
test tastiera/NVDA → `compila.bat` → GitHub Desktop → release → (store se Add-on).  
Vedi `docs/AUTOMAZIONE_RILASCIO.md`.

---

## Idee in lista d’attesa (non schedule)

- Migliorie export/stampa  
- **EPUB:** fattibile in modo snello (è uno ZIP di XHTML, simile a DOCX) → buona candidata `1.5.2`/`1.5.3`  
- **ZIP generici:** più delicati (tanti formati, archivi enormi) → più avanti, opt-in  
- **PDF migliorato:** decompressione stream zlib senza librerie pesanti (oggi già utile su molti PDF “semplici”)  
- OCR opt-in Standalone  
- Progetto gemello media / Whisper (separato)  
- Altro che emergerà dagli utenti dello store  

---

*Documento di piano: si aggiorna quando una fase è chiusa o cambia priorità.*
