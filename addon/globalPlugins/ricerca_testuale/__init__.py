import addonHandler
import ctypes
import datetime
import globalPluginHandler
import globalVars
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
import quopri
import urllib.parse
import urllib.request
import email
from email import policy
import html
import csv

try:
    import tones
except ImportError:
    tones = None

addonHandler.initTranslation()

APP_TITLE = "Ricerca Testuale Accesso Digitale"
APP_VERSION = "1.4.5"
DONATION_URL = "https://paypal.me/AccessoDigitale"
YOUTUBE_URL = "https://www.youtube.com/@AccessoDigitale"
GITHUB_URL = "https://github.com/barramaurizio/ricerca_testuale_accesso_digitale/releases"

CONFIG_DIR = os.path.join(globalVars.appArgs.configPath, "rtad_data")
if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass
CONFIG_FILE = os.path.join(CONFIG_DIR, "rtad_settings.json")


def normalize_search_text(txt, remove_accents=False):
    if not txt:
        return ""
    for ap in ["’", "‘", "`", "´", "ʼ", "ʻ", "′", "‵", "՚", "Ꞌ"]:
        txt = txt.replace(ap, "'")
    for q in ["“", "”", "«", "»", "„"]:
        txt = txt.replace(q, '"')
    txt = txt.replace(chr(160), " ")
    if remove_accents:
        import unicodedata
        nfkd = unicodedata.normalize('NFKD', txt)
        return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return txt.lower()

def text_matches_terms(text, terms):
    if not text or not terms:
        return False
    n = normalize_search_text(text, False)
    if all(t in n for t in terms):
        return True
    n_no = normalize_search_text(text, True)
    terms_no = [normalize_search_text(t, True) for t in terms]
    return all(t in n_no for t in terms_no)

def clean_eml_text(raw_text):
    try:
        decoded = quopri.decodestring(raw_text.encode("latin1", errors="ignore")).decode("utf-8", errors="ignore")
    except Exception:
        decoded = raw_text
    decoded = urllib.parse.unquote_plus(decoded)
    decoded = re.sub(r"<[^<]+?>", " ", decoded)
    return " ".join(decoded.split())

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
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["last_path"] = path
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def load_bookmarks():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("bookmarks", [])
    except Exception:
        pass
    return []

def save_bookmarks(bookmarks_list):
    try:
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["bookmarks"] = bookmarks_list
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def get_dynamic_desktop_path():
    desktop_path = os.path.expanduser("~\\Desktop")
    if not os.path.exists(desktop_path):
        desktop_path = os.path.expanduser("~\\OneDrive\\Desktop")
        if not os.path.exists(desktop_path):
            desktop_path = os.path.expanduser("~")
    return desktop_path

def get_real_ready_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if bitmask & 1:
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                try:
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    if drive_type in (2, 3):  
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

