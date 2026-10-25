# -*- coding: utf-8 -*-
"""Traduzione del testo già aperto, via Gemini, a pezzi.

L'originale non si sostituisce: la traduzione si aggiunge sotto.
Se c'è una trascrizione, si traduce quella e i timestamp restano.
Niente temperature, niente thinking_budget: solo maxOutputTokens.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

try:
    import rtad_ocr
except ImportError:
    rtad_ocr = None

# codice, etichetta in elenco, forma nella frase, nome per il modello
LANGUAGES = (
    ("it", "Italiano", "italiano", "Italian"),
    ("en", "Inglese", "inglese", "English"),
    ("fr", "Francese", "francese", "French"),
    ("de", "Tedesco", "tedesco", "German"),
    ("es", "Spagnolo", "spagnolo", "Spanish"),
    ("pt", "Portoghese", "portoghese", "Portuguese"),
    ("pl", "Polacco", "polacco", "Polish"),
    ("ro", "Rumeno", "rumeno", "Romanian"),
    ("nl", "Olandese", "olandese", "Dutch"),
    ("ru", "Russo", "russo", "Russian"),
    ("uk", "Ucraino", "ucraino", "Ukrainian"),
    ("ar", "Arabo", "arabo", "Arabic"),
    ("zh", "Cinese", "cinese", "Chinese"),
    ("ja", "Giapponese", "giapponese", "Japanese"),
    ("ko", "Coreano", "coreano", "Korean"),
    ("tr", "Turco", "turco", "Turkish"),
    ("el", "Greco", "greco", "Greek"),
    ("sv", "Svedese", "svedese", "Swedish"),
    ("cs", "Ceco", "ceco", "Czech"),
    ("hu", "Ungherese", "ungherese", "Hungarian"),
)

MSG_DONE = "Traduzione completa."
MSG_DONE_SHORT = "Traduzione completa, con un pezzo accorciato dal limite tecnico."
MSG_ABORT = "Traduzione interrotta."
MSG_EMPTY = "Niente da tradurre."
MSG_NO_TRANSCRIPT = "Non c'è una trascrizione da tradurre."
MSG_NO_KEY = "Per tradurre serve la chiave Gemini, da Strumenti."
MSG_UNAVAILABLE = "Traduzione non disponibile."

_CHUNK_CHARS = 1600
_MIN_SPLIT = 400
_TIMEOUT_SEC = 90
_MAX_OUTPUT_TOKENS = 8192
_TS_LINE_RE = re.compile(
    r"^\s*\[(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]"
)
_SECTION_RE = re.compile(r"^=== (.+?) ===\s*$", re.M)
_TRUNC_NOTE_RE = re.compile(
    r"\n*\(Nota:[^)\n]*accorciata dal limite tecnico[^)\n]*\)\s*$",
    re.I,
)


def language_by_code(code: str) -> tuple | None:
    wanted = (code or "").strip().lower()
    for item in LANGUAGES:
        if item[0] == wanted:
            return item
    return None


def language_labels() -> list:
    return [item[1] for item in LANGUAGES]


def language_codes() -> list:
    return [item[0] for item in LANGUAGES]


def msg_fail(err: str) -> str:
    raw = (err or "").strip() or "Gemini non ha risposto."
    return f"Traduzione non riuscita: {raw}"


def msg_progress(index: int, total: int) -> str:
    return f"Traduzione in corso, pezzo {int(index)} di {int(total)}."


def has_translation(text: str) -> bool:
    return "=== Traduzione" in (text or "")


def strip_translation(text: str) -> str:
    """Toglie una traduzione già aggiunta in fondo. L'originale resta."""
    raw = text or ""
    cut = raw.find("\n=== Traduzione")
    if cut < 0 and raw.startswith("=== Traduzione"):
        cut = 0
    if cut < 0:
        return raw
    return raw[:cut].rstrip()


