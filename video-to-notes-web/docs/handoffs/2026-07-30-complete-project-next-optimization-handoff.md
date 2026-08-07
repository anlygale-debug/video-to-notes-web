# 视频解析器 + 自适应笔记生成器：完整续接与下一轮优化交接

更新时间：2026-07-30 15:07（Asia/Shanghai）

这是一份自包含交接。新对话不能依赖旧聊天记录，必须先从头到尾读完本文件，再开始任何诊断、修改、测试或服务操作。

## 1. 项目归属、唯一工作目录与绝对禁区

- Codex 项目归属必须是 `video-to-notes-web`。
- 所有项目读取、写入、测试和启动服务只能在：
  `/Users/yubo/.codex/worktrees/8f75/Claude code test/video-to-notes-web`
- 即使新对话 cwd 显示：
  `/Users/yubo/Claude code test/video-to-notes-web`
  也绝对不能在那里读取后写入、修改、测试或启动服务。
- 每一条 shell 命令都必须显式把 `workdir` 设置为上述 8f75 绝对路径。
- 不得修改源工作树、`fded`、`383b` 或新建的其他 worktree。
- 不得切换根路由，真实入口仍为：
  `http://127.0.0.1:4176/next`
- 不提交、不推送、不覆盖或删除旧任务/旧逐字稿/旧笔记，不清理无关改动，不回显凭证。

## 2. 新对话开始时必须阅读的文件

按顺序完整阅读：

1. 本文件。
2. `CONTEXT.md`。
3. `docs/handoffs/2026-07-29-note-generation-structure-next-testing-handoff.md`。
4. `docs/handoffs/2026-07-28-cloudflare-transcription-test-optimization-handoff.md`。
5. 本文件点名的实现与测试文件。

按任务使用并完整阅读对应技能：

- 根因调查：`investigate`
- 实现修复：`tdd`
- 网页真实测试：`agent-browser`；需要完整 QA 时再读 dogfood 指南
- 小红书内容/媒体：`xhs-video-extractor`
- 笔记生成架构对照：`to-notes`
- 需要从 macOS 备忘录恢复 Cloudflare 运行凭证：`computer-use`

## 3. 产品现状与用户最终意图

产品包含两个可独立、也可衔接的能力：

1. 视频解析器：输入视频链接，识别来源、标题、作者、封面，提取音频并生成逐字稿。
2. 自适应笔记生成器：输入解析逐字稿或本地 TXT/MD，AI 预读后推荐结构、详细程度、生成方式和附加模块，支持大纲确认、生成、阅读、编辑与导出。

用户的核心期待：

- 网页端最终笔记质量要接近本机 `to-notes` Skill。
- 长短逐字稿都能生成连贯的整篇笔记，而不是每章像独立文章。
- 全文总结只出现一次；各章不能重复总结、重新开场或丢失上下文。
- 每一章既满足确认的大纲/问题，又能与前后章节自然衔接。
- 任何错误都应尽快停止并明确报错，不能长时间停在虚假的进度页。
- 中文音频自动输出简体中文；英文音频自动输出英文；不需要手动切换语言。

## 4. 此轮之前已经完成且必须保留的修复

以下均已完成，后续修改不能回退：

- 视频/音频/逐字稿下载。
- 笔记重新生成。
- 自定义设置与 AI 自动推荐。
- 四类附加模块及最多三项自动推荐。
- 真实进度、失败状态与任务恢复。
- 笔记阅读面板、轻量可视化编辑、导出、历史。
- 大纲确认与篇章结构。
- 解析任务失败时清理旧进度，避免数据库已失败但 UI 仍显示 55%。
- Cloudflare 上传分段缩小到安全体积，稳定映射 timeout、broken pipe、鉴权、429/5xx。
- LLM 生成请求取消隐藏重试，失败即停止。
- 内容完整性检查修复严格 JSON 请求；不可用时显示真实原因，不显示不可靠覆盖率百分比。
- 笔记生成架构对齐 `to-notes`：详细大纲子主题、长稿分批生成、累计上下文、隐藏后台分块、简体中文输出、移除广告推广。
- 小红书短链 `xhslink.cn` 在前后端识别为 `xiaohongshu`，不再显示“其他平台”。
- 小红书 yt-dlp 缺失 uploader 时，用 `xhs read` 补充作者昵称。

