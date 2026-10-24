# Piano RTAD 1.8.4

**Ultima pubblicata:** `1.8.3` — 23/10/2026. Non hotfixarla.  
**Questa versione:** in corso, non pubblicata. Standalone e Add-on insieme. Cloud Vision resta l’OCR. Whisper non si apre.

## Cosa fare

1. Chiedere a Gemini da un `.rtad.txt` già salvato, senza rifare l’analisi.
2. Se accanto c’è ancora la foto, il video o il documento con lo stesso nome, quello resta il file di partenza. Il testo del `.rtad.txt` è il materiale già pronto.
3. Se l’originale non c’è più, la conversazione resta sul testo salvato e lo dice, a voce e a schermo: «Il file originale non è più accanto a questo resoconto. La conversazione resta sul testo salvato.»
4. Poi valgono Alt+A, il tetto di 12 e Shift+Invio.

## Cosa non entra

- Whisper, in una versione tutta sua.
- Il confronto tra più file come funzione a sé.
- Gemini su ogni risultato di ricerca.
- VIDEO_TS, OneCore, export multipli.
- Una riga di prompt o una regola di glossario sui nomi dei giocatori. Nello stesso video un nome può essere sbagliato due volte e giusto una (Savona di Motta).
- Le e-mail `.eml` come allegato di chat.

## Prova

- Su un `.rtad.txt` con il video accanto: Chiedi a Gemini. La frase dice il file di partenza. La domanda usa il testo già salvato. Il video non viene ricaricato.
- Su un `.rtad.txt` rimasto solo: la frase, a voce e a schermo, dice che l’originale non c’è più e che la chat resta sul testo salvato.
- Alt+A, Shift+Invio e il tetto di 12 restano come nella 1.8.3.

## Anche, dopo le prove del 24/10

- Un elenco ancora vuoto ha una frase vera, a schermo e in voce. Non resta «sconosciuto».
- Nell’Add-on, percorso impostato, testo salvato e risultati esportati si sentono anche dopo la chiusura della finestra.

Prove di Maurizio, 24/10 pomeriggio: i due casi del `.rtad.txt`, gli elenchi vuoti, Sfoglia e l’esportazione dei risultati. L’exe Standalone non è ancora compilato.