def portion_to_translate(text: str) -> tuple:
    """(testo da mandare, 'transcript' oppure 'document').

    Se c'è una sezione Trascrizione con del parlato, si traduce quella.
    Il riassunto già in italiano resta dov'è e non si rimanda.
    """
    raw = strip_translation(text or "")
    matches = list(_SECTION_RE.finditer(raw))
    for i, match in enumerate(matches):
        title = (match.group(1) or "").strip().lower()
        if not title.startswith("trascrizione"):
            continue
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[start:end].strip()
        if not body or body.startswith("(Non disponibile"):
            return "", "transcript"
        return body, "transcript"
    return raw.strip(), "document"


def heading_for(code: str, kind: str) -> str:
    item = language_by_code(code) or LANGUAGES[0]
    forma = item[2]
    if kind == "transcript":
        return f"=== Traduzione della trascrizione in {forma} ==="
    return f"=== Traduzione in {forma} ==="


def assemble(original: str, translation: str, code: str, kind: str) -> str:
    base = strip_translation(original or "").rstrip()
    body = (translation or "").strip()
    if not body:
        return base
    head = heading_for(code, kind)
    return f"{base}\n\n{head}\n\n{body}\n"


def chunk_text(text: str, max_chars: int = _CHUNK_CHARS) -> list:
    """Pezzi che non spezzano una riga con timestamp."""
    raw = (text or "").strip()
    if not raw:
        return []
    limit = max(200, int(max_chars or _CHUNK_CHARS))
    lines = raw.splitlines()
    timed = sum(1 for line in lines if _TS_LINE_RE.match(line)) >= 2
    if timed:
        chunks = []
        buf = []
        size = 0
        for line in lines:
            add = len(line) + 1
            if buf and size + add > limit:
                chunks.append("\n".join(buf))
                buf = [line]
                size = add
            else:
                buf.append(line)
                size += add
        if buf:
            chunks.append("\n".join(buf))
        return [c for c in chunks if c.strip()]
    parts = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    chunks = []
    buf = ""
    for part in parts:
        if len(part) > limit:
            if buf:
                chunks.append(buf)
                buf = ""
            start = 0
            while start < len(part):
                chunks.append(part[start : start + limit])
                start += limit
            continue
        if buf and len(buf) + 2 + len(part) > limit:
            chunks.append(buf)
            buf = part
        else:
            buf = f"{buf}\n\n{part}" if buf else part
    if buf:
        chunks.append(buf)
    return chunks


def _split_piece(piece: str) -> tuple:
    lines = (piece or "").splitlines()
    if len(lines) >= 2:
        mid = max(1, len(lines) // 2)
        left = "\n".join(lines[:mid]).strip()
        right = "\n".join(lines[mid:]).strip()
        if left and right and left != piece:
            return left, right
    if len(piece) < _MIN_SPLIT * 2:
        return piece, ""
    mid = len(piece) // 2
    cut = piece.rfind("\n", 0, mid)
    if cut < 80:
        cut = piece.find("\n", mid)
    if cut <= 0 or cut >= len(piece) - 1:
        cut = mid
    left = piece[:cut].strip()
    right = piece[cut:].strip()
    if not left or not right:
        return piece, ""
    return left, right


def _looks_truncated(finish: str, text: str) -> bool:
    fin = (finish or "").upper()
    if fin in ("MAX_TOKENS", "LENGTH"):
        return True
    if _TRUNC_NOTE_RE.search(text or ""):
        return True
    return False


def _strip_trunc_note(text: str) -> str:
    return _TRUNC_NOTE_RE.sub("", text or "").rstrip()


def _prompt(language_en: str, forma: str, piece: str) -> str:
    return (
        f"Traduci il testo seguente in {forma} ({language_en}).\n"
        "Regole:\n"
        "- Restituisci solo la traduzione, senza introduzione e senza commenti.\n"
        "- Se una riga inizia con un timestamp tra parentesi quadre, "
        "come [00:43] o [01:02:03], lascialo identico e traduci solo le parole dopo.\n"
        "- Non unire e non spezzare le righe che hanno un timestamp.\n"
        "- Non riassumere. Traduci tutto il pezzo.\n"
        f"- Se il pezzo è già in {forma}, ripetilo com'è.\n\n"
        "Testo:\n"
        f"{piece}"
    )


def _readable(err: str) -> str:
    if rtad_ocr is not None and hasattr(rtad_ocr, "readable_gemini_error"):
        try:
            return rtad_ocr.readable_gemini_error(err)
        except Exception:
            logging.debug("Frase Gemini non tradotta", exc_info=True)
    raw = (err or "").strip()
    return raw or "Gemini non ha risposto."


def _text_from(data: dict) -> tuple:
    cands = (data or {}).get("candidates") or []
    if not cands:
        feedback = (data or {}).get("promptFeedback") or {}
        return "", "", f"nessuna risposta ({feedback or 'vuoto'})"
    parts = (((cands[0] or {}).get("content") or {}).get("parts")) or []
    texts = []
    for part in parts:
        if not isinstance(part, dict) or part.get("thought"):
            continue
        bit = (part.get("text") or "").strip()
        if bit:
            texts.append(bit)
    text = "\n".join(texts).strip()
    finish = str((cands[0] or {}).get("finishReason") or "")
    if not text:
        return "", finish, "testo vuoto"
    return text, finish, ""


def _post(model: str, key: str, payload: dict) -> tuple:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={urllib.parse.quote(key, safe='')}"
    )
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return True, json.loads(raw) if raw else {}, ""
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            pass
        err = f"HTTP {exc.code} ({model})"
        if err_body:
            err += f": {err_body}"
        err = re.sub(r"key=[^&\s\"']+", "key=…", err)
        return False, {"_http": exc.code}, err
    except Exception as exc:
        return False, {}, f"{model}: {exc}"


