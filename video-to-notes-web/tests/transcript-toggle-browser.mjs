import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const longTranscript = "这是用于验证逐字稿预览、原位展开与收起的长文本。".repeat(220);
const shortTranscript = "这是一个短逐字稿，应该直接完整显示。";
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1050 },
  permissions: ["clipboard-read", "clipboard-write"],
});
const page = await context.newPage();
const errors = [];
let dialogCount = 0;

await page.addInitScript(() => {
  localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
});

page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});
page.on("dialog", async (dialog) => {
  dialogCount += 1;
  await dialog.dismiss();
});

await page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});
await page.route("**/api/v3/parser/records/**", async (route) => {
  const isShort = route.request().url().endsWith("record-short");
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      record: {
        id: isShort ? "record-short" : "record-long",
        source_url: "https://www.bilibili.com/video/BV1TRANSCRIPT",
        platform: "bilibili",
        title: isShort ? "短逐字稿测试视频" : "长逐字稿测试视频",
        creator: "测试作者",
        description: "逐字稿交互测试",
        duration_seconds: 120,
        thumbnail_url: null,
        transcript_text: isShort ? shortTranscript : longTranscript,
      },
    }),
  });
});

try {
  await page.goto(`${baseURL}/next?record=record-long`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "长逐字稿测试视频", exact: true }).waitFor();

  const preview = page.locator(".transcript-preview");
  const toggle = page.getByRole("button", { name: "展开完整逐字稿 ↓", exact: true });
  if ((await page.locator(".transcript-panel h3").innerText()).trim() !== `逐字稿 · ${longTranscript.length.toLocaleString()} 字`) {
    throw new Error("逐字稿标题没有显示真实字符数");
  }
  if ((await toggle.getAttribute("aria-expanded")) !== "false") {
    throw new Error("长逐字稿默认没有处于收起状态");
  }
  if (!(await preview.evaluate((element) => element.classList.contains("is-collapsed")))) {
    throw new Error("长逐字稿默认没有视觉预览状态");
  }
  await page.getByRole("button", { name: /下载 TXT/ }).waitFor();
  await page.getByRole("button", { name: /下载 MD/ }).waitFor();
  const copyButton = page.getByRole("button", { name: "复制全文", exact: true });
  await copyButton.click();
  if (await page.evaluate(() => navigator.clipboard.readText()) !== longTranscript) {
    throw new Error("复制全文没有把完整逐字稿写入剪贴板");
  }
  await page.getByRole("button", { name: "✓ 已复制", exact: true }).waitFor();
  await page.getByText("逐字稿全文已复制到剪贴板", { exact: true }).waitFor();
  await page.getByRole("button", { name: "复制全文", exact: true }).waitFor();
  await page.evaluate(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: () => Promise.reject(new Error("permission denied")) },
    });
  });
  await copyButton.click();
  await page.getByText("复制失败，请检查浏览器剪贴板权限后重试。", { exact: true }).waitFor();

  await toggle.click();
  await page.getByRole("button", { name: "收起逐字稿 ↑", exact: true }).waitFor();
  if ((await page.getByRole("button", { name: "收起逐字稿 ↑", exact: true }).getAttribute("aria-expanded")) !== "true") {
    throw new Error("展开后 aria-expanded 没有更新");
  }
  if (!(await preview.evaluate((element, expected) => !element.classList.contains("is-collapsed") && element.textContent === expected, longTranscript))) {
    throw new Error("逐字稿没有在结果卡内完整展开");
  }

  await page.getByRole("button", { name: "收起逐字稿 ↑", exact: true }).click();
  await toggle.waitFor();
  if (!(await preview.evaluate((element) => element.classList.contains("is-collapsed")))) {
    throw new Error("逐字稿再次点击后没有恢复预览");
  }

  await page.goto(`${baseURL}/next?record=record-short`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "短逐字稿测试视频", exact: true }).waitFor();
  if ((await page.locator(".transcript-preview").innerText()).trim() !== shortTranscript) {
    throw new Error("短逐字稿没有完整显示");
  }
  if (await page.locator("[data-toggle-transcript]").count()) {
    throw new Error("短逐字稿仍显示了展开按钮");
  }
  if (dialogCount) throw new Error(`逐字稿交互触发了 ${dialogCount} 次原型弹窗`);
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, longCharacters: longTranscript.length, shortTranscript: true, dialogs: dialogCount }));
} finally {
  await context.close();
  await browser.close();
}
