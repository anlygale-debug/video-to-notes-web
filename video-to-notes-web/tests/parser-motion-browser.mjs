import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });

async function stubSafeStartup(page) {
  await page.route("**/api/v3/migrations/browser-history", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
  });
}

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  await stubSafeStartup(page);
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto(`${baseURL}/next?motion-test=1`, { waitUntil: "networkidle" });

  await page.waitForFunction(() => document.documentElement.dataset.motionReady === "true");
  const motionState = await page.evaluate(() => ({
    gsap: typeof window.gsap?.timeline === "function",
    scrollTrigger: typeof window.ScrollTrigger?.create === "function",
    mode: document.documentElement.dataset.motionMode,
    heroTransform: getComputedStyle(document.querySelector("#parser .intro-grid")).transform,
    heroOpacity: getComputedStyle(document.querySelector("#parser .intro-grid")).opacity,
  }));
  if (!motionState.gsap || !motionState.scrollTrigger) {
    throw new Error("视频解析首页没有加载完整 GSAP 动效运行时");
  }
  if (motionState.mode !== "full") {
    throw new Error(`标准动态偏好没有启用完整动效：${motionState.mode}`);
  }
  if (motionState.heroTransform !== "none" || motionState.heroOpacity !== "1") {
    throw new Error(`首屏入场完成后没有回到稳定布局：${JSON.stringify(motionState)}`);
  }

  const reducedPage = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  await stubSafeStartup(reducedPage);
  await reducedPage.emulateMedia({ reducedMotion: "reduce" });
  await reducedPage.goto(`${baseURL}/next?motion-test=reduced`, { waitUntil: "networkidle" });
  await reducedPage.waitForFunction(() => document.documentElement.dataset.motionReady === "true");
  const reducedState = await reducedPage.evaluate(() => ({
    mode: document.documentElement.dataset.motionMode,
    transformed: [...document.querySelectorAll("[data-motion-reveal]")].some((element) =>
      getComputedStyle(element).transform !== "none" || getComputedStyle(element).opacity !== "1"
    ),
  }));
  if (reducedState.mode !== "reduced" || reducedState.transformed) {
    throw new Error(`减少动态偏好仍执行了位移动画：${JSON.stringify(reducedState)}`);
  }

  console.log(JSON.stringify({ ok: true, fullMotion: true, reducedMotion: true }));
} finally {
  await browser.close();
}
