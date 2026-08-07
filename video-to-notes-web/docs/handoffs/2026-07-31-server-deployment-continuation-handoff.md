# Video to Notes 公网部署续接交接（2026-07-31）

## 0. 新对话必须遵守的边界

正式续接“视频解析器 + 自适应笔记生成器”的内测公网部署。

唯一允许操作的项目工作目录：

`/Users/yubo/.codex/worktrees/8f75/Claude code test/video-to-notes-web`

即使新对话 cwd 显示为源工作树，也绝对不能在那里读取后写入、修改、测试或启动服务。所有项目命令必须显式使用上述 8f75 绝对 workdir。不得操作源工作树、fded、383b 或其他 worktree。

开始前必须从头到尾完整阅读：

1. 本文件。
2. `docs/handoffs/2026-07-30-server-deployment-handoff.md`
3. `docs/handoffs/2026-07-30-complete-project-next-optimization-handoff.md`
4. `CONTEXT.md`
5. 上述文件要求的 ADR、技术规格、旧交接、实现与测试。

不得依赖旧对话记忆替代文件阅读。

安全约束：

- 不得提交、推送、删除或覆盖旧数据。
- 不得回显 Cloudflare、LLM、SSH、session secret 或内测码内容。
- 不得上传本地 `data/vtn.sqlite3`，线上必须继续使用新建的空数据库。
- 不得自动发起真实 Cloudflare/LLM 请求；配置凭证并启用付费调用前需要明确告知用户。
- 不得修改服务器已有博客、热搜、NoteFlow 项目或默认根路由。
- 不得使用或依赖 `yubo.tech`；用户已明确说明该域名不可用。

## 1. 用户确认的产品与部署方向

当前目标不是商业化，而是：

1. 作为求职作品在公网展示。
2. 少量朋友可以真实体验。
3. 控制 Cloudflare 转录和 LLM 生成成本。
4. 暂不做注册系统、设置页面或完整管理后台。
5. 未来另做“本地个人版”：用户配置自己的转录/LLM API，或使用本地 Whisper；不要与本轮公网作品版混在一起。

用户已明确赞成当前方案：

- 页面和固定示例公开可看。
- 真实解析和真实笔记生成需要独立内测码。
- 每个内测码拥有独立额度、独立历史和可撤销资格。
- 服务端统一持有 provider 密钥，普通测试者看不到。
- 首批默认额度：30 分钟转录、5 次笔记、单视频最长 20 分钟。
- owner 内测码本轮创建为 120 分钟转录、20 次笔记、单视频最长 20 分钟。

## 2. 无自有域名时选定的公网入口

用户确认没有可用域名，`yubo.tech` 不可使用。

已核验并选定临时 HTTPS 主机名：

`video-notes-8-135-44-86.sslip.io`

它当前解析到：

`8.135.44.86`

依据：sslip.io/nip.io 官方说明支持把 IP 嵌入主机名，并通过 HTTP-01 为单个主机名签发正常的 Let’s Encrypt 证书。

预期最终入口：

`https://video-notes-8-135-44-86.sslip.io/next`

这是临时求职/内测入口；以后有正式域名时再迁移。

## 3. 本轮已经完成的本地代码改造

### 3.1 内测授权与会话

新增：

- `vtn/access.py`
- `scripts/manage_invites.py`

实现内容：

- 内测码使用 scrypt 哈希保存，不保存明文。
- 通过 server session secret 生成/校验 HttpOnly session cookie。
- 生产环境 cookie 为 `Secure`、`SameSite=Lax`。
- `/api/v3/access/login`
- `/api/v3/access/logout`
- `/api/v3/access/status`
- 未授权访问受保护 API 返回 `401 ACCESS_REQUIRED`。
- access control 未启用的本地模式仍返回 `enabled:false`，保持原开发流程兼容。

### 3.2 额度与付费调用开关

数据库新增：

- `access_grants`
- `access_usage`
- `parser_records.access_id`
- schema migration version 3

当前额度行为：

