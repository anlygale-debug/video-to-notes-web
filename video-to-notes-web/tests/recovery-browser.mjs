import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const deviceId = process.env.VTN_DEVICE_ID;
const expectedTitle = process.env.VTN_EXPECTED_TITLE;
if (!deviceId || !expectedTitle) throw new Error("VTN_DEVICE_ID 与 VTN_EXPECTED_TITLE 必填");

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
await context.addInitScript((device) => {
  localStorage.setItem("vtn-device-id", device);
  localStorage.setItem("vtn-v3-migration-complete", "1");
}, deviceId);
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(message.text());
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成" }).click();
  await page.getByRole("button", { name: "恢复任务" }).click();
  const row = page.getByText(expectedTitle, { exact: true }).locator("xpath=ancestor::article");
  await row.getByRole("button").click();
  await page.getByRole("button", { name: "编辑笔记" }).waitFor();
  const title = (await page.locator("[data-note-title]").first().innerText()).trim();
  if (title !== expectedTitle) throw new Error(`重启恢复标题不一致：${title}`);
  await page.screenshot({
    path: "prototype-phase1-video-parser/screenshots/implementation-e2e-boundaries/boundary-06-service-restart.png",
    fullPage: true,
  });
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, serviceRestartRecovery: true, title }));
} finally {
  await context.close();
  await browser.close();
}
