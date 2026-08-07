import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseURL = process.env.VTN_REAL_URL || "http://127.0.0.1:4176";
const recordId = process.env.VTN_EXISTING_RECORD_ID || "9421cc71-25fa-4896-be38-6790836ce843";
const output = "prototype-phase1-video-parser/screenshots/implementation-e2e-final-existing";
await fs.mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});

try {
  const recordResponse = await page.request.get(`${baseURL}/api/v3/parser/records/${recordId}`);
  if (!recordResponse.ok()) throw new Error(`真实解析记录不可用：${recordResponse.status()}`);
  const historyResponse = await page.request.get(`${baseURL}/api/v3/parser/records?limit=100`);
  const record = (await historyResponse.json()).items.find((item) => item.id === recordId);
  if (!record) throw new Error("真实解析记录不在最近 100 条历史中");
  if (!record.note_id) throw new Error("真实解析记录没有关联成品笔记");

  await page.goto(`${baseURL}/next?record=${encodeURIComponent(recordId)}`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /用此逐字稿生成笔记/ }).waitFor();
  await page.getByRole("button", { name: /查看解析历史/ }).click();
  await page.getByRole("heading", { name: "解析历史", exact: true }).waitFor();
  const recordRow = page.locator(`[data-real-record="${recordId}"]`);
  await recordRow.getByRole("button", { name: /查看已生成笔记/ }).click();
  await page.getByRole("button", { name: "编辑笔记" }).waitFor();

  const title = (await page.locator("[data-note-title]").first().innerText()).trim();
  if (!title || !(await page.locator(".note-body").innerText()).trim()) {
    throw new Error("关联笔记阅读页没有载入真实标题或正文");
  }
  await page.screenshot({ path: `${output}/final-existing-01-reading.png`, fullPage: true });

  await page.getByRole("button", { name: "导出" }).click();
  await page.getByRole("button", { name: /准备 Markdown 下载/ }).waitFor();
  const exportTitle = (await page.locator(".paper-lines strong").innerText()).trim();
  if (exportTitle !== title) throw new Error(`导出标题漂移：${title} -> ${exportTitle}`);
  await page.screenshot({ path: `${output}/final-existing-02-export.png`, fullPage: true });

  await page.getByRole("button", { name: "返回笔记" }).click();
  await page.getByRole("button", { name: "笔记历史" }).click();
  await page.locator(`[data-real-note="${record.note_id}"]`).waitFor();
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.getByRole("heading", { name: "提供逐字稿", exact: true }).waitFor();
  await page.screenshot({ path: `${output}/final-existing-03-history-return.png`, fullPage: true });

  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, recordId, noteId: record.note_id, title }));
} finally {
  await context.close();
  await browser.close();
}