- 转录按照视频 metadata 中的 `duration_seconds` 扣秒数。
- 单视频超过 `max_video_seconds` 时，在下载和转录前停止。
- 剩余额度不足时，在 Cloudflare 调用前停止。
- 笔记额度按照新建 note task 扣 1 次。
- 同一转录任务重试使用相同 reference，不重复扣转录额度。
- `VTN_PAID_CALLS_ENABLED=0` 时，真实转录与笔记任务会返回 `PAID_CALLS_PAUSED`。

尚未完成、启用真实付费调用前应处理或明确接受：

- 当前额度是“预留式扣减”，系统/provider 失败不会自动退回；此前讨论希望系统故障退款，需要补 usage refund/release 行为或明确保守计费。
- 尚未实现整台服务器全局只运行 1 个重任务的并发锁。
- note task 在深层输入校验失败前可能已经预留 1 次额度；应先完成可观察输入校验或实现失败回滚。

### 3.3 历史隔离

生产 access 模式下：

- 后端忽略浏览器伪造的 `device_id`，使用内测资格 ID 作为 owner。
- parser task、parser record、note task、note 读取与列表按 owner 隔离。
- 跨内测码直接猜 ID 返回 404。
- 下载、删除、编辑、导出、候选章节、完整性复查均先做 ownership 检查。

### 3.4 旧接口防绕过

access middleware 在托管版禁用以下旧接口，避免绕过 v3 额度：

- `/api/search`
- `/api/process`
- `/api/export-pdf`
- `/api/settings`
- `/api/test-connection`
- `/api/v3/migrations/browser-history`
- `/api/download/*`

需要继续处理的安全缺口：

- `/api/proxy-image` 仍开放给已授权用户，当前 legacy 实现可以请求任意 URL，存在 SSRF 风险。公网开放前应限制为解析记录中的 public HTTP(S) thumbnail，或在 hosted mode 禁用并接受封面不代理。

### 3.5 公开展示与内测码 UI

修改：

- `static/app.html`
- `static/app.css`
- `static/app-prototype.js`
- `static/real-app.js`

实现：

- 页面公开可打开。
- “查看公开示例”展示固定解析结果，不调用后端付费服务。
- 真实 API 返回 401 时弹出内测码 dialog。
- 登录后页头显示内测标签、剩余转录分钟和剩余笔记次数。
- 未启用 access control 的本地开发模式隐藏内测 UI。

### 3.6 生产运行文件

新增：

- `requirements.txt`
- `deploy/video-to-notes.service`
- `deploy/nginx-video-to-notes-http.conf`
- `deploy/nginx-video-to-notes-https.conf`
- `deploy/video-to-notes.env.example`

其他生产修正：

- 新增 `/api/health`。
- PDF 导出不再写死 `/opt/homebrew/bin/weasyprint`，改为优先 `shutil.which("weasyprint")`。
- systemd 设置 `UMask=0077`、单 worker、内存上限 1400M、只写应用 data 和生产数据库目录。

## 4. 本地测试证据

未发起真实 Cloudflare/LLM 请求。

已通过：

- Python：76 项，全绿。
- `tests/access-gate-browser.mjs`：公开示例、真实操作授权、额度显示全绿。
- `tests/history-navigation-browser.mjs`：历史入口醒目、跨视图、滚入视野全绿。
- `tests/boundary-browser.mjs`：PDF、章节候选、恢复、非级联删除、旧历史迁移全绿。

为消除 Playwright strict locator 歧义，`tests/boundary-browser.mjs` 的“恢复任务”定位增加了 `exact:true`。

本机 4176 当前已停止；断线后没有重启。本轮浏览器验收使用 4175 + `VTN_FAKE_ADAPTERS=1` + `/tmp` 临时数据库，验收后已停止。

## 5. Git / 工作区状态

Git 根仍是父目录：

`/Users/yubo/.codex/worktrees/8f75/Claude code test`

工作区原本就高度 dirty/untracked；不要清理或覆盖用户修改，不要提交/推送。

本轮相关文件包括：

