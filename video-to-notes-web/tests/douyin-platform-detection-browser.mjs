import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const douyinUrl = "https://v.douyin.com/ieYvXhHW";

await page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});
await page.route("**/api/v3/parser/records/record-douyin", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      record: {
        id: "record-douyin",
        source_url: douyinUrl,
        platform: "douyin",
        title: "抖音平台识别测试",
        creator: "测试作者",
        description: "",
        duration_seconds: 6,
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
          id: "task-douyin",
          state: "created",
          source_url: douyinUrl,
          platform_hint: "douyin",
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
        id: "task-douyin",
        state: "completed",
        source_url: douyinUrl,
        platform_hint: "douyin",
        record_id: "record-douyin",
        progress: { stage: "complete", label: "解析完成", percent: 100 },
      },
    }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  const input = page.locator("#video-link");
  await input.waitFor({ state: "visible" });
  await input.evaluate((element, shareText) => {
    element.value = shareText;
    element.dispatchEvent(new Event("input", { bubbles: true }));
  }, `复制此链接，打开抖音查看作品 ${douyinUrl}`);

  const chip = (await page.locator("#platform-detection .platform-chip").innerText()).trim();
  const message = (
    await page.locator("#platform-detection .platform-message").innerText()
  ).trim();
  if (chip !== "抖音" || !message.includes("已识别为抖音")) {
    throw new Error(`抖音即时识别不正确：${chip} / ${message}`);
  }

  await page.locator("#parser-form").evaluate((form) => {
    const submitter = form.querySelector('button[type="submit"]');
    form.dispatchEvent(new SubmitEvent("submit", { bubbles: true, cancelable: true, submitter }));
  });
  await page.getByRole("heading", { name: "抖音平台识别测试", exact: true }).waitFor();

  const resultPlatform = (
    await page.locator("[data-result-platform-name]").innerText()
  ).trim();
  const coverPlatform = (await page.locator(".cover-platform").innerText()).trim();
  if (resultPlatform !== "抖音" || coverPlatform !== "抖音") {
    throw new Error(
      `解析完成后的抖音平台展示不正确：字段=${resultPlatform}，封面=${coverPlatform}`
    );
  }

  console.log(JSON.stringify({ ok: true, chip, message, resultPlatform, coverPlatform }));
} finally {
  await browser.close();
}
