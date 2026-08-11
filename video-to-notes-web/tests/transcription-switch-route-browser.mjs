import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
await page.addInitScript(() => {
  localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
});

await page.route("**/api/v3/capabilities", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    integrity_recheck: true,
    transcription_providers: { local: true, cloudflare: true },
  }),
}));
await page.route("**/api/v3/parser/records/record-switch-route/transcription-tasks", (route) =>
  route.fulfill({
    status: 202,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-switch-route",
        operation: "transcription",
        transcription_provider: "cloudflare",
        state: "created",
        progress: {},
      },
    }),
  })
);
await page.route("**/api/v3/parser/tasks/task-switch-route", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    task: {
      id: "task-switch-route",
      operation: "transcription",
      transcription_provider: "cloudflare",
      state: "failed",
      error_code: "TRANSCRIPTION_UPLOAD_TIMEOUT",
      error_message: "高速线路暂时没有响应。",
      error_retryable: true,
      progress: {},
    },
  }),
}));
await page.route("**/api/v3/parser/records/record-switch-route", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      record: {
        id: "record-switch-route",
        source_url: "https://example.test/switch-route",
        platform: "douyin",
        title: "转录线路切换测试",
        creator: "测试作者",
        description: "",
        duration_seconds: 120,
        thumbnail_url: "",
        transcript_text: "",
      },
    }),
  })
);

try {
  await page.goto(`${baseURL}/next?record=record-switch-route`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "转录线路切换测试", exact: true }).waitFor();
  await page.locator("[data-generate-transcript=cloudflare]:visible").click();
  const errorPanel = page.locator("[data-transcription-error]:visible");
  await errorPanel.getByText("高速线路暂时没有响应。", { exact: true }).waitFor();
  await errorPanel.getByRole("button", { name: "切换转录线路", exact: true }).click();
  await page.getByText("请选择免费转录或高速高质量转录。", { exact: true }).waitFor();

  const freeRoute = page.locator("[data-transcript-empty] [data-generate-transcript=local]");
  if (!(await freeRoute.evaluate((node) => node === document.activeElement))) {
    throw new Error("切换线路后没有把焦点带回可选择的转录线路");
  }
  console.log(JSON.stringify({ ok: true, noTranscriptRouteChooserFocused: true }));
} finally {
  await browser.close();
}
