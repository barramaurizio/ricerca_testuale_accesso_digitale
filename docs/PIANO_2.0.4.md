# Piano RTAD 2.0.4

**Pubblicata** il 15/11/2026. Versione `2.0.4`. GitHub `v2.0.4` / `app-v2.0.4`. Vale per Standalone e Add-on (punti 1–3). Il punto 4 solo Installer. A schermo e a voce. Il tasto e il gesto del mouse che fa la stessa cosa stanno nella stessa frase.

L’ultima pubblicata prima di questa è la `2.0.3` (14/11/2026, GitHub `v2.0.3` / `app-v2.0.3`, commit `20d8838`, DataStore #13027 via #13028 accettato). Non si rifà. In questo rilascio entrano anche quel commit corto e quel numero DataStore della 2.0.3, già nelle tre note.

## Primo punto

Nome file dal testo del post, il più lungo possibile. Oggi `post_piece` taglia a 80; i video già usano fino a 240 come il titolo pagina. Si allinea a quel tetto. Vale per Salva immagine e per le descrizioni da post (anche con 1, 2, 3 o 4). Esempio 14/11/2026: post twitorino Fan Village / Turismo Torino / #Torino #atpfinals. Se nel testo c’è un URL insieme alle parole, può restare se entra senza guai. Un testo che è solo un indirizzo non diventa il nome.

## Secondo punto

Dopo Salva video o Salva audio, Taglia e unisci (e Converti) dal risultato usano il file già salvato: stessa cartella e stesso titolo, non il `rtad_media_*` in `%TEMP%`. Il file tagliato si chiama `titolo-taglio`. Se per qualche motivo il risultato resta in Temp, Stato e Fatti dicono il percorso intero. Caso del 14/11/2026: originale salvato in Juve col testo, il `-taglio` era finito in Temp sul nome temporaneo.

## Terzo punto

Unione audio o video: con due file, `nome1-unione-nome2` (principio di entrambi se i titoli sono lunghi). Da tre in su: i primi due più `e-N` (es. `…-e-4`). Se il nome c’è già, si aggiunge `-2`. Il file di partenza resta com’è.

## Quarto punto

Invia a, solo Standalone installata. L’Installer scrive il collegamento `.lnk` in `shell:sendto` (`%AppData%\Roaming\Microsoft\Windows\SendTo`), che punta all’exe installato e segue gli aggiornamenti. Non si copia l’exe intero (copia ferma e pesante). Chi ha già il `.lnk` lo vede aggiornato al percorso corretto. Portable e Add-on: niente SendTo automatico; la guida resta.

## Resta fuori (versioni successive)

- Tutte le immagini di una pagina qualsiasi, con filtro e caselle.
- PDF e testo.
- Un audio su un video.
- Le immagini in un PDF.

## Idee future (da discutere con calma)

- Dettatura vocale.
- Un operatore integrato per passi poco accessibili o per chi è poco pratico.
- Confronto del parlato, confronto del testo di un’immagine, riga sulla figura di un EPUB.
