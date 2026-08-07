# 视频解析器 + 自适应笔记生成器：Ticket 规划交接

> 日期：2026-07-27
> 来源任务：`019fa3c8-17dc-7e93-9998-10f47513adc9`
> 当前工作树：`/Users/yubo/.codex/worktrees/8f75/Claude code test/video-to-notes-web`
> 下一阶段：依据已确认技术规格拆分可执行 tickets
> 禁止事项：本阶段不开始实现、不提交、不重新设计 UI

## 1. 已完成并由用户确认的工作

1. “视频解析器 + 自适应笔记生成器”四阶段高保真假数据原型已经逐阶段实际点击确认。
2. 两条完整端到端路径已经验收：
   - 路径 A：视频解析 → 带入逐字稿 → 接受推荐 → 快速生成 → 阅读/编辑/导出。
   - 路径 B：独立逐字稿输入 → 自定义设置 → 大纲确认 → 逐章生成/失败恢复 → 成品历史与删除边界。
3. UI 合同已经锁定。用户确认前的 35 项产品决定、四阶段 27 个状态和视觉基线都不再重新讨论。
4. 用户已经明确确认第一版范围：
   - 只做本地网页项目。
   - 本地 FastAPI + 浏览器页面 + 本地 SQLite。
   - 默认仅监听 `127.0.0.1`，供用户本人使用。
   - 不做服务器部署、账号登录、云数据库、跨设备同步。
   - 不做手机版 App，也不把完整移动端适配作为第一版验收项。
   - 只保留未来迁移所需的模块接口，不提前实现服务器或移动端能力。
5. 完整技术规格已经由用户确认，没有遗留待定产品项。

## 2. 下一任务的唯一目标

读取本交接列出的全部材料，把已经确认的技术规格拆成一组可执行、可验证、有依赖顺序的实施 tickets。

每个 ticket 至少包含：

- 目标与用户价值。
- 明确范围和非范围。
- 允许修改的文件或模块。
- 前置依赖。
- 实现要点，但不重复整份技术规格。
- 可自动验证的验收标准。
- 需要保留的兼容行为和安全边界。
- 与 27 个 UI 状态或两条 E2E 路径的对应关系。

Ticket 拆分必须让后续执行者可以逐个实现、测试和交付，不需要重新猜测产品决定。

完成 tickets 后停止并交给用户确认。用户确认 tickets 前，不开始真实实现。

## 3. 必读材料与优先级

按以下顺序完整阅读：

1. `docs/handoffs/2026-07-27-adaptive-video-notes-ticket-planning-handoff.md`
2. `docs/superpowers/specs/2026-07-27-adaptive-video-notes-technical-spec.md`
3. `docs/handoffs/2026-07-27-adaptive-notes-ui-final-acceptance.md`
4. `docs/handoffs/2026-07-27-adaptive-notes-ui-final-e2e-handoff.md`
5. `docs/handoffs/2026-07-27-adaptive-notes-ui-grill-handoff-2.md`
6. `docs/adr/0001-sqlite-as-local-source-of-truth.md`
7. `CONTEXT.md`
8. `prototype-phase1-video-parser/README.md`
9. `prototype-phase1-video-parser/index.html`
10. `prototype-phase1-video-parser/styles.css`
11. `prototype-phase1-video-parser/script.js`
12. 当前真实应用的 `app.py`、`static/parser.html`、`static/index.html`
13. `docs/ARCHITECTURE.md` 与现有 PRD/规格中仍适用的兼容约束

事实冲突时使用以下优先级：

1. 用户在最终验收和本交接中的明确确认。
2. 已确认技术规格。
3. UI 最终验收记录和 final-e2e 交接。
4. 锁定原型的实际行为。
5. 旧架构文档和当前旧实现。

## 4. 已确认的技术主线

- FastAPI + 原生 HTML/CSS/ES Modules，不引入 React/Vue 构建链。
- SQLite `data/vtn.sqlite3` 是任务、历史、版本、关联和事件的本地事实源。
- 六个深模块：
  - `ParserWorkflow`
  - `NoteWorkflow`
  - `NoteDocument`
  - `Exporter`
  - `HistoryQuery`
  - `SQLiteRepository`
- 真实外部依赖通过 adapters 隔离：
  - `PlatformMedia`
  - `Transcriber`
  - `LLM`
  - `Clock`
- 视频解析器必须独立运行，不得要求 LLM 配置。
- 解析任务与笔记任务使用独立状态机。
- SSE 改为可重连 GET 订阅，以 SQLite 事件序号补发；SSE 不是唯一事实源。
- 解析记录和笔记任务分别保存逐字稿副本，删除一侧不级联删除另一侧。
- Markdown 是成品笔记的持久化事实源。
- 编辑使用轻量可视化编辑、650 ms 防抖自动保存、乐观并发版本。
- AI 初始版本不可变；单章重新生成先产生候选，用户接受后才替换。
- 视频和音频只按需重新拉取，不作为历史资产长期缓存。
- Mermaid 网页失败时降级为结构化文字；PDF 始终使用保存的结构化文字表示，不引入额外浏览器渲染依赖。
- 状态控制台默认隐藏，只在 `?acceptance=1` 验收模式使用 fake adapters 和固定 fixtures。

