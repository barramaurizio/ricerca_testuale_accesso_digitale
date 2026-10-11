# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Piano operativo 1.6.8:** `docs/PIANO_1.6.8.md` ← aprire questo in chat nuova.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (11/10/2026)
- **Ultima pubblicata:** `1.6.7` — GitHub (`v1.6.7` + `app-v1.6.7`) + Add-on Store
  (DataStore #12099 → #12100 accettata). **Non ripubblicare / non hotfixare 1.6.7.**
- **Pronta al rilascio:** `1.6.8` — docs/novità/guida aggiornate; vedi `docs/NOTE_RILASCIO_1.6.8.txt`
  e piano `docs/PIANO_1.6.8.md` (C1+C2 + A documenti; B/B0 rimandati).
- Chiavi opt-in personali: Google Vision + Gemini (AI Studio), salvate in locale
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, guida
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc` (check versioni/docs prima di «vai»)

### Cosa c’è in 1.6.8 (da pubblicare)
1. Documenti strutturati DOCX/EPUB + PDF onesto; «Leggi documento…» anche Add-on.
2. UX salvataggi: report media (cartella/nome) + auto-salvataggio risultati.
3. Sfoglia cartella **o** singolo file.
4. Restano hub audio/video 1.6.7.

### Cosa c’è in 1.6.7 (storico / pubblicata)
1. Hub audio/video + URL (yt-dlp/ffmpeg) + File API Gemini (~2 GB / ~3 h).
2. Scheda tecnica (ffprobe), Short, Titolo/ID/URL sorgente, ripresa trascrizione.
3. Avanzamento (gauge + Alt+S) + Salva testo report.
4. Explorer / menu / CLI gemello.

### Dopo 1.6.8 (1.6.9+)
- TOC/link PDF; batch media; ricerca in transcript già in cache poi «trascrivi e cerca» (B0)
- Whisper locale opt-in; «Apri con» / associazione Windows
- Canale YouTube **Accesso Digitale** — chat Cursor dedicata, stesso workspace OK

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «1.6.7…»)
- Chat separata per YouTube / brand
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«1.6.7: continuiamo dal dialogo Tutto sull’audio/video / scheda tecnica»
Leggere prima questo file e `docs/ROADMAP_DOPO_1.5.0.md` (Fase N).
