# -*- coding: utf-8 -*-
"""Lettore di una pagina HTML: intestazioni, link, indietro.

Una pagina Internet e un file .html locale sono lo stesso formato.
Word, EPUB e PDF restano sul lettore dei documenti.
"""

from __future__ import annotations

import html as html_lib
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from urllib.request import url2pathname

import wx

MAX_FETCH_BYTES = 2 * 1024 * 1024
MAX_PAGE_CHARS = 1_500_000
MAX_HEADINGS = 300
MAX_LINKS = 300
FETCH_TIMEOUT = 20

MSG_LOADING = "Carico la pagina: {name}. Attendere."
MSG_LOADING_ROW = "Carico la pagina. Attendere."
MSG_READY = "Pagina: {title}. {heads} intestazioni, {links} link."
MSG_NO_HEAD = "Nessuna intestazione in questa pagina."
MSG_NO_LINK = "Nessun link in questa pagina."
MSG_NO_TEXT = "Questa pagina non ha testo."
MSG_BACK_NONE = "Non c'è un punto precedente."
MSG_FWD_NONE = "Non c'è un punto successivo."
MSG_STEP = "Passo {i} di {n}."
MSG_POINT = "Punto: {title}."
MSG_HEAD_FIRST = (
    "Per un'intestazione, prima Invio nel lettore, poi lo stesso pulsante."
)
MSG_HEADING = "Intestazione: {title}."
MSG_EXTERNAL_HEAD = "Pagina aperta nel browser di Windows, sull'intestazione {title}."
MSG_EXTERNAL_LINK = "Pagina aperta nel browser di Windows, sul link {title}."
MSG_EXTERNAL_POINT = "Pagina aperta nel browser di Windows, sul punto {title}."
MSG_EXTERNAL_TOP = "Pagina aperta nel browser di Windows, dall'inizio."
MSG_EXTERNAL_NO_ANCHOR = (
    "Pagina aperta nel browser di Windows, dall'inizio. "
    "L'intestazione {title} non ha un indirizzo proprio."
)
MSG_ANCHOR_MISS = "Questo link resta in questa pagina, ma il punto non c'è."
MSG_NOT_PAGE = "Questo link non è una pagina. Destinazione: {href}"
MSG_FILE_FROM_WEB = "Da una pagina Internet non si apre un file del computer."
MSG_EXTERNAL = "Pagina aperta nel browser di Windows."
MSG_EXTERNAL_FAIL = "Impossibile aprire la pagina nel browser di Windows."
MSG_TOO_BIG = "La pagina supera 2 MB. Aprila nel browser di Windows."
MSG_TIMEOUT = "La pagina non ha risposto in tempo."
MSG_HTTP = "La pagina ha risposto con un errore ({code})."
MSG_DOWNLOAD = "Impossibile scaricare la pagina."
MSG_NOT_HTML = "Questo file non è una pagina HTML."
MSG_NOT_FOUND = "File non trovato."
MSG_EMPTY = "La pagina è vuota."

HINT = (
    "Tab: intestazioni, link e testo. "
    "Invio resta qui: un'intestazione o un link della stessa pagina "
    "vanno a quel punto, un link di un altro sito apre quella pagina. "
    "Nel testo, un indirizzo https si attiva con Invio. "
    "Maiusc+Tab dal testo seleziona quel link nell'elenco. "
    "Indietro e Avanti tornano al punto di prima, "
    "anche con Alt+freccia sinistra e Alt+freccia destra. "
    "Apri nel browser di Windows apre il link selezionato nell'elenco. "
    "Per un'intestazione, prima Invio qui, poi lo stesso pulsante: "
    "il browser si apre su quel punto. "
    "I tasti H e K di NVDA si usano in quel browser: qui si usano gli elenchi."
)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 RTAD"
)
_SKIP_SCHEME = ("javascript:", "data:", "vbscript:")
_HEAD_OPEN = re.compile(r"h([1-6])\b", re.I)
_ATTR = re.compile(
    r"""\b(id|href|name)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""",
    re.I,
)
_TITLE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
_CHARSET = re.compile(
    r"""charset\s*=\s*["']?\s*([a-zA-Z0-9._-]+)""",
    re.I,
)


def text_pos_to_ctrl(text: str, pos: int) -> int:
    """Posto nella stringa. Il controllo rich conta ogni a capo come un carattere."""
    if pos <= 0:
        return 0
    return min(pos, len(text or ""))


def ctrl_pos_to_text(text: str, ctrl_pos: int) -> int:
    """Dal posto del controllo al posto nella stringa."""
    if ctrl_pos <= 0:
        return 0
    return min(ctrl_pos, len(text or ""))


def _nth_find(text: str, needle: str, n: int) -> int:
    """Posizione dell'n-esima occorrenza, 1 = la prima. -1 se manca."""
    if not needle:
        return -1
    count = max(1, int(n or 1))
    start = 0
    found = -1
    for _ in range(count):
        found = (text or "").find(needle, start)
        if found < 0:
            return -1
        start = found + 1
    return found


def _any_attr(tag: str, name: str) -> str:
    match = re.search(
        rf"""(?i)\b{re.escape(name)}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""",
        tag or "",
    )
    if not match:
        return ""
    return html_lib.unescape(
        (match.group(1) or match.group(2) or match.group(3) or "").strip()
    )


