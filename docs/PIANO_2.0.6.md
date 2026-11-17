# Piano RTAD 2.0.6

**Pubblicata** il 17/11/2026. Versione `2.0.6`. GitHub `v2.0.6` / `app-v2.0.6`. Commit `6bd826e`. Vale per Standalone e Add-on. A schermo e a voce. Il tasto e il gesto del mouse che fa la stessa cosa stanno nella stessa frase. Caselle di scelta: `wx.CheckBox` vere (anche nell’Add-on con NVDA), non `CheckListBox`.

L’ultima pubblicata prima di questa era la `2.0.5` (16/11/2026, GitHub `v2.0.5` / `app-v2.0.5`, commit `3e83931`, DataStore #13068 via #13069 accettato). Non si tocca.

## Perché questi due pezzi

Il bug immagine+video e «un audio su un video» (sostituzione) stanno sullo stesso filone media. Mix, volumi e durata intera restano fuori: altro pezzo di UI e di prove → `2.0.7`.

## Primo punto (must) — OK in prova

Post o pagina con **immagine e video**: entrambi i flussi, menu completo (~21 voci) dopo lo scarico. Caso Juventus X. SA e Add-on. Regola: `.cursor/rules/rtad-non-rompere-flussi.mdc`.

## Secondo punto — OK in prova

**Audio sul video** (sostituzione): in Taglia e unisci, un video + un audio → pulsante **Audio sul video** (Alt+V). Nel file nuovo: immagini del video, **solo** l’audio scelto (l’audio originale del video non resta sotto). Utile anche se il video è muto. Nome: `nomevideo-con-audio-nomeaudio.mp4`. Se il nome c’è già → `-2`, `-3`… Durata: il più corto; se l’audio è più corto, il video nuovo dura quanto l’audio. Copertine negli mp3 (`attached_pic`) non contano come video. Standalone e Add-on.

## Lucidatura in 2.0.6

- Spazio sull’elenco di lavoro e sui Fatti = ascolta; se sta già suonando, Spazio ferma. Invio sui Fatti resta «rimetti in elenco».

## Resta fuori (versioni successive)

- **`2.0.7`:** Audio sul video — **mix/sovrapposizione** con volumi regolabili; scelte di durata (più corto / tutto il video / tutto l’audio). In ascolto/anteprima: freccia destra/sinistra avanti/indietro; freccia su/giù volume; Spazio in pausa/ripresa con orario a schermo e a voce (es. «fermato a 6 s», «riparto da 6 s»).
- **`2.0.8`:** le immagini in un PDF.
- **`2.0.9`:** PDF e testo (pagine da-a, più PDF nell’ordine, brano dal lettore).

## Idee future (da discutere con calma)

- Dettatura vocale.
- Un operatore integrato per passi poco accessibili o per chi è poco pratico.
- Confronto del parlato, confronto del testo di un’immagine, riga sulla figura di un EPUB.
