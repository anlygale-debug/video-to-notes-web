# Cloudflare 云端转录与下一轮测试优化：完整交接

日期：2026-07-28 16:30 CST

## 1. 新对话的工作目标

继续“视频解析器 + 自适应笔记生成器”的转录质量测试与优化，重点是：

1. 在不接入 LLM 修正文稿的前提下，继续减少 Cloudflare `whisper-large-v3-turbo` 的中文同音字和专有名词错误。
2. 用可重复、可比较的 A/B 测试评估参数、提示词和术语表，不凭主观印象改模型。
3. 保持 2 核 2GB 云服务器可部署：服务器不加载本地 Whisper 模型，长音频低内存、顺序处理。
4. 保持现有 `/next` UI、逐字稿简体化、默认预览和原位展开/收起合同不回退。

这是一个真正空白的新对话时，必须先完整阅读本文件、项目 `CONTEXT.md`、本文件列出的实现和测试文件。不要依赖旧对话历史。

## 2. 唯一允许工作的目录

```text
/Users/yubo/.codex/worktrees/8f75/Claude code test/video-to-notes-web
```

Codex 界面默认 cwd 可能显示为：

```text
/Users/yubo/Claude code test/video-to-notes-web
```

那是源工作树，不是本任务目录。所有读取、编辑、测试和服务命令必须显式使用上面的 `8f75` 绝对路径或把 `workdir` 指向它。

禁止修改：

```text
/Users/yubo/Claude code test/video-to-notes-web
/Users/yubo/.codex/worktrees/fded/Claude code test/video-to-notes-web
```

## 3. 用户已经确认的产品与技术决定

- 逐字稿最终必须统一为简体中文。
- 不使用 LLM 对逐字稿进行二次纠错；当前只优化 ASR、音频预处理、提示词和可维护术语表。
- 本地 Whisper `tiny` 继续作为无云端配置时的默认回退，不删除。
- 2 核 2GB 云服务器不适合常驻 OpenAI Whisper `small`；swap 不能当作真实内存和吞吐能力。
- 当前云端正式候选为 Cloudflare Workers AI：`@cf/openai/whisper-large-v3-turbo`。
- Cloudflare 配置必须显式启用：`VTN_TRANSCRIBER=cloudflare`；不能因环境里偶然存在 Token 就静默切换。
- Cloudflare 不可用或未选择时保留本地 `tiny`，但不要在一次失败任务中自动把云端失败静默降级为低质量 tiny 结果。
- 长音频必须切段后顺序上传，避免请求体上限、峰值内存和并发额度问题。
- API Token 只能通过运行环境传入，不写进代码、README、测试、Git 或交接文件。
- 当前 `/next` 仍是正式验收路由；不要切根路由。
- 不做公开部署、账号系统或移动端扩展，除非用户在新对话明确改变范围。
- 不提交、不推送、不删除用户数据，不覆盖已有真实逐字稿。
- 用户最终点击确认前，不宣布 UI 合同锁定。

## 4. Cloudflare 凭证与安全状态

用户已经把最新的 Cloudflare Account ID 和 API Token 保存到 macOS“备忘录”最新一条。

已验证的非敏感事实：

- Account ID 长度：32 位。
- Token 长度：53 位。
- Cloudflare 官方 `/user/tokens/verify` 返回 `success: true`、`status: active`。
- 旧 Token 曾被用户粘贴进聊天，随后已撤销；不要使用旧 Token。
- 新 Token 没有出现在项目文件、测试输出或交接文件中。
- 用户明确授权 Codex 从最新备忘录读取 Account ID 和 Token，并只用于本项目的 Cloudflare Workers AI 配置与测试。

严格规则：

- 读取凭证时不得把原文打印到工具输出或聊天。
- 不读取浏览器 cookie、localStorage、密码库或无关备忘录。
- 不要把真实 Token 放进 shell 命令字符串；可使用权限 `0600` 的临时配置文件或进程环境。
- 临时凭证文件在上一对话结束前已经删除：
  - `/tmp/vtn-cloudflare-auth-20260728.conf`
  - `/tmp/vtn-cloudflare-transcribe-20260728.conf`
  - `/tmp/vtn-cloudflare-runtime-20260728.env`
