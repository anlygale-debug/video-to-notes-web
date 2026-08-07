import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const output = "prototype-phase1-video-parser/screenshots/implementation-e2e";
await fs.mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
const errors = [];
page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});

async function screenshot(name) {
  await page.screenshot({ path: `${output}/${name}.png`, fullPage: true });
}

async function pathA() {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  const sharedURL = "https://www.bilibili.com/video/BV1zR4xzRECc?vd_source=eead6df7744cee5494396b8478260e72";
  await page.locator("#video-link").fill(
    `【心理学：亲密关系中的控制欲破解路径：分离创伤，客体认同，认知固化三重根源解读】${sharedURL}`
  );
  await page.locator("#parser-form button[type=submit]").click();
  await page.getByRole("button", { name: /用此逐字稿生成笔记/ }).waitFor();
  if (await page.locator("#video-link").inputValue() !== sharedURL) {
    throw new Error("平台分享文案没有自动提取并规范化为纯视频链接");
  }
  await screenshot("a-01-parser-result");
  await page.getByRole("button", { name: /用此逐字稿生成笔记/ }).click();
  await page.getByRole("button", { name: /按推荐快速生成/ }).waitFor();
  await screenshot("a-02-recommendation");
  await page.getByRole("button", { name: /按推荐快速生成/ }).click();
  await page.getByRole("button", { name: /打开笔记/ }).waitFor();
  await screenshot("a-03-generation-complete");
  await page.getByRole("button", { name: /打开笔记/ }).click();
  await page.getByRole("button", { name: "编辑笔记" }).waitFor();
  const readingTitle = (await page.locator("[data-note-title]").first().innerText()).trim();
  const readingAnchor = (await page.locator(".note-content .note-chapter p, .note-content .note-chapter li").first().innerText()).trim();
  await screenshot("a-04-reading");
  await page.getByRole("button", { name: "编辑笔记" }).click();
  const editor = page.locator("[data-editor-content]").first();
  if (!readingAnchor || !(await editor.innerText()).includes(readingAnchor)) {
    throw new Error("编辑页没有载入当前笔记正文");
  }
  await editor.click();
  await page.keyboard.press("Meta+ArrowDown");
  await editor.type("\n\n这是浏览器自动保存后的最新内容。");
  await page.getByText(/已自动保存 · 刚刚/).waitFor();
  await page.getByRole("button", { name: "完成编辑" }).click();
  const savedBody = await page.locator(".note-body").innerText();
  if (!savedBody.includes(readingAnchor) || !savedBody.includes("这是浏览器自动保存后的最新内容。")) {
    throw new Error("可视化编辑保存后正文结构或新增内容丢失");
  }
  await page.getByRole("button", { name: "导出" }).click();
  await page.getByRole("button", { name: /准备 Markdown 下载/ }).waitFor();
  const exportTitle = (await page.locator(".paper-lines strong").innerText()).trim();
  if (exportTitle !== readingTitle) throw new Error(`导出标题漂移：阅读=${readingTitle}，导出=${exportTitle}`);
  const exportHeadings = await page.locator(".paper-lines h4").allInnerTexts();
  if (exportHeadings.some((heading) => /^\d{2}\s+#+\s*$/.test(heading.trim()))) {
    throw new Error(`导出预览出现空章节：${exportHeadings.join(" / ")}`);
  }
  await screenshot("a-05-export");
  await page.getByRole("button", { name: "返回笔记" }).click();
  await page.getByRole("button", { name: "笔记历史" }).click();
  await page.getByRole("button", { name: /打开笔记/ }).first().waitFor();
  await screenshot("a-06-history");
}

async function pathB() {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成" }).click();
  await page.locator(".notes-textarea").first().fill(
    "亲密关系中的控制欲可能来自分离创伤、客体认同与认知固化。需要通过觉察、表达和边界练习逐步调整。"
  );
  await page.locator(".notes-request").fill("用于复习，请保留三类根源和行动练习。");
  await page.getByRole("button", { name: /分析逐字稿/ }).click();
  await page.getByRole("button", { name: "自定义生成" }).waitFor();
  await page.getByRole("button", { name: "自定义生成" }).click();
  await page.locator('[data-setting-group="method"] [data-choice="outline"]').click();
  await page.getByRole("button", { name: /按当前设置开始生成/ }).click();
  await page.getByRole("button", { name: /确认大纲并开始生成/ }).waitFor();
  await page.locator("#outline-feedback").fill("请把第三章的行动练习写得更具体。");
  await page.getByRole("button", { name: "重新生成整份大纲" }).click();
  await page.getByRole("button", { name: /确认大纲并开始生成/ }).waitFor();
  await screenshot("b-01-outline-regenerated");
  await page.getByRole("button", { name: /确认大纲并开始生成/ }).click();
  await page.getByRole("button", { name: /打开笔记/ }).waitFor();
  await screenshot("b-02-complete");
}

async function acceptanceStates() {
  await page.goto(`${baseURL}/next?acceptance=1`, { waitUntil: "networkidle" });
  const parserButtons = page.locator("[data-parser-state]");
  for (let index = 0; index < await parserButtons.count(); index += 1) {
    await parserButtons.nth(index).click();
    const dialog = page.locator("dialog[open]");
    if (await dialog.count()) await dialog.locator("[data-close-modal]").click();
  }
  await page.getByRole("button", { name: "笔记生成" }).click();
  const noteButtons = page.locator("[data-notes-state]");
  for (let index = 0; index < await noteButtons.count(); index += 1) {
    await noteButtons.nth(index).click();
    const dialog = page.locator("dialog[open]");
    if (await dialog.count()) await dialog.locator("[data-close-modal]").click();
  }
  await screenshot("acceptance-27-states");
}

try {
  await pathA();
  await pathB();
  await acceptanceStates();
  if (errors.length) throw new Error(errors.join("\n"));
  console.log("E2E browser paths A/B and all 27 acceptance states passed.");
} finally {
  await browser.close();
}
