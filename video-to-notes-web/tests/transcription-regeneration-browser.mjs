import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
await page.addInitScript(() => {
  localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
});

const shortTranscript = "这是云端第一次返回的不完整逐字稿，只有视频开头的一小段内容。";
const longTranscript = "这是重新生成后的完整逐字稿，包含视频从开头到结尾的全部内容。".repeat(120);
let currentTranscript = shortTranscript;
let activeProvider = "cloudflare";
let taskReads = 0;

await page.route("**/api/v3/capabilities", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    integrity_recheck: true,
    transcription_providers: { local: true, cloudflare: true },
  }),
}));
await page.route("**/api/v3/parser/records/record-regenerate/transcription-tasks", async (route) => {
  const body = route.request().postDataJSON();
  if (body.replace_existing !== true) {
    throw new Error("重新生成没有声明保留并替换已有逐字稿");
  }
  activeProvider = body.provider;
  taskReads = 0;
  await route.fulfill({
    status: 202,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: `task-${activeProvider}`,
        operation: "transcription",
        transcription_provider: activeProvider,
        state: "created",
        progress: {},
      },
    }),
  });
});
await page.route("**/api/v3/parser/tasks/task-*", async (route) => {
  taskReads += 1;
  if (activeProvider === "cloudflare") {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        task: {
          id: "task-cloudflare",
          operation: "transcription",
          transcription_provider: "cloudflare",
          state: "failed",
          error_code: "TRANSCRIPTION_INCOMPLETE",
          error_message: "云端只返回了 76 个字，结果明显不完整，已保留原逐字稿。请重试或切换转录线路。",
          error_retryable: true,
          progress: {},
        },
      }),
    });
    return;
  }
  const complete = taskReads > 1;
  if (complete) currentTranscript = longTranscript;
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-local",
        operation: "transcription",
        transcription_provider: "local",
        state: complete ? "completed" : "transcribing",
        progress: {
          stage: complete ? "complete" : "transcribe",
          label: complete ? "逐字稿已生成" : "生成逐字稿",
          percent: complete ? 100 : 55,
        },
      },
    }),
  });
});
await page.route("**/api/v3/parser/records/record-regenerate", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    record: {
      id: "record-regenerate",
      source_url: "https://example.test/video",
      platform: "douyin",
      title: "逐字稿重新生成测试",
      creator: "测试作者",
      description: "",
      duration_seconds: 152,
      thumbnail_url: "",
      transcript_text: currentTranscript,
    },
  }),
}));

try {
  await page.goto(`${baseURL}/next?record=record-regenerate`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "逐字稿重新生成测试", exact: true }).waitFor();
  await page.getByRole("button", { name: /重新生成 \/ 切换线路/ }).click();
  await page.getByText("选择这次重新生成使用的线路", { exact: true }).waitFor();

  await page.locator("[data-transcript-regenerate] [data-generate-transcript=cloudflare]").click();
  await page.getByRole("alert").getByText(/云端只返回了 76 个字/).waitFor();
  await page.getByRole("button", { name: "↻ 重试当前线路", exact: true }).waitFor();
  await page.getByRole("button", { name: "切换转录线路", exact: true }).click();
  if ((await page.locator(".transcript-preview").innerText()).trim() !== shortTranscript) {
    throw new Error("失败后没有保留原逐字稿");
  }

  await page.locator("[data-transcript-regenerate] [data-generate-transcript=local]").click();
  await page.getByRole("button", { name: "展开完整逐字稿 ↓", exact: true }).waitFor();
  await page.getByRole("button", { name: "展开完整逐字稿 ↓", exact: true }).click();
  await page.getByRole("button", { name: "收起逐字稿 ↑", exact: true }).waitFor();
  await page.getByRole("button", { name: "收起逐字稿 ↑", exact: true }).click();
  await page.getByRole("button", { name: "展开完整逐字稿 ↓", exact: true }).waitFor();

  if ((await page.locator(".transcript-preview").innerText()).trim() !== longTranscript) {
    throw new Error("切换线路成功后没有显示完整新逐字稿");
  }
  console.log(JSON.stringify({
    ok: true,
    incompleteErrorShown: true,
    originalPreserved: true,
    switchedProvider: "local",
    expandCollapseRestored: true,
  }));
} finally {
  await browser.close();
}
