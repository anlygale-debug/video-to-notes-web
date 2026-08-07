# 视频解析结果逐字稿折叠交互：实施交接

日期：2026-07-28

工作树：`/Users/yubo/.codex/worktrees/8f75/Claude code test/video-to-notes-web`

## 1. 新对话的唯一任务

实现并验收“解析结果页逐字稿默认预览、原位展开/收起”的正式交互，移除当前仍会出现的原型提示。完成实现、自测并重启 4176 后停止，交给用户点击确认。

不要继续扩展别的功能，不要重新讨论已经确认的选择。

## 2. 用户刚刚确认的产品决定

用户确认采用：

> 默认预览，原位展开/收起。

具体合同：

- 视频解析完成后，不默认展示几千字的完整逐字稿。
- 默认展示前 6–8 行，末尾通过视觉渐隐表达“后面还有内容”。
- 标题区域显示真实字数，例如“逐字稿 · 6,286 字”。
- 主按钮为“展开完整逐字稿 ↓”。
- 点击后在当前结果卡内展开全文；不弹窗、不跳新页面。
- 展开后按钮改为“收起逐字稿 ↑”。
- TXT、MD 下载按钮始终可见。
- 短逐字稿直接完整展示并隐藏展开按钮。
- 不再出现任何“原型提示”。

用户给出的现场截图：

`/var/folders/fs/3xmq6lp9551ccnk_x_2j7_d00000gp/T/codex-clipboard-040addb1-d329-404a-bc64-48161527380f.png`

截图表明当前页面已经把完整逐字稿直接写进结果卡，但仍保留“查看完整逐字稿”按钮；点击按钮会触发浏览器 `alert`：

> 原型提示：这里会打开完整逐字稿；第二阶段重点验证生成器中的查看与修正流程。

## 3. 已确认的根因

- `static/real-app.js` 的 `bindParserRecord()` 当前把 `record.transcript_text` 全量写入 `.transcript-preview`。
- `static/app.css` 的 `.transcript-preview` 没有折叠高度、渐隐或展开状态。
- `static/app.html` 的按钮仍是 `data-transcript` / “查看完整逐字稿”。
- `static/real-app.js` 的真实点击捕获列表没有处理 `data-transcript`。
- 因此点击事件继续冒泡到先加载的 `static/app-prototype.js`，触发固定原型 `alert`。

## 4. 建议按 TDD 实施

先补浏览器失败测试，再实现。公共 seam 是 `/next` 的真实结果卡交互，不测试私有函数。

建议新增 `tests/transcript-toggle-browser.mjs`，或在现有 `tests/parser-ui-race-browser.mjs` 中增加独立场景。测试必须覆盖：

1. 使用足够长的假逐字稿打开成功结果。
2. 默认状态：
   - `aria-expanded="false"`；
   - 逐字稿容器处于折叠状态；
   - 显示真实字数；
   - 下载 TXT / MD 按钮仍可见；
   - 不出现浏览器 alert。
3. 点击“展开完整逐字稿”：
   - 全文在原位可见；
   - 按钮改为“收起逐字稿 ↑”；
   - `aria-expanded="true"`。
4. 再次点击后恢复折叠状态。
5. 短逐字稿：完整显示，展开按钮隐藏。
6. 捕获页面错误与 console error，必须为 0。

## 5. 允许修改的实现范围

预计只需修改：

- `static/app.html`
- `static/app.css`
- `static/real-app.js`
- 对应浏览器测试

实现注意：

- 真实点击处理必须在 capture 阶段截获 `data-transcript`，阻止 `app-prototype.js` 的 alert。
- 建议把按钮语义改为 `data-toggle-transcript`；若保留 `data-transcript`，真实 handler 必须优先处理并 `stopImmediatePropagation()`。
- 逐字稿文本继续使用 `textContent`，不要拼未转义 HTML。
- 展开/收起只改变 class、ARIA 与按钮文字，不重复请求后端。
- 折叠高度用视觉行数或 `max-height`，不要截断或修改原始逐字稿数据。
- 渐隐层不能遮挡展开按钮，也不能影响 TXT/MD 下载按钮。
- 兼容 `prefers-reduced-motion`。
- 当前静态资源版本为 `v3`；完成后升级为 `v4`，避免用户浏览器缓存旧 JS/CSS。

