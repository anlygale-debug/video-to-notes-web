import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
const errors = [];
let unavailableNote = null;
let recheckCount = 0;

page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});

await page.route("**/api/v3/capabilities", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: '{"integrity_recheck":true}',
  });
});

await page.route("**/api/v3/notes/**", async (route) => {
  const request = route.request();
  if (request.method() === "POST" && request.url().endsWith("/integrity-check")) {
    recheckCount += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        note: { ...unavailableNote, integrity: { status: "ok" } },
      }),
    });
    return;
  }
  const response = await route.fetch();
  if (request.method() !== "GET" || !response.ok()) {
    await route.fulfill({ response });
    return;
  }
  const payload = await response.json();
  if (!payload.note) {
    await route.fulfill({ response });
    return;
  }
  unavailableNote = {
    ...payload.note,
    integrity: {
      status: "check_unavailable",
      check_failed: true,
      error_code: "LLM_REQUEST_FAILED",
      error_message: "AI 请求失败：测试连接超时",
      retryable: true,
    },
  };
  await route.fulfill({
    status: response.status(),
    headers: response.headers(),
    contentType: "application/json",
    body: JSON.stringify({ note: unavailableNote }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.locator(".notes-textarea").first().fill("用于验证内容重新检查的逐字稿。");
  await page.getByRole("button", { name: /分析逐字稿/ }).click();
  await page.getByRole("button", { name: /按推荐快速生成/ }).click();

  await page.getByRole("heading", { name: "内容检查暂不可用", exact: true }).waitFor({ timeout: 15_000 });
  await page.getByText(/AI 服务请求失败/).waitFor();
  const recheckButton = page.getByRole("button", { name: "重新检查内容", exact: true });
  await recheckButton.waitFor();
  await recheckButton.click();

  await page.getByRole("heading", { name: "未发现明显遗漏", exact: true }).waitFor();
  if (await recheckButton.isVisible()) throw new Error("检查成功后仍显示重新检查按钮");
  if (recheckCount !== 1) throw new Error(`重新检查请求次数错误：${recheckCount}`);
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, reasonVisible: true, recheckCount }));
} finally {
  await browser.close();
}
