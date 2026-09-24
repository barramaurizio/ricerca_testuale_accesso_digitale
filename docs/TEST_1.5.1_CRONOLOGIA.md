# Test Standalone 1.5.1 — Cronologia ricerche

Copia sul PC i file aggiornati in `Standalone/` (soprattutto `app_gui.py`) e prova così, anche senza ricompilare subito:

```
cd Standalone
python app_gui.py
```

Oppure `compila.bat` + Inno come di consueto.

## Cosa verificare

1. Avvia una ricerca (testo + percorso qualsiasi) → deve funzionare come in 1.5.0.
2. **Ctrl+H** oppure pulsante **Cronologia** → elenco dei testi; scegline uno → compare nel campo testo e viene annunciato.
3. **Ctrl+Shift+H** → elenco percorsi; scegline uno → riempie il percorso.
4. Menu **Cronologia** → ultimi testi in fondo; **Svuota** testi/percorsi.
5. Chiudi e riapri l’app → la cronologia è ancora lì (file `settings.json` nella cartella config dell’app).
6. Regressione rapida: Feed Thunderbird, Alt+P (doppio = copia), Ctrl+F filtro, Invio sui `[FEED]`.

Se tutto ok, portiamo la stessa cronologia sull’Add-on e prepariamo il rilascio gemello.
