import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const transcriptPath = process.env.VTN_TRANSCRIPT_PATH;
if (!transcriptPath) throw new Error("请通过 VTN_TRANSCRIPT_PATH 指定要上传的 TXT / MD 文件");

const output = process.env.VTN_E2E_OUTPUT || "dogfood-output/long-transcript-upload-2026-07-30/screenshots";
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
const errors = [];

page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error" && !message.text().includes("favicon.ico")) {
    errors.push(`console: ${message.text()}`);
  }
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();

  const chooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "选择 TXT / MD 文件", exact: true }).click();
  const chooser = await chooserPromise;
  await chooser.setFiles(transcriptPath);

  const analyzeButton = page.getByRole("button", { name: /分析逐字稿/ });
  await analyzeButton.waitFor();
  await page.screenshot({ path: `${output}/real-file-ready.png`, fullPage: true });
  const startedAt = Date.now();
  await analyzeButton.click();
  await page.locator(".recommendation-stack, .notes-analysis-failure")
    .waitFor({ timeout: 35_000 });
  const elapsedMs = Date.now() - startedAt;

  if (await page.locator(".notes-analysis-failure").count()) {
    const message = await page.locator("[data-analysis-failure-message]").innerText();
    throw new Error(`真实文件预读失败：${message}`);
  }
  const source = await page.locator("[data-analysis-source]").first().innerText();
  await page.screenshot({ path: `${output}/real-file-recommendation-ready.png`, fullPage: true });
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, elapsedMs, source }));
} finally {
  await browser.close();
}
