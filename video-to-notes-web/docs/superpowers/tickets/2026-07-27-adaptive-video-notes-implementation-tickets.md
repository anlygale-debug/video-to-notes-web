# 视频解析器 + 自适应笔记生成器：实施 Ticket 包

> 状态：用户已于 2026-07-27 确认；尚未开始真实实现
>
> 依据：[已确认技术规格](../specs/2026-07-27-adaptive-video-notes-technical-spec.md)、[UI 合同验收](../../handoffs/2026-07-27-adaptive-notes-ui-final-acceptance.md)、[规划交接](../../handoffs/2026-07-27-adaptive-video-notes-ticket-planning-handoff.md)

## 执行总则

- 第一版仅在本机运行：FastAPI + 原生浏览器页面 + SQLite，默认绑定 `127.0.0.1`。
- 不做账号、云同步、服务器部署、手机版 App 或完整移动端适配。
- UI 合同中的双入口、27 个状态、关键文案与视觉层级不可自行改写。
- 每个 Ticket 完成后必须先跑自己的自动验收；未完成的依赖不得并行进入下游。
- 旧路由与旧页面在新 UI 真实验收通过前保留；不得在迁移中删除 `app.py`、`static/` 的旧能力。

## 依赖图

```text
T01 ─┬─ T02 ─ T03 ─┐
     ├─ T04 ─┬─ T05 ─┤
     │       └─ T06 ─┤
     └─ T11 ─────────┼─ T12 ─ T13
T05 + T06 ─ T07 ─┬─ T08 ─┤
                  ├─ T09 ─┤
                  └─ T10 ─┘
```

T02 与 T04 可在 T01 后并行；T11 只建立真实 UI 的公共骨架与客户端，可在 T01 后并行。其余依赖以数据契约为准。

---

## T01｜领域契约、SQLiteRepository 与迁移框架

**目标与价值**：让任务、记录、笔记、版本和事件有一个可恢复的本地事实源，后续工作流不再直接依赖进程内字典或浏览器正文。

- **范围**：建立 `vtn/domain` 的枚举、值对象、稳定错误码；`vtn/storage` 的 schema、迁移、短事务 repository；建立 `data/vtn.sqlite3` 初始化与临时数据库测试工具。
- **非范围**：不接入路由、真实媒体、Whisper、LLM 或新页面；不导入旧 localStorage。
- **允许修改模块**：新增 `vtn/domain/*`、`vtn/storage/*`、`tests/unit/*`、`tests/integration/*`，仅把 `app.py` 改为未来可装配入口所需的最小导入骨架。
- **依赖**：无。
- **实现要点**：严格落实 `parser_tasks`、`parser_records`、`note_tasks`、`note_chapters`、`notes`、`note_versions`、`chapter_candidates`、`parse_note_links`、`workflow_events`；启用 WAL、外键和 busy timeout；所有时间 UTC、ID UUID4；事件 `(workflow_type, task_id, seq)` 单调递增。
- **自动验收**：临时 SQLite 上验证 schema 幂等迁移、外键只删除关联行、游标分页排序、事件续号、短事务不包裹外部调用；`pytest tests/unit tests/integration` 通过。
- **安全与兼容**：所有 SQL 参数化；不把 API Key、逐字稿或笔记正文写入日志；不删除 `tasks`、localStorage 或旧数据库配置。
- **UI/E2E 对应**：为全部 27 状态提供持久化投影基础；路径 A/B 尚不打开页面。

## T02｜ParserWorkflow 与安全媒体适配层

**目标与价值**：让视频解析能在未配置 LLM 时独立工作，并把平台解析、临时媒体和转录复杂度收进明确模块。

- **范围**：实现 `ParserWorkflow`、`PlatformMedia`、`Transcriber` interface 及 production/fake adapter；解析状态机、语义进度、重试和临时文件清理。
- **非范围**：不实现 v3 HTTP、历史界面、媒体长期保存或笔记生成。
- **允许修改模块**：新增 `vtn/workflows/parser.py`、`vtn/adapters/media.py`、`vtn/adapters/transcription.py`、相关测试；只抽取可复用的旧 `app.py` resolver/Whisper 逻辑，不改变旧路由行为。
- **依赖**：T01。
- **实现要点**：`start_parse` 不读取设置或 LLM；`created → resolving → transcribing → completed` 及失败/重试；保存事件后通知订阅者；调用 xhs/yt-dlp/curl/ffmpeg 一律参数数组，临时媒体只为当前任务存在；fake adapter 返回固定 fixture。
- **自动验收**：fake media/transcriber 覆盖成功、平台失败、转录失败、仅 failed 可 retry、临时文件 finally 清理、无 LLM 配置仍可完成解析；静态检查拒绝新增 `shell=True`。
- **安全与兼容**：URL、文件名和搜索词不得拼接进 shell；不删除或改写旧 `/api/process`；生产 adapter 不在测试中访问网络。
- **UI/E2E 对应**：解析 02、04 的行为基础；路径 A 的“开始解析”到失败重试可模拟验证。