- 当前 4176 进程已把凭证读入内存；如果重启进程，必须重新从备忘录安全读取或由用户在终端设置环境变量。
- 不要为了方便把 Token 持久化到项目目录。若未来要写入 macOS Keychain、服务器 `/etc` 环境文件或 secret manager，必须在动作发生前向用户说明并确认持久访问范围。

## 5. 当前代码实现

### 5.1 Cloudflare 转录适配器

文件：`vtn/adapters/transcription.py`

已实现 `CloudflareTranscriber`：

- 模型：`@cf/openai/whisper-large-v3-turbo`。
- 输入 JSON：base64 音频。
- 固定参数：
  - `task: transcribe`
  - `language: zh`
  - `vad_filter: true`
  - `beam_size: 5`
  - `condition_on_previous_text: true`
- 可选 `initial_prompt`。
- Cloudflare 输出继续经过 `zhconv(..., "zh-cn")`，保证简体中文。
- 小于等于 6 MiB 的音频直接上传。
- 大于 6 MiB 时用 FFmpeg：16 kHz、单声道、64 kbps MP3、每段 600 秒；逐段顺序请求并按顺序合并。
- HTTP 401/403 映射为：
  - code：`TRANSCRIPTION_AUTH_FAILED`
  - retryable：`false`
- HTTP 429 和 5xx 为可重试 `TRANSCRIPTION_FAILED`。
- 使用 `certifi` 构造保持证书校验开启的 SSL context；禁止改成不验证证书。

### 5.2 启动时选择转录器

文件：`vtn/bootstrap.py`

已实现公共工厂 `build_transcriber(env=None)`：

- 未设置 `VTN_TRANSCRIBER`：`WhisperTranscriber("tiny")`。
- `local` / `tiny` / `whisper`：本地 Whisper，可通过 `VTN_WHISPER_MODEL` 改模型。
- `cloudflare`：必须同时提供：
  - `CLOUDFLARE_ACCOUNT_ID`
  - `CLOUDFLARE_API_TOKEN`
- 可选：`VTN_TRANSCRIPTION_PROMPT`。
- 未知 provider：`TRANSCRIPTION_CONFIG_INVALID`。
- Cloudflare 缺凭证：`TRANSCRIPTION_CONFIG_MISSING`。
- `VTN_FAKE_ADAPTERS=1` 的自动测试仍强制使用 `FakeTranscriber`，不会消耗云端额度。

### 5.3 简体中文版本

- `WhisperTranscriber` 明确使用 `language="zh"`、`task="transcribe"`。
- 本地和 Cloudflare 输出都经过 `zhconv`。
- 新解析记录写入 `transcript_format_version = 2`。
- 已有一条真实记录曾原位迁移到简体，迁移前数据库备份：
  `/tmp/vtn-real-smoke-20260728-2.before-simplified.sqlite3`。

### 5.4 逐字稿 UI

文件：

- `static/app.html`
- `static/app.css`
- `static/real-app.js`
- `tests/transcript-toggle-browser.mjs`

当前合同已经实现：

- 长逐字稿默认约 7 行预览并渐隐。
- 标题显示真实字符数。
- “展开完整逐字稿 ↓”在结果卡内原位展开。
- 展开后为“收起逐字稿 ↑”。
- 无弹窗、无 alert、无跳页。
- TXT/MD 下载始终可见。
- 短逐字稿完整显示并隐藏开关。
- capture 阶段阻断旧原型提示链。
- 静态资源版本为 `v4`。

## 6. 当前 4176 正式服务状态

- 地址：`http://127.0.0.1:4176/next`
- 2026-07-28 16:30 CST 监听 PID：`39456`
- 工作目录：本文件第 2 节的 8f75 工作树。
- 数据库：`/tmp/vtn-real-smoke-20260728-2.sqlite3`
- 当前进程 provider：Cloudflare（凭证仅在进程内存）。
- 最终 GET `/next`：HTTP 200。
- 当前 URL 只能从同一台 Mac 的其他浏览器访问；它不是公网网址，也不是其他设备可访问的部署地址。

如果 4176 仍在线，不要为了“确认配置”无意义重启。先用 `lsof -nP -iTCP:4176 -sTCP:LISTEN` 和只读 GET 检查。

如果必须重启：

