# 视频解析器 + 自适应笔记生成器：技术规格

> 日期：2026-07-27
> 状态：用户已于 2026-07-27 确认；Ticket 包已确认；尚未开始实现
> UI 合同：`prototype-phase1-video-parser/`，已于 2026-07-27 完成最终点击验收并锁定
> 验收记录：`docs/handoffs/2026-07-27-adaptive-notes-ui-final-acceptance.md`

## 1. 目标

把已经锁定的四阶段假数据原型实现为本地可真实使用的桌面网页：

1. 视频解析器可以独立完成链接识别、元信息读取、音频提取、Whisper 转录、逐字稿保存和按需下载。
2. 自适应笔记生成器可以独立接收粘贴文本或 TXT/MD 文件，也可以接收解析器带入的逐字稿。
3. AI 先预读逐字稿和本次笔记需求，再给出标题与四项推荐设置。
4. 快速生成和大纲确认必须走不同的前台流程；后台分块不能改变用户选择的流程。
5. 任务、历史、生成依据、成品和版本使用本地持久存储，刷新或关闭标签页后可以恢复。
6. 成品笔记支持同页轻量可视化编辑、自动保存、单章候选、Markdown/PDF/复制导出。
7. 真实页面必须逐状态匹配已锁定 UI 合同。

## 2. 非目标

本阶段不包含：

- 公开服务器部署、账号、登录、跨设备同步。
- 手机端 App 或完整移动端适配。
- 多人协作、评论、复杂块编辑器。
- Word、Notion、Obsidian 或第三方同步。
- 视频、音频长期存储。
- 回收站、批量永久删除。
- AI 模型质量评测平台。
- 搜索视频入口；现有搜索实现保留为兼容能力，但不进入锁定的一级流程。

## 3. 当前实现事实与迁移约束

当前真实应用是单文件 FastAPI 后端 `app.py` 与原生 HTML/CSS/JS 页面：

- `/` 返回 `static/parser.html`。
- `/v1` 返回旧笔记页 `static/index.html`。
- `POST /api/process` 同时承担解析、下载、转录和笔记生成，并以 POST 响应体持续输出 SSE。
- 即使 `stop_at="transcribe"`，接口也会先检查 LLM 配置，导致视频解析器不能真正独立。
- 任务状态只存在进程内 `tasks: dict`；服务重启即丢失。
- 解析历史和笔记历史分别存在浏览器 `localStorage`。
- 下载接口依赖仍在内存中的 `task_id`。
- 外部命令存在字符串拼接和 `shell=True`，需要在迁移时消除命令注入风险。
- PDF 由 WeasyPrint 生成；Markdown、Whisper、yt-dlp、xhs CLI、ffmpeg 已经存在。

迁移必须复用已经稳定的平台解析、Whisper、LLM 调用和导出能力，但不能继续把所有行为放在一个浅层路由函数中。

## 4. 总体架构决策

### 4.1 运行形态

- 保持 Python FastAPI + 本地静态网页。
- 默认只绑定 `127.0.0.1`。
- 不引入账号系统。
- 前端继续使用原生 HTML/CSS/ES Modules，不增加 React/Vue 构建链。
- SQLite 使用 Python 标准库 `sqlite3`，数据库文件为 `data/vtn.sqlite3`。
- 后台任务继续在本地进程执行，但状态与事件先写入 SQLite，再通知浏览器。

### 4.2 深模块与 seam

系统由六个深模块组成：

```text
Browser
  │
  ▼
HTTP + SSE adapter
  │
  ├── ParserWorkflow
  ├── NoteWorkflow
  ├── NoteDocument
  ├── Exporter
  └── HistoryQuery
          │
          ▼
    SQLiteRepository

ParserWorkflow adapters:
  PlatformMedia / Transcriber

NoteWorkflow adapters:
  LLM / Clock
```

模块定义：

- **ParserWorkflow**：隐藏平台识别、解析、临时媒体、Whisper、重试、记录保存和事件发布。
- **NoteWorkflow**：隐藏预读、推荐、设置、大纲、生成分支、章节恢复、完整性检查和单章候选。
- **NoteDocument**：隐藏 Markdown 与可视化编辑 DOM 的转换、自动保存、乐观并发和版本恢复。
- **Exporter**：隐藏 Markdown/PDF/复制内容组合、来源附加和文件名处理。
- **HistoryQuery**：一次返回 UI 需要的解析历史、笔记历史和双向关联投影。
- **SQLiteRepository**：隐藏事务、表结构、游标分页和事件序号。

