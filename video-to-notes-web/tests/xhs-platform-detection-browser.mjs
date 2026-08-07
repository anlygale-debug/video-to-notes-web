import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

await page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});
await page.route("**/api/v3/parser/records/record-xhs", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      record: {
        id: "record-xhs",
        source_url: "http://xhslink.cn/o/4W5MlG9aJai",
        platform: "xiaohongshu",
        title: "小红书平台识别测试",
        creator: "测试作者",
        description: "",
        duration_seconds: 60,
        thumbnail_url: "",
        transcript_text: "测试逐字稿",
      },
    }),
  });
});
await page.route("**/api/v3/parser/tasks**", async (route) => {
  if (route.request().method() === "POST") {
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({
        task: {
          id: "task-xhs",
          state: "created",
          source_url: "http://xhslink.cn/o/4W5MlG9aJai",
          platform_hint: "xiaohongshu",
          progress: {},
        },
      }),
    });
    return;
  }
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "task-xhs",
        state: "completed",
        source_url: "http://xhslink.cn/o/4W5MlG9aJai",
        platform_hint: "xiaohongshu",
        record_id: "record-xhs",
        progress: { stage: "complete", label: "解析完成", percent: 100 },
      },
    }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.locator("#video-link").fill(
    "拯救你AI审美的5个宝藏网站❗️打破信息差 提升网页质... " +
    "http://xhslink.cn/o/4W5MlG9aJai\n先复制这段口令，再去【小红书】打开笔记~"
  );

  const chip = (await page.locator("#platform-detection .platform-chip").innerText()).trim();
  const message = (
    await page.locator("#platform-detection .platform-message").innerText()
  ).trim();

  if (chip !== "小红书") {
    throw new Error(`xhslink.cn 被错误显示为：${chip}`);
  }
  if (!message.includes("已识别为小红书")) {
    throw new Error(`小红书识别提示不正确：${message}`);
  }

  await page.locator("#parser-form").evaluate((form) => {
    const submitter = form.querySelector('button[type="submit"]');
    form.dispatchEvent(new SubmitEvent("submit", { bubbles: true, cancelable: true, submitter }));
  });
  await page.getByRole("heading", { name: "小红书平台识别测试", exact: true }).waitFor();

  const resultPlatform = (
    await page.locator("[data-result-platform-name]").innerText()
  ).trim();
  const coverPlatform = (await page.locator(".cover-platform").innerText()).trim();
  if (resultPlatform !== "小红书" || coverPlatform !== "小红书") {
    throw new Error(
      `解析完成后的平台展示不正确：字段=${resultPlatform}，封面=${coverPlatform}`
    );
  }

  console.log(JSON.stringify({ ok: true, chip, message, resultPlatform, coverPlatform }));
} finally {
  await browser.close();
}