```bash
VTN_TRANSCRIBER=cloudflare \
CLOUDFLARE_ACCOUNT_ID='<从备忘录安全读取>' \
CLOUDFLARE_API_TOKEN='<从备忘录安全读取>' \
VTN_TRANSCRIPTION_PROMPT='普通话中文视频内容，请准确识别专有名词并使用简体中文。' \
VTN_DATABASE_PATH=/tmp/vtn-real-smoke-20260728-2.sqlite3 \
python3 -m uvicorn app:app --host 127.0.0.1 --port 4176
```

不要把上面的占位符替换后再输出到聊天或工具日志。

## 7. 真实基准音频与结果

基准根目录：

```text
/tmp/vtn-asr-benchmark-20260728
```

音频：

- `/tmp/vtn-asr-benchmark-20260728/audio/clip-3m.wav`：5.5 MiB，前 3 分钟，16 kHz 单声道 PCM。
- `/tmp/vtn-asr-benchmark-20260728/audio/source.mp3`：9.0 MiB，完整来源音频。

来源视频：

- Bilibili：`BV1zR4xzRECc`
- 标题：`心理学：亲密关系中的控制欲破解路径：分离创伤，客体认同，认知固化三重根源解读`
- 作者：`ZZJ-Anna`

质量代理：18 个可从标题、语音上下文确认的短语命中数；这不是人工逐字稿 CER/WER，只能作为相对比较。

本地模型结果：

| 引擎 | 耗时 | 峰值内存 | 关键词 |
|---|---:|---:|---:|
| OpenAI Whisper tiny 当前参数 | 5.6 秒 | 795 MB | 4/18 |
| tiny + prompt + beam 3 | 18.9 秒 | 907 MB | 5/18 |
| OpenAI Whisper small 当前参数 | 28.4 秒 | 2,186 MB | 15/18 |
| small + prompt + beam 3 | 124.4 秒 | 2,041 MB | 9/18，标点退化 |
| whisper.cpp base Q5_1 | 42.9 秒 | 451 MB | 8/18 |
| whisper.cpp small Q5_1 | 87.4 秒 | 744 MB | 17/18 |

Cloudflare 结果：

| 配置 | API 耗时 | 字符数 | 关键词 |
|---|---:|---:|---:|
| generic（第一轮误用了 AI 技术领域提示） | 12.278 秒 | 970 | 16/18 |
| 视频标题 + 作者提示 | 16.146 秒 | 969 | 16/18 |
| 应用内真实 `CloudflareTranscriber` + 正确 SSL | 成功 | 962 | 已确认简体 |

Cloudflare 两轮共同缺失：

- `报备行踪` 被识别为类似“抱贝行踪”。
- `客体关系` 被识别为类似“与科技关系”。

重要结论：

- Cloudflare 相比 tiny 从 4/18 提升到 16/18，速度只从 5.6 秒变为约 12–16 秒。
- 标题 + 作者 prompt 没有改善上述两个术语，不要重复做同样实验。
- whisper.cpp small Q5_1 在该样本达到 17/18，但云服务器需要 744 MB 模型内存和更慢 CPU；Cloudflare 更适合 2GB 服务器。
- 不要把手工塞入全部“正确答案词表”后的得分冒充泛化提升。若测试术语表，必须明确术语来自生产可获得来源：标题、描述、用户自定义术语表或稳定领域词库。

结果文件：

- `results/cloudflare-whisper-large-v3-turbo.json`
- `results/cloudflare-whisper-large-v3-turbo.txt`
- `results/cloudflare-title-prompt.json`
- `results/cloudflare-title-prompt.txt`
- `results/openai-tiny-current.txt`
- `results/openai-tiny-optimized.txt`
- `results/openai-small-current.txt`
- `results/openai-small-optimized.txt`
- `results/whispercpp-base-q5_1.txt`
- `results/whispercpp-small-q5_1.txt`
- `report.md`
- `analyze_results.py`

## 8. 已完成验证

### 单元与语法

- `python3 -m unittest discover -s tests -p 'test_*.py'`
- 结果：31 项全绿。
- Python AST 语法检查通过。
- `node --check static/real-app.js` 通过。
- `git diff --check` 通过。

新增 Cloudflare 测试覆盖：