外部 seam 与 adapter：

- `PlatformMedia`：生产 adapter 使用 xhs CLI、yt-dlp、curl/urllib、ffmpeg；测试 adapter 使用固定媒体 fixture。
- `Transcriber`：生产 adapter 使用本地 Whisper；测试 adapter 返回固定逐字稿。
- `LLM`：生产 adapter 使用 OpenAI 兼容接口；测试 adapter 返回固定结构化结果。
- `Clock`：生产 adapter 返回 UTC 时间；测试 adapter 固定时间，保证截图和状态测试稳定。

所有调用者和自动化测试通过模块 interface 验证行为，不直接读写 SQLite 表或模块内部状态。

## 5. 建议目录结构

```text
app.py                         # 只负责装配 FastAPI、adapter 与启动
vtn/
  domain/
    models.py                  # 枚举、值对象、不可变结果
    errors.py                  # 稳定错误码
  workflows/
    parser.py                  # ParserWorkflow
    notes.py                   # NoteWorkflow
  documents/
    notes.py                   # NoteDocument 服务端规则
  exports/
    exporter.py                # Markdown/PDF 内容组合
  storage/
    sqlite.py                  # SQLiteRepository
    schema.sql
    migrations.py
  adapters/
    media.py
    transcription.py
    llm.py
    pdf.py
  web/
    parser_routes.py
    note_routes.py
    history_routes.py
    settings_routes.py
    events.py
static/
  app.html
  css/
    tokens.css                 # 从 UI 合同提取，不重新设计
    components.css
    pages.css
  js/
    main.js
    app-state.js
    workflow-client.js
    parser-view.js
    notes-view.js
    note-document.js
    dialogs.js
  vendor/
    marked.min.js
    dompurify.min.js
    turndown.min.js
    mermaid.min.js
tests/
  unit/
  integration/
  e2e/
  visual/
```

`app.py` 不再包含业务实现。它创建 repository、生产 adapters、两个 workflow 模块和 HTTP adapter。

## 6. 领域对象与所有权

### 6.1 解析任务

一次视频解析执行。拥有进度、错误、重试次数和临时执行信息；成功后产生一条解析记录。

不拥有长期视频或音频文件。

### 6.2 解析记录

视频解析器历史中的持久结果。拥有：

- 原始链接。
- 平台、标题、作者、简介、时长、封面 URL。
- 解析侧逐字稿副本。
- 创建与更新时间。

删除解析记录时删除该侧逐字稿和关联关系，但不删除成品笔记或笔记侧生成依据逐字稿。

### 6.3 笔记任务

从输入到成品的持久工作流。拥有：

- 来源类型与来源快照。
- 生成依据逐字稿。
- 本次笔记需求。
- AI 推荐设置、最终设置、大纲。
- 当前状态、失败信息、章节进度和上下文摘要。
- 生成出的成品笔记引用。

### 6.4 成品笔记

已经生成、可阅读和编辑的知识内容。拥有：

- 笔记标题。
- AI 初始版本。
- 当前编辑版本。
- 内容完整性检查结果。
- 单章候选。
- 导出所需的来源快照。

### 6.5 关联关系

解析记录与笔记任务之间只通过关联关系连接。关系本身不拥有逐字稿。删除任一侧只删除关系，不级联删除另一侧。

## 7. 数据模型