## 5. 当前真实实现必须解决的已知问题

- `app.py` 是约 1300 行的单文件业务实现。
- `POST /api/process` 同时承担解析、转录和笔记生成。
- 即使 `stop_at="transcribe"`，当前接口也先检查 LLM 配置。
- 任务只存在进程内 `tasks: dict`，服务重启会丢失。
- 解析历史和笔记历史分别存在浏览器 localStorage。
- 下载依赖仍存在内存中的 `task_id`。
- 部分外部命令使用字符串拼接和 `shell=True`，必须迁移为参数数组。
- 新实现切换前需要保留旧接口和旧页面兼容，不能在同一批次直接删除。

这些是 ticket 必须覆盖的迁移问题，不是重新设计产品的理由。

## 6. Ticket 规划建议边界

推荐按技术规格第 26 节的依赖顺序拆分，但 ticket 粒度应以“可独立验证、不会跨越过多模块”为准：

1. 领域模型、错误码、SQLite schema/repository 和迁移框架。
2. ParserWorkflow 抽离及解析对 LLM 配置解耦。
3. 解析记录、历史、按需下载、失败与重启恢复。
4. NoteWorkflow 预读、推荐、推荐过期与设置保存。
5. 快速生成分支。
6. 大纲确认、逐章生成和章节失败恢复分支。
7. 成品、完整性检查、版本和历史关联。
8. 轻量编辑、自动保存、AI 初始版本恢复。
9. 单章候选。
10. Markdown/PDF/复制导出。
11. 非级联永久删除和旧 localStorage 迁移。
12. 锁定前端接入真实投影。
13. 两条 E2E、27 状态视觉回归和根路由切换验收。

这只是分组提示，不是要求机械生成 13 个 tickets。需要根据可测试边界决定最终数量和依赖图。

## 7. UI 合同与验收不可丢失的边界

- 只有“视频解析 / 笔记生成”两个一级入口。
- 视频解析器 6 个状态、笔记生成器 21 个状态必须全部有实现与测试归属。
- 快速生成和大纲确认是用户可见的两条不同路径；后台分块不能伪装成大纲确认。
- 标题、本次需求、来源、版本、历史和导出文件名必须来自同一后端投影，不能跨阶段漂移。
- 失败后保留已经完成的内容，章节重试不能覆盖完成章节。
- “可能遗漏”是具体、非阻断提醒，不显示虚假覆盖率。
- 删除确认必须明确删除范围；解析记录与笔记互不级联。
- 用户已下载到电脑的文件不在应用删除范围内。
- 不因历史超过 30 条自动删除；30 只是分页大小。
- 真页面最终仍需用户实际点击确认，自动化测试不能代替用户确认。

## 8. 工作树与安全边界

- 只使用当前工作树：
  `/Users/yubo/.codex/worktrees/8f75/Claude code test/video-to-notes-web`
- 不修改源工作树：
  `/Users/yubo/.codex/worktrees/fded/Claude code test/video-to-notes-web`
- 当前仓库存在大量与本任务无关的改动和未跟踪文件，必须保留并避开。
- 不执行 reset、checkout 覆盖、清理或批量删除。
- 当前阶段不修改 `app.py`、`static/` 或真实后端。
- 当前阶段不接 AI、Whisper、真实视频解析、下载、数据库、真实恢复或真实导出。
- 不提交、不推送。
- 如需浏览原型，使用当前工作树的独立端口 4174；不得使用源工作树服务的 4173。
- final-e2e 截图已经存在，不覆盖现有基线。

## 9. 当前文件状态

本轮新增或更新但未提交：

- `docs/handoffs/2026-07-27-adaptive-notes-ui-final-acceptance.md`
- `docs/superpowers/specs/2026-07-27-adaptive-video-notes-technical-spec.md`
- `docs/adr/0001-sqlite-as-local-source-of-truth.md`
- `docs/handoffs/2026-07-27-adaptive-video-notes-ticket-planning-handoff.md`
- `CONTEXT.md`
- `prototype-phase1-video-parser/README.md`
- `prototype-phase1-video-parser/` 原型及 final-e2e 截图

不要因为这些文件显示为未跟踪而重新复制、删除或覆盖。

## 10. 下一任务的停止条件

满足以下条件后停止：

- tickets 覆盖技术规格的全部实现范围。
- 每个 ticket 都有依赖、范围、验收与 UI/E2E 对应。
- 27 个 UI 状态没有无人负责的实现或测试空洞。
- 本地第一版边界清晰，没有混入服务器、账号、云同步或手机版。
- tickets 之间没有重复拥有同一数据或状态机责任。
- 未修改真实应用代码，未开始实现，未提交。
- 把 ticket 包交给用户确认。
