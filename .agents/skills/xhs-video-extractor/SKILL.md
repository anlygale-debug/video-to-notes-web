---
name: xhs-video-extractor
description: Extract video content from Xiaohongshu (小红书) posts — including audio, transcript, and metadata. Unlike web scraping tools that hit anti-bot walls, this uses the internal XHS API with real user cookies to get CDN video streams directly. Use when: user shares a XHS link and wants to see/read the video content, or any agent needs to access XHS video behind the login wall.
---

# 小红书 Video Extractor

Access Xiaohongshu video content through its internal API — the same way the official app does. This bypasses the web scraping anti-bot measures that block browser-based tools.

## Why This Works (When Others Don't)

```
Browser tools (BB Browser, agent-reach):
  → visit xiaohongshu.com web page
  → try to read DOM
  → blocked by anti-bot detection, JS rendering, missing auth

This skill:
  → use real user cookies from xhs login
  → call internal API at edith.xiaohongshu.com
  → server thinks it's the official app
  → returns full data including CDN video URLs
```

## Prerequisites

```bash
pip install xiaohongshu-cli
xhs login  # Scan QR code once with Xiaohongshu app
```

## Pipeline

### Step 1: Resolve the link

```bash
# Resolve short link to get note_id
curl -sL -o /dev/null -w "%{url_effective}" "http://xhslink.com/o/xxxxx"
# → https://www.xiaohongshu.com/discovery/item/<note_id>?...

# Extract note_id from URL (regex: /item/([a-f0-9]+))
```

### Step 2: Get xsec_token (security token)

The internal API requires an `xsec_token` to access video data. Get it from search:

```bash
xhs search "video title keywords" --json
```

Parse the JSON response. Each result item has:
- `id`: note_id
- `xsec_token`: needed for Step 3
- `note_card.display_title`: video title
- `note_card.user.nickname`: creator
- `note_card.interact_info.liked_count`: likes

### Step 3: Read video data with xsec_token

```bash
xhs read "<note_id>" --xsec-token "<xsec_token>" --json
```

The response contains:
- `note_card.title`: actual title
- `note_card.desc`: description / hashtags
- `note_card.video.media.stream`: CDN video URLs

### Step 4: Extract CDN video URL

Parse the video streams from the response. Choose the smallest h265 stream:

```python
streams = note_card['video']['media']['stream']
for codec, formats in streams.items():
    for f in formats:
        if '114' in f.get('stream_desc', ''):  # h265 720p
            url = f['master_url']
            break
```

> The `master_url` contains signed `sign` and `t` parameters that **expire within minutes**. Download immediately.

### Step 5: Download video and extract audio

```bash
# Download from CDN (URL expires!)
curl -sL -o /tmp/xhs_video.mp4 "<master_url>"

# Extract audio for transcription
ffmpeg -y -i /tmp/xhs_video.mp4 -vn -acodec libmp3lame -q:a 2 /tmp/xhs_audio.mp3
```

### Step 6: Transcribe

```bash
# Option A: Local Whisper (free, private)
python3 -c "
import whisper
model = whisper.load_model('tiny')
result = model.transcribe('/tmp/xhs_audio.mp3')
print(result['text'])
"

# Option B: Groq API (fast, requires API key)
curl -s --proxy http://127.0.0.1:7890 \
  https://api.groq.com/openai/v1/audio/transcriptions \
  -H "Authorization: bearer $GROQ_KEY" \
  -F "file=@/tmp/xhs_audio.mp3" \
  -F "model=whisper-large-v3" \
  -F "language=zh"

# Option C: DeepSeek/GPT — feed audio via multimodal if supported
```

## Common Issues

| Problem | Fix |
|---------|-----|
| `xhs read` returns empty `{}` | Missing xsec_token — get from `xhs search` first |
| CDN URL returns 404 | URL expired — re-run `xhs read` for fresh URL |
| `xhs search` SSL error | Network issue — retry or check proxy |
| Need to re-login | `xhs login --qrcode` to refresh cookies |

## Why Not Use Other Tools

| Tool | Approach | XHS Result |
|------|----------|------------|
| BB Browser | Chrome automation → web page DOM | ❌ Anti-bot blocks |
| agent-reach | Browser-based extraction | ❌ Can't get video |
| Playwright/Selenium | Browser automation | ❌ JS-rendered content missing |
| This skill | Internal API with real cookies | ✅ Full CDN access |
