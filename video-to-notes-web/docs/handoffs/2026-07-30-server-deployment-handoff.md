# 视频解析器 + 自适应笔记生成器：服务器部署交接

日期：2026-07-30

## 1. 下一轮目标

下一轮正式进入“部署到服务器”的准备与实施。

第一步必须先完成只读部署审计，并和用户确认服务器类型、操作系统、域名、访问范围、是否需要登录鉴权、数据备份要求和可接受成本。当前应用最初按本地个人工具设计，未经安全审计前不得直接暴露到公网。

## 2. 唯一允许操作的目录

```text
/Users/yubo/.codex/worktrees/8f75/Claude code test/video-to-notes-web
```

所有命令必须显式使用这个绝对路径作为 workdir。

绝对禁止在以下位置读取后写入、修改、测试、启动服务或部署：

```text
/Users/yubo/Claude code test/video-to-notes-web
/Users/yubo/.codex/worktrees/fded/Claude code test/video-to-notes-web
/Users/yubo/.codex/worktrees/383b/Claude code test/video-to-notes-web
任何其他 worktree
```

不得切换根路由，不得清理或覆盖用户已有改动，不得删除历史数据，不得回显任何凭证。

## 3. 新对话开始前必须完整阅读

按顺序从头到尾阅读：

1. `docs/handoffs/2026-07-30-server-deployment-handoff.md`（本文件）
2. `docs/handoffs/2026-07-30-complete-project-next-optimization-handoff.md`
3. `CONTEXT.md`
4. 上述旧交接要求继续阅读的旧交接、ADR、技术规格、实现文件与测试

不要依赖旧对话记忆。先核验工作目录、4176 服务、数据库和 Git 状态，再开始部署设计。

## 4. 当前运行状态

- 页面入口：`http://127.0.0.1:4176/next`
- 当前监听进程：PID `81239`
- 监听范围：`127.0.0.1:4176`
- 当前转录 provider：Cloudflare（只核验配置，不要自动发起真实请求）
- 当前数据库：项目内 `data/vtn.sqlite3`
- 不得改回旧的 `/tmp/vtn-*.sqlite3`

2026-07-30 交接时数据库只读统计：

| 数据 | 数量 |
| --- | ---: |
| 解析记录 | 11 |
| 笔记任务 | 5 |
| 成品笔记 | 2 |

SQLite 当前有 `-wal` 和 `-shm` 文件。服务器部署必须设计持久卷、单实例/并发策略、备份与恢复流程；不能把数据库放进临时容器文件系统。

## 5. 本轮已经完成的产品改动

### 5.1 历史中心

- 顶部增加醒目的“解析历史”和“笔记历史”入口。
- 两种历史入口支持跨模块切换。
- 修复历史为空的根因：此前服务误连空的 `/tmp` 数据库，现已恢复项目数据库。
- 最新优化：点击任一历史入口后，等待历史加载完成并平滑滚动到历史区域，使历史直接出现在视野中。
- `prefers-reduced-motion: reduce` 下改为立即定位。

主要文件：

- `static/app.html`
- `static/app.css`
- `static/app-prototype.js`
- `static/real-app.js`
- `tests/history-navigation-browser.mjs`

### 5.2 全流程动画

已引入项目本地 GSAP，并覆盖：

- 解析器首页入场、表单焦点、解析状态、逐字稿展开/收起、历史卡片
- 解析提交、进度、成功、失败、历史
- 笔记输入、预读、推荐、自定义、大纲、逐章生成、失败与恢复
- 完成、阅读、编辑、导出、笔记历史
- 解析器与笔记生成器的模块切换
- 动态卡片微交互、阅读章节滚动揭示
- 减少动态效果无障碍模式

主要文件：

- `static/motion.js`
- `static/vendor/gsap/gsap.min.js`
- `static/vendor/gsap/ScrollTrigger.min.js`
- `package.json`
- `package-lock.json`
- `tests/full-flow-motion-browser.mjs`
- `tests/parser-motion-browser.mjs`
- `tests/parser-motion-interactions-browser.mjs`
- `tests/transcript-motion-browser.mjs`

视觉验收录像：

```text
dogfood-output/full-flow-motion-2026-07-30/videos/full-flow-motion-verified.webm
```

## 6. 已通过的测试基线

后端：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

结果：`Ran 71 tests ... OK`

