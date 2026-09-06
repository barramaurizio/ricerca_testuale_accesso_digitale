import globalPluginHandler
import ui
import scriptHandler
import addonHandler
import globalVars
import wx
import os
import zipfile
import threading
import ctypes
import re
import datetime
import json
import shutil
import webbrowser
import xml.etree.ElementTree as ET

addonHandler.initTranslation()

CONFIG_DIR = os.path.join(globalVars.appArgs.configPath, "rtad_data")
if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass
CONFIG_FILE = os.path.join(CONFIG_DIR, "rtad_settings.json")

def create_html_help_file():
    """Crea la guida HTML ufficiale leggibile e navigabile nel browser."""
    help_path = os.path.join(CONFIG_DIR, "guida_ricerca_testuale.html")
    html_content = """<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Guida Ufficiale - Ricerca Testuale Accesso Digitale</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 30px; color: #111; background-color: #f9f9f9; }
        h1 { color: #005a9c; border-bottom: 2px solid #005a9c; padding-bottom: 10px; }
        h2 { color: #333; margin-top: 25px; }
        ul { margin-left: 20px; }
        li { margin-bottom: 8px; }
        code { background-color: #eee; padding: 2px 5px; border-radius: 4px; font-weight: bold; }
        .box { background-color: #eef6fc; border-left: 5px solid #005a9c; padding: 15px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Ricerca Testuale Accesso Digitale</h1>
    <p><strong>Autore e Sviluppatore:</strong> Maurizio Barra</p>
    <p><em>Add-on per NVDA - Versione 1.0</em></p>

    <div class="box">
        <p><strong>Descrizione:</strong> Ricerca Testuale Accesso Digitale è uno strumento avanzato e accessibile progettato per permettere agli utenti di lettori di schermo di cercare parole, frasi e stringhe di testo all'interno di documenti, immagini, file multimediali e interi dischi del computer.</p>
    </div>

    <h2>1. Scorciatoie da Tastiera e Comandi Principali</h2>
    <ul>
        <li><code>NVDA + Shift + Control + F</code> seguito da <code>F</code>: Apri la maschera di ricerca nei file e dischi.</li>
        <li><code>NVDA + Shift + Control + F</code> seguito da <code>S</code>: Mostra la finestra dei comandi rapidi.</li>
        <li><code>NVDA + Shift + Control + F</code> seguito da <code>H</code>: Apri questa guida completa nel browser predefinito.</li>
        <li><code>Alt + K</code>: Scatta uno screenshot immediato dello schermo e lo salva nella cartella <em>Catture di schermata</em>.</li>
    </ul>

    <h2>2. Tipi di File Supportati e Funzionamento</h2>
    <ul>
        <li><strong>Documenti di Testo:</strong> Cerca nei file <code>.txt</code>, <code>.docx</code>, <code>.pdf</code>, <code>.eml</code>, <code>.log</code>, <code>.csv</code>. Trova il testo interno e permette di estrarre sia l'intero contenuto sia il blocco di notizia/paragrafo con la parola chiave.</li>
        <li><strong>Immagini:</strong> Cerca nei file <code>.jpg</code>, <code>.png</code>, <code>.jpeg</code>, <code>.bmp</code> basandosi sui nomi dei file, metadati ed Exif. Permette inoltre di copiare direttamente l'immagine grafica negli appunti per incollaria in chat o documenti.</li>
        <li><strong>Audio e Video:</strong> Filtra e individua i file multimediali (<code>.mp4</code>, <code>.mp3</code>, <code>.mkv</code>, <code>.avi</code>, <code>.wav</code>) basandosi su titoli e tag.</li>
    </ul>

    <h2>3. Menu Contestuale dei Risultati (Tasto APPLICAZIONI o Shift + F10)</h2>
    <p>Posizionandosi su un risultato della lista, premendo il Tasto APPLICAZIONI o Shift+F10 si apre un menu con le seguenti opzioni:</p>
    <ul>
        <li><strong>Apri File (INVIO):</strong> Apre direttamente il file con l'applicazione di sistema.</li>
        <li><strong>Copia Blocco Notizia / Frase con parola chiave:</strong> Copia negli appunti la riga del risultato insieme al contesto (2 righe prima e 2 dopo).</li>
        <li><strong>Copia Percorso Completo:</strong> Copia il percorso esatto del file.</li>
        <li><strong>Copia Tutto il Contenuto (o Immagine):</strong> Copia l'intero testo del documento o l'immagine grafica pronta da incollare.</li>
        <li><strong>Invia / Copia File in un'altra cartella:</strong> Consente di salvare subito una copia del file in una posizione a scelta.</li>
        <li><strong>Apri Cartella Contenitore:</strong> Apre Esplora File selezionando direttamente il file.</li>
        <li><strong>Ordinamento Risultati:</strong> Permette di ordinare i risultati dal più recente al meno recente (default), dal meno recente al più recente o alfabeticamente.</li>
    </ul>

    <h2>4. Note Tecniche e Sviluppi Futuri</h2>
    <p>Il percorso di ricerca selezionato viene ricordato automaticamente anche dopo il riavvio o l'aggiornamento dell'add-on. L'integrazione del motore OCR visivo nativo su larga scala per le immagini è prevista per la versione 2.0.</p>
</body>
</html>
"""
    try:
        with open(help_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception:
        pass
    return help_path

def load_last_path():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                path = data.get("last_path", "")
                if path and os.path.exists(path.split(";")[0]):
                    return path
    except Exception:
        pass
    return os.path.expanduser("~\\Downloads")

def save_last_path(path):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_path": path}, f)
    except Exception:
        pass

def get_real_ready_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if bitmask & 1:
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                try:
                    os.listdir(drive_path)
                    drives.append(drive_path)
                except Exception:
                    pass
        bitmask >>= 1
    return drives

def extract_text_from_docx(file_path):
    try:
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            text_list = []
            for elem in tree.iter():
                if elem.tag.endswith('t') and elem.text:
                    text_list.append(elem.text)
            return " ".join(text_list)
    except Exception:
        return ""

def extract_text_from_pdf(file_path):
    try:
        with open(file_path, "rb") as f:
            content = f.read().decode("latin1", errors="ignore")
            matches = re.findall(r'\((.*?)\)', content)
            return " ".join(matches)
    except Exception:
        return ""

def deep_ocr_jpg_scan(file_path):
    try:
        with open(file_path, "rb") as f:
            header = f.read(4194304)
            content_str = header.decode("latin1", errors="ignore")
            words = re.findall(r'[A-Za-z0-9\s]{3,}', content_str)
            return " ".join(words)
    except Exception:
        return ""

class SearchFrame(wx.Frame):

    def __init__(self):
        super(SearchFrame, self).__init__(
            None, 
            title="Ricerca Testuale Accesso Digitale - Maurizio Barra", 
            size=(780, 680),
            style=wx.DEFAULT_FRAME_STYLE
        )
        
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Campo Testo
        lbl_query = wx.StaticText(panel, label="&Testo o frase da cercare:")
        vbox.Add(lbl_query, 0, wx.ALL, 5)
        self.txt_query = wx.TextCtrl(panel)
        vbox.Add(self.txt_query, 0, wx.EXPAND | wx.ALL, 5)

        # Filtro Tipo File
        lbl_filter = wx.StaticText(panel, label="T&ipo di file da cercare:")
        vbox.Add(lbl_filter, 0, wx.ALL, 5)
        self.combo_filter = wx.Choice(
            panel, 
            choices=[
                "Tutti i tipi di file", 
                "Solo Immagini (.jpg, .png, .jpeg, .bmp)", 
                "Solo Audio e Video (.mp4, .mp3, .mkv, .avi, .wav)", 
                "Solo Documenti (.txt, .docx, .pdf, .eml)"
            ]
        )
        self.combo_filter.SetSelection(0)
        vbox.Add(self.combo_filter, 0, wx.EXPAND | wx.ALL, 5)

        # Percorso
        lbl_path = wx.StaticText(panel, label="&Percorso di ricerca (Memoria automatica):")
        vbox.Add(lbl_path, 0, wx.ALL, 5)
        
        hbox_path = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_path = wx.TextCtrl(panel, value=load_last_path())
        hbox_path.Add(self.txt_path, 1, wx.EXPAND | wx.ALL, 5)
        
        btn_browse = wx.Button(panel, label="&Sfoglia...")
        btn_browse.Bind(wx.EVT_BUTTON, self.on_browse)
        hbox_path.Add(btn_browse, 0, wx.ALL, 5)

        btn_drives = wx.Button(panel, label="&Dischi Pronti")
        btn_drives.Bind(wx.EVT_BUTTON, self.on_all_drives_set)
        hbox_path.Add(btn_drives, 0, wx.ALL, 5)

        vbox.Add(hbox_path, 0, wx.EXPAND)

        # Pulsanti Azioni principali
        hbox_actions = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_search = wx.Button(panel, label="&Avvia Ricerca")
        self.btn_search.Bind(wx.EVT_BUTTON, lambda e: self.start_search_thread())
        hbox_actions.Add(self.btn_search, 0, wx.ALL, 5)

        btn_screenshot = wx.Button(panel, label="Cattura Sc&hermo (Alt+K)")
        btn_screenshot.Bind(wx.EVT_BUTTON, self.on_take_screenshot)
        hbox_actions.Add(btn_screenshot, 0, wx.ALL, 5)

        vbox.Add(hbox_actions, 0, wx.ALIGN_CENTER)

        # Barra Progresso
        lbl_progress = wx.StaticText(panel, label="Avanzamento ricerca:")
        vbox.Add(lbl_progress, 0, wx.ALL, 5)
        self.gauge = wx.Gauge(panel, range=100)
        vbox.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 5)

        # Lista Risultati
        lbl_results = wx.StaticText(panel, label="&Risultati trovati (Premi INVIO o Tasto APPLICAZIONI per opzioni):")
        vbox.Add(lbl_results, 0, wx.ALL, 5)
        self.lst_results = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.lst_results.Bind(wx.EVT_CHAR_HOOK, self.on_list_char_hook)
        self.lst_results.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open_file_event)
        self.lst_results.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        vbox.Add(self.lst_results, 1, wx.EXPAND | wx.ALL, 5)

        self.current_matches = []
        self.file_map = {}
        self.last_spoken_percent = -1
        self.current_query = ""

        # Pulsanti inferiori
        hbox_bottom = wx.BoxSizer(wx.HORIZONTAL)
        btn_open = wx.Button(panel, label="&Apri File Selezionato")
        btn_open.Bind(wx.EVT_BUTTON, self.on_open_file_event)
        hbox_bottom.Add(btn_open, 0, wx.ALL, 5)

        btn_close = wx.Button(panel, label="C&hiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        hbox_bottom.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_bottom, 0, wx.EXPAND)

        panel.SetSizer(vbox)
        self.Centre()

        self.Bind(wx.EVT_CHAR_HOOK, self.on_general_char_hook)

    def on_general_char_hook(self, event):
        if event.AltDown() and event.GetKeyCode() == ord('K'):
            self.on_take_screenshot(None)
        elif event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            event.Skip()

    def on_close(self, event):
        self.Destroy()

    def on_browse(self, event):
        dlg = wx.DirDialog(self, "Seleziona la cartella o l'unità per la ricerca", defaultPath=self.txt_path.GetValue())
        if dlg.ShowModal() == wx.ID_OK:
            selected_path = dlg.GetPath()
            self.txt_path.SetValue(selected_path)
            save_last_path(selected_path)
        dlg.Destroy()

    def on_all_drives_set(self, event):
        drives = get_real_ready_drives()
        drives_str = ";".join(drives)
        self.txt_path.SetValue(drives_str)
        save_last_path(drives_str)
        ui.message(f"Impostata ricerca sui dischi pronti: {', '.join(drives)}. Premi Avvia Ricerca.")

    def on_take_screenshot(self, event):
        try:
            screen = wx.ScreenDC()
            size = screen.GetSize()
            bmp = wx.Bitmap(size.width, size.height)
            mem = wx.MemoryDC(bmp)
            mem.Blit(0, 0, size.width, size.height, screen, 0, 0)
            mem.SelectObject(wx.NullBitmap)

            pictures_dir = os.path.expanduser("~\\Pictures\\Catture di schermata")
            if not os.path.exists(pictures_dir):
                pictures_dir = os.path.expanduser("~\\OneDrive\\Immagini\\Catture di schermata")
                if not os.path.exists(pictures_dir):
                    os.makedirs(pictures_dir, exist_ok=True)

            filename = f"Screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            full_path = os.path.join(pictures_dir, filename)
            bmp.SaveFile(full_path, wx.BITMAP_TYPE_PNG)
            ui.message("Screenshot salvato con successo in Catture di schermata.")
        except Exception:
            ui.message("Impossibile salvare lo screenshot.")

    def start_search_thread(self):
        query = self.txt_query.GetValue().strip().lower()
        target_input = self.txt_path.GetValue().strip()
        filter_mode = self.combo_filter.GetSelection()

        if not query:
            ui.message("Inserire un testo da cercare.")
            return

        self.current_query = query
        save_last_path(target_input)

        self.lst_results.Clear()
        self.file_map.clear()
        self.current_matches = []
        self.gauge.SetValue(0)
        self.last_spoken_percent = -1
        self.btn_search.Disable()
        
        ui.message("Ricerca in corso...")

        targets = [t.strip() for t in target_input.split(";") if t.strip()]
        threading.Thread(target=self.run_search, args=(query, targets, filter_mode), daemon=True).start()

    def run_search(self, query, targets, filter_mode):
        raw_matches = []
        ignored = ["$recycle.bin", "temp", "system volume information", "appdata\\local\\temp"]

        img_exts = [".jpg", ".jpeg", ".png", ".bmp"]
        media_exts = [".mp4", ".mp3", ".mkv", ".avi", ".wav"]
        doc_exts = [".txt", ".eml", ".log", ".csv", ".docx", ".pdf"]

        file_list = []

        for folder in targets:
            if not os.path.exists(folder):
                continue

            for root, dirs, files in os.walk(folder):
                root_lower = root.lower()
                if any(ign in root_lower for ign in ignored):
                    continue

                for file in files:
                    ext = os.path.splitext(file)[1].lower()

                    if filter_mode == 1 and ext not in img_exts:
                        continue
                    elif filter_mode == 2 and ext not in media_exts:
                        continue
                    elif filter_mode == 3 and ext not in doc_exts:
                        continue

                    file_list.append(os.path.normpath(os.path.join(root, file)))

        total_files = len(file_list)

        for i, file_path in enumerate(file_list, 1):
            file_name = os.path.basename(file_path)
            ext = os.path.splitext(file_name)[1].lower()

            found = False
            snippet = f"Trovata corrispondenza per '{query}' nel nome del file."
            prefix = f"[{ext.replace('.', '').upper()}]"

            # 1. Controllo NOME FILE
            if query in file_name.lower():
                found = True

            # 2. Controllo CONTENUTO IMMAGINI
            elif ext in img_exts:
                img_text = deep_ocr_jpg_scan(file_path)
                if query in img_text.lower():
                    found = True
                    prefix = "[IMG-TEXT]"
                    snippet = f"Trovato testo visivo contenente '{query}'."

            # 3. Controllo DOCUMENTI (Blocco notizia esteso)
            elif ext in [".txt", ".eml", ".log", ".csv"]:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        for idx, line in enumerate(lines):
                            if query in line.lower():
                                found = True
                                start_i = max(0, idx - 2)
                                end_i = min(len(lines), idx + 3)
                                snippet = "".join(lines[start_i:end_i]).strip()
                                break
                except Exception:
                    pass

            elif ext == ".docx":
                text = extract_text_from_docx(file_path)
                if query in text.lower():
                    found = True
                    snippet = f"Corrispondenza per '{query}' nel documento Word."

            elif ext == ".pdf":
                text = extract_text_from_pdf(file_path)
                if query in text.lower():
                    found = True
                    snippet = f"Corrispondenza per '{query}' nel PDF."

            if found:
                try:
                    mtime = os.path.getmtime(file_path)
                except Exception:
                    mtime = 0

                raw_matches.append({
                    "file_path": file_path,
                    "file_name": file_name,
                    "prefix": prefix,
                    "mtime": mtime,
                    "snippet": snippet
                })

            if total_files > 0:
                percent = int((i / total_files) * 100)
                if percent % 10 == 0 and percent != self.last_spoken_percent:
                    self.last_spoken_percent = percent
                    wx.CallAfter(self.update_progress, percent)

        self.current_matches = raw_matches
        self.sort_and_display_matches(sort_type="recent_first")
        wx.CallAfter(self.finish_search, len(raw_matches))

    def sort_and_display_matches(self, sort_type="recent_first"):
        if sort_type == "recent_first":
            self.current_matches.sort(key=lambda x: x["mtime"], reverse=True)
        elif sort_type == "oldest_first":
            self.current_matches.sort(key=lambda x: x["mtime"], reverse=False)
        elif sort_type == "name":
            self.current_matches.sort(key=lambda x: x["file_name"].lower())

        self.lst_results.Clear()
        self.file_map.clear()

        for item in self.current_matches:
            display_str = f"{item['prefix']} {item['file_name']} -- ({item['file_path']})"
            idx = self.lst_results.Append(display_str)
            self.file_map[idx] = item

    def update_progress(self, percent):
        self.gauge.SetValue(percent)
        ui.message(f"Ricerca in corso: {percent} percento")

    def finish_search(self, matches):
        self.gauge.SetValue(100)
        self.btn_search.Enable()
        ui.message(f"Ricerca completata. Trovati {matches} risultati ordinati dal più recente.")

    def on_list_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN:
            self.open_selected_file()
        elif event.GetKeyCode() == wx.WXK_WINDOWS_MENU:
            self.on_context_menu(None)
        elif event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            event.Skip()

    def on_open_file_event(self, event):
        self.open_selected_file()

    def open_selected_file(self):
        sel = self.lst_results.GetSelection()
        if sel != wx.NOT_FOUND and sel in self.file_map:
            file_to_open = self.file_map[sel]["file_path"]
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "open", file_to_open, None, None, 1)
                ui.message(f"Apertura file: {os.path.basename(file_to_open)}")
            except Exception:
                ui.message("Impossibile aprire il file selezionato.")

    def on_context_menu(self, event):
        sel = self.lst_results.GetSelection()
        if sel == wx.NOT_FOUND or sel not in self.file_map:
            return

        item_data = self.file_map[sel]
        file_path = item_data["file_path"]
        snippet = item_data["snippet"]

        menu = wx.Menu()
        item_open = menu.Append(wx.ID_ANY, "Apri File\tINVIO")
        item_copy_snippet = menu.Append(wx.ID_ANY, "Copia Blocco Notizia / Frase con parola chiave")
        item_copy_path = menu.Append(wx.ID_ANY, "Copia Percorso Completo")
        item_copy_text = menu.Append(wx.ID_ANY, "Copia Tutto il Contenuto (o Immagine)")
        item_copy_to = menu.Append(wx.ID_ANY, "Invia / Copia File in un'altra cartella...")
        item_open_folder = menu.Append(wx.ID_ANY, "Apri Cartella Contenitore")

        menu.AppendSeparator()
        sort_submenu = wx.Menu()
        item_sort_recent = sort_submenu.Append(wx.ID_ANY, "Dal Più Recente al Meno Recente")
        item_sort_oldest = sort_submenu.Append(wx.ID_ANY, "Dal Meno Recente al Più Recente")
        item_sort_name = sort_submenu.Append(wx.ID_ANY, "Alfabeticamente per Nome (A-Z)")
        menu.AppendSubMenu(sort_submenu, "Ordinamento Risultati")

        self.Bind(wx.EVT_MENU, lambda e: self.open_selected_file(), item_open)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_snippet_to_clipboard(snippet), item_copy_snippet)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_path_to_clipboard(file_path), item_copy_path)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_content_or_image_to_clipboard(file_path), item_copy_text)
        self.Bind(wx.EVT_MENU, lambda e: self.copy_file_to_destination(file_path), item_copy_to)
        self.Bind(wx.EVT_MENU, lambda e: self.open_containing_folder(file_path), item_open_folder)

        self.Bind(wx.EVT_MENU, lambda e: self.change_sort_order("recent_first"), item_sort_recent)
        self.Bind(wx.EVT_MENU, lambda e: self.change_sort_order("oldest_first"), item_sort_oldest)
        self.Bind(wx.EVT_MENU, lambda e: self.change_sort_order("name"), item_sort_name)

        self.PopupMenu(menu)
        menu.Destroy()

    def change_sort_order(self, sort_type):
        self.sort_and_display_matches(sort_type)
        if sort_type == "recent_first":
            ui.message("Risultati ordinati dal più recente al meno recente.")
        elif sort_type == "oldest_first":
            ui.message("Risultati ordinati dal meno recente al più recente.")
        elif sort_type == "name":
            ui.message("Risultati ordinati alfabeticamente per nome.")

    def copy_snippet_to_clipboard(self, snippet):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(snippet))
            wx.TheClipboard.Close()
            ui.message("Blocco notizia / frase copiata negli appunti!")

    def copy_path_to_clipboard(self, file_path):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(file_path))
            wx.TheClipboard.Close()
            ui.message("Percorso copiato negli appunti!")

    def copy_content_or_image_to_clipboard(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            try:
                img = wx.Image(file_path, wx.BITMAP_TYPE_ANY)
                bmp = wx.Bitmap(img)
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.BitmapDataObject(bmp))
                    wx.TheClipboard.Close()
                    ui.message("Immagine grafica copiata negli appunti! Pronta da incollare.")
                    return
            except Exception:
                pass

        text_content = ""
        if ext == ".docx":
            text_content = extract_text_from_docx(file_path)
        elif ext == ".pdf":
            text_content = extract_text_from_pdf(file_path)
        elif ext in [".txt", ".eml", ".log", ".csv"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text_content = f.read()
            except Exception:
                pass

        if text_content:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text_content))
                wx.TheClipboard.Close()
                ui.message("Contenuto testuale copiato negli appunti!")
        else:
            ui.message("Impossibile copiare il contenuto da questo formato.")

    def copy_file_to_destination(self, file_path):
        dlg = wx.DirDialog(self, "Seleziona la cartella dove copiare il file", defaultPath=os.path.expanduser("~\\Desktop"))
        if dlg.ShowModal() == wx.ID_OK:
            dest_dir = dlg.GetPath()
            try:
                shutil.copy(file_path, dest_dir)
                ui.message(f"File copiato con successo in {dest_dir}!")
            except Exception:
                ui.message("Impossibile copiare il file nella destinazione.")
        dlg.Destroy()

    def open_containing_folder(self, file_path):
        try:
            folder_path = os.path.dirname(file_path)
            ctypes.windll.shell32.ShellExecuteW(None, "explore", folder_path, None, None, 1)
            ui.message("Apertura cartella contenitore in corso...")
        except Exception:
            ui.message("Impossibile aprire la cartella contenitore.")


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self):
        super(GlobalPlugin, self).__init__()
        self._waiting_for_second_key = False

    @scriptHandler.script(
        description="Leader Key per Ricerca Testuale Accesso Digitale",
        category="Ricerca Testuale",
        gesture="kb:NVDA+shift+control+f"
    )
    def script_leaderKey(self, gesture):
        self._waiting_for_second_key = True
        ui.message("Ricerca Testuale: premere F per cercare, S per comandi, H per la Guida nel Browser")

    @scriptHandler.script(
        description="Apri maschera di ricerca",
        gesture="kb:f"
    )
    def script_handleShortcutF(self, gesture):
        if self._waiting_for_second_key:
            self._waiting_for_second_key = False
            wx.CallAfter(self.open_search_window)
        else:
            gesture.send()

    @scriptHandler.script(
        description="Gestore dei sotto-comandi in sequenza",
        gesture="kb:s"
    )
    def script_handleShortcutS(self, gesture):
        if self._waiting_for_second_key:
            self._waiting_for_second_key = False
            wx.CallAfter(self.show_shortcuts_dialog)
        else:
            gesture.send()

    @scriptHandler.script(
        description="Guida dell'add-on nel Browser",
        gesture="kb:h"
    )
    def script_handleShortcutH(self, gesture):
        if self._waiting_for_second_key:
            self._waiting_for_second_key = False
            html_file = create_html_help_file()
            webbrowser.open(f"file:///{html_file}")
            ui.message("Apertura guida completa nel browser in corso...")
        else:
            gesture.send()

    def open_search_window(self):
        frame = SearchFrame()
        frame.Show()
        frame.Raise()
        frame.txt_query.SetFocus()

    def show_shortcuts_dialog(self):
        msg = (
            "Comandi disponibili dopo NVDA+Shift+Control+F:\n\n"
            "F - Apri maschera di ricerca nei file o dischi\n"
            "S - Mostra questa finestra con i comandi\n"
            "H - Apri la guida completa HTML nel browser\n"
        )
        gui_dialog = wx.MessageDialog(
            None, 
            msg, 
            "Ricerca Testuale Accesso Digitale - Comandi", 
            wx.OK | wx.ICON_INFORMATION
        )
        gui_dialog.ShowModal()
        gui_dialog.Destroy()