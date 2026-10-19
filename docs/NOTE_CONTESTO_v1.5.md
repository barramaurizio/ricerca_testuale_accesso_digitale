# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Piano corrente:** `docs/PIANO_1.7.6.md` (in chiusura: guida/bump fatti; compila + tag + DataStore).  
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

## Stato attuale (19/10/2026)
- **Versione in corso di rilascio:** `1.7.6` — drop affidabile, updater in `updates\`, CD/DVD+.cda, wrap report, marker Installer, guide.
  Note: `docs/NOTE_RILASCIO_1.7.6.txt`. Smoke: `python tools/_smoke_1_7_6.py`.
- **Ultima pubblicata (ancora online finché non pubblichi 1.7.6):** `1.7.5`.
- **Prove papà (Portable WhatsApp):** drop OK; wrap OK; avviso `.cda` OK; OCR solo-tabella resta a colonne (atteso; Gemini OK). WMP rip da riprovate.
- **Non in 1.7.6:** Whisper; OCR layout tabelle; ffmpeg bundlato (resta opzionale nel PATH).
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Cosa c’è in 1.7.6
1. Drag&drop SA (FileDropTarget) + Incolla Ctrl+Alt+V.
2. Updater → `%LocalAppData%\RTAD_Standalone\updates\` + Trova copie/script allineati.
3. Unità ottiche in «Tutto il PC»; messaggio `.cda`; guida WMP per rip.
4. Wrap report / descrizioni; marker `rtad_install_channel.txt` nell’Installer.

### Prossima chat (dopo pubblicazione)
Titolo tipico: **«RTAD 1.7.7»** — OCR tabelle / Whisper opt-in / VIDEO_TS conscious (vedi roadmap).

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.7.6»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.7.6: compila.bat + F9 setup.iss; installa addon; tag v + app-v; DataStore»