SQLite 配置：

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
```

时间统一保存为 UTC ISO-8601；展示时由前端转换为本地时区。ID 使用 UUID4 字符串。

### 7.1 `parser_tasks`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | 任务 ID |
| device_id | TEXT | 当前浏览器本地标识 |
| source_url | TEXT | 用户提交的链接 |
| platform_hint | TEXT | 提交时识别结果 |
| state | TEXT | 解析状态 |
| progress_json | TEXT | 当前语义进度 |
| error_code | TEXT NULL | 稳定错误码 |
| error_message | TEXT NULL | 用户可读错误 |
| retry_count | INTEGER | 自动/手动重试次数 |
| record_id | TEXT NULL | 成功后产生的记录 |
| created_at / updated_at | TEXT | 时间 |

### 7.2 `parser_records`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | 解析记录 ID |
| source_url | TEXT | 原链接 |
| platform | TEXT | xiaohongshu/bilibili/youtube/other |
| title / creator / description | TEXT | 来源元信息 |
| duration_seconds | INTEGER | 视频时长 |
| thumbnail_url | TEXT | 封面地址；失败可为空 |
| transcript_text | TEXT | 解析侧逐字稿副本 |
| transcript_format_version | INTEGER | 文本格式迁移版本 |
| created_at / updated_at | TEXT | 时间 |

不保存视频和音频路径。

### 7.3 `note_tasks`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | 笔记任务 ID |
| device_id | TEXT | 同浏览器恢复标识 |
| state | TEXT | 当前工作流状态 |
| source_type | TEXT | parser/paste/file |
| source_name | TEXT | 视频标题或文件名 |
| source_snapshot_json | TEXT | 来源元信息不可变快照 |
| basis_transcript | TEXT | 笔记侧生成依据逐字稿 |
| transcript_revision | INTEGER | 修改次数 |
| request_text | TEXT | 本次笔记需求 |
| proposed_title | TEXT | AI 拟定或用户修改标题 |
| recommendation_json | TEXT NULL | AI 推荐 |
| recommendation_revision | INTEGER NULL | 推荐基于哪个逐字稿版本 |
| final_settings_json | TEXT NULL | 最终设置 |
| outline_json | TEXT NULL | 只读大纲 |
| outline_feedback | TEXT NULL | 最近一次重拟要求 |
| progress_json | TEXT | 当前语义/章节进度 |
| error_code / error_message | TEXT NULL | 失败信息 |
| note_id | TEXT NULL | 完成后的成品 |
| created_at / updated_at | TEXT | 时间 |

`recommendation_revision != transcript_revision` 时，任务必须显示“推荐过期”，不能开始生成。

### 7.4 `note_chapters`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | 章节 ID |
| task_id | TEXT FK | 所属笔记任务 |
| position | INTEGER | 大纲顺序 |
| title | TEXT | 章节标题 |
| status | TEXT | waiting/running/complete/failed |
| content_md | TEXT | 已保存章节 |
| context_summary | TEXT | 供后续章节续写 |
| attempt_count | INTEGER | 尝试次数 |

章节失败不得覆盖已经 `complete` 的行。

### 7.5 `notes`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | 成品 ID |
| task_id | TEXT UNIQUE FK | 来源任务 |
| title | TEXT | 当前标题 |
| current_markdown | TEXT | 当前编辑版本 |
| version | INTEGER | 乐观并发版本 |
| integrity_json | TEXT | 完整性检查结果 |
| source_snapshot_json | TEXT | 导出所需来源快照 |
| basis_transcript | TEXT | 独立副本 |
| created_at / updated_at | TEXT | 时间 |

### 7.6 `note_versions`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | 版本 ID |
| note_id | TEXT FK | 所属笔记 |
| kind | TEXT | ai_initial/user_checkpoint/before_restore/candidate_accept |
| title | TEXT | 当时标题 |
| markdown | TEXT | 当时全文 |
| created_at | TEXT | 时间 |

AI 初始版本创建后不可修改。当前版本直接保存在 `notes`；编辑会话结束、恢复前和候选替换前创建检查点，避免每次按键生成版本。

### 7.7 `chapter_candidates`

保存待用户决定的单章候选：

- `note_id`
- `chapter_id`
- `current_chapter_markdown`
- `candidate_markdown`
- `status`: pending/accepted/rejected
- `created_at`

同一章节同时最多有一个 `pending` 候选。

### 7.8 `parse_note_links`

```sql
parse_record_id TEXT REFERENCES parser_records(id) ON DELETE CASCADE
note_task_id    TEXT REFERENCES note_tasks(id) ON DELETE CASCADE
PRIMARY KEY (parse_record_id, note_task_id)
```

级联只删除关联行，不删除两侧实体。

### 7.9 `workflow_events`

| 字段 | 类型 | 说明 |
|---|---|---|
| workflow_type | TEXT | parser/note |
| task_id | TEXT | 任务 ID |
| seq | INTEGER | 任务内单调递增 |
| event_type | TEXT | state/progress/error/complete |
| payload_json | TEXT | 前端投影 |
| created_at | TEXT | 时间 |

主键为 `(workflow_type, task_id, seq)`。事件保留 30 天；任务和成品状态不依赖事件重建。

## 8. 状态机

### 8.1 解析任务状态

```text
created
  → resolving
  → transcribing
  → completed

resolving/transcribing
  → failed
  → retrying
  → resolving
