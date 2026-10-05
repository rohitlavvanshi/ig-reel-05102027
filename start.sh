#!/bin/sh
# Grab the newest yt-dlp each time the server wakes up (keeps it working when Instagram changes)
pip install --no-cache-dir -q -U yt-dlp || true
exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-10000}"
