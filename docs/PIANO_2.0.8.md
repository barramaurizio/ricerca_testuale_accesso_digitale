# Piano RTAD 2.0.8

**Pubblicata** il 20/11/2026. GitHub `v2.0.8` / `app-v2.0.8`, commit `c8512b5`. Versione `2.0.8`. Vale per Standalone e Add-on. A schermo e a voce. Il tasto e il gesto del mouse che fa la stessa cosa stanno nella stessa frase. Caselle di scelta: `wx.CheckBox` o `wx.RadioButton` vere (anche nell’Add-on con NVDA), non `CheckListBox`.

L’ultima pubblicata prima di questa era la `2.0.7` (18/11/2026, GitHub `v2.0.7` / `app-v2.0.7`, commit `ddd1e43`). Non si tocca. Piano `docs/PIANO_2.0.7.md`.

## Perché questa versione

In Taglia e unisci c’è già un ascolto solido (Spazio, pausa con orario, frecce seek/volume, memoria per file, volume 0–200 pulito). Qui lo **ampliamo** in un **lettore audio/video interno** di RTAD, con segnalibri di posizione, ingressi da Windows e, quando è maturo, associazione / predefinito.

La chat Desktop della prima stesura è andata persa col PC Acer (scheda madre). Si ricostruisce da questo piano + codice 2.0.7. Le pezze anti-freeze di quella chat non si riprendono: era la tastiera senza pile.

Immagini in un PDF e PDF/testo → `2.0.9` / `2.0.10` (dopo il lettore).

## Regola per tutti (sempre)

Chi vede e chi non vede: **stessa informazione a voce e a schermo**.  
Trascinamento col mouse = **Control+Alt+V** (file copiato in Esplora) = pulsante **Incolla…**. Stesso effetto. Invio e clic sullo stesso pulsante. Non basta che NVDA lo dica.

## Must — Lettore interno

1. **Finestra dedicata** «Riproduttore» (o «Lettore audio/video»), Standalone e Add-on gemelli.
2. **Motore**: riusa `LiveListenPlayer` e la preparazione wav di Taglia e unisci (`rtad_clip.py`). Volume **0–200** percento, in modo pulito (già lì). Video a schermo: stessa posizione oraria; la parte visiva (finestra/ffplay) si completa senza spezzare l’audio.
3. **Controlli** (voce + schermo, SA e Add-on):
   - **Freccia destra** avanti (es. 5 s); **sinistra** indietro.
   - **Freccia su** alza volume; **giù** abbassa (passi come in Taglia/unisci).
   - **Spazio** = pausa / ripresa (stesso effetto del pulsante Pausa/Riprendi).
   - Pulsante **Pausa**: mentre suona resta etichetta «Pausa»; in pausa diventa «Riprendi». Invio o clic.
   - Pulsante **Ferma**: etichetta fissa «Ferma». Invio o clic.
   - Se si dà Invio/clic su **Ferma** (o si tenta di fermare) quando è **già fermo o in pausa**: avviso a voce e a schermo che la riproduzione è già ferma o in pausa.
4. **Istruzioni scritte** nella finestra (non solo guida), come da regola `rtad-per-tutti`.

## Must — Segnalibri di posizione (media)

Distinti dai Segnalibri di percorso (Ctrl+D) e dai punti di lettura documento (Ctrl+B). File dedicato, es. `media_marks.json` (cartella comune RTAD come gli altri).

1. **Senza tetto pratico** di quantità (non come i 100 del documento): se un giorno serve un tetto tecnico altissimo, si dice in guida.
2. Con audio/video in riproduzione, **Pausa** e **Ferma** creano **automaticamente** un segnalibro a quell’orario.
3. Nome predefinito = orario. Si può **rinominare**; in elenco restano **orario e nome** (es. `1:35 — Intervista`).
4. All’avvio dell’ascolto il focus va su **Pausa**, così Spazio e le frecce agiscono subito.
5. Alla **riapertura** del riproduttore sullo stesso file: dialogo che chiede se riprendere da quel punto («Ti eri fermato a …» + nome se rinominato) oppure ripartire dall’inizio. Stessa frase a voce e a schermo.
6. Elenco segnalibri del file: scegliere, rinominare, eliminare (Invio/clic come di consueto).

## Must — Ingressi Windows e menu

**Stato integrazione Windows (codice):** voce Explorer `Riproduci con RTAD` (`--play`) in tutti i menu Media; Invia a `Riproduttore RTAD`; ProgID `RTAD.AudioVideo` + OpenWithProgids + RegisteredApplications; Strumenti → Imposta riproduttore predefinito in Windows (`ms-settings:defaultapps`); menu risultato `Riproduci con RTAD`. Resto: prova Add-on + Installer locale di Maurizio.


1. Menu **Strumenti** (e impostazioni dove già si scelgono comportamenti SA): apri Riproduttore / preferenze legate al lettore.
2. **Cerca con Accesso Digitale** (Installer, `setup.iss`): su audio/video aggiungere voce **Riproduci** (o equivalente), senza togliere Taglia/Converti/analisi già presenti (`rtad-non-rompere-flussi`).
3. **Invia a**: il file audio/video apre il Riproduttore (Standalone installata), non solo l’analisi.
4. **Apri con** / **predefinito Windows**: quando il lettore è solido; scelta utente, senza rubare i flussi già usati per analizzare. CLI nuova tipo `--play "%1"`.

## Fuori da questa versione (subito dopo)

- Immagini in un PDF; PDF e testo (piani già nominati in roadmap).
- Dettatura vocale; operatore integrato; confronti parlato/immagine; riga su figura EPUB.

## Criterio «fatto»

- SA: apri un mp3/mp4 dal menu Strumenti e da CLI `--play`; Spazio/Pausa/Riprendi/Ferma e frecce come sopra; Ferma crea segnalibro; riapertura chiede ripresa; volume fino a 200.
- Stesso comportamento Add-on (voce NVDA).
- Voci Explorer/Invia a/Apri con allineate al piano, senza ridurre menu esistenti.
- Documenti e gemelli allineati (`rtad_release.py check`, `_sync_release_docs.py`) prima di «puoi compilare».

## File toccati (previsti)

- Nuovi: `Standalone/rtad_player.py` (+ gemello Add-on), `docs/PIANO_2.0.8.md`, note rilascio a fine ciclo.
- Aggiornati: `app_gui.py`, Add-on `__init__.py`, `setup.iss`, guide, novità, CLI, sync gemelli.

## Verifica PC nuovo (Maurizio)

Sul PC di riserva, in **Prompt dei comandi** o PowerShell:

```text
python --version
py -3 --version
where python
where ffmpeg
where ffprobe
ffmpeg -version
echo %PATH%
```

Serve: Python 3.x, `pip install -r Standalone/requirements-standalone.txt`, **e** `pip install -r Standalone/requirements-ocr-easy.txt` (EasyOCR+torch: senza di loro `compila.bat` fa un exe ~20 MB invece dei ~250 MB di GitHub). Poi ffmpeg+ffprobe e yt-dlp nel PATH (come sull’Acer). Verifica: `python -c "import easyocr, torch; print(easyocr.__version__, torch.__version__)"`. Prova: `python Standalone/app_gui.py` dalla cartella del clone. L’Add-on non bundla EasyOCR.
