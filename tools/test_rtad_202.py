# -*- coding: utf-8 -*-
"""Prove della 2.0.2: nome dal post, e due copie che non si sovrascrivono."""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_chat
import rtad_ocr


def check(ok, label):
    if not ok:
        raise SystemExit("FALLITA: " + label)
    print("OK", label)


def main():
    piece = rtad_ocr.post_piece(
        "Il cielo sopra Roma stamattina era limpido e freddo"
    )
    check(piece.startswith("Il cielo"), "pezzo del post")
    check(not rtad_ocr.post_piece("Log in to X to see this post"), "invito escluso")
    check(not rtad_ocr.post_piece("Mario Rossi on X"), "solo il profilo")
    html = (
        '<html><meta property="og:description" '
        'content="Il cielo sopra Roma stamattina era limpido"></html>'
    )
    check(
        rtad_ocr.post_text_from_html(html).startswith("Il cielo"),
        "meta della pagina",
    )
    slug = ("titolo-lungo-della-pagina-" * 8).strip("-")
    name = rtad_ocr.suggest_image_save_stem(
        "https://example.com/articoli/" + slug, ""
    )
    check(len(name) > 70 and "cielo" not in name, "senza post resta l'indirizzo")
    named = rtad_ocr.suggest_image_save_stem(
        "https://x.com/rossi/status/1",
        "https://pbs.twimg.com/media/AbCdEf123.jpg",
        "Il cielo sopra Roma stamattina era limpido",
    )
    check(named.startswith("Il cielo"), "con il post il nome è il post")

    cache = tempfile.mkdtemp(prefix="rtad202_img_")
    rtad_ocr._image_post_dir = cache
    img = "https://pbs.twimg.com/media/HXAA6urXgAAEso3?format=jpg&name=900x900"
    page = "https://x.com/EASPORTSFC/status/2121196437698392308"
    post = "An unstoppable force in front of goal Nicolas Jackson is your October"
    rtad_ocr.remember_image_post(img, page, post)
    known = rtad_ocr.recall_image_post(
        "https://pbs.twimg.com/media/HXAA6urXgAAEso3?format=jpg&name=large"
    )
    check(known.get("post_text", "").startswith("An unstoppable"), "ricorda il post della foto")
    check(known.get("page_url") == page, "ricorda la pagina della foto")
    key_a = rtad_ocr.image_post_key(img)
    key_b = rtad_ocr.image_post_key(
        "https://pbs.twimg.com/media/HXAA6urXgAAEso3.jpg"
    )
    check(key_a == key_b and key_a.endswith("/HXAA6urXgAAEso3"), "stessa chiave per la foto")
    check(rtad_ocr.is_social_post_url(page), "indirizzo del post")
    check(rtad_ocr.is_likely_image_url(img), "indirizzo della foto")
    check(not rtad_ocr.is_social_post_url(img), "la foto non è il post")

    folder = tempfile.mkdtemp(prefix="rtad202_")
    other = os.path.join(folder, "a")
    shared = os.path.join(folder, "b")
    os.makedirs(os.path.join(other, "chat"), exist_ok=True)
    sample = os.path.join(other, "chat", "uno.json")
    with open(sample, "w", encoding="utf-8") as handle:
        json.dump({"title": "Prima", "turns": []}, handle)
    rtad_chat._copy_new_chats(os.path.join(other, "chat"), shared)
    check(os.path.isfile(os.path.join(shared, "uno.json")), "copia la chat che manca")
    with open(sample, "w", encoding="utf-8") as handle:
        json.dump({"title": "Diversa", "turns": [{"role": "user", "text": "x"}]}, handle)
    rtad_chat._pending.clear()
    rtad_chat._copy_new_chats(os.path.join(other, "chat"), shared)
    kept = [name for name in os.listdir(shared) if "altra-copia" in name]
    check(bool(kept), "tiene l'altra copia")
    check(rtad_chat.NOTICE_CHATS_KEPT in rtad_chat._pending, "frase delle due copie")

    base = os.path.join(folder, "prog")
    session = {
        "path": os.path.join(folder, "file.txt"),
        "kind": "document",
        "title": "Nota",
        "turns": [
            {"role": "user", "text": "ciao"},
            {"role": "model", "text": "salve"},
        ],
    }
    dest = rtad_chat.save_current(base, session)
    check(os.path.isfile(dest), "prima scrittura")
    with open(dest, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    data["turns"].append({"role": "user", "text": "dall'altra"})
    data["turns"].append({"role": "model", "text": "risposta"})
    with open(dest, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    session["turns"].append({"role": "user", "text": "da questa"})
    session["turns"].append({"role": "model", "text": "qui"})
    rtad_chat._notice = ""
    aside = rtad_chat.save_current(base, session)
    check(aside != dest, "non sovrascrive")
    check(rtad_chat.take_notice() == rtad_chat.NOTICE_BOTH_CHANGED, "frase a voce")
    with open(dest, "r", encoding="utf-8") as handle:
        still = json.load(handle)
    check(
        still["turns"][-1]["text"] == "risposta",
        "la copia già salvata resta",
    )
    print("202 OK")


if __name__ == "__main__":
    main()