- Cloudflare 输出转简体。
- 请求参数符合官方模型合同。
- SSL context 存在且证书验证开启。
- 401/403 稳定映射且不可重试。
- 大音频 FFmpeg 切段后逐段上传并合并。
- 启动配置保留 tiny 默认并允许显式 Cloudflare。

### 浏览器测试

隔离 4175 假适配器：

- `tests/e2e-browser.mjs`：通过，路径 A/B + 27 状态。
- `tests/boundary-browser.mjs`：通过。
- `tests/parser-ui-race-browser.mjs`：通过。
- `tests/transcript-toggle-browser.mjs`：通过。
- `tests/pagination-browser.mjs`：单独使用新数据库重跑后通过，35/35/35。

分页测试第一次失败的原因不是产品 bug：当时 5 个浏览器测试并行，共用一个测试数据库，其他测试同时插入记录，破坏了分页测试“必须正好 35 条”的前提。后来换新数据库单独跑通过。今后不要把严格计数的分页测试与写同一数据库的测试并行。

正式 4176：

- `VTN_E2E_URL=http://127.0.0.1:4176 node tests/transcript-toggle-browser.mjs`
- 结果：长文本、短文本、展开/收起、0 dialog 全通过。
- 该测试通过 Playwright route 拦截假数据，不写真实数据库。
- 最终 `/next` HTTP 200。

### 真实 Cloudflare

- Token verify：active。
- 手工官方 REST 调用：HTTP 200。
- 应用内 `CloudflareTranscriber` 首次真实运行复现 macOS Python 证书链问题。
- 修复为 certifi SSL context 后再次运行成功：`CloudflareTranscriber 962 simplified=True`。

## 9. 下一轮推荐的测试优化顺序

先测试，不要立即加 UI 或重构：

### A. 建立更可信的人工参考

当前 18 个关键词只是代理。建议先对 3 分钟音频制作一份人工校对参考文本，至少完整标注容易错的 30–50 个短语，再计算：

- 字符错误率 CER。
- 关键术语准确率。
- 漏句/幻觉段数。
- 标点只做单独指标，不与字词正确率混在一起。

人工参考是下一轮最有价值的测试基础；没有它，参数优化很容易过拟合几个关键词。

### B. Cloudflare 参数小矩阵

只改一个变量，每个配置保存完整请求参数、响应、耗时和指标：

1. 当前基线：beam 5、VAD true、condition previous true、generic prompt。
2. `condition_on_previous_text=false`：观察重复/幻觉与跨句连贯性。
3. `vad_filter=false`：当前前 3 分钟连续语音，验证 VAD 是否反而切断短词。
4. `beam_size` 1、3、5：比较速度与 CER；不要默认越大越准。
5. 只使用标题中可获得的术语提示；标题+作者已测试无提升，避免原样重复。
6. 可维护用户术语表：仅加入用户真正提供的词或标题/描述可提取词，并与“手工答案全塞入 prompt”明确区分。

### C. 音频预处理

对相同语音内容比较：

- 原始 WAV。
- 16 kHz 单声道 64 kbps MP3（生产切段格式）。
- 16 kHz 单声道 FLAC 或 WAV 小段（若请求体允许）。
- 可选轻度响度归一化；不要默认做强降噪。

重点确认生产切段格式没有让 `报备行踪`、`客体关系` 等词进一步恶化。

### D. 长音频边界

使用复制/拼接的非敏感测试音频或当前完整公开音频验证：

- >6 MiB 必须切段。
- 每段 <=600 秒、顺序稳定。
- 中断一段时任务进入稳定失败状态，不保存半份解析记录。
- 临时切段目录最终清理。
- 2GB 条件下峰值内存，尤其 base64 JSON 构造阶段。
- 段边界是否丢词或重复；如有，需要短重叠窗口和去重策略，但不要先实现。

### E. 网页真实链路

在参数选定后再跑一次真实 Bilibili 链路：解析元信息 → 下载音频 → Cloudflare → 保存简体逐字稿 → `/next` 默认预览 → 展开/收起 → TXT/MD 下载。

新真实结果必须创建为候选记录；不要覆盖现有 6,286 字记录。用户人工对照并明确确认后，才能考虑替换。

## 10. 当前已知限制与待决策项

