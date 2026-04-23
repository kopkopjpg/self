#!/usr/bin/env python3
“””
MediaDrop - Web-based media downloader
Supports YouTube, SoundCloud, and Spotify (via YouTube search)

Install:  pip install flask yt-dlp requests
Run:      python app.py
Open:     http://localhost:5000
“””

from flask import Flask, request, jsonify, send_from_directory, render_template_string
import yt_dlp
import requests
import re
import os
import threading
import uuid
from pathlib import Path

app = Flask(**name**)
DOWNLOAD_DIR = Path(“downloads”)
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Track job status in memory

jobs = {}

# – platform detection ––––––––––––––––––––––––––––

def detect_platform(url):
url_lower = url.lower()
if “youtube.com” in url_lower or “youtu.be” in url_lower:
return “youtube”
if “spotify.com” in url_lower:
return “spotify”
if “soundcloud.com” in url_lower:
return “soundcloud”
return “generic”

# – spotify metadata –––––––––––––––––––––––––––––

def resolve_spotify(url):
try:
r = requests.get(f”https://open.spotify.com/oembed?url={url}”, timeout=10)
r.raise_for_status()
title = r.json().get(“title”, “”)
return re.sub(r”\s*-\s*”, “ “, title)
except Exception:
return None

# – download worker ———————————————————–

def run_download(job_id, url, mode):
jobs[job_id][“status”] = “downloading”
platform = detect_platform(url)

```
def progress_hook(d):
    if d["status"] == "downloading":
        pct = d.get("_percent_str", "0%").strip().replace("%", "")
        try:
            jobs[job_id]["progress"] = float(pct)
        except ValueError:
            pass
        jobs[job_id]["speed"] = d.get("_speed_str", "").strip()
        jobs[job_id]["eta"] = d.get("_eta_str", "").strip()
    elif d["status"] == "finished":
        jobs[job_id]["filename"] = Path(d["filename"]).name

audio_only = mode == "audio"

if platform == "spotify":
    query = resolve_spotify(url)
    if not query:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = "Could not resolve Spotify track metadata."
        return
    jobs[job_id]["info"] = f"Spotify -> searching YouTube for: {query}"
    actual_url = f"ytsearch1:{query} official audio"
else:
    actual_url = url

if audio_only or platform in ("soundcloud", "spotify"):
    fmt = "bestaudio/best"
    postprocessors = [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }]
else:
    quality_map = {
        "best": "bestvideo+bestaudio/best",
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    }
    fmt = quality_map.get(jobs[job_id].get("quality", "best"), "bestvideo+bestaudio/best")
    postprocessors = []

ydl_opts = {
    "format": fmt,
    "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
    "postprocessors": postprocessors,
    "progress_hooks": [progress_hook],
    "merge_output_format": "mp4" if not audio_only else None,
    "quiet": True,
    "no_warnings": True,
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(actual_url, download=True)
        if info and "title" in info:
            jobs[job_id]["title"] = info.get("title", "")
            jobs[job_id]["thumbnail"] = info.get("thumbnail", "")
            jobs[job_id]["duration"] = info.get("duration_string", "")
    jobs[job_id]["status"] = "done"
    jobs[job_id]["progress"] = 100
except Exception as e:
    jobs[job_id]["status"] = "error"
    jobs[job_id]["error"] = str(e)
```

# – API routes ––––––––––––––––––––––––––––––––

@app.route(”/api/download”, methods=[“POST”])
def start_download():
data = request.json
url = (data.get(“url”) or “”).strip()
mode = data.get(“mode”, “video”)
quality = data.get(“quality”, “best”)

```
if not url:
    return jsonify({"error": "No URL provided"}), 400

job_id = str(uuid.uuid4())[:8]
jobs[job_id] = {
    "status": "queued",
    "progress": 0,
    "url": url,
    "mode": mode,
    "quality": quality,
    "platform": detect_platform(url),
    "filename": None,
    "title": "",
    "thumbnail": "",
    "speed": "",
    "eta": "",
    "error": "",
    "info": "",
}

thread = threading.Thread(target=run_download, args=(job_id, url, mode), daemon=True)
thread.start()
return jsonify({"job_id": job_id})
```

@app.route(”/api/status/<job_id>”)
def job_status(job_id):
job = jobs.get(job_id)
if not job:
return jsonify({“error”: “Job not found”}), 404
return jsonify(job)

@app.route(”/api/file/<job_id>”)
def serve_file(job_id):
job = jobs.get(job_id)
if not job or not job.get(“filename”):
return jsonify({“error”: “File not ready”}), 404
return send_from_directory(DOWNLOAD_DIR.resolve(), job[“filename”], as_attachment=True)

@app.route(”/downloads/<filename>”)
def download_file(filename):
return send_from_directory(DOWNLOAD_DIR.resolve(), filename, as_attachment=True)

# – frontend ——————————————————————

HTML = “””<!DOCTYPE html>

<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>MediaDrop</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #13131a;
    --border: #1f1f2e;
    --accent: #c8f135;
    --accent2: #f13579;
    --text: #e8e8f0;
    --muted: #6b6b80;
    --radius: 16px;
  }

