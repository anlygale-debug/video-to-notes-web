import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });
const viewport = process.env.VTN_E2E_MOBILE === "1"
  ? { width: 390, height: 844 }
  : { width: 1440, height: 1050 };
const page = await browser.newPage({
  viewport,
  permissions: ["clipboard-read", "clipboard-write"],
});
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
  await page.goto(`${baseURL}/next`, { waitUntil: "domcontentloaded" });
  const welcomeDialog = page.getByRole("dialog", { name: "欢迎使用视频内容知识化工具" });
  await welcomeDialog.waitFor({ state: "visible" });
  await welcomeDialog.getByRole("button", { name: "体验完整公开案例" }).click();
  await welcomeDialog.waitFor({ state: "hidden" });
  await page.getByText("公开示例 · 全流程体验", { exact: true }).waitFor();
  await page.getByText("刚毕业一年，我如何用 AI 重建自己的学习系统", { exact: true }).waitFor();
  const demoTranscript = await page.locator(".transcript-preview").textContent();
  if (!demoTranscript?.includes("以前我学习新东西")) {
    throw new Error("公开示例缺少预期逐字稿内容");
  }
  await page.getByRole("button", { name: "复制全文", exact: true }).click();
  if (await page.evaluate(() => navigator.clipboard.readText()) !== demoTranscript) {
    throw new Error("公开示例没有复制完整逐字稿");
  }
  await page.getByRole("button", { name: "✓ 已复制", exact: true }).waitFor();

  await page.getByRole("button", { name: /用此逐字稿生成笔记/ }).click();
  await page.getByRole("heading", { name: "推荐设置已准备好。" }).waitFor();
  await page.getByRole("button", { name: /按推荐快速生成/ }).click();
  await page.getByRole("heading", { name: "完整笔记已经生成。" }).waitFor();
  const completionReceipt = await page.locator(".completion-summary").innerText();
  for (const expected of ["3,486 字 · 5 章", "核心摘要、行动清单、学习闭环", "Bilibili 视频逐字稿 · 3,842 字", "2026.07.27 19:26"]) {
    if (!completionReceipt.includes(expected)) {
      throw new Error(`公开示例笔记回执缺少真实内容：${expected}`);
    }
  }
  if (/正在统计|正在读取/.test(completionReceipt)) {
    throw new Error("公开示例笔记回执仍包含占位文案");
  }
  if (process.env.VTN_E2E_COMPLETION_SCREENSHOT) {
    await page.screenshot({ path: process.env.VTN_E2E_COMPLETION_SCREENSHOT, fullPage: false });
  }
  await page.getByRole("button", { name: /打开笔记/ }).click();
  await page.getByRole("heading", { name: "用 AI Agent 重建个人学习系统：从收藏到行动" }).waitFor();
  const noteContent = page.locator(".note-content");
  await noteContent.waitFor();
  const noteContentBox = await noteContent.boundingBox();
  const paragraphCount = await noteContent.locator("p").count();
  const hiddenChapterCount = await noteContent.locator(".note-chapter").evaluateAll((chapters) => chapters.filter((chapter) => {
    const style = getComputedStyle(chapter);
    return style.visibility === "hidden" || Number(style.opacity) < 0.9;
  }).length);
  if (!noteContentBox || noteContentBox.width > 760) {
    throw new Error(`公开示例正文过宽：${noteContentBox?.width ?? "unknown"}px`);
  }
  if (paragraphCount < 10) {
    throw new Error(`公开示例段落过少：${paragraphCount}`);
  }
  if (hiddenChapterCount) {
    throw new Error(`公开示例存在尚未显示的章节：${hiddenChapterCount}`);
  }
  if (process.env.VTN_E2E_SCREENSHOT) {
    await page.screenshot({ path: process.env.VTN_E2E_SCREENSHOT, fullPage: true });
  }

  if (paidTaskRequests.length) {
    throw new Error(`公开示例发起了真实任务请求：${paidTaskRequests.join(", ")}`);
  }

  console.log(JSON.stringify({
    ok: true,
    parserExample: true,
    recommendationFlow: true,
    completedNote: true,
    readableNoteLayout: true,
    paidTaskRequests: 0,
  }));
} finally {
  await browser.close();
}
