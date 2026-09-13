_speech_active = True
import ctypes
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
import zipfile
import quopri
import wx

APP_TITLE = "Ricerca Testuale Accesso Digitale"
APP_VERSION = "1.4.3"
DONATION_URL = "https://paypal.me/AccessoDigitale"
YOUTUBE_URL = "https://www.youtube.com/@AccessoDigitale"
GITHUB_REPO_URL = "https://github.com/barramaurizio/ricerca_testuale_accesso_digitale"
GITHUB_API_LATEST = "https://api.github.com/repos/barramaurizio/ricerca_testuale_accesso_digitale/releases/latest"

CONFIG_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "RTAD_Standalone")
if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")


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

_sapi_voice = None
_sapi_lock = threading.Lock()

def get_sapi_voice():
    global _sapi_voice
    with _sapi_lock:
        if _sapi_voice is None:
            try:
                import pythoncom
                import win32com.client
                pythoncom.CoInitialize()
                _sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
            except Exception:
                _sapi_voice = False
    return _sapi_voice if _sapi_voice is not False else None

def stop_accessible_speech():
    for dll_name in ("nvdaControllerClient64.dll", "nvdaControllerClient32.dll", "nvdaControllerClient.dll"):
        try:
            client = ctypes.windll.LoadLibrary(dll_name)
            if client.nvdaController_testIfRunning() == 0:
                client.nvdaController_cancelSpeech()
                break
        except Exception:
            pass
    v = get_sapi_voice()
    if v:
        try:
            v.Speak("", 2)
        except Exception:
            pass

def speak_accessible(text, force=False):
    global _speech_active
    if not _speech_active and not force:
        return
    if not text:
        return

    def _worker():
        for dll_name in ("nvdaControllerClient64.dll", "nvdaControllerClient32.dll", "nvdaControllerClient.dll"):
            try:
                client = ctypes.windll.LoadLibrary(dll_name)
                if client.nvdaController_testIfRunning() == 0:
                    client.nvdaController_cancelSpeech()
                    client.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                    client.nvdaController_speakText.restype = ctypes.c_long
                    if client.nvdaController_speakText(str(text)) == 0:
                        return
            except Exception:
                pass

        v = get_sapi_voice()
        if v:
            try:
                v.Speak(str(text), 3)
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()

def clean_eml_text(raw_text):
    try:
        decoded = quopri.decodestring(raw_text.encode("latin1", errors="ignore")).decode("utf-8", errors="ignore")
    except Exception:
        decoded = raw_text
    decoded = urllib.parse.unquote_plus(decoded)
    decoded = re.sub(r"<[^<]+?>", " ", decoded)
    return " ".join(decoded.split())


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
    <p><em>Applicazione Standalone - Versione {APP_VERSION}</em></p>

    <div class="box">
        <p><strong>Novit&agrave; Versione 1.4.3:</strong> Posizionamento millimetrico del cursore all'apertura dei file Microsoft Word (.doc/.docx) sul paragrafo esatto, miglioramenti generali e stabilit&agrave;.</p>
        <p>F7: Attiva / Disattiva sintesi vocale<br>CONTROL: Zittisce immediatamente la voce</p>
    </div>

    <h2>1. Scorciatoie da Tastiera</h2>
    <ul>
        <li><code>Alt + T</code>: Seleziona automaticamente tutte le unit&agrave; disco attive (Tutto il PC).</li>
        <li><code>Alt + N</code>: Annulla la ricerca in corso e salva i risultati trovati.</li>
        <li><code>Alt + I</code>: Info Versione e Autore.</li>
        <li><code>Alt + P</code>: Annuncia la percentuale, lo stato e i risultati in tempo reale.</li>
        <li><code>Tab</code>: Raggiunge la casella accessibile di stato e avanzamento ricerca.</li>
        <li><code>Alt + K</code>: Scatta uno screenshot e lo salva in <em>Catture di schermata</em>.</li>
        <li><code>SPAZIO</code> o <code>F4</code> (sui risultati): Anteprima vocale immediata del contesto.</li>
        <li><code>INVIO</code> (sui risultati): Apre il file alla riga esatta in Notepad++ o Blocco Note.</li>
        <li><code>Tasto APPLICAZIONI</code> o <code>Shift + F10</code>: Menu contestuale completo.</li>
        <li><code>F1</code>: Apri la presente guida nel browser predefinito.</li>
        <li><code>ESC</code>: Chiudi la finestra attiva.</li>
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
                    p_text = "".join([elem.text for elem in p.iter() if elem.tag.endswith("t") and elem.text])
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