```

前台“整理可下载材料”是完成前的语义投影，不增加底层持久状态。

允许命令：

- `retry`：仅 `failed`。
- `delete_record`：仅已有解析记录时；删除前由 UI 对话框确认。

### 8.2 笔记任务状态

```text
draft
  → analyzing
  → recommendation_ready
  → recommendation_stale
  → analyzing

recommendation_ready
  → generating_direct
  → complete

recommendation_ready
  → outline_ready
  → outline_regenerating
  → outline_ready
  → generating_chapters
  → chapter_failed
  → generating_chapters
  → complete

analyzing → analysis_failed → analyzing
generating_direct/generating_chapters → generation_failed
```

规则：

- 修改生成依据逐字稿时递增 `transcript_revision`，立即进入 `recommendation_stale`。
- `start_generation` 由后端读取 `final_settings.method`，确定性选择 direct 或 outline。
- 直接生成允许后台分块，但事件只发布五个语义阶段。
- 大纲模式才创建并公开 `note_chapters` 的章节级进度。
- 章节重试只更新失败章节；已完成章节不可回退为 waiting。
- `complete` 创建 `notes`、AI 初始版本和完整性检查结果。
- 单章重新生成属于成品操作，不把整个任务重新置为生成中。

### 8.3 服务重启恢复

启动时：

- `resolving`、`transcribing` 标记为 `failed`，错误码 `PROCESS_INTERRUPTED`，允许从安全阶段重试。
- `analyzing`、`generating_direct` 标记为 `generation_failed`，允许重新调用当前阶段。
- `generating_chapters` 检查章节表；保留 complete 章节，把 running 章节改为 failed。
- 等待设置、等待大纲、失败和已完成状态保持不变。

刷新或关闭标签页但服务仍运行时，不改变任务；前端使用 `device_id` 重新查询并从最新事件序号继续订阅。

## 9. 模块 interface

### 9.1 `ParserWorkflow`

```python
start_parse(device_id: str, source_url: str) -> TaskRef
command(task_id: str, command: ParserCommand) -> ParserTaskView
get_task(task_id: str) -> ParserTaskView
subscribe(task_id: str, after_seq: int) -> Iterator[WorkflowEvent]
```

`start_parse` 不读取 LLM 设置。

### 9.2 `NoteWorkflow`

```python
start_analysis(input: NoteInput) -> TaskRef
command(task_id: str, command: NoteCommand) -> NoteTaskView
get_task(task_id: str) -> NoteTaskView
subscribe(task_id: str, after_seq: int) -> Iterator[WorkflowEvent]
```

`NoteCommand` 使用带类型的联合：

- `update_transcript`
- `update_title`
- `save_settings`
- `start_generation`
- `regenerate_outline`
- `confirm_outline`
- `retry_analysis`
- `retry_failed_chapter`
- `restart_generation`

### 9.3 `NoteDocument`

```python
get(note_id: str) -> NoteView
save(note_id: str, expected_version: int, title: str, markdown: str) -> NoteView
restore_ai_initial(note_id: str, expected_version: int) -> NoteView
regenerate_chapter(note_id: str, chapter_id: str) -> CandidateView
decide_candidate(note_id: str, candidate_id: str, decision: str) -> NoteView
```

`save` 使用乐观并发。版本不匹配返回 `NOTE_VERSION_CONFLICT`，前端保留本地内容并提示重新载入，不能静默覆盖。

## 10. HTTP interface

所有 JSON 错误统一为：

```json
{
  "error": {
    "code": "STABLE_CODE",
    "message": "用户可读说明",
    "retryable": true,
    "details": {}
  }
}
```

### 10.1 视频解析

| 方法 | 路由 | 说明 |
|---|---|---|
| POST | `/api/v3/parser/tasks` | 创建解析任务，返回 202 + task |
| GET | `/api/v3/parser/tasks/{id}` | 查询当前状态 |
| GET | `/api/v3/parser/tasks/{id}/events?after={seq}` | 可重连 SSE |
| POST | `/api/v3/parser/tasks/{id}/commands` | `retry` |
| GET | `/api/v3/parser/records?limit=30&cursor=` | 解析历史 |
| GET | `/api/v3/parser/records/{id}` | 解析结果 |
| DELETE | `/api/v3/parser/records/{id}` | 永久删除解析记录 |
| GET | `/api/v3/parser/records/{id}/transcript.txt` | 下载 TXT |
| GET | `/api/v3/parser/records/{id}/transcript.md` | 下载 MD |
| GET | `/api/v3/parser/records/{id}/video` | 按需视频下载 |
| GET | `/api/v3/parser/records/{id}/audio` | 按需音频下载 |

### 10.2 笔记任务

| 方法 | 路由 | 说明 |
|---|---|---|
| POST | `/api/v3/note-tasks` | 明确点击“分析”或解析器带入时创建并启动预读 |
| GET | `/api/v3/note-tasks?device_id=&limit=30&cursor=` | 恢复中心/笔记任务历史 |
| GET | `/api/v3/note-tasks/{id}` | 查询任务投影 |
| GET | `/api/v3/note-tasks/{id}/events?after={seq}` | 可重连 SSE |
| POST | `/api/v3/note-tasks/{id}/commands` | 执行带类型命令 |
| DELETE | `/api/v3/note-tasks/{id}` | 删除未完成任务及其数据 |

创建请求：

```json
{
  "device_id": "browser-local-id",
  "source": {
    "type": "parser | paste | file",
    "parser_record_id": "optional",
    "name": "optional-file-name",
    "transcript": "required-for-paste-or-file"
  },
  "request_text": "optional"
}
```

文件选择与读取发生在浏览器；只允许 `.txt`、`.md`、UTF-8/UTF-8 BOM，最大 5 MB。选择文件不会请求后端，点击“分析逐字稿”才提交。

### 10.3 成品笔记

| 方法 | 路由 | 说明 |
|---|---|---|
| GET | `/api/v3/notes?limit=30&cursor=` | 笔记历史 |
| GET | `/api/v3/notes/{id}` | 阅读/编辑内容 |
| PATCH | `/api/v3/notes/{id}` | 标题或 Markdown 自动保存 |
| POST | `/api/v3/notes/{id}/restore-ai-initial` | 恢复 AI 初始版本 |
| POST | `/api/v3/notes/{id}/chapters/{chapter_id}/candidates` | 生成单章候选 |
| POST | `/api/v3/notes/{id}/candidates/{candidate_id}/decision` | accept/reject |
| GET | `/api/v3/notes/{id}/export?format=md&content=note&source=include` | Markdown/PDF |
| DELETE | `/api/v3/notes/{id}` | 永久删除笔记、依据、设置、版本与任务 |

复制全文在前端使用当前已保存 Markdown；复制前若存在未完成自动保存，必须先等待保存成功。

### 10.4 设置

保留 `/api/settings` 与 `/api/test-connection`，但：

- API Key 响应始终掩码，不返回明文。
- 视频解析接口不得读取或要求 LLM 设置。
- 保存文件权限为用户可读写，其他用户不可读。

## 11. SSE 事件协议

SSE 只传输状态投影，不承担唯一存储。

```text
id: 17
event: progress
data: {"state":"generating_direct","stage":"generate_content","label":"生成内容"}
```

事件类型：

- `state`：持久状态改变。
- `progress`：同一状态内的语义进度。
- `error`：稳定错误码、说明、可重试性。
- `complete`：返回下一资源 ID。
- `heartbeat`：15 秒一次，避免连接被认为失效。

前端保存每个任务最后一个 `seq`。重连时传 `after`；服务端先补发数据库中的后续事件，再进入实时等待。若没有 SSE，页面仍可通过 `GET task` 恢复正确状态。

## 12. 视频解析工作流

1. 前端本地识别平台，只用于即时提示。
2. 后端重新检测平台，后端结果为事实源。
3. `resolve` 读取元信息与封面。
4. 下载仅用于本次转录的临时媒体。
5. Whisper 转录成功后，在同一个事务内创建解析记录并完成任务。
6. 临时视频和音频在任务结束后清理。
7. 用户点击媒体下载时，按原链接重新拉取并直接流向浏览器。
8. 封面提取失败时 `thumbnail_url` 为空，前端保留同一封面位置并使用 UI 合同中的回退视觉。

外部命令必须使用参数数组，不允许将 URL、搜索词、标题或文件名拼入 `shell=True` 字符串。

## 13. AI 预读与推荐

LLM 返回严格 JSON；后端验证失败时自动重试一次。第二次仍失败进入 `analysis_failed`，保留全部输入。

推荐结果：

```json
{
  "title": "用 AI Agent 重建个人学习系统：从收藏到行动",
  "reason": "一句可展示说明",
  "structure": {
    "question": "怎样组织最容易理解？",
    "options": [
      {"id": "problem_method_practice", "label": "问题 → 方法 → 实践", "reason": "..."}
    ],
    "recommended_id": "problem_method_practice"
  },
  "detail": {
    "options": ["quick", "key", "complete"],
    "recommended_id": "complete"
  },
  "method": {
    "options": ["direct", "outline"],
    "recommended_id": "direct"
  },
  "modules": {
    "recommended_ids": ["summary", "concepts", "actions", "review_questions"],
    "reasons": {}
  }
}
```

稳定执行 ID：

- 详细程度：`quick`、`key`、`complete`。
- 生成方式：`direct`、`outline`。
- 附加模块：`summary`、`concepts`、`actions`、`review_questions`。前台固定只展示这四项，AI 自动推荐最多三项；正文必须保持主体地位，附加模块合计不超过成品约 25%。术语解释并入关键概念，案例与行动并入实践提炼，原文金句按正文需要自然引用。

AI 可以动态生成问题、标签和理由，但不能返回前端未知的模块 ID。

## 14. 生成执行

### 14.1 快速生成

- 后端使用推荐设置作为最终设置。
- 事件只公开：理解逐字稿、组织结构、生成内容、检查遗漏、完成。
- 长逐字稿允许内部切块，但 chunk 数、分块文本和内部重试不进入 UI。
- 失败自动重试最多 2 次；仍失败进入恢复中心的失败状态。

### 14.2 大纲确认

- 先生成只读大纲 JSON：章节 ID、标题、目标、顺序。
- 用户补充一句要求时，重新生成整份大纲。
- 确认后创建 `note_chapters`。
- 每章生成时输入：生成依据逐字稿相关段、整份大纲、本次需求、最终设置、前章上下文摘要。
- 一章完成后，章节内容和上下文摘要在同一事务中保存，再开始下一章。

### 14.3 内容完整性检查

输入：

- 生成依据逐字稿。
- 本次笔记需求。
- 最终设置。
- 生成结果。

输出只允许：

```json
{"status":"ok"}
```

或：

```json
{
  "status":"possible_omission",
  "items":[
    {
      "source_locator":"06:12",
      "summary":"失败后调整下一周目标的判断步骤未展开",
      "chapter_id":"chapter-04"
    }
  ]
}
```

不生成覆盖率百分比。检查失败本身不得阻塞成品保存。

### 14.4 图示能力

- 第一版本轮不把 Mermaid 作为普通用户可选的附加模块，避免增加决策负担和挤占正文。
- 未来如作为高级能力重新开放，只在内容存在明确流程、层级、因果或关系网络时使用。
- 图示失败不得阻止正文完成；前端永远不展示原始错误代码。

## 15. 阅读、编辑与版本

Markdown 是持久化事实源。

阅读流程：

1. `marked` 将 Markdown 转为 HTML。
2. `DOMPurify` 清洗后插入页面。
3. Mermaid 只处理清洗后的允许节点。

编辑流程：

1. 在同一文档位置把内容切换为 `contenteditable`。
2. 工具栏仅支持 H2、加粗、列表、引用、代码块、撤销、重做。
3. `NoteDocument` 前端模块把编辑 DOM 转成 Markdown；普通用户不接触原始语法。
4. 输入后 650 ms 防抖自动保存。
5. 请求携带 `expected_version`；成功后更新本地版本号。
6. 离开编辑状态时强制 flush 未保存内容并创建一个用户检查点。

第三方前端库以本地 vendored 文件提供，不能依赖运行时 CDN：

- `marked`
- `DOMPurify`
- `Turndown`
- `Mermaid`

恢复 AI 初始版本前创建 `before_restore` 检查点。恢复后仍递增版本号。

## 16. 单章候选

1. 从当前 Markdown 定位章节边界。
2. 向 LLM 提供生成依据逐字稿、整份大纲、前后章节、本次需求、最终设置和当前章节。
3. 保存 pending 候选，不修改当前笔记。
4. 接受时先保存 `candidate_accept` 检查点，再替换该章节并递增版本。
5. 保留时把候选标记为 rejected，当前版本不变。

如果用户正在编辑且存在未保存内容，必须先完成自动保存才能开始单章重新生成。

## 17. 导出

### 17.1 Markdown

- 默认仅当前笔记 Markdown。
- 选择“笔记 + 生成依据逐字稿”时追加：

```markdown
---

