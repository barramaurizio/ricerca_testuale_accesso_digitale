# Note di contesto — Ricerca Testuale Accesso Digitale

Documento di lavoro per nuove chat Cursor.  
Piano release: `docs/ROADMAP_DOPO_1.5.0.md`.  
**Ultima pubblicata:** `1.8.8` — piano `docs/PIANO_1.8.8.md` (28/10/2026, GitHub `v1.8.8` / `app-v1.8.8`, commit `93faddb`, DataStore #12565 chiuso via #12566, accettato). Non hotfixarla. Commit `ee28948`: finestra di benvenuto e guida HTML allineate; gli exe della Standalone sulla release sono stati sostituiti. Il pacchetto Add-on dello store resta quello accettato.  
**In corso:** `1.8.9` — piano `docs/PIANO_1.8.9.md`. Prima cosa: lettore sui PDF DocuSign firmati. Papà (22/10, sera) ha tolto le chiavi Gemini e Cloud Vision dal programma e non fa da tester su quei conti: per i testi dei brani gli basta rimettere la chiave Gemini nella Standalone.  
**NVDA:** ultima versione testata sull’Add-on pubblicato: `2026.3.0` (`lastTestedNVDAVersion`).

## Sorgente
- GitHub: https://github.com/barramaurizio/ricerca_testuale_accesso_digitale
- Cartella locale: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone (`Standalone/app_gui.py` + moduli) — prova e test
2. Add-on NVDA gemello (solo dopo SA ok)
3. Compila Portable/Installer → due tag GitHub (`vX.Y.Z` add-on, `app-vX.Y.Z` standalone) → store NVDA

## Stato attuale (29/10/2026)
- **Ultima pubblicata:** `1.8.8` — scheda video, glossario nel lettore, pagine HTML, indirizzo Internet in elenco.  
  Pubblicata il 28/10/2026. GitHub `v1.8.8` / `app-v1.8.8`, commit `93faddb`. DataStore #12565 chiuso via #12566, accettato.  
  **Non hotfixare 1.8.8.**  
  Prima: `1.8.7` il 27/10 (DataStore #12546); `1.8.6` il 26/10 (DataStore #12533); `1.8.5` il 25/10 (DataStore #12491).
- Chiavi opt-in: Google Vision + Gemini (AI Studio), locali
- Gemello SA ↔ Add-on: `rtad_ocr.py`, `rtad_media.py`, `rtad_whisper.py`, `rtad_epub.py`, `rtad_docstruct.py`, `rtad_reading_mark.py`, `rtad_chat.py`, `rtad_attach_dialog.py`, `rtad_compare.py`, `rtad_guida_pratica.py`, `rtad_guida_html.py`
- Solo SA: `rtad_copie.py` (Trova copie)
- Promemoria Cursor: `.cursor/rules/rtad-pre-release-check.mdc`
- Verifica commit prima del push: `git --no-pager show --stat -1`

### Versione in corso
`1.8.9`. Piano: `docs/PIANO_1.8.9.md`. Il numero nel programma è `1.8.9`. I testi delle novità sono scritti. Non è ancora su GitHub né sullo store. I due exe li compila Maurizio.

Lettore PDF: i tre accordi DocuSign in Download tengono `/ToUnicode` e `/Font` in un object stream compresso. Standalone e Add-on aprono quel collegamento. Maurizio ha riletto i testi salvati: Cechov, Dostoevskij e Puškin sono a posto. Il sommario «Spett.le» / «PREMESSO» è stato corretto dopo quella lettura, insieme a virgolette attaccate, «sub-licenze» e «proporVi». «trascriv iamo» resta con lo spazio.

Confronto tra più file: provato da Maurizio sulla Standalone il 29/10, anche con tipo, dimensione e ultima modifica quando non coincidono. La durata compare solo se c’è un audio o un video. Stessa finestra di scelta in Gemini, Alt+L prima di Invio. Pacchetto locale: `ricerca_testuale_accesso_digitale-1.8.9.nvda-addon`. Il numero è nuovo: NVDA chiede il riavvio, non serve uscire prima. Dopo la pubblicazione, quattro cose non iniziate: Gemini su ogni risultato, VIDEO_TS (avviso, niente copia del film), OneCore, export multipli. Più avanti: confronto del parlato e del testo di un’immagine, poi un browser che segua i link.

**Log SA:** `%AppData%\Roaming\RTAD_Standalone\rtad_debug.log`

## Igiene chat
- Nuova chat per ogni versione RTAD (es. «RTAD 1.8.0»)
- Chat separata per YouTube / brand / Supporto Accessibile
- Versione pubblicata: non toccare; fix → versione successiva

## Come ripartire (prompt tipico)
«RTAD 1.8.9. Ultima pubblicata 1.8.8 il 28/10/2026: GitHub v1.8.8 / app-v1.8.8, commit 93faddb. DataStore #12565 chiuso via #12566, accettato. Non hotfixare la 1.8.8. Commit ee28948: finestra di benvenuto e guida HTML allineate; gli exe della Standalone sulla release sono stati sostituiti. Il pacchetto Add-on dello store resta quello accettato. Nel lettore, i PDF DocuSign firmati aprono il collegamento font–tabella anche dentro l’object stream. Maurizio ha riletto i tre testi salvati: Cechov, Dostoevskij e Puškin sono a posto. Sommario «Spett.le» e «PREMESSO», virgolette, «sub-licenze» e «proporVi» corretti dopo. «trascriv iamo» resta con lo spazio. Il numero nel programma è 1.8.9. I testi sono scritti. Non è ancora pubblicata. Confronto provato sulla Standalone. Pacchetto locale ricerca_testuale_accesso_digitale-1.8.9.nvda-addon. Il numero è nuovo: NVDA chiede il riavvio. I due exe li compila Maurizio. Dopo la pubblicazione, quattro cose non iniziate: Gemini su ogni risultato, VIDEO_TS (avviso, niente copia del film), OneCore, export multipli. Più avanti: confronto del parlato e del testo di un’immagine, poi un browser che segua i link. Piano: docs/PIANO_1.8.9.md.»
