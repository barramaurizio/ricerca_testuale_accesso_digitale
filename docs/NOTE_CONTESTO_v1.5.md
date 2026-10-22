# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.8.1` — piano chiuso `docs/PIANO_1.8.1.md`.  
**In corso, non pubblicata:** `1.8.2` — codice del 22/10/2026, piano `docs/PIANO_1.8.2.md`. Non aprire Whisper.

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (22/10/2026)
- **Ultima pubblicata:** `1.8.1` — Gemini a schermo (domanda e motivo restano scritti) e, nella Standalone installata, «Chiedi a Gemini» in Esplora file.  
  Pubblicata il 21/10/2026. Prove Maurizio OK su Standalone e Add-on. Papà deve ancora provare.  
  **Non hotfixare 1.8.1.**  
  Prima: `1.8.0` chat Gemini sul file, GitHub `v1.8.0` / `app-v1.8.0`, commit `a7fcb79`, DataStore #12370 → #12371.
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_docstruct.py`, `rtad_chat.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
**`1.8.2` codice fatto il 22/10/2026, non pubblicata.** Pacchetto Add-on ricostruito: `ricerca_testuale_accesso_digitale-1.8.2.nvda-addon`. Standalone exe non compilato.  
Feedback di papà (21/10, sera): HTTP 503 su `gemini-3.5-flash` (servizio occupato) e 429 (tetto temporaneo). Ha ancora circa 100 €. Ora un 503 prova il modello successivo. La frase a schermo dice «servizio occupato» oppure «limite temporaneo di richieste», e cita il pagamento solo se lo scrive Google.  
Tasti: Alt+L chiave Google, Alt+H chiave Gemini, Alt+B conversazioni. Alt+G sulla finestra principale è Segnalibri. Alt+M è Strumenti. «Chiedi a Gemini» sul report resta Alt+G. Ctrl+Shift+G resta. Le lettere doppie dello stesso menu o dialogo sono state separate.  
Le cronologie restano due cartelle: Standalone in `%AppData%\Roaming\RTAD_Standalone\chat`, Add-on in `{profilo NVDA}\rtad_data\chat`. Unificarle non è in 1.8.2.  
Il `.rtad.txt` già salvato passa alla versione dopo. Whisper, confronto tra più file, chat vuota e Gemini su ogni risultato restano fuori.

Lista d’attesa: Whisper opt-in (versione dedicata); VIDEO_TS; OneCore; export multipli.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.8.2: codice già fatto il 22/10, non pubblicato e non compilato. Leggere NOTE_CONTESTO. Prova: una domanda Gemini se il primo modello dà 503, e i tasti Alt+L / Alt+H / Alt+B / Alt+G / Alt+M. Poi, se Maurizio conferma, compilare.»
