# Piano RTAD 2.0.7

**Pubblicata** il 18/11/2026. Versione `2.0.7`. GitHub `v2.0.7` / `app-v2.0.7`. Vale per Standalone e Add-on. A schermo e a voce. Il tasto e il gesto del mouse che fa la stessa cosa stanno nella stessa frase. Caselle di scelta: `wx.CheckBox` o `wx.RadioButton` vere (anche nell’Add-on con NVDA), non `CheckListBox`.

L’ultima pubblicata è la `2.0.6` (17/11/2026, GitHub `v2.0.6` / `app-v2.0.6`, commit `6bd826e`, DataStore #13083 via #13084 accettato). Non si tocca. Piano `docs/PIANO_2.0.6.md`.

## Perché questa versione

La 2.0.6 ha portato **Audio sul video** in sostituzione (anche su video muto) e Spazio ascolta/ferma. Mix, durata intera e controlli di ascolto con posizione/volume restano fuori da quella versione: altro pezzo di UI e di prove. Oggi li chiudiamo qui. Immagini in un PDF → `2.0.8`. PDF e testo → `2.0.9`.

## Primo punto (must) — Audio sul video: mix e durata

In Taglia e unisci, con un video e un audio in elenco, Invio sul pulsante **Audio sul video**, o un clic, apre le scelte (non parte subito come in 2.0.6).

1. **Modo**
   - **Sostituisci** (come nella 2.0.6, scelta predefinita): immagini del video, solo l’audio scelto.
   - **Mix / sovrapponi**: resta l’audio del video (se c’è) e sopra ci va l’audio scelto.
2. **Volumi** (in Mix tutti e due; in Sostituisci l’audio nuovo): da **0 a 200 percento**, a passi di 10, a schermo e a voce (SpinCtrl, non slider ciechi). Oltre 100: gain con soft-limiter (ffmpeg `alimiter` / tanh in ascolto), senza distorsione brusca, in stile VLC.
3. **Durata** — due caselle indipendenti (`wx.CheckBox`, Spazio accende/spegne):
   - spente tutte e due → più corto (come 2.0.6);
   - solo Tutto il video / solo Tutto l’audio / tutte e due;
   - casella spenta → ore/minuti/secondi con frecce su/giù per quel pezzo.

Nome file: resta `nomevideo-con-audio-nomeaudio.mp4` (se c’è già → `-2`, `-3`…). File di partenza intatti. Standalone e Add-on.

## Secondo punto — Ascolto con posizione, frecce e volume

Nell’ascolto/anteprima di Taglia e unisci (elenco di lavoro e Fatti):

- **Spazio**: pausa / ripresa **con orario** a schermo e a voce (es. «Fermato a 6 s», «Riparto da 6 s»). Non riparte sempre da zero.
- **Freccia destra / sinistra**: avanti / indietro di un passo (es. 5 s), con orario detto e mostrato.
- **Freccia su / giù**: alza / abbassa il volume di ascolto da 0 a **200 percento** (passi di 10), con livello detto e mostrato; oltre 100 in modo pulito.

Istruzioni scritte nella finestra. Stesso comportamento SA e Add-on.

## Resta fuori (versioni successive)

- **`2.0.8`:** le immagini in un PDF.
- **`2.0.9`:** PDF e testo (pagine da-a, più PDF nell’ordine, brano dal lettore).

## Idee future (da discutere con calma)

- Dettatura vocale.
- Un operatore integrato per passi poco accessibili o per chi è poco pratico.
- Confronto del parlato, confronto del testo di un’immagine, riga sulla figura di un EPUB.