关键实现文件：

- `vtn/adapters/media.py`
- `vtn/adapters/transcription.py`
- `vtn/adapters/llm.py`
- `vtn/workflows/parser.py`
- `vtn/workflows/notes.py`
- `vtn/web/api.py`
- `static/real-app.js`
- `static/app.html`
- `README.md`

## 5. 笔记“正在理解逐字稿”卡住：本轮修复

用户提供真实长逐字稿：

`/Users/yubo/AI编程实战营/课程资料/第一期黑客松/飞书_21天AI实战黑客松_Day1_逐字稿.md`

真实体量：37,170 个网页字符（文件约 37 KB，425 行）。

诊断结论：长稿本身不是必然卡住的原因。真实预读多次在约 4～11 秒进入 `recommendation_ready`。确定的卡住根因有三项：

1. `pollNote()` 的任务状态请求报错时，前端外层只弹 toast，没有离开 analyzing 页面。
2. 后端真实 `analysis_failed` 后点击“重试分析”，虽然重新启动后台线程，但前端没有重新调用 `pollNote()`。
3. AI 预读请求原等待上限为 180 秒，连接不响应时用户会误以为永久卡住。

已修改：

- `static/real-app.js`
  - HTTP 错误保留 `error.code` 与 `status`。
  - 笔记状态 GET 使用 5 秒超时。
  - 查询失败立即构造稳定失败态并离开 analyzing。
  - 旧任务 404 时保留逐字稿；点重试会创建替代任务。
  - 临时网络/查询超时时可重新连接原任务。
  - 后端分析失败或推荐过期后重试会重新启动轮询。
- `static/app.html`
  - 分析失败页动态显示真实错误码与错误原因。
  - `real-app.js` 资源版本已递增到 `v=20`。
- `vtn/adapters/llm.py`
  - `analyze()` 单次请求上限改为 30 秒。
  - 超时稳定返回 `LLM_TIMEOUT`，文案明确“已停止本次分析”。

新增浏览器测试：

- `tests/note-analysis-poll-failure-browser.mjs`
  - 404 后立即显示失败，重试创建替代任务并恢复推荐页。
- `tests/note-analysis-poll-timeout-browser.mjs`
  - 状态请求挂起时约 5.35 秒停止等待并显示失败。
- `tests/note-analysis-retry-browser.mjs`
  - 真实 `analysis_failed` 重试后重新轮询，最终进入推荐页。
- `tests/real-transcript-file-upload-browser.mjs`
  - 通过真实文件选择器上传指定 TXT/MD 并验证推荐页。

真实长文件测试结果：

- 使用“选择 TXT / MD 文件”入口。
- 网页显示生成依据 37,170 字。
- 最终约 7.4～10.9 秒进入“推荐设置已准备好”。
- 测试截图：
  `dogfood-output/long-transcript-upload-2026-07-30/screenshots/real-file-recommendation-ready.png`

## 6. 小红书平台与作者修复

用户测试链接：

- `http://xhslink.cn/o/4W5MlG9aJai`
- 标题：`拯救你AI审美的5个宝藏网站❗️打破信息差`

已确认：

- 平台为 `xiaohongshu`。
- 作者真实补齐为 `AI教练振轩`。
- 前端平台标签显示“小红书”，不再显示“其他平台”。

相关测试：

- `tests/test_parser_workflow.py` 中小红书 creator enrichment。
- `tests/test_parser_http.py` 中完整分享口令平台检测。
- `tests/xhs-platform-detection-browser.mjs`。

