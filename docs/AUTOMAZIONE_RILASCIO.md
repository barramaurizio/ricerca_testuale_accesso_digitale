# Automazione rilascio RTAD

Obiettivo: snellire i passaggi **ripetitivi** (numeri di versione, pacchetto Add-on, testi pronti).  
Restano **sempre manuali**: codice delle novità, test, compile `.exe`, GitHub Desktop, Release Web, store NVDA.

## Cosa può fare lo script

| Comando | Effetto |
|---------|---------|
| `check` | Controlla che Standalone, Add-on, manifest, setup, README abbiano la **stessa** versione |
| `bump X.Y.Z` | Aggiorna i file tecnici + stub changelog + template note + ricostruisce `.nvda-addon` |
| `addon` | Solo ricostruisce il pacchetto Add-on (versione da `manifest.ini`) |
| `notes` | Genera `docs/NOTE_RILASCIO_X.Y.Z.txt` |
| `summary` | Stampa Summary commit, titoli tag Release, URL datastore |

## Come usarlo sul PC (Windows)

Nella root del repo GitHub (`RicercaTestualeAccessoDigitaleGitHub`):

1. Doppio clic su **`prepara_rilascio.bat`** (menu guidato), oppure  
2. Da CMD:

```bat
python tools\rtad_release.py check
python tools\rtad_release.py bump 1.5.2
python tools\rtad_release.py summary 1.5.2
```

Scorciatoia solo controllo: **`verifica_versioni.bat`**.

`make_addon.py` ora legge la versione da `addon/manifest.ini` (niente doppio aggiornamento del nome file).

## Cosa resta sempre a te

1. Scrivere/implementare le novità (con Cursor o a mano).  
2. Completare i bullet in `docs/NOTE_RILASCIO_…` e nel changelog.  
3. Test Standalone + Add-on.  
4. `Standalone\compila.bat` → Inno Setup → Portable.  
5. Pulizia: elimina `build\` e `*.spec`; **non** commitare `dist\` / `InstallerOutput\`.  
6. GitHub Desktop → Commit → Push.  
7. Due Release Web + issue addon-datastore.

## GitHub Desktop / Web: sync automatica?

- **GitHub Desktop** non viene “pilotato” dallo script (è voluto: tu controlli la spunta sui file).  
- Lo script prepara i file; Desktop fa Commit/Push.  
- Le Release Web e lo store restano un clic umano (controllo qualità).  
- In futuro, se un giorno userai `gh` (GitHub CLI) autenticato, si potrà aggiungere un comando opzionale `release` che crea i tag e carica gli asset: **non è obbligatorio oggi**.

## Flusso consigliato dalla 1.5.2 in poi

1. Sviluppo (Regola Zero: Standalone → Add-on).  
2. `python tools\rtad_release.py bump 1.5.2`  
3. Completa note/changelog/WhatsNew.  
4. Test.  
5. Compile Standalone.  
6. Desktop + Release + store (testi da `summary` / `NOTE_RILASCIO`).

Così non dimentichi più un `version.txt` o il `make_addon`, e tieni sotto controllo ogni passo critico.
