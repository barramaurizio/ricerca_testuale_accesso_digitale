Campioni per prove RTAD
=======================

prova_rtad_epub.epub
  Libro minimo per testare la ricerca EPUB (v1.5.9).
  (Se manca in questa cartella, era in un commit precedente:
   puoi riprenderlo dal repo o ricrearlo.)

rtad_prova_zip_1.6.1.zip
  Archivio di prova per ZIP opt-in (v1.6.1). Contiene sottocartelle e
  formati misti: .txt, .md, .html, .csv, .json, .log, .py, più un .bin
  e un .jpg finti (non devono dare hit sul contenuto).

Come provare l'EPUB
-------------------
1. Percorso = questa cartella (docs\campioni) oppure copia il file altrove.
2. Testo: MelagranoDigital (oppure accessibilità, biblioteca, Benvenuto).
3. Tipo: Tutti / Solo Documenti / estensione .epub.
4. Risultato atteso: [EPUB] con snippet sul capitolo.

Come provare lo ZIP (1.6.1)
---------------------------
1. Attiva la casella «Includi contenuti negli archivi ZIP».
2. Percorso = docs\campioni (o dove hai copiato lo zip).
3. Tipo: Tutti, oppure Solo Documenti (con ZIP opt-in i .zip entrano
   anche nel filtro Documenti), oppure estensione .zip.
4. Parole da cercare (una per volta):
   - squadlist  → hit in leggi_me.txt, note.html, esempio.py
   - maxwell    → hit in leggi_me.txt, appunti.md, contatti.csv
   - energia    → hit in leggi_me.txt, appunti.md, config.json, sessione.log
   - Acqui      → hit in note.html
5. Risultati attesi: prefisso [ZIP], location tipo
   «ZIP documenti/appunti.md riga 3».
6. Controlli negativi: cercando solo nel .bin/.jpg non deve uscire hit
   di contenuto (al più il nome file se coincide).
