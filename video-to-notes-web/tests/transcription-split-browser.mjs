import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const sourceURL = "https://www.bilibili.com/video/BV1SPLIT";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
await page.addInitScript(() => {
  localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
});
let transcriptGenerated = false;
let parseRequest = null;
let transcriptionPosts = 0;
let transcriptionReads = 0;

await page.route("**/api/v3/capabilities", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    integrity_recheck: true,
    transcription_providers: { local: true, cloudflare: true },
  }),
}));
await page.route("**/api/v3/migrations/browser-history", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: '{"ok":true}',
}));
await page.route("**/api/v3/parser/records/record-split/transcription-tasks", async (route) => {
  transcriptionPosts += 1;
  const body = route.request().postDataJSON();
  if (body.provider !== "cloudflare") {
    throw new Error(`未使用用户选择的云端线路：${JSON.stringify(body)}`);
  }
  await route.fulfill({
    status: 202,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-transcription",
        operation: "transcription",
        transcription_provider: "cloudflare",
        state: "created",
        progress: {},
      },
    }),
  });
});
await page.route("**/api/v3/parser/records/record-split", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    record: {
      id: "record-split",
      source_url: sourceURL,
      platform: "bilibili",
      title: "分阶段转录测试",
      creator: "测试作者",
      description: "先解析视频信息，再按需生成逐字稿。",
      duration_seconds: 120,
      thumbnail_url: "",
      transcript_text: transcriptGenerated ? "这是用户主动生成的逐字稿。" : "",
    },
  }),
}));
await page.route("**/api/v3/parser/tasks/task-transcription", async (route) => {
  transcriptionReads += 1;
  const complete = transcriptionReads > 2;
  if (complete) transcriptGenerated = true;
  const transcriptionPercent = transcriptionReads === 1 ? 30 : 70;
  const processedSeconds = transcriptionReads === 1 ? 36 : 84;
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-transcription",
        operation: "transcription",
        transcription_provider: "cloudflare",
        state: complete ? "completed" : "transcribing",
        progress: {
          stage: complete ? "complete" : "transcribe",
          label: complete ? "逐字稿已生成" : "生成逐字稿",
          percent: complete ? 100 : 55,
          transcription_percent: complete ? 100 : transcriptionPercent,
          processed_seconds: complete ? 120 : processedSeconds,
          total_seconds: 120,
          remaining_seconds: complete ? 0 : (transcriptionReads === 1 ? 84 : 36),
        },
      },
    }),
  });
});
await page.route("**/api/v3/parser/tasks/task-metadata", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    task: {
      id: "task-metadata",
      operation: "metadata",
      state: "completed",
      source_url: sourceURL,
      record_id: "record-split",
      progress: { stage: "complete", label: "视频信息已解析", percent: 100 },
    },
  }),
}));
await page.route("**/api/v3/parser/tasks", async (route) => {
  parseRequest = route.request().postDataJSON();
  await route.fulfill({
    status: 202,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-metadata",
        operation: "metadata",
        state: "created",
        source_url: sourceURL,
        progress: {},
      },
    }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.locator("#video-link").fill(sourceURL);
  await page.locator("#parser-form").evaluate((form) => {
    const submitter = form.querySelector('button[type="submit"]');
    form.dispatchEvent(new SubmitEvent("submit", {
      bubbles: true,
      cancelable: true,
      submitter,
    }));
  });
  await page.getByRole("heading", { name: "分阶段转录测试", exact: true }).waitFor();

  if (parseRequest?.include_transcript !== false) {
    throw new Error(`首次解析仍然自动生成逐字稿：${JSON.stringify(parseRequest)}`);
  }
  await page.getByRole("button", { name: /高速高质量转录/ }).waitFor();
  await page.getByRole("button", { name: /免费转录/ }).waitFor();
  if (!(await page.getByRole("button", { name: "↓ 视频 MP4" }).isVisible())) {
    throw new Error("逐字稿生成前没有保留视频下载入口");
  }
  if (await page.getByRole("button", { name: "复制全文" }).isVisible()) {
    throw new Error("逐字稿生成前提前显示了复制入口");
  }

  await page.getByRole("button", { name: /高速高质量转录/ }).click();
  await page.locator("[data-transcription-progress-percent]", { hasText: "30%" }).waitFor();
  await page.getByText("已处理 0:36 / 2:00", { exact: true }).waitFor();
  await page.getByText("预计还需约 2 分钟", { exact: true }).waitFor();
  await page.getByText("这是用户主动生成的逐字稿。").waitFor();
  await page.getByRole("button", { name: "复制全文" }).waitFor();

  if (transcriptionPosts !== 1) {
    throw new Error(`逐字稿任务创建次数异常：${transcriptionPosts}`);
  }
  console.log(JSON.stringify({
    ok: true,
    metadataOnly: true,
    transcriptionPosts,
    transcriptGenerated,
  }));
} finally {
  await browser.close();
}