## T03｜解析记录、v3 Parser HTTP、历史与按需下载

**目标与价值**：完成可恢复的解析结果和历史，使用户能查看逐字稿、下载材料、带入笔记而不依赖内存 task。

- **范围**：ParserWorkflow 的 v3 routes、GET SSE、记录查询、TXT/MD/视频/音频下载、解析删除、启动恢复和 HistoryQuery 的解析投影。
- **非范围**：不做新笔记工作流、不删除旧下载 API、不长期缓存视频/音频。
- **允许修改模块**：`vtn/web/parser_routes.py`、`vtn/web/events.py`、`vtn/web/history_routes.py`、`vtn/workflows/parser.py`、`vtn/storage/*`、解析相关 HTTP/integration tests。
- **依赖**：T01、T02。
- **实现要点**：实现 `/api/v3/parser/...` 契约；SSE 通过 `after` 补发且 15 秒 heartbeat；记录保存解析侧逐字稿副本，下载媒体按原链接重新流向浏览器；启动把中断解析标记 `PROCESS_INTERRUPTED`；封面失败仍返回稳定回退投影。
- **自动验收**：HTTP schema、202 创建、事件 seq/断线补发、TXT/MD headers、按需下载不写持久媒体路径、分页 `limit=30`、删除记录后关联笔记数据仍存在、重启恢复测试。
- **安全与兼容**：仅已保存 record ID 可取封面/下载；禁止任意 URL 图片代理；旧 `/api/process` 和旧页面继续可用。
- **UI/E2E 对应**：解析 01–06；路径 A 的解析→结果→带入来源入口，路径 B 不依赖本 Ticket。

## T04｜NoteWorkflow 预读、推荐、设置与任务投影

**目标与价值**：把逐字稿输入变为可恢复、可解释且不强制用户逐项确认的 AI 推荐流程。

- **范围**：NoteWorkflow 的 `draft/analyzing/recommendation_ready/recommendation_stale/analysis_failed`、LLM/Clock adapter、严格推荐 JSON 校验、typed commands、来源快照与设置保存。
- **非范围**：不生成成品正文、不实现大纲/章节、不实现编辑导出。
- **允许修改模块**：新增 `vtn/workflows/notes.py`、`vtn/adapters/llm.py`、`vtn/web/note_routes.py`、任务 HTTP/单元测试。
- **依赖**：T01。
- **实现要点**：仅明确点击分析或解析器带入时创建并启动任务；本地文件由浏览器读取，后端只接 UTF-8 TXT/MD 文本（≤5 MB）；动态理由/问题可变，执行 ID 必须来自八项稳定能力库；修改生成依据递增 revision 并立即过期；LLM JSON 失败自动重试一次。
- **自动验收**：fake LLM 覆盖粘贴、文件、parser 三类来源，推荐成功、格式失败、重试、标题更新、推荐过期和无法开始生成；HTTP 错误统一结构。
- **安全与兼容**：不记录 API Key 或完整正文；文件名净化、UTF-8/BOM/二进制检查；不改旧文本输入页面。
- **UI/E2E 对应**：笔记 01–07；路径 A 的带入预读和路径 B 的独立输入、需求、推荐、自定义入口。

## T05｜快速生成、完整性检查与直接路径恢复

**目标与价值**：实现用户接受推荐后一次性得到成品的可恢复直达路径，同时不暴露内部 chunk。