def _attr(tag: str, name: str) -> str:
    for match in _ATTR.finditer(tag or ""):
        if match.group(1).lower() != name.lower():
            continue
        return html_lib.unescape(
            (match.group(2) or match.group(3) or match.group(4) or "").strip()
        )
    return ""


def _inline_text(fragment: str) -> str:
    text = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->", " ", fragment or "")
    text = re.sub(r"(?i)<br\s*/?>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _is_http(url: str) -> bool:
    return (url or "").lower().startswith(("http://", "https://"))


def _is_file_url(url: str) -> bool:
    return (url or "").lower().startswith("file:")


def file_url_to_path(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    path = url2pathname(parsed.path or "")
    if os.name == "nt" and len(path) >= 3 and path[0] in "\\/" and path[2] == ":":
        path = path[1:]
    return os.path.normpath(path)


def path_to_file_url(path: str) -> str:
    return urllib.parse.urljoin("file:", urllib.request.pathname2url(os.path.abspath(path)))


def _same_document(base: str, absolute: str) -> bool:
    left = urllib.parse.urldefrag(base or "")[0].rstrip("/")
    right = urllib.parse.urldefrag(absolute or "")[0].rstrip("/")
    return bool(left) and left == right


def http_base_from_html(text: str) -> str:
    """<base href>, oppure canonical / og:url, se è un indirizzo http."""
    head = (text or "")[:30000]
    match = re.search(r"(?is)<base\b([^>]*)>", head)
    if match:
        href = _attr(match.group(1), "href")
        if _is_http(href):
            return href
    for link in re.finditer(r"(?is)<link\b([^>]*)>", head):
        tag = link.group(1)
        rel = _any_attr(tag, "rel").lower().split()
        if "canonical" in rel:
            href = _attr(tag, "href")
            if _is_http(href):
                return href
    for meta in re.finditer(r"(?is)<meta\b([^>]*)>", head):
        tag = meta.group(1)
        if _any_attr(tag, "property").lower() == "og:url":
            content = _any_attr(tag, "content")
            if _is_http(content):
                return content
    return ""


def classify_href(base: str, href: str) -> dict:
    raw = html_lib.unescape((href or "").strip())
    low = raw.lower()
    if not raw or low.startswith(_SKIP_SCHEME):
        return {"kind": "skip", "target": "", "fragment": "", "href": raw}
    if low.startswith("mailto:"):
        return {"kind": "mailto", "target": raw, "fragment": "", "href": raw}
    joined = urllib.parse.urljoin(base or "", raw)
    absolute, fragment = urllib.parse.urldefrag(joined)
    fragment = urllib.parse.unquote(fragment or "")
    base_scheme = urllib.parse.urlparse(base or "").scheme.lower()
    target_scheme = urllib.parse.urlparse(absolute).scheme.lower()
    if base_scheme in ("http", "https") and target_scheme == "file":
        return {"kind": "blocked", "target": absolute, "fragment": fragment, "href": raw}
    if fragment and _same_document(base, absolute):
        kind = "anchor"
    elif target_scheme in ("http", "https"):
        kind = "http"
    elif target_scheme == "file":
        kind = "file"
    else:
        kind = "other"
    return {"kind": kind, "target": absolute, "fragment": fragment, "href": raw}


def build_page(raw: str, base: str) -> dict:
    """Titolo, intestazioni, link e testo con marcatori [H1]."""
    raw = raw or ""
    if len(raw) > MAX_PAGE_CHARS:
        raw = raw[:MAX_PAGE_CHARS]
    title_match = _TITLE.search(raw)
    title = _inline_text(title_match.group(1)) if title_match else ""
    raw = re.sub(
        r"(?is)<head\b[^>]*>.*?</head>|<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>|<!--.*?-->",
        " ",
        raw,
    )
    headings = []
    links = []
    anchors: dict[str, str] = {}
    lines: list[str] = []
    current: list[str] = []
    pending_anchors: list[str] = []
    heading_level = 0
    heading_anchor = ""
    heading_href = ""
    line_hrefs: list[str] = []
    skip_until = ""
    marker_occ: dict[str, int] = {}
    i = 0
    n = len(raw)

    def add_heading(level: int, text: str, anchor: str, href: str):
        marker = f"[H{level}] {text}"
        lines.append(marker)
        target = ""
        if href:
            info = classify_href(base, href)
            if info.get("kind") in ("http", "file") and info.get("target"):
                target = info.get("target") or ""
            elif info.get("kind") == "anchor" and info.get("fragment"):
                target = _with_fragment(base, info.get("fragment") or "")
        if len(headings) < MAX_HEADINGS:
            marker_occ[marker] = marker_occ.get(marker, 0) + 1
            headings.append(
                {
                    "level": level,
                    "title": text,
                    "anchor": anchor,
                    "marker": marker,
                    "occ": marker_occ[marker],
                    "href": target,
                }
            )
        remember(anchor, marker)

    def remember(anchor: str, marker: str):
        if anchor and marker and not anchors.get(anchor):
            anchors[anchor] = marker

    def flush_line():
        piece = _inline_text("".join(current))
        current.clear()
        hrefs = list(line_hrefs)
        line_hrefs.clear()
        if piece and len(hrefs) == 1:
            info = classify_href(base, hrefs[0])
            token = ""
            if info.get("kind") == "anchor" and info.get("fragment"):
                token = "#" + (info.get("fragment") or "")
            elif info.get("kind") == "http" and len(piece) >= 40:
                token = info.get("target") or ""
            if token and token not in piece:
                piece = piece + " " + token
        if piece:
            lines.append(piece)
            while pending_anchors:
                remember(pending_anchors.pop(0), piece)

    while i < n:
        if raw[i] != "<":
            j = raw.find("<", i)
            if j < 0:
                j = n
            if not skip_until:
                current.append(raw[i:j])
            i = j
            continue
        if raw.startswith("<!--", i):
            j = raw.find("-->", i + 4)
            i = n if j < 0 else j + 3
            continue
        j = raw.find(">", i)
        if j < 0:
            break
        tag = raw[i + 1 : j].strip()
        i = j + 1
        if not tag:
            continue
        closing = tag.startswith("/")
        name = tag[1:].split(None, 1)[0].lower() if closing else tag.split(None, 1)[0].lower()
        if name in ("script", "style"):
            if not closing:
                skip_until = f"</{name}"
            elif skip_until == f"</{name}":
                skip_until = ""
            continue
        if skip_until:
            continue
        if closing and heading_level and name == f"h{heading_level}":
            text = _inline_text("".join(current))
            current.clear()
            if text:
                add_heading(heading_level, text, heading_anchor, heading_href)
            heading_level = 0
            heading_anchor = ""
            heading_href = ""
            continue
        if closing and name in (
            "p",
            "li",
            "tr",
            "div",
            "dt",
            "dd",
            "pre",
            "section",
            "article",
            "blockquote",
            "br",
        ):
            flush_line()
            continue
        if name == "br":
            flush_line()
            continue
        head = _HEAD_OPEN.fullmatch(name)
        if head and not closing:
            flush_line()
            heading_level = int(head.group(1))
            heading_anchor = _attr(tag, "id")
            heading_href = ""
            continue
        if not closing and name == "a":
            href = _attr(tag, "href")
            if href and heading_level and not heading_href:
                heading_href = href
            elif href and not heading_level:
                line_hrefs.append(href)
        if not closing and not heading_level:
            anchor = _attr(tag, "id") or (name == "a" and _attr(tag, "name"))
            if anchor and anchor not in anchors and anchor not in pending_anchors:
                pending_anchors.append(anchor)
    flush_line()
    if heading_level and current:
        text = _inline_text("".join(current))
        if text:
            add_heading(heading_level, text, heading_anchor, heading_href)
    body = "\n".join(lines).strip()
    links = _links_with_text(raw, base)
    if not title:
        title = headings[0]["title"] if headings else "Pagina"
    message = MSG_READY.format(title=title, heads=len(headings), links=len(links))
    return {
        "ok": bool(body or headings or links),
        "title": title,
        "headings": headings,
        "links": links,
        "anchors": anchors,
        "body": body,
        "base": base,
        "message": message,
    }


def _links_with_text(raw: str, base: str) -> list[dict]:
    found = []
    for match in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", raw):
        href = _attr(match.group(1), "href")
        if not href:
            continue
        info = classify_href(base, href)
        if info["kind"] == "skip":
            continue
        info["text"] = _inline_text(match.group(2)) or href
        found.append(info)
        if len(found) >= MAX_LINKS:
            break
    return found


def decode_html_bytes(raw: bytes, header_charset: str = "") -> str:
    if not raw:
        return ""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="ignore")
    charset = (header_charset or "").strip()
    if not charset:
        head = raw[:4000].decode("ascii", errors="ignore")
        found = _CHARSET.search(head)
        if found:
            charset = found.group(1)
    for encoding in (charset, "utf-8", "cp1252", "latin1"):
        if not encoding:
            continue
        try:
            return raw.decode(encoding)
        except LookupError:
            continue
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _read_limited(resp) -> tuple[bytes, str]:
    length = resp.headers.get("Content-Length")
    try:
        if length and int(length) > MAX_FETCH_BYTES:
            return b"", MSG_TOO_BIG
    except ValueError:
        pass
    raw = resp.read(MAX_FETCH_BYTES + 1)
    if len(raw) > MAX_FETCH_BYTES:
        return b"", MSG_TOO_BIG
    ctype = resp.headers.get("Content-Type", "")
    charset = ""
    found = _CHARSET.search(ctype or "")
    if found:
        charset = found.group(1)
    return raw, charset


def fetch_html(url: str) -> tuple[str, str, str]:
    """(html, base_finale, errore)."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml,*/*"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw, charset_or_err = _read_limited(resp)
            if not raw and charset_or_err == MSG_TOO_BIG:
                return "", url, MSG_TOO_BIG
            final = resp.geturl() or url
            ctype = (resp.headers.get("Content-Type") or "").lower()
    except urllib.error.HTTPError as exc:
        return "", url, MSG_HTTP.format(code=exc.code)
    except TimeoutError:
        return "", url, MSG_TIMEOUT
    except Exception as exc:
        if "timed out" in str(exc).lower():
            return "", url, MSG_TIMEOUT
        return "", url, MSG_DOWNLOAD
    if charset_or_err == MSG_TOO_BIG:
        return "", final, MSG_TOO_BIG
    text = decode_html_bytes(raw, charset_or_err if isinstance(charset_or_err, str) else "")
    if "html" not in ctype and "xml" not in ctype and "<" not in text[:500].lower():
        return "", final, MSG_NOT_HTML
    return text, final, ""


def read_html_file(path: str) -> tuple[str, str, str]:
    if not path or not os.path.isfile(path):
        return "", "", MSG_NOT_FOUND
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_FETCH_BYTES + 1)
    except Exception:
        return "", "", MSG_NOT_FOUND
    if len(raw) > MAX_FETCH_BYTES:
        return "", path_to_file_url(path), MSG_TOO_BIG
    text = decode_html_bytes(raw)
    if "<" not in text[:800].lower() and not path.lower().endswith((".html", ".htm")):
        return "", path_to_file_url(path), MSG_NOT_HTML
    return text, path_to_file_url(path), ""


def load_page(source: str, page_url: str = "") -> tuple[dict, str]:
    """Carica un percorso, un file:// o un http(s). (pagina, errore).

    page_url è l'indirizzo Internet da cui il file è stato scaricato:
    i link che iniziano con / si risolvono su quel sito.
    """
    source = (source or "").strip()
    page_url = (page_url or "").strip()
    if _is_http(source):
        text, base, err = fetch_html(source)
    elif _is_file_url(source):
        text, base, err = read_html_file(file_url_to_path(source))
        base = source if not err else base
    else:
        text, base, err = read_html_file(source)
    if err:
        return {}, err
    if not (text or "").strip():
        return {}, MSG_EMPTY
    if not _is_http(source):
        declared = ""
        match = re.search(r"(?is)<base\b([^>]*)>", (text or "")[:30000])
        if match:
            declared = _attr(match.group(1), "href")
        if _is_http(declared):
            base = declared
        elif _is_http(page_url):
            base = page_url
        else:
            found = http_base_from_html(text)
            if found:
                base = found
    else:
        match = re.search(r"(?is)<base\b([^>]*)>", (text or "")[:30000])
        if match and _is_http(_attr(match.group(1), "href")):
            base = _attr(match.group(1), "href")
    page = build_page(text, base)
    page["source"] = source
    page["address"] = base if _is_http(base) else source
    page["link_base"] = base if _is_http(base) else ""
    return page, ""


def display_name(source: str) -> str:
    source = (source or "").strip()
    if _is_http(source):
        parsed = urllib.parse.urlparse(source)
        name = urllib.parse.unquote(os.path.basename(parsed.path or "") or "")
        if not name or name in ("/", "."):
            name = parsed.netloc or source
        return name[:80]
    if _is_file_url(source):
        return os.path.basename(file_url_to_path(source)) or "pagina.html"
    return os.path.basename(source) or "pagina.html"


def heading_open_address(head: dict, base: str) -> tuple[str, str]:
    """Indirizzo da aprire nel browser per un'intestazione, e la frase."""
    title = (head or {}).get("title") or ""
    href = ((head or {}).get("href") or "").strip()
    if href and (_is_http(href) or _is_file_url(href)):
        return href, MSG_EXTERNAL_HEAD.format(title=title)
    anchor = ((head or {}).get("anchor") or "").strip()
    if anchor:
        return _with_fragment(base, anchor), MSG_EXTERNAL_HEAD.format(title=title)
    return base, MSG_EXTERNAL_NO_ANCHOR.format(title=title)


def windows_browser_argv(url: str) -> list[str]:
    """Argomenti del browser predefinito. Su Edge, --single-argument tiene il #."""
    if os.name != "nt":
        return []
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice",
        ) as key:
            progid = winreg.QueryValueEx(key, "ProgId")[0]
        with winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT, str(progid) + r"\shell\open\command"
        ) as key:
            command = winreg.QueryValueEx(key, "")[0]
    except Exception:
        return []
    match = re.match(r'\s*"([^"]+\.exe)"', command or "", re.I)
    if not match:
        match = re.match(r"\s*(\S+\.exe)", command or "", re.I)
    if not match or not os.path.isfile(match.group(1)):
        return []
    exe = match.group(1)
    if "--single-argument" in (command or "").lower():
        return [exe, "--single-argument", url]
    return [exe, url]