## 生成依据逐字稿

...
```

- 来源信息根据选项包含标题、作者、平台、原链接、生成与修改时间。

### 17.2 PDF

- 使用最新已保存 Markdown。
- 逐字稿附录从新页开始。
- Mermaid 模块在 PDF 中使用生成时保存的结构化文字表示；网页可渲染图形，但 PDF 不引入额外浏览器渲染依赖，且不输出原始 Mermaid 代码。
- 临时 HTML/PDF 在响应完成后清理。

### 17.3 复制全文

- 前端复制与 Markdown 导出相同的最新内容组合。
- Clipboard 失败显示可重试提示，不改变笔记状态。

## 18. 历史、关联与删除

- 两类历史默认 `limit=30`，使用 `(created_at, id)` 游标加载更多。
- 不因第 31 条记录自动删除旧数据。
- 解析历史投影包含是否关联成品笔记和 `note_id`。
- 笔记历史投影包含来源类型、任务状态、章节进度和关联解析记录。

删除解析记录事务：

1. 删除 `parse_note_links`。
2. 删除解析侧逐字稿与记录。
3. 保留笔记任务、成品、生成依据和版本。

删除笔记事务：

1. 删除候选、版本、成品、章节、笔记任务和关联行。
2. 保留解析记录及其逐字稿。

两类操作都是真正硬删除；前端确认后才调用 DELETE。下载到电脑的文件不在应用控制范围内。

## 19. 前端状态与 UI 合同映射

应用外壳只保留“视频解析 / 笔记生成”两个一级入口。根地址默认视频解析。

### 19.1 视频解析器

| UI 状态 | 数据投影 |
|---|---|
| 01 初始 | 无当前任务 |
| 02 解析中 | parser task resolving/transcribing |
| 03 结果 | parser record |
| 04 失败 | parser task failed |
| 05 历史 | parser record query |
| 06 删除确认 | parser record + 本地 dialog 状态 |

### 19.2 笔记生成器

| UI 状态 | 数据投影 |
|---|---|
| 01 输入 | 本地未提交草稿 |
| 02 已就绪 | 本地文件读取完成 |
| 03 预读中 | analyzing |
| 04 推荐 | recommendation_ready |
| 05 自定义 | recommendation_ready + 本地设置草稿 |
| 06 推荐过期 | recommendation_stale |
| 07 预读失败 | analysis_failed |
| 08 直接生成 | generating_direct |
| 09 大纲 | outline_ready |
| 10 重拟大纲 | outline_regenerating |
| 11 逐章生成 | generating_chapters |
| 12 章节失败 | chapter_failed |
| 13 任务恢复 | note task history query |
| 14 生成完成 | complete + note receipt |
| 15 阅读 | note current version |
| 16 编辑 | note current version + local editor state |
| 17 单章候选 | pending chapter candidate |
| 18 导出 | note current version + export options |
| 19 可能遗漏 | integrity possible_omission |
| 20 笔记历史 | note history query |
| 21 删除确认 | note/task + 本地 dialog 状态 |

状态控制台只存在于开发/验收模式。生产本地应用默认隐藏，通过 `?acceptance=1` 打开，并使用 fake adapters 与固定 fixture 重现 27 个状态。

## 20. 前端数据流

`app-state.js` 维护：

- 当前一级视图。
- 当前 parser task/record。
- 当前 note task/note。
- SSE 最后序号。
- 编辑器未保存状态。

页面切换不能靠复制 HTML 状态。视图只从投影渲染：

```text
用户动作
  → workflow-client command
  → 后端事务更新
  → SSE/GET task projection
  → app-state
  → render
