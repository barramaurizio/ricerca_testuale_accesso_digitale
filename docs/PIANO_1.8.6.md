# Piano RTAD 1.8.6

**Ultima pubblicata:** `1.8.5` — 25/10/2026. Non hotfixarla.  
**Questa versione:** in corso, non pubblicata. Standalone e Add-on insieme. Cloud Vision resta l’OCR. Gemini resta la trascrizione quando la chiave c’è e questa opzione è spenta.

**NVDA:** l’Add-on 1.8.5 è stato provato da Maurizio su NVDA 2026.3 e funziona. Nel pacchetto 1.8.6, `lastTestedNVDAVersion` diventa `2026.3.0`. Le novità 2026.3 non toccano il codice di RTAD: niente import di `braille` / `brailleInput`, niente API rimosse che l’Add-on usi. `minimumNVDAVersion` resta `2024.1.0`.

## Cosa fare

1. Trascrizione sul proprio PC, spenta di default. Si accende solo se si sceglie, su un file audio o video, oppure su una cartella piccola.
2. Nessun modello dentro l’installer né dentro l’Add-on. Al primo uso si scarica il modello, e lo si dice a voce e a schermo. Motore: eseguibile Whisper a parte (whisper.cpp), non una libreria Python dentro NVDA. Modello: `small`, multilingue. Non `large`.
3. Un file fino a 20 minuti. Una cartella fino a 5 file, ciascuno entro 20 minuti. Oltre, frase chiara e stop. Si può interrompere.
4. Funziona anche senza chiave Gemini. Se la chiave c’è e questa opzione è spenta, resta la trascrizione Gemini di oggi.
5. Il testo esce come `.rtad.txt`, nella stessa forma della trascrizione già nota. Da lì valgono già Chiedi a Gemini (1.8.4) e Traduci (1.8.5).
6. Stesse frasi a schermo e a voce, in Standalone e Add-on. Se manca il programma esterno o il modello non è ancora arrivato, la frase dice che cosa manca.

## Cosa non entra

- Un modello enorme nell’installer, o la trascrizione di tutta una raccolta.
- Il segnalibro di lettura dentro un PDF, un EPUB o un altro documento. I Segnalibri di oggi (Ctrl+D) salvano un percorso di ricerca, non il punto in cui si è arrivati a leggere. Confermato il 26/10: è la 1.8.7, il giorno dopo.
- Il confronto tra più file, Gemini su ogni risultato, VIDEO_TS, OneCore, export multipli.
- Un secondo motore di traduzione. La traduzione automatica su ogni video.

## Prova

Fatte da Maurizio il 26/10/2026, Standalone e Add-on, su NVDA 2026.3:

- Standalone, file locale, primo uso: si è sentita la preparazione e lo scaricamento, poi la trascrizione. Resoconto salvato da solo. Video musicale, 6 min 46 s.
- Add-on, file locale: stessa frase di preparazione e di trascrizione, resoconto salvato. Approfondimento sportivo, 9 min 57 s, timestamp fino a 9:51.
- Il tetto dei 20 minuti e la cartella da 5 file sono nel codice e nelle prove automatiche. Non sono stati cliccati a mano. Un URL non è stato provato: dopo lo scaricamento la trascrizione è la stessa, e il `.rtad.txt` si tiene con Salva testo.

## Da fare prima di pubblicare

- Add-on: il pacchetto `ricerca_testuale_accesso_digitale-1.8.6.nvda-addon` è già ricostruito, con `lastTestedNVDAVersion` = `2026.3.0`.
- Standalone: l’exe installato non è questa versione finché non si lancia `Standalone\compila.bat` e poi F9 su `setup.iss`.
