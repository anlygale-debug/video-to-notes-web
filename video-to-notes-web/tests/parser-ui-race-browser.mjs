import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const sourceURL = "https://www.bilibili.com/video/BV1RACE";
const thumbnailURL = "https://images.example.test/video-cover.png";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
const errors = [];
let postCount = 0;
let taskReadCount = 0;

page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});

await page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});
await page.route(
  "**/api/v3/parser/records/record-race/thumbnail",
  async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "image/png",
    body: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAFElEQVR42mNkYPj/n4GBgYGJAQoAHgQCAf2Kz9sAAAAASUVORK5CYII=",
      "base64"
    ),
  });
  }
);
await page.route("**/api/v3/parser/records/record-race", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      record: {
        id: "record-race",
        source_url: sourceURL,
        platform: "bilibili",
        title: "竞态测试视频",
        creator: "测试作者",
        description: "",
        duration_seconds: 120,
        thumbnail_url: thumbnailURL,
        transcript_text: "竞态测试逐字稿",
      },
    }),
  });
});
await page.route("**/api/v3/parser/tasks**", async (route) => {
  const request = route.request();
  if (request.method() === "POST") {
    postCount += 1;
    await new Promise((resolve) => setTimeout(resolve, 150));
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({
        task: { id: "task-race", state: "created", source_url: sourceURL, progress: {} },
      }),
    });
    return;
  }
  taskReadCount += 1;
  const stages = [
    ["resolving", "resolve", "识别视频来源", 10],
    ["downloading", "download", "获取视频音频", 30],
    ["transcribing", "transcribe", "生成逐字稿", 55],
    ["saving", "save", "整理并保存结果", 90],
    ["completed", "complete", "解析完成", 100],
  ];
  const [state, stage, label, percent] = stages[Math.min(taskReadCount - 1, stages.length - 1)];
  await new Promise((resolve) => setTimeout(resolve, 220));
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-race",
        state,
        source_url: sourceURL,
        record_id: state === "completed" ? "record-race" : null,
        progress: { stage, label, percent },
      },
    }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.locator("#video-link").fill(`【竞态测试】${sourceURL}`);
  await page.locator("#parser-form").evaluate((form) => {
    const submitter = form.querySelector('button[type="submit"]');
    form.dispatchEvent(new SubmitEvent("submit", { bubbles: true, cancelable: true, submitter }));
    form.dispatchEvent(new SubmitEvent("submit", { bubbles: true, cancelable: true, submitter }));
  });

  await page.locator('#parser-form button[type="submit"]').waitFor({ state: "visible" });
  if (!(await page.locator('#parser-form button[type="submit"]').isDisabled())) {
    throw new Error("解析开始后提交按钮没有立即锁定");
  }
  await page.getByRole("heading", { name: "正在识别视频来源", exact: true }).waitFor();
  await page.getByRole("heading", { name: "正在获取音频内容", exact: true }).waitFor();
  const orbitAnimation = await page.locator(".parser-progress-orbit").evaluate(
    (element) => getComputedStyle(element).animationName
  );
  if (!orbitAnimation || orbitAnimation === "none") throw new Error("解析进度没有动态反馈");
  await page.getByRole("heading", { name: "正在生成逐字稿", exact: true }).waitFor();
  await page.getByRole("heading", { name: "正在整理解析结果", exact: true }).waitFor();
  await page.getByRole("heading", { name: "竞态测试视频", exact: true }).waitFor();
  const cover = page.locator("[data-result-thumbnail]");
  await cover.waitFor({ state: "visible" });
  if (
    !(await cover.getAttribute("src"))?.includes(
      "/api/v3/parser/records/record-race/thumbnail"
    )
  ) {
    throw new Error("真实视频封面没有绑定到解析记录安全端点");
  }
  await page.waitForFunction(() => document.querySelector("[data-result-thumbnail]")?.naturalWidth > 0);
  await page.waitForTimeout(1200);

  if (postCount !== 1) throw new Error(`连续提交创建了 ${postCount} 个解析任务`);
  if (!(await page.getByRole("heading", { name: "竞态测试视频", exact: true }).isVisible())) {
    throw new Error("解析成功后又被旧轮询覆盖");
  }
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, postCount, taskReadCount, stableSuccess: true }));
} finally {
  await browser.close();
}
