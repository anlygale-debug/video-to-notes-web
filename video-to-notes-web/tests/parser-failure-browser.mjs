import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const sourceURL = "https://www.bilibili.com/video/BV1TIMEOUT";
const errorMessage = "Cloudflare 音频上传超时，已停止本次解析，请检查网络后重试。";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
const errors = [];

page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});

await page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});
await page.route("**/api/v3/parser/tasks**", async (route) => {
  if (route.request().method() === "POST") {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({
        task: { id: "task-timeout", state: "created", source_url: sourceURL, progress: {} },
      }),
    });
    return;
  }
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-timeout",
        state: "failed",
        source_url: sourceURL,
        error_code: "TRANSCRIPTION_UPLOAD_TIMEOUT",
        error_message: errorMessage,
        error_retryable: true,
        progress: {},
      },
    }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.locator("#video-link").fill(sourceURL);
  await page.locator('#parser-form button[type="submit"]').click();

  await page.getByRole("heading", { name: "云端转录没有完成。", exact: true }).waitFor();
  await page.locator("[data-parser-failure-message]").getByText(errorMessage, { exact: true }).waitFor();
  await page.getByText("TRANSCRIPTION_UPLOAD_TIMEOUT", { exact: false }).waitFor();
  await page.getByRole("button", { name: /重试解析/ }).waitFor();

  if (await page.locator(".progress-panel").count()) {
    throw new Error("任务失败后仍显示转录进度面板");
  }
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, visibleFailure: true, staleProgress: false }));
} finally {
  await browser.close();
}
