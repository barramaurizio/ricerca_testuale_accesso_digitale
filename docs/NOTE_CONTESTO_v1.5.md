# Note di contesto — Ricerca Testuale Accesso Digitale v1.5

## Sorgente
- GitHub pubblico (release): https://github.com/barramaurizio/ricerca_testuale_accesso_digitale (finora 1.4.6 online)
- Cartella locale PC: `C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`
- Feed Thunderbird di Maurizio (riferimento):
  `C:\Users\barra\AppData\Roaming\thunderbird\Profiles\ncyqi6ka.default-release\Mail\Feeds`

## Workflow (Regola Zero)
1. Standalone `app_gui.py` — prova da CMD: `app_gui.py` nella cartella Standalone
2. Add-on NVDA gemello (solo dopo che Standalone è ok)
3. Compilazione Portable/Installer → GitHub release → store NVDA

## Stato codice in questo workspace
- `Standalone/app_gui.py` = **1.5.0** con miglioramenti feed (non ancora pubblicato su GitHub da Maurizio)
- Build: `version.txt`, `setup.iss`, `compila.bat` aggiornati a 1.5.0
- Dipendenza: `feedparser` (`Standalone/requirements-standalone.txt`)

## Come testare sul PC di Maurizio
1. Copia `Standalone/app_gui.py` (e idealmente `requirements-standalone.txt`) nella cartella Standalone locale
2. `pip install feedparser` (se non già presente)
3. CMD nella cartella Standalone → `app_gui.py`
4. Premi **Feed Thunderbird** (dovrebbe trovare `...\Mail\Feeds`) oppure incolla il percorso Feeds
5. Cerca una parola presente in un articolo dei tuoi feed
6. INVIO sul risultato `[FEED]` / `[RSS]` apre l’articolo nel browser

## Novità 1.5.0 (Standalone)
- Pulsante Feed Thunderbird (rileva profili)
- RSS/Atom URL + file `.rss/.atom/.xml` + `.opml`
- Feed locali: testo pulito, un risultato per articolo, Content-Base / base href
- Progresso anche sulla fase RSS
- Filtro risultati Ctrl+F, MBOX/EML come già previsto
