import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const title = `阅读面板验收-${Date.now()}`;
const markdown = `# ${title}

> **核心摘要**
>
> 这份笔记的**核心结论**是：先理解问题，再形成可以执行的步骤。

### 第一章：看清问题

#### 三重心理机制

正文中的**重点内容**应该加粗，而不是露出星号。

---

- [x] 已完成的觉察练习
- [ ] 下一步关系练习

参考[延伸阅读](https://example.com/reading)，并保留\`边界感\`这个概念。

###### 更深一层的提醒

这里使用__另一种强调__写法。

### 第二章：开始行动

1. 先记录触发场景
2. 再区分事实与猜测

**复习增强｜关键概念**

- 分离创伤：关系中的失去恐惧。

**复习增强｜实践提炼**

- 记录一次控制冲动前的真实需要。
`;

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
await context.addInitScript(({ title, markdown }) => {
  localStorage.removeItem("vtn-v3-migration-complete");
  localStorage.setItem("vtn-history", JSON.stringify([{
    id: `note-reading-${title}`,
    title,
    platform: "text",
    notes: markdown,
    transcript: "用于阅读面板公开验收的生成依据逐字稿。",
  }]));
}, { title, markdown });
const page = await context.newPage();

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.getByRole("button", { name: "笔记历史", exact: true }).click();
  const row = page.getByText(title, { exact: true }).locator("xpath=ancestor::article");
  await row.getByRole("button", { name: /打开笔记/ }).click();
  await page.getByRole("button", { name: "编辑笔记", exact: true }).waitFor();

  const deck = page.locator(".note-deck");
  if (!(await deck.innerText()).includes("核心结论")) {
    throw new Error("标题区没有提取真实核心摘要");
  }
  if (await deck.locator("strong").count() !== 1) {
    throw new Error("概述中的强调符号没有渲染");
  }

  const body = page.locator(".note-body");
  const bodyText = await body.innerText();
  for (const marker of ["###", "**", "---", "[x]", "[ ]", "__", "######"]) {
    if (bodyText.includes(marker)) throw new Error(`正文仍暴露 Markdown 符号：${marker}`);
  }
  if (await body.locator(".note-toc a").count() !== 2) {
    throw new Error("目录没有按真实正文章节生成");
  }
  if (await body.locator(".note-chapter").count() !== 2) {
    throw new Error("正文没有组织成真实章节面板");
  }
  if (await body.locator(".note-module").count() !== 2) {
    throw new Error("复习增强内容没有独立组织成附加模块面板");
  }
  const secondChapterText = await body.locator(".note-chapter").nth(1).innerText();
  if (secondChapterText.includes("关键概念") || secondChapterText.includes("实践提炼")) {
    throw new Error("附加模块仍被错误合并进最后一个正文篇章");
  }
  if (await body.locator('input[type="checkbox"]').count() !== 2) {
    throw new Error("任务清单没有渲染为可读状态");
  }
  if (await body.locator('a[href="https://example.com/reading"]').count() !== 1) {
    throw new Error("Markdown 链接没有渲染");
  }
  if (await body.locator("hr").count() !== 1) {
    throw new Error("Markdown 分隔线没有渲染");
  }

  const output = "prototype-phase1-video-parser/screenshots/note-reading-panel";
  await fs.mkdir(output, { recursive: true });
  await page.screenshot({ path: `${output}/note-reading-panel.png`, fullPage: true });
  console.log(JSON.stringify({
    ok: true,
    toc: await body.locator(".note-toc a").count(),
    chapters: await body.locator(".note-chapter").count(),
    modules: await body.locator(".note-module").count(),
    markdownClean: true,
  }));
} finally {
  await context.close();
  await browser.close();
}
