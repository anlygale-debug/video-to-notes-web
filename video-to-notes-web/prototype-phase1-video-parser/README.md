# 四阶段完整高保真原型

这是一个完全独立、固定假数据驱动的本地桌面网页原型。目前覆盖统一应用外壳、视频解析器、逐字稿输入与 AI 推荐、大纲与生成、任务恢复，以及笔记成品、编辑、导出和历史。它不读取或修改真实应用、`app.py`、真实页面、后端、下载、数据库或 AI 服务。

## 打开方式

直接用浏览器打开 [index.html](index.html)，或在本目录运行：

```bash
python3 -m http.server 4173
```

然后访问 <http://localhost:4173>。

## 验收入口

「视频解析」中的验收控制台可直接切换六个关键状态：

1. 初始空状态：输入链接、没有任务。
2. 解析中：语义阶段进度。
3. 结果：封面、元信息、逐字稿、按需下载和「用此逐字稿生成笔记」。
4. 失败：代表性错误、重试与修改链接。
5. 历史：普通记录、已关联笔记记录、按需下载状态。
6. 删除确认：永久删除的范围说明与二次确认。

其他可点击验收项：顶部双功能导航的选中状态、提交链接后模拟解析、主衔接按钮、下载占位操作、历史条目的删除确认。

「笔记生成」中的第二阶段控制台可直接切换七个关键状态：

1. 独立粘贴或上传 `.txt` / `.md`。
2. 内容已就绪、尚未调用 AI。
3. AI 预读中的语义进度。
4. 四项 AI 推荐摘要与快速生成入口。
5. 同页展示的四项自定义设置。
6. 修改生成依据逐字稿后，推荐立即过期。
7. 代表性 AI 预读失败与重试。

从视频解析结果点击「用此逐字稿生成笔记」会模拟自动带入来源并直接触发 AI 预读；独立输入仍需要用户明确点击「分析逐字稿」。

第三阶段在同一控制台增加七个关键状态：

1. 直接生成：隐藏后台分块，只展示五个语义阶段。
2. 大纲确认：只读章节预览、确认、补充要求和返回设置。
3. 重拟大纲：沿用原设置与补充要求，重新生成整份大纲。
4. 逐章生成：显示章节进度、已完成章节和上下文保留。
5. 章节失败：保留已完成内容，可继续、稍后处理或整份重新生成。
6. 任务恢复：集中展示等待设置、等待大纲、生成中、失败和已完成五类恢复入口。
7. 生成完成：显示保存结果与简洁内容完整性检查，并进入成品阅读。

第四阶段在同一控制台增加七个关键状态：

1. 阅读：单栏成品阅读、轻量标题修改、来源与生成依据。
2. 编辑：同页轻量可视化编辑、基础格式工具与自动保存。
3. 单章候选：同时展示当前版本和 AI 候选版本，由用户决定是否替换。
4. 导出：Markdown、PDF、复制全文，以及内容范围和来源信息选项。
5. 可能遗漏：具体、非阻断式提醒，仍可继续编辑和导出。
6. 笔记历史：视频解析、粘贴文本、TXT/MD 文件来源及关联状态。
7. 删除确认：明确删除范围、不级联影响及不可恢复说明。

## 第二阶段关键截图

- `screenshots/07-notes-input.png`：独立逐字稿输入。
- `screenshots/08-notes-analyzing.png`：AI 预读中。
- `screenshots/09-notes-recommendations.png`：推荐结果。
- `screenshots/10-notes-custom.png`：AI 默认值下的自定义设置。
- `screenshots/10-notes-custom-conflict.png`：冲突组合提示。
- `screenshots/11-notes-stale.png`：修改逐字稿后推荐过期。
- `screenshots/12-notes-analysis-failure.png`：预读失败与重试。

## 第三阶段关键截图

- `screenshots/13-direct-generating.png`：一次性生成的语义阶段进度。
- `screenshots/14-outline-confirmation.png`：只读大纲确认。
- `screenshots/15-outline-regenerating.png`：按补充要求重拟整份大纲。
- `screenshots/16-chapter-generating.png`：章节级生成与已完成内容保留。
- `screenshots/17-chapter-failure.png`：代表性章节失败与恢复操作。
- `screenshots/18-task-recovery.png`：五类同浏览器任务恢复入口。
- `screenshots/18-generation-complete.png`：生成完成与内容完整性检查。

## 第四阶段关键截图

- `screenshots/19-note-reading.png`：排版后的单栏阅读视图。
- `screenshots/20-note-editing.png`：同页轻量可视化编辑与自动保存。
- `screenshots/21-chapter-candidate.png`：单章当前版本与候选版本。
- `screenshots/22-note-export.png`：导出格式、内容和来源选择。
- `screenshots/23-possible-omission.png`：非阻断式可能遗漏提醒。
- `screenshots/24-note-history.png`：笔记历史与三类来源。
- `screenshots/25-note-delete-confirmation.png`：永久删除确认。

## 当前边界

四阶段核心原型已覆盖，并于 2026-07-27 完成最终端到端实际点击验收，现已正式锁定为 UI 合同。未接入真实数据、AI、任务恢复、编辑存储、导出文件或数据库；下一阶段可以依据本原型开始技术规格。任何用户可见偏差仍须提前说明并获得确认。
