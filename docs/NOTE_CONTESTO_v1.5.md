# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor. Piano dettagliato: `docs/ROADMAP_DOPO_1.5.0.md`.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (06/10/2026)
- **Ultima pubblicata:** `1.6.3` — GitHub + Add-on Store (DataStore #11999 → #12001 accettata)
- **Lavoro corrente:** `1.6.4` — avviata: descrivi da web/URL/appunti/cattura (+ gesture NVDA)
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale per utente/PC
- Gemello SA ↔ Add-on su OCR/immagini (`rtad_ocr.py`)

### Cosa c’è in 1.6.3 (riassunto)
- Descrizione avanzata Gemini (immersiva) + fallback Vision/scheda tecnica
- Grounding anti-allucinazione: OCR + data da nome file; finestra descrizione indipendente (resta aperta)
- Ricerca contenuto visivo opt-in `[IMG-VIS]`; etichette; scheda tecnica
- Standalone: sottomenù Explorer «Cerca con Accesso Digitale» sulle immagini + flag CLI

## In corso: 1.6.4 (ordine aggiornato 06/10/2026)
1. ~~Descrivi da web / URL / Appunti / cattura schermo~~ → **in codice** (SA + Add-on; gesture NVDA+Shift+G solo Add-on)  
1b. ~~NVDA+Shift+G anche su file immagine in Explorer/Desktop~~ → **in codice** (Add-on)  
2. ~~Alt-text breve + descrizione lunga~~ → **in codice** (SA + Add-on)  
3. Dialogo unico «Tutto sull’immagine»  
4. ~~Descrivi da PDF~~ → **in codice** (SA + Add-on)  
5. Batch cartella  

**Solo Add-on NVDA:** gesture sul navigatore (`NVDA+Shift+G`).  
**Gemello ovunque:** URL, Appunti, cattura schermo (+ CLI `--describe-url` nello Standalone).

## Dopo 1.6.4 (voluto da Maurizio)
- Descrizione **audio/video** (anche senza feedback esterni)
- Canale YouTube **Accesso Digitale** (banner, tag, contenuti tech originali) — chat Cursor dedicata, stesso workspace OK

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «1.6.4…»)
- Chat separata per YouTube / brand
- Richieste urgenti dal feedback possono anticipare pezzi di roadmap

## Come ripartire (prompt tipico)
«1.6.4: continuiamo da alt-text» oppure «test gesture NVDA+Shift+G sulle pagine Juventus».
Leggere prima `docs/ROADMAP_DOPO_1.5.0.md` e questo file.
