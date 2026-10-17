# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Piano corrente:** `docs/PIANO_1.7.4.md` (updater Setup/Portable + guida HTML + shell «Apri» smart).  
Piano chiuso 1.7.3: `docs/PIANO_1.7.3.md`. Piano chiuso 1.7.2: `docs/PIANO_1.7.2.md`.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (17/10/2026)
- **Ultima pubblicata:** `1.7.3` (GitHub SA+Add-on + DataStore, 16/10). **Non hotfixare 1.7.3.**
- **Pronta al rilascio:** `1.7.4` — updater Setup/Portable, shell Apri smart, Sfoglia, guida HTML, singola istanza. Vedi `docs/PIANO_1.7.4.md` e `docs/NOTE_RILASCIO_1.7.4.txt`.
- Pacchetto Add-on fresco: `ricerca_testuale_accesso_digitale-1.7.4.nvda-addon`.
- Workflow Maurizio: install Add-on → `Standalone/compila.bat` → Inno F9 → tag `v1.7.4` + `app-v1.7.4` → DataStore.
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, guida
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`

### Priorità 1.7.4 (vedi `docs/PIANO_1.7.4.md`)
1. **P0 Updater SA** — Installer → sempre `Setup_Ricerca…`; Portable → solo Portable; release `app-v*` (non Latest Add-on); stesso per check silenzioso all’avvio.
2. **P0 Guida HTML completa** — indice, cercabile in browser, Vision + Gemini passo-passo; novità aggiornate a ogni release.
3. **P1 Shell Explorer (solo SA)** — «Apri in Ricerca Testuale» deve aprire/analizzare il file scelto (immagine/media/documento), non solo avviare il programma; + sottomenù `.xlsx`; ideale singola istanza se già aperto.
4. PDF papà / altro — solo con campione e fix mirato.

### Cosa c’è in 1.7.2 (pubblicata)
1. **P0** Batch cartella audio/video → `.rtad.txt` accanto a ogni file.
2. **P1** B0: ricerca mirata nei `.rtad.txt` già salvati ([AV] + timestamp).
3. **P2** Glossario post-trascrizione (accent-fold; rewrite `.rtad.txt` all’apertura).

### Cosa c’è in 1.7.1
1. PDF scansione: dialogo Descrivi / Apri lettore; stem/cartella PDF originale; Stampa testo.
2. Scheda tecnica: Data analisi + Ultima modifica originale (Esplora).
3. Focus freccia lettore dopo iconizza.

### Cosa c’è in 1.7.0 (pubblicata)
1. Lettore documento (cerca/titoli/esterno).
2. Spazi PDF tipici; toast fine-ricerca meno invasivo.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.7.4»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.7.4: updater Setup/Portable + guida HTML + shell Apri»
Leggere prima questo file, `docs/ROADMAP_DOPO_1.5.0.md` e `docs/PIANO_1.7.4.md`.