def open_word_at_paragraph(file_path, paragraph_index, snippet_text):
    def _worker():
        opened = False
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import win32com.client
            try:
                word = win32com.client.GetActiveObject("Word.Application")
            except Exception:
                word = win32com.client.DispatchEx("Word.Application")
            word.Visible = True
            doc = word.Documents.Open(os.path.abspath(file_path))
            time.sleep(0.4)
            
            target_selected = False

            # Strategia prioritaria ottimizzata: Ricerca testuale mirata usando il cuore dello snippet
            if snippet_text:
                try:
                    lines = [l.strip() for l in snippet_text.split("\n") if l.strip()]
                    for line_to_find in lines:
                        if len(line_to_find) > 12:
                            rng = doc.Content
                            find = rng.Find
                            find.ClearFormatting()
                            find.Text = line_to_find[:40]
                            find.Forward = True
                            find.Wrap = 0
                            if find.Execute():
                                rng.Select()
                                target_selected = True
                                break
                except Exception:
                    pass

            # Fallback secondario: se la ricerca testuale fallisce, usiamo l'indice del paragrafo
            if not target_selected and paragraph_index and paragraph_index > 0:
                try:
                    doc.Paragraphs(paragraph_index).Range.Select()
                    target_selected = True
                except Exception:
                    pass

            if not target_selected:
                rng = doc.Content
                rng.Select()

            word.Activate()
            hwnd = ctypes.windll.user32.FindWindowW(None, word.Caption)
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 3)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            opened = True
        except Exception:
            pass
        if not opened:
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "open", file_path, None, None, 1)
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()

class ShortcutsFrame(wx.Frame):
    def __init__(self, parent):
        super(ShortcutsFrame, self).__init__(
            parent,
            title=f"{APP_TITLE} v{APP_VERSION} - Comandi",
            size=(700, 580),
            style=wx.DEFAULT_FRAME_STYLE,
        )

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.text_content = (
            f"{APP_TITLE} v{APP_VERSION}\n"
            "Autore e Sviluppatore: Maurizio Barra (Accesso Digitale)\n\n"
            "--------------------------------------------------\n"
            "COMANDI E SCORCIATOIE DA TASTIERA (STANDALONE):\n"
            "--------------------------------------------------\n"
            "  - Alt + T : Seleziona TUTTO IL PC (tutte le unità attive)\n"
            "  - Alt + N : Annulla ricerca in corso e mantieni i risultati\n"
            "  - Alt + I : Info Versione e Autore\n"
            "  - Alt + P : Annuncia stato, percentuale e risultati in tempo reale\n"
            "  - TAB : Raggiunge la casella 'Stato avanzamento'\n"
            "  - Alt + K : Scatta uno screenshot salvato in 'Catture di schermata'\n"
            "  - INVIO : Avvia ricerca o apri file alla riga esatta\n"
            "  - SPAZIO / F4 : Anteprima vocale immediata del risultato\n"
            "  - F7 : Attiva / Disattiva sintesi vocale (Mute)\n"
            "  - CONTROL : Zittisce all'istante la lettura in corso\n"
            "  - Tasto APPLICAZIONI : Menu contestuale completo\n"
            "  - F1 : Apri la Guida HTML nel Browser\n"
            "  - ESC : Chiudi la finestra\n\n"
            "--------------------------------------------------\n"
            "SOSTIENI IL PROGETTO:\n"
            f"{DONATION_URL}\n"
            "--------------------------------------------------"
        )

        lbl_info = wx.StaticText(panel, label="Usa le frecce Su/Giù e Sinistra/Destra per navigare nel testo:")
        vbox.Add(lbl_info, 0, wx.ALL, 8)

        self.txt_display = wx.TextCtrl(panel, value=self.text_content, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        vbox.Add(self.txt_display, 1, wx.EXPAND | wx.ALL, 8)

        hbox_btns = wx.BoxSizer(wx.HORIZONTAL)
        btn_copy = wx.Button(panel, label="&Copia Testo Comandi")
        btn_copy.Bind(wx.EVT_BUTTON, self.on_copy_text)
        hbox_btns.Add(btn_copy, 0, wx.ALL, 5)

        btn_guide = wx.Button(panel, label="Apri &Guida Browser...")
        btn_guide.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open(f"file:///{create_html_help_file()}"))
        hbox_btns.Add(btn_guide, 0, wx.ALL, 5)

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
            speak_accessible("Testo copiato negli appunti!")

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            event.Skip()