- `app.py`
- `vtn/access.py`
- `vtn/bootstrap.py`
- `vtn/storage/schema.sql`
- `vtn/storage/sqlite.py`
- `vtn/web/api.py`
- `vtn/workflows/parser.py`
- `vtn/workflows/notes.py`
- `static/app.html`
- `static/app.css`
- `static/app-prototype.js`
- `static/real-app.js`
- `tests/test_access_http.py`
- `tests/access-gate-browser.mjs`
- `tests/boundary-browser.mjs`
- `requirements.txt`
- `scripts/manage_invites.py`
- `deploy/*`

## 6. 阿里云服务器信息与已有项目（只供续接）

服务器：

- IP：`8.135.44.86`
- SSH 用户：`root`
- SSH key：`/Users/yubo/.ssh/aliyun_hot`
- Ubuntu 24.04
- 2 CPU
- 约 1.6 GiB RAM + 2 GiB swap
- 40G 磁盘，之前约 28G 可用

已有服务，禁止破坏：

- 80：个人博客（Nginx `/var/www/blog`）
- 8765：今日热搜（Nginx `/var/www/hot` + Node 3001）
- 8766：NoteFlow（Nginx `/var/www/noteflow`）
- PM2 `hot-api` 保持在线

## 7. 本轮已经发生的服务器写入

以下不是计划，而是已经完成，续接时不得重复假设为空：

### 7.1 修复服务器 `/tmp`

发现 `/tmp` 被错误设置为 `0700 root:root`，导致 apt 无法创建临时文件。

已恢复为标准 `1777`。

### 7.2 安装/更新系统依赖

已通过 apt 安装：

- `ffmpeg`
- `python3-venv`
- `rsync`

apt 同时把部分 Ubuntu 24.04 Python/图形/媒体依赖更新到当前镜像版本。安装成功，现有 Nginx/PM2 服务未被替换。

### 7.3 新增生产用户与目录

已创建：

- 系统用户 `vtn`
- `/opt/video-to-notes`
- `/opt/video-to-notes/data`
- `/var/lib/video-to-notes`
- `/var/www/certbot`

### 7.4 上传应用和 Python 虚拟环境

已经 rsync 到 `/opt/video-to-notes`：

- `app.py`
- `requirements.txt`
- `vtn/`
- `static/`
- `scripts/`

未上传：

- 本地 `data/vtn.sqlite3`
- node_modules
- dogfood 输出
- 旧历史数据

已创建 `/opt/video-to-notes/.venv` 并安装 requirements。

服务器验证版本：

- yt-dlp `2026.03.17`
- FFmpeg `6.1.1`
- WeasyPrint `68.1`

### 7.5 生产设置与环境文件

已把本地 `data/settings.json` 通过 SSH 传到：

`/opt/video-to-notes/data/settings.json`

远端权限：`0600 vtn:vtn`。

不得回显其内容或 LLM key。

已生成：

`/etc/video-to-notes.env`

远端权限：`0600 root:root`。

当前关键状态：

- `VTN_ACCESS_CONTROL=1`
- `VTN_COOKIE_SECURE=1`
- `VTN_PAID_CALLS_ENABLED=0`
- `VTN_DATABASE_PATH=/var/lib/video-to-notes/vtn.sqlite3`
- `VTN_TRANSCRIBER=local`
- session secret 已在服务器随机生成，禁止回显
- 尚无 Cloudflare account/token

### 7.6 systemd 服务

已安装并启用：

`/etc/systemd/system/video-to-notes.service`

当前状态最后核验为 active。

内部监听：

`127.0.0.1:8767`

最后核验：

- `/api/health` 返回 `{"ok":true,"service":"video-to-notes"}`
- 常驻内存约 34MB
- 单 uvicorn worker

新生产数据库：

`/var/lib/video-to-notes/vtn.sqlite3`

数据库、WAL、SHM 已收紧到 `0600 vtn:vtn`，systemd 已增加 `UMask=0077`。

### 7.7 owner 内测码

已创建 owner grant：

- 120 分钟转录
- 20 次笔记生成
- 单视频最长 20 分钟

