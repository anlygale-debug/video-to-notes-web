import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.addInitScript(() => {
  localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
});

await page.route("**/api/v3/migrations/browser-history", (route) => route.fulfill({
  status: 200, contentType: "application/json", body: '{"ok":true}',
}));
await page.route("**/api/v3/parser/records/record-long", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    record: {
      id: "record-long",
      source_url: "https://www.bilibili.com/video/BV1test",
      platform: "bilibili",
      title: "六十分钟测试视频",
      creator: "测试作者",
      description: "",
      duration_seconds: 60 * 60,
      thumbnail_url: "",
      transcript_text: "短逐字稿",
    },
  }),
}));

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "domcontentloaded" });
  await page.locator('[data-nav="notes"]').click();

  const input = page.locator("#notes-transcript-input");
  const notice = page.locator("#notes-state-host [data-free-capacity]");

  await input.fill("知".repeat(845));
  if ((await notice.getAttribute("data-free-capacity-level")) !== "recommended") {
    throw new Error("短内容没有进入免费线路推荐范围");
  }
  if (!(await notice.innerText()).includes("适合使用免费线路")) {
    throw new Error("短内容提示文案未显示");
  }

  await input.fill("知".repeat(9_001));
  if ((await notice.getAttribute("data-free-capacity-level")) !== "caution") {
    throw new Error("中等内容没有进入谨慎档");
  }

  await input.fill("知".repeat(13_501));
  if ((await notice.getAttribute("data-free-capacity-level")) !== "high_risk") {
    throw new Error("长内容没有进入高风险档");
  }
  if (!(await notice.innerText()).includes("当前不建议用免费线路直接生成")) {
    throw new Error("高风险提示文案未显示");
  }

  await page.goto(`${baseURL}/next?record=record-long`, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "六十分钟测试视频", exact: true }).waitFor();
  const parserNotice = page.locator("#state-host [data-free-capacity]");
  if ((await parserNotice.getAttribute("data-free-capacity-level")) !== "high_risk") {
    throw new Error("已知视频时长没有覆盖较短逐字稿的低风险判断");
  }
  if (!(await parserNotice.innerText()).includes("60 分钟")) {
    throw new Error("解析结果没有向用户显示视频时长判断依据");
  }

  console.log(JSON.stringify({ ok: true, levels: ["recommended", "caution", "high_risk"], parserDuration: "60 分钟" }));
} finally {
  await browser.close();
}
