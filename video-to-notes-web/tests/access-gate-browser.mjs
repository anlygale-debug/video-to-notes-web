import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
page.setDefaultTimeout(5_000);
page.setDefaultNavigationTimeout(15_000);

await page.route("**/api/v3/access/status", async (route) => {
  await route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ authenticated: false, access: null }),
  });
});
await page.route("**/api/v3/access/login", async (route) => {
  const body = route.request().postDataJSON();
  if (body.code !== "VTN-DEMO") {
    await route.fulfill({
      status: 401, contentType: "application/json",
      body: JSON.stringify({ error: { code: "ACCESS_CODE_INVALID", message: "内测码无效或已到期" } }),
    });
    return;
  }
  await route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({
      access: {
        label: "招聘体验",
        remaining_transcription_seconds: 1800,
        remaining_note_generations: 5,
        max_video_seconds: 1200,
      },
    }),
  });
});
await page.route("**/api/v3/parser/tasks", async (route) => {
  await route.fulfill({
    status: 401, contentType: "application/json",
    body: JSON.stringify({ error: { code: "ACCESS_REQUIRED", message: "请输入有效内测码后继续" } }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  const welcomeDialog = page.getByRole("dialog", { name: "欢迎使用视频内容知识化工具" });
  await welcomeDialog.waitFor({ state: "visible" });
  await welcomeDialog.getByRole("button", { name: "先看看页面" }).click();
  await welcomeDialog.waitFor({ state: "hidden" });
  await page.getByRole("button", { name: "查看公开示例", exact: true }).click();
  await page.getByText("刚毕业一年，我如何用 AI 重建自己的学习系统", { exact: true }).waitFor();
  await page.getByRole("button", { name: "退出示例" }).click();

  await page.locator("#video-link").fill("https://example.test/video");
  await page.locator("#parser-form button[type=submit]").click();
  const dialog = page.locator("#access-dialog");
  await dialog.waitFor({ state: "visible" });
  await dialog.locator("input[name=access-code]").fill("VTN-DEMO");
  await dialog.getByRole("button", { name: /进入真实体验/ }).click();
  await dialog.waitFor({ state: "hidden" });
  await page.getByText("招聘体验", { exact: true }).waitFor();
  await page.getByText(/转录 30 分钟/).waitFor();
  await page.getByText(/笔记 5 次/).waitFor();

  console.log(JSON.stringify({ ok: true, publicDemo: true, gatedRealActions: true, quotaVisible: true }));
} finally {
  await browser.close();
}
