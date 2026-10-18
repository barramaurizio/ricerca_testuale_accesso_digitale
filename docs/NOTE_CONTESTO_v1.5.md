# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Piano corrente:** `docs/PIANO_1.7.6.md` (marker Installer / CD-DVD / Whisper opt-in).  
Piano chiuso 1.7.5: `docs/PIANO_1.7.5.md`. Piano chiuso 1.7.4: `docs/PIANO_1.7.4.md`.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (18/10/2026)
- **In rilascio / pronta al build:** `1.7.5` — OCR orizzontale, Trova copie (SA), Incolla Appunti (+ drag SA), guida AV/.rtad.txt.  
  Pacchetto Add-on: `ricerca_testuale_accesso_digitale-1.7.5.nvda-addon`.  
  **Non hotfixare 1.7.4.** Dopo tag GitHub + DataStore, ultima pubblicata = 1.7.5.
- **Prossima chat / versione:** `1.7.6` — vedi `docs/PIANO_1.7.6.md`.
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Cosa c’è in 1.7.5
1. OCR reflow verticale → orizzontale (`rtad_ocr` cache v18).
2. Trova altre copie sul PC (elenco + rapporto + rimozione sicura con consenso).
3. Incolla percorso Appunti (Ctrl+Alt+V) SA+Add-on; drag&drop SA.
4. Guida HTML: AV via `.rtad.txt`, copie, Incolla.

### Priorità 1.7.6 (bozza — dettaglio in PIANO)
1. P0 feedback 1.7.5.
2. Marker Installer più esplicito.
3. Unità CD/DVD in «Tutto il PC».
4. Whisper locale opt-in (se leggero).
5. OneCore / VIDEO_TS / profili AV → dopo se serve.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.7.6»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.7.6: leggere NOTE_CONTESTO + PIANO_1.7.6; P0 feedback poi marker/CD/Whisper»
