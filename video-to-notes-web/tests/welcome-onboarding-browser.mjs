import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });
const viewport = process.env.VTN_E2E_MOBILE === "1"
  ? { width: 390, height: 844 }
  : { width: 1440, height: 1050 };
const context = await browser.newContext({ viewport });
const page = await context.newPage();
page.setDefaultTimeout(5_000);
page.setDefaultNavigationTimeout(15_000);
const paidTaskRequests = [];

page.on("request", (request) => {
  const path = new URL(request.url()).pathname;
  if (request.method() === "POST" && ["/api/v3/parser/tasks", "/api/v3/note-tasks"].includes(path)) {
    paidTaskRequests.push(path);
  }
});

await page.route("**/api/v3/access/status", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ authenticated: false, access: null }),
  });
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  const dialog = page.getByRole("dialog", { name: "欢迎使用视频内容知识化工具" });
  await dialog.waitFor({ state: "visible" });
  await dialog.getByText("把一条视频，变成一份真正能复习的笔记。", { exact: true }).waitFor();
  for (const expected of ["粘贴视频链接", "AI 预读并推荐", "阅读、编辑与导出", "当前公网真实调用暂未开放"]) {
    await dialog.getByText(expected, { exact: true }).waitFor();
  }
  await page.waitForFunction(() => !document.querySelector("#welcome-dialog .is-motion-animating"));
  const primaryButton = dialog.getByRole("button", { name: "体验完整公开案例" });
  if (process.env.VTN_E2E_MOBILE === "1") {
    const buttonBox = await primaryButton.boundingBox();
    if (!buttonBox || buttonBox.y < 0 || buttonBox.y + buttonBox.height > viewport.height) {
      throw new Error("手机端首屏未显示完整公开案例主按钮");
    }
  }
  if (process.env.VTN_E2E_SCREENSHOT) {
    await page.screenshot({ path: process.env.VTN_E2E_SCREENSHOT, fullPage: false });
  }

  await primaryButton.click();
  await dialog.waitFor({ state: "hidden" });
  await page.getByText("刚毕业一年，我如何用 AI 重建自己的学习系统", { exact: true }).waitFor();

  await page.reload({ waitUntil: "networkidle" });
  if (await dialog.isVisible()) throw new Error("首次欢迎引导在刷新后重复自动弹出");

  await page.getByRole("button", { name: "使用说明" }).click();
  await dialog.waitFor({ state: "visible" });
  await dialog.getByRole("button", { name: "先看看页面" }).click();
  await dialog.waitFor({ state: "hidden" });

  if (paidTaskRequests.length) {
    throw new Error(`欢迎引导触发了真实任务请求：${paidTaskRequests.join(", ")}`);
  }

  console.log(JSON.stringify({
    ok: true,
    firstVisitOnly: true,
    publicDemoEntry: true,
    guideCanReopen: true,
    paidTaskRequests: 0,
  }));
} finally {
  await browser.close();
}
