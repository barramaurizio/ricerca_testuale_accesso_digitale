# Text Search Accesso Digitale for NVDA / Ricerca Testuale Accesso Digitale per NVDA

**Author / Autore:** Maurizio Barra (Accesso Digitale)  
**Version / Versione:** 1.4.1  
**NVDA Compatibility / Compatibilità NVDA:** 2024.1.0 to 2026.2.0  
**License / Licenza:** GNU General Public License v2.0  

---

## English Documentation

### What's New in Version 1.4.1:
* **Critical Browse Mode Fix:** Completely eliminated single-letter gesture capture bindings (`F`, `H`, `S`). The sequential leader key layer (`NVDA + Shift + Control + F`) is now handled exclusively via a dedicated modal input manager with an automatic 3-second timeout. When inactive, all single keys are completely untouched, restoring full and uninterrupted Browse Mode navigation across web pages and virtual buffers.
* **Dialect and Special Character Search:** Fully normalized character matching for typographical curved apostrophes and quotation marks.
* **Multi-drive PC Scanning:** Fast drive detection with `Alt + T`.
* **Instant Speech Feedback:** Keyboard shortcuts (`Space` / `F4` for voice preview, `Alt + P` for progress announcement).

### Description
**Text Search Accesso Digitale** is an advanced accessibility add-on for the NVDA screen reader designed to perform rapid, in-depth text and keyword searches across documents, text files, images, and entire storage drives.

### Key Features
* **Global Shortcut:** Press `NVDA + Shift + Control + F` followed by `F` to open the search interface.
* **Scan Entire PC (`Alt + T`):** Scan every available drive and partition simultaneously with a single click or shortcut.
* **Live Progress Announcement (`Alt + P`):** Instantly hear the search percentage and examined file count at any moment.
* **Direct Jump to Exact Line:** Press `Enter` on any text result to open the document and place the cursor exactly on the matching line.
* **Instant Speech Preview:** Press `Space` or `F4` to hear an immediate audio preview of the text snippet without opening the file.
* **Export to Desktop:** Export all search results into a clean, structured `.txt` report saved directly to your Desktop.
* **Smart Context Menu (`Applications` key or `Shift + F10`):** Copy the matching context snippet, copy the full file content or image to the clipboard, reveal the file in Explorer, or copy it to another directory.
* **Custom Extension Filtering:** Filter searches by document types, media, images, or define your own custom extension (e.g. `.ini`, `.srt`, `.log`).
* **Multi-term Search:** Supports searching multiple keywords simultaneously with boolean AND logic.
* **Instant Screenshot:** Press `Alt + K` within the dialog to capture and save the screen directly into your screenshots directory.
* **In-App Documentation:** Press `NVDA + Shift + Control + F` followed by `H` to view the comprehensive HTML documentation.

---

## Documentazione in Italiano

### Novità della Versione 1.4.1:
* **Correzione Critica per la Modalità Navigazione:** Rimossa qualsiasi registrazione globale permanente per i tasti a lettera singola (`F`, `H`, `S`). Il tasto guida sequenziale (`NVDA + Shift + Control + F`) opera ora attraverso un gestore modale provvisorio con timeout automatico di 3 secondi. Quando il layer non è attivo, nessun tasto viene intercettato, garantendo la totale assenza di conflitti con la navigazione rapida per titoli o campi modulo sul Web.
* **Normalizzazione Ricerca Testuale:** Piena compatibilità con apostrofi tipografici ricurvi, virgolette e accenti in testi dialettali o formattati.
* **Scansione Tutto il PC:** Rilevamento istantaneo delle unità disco attive con `Alt + T`.
* **Feedback Vocale Rapido:** Scorciatoie `Spazio` o `F4` per ascoltare l'anteprima e `Alt + P` per la percentuale di avanzamento.

### Descrizione
**Ricerca Testuale Accesso Digitale** è un componente aggiuntivo per lo screen reader NVDA sviluppato per cercare parole, frasi ed elementi testuali all'interno di documenti, testi, immagini e intere unità di archiviazione.

### Caratteristiche Principali
* **Scorciatoia Globale:** `NVDA + Shift + Control + F` seguita da `F` per richiamare la schermata di ricerca.
* **Ricerca su Tutto il PC (`Alt + T`):** Scansiona tutti i dischi, partizioni e memorie collegate contemporaneamente con un solo clic o tramite scorciatoia rapida.
* **Annuncio Percentuale Istantaneo (`Alt + P`):** Vocalizza in tempo reale la percentuale e i file analizzati.
* **Salto Diretto alla Riga Esatta:** Premendo `Invio` sul risultato di un documento di testo, il file si apre posizionando automaticamente il cursore sulla riga corrispondente.
* **Anteprima Vocale Immediata:** Premendo `Spazio` o `F4` sull'elenco dei risultati, NVDA legge all'istante l'estratto testuale trovato.
* **Esportazione su Desktop:** Salva l'intero elenco dei risultati in un file `.txt` ordinato direttamente sul Desktop.
* **Menu Contestuale Avanzato (`Tasto Applicazioni` o `Shift + F10`):** Copia il frammento di contesto, copia tutto il testo o l'immagine grafica negli appunti, apri la cartella di origine o duplica il file altrove.
* **Filtro Estensioni Personalizzato:** Cerca per categorie (documenti, immagini, audio/video) oppure imposta un'estensione specifica a piacere (es. `.ini`, `.srt`, `.log`).
* **Ricerca Multi-termine:** Permette di inserire più parole chiave contemporaneamente con logica AND.
* **Cattura Schermo Istantanea:** `Alt + K` all'interno della finestra per salvare uno screenshot nella cartella dedicata.
* **Guida Completa Integrata:** `NVDA + Shift + Control + F` seguita da `H` per consultare la guida formattata nel browser.