- { box-sizing: border-box; margin: 0; padding: 0; }

body {
background: var(–bg);
color: var(–text);
font-family: ‘Syne’, sans-serif;
min-height: 100dvh;
padding: env(safe-area-inset-top, 0) env(safe-area-inset-right, 16px) env(safe-area-inset-bottom, 0) env(safe-area-inset-left, 16px);
overflow-x: hidden;
}

/* noise texture overlay */
body::before {
content: ‘’;
position: fixed;
inset: 0;
background-image: url(“data:image/svg+xml,%3Csvg viewBox=‘0 0 256 256’ xmlns=‘http://www.w3.org/2000/svg’%3E%3Cfilter id=‘noise’%3E%3CfeTurbulence type=‘fractalNoise’ baseFrequency=‘0.9’ numOctaves=‘4’ stitchTiles=‘stitch’/%3E%3C/filter%3E%3Crect width=‘100%25’ height=‘100%25’ filter=‘url(%23noise)’ opacity=‘0.04’/%3E%3C/svg%3E”);
pointer-events: none;
z-index: 0;
}

.wrap {
position: relative;
z-index: 1;
max-width: 480px;
margin: 0 auto;
padding: 40px 16px 60px;
}

/* header */
header {
text-align: center;
margin-bottom: 48px;
}
.logo {
display: inline-flex;
align-items: center;
gap: 10px;
margin-bottom: 8px;
}
.logo-icon {
width: 40px; height: 40px;
background: var(–accent);
border-radius: 10px;
display: grid;
place-items: center;
}
.logo-icon svg { width: 22px; height: 22px; }
h1 {
font-size: 2rem;
font-weight: 800;
letter-spacing: -0.04em;
color: var(–accent);
}
.tagline {
font-family: ‘DM Mono’, monospace;
font-size: 0.72rem;
color: var(–muted);
letter-spacing: 0.1em;
text-transform: uppercase;
margin-top: 4px;
}

/* platform pills */
.platforms {
display: flex;
gap: 8px;
justify-content: center;
margin-bottom: 32px;
flex-wrap: wrap;
}
.pill {
font-family: ‘DM Mono’, monospace;
font-size: 0.7rem;
padding: 4px 12px;
border-radius: 100px;
border: 1px solid var(–border);
color: var(–muted);
letter-spacing: 0.05em;
transition: all 0.2s;
}
.pill.yt  { border-color: #ff4444; color: #ff4444; }
.pill.sp  { border-color: #1db954; color: #1db954; }
.pill.sc  { border-color: #f50; color: #f50; }

/* card */
.card {
background: var(–surface);
border: 1px solid var(–border);
border-radius: var(–radius);
padding: 24px;
margin-bottom: 16px;
}

label {
display: block;
font-family: ‘DM Mono’, monospace;
font-size: 0.68rem;
letter-spacing: 0.12em;
text-transform: uppercase;
color: var(–muted);
margin-bottom: 8px;
}

.url-input-wrap {
display: flex;
gap: 8px;
align-items: stretch;
}

input[type=“url”] {
flex: 1;
background: var(–bg);
border: 1px solid var(–border);
border-radius: 10px;
color: var(–text);
font-family: ‘DM Mono’, monospace;
font-size: 0.85rem;
padding: 12px 14px;
outline: none;
transition: border-color 0.2s;
-webkit-appearance: none;
}
input[type=“url”]:focus { border-color: var(–accent); }
input[type=“url”]::placeholder { color: var(–muted); }

.paste-btn {
background: var(–border);
border: none;
border-radius: 10px;
color: var(–muted);
font-family: ‘DM Mono’, monospace;
font-size: 0.7rem;
padding: 0 14px;
cursor: pointer;
transition: all 0.2s;
white-space: nowrap;
}
.paste-btn:active { background: var(–accent); color: var(–bg); }

/* mode toggle */
.mode-toggle {
display: flex;
gap: 8px;
margin-top: 16px;
}
.mode-btn {
flex: 1;
background: var(–bg);
border: 1px solid var(–border);
border-radius: 10px;
color: var(–muted);
font-family: ‘Syne’, sans-serif;
font-size: 0.85rem;
font-weight: 700;
padding: 10px;
cursor: pointer;
transition: all 0.2s;
display: flex;
align-items: center;
justify-content: center;
gap: 6px;
}
.mode-btn.active {
background: var(–accent);
border-color: var(–accent);
color: var(–bg);
}

/* quality select */
.quality-row {
margin-top: 16px;
display: none;
}
.quality-row.visible { display: block; }
select {
width: 100%;
background: var(–bg);
border: 1px solid var(–border);
border-radius: 10px;
color: var(–text);
font-family: ‘DM Mono’, monospace;
font-size: 0.85rem;
padding: 12px 14px;
outline: none;
-webkit-appearance: none;
appearance: none;
cursor: pointer;
background-image: url(“data:image/svg+xml,%3Csvg xmlns=‘http://www.w3.org/2000/svg’ width=‘12’ height=‘8’ viewBox=‘0 0 12 8’%3E%3Cpath d=‘M1 1l5 5 5-5’ stroke=’%236b6b80’ stroke-width=‘1.5’ fill=‘none’ stroke-linecap=‘round’/%3E%3C/svg%3E”);
background-repeat: no-repeat;
background-position: right 14px center;
}

/* download button */
.dl-btn {
width: 100%;
background: var(–accent);
border: none;
border-radius: 12px;
color: var(–bg);
font-family: ‘Syne’, sans-serif;
font-size: 1rem;
font-weight: 800;
padding: 16px;
cursor: pointer;
margin-top: 16px;
transition: all 0.15s;
letter-spacing: -0.02em;
position: relative;
overflow: hidden;
}
.dl-btn:active { transform: scale(0.98); }
.dl-btn:disabled {
background: var(–border);
color: var(–muted);
cursor: not-allowed;
}

/* status card */
.status-card {
display: none;
animation: slideUp 0.3s ease;
}
.status-card.visible { display: block; }

@keyframes slideUp {
from { opacity: 0; transform: translateY(12px); }
to   { opacity: 1; transform: translateY(0); }
}

.status-header {
display: flex;
align-items: center;
gap: 12px;
margin-bottom: 16px;
}
.thumb {
width: 60px; height: 60px;
border-radius: 8px;
object-fit: cover;
background: var(–border);
flex-shrink: 0;
}
.thumb-placeholder {
width: 60px; height: 60px;
border-radius: 8px;
background: var(–border);
flex-shrink: 0;
display: grid;
place-items: center;
color: var(–muted);
font-size: 1.4rem;
}
.status-meta { flex: 1; min-width: 0; }
.status-title {
font-weight: 700;
font-size: 0.9rem;
white-space: nowrap;
overflow: hidden;
text-overflow: ellipsis;
margin-bottom: 4px;
}
.status-platform {
font-family: ‘DM Mono’, monospace;
font-size: 0.68rem;
color: var(–muted);
text-transform: uppercase;
letter-spacing: 0.08em;
}

/* progress bar */
.progress-track {
height: 4px;
background: var(–border);
border-radius: 100px;
overflow: hidden;
margin-bottom: 8px;
}
.progress-fill {
height: 100%;
background: var(–accent);
border-radius: 100px;
transition: width 0.4s ease;
width: 0%;
}
.progress-fill.error { background: var(–accent2); }
.progress-stats {
display: flex;
justify-content: space-between;
font-family: ‘DM Mono’, monospace;
font-size: 0.68rem;
color: var(–muted);
}

/* info line */
.info-line {
font-family: ‘DM Mono’, monospace;
font-size: 0.72rem;
color: var(–muted);
margin-top: 8px;
word-break: break-all;
}

/* save button */
.save-btn {
display: none;
width: 100%;
background: transparent;
border: 1px solid var(–accent);
border-radius: 12px;
color: var(–accent);
font-family: ‘Syne’, sans-serif;
font-size: 1rem;
font-weight: 700;
padding: 14px;
cursor: pointer;
margin-top: 12px;
transition: all 0.15s;
text-decoration: none;
text-align: center;
}
.save-btn.visible { display: block; }
.save-btn:active { background: var(–accent); color: var(–bg); }

.new-btn {
display: none;
width: 100%;
background: transparent;
border: 1px solid var(–border);
border-radius: 12px;
color: var(–muted);
font-family: ‘Syne’, sans-serif;
font-size: 0.9rem;
font-weight: 700;
padding: 12px;
cursor: pointer;
margin-top: 8px;
transition: all 0.15s;
}
.new-btn.visible { display: block; }

.error-msg {
font-family: ‘DM Mono’, monospace;
font-size: 0.75rem;
color: var(–accent2);
margin-top: 8px;
line-height: 1.5;
}

/* footer */
footer {
text-align: center;
margin-top: 48px;
font-family: ‘DM Mono’, monospace;
font-size: 0.65rem;
color: var(–muted);
letter-spacing: 0.08em;
}
footer span { color: var(–accent); }
</style>

</head>
<body>
<div class="wrap">

  <header>
    <div class="logo">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#0a0a0f" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2v10m0 0l-3-3m3 3l3-3"/>
          <path d="M3 17v2a2 2 0 002 2h14a2 2 0 002-2v-2"/>
        </svg>
      </div>
      <h1>MediaDrop</h1>
    </div>
    <p class="tagline">paste * pick * download</p>
  </header>

  <div class="platforms">
    <span class="pill yt">YouTube</span>
    <span class="pill sp">Spotify</span>
    <span class="pill sc">SoundCloud</span>
  </div>

  <!-- main card -->

  <div class="card" id="mainCard">
    <label>Paste your link</label>
    <div class="url-input-wrap">
      <input type="url" id="urlInput" placeholder="https://..." autocomplete="off" autocorrect="off" spellcheck="false">
      <button class="paste-btn" onclick="pasteFromClipboard()">Paste</button>
    </div>

```
<div class="mode-toggle">
  <button class="mode-btn active" id="btnVideo" onclick="setMode('video')">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M9 9l6 3-6 3V9z"/></svg>
    Video
  </button>
  <button class="mode-btn" id="btnAudio" onclick="setMode('audio')">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M9 18V6l12-3v12"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="15" r="3"/></svg>
    Audio (MP3)
  </button>
</div>

<div class="quality-row visible" id="qualityRow">
  <label style="margin-top:16px">Quality</label>
  <select id="qualitySelect">
    <option value="best">Best available</option>
    <option value="1080p">1080p Full HD</option>
    <option value="720p">720p HD</option>
    <option value="480p">480p SD</option>
  </select>
</div>

<button class="dl-btn" id="dlBtn" onclick="startDownload()">v Download</button>
```

  </div>

  <!-- status card -->

  <div class="card status-card" id="statusCard">
    <div class="status-header">
      <div class="thumb-placeholder" id="thumbPlaceholder">~</div>
      <img class="thumb" id="thumb" style="display:none" alt="thumbnail">
      <div class="status-meta">
        <div class="status-title" id="statusTitle">Starting...</div>
        <div class="status-platform" id="statusPlatform">-</div>
      </div>
    </div>

```
<div class="progress-track">
  <div class="progress-fill" id="progressFill"></div>
</div>
<div class="progress-stats">
  <span id="progressPct">0%</span>
  <span id="progressSpeed"></span>
  <span id="progressEta"></span>
</div>

<div class="info-line" id="infoLine"></div>
<div class="error-msg" id="errorMsg"></div>

<a class="save-btn" id="saveBtn" href="#" download>v Save to Files</a>
<button class="new-btn" id="newBtn" onclick="reset()"><- Download another</button>
```

  </div>

  <footer>made with <span>yt-dlp</span> * runs locally on your machine</footer>
</div>

<script>
let mode = 'video';
let pollTimer = null;

function setMode(m) {
  mode = m;
  document.getElementById('btnVideo').classList.toggle('active', m === 'video');
  document.getElementById('btnAudio').classList.toggle('active', m === 'audio');
  document.getElementById('qualityRow').classList.toggle('visible', m === 'video');
}

async function pasteFromClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    document.getElementById('urlInput').value = text;
  } catch {
    document.getElementById('urlInput').focus();
  }
}

async function startDownload() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) { document.getElementById('urlInput').focus(); return; }

  const quality = document.getElementById('qualitySelect').value;
  document.getElementById('dlBtn').disabled = true;
  document.getElementById('dlBtn').textContent = 'Starting...';

  // show status card
  document.getElementById('statusCard').classList.add('visible');
  document.getElementById('statusTitle').textContent = 'Queuing download...';
  document.getElementById('statusPlatform').textContent = detectPlatform(url);
  document.getElementById('progressFill').style.width = '0%';
  document.getElementById('progressPct').textContent = '0%';
  document.getElementById('progressSpeed').textContent = '';
  document.getElementById('progressEta').textContent = '';
  document.getElementById('infoLine').textContent = '';
  document.getElementById('errorMsg').textContent = '';
  document.getElementById('saveBtn').classList.remove('visible');
  document.getElementById('newBtn').classList.remove('visible');
  document.getElementById('thumb').style.display = 'none';
  document.getElementById('thumbPlaceholder').style.display = 'grid';

  const res = await fetch('/api/download', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ url, mode, quality })
  });
  const { job_id } = await res.json();
  pollJob(job_id);
}

