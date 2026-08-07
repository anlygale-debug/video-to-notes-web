import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
const errors = [];
let createCount = 0;

page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error" && !message.text().includes("status of 404")) {
    errors.push(`console: ${message.text()}`);
  }
});

await page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});
await page.route("**/api/v3/note-tasks**", async (route) => {
  const request = route.request();
  if (request.method() === "POST" && /\/api\/v3\/note-tasks$/.test(request.url())) {
    createCount += 1;
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({
        task: {
          id: createCount === 1 ? "lost-analysis-task" : "replacement-analysis-task",
          state: "analyzing",
          source_name: "粘贴文本",
          basis_transcript: "一份需要安全恢复的长逐字稿。",
          request_text: "",
        },
      }),
    });
    return;
  }
  if (request.url().endsWith("/lost-analysis-task")) {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({
        error: { code: "NOTE_TASK_NOT_FOUND", message: "笔记任务不存在" },
      }),
    });
    return;
  }
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "replacement-analysis-task",
        state: "recommendation_ready",
        source_name: "粘贴文本",
        basis_transcript: "一份需要安全恢复的长逐字稿。",
        request_text: "",
        proposed_title: "安全恢复后的笔记",
        recommendation: {
          reason: "已经重新完成分析。",
          structure: { option_ids: ["source_flow"], recommended_id: "source_flow", reason: "沿原文组织。" },
          detail: { recommended_id: "key", reason: "保留关键内容。" },
          method: { recommended_id: "direct", reason: "可直接生成。" },
          modules: { recommended_ids: ["summary"], reasons: { summary: "便于复习。" } },
        },
      },
    }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.locator(".notes-textarea").first().fill("一份需要安全恢复的长逐字稿。");
  await page.getByRole("button", { name: /分析逐字稿/ }).click();

  await page.getByRole("heading", { name: "暂时无法完成逐字稿分析。", exact: true })
    .waitFor({ timeout: 3_000 });
  await page.locator("[data-analysis-failure-message]")
    .getByText("笔记任务不存在", { exact: true }).waitFor();
  if (await page.getByRole("heading", { name: "正在理解这份逐字稿", exact: true }).count()) {
    throw new Error("状态查询失败后仍停留在正在理解页面");
  }

  await page.getByRole("button", { name: /重试分析/ }).click();
  await page.getByRole("heading", { name: "推荐设置已准备好。", exact: true }).waitFor();
  if (createCount !== 2) throw new Error(`丢失任务重试时未创建新任务：${createCount}`);
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, visibleFailure: true, recreatedTask: true }));
} finally {
  await browser.close();
}
