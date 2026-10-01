# Ricerca Testuale Accesso Digitale / Text Search Accesso Digitale (v1.5.9)
**Autore / Author:** Maurizio Barra (Accesso Digitale)

---

## 🇮🇹 Italiano

Uno strumento di ricerca testuale avanzata progettato per facilitare l'accessibilità e il recupero rapido di informazioni all'interno del computer. Disponibile sia come **Componente Aggiuntivo (Add-on) per NVDA** sia come **Applicazione Standalone (.exe)**.

### 🌟 Novità della Versione 1.5.9

*(In corso — ultima pubblicata: **1.5.8**.)*

- **Guida pratica** (menu Aiuto): linguaggio semplice; a ogni release le novità sono aggiornate lì, in parallelo alla guida tecnica.
- Ricerca nei libri **EPUB** (`.epub`), risultati `[EPUB]`; nel filtro Documenti.
- Restano OCR 1.5.8, voce 1.5.7, posta 1.5.6, date, profili.

### 🌟 Novità della Versione 1.5.8

*(Pubblicata.)*

- **OCR opt-in:** testo in immagini e PDF scansionati; risultati `[IMG-OCR]` / `[PDF-OCR]`; cache e profili.
- Motori: **Windows.Media.Ocr** (predefinito) oppure **EasyOCR** opzionale (Standalone consigliata per EasyOCR).
- Preprocess + match fuzzy; sinonimi birthday↔compleanno; **Copia Testo pulito** / **Copia OCR completo**.
- OCR senza parola chiave (OCR attivo + testo vuoto → Avvia). Restano voce 1.5.7, posta 1.5.6, date, profili.

### 🌟 Novità della Versione 1.5.7

- **Voce Standalone:** velocità SAPI (Ctrl++ / Ctrl+-), tono, scelta voce (anche OneCore), menu Voce, salvataggio.
- Annunci RTAD con SAPI regolabile (oppure NVDA). **F7** Mute persistente.
- **Add-on gemello:** Mute annunci RTAD (F7); velocità/voce = impostazioni NVDA.
- Restano posta completa 1.5.6, date, profili e filtri.

### 🌟 Novità della Versione 1.5.6

- **Posta completa:** caselle Thunderbird/MBOX senza tetto di dimensione (streaming); anche messaggi con allegati PDF grandi.
- Filtro **`.pdf`**: include caselle posta/.eml e cerca negli allegati; **Apri/Salva allegato PDF** (non l’INBOX intera).
- Meno rumore: esclusi WinSxS, cache Cursor e log RTAD; stato con messaggi posta e hit allegati.
- Tetto ~40 MB per DOC/testi; **PDF ~80 MB**. Restano stabilità 1.5.5, feedparser, date e profili.

### 🌟 Novità della Versione 1.5.5

- **Stabilità / anti-blocco:** niente «Non risponde» su cartelle grandi e PDF/DOC difficili (es. G:\), **senza ridurre** le ricerche normali.
- Tetto decompressione PDF; timeout soft solo sui file che si bloccano; `.doc` OLE senza ZipFile inutile.
- **Data (gg/mm/aaaa) su tutti i risultati:** txt, Word, media, immagini, nome file… come già per email e PDF.
- File molto grandi (> ~40 MB): ricerca sul **nome**; Alt+S/avanzamento più leggeri; indicizzazione cartelle visibile.
- Add-on: **feedparser incluso** (RSS/Atom in NVDA); **`.eml`/MBOX** come nello Standalone (un risultato per messaggio).
- Restano i **profili** e i filtri della 1.5.4.

### 🌟 Novità della Versione 1.5.4

- **Profili di ricerca:** salva percorso, tipo file, opzioni e (opzionale) testo; menu Profili; Ctrl+Shift+P / Ctrl+Shift+L.
- Gestisci profili: rinomina o elimina.
- **Filtri tipologici più ricchi:** più estensioni in Immagini, Audio/Video e Documenti (es. m4a, flac, webp, html, md…).
- **Scorciatoie Alt senza conflitti:** una sola azione per lettera (T/P/N/I/S/K); Avvia con INVIO nel campo testo.
- Restano le novità 1.5.3 (PDF testo/immagini, Copia/Salva Immagine).

### 🌟 What's New in Version 1.5.9

*(In progress — last published: **1.5.8**.)*

- **Practical guide** (Help menu): plain language; each release updates the simple “what’s new” there, alongside the technical guide.
- Search inside **EPUB** books (`.epub`), `[EPUB]` results; included in Documents filter.
- 1.5.8 OCR, 1.5.7 voice, 1.5.6 mail, dates and profiles remain.

### 🌟 What's New in Version 1.5.8

*(Published.)*

- **Opt-in OCR:** text in images and scanned PDFs; `[IMG-OCR]` / `[PDF-OCR]`; cache and profiles.
- Engines: **Windows.Media.Ocr** (default) or optional **EasyOCR** (Standalone recommended for EasyOCR).
- Preprocess + fuzzy match; birthday↔compleanno synonyms; **Copy clean text** / **Copy full OCR**.
- OCR without a query (OCR on + empty text → Start). 1.5.7 voice, 1.5.6 mail, dates, profiles remain.

### 🌟 What's New in Version 1.5.7

