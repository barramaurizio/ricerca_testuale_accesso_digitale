# -*- coding: utf-8 -*-
"""Smoke 1.8.0 — contesto chat Gemini, senza rete.

Uso (dalla root del repo):
  python tools/_smoke_chat_context.py
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_chat  # noqa: E402


def main() -> int:
    ko = 0

    def check(cond, msg):
        nonlocal ko
        print(("OK" if cond else "KO"), msg)
        if not cond:
            ko += 1

    when = datetime.datetime(2026, 10, 21, 8, 43)
    check(
        rtad_chat.format_now(when) == "mercoledì 21 ottobre 2026, ore 08:43",
        "data di oggi in italiano",
    )

    full = ("A" * rtad_chat.CONTEXT_CHAR_CAP) + "\nCapitolo lontano\n" + ("B" * 40)
    session = {
        "kind": "document",
        "path": r"C:\prova\manuale.pdf",
        "title": "manuale.pdf",
        "turns": [{"role": "user", "text": "Ciao"}, {"role": "model", "text": "Eccomi."}],
        "context_text": "INIZIO DEL FILE",
        "context_note": "",
        "full_text": full,
        "outline": [{"title": "Capitolo lontano", "level": 1, "page": 3}],
        "image_b64": "",
        "image_mime": "",
        "image_missing": False,
    }
    extra = rtad_chat.focus_slice(session, "Che cosa dice a pagina 3?")
    check("Capitolo lontano" in extra, "estratto oltre il pacchetto iniziale")
    check("AAAA" not in extra, "l'estratto non ripete l'inizio")

    payload = rtad_chat.build_payload(session, "Che cosa dice a pagina 3?", True, when)
    blob = json.dumps(payload)
    check("temperature" not in blob, "niente temperature")
    check(payload["tools"] == [{"google_search": {}}], "web acceso nel payload")
    sys_txt = payload["systemInstruction"]["parts"][0]["text"]
    check("mercoledì 21 ottobre 2026" in sys_txt, "data nel system instruction")
    check("INIZIO DEL FILE" in sys_txt, "materiale nel system instruction")
    check("Nel file:" in sys_txt and "Approfondimento:" in sys_txt, "due piani")
    user_text = payload["contents"][-1]["parts"][0]["text"]
    check("Estratto aggiuntivo" in user_text, "estratto allegato alla domanda")
    check(payload["contents"][0]["parts"][0]["text"] == "Ciao", "cronologia visibile senza il pacchetto")
    check("inline_data" not in blob, "il documento non allega un'immagine")

    off = rtad_chat.build_payload(session, "Riassumi", False, when)
    check("tools" not in off, "web spento: niente tool")

    image = {
        "kind": "image",
        "path": r"C:\prova\foto.jpg",
        "title": "foto.jpg",
        "turns": [],
        "context_text": "Analisi già svolta",
        "context_note": "",
        "full_text": "Analisi già svolta",
        "outline": [],
        "image_b64": "QUJD",
        "image_mime": "image/jpeg",
        "image_missing": False,
    }
    img_payload = rtad_chat.build_payload(image, "Chi c'è?", False, when)
    parts = img_payload["contents"][-1]["parts"]
    check(any("inline_data" in p for p in parts), "l'immagine è allegata allo scambio")
    check(parts[-1]["inline_data"]["data"] == "QUJD", "byte immagine nel turno corrente")

    rtad_chat.append_exchange(image, "Chi c'è?", "Una persona.", "gemini-test")
    text = rtad_chat.transcript(image)
    check("Tu:" in text and "Gemini:" in text and "Una persona." in text, "testo piano")
    check("api" not in text.lower() or "chiave" not in text.lower(), "il testo non parla di chiavi")

    with tempfile.TemporaryDirectory() as tmp:
        image["path"] = os.path.join(tmp, "foto.jpg")
        image["image_b64"] = "SEGRETO_NON_SALVARE"
        dest = rtad_chat.save_current(tmp, image)
        raw = open(dest, encoding="utf-8").read()
        check("SEGRETO_NON_SALVARE" not in raw, "su disco non finiscono i byte dell'immagine")
        check("api_key" not in raw and "AIza" not in raw, "su disco non finisce una chiave")
        data = json.loads(raw)
        check(data["turns"][-1]["text"] == "Una persona.", "turno salvato")
        loaded = rtad_chat.load_current(tmp, image["path"], prior_report="Analisi già svolta")
        check(loaded is not None and len(loaded["turns"]) == 2, "cronologia riletta")
        check(not loaded.get("image_b64"), "in rilettura senza file non si inventano byte")
        export = os.path.join(tmp, "foto.chat.txt")
        found = rtad_chat.find_export(tmp, export)
        check(found == dest, "il .chat.txt ritrova la conversazione salvata")
        listed = rtad_chat.list_all_saved(tmp)
        check(any("foto.jpg" in (row.get("label") or "") for row in listed), "elenco di tutte le conversazioni")

    check(len(rtad_chat.suggested_questions("image")) == 3, "domande pronte immagine")
    check(len(rtad_chat.suggested_questions("document")) == 3, "domande pronte documento")
    sample = (
        "Fonte: [NASA Voyager](https://science.nasa.gov/mission/voyager/).\n"
        "Fonti web:\n"
        "- nasa.gov: https://vertexaisearch.cloud.google.com/grounding-api-redirect/ABC\n"
        "- esa.int: https://www.esa.int/Euclid\n"
    )
    links = rtad_chat.extract_links(sample)
    urls = [item["url"] for item in links]
    check(
        "https://science.nasa.gov/mission/voyager/" in urls,
        "link nel testo della risposta",
    )
    check(any("grounding-api-redirect" in u for u in urls), "link di rinvio Google")
    check("https://www.esa.int/Euclid" in urls, "link breve nelle fonti")
    grounding = next(item for item in links if "grounding-api-redirect" in item["url"])
    check(
        rtad_chat.link_label(grounding) == "nasa.gov",
        "in elenco il rinvio Google si legge col nome del sito",
    )
    redacted = rtad_chat._safe_err("m", Exception("url?key=AIzaSECRET&x=1"))
    check("AIzaSECRET" not in redacted and "key=…" in redacted, "errore senza chiave")

    fd, media = tempfile.mkstemp(prefix="rtad_media_", suffix=".mp4")
    os.close(fd)
    side = media + ".rtad_src.json"
    try:
        with open(side, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "title": "Titolo del video",
                    "url": "https://example.com/clip",
                    "webpage_url": "https://example.com/clip",
                    "id": "abc",
                },
                handle,
            )
        with tempfile.TemporaryDirectory() as tmp:
            legacy = {
                "v": 1,
                "kind": "document",
                "path": media,
                "title": os.path.basename(media),
                "created": "2026-10-21T11:20:17",
                "updated": "2026-10-21T11:39:25",
                "turns": [
                    {"role": "user", "text": "Chi è?"},
                    {"role": "model", "text": "Nel file: un calciatore."},
                ],
            }
            os.makedirs(os.path.join(tmp, "chat"), exist_ok=True)
            old = os.path.join(tmp, "chat", rtad_chat._file_key(media) + ".json")
            with open(old, "w", encoding="utf-8") as handle:
                json.dump(legacy, handle)
            loaded = rtad_chat.load_current(tmp, media)
            check(loaded is not None, "chat da URL riletta")
            check(loaded.get("title") == "Titolo del video", "titolo vero, non il nome temporaneo")
            check(loaded.get("source_url") == "https://example.com/clip", "URL conservato")
            check("Temp" not in rtad_chat.transcript(loaded), "il testo salvato non cita la cartella temporanea")
            check(rtad_chat.has_saved(tmp, media), "la chat da URL risulta salvata")
            listed = rtad_chat.list_all_saved(tmp)
            check(
                any("Titolo del video" in (row.get("label") or "") for row in listed),
                "in elenco compare il titolo del video",
            )
            check(not os.path.isfile(old), "il file temporaneo della chat è stato sostituito")
    finally:
        for item in (media, side):
            try:
                os.remove(item)
            except Exception:
                pass

    notice = rtad_chat.format_hit_notice("Testo Email 1 marzo", "ciao   mondo")
    check(
        notice == "Punto della ricerca: Testo Email 1 marzo. Estratto: ciao mondo",
        "punto della ricerca",
    )
    check(rtad_chat.format_hit_notice("", "") == "", "senza punto, frase vuota")
    msg_key = rtad_chat.message_storage_key(r"C:\posta\Inbox", 4)
    check(msg_key and msg_key != rtad_chat.message_storage_key(r"C:\posta\Inbox", 5), "chiave per messaggio")
    check(
        rtad_chat.result_message_key(r"C:\posta\Inbox", "[MBOX]", 4, "Oggetto: Ciao", "") == msg_key,
        "la casella non è un'unica chat",
    )
    check(
        rtad_chat.result_message_key(r"C:\a.eml", "[EML]", 1, "corpo", "") == "",
        "un .eml resta sul file",
    )
    hit_session = rtad_chat.new_session(
        "document",
        "",
        hit_notice=notice,
        material_text="Oggetto: Ciao\n\ncorpo del messaggio",
        stable_key="hitkey123",
        title="Ciao",
    )
    check(hit_session["context_text"].startswith(notice), "il punto sta nel materiale")
    check("corpo del messaggio" in hit_session["context_text"], "il messaggio sta nel materiale")
    check(hit_session["stable_key"] == "hitkey123", "chiave salvata sulla sessione")
    tmp_hit = tempfile.mkdtemp()
    try:
        rtad_chat.append_exchange(hit_session, "Chi scrive?", "Un messaggio.", "gemini-test")
        rtad_chat.save_current(tmp_hit, hit_session)
        loaded_hit = rtad_chat.load_by_key(tmp_hit, "hitkey123")
        check(bool(loaded_hit), "il messaggio si riapre")
        check(
            loaded_hit and loaded_hit.get("hit_notice") == notice,
            "il punto resta nella cronologia",
        )
        check(
            loaded_hit and "corpo del messaggio" in (loaded_hit.get("context_text") or ""),
            "il testo del messaggio resta",
        )
        check(rtad_chat.has_saved_key(tmp_hit, "hitkey123"), "risulta una conversazione già aperta")
    finally:
        try:
            for name in os.listdir(os.path.join(tmp_hit, "chat")):
                os.remove(os.path.join(tmp_hit, "chat", name))
            os.rmdir(os.path.join(tmp_hit, "chat"))
            os.rmdir(tmp_hit)
        except Exception:
            pass

    print("PASS" if ko == 0 else f"FAIL {ko}")
    return 0 if ko == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