- **范围**：`generating_direct` 执行、五段语义事件、自动重试、`generation_failed` 恢复、完整性检查和成品创建入口。
- **非范围**：不展示/生成前台大纲、不创建章节进度、不实现编辑器或导出。
- **允许修改模块**：`vtn/workflows/notes.py`、`vtn/storage/*`、`vtn/domain/*`、对应 unit/integration tests。
- **依赖**：T04。
- **实现要点**：只由 `final_settings.method=direct` 选择本分支；内部可分块但不可泄漏到前台；只发布“理解逐字稿、组织结构、生成内容、检查遗漏、完成”；检查失败不阻塞保存；完成时原子创建 notes 和 `ai_initial` 版本。
- **自动验收**：验证设置分支确定性、最多两次自动重试、五种事件标签、失败后 restart、服务重启后可重新调用当前阶段、完整性 `ok/possible_omission` 两种投影。
- **安全与兼容**：LLM 调用不在 SQLite 事务内；不覆盖用户标题或来源快照；不改变 outline 选择的语义。
- **UI/E2E 对应**：笔记 08、14、19 的后端基础；路径 A 的推荐→快速生成→成品。

## T06｜大纲确认、逐章生成与章节级恢复

**目标与价值**：实现与快速生成不同的用户可见流程，让失败后只重试失败章节并保留已完成内容。

- **范围**：只读大纲、重拟、确认、章节表、上下文摘要、章节失败/重试/稍后继续、整份重生成命令。
- **非范围**：不支持章节手动改名、增删、排序；不实现候选章节或阅读编辑。
- **允许修改模块**：`vtn/workflows/notes.py`、`vtn/storage/*`、`vtn/web/note_routes.py`、相关测试。
- **依赖**：T04。
- **实现要点**：仅 `method=outline` 产生 `outline_ready`；反馈重拟整份只读大纲并保留 final settings/需求；确认后创建 `note_chapters`；每章完成时内容和 context summary 同一事务保存；启动恢复把 running 改 failed、complete 保留。
- **自动验收**：覆盖 outline ready/regenerating、反馈回显、确认、逐章事件、失败不回退已完成章节、retry_failed_chapter、稍后继续查询和主动整份重生成；断言 direct 不创建公开章节。
- **安全与兼容**：外部调用不占事务；不让大纲模式因为后台分块而出现在 direct 流程；不改原型结构或文案。
- **UI/E2E 对应**：笔记 09–14；路径 B 的自定义→大纲→失败→恢复→完成。

## T07｜成品笔记、历史关联、完整性与所有权删除服务

**目标与价值**：让完成笔记成为独立、可查询的知识对象，明确来源关联和双方逐字稿不级联的所有权。

- **范围**：NoteDocument 的读模型、notes/history query、parse-note link、完整性投影、笔记/解析删除领域服务。
- **非范围**：不做前端编辑 DOM、候选生成、导出格式渲染或浏览器 localStorage 导入。
- **允许修改模块**：`vtn/documents/notes.py`、`vtn/web/history_routes.py`、`vtn/storage/*`、`vtn/domain/*`、integration tests。
- **依赖**：T03、T05、T06。
- **实现要点**：完成任务原子创建 note、AI 初始版本、来源快照和双向链接；历史为 `(created_at,id)` 游标；笔记历史显示来源类型、任务状态、章节进度；删除 service 严格按双方副本边界执行。
- **自动验收**：解析历史可返回关联 `note_id`，笔记历史保留 parser/paste/file；删除解析记录后笔记/生成依据仍可读，删除笔记后解析记录/逐字稿仍可读；第 31 条不自动删除。
- **安全与兼容**：硬删除仅经后续 HTTP 确认入口调用；不清理用户下载文件；不改旧历史 localStorage。
- **UI/E2E 对应**：解析 05/06、笔记 14/15/19/20/21；路径 A 的反向打开笔记和路径 B 的删除边界。

## T08｜轻量编辑、版本恢复与单章候选

**目标与价值**：让用户能安全编辑成品、恢复 AI 初始版本并比较单章候选，绝不静默覆盖当前内容。

- **范围**：NoteDocument save 乐观并发、检查点、初始版本恢复、候选生成/接受/保留与章节 Markdown 边界定位。
- **非范围**：不写浏览器 contenteditable UI、不做复杂 diff 或块编辑器。
- **允许修改模块**：`vtn/documents/notes.py`、`vtn/web/note_routes.py`、`vtn/workflows/notes.py`（候选调用）、相关测试。
- **依赖**：T07。
- **实现要点**：PATCH 带 `expected_version`；冲突返回 `NOTE_VERSION_CONFLICT`；离开编辑和候选接受/恢复前各建适当检查点；同章最多一个 pending 候选；候选参考完整规定上下文且接受才替换。
- **自动验收**：并发 save 冲突不丢本地内容、AI 初始版本不可变、恢复前有 `before_restore`、接受递增版本且有 `candidate_accept`、拒绝不改当前版本、未保存内容时拒绝启动候选。
- **安全与兼容**：正文只从 Markdown 事实源转换，不能把编辑 DOM 当持久化事实；不新增第三方云编辑器。
- **UI/E2E 对应**：笔记 15–17；路径 A 的编辑/自动保存，路径 B 的单章候选替换或保留。

