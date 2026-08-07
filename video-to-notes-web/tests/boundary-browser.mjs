import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const output = "prototype-phase1-video-parser/screenshots/implementation-e2e-boundaries";
await fs.mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, acceptDownloads: true });
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});

async function latestRecordFor(url) {
  const response = await page.request.get(`${baseURL}/api/v3/parser/records?limit=100`);
  const records = (await response.json()).items;
  return records.find((record) => record.source_url === url);
}

async function latestNoteByTitle(title) {
  const response = await page.request.get(`${baseURL}/api/v3/notes?limit=100`);
  const notes = (await response.json()).items;
  return notes.find((note) => note.title === title);
}

async function generateLinkedNote(title) {
  await page.getByRole("button", { name: /用此逐字稿生成笔记/ }).click();
  await page.getByRole("button", { name: /按推荐快速生成/ }).waitFor();
  await page.locator("#suggested-note-title").fill(title);
  await page.getByRole("button", { name: /按推荐快速生成/ }).click();
  await page.getByRole("button", { name: /打开笔记/ }).waitFor();
  await page.getByRole("button", { name: /打开笔记/ }).click();
  await page.getByRole("button", { name: "编辑笔记" }).waitFor();
  const actualTitle = (await page.locator("[data-note-title]").first().innerText()).trim();
  if (actualTitle !== title) throw new Error(`用户标题未贯穿到阅读页：${actualTitle}`);
}

