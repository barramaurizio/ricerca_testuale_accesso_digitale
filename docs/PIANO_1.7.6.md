# Piano RTAD 1.7.6

**Ultima pubblicata:** `1.7.5` — OCR orizzontale, Trova copie, Incolla Appunti.  
GitHub `v1.7.5` / `app-v1.7.5`; DataStore #12270 → #12272 (accepted 18/10/2026).  
**Questa versione:** `1.7.6`. **Non hotfixare 1.7.5.**

Vedi `docs/ROADMAP_DOPO_1.5.0.md` e `docs/NOTE_CONTESTO_v1.5.md`.

---

## Spirito della 1.7.6

Patch **utile e rassicurante**: chiudere i feedback 1.7.5 (drop, updater che
sporca Download, report a riga unica) + aprire le unità ottiche. Whisper
resta opt-in se c’è tempo e resta leggero. Niente major 2.0.

---

## Feedback già raccolti (18/10, papà + log)

1. **Drag & drop SA non funzionava** in 1.7.5 pubblicata: `DragAcceptFiles`
   solo sul Frame; i file cadono sul Panel → nessun evento.  
   Fix già in codice locale (`_enable_file_drop_targets` su Frame+Panel+campo
   percorso + log `Drop file ricevuto`). **Da includere in 1.7.6.**
2. **Updater Installer** scarica `Setup_…exe` in `%USERPROFILE%\Downloads`,
   lo avvia, e il file **resta** → «Trova copie» lo propone come copia sicura
   a ogni aggiornamento (log papà 18:19: download Setup 1.7.5 in Download).
   Comportamento corretto per Trova copie, **sbagliato come UX update**.
