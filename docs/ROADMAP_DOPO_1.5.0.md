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

Regola Zero invariata: **Standalone → Add-on → compile → due tag** (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store se serve.

---

## Cosa NON entrare nel nucleo (per ora)

- Whisper / trascrizione ML su audio-video in massa  
- OCR pesante bundlato nell’Add-on NVDA (Tesseract/EasyOCR shippato nel pacchetto)  
- Scansione “tutto il PC” con motori lenti (OCR/vision) senza opt-in  
- Ricerca semantica oggetti/scene nel default (lupo, spiaggia, …) — pista Standalone opt-in o gemello “media”

Queste idee restano valide come **pista separata**, non come default RTAD.

---

## Piano per fasi (testabili una alla volta)

### Fase A — `1.5.1` (cronologia) — FATTA ✅

### Fase B — `1.5.2` (lettore email sicuro + date) — FATTA ✅

### Fase C — `1.5.3` (PDF migliorato) — FATTA ✅

PDF testo (FlateDecode + ToUnicode/CID), Copia Testo / Copia Immagine / Salva Immagine, data documento, avvisi accessibili.

### Fase D — `1.5.4` (profili di ricerca) — IMPLEMENTATA (da provare / rilasciare)

Obiettivo: salvare e richiamare in un colpo le impostazioni di ricerca usate spesso.

**Cosa salva un profilo**

1. Nome leggibile (es. «Documenti Desktop», «Feed TB», «PDF fatture»).  
2. Percorso (cartella, unità, URL feed, o «tutto il PC» se era impostato così).  
3. Tipo di file (combo: tutti / immagini / media / documenti / estensione personalizzata).  
4. Estensione personalizzata (se attiva).  
5. Opzione feed grezzi (checkbox occorrenze grezze).  
6. Testo di ricerca: **opzionale** (chiedere in salvataggio se includerlo).  
7. Avvio automatico: se c’è testo salvato, opzione «all’apertura del profilo avvia subito la ricerca».

**UX (Standalone = Add-on)**

- Menu **Profili**: Salva attuale, Carica / elenco rapido, Gestisci (elimina / rinomina).  
- Scorciatoia: **Ctrl+Shift+P** = salva profilo attuale; elenco anche da menu.  
- Stesso stile accessibile di Segnalibri/Cronologia (dialoghi semplici, `ui.message` / sintesi differita nell’Add-on).  
- Max ~20 profili; persistenza in `settings.json`.

*Criterio “fatto”:* creo «Documenti Desktop», chiudo e riapro, carico il profilo → percorso + filtro ripristinati; se avevo salvato anche il testo e l’auto-avvio, la ricerca parte.

### Fase E — `1.5.5` (voce Standalone)

1. Velocità (e tono se semplice) SAPI5; menu + scorciatoie; persistenza.  
2. Solo Standalone (Add-on = voce NVDA).  
3. Eventuale scelta voce tra token SAPI (spesso include OneCore).

### Fase F — anteprima + avvisi a fine ricerca (`1.5.x` successiva)

### Fase G — OCR testo in immagini / PDF scansione (`1.5.6` o ingresso `1.6`)

**Priorità alta dopo voce** (accordo settembre 2026).

1. **Opt-in** esplicito: «Includi testo nelle immagini (OCR)».  
2. Motore: **Windows.Media.Ocr** (niente pacchetto pesante).  
3. Target: `.jpg/.png/.…` e pagine grafiche PDF (già estraibili).  
4. Cache testo OCR per file (hash + mtime) per non ripetere lavoro.  
5. Standalone prima → Add-on con lo stesso OCR di sistema.  
6. Messaggi chiari su qualità / assenza testo.

**Non in questa fase:** ricerca per oggetti/scene («foto con un lupo»). Quella è vision/captioning → modulo opt-in successivo o gemello.

### Fase H — EPUB + ZIP opt-in (`1.5.x` / pezzo di `1.6`)

Ordine consigliato: **dopo OCR di base** (o in parallelo snello se OCR slitta).

| Formato | Perché | Note |
|---------|--------|------|
| **EPUB** | Lettori assidui e studenti | ZIP+XHTML interno; testo ricercabile come documenti. Serve qualche file di prova. |
| **ZIP / archivi** | Cercare dentro senza scompattare a mano | **Sempre opt-in** (lento, molti file); depth limit; niente autocompilazione di tutto il PC. |

### Fase I — `1.6.0` (salto sostanzioso)

Quando almeno due arricchimenti «si sentono» come pacchetto (es. OCR + EPUB, o OCR + vision leggera), si valuta il salto.

**Candidati vision (dopo OCR testo):** caption/tag opzionale sul risultato selezionato; ricerca semantica solo se feedback la chiedono e resta opt-in Standalone.

---

## Decisioni UX (settembre 2026)

- **Niente** secondo/terzo pulsante Cronologia in interfaccia.  
- **Pin / Windows+N:** gestiti da Windows.  
- **Notifiche fine ricerca:** dopo i profili.  
- **Log lunghi:** ultime 30–40 righe bastano.  
- **Voce:** solo Standalone; OneCore via token SAPI prima di API native.  
- **PDF 1.5.3:** rilasciato.  
- **Profili** = `1.5.4`; **voce** = `1.5.5`; **OCR** = dopo voce.  
- **EPUB/ZIP:** dopo OCR (o pezzo `1.6`); ZIP sempre opt-in.  
- **Oggetti nelle foto:** non nel nucleo; pista futura opt-in.

---

## Ordine di lavoro

1. ~~1.5.0 / 1.5.1 / 1.5.2 / 1.5.3~~ fatte.  
2. **1.5.4 profili** — implementata; prova + release.  
3. **1.5.5 voce Standalone.**  
4. **OCR** (immagini + PDF scansione, opt-in, Windows OCR).  
5. Anteprima / notifiche; **EPUB**; **ZIP opt-in**.  
6. Decidere insieme **1.6.0** (e eventuale vision leggera).

---

## Idee in lista d’attesa

- Caption/tag visuali opt-in Standalone; ricerca semantica scene  
- Media/Whisper gemello; export/stampa extra; API OneCore native  
- Feedback esterni → aggiornano priorità qui  

---

*Documento di piano: si aggiorna quando una fase è chiusa o cambia priorità.*
