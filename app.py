"""
Tiny Instagram reel download API (wraps yt-dlp).

Endpoints
  GET /                      -> health check
  GET /download?url=<reel>   -> JSON with a direct video link (+ title, thumbnail, etc.)
  GET /file?url=<reel>       -> the .mp4 file itself

Auth: send your API key as header  X-API-Key: <key>   (or ?key=<key>)
"""

import glob
import hmac
import os
import re
import shutil
import tempfile

import yt_dlp
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse

API_KEY = os.environ.get("API_KEY", "").strip()

IG_URL = re.compile(
    r"^https?://(www\.)?instagram\.com/(reel|reels|p|tv)/[A-Za-z0-9_-]+/?(\?.*)?$"
)


# Optional Instagram login cookies (only needed if Instagram starts saying "login required").
# Either a Render "Secret File" named cookies.txt, or an IG_COOKIES env var with the file contents.
def _load_cookies():
    dest = os.path.join(tempfile.gettempdir(), "ig_cookies.txt")
    secret = "/etc/secrets/cookies.txt"
    if os.path.exists(secret):
        shutil.copy(secret, dest)  # copy: yt-dlp needs a writable file
        return dest
    raw = os.environ.get("IG_COOKIES", "").strip()
    if raw:
        with open(dest, "w") as f:
            f.write(raw + "\n")
        return dest
    return None


COOKIES = _load_cookies()

app = FastAPI(title="Reel Downloader API", docs_url="/docs")


def _check(url: str, header_key: str | None, query_key: str | None):
    if API_KEY:
        given = header_key or query_key or ""
        if not hmac.compare_digest(given, API_KEY):
            raise HTTPException(401, "Missing or wrong API key")
    if not IG_URL.match(url.strip()):
        raise HTTPException(400, "Please send an Instagram reel/post URL")


def _opts(**extra):
    o = {"quiet": True, "no_warnings": True, "noplaylist": True}
    if COOKIES:
        o["cookiefile"] = COOKIES
    o.update(extra)
    return o


def _fail(e: Exception):
    msg = str(e)
    hint = None
    if "login" in msg.lower() or "rate" in msg.lower() or "cookies" in msg.lower():
        hint = "Instagram wants a login. Add a cookies.txt secret file (see README)."
    raise HTTPException(502, {"error": msg[-500:], "hint": hint})


@app.get("/")
def health():
    return {"ok": True, "cookies_loaded": bool(COOKIES)}


@app.get("/download")
def download_link(
    url: str = Query(..., description="Instagram reel URL"),
    key: str | None = Query(None),
    x_api_key: str | None = Header(None),
):
    _check(url, x_api_key, key)
    try:
        with yt_dlp.YoutubeDL(_opts(format="b[ext=mp4]/b")) as ydl:
            info = ydl.extract_info(url.strip(), download=False)
    except Exception as e:
        _fail(e)

    video_url = info.get("url")
    if not video_url and info.get("requested_formats"):
        video_url = info["requested_formats"][0].get("url")

    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "caption": info.get("description"),
        "uploader": info.get("uploader") or info.get("channel"),
        "duration": info.get("duration"),
        "width": info.get("width"),
        "height": info.get("height"),
        "thumbnail": info.get("thumbnail"),
        "ext": info.get("ext") or "mp4",
        "video_url": video_url,  # direct link; expires after a few hours
        "webpage_url": info.get("webpage_url") or url,
    }


@app.get("/file")
def download_file(
    background: BackgroundTasks,
    url: str = Query(..., description="Instagram reel URL"),
    key: str | None = Query(None),
    x_api_key: str | None = Header(None),
):
    _check(url, x_api_key, key)
    tmp = tempfile.mkdtemp(prefix="reel_")
    background.add_task(shutil.rmtree, tmp, ignore_errors=True)
    try:
        opts = _opts(
            format="b[ext=mp4]/bv*+ba/b",
            merge_output_format="mp4",
            outtmpl=os.path.join(tmp, "%(id)s.%(ext)s"),
        )
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url.strip(), download=True)
    except Exception as e:
        _fail(e)

    files = [f for f in glob.glob(os.path.join(tmp, "*")) if not f.endswith(".part")]
    if not files:
        raise HTTPException(502, "Download finished but no file was produced")
    path = max(files, key=os.path.getsize)
    name = f"{info.get('id', 'reel')}{os.path.splitext(path)[1] or '.mp4'}"
    return FileResponse(path, media_type="video/mp4", filename=name)