def _model_candidates(key: str) -> list:
    if rtad_ocr is not None and hasattr(rtad_ocr, "set_gemini_api_key"):
        try:
            rtad_ocr.set_gemini_api_key(key)
        except Exception:
            logging.debug("Chiave Gemini non impostata", exc_info=True)
    if rtad_ocr is not None and hasattr(rtad_ocr, "_gemini_model_candidates"):
        try:
            found = list(rtad_ocr._gemini_model_candidates(key) or [])
        except Exception:
            found = []
        if found:
            return found
    if rtad_ocr is not None:
        preferred = list(getattr(rtad_ocr, "_GEMINI_MODELS_PREFERRED", ()) or ())
        if preferred:
            return preferred
    return ["gemini-2.5-flash", "gemini-flash-latest"]


def _default_generate(piece: str, language_en: str, forma: str, api_key: str, should_abort=None) -> tuple:
    """(testo, finish, errore). errore 'aborted' se si interrompe."""
    if should_abort and should_abort():
        return "", "", "aborted"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": _prompt(language_en, forma, piece)}],
            }
        ],
        "generationConfig": {"maxOutputTokens": _MAX_OUTPUT_TOKENS},
    }
    last_err = ""
    for model in _model_candidates(api_key):
        if should_abort and should_abort():
            return "", "", "aborted"
        ok, data, err = _post(model, api_key, payload)
        if not ok:
            last_err = err or "errore Gemini"
            code = int((data or {}).get("_http") or 0)
            if code == 402:
                return "", "", _readable(last_err)
            if code in (404, 429, 503):
                logging.info("Traduzione %s HTTP %s, provo il modello successivo", model, code)
                continue
            if code == 400 and "not found" in (err or "").lower():
                continue
            return "", "", _readable(last_err)
        text, finish, parse_err = _text_from(data)
        if text or (finish or "").upper() in ("MAX_TOKENS", "LENGTH"):
            return text, finish, ""
        last_err = f"{model}: {parse_err or 'testo vuoto'}"
    return "", "", _readable(last_err or "Nessun modello ha risposto.")


