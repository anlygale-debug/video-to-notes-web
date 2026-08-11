# Changelog

## 2026-08-11

### 修复

- 区分本地与服务器抖音凭证错误，公网环境不再错误提示用户打开本机 Chrome
- 新增服务器抖音凭证安全刷新工具，仅上传 `douyin.com` 域名 Cookie

## v2.5 — 2026-07-14

### 重大改动

- **视频解析器独立页面**（`static/parser.html`）：首页从笔记生成改为纯视频解析
- **五层管道拆分**：`/api/process` 新增 `stop_at` 参数，转录后自动停下，不再强行生成笔记
- **统一解析器架构**（`app.py`，~250 行新增）：`BaseResolver` 抽象基类 + `YtDlpResolver`（1800+ 平台）+ `XhsResolver`（小红书专用）

### 新功能

- **平台自动识别**：`detect_platform()` 根据 URL 域名自动匹配解析器，无需手动选平台
- **流式视频下载**：`/api/download/{id}/video` 直接流式返回，不落盘，用户不点不占空间
- **视频元数据展示**：封面全宽 → 标题 → 简介 → 原链接 → 作者/平台/时长 → 下载按钮
- **解析历史**：localStorage 存储最近 30 条解析记录，可查看、删除指定条、重新解析
- **三种错误态区分**：非链接（红色）、未知平台（橙色）、正常识别（绿色）
- **B站封面图片代理**：`/api/proxy-image` 绕过防盗链
- **小红书封面提取**：`imageList[0].urlDefault`
- **小红书时长提取**：`capa.duration`

### Bug 修复

- `_read_api_config()` 环境变量 `ANTHROPIC_*` → `VTN_*`，避免与 Claude Code 冲突
- `_basic_notes()` 文案「Groq Whisper large-v3」→「本地 Whisper tiny」
- yt-dlp 简介字段显示 `-` → 空字符串
- 加载态简化为「解析中...」弹跳点动画，移除步骤文字和 spinner 图标
- 平台识别 badge 在解析第一步即时显示，无需等全流程结束
- 前端智能提取 URL（支持从小红书分享文案中自动提取链接）
- 简介区可滚动 + 细条滚动条
- 下载按钮样式统一
- 清理死代码：`PROXY`、`_get_config()`

### 平台测试

| 平台 | 结果 |
|------|:--:|
| 小红书 | ✅ |
| Bilibili | ✅ |
| YouTube | ✅（需代理） |
| 抖音 | ❌ (yt-dlp extractor 已挂） |
| 快手 | ❌ (yt-dlp extractor 已挂） |

### 破坏性变更

- 根路由 `/` 从完整笔记生成页 → 视频解析器页面
- 旧版笔记生成 UI 移到 `/v1`
- 环境变量 `ANTHROPIC_AUTH_TOKEN`/`ANTHROPIC_BASE_URL`/`ANTHROPIC_MODEL` 不再生效，改用 `VTN_API_KEY`/`VTN_API_BASE`/`VTN_MODEL`

---

## 2026-05-23

### 新增

- **音频下载**：处理完成后可下载 `.mp3` 音频文件，保存在 `/tmp/vtn-audio-{id}.mp3`
- **转录文本下载**：下载纯文本 `.txt` 逐字稿
- **笔记+转录合并下载**：单个 `.md` 文件，笔记在前，转录全文在后
- **完整包下载**：`.zip` 包内含笔记 `.md` + 转录 `.txt`
- **转录文本预览**：笔记下方可折叠区域，默认收起，点开展示完整逐字稿

### 修复

- **B站 HTTP 412**：B站 Cookie 认证，`step_resolve`（获取标题）和 `step_download`（下载音频）均已加 Cookie fallback
- **繁体转简体**：转录完成后自动通过 `zhconv` 转换为简体中文
- **标题获取**：B站直达链接现在能正确获取视频标题（之前因缺少 Cookie 导致标题为空）

### 技术细节

- `zhconv` 库用于繁简转换，转录步骤中静默执行，失败不阻塞
- B站下载：优先 `--cookies-from-browser chrome`，失败回退无 Cookie
- 音频文件从临时目录复制到 `/tmp/vtn-audio-{task_id}.mp3` 持久化，任务完成后临时目录仍会清理
- 前端新增 5 个下载按钮：音频、转录文本、笔记+转录、完整包、Markdown/PDF
