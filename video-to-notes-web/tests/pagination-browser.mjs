import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const output = "prototype-phase1-video-parser/screenshots/implementation-e2e-pagination";
const deviceId = "pagination-browser";
await fs.mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
await context.addInitScript(({ deviceId: id }) => {
  localStorage.setItem("vtn-device-id", id);
  localStorage.setItem("vtn-v3-migration-complete", "1");
}, { deviceId });
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});

try {
  const transcripts = [];
  const notes = [];
  for (let index = 0; index < 35; index += 1) {
    const suffix = String(index + 1).padStart(2, "0");
    const url = `https://example.com/pagination-${suffix}`;
    transcripts.push({
      id: `pagination-record-${suffix}`,
      url,
      title: `分页解析 ${suffix}`,
      creator: "分页测试",
      transcript: `分页逐字稿 ${suffix}`,
    });
    notes.push({
      id: `pagination-note-${suffix}`,
      url,
      title: `分页笔记 ${suffix}`,
      notes: `# 分页笔记 ${suffix}\n\n正文 ${suffix}`,
    });
  }
  const migration = await page.request.post(`${baseURL}/api/v3/migrations/browser-history`, {
    data: { device_id: "pagination-migration", transcripts, notes },
  });
  if (!migration.ok()) throw new Error(`分页数据迁移失败：${migration.status()}`);

  for (let index = 0; index < 35; index += 1) {
    const response = await page.request.post(`${baseURL}/api/v3/note-tasks`, {
      data: {
        device_id: deviceId,
        source: {
          type: "paste",
          name: `恢复任务 ${String(index + 1).padStart(2, "0")}`,
          transcript: `恢复任务逐字稿 ${index + 1}`,
        },
      },
    });
    if (!response.ok()) throw new Error(`恢复任务种子失败：${response.status()}`);
  }

  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /查看解析历史/ }).click();
  await page.waitForFunction(() => document.querySelectorAll("[data-real-record]").length === 30);
  if (await page.locator("[data-real-record]").count() !== 30) {
    throw new Error("解析历史首屏没有严格按 30 条分页");
  }
  await page.getByRole("button", { name: /加载更早的解析记录/ }).click();
  await page.waitForFunction(
    () => document.querySelectorAll("[data-real-record]").length === 35, null, { timeout: 5000 }
  );
  if (await page.locator("[data-real-record]").count() !== 35) {
    throw new Error("解析历史加载更多后没有追加剩余 5 条");
  }
  await page.screenshot({ path: `${output}/pagination-01-parser.png`, fullPage: true });
  console.log("pagination parser: 35");

  await page.getByRole("button", { name: "笔记生成" }).click();
  await page.getByRole("button", { name: "笔记历史" }).click();
  await page.waitForFunction(() => document.querySelectorAll("[data-real-note]").length === 30);
  if (await page.locator("[data-real-note]").count() !== 30) {
    throw new Error("笔记历史首屏没有严格按 30 条分页");
  }
  await page.getByRole("button", { name: /加载更早的笔记/ }).click();
  await page.waitForFunction(
    () => document.querySelectorAll("[data-real-note]").length === 35, null, { timeout: 5000 }
  );
  if (await page.locator("[data-real-note]").count() !== 35) {
    throw new Error("笔记历史加载更多后没有追加剩余 5 条");
  }
  await page.screenshot({ path: `${output}/pagination-02-notes.png`, fullPage: true });
  console.log("pagination notes: 35");

  await page.getByRole("button", { name: "笔记生成" }).click();
  await page.getByRole("button", { name: "恢复任务" }).click();
  await page.waitForFunction(
    () => document.querySelectorAll(".recovery-list [data-real-resume-task]").length === 30,
    null,
    { timeout: 5000 }
  );
  if (await page.locator(".recovery-list [data-real-resume-task]").count() !== 30) {
    throw new Error("恢复任务首屏没有严格按 30 条分页");
  }
  await page.getByRole("button", { name: /加载更早的任务/ }).click();
  await page.waitForFunction(
    () => document.querySelectorAll(".recovery-list [data-real-resume-task]").length === 35,
    null,
    { timeout: 5000 }
  );
  if (await page.locator(".recovery-list [data-real-resume-task]").count() !== 35) {
    throw new Error("恢复任务加载更多后没有追加剩余 5 条");
  }
  await page.screenshot({ path: `${output}/pagination-03-recovery.png`, fullPage: true });

  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, parser: 35, notes: 35, recovery: 35 }));
} catch (error) {
  console.error(error.stack || error.message);
  process.exitCode = 1;
} finally {
  await context.close();
  await browser.close();
}