function pollJob(jobId) {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    const res = await fetch(`/api/status/${jobId}`);
    const job = await res.json();

    if (job.title) document.getElementById('statusTitle').textContent = job.title;
    if (job.info)  document.getElementById('infoLine').textContent = job.info;

    if (job.thumbnail) {
      const img = document.getElementById('thumb');
      img.src = job.thumbnail;
      img.style.display = 'block';
      document.getElementById('thumbPlaceholder').style.display = 'none';
    }

    const pct = Math.round(job.progress || 0);
    document.getElementById('progressFill').style.width = pct + '%';
    document.getElementById('progressPct').textContent = pct + '%';
    if (job.speed) document.getElementById('progressSpeed').textContent = job.speed;
    if (job.eta)   document.getElementById('progressEta').textContent = 'ETA ' + job.eta;

    if (job.status === 'done') {
      clearInterval(pollTimer);
      document.getElementById('progressFill').style.width = '100%';
      document.getElementById('progressPct').textContent = '100%';
      document.getElementById('progressSpeed').textContent = '';
      document.getElementById('progressEta').textContent = 'v Done';
      const saveBtn = document.getElementById('saveBtn');
      saveBtn.href = `/api/file/${jobId}`;
      saveBtn.setAttribute('download', job.filename || 'media');
      saveBtn.classList.add('visible');
      document.getElementById('newBtn').classList.add('visible');
      document.getElementById('dlBtn').textContent = 'v Download';
    }

    if (job.status === 'error') {
      clearInterval(pollTimer);
      document.getElementById('progressFill').classList.add('error');
      document.getElementById('progressFill').style.width = '100%';
      document.getElementById('errorMsg').textContent = '! ' + job.error;
      document.getElementById('newBtn').classList.add('visible');
      document.getElementById('dlBtn').disabled = false;
      document.getElementById('dlBtn').textContent = 'v Download';
    }
  }, 800);
}

function detectPlatform(url) {
  url = url.toLowerCase();
  if (url.includes('youtube') || url.includes('youtu.be')) return 'YOUTUBE';
  if (url.includes('spotify')) return 'SPOTIFY';
  if (url.includes('soundcloud')) return 'SOUNDCLOUD';
  return 'GENERIC';
}

function reset() {
  clearInterval(pollTimer);
  document.getElementById('statusCard').classList.remove('visible');
  document.getElementById('progressFill').classList.remove('error');
  document.getElementById('urlInput').value = '';
  document.getElementById('dlBtn').disabled = false;
  document.getElementById('dlBtn').textContent = 'v Download';
  document.getElementById('urlInput').focus();
}
</script>

</body>
</html>"""

@app.route(”/”)
def index():
return render_template_string(HTML)

if **name** == “**main**”:
port = int(os.environ.get(“PORT”, 8080))
print(f”\n  ~  MediaDrop is running on port {port}!\n”)
app.run(host=“0.0.0.0”, port=port, debug=False)