关键浏览器回归已通过：

- `tests/history-navigation-browser.mjs`
- `tests/full-flow-motion-browser.mjs`
- `tests/parser-motion-browser.mjs`
- `tests/parser-motion-interactions-browser.mjs`
- `tests/transcript-motion-browser.mjs`
- `tests/transcript-toggle-browser.mjs`
- `tests/parser-failure-browser.mjs`
- `tests/xhs-platform-detection-browser.mjs`

最新历史定位测试输出：

```json
{"ok":true,"prominent":true,"crossViewNavigation":true,"historyInViewport":true}
```

最新全流程动画测试输出：

```json
{"ok":true,"noteStates":13,"parserStates":4,"reducedMotion":true}
```

真实页面只读验收：

- 笔记历史进入 1050px 高视口的主要区域。
- 解析历史标题滚动到视口顶部附近。
- 控制台和页面错误为空。
- 验收没有触发真实 Cloudflare 或 LLM 请求。

## 7. Git 与工作区风险

- 当前 HEAD：`beb0806`
- 当前处于 detached HEAD（`git branch --show-current` 为空）。
- 工作区有大量未提交、未跟踪和项目上层的既有改动。
- 不得 reset、checkout、clean、删除、覆盖或“整理”这些内容。
- 不得自动 commit、push、merge 或创建 PR。
- 部署前必须先制定如何把当前 8f75 的完整可用状态安全固化到明确分支/提交；执行任何 Git 写操作前向用户说明并取得确认。

## 8. 当前部署缺口

只读扫描未发现以下部署文件：

- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt` / `pyproject.toml` / `uv.lock`
- `Procfile`
- Render/Fly/Railway/Vercel 部署清单
- `.openai/hosting.json`

现有 README 的部分描述已经落后，例如仍写 `localhost:3000` 和浏览器 localStorage 历史；真实新版使用 `/next`、4176 验收服务和 SQLite 持久化。部署时不要把旧 README 当作完整生产说明。

服务器部署至少需要解决：

1. 明确并锁定 Python、系统包和 Node/静态依赖。
2. 安装并验证 FFmpeg、yt-dlp、WeasyPrint/字体等运行依赖。
3. Cloudflare 与 LLM 凭证只能通过服务器环境变量或秘密管理注入。
4. SQLite 数据目录持久化、备份、恢复和单实例约束。
5. 生产进程管理、反向代理、HTTPS、上传大小、超时和日志轮转。
6. 公开访问前的身份认证、权限控制、CSRF/CORS、SSRF/任意 URL 获取、文件上传下载与速率限制安全审计。
7. Bilibili、YouTube、小红书在服务器 IP/无桌面登录环境下的真实兼容性。
8. 不在生产部署或验收中使用真实用户历史数据做破坏性测试。

## 9. 下一对话建议执行顺序

1. 完整阅读本文件及它要求的上下文。
2. 只读核验 8f75 工作目录、Git 状态、4176、Cloudflare provider、数据库计数和测试基线。
3. 询问并确认目标服务器信息；如果用户已经提供，复述关键约束。
4. 做部署安全与架构审计，给出最小可行部署方案和回滚方案。
5. 先在隔离的临时数据库和假 adapters 下完成容器/服务器本地验证。
6. 用户确认后，再进行 Git 固化、服务器写入、凭证配置、域名/HTTPS 或真实外部请求。
7. 部署后分别验证健康检查、解析历史、笔记历史、静态资源、SQLite 持久化和重启恢复。

## 10. 明确禁止事项

- 不自动发起真实 Cloudflare/LLM 请求。
- 不回显、读取进输出或写入仓库任何 Token、Cookie、私钥或密码。
- 不提交、推送、删除或覆盖旧数据。
- 不清理无关改动。
- 不改动源工作树或其他 worktree。
- 不把当前本地个人工具未经安全审计直接开放到公网。
- 不在未确认服务器目标与回滚方案前执行部署。

## 11. 给下一位代理的第一句任务

正式接手 `video-to-notes-web` 的服务器部署。先完整阅读部署交接与其引用文件，只读核验当前 8f75 工作区和部署缺口；不要触发真实 Cloudflare/LLM 请求，不要执行 Git 写操作或服务器部署。完成后用简短中文汇报部署前置条件，并等待/收集用户的服务器信息。
