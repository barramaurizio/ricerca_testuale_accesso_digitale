# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.7.7` — piano chiuso `docs/PIANO_1.7.7.md`.  
**Pronta in locale, non ancora su GitHub:** `1.8.0` chat Gemini sul file — piano `docs/PIANO_1.8.0.md`. Prove Maurizio 21/10 OK (SA e Add-on).

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (21/10/2026)
- **Ultima pubblicata:** `1.7.7` — OCR tabelle riga-per-riga (cache v20, anche Vision) + Add-on voce/casella OCR.  
  GitHub `v1.7.7` / `app-v1.7.7` (commit `583dec7`); DataStore #12333 → #12334 (accepted).  
  **Non hotfixare 1.7.7.** Feedback papà: **OK** (20/10 sera) — prove perfette.
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, `rtad_chat.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
**`1.8.0`:** chat Gemini sul file, prove Maurizio OK il 21/10 (file locale e URL, SA e Add-on).  
Pacchetti da installare in locale; **non** ancora tag GitHub né DataStore.  
Cronologie SA e Add-on separate. Link: Apri fonte / Alt+F; Invio sull’elenco non apre il browser.  
`1.7.8` solo se bug/feedback urgente sulla 1.7.7.

Lista d’attesa (dopo o se feedback): Whisper opt-in; `.rtad.txt`-only; VIDEO_TS; OneCore; export multipli.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.8.0: leggere NOTE_CONTESTO + PIANO_1.8.0; partire da P0 dialogo Gemini su immagine e documento»
