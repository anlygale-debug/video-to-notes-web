import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
let migrationRequests = 0;

await page.route("**/api/v3/access/status", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      enabled: true,
      authenticated: true,
      access: {
        label: "线上测试者",
        remaining_transcription_seconds: 3600,
        remaining_note_generations: 5,
      },
    }),
  });
});
await page.route("**/api/v3/migrations/browser-history", async (route) => {
  migrationRequests += 1;
  await route.fulfill({
    status: 404,
    contentType: "application/json",
    body: JSON.stringify({
      error: {
        code: "LEGACY_API_DISABLED",
        message: "该旧接口未在公网版本开放",
      },
    }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });

  if (migrationRequests !== 0) {
    throw new Error(`公网启动仍调用旧历史迁移接口：${migrationRequests} 次`);
  }
  const startupWarning = page.getByText(/启动检查未完成/);
  if (await startupWarning.count()) {
    throw new Error(`公网启动仍显示误报：${await startupWarning.first().innerText()}`);
  }
  console.log(JSON.stringify({ ok: true, migrationRequests, startupWarning: false }));
} finally {
  await browser.close();
}
