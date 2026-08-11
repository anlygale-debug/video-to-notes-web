import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
await page.addInitScript(() => {
  localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
});

const transcript = "状态查询短暂中断后，网页仍然自动找回了已经完成的逐字稿。".repeat(40);
let taskReads = 0;

await page.route("**/api/v3/capabilities", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    integrity_recheck: true,
    transcription_providers: { local: true, cloudflare: true },
  }),
}));
await page.route("**/api/v3/parser/records/record-status-recovery/transcription-tasks", (route) =>
  route.fulfill({
    status: 202,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-status-recovery",
        operation: "transcription",
        transcription_provider: "cloudflare",
        state: "created",
        progress: {},
      },
    }),
  })
);
await page.route("**/api/v3/parser/tasks/task-status-recovery", async (route) => {
  taskReads += 1;
  if (taskReads === 1) {
    await route.abort("connectionreset");
    return;
  }
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-status-recovery",
        operation: "transcription",
        transcription_provider: "cloudflare",
        state: "completed",
        progress: { stage: "complete", label: "逐字稿已生成", percent: 100 },
      },
    }),
  });
});
await page.route("**/api/v3/parser/records/record-status-recovery", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      record: {
        id: "record-status-recovery",
        source_url: "https://example.test/status-recovery",
        platform: "douyin",
        title: "转录状态恢复测试",
        creator: "测试作者",
        description: "",
        duration_seconds: 120,
        thumbnail_url: "",
        transcript_text: taskReads > 1 ? transcript : "",
      },
    }),
  })
);

try {
  await page.goto(`${baseURL}/next?record=record-status-recovery`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "转录状态恢复测试", exact: true }).waitFor();
  await page.locator("[data-generate-transcript=cloudflare]:visible").click();
  await page.getByRole("button", { name: "展开完整逐字稿 ↓", exact: true }).waitFor({
    timeout: 8_000,
  });

  if (taskReads < 2) throw new Error("状态请求失败后没有自动重新查询任务");
  if (await page.locator("[data-transcription-error]:visible").count()) {
    throw new Error("单次状态请求失败被错误展示为转录失败");
  }
  console.log(JSON.stringify({ ok: true, taskReads, transientStatusFailureRecovered: true }));
} finally {
  await browser.close();
}
