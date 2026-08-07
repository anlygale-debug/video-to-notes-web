import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const output = "prototype-phase1-video-parser/screenshots/uploaded-transcript-ready";
await fs.mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
const errors = [];
let submittedSource = null;

page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error" && !message.text().includes("favicon.ico")) {
    errors.push(`console: ${message.text()}`);
  }
});

const transcript = "第一章：真实上传内容\n这是煜博刚刚上传的逐字稿。";
const expectedCount = Array.from(transcript.trim()).length.toLocaleString("zh-CN");
const failedTask = {
  id: "task-upload-source-001",
  state: "analysis_failed",
  source_type: "file",
  source_name: "我的真实访谈记录.md",
  source_snapshot: { type: "file", name: "我的真实访谈记录.md" },
  basis_transcript: transcript,
  proposed_title: "我的真实访谈记录",
  request_text: "",
  recommendation: null,
  progress: { stage: "analysis_failed", label: "测试已拦截", percent: 0 },
  error_code: "LLM_DISABLED",
  error_message: "浏览器测试已阻止真实 LLM 请求",
  error_retryable: false,
  outline: [],
  chapters: [],
};

await page.route("**/api/v3/note-tasks", async (route) => {
  if (route.request().method() !== "POST") return route.continue();
  submittedSource = route.request().postDataJSON().source;
  await route.fulfill({
    status: 202,
    contentType: "application/json",
    body: JSON.stringify({ task: failedTask }),
  });
});
await page.route("**/api/v3/note-tasks/task-upload-source-001", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ task: failedTask }),
  });
});

try {
  await page.addInitScript(() => {
    localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
  });
  await page.goto(`${baseURL}/next?uploaded-transcript-ready=1`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();

  const chooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "选择 TXT / MD 文件", exact: true }).click();
  const chooser = await chooserPromise;
  await chooser.setFiles({
    name: "我的真实访谈记录.md",
    mimeType: "text/markdown",
    buffer: Buffer.from(transcript),
  });

  const readyCard = page.locator(".ready-file");
  await readyCard.waitFor({ state: "visible" });
  if (await readyCard.locator("[data-ready-file-name]").innerText() !== "我的真实访谈记录.md") {
    throw new Error("已就绪卡片没有显示真实文件名");
  }
  if (await readyCard.locator("[data-ready-file-type]").innerText() !== "MD / 01") {
    throw new Error("已就绪卡片没有显示真实文件类型");
  }
  const readyMeta = await readyCard.locator("[data-ready-file-meta]").innerText();
  if (!readyMeta.includes(`${expectedCount} 字`)) {
    throw new Error(`已就绪卡片字数不正确：${readyMeta}`);
  }
  const summary = await page.locator("[data-ready-source-summary]").innerText();
  if (!summary.includes(`${expectedCount} 字`)) {
    throw new Error(`来源摘要字数不正确：${summary}`);
  }
  await page.screenshot({ path: `${output}/real-upload-metadata.png`, fullPage: true });

  await page.getByRole("button", { name: /分析逐字稿/ }).click();
  await page.locator(".notes-analysis-failure").waitFor({ state: "visible" });
  if (submittedSource?.type !== "file" || submittedSource?.name !== "我的真实访谈记录.md") {
    throw new Error(`上传来源提交错误：${JSON.stringify(submittedSource)}`);
  }
  if (submittedSource?.transcript !== transcript) {
    throw new Error("上传文件正文没有原样提交");
  }
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, fileName: submittedSource.name, characterCount: expectedCount }));
} finally {
  await browser.close();
}
