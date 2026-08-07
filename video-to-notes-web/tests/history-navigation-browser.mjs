import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });

async function expectHistoryInViewport(selector, label) {
  try {
    await page.waitForFunction((target) => {
      const element = document.querySelector(target);
      if (!element) return false;
      const bounds = element.getBoundingClientRect();
      return bounds.top >= 0 && bounds.top < window.innerHeight * 0.5;
    }, selector, { timeout: 1800 });
  } catch {
    const bounds = await page.locator(selector).boundingBox();
    throw new Error(`${label}已打开，但没有自动滚入主要视野：${JSON.stringify(bounds)}`);
  }
}

await page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});
await page.route("**/api/v3/parser/records?**", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      items: [{
        id: "history-parser-record",
        source_url: "https://example.test/history-video",
        platform: "bilibili",
        title: "历史解析记录测试",
        creator: "测试作者",
        duration_seconds: 120,
        note_id: null,
      }],
      next_cursor: null,
    }),
  });
});
await page.route("**/api/v3/notes?**", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      items: [{
        id: "history-note",
        title: "历史笔记测试",
        source_type: "paste",
        version: 1,
        parser_record_id: null,
      }],
      next_cursor: null,
    }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });

  const parserShortcut = page.locator('[data-history-shortcut="parser"]');
  const noteShortcut = page.locator('[data-history-shortcut="notes"]');
  if (await parserShortcut.count() !== 1 || await noteShortcut.count() !== 1) {
    throw new Error("首屏没有同时提供解析历史与笔记历史的醒目入口");
  }
  for (const shortcut of [parserShortcut, noteShortcut]) {
    const box = await shortcut.boundingBox();
    if (!box || box.width < 210 || box.height < 54) {
      throw new Error(`历史入口仍然过小：${JSON.stringify(box)}`);
    }
  }

  await noteShortcut.click();
  await page.getByText("历史笔记测试", { exact: true }).waitFor();
  if (await page.locator("#notes-view").isHidden()) {
    throw new Error("从解析页点击笔记历史后没有切换到笔记视图");
  }
  await expectHistoryInViewport("#notes-state-host .note-history-stack", "笔记历史");

  await parserShortcut.click();
  await page.getByText("历史解析记录测试", { exact: true }).waitFor();
  if (await page.locator("#parser-view").isHidden()) {
    throw new Error("从笔记页点击解析历史后没有切换到解析视图");
  }
  await expectHistoryInViewport("#state-host .history-section", "解析历史");

  console.log(JSON.stringify({ ok: true, prominent: true, crossViewNavigation: true, historyInViewport: true }));
} finally {
  await browser.close();
}
