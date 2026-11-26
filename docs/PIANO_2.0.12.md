# Piano RTAD 2.0.12

**Non iniziata.** Si apre dopo la 2.0.11 pubblicata il 26/11/2026 (GitHub `v2.0.11` / `app-v2.0.11`, commit `7b9f3e1`, DataStore #13290 via #13291 accettato). Vale per Standalone e Add-on. Non si tocca la `2.0.11` pubblicata.

Due cose, nella stessa versione.

## 1. Modificare e scrivere in un PDF

A voce e a schermo, la stessa frase: il testo che c’è, le pagine. Glielo hanno chiesto in diversi, e lo vuole anche Maurizio.

Acrobat è a pagamento. Firefox modifica i PDF: da provare per l’accessibilità, non è il programma. RTAD predefinito per i PDF, e un abbonamento per queste funzioni, restano più avanti, se Maurizio vorrà. Il dettaglio di finestra, tasti e motore si scrive quando si inizia. Questa nota ferma il senso.

## 2. Tutte le foto di un post su X

Dalla 2.0.3 l’elenco del post si ferma a quattro foto. Il 26/11/2026 X ne consegna di più. Il post https://x.com/juventusfc/status/2125892317617725946 («La Coppa Intercontinentale 1996») ne ha 6. La pagina HTML ha già i sei indirizzi `pbs.twimg.com`, in quest’ordine. RTAD ne ha date le prime quattro, in `J:\Juve`, con la descrizione accanto.

1. Del Piero nello spogliatoio, intervistato, coppa a palla d’oro fra le gambe.
2. In aereo: fascia del sol levante, Del Piero col ventaglio.
3. Nello spogliatoio, sorriso, coppa tenuta con due mani.
4. La formazione in campo, undici, di notte.
5. Manca: la festa in pedana, di notte, coppe alzate, fascia «EUROPEAN/SOUTH AMERICAN CUP WINNER», a destra una maglia col 3.
6. Manca: Del Piero di spalle col 10, un avversario in maglia bianca con la fascia rossa è a terra.

Il fermo è `_POST_IMAGE_LIMIT = 4` in `Standalone/rtad_ocr.py`, usato da `image_urls_from_html` nel ramo del post. Le altre pagine usano già `_PAGE_IMAGE_LIMIT = 40` e l’elenco con una casella vera per riga. La frase del post è già pronta per un numero qualsiasi: `post_images_choice_hint`. Si alza il limite del post così l’elenco mostra tutte le foto che la pagina consegna. Spazio sulla casella, o un clic, accende o spegne. Invio sul pulsante Scarica e descrivi, o un clic, prende le selezionate una dopo l’altra. Invio su Solo la prima, o un clic, prende solo la prima. Il nome resta il testo del post, con 1, 2, 3… Il navigatore dell’Add-on resta per la figura sotto il focus. Stessa cosa in Standalone e Add-on. Le caselle sono `wx.CheckBox`, una per riga.
