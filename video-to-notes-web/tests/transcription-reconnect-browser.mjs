import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
await page.addInitScript(() => {
  localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
});

const transcript = "重新连接只是找回后台任务状态，不会重复创建一次高速转录。".repeat(40);
let taskReads = 0;
let commandCalls = 0;

await page.route("**/api/v3/capabilities", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    integrity_recheck: true,
    transcription_providers: { local: true, cloudflare: true },
  }),
}));
await page.route("**/api/v3/parser/records/record-reconnect/transcription-tasks", (route) =>
  route.fulfill({
    status: 202,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-reconnect",
        operation: "transcription",
        transcription_provider: "cloudflare",
        state: "created",
        progress: {},
      },
    }),
  })
);
await page.route("**/api/v3/parser/tasks/task-reconnect/commands", (route) => {
  commandCalls += 1;
  return route.fulfill({ status: 409, contentType: "application/json", body: "{}" });
});
await page.route("**/api/v3/parser/tasks/task-reconnect", async (route) => {
  taskReads += 1;
  if (taskReads <= 6) {
    await route.abort("connectionreset");
    return;
  }
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-reconnect",
        operation: "transcription",
        transcription_provider: "cloudflare",
        state: "completed",
        progress: { stage: "complete", label: "逐字稿已生成", percent: 100 },
      },
    }),
  });
});
await page.route("**/api/v3/parser/records/record-reconnect", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      record: {
        id: "record-reconnect",
        source_url: "https://example.test/reconnect",
        platform: "douyin",
        title: "转录任务重新连接测试",
        creator: "测试作者",
        description: "",
        duration_seconds: 120,
        thumbnail_url: "",
        transcript_text: taskReads > 6 ? transcript : "",
      },
    }),
  })
);

try {
  await page.goto(`${baseURL}/next?record=record-reconnect`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "转录任务重新连接测试", exact: true }).waitFor();
  await page.locator("[data-generate-transcript=cloudflare]:visible").click();
  const errorPanel = page.locator("[data-transcription-error]:visible");
  await errorPanel.waitFor({ timeout: 12_000 });
  await errorPanel.getByText(
    "暂时无法读取转录进度，后台任务可能仍在继续。请重新连接任务状态。",
    { exact: true },
  ).waitFor();
  if (await errorPanel.getByRole("button", { name: "切换转录线路", exact: true }).isVisible()) {
    throw new Error("任务状态未知时不应引导用户重复创建另一条转录任务");
  }
  await errorPanel.getByRole("button", { name: "↻ 重新连接任务进度", exact: true }).click();
  await page.getByRole("button", { name: "展开完整逐字稿 ↓", exact: true }).waitFor({
    timeout: 8_000,
  });

  if (commandCalls !== 0) {
    throw new Error("状态断开时错误地重新执行了后台高速转录任务");
  }
  console.log(JSON.stringify({ ok: true, taskReads, commandCalls, clientReconnectRecovered: true }));
} finally {
  await browser.close();
}
