# TikTok Downloader — online wala (v1)
# Paste a TikTok link -> download buttons (video / HD / watermark / audio).
# Data source: tikwm public API. Streams downloads through /dl so the
# browser saves the file instead of playing it.
import os
from urllib.parse import urlparse, quote

import requests
from flask import Flask, request, jsonify, render_template, Response, abort

app = Flask(__name__)

API = "https://www.tikwm.com/api/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0 Safari/537.36"}
ALLOWED_HOSTS = ("tiktokcdn", "muscdn", "byteoversea", "akamaized")


def looks_like_tiktok(url):
    try:
        h = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(x in h for x in ("tiktok.com", "tiktok"))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return "ok"


@app.route("/api/fetch", methods=["POST"])
def fetch():
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    if not url or not looks_like_tiktok(url):
        return jsonify(ok=False, error="That doesn't look like a TikTok "
                                       "link. Please paste a valid one."), 400
    try:
        r = requests.get(API, params={"url": url, "hd": 1},
                         headers=UA, timeout=25)
        data = r.json()
    except Exception:
        return jsonify(ok=False, error="The service didn't respond. "
                                       "Please try again in a moment."), 502
    if data.get("code") != 0 or not data.get("data"):
        return jsonify(ok=False, error="Video not found — the link may be "
                                       "wrong or the video is private."), 404
    d = data["data"]
    author = d.get("author") or {}

    def mb(n):
        try:
            return round(int(n) / 1048576, 1)
        except Exception:
            return None

    dur = int(d.get("duration") or 0)
    out = {
        "ok": True,
        "id": d.get("id"),
        "title": d.get("title") or "TikTok video",
        "cover": d.get("cover"),
        "author": author.get("nickname") or "",
        "author_id": author.get("unique_id") or "",
        "duration": "%d:%02d" % (dur // 60, dur % 60),
        "links": {},
    }
    vid = str(d.get("id") or "video")
    for key, src, label, size in (
        ("nowm", d.get("play"), "Video — No Watermark", d.get("size")),
        ("hd", d.get("hdplay"), "Video — HD", d.get("hd_size")),
        ("wm", d.get("wmplay"), "Video — With Watermark", d.get("wm_size")),
        ("mp3", d.get("music"), "Audio — MP3", None),
    ):
        if src:
            ext = "mp3" if key == "mp3" else "mp4"
            name = "tiktok-%s-%s.%s" % (vid, key, ext)
            out["links"][key] = {
                "label": label,
                "size_mb": mb(size),
                "href": "/dl?u=%s&n=%s" % (quote(src, safe=""), name),
            }
    if not out["links"]:
        return jsonify(ok=False, error="No download links were found "
                                       "for this video."), 404
    return jsonify(out)


@app.route("/dl")
def dl():
    u = request.args.get("u") or ""
    n = request.args.get("n") or "tiktok-video.mp4"
    p = urlparse(u)
    if p.scheme != "https" or not any(h in p.netloc for h in ALLOWED_HOSTS):
        abort(400)
    try:
        r = requests.get(u, headers=UA, stream=True, timeout=30)
    except Exception:
        abort(502)
    if r.status_code != 200:
        abort(502)
    headers = {
        "Content-Disposition": 'attachment; filename="%s"' % n,
        "Content-Type": r.headers.get("Content-Type", "application/octet-stream"),
    }
    if r.headers.get("Content-Length"):
        headers["Content-Length"] = r.headers["Content-Length"]
    return Response(r.iter_content(chunk_size=262144), headers=headers)


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("SERVER_PORT") or 5005)
    app.run(host="0.0.0.0", port=port)
