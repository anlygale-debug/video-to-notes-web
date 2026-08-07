import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });

async function assertSettled(locator, label, attribute) {
  await locator.waitFor({ state: "visible" });
  await locator.evaluate((node, name) => new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => reject(new Error(`${name} 动效未在时限内完成`)), 2400);
    const check = () => {
      if (node.getAttribute(name) === "settled") {
        window.clearTimeout(timeout);
        resolve();
        return;
      }
      window.requestAnimationFrame(check);
    };
    check();
  }), attribute);

  const layout = await locator.evaluate((node) => ({
    transform: getComputedStyle(node).transform,
    opacity: getComputedStyle(node).opacity,
    visibility: getComputedStyle(node).visibility,
  }));
  if (layout.transform !== "none" || layout.opacity !== "1" || layout.visibility !== "visible") {
    throw new Error(`${label} 动效结束后没有回到稳定布局：${JSON.stringify(layout)}`);
  }
}

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto(`${baseURL}/next?acceptance=1&full-flow-motion=1`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.documentElement.dataset.motionReady === "true");

  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await assertSettled(page.locator("#notes-view"), "笔记模块切换", "data-motion-view");

  const noteStates = [
    "analyzing",
    "recommendations",
    "custom",
    "direct-generating",
    "outline",
    "chapter-generating",
    "chapter-failure",
    "recovery",
    "generation-complete",
    "reading",
    "editing",
    "export",
    "note-history",
  ];
  for (const state of noteStates) {
    await page.locator(`[data-notes-state="${state}"]`).click();
    await assertSettled(page.locator("#notes-state-host > :first-child"), `笔记状态 ${state}`, "data-motion-state");
  }

  await page.getByRole("button", { name: "视频解析", exact: true }).click();
  await assertSettled(page.locator("#parser-view"), "解析模块切换", "data-motion-view");
  for (const state of ["loading", "success", "failure", "history"]) {
    await page.locator(`[data-parser-state="${state}"]`).click();
    await assertSettled(page.locator("#state-host > :first-child"), `解析状态 ${state}`, "data-motion-state");
  }

  const contract = await page.evaluate(() => ({
    mode: document.documentElement.dataset.motionMode,
    dynamicCards: document.querySelectorAll("[data-motion-bound]").length,
  }));
  if (contract.mode !== "full" || contract.dynamicCards < 1) {
    throw new Error(`全流程微交互动效没有绑定到动态内容：${JSON.stringify(contract)}`);
  }

  const reducedPage = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  await reducedPage.emulateMedia({ reducedMotion: "reduce" });
  await reducedPage.goto(`${baseURL}/next?acceptance=1&full-flow-motion=reduced`, { waitUntil: "networkidle" });
  await reducedPage.getByRole("button", { name: "笔记生成", exact: true }).click();
  await reducedPage.locator('[data-notes-state="recommendations"]').click();
  await assertSettled(reducedPage.locator("#notes-view"), "减少动态模式的模块切换", "data-motion-view");
  await assertSettled(reducedPage.locator("#notes-state-host > :first-child"), "减少动态模式的状态切换", "data-motion-state");
  const reducedContract = await reducedPage.evaluate(() => ({
    mode: document.documentElement.dataset.motionMode,
    animatedItem: [...document.querySelectorAll("[data-motion-item]")].some((node) =>
      getComputedStyle(node).transform !== "none" || getComputedStyle(node).opacity !== "1"
    ),
  }));
  if (reducedContract.mode !== "reduced" || reducedContract.animatedItem) {
    throw new Error(`减少动态偏好没有覆盖完整流程：${JSON.stringify(reducedContract)}`);
  }

  console.log(JSON.stringify({ ok: true, noteStates: noteStates.length, parserStates: 4, reducedMotion: true }));
} finally {
  await browser.close();
}
