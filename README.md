# Reel Downloader API: setup guide

This is your own free API for downloading Instagram reels, built to be called from Make.
Setup takes about 10 minutes, and you only do it once.

---

## Step 1: Put the files on GitHub (about 2 min)

1. Go to **github.com** and sign in with your **personal** account.
2. Click **New repository**, name it `reel-api`, choose **Private**, then click **Create repository**.
3. Click **"uploading an existing file"** and drag in these 5 files:
   `app.py`, `requirements.txt`, `Dockerfile`, `start.sh`, `README.md`
4. Click **Commit changes**.

## Step 2: Deploy it on Render, free (about 5 min)

1. Go to **render.com** and sign up with GitHub.
2. Click **New +** and choose **Web Service**, then pick your `reel-api` repo.
3. Render detects the Dockerfile automatically. Set **Instance Type** to **Free**.
4. Under **Environment Variables**, add:
   - Key: `API_KEY`
   - Value: any long password you make up (e.g. `rohit-reels-8f3k2m9x`)
5. Click **Deploy**. When it says **Live**, copy your URL (it looks like `https://reel-api-xxxx.onrender.com`).

**Test it:** open `https://YOUR-URL.onrender.com/docs` in your browser. You can try the API there.

## Step 3: Call it from Make

Add an **HTTP > Make a request** module:

| Field | Value |
|---|---|
| URL | `https://YOUR-URL.onrender.com/download` |
| Method | GET |
| Query string | `url` = your reel link (e.g. `https://www.instagram.com/reel/DbexRNPAQk-/`) |
| Headers | `X-API-Key` = your API_KEY |
| Parse response | **Yes** |
| Timeout | **300** (the server can take about 1 min to wake up) |

You get back:

```json
{
  "id": "DbexRNPAQk-",
  "title": "...",
  "caption": "...",
  "uploader": "...",
  "duration": 15,
  "thumbnail": "https://...",
  "video_url": "https://...mp4"
}
```

**To get the actual video file:** add a second **HTTP > Get a file** module with `video_url` as the URL.
Its output is the .mp4, which you can map into Google Drive, Dropbox, Slack, and so on.

**Shortcut:** call `/file` instead of `/download` and the API sends back the .mp4 directly.
This uses Render's free bandwidth (5 GB/month, roughly a few hundred reels), so `/download` is the better default.

---

## If you see "login required"

Instagram sometimes blocks anonymous requests from cloud servers. To fix it, give the API a login:

1. In Chrome, log in to Instagram with a **spare account**. Instagram can restrict accounts used for automation, so don't use your main one.
2. In Terminal on your Mac, run:

   ```bash
   cd ~/Downloads
   yt-dlp --cookies-from-browser chrome --cookies all.txt --skip-download "https://www.instagram.com/reel/DbexRNPAQk-/"
   (echo "# Netscape HTTP Cookie File"; grep 'instagram\.com' all.txt) > cookies.txt && rm all.txt
   ```

   This keeps **only** the Instagram cookies. Never upload the full file, because it holds your logins for every site.
3. In Render, open your service, go to **Environment > Secret Files > Add**, set the filename to `cookies.txt`, paste the contents, and **Save**.
   Render restarts the service automatically.

Check `https://YOUR-URL.onrender.com/` afterward. It should show `"cookies_loaded": true`.

---

## Good to know

- **Cost:** free. Render's free tier covers one service running all month.
- **Sleeps when idle:** after 15 min without calls, the first request takes about 1 min. That's why the Make timeout is set to 300.
- **No maintenance:** each time the server wakes up, it updates yt-dlp to the newest version, so Instagram changes are usually handled automatically.
- **`video_url` expires** after a few hours, so download the file in the same scenario run.
- **Locked down:** the API only accepts Instagram links, and only with your API key. Keep the key private.
- Only download reels you own or have permission to use.
