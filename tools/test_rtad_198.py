# -*- coding: utf-8 -*-
"""Prove della 1.9.8: login del browser e audio RaiPlay Sound."""
import os
import struct
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Standalone"))

import rtad_media as m  # noqa: E402


def _box(typ: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + typ + payload


def _audio_mp4() -> bytes:
    # hdlr: version+flags, pre_defined, handler soun
    hdlr = _box(b"hdlr", b"\x00" * 8 + b"soun" + b"\x00" * 8)
    moov = _box(b"moov", _box(b"trak", _box(b"mdia", _box(b"minf", hdlr))))
    ftyp = _box(b"ftyp", b"isom" + b"\x00\x00\x00\x00" + b"isom")
    return ftyp + moov


def _video_mp4() -> bytes:
    hdlr = _box(b"hdlr", b"\x00" * 8 + b"vide" + b"\x00" * 8)
    moov = _box(b"moov", _box(b"trak", _box(b"mdia", _box(b"minf", hdlr))))
    ftyp = _box(b"ftyp", b"isom" + b"\x00\x00\x00\x00" + b"isom")
    return ftyp + moov


def test_hosts_and_drm():
    assert m.is_raiplay_sound_url("https://www.raiplaysound.it/audio/gr1")
    assert not m.is_raiplay_sound_url("https://www.raiplay.it/video/x")
    assert m.is_page_media_url("https://www.raiplaysound.it/audio/gr1")
    assert m.url_is_drm_service("https://www.netflix.com/watch/1")
    assert m.url_is_drm_service("https://www.primevideo.com/detail/1")
    assert m.url_is_drm_service("https://dazn.com/en/home")
    assert not m.url_is_drm_service("https://www.raiplaysound.it/audio/gr1")
    assert not m.url_is_drm_service("https://www.youtube.com/watch?v=abc")
    closed = m.materialize_media_from_url(
        "https://www.netflix.com/watch/1", browser="chrome"
    )
    assert closed["ok"] is False
    assert closed["needs_browser_login"] is False
    assert "DRM" in closed["error"]
    assert "non scaricabile" in closed["error"]


def test_login_versus_drm_text():
    denied = m._access_denied_message()
    assert m.error_needs_browser_login(denied)
    assert not m.error_is_drm(denied)
    assert m.error_is_drm("This video is DRM protected")
    assert m.error_is_drm("Widevine")
    assert not m.error_needs_browser_login("Widevine protected")
    assert m.error_needs_browser_login("Sign in to confirm your age")
    assert m._safe_browser_id("chrome") == "chrome"
    assert m._safe_browser_id("not-a-browser") == ""
    assert m._safe_browser_id("chrome;rm") == ""


def test_ytdlp_argv_keeps_sound_and_cookies():
    argv = m._ytdlp_argv(
        "https://www.youtube.com/watch?v=abc", "out", "meta.txt", ""
    )
    assert "--cookies-from-browser" not in argv
    assert "--merge-output-format" in argv
    sound = m._ytdlp_argv(
        "https://www.raiplaysound.it/audio/gr1", "out", "meta.txt", "chrome"
    )
    assert sound[sound.index("--cookies-from-browser") + 1] == "chrome"
    assert "--merge-output-format" not in sound
    assert "bestaudio/best" in sound
    poisoned = m._ytdlp_argv(
        "https://www.raiplaysound.it/audio/gr1", "out", "meta.txt", "chrome&calc"
    )
    assert "--cookies-from-browser" not in poisoned
    referred = m._ytdlp_argv(
        "https://cdn.example/a.m3u8",
        "out",
        "meta.txt",
        "edge",
        referer="https://www.juventus.com/it/video/x",
    )
    assert referred[referred.index("--referer") + 1].startswith("https://www.juventus.com/")
    assert "--cookies-from-browser" in referred


def test_audio_mp4_stays_audio():
    raw = _audio_mp4()
    video = _video_mp4()
    with tempfile.TemporaryDirectory() as folder:
        audio_path = os.path.join(folder, "gr1.mp4")
        video_path = os.path.join(folder, "mute.mp4")
        with open(audio_path, "wb") as handle:
            handle.write(raw)
        with open(video_path, "wb") as handle:
            handle.write(video)
        assert m.file_is_audio_only(audio_path)
        assert not m.file_is_audio_only(video_path)
        picked = m._pick_ytdlp_outputs(folder, page_url="https://www.raiplaysound.it/audio/gr1")
        # Due file: prende il più grande. Sono simili: verifica entrambi i ruoli a parte.
        assert m._media_role_hint(audio_path) == "audio"
        assert m._media_role_hint(video_path) == "video"
        assert "È l'audio" in m.list_sentence_for_download("GR1", "audio")
        assert "formato consegnato" in m.list_sentence_for_download("GR1", "audio")
        plain = m.list_sentence_for_download("Clip", "video")
        assert plain.startswith("Il file è in elenco")
        only = os.path.join(folder, "solo")
        os.makedirs(only)
        sole = os.path.join(only, "giornale.mp4")
        with open(sole, "wb") as handle:
            handle.write(raw)
        one = m._pick_ytdlp_outputs(
            only, page_url="https://www.raiplaysound.it/audio/gr1"
        )
        assert one["ok"] is True
        assert one["content_kind"] == "audio"
        assert one["path"].endswith("giornale.mp4")
        mute_dir = os.path.join(folder, "mute")
        os.makedirs(mute_dir)
        mute = os.path.join(mute_dir, "solo_video.mp4")
        with open(mute, "wb") as handle:
            handle.write(video)
        rejected = m._pick_ytdlp_outputs(
            mute_dir, page_url="https://www.youtube.com/watch?v=abc"
        )
        assert rejected["ok"] is False
        assert "senza audio" in rejected["error"]


def test_denied_playlist_is_retried_with_login():
    page = "https://www.juventus.com/it/video/uel-spalletti"
    found = {
        "needs_browser_login": True,
        "media_url": "https://cdn.example/playlist.m3u8",
        "error": "Accesso negato",
    }
    target, referer = m.page_download_target(page, found, "chrome")
    assert target.endswith("playlist.m3u8")
    assert referer == page
    bare, no_ref = m.page_download_target(page, found, "")
    assert bare == page
    assert no_ref == ""
    public, pub_ref = m.page_download_target(
        page, {"media_url": "https://cdn.example/ok.m3u8"}, "chrome"
    )
    assert public.endswith("ok.m3u8")
    assert pub_ref == ""
    assert m.error_is_cookie_read_failure(
        "ERROR: Could not copy Chrome cookie database"
    )
    assert not m.error_is_cookie_read_failure("Accesso negato")
    unread = m.cookie_unread_message("edge", still_open=True)
    assert "Microsoft Edge" in unread
    assert "lascialo chiuso" in unread
    assert "vassoio" in unread
    assert "riaperta" in unread
    closed = m.cookie_unread_message("edge", still_open=False)
    assert "anche a browser chiuso" in closed
    assert "Firefox" in closed
    assert m.browser_locks_cookie_file("edge")
    assert not m.browser_locks_cookie_file("firefox")


def test_raiplay_sheet_does_not_blame_the_size_cap():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "rtad_media_gr1.mp3")
        with open(path, "wb") as handle:
            handle.write(b"ID3")
        m._write_media_source_sidecar(
            path,
            {
                "url": "https://www.raiplaysound.it/audio/gr1",
                "webpage_url": "https://www.raiplaysound.it/audio/gr1",
                "title": "GR1",
                "content_kind": "audio",
                "via": "yt-dlp",
            },
        )
        sheet = m.format_media_tech_sheet(
            {
                "ok": True,
                "kind": "audio",
                "file_name": "rtad_media_gr1.mp3",
                "path": path,
                "source_path": path,
                "format_label": "MP3",
            }
        )
        assert "Tipo: Audio" in sheet
        assert "troppo pesante" not in sheet
        tube = os.path.join(folder, "rtad_media_clip.m4a")
        with open(tube, "wb") as handle:
            handle.write(b"x")
        m._write_media_source_sidecar(
            tube,
            {
                "url": "https://www.youtube.com/watch?v=abc",
                "webpage_url": "https://www.youtube.com/watch?v=abc",
                "via": "yt-dlp",
            },
        )
        heavy = m.format_media_tech_sheet(
            {
                "ok": True,
                "kind": "audio",
                "file_name": "rtad_media_clip.m4a",
                "path": tube,
                "source_path": tube,
                "format_label": "M4A",
            }
        )
        assert "troppo pesante" in heavy


