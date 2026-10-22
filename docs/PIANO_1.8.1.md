# Piano RTAD 1.8.1

**Pubblicata** il 21/10/2026, lo stesso giorno della 1.8.0. Prove Maurizio OK.  
**Non hotfixare.** Il seguito è `docs/PIANO_1.8.2.md`.

## Cosa c’è nella 1.8.1

- Se Gemini non manda un testo, la domanda e il motivo restano scritti in Conversazione e nel log.
- Standalone installata: in Esplora file, «Cerca con Accesso Digitale» → «Chiedi a Gemini» sul file scelto.

## Rimandato

**Chiedi a Gemini partendo da un `.rtad.txt` già salvato**, senza rifare l’analisi.

Oggi la chat legge il report aperto in quel momento, oppure la cronologia già legata al file. Un resoconto salvato accanto alla foto o al video (scheda, OCR, trascrizione) non è ancora un ingresso. Maurizio lo aveva chiesto il 21/10, all’inizio della 1.8.0.

Comportamento previsto:

- Dal `.rtad.txt` (ricerca, Invio, o menu del risultato) si apre la conversazione sul **file originale** se RTAD lo ritrova accanto (stesso stem: foto, audio, video, documento).
- Il testo del `.rtad.txt` è il materiale già pronto. Non si richiama Gemini per ridescritvere o ritrascrivere.
- Se l’originale non c’è più, la chat resta sul testo salvato e lo dice.
- Stesse regole della 1.8.0: data di oggi, web con la casella, Apri fonte / Alt+F, Invio sull’elenco non apre il browser, cronologie SA e Add-on separate.

Prova: un `.rtad.txt` di un video o di una foto già analizzati, una domanda, salva. Poi lo stesso sull’Add-on.

## Se prima di domani arriva un feedback

Quel punto **sostituisce** la funzione qui sopra. Non si mettono insieme. Si annota in questo file e si parte da lì.

## Cosa non entra in 1.8.1

- Whisper, modelli scaricati, trascrizione offline. Resta in lista, versione dedicata: pesa, va provato da solo, non il giorno dopo la chat.
- Chat senza alcun file.
- Una conversazione su più file («confronta questi tre»). Solo dopo qualche giorno di uso della 1.8.0.
- Gemini su ogni risultato della ricerca.
- `.rtad.txt` orfani come novità a sé, VIDEO_TS, OneCore, export multipli.

## Come ripartire

Il punto «`.rtad.txt` già salvato» era passato a `docs/PIANO_1.8.2.md`.  
Il 21/10 sera il feedback di papà (503 e 429, credito ancora presente) lo ha sostituito: la 1.8.2 sistema quello. Il `.rtad.txt` resta in lista per la versione dopo.  
Titolo della prossima chat: **«RTAD 1.8.2»**.