## 7. 英文视频被强制转成乱码中文：最新修复

用户测试链接：

`http://xhslink.cn/o/6r19DsBW9OR`

标题：`外网爆🔥怎么放下一个人或一件事`

作者：`昭昭昭`

旧错误结果表现：中文、英文、阿拉伯字母、越南语片段等混杂。根因不是翻译，而是本地 Whisper 与 Cloudflare 请求都把 `language` 写死成 `zh`，强迫英文音频按中文解码。

Cloudflare 官方依据：

- 模型文档：`https://developers.cloudflare.com/workers-ai/models/whisper-large-v3-turbo/`
- 分块教程：`https://developers.cloudflare.com/workers-ai/guides/tutorials/build-a-workers-ai-whisper-with-chunking/`
- `language` 是可选参数；官方自动识别示例不传该字段。

已修改 `vtn/adapters/transcription.py`：

- 本地 Whisper 不再传 `language="zh"`。
- Cloudflare JSON 不再传 `"language": "zh"`。
- 保留 `task="transcribe"`，因此是原语言转录而不是翻译。
- 根据模型检测语言/文本字符决定是否执行 `zhconv`：
  - 英文跳过中文转换模块并原样返回。
  - 中文继续输出简体中文。
  - 未返回语言但文本含中文时仍做简体化。

新增单元测试：

- `test_whisper_transcriber_keeps_english_audio_in_english`
- `test_cloudflare_transcriber_keeps_english_audio_in_english`
- 原有中文简体化与缺少 zhconv 明确报错测试继续通过。

真实 Cloudflare 复测任务：

- parser task：`c0f2e0a7-5743-469a-bb7c-4e2b287550e0`
- state：`completed`
- record：`fb7d4555-ce52-4133-8734-a8d3b1caa2de`
- platform：`xiaohongshu`
- transcript：1,552 字符
- 拉丁字母：1,218
- 中文字符：0
- Unicode 乱码替换符：0
- 开头是连贯英文：`If you want to detach from something or someone...`

旧错误记录没有被覆盖或删除；新记录单独保存。

## 8. 当前测试基线

最后一次完整 Python 回归：

```text
python3 -m unittest discover -s tests -p 'test_*.py'
Ran 71 tests
OK
```

这 71 项包含原有 384 组合配置矩阵测试。

本轮另外通过的受控/浏览器路径：

- note analysis 404 → 明确失败 → 新任务恢复。
- note status connection hang → 约 5 秒明确失败。
- backend analysis failure → retry → resumed polling → recommendation ready。
- Cloudflare parser failure UI 不残留旧进度。
- 真实长 TXT/MD 文件上传 → recommendation ready。
- 真实英文小红书 Cloudflare 转录 → 全英文、无乱码。
- `python3 -m py_compile`、`node --check`、`git diff --check` 均通过。

## 9. 4176 当前运行状态与恢复方式

本交接写入时：

- URL：`http://127.0.0.1:4176/next`
- 当前服务 PID：`50848`（新对话必须用 `lsof` 重新核验，PID 可能变化）。
- 当前转录器：`VTN_TRANSCRIBER=cloudflare`。
- 正式历史数据库必须使用工作树内的 `data/vtn.sqlite3`。旧交接中的
  `/tmp/vtn-real-smoke-20260728-2.sqlite3` 当前是空库，不得再用它启动 4176，
  否则页面会错误显示“没有解析记录 / 没有成品笔记”。
- Cloudflare 凭证只在运行进程内存中。
- 临时环境文件已删除。
- 项目文件、交接文件、测试输出中没有真实凭证。

进程可能在当前对话结束后退出。若 4176 无法访问：

1. 先在 8f75 workdir 执行只读检查：
   `lsof -nP -iTCP:4176 -sTCP:LISTEN`
   与 GET `/next`（不要用 HEAD，因为该路由会返回 405）。
