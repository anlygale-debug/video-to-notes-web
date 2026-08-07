# 视频解析器 + 自适应笔记生成器：笔记结构修复后续测试交接

时间：2026-07-29（Asia/Shanghai）

## 1. 接手方式与唯一工作目录

这是给全新对话使用的自包含交接。不要依赖旧对话历史。

唯一允许工作的目录：

`/Users/yubo/.codex/worktrees/8f75/Claude code test/video-to-notes-web`

新对话默认 cwd 可能是源工作树或其他临时目录。所有读取、编辑、测试、服务命令必须显式使用上面的绝对路径或把 `workdir` 指向它。不得修改：

- `/Users/yubo/Claude code test/video-to-notes-web`
- `/Users/yubo/.codex/worktrees/fded/Claude code test/video-to-notes-web`

开始前完整阅读：

1. 本文件。
2. `CONTEXT.md`。
3. `docs/handoffs/2026-07-28-cloudflare-transcription-test-optimization-handoff.md`。
4. 本文件下方列出的实现与测试文件。
5. 与下一项具体测试相匹配的技能说明。

## 2. 用户现在要做什么

用户明确要求把后续测试放到新对话，原因是原对话已经很卡。新对话应先只读核验本交接和 4176 服务，然后用简短中文告诉用户已接手、页面地址和当前基线，等待用户提出下一项具体现象或测试指令。

页面地址：

`http://127.0.0.1:4176/next`

不要在接手后自行重做已经完成的修复或重新跑真实 AI。用户下一条具体测试指令到来后再行动。

## 3. 当前运行状态

- 4176 正在监听，最近一次启动 PID 为 `95601`。
- 启动目录是唯一允许的 8f75 工作树。
- 数据库：`/tmp/vtn-real-smoke-20260728-2.sqlite3`。
- 转录器：Cloudflare Workers AI。
- 页面静态资源版本：`app.css?v=13`、`real-app.js?v=13`。
- 4175 测试服务已经停止，不应残留监听。
- 当前对话最后一次没有调用真实 Cloudflare 转录，也没有调用真实笔记 AI。
- 没有提交、没有推送、没有覆盖或删除任何旧笔记/逐字稿。

只读核验命令：

```bash
lsof -nP -iTCP:4176 -sTCP:LISTEN
curl -sS http://127.0.0.1:4176/next | rg -o 'app\.css\?v=[0-9]+|real-app\.js\?v=[0-9]+'
lsof -nP -iTCP:4175 -sTCP:LISTEN
```

## 4. 凭证与安全边界

- 真实 Cloudflare Account ID/Token 只存在于用户 macOS 备忘录最新一条，本交接不包含密钥。
- 用户已授权：只读该目标备忘录，并把凭证仅用于本项目 Cloudflare Workers AI 测试。
- 禁止回显、写入代码/Git/普通日志或长期文件。
- 4176 已在进程内存持有凭证；不必要时不要重启。
- 如确实必须重启，完整阅读并遵守 `computer-use` 技能，使用 `node_repl + @oai/sky` 读取 Notes；只把凭证写入 0600 临时环境文件，进程启动后立即删除并清空 REPL 变量。
- 不切根路由；应用入口仍是 `/next`。
- 不删除真实数据，不覆盖已有真实逐字稿或笔记。

## 5. 本轮之前已经完成的产品修复

这些功能已经修过，不要重做，除非用户给出新的可复现证据：

1. 视频/音频浏览器下载：点击后使用浏览器下载，不依赖网页本地缓存。
2. 成品笔记可以点击“重新生成整份笔记”，复用生成依据但保存为独立新笔记。
3. 自定义生成不再跳回推荐页；推荐与自定义共用同一个持久化生成方案。
4. 自动推荐基于当前逐字稿分析，不再使用原型固定问题。
5. 附加模块收敛为 4 项：核心摘要、关键概念、实践提炼、复习问题；推荐最多 3 项，用户最多 4 项。
6. 大纲章节进度和右侧说明绑定真实完成数量、当前篇章及状态。
7. 章节失败页绑定真实失败篇章和尝试次数，不再固定显示“第三章”。
8. 阅读面板已清洗常见 Markdown 符号并优化概述、正文、目录和附加模块样式。

