import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });

await page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});
await page.route("**/api/v3/note-tasks**", async (route) => {
  if (route.request().method() === "POST") {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({
        task: {
          id: "hanging-analysis-task",
          state: "analyzing",
          source_name: "粘贴文本",
          basis_transcript: "用于验证状态查询超时的逐字稿。",
          request_text: "",
        },
      }),
    });
    return;
  }
  await new Promise((resolve) => setTimeout(resolve, 10_000));
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ task: { id: "hanging-analysis-task", state: "analyzing" } }),
  }).catch(() => {});
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.locator(".notes-textarea").first().fill("用于验证状态查询超时的逐字稿。");
  const startedAt = Date.now();
  await page.getByRole("button", { name: /分析逐字稿/ }).click();

  await page.getByRole("heading", { name: "暂时无法完成逐字稿分析。", exact: true })
    .waitFor({ timeout: 7_000 });
  const elapsedMs = Date.now() - startedAt;
  await page.locator("[data-analysis-failure-message]").getByText(/状态查询 5 秒内没有响应/).waitFor();
  if (elapsedMs >= 7_000) throw new Error(`状态查询没有及时停止：${elapsedMs}ms`);
  console.log(JSON.stringify({ ok: true, elapsedMs, stoppedWaiting: true }));
} finally {
  await browser.close();
}