- 现在没有 UI 模型切换器；只通过环境变量选择。用户此前讨论过 UI 切换，但最终先保留 tiny 默认、Cloudflare 显式配置。不要未经确认增加切换控件。
- 当前 `initial_prompt` 是进程级配置，尚未从每个视频的标题/作者动态传入。标题 prompt 对当前样本无提升，因此不要先为它改 workflow 接口；应以新的可靠测试数据证明值得做。
- Cloudflare 的 `word_count` 在中文响应里数值不可靠，不要用于 UI 字数；UI 使用真实字符长度。
- Cloudflare 免费额度和定价会变化；新对话若要给出当前额度必须浏览 Cloudflare 官方文档。
- 当前服务配置是进程内临时状态，Mac 重启或服务重启后不会自动恢复 Cloudflare Token。
- README 已写通用环境变量说明，但没有真实凭证。
- 测试会出现 `zhconv` 的 `pkg_resources` 弃用警告和资源文件未关闭警告；当前不影响功能，尚未单独修复。
- 4176 是本地回环地址，不是公网部署网址。

## 11. 相关文件清单

开始工作前完整阅读：

1. `CONTEXT.md`
2. 本交接文件
3. `vtn/adapters/transcription.py`
4. `vtn/bootstrap.py`
5. `vtn/workflows/parser.py`
6. `tests/test_parser_workflow.py`
7. `tests/test_parser_http.py`
8. `tests/transcript-toggle-browser.mjs`
9. `static/app.html`
10. `static/app.css`
11. `static/real-app.js`
12. `README.md`
13. `/tmp/vtn-asr-benchmark-20260728/report.md`
14. `/tmp/vtn-asr-benchmark-20260728/analyze_results.py`

适用技能：

- 改实现时使用 `tdd`，公共 seam 为 `Transcriber.transcribe(audio_path)`、`build_transcriber(env)` 和 `/api/v3/parser/tasks` / `/next` 用户链路。
- 做浏览器验收时遵守当前可用 Browser/Chrome 技能说明。
- 读取备忘录凭证时使用 Computer Use 技能，只读最新目标备忘录，不回显敏感内容。

## 12. 工作树与改动边界

仓库根目录含大量用户已有的修改、删除和未跟踪文件，包括上级 `.agents`、`.claude`、`skills-lock.json` 等。不要清理、恢复、覆盖或提交它们。

本轮直接相关文件：

- `README.md`
- `vtn/adapters/transcription.py`
- `vtn/bootstrap.py`
- `tests/test_parser_workflow.py`
- 之前同一任务已完成的 `static/app.html`
- `static/app.css`
- `static/real-app.js`
- `tests/transcript-toggle-browser.mjs`
- `vtn/workflows/parser.py`

`app.py` 也已有用户/前序工作修改，不要把它当作本轮 Cloudflare 新改动覆盖。

禁止：

- `git reset --hard`
- `git checkout -- ...`
- 清理未跟踪文件
- 提交或推送
- 删除真实数据库记录
- 覆盖现有逐字稿
- 修改 fded 或默认源工作树

## 13. 新对话的开场执行顺序

1. 确认 cwd 并切到 8f75 绝对工作树。
2. 完整阅读本交接、`CONTEXT.md` 和第 11 节文件。
3. `git status --short`，只识别，不清理。
4. 检查 4176 是否仍在线；不必要时不要重启。
5. 检查 `/tmp/vtn-asr-benchmark-20260728` 是否仍存在。
6. 向用户用简短中文复述：下一轮先建立更可信人工参考，再跑单变量 A/B；不要重新讨论已确认的 Cloudflare/tiny 架构。
7. 若用户明确让直接继续，先产出测试方案和预期指标；涉及真实 Cloudflare 调用时说明会消耗少量额度并按已有授权执行。
8. 每轮 A/B 后保存请求参数、耗时、完整输出和指标，不覆盖旧结果。
9. 修复可复现问题后跑 31 项 unittest、相关浏览器回归和 4176 验收。
10. 停在用户点击/人工对照环节，不擅自替换真实记录或宣布合同锁定。

## 14. 当前停止点

当前功能已打通，测试全绿，4176 在线。下一对话从“转录质量测试优化”开始，不需要重做 Cloudflare 注册、Token 创建、Forbidden 排查、tiny/small 基准或逐字稿折叠 UI。

第一件有价值的事是把 3 分钟样本建立为更可信的人工参考，再做 Cloudflare 单变量 A/B。
