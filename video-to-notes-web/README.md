# Video to Notes

Paste a video link → get structured study notes. Supports Douyin, Xiaohongshu, Bilibili, and YouTube.

## Quick Start (macOS)

### 1. Prerequisites

```bash
# System tools
brew install ffmpeg weasyprint

# Python venv
python3 -m venv ~/.vtn-venv
source ~/.vtn-venv/bin/activate
```

### 2. Install

```bash
git clone https://github.com/anlygale-debug/video-to-notes-web.git
cd video-to-notes-web

# Install Python packages
pip install fastapi uvicorn openai-whisper yt-dlp markdown zhconv

# Download the Whisper model (one-time, ~70MB)
mkdir -p ~/.cache/whisper
curl -L -o ~/.cache/whisper/tiny.pt \
  "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt"
```

### 3. Configure (Optional)

#### Cloudflare 云端转录（低内存服务器推荐）

本地默认仍使用 Whisper `tiny`。要改用 Cloudflare Workers AI 的
`whisper-large-v3-turbo`，在启动服务前设置：

```bash
export VTN_TRANSCRIBER=cloudflare
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
export CLOUDFLARE_API_TOKEN="your-workers-ai-token"

# 可选：提供不限定语言的领域词，帮助识别专有名词。
# 中英文或多语言视频建议留空，避免提示词干扰自动语言识别。
export VTN_TRANSCRIPTION_PROMPT="AI Agent、RAG、Whisper"
```

不要把真实 Token 写进代码、README 或提交到 Git。转录默认由 Whisper 自动识别
音频语言：英文语音保留英文，中文语音输出简体中文。大音频会在本机通过 FFmpeg
转成单声道并按 10 分钟切段，再逐段发送到 Cloudflare，避免请求体过大；转录时
不需要在服务器内存中加载 Whisper 模型。删除 `VTN_TRANSCRIBER` 或设为 `local`
即可恢复本地 `tiny`。

#### AI 笔记生成

For AI-powered note generation, set your LLM API key. Create `~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "sk-your-key-here",
    "ANTHROPIC_MODEL": "DeepSeek-V4-pro[1m]"
  }
}
```

Without this, notes will be plain transcripts.

### 4. Start

在 macOS 上可直接双击项目根目录的 `打开 Video to Notes.command`。它会启动
本地服务并打开产品介绍页；点击「开始使用」即可进入应用。管理免费/高速线路时，
双击 `打开本地管理后台.command`。

也可以从终端启动：

```bash
./scripts/run-local.sh
```

产品介绍页：http://127.0.0.1:4176/video-notes
应用页：http://127.0.0.1:4176/next

## Public Access and High-speed Routes

The hosted app is open without an invite code. Anonymous visitors can parse a
supported video link, download video/audio, use free transcription, and use the
free note-generation route. An invite code only unlocks the high-speed routes:

- high-speed transcription consumes the invite's remaining audio minutes;
- high-speed note generation consumes one generation at a time;
- when high-speed quota is exhausted, all free features remain available.

The browser device ID owns history records independently from the invite code,
so entering a code does not hide work created before activation.

## Platform Support

| Platform | Search | Download | Notes |
|----------|--------|----------|-------|
| Bilibili | ✅ Official API | ✅ yt-dlp | |
| YouTube | ✅ yt-dlp | ✅ yt-dlp | |
| Xiaohongshu | ✅ xhs CLI | ✅ CDN direct | Requires `xhs login` |
| Douyin | — | ✅ yt-dlp | Requires fresh anonymous browser cookies |

### Douyin Setup

The local app first tries the current Chrome browser's Douyin cookies. Open
`https://www.douyin.com/` once in Chrome before retrying; login is not always
required. On a server, point the app to a dedicated Netscape cookie file:

```bash
export VTN_DOUYIN_COOKIES_PATH="/var/lib/video-to-notes/douyin-cookies.txt"
```

### Xiaohongshu Setup

```bash
pip install xiaohongshu-cli
xhs login  # Scan QR code with Xiaohongshu app
```

## Features

- **Standard Mode**: Single-pass LLM structuring, fast (<15 min videos)
- **Detailed Mode**: Chunked parallel processing for long videos (>20 min)
- **PDF Export**: Styled PDF via weasyprint
- **Note History**: Stored in browser localStorage, survives refresh
- **Mobile**: Responsive design, works on iPhone Safari via LAN

## iPhone Access

Same WiFi → visit `http://[Mac-IP]:3000` (printed at startup)

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Whisper model not found | `curl -L -o ~/.cache/whisper/tiny.pt [URL]` |
| 逐字稿没有转换为简体中文 | `pip install zhconv` 后重启本地服务 |
| Cloudflare 转录提示凭证无效 | 确认 Token 具有 Workers AI Read/Edit 权限，并检查 Account ID |
| B站 search fails | Ensure direct network access (no proxy needed for B站 API) |
| XHS fails | Run `xhs login` again to refresh cookies |
| LLM notes won't generate | Check `~/.claude/settings.json` has valid API credentials |
| PDF export fails | `brew install weasyprint` |