## T09｜Exporter 与最新版本导出

**目标与价值**：让 Markdown、PDF 和复制全文始终以最新保存版本、明确的来源与逐字稿范围输出。

- **范围**：Exporter、v3 export route、Markdown 组合、WeasyPrint PDF、文件名净化、复制所需的内容组合 endpoint/view。
- **非范围**：不添加 Word/Notion/Obsidian；不在数据库存储导出文件；不为 PDF 引入浏览器/Node Mermaid 渲染。
- **允许修改模块**：新增 `vtn/exports/exporter.py`、`vtn/adapters/pdf.py`、`vtn/web/note_routes.py`、tests。
- **依赖**：T07。
- **实现要点**：默认仅笔记；选择时追加“生成依据逐字稿”并从新页输出 PDF 附录；来源可包含/排除；PDF Mermaid 用已保存结构化文字；浏览器复制必须先等待未保存编辑 flush。
- **自动验收**：六种 format/content/source 组合、最新版本而非 AI 初始版本、PDF 新页、Markdown 分隔线、Content-Disposition 安全文件名、Clipboard 失败仅提示不改数据。
- **安全与兼容**：清理临时 HTML/PDF；文件名去路径/控制字符且限长；不把原始 Mermaid 错误暴露给用户。
- **UI/E2E 对应**：笔记 18；路径 A 的 Markdown/PDF/复制、范围及来源切换。

## T10｜浏览器历史导入、设置边界与迁移兼容

**目标与价值**：把现有本地用户记录安全移入新事实源，同时保证旧页面、旧接口和 LLM 设置仍可用。

- **范围**：一次性 `vtn-transcripts`/`vtn-history` 导入、迁移标记、旧路由保留、设置 API 掩码与权限、legacy 路由映射。
- **非范围**：不删除旧接口、不清除 localStorage、不切根路由、不部署服务。
- **允许修改模块**：`vtn/storage/migrations.py`、`vtn/web/settings_routes.py`、migration routes、最小 `app.py` 装配与 migration tests。
- **依赖**：T03、T07。
- **实现要点**：前端仅在首次进入新页面请求导入；后端去重、导入后前端写 `vtn-v3-migration-complete`，保留旧数据一个发布周期；`/api/settings` 不回显密钥；legacy parser/notes 不出现在双入口导航。
- **自动验收**：重复导入幂等、导入解析/成品后关联正确、旧 key 不被删除、设置响应掩码、文件权限仅当前用户、旧路由 smoke tests。
- **安全与兼容**：兼容不等于继续使用 localStorage 作为正文事实源；任何旧接口删除必须单独 ticket 和用户确认。
- **UI/E2E 对应**：笔记 13、20 及解析 05 的历史连续性；两条路径均能从迁移后的历史打开。

## T11｜锁定 UI 外壳、应用状态与真实 workflow client

**目标与价值**：把独立原型的视觉合同转换为真实应用的公共壳、投影状态和可靠网络客户端，而不重新设计。

- **范围**：`static/app.html`、CSS tokens/components/pages、app-state、workflow client、dialog helper、双导航、acceptance mode/fake fixture 装配。
- **非范围**：不在本 Ticket 实现具体 Parser/Notes 业务页面；不使用 CDN；不改变原型视觉或增加一级导航。
- **允许修改模块**：新增 `static/app.html`、`static/css/*`、`static/js/app-state.js`、`workflow-client.js`、`dialogs.js`、`static/vendor/*`、frontend unit tests。
- **依赖**：T01（ID/错误/事件契约）；可与 T02/T04 并行。
- **实现要点**：所有渲染从投影而非复制 HTML；维护 task/record/note、事件游标和未保存编辑标记；GET SSE reconnect + GET fallback；依赖 marked/DOMPurify/Turndown/Mermaid 全部 vendored；`?acceptance=1` 才加载固定 fake adapter。
- **自动验收**：无 CDN 请求、two-tab active state、SSE after cursor/reconnect UI 测试、错误投影、开发控制台默认隐藏、固定 fixture 截图稳定。
- **安全与兼容**：DOMPurify 在任何 Markdown 插入前执行；不加载未验证的封面 URL；旧 `static/parser.html`、`static/index.html` 不改。
- **UI/E2E 对应**：全部 27 状态的公共布局、颜色语义和导航连续性；路径 A/B 的切页基础。

