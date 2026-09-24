# Checklist rilascio v1.5.0 — cosa fare sul PC (Maurizio)

Non sei imbranato: il flusso nuovo si impara una volta sola. Qui sotto c’è tutto, in ordine.

## Cosa ho già preparato io (non serve che me li re-incolli)

Questi file sono già allineati alla **1.5.0**:

- `Standalone/app_gui.py` (che stai già testando)
- `Standalone/version.txt`, `setup.iss`, `compila.bat`, `changelog.txt`, `requirements-standalone.txt`
- `addon/globalPlugins/ricerca_testuale/__init__.py` (cuore Add-On)
- `addon/manifest.ini`
- `addon/doc/it/readme.html` e `addon/doc/en/readme.html`
- `README.md`, `make_addon.py`
- `.gitignore` (come quello che hai già messo)
- Pacchetto pronto: `ricerca_testuale_accesso_digitale-1.5.0.nvda-addon`

## Cosa devi fare tu: copiare nella cartella GitHub

Cartella tipica:
`C:\Users\barra\Downloads\RicercaTestualeAccessoDigitaleGitHub`

Sostituisci/copia da questo lavoro Cursor i file sopra (stessa struttura cartelle).
Poi verifica con Notepad++ che in `app_gui.py` e in `addon/.../__init__.py` ci sia `APP_VERSION = "1.5.0"`.

---

## A) STANDALONE — Installer + Portable (sul tuo Windows)

Prerequisiti (una tantum):
```
pip install feedparser wxPython pywin32 pyinstaller
```

Ordine tassativo (come nel tuo master file):

1. Apri CMD nella cartella `Standalone`
2. Lancia: `compila.bat`
   - produce `dist\Ricerca Testuale Accesso Digitale.exe`
3. Apri `setup.iss` con **Inno Setup** e premi **F9**
   - produce `InstallerOutput\Setup_RicercaTestualeAccessoDigitale_v1.5.0.exe`
4. Solo dopo l’installer, in `dist` rinomina l’exe in:
   `RicercaTestualeAccessoDigitale_Portable_v1.5.0.exe`
5. Prova Portable e Installer a mano (anche con NVDA)
6. Sposta i vecchi Setup/Portable 1.4.x sul disco esterno

Nota: la compilazione Windows la fai **tu sul PC** (qui in cloud non generiamo i tuoi .exe finali).

---

## B) ADD-ON NVDA — come testarlo

### Opzione 1 (più semplice)
Usa il file già generato:
`ricerca_testuale_accesso_digitale-1.5.0.nvda-addon`

1. Copia quel file sul Desktop
2. Con NVDA attivo, Invio sul file (oppure NVDA → Strumenti → Gestore componenti aggiuntivi → Installa)
3. Riavvia NVDA se richiesto
4. Apri la ricerca (scorciatoia solita) e prova:
   - pulsante **Feed Thunderbird**
   - ricerca parola nei feed
   - casella occorrenze grezze
   - INVIO apre browser
   - NVDA annuncia messaggi (`ui.message`)

### Opzione 2 (rigenerare tu il pacchetto)
Nella root del progetto GitHub:
```
python make_addon.py
```
Nasce di nuovo `ricerca_testuale_accesso_digitale-1.5.0.nvda-addon`.

---

## C) GitHub Desktop + Release (quando i test vanno bene)

1. GitHub Desktop: commit su `main` tipo  
   `Aggiornamento Standalone e Add-on alla v1.5.0` → Push
2. Due release separate:
   - Tag `v1.5.0` → Add-On (allega `.nvda-addon`)
   - Tag `app-v1.5.0` → Standalone (allega Setup + Portable)
3. Poi issue sullo store NVDA (addon-datastore) con URL diretto del `.nvda-addon`

Testo novità pronto: vedi `docs/NOTE_RILASCIO_1.5.0.txt`

---

## Non serve darmi altri file ora

Hai già testato lo Standalone: ottimo.  
Per packaging ti basta **sincronizzare** i file che ho aggiornato e seguire A → B → C.

Se qualcosa non torna (messaggio di errore di `compila.bat` o install Add-On), incolla qui l’errore o uno screenshot con Ctrl+V.