def open_in_windows_browser(address: str) -> bool:
    """Apre l'indirizzo, anche con #punto, nel browser di Windows."""
    target = (address or "").strip()
    if not target:
        return False
    try:
        root, fragment = urllib.parse.urldefrag(target)
        if _is_http(root) or _is_file_url(root):
            url = root
        elif os.path.isfile(root):
            url = path_to_file_url(root)
        else:
            return False
        if fragment:
            url += "#" + urllib.parse.quote(fragment, safe="")
        argv = windows_browser_argv(url)
        if argv:
            import subprocess

            subprocess.Popen(argv)
            return True
        import webbrowser

        return bool(webbrowser.open(url))
    except Exception:
        return False


def _with_fragment(base: str, fragment: str) -> str:
    root, _old = urllib.parse.urldefrag(base or "")
    fragment = (fragment or "").strip()
    if not fragment:
        return root
    return root + "#" + fragment


class HtmlBrowserFrame(wx.Frame):
    """Pagina HTML dentro RTAD. La stessa frase è in etichetta e in voce."""

    def __init__(self, speak, source, parent=None, page_url: str = ""):
        self.speak = speak or (lambda *_a, **_k: None)
        self._alive = True
        self._gen = 0
        self._hint_said = False
        self.history: list[dict] = []
        self.index = -1
        self._last_list = "heads"
        name = display_name(source)
        super().__init__(
            parent,
            title=f"Lettore pagina — {name}",
            size=(820, 720),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.lbl_status = wx.StaticText(panel, label=MSG_LOADING.format(name=name))
        self.lbl_status.SetName("Stato pagina")
        vbox.Add(self.lbl_status, 0, wx.ALL | wx.EXPAND, 8)
        self.lbl_address = wx.StaticText(panel, label=source)
        self.lbl_address.SetName("Indirizzo della pagina")
        vbox.Add(self.lbl_address, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        self.lbl_hint = wx.StaticText(panel, label=HINT)
        vbox.Add(self.lbl_hint, 0, wx.ALL | wx.EXPAND, 8)

        vbox.Add(wx.StaticText(panel, label="&Intestazioni"), 0, wx.LEFT | wx.RIGHT, 8)
        self.lst_heads = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.lst_heads.SetName("Intestazioni")
        self.lst_heads.Append(MSG_LOADING_ROW)
        self.lst_heads.SetSelection(0)
        vbox.Add(self.lst_heads, 0, wx.EXPAND | wx.ALL, 8)
        self.lst_heads.Bind(wx.EVT_LISTBOX_DCLICK, self.on_heading)
        self.lst_heads.Bind(wx.EVT_SET_FOCUS, lambda e: self._remember_list("heads", e))

        vbox.Add(wx.StaticText(panel, label="&Link"), 0, wx.LEFT | wx.RIGHT, 8)
        self.lst_links = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.lst_links.SetName("Link")
        self.lst_links.Append(MSG_LOADING_ROW)
        self.lst_links.SetSelection(0)
        vbox.Add(self.lst_links, 0, wx.EXPAND | wx.ALL, 8)
        self.lst_links.Bind(wx.EVT_LISTBOX_DCLICK, self.on_link)
        self.lst_links.Bind(wx.EVT_SET_FOCUS, lambda e: self._remember_list("links", e))

        vbox.Add(wx.StaticText(panel, label="&Testo"), 0, wx.LEFT | wx.RIGHT, 8)
        self.txt = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_AUTO_URL,
        )
        self.txt.SetName("Testo della pagina")
        vbox.Add(self.txt, 1, wx.EXPAND | wx.ALL, 8)
        self.txt.Bind(wx.EVT_TEXT_URL, self.on_text_url)
        self.txt.Bind(wx.EVT_KILL_FOCUS, self._on_text_kill_focus)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_back = wx.Button(panel, label="&Indietro")
        self.btn_fwd = wx.Button(panel, label="A&vanti")
        self.btn_reload = wx.Button(panel, label="&Ricarica")
        self.btn_external = wx.Button(panel, label="Apri nel browser di &Windows")
        btn_close = wx.Button(panel, label="&Chiudi")
        self.btn_back.Bind(wx.EVT_BUTTON, lambda e: self.go_back())
        self.btn_fwd.Bind(wx.EVT_BUTTON, lambda e: self.go_forward())
        self.btn_reload.Bind(wx.EVT_BUTTON, lambda e: self.reload_page())
        self.btn_external.Bind(wx.EVT_BUTTON, lambda e: self.open_external())
        btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        for btn in (self.btn_back, self.btn_fwd, self.btn_reload, self.btn_external, btn_close):
            buttons.Add(btn, 0, wx.ALL, 5)
        vbox.Add(buttons, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        panel.SetSizer(vbox)
        for label in (self.lbl_status, self.lbl_address, self.lbl_hint):
            try:
                label.Wrap(760)
            except Exception:
                pass
        self.Centre()
        self._id_back = wx.NewIdRef()
        self._id_fwd = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, lambda e: self.go_back(), id=self._id_back)
        self.Bind(wx.EVT_MENU, lambda e: self.go_forward(), id=self._id_fwd)
        self.SetAcceleratorTable(
            wx.AcceleratorTable(
                [
                    (wx.ACCEL_ALT, wx.WXK_LEFT, self._id_back),
                    (wx.ACCEL_ALT, wx.WXK_RIGHT, self._id_fwd),
                ]
            )
        )
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self._set_nav_enabled()
        self.Show()
        self._say(HINT, force_hint=True)
        self.load(source, push=True, page_url=page_url)

    def _on_close(self, event):
        self._alive = False
        self._gen += 1
        event.Skip()

    def _say(self, text: str, force_hint: bool = False):
        if force_hint:
            self._hint_said = True
        try:
            self.speak(text)
        except Exception:
            pass

    def _set_status(self, text: str):
        self.lbl_status.SetLabel(text)
        try:
            self.lbl_status.Wrap(760)
        except Exception:
            pass

    def _set_nav_enabled(self):
        self.btn_back.Enable(True)
        self.btn_fwd.Enable(True)

    def _step_sentence(self) -> str:
        total = max(1, len(self.history))
        current = self.index + 1 if self.index >= 0 else 1
        return MSG_STEP.format(i=current, n=total)

    def current_page(self) -> dict:
        if 0 <= self.index < len(self.history):
            return self.history[self.index]
        return {}

    def load(self, source: str, push: bool, page_url: str = ""):
        self._gen += 1
        gen = self._gen
        name = display_name(source)
        self.SetTitle(f"Lettore pagina — {name}")
        self._set_status(MSG_LOADING.format(name=name))
        self._fill_lists([], [], loading=True)
        self._say(MSG_LOADING.format(name=name))

        def work():
            page, err = load_page(source, page_url=page_url)
            wx.CallAfter(self._finish_load, gen, source, page, err, push)

        threading.Thread(target=work, daemon=True).start()

    def _finish_load(self, gen, source, page, err, push):
        if not self._alive or gen != self._gen:
            return
        if err or not page:
            self._show_error(err or MSG_DOWNLOAD, source)
            return
        page["source"] = page.get("source") or source
        if push:
            if self.index < len(self.history) - 1:
                self.history = self.history[: self.index + 1]
            self.history.append(page)
            self.index = len(self.history) - 1
        else:
            if 0 <= self.index < len(self.history):
                self.history[self.index] = page
            else:
                self.history = [page]
                self.index = 0
        self._render(page)

    def _show_error(self, err: str, source: str):
        self._set_status(err)
        self.lbl_address.SetLabel(source)
        self._fill_lists([], [])
        self.txt.SetValue(err)
        self._set_nav_enabled()
        self._say(err)

    def _fill_lists(self, headings, links, loading=False):
        self.lst_heads.Clear()
        self.lst_links.Clear()
        if loading:
            self.lst_heads.Append(MSG_LOADING_ROW)
            self.lst_links.Append(MSG_LOADING_ROW)
        else:
            if headings:
                for i, item in enumerate(headings, 1):
                    self.lst_heads.Append(
                        f"{i}. [H{item.get('level') or 1}] {item.get('title') or ''}"
                    )
            else:
                self.lst_heads.Append(MSG_NO_HEAD)
            if links:
                for i, item in enumerate(links, 1):
                    dest = item.get("href") or ""
                    if item.get("kind") in ("http", "file"):
                        dest = item.get("target") or dest
                    self.lst_links.Append(f"{i}. {item.get('text') or ''} -> {dest}")
            else:
                self.lst_links.Append(MSG_NO_LINK)
        if self.lst_heads.GetCount():
            self.lst_heads.SetSelection(0)
        if self.lst_links.GetCount():
            self.lst_links.SetSelection(0)

    def _render(self, page: dict):
        title = page.get("title") or "Pagina"
        self.SetTitle(f"Lettore pagina — {title}")
        message = page.get("message") or MSG_READY.format(
            title=title,
            heads=len(page.get("headings") or []),
            links=len(page.get("links") or []),
        )
        point = (page.get("place_title") or "").strip()
        if point:
            message = MSG_POINT.format(title=point) + " " + message
        message = message + " " + self._step_sentence()
        self._set_status(message)
        self.lbl_address.SetLabel(page.get("address") or page.get("base") or "")
        self._fill_lists(page.get("headings") or [], page.get("links") or [])
        self.txt.SetValue(page.get("body") or MSG_NO_TEXT)
        self._set_nav_enabled()
        marker = page.get("place_marker") or ""
        if marker:
            self._select_marker(marker, page.get("place_occ") or 1)
            self._jump_marker(
                marker, point, announce=False, occ=page.get("place_occ") or 1
            )
        elif page.get("headings"):
            self.lst_heads.SetFocus()
        else:
            self.txt.SetFocus()
        self._say(message)

    def _selected(self, ctrl, items, empty_msg):
        if not items:
            self._say(empty_msg)
            return None
        sel = ctrl.GetSelection()
        if sel == wx.NOT_FOUND or sel < 0 or sel >= len(items):
            return None
        return items[sel]

    def on_heading(self, event=None):
        label = self.lst_heads.GetStringSelection() or ""
        if label in (MSG_LOADING_ROW, MSG_NO_HEAD):
            self._say(label)
            return
        page = self.current_page()
        item = self._selected(self.lst_heads, page.get("headings") or [], MSG_NO_HEAD)
        if not item:
            return
        self._push_place(
            item.get("marker") or "",
            item.get("title") or "",
            item.get("occ") or 1,
        )

    def _select_marker(self, marker: str, occ: int = 1):
        page = self.current_page()
        seen = 0
        for i, head in enumerate(page.get("headings") or []):
            if (head.get("marker") or "") != marker:
                continue
            seen += 1
            if seen == max(1, int(occ or 1)) and i < self.lst_heads.GetCount():
                self.lst_heads.SetSelection(i)
                return

    def _push_place(self, marker: str, title: str, occ: int = 1):
        page = self.current_page()
        occ = max(1, int(occ or 1))
        if not page:
            self._jump_marker(marker, title, occ=occ)
            return
        same_point = (page.get("place_marker") or "") == (marker or "") and int(
            page.get("place_occ") or 1
        ) == occ
        if same_point:
            self._jump_marker(marker, title, occ=occ)
            return
        if self.index < len(self.history) - 1:
            self.history = self.history[: self.index + 1]
        new = dict(page)
        new["place_marker"] = marker
        new["place_title"] = title
        new["place_occ"] = occ
        self.history.append(new)
        self.index = len(self.history) - 1
        self._render(new)

    def _jump_marker(self, marker: str, title: str, announce: bool = True, occ: int = 1):
        content = self.txt.GetValue() or ""
        pos = _nth_find(content, marker, occ) if marker else -1
        if pos < 0 and title:
            pos = content.find(title)
            marker = title
        if pos < 0:
            self._set_status(MSG_ANCHOR_MISS)
            self._say(MSG_ANCHOR_MISS)
            return
        start = text_pos_to_ctrl(content, pos)
        end = text_pos_to_ctrl(content, pos + len(marker or title))
        self.txt.SetFocus()
        self.txt.SetInsertionPoint(start)
        try:
            self.txt.ShowPosition(start)
            self.txt.SetSelection(start, end)
        except Exception:
            pass
        if announce:
            self._say(MSG_HEADING.format(title=title or marker))

    def on_link(self, event=None):
        label = self.lst_links.GetStringSelection() or ""
        if label in (MSG_LOADING_ROW, MSG_NO_LINK):
            self._say(label)
            return
        page = self.current_page()
        item = self._selected(self.lst_links, page.get("links") or [], MSG_NO_LINK)
        if not item:
            return
        self._activate_link(item)

    def go_back(self):
        if self.index <= 0:
            self._set_status(MSG_BACK_NONE)
            self._say(MSG_BACK_NONE)
            return
        self.index -= 1
        self._render(self.history[self.index])

    def go_forward(self):
        if self.index < 0 or self.index >= len(self.history) - 1:
            self._set_status(MSG_FWD_NONE)
            self._say(MSG_FWD_NONE)
            return
        self.index += 1
        self._render(self.history[self.index])

    def reload_page(self):
        page = self.current_page()
        source = page.get("source") or ""
        if not source:
            self._say(MSG_EMPTY)
            return
        self.load(source, push=False, page_url=page.get("link_base") or "")

    def _remember_list(self, which: str, event):
        self._last_list = which
        event.Skip()

    def _item_at(self, ctrl, items):
        if not items:
            return None
        sel = ctrl.GetSelection()
        if sel == wx.NOT_FOUND or sel < 0 or sel >= len(items):
            return None
        label = ctrl.GetStringSelection() or ""
        if label in (MSG_LOADING_ROW, MSG_NO_HEAD, MSG_NO_LINK):
            return None
        return items[sel]

    def _url_on_caret_line(self) -> str:
        content = self.txt.GetValue() or ""
        if not content:
            return ""
        py = ctrl_pos_to_text(content, self.txt.GetInsertionPoint())
        py = min(max(py, 0), len(content))
        start = content.rfind("\n", 0, py) + 1
        end = content.find("\n", py)
        if end < 0:
            end = len(content)
        line = content[start:end]
        found = re.findall(r"https?://[^\s<>\"']+", line)
        if found:
            return found[0].rstrip(".,);")
        hashes = re.findall(r"#[A-Za-z0-9_-]+", line)
        if len(hashes) == 1:
            return hashes[0]
        return ""

    def _select_link_near_caret(self):
        token = self._url_on_caret_line()
        if not token:
            return
        links = self.current_page().get("links") or []
        for i, item in enumerate(links):
            target = (item.get("target") or "").rstrip("/")
            href = item.get("href") or ""
            frag = "#" + (item.get("fragment") or "")
            if token.rstrip("/") in (target, href, (item.get("target") or "")) or (
                token.startswith("#") and token == frag
            ):
                if i < self.lst_links.GetCount():
                    self.lst_links.SetSelection(i)
                return

    def _on_text_kill_focus(self, event):
        event.Skip()
        wx.CallAfter(self._sync_link_if_list_focused)

    def _sync_link_if_list_focused(self):
        if not self._alive:
            return
        if self.FindFocus() is self.lst_links:
            self._select_link_near_caret()

    def _activate_link(self, item: dict):
        if not item:
            return
        kind = item.get("kind") or ""
        page = self.current_page()
        if kind == "anchor":
            fragment = item.get("fragment") or ""
            anchors = page.get("anchors") or {}
            marker = anchors.get(fragment) or ""
            if marker:
                self._push_place(marker, item.get("text") or fragment)
                return
            for head in page.get("headings") or []:
                if (head.get("anchor") or "") == fragment:
                    self._push_place(
                        head.get("marker") or "",
                        head.get("title") or item.get("text") or fragment,
                        head.get("occ") or 1,
                    )
                    return
            self._set_status(MSG_ANCHOR_MISS)
            self._say(MSG_ANCHOR_MISS)
            return
        if kind == "blocked":
            self._set_status(MSG_FILE_FROM_WEB)
            self._say(MSG_FILE_FROM_WEB)
            return
        if kind == "mailto":
            try:
                import webbrowser

                webbrowser.open(item.get("target") or "")
                sentence = f"Apro l'indirizzo di posta: {item.get('text') or item.get('href')}"
                self._set_status(sentence)
                self._say(sentence)
            except Exception:
                self._set_status(MSG_NOT_PAGE.format(href=item.get("href") or ""))
                self._say(MSG_NOT_PAGE.format(href=item.get("href") or ""))
            return
        if kind in ("http", "file"):
            target = item.get("target") or ""
            if kind == "file":
                path = file_url_to_path(target)
                if not path.lower().endswith((".html", ".htm", ".xhtml")):
                    self._set_status(MSG_NOT_PAGE.format(href=item.get("href") or target))
                    self._say(MSG_NOT_PAGE.format(href=item.get("href") or target))
                    return
                target = path
            self.load(target, push=True)
            return
        self._set_status(MSG_NOT_PAGE.format(href=item.get("href") or ""))
        self._say(MSG_NOT_PAGE.format(href=item.get("href") or ""))

    def _follow_text_url(self, url: str):
        page = self.current_page()
        base = (
            page.get("base")
            or page.get("link_base")
            or page.get("address")
            or page.get("source")
            or ""
        )
        info = classify_href(base, url)
        info["text"] = url
        self._activate_link(info)

    def on_text_url(self, event):
        mouse = event.GetMouseEvent()
        url = event.GetString() or ""
        if url and mouse is not None and mouse.LeftUp():
            self._follow_text_url(url)
            return
        event.Skip()

    def _link_external(self, item: dict, base: str) -> tuple[str, str]:
        kind = item.get("kind") or ""
        title = item.get("text") or item.get("href") or ""
        if kind == "anchor" and item.get("fragment"):
            return (
                _with_fragment(base, item.get("fragment") or ""),
                MSG_EXTERNAL_POINT.format(title=title),
            )
        if kind in ("http", "file") and item.get("target"):
            return item.get("target") or "", MSG_EXTERNAL_LINK.format(title=title)
        return "", ""

    def _selected_link_address(self, base: str) -> tuple[str, str]:
        item = self._item_at(self.lst_links, self.current_page().get("links") or [])
        if not item:
            return "", ""
        return self._link_external(item, base)

    def _opened_heading_address(self, page: dict, base: str) -> tuple[str, str]:
        marker = page.get("place_marker") or ""
        if not marker:
            return "", ""
        occ = int(page.get("place_occ") or 1)
        seen = 0
        for head in page.get("headings") or []:
            if (head.get("marker") or "") != marker:
                continue
            seen += 1
            if seen == occ:
                return heading_open_address(head, base)
        return "", ""

    def _windows_target(self) -> tuple[str, str]:
        page = self.current_page()
        base = (page.get("base") or page.get("address") or page.get("source") or "").strip()
        focus = self.FindFocus()
        # Il pulsante prende il fuoco: vale l'elenco che si stava usando.
        if focus is self.lst_links or (
            focus not in (self.lst_heads, self.txt) and self._last_list == "links"
        ):
            found = self._selected_link_address(base)
            if found[0]:
                return found
        if focus is self.lst_heads:
            opened = self._opened_heading_address(page, base)
            if opened[0]:
                return opened
            return "", MSG_HEAD_FIRST
        if focus is self.txt:
            try:
                token = self._url_on_caret_line()
            except Exception:
                token = ""
            if token:
                info = classify_href(base, token)
                info["text"] = token
                found = self._link_external(info, base)
                if found[0]:
                    return found
        opened = self._opened_heading_address(page, base)
        if opened[0] and self._last_list != "links":
            return opened
        if self._last_list == "heads":
            return "", MSG_HEAD_FIRST
        found = self._selected_link_address(base)
        if found[0]:
            return found
        return base, MSG_EXTERNAL_TOP

    def open_external(self):
        address, sentence = self._windows_target()
        if not address:
            self._set_status(sentence or MSG_EXTERNAL_FAIL)
            self._say(sentence or MSG_EXTERNAL_FAIL)
            return
        if open_in_windows_browser(address):
            self._set_status(sentence)
            self._say(sentence)
            return
        self._set_status(MSG_EXTERNAL_FAIL)
        self._say(MSG_EXTERNAL_FAIL)

    def on_char_hook(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self.Close()
            return
        if event.AltDown() and key == wx.WXK_LEFT:
            self.go_back()
            return
        if event.AltDown() and key == wx.WXK_RIGHT:
            self.go_forward()
            return
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            focus = self.FindFocus()
            if focus is self.lst_heads:
                self.on_heading()
                return
            if focus is self.lst_links:
                self.on_link()
                return
            if focus is self.txt:
                url = self._url_on_caret_line()
                if url:
                    self._follow_text_url(url)
                    return
        event.Skip()


def open_browser(speak, source, keep=None, page_url: str = ""):
    """Apre il lettore e, se serve, lo tiene in una lista contro il garbage collector."""
    frame = HtmlBrowserFrame(speak, source, page_url=page_url)
    if keep is not None:
        keep.append(frame)

        def _cleanup(evt, held=frame):
            try:
                if held in keep:
                    keep.remove(held)
            except Exception:
                pass
            evt.Skip()

        frame.Bind(wx.EVT_CLOSE, _cleanup)
    return frame
