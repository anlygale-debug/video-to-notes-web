import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });

await page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});

try {
  await page.goto(`${baseURL}/next?motion-interactions=1`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.documentElement.dataset.motionReady === "true");

  const shortcut = page.locator('[data-history-shortcut="parser"]');
  const arrow = shortcut.locator(".history-shortcut__arrow");
  const restingArrow = await arrow.evaluate((element) => getComputedStyle(element).transform);
  await shortcut.hover();
  await page.waitForFunction(() =>
    getComputedStyle(document.querySelector('[data-history-shortcut="parser"] .history-shortcut__arrow')).transform !== "none"
  );
  const activeArrow = await arrow.evaluate((element) => getComputedStyle(element).transform);
  if (activeArrow === restingArrow) {
    throw new Error("解析历史入口悬停后没有方向性箭头反馈");
  }

  const input = page.locator("#video-link");
  const form = page.locator("#parser-form");
  await input.focus();
  await page.waitForFunction(() => {
    const form = document.querySelector("#parser-form");
    return form?.dataset.motionFocus === "active" && getComputedStyle(form).transform !== "none";
  });
  const focusedTransform = await form.evaluate((element) => getComputedStyle(element).transform);
  if (focusedTransform === "none") {
    throw new Error("视频链接输入聚焦后没有产生层级位移");
  }
  await page.locator("#parser-view .parser-stage .stage-heading h2").click();
  await page.waitForFunction(() => {
    const form = document.querySelector("#parser-form");
    return form?.dataset.motionFocus === "idle" && getComputedStyle(form).transform === "none";
  });
  const restingForm = await form.evaluate((element) => getComputedStyle(element).transform);
  if (restingForm !== "none") {
    throw new Error(`输入区失焦后没有回到稳定布局：${restingForm}`);
  }

  console.log(JSON.stringify({ ok: true, historyHover: true, inputFocus: true }));
} finally {
  await browser.close();
}
