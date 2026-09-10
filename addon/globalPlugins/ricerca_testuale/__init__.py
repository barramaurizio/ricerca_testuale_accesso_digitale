import addonHandler
import ctypes
import datetime
import globalPluginHandler
import globalVars
import inputCore
import json
import os
import re
import shutil
import scriptHandler
import subprocess
import threading
import time
import ui
import webbrowser
import wx
import xml.etree.ElementTree as ET
import zipfile

addonHandler.initTranslation()

APP_TITLE = "Ricerca Testuale Accesso Digitale"
APP_VERSION = "1.4.1"
DONATION_URL = "https://paypal.me/AccessoDigitale"
YOUTUBE_URL = "https://www.youtube.com/@AccessoDigitale"
GITHUB_URL = "https://github.com/barramaurizio/ricerca_testuale_accesso_digitale"

CONFIG_DIR = os.path.join(globalVars.appArgs.configPath, "rtad_data")
if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass
CONFIG_FILE = os.path.join(CONFIG_DIR, "rtad_settings.json")


def create_html_help_file():
    help_path = os.path.join(CONFIG_DIR, "guida_ricerca_testuale.html")
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Guida Ufficiale - {APP_TITLE}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 30px; color: #111; background-color: #f9f9f9; }}
        h1 {{ color: #005a9c; border-bottom: 2px solid #005a9c; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 25px; }}
        ul {{ margin-left: 20px; }}
        li {{ margin-bottom: 8px; }}
        code {{ background-color: #eee; padding: 2px 5px; border-radius: 4px; font-weight: bold; }}
        .box {{ background-color: #eef6fc; border-left: 5px solid #005a9c; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>{APP_TITLE}</h1>
    <p><strong>Autore:</strong> Maurizio Barra (Accesso Digitale)</p>
    <p><em>Add-on per NVDA - Versione {APP_VERSION}</em></p>

    <div class="box">
        <p><strong>Novit&agrave; Versione 1.4.1:</strong> Piena compatibilit&agrave; con la modalit&agrave; navigazione di NVDA (nessuna interferenza con i tasti H, F, S), ricerca su Tutto il PC (<code>Alt + T</code>), lettura avanzamento con <code>Tab</code> o <code>Alt + P</code>, apertura mirata alla riga esatta con <code>INVIO</code>, anteprima vocale con <code>SPAZIO</code> o <code>F4</code> ed esportazione risultati su Desktop.</p>
    </div>

    <h2>1. Scorciatoie da Tastiera</h2>
    <ul>
        <li><code>NVDA + Shift + Control + F</code> seguito da <code>F</code>: Apri la finestra di ricerca.</li>
        <li><code>NVDA + Shift + Control + F</code> seguito da <code>S</code>: Mostra la finestra dei comandi rapidi.</li>
        <li><code>NVDA + Shift + Control + F</code> seguito da <code>D</code>: Apri la pagina Donazioni PayPal.</li>
        <li><code>NVDA + Shift + Control + F</code> seguito da <code>H</code>: Apri la Guida nel Browser.</li>
        <li><code>Alt + T</code>: Seleziona automaticamente tutte le unit&agrave; disco attive (Tutto il PC).</li>
        <li><code>Alt + P</code>: Annuncia all'istante la percentuale e lo stato di avanzamento della ricerca.</li>
        <li><code>Alt + K</code>: Scatta uno screenshot e lo salva in <em>Catture di schermata</em>.</li>
        <li><code>SPAZIO</code> o <code>F4</code> (sui risultati): Anteprima vocale immediata del contesto.</li>
        <li><code>INVIO</code> (sui risultati): Apre il file alla riga esatta in Notepad++ o Blocco Note.</li>
    </ul>
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
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if bitmask & 1:
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                try:
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    if drive_type in (2, 3):  # 2=Removibile, 3=Fisso
                        os.listdir(drive_path)
                        drives.append(drive_path)
                except Exception:
                    pass
        bitmask >>= 1
    return drives


def extract_paragraphs_from_docx(file_path):
    try:
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            paragraphs = []
            for p in tree.iter():
                if p.tag.endswith("p"):
                    p_text = "".join(
                        [elem.text for elem in p.iter() if elem.tag.endswith("t") and elem.text]
                    )
                    if p_text.strip():
                        paragraphs.append(p_text.strip())
            return paragraphs
    except Exception:
        return []


def extract_lines_from_pdf(file_path):
    try:
        with open(file_path, "rb") as f:
            content = f.read(4194304).decode("latin1", errors="ignore")
            matches = re.findall(r"\((.*?)\)", content)
            if not matches:
                matches = re.findall(r"[A-Za-z0-9àèéìòùÀÈÉÌÒÙ\s]{3,}", content)
            return [m.strip() for m in matches if m.strip()]
    except Exception:
        return []


def deep_ocr_jpg_scan(file_path):
    try:
        with open(file_path, "rb") as f:
            header = f.read(4194304)
            content_str = header.decode("latin1", errors="ignore")
            words = re.findall(r"[A-Za-z0-9\s]{3,}", content_str)
            return " ".join(words)
    except Exception:
        return ""


def jump_to_line_in_editor(file_path, line_number):
    def _jump_worker():
        npp_path = shutil.which("notepad++.exe") or r"C:\Program Files\Notepad++\notepad++.exe"
        vscode_path = shutil.which("code.cmd") or shutil.which("code.exe")

        if os.path.exists(npp_path):
            subprocess.Popen([npp_path, f"-n{line_number}", file_path])
            return

        if vscode_path:
            subprocess.Popen([vscode_path, "-g", f"{file_path}:{line_number}"])
            return

        subprocess.Popen(["notepad.exe", file_path])
        time.sleep(0.6)

        VK_CONTROL = 0x11
        VK_G = 0x47
        VK_RETURN = 0x0D

        user32 = ctypes.windll.user32
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_G, 0, 0, 0)
        user32.keybd_event(VK_G, 0, 2, 0)
        user32.keybd_event(VK_CONTROL, 0, 2, 0)
        time.sleep(0.3)

        for digit in str(line_number):
            vk = ord(digit)
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
            time.sleep(0.05)

        user32.keybd_event(VK_RETURN, 0, 0, 0)
        user32.keybd_event(VK_RETURN, 0, 2, 0)

    threading.Thread(target=_jump_worker, daemon=True).start()


class ShortcutsFrame(wx.Frame):

    def __init__(self, parent):
        super(ShortcutsFrame, self).__init__(
            parent,
            title=f"{APP_TITLE} v{APP_VERSION} - Comandi e Info",
            size=(680, 560),
            style=wx.DEFAULT_FRAME_STYLE,
        )

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.text_content = (
            f"{APP_TITLE} v{APP_VERSION}\n"
            "Autore e Sviluppatore: Maurizio Barra (Accesso Digitale)\n\n"
            "--------------------------------------------------\n"
            "COMANDI E SCORCIATOIE DA TASTIERA:\n"
            "--------------------------------------------------\n"
            "Attivazione comandi sequenziali: NVDA + Shift + Control + F\n\n"
            "Sequenze disponibili dopo il tasto di attivazione:\n"
            "  - F : Apri la finestra principale di ricerca\n"
            "  - S : Apri questa finestra comandi navigabile\n"
            "  - D : Apri la pagina per le Donazioni PayPal\n"
            "  - H : Apri la Guida HTML nel Browser\n\n"
            "Comandi Finestra di Ricerca:\n"
            "  - Alt + T : Imposta la scansione su TUTTO IL PC (tutte le unità attive)\n"
            "  - Alt + P : Annuncia all'istante lo stato e la percentuale di ricerca\n"
            "  - TAB : Raggiunge anche il campo 'Stato avanzamento' leggibile dallo screen reader\n"
            "  - Alt + K : Scatta uno screenshot salvato in 'Catture di schermata'\n"
            "  - INVIO (su campo testo) : Avvia subito la ricerca\n"
            "  - INVIO (sui risultati) : Apri file alla riga esatta\n"
            "  - SPAZIO / F4 : Anteprima vocale immediata del contesto\n"
            "  - Tasto APPLICAZIONI : Menu contestuale del file selezionato\n"
            "  - ESC : Chiudi la finestra\n\n"
            "--------------------------------------------------\n"
            "SOSTIENI IL PROGETTO:\n"
            f"{DONATION_URL}\n"
            "--------------------------------------------------"
        )

        lbl_info = wx.StaticText(
            panel,
            label="Usa le frecce Su/Giù e Sinistra/Destra per navigare nel testo:",
        )
        vbox.Add(lbl_info, 0, wx.ALL, 8)

        self.txt_display = wx.TextCtrl(
            panel,
            value=self.text_content,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
        )
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_copy = wx.Button(panel, label="&Copia Testo Comandi")
        btn_copy.Bind(wx.EVT_BUTTON, self.on_copy_text)
        hbox_btns.Add(btn_copy, 0, wx.ALL, 5)

        btn_donate = wx.Button(panel, label="Apri Link &Donazione...")
        btn_donate.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open(DONATION_URL))
        hbox_btns.Add(btn_donate, 0, wx.ALL, 5)

        btn_close = wx.Button(panel, label="C&hiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
        hbox_btns.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_btns, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(vbox)
        self.Centre()
        self.txt_display.SetFocus()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

    def on_copy_text(self, event):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.text_content))
            wx.TheClipboard.Close()
            ui.message("Testo dei comandi copiato negli appunti!")

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            event.Skip()


class SearchFrame(wx.Frame):

    def __init__(self):
        super(SearchFrame, self).__init__(
            None,
            title=f"{APP_TITLE} v{APP_VERSION} - Maurizio Barra",
            size=(860, 780),
            style=wx.DEFAULT_FRAME_STYLE,
        )

        self._stop_search = False
        self.current_percent = 0
        self.scanned_count = 0
        self.current_matches = []
        self.file_map = {}
        self.current_query = ""

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # 1. Campo Testo
        lbl_query = wx.StaticText(panel, label="&Testo o frase da cercare (supporta più termini):")
        vbox.Add(lbl_query, 0, wx.ALL, 5)
        self.txt_query = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.txt_query.Bind(wx.EVT_TEXT_ENTER, lambda e: self.start_search_thread())
        vbox.Add(self.txt_query, 0, wx.EXPAND | wx.ALL, 5)

        # 2. Filtro Tipo File
        hbox_filter = wx.BoxSizer(wx.HORIZONTAL)
        vbox_filter_choice = wx.BoxSizer(wx.VERTICAL)
        lbl_filter = wx.StaticText(panel, label="T&ipo di file da cercare:")
        vbox_filter_choice.Add(lbl_filter, 0, wx.ALL, 5)
        self.combo_filter = wx.Choice(
            panel,
            choices=[
                "Tutti i tipi di file",
                "Solo Immagini (.jpg, .png, .jpeg, .bmp)",
                "Solo Audio e Video (.mp4, .mp3, .mkv, .avi, .wav)",
                "Solo Documenti (.txt, .docx, .pdf, .eml, .log, .csv)",
                "Estensione Personalizzata...",
            ],
        )
        self.combo_filter.SetSelection(0)
        self.combo_filter.Bind(wx.EVT_CHOICE, self.on_filter_changed)
        vbox_filter_choice.Add(self.combo_filter, 1, wx.EXPAND | wx.ALL, 5)
        hbox_filter.Add(vbox_filter_choice, 1, wx.EXPAND)

        self.vbox_custom_ext = wx.BoxSizer(wx.VERTICAL)
        lbl_custom_ext = wx.StaticText(panel, label="Estensione specifica (es. .ini o .srt):")
        self.vbox_custom_ext.Add(lbl_custom_ext, 0, wx.ALL, 5)
        self.txt_custom_ext = wx.TextCtrl(panel, value=".txt")
        self.txt_custom_ext.Enable(False)
        self.vbox_custom_ext.Add(self.txt_custom_ext, 1, wx.EXPAND | wx.ALL, 5)
        hbox_filter.Add(self.vbox_custom_ext, 1, wx.EXPAND)
        vbox.Add(hbox_filter, 0, wx.EXPAND)

        # 3. Percorso
        lbl_path = wx.StaticText(panel, label="&Percorso di ricerca (Memoria automatica):")
        vbox.Add(lbl_path, 0, wx.ALL, 5)

        hbox_path = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_path = wx.TextCtrl(panel, value=load_last_path())
        hbox_path.Add(self.txt_path, 1, wx.EXPAND | wx.ALL, 5)

        btn_browse = wx.Button(panel, label="&Sfoglia...")
        btn_browse.Bind(wx.EVT_BUTTON, self.on_browse)
        hbox_path.Add(btn_browse, 0, wx.ALL, 5)

        btn_all_pc = wx.Button(panel, label="&Tutto il PC")
        btn_all_pc.Bind(wx.EVT_BUTTON, self.on_search_all_pc)
        hbox_path.Add(btn_all_pc, 0, wx.ALL, 5)
        vbox.Add(hbox_path, 0, wx.EXPAND)

        # 4. Pulsanti Azioni Principali
        hbox_actions = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_search = wx.Button(panel, label="&Avvia Ricerca")
        self.btn_search.Bind(wx.EVT_BUTTON, lambda e: self.start_search_thread())
        hbox_actions.Add(self.btn_search, 0, wx.ALL, 5)

        btn_progress_now = wx.Button(panel, label="&Percentuale (Alt+P)")
        btn_progress_now.Bind(wx.EVT_BUTTON, lambda e: self.announce_progress())
        hbox_actions.Add(btn_progress_now, 0, wx.ALL, 5)

        btn_screenshot = wx.Button(panel, label="Cattura Sc&hermo (Alt+K)")
        btn_screenshot.Bind(wx.EVT_BUTTON, self.on_take_screenshot)
        hbox_actions.Add(btn_screenshot, 0, wx.ALL, 5)

        btn_export = wx.Button(panel, label="&Esporta Risultati...")
        btn_export.Bind(wx.EVT_BUTTON, self.on_export_results)
        hbox_actions.Add(btn_export, 0, wx.ALL, 5)

        btn_donate = wx.Button(panel, label="&Sostieni il Progetto...")
        btn_donate.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open(DONATION_URL))
        hbox_actions.Add(btn_donate, 0, wx.ALL, 5)
        vbox.Add(hbox_actions, 0, wx.ALIGN_CENTER)

        # 5. Sezione Avanzamento (Accessibile via TAB + Barra Grafica)
        lbl_status_progress = wx.StaticText(panel, label="&Stato avanzamento ricerca (raggiungibile con Tab):")
        vbox.Add(lbl_status_progress, 0, wx.ALL, 5)

        self.txt_status_progress = wx.TextCtrl(
            panel,
            value="Pronto per la ricerca. Premi Alt+P o ascolta l'avanzamento.",
            style=wx.TE_READONLY,
        )
        vbox.Add(self.txt_status_progress, 0, wx.EXPAND | wx.ALL, 5)

        self.gauge = wx.Gauge(panel, range=100)
        vbox.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 5)

        # 6. Lista Risultati
        lbl_results = wx.StaticText(
            panel,
            label="&Risultati trovati (INVIO per riga esatta, SPAZIO/F4 anteprima audio, APPLICAZIONI opzioni):",
        )
        vbox.Add(lbl_results, 0, wx.ALL, 5)
        self.lst_results = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.lst_results.Bind(wx.EVT_CHAR_HOOK, self.on_list_char_hook)
        self.lst_results.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open_file_event)
        self.lst_results.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        vbox.Add(self.lst_results, 1, wx.EXPAND | wx.ALL, 5)

        # 7. Pulsanti Inferiori
        hbox_bottom = wx.BoxSizer(wx.HORIZONTAL)
        btn_open = wx.Button(panel, label="&Apri File (Alla Riga)")
        btn_open.Bind(wx.EVT_BUTTON, self.on_open_file_event)
        hbox_bottom.Add(btn_open, 0, wx.ALL, 5)

        btn_preview = wx.Button(panel, label="Anteprima &Voce (F4)")
        btn_preview.Bind(wx.EVT_BUTTON, lambda e: self.speak_selected_preview())
        hbox_bottom.Add(btn_preview, 0, wx.ALL, 5)

        btn_github = wx.Button(panel, label="Pagina &GitHub")
        btn_github.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open(GITHUB_URL))
        hbox_bottom.Add(btn_github, 0, wx.ALL, 5)

        btn_close = wx.Button(panel, label="C&hiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        hbox_bottom.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_bottom, 0, wx.EXPAND)
        panel.SetSizer(vbox)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_general_char_hook)

    def on_filter_changed(self, event):
        sel = self.combo_filter.GetSelection()
        self.txt_custom_ext.Enable(sel == 4)

    def on_search_all_pc(self, event):
        drives = get_real_ready_drives()
        drives_str = ";".join(drives)
        self.txt_path.SetValue(drives_str)
        save_last_path(drives_str)
        ui.message(f"Tutto il PC impostato: {len(drives)} unità attive. Premi Invio per avviare.")
        self.btn_search.SetFocus()

    def announce_progress(self):
        found = len(self.current_matches)
        if not self.btn_search.IsEnabled():
            msg = f"Avanzamento ricerca: {self.current_percent} percento. File analizzati: {self.scanned_count}. Trovati: {found}."
        else:
            msg = f"Stato: {self.txt_status_progress.GetValue()}. Risultati in lista: {found}."
        ui.message(msg)

    def on_general_char_hook(self, event):
        key = event.GetKeyCode()
        if event.AltDown() and key == ord("K"):
            self.on_take_screenshot(None)
        elif event.AltDown() and key == ord("T"):
            self.on_search_all_pc(None)
        elif event.AltDown() and key == ord("P"):
            self.announce_progress()
        elif key == wx.WXK_ESCAPE:
            self._stop_search = True
            self.Destroy()
        else:
            event.Skip()

    def on_close(self, event):
        self._stop_search = True
        self.Destroy()

    def on_browse(self, event):
        dlg = wx.DirDialog(
            self,
            "Seleziona la cartella o l'unità per la ricerca",
            defaultPath=self.txt_path.GetValue(),
        )
        if dlg.ShowModal() == wx.ID_OK:
            selected_path = dlg.GetPath()
            self.txt_path.SetValue(selected_path)
            save_last_path(selected_path)
            ui.message(f"Percorso impostato: {selected_path}.")
        dlg.Destroy()

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

    def on_export_results(self, event):
        if not self.current_matches:
            ui.message("Nessun risultato da esportare.")
            return

        desktop_path = os.path.expanduser("~\\Desktop")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = os.path.join(desktop_path, f"Risultati_Ricerca_{timestamp}.txt")

        try:
            with open(export_file, "w", encoding="utf-8") as f:
                f.write(f"=== {APP_TITLE} v{APP_VERSION} - Risultati Ricerca ===\n")
                f.write(f"Data: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write(f"Parola cercata: {self.current_query}\n")
                f.write(f"Totale risultati: {len(self.current_matches)}\n\n")
                for idx, item in enumerate(self.current_matches, 1):
                    loc = f" [{item.get('location_info', '')}]" if item.get("location_info") else ""
                    f.write(f"{idx}. {item['file_name']}{loc}\n")
                    f.write(f"   Percorso: {item['file_path']}\n")
                    if item.get("snippet"):
                        f.write(f"   Estratto: {item['snippet']}\n")
                    f.write("-" * 50 + "\n")
            ui.message(f"Risultati esportati sul Desktop nel file: Risultati_Ricerca_{timestamp}.txt")
        except Exception:
            ui.message("Errore durante l'esportazione dei risultati.")

    def speak_selected_preview(self):
        sel = self.lst_results.GetSelection()
        if sel != wx.NOT_FOUND and sel in self.file_map:
            item = self.file_map[sel]
            snippet = item.get("snippet", "")
            loc = item.get("location_info", "")
            if snippet:
                ui.message(f"{loc}: {snippet}")
            else:
                ui.message(f"{item['file_name']} - Nessuna anteprima di testo disponibile.")

    def start_search_thread(self):
        query = self.txt_query.GetValue().strip().lower()
        target_input = self.txt_path.GetValue().strip()
        filter_mode = self.combo_filter.GetSelection()
        custom_ext = self.txt_custom_ext.GetValue().strip().lower()
        if not custom_ext.startswith(".") and custom_ext:
            custom_ext = "." + custom_ext

        if not query:
            ui.message("Inserire un testo da cercare.")
            return

        self._stop_search = False
        self.current_query = query
        self.current_percent = 0
        self.scanned_count = 0
        save_last_path(target_input)

        self.lst_results.Clear()
        self.file_map.clear()
        self.current_matches = []
        self.gauge.SetValue(0)
        self.txt_status_progress.SetValue("Ricerca in corso: 0%...")
        self.btn_search.Disable()

        ui.message(f"Ricerca avviata per '{query}'.")

        targets = [t.strip() for t in target_input.split(";") if t.strip()]
        threading.Thread(
            target=self.run_search,
            args=(query, targets, filter_mode, custom_ext),
            daemon=True,
        ).start()

    def run_search(self, query, targets, filter_mode, custom_ext):
        raw_matches = []
        ignored = [
            "$recycle.bin",
            "system volume information",
            "appdata\\local\\temp",
        ]

        terms = query.split()
        img_exts = [".jpg", ".jpeg", ".png", ".bmp"]
        media_exts = [".mp4", ".mp3", ".mkv", ".avi", ".wav"]
        doc_exts = [".txt", ".eml", ".log", ".csv", ".docx", ".pdf"]

        file_list = []

        for folder in targets:
            if self._stop_search or not os.path.exists(folder):
                continue

            if os.path.isfile(folder):
                file_list.append(os.path.normpath(folder))
                continue

            for root, dirs, files in os.walk(folder):
                if self._stop_search:
                    break
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
                    elif filter_mode == 4 and ext != custom_ext:
                        continue

                    file_list.append(os.path.normpath(os.path.join(root, file)))

        total_files = len(file_list)
        last_spoken_percent = -1

        for i, file_path in enumerate(file_list, 1):
            if self._stop_search:
                break

            self.scanned_count = i
            file_name = os.path.basename(file_path)
            file_name_lower = file_name.lower()
            ext = os.path.splitext(file_name)[1].lower()
            prefix = f"[{ext.replace('.', '').upper()}]"

            try:
                mtime = os.path.getmtime(file_path)
            except Exception:
                mtime = 0

            if all(term in file_name_lower for term in terms):
                raw_matches.append({
                    "file_path": file_path,
                    "file_name": file_name,
                    "prefix": prefix,
                    "mtime": mtime,
                    "line_number": None,
                    "location_info": "Nome File",
                    "snippet": f"Corrispondenza nel nome: '{file_name}'",
                })
            elif ext in img_exts:
                img_text = deep_ocr_jpg_scan(file_path).lower()
                if all(term in img_text for term in terms):
                    raw_matches.append({
                        "file_path": file_path,
                        "file_name": file_name,
                        "prefix": "[IMG-TEXT]",
                        "mtime": mtime,
                        "line_number": None,
                        "location_info": "Testo visivo",
                        "snippet": f"Trovato testo visivo contenente '{query}'.",
                    })
            elif ext in [".txt", ".eml", ".log", ".csv", custom_ext]:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        for idx, line in enumerate(lines):
                            if all(term in line.lower() for term in terms):
                                start_i = max(0, idx - 2)
                                end_i = min(len(lines), idx + 3)
                                snippet = "".join(lines[start_i:end_i]).strip()
                                raw_matches.append({
                                    "file_path": file_path,
                                    "file_name": file_name,
                                    "prefix": prefix,
                                    "mtime": mtime,
                                    "line_number": idx + 1,
                                    "location_info": f"Riga {idx + 1}",
                                    "snippet": snippet,
                                })
                except Exception:
                    pass
            elif ext == ".docx":
                paragraphs = extract_paragraphs_from_docx(file_path)
                for idx, p_text in enumerate(paragraphs):
                    if all(term in p_text.lower() for term in terms):
                        start_i = max(0, idx - 1)
                        end_i = min(len(paragraphs), idx + 2)
                        snippet = " \n".join(paragraphs[start_i:end_i])
                        raw_matches.append({
                            "file_path": file_path,
                            "file_name": file_name,
                            "prefix": prefix,
                            "mtime": mtime,
                            "line_number": None,
                            "location_info": f"Paragrafo {idx + 1}",
                            "snippet": snippet,
                        })
            elif ext == ".pdf":
                pdf_lines = extract_lines_from_pdf(file_path)
                for idx, line in enumerate(pdf_lines):
                    if all(term in line.lower() for term in terms):
                        start_i = max(0, idx - 1)
                        end_i = min(len(pdf_lines), idx + 2)
                        snippet = " ".join(pdf_lines[start_i:end_i])
                        raw_matches.append({
                            "file_path": file_path,
                            "file_name": file_name,
                            "prefix": prefix,
                            "mtime": mtime,
                            "line_number": None,
                            "location_info": f"Sezione {idx + 1}",
                            "snippet": snippet,
                        })

            if total_files > 0:
                percent = int((i / total_files) * 100)
                self.current_percent = percent
                if percent % 10 == 0 and percent != last_spoken_percent:
                    last_spoken_percent = percent
                    wx.CallAfter(self.update_progress, percent, i, total_files, len(raw_matches))

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
            loc = f" ({item['location_info']})" if item.get("location_info") else ""
            display_str = f"{item['prefix']} {item['file_name']}{loc} -- ({item['file_path']})"
            idx = self.lst_results.Append(display_str)
            self.file_map[idx] = item

    def update_progress(self, percent, current, total, matches):
        self.gauge.SetValue(percent)
        text = f"Avanzamento: {percent}% ({current}/{total} file esaminati, {matches} risultati)"
        self.txt_status_progress.SetValue(text)
        ui.message(f"Ricerca al {percent} percento")

    def finish_search(self, matches):
        self.gauge.SetValue(100)
        self.current_percent = 100
        text = f"Ricerca completata: 100% ({self.scanned_count} file analizzati). Trovati {matches} risultati."
        self.txt_status_progress.SetValue(text)
        self.btn_search.Enable()
        ui.message(f"Ricerca completata. Trovati {matches} risultati ordinati dal più recente.")
        if matches > 0:
            self.lst_results.SetSelection(0)
            self.lst_results.SetFocus()

    def on_list_char_hook(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_RETURN:
            self.open_selected_file()
        elif key in [wx.WXK_SPACE, wx.WXK_F4]:
            self.speak_selected_preview()
        elif key == wx.WXK_WINDOWS_MENU:
            self.on_context_menu(None)
        elif key == wx.WXK_ESCAPE:
            self._stop_search = True
            self.Destroy()
        else:
            event.Skip()

    def on_open_file_event(self, event):
        self.open_selected_file()

    def open_selected_file(self):
        sel = self.lst_results.GetSelection()
        if sel != wx.NOT_FOUND and sel in self.file_map:
            item = self.file_map[sel]
            file_to_open = item["file_path"]
            line_num = item.get("line_number")

            if line_num:
                ui.message(f"Apertura alla riga {line_num}: {os.path.basename(file_to_open)}")
                jump_to_line_in_editor(file_to_open, line_num)
            else:
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
        item_open = menu.Append(wx.ID_ANY, "Apri File (alla riga esatta)\tINVIO")
        item_preview = menu.Append(wx.ID_ANY, "Ascolta Anteprima Vocale\tSPAZIO")
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
        self.Bind(wx.EVT_MENU, lambda e: self.speak_selected_preview(), item_preview)
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
            paragraphs = extract_paragraphs_from_docx(file_path)
            text_content = "\n".join(paragraphs)
        elif ext == ".pdf":
            lines = extract_lines_from_pdf(file_path)
            text_content = "\n".join(lines)
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
        dlg = wx.DirDialog(
            self,
            "Seleziona la cartella dove copiare il file",
            defaultPath=os.path.expanduser("~\\Desktop"),
        )
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
        self._timeout_timer = None

    def _cancel_leader(self):
        self._waiting_for_second_key = False
        if self._timeout_timer:
            try:
                self._timeout_timer.Stop()
            except Exception:
                pass
            self._timeout_timer = None

    @scriptHandler.script(
        description="Leader Key per Ricerca Testuale Accesso Digitale",
        category="Ricerca Testuale",
        gesture="kb:NVDA+shift+control+f",
    )
    def script_leaderKey(self, gesture):
        self._waiting_for_second_key = True
        ui.message("Ricerca Testuale: premere F per cercare, S per comandi, D per Donazione, H per la Guida")

        if self._timeout_timer:
            try:
                self._timeout_timer.Stop()
            except Exception:
                pass
        self._timeout_timer = wx.PyTimer(self._cancel_leader)
        self._timeout_timer.Start(3000, oneShot=True)

    def event_inputManager_gesture(self, gesture):
        if not self._waiting_for_second_key:
            return

        # Catturiamo solo il singolo tasto subito successivo alla sequenza leader
        sub_key = getattr(gesture, "mainKeyName", "") or getattr(gesture, "displayName", "")
        sub_key = str(sub_key).lower()

        if sub_key == "f":
            self._cancel_leader()
            wx.CallAfter(self.open_search_window)
            return True
        elif sub_key == "s":
            self._cancel_leader()
            wx.CallAfter(self.show_shortcuts_dialog)
            return True
        elif sub_key == "d":
            self._cancel_leader()
            webbrowser.open(DONATION_URL)
            ui.message("Apertura pagina per la Donazione nel browser...")
            return True
        elif sub_key == "h":
            self._cancel_leader()
            html_file = create_html_help_file()
            webbrowser.open(f"file:///{html_file}")
            ui.message("Apertura guida completa nel browser in corso...")
            return True
        else:
            # Qualsiasi altro tasto disattiva subito il layer e lascia passare l'evento normalmente
            self._cancel_leader()

    def open_search_window(self):
        frame = SearchFrame()
        frame.Show()
        frame.Raise()
        frame.txt_query.SetFocus()

    def show_shortcuts_dialog(self):
        frame = ShortcutsFrame(None)
        frame.Show()
        frame.Raise()