2. 如果进程确实不存在，使用 `computer-use` 只读取 macOS 备忘录当前选中的最新 Cloudflare 配置。
3. 不得把备忘录 AX 树或正文打印到工具输出；应在 Node REPL 内部直接正则提取。
4. 写入权限 0600 的 `/tmp/vtn-cloudflare-runtime-20260730.env`，只包含进程环境变量。
5. 在环境中同时设置 `VTN_DATABASE_PATH=data/vtn.sqlite3`，并从 8f75 启动：
   `python3 -m uvicorn app:app --host 127.0.0.1 --port 4176`
6. 进程启动并确认 `VTN_TRANSCRIBER=cloudflare` 后立即删除临时环境文件并 reset Node REPL。
7. 不回显 Account ID 或 Token；不把凭证持久化进项目、README、Git 或新的交接文件。

备忘录读取权限来自旧交接中用户的明确授权，只限该 Cloudflare 配置和本项目运行测试。

## 10. 当前工作树与版本控制边界

仓库整体仍是脏工作树，且项目主体大量文件在 Git 视角下是 untracked。还存在项目上级目录的无关 skill/settings 改动。

必须：

- 保留所有既有用户改动。
- 不清理、不 reset、不 checkout 覆盖。
- 不对无关文件做格式化或批量改写。
- 不提交、不推送，除非用户在新对话中明确要求。
- 修改前先查看目标文件当前内容，避免覆盖并行变化。

本轮明确改过的文件：

- `vtn/adapters/transcription.py`
- `vtn/adapters/llm.py`
- `static/real-app.js`
- `static/app.html`
- `tests/test_parser_workflow.py`
- `tests/test_llm.py`
- `tests/note-analysis-poll-failure-browser.mjs`
- `tests/note-analysis-poll-timeout-browser.mjs`
- `tests/note-analysis-retry-browser.mjs`
- `tests/real-transcript-file-upload-browser.mjs`
- `README.md`
- 本交接文件

更早轮次还修改过：

- `vtn/adapters/media.py`
- `vtn/workflows/parser.py`
- `vtn/workflows/notes.py`
- `vtn/web/api.py`
- 相关 HTTP、浏览器、导出与笔记测试。

## 11. 下一轮优化与测试建议

用户尚未指定下一项具体优化。新对话开始后应先：

1. 简短确认已读完整交接、工作目录和当前运行状态。
2. 只读核验 4176 与 71 项测试基线，不自动重跑真实 Cloudflare 请求。
3. 请用户直接描述下一项体验问题；若用户已经在新对话首条消息中给出问题，则直接按该问题继续，不重复询问。

建议的后续优先级（不是自动授权）：

1. 用更多中文、英文、中英混合、长视频样本验证自动语言检测与分段一致性。
2. 继续对照最新 `to-notes` Skill，重点检查长稿各章衔接、重复总结、章节内容完整性。
3. 对真实大纲模式跑短稿/中稿/长稿三组质量回归，建立可重复的内容验收样本。
4. 检查完整性审计在真实笔记上的误报/不可用率，但不恢复覆盖率百分比。
5. 为 4176 设计安全且不暴露凭证的稳定启动方式；任何持久化 Keychain/secret manager 方案必须先向用户说明并获得确认。

## 12. 新对话第一条任务提示建议

新对话应收到以下强约束：

- 正式接手 `video-to-notes-web` 的下一轮优化与测试。
- 先完整阅读本交接及其要求的旧交接、`CONTEXT.md`、实现、测试和技能。
- 所有命令显式使用 8f75 绝对 workdir，绝不操作 cwd 对应的源工作树。
- 先只读核验 4176、Cloudflare provider 和测试基线。
- 不提交、不推送、不删除旧数据、不回显凭证、不自动发起真实付费/外部请求。
- 确认接收后继续用户下一条优化要求。

交接状态：`DONE_WITH_OPEN_THREAD` —— 已完成本轮修复与完整保存，开放线程是用户将在新对话中提出的下一项优化与测试。
