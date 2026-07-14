# Video-to-Notes-Web 架构文档

> **版本**: v2.5
> **日期**: 2026-07-09
> **状态**: 生产可用

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [五层处理管道](#3-五层处理管道)
4. [完整数据流（以小红书为例）](#4-完整数据流以小红书为例)
5. [三种笔记生成模式](#5-三种笔记生成模式)
6. [外部依赖地图](#6-外部依赖地图)
7. [API 路由表](#7-api-路由表)
8. [前端架构](#8-前端架构)
9. [文件结构](#9-文件结构)

---

## 1. 项目概述

**Video-to-Notes-Web** 是一个本地 Web 应用，将任意视频链接自动转化为结构化的中文 Markdown 学习笔记。

- **入口**: 浏览器 `http://localhost:3000` 或 macOS 桌面应用
- **后端**: Python FastAPI 单文件 (`app.py`, ~1030 行)
- **前端**: 纯 HTML/CSS/JS 单页面 (`static/index.html`, ~1439 行)
- **设计哲学**: 极简——零数据库、零前端构建、零用户系统

### 支持平台

| 平台     | 搜索 | 下载方式                    | 转录 |
| -------- | :--: | --------------------------- | :--: |
| 小红书   |  ✅  | xhs CLI → CDN 直链 → curl |  ✅  |
| Bilibili |  ✅  | yt-dlp（Chrome Cookie）     |  ✅  |
| YouTube  |  ✅  | yt-dlp                      |  ✅  |
| 纯文本   |  —  | 跳过下载，直接生成笔记      |  —  |

---

## 2. 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                     浏览器 / macOS App                     │
│  static/index.html  ←→  SSE  ←→  FastAPI (app.py)        │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                     触发入口（两种）                        │
│                                                          │
│  ① 浏览器 UI ──▶ POST /api/process ──▶ SSE 事件流        │
│  ② Claude 对话 ──▶ video-to-notes skill ──▶ subprocess   │
│                    (Claude Code 插件)                     │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│                    五层处理管道                            │
│                                                          │
│  ① Search  ──▶ ② Resolve ──▶ ③ Download ──▶ ④ Transcribe│
│                                                  │       │
│                                                  ▼       │
│                                        ⑤ Generate (LLM)  │
│                                           │               │
│                                           ▼               │
│                                    结构化 Markdown 笔记    │
└──────────────────────────────────────────────────────────┘
```

### 核心设计决策

| 决策                       | 原因                                      |
| -------------------------- | ----------------------------------------- |
| 单文件后端                 | 项目规模小，避免过度工程化                |
| subprocess 调外部工具      | 复用已有 CLI（xhs、yt-dlp），不重复造轮子 |
| 内存状态 (`tasks: dict`) | 本地单用户，无需数据库                    |
| SSE 非 WebSocket           | 单向推送进度即可，SSE 实现更简单          |
| 本地 Whisper               | 省钱（免 API 费用）、隐私（音频不出本机） |
| curl 而非 httpx            | 减少依赖，curl 系统自带                   |

---

## 3. 五层处理管道

### ① Search — 视频搜索

```
用户输入关键词
    │
    ├─ 小红书 ──▶ ~/.agent-reach-venv xhs search --json
    │             → 解析 data.items[].note_card → {title, creator, id, likes}
    │
    ├─ B站    ──▶ curl api.bilibili.com 公开搜索 API
    │             → 解析 data.result[] → {bvid, title, author, duration}
    │
    └─ YouTube──▶ yt-dlp --flat-playlist --dump-json ytsearch8:{query}
                  → 解析 {id, title, uploader, duration, like_count}
```

**输出**: `[{id, title, creator, likes, platform, url, duration}]`

> ⚠️ 搜索后端已实现，前端尚未接入（当前仅支持粘贴链接模式）

---

### ② Resolve — 链接解析

**目标**: 获取视频元数据和下载直链。

```
小红书短链 (xhslink.com)
    │
    ├─ curl -sL 追踪重定向 → 提取 note_id + xsec_token
    │
    └─ xhs read {note_id} --xsec-token {token} --json
       → 解析 video.media.stream → 获取 masterUrl (CDN 直链)
       → 解析 title / user.nickname / interact_info.liked_count

B站链接
    │
    └─ yt-dlp --cookies-from-browser chrome --dump-json {url}
       → 提取 title / uploader
       （失败回退无 cookie 模式）

YouTube 链接
    │
    └─ 直接透传 URL（yt-dlp 下载时再解析）
```

**输出**: `{title, creator, likes, download_url, platform}`

---

### ③ Download — 下载与音频提取

```
小红书: curl 下载 CDN 视频 (.mp4)
       → ffmpeg -vn -acodec libmp3lame -q:a 2 → audio.mp3

B站:    yt-dlp -x --audio-format mp3 {url}
       （优先 --cookies-from-browser chrome，失败回退无 cookie）

YouTube: yt-dlp -x --audio-format mp3 {url}
```

**输出**: `/tmp/vtn-{uuid}/audio.mp3`（通常几 MB ~ 几十 MB）

---

### ④ Transcribe — 本地语音转录

```python
# 全局单例，只加载一次
whisper.load_model("tiny")  # ~72MB, 缓存于 ~/.cache/whisper/

model.transcribe(audio_path, fp16=False)
    → zhconv.convert(text, 'zh-cn')  # 繁→简
```

**当前模型**: `tiny`（最快，精度一般）
**可选扩展**: `base` (150MB) / `small` (500MB)（TODO 中计划加入前端选择器）

**输出**: 纯文本字符串（通常几百～几千字）

---

### ⑤ Generate — LLM 结构化为笔记

调用 DeepSeek API（OpenAI 兼容协议）将原始转录文本整理为结构化 Markdown 笔记。

**配置优先级**: 环境变量 > `data/settings.json` > 默认值

```python
# 默认配置
api_base = "https://api.deepseek.com"
model    = "deepseek-chat"
```

详见 [三种笔记生成模式](#5-三种笔记生成模式)。

**可选**: 第二次 LLM 调用插入 Mermaid 图表（`_insert_mermaid()`），再经 `_fix_mermaid_syntax()` 做确定性正则修复。

---

## 4. 完整数据流（以小红书为例）

```
用户粘贴小红书链接
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ ① Resolve: curl 追踪短链 → 提取 note_id + xsec_token     │
│    输入: https://xhslink.com/xxxxx                       │
│    操作: curl -sL 跟随重定向，正则提取 note_id             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ ② Resolve: xhs read API → 从 video.media.stream 取直链   │
│    输入: note_id + xsec_token                            │
│    操作: xhs read {id} --xsec-token {token} --json       │
│    输出: {title, creator, likes, download_url}            │
│          download_url = CDN masterUrl (mp4 直链)          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ ③ Download: curl 下载 .mp4 → ffmpeg 提取 .mp3            │
│    输入: CDN download_url                                │
│    操作: curl -sL -o video.mp4 → ffmpeg 提取音频          │
│    输出: /tmp/vtn-XXXX/audio.mp3                         │
│    清理: 删除 video.mp4（保留音频）                        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ ④ Transcribe: Whisper tiny → 转录文本                    │
│    输入: /tmp/vtn-XXXX/audio.mp3                         │
│    操作: whisper.transcribe() + zhconv 繁→简              │
│    输出: transcript (string, 几百～几千字)                 │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ ⑤ Generate: DeepSeek API → 结构化 Markdown               │
│    输入: transcript + {title, creator, platform, likes}    │
│    模式决策:                                              │
│      transcript ≤ 4000 字 → standard（单次 LLM）          │
│      transcript > 4000 字 → detailed（分块并行）           │
│      scholar 模式 → 详解笔记（叙事段落风格）               │
│    可选: 第二次 LLM 调用插入 Mermaid 图表                  │
│    输出: 结构化 Markdown 笔记                              │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 前端 SSE 实时推送                                         │
│                                                          │
│  event: progress → 更新进条（解析→下载→转录→生成）         │
│  event: complete → 渲染笔记 + 下载按钮                    │
│                                                          │
│  下载选项:                                                │
│    📥 Markdown (.md)     📄 PDF (.pdf)                   │
│    🎵 音频 (.mp3)        📝 转录 (.txt)                  │
│    📋 笔记+转录 (.md)    📦 完整包 (.zip)                │
│                                                          │
│  临时文件 /tmp/vtn-XXXX → 自动清理                        │
│  音频文件 → 持久化到 /tmp/vtn-audio-{task_id}.mp3         │
└─────────────────────────────────────────────────────────┘
```

### 路径二：文本输入模式（跳过 ①-④）

```
用户粘贴文本 + 标题
    │
    ▼
跳过 Resolve / Download / Transcribe
    │
    ▼
⑤ Generate → 直接对文本做结构化 → 输出 Markdown 笔记
```

---

## 5. 三种笔记生成模式

### Standard（标准模式）— 默认

- **适用**: 短视频（< 15 分钟，转录 < 4000 字）
- **方式**: 单次 LLM 调用
- **输出结构**:

```markdown
# 标题 — 课后笔记
> 视频作者 | 平台 | ❤️ 点赞数

## 核心论点
## 内容框架
## 关键概念
## 个人思考
```

### Detailed（详细模式）

- **适用**: 长视频（转录 > 4000 字）
- **方式**: 6000 字分块（300 字重叠）→ 3 线程并行处理 → 直接拼接
- **特点**: 不经过二次合并（节省一次 LLM 调用），每个块独立生成
- **输出结构**: 分块笔记直接拼接，每个块有 ## 小标题

### Scholar（详解模式）

- **适用**: 知识型/课程型深度内容，需要「读完笔记就能替代看视频」
- **方式**:
  - 短文本（≤ 8000 字）：单次 LLM 调用
  - 长文本：分块并行 → 二次总结生成概览 + 术语表
- **输出结构**:

```markdown
# 标题 — 详解笔记
> 视频作者 | 平台 | ❤️ 点赞数

## 本节概览
## 逐节详解
  ### 一、第一个概念
  ### 二、第二个概念
  ...
## 关键术语表
| 术语 | 解释 | 关键表述 |
## 一句话总结
```

- **风格**: 叙事段落而非要点列表，适合 Obsidian 阅读和高亮

---

## 6. 外部依赖地图

```
video-to-notes-web/
    │
    ├─ ~/.agent-reach-venv/          ← 自定义 Python 虚拟环境
    │   ├─ xhs (xiaohongshu-cli)     ← 小红书搜索 / 笔记读取
    │   └─ yt-dlp                     ← B站/YouTube 搜索 + 下载
    │
    ├─ DeepSeek API                   ← LLM 笔记生成 (OpenAI 兼容)
    │   └─ POST {api_base}/chat/completions
    │      model: deepseek-chat
    │      auth: Bearer token
    │
    ├─ OpenAI Whisper (本地)           ← 语音转文字
    │   └─ whisper.load_model("tiny")  ← ~72MB, ~/.cache/whisper/
    │
    ├─ ffmpeg (系统级)                 ← 视频→音频提取
    │
    ├─ curl (系统级)                   ← HTTP 请求（搜索/下载/LLM调用）
    │
    ├─ weasyprint (Homebrew)          ← PDF 导出
    │   └─ /opt/homebrew/bin/weasyprint
    │
    ├─ zhconv (Python 库)             ← 繁体→简体转换
    │
    └─ CDN (前端，仅首次加载)
        ├─ marked.js                   ← Markdown 渲染
        └─ mermaid.js                  ← 图表渲染
```

---

## 7. API 路由表

| 方法     | 路由                              | 说明              | 请求体                                                | 响应                        |
| -------- | --------------------------------- | ----------------- | ----------------------------------------------------- | --------------------------- |
| `GET`  | `/`                             | 前端主页          | —                                                    | `index.html`              |
| `GET`  | `/v2`                           | 前端 v2 版本      | —                                                    | `index-v2.html`           |
| `POST` | `/api/search`                   | 搜索视频          | `{query, platform}`                                 | `{task_id, results[]}`    |
| `POST` | `/api/process`                  | 主处理管道        | `{url, platform, mode, mermaid, title, xsec, text}` | SSE 事件流                  |
| `POST` | `/api/export-pdf`               | 导出 PDF          | `{notes, title}`                                    | PDF 文件                    |
| `GET`  | `/api/download/{id}`            | 下载笔记 .md      | —                                                    | Markdown 文件               |
| `GET`  | `/api/download/{id}/audio`      | 下载音频 .mp3     | —                                                    | MP3 文件                    |
| `GET`  | `/api/download/{id}/transcript` | 下载转录 .txt     | —                                                    | 文本文件                    |
| `GET`  | `/api/download/{id}/merged`     | 下载笔记+转录 .md | —                                                    | Markdown 文件               |
| `GET`  | `/api/download/{id}/full`       | 下载完整包 .zip   | —                                                    | ZIP 文件                    |
| `GET`  | `/api/settings`                 | 读取设置          | —                                                    | `{api_base, model, ...}`  |
| `POST` | `/api/settings`                 | 保存设置          | `{api_key, api_base, model, ...}`                   | `{ok: true}`              |
| `POST` | `/api/test-connection`          | 测试 API 连通性   | `{api_key, api_base, model}`                        | `{ok, latency_ms, model}` |

### SSE 事件类型 (`/api/process`)

```json
// 进度更新
{"event": "progress", "data": {"step": "download", "status": "running", "message": "32MB"}}

// 处理完成
{"event": "complete", "data": {"task_id": "abc123", "notes": "...", "transcript": "...", "meta": {...}}}

// 错误
{"event": "error", "data": "Download failed"}
```

---

## 8. 前端架构

- **文件**: `static/index.html`（单文件，~1439 行）
- **技术栈**: 原生 HTML/CSS/JS，零构建步骤
- **CDN 依赖**: `marked.js`（Markdown 渲染）、`mermaid.js`（图表渲染）
- **设计风格**: 暖色极简——米白底色 (`#faf8f5`) + 暖棕文字 (`#5c5040`)

### 页面结构

```
┌──────────────────────────────────────┐
│ Header: 🎬 Video to Notes + 设置⚙    │
├──────────────────────────────────────┤
│ [URL 输入框________________] [平台▼]  │
│ [文本输入 Tab]                        │
│ 生成模式: ○ 标准 ○ 详细 ○ 详解        │
│ Mermaid 图表: [开关]                  │
│ [开始处理]                            │
├──────────────────────────────────────┤
│ 搜索/历史记录（可折叠）                │
├──────────────────────────────────────┤
│ 进度指示器                            │
│ 解析链接 → 下载音频 → 语音转录 → 生成  │
├──────────────────────────────────────┤
│ 笔记预览（Markdown 渲染）              │
│ [📥下载按钮组]                        │
├──────────────────────────────────────┤
│ 转录文本预览（可折叠）                 │
└──────────────────────────────────────┘
```

### 设置页（全屏浮层）

- API 配置（密钥、Base URL、模型名）
- 连接测试（显示延迟）
- 默认偏好（笔记模式、Mermaid 开关）
- 数据持久化到 `data/settings.json`

### 浏览器本地存储

```
localStorage:
  vtn-history → [{id, title, platform, url, date, notes}, ...]  (最近 20 条)
  vtn-theme  → "light" | "dark"
```

---

## 9. 文件结构

```
video-to-notes-web/
├── app.py                      # FastAPI 后端 (1030 行，单文件)
├── start.sh                    # 一键启动脚本
├── data/
│   └── settings.json           # 用户 API 配置（持久化）
├── static/
│   ├── index.html              # 当前前端 (v3)
│   ├── index-v2.html           # 上一版本前端
│   └── index-v1-backup.html    # 最初版前端（深色模式）
├── docs/
│   ├── ARCHITECTURE.md         # 本文档
│   └── superpowers/
│       ├── plans/              # 实现计划（3 个）
│       └── specs/              # 设计规格（3 个）
├── Video to Notes.app/         # macOS 原生应用包
├── PRD-Video-to-Notes-Web.md   # 产品需求文档
├── CHANGELOG.md                # 更新日志
├── TODO-后续优化.md             # 后续优化清单
├── README.md                   # 英文说明
└── README_zh.md                # 中文说明
```

### 设计文档索引

| 文档                            | 说明                         |
| ------------------------------- | ---------------------------- |
| [PRD](PRD-Video-to-Notes-Web.md) | 产品需求——目标、用户、方案 |
| [CHANGELOG](CHANGELOG.md)        | 版本更新记录                 |
| [TODO](TODO-后续优化.md)         | 后续优化方向与优先级         |
| `docs/superpowers/plans/`     | 各功能实现计划               |
| `docs/superpowers/specs/`     | 各功能设计规格               |

---

## 版本历史

| 版本 | 日期    | 里程碑                                               |
| ---- | ------- | ---------------------------------------------------- |
| v1.0 | 2026-05 | MVP：粘贴链接 → 出笔记，小红书+B站+YouTube          |
| v2.0 | 2026-06 | 前端 v3 UI、三种笔记模式、文本输入、设置页、下载选项 |
| v2.1 | 2026-06 | Mermaid 图表支持 + 确定性语法修复                    |
| v2.2 | 2026-06 | Scholar 详解模式、xhs-cli v2 兼容                    |
| v2.3 | 2026-07 | 设置页重构（全屏浮层）、macOS .app 打包、架构文档    |