class MainWindow(wx.Frame):
    def __init__(self):
        super(MainWindow, self).__init__(
            None,
            title=f"{APP_TITLE} v{APP_VERSION} - Maurizio Barra",
            size=(880, 800),
            style=wx.DEFAULT_FRAME_STYLE,
        )

        self._stop_search = False
        self.current_percent = 0
        self.scanned_count = 0
        self.current_matches = []
        self.file_map = {}
        self.current_query = ""
        self.live_matches_count = 0

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

        self.txt_status_progress = wx.TextCtrl(panel, value="Pronto per la ricerca. Premi Alt+P o ascolta l'avanzamento.", style=wx.TE_READONLY)
        vbox.Add(self.txt_status_progress, 0, wx.EXPAND | wx.ALL, 5)

        self.gauge = wx.Gauge(panel, range=100)
        vbox.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 5)

        lbl_results = wx.StaticText(panel, label="&Risultati trovati (INVIO apre file, SPAZIO/F4 anteprima vocale, APPLICAZIONI opzioni):")
        vbox.Add(lbl_results, 0, wx.ALL, 5)
        self.lst_results = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.lst_results.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open_file_event)
        self.lst_results.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.lst_results.Bind(wx.EVT_KEY_DOWN, self.on_list_key_down)
        vbox.Add(self.lst_results, 1, wx.EXPAND | wx.ALL, 5)

        hbox_bottom = wx.BoxSizer(wx.HORIZONTAL)
        btn_open = wx.Button(panel, label="&Apri File (Alla Riga)")
        btn_open.Bind(wx.EVT_BUTTON, self.on_open_file_event)
        hbox_bottom.Add(btn_open, 0, wx.ALL, 5)

        btn_preview = wx.Button(panel, label="Anteprima &Voce (F4)")
        btn_preview.Bind(wx.EVT_BUTTON, lambda e: self.speak_selected_preview())
        hbox_bottom.Add(btn_preview, 0, wx.ALL, 5)

        btn_shortcuts = wx.Button(panel, label="&Comandi (F1)")
        btn_shortcuts.Bind(wx.EVT_BUTTON, lambda e: self.show_shortcuts_dialog())
        hbox_bottom.Add(btn_shortcuts, 0, wx.ALL, 5)

        btn_export = wx.Button(panel, label="&Esporta Risultati...")
        btn_export.Bind(wx.EVT_BUTTON, self.on_export_results)
        hbox_bottom.Add(btn_export, 0, wx.ALL, 5)

        btn_update = wx.Button(panel, label="Verifica &Aggiornamenti...")
        btn_update.Bind(wx.EVT_BUTTON, self.on_check_updates)
        hbox_bottom.Add(btn_update, 0, wx.ALL, 5)

        btn_close = wx.Button(panel, label="C&hiudi (ESC)")
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)
        hbox_bottom.Add(btn_close, 0, wx.ALL, 5)

        vbox.Add(hbox_bottom, 0, wx.EXPAND)
        panel.SetSizer(vbox)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_global_char_hook)

    def show_shortcuts_dialog(self):
        dlg = ShortcutsFrame(self)
        dlg.Show()
        dlg.Raise()

    def on_filter_changed(self, event):
        sel = self.combo_filter.GetSelection()
        self.txt_custom_ext.Enable(sel == 4)

    def on_search_all_pc(self, event):
        drives = get_real_ready_drives()
        drives_str = ";".join(drives)
        self.txt_path.SetValue(drives_str)
        save_last_path(drives_str)
        speak_accessible(f"Tutto il PC impostato: {len(drives)} unità attive. Premi Invio per avviare.")
        self.btn_search.SetFocus()

    def announce_progress(self):
        if not self.btn_search.IsEnabled():
            found = getattr(self, 'live_matches_count', 0)
            msg = f"Avanzamento {self.current_percent} percento. File esaminati {self.scanned_count}. Risultati trovati {found}."
        else:
            found = len(self.current_matches)
            msg = f"Stato: {self.txt_status_progress.GetValue()}. Risultati in lista: {found}."
        speak_accessible(msg)

    def on_cancel_search(self, event):
        if not self.btn_search.IsEnabled():
            self._stop_search = True
            self.btn_cancel.Disable()
            speak_accessible("Ricerca interrotta dall'utente. Salvataggio risultati parziali in corso...")

    def on_show_info(self, event):
        msg = f"{APP_TITLE}\nVersione: {APP_VERSION}\nAutore: Maurizio Barra\nLicenza: GPL v2"
        speak_accessible(f"Versione installata {APP_VERSION}. Autore Maurizio Barra.")
        wx.MessageBox(msg, "Informazioni Versione", wx.OK | wx.ICON_INFORMATION)

    def on_global_char_hook(self, event):
        key = event.GetKeyCode()
        alt = event.AltDown()

        if alt and key in (ord("P"), ord("p")):
            self.announce_progress()
            return
        elif alt and key in (ord("T"), ord("t")):
            self.on_search_all_pc(None)
            return
        elif alt and key in (ord("K"), ord("k")):
            self.on_take_screenshot(None)
            return
        elif alt and key in (ord("N"), ord("n")):
            self.on_cancel_search(None)
            return
        elif alt and key in (ord("I"), ord("i")):
            self.on_show_info(None)
            return
        elif key in (wx.WXK_F3, wx.WXK_F4):
            self.speak_selected_preview()
            return
        elif key == wx.WXK_F1:
            self.show_shortcuts_dialog()
            return
        elif key == wx.WXK_CONTROL:
            stop_accessible_speech()
            return
        elif key == wx.WXK_F7:
            self.on_toggle_speech()
            return
        elif key == wx.WXK_SHIFT:
            return
        elif key == wx.WXK_ESCAPE:
            self._stop_search = True
            self.Destroy()
            return

        focus = wx.Window.FindFocus()
        text_ctrls = (self.txt_query, self.txt_path, self.txt_custom_ext)
        
        if key == wx.WXK_SPACE:
            if focus not in text_ctrls and not isinstance(focus, wx.Button):
                self.speak_selected_preview()
                return

        if focus == self.lst_results or (focus not in text_ctrls and not isinstance(focus, wx.Button)):
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                self.open_selected_file()
                return
            elif key == wx.WXK_WINDOWS_MENU:
                self.on_context_menu(None)
                return

        event.Skip()

    def on_toggle_speech(self, evt=None):
        global _speech_active
        stop_accessible_speech()
        _speech_active = not _speech_active
        if _speech_active:
            speak_accessible("Sintesi vocale attivata", force=True)
        else:
            speak_accessible("Sintesi vocale disattivata", force=True)

    def on_close(self, event):
        self._stop_search = True
        self.Destroy()

    def on_browse(self, event):
        dlg = wx.DirDialog(self, "Seleziona cartella o unità", defaultPath=self.txt_path.GetValue())
        if dlg.ShowModal() == wx.ID_OK:
            selected_path = dlg.GetPath()
            self.txt_path.SetValue(selected_path)
            save_last_path(selected_path)
            speak_accessible(f"Percorso impostato: {selected_path}.")
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
                os.makedirs(pictures_dir, exist_ok=True)
            filename = f"Screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            full_path = os.path.join(pictures_dir, filename)
            bmp.SaveFile(full_path, wx.BITMAP_TYPE_PNG)
            speak_accessible("Screenshot salvato con successo in Catture di schermata.")
        except Exception:
            speak_accessible("Impossibile salvare lo screenshot.")

    def on_export_results(self, event):
        if not self.current_matches:
            speak_accessible("Nessun risultato da esportare.")
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
                    f.write(f"{idx}. {item['file_name']}{loc}\n    Percorso: {item['file_path']}\n")
                    if item.get("snippet"):
                        f.write(f"    Estratto: {item['snippet']}\n")
                    f.write("-" * 50 + "\n")
            speak_accessible(f"Risultati esportati sul Desktop nel file Risultati Ricerca {timestamp}.")
        except Exception:
            speak_accessible("Errore durante l'esportazione.")

    def on_list_key_down(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_SPACE, wx.WXK_F3, wx.WXK_F4):
            self.speak_selected_preview()
            return
        elif key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.open_selected_file()
            return
        event.Skip()

    def speak_selected_preview(self):
        sel = self.lst_results.GetSelection()
        if sel == wx.NOT_FOUND:
            speak_accessible("Nessun elemento selezionato nella lista.")
            return
        item = self.file_map.get(sel)
        if not item and 0 <= sel < len(self.current_matches):
            item = self.current_matches[sel]
        if item:
            snip = item.get("snippet", "").strip()
            loc = item.get("location_info", "")
            fname = item.get("file_name", "")
            if snip:
                speak_accessible(f"{loc}. {snip}")
            else:
                speak_accessible(f"{fname}. Nessuna riga di anteprima.")
        else:
            riga = self.lst_results.GetString(sel)
            speak_accessible(f"Elemento: {riga}")

    def on_check_updates(self, event=None, silent=False):
        def _check():
            try:
                if not silent:
                    speak_accessible("Verifica aggiornamenti in corso...")
                req = urllib.request.Request(GITHUB_API_LATEST, headers={"User-Agent": "RTAD-Updater"})
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    latest_tag = data.get("tag_name", "").replace("app-", "").replace("v", "").strip()
                    html_url = data.get("html_url", GITHUB_REPO_URL)
                    if latest_tag and latest_tag != APP_VERSION:
                        exe_url = None
                        for asset in data.get("assets", []):
                            if asset.get("name", "").endswith(".exe"):
                                exe_url = asset.get("browser_download_url")
                                break
                        def _prompt():
                            dlg = wx.MessageDialog(self, f"Nuova versione {latest_tag} disponibile!\n\nScarico subito?", "Aggiornamento", wx.YES_NO | wx.ICON_QUESTION)
                            if dlg.ShowModal() == wx.ID_YES:
                                dlg.Destroy()
                                if exe_url:
                                    def _dl():
                                        try:
                                            speak_accessible("Download in corso, attendere...")
                                            out = os.path.join(os.path.expanduser("~"), "Downloads", f"Ricerca_Testuale_v{latest_tag}.exe")
                                            req2 = urllib.request.Request(exe_url, headers={"User-Agent": "Mozilla/5.0"})
                                            with urllib.request.urlopen(req2) as resp, open(out, "wb") as f_out:
                                                f_out.write(resp.read())
                                            speak_accessible("Avvio aggiornamento.")
                                            subprocess.Popen([out])
                                            wx.CallAfter(self.Close)
                                        except Exception:
                                            wx.CallAfter(lambda: speak_accessible("Errore download."))
                                    threading.Thread(target=_dl, daemon=True).start()
                                else:
                                    webbrowser.open(html_url)
                            else:
                                dlg.Destroy()
                        wx.CallAfter(_prompt)
                    else:
                        if not silent:
                            wx.CallAfter(lambda: speak_accessible("Versione aggiornata."))
            except Exception:
                if not silent:
                    wx.CallAfter(lambda: speak_accessible("Impossibile verificare connessione."))
        threading.Thread(target=_check, daemon=True).start()

    def start_search_thread(self):
        query = self.txt_query.GetValue().strip()
        target_input = self.txt_path.GetValue().strip()
        filter_mode = self.combo_filter.GetSelection()
        custom_ext = self.txt_custom_ext.GetValue().strip().lower()
        if not custom_ext.startswith(".") and custom_ext:
            custom_ext = "." + custom_ext

        if not query:
            speak_accessible("Inserire un testo da cercare.")
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

        speak_accessible(f"Ricerca avviata per '{query}'.")

        targets = [t.strip() for t in target_input.split(";") if t.strip()]
        threading.Thread(target=self.run_search, args=(query, targets, filter_mode, custom_ext), daemon=True).start()

    def run_search(self, query, targets, filter_mode, custom_ext):
        raw_matches = []
        ignored = ["$recycle.bin", "system volume information", "appdata\\local\\temp"]
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
                if self._stop_search: break
                if any(ign in root.lower() for ign in ignored): continue
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if filter_mode == 1 and ext not in img_exts: continue
                    elif filter_mode == 2 and ext not in media_exts: continue
                    elif filter_mode == 3 and ext not in doc_exts: continue
                    elif filter_mode == 4 and ext != custom_ext: continue
                    file_list.append(os.path.normpath(os.path.join(root, file)))

        total_files = len(file_list)
        last_spoken_percent = -1

        for i, file_path in enumerate(file_list, 1):
            if self._stop_search: break
            self.scanned_count = i
            file_name = os.path.basename(file_path)
            ext = os.path.splitext(file_name)[1].lower()
            prefix = f"[{ext.replace('.', '').upper()}]"
            try: mtime = os.path.getmtime(file_path)
            except: mtime = 0

            if text_matches_terms(file_name, terms):
                raw_matches.append({"file_path": file_path, "file_name": file_name, "prefix": prefix, "mtime": mtime, "line_number": None, "paragraph_index": None, "location_info": "Nome File", "snippet": f"Corrispondenza: '{file_name}'"})
            elif ext in img_exts:
                img_text = normalize_search_text(deep_ocr_jpg_scan(file_path))
                if all(t in img_text for t in terms):
                    raw_matches.append({"file_path": file_path, "file_name": file_name, "prefix": "[IMG-TEXT]", "mtime": mtime, "line_number": None, "paragraph_index": None, "location_info": "Testo visivo", "snippet": f"Trovato testo visivo contenente '{query}'."})
            elif ext in [".txt", ".eml", ".log", ".csv", custom_ext]:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        for idx, line in enumerate(lines):
                            cleaned_line = clean_eml_text(line) if ext == ".eml" else line
                            if text_matches_terms(cleaned_line, terms):
                                start_i, end_i = max(0, idx - 2), min(len(lines), idx + 3)
                                raw_snip = "".join(lines[start_i:end_i]).strip()
                                snippet = clean_eml_text(raw_snip) if ext == ".eml" else raw_snip
                                raw_matches.append({"file_path": file_path, "file_name": file_name, "prefix": prefix, "mtime": mtime, "line_number": idx + 1, "paragraph_index": None, "location_info": f"Riga {idx + 1}", "snippet": snippet})
                except: pass
            elif ext in [".docx", ".doc"]:
                paragraphs = extract_paragraphs_from_docx(file_path)
                found_doc = False
                for idx, p_text in enumerate(paragraphs):
                    if text_matches_terms(p_text, terms):
                        found_doc = True
                        start_i, end_i = max(0, idx - 1), min(len(paragraphs), idx + 2)
                        snippet = " \n".join(paragraphs[start_i:end_i])
                        raw_matches.append({"file_path": file_path, "file_name": file_name, "prefix": prefix, "mtime": mtime, "line_number": None, "paragraph_index": idx + 1, "location_info": f"Paragrafo {idx + 1}", "snippet": snippet})
                if not found_doc and ext == ".doc":
                    try:
                        with open(file_path, "rb") as f:
                            raw_data = normalize_search_text(f.read(4194304).decode("latin1", errors="ignore"))
                            if text_matches_terms(raw_data, terms):
                                raw_matches.append({"file_path": file_path, "file_name": file_name, "prefix": prefix, "mtime": mtime, "line_number": None, "paragraph_index": 1, "location_info": "Documento Word", "snippet": f"Testo nel file Word: '{query}'."})
                    except: pass
            elif ext == ".pdf":
                pdf_lines = extract_lines_from_pdf(file_path)
                for idx, line in enumerate(pdf_lines):
                    if text_matches_terms(line, terms):
                        start_i, end_i = max(0, idx - 1), min(len(pdf_lines), idx + 2)
                        snippet = " ".join(pdf_lines[start_i:end_i])
                        raw_matches.append({"file_path": file_path, "file_name": file_name, "prefix": prefix, "mtime": mtime, "line_number": None, "paragraph_index": None, "location_info": f"Sezione {idx + 1}", "snippet": snippet})

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
        text = f"Avanzamento: {percent}% ({current}/{total} file, {matches} risultati)"
        self.txt_status_progress.SetValue(text)
        speak_accessible(f"Ricerca al {percent} percento")

    def finish_search(self, matches):
        self.gauge.SetValue(100)
        self.current_percent = 100
        if self._stop_search:
            text = f"Ricerca interrotta al {self.current_percent}% ({self.scanned_count} file). Salvati {matches} risultati."
            speak_accessible(f"Ricerca annullata. Conservati {matches} risultati.")
        else:
            text = f"Ricerca completata: 100% ({self.scanned_count} file). Trovati {matches} risultati."
            speak_accessible(f"Completata. Trovati {matches} risultati.")
        self.txt_status_progress.SetValue(text)
        self.btn_search.Enable()
        self.btn_cancel.Disable()
        if matches > 0:
            self.lst_results.SetSelection(0)
            self.lst_results.SetFocus()

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
                para_idx = item.get("paragraph_index")
                snippet_to_find = item.get("snippet", "")
                speak_accessible(f"Apertura Word su {item.get('location_info', 'documento')}")
                open_word_at_paragraph(file_to_open, para_idx, snippet_to_find)
                return
            if ext == ".eml":
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "open", file_to_open, None, None, 1)
                    speak_accessible(f"Apertura email: {os.path.basename(file_to_open)}")
                except: speak_accessible("Impossibile aprire l'email.")
                return

            if line_num:
                speak_accessible(f"Apertura alla riga {line_num}: {os.path.basename(file_to_open)}")
                jump_to_line_in_editor(file_to_open, line_num)
            else:
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "open", file_to_open, None, None, 1)
                    speak_accessible(f"Apertura file: {os.path.basename(file_to_open)}")
                except: speak_accessible("Errore apertura.")

    def on_context_menu(self, event):
        sel = self.lst_results.GetSelection()
        if sel == wx.NOT_FOUND or sel not in self.file_map: return
        item_data = self.file_map[sel]
        file_path = item_data["file_path"]
        snippet = item_data["snippet"]

        menu = wx.Menu()
        item_open = menu.Append(wx.ID_ANY, "Apri File (alla riga esatta)\tINVIO")
        item_preview = menu.Append(wx.ID_ANY, "Ascolta Anteprima Vocale\tSPAZIO")
        item_copy_snippet = menu.Append(wx.ID_ANY, "Copia Blocco Notizia")
        item_copy_path = menu.Append(wx.ID_ANY, "Copia Percorso Completo")
        item_copy_text = menu.Append(wx.ID_ANY, "Copia Contenuto (o Immagine)")
        item_copy_to = menu.Append(wx.ID_ANY, "Copia File altrove...")
        item_open_folder = menu.Append(wx.ID_ANY, "Apri Cartella")

        menu.AppendSeparator()
        sort_submenu = wx.Menu()
        item_sort_recent = sort_submenu.Append(wx.ID_ANY, "Dal Più Recente")
        item_sort_oldest = sort_submenu.Append(wx.ID_ANY, "Dal Meno Recente")
        item_sort_name = sort_submenu.Append(wx.ID_ANY, "Alfabeticamente (A-Z)")
        menu.AppendSubMenu(sort_submenu, "Ordinamento")

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
        if sort_type == "recent_first": speak_accessible("Ordinati dal più recente.")
        elif sort_type == "oldest_first": speak_accessible("Ordinati dal meno recente.")
        elif sort_type == "name": speak_accessible("Ordinati alfabeticamente.")

    def copy_snippet_to_clipboard(self, snippet):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(snippet))
            wx.TheClipboard.Close()
            speak_accessible("Estratto copiato negli appunti!")

    def copy_path_to_clipboard(self, file_path):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(file_path))
            wx.TheClipboard.Close()
            speak_accessible("Percorso copiato!")

    def copy_content_or_image_to_clipboard(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            try:
                img = wx.Image(file_path, wx.BITMAP_TYPE_ANY)
                if wx.TheClipboard.Open():
                    wx.TheClipboard.SetData(wx.BitmapDataObject(wx.Bitmap(img)))
                    wx.TheClipboard.Close()
                    speak_accessible("Immagine copiata negli appunti!")
                    return
            except: pass

        text_content = ""
        if ext in [".docx", ".doc"]: text_content = "\n".join(extract_paragraphs_from_docx(file_path))
        elif ext == ".pdf": text_content = "\n".join(extract_lines_from_pdf(file_path))
        elif ext in [".txt", ".eml", ".log", ".csv"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text_content = f.read()
                    if ext == ".eml": text_content = clean_eml_text(text_content)
            except: pass

        if text_content:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(text_content))
                wx.TheClipboard.Close()
                speak_accessible("Testo copiato negli appunti!")
        else: speak_accessible("Impossibile copiare il contenuto.")

    def copy_file_to_destination(self, file_path):
        dlg = wx.DirDialog(self, "Seleziona cartella", defaultPath=os.path.expanduser("~\\Desktop"))
        if dlg.ShowModal() == wx.ID_OK:
            dest_dir = dlg.GetPath()
            try:
                shutil.copy(file_path, dest_dir)
                speak_accessible(f"File copiato in {dest_dir}!")
            except: speak_accessible("Errore copia.")
        dlg.Destroy()

    def open_containing_folder(self, file_path):
        try:
            folder_path = os.path.dirname(file_path)
            ctypes.windll.shell32.ShellExecuteW(None, "explore", folder_path, None, None, 1)
            speak_accessible("Apertura cartella...")
        except: speak_accessible("Impossibile aprire la cartella.")

def main():
    app = wx.App(False)
    frame = MainWindow()
    frame.Show()
    frame.Raise()
    frame.txt_query.SetFocus()
    wx.CallLater(1200, frame.on_check_updates, None, True)
    if len(sys.argv) > 1:
        initial_arg = sys.argv[1]
        if os.path.exists(initial_arg):
            frame.txt_path.SetValue(initial_arg)
            save_last_path(initial_arg)
    app.MainLoop()

if __name__ == "__main__":
    main()