明文只保存在服务器：

`/root/video-to-notes-owner-invite.txt`

权限：`0600 root:root`。

禁止在工具输出、交接文件或聊天中回显。最终需要让用户使用时，建议通过 SSH 提取 `INVITE_CODE` 后直接管道到本机 `pbcopy`，只告诉用户“已复制到剪贴板”，不要输出内容。

### 7.8 Nginx 当前部分完成状态

已安装：

- `/etc/nginx/sites-available/video-to-notes`
- `/etc/nginx/sites-enabled/video-to-notes`（符号链接）

当前内容来自：

`deploy/nginx-video-to-notes-http.conf`

Nginx 语法检查成功并 reload。

该临时 HTTP 配置的作用主要是 ACME challenge；它的普通 location 当前 `return 302 /next`，访问 `/next` 会形成自重定向，不应视为已上线。付费调用仍暂停，因此没有额度风险。

尚未执行 certbot，尚未开放正常 HTTPS 页面。

## 8. Cloudflare 凭证现状

断线前本地 4176 进程曾拥有 Cloudflare account/token，但该进程已经退出。

检查结果：

- 当前 shell 无凭证。
- launchctl 无凭证。
- 项目文件与 shell 配置无凭证明文。
- Codex 历史日志只有变量引用/假值，无法安全恢复真实 token。

因此当前没有向服务器写入 Cloudflare 凭证，也没有发起真实请求。

后续需要用户重新提供或在其 Cloudflare 后台创建/取得权限最小化 token。不要让 token 出现在聊天回显或命令输出中；优先让用户在本机/服务器安全输入，或使用不回显的 stdin 流程。

## 9. 新对话的精确下一步

按顺序继续：

1. 完整阅读要求文件并只读复核本交接所述状态。
2. 检查 `systemctl is-active video-to-notes`、内部 `/api/health`、Nginx 当前配置和现有项目端口，确认未漂移。
3. 修复/禁用 hosted mode 的 `/api/proxy-image` SSRF 风险。
4. 为 `video-notes-8-135-44-86.sslip.io` 执行 Let’s Encrypt HTTP-01：
   - `certbot certonly --webroot -w /var/www/certbot -d video-notes-8-135-44-86.sslip.io --non-interactive --agree-tos`
5. 证书成功后，用本地 `deploy/nginx-video-to-notes-https.conf` 替换远端新站点文件；先 `nginx -t`，成功才 reload。
6. 外网验证：
   - HTTP 正确跳 HTTPS。
   - HTTPS `/next` 200。
   - `/api/health` 200。
   - 未授权 `/api/v3/parser/records` 401。
   - 公开示例无需登录可见。
   - 不使用/不修改 `yubo.tech`。
7. 用 owner 内测码登录验证授权与额度 UI；当前付费调用开关保持关闭，不测试真实转录/LLM。
8. 若用户补充 Cloudflare 凭证：
   - 安全写入 `/etc/video-to-notes.env`。
   - 改为 `VTN_TRANSCRIBER=cloudflare`。
   - 在处理扣额失败回滚/接受规则后，再将 `VTN_PAID_CALLS_ENABLED=1`。
   - 重启服务后只做用户明确授权的一次短视频真实验收。
9. 补齐并验证：系统失败额度回滚、全局单重任务并发控制、输入校验前不扣 note 额度。
10. 执行代码审查与完整本地/线上非付费回归；不得提交或推送。

## 10. 当前终态说明

本轮在用户要求切换新对话时，部署处于：

- 本地功能已实现并通过非付费测试。
- 服务器内部应用已 active。
- 生产空数据库已创建并加固权限。
- owner 内测码已创建并安全保存。
- 临时 HTTP Nginx 站点已挂载用于 ACME。
- HTTPS 证书尚未申请。
- 公网正常页面尚未完成。
- Cloudflare 凭证尚未配置。
- 付费调用全局暂停。

新对话必须从这里继续，不要重新部署一遍，也不要把“HTTP 站点已存在”误判成公网部署完成。
