# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.8.0` — piano chiuso `docs/PIANO_1.8.0.md`.  
**Prossima, solo se serve:** `1.8.1` — piano `docs/PIANO_1.8.1.md`. Non aprire Whisper.

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
- **Ultima pubblicata:** `1.8.0` — chat Gemini sul file (immagine, documento, audio/video, URL).  
  GitHub `v1.8.0` / `app-v1.8.0` (21/10/2026, commit `a7fcb79`); DataStore #12370 → #12371 (accepted).  
  **Non hotfixare 1.8.0.** Prove Maurizio OK. Link: Apri fonte / Alt+F. Cronologie SA e Add-on separate.  
  Prima di questa: `1.7.7` OCR tabelle, DataStore #12333 → #12334. Feedback papà OK (20/10).
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, `rtad_chat.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
**`1.8.1` non è ancora iniziata.** Piano: `docs/PIANO_1.8.1.md`.  
Se non arriva feedback: chat Gemini da un `.rtad.txt` già salvato, senza rifare l’analisi.  
Se arriva feedback: quello sostituisce il piano, non si somma.  
Whisper, confronto tra più file, chat vuota e Gemini su ogni risultato restano fuori.

Lista d’attesa: Whisper opt-in (versione dedicata); VIDEO_TS; OneCore; export multipli.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.8.1: leggere NOTE_CONTESTO + PIANO_1.8.1; non toccare la 1.8.0 pubblicata; se non c’è feedback, partire dal .rtad.txt già salvato»
