# Piano RTAD 1.8.5

**Ultima pubblicata:** `1.8.4` — 24/10/2026. Non hotfixarla.  
**Questa versione:** in corso, non pubblicata. Standalone e Add-on insieme. Cloud Vision resta l’OCR. Whisper non si apre.

## Cosa fare

1. Traduci il testo già aperto: la trascrizione di un video, il resoconto `.rtad.txt`, il testo di un documento nel lettore. Pulsante Traduci (Alt+U).
2. L’originale resta. La traduzione si aggiunge sotto. Nel video restano i timestamp.
3. La lingua di arrivo si sceglie. L’italiano è già selezionato. Gemini riconosce la lingua di partenza. Si usa la chiave Gemini già presente.
4. Un testo lungo va a pezzi, fino alla fine. A schermo e a voce si dice a che punto è. Alla fine: «Traduzione completa.» Un secondo clic interrompe.
5. Non parte da sola. Nell’analisi audio/video la casella «Traduci la trascrizione» è spenta, e si accende solo insieme alla trascrizione.

## Cosa non entra

- Un secondo motore (DeepL, Google Traduttore).
- Whisper.
- La traduzione automatica su ogni video.
- La promessa di proprio tutte le lingue: quelle solite, in elenco.
- Il confronto tra più file, Gemini su ogni risultato, VIDEO_TS, OneCore, export multipli.

## Prova

- Su un resoconto con trascrizione inglese e timestamp: Traduci. L’inglese resta. Sotto c’è l’italiano, con gli stessi timestamp. Si sente il pezzo, e alla fine «Traduzione completa.»
- Su un documento nel lettore: Traduci, lingua diversa dall’italiano. L’originale resta.
- Se c’è già una traduzione: «C’è già una traduzione. Vuoi sostituirla?»
- Nell’hub audio/video la casella è spenta. Accesa insieme alla trascrizione, il report esce già tradotto.
- Senza chiave Gemini: «Per tradurre serve la chiave Gemini, da Strumenti.»