3. **CD audio**: shell apre `E:\Track05.cda` / `F:\Track11.cda`; ricerca su
   `F:\` con testo `.cda` → 0 file. I `.cda` non sono audio veri (shortcut
   Windows alle tracce). Serve: unità ottiche in «Tutto il PC» + messaggio
   chiaro su `.cda` vs file dati sul DVD.  
   Campioni `.cda` ricevuti (18/10 sera): `Track01.cda` / `Track03.cda`
   (44 byte, RIFF/CDDA) — utili per messaggi e smoke.
4. **Report a riga lunghissima** (audio/video, immagini, documenti, ecc.):
   in SA le finestre report usano `wx.HSCROLL` → una sola riga orizzontale;
   con NVDA (cursore) si seleziona bene, ma a occhio / Incolla in Word è
   scomodo (papà ha dovuto regolare a mano; file Word ricevuti ma non
   necessari — intervento già chiaro). Serve **wrap uniforme** su tutte
   le descrizioni / report, in finestra e nel testo copiato/salvato.
5. **OCR «Leggi testo immagine»** (retest papà 18/10 sera): **OK / perfetto**
   (fix 1.7.5 confermato; niente da rifare in 1.7.6 su quel punto).

---

## Priorità consigliate (ordine)

### P0 — Fix drop + updater senza sporcare Download (SA)

**P0a — Drag & drop**  
Ship del fix già pronto (Panel + Frame + `txt_path`). Criterio: trascina JPG
sulla finestra → percorso impostato + eventuale «Apri ora»; riga nel log.

**P0b — Download aggiornamento fuori da Download**  
- Cartella dedicata, es.  
  `%LocalAppData%\Programs\…` no — meglio:  
  `%LocalAppData%\RTAD_Standalone\updates\`  
  (o sotto Roaming solo se già usiamo quella; preferire Local per i binari).
- L’updater Setup/Portable scarica **lì**, avvia l’exe, poi:
  - elimina il file dopo `Popen` riuscito, **oppure**
  - lo lascia in `updates\` e alla prossima verifica aggiornamenti / avvio
    cancella Setup/Portable vecchi in quella cartella.
- **Mai** scrivere di default in `Downloads` per l’update automatico.
- Download manuale da GitHub in Download: resta affare dell’utente;
  Trova copie continua a proporli come «sicuri» (consenso).

**P0c — Trova copie / `rtad_copie.py` / script `.ps1` (allineamento)**  
- **Non** classificare come «copia sicura da rimuovere» i file sotto
  `%LocalAppData%\RTAD_Standalone\updates\` (cartella gestita dal programma).
- Opzionale: nel rapporto una nota «cartella aggiornamenti RTAD (gestita in
  automatico)».
- Script `tools/rtad_trova_copie.ps1`: stessa regola (non proporre
  cancellazione di `updates\`).
- Guida: spiegare che l’update automatico non lascia più exe in Download;
  Trova copie serve per Setup/Portable **scaricati a mano** o copie confusive.

### P1 — Unità CD/DVD in «Tutto il PC» (SA; Add-on se condivide la stessa helper)

- Includere drive type **CDROM (5)** quando l’unità è pronta.
- Accettare `E:\` / `F:\` da Sfoglia / percorso.
- Se il percorso punta a `.cda` o a sola audio CD: messaggio accessibile
  («questa traccia non è un file audio sul disco; per i CD audio…» /
  indicare limiti onesti).
- File **dati** su DVD/CD (mp3, pdf, jpg in cartelle): devono essere
  cercabili come su un’unità USB.
- `VIDEO_TS` commerciale: avviso chiaro, niente ripping in 1.7.6
  (candidare 1.7.7+).

Campione utile: ISO o DVD con pochi mp3/pdf; `.cda` già in Download (Track01/03).

### P1b — Marker Installer più esplicito (SA)

Inno / primo avvio: marker `install_channel=installer` (file o setting),
così l’updater non dipende solo da Program Files / `unins000.exe`.

### P1c — Righe standard nei report / descrizioni (SA; Add-on se stessa UI)

**Problema:** finestre report con `TE_MULTILINE | … | HSCROLL` → niente a capo
automatico; selezione/copia “a occhio” e Incolla in Word scomodi.

**Obiettivo:** testo leggibile e selezionabile in modo classico, **uniforme**
per tutti i tipi (immagine, AV, documento, Trova copie, ecc.).

**Direzione tecnica (da confermare in implementazione):**
1. **UI:** togliere `wx.HSCROLL` (o equivalente) dai `TextCtrl` dei report
   così wx fa word-wrap a larghezza finestra; barre verticali ok.
2. **Testo “duro” (copia / salva / sidecar):** helper unico tipo
   `wrap_report_text(s, width=72)` (o 70–80) che spezza a spazio senza
   rompere URL/path lunghi in modo aggressivo; usarlo ovunque si mostra o
   esporta una descrizione/analisi.
3. Non cambiare il contenuto semantico del report, solo la presentazione
   a riga.

**Criterio:** aprire un report immagine o AV → righe “normali”; Ctrl+A /
copia → in Word le righe restano spezzate in modo sensato; stesso aspetto
su tutti i tipi di analisi.

### P2 — Whisper locale opt-in (solo se P0–P1 chiusi e resta tempo)

Opt-in, cartella/file piccoli, niente modelli enormi bundlati di default.

### P2b — Guida / novità

Documentare: drop, updater silenzioso, CD/DVD, report a righe standard,
Trova copie aggiornato; EN se tempo.

### P3 — Opzionali

- Profilo «solo AV + Trascrivi e cerca»  
- Ricerca nei soli `.rtad.txt`  
- Cronologia file aperti da Explorer  

---

## Idee buone per dopo (1.7.7+)

| Idea | Note |
|------|------|
| DVD / VIDEO_TS conscious | Oltre unità ottica + file dati |
| OneCore native voce SA | Dopo Whisper |
| Export report multipli | Un `.rtad.txt` / HTML |
| Add-on: più azioni da focus Explorer | Spiriti menù SA |
| YouTube / brand | Chat dedicata |

---

## Cosa NON mettere in 1.7.6 di default

- Whisper di massa / modelli giganti bundlati  
- Shell context menu nell’Add-on  
- Major 2.0  
- Continuare a scaricare Setup in Download (da eliminare come default)

---

## Criterio “1.7.6 pronta”

- [x] Drop SA funziona (mouse / log `Drop file ricevuto`) — prova papà 19/10  
- [x] Updater non lascia Setup/Portable in Download; cartella `updates\` gestita  
- [x] Trova copie / script allineati (niente «sicuro» su `updates\`)  
- [x] Unità ottiche in «Tutto il PC» + comportamento onesto su `.cda`  
- [x] Report / descrizioni con righe standard (UI wrap + testo copiabile)  
- [x] Guida / novità / bump `1.7.6`  
- [x] `compila` / tag `v` + `app-v` + DataStore (#12312 → #12313 accepted 19/10)  

---

## Nuova chat

Titolo: **«RTAD 1.7.6»**  
Prompt:  
«leggere NOTE_CONTESTO + PIANO_1.7.6; partire da P0 drop+updater updates\, poi CD/DVD e wrap report»

---

*Creato 18/10/2026; aggiornato sera 18/10 (Setup in Download, .cda, drop, wrap report).*