try {
  const sourceURL = `https://www.bilibili.com/video/BV1BOUNDARY${Date.now()}`;
  const firstTitle = `边界验收笔记一-${Date.now()}`;
  const secondTitle = `边界验收笔记二-${Date.now()}`;

  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.locator("#video-link").fill(sourceURL);
  await page.locator("#parser-form button[type=submit]").click();
  await page.getByRole("button", { name: /用此逐字稿生成笔记/ }).waitFor();
  if (!(await page.locator(".transcript-preview").innerText()).includes("固定逐字稿")) {
    throw new Error("解析结果没有绑定真实逐字稿投影");
  }
  const record = await latestRecordFor(sourceURL);
  if (!record) throw new Error("找不到边界测试解析记录");

  await generateLinkedNote(firstTitle);
  const firstNote = await latestNoteByTitle(firstTitle);
  if (!firstNote) throw new Error("第一份边界笔记未保存");

  await page.getByRole("button", { name: /重新生成本章/ }).click();
  await page.getByRole("button", { name: "保留当前版本" }).waitFor();
  const candidateHeading = (await page.locator(".candidate-hero h2").innerText()).trim();
  const candidateContext = (await page.locator(".candidate-context").innerText()).trim();
  if (!candidateHeading.includes(stateCandidateChapterName(candidateContext))) {
    throw new Error(`候选页标题没有绑定真实章节：${candidateHeading} / ${candidateContext}`);
  }
  for (const card of await page.locator(".candidate-card").all()) {
    if (/^#{1,6}\s/m.test(await card.innerText())) {
      throw new Error("候选章节仍暴露原始 Markdown 标题符号");
    }
  }
  await page.screenshot({ path: `${output}/boundary-01-candidate.png`, fullPage: true });
  await page.getByRole("button", { name: "保留当前版本" }).click();
  await page.getByRole("button", { name: /重新生成本章/ }).click();
  await page.getByRole("button", { name: "用候选版本替换" }).click();
  await page.getByRole("button", { name: "编辑笔记" }).waitFor();

  await page.getByRole("button", { name: "导出" }).click();
  await page.getByText("PDF", { exact: true }).click();
  await page.getByText(/笔记 \+ 生成依据逐字稿/).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /准备 PDF 下载/ }).click();
  const download = await downloadPromise;
  if (!download.suggestedFilename().endsWith(".pdf")) throw new Error("PDF 下载文件名不正确");
  const stream = await download.createReadStream();
  const firstChunk = await new Promise((resolve, reject) => {
    stream.once("data", resolve);
    stream.once("error", reject);
  });
  if (!firstChunk.toString("ascii", 0, 4).startsWith("%PDF")) throw new Error("PDF 响应不是有效 PDF");
  await page.screenshot({ path: `${output}/boundary-02-pdf.png`, fullPage: true });

  await page.getByRole("button", { name: "返回笔记" }).click();
  await page.getByRole("button", { name: "笔记历史" }).click();
  const firstHistory = page.locator(`[data-real-note="${firstNote.id}"]`);
  await firstHistory.getByRole("button", { name: "删除" }).click();
  await page.getByRole("dialog").getByRole("button", { name: /确认永久删除/ }).click();
  if ((await page.request.get(`${baseURL}/api/v3/notes/${firstNote.id}`)).status() !== 404) {
    throw new Error("确认删除笔记后笔记仍存在");
  }
  if ((await page.request.get(`${baseURL}/api/v3/parser/records/${record.id}`)).status() !== 200) {
    throw new Error("删除笔记错误级联删除了解析记录");
  }

  await page.getByRole("button", { name: "视频解析" }).click();
  await page.getByRole("button", { name: /用此逐字稿生成笔记/ }).click();
  await page.getByRole("button", { name: /按推荐快速生成/ }).waitFor();
  await page.locator("#suggested-note-title").fill(secondTitle);
  await page.getByRole("button", { name: /按推荐快速生成/ }).click();
  await page.getByRole("button", { name: /打开笔记/ }).waitFor();
  const secondNote = await latestNoteByTitle(secondTitle);
  if (!secondNote) throw new Error("第二份边界笔记未保存");

  await page.getByRole("button", { name: "视频解析" }).click();
  await page.getByRole("button", { name: /查看解析历史/ }).click();
  const recordRow = page.locator(`[data-real-record="${record.id}"]`);
  await recordRow.getByRole("button", { name: /查看已生成笔记/ }).click();
  await page.getByRole("button", { name: "编辑笔记" }).waitFor();
  if ((await page.locator("[data-note-title]").first().innerText()).trim() !== secondTitle) {
    throw new Error("解析历史没有反向打开关联笔记");
  }

  await page.reload({ waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成" }).click();
await page.getByRole("button", { name: "恢复任务", exact: true }).click();
  await page.getByText(secondTitle, { exact: true }).waitFor();
  await page.getByText(secondTitle, { exact: true }).locator("xpath=ancestor::article").getByRole("button").click();
  await page.getByRole("button", { name: "编辑笔记" }).waitFor();
  await page.screenshot({ path: `${output}/boundary-03-recovery.png`, fullPage: true });

  await page.getByRole("button", { name: "视频解析" }).click();
  await page.getByRole("button", { name: /查看解析历史/ }).click();
  await page.locator(`[data-real-record="${record.id}"]`).getByRole("button", { name: "删除" }).click();
  await page.getByRole("dialog").getByRole("button", { name: /确认永久删除/ }).click();
  if ((await page.request.get(`${baseURL}/api/v3/parser/records/${record.id}`)).status() !== 404) {
    throw new Error("确认删除解析记录后记录仍存在");
  }
  if ((await page.request.get(`${baseURL}/api/v3/notes/${secondNote.id}`)).status() !== 200) {
    throw new Error("删除解析记录错误级联删除了笔记");
  }
  await page.screenshot({ path: `${output}/boundary-04-parser-delete.png`, fullPage: true });

  const migrationContext = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
  await migrationContext.addInitScript(() => {
    localStorage.removeItem("vtn-v3-migration-complete");
    localStorage.setItem("vtn-history", JSON.stringify([{
      id: "browser-boundary-legacy-note",
      title: "浏览器旧历史迁移笔记",
      platform: "text",
      notes: "# 浏览器旧历史迁移笔记\n\n## 内容\n\n迁移成功。",
    }]));
  });
  const migrationPage = await migrationContext.newPage();
  const migrationResponse = migrationPage.waitForResponse((response) => response.url().includes("/api/v3/migrations/browser-history"));
  await migrationPage.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await migrationResponse;
  await migrationPage.getByRole("button", { name: "笔记生成" }).click();
  await migrationPage.getByRole("button", { name: "笔记历史" }).click();
  await migrationPage.getByText("浏览器旧历史迁移笔记", { exact: true }).waitFor();
  await migrationPage.screenshot({ path: `${output}/boundary-05-migration.png`, fullPage: true });
  await migrationContext.close();

  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, pdf: true, candidate: true, recovery: true, nonCascadeDelete: true, migration: true }));
} finally {
  await context.close();
  await browser.close();
}

function stateCandidateChapterName(contextText) {
  return contextText.split("\n")[0].replace(/^章节\s*\/?\s*/, "").trim();
}
