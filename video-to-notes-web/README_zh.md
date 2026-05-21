# Video to Notes

粘贴视频链接 → 获取结构化笔记。支持小红书、B站、YouTube。

## 快速开始（macOS）

### 1. 安装系统依赖

```bash
brew install ffmpeg weasyprint
```

### 2. 创建虚拟环境

```bash
python3 -m venv ~/.vtn-venv
source ~/.vtn-venv/bin/activate
```

### 3. 克隆项目并安装

```bash
git clone https://github.com/anlygale-debug/video-to-notes-web.git
cd video-to-notes-web

# 安装 Python 依赖
pip install fastapi uvicorn openai-whisper yt-dlp markdown

# 下载 Whisper 模型（只需一次，约 70MB）
mkdir -p ~/.cache/whisper
curl -L -o ~/.cache/whisper/tiny.pt \
  "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt"
```

> 如果 `curl` 下载失败（国内网络），可手动下载后放到 `~/.cache/whisper/tiny.pt`

### 4. 配置 LLM API（可选，但推荐）

笔记生成需要大语言模型。创建 `~/.claude/settings.json`，填入你的 DeepSeek API Key：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "sk-你的密钥",
    "ANTHROPIC_MODEL": "DeepSeek-V4-pro[1m]"
  }
}
```

> [点击获取 DeepSeek API Key](https://platform.deepseek.com/)（新用户有免费额度）

不配置的话，笔记会降级为纯转录文本。

### 5. 启动

```bash
./start.sh
```

浏览器打开 http://localhost:3000

## 平台支持

| 平台 | 搜索 | 下载 | 备注 |
|------|------|------|------|
| B站 | ✅ 官方 API | ✅ yt-dlp | |
| YouTube | ✅ yt-dlp | ✅ yt-dlp | |
| 小红书 | ✅ xhs CLI | ✅ CDN 直链 | 需要登录 |

### 小红书额外配置

```bash
pip install xiaohongshu-cli
xhs login  # 用小红书 App 扫码登录
```

## 功能说明

| 功能 | 说明 |
|------|------|
| 标准笔记 | 单次 LLM 调用，适合 15 分钟以内的视频 |
| 详细笔记 | 分段并行处理，适合 20 分钟以上的长视频 |
| 三种平台搜索 | 小红书、B站、YouTube 关键词搜索 |
| 链接自动识别 | 粘贴带文字的分享链接，自动提取 URL |
| PDF 导出 | 排版精美的 PDF 文件下载 |
| 笔记历史 | 自动保存最近 20 条笔记，刷新不丢失 |
| 移动端适配 | iPhone Safari 同 WiFi 直接访问 |

## iPhone 使用

Mac 启动服务后，iPhone 连接同一 WiFi，访问启动时打印的局域网地址：

```
http://192.168.x.x:3000
```

## 常见问题

| 问题 | 解决方法 |
|------|---------|
| Whisper 模型找不到 | 重新下载：`curl -L -o ~/.cache/whisper/tiny.pt [模型地址]` |
| B站搜索无结果 | 确认网络直连（B站 API 不需要代理） |
| 小红书无法使用 | 运行 `xhs login` 重新扫码登录 |
| 笔记生成的是纯转录 | 检查 `~/.claude/settings.json` 配置是否正确 |
| PDF 导出失败 | `brew install weasyprint` |
| 端口被占用 | `lsof -ti:3000 | xargs kill` 然后重新启动 |

## 网络说明（中国大陆用户）

- **B站 API**：直连，不需要代理
- **小红书**：可能需要代理（取决于网络环境）
- **YouTube**：需要代理
- **DeepSeek API**：直连，国产服务
- **Whisper 模型下载**：首次下载可能需要代理，之后永久缓存本地
