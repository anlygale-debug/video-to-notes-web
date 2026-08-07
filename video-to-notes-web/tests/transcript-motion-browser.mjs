import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const transcriptText = "这是用于验证逐字稿高级展开动画的长文本。".repeat(260);
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });

await page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});
await page.route("**/api/v3/parser/records/**", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      record: {
        id: "motion-record",
        source_url: "https://example.test/motion-video",
        platform: "bilibili",
        title: "逐字稿动效测试",
        creator: "测试作者",
        description: "只验证本地交互动效",
        duration_seconds: 180,
        thumbnail_url: "",
        transcript_text: transcriptText,
      },
    }),
  });
});

try {
  await page.goto(`${baseURL}/next?record=motion-record`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.documentElement.dataset.motionReady === "true");
  await page.getByRole("heading", { name: "逐字稿动效测试", exact: true }).waitFor();

  const transcript = page.locator(".transcript-preview");
  const toggle = page.getByRole("button", { name: "展开完整逐字稿 ↓", exact: true });
  const collapsedHeight = await transcript.evaluate((element) => element.getBoundingClientRect().height);
  await toggle.click();
  await page.waitForFunction(() =>
    document.querySelector(".transcript-preview")?.dataset.motionTranscript === "expanding"
  );
  await page.waitForFunction(() =>
    document.querySelector(".transcript-preview")?.dataset.motionTranscript === "expanded"
  );
  const expandedHeight = await transcript.evaluate((element) => element.getBoundingClientRect().height);
  if (expandedHeight <= collapsedHeight * 1.5) {
    throw new Error(`逐字稿没有展开到真实内容高度：${collapsedHeight} → ${expandedHeight}`);
  }

  await page.getByRole("button", { name: "收起逐字稿 ↑", exact: true }).click();
  await page.waitForFunction(() =>
    document.querySelector(".transcript-preview")?.dataset.motionTranscript === "collapsing"
  );
  await page.waitForFunction(() =>
    document.querySelector(".transcript-preview")?.dataset.motionTranscript === "collapsed"
  );
  const collapsedAgain = await transcript.evaluate((element) => element.getBoundingClientRect().height);
  if (Math.abs(collapsedAgain - collapsedHeight) > 2) {
    throw new Error(`逐字稿收起后高度不稳定：${collapsedHeight} → ${collapsedAgain}`);
  }

  console.log(JSON.stringify({ ok: true, collapsedHeight, expandedHeight, collapsedAgain }));
} finally {
  await browser.close();
}
