---
name: bilibili-video-extractor
description: Extract video content from Bilibili (B站) — search videos, download audio, and get transcripts. Uses B站 official public API for search and yt-dlp for media extraction. No login required for basic quality. Use when: user shares a B站 link or wants to search B站 videos and read their content.
---

# Bilibili Video Extractor

Access Bilibili video content through its public API and yt-dlp. No authentication needed — B站's search API is open and yt-dlp handles media extraction from the public CDN.

## Pipeline

### Search

B站 has a public search API with no auth required:

```bash
curl -s "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=URL_ENCODED_QUERY" \
  -H "User-Agent: Mozilla/5.0"
```

Returns JSON with video results including:

```python
{
    "bvid": "BV1U1RTBTEVa",           # Video ID
    "title": "...",                     # Title (may contain HTML <em> tags)
    "author": "创作者名",               # Creator name
    "duration": "14:10",               # Duration string (MM:SS or HH:MM:SS)
    "video_review": 0,                 # Like count
    "play": 12345,                     # Play count
}
```

Parse the `title` by stripping HTML tags: `re.sub(r'<[^>]+>', '', title)`

### Extract Video/Audio

Use yt-dlp with B站 BV号:

```bash
yt-dlp -x --audio-format mp3 -o "/tmp/bili_audio.%(ext)s" \
  "https://www.bilibili.com/video/BV1U1RTBTEVa"
```

Options:
- `-x`: extract audio only
- `--audio-format mp3`: convert to mp3
- For high-res video (1080P+): add `--cookies-from-browser chrome` (requires B站 login in browser)

### Transcribe Audio

Same as any audio file:

```bash
# Local Whisper
python3 -c "
import whisper
model = whisper.load_model('tiny')
result = model.transcribe('/tmp/bili_audio.mp3')
print(result['text'])
"

# Or Groq API
curl -s --proxy http://127.0.0.1:7890 \
  https://api.groq.com/openai/v1/audio/transcriptions \
  -H "Authorization: bearer $GROQ_KEY" \
  -F "file=@/tmp/bili_audio.mp3" \
  -F "model=whisper-large-v3"
```

### Duration Parsing

B站 returns durations as strings like `"14:10"` or `"1083:13"`:

```python
def parse_duration(s):
    parts = s.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])   # MM:SS
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])  # HH:MM:SS
    return 0
```

## Platform Comparison

| | B站 | YouTube | 小红书 |
|------|------|------|------|
| Search | Public API, no auth | yt-dlp search | xhs-cli, needs login |
| Download | yt-dlp | yt-dlp | xhs-cli + CDN URL |
| Auth needed | No (basic quality) | No | Yes (scan QR) |
| Difficulty | Easy | Easy | Complex (xsec_token) |

## Common Issues

| Problem | Fix |
|---------|-----|
| High-res video blocked | Add `--cookies-from-browser chrome` to yt-dlp |
| Search returns empty | URL-encode the keyword, add User-Agent header |
| yt-dlp not found | `pip install yt-dlp` |
| Title contains HTML | Strip with regex before displaying |
