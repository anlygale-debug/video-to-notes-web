import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseURL = process.env.VTN_REAL_URL || "http://127.0.0.1:4176";
const existingRecordId = process.env.VTN_EXISTING_RECORD_ID || "";
const videoURL = "https://www.bilibili.com/video/BV1zR4xzRECc?vd_source=eead6df7744cee5494396b8478260e72";
const output = "prototype-phase1-video-parser/screenshots/implementation-e2e-real";
await fs.mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
const errors = [];
page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});

try {
  await page.goto(
    existingRecordId ? `${baseURL}/next?record=${encodeURIComponent(existingRecordId)}` : `${baseURL}/next`,
    { waitUntil: "networkidle" }
  );
  if (!existingRecordId) {
    await page.locator("#video-link").fill(videoURL);
    await page.locator("#parser-form button[type=submit]").click();
  }
  const result = page.getByRole("button", { name: /用此逐字稿生成笔记/ });
  const failure = page.getByRole("button", { name: /重试解析/ });
  await Promise.race([
    result.waitFor({ timeout: 1_200_000 }).then(() => "success"),
    failure.waitFor({ timeout: 1_200_000 }).then(() => "failure"),
  ]);
  if (await failure.isVisible()) {
    await page.screenshot({ path: `${output}/real-parser-failure.png`, fullPage: true });
    const text = await page.locator("#state-host").innerText();
    throw new Error(`真实视频解析失败：${text}`);
  }
  await page.screenshot({ path: `${output}/real-01-parser-result.png`, fullPage: true });

  await result.click();
  await page.getByRole("button", { name: /按推荐快速生成/ }).waitFor({ timeout: 300_000 });
  const proposedTitle = await page.locator("#suggested-note-title").inputValue();
  const sourceLine = await page.locator("[data-analysis-source]").innerText();
  if (!sourceLine.includes("心理学") && !sourceLine.includes("亲密关系")) {
    throw new Error(`来源未正确贯穿：${sourceLine}`);
  }
  await page.screenshot({ path: `${output}/real-02-recommendation.png`, fullPage: true });

  await page.getByRole("button", { name: /按推荐快速生成/ }).click();
  await page.getByRole("button", { name: /打开笔记/ }).waitFor({ timeout: 600_000 });
  await page.getByRole("button", { name: /打开笔记/ }).click();
  await page.getByRole("button", { name: "编辑笔记" }).waitFor();
  const readingTitle = await page.locator("[data-note-title]").first().innerText();
  if (readingTitle.trim() !== proposedTitle.trim()) {
    throw new Error(`标题跨阶段漂移：推荐=${proposedTitle}，阅读=${readingTitle}`);
  }
  await page.screenshot({ path: `${output}/real-03-reading.png`, fullPage: true });

  await page.getByRole("button", { name: "编辑笔记" }).click();
  const editor = page.locator("[data-editor-content]").first();
  const editorBefore = await editor.innerText();
  const readingAnchor = (await page.locator(".note-body p").first().innerText()).trim();
  if (!readingAnchor || !editorBefore.includes(readingAnchor)) {
    throw new Error(`编辑页没有载入当前真实笔记内容：anchor=${readingAnchor}; editor=${editorBefore.slice(0, 240)}`);
  }
  await editor.click();
  await page.keyboard.press("Meta+ArrowDown");
  await editor.type("\n\n浏览器真实链路验收已完成。", { delay: 15 });
  await page.getByText(/已自动保存 · 刚刚/).waitFor({ timeout: 30_000 });
  await page.getByRole("button", { name: "完成编辑" }).click();
  await page.getByRole("button", { name: "导出" }).click();
  await page.getByRole("button", { name: /准备 Markdown 下载/ }).waitFor();
  const exportTitle = await page.locator(".paper-lines strong").innerText();
  if (exportTitle.trim() !== proposedTitle.trim()) {
    throw new Error(`导出预览标题漂移：推荐=${proposedTitle}，导出=${exportTitle}`);
  }
  await page.screenshot({ path: `${output}/real-04-export.png`, fullPage: true });

  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, proposedTitle, sourceLine, exportPageReached: true }));
} finally {
  await browser.close();
}