## 6. 当前已完成并验证的相关修复

不要回退这些内容：

- 支持直接粘贴 B站/小红书“标题或文案 + 链接”，后端自动提取首个 URL。
- 输入框已从浏览器强制 `type=url` 改为支持分享文案。
- 解析按钮开始后立即锁定，连续提交只创建一个当前任务。
- 旧轮询不能覆盖当前任务；成功页不会再被旧任务改回解析中。
- 后端真实阶段已拆分为：识别来源、获取音频、生成逐字稿、整理保存、完成。
- 加载页已绑定真实阶段，并有工业仪表式动态反馈；写死的 62% 已移除。
- 真实视频封面已绑定 `thumbnail_url`，通过 `/api/proxy-image` 加载；失败时保留原型占位图。
- 解析历史、笔记历史、恢复任务均已完成稳定游标分页。
- 历史/恢复页面的导航死胡同已修复。

## 7. 当前验证基线

最近一次结果：

- 25 项 unittest 全绿。
- Python / JS 语法检查通过。
- 两条完整 E2E 路径通过。
- 四阶段 27 状态通过。
- 候选章节、PDF、恢复、双向非级联删除、旧历史迁移通过。
- 新解析竞态测试通过：连续提交只产生 1 个任务，5 个真实阶段按序投影，成功状态稳定。
- 真实 B站封面验证通过：`naturalWidth = 1285`，结果卡使用真实图片。
- 浏览器控制台错误为 0。

关键测试：

- `tests/e2e-browser.mjs`
- `tests/boundary-browser.mjs`
- `tests/parser-ui-race-browser.mjs`
- `tests/pagination-browser.mjs`

视觉证据：

- `dogfood-output/parser-progress-20260728/screenshots/parser-progress-full.png`
- `dogfood-output/parser-progress-20260728/screenshots/real-video-thumbnail.png`

## 8. 本地服务与数据状态

- 正式验收地址：`http://127.0.0.1:4176/next`
- 当前 4176 进程：PID 12162（交接时在线，HTTP 200）。
- 当前数据库：`/tmp/vtn-real-smoke-20260728-2.sqlite3`
- 当前静态资源版本：`v3`
- 4175 假适配器服务已停止；测试时可重新用独立 4175 启动。
- 可用于只读深链接检查的最新成功解析记录：`49405e13-a93e-414c-a0d2-fdf7eaeaaddd`
- 用户刚才的重复点击问题产生了 4 条重复成功解析记录；没有擅自删除。

启动真实服务：

```bash
VTN_DATABASE_PATH=/tmp/vtn-real-smoke-20260728-2.sqlite3 \
python3 -m uvicorn app:app --host 127.0.0.1 --port 4176
```

启动假服务（仅自动测试）：

```bash
VTN_FAKE_ADAPTERS=1 \
VTN_DATABASE_PATH=/tmp/<明确的新测试数据库>.sqlite3 \
python3 -m uvicorn app:app --host 127.0.0.1 --port 4175
```

## 9. 安全与范围边界

- 第一版仍只做本地网页：FastAPI + 浏览器 + SQLite，默认 `127.0.0.1`。
- 不做服务器部署、账号、云同步、手机版 App 或完整移动端适配。
- 根路由仍保留旧页面；新应用继续使用 `/next`。
- 不修改 fded 源工作树。
- 不删除用户历史或重复记录，除非用户明确授权。
- 不提交、不推送。
- 父工作树有大量无关改动和未跟踪文件，必须保留并避开。
- 用户最终确认前，不宣布 UI 合同锁定。

## 10. 新对话的执行顺序与停止条件

1. 完整读取本交接和相关前端三文件。
2. 按 TDD 先复现“全文默认展开 + 原型 alert”。
3. 实现已确认的默认预览、原位展开/收起。
4. 运行相关浏览器测试、全量 unittest、两条 E2E、27 状态与必要边界回归。
5. 用真实记录只读验证折叠页面，不再次运行真实 Whisper。
6. 将静态版本升级到 `v4`。
7. 重启/确认 4176，交给用户点击。
8. 停止；不要自行进入下一产品决策。
