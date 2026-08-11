import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
await page.addInitScript(() => {
  localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
});

const transcript = "重试请求的响应丢失后，网页通过任务状态确认后台已经接受重试。".repeat(40);
let retryAccepted = false;
let commandCalls = 0;

await page.route("**/api/v3/capabilities", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    integrity_recheck: true,
    transcription_providers: { local: true, cloudflare: true },
  }),
}));
await page.route("**/api/v3/parser/records/record-command-reconcile/transcription-tasks", (route) =>
  route.fulfill({
    status: 202,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-command-reconcile",
        operation: "transcription",
        transcription_provider: "cloudflare",
        state: "created",
        progress: {},
      },
    }),
  })
);
await page.route("**/api/v3/parser/tasks/task-command-reconcile/commands", async (route) => {
  commandCalls += 1;
  retryAccepted = true;
  await route.abort("connectionreset");
});
await page.route("**/api/v3/parser/tasks/task-command-reconcile", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    task: retryAccepted
      ? {
          id: "task-command-reconcile",
          operation: "transcription",
          transcription_provider: "cloudflare",
          state: "completed",
          progress: { stage: "complete", label: "逐字稿已生成", percent: 100 },
        }
      : {
          id: "task-command-reconcile",
          operation: "transcription",
          transcription_provider: "cloudflare",
          state: "failed",
          error_code: "TRANSCRIPTION_QUOTA_EXCEEDED",
          error_message: "转录分钟额度已用完",
          error_retryable: false,
          progress: {},
        },
  }),
}));
await page.route("**/api/v3/parser/records/record-command-reconcile", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      record: {
        id: "record-command-reconcile",
        source_url: "https://example.test/command-reconcile",
        platform: "douyin",
        title: "转录重试确认测试",
        creator: "测试作者",
        description: "",
        duration_seconds: 120,
        thumbnail_url: "",
        transcript_text: retryAccepted ? transcript : "",
      },
    }),
  })
);

try {
  await page.goto(`${baseURL}/next?record=record-command-reconcile`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "转录重试确认测试", exact: true }).waitFor();
  await page.locator("[data-generate-transcript=cloudflare]:visible").click();
  const errorPanel = page.locator("[data-transcription-error]:visible");
  await errorPanel.getByText("转录分钟额度已用完", { exact: true }).waitFor();
  await errorPanel.getByRole("button", { name: "↻ 重试当前线路", exact: true }).click();
  await page.getByRole("button", { name: "展开完整逐字稿 ↓", exact: true }).waitFor({
    timeout: 8_000,
  });

  if (commandCalls !== 1) throw new Error(`重试命令执行了 ${commandCalls} 次`);
  console.log(JSON.stringify({ ok: true, commandCalls, lostResponseReconciled: true }));
} finally {
  await browser.close();
}