## T12｜真实投影接入：解析、笔记、阅读与对话框

**目标与价值**：用真实 v3 数据驱动锁定页面，使全部状态、文案和跨阶段字段连续，而非继续依赖假数据模板。

- **范围**：parser view、notes input/recommendation/generation/recovery view、阅读/编辑/候选/导出/历史 view 与删除确认；标题、需求、来源、版本、文件名贯穿绑定。
- **非范围**：不改变后端领域规则，不新增 UI 合同外能力，不切换根路由。
- **允许修改模块**：`static/js/parser-view.js`、`notes-view.js`、`note-document.js`、`main.js`、`dialogs.js`、对应 CSS 与 E2E tests。
- **依赖**：T03–T11。
- **实现要点**：每个页面状态只来自 task/note/history projection；解析带入自动开始预读；独立输入明确点击分析；direct/outline 使用不同视图；编辑 650 ms debounce + flush；所有 DELETE 先显示约定范围；反向打开关联笔记。
- **自动验收**：浏览器 E2E 以 fake adapters 完整跑路径 A/B；断言标题、需求、来源、当前版本和导出名称无漂移；27 状态逐项可达；控制台模式可复现全部状态。
- **安全与兼容**：媒体/导出调用只经记录或笔记 ID；不把 API Key 放入前端状态；用户可见偏差必须先获确认。
- **UI/E2E 对应**：全部 27 状态；路径 A/B 的主功能整合 Ticket。

## T13｜全栈合同回归、视觉验收与受控根路由切换

**目标与价值**：在不破坏旧版本的前提下，证明确实实现了锁定合同，并在用户确认后才让真实应用成为默认入口。

- **用户提供的真实验收样本**：
  - 平台：Bilibili。
  - 标题：`心理学：亲密关系中的控制欲破解路径：分离创伤，客体认同，认知固化三重根源解读`。
  - BV 号：`BV1zR4xzRECc`。
  - 完整链接：`https://www.bilibili.com/video/BV1zR4xzRECc?vd_source=eead6df7744cee5494396b8478260e72`。
  - 用途：实现完成后的真实本地浏览器全量验收；用于验证完整链接识别、Bilibili 解析、来源信息、Whisper 转录、带入笔记和后续成品链路。
- **范围**：模块/SQLite/HTTP/E2E/视觉测试、错误监测、性能资源约束、真实端到端验收包、受控根路由切换开关。
- **非范围**：不自动宣布 UI 合同通过，不删除旧接口/页面，不部署或开发移动端。
- **允许修改模块**：`tests/*`、测试 fixtures、visual baseline 元数据、最小 `app.py` 路由装配、验收文档；根路由只在用户确认后变更。
- **依赖**：T03–T12。
- **实现要点**：使用 fake adapters 做确定性 1440×1050 截图并对照基线；真实本地 smoke 与两条路径在隔离环境执行；记录页面运行时错误为 0；为每个稳定错误码、恢复和删除边界提供回归。
- **自动验收**：所有单元、集成、HTTP、浏览器 E2E、27 状态视觉回归通过；自动化测试使用固定 fake adapters 和本地 fixtures，不依赖该真实视频或外部网络；LLM 未配置的 parser 独立 smoke；刷新/SSE 重连；不级联删除；`git diff --check`；新代码无 `shell=True` 用户输入拼接。
- **人工浏览器全量验收**：实现完成后，由执行者从根地址开始亲自操作浏览器，完整走通路径 A 和路径 B，逐项检查 27 个状态、跨阶段字段、失败恢复、历史关联、导出和删除边界；发现可复现缺陷后必须修复，并重新跑受影响路径及相关回归。只有两条路径从头到尾均通过、页面运行时错误为 0，才可交给用户最终验收。
- **安全与兼容**：4174 仅用于原型对照，真实验收另行记录端口；用户实际点击并确认前，`/` 继续保持旧入口，旧 API 和 legacy 页面可访问。
- **UI/E2E 对应**：覆盖矩阵的最终 owner；路径 A/B 及用户最终点击验收。

## 交付与停点

本文件与覆盖矩阵已经由用户确认。执行者应从 T01 开始，并在每个 Ticket 完成时提交独立验证记录；全部实现完成后必须先由执行者进行浏览器全量点击、修复缺陷并重跑，再交给用户最终验收。T13 的根路由切换仍需要真实页面验收后再次获得用户确认。
