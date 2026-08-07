# 视频解析器 + 自适应笔记生成器：UI 与 E2E 覆盖矩阵

> 状态：用户已于 2026-07-27 确认。此表是实施期间防止 27 状态遗漏的验收清单，不替代执行者全量浏览器测试和用户最终实际点击。

## 27 状态覆盖

| 状态 | 真实投影/触发 | 主实现 Ticket | 自动验收 | E2E 路径 |
|---|---|---|---|---|
| 解析 01 初始 | 无当前 parser task | T11/T12 | UI 初始快照 | A |
| 解析 02 解析中 | `resolving` / `transcribing` SSE | T02/T03/T12 | fake SSE 阶段 | A |
| 解析 03 结果 | `parser_record` | T03/T12 | record/download schema | A |
| 解析 04 失败 | `failed` + retry | T02/T03/T12 | retry contract | A |
| 解析 05 历史 | parser cursor query | T03/T07/T12 | pagination/link query | A |
| 解析 06 删除确认 | record + local dialog | T07/T12 | non-cascade delete | B |
| 笔记 01 输入 | 本地草稿 | T11/T12 | paste/file validation | B |
| 笔记 02 已就绪 | 本地文件已读 | T04/T12 | no AI before click | B |
| 笔记 03 预读中 | `analyzing` | T04/T12 | fake LLM event | A/B |
| 笔记 04 推荐 | `recommendation_ready` | T04/T12 | JSON contract/title source | A/B |
| 笔记 05 自定义 | 推荐 + local settings draft | T04/T12 | valid/conflict choice | B |
| 笔记 06 推荐过期 | revision mismatch | T04/T12 | transcript change blocks generate | B |
| 笔记 07 预读失败 | `analysis_failed` | T04/T12 | retry retains input | B |
| 笔记 08 直接生成 | `generating_direct` | T05/T12 | five semantic stages | A |
| 笔记 09 大纲 | `outline_ready` | T06/T12 | read-only outline | B |
| 笔记 10 重拟大纲 | `outline_regenerating` | T06/T12 | feedback persists/reappears | B |
| 笔记 11 逐章生成 | `generating_chapters` | T06/T12 | chapter event/progress | B |
| 笔记 12 章节失败 | `chapter_failed` | T06/T12 | completed chapters retained | B |
| 笔记 13 任务恢复 | task history + reconnect | T03/T06/T10/T12 | restart/SSE recovery | B |
| 笔记 14 生成完成 | `complete` + receipt | T05/T06/T07/T12 | note+initial version transaction | A/B |
| 笔记 15 阅读 | current note version | T07/T08/T12 | sanitized Markdown/render | A/B |
| 笔记 16 编辑 | current note + editor state | T08/T12 | debounce/flush/conflict | A |
| 笔记 17 单章候选 | pending candidate | T08/T12 | accept/reject no overwrite | B |
| 笔记 18 导出 | current saved version + options | T09/T12 | six export combinations | A |
| 笔记 19 可能遗漏 | integrity `possible_omission` | T05/T07/T12 | non-blocking projection | B |
| 笔记 20 笔记历史 | note cursor query | T07/T10/T12 | source/status/link query | A/B |
| 笔记 21 删除确认 | note/task + local dialog | T07/T12 | non-cascade hard delete | B |

## 两条 E2E 路径覆盖

| 路径 | 关键链路 | 必经 Tickets | 自动化断言 |
|---|---|---|---|
| A：视频解析→快速生成→成品 | 解析→来源带入→预读→推荐→direct→阅读→编辑→导出→历史反向打开 | T01–T05、T07–T09、T11–T13 | 未配置 LLM 时 parser 可独立；带入后自动预读；标题/来源/版本/导出文件名一致；编辑保存后导出最新版本；解析历史反向打开笔记 |
| B：独立逐字稿→大纲→失败恢复→候选 | 粘贴/文件→需求→自定义→大纲重拟→逐章→失败→稍后继续→候选→遗漏→删除 | T01、T04、T06–T08、T10–T13 | 未点击分析不调 AI；需求贯穿重拟大纲；完成章节保留；服务重启可恢复；候选不直接覆盖；遗漏不阻断；双方删除不级联 |

路径 A 的最终真实浏览器验收使用用户提供的 Bilibili 完整链接 `https://www.bilibili.com/video/BV1zR4xzRECc?vd_source=eead6df7744cee5494396b8478260e72`；确定性自动化回归继续使用本地 fixtures。

## 跨阶段不变量

| 不变量 | 责任 Ticket | 验证点 |
|---|---|---|
| 标题、本次需求、来源、版本、导出名称来自同一投影 | T04、T07、T08、T09、T12 | A/B 全链路字段一致性断言 |
| Parser 不依赖 LLM 配置 | T02、T03、T13 | 无配置 parser smoke |
| 逐字稿双方独立所有且删除不级联 | T01、T07、T10 | 双向删除集成测试 |
| 任务刷新/服务重启后可恢复 | T01、T03、T06、T10 | event 补发与启动恢复测试 |
| UI 仅两级入口并保持视觉合同 | T11、T12、T13 | 1440×1050 视觉回归与人工对照 |
| 没有原始 Mermaid 错误或不安全 Markdown | T05、T09、T11 | Mermaid 降级/DOMPurify 测试 |

## 结束门槛

T13 完成自动回归后，执行者必须先在真实本地页面从头到尾走完路径 A 与 B，修复所有可复现缺陷并重跑受影响路径，确认页面运行时错误为 0；之后仍须由用户进行最终点击验收。用户确认前不得把根路由切到新页面，也不得宣称最终 UI 合同验收完成。