class EmlViewerFrame(wx.Frame):
    def __init__(self, parent, file_path, search_query):
        super(EmlViewerFrame, self).__init__(
            parent,
            title=f"Lettore Email - {os.path.basename(file_path)}",
            size=(800, 650),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.file_path = file_path
        self.search_query = search_query

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.txt_display = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_close = wx.Button(panel, label="C&hiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
        hbox_btns.Add(btn_close, 0, wx.ALL, 5)
        
        vbox.Add(hbox_btns, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(vbox)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        
        wx.CallAfter(self.load_email)

    def load_email(self):
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                msg = email.message_from_file(f, policy=policy.default)
        except Exception:
            try:
                with open(self.file_path, "r", encoding="latin1", errors="ignore") as f:
                    msg = email.message_from_file(f, policy=policy.default)
            except Exception:
                self.txt_display.SetValue("Errore durante la lettura del file email.")
                return

        subject = msg.get("subject", "(Nessun oggetto)")
        sender = msg.get("from", "(Sconosciuto)")
        to = msg.get("to", "(Sconosciuto)")
        date = msg.get("date", "(Nessuna data)")

        body = ""
        body_html = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" not in content_disposition:
                    try:
                        if content_type == "text/plain":
                            body += part.get_content()
                        elif content_type == "text/html":
                            body_html += part.get_content()
                    except Exception:
                        pass
        else:
            try:
                body = msg.get_content()
            except Exception:
                pass

        if not body.strip() and body_html:
            body = body_html

        body = re.sub(r'<style.*?>.*?</style>', ' ', body, flags=re.IGNORECASE | re.DOTALL)
        body = re.sub(r'<script.*?>.*?</script>', ' ', body, flags=re.IGNORECASE | re.DOTALL)
        body = re.sub(r'<br\s*/?>', '\n', body, flags=re.IGNORECASE)
        body = re.sub(r'</p>', '\n\n', body, flags=re.IGNORECASE)
        body = re.sub(r'</div>', '\n', body, flags=re.IGNORECASE)
        body = re.sub(r'<[^>]+>', ' ', body)
        body = html.unescape(body)
        
        lines = [line.strip() for line in body.split('\n')]
        body = '\n'.join([line for line in lines if line])

        full_text = (
            f"Oggetto: {subject}\n"
            f"Da: {sender}\n"
            f"A: {to}\n"
            f"Data: {date}\n"
            f"{'-'*60}\n\n"
            f"{body}"
        )

        full_text = full_text.replace('\r\n', '\n').replace('\n', '\r\n')
        self.txt_display.SetValue(full_text)

        if self.search_query:
            terms = self.search_query.split()
            pos = -1
            term_len = 0
            
            text_lower = full_text.lower()
            for term in terms:
                t = term.lower()
                idx = text_lower.find(t)
                if idx != -1:
                    pos = idx
                    term_len = len(t)
                    break
            
            if pos == -1:
                text_norm = normalize_search_text(full_text, True)
                for term in normalize_search_text(self.search_query, True).split():
                    idx = text_norm.find(term)
                    if idx != -1:
                        pos = idx
                        term_len = len(term)
                        break

            self.txt_display.SetFocus()
            if pos != -1:
                self.txt_display.SetSelection(pos, pos + term_len)
            else:
                self.txt_display.SetInsertionPoint(0)
        else:
            self.txt_display.SetFocus()

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            event.Skip()

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
            "Comandi Globali NVDA:\n"
            "  - NVDA + Shift + Control + F : Apri la finestra principale di ricerca\n"
            "  - NVDA + Shift + Control + S : Apri questa finestra comandi\n"
            "  - NVDA + Shift + Control + D : Apri la pagina per le Donazioni PayPal\n"
            "  - (Per la Guida in formato Web, usa Gestione Componenti Aggiuntivi -> Guida)\n\n"
            "Comandi Finestra di Ricerca:\n"
            "  - Alt + T : Imposta la scansione su TUTTO IL PC (tutte le unità attive)\n"
            "  - Alt + N : Annulla ricerca in corso e mantieni i risultati\n"
            "  - Alt + I : Mostra Info Versione e Autore\n"
            "  - Alt + P : Annuncia all'istante lo stato e la percentuale di ricerca\n"
            "  - TAB : Raggiunge anche il campo 'Stato avanzamento' leggibile dallo screen reader\n"
            "  - Alt + K : Scatta uno screenshot salvato in 'Catture di schermata'\n"
            "  - Ctrl + P : Stampa rapida dei risultati di ricerca in lista\n"
            "  - Ctrl + E : Esporta Risultati\n"
            "  - Ctrl + D : Aggiunge percorso attuale ai Segnalibri\n"
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
        self.live_matches_count = 0 
        self.bookmark_items = []

        self._init_menu_bar()

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        lbl_query = wx.StaticText(panel, label="&Testo o frase da cercare (supporta più termini e dialetti):")
        vbox.Add(lbl_query, 0, wx.ALL, 5)
        self.txt_query = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.txt_query.Bind(wx.EVT_TEXT_ENTER, lambda e: self.start_search_thread())
        vbox.Add(self.txt_query, 0, wx.EXPAND | wx.ALL, 5)

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
                "Solo Documenti (.txt, .docx, .doc, .pdf, .eml, .log, .csv)",
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

        hbox_actions = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_search = wx.Button(panel, label="&Avvia Ricerca")
        self.btn_search.Bind(wx.EVT_BUTTON, lambda e: self.start_search_thread())
        hbox_actions.Add(self.btn_search, 0, wx.ALL, 5)

        self.btn_cancel = wx.Button(panel, label="A&nnulla Ricerca")
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel_search)
        self.btn_cancel.Disable()
        hbox_actions.Add(self.btn_cancel, 0, wx.ALL, 5)

        btn_info = wx.Button(panel, label="&Info Versione")
        btn_info.Bind(wx.EVT_BUTTON, self.on_show_info)
        hbox_actions.Add(btn_info, 0, wx.ALL, 5)

        btn_progress_now = wx.Button(panel, label="&Percentuale (Alt+P)")
        btn_progress_now.Bind(wx.EVT_BUTTON, lambda e: self.announce_progress())
        hbox_actions.Add(btn_progress_now, 0, wx.ALL, 5)

        btn_screenshot = wx.Button(panel, label="Cattura Sc&hermo (Alt+K)")
        btn_screenshot.Bind(wx.EVT_BUTTON, self.on_take_screenshot)
        hbox_actions.Add(btn_screenshot, 0, wx.ALL, 5)

        vbox.Add(hbox_actions, 0, wx.ALIGN_CENTER)

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

        hbox_bottom = wx.BoxSizer(wx.HORIZONTAL)
        btn_open = wx.Button(panel, label="&Apri File (Alla Riga)")
        btn_open.Bind(wx.EVT_BUTTON, self.on_open_file_event)
        hbox_bottom.Add(btn_open, 0, wx.ALL, 5)

        btn_preview = wx.Button(panel, label="Anteprima &Voce (F4)")
        btn_preview.Bind(wx.EVT_BUTTON, lambda e: self.speak_selected_preview())
        hbox_bottom.Add(btn_preview, 0, wx.ALL, 5)
        
        btn_export = wx.Button(panel, label="&Esporta Risultati...")
        btn_export.Bind(wx.EVT_BUTTON, self.on_export_results)
        hbox_bottom.Add(btn_export, 0, wx.ALL, 5)
        
        btn_print = wx.Button(panel, label="Stam&pa Risultati...")
        btn_print.Bind(wx.EVT_BUTTON, self.on_print_results)
        hbox_bottom.Add(btn_print, 0, wx.ALL, 5)

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

    def _init_menu_bar(self):
        menubar = wx.MenuBar()

        # Menu File
        file_menu = wx.Menu()
        item_export = file_menu.Append(wx.ID_ANY, "Esporta &Risultati...\tCtrl+E")
        item_print = file_menu.Append(wx.ID_ANY, "&Stampa Risultati...\tCtrl+P")
        file_menu.AppendSeparator()
        item_exit = file_menu.Append(wx.ID_EXIT, "E&sci\tCtrl+Q")
        menubar.Append(file_menu, "&File")

        # Menu Segnalibri
        self.bookmarks_menu = wx.Menu()
        item_add_bm = self.bookmarks_menu.Append(wx.ID_ANY, "Aggiungi percorso attuale ai Segnalibri\tCtrl+D")
        item_manage_bm = self.bookmarks_menu.Append(wx.ID_ANY, "Gestisci Segnalibri...")
        self.bookmarks_menu.AppendSeparator()
        menubar.Append(self.bookmarks_menu, "Se&gnalibri")
        
        self.Bind(wx.EVT_MENU, self.on_add_bookmark, item_add_bm)
        self.Bind(wx.EVT_MENU, self.on_manage_bookmarks, item_manage_bm)
        self.update_bookmarks_menu()

        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self.on_export_results, item_export)
        self.Bind(wx.EVT_MENU, self.on_print_results, item_print)
        self.Bind(wx.EVT_MENU, self.on_close, item_exit)

    def on_add_bookmark(self, event=None):
        path = self.txt_path.GetValue().strip()
        if not path:
            wx.CallLater(200, lambda: ui.message("Nessun percorso da salvare."))
            return
        bms = load_bookmarks()
        if path not in bms:
            bms.append(path)
            save_bookmarks(bms)
            self.update_bookmarks_menu()
            wx.CallLater(200, lambda: ui.message("Percorso salvato nei segnalibri."))
        else:
            wx.CallLater(200, lambda: ui.message("Percorso già presente nei segnalibri."))

    def on_manage_bookmarks(self, event=None):
        bms = load_bookmarks()
        if not bms:
            wx.CallLater(200, lambda: ui.message("Nessun segnalibro salvato."))
            return
        dlg = wx.SingleChoiceDialog(self, "Seleziona il segnalibro da ELIMINARE:", "Gestione Segnalibri", bms)
        if dlg.ShowModal() == wx.ID_OK:
            sel = dlg.GetStringSelection()
            if sel in bms:
                bms.remove(sel)
                save_bookmarks(bms)
                self.update_bookmarks_menu()
                wx.CallLater(200, lambda: ui.message("Segnalibro eliminato correttamente."))
        dlg.Destroy()

    def on_select_bookmark(self, path):
        self.txt_path.SetValue(path)
        save_last_path(path)
        wx.CallLater(200, lambda: ui.message(f"Segnalibro caricato: {path}"))

    def update_bookmarks_menu(self):
        for item_id in self.bookmark_items:
            self.bookmarks_menu.Remove(item_id)
        self.bookmark_items.clear()
        
        bms = load_bookmarks()
        for bm in bms:
            item = self.bookmarks_menu.Append(wx.ID_ANY, bm)
            self.bookmark_items.append(item.GetId())
            self.Bind(wx.EVT_MENU, lambda e, p=bm: self.on_select_bookmark(p), item)

    def on_cancel_search(self, event):
        if not self.btn_search.IsEnabled():
            self._stop_search = True
            self.btn_cancel.Disable()
            ui.message("Ricerca interrotta dall'utente. Salvataggio risultati parziali in corso...")

    def on_show_info(self, event):
        msg = f"{APP_TITLE}\nVersione: {APP_VERSION}\nAutore: Maurizio Barra\nLicenza: GPL v2"
        ui.message(f"Versione installata {APP_VERSION}. Autore Maurizio Barra.")
        wx.MessageBox(msg, "Informazioni Versione", wx.OK | wx.ICON_INFORMATION)

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
        if not self.btn_search.IsEnabled():
            found = getattr(self, 'live_matches_count', 0)
            msg = f"Avanzamento ricerca: {self.current_percent} percento. File esaminati: {self.scanned_count}. Trovati: {found}."
        else:
            found = len(self.current_matches)
            msg = f"Stato: {self.txt_status_progress.GetValue()}. Risultati in lista: {found}."
        ui.message(msg)

    def on_general_char_hook(self, event):
        key = event.GetKeyCode()
        ctrl = event.ControlDown()
        alt = event.AltDown()
        
        if ctrl and key in (ord("P"), ord("p")):
            self.on_print_results(None)
            return
        elif ctrl and key in (ord("E"), ord("e")):
            self.on_export_results(None)
            return
        elif ctrl and key in (ord("D"), ord("d")):
            self.on_add_bookmark(None)
            return
        elif alt and key in (ord("K"), ord("k")):
            self.on_take_screenshot(None)
            return
        elif alt and key in (ord("T"), ord("t")):
            self.on_search_all_pc(None)
            return
        elif alt and key in (ord("P"), ord("p")):
            self.announce_progress()
            return
        elif alt and key in (ord("N"), ord("n")):
            self.on_cancel_search(None)
            return
        elif alt and key in (ord("I"), ord("i")):
            self.on_show_info(None)
            return
        elif key == wx.WXK_ESCAPE:
            self._stop_search = True
            self.Destroy()
            return
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

        wildcard_filters = "File di Testo (*.txt)|*.txt|Pagina Web HTML (*.html)|*.html|File CSV per Tabelle (*.csv)|*.csv"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dlg = wx.FileDialog(self, message="Esporta Risultati", 
                            defaultDir=get_dynamic_desktop_path(),
                            defaultFile=f"Risultati_Ricerca_{timestamp}",
                            wildcard=wildcard_filters, 
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            export_file = dlg.GetPath()
            ext = os.path.splitext(export_file)[1].lower()
            
            try:
                if ext == ".csv":
                    with open(export_file, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f, delimiter=';')
                        writer.writerow(["Numero", "Nome File", "Percorso", "Informazione Posizione", "Estratto"])
                        for idx, item in enumerate(self.current_matches, 1):
                            writer.writerow([idx, item['file_name'], item['file_path'], item.get('location_info', ''), item.get('snippet', '')])
                
                elif ext == ".html":
                    with open(export_file, "w", encoding="utf-8") as f:
                        f.write("<!DOCTYPE html><html lang='it'><head><meta charset='utf-8'><title>Risultati Ricerca</title></head><body>\n")
                        f.write(f"<h1>Risultati Ricerca - {APP_TITLE}</h1>\n")
                        f.write(f"<p>Parola cercata: <strong>{self.current_query}</strong></p>\n")
                        f.write(f"<p>Totale risultati trovati: <strong>{len(self.current_matches)}</strong></p><hr>\n")
                        for idx, item in enumerate(self.current_matches, 1):
                            f.write(f"<h2>{idx}. {item['file_name']}</h2>\n<ul>\n")
                            f.write(f"<li><strong>Percorso Completo:</strong> {item['file_path']}</li>\n")
                            if item.get("location_info"):
                                f.write(f"<li><strong>Posizione:</strong> {item['location_info']}</li>\n")
                            if item.get("snippet"):
                                f.write(f"<li><strong>Estratto:</strong> {item['snippet']}</li>\n")
                            f.write("</ul>\n<hr>\n")
                        f.write("</body></html>")
                
                else: 
                    with open(export_file, "w", encoding="utf-8") as f:
                        f.write(f"=== {APP_TITLE} v{APP_VERSION} - Risultati Ricerca ===\n")
                        f.write(f"Data: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                        f.write(f"Parola cercata: {self.current_query}\n")
                        f.write(f"Totale risultati: {len(self.current_matches)}\n\n")
                        for idx, item in enumerate(self.current_matches, 1):
                            loc = f" [{item.get('location_info', '')}]" if item.get("location_info") else ""
                            f.write(f"{idx}. {item['file_name']}{loc}\n    Percorso: {item['file_path']}\n")
                            if item.get("snippet"):
                                f.write(f"    Estratto: {item['snippet']}\n")
                            f.write("-" * 50 + "\n")
                
                ui.message("Risultati esportati con successo nel formato scelto.")
            except Exception:
                ui.message("Errore durante l'esportazione dei risultati.")
        dlg.Destroy()

    def on_print_results(self, event):
        total_matches = len(self.current_matches)
        if total_matches == 0:
            ui.message("Nessun risultato da stampare.")
            return

        dlg = wx.TextEntryDialog(
            self,
            f"Hai trovato {total_matches} risultati.\nQuanti vuoi stamparne partendo dal primo?\n(Lascia vuoto e premi Invio per stamparli tutti)",
            "Opzioni di Stampa"
        )
        
        if dlg.ShowModal() == wx.ID_OK:
            val = dlg.GetValue().strip()
            limit = total_matches
            if val.isdigit():
                limit = int(val)
                if limit <= 0:
                    limit = total_matches
                elif limit > total_matches:
                    limit = total_matches
            
            dlg.Destroy()
            
            temp_print_path = os.path.join(CONFIG_DIR, "stampa_temporanea.txt")
            try:
                with open(temp_print_path, "w", encoding="utf-8") as f:
                    f.write(f"=== {APP_TITLE} - Risultati Ricerca ===\n")
                    f.write(f"Data Stampa: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                    f.write(f"Parola cercata: {self.current_query}\n")
                    f.write(f"Risultati stampati: {limit} di {total_matches}\n\n")
                    
                    for idx, item in enumerate(self.current_matches[:limit], 1):
                        loc = f" [{item.get('location_info', '')}]" if item.get("location_info") else ""
                        f.write(f"{idx}. {item['file_name']}{loc}\n    Percorso: {item['file_path']}\n")
                        if item.get("snippet"):
                            f.write(f"    Estratto: {item['snippet']}\n")
                        f.write("-" * 40 + "\n")
                
                notepad_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "notepad.exe")
                if not os.path.exists(notepad_path):
                    notepad_path = "notepad.exe"
                    
                subprocess.Popen([notepad_path, "/p", temp_print_path])
                
                if limit == total_matches:
                    ui.message("Inviati tutti i risultati alla stampante predefinita.")
                else:
                    ui.message(f"Inviati i primi {limit} risultati alla stampante predefinita.")
            except Exception:
                ui.message("Impossibile stampare. Assicurati di avere una stampante configurata.")
        else:
            dlg.Destroy()
            ui.message("Stampa annullata.")


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
        query = self.txt_query.GetValue().strip()
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
        self.live_matches_count = 0 
        save_last_path(target_input)

        self.lst_results.Clear()
        self.file_map.clear()
        self.current_matches = []
        self.gauge.SetValue(0)
        self.txt_status_progress.SetValue("Ricerca in corso: 0%...")
        
        self.btn_search.Disable()
        self.btn_cancel.Enable()

        ui.message(f"Ricerca avviata per '{query}'.")
        
        # --- INIZIO EARCONS NVDA (Avvio) ---
        if tones:
            try:
                wx.CallLater(100, lambda: tones.beep(800, 150))
            except Exception:
                pass
        # --- FINE EARCONS ---

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

        norm_query = normalize_search_text(query)
        terms = norm_query.split()
        img_exts = [".jpg", ".jpeg", ".png", ".bmp"]
        media_exts = [".mp4", ".mp3", ".mkv", ".avi", ".wav"]
        doc_exts = [".txt", ".eml", ".log", ".csv", ".docx", ".doc", ".pdf"]

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
            ext = os.path.splitext(file_name)[1].lower()
            prefix = f"[{ext.replace('.', '').upper()}]"

            try:
                mtime = os.path.getmtime(file_path)
            except Exception:
                mtime = 0

            if text_matches_terms(file_name, terms):
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
                img_text = normalize_search_text(deep_ocr_jpg_scan(file_path))
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
                            cleaned_line = clean_eml_text(line) if ext == ".eml" else line
                            if text_matches_terms(cleaned_line, terms):
                                start_i = max(0, idx - 2)
                                end_i = min(len(lines), idx + 3)
                                raw_snip = "".join(lines[start_i:end_i]).strip()
                                snippet = clean_eml_text(raw_snip) if ext == ".eml" else raw_snip
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
            elif ext in [".docx", ".doc"]:
                paragraphs = extract_paragraphs_from_docx(file_path)
                found_doc = False
                for idx, p_text in enumerate(paragraphs):
                    if text_matches_terms(p_text, terms):
                        found_doc = True
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
                if not found_doc and ext == ".doc":
                    try:
                        with open(file_path, "rb") as f:
                            raw_data = normalize_search_text(f.read(4194304).decode("latin1", errors="ignore"))
                            if text_matches_terms(raw_data, terms):
                                raw_matches.append({
                                    "file_path": file_path,
                                    "file_name": file_name,
                                    "prefix": prefix,
                                    "mtime": mtime,
                                    "line_number": None,
                                    "location_info": "Documento Word",
                                    "snippet": f"Trovato testo nel file Word: '{query}'.",
                                })
                    except Exception:
                        pass
            elif ext == ".pdf":
                pdf_lines = extract_lines_from_pdf(file_path)
                for idx, line in enumerate(pdf_lines):
                    if text_matches_terms(line, terms):
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
                self.live_matches_count = len(raw_matches) 
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
        
        if self._stop_search:
            text = f"Ricerca interrotta al {self.current_percent}% ({self.scanned_count} file analizzati). Salvati {matches} risultati parziali."
            ui.message(f"Ricerca annullata. Sono stati conservati {matches} risultati trovati finora.")
            # --- EARCONS NVDA (Annullato) ---
            if tones:
                try: wx.CallLater(100, lambda: tones.beep(400, 300))
                except Exception: pass
        else:
            text = f"Ricerca completata: 100% ({self.scanned_count} file analizzati). Trovati {matches} risultati."
            ui.message(f"Ricerca completata. Trovati {matches} risultati ordinati dal più recente.")
            # --- EARCONS NVDA (Completato) ---
            if tones:
                try:
                    if matches > 0:
                        wx.CallLater(100, lambda: tones.beep(1000, 150))
                        wx.CallLater(300, lambda: tones.beep(1500, 200))
                    else:
                        wx.CallLater(100, lambda: tones.beep(600, 300))
                except Exception:
                    pass
            
        self.txt_status_progress.SetValue(text)
        self.btn_search.Enable()
        self.btn_cancel.Disable()
        
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
            ext = os.path.splitext(file_to_open)[1].lower()

            if ext in [".docx", ".doc"]:
                ui.message(f"Apertura file Word: {os.path.basename(file_to_open)}")
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "open", file_to_open, None, None, 1)
                except Exception:
                    pass
                return
            
            if ext == ".eml":
                ui.message(f"Apertura email nel lettore interno: {os.path.basename(file_to_open)}")
                viewer = EmlViewerFrame(self, file_to_open, self.current_query)
                viewer.Show()
                return

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
        self.Bind(wx.EVT_MENU, lambda e: wx.CallLater(250, self.speak_selected_preview), item_preview)
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
        if ext in [".docx", ".doc"]:
            paragraphs = extract_paragraphs_from_docx(file_path)
            text_content = "\n".join(paragraphs)
        elif ext == ".pdf":
            lines = extract_lines_from_pdf(file_path)
            text_content = "\n".join(lines)
        elif ext in [".txt", ".eml", ".log", ".csv"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text_content = f.read()
                    if ext == ".eml":
                        text_content = clean_eml_text(text_content)
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
            defaultPath=get_dynamic_desktop_path(),
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

    @scriptHandler.script(
        description="Apri la finestra principale di Ricerca Testuale",
        category="Ricerca Testuale Accesso Digitale",
        gesture="kb:NVDA+shift+control+f",
    )
    def script_openSearch(self, gesture):
        wx.CallAfter(self.open_search_window)

    @scriptHandler.script(
        description="Mostra la finestra dei comandi rapidi",
        category="Ricerca Testuale Accesso Digitale",
        gesture="kb:NVDA+shift+control+s",
    )
    def script_showShortcuts(self, gesture):
        wx.CallAfter(self.show_shortcuts_dialog)

    @scriptHandler.script(
        description="Apri la pagina delle Donazioni PayPal",
        category="Ricerca Testuale Accesso Digitale",
        gesture="kb:NVDA+shift+control+d",
    )
    def script_openDonation(self, gesture):
        webbrowser.open(DONATION_URL)
        ui.message("Apertura pagina donazioni...")

    def open_search_window(self):
        frame = SearchFrame()
        frame.Show()
        frame.Raise()
        frame.txt_query.SetFocus()

    def show_shortcuts_dialog(self):
        frame = ShortcutsFrame(None)
        frame.Show()
        frame.Raise()