import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
let retryStarted = false;

await page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});
await page.route("**/api/v3/note-tasks**", async (route) => {
  const request = route.request();
  const task = {
    id: "retry-analysis-task",
    state: retryStarted ? "recommendation_ready" : "analysis_failed",
    source_name: "粘贴文本",
    basis_transcript: "用于验证预读重试的逐字稿。",
    request_text: "",
    proposed_title: "重试成功后的笔记",
    error_code: retryStarted ? null : "LLM_TIMEOUT",
    error_message: retryStarted ? null : "AI 服务 30 秒内没有响应，已停止本次分析，请重试。",
    recommendation: retryStarted ? {
      reason: "重试后完成分析。",
      structure: { option_ids: ["source_flow"], recommended_id: "source_flow", reason: "沿原文组织。" },
      detail: { recommended_id: "key", reason: "保留关键内容。" },
      method: { recommended_id: "direct", reason: "可直接生成。" },
      modules: { recommended_ids: ["summary"], reasons: { summary: "便于复习。" } },
    } : null,
  };
  if (request.method() === "POST" && request.url().endsWith("/commands")) {
    retryStarted = true;
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ task: { ...task, state: "analyzing", error_code: null, error_message: null } }),
    });
    return;
  }
  if (request.method() === "POST") {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ task: { ...task, state: "analyzing", error_code: null, error_message: null } }),
    });
    return;
  }
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ task }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.locator(".notes-textarea").first().fill("用于验证预读重试的逐字稿。");
  await page.getByRole("button", { name: /分析逐字稿/ }).click();
  await page.getByRole("heading", { name: "暂时无法完成逐字稿分析。", exact: true }).waitFor();

  await page.getByRole("button", { name: /重试分析/ }).click();
  await page.getByRole("heading", { name: "推荐设置已准备好。", exact: true })
    .waitFor({ timeout: 3_000 });
  if (!retryStarted) throw new Error("重试命令没有提交");
  console.log(JSON.stringify({ ok: true, resumedPolling: true }));
} finally {
  await browser.close();
}
