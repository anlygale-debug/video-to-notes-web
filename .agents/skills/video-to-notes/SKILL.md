---
name: video-to-notes
description: "Turn video content into structured study notes and publish to Feishu. Triggers when user asks to 'take notes on this video', 'summarize this video', 'make study notes', 'convert video to notes'. Full pipeline: search → download audio → transcribe → structure notes → publish to Feishu → clean up."
---

# Video to Study Notes → Feishu

Convert any online video into structured study notes, then publish directly to Feishu Docs. The full pipeline: search → find → download audio → transcribe → structure notes → publish to Feishu → clean up ALL intermediate files.

## CRITICAL: Always Clean Up

After the Feishu doc is published, **delete EVERY intermediate file**. Only the `.md` notes file should remain locally. See Step 7 for the complete cleanup checklist.

## Supported Platforms

| Platform | Search/Discovery | Audio Download | Auth Required |
|----------|-----------------|----------------|----------------|
| 小红书 | `xhs search` → xsec_token → CDN直链 | curl CDN → ffmpeg extract | `xhs login` |
| B站 | [官方公开 API](https://api.bilibili.com/x/web-interface/search/type) | `yt-dlp --cookies-from-browser chrome` | Chrome 登录 |
| YouTube | yt-dlp search | `yt-dlp -x --audio-format mp3` | 无 |
| YouTube | `yt-dlp` or direct URL | `yt-dlp -x --audio-format mp3` (try `--write-auto-subs` first) |

## Prerequisites

All tools are installed via agent-reach venv. Always activate first:

```bash
source ~/.agent-reach-venv/bin/activate
```

Required:
- `xhs` CLI — XHS search, metadata, and video CDN URL extraction (logged in via `xhs login`)
- `yt-dlp` — B站/YouTube audio download
- `curl` — XHS CDN download + Groq API call
- `ffmpeg` — extract audio from XHS video mp4
- `python3` — JSON processing, Groq key retrieval
- Groq API Key — stored in `~/.agent-reach/config.yaml` (`groq_api_key`)
- Proxy at `127.0.0.1:7890` — needed for Groq API (blocked in mainland China)

## Workflow

### Step 1: Find the Video and Get xsec_token

**小红书 — user provides a short link or note URL:**

1. Resolve short link (if needed):
   ```bash
   curl -sL -o /dev/null -w "%{url_effective}" "http://xhslink.com/..."
   ```
   Extract note_id from the final URL.

2. Search to get the `xsec_token` (required for reading video data):
   ```bash
   xhs search "video title keywords" --json > /tmp/xhs_search.json
   ```

3. Parse the search results — find the matching note and extract:
   - `id` → note_id
   - `xsec_token` → needed for Step 2
   - `display_title`, `user.nickname`, `interact_info` → metadata

**小红书 — user provides a search query:**

Directly use `xhs search "query" --json`, find the item with highest `liked_count`, extract note_id + xsec_token.

**B站/YouTube:**

- B站: extract BV号 from URL; or web search `"title keywords" bilibili` to find BV号
- YouTube: direct URL or `yt-dlp "ytsearch:query"`

### Step 2: Get Full Video Metadata

**小红书** — use xsec_token to get video data including CDN URLs:

```bash
xhs read <note_id> --xsec-token "<xsec_token>" --json > /tmp/xhs_video.json
```

Parse the JSON to extract:
- `note_card.display_title` → title
- `note_card.user.nickname` → creator
- `note_card.interact_info.liked_count` etc. → engagement
- `note_card.desc` → description
- `note_card.video.media.stream` → video CDN URLs (see Step 3)

**B站** — `yt-dlp --cookies-from-browser chrome --dump-json URL`（需要 Cookie）

### Step 3: Download Audio

**小红书 — CDN direct download + ffmpeg audio extraction:**

1. From the video JSON, pick the best quality stream that balances size and quality:
   ```python
   # Prefer h265 720p (smallest), fallback to h264
   streams = video['media']['stream']
   # Pick h265 > h264, prefer 720p over 1080p for smaller file
   ```

2. The `master_url` contains `sign` and `t` parameters that **expire quickly** — download immediately:
   ```bash
   curl -sL -o /tmp/xhs_video.mp4 "<master_url>"
   ```

3. Extract audio from the downloaded video:
   ```bash
   ffmpeg -y -i /tmp/xhs_video.mp4 -vn -acodec libmp3lame -q:a 2 /tmp/video_audio.mp3
   ```

> ⚠️ CDN URLs expire within minutes. Never cache them — download right after getting from `xhs read`.

**B站:**

```bash
# 必须带 Chrome Cookie！2026 年起 B站 HTTP 412 拦截所有未认证请求
yt-dlp --cookies-from-browser chrome -x --audio-format mp3 -o "/tmp/video_audio.%(ext)s" "https://www.bilibili.com/video/BVxxxxxx"
```

**YouTube:**

```bash
# Try subtitles first (no transcription needed)
yt-dlp --write-auto-subs --skip-download --sub-lang zh-Hans,zh,en "URL"

# If no subtitles, download audio
yt-dlp -x --audio-format mp3 -o "/tmp/video_audio.%(ext)s" "URL"
```

### Step 4: Transcribe Audio

**首选：本地 Whisper（免费，离线）**

```python
import whisper
model = whisper.load_model('tiny')  # tiny=70MB快, base=150MB, small=500MB高质量
result = model.transcribe(audio_path, task='transcribe', verbose=False, fp16=False)
text = result['text'].strip()
```

**繁体转简体（可选）：**

```python
from zhconv import convert
text = convert(text, 'zh-cn')
```

**备选：Groq API（云端快，需代理）**

```bash
GROQ_KEY=$(python3 -c "import yaml; d=yaml.safe_load(open('$HOME/.agent-reach/config.yaml')); print(d['groq_api_key'])")
curl -s --proxy http://127.0.0.1:7890 \
  https://api.groq.com/openai/v1/audio/transcriptions \
  -H "Authorization: bearer $GROQ_KEY" \
  -F "file=@/tmp/video_audio.mp3" \
  -F "model=whisper-large-v3" \
  -F "response_format=json" \
  -F "language=zh" \
  -o /tmp/transcript.json
python3 -c "import json; d=json.load(open('/tmp/transcript.json')); print(d['text'])"
```

- `tiny` 模型最快（~70MB），`small` 最准确；lang 参数 `None`=自动检测
- File size limit: ~25MB. For videos >20 min, transcribe in segments
- **Always use `--proxy`** for Groq API calls — Groq is blocked in mainland China

### Step 5: Generate Markdown Notes

Read the full transcript, then produce a markdown document. Template:

```
# [Title] — 课后笔记

> metadata: creator, platform, engagement stats, transcription method

## 一、核心论点
## 二、内容框架
## 三、关键数据与引用
## 四、个人思考
```

Principles: preserve exact phrasing as blockquotes, use tables for comparisons, write so notes are useful without watching the video. Save as `[Title]-课后笔记.md`.

**双模式：**
- **标准模式**：全文 → 单次 LLM 调用（max_tokens=16000），快，适合<15min
- **详细模式**：分段并行处理（~6000字/段，最多3段同时），适合>20min 长视频

### Step 6: Publish to Feishu

One command, ~3 seconds:

```bash
python3 ~/.agent-reach/tools/feishu_publish.py "[Title] — 课后笔记" "[path].md"
```

Prints the doc URL. Share it with the user.

Requires `feishu_app_id` and `feishu_app_secret` in `~/.agent-reach/config.yaml`.

### Step 7: Clean Up ALL Intermediate Files

**After Feishu publish is confirmed, delete every intermediate file:**

```bash
rm -f /tmp/xhs_search.json \
      /tmp/xhs_video.json \
      /tmp/xhs_video.mp4 \
      /tmp/video_audio.mp3 \
      /tmp/transcript.json
```

**Checklist — make sure ALL of these are gone:**
- [ ] Search result JSON (`/tmp/xhs_search.json`)
- [ ] Video metadata JSON (`/tmp/xhs_video.json`)
- [ ] Downloaded video mp4 (`/tmp/xhs_video.mp4`) — XHS path
- [ ] Audio mp3 (`/tmp/video_audio.mp3`)
- [ ] Transcript JSON (`/tmp/transcript.json`)
- [ ] Any raw transcript `.txt` saved during processing

**保留：** `[Title]-课后笔记.md` 在工作目录。音频和转录文本可单独下载。

### Step 8: 输出选项

| 文件 | 说明 |
|------|------|
| `[Title]-课后笔记.md` | Markdown 笔记 |
| `[Title]-课后笔记.pdf` | PDF（weasyprint 渲染） |
| 下载音频 | 原始 mp3 音频文件 |
| 下载转录文本 | 纯文本转录全文 |
| 下载完整包 | 笔记 + 转录 + 音频 打包 |
| 笔记 + 转录 | 合并 Markdown 文件 |

## Platform-Specific Details

### 小红书 (Xiaohongshu) — Direct CDN Path

The complete end-to-end flow for XHS:

```
短链接 → curl -sL resolve → note_id
    ↓
xhs search "title" --json → xsec_token
    ↓
xhs read <id> --xsec-token <token> --json → CDN master_url
    ↓  (immediately — URLs expire in minutes)
curl -sL -o /tmp/xhs_video.mp4 "<master_url>"
    ↓
ffmpeg -i /tmp/xhs_video.mp4 -vn -acodec libmp3lame /tmp/video_audio.mp3
    ↓
Groq Whisper → transcript
    ↓
Generate notes → clean up ALL /tmp files
```

Key points:
- Note ID format: `69f46bcc0000000023015b24`
- Short link format: `http://xhslink.com/o/xxxxx`
- `xsec_token` comes from search results (not from the URL or short link resolution)
- CDN URLs have signed `sign` and `t` parameters that expire — download immediately
- Prefer h265 720p stream for smallest file size (~14MB for 2-3 min video)
- Stream types: h264 (259, larger) / h265 (114=720p, 115=1080p)
- No cookies needed for CDN download once you have the signed URL

### B站 (Bilibili)

- BV号 format: `BV1U1RTBTEVa`，完整链接: `https://www.bilibili.com/video/BVxxxxxx`
- **2026 年起必须带 Chrome Cookie**，否则 HTTP 412（`--cookies-from-browser chrome`）
- 搜索用官方公开 API: `api.bilibili.com/x/web-interface/search/type`
- `yt-dlp --cookies-from-browser chrome --dump-json` 取元数据（title/uploader/duration）
- `yt-dlp --cookies-from-browser chrome -x --audio-format mp3` 下载音频

### YouTube

- Standard yt-dlp support
- **Always try `--write-auto-subs` first** — if subtitles exist, skip audio download + transcription entirely
- YouTube auto-captions are often good enough quality for notes

## How to Find Groq API Key

```bash
python3 -c "import yaml; d=yaml.safe_load(open('$HOME/.agent-reach/config.yaml')); print(d['groq_api_key'])"
```

If not configured, ask user to get free key at https://console.groq.com and run:
```bash
agent-reach configure groq-key gsk_xxxxx
```

## Error Handling

| Problem | Solution |
|---------|----------|
| `xhs read` returns empty `{}` | Need xsec_token — get from `xhs search` results first |
| CDN URL returns 404 | URL expired, re-run `xhs read` with xsec_token for fresh URL |
| Short link won't resolve | Try both `curl -sL` and `curl -sI`; also try with proxy |
| Groq returns "Forbidden" | Add `--proxy http://127.0.0.1:7890` to curl |
| Audio >25MB | Split with ffmpeg: `ffmpeg -i input.mp3 -f segment -segment_time 600 -c copy /tmp/part_%03d.mp3` |
| B站 HTTP 412 (无 Cookie) | 加 `--cookies-from-browser chrome`，确保 Chrome 已登录 B站 |
| B站 搜索无结果 | 用官方 API 而非 yt-dlp search：`api.bilibili.com/x/web-interface/search/type` |
| 繁体字输出 | `pip install zhconv`，转录后 `convert(text, 'zh-cn')` |
| No Groq key configured | Ask user to get free key at https://console.groq.com |
| Transcript quality poor | Try `whisper-large-v3` (not turbo), or check if audio has clear speech |
| XHS CDN download slow | Use the lower-quality stream (h265 720p) for smaller file size |
