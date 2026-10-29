# Piano RTAD 1.8.8

**Pubblicata** il 28/10/2026. Non hotfixarla.  
GitHub `v1.8.8` / `app-v1.8.8`, commit `93faddb`. DataStore #12565 chiuso via #12566, accettato.  
Commit `ee28948`: finestra di benvenuto e guida HTML allineate. Gli exe della Standalone sulla release sono stati sostituiti. Il pacchetto Add-on dello store resta quello accettato.  
Provata da Maurizio il 28/10/2026. Standalone e Add-on insieme. Il modulo è `rtad_media.py`, gemello.

Prova superata. Analisi rifatta sui due MP4, una con l’Add-on e una con la Standalone: Spalletti e Zliani («A TUTTO GOL») riportano durata, risoluzione e forma. Glossario acceso, in entrambi i programmi il lettore dice Alajbegović. La guida HTML, aperta nell’Add-on incollando il percorso, si legge come testo. La stessa pagina non è stata rifatta nella Standalone: la funzione è la stessa.

## Prima cosa: scheda tecnica di un MP4 grosso

Provato il 27/10 alle 18:31 sul file

`I:\Juve\“NON CONTA CHI PARTE, CONTA COME ENTRI”   Spalletti pre Genoa-Juventus!.mp4`

786747932 byte (750,30 MB). Nel resoconto accanto, la scheda dice:

- Forma: Video (forma non classificata).
- Durata: non rilevata.

Il video è intero. ffprobe legge: H.264, 1920×1080, AAC, 1339 secondi (22 min 19 s). La trascrizione nel `.rtad.txt` arriva a `[22:13]`. Esplora file mostra subito durata e dimensioni. Rianalizzare con la 1.8.7 non ricalcola: se il `.rtad.txt` c’è già, resta com’è e la risposta arriva subito.

Struttura del file: `ftyp`, `free`, `mdat` da 785345672 byte, poi `moov` all’offset 785345712 (1,4 MB). L’indice è in fondo.

Due buchi in `get_media_tech_info`:

1. `_locate_mp4_moov_bytes` incolla i primi 32 MB e gli ultimi 16 MB. `moov` è in quella coda, ma `_read_mp4_boxes` si ferma sul `mdat` perché il box è più grande del buffer. La scansione che leggerebbe solo `moov` non parte, perché la parola `moov` è già nel buffer incollato. `_mp4_tech` quindi non vede `mvhd` né `tkhd`.
2. `_ffprobe_tech` legge il testo con la codifica di Windows (`text=True`, cp1252). Il nome ha le virgolette curve “ ” (byte UTF-8 `9d`). La lettura si rompe, il JSON si butta, il risultato è vuoto. Lo stesso vale per un nome con emoji.

Esito atteso dopo la correzione, a schermo e a voce: durata 22 min 19 s, risoluzione 1920 x 1080, forma «Video normale». Per vederla su questo file bisogna rifare l’analisi e non riusare il resoconto del 27/10.

Stesso buco, confermato il 28/10 alle 09:17 sul file

`I:\Juve\A TUTTO GOL ⚽️ VOGLIONO PORTARE IL CALCIO A MILANO 🥶 IL TENNIS SUPERA LA FIGC 😂 WOLTE O KOLO.mp4`

203624878 byte. `ftyp`, `free`, `mdat` da 203010350 byte, `moov` all’offset 203010390. Nel `.rtad.txt` delle 09:17 la scheda dice ancora «forma non classificata» e «durata non rilevata». Il nome ha le emoji. Con il codice nuovo la scheda legge 10 min 34 s, 1920 x 1080, «Video normale». La trascrizione arriva intorno a `[10:01]`. Anche questo resoconto va rifatto, non riusato. Nel codice del 28/10 i due buchi sono chiusi: l’indice si legge saltando il `mdat`, e ffprobe si decodifica in UTF-8.

## Subito dopo: glossario anche nel lettore

Provato la sera del 27/10 sullo stesso resoconto. In Standalone il glossario è attivo. Regola salvata: `Almqvist` → `Alajbegović`. Nel file la parola c’è ancora, intera, intorno a 2:43, 4:24 e 15:30.

`apply_glossary_to_rtad_txt_file` riscrive il `.rtad.txt` solo all’apertura da un risultato di ricerca, poi il file va al programma predefinito (Notepad++). «Leggi documento» chiama `read_document_file` e non passa di lì, quindi il lettore mostra «Almqvist». Una nuova analisi non riscrive un resoconto già presente.

Nel lettore, Standalone e Add-on, con glossario attivo: prima la stessa riscrittura, poi il testo corretto a schermo e a voce. Prova: «Leggi documento» su quel `.rtad.txt` deve dire «Alajbegović». Il file sul disco resta allineato. Nel codice del 28/10 «Leggi documento» e «Copia testo del documento» chiamano quella riscrittura prima di leggere.

## Poi: una pagina HTML nel lettore

Chiesta la sera del 27/10. «Leggi documento» su un `.html` o `.htm` legge il file come testo puro (`extract_document_text` → `extract_plain_text_file`). Si sentono i tag e i codici, come gli EPUB prima della 1.8.7. La guida HTML è il caso visto. `strip_html_to_text` esiste già per mail e feed, e negli EPUB `html.unescape` copre tutte le entità, ma il lettore dei file HTML non le usa.

Nel lettore, Standalone e Add-on: togliere script, style e tag; titoli, paragrafi e voci di elenco restano righe; `html.unescape` trasforma ogni entità nota e ogni codice numerico in lettera o segno. Non si elenca a mano. Non è un browser: niente JavaScript, niente impaginazione, niente immagini della pagina. Vale per un file locale aperto con «Leggi documento», copia e ricerca comprese. Nel codice del 28/10 lettore, copia e ricerca passano da `strip_html_to_text`, titoli e voci di elenco compresi.

## Poi, chiesto il 28/10: il file e l’indirizzo nell’elenco

Sfoglia, singolo file, anche un `file:///…` della guida: il lettore si apriva e l’elenco dell’Add-on restava su «Nessuna ricerca avviata». Nel pomeriggio del 28/10 Maurizio ha confermato, in Add-on e in Standalone, le 16 voci e la lettura.

Un indirizzo `http` o `https` nel campo percorso si scarica. A schermo e a voce: «Scarico la pagina: nome. Attendere.», poi «L'indirizzo è in elenco: nome. Da qui puoi fare altre operazioni.» Il menu è quello del file, più «Apri pagina nel browser». Il lettore non si apre da solo: si apre da «Leggi documento». Da Sfoglia, se la pagina arriva come file, restano le stesse voci di un documento e la domanda di aprirlo nel lettore. YouTube e il filtro Solo Audio e Video aprono ancora l’hub. Un audio o un video già scaricato resta in elenco: «Il file è in elenco: nome. Da qui puoi fare altre operazioni.»

Confermato da Maurizio il 28/10, in entrambi i programmi. Il lettore HTML non segue i link: resta un passo successivo.

## Poi, se non arriva altro

Lista già concordata, nello stesso ordine, dopo la scheda:

- confronto tra più file
- Gemini su ogni risultato
- VIDEO_TS
- OneCore
- export multipli

Un feedback vero, o un altro file che si comporta male, passa davanti a questa lista.

## Cosa non entra

- Un secondo motore di traduzione. La traduzione automatica su ogni video.
- Qualsiasi ritocco a Whisper. La 1.8.6 resta com’è.
- Un hotfix della 1.8.7 già pubblicata.
