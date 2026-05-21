# Video to Notes

Paste a video link → get structured study notes. Supports Xiaohongshu, Bilibili, and YouTube.

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
pip install fastapi uvicorn openai-whisper yt-dlp markdown

# Download the Whisper model (one-time, ~70MB)
mkdir -p ~/.cache/whisper
curl -L -o ~/.cache/whisper/tiny.pt \
  "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt"
```

### 3. Configure (Optional)

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

```bash
./start.sh
```

Open http://localhost:3000

## Platform Support

| Platform | Search | Download | Notes |
|----------|--------|----------|-------|
| Bilibili | ✅ Official API | ✅ yt-dlp | |
| YouTube | ✅ yt-dlp | ✅ yt-dlp | |
| Xiaohongshu | ✅ xhs CLI | ✅ CDN direct | Requires `xhs login` |

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
| B站 search fails | Ensure direct network access (no proxy needed for B站 API) |
| XHS fails | Run `xhs login` again to refresh cookies |
| LLM notes won't generate | Check `~/.claude/settings.json` has valid API credentials |
| PDF export fails | `brew install weasyprint` |