```

标题、本次需求、来源、版本和导出文件名都必须来自同一投影字段，禁止在不同模板中硬编码重复值。

## 21. 并发与资源

- Whisper 模型进程内单例。
- 同时最多 1 个 Whisper 转录任务，避免内存争用。
- 同时最多 2 个平台下载/解析任务。
- 同时最多 1 个用户级笔记生成任务；内部 chunk 最多 3 个并发。
- SQLite 写操作使用短事务，不在事务内调用外部命令或 LLM。
- SSE 连接断开不取消后台任务。
- 每个外部调用有明确超时、最多重试次数和稳定错误码。

## 22. 安全与本地隐私

- 默认绑定 `127.0.0.1`；若以后开放局域网，需要单独安全评审。
- 所有 SQL 参数化。
- 所有外部命令使用参数数组，禁止 `shell=True` 拼接用户输入。
- 移除任意 URL 图片代理；封面代理只能通过已保存记录 ID 获取后端已验证的 URL。
- 上传文件检查扩展名、大小、UTF-8 解码和二进制特征。
- Markdown 在浏览器渲染前使用 DOMPurify。
- API Key 不进入日志、SSE、任务表或错误详情。
- 导出文件名去除路径字符、控制字符并限制长度。
- 错误日志记录 `task_id` 和错误码，不记录完整逐字稿或 API Key。

## 23. 旧数据迁移与兼容

首次进入新页面时：

1. 前端读取 `vtn-transcripts` 和 `vtn-history`。
2. 调用一次性 `/api/v3/migrations/browser-history`。
3. 后端去重导入解析记录和旧成品。
4. 成功后写入 `vtn-v3-migration-complete`，保留旧 localStorage 一版发布周期，不立即删除。

兼容策略：

- 现有 `/api/process` 和下载路由在新 UI 验收前保留。
- 旧页面移动到 `/legacy/parser` 和 `/legacy/notes`，不出现在一级导航。
- 新 UI 通过真实端到端验收后，根路由切换到 `static/app.html`。
- 旧接口删除另行评审，不在同一次切换中完成。

## 24. 测试策略

### 24.1 模块测试

- ParserWorkflow：fake media + fake transcriber，覆盖成功、平台失败、转录失败、重试和记录删除。
- NoteWorkflow：fake LLM，覆盖预读、推荐过期、direct/outline 分支、章节失败、恢复和完整性检查。
- NoteDocument：覆盖自动保存版本冲突、初始版本恢复、候选接受/拒绝。
- Exporter：覆盖六种格式/范围/来源组合及文件名清洗。

测试只通过模块 interface 操作，不断言内部函数调用顺序。

### 24.2 SQLite 集成测试

- 使用临时数据库。
- 验证事务、外键、非级联所有权、游标分页和启动恢复。
- 验证删除解析记录后笔记依据仍存在，删除笔记后解析逐字稿仍存在。

### 24.3 HTTP 合同测试

- 请求/响应 JSON schema。
- 统一错误结构。
- SSE `seq` 递增、断线补发、heartbeat。
- API Key 掩码。
- 文件上传和导出响应头。

### 24.4 浏览器 E2E

必须完整通过已锁定的两条路径 A/B。测试使用 fake adapters 和固定 fixture，避免真实网络与 LLM 造成不稳定。

### 24.5 视觉回归

- 视口：1440 × 1050，桌面 Chrome。
- 固定字体和 fixture。
- 覆盖全部 27 个验收状态。
- 与 `prototype-phase1-video-parser/screenshots/` 和 `screenshots/final-e2e/` 对照。
- 任何布局、组件形态、关键文案或颜色语义偏差必须人工确认，不能只依赖像素阈值。

## 25. 可观测性

本地日志使用结构化单行 JSON：

```json
{
  "time": "2026-07-27T13:00:00Z",
  "level": "INFO",
  "workflow": "note",
  "task_id": "...",
  "state": "generating_chapters",
  "event": "chapter_completed",
  "duration_ms": 1234
}
```

记录：

- 状态迁移。
- adapter 调用耗时与错误码。
- 自动重试。
- 任务恢复。
- 导出完成和临时文件清理。

不记录逐字稿正文、笔记正文、API Key 或完整外部响应。

## 26. 实现顺序

这不是 ticket 拆分，只定义降低返工风险的依赖顺序：

1. 建立新目录骨架、领域模型、SQLiteRepository 和迁移。
2. 抽出 ParserWorkflow，先解除解析对 LLM 配置的依赖。
3. 实现解析记录、历史、下载和恢复接口。
4. 实现 NoteWorkflow 的预读、推荐、设置与两条生成分支。
5. 实现成品、编辑、版本、候选、导出与删除。
6. 将锁定原型转换为真实前端，逐状态接入投影。
7. 导入旧 localStorage 数据。
8. 跑模块、集成、HTTP、两条 E2E 和 27 状态视觉回归。
9. 用户确认真实页面后再切换根路由。

## 27. 完成定义

只有同时满足以下条件，真实实现才算完成：

- 两条端到端路径使用真实后端流程通过。
- 27 个状态与 UI 合同对照通过。
- 视频解析器在未配置 LLM 时可独立运行。
- 刷新/关闭标签页后任务可恢复。
- 标题、本次需求、来源、最新版本和导出内容跨阶段一致。
- 解析记录与笔记删除互不级联。
- 下载媒体不长期缓存。
- 页面运行时错误为 0。
- 模块、SQLite、HTTP、E2E 和视觉测试通过。
- `app.py` 不再承载业务实现。
- 用户再次确认真实页面与锁定原型一致。