- **Standalone voice:** SAPI rate (Ctrl++ / Ctrl+-), pitch, voice picker (incl. OneCore), Voice menu, persistence.
- RTAD announcements via adjustable SAPI (or NVDA). **F7** persistent Mute.
- **Twin Add-on:** Mute RTAD announcements (F7); rate/voice = NVDA settings.
- 1.5.6 complete mail search, dates, profiles and filters remain.

### 🌟 What's New in Version 1.5.6

- **Complete mail search:** Thunderbird/MBOX with no mailbox size cap (streaming); large PDF-attachment messages included.
- **`.pdf` filter:** also scans mailboxes/.eml for PDF attachments; **Open/Save extracted PDF** (not the whole INBOX).
- Less noise: WinSxS, Cursor caches and RTAD logs excluded; status reports mail messages and attachment hits.
- ~40 MB for DOC/text; **PDF ~80 MB**. 1.5.5 stability, feedparser, dates and profiles remain.

### 🌟 What's New in Version 1.5.5

- **Stability / anti-freeze:** no “Not responding” on large folders or awkward PDF/DOC (e.g. external drives), **without limiting** normal searches.
- PDF inflate hard cap; soft timeout only for stuck files; legacy OLE `.doc` skips useless ZipFile.
- **Date (dd/mm/yyyy) on every result:** txt, Word, media, images, file name… same as email and PDF.
- Very large files (> ~40 MB): match on **name**; lighter Alt+S/progress; visible folder indexing.
- Add-on: **bundled feedparser** (RSS/Atom in NVDA); **`.eml`/MBOX** match Standalone (one result per message).
- 1.5.4 profiles and filters remain.

### 🌟 What's New in Version 1.5.4

- **Search profiles:** save path, file type, options and (optional) query; Profiles menu; Ctrl+Shift+P / Ctrl+Shift+L.
- Manage profiles: rename or delete.
- **Richer type filters:** more extensions for Images, Audio/Video and Documents (e.g. m4a, flac, webp, html, md…).
- **Conflict-free Alt shortcuts:** one action per key (T/P/N/I/S/K); start search with Enter in the query field.
- 1.5.3 features remain (PDF text/images, Copy/Save Image).


### 🌟 What's New in Version 1.5.2
- **Safer email/MBOX viewer:** background loading; PDF/binary attachments skipped in displayed text.
- **Message date** (dd/mm/yyyy) also in MBOX and `.eml` results.

### 🌟 What's New in Version 1.5.1
- **Search history:** recent queries and paths kept locally; `Ctrl+H` / Cronologia button and `Ctrl+Shift+H`; Cronologia menu.

### 🌟 What's New in Version 1.5.0
- **RSS/Atom feeds:** search http(s) URLs, local `.rss`/`.atom`/`.xml` files and OPML lists; multiple paths separated by `;` or `,`.
- **Thunderbird Feeds:** dedicated button to auto-detect `Mail\Feeds` folders; cleaned-text search (one result per article) and open the original link in the browser.
- **Optional raw occurrences:** checkbox to also list `[FEED-RIGA]` lines besides articles, with jump-to-line in an editor.
- **Sort by article date** for feeds and a status note comparing raw occurrences to distinct articles.

### Key Features
- **Multi-format support**: Search across text files (`.txt`, `.log`, `.csv`), Word documents (`.docx`, `.doc`), PDF files, emails (`.eml` with native reader), RSS/Thunderbird feeds, and images with basic OCR scanning (`.jpg`, `.png`, `.bmp`).
- **Multiple keywords**: Supports flexible searches with multiple terms.
- **Automatic path memory**: Remembers the last searched folder to speed up workflows.
- **Global scan**: Ability to scan the entire PC across all active drives with a single command.

### How to reach the exact text in Word documents
For Microsoft Word documents, the add-on opens the file cleanly and safely. You can instantly reach the exact phrase by following these steps:
1. In the add-on results list, press the **Applications Key** on the desired Word file.
2. Select **"Copy News Block / Phrase with keyword"**.
3. Open the Word document directly from the results.
4. Press the shortcut **`Control + Shift + T`** to trigger targeted search.
5. Paste the copied text with **`Control + V`** and press **Enter**.
6. When the speech synthesizer announces the result and the next button, press **`Esc`**: the cursor will position itself precisely over the searched text, ready for reading (`NVDA + Down Arrow`).

*(Note: For those who prefer instant automatic opening without manual steps, the **Standalone .exe** version is also available).*

### Keyboard Shortcuts (NVDA Add-on)
- `NVDA + Shift + Control + F`: Open the main search window.
- `NVDA + Shift + Control + S`: Open the shortcuts and info dialog.
- `NVDA + Shift + Control + D`: Open the PayPal donation page.
- In the window: `Ctrl+F` filters results, `Alt+P` announces status (twice = copy), `Ctrl+U` checks for updates, **Feed Thunderbird** button for local RSS Feeds.
- Full guide (IT/EN): `addon/doc/it/readme.html` and `addon/doc/en/readme.html` (also via Add-on Manager → Help).

---

## 📦 Download & Install
Scarica l'ultima versione rilasciata (`.nvda-addon` o la versione `.exe` standalone) dalla sezione [Releases di GitHub](https://github.com/barramaurizio/ricerca_testuale_accesso_digitale/releases).

---
*Sostieni il progetto / Support the project:* [PayPal](https://paypal.me/AccessoDigitale) | [YouTube](https://www.youtube.com/@AccessoDigitale)