## 6. 用户提供的严重结构问题及根因

用户提供过两份真实导出文件，只读分析过，绝不能修改：

- `/Users/yubo/Downloads/亲密关系中的控制欲：成因与应对.md`
- `/Users/yubo/Downloads/亲密关系中的控制欲：成因与应对 (1).md`

两份旧文件的现象：真实篇章没有成为 H2；`核心摘要`、`正文` 被模型反复输出成标题。新文件中这类包装标题重复约 7 次。

根因不是单一提示词，而是旧架构把整份 Markdown 结构交给每章模型自由生成：

- 每章都收到整份方案、模块、完整大纲和逐字稿。
- 每章生成结果直接拼接，没有程序生成的确定性篇章外壳。
- 附加模块在每章重复生成。
- 旧章节摘要直接截取 Markdown，污染后续上下文。
- 完整性检查调用失败时曾被错误记录为 `ok`。
- 导出器曾把来源信息和逐字稿也追加为 H2。

## 7. 已完成的结构性修复

核心原则：**程序拥有文档结构，模型只生成内容。**

### 确定性组合器

新增 `vtn/documents/composer.py` 的 `NoteMarkdownComposer`：

- 成品永远只有一个 H1（文档标题）。
- H2 只能来自直接生成返回的结构化篇章，或用户确认的大纲篇章。
- 模型返回的篇章标题、`正文`、重复摘要、附加模块包装标题会被剥离。
- 模型内部标题统一降为 H3 及以下。
- 核心摘要只出现一次，使用引用式概述而不是篇章标题。
- 其他附加模块使用 `复习增强｜模块名` 标签，不占用 H2。
- Mermaid 源码会转换为可读的文字关系，避免把源码暴露给用户。
- 大纲标题重复、篇章不一致、空正文、已选模块缺失都会明确失败，不能生成假成功笔记。
- 模型给附加模块多包一层同名标题时会宽容解包，不会误判为空。

### 生成流程

`vtn/adapters/llm.py` 和 `vtn/workflows/notes.py` 已改为：

- 直接生成返回严格 JSON：`chapters[] + supplements{}`，不再返回自由形态整份 Markdown。
- 大纲模式每次只生成当前篇章的正文和干净的上下文摘要。
- 所有正文篇章完成后，附加模块只统一生成一次。
- 无效重复大纲在进入确认页之前被拦截。
- 完整性检查不可用时记录 `check_unavailable`，不再伪装为 `ok`。
- 每个结构、详细程度、生成方式、附加模块组合都走同一结构契约。

### 阅读与导出

- `static/real-app.js` 能提取新的引用式核心摘要。
- `复习增强｜关键概念/实践提炼/复习问题` 独立显示为模块卡片，不会并入最后一章。
- 完成页根据真实 integrity 状态显示：通过、可能遗漏、检查暂不可用。
- `vtn/exports/exporter.py` 把来源和逐字稿标为附录粗体标签，不再制造额外 H2。
- 接受“重新生成本章”候选时仍保持原 H2 篇章契约。

主要实现文件：

- `vtn/documents/composer.py`
- `vtn/documents/__init__.py`
- `vtn/adapters/llm.py`
- `vtn/workflows/notes.py`
- `vtn/documents/notes.py`
- `vtn/exports/exporter.py`
- `static/real-app.js`
- `static/app.html`
- `static/app.css`

## 8. 已通过的验证

### Python

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

结果：`Ran 51 tests ... OK`。

其中包含完整配置矩阵：

- 4 种正文结构
- 3 种详细程度
- 2 种生成方式
- 4 个附加模块的全部 16 种子集
- 合计 384 个设置组合，全部保持一个 H1、唯一且正确的 H2 篇章、无包装标题重复。

### 浏览器

已通过：