def test_consent_sentences():
    none = m.browser_login_sentence([])
    assert "Annulla" in none
    assert "Nessun browser" in none
    one = m.browser_login_sentence([{"id": "edge", "label": "Microsoft Edge"}])
    assert "Microsoft Edge" in one
    assert "Autorizza" in one
    assert "non si decifra" in one
    assert "Firefox" in one
    dpapi = (
        "ERROR: Failed to decrypt with DPAPI. See "
        "https://github.com/yt-dlp/yt-dlp/issues/10927 for more info"
    )
    assert m.error_is_dpapi_cookie_failure(dpapi)
    assert not m.error_is_cookie_read_failure(dpapi)
    said = m.dpapi_cookie_message("edge")
    assert "non si decifrano" in said
    assert "Task Manager" in said
    assert "Firefox" in said
    assert "2.00 GB" not in said
    forbidden = (
        "ERROR: [generic] index: Unable to download webpage: "
        "HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>)"
    )
    assert m.error_is_http_forbidden(forbidden)
    refused = m.playlist_refused_message("firefox")
    assert "Firefox" in refused
    assert "Accesso negato" in refused
    assert "non c'entra" in refused
    assert "2.00 GB" not in refused
    firefox = m.browser_login_sentence([{"id": "firefox", "label": "Firefox"}])
    assert "già aperto" in firefox
    assert "Scarica" in m.browser_close_sentence("edge")
    many = m.browser_login_sentence(
        [{"id": "chrome", "label": "Google Chrome"}, {"id": "edge", "label": "Microsoft Edge"}]
    )
    assert "scelgono il browser" in many
    assert "DRM" in m.DRM_CLOSED_MESSAGE


if __name__ == "__main__":
    test_hosts_and_drm()
    test_login_versus_drm_text()
    test_ytdlp_argv_keeps_sound_and_cookies()
    test_audio_mp4_stays_audio()
    test_denied_playlist_is_retried_with_login()
    test_raiplay_sheet_does_not_blame_the_size_cap()
    test_consent_sentences()
    print("test_rtad_198 OK")