def _translate_piece(piece, language_en, forma, api_key, generate, should_abort, depth=0) -> tuple:
    """(testo, errore, accorciato). errore 'aborted' se si interrompe."""
    if should_abort and should_abort():
        return "", "aborted", False
    text, finish, err = generate(piece, language_en, forma, api_key, should_abort)
    if err == "aborted":
        return "", "aborted", False
    if err:
        return "", err, False
    text = _strip_trunc_note(text)
    truncated = _looks_truncated(finish, text)
    if truncated and depth < 4 and len(piece) > _MIN_SPLIT:
        left, right = _split_piece(piece)
        if right:
            a, err_a, short_a = _translate_piece(
                left, language_en, forma, api_key, generate, should_abort, depth + 1
            )
            if err_a:
                return "", err_a, False
            b, err_b, short_b = _translate_piece(
                right, language_en, forma, api_key, generate, should_abort, depth + 1
            )
            if err_b:
                return "", err_b, False
            joined = (a.rstrip() + "\n" + b.lstrip()).strip()
            return joined, "", bool(short_a or short_b)
    if truncated:
        note = "(Questo pezzo è stato accorciato dal limite tecnico.)"
        body = text.strip()
        if note not in body:
            body = (body + "\n" + note).strip() if body else note
        return body, "", True
    return text.strip(), "", False


def _result(ok, text, status, *, error="", aborted=False, skipped=False, shortened=False) -> dict:
    return {
        "ok": bool(ok),
        "text": text or "",
        "status": status or "",
        "error": error or "",
        "aborted": bool(aborted),
        "skipped": bool(skipped),
        "shortened": bool(shortened),
    }


def translate_text(
    text: str,
    target_code: str,
    api_key: str,
    *,
    should_abort=None,
    on_progress=None,
    generate=None,
    max_chars: int = _CHUNK_CHARS,
) -> dict:
    """Traduce e restituisce il testo intero, originale più traduzione.

    on_progress(indice, totale, frase) parte prima di ogni pezzo.
    generate, se passato, è per le prove: (pezzo, lingua_en, forma, chiave, should_abort)
    e restituisce (testo, finish, errore).
    """
    original = text or ""
    base = strip_translation(original)
    item = language_by_code(target_code) or LANGUAGES[0]
    code, _label, forma, language_en = item
    portion, kind = portion_to_translate(base)
    if not (portion or "").strip():
        status = MSG_NO_TRANSCRIPT if kind == "transcript" else MSG_EMPTY
        return _result(False, base, status, error=status, skipped=True)
    if not (api_key or "").strip() and generate is None:
        status = MSG_NO_KEY
        shown = base.rstrip() + "\n\n" + status + "\n"
        return _result(False, shown, status, error=status)

    chunks = chunk_text(portion, max_chars=max_chars)
    if not chunks:
        status = MSG_EMPTY
        return _result(False, base, status, error=status, skipped=True)

    runner = generate or _default_generate
    done = []
    shortened = False
    total = len(chunks)
    for index, piece in enumerate(chunks, start=1):
        if should_abort and should_abort():
            partial = "\n".join(done).strip()
            shown = assemble(base, partial, code, kind) if partial else base
            return _result(False, shown, MSG_ABORT, aborted=True)
        if on_progress:
            try:
                on_progress(index, total, msg_progress(index, total))
            except Exception:
                logging.debug("Avanzamento traduzione non mostrato", exc_info=True)
        translated, err, short = _translate_piece(
            piece, language_en, forma, api_key, runner, should_abort
        )
        if err == "aborted":
            partial = "\n".join(done).strip()
            shown = assemble(base, partial, code, kind) if partial else base
            return _result(False, shown, MSG_ABORT, aborted=True)
        if not err and not (translated or "").strip():
            err = "Gemini non ha risposto."
        if err:
            status = msg_fail(err)
            partial = "\n".join(done).strip()
            block = (partial + "\n\n" + status).strip() if partial else status
            shown = assemble(base, block, code, kind)
            return _result(False, shown, status, error=err, shortened=shortened)
        if short:
            shortened = True
        if translated:
            done.append(translated)
    translation = "\n".join(done).strip()
    shown = assemble(base, translation, code, kind)
    status = MSG_DONE_SHORT if shortened else MSG_DONE
    return _result(True, shown, status, shortened=shortened)