- `tests/e2e-browser.mjs`：推荐/自定义、直接/大纲以及 27 个验收状态。
- `tests/boundary-browser.mjs`：PDF、候选章节、恢复、非级联删除、迁移。
- `tests/note-reading-browser.mjs`：2 个正文篇章、2 个独立附加模块、Markdown 符号清洗。
- `tests/note-regeneration-browser.mjs`：旧笔记保留，新笔记独立生成，新需求生效。
- `tests/adaptive-note-settings-browser.mjs`：真实自定义方案持久化。
- `tests/runtime-data-browser.mjs`：直接生成进度和完成回执使用真实运行数据。
- `tests/chapter-progress-browser.mjs`：进度依次出现 0/3、1/3、2/3；右侧当前标题与左侧同步。
- `tests/chapter-failure-browser.mjs`：首章失败显示第 1 章，第二次尝试显示真实次数。

## 9. 当前文件状态

- 工作树原本就很脏，大量文件未跟踪或有用户改动。
- 不要清理、重置、覆盖无关改动。
- 没有 commit/push，用户也没有要求。
- 最后 `git diff --check` 通过，`node --check static/real-app.js` 通过。

重点测试文件：

- `tests/test_note_workflow.py`
- `tests/test_note_document_export.py`
- `tests/test_llm.py`
- `tests/note-reading-browser.mjs`
- `tests/runtime-data-browser.mjs`
- `tests/chapter-progress-browser.mjs`
- `tests/chapter-failure-browser.mjs`

## 10. 新对话第一条回复建议

完成只读核验后，简短告诉用户：

> 已接手。网页地址是 http://127.0.0.1:4176/next，4176 当前正常运行，笔记结构修复与 51 项单元测试、全部关键浏览器路径已经通过。你可以直接在浏览器继续测试；把下一个具体问题告诉我，我会只在 8f75 工作树处理。

然后等待用户给出下一项具体测试或问题。不要自行调用真实 AI，不要重启 4176，不要修改代码。

## 11. 交接后出现的新问题：Cloudflare 转录上传失败

用户随后测试了这个视频：

`https://www.bilibili.com/video/BV1zR4xzRECc?vd_source=eead6df7744cee5494396b8478260e72`

BVID：`BV1zR4xzRECc`。

用户看到页面一直卡在“转成逐字稿”。无项目诊断任务 `019fab9e-12ee-7ca1-a5cd-f9dac2de1caf` 已完成只读调查，结论如下：

- 对应最近解析任务 ID 前缀：`69d96296…`。
- 后端任务实际状态已经是 `failed`，并不是仍在运行。
- 没有任何 `resolving`、`downloading`、`transcribing` 或 `retrying` 状态的任务。
- 第一次转录失败错误：`Broken pipe`。
- 用户重试后第二次仍在转录阶段失败：`The write operation timed out`。
- 两次失败都没有收到 Cloudflare HTTP 响应，因此失败点位于音频上传/请求写入阶段。
- 不是 Bilibili 下载失败，不是逐字稿保存失败，也不是前端轮询仍有真实后端任务。
- 4176 进程、唯一 8f75 工作目录和数据库均正确。
- 诊断时没有 Cloudflare、ffmpeg、yt-dlp 活动连接，也没有遗留临时音频目录。
- 当前实现把音频按 600 秒切段，并以 Base64 JSON 上传；这个视频的分段在 180 秒请求窗口内发生写入超时。
- 数据库虽已保存 `state=failed`，但 `progress` 仍残留 `transcribe / 55%`，导致页面视觉上像持续卡住。

诊断过程没有重启 4176，没有重新提交任务，没有调用新的真实 Cloudflare 转录，也没有删除或覆盖数据。

下一步修复范围已经明确，但尚未执行：

1. 缩小 Cloudflare 单段上传体积（用测试确定安全切段时长/字节上限，避免再次猜固定值）。
2. 为上传写入超时与 `Broken pipe` 增加稳定、可理解的错误码和可重试语义。
3. 任务进入 `failed` 后同步清理或覆盖旧 `progress`，前端必须显示失败态，不能继续显示 55% 转录中。
4. 先用 mock/受控失败测试验证，不要直接重复真实调用。
5. 真实重试前必须再次核验不会覆盖旧逐字稿或创建重复记录，并明确告知用户将产生一次真实 Cloudflare 调用。

新项目任务接手后应先向用户复述以上结论，并等待用户确认开始修复；不要重复调查已经确认的 Bilibili 下载和前端轮询问题。
