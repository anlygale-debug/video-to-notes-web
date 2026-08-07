import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const output = "prototype-phase1-video-parser/screenshots/new-note-navigation";
await fs.mkdir(output, { recursive: true });

const browser = await chromium.launch({ headless: true });

async function openNotesState(page, state) {
  await page.evaluate((nextState) => {
    switchView("notes");
    setNotesState(nextState);
  }, state);
  await page.locator("#notes-state-host > :first-child").waitFor({ state: "visible" });
  await page.waitForFunction(() => {
    const current = document.querySelector("#notes-state-host > :first-child");
    return !current?.dataset.motionState || current.dataset.motionState === "settled";
  });
}

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  let livePollRequests = 0;
  let deleteRequests = 0;
  const liveTask = {
    id: "task-live-001",
    state: "analyzing",
    proposed_title: "轮询离开测试",
    source_name: "浏览器测试逐字稿",
    source_snapshot: null,
    basis_transcript: "这是一段用于验证离开生成行为的测试逐字稿。",
    request_text: "验证返回首页",
    recommendation: null,
    progress: { stage: "understand", label: "正在分析", percent: 20 },
    outline: [],
    chapters: [],
  };
  await page.route("**/api/v3/note-tasks", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ task: liveTask }) });
  });
  await page.route("**/api/v3/note-tasks/task-live-001", async (route) => {
    if (route.request().method() === "DELETE") {
      deleteRequests += 1;
      return route.fulfill({ status: 204, body: "" });
    }
    livePollRequests += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ task: liveTask }) });
  });
  await page.addInitScript(() => {
    localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
  });
  await page.goto(`${baseURL}/next?new-note-navigation=1`, { waitUntil: "networkidle" });

  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.locator("#notes-transcript-input").fill(liveTask.basis_transcript);
  await page.getByRole("button", { name: /分析逐字稿/ }).click();
  await page.locator(".analysis-panel").waitFor({ state: "visible" });
  const workspaceBar = page.locator("[data-notes-workspace-bar]");
  await workspaceBar.waitFor({ state: "visible" });
  if (!(await workspaceBar.innerText()).includes("返回首页将删除本次未完成进度")) {
    throw new Error("生成中没有显示放弃任务的明确后果");
  }

  await workspaceBar.getByRole("button", { name: /放弃生成/ }).click();
  const dialog = page.getByRole("dialog", { name: "放弃本次笔记生成？" });
  await dialog.waitFor({ state: "visible" });
  await page.screenshot({ path: `${output}/desktop-abandon-confirmation.png`, fullPage: true });
  if (!(await page.locator(".analysis-panel").isVisible())) {
    throw new Error("确认离开前不应改变当前生成页面");
  }
  await dialog.getByRole("button", { name: "继续当前任务" }).click();
  await dialog.waitFor({ state: "hidden" });
  if (!(await page.locator(".analysis-panel").isVisible())) {
    throw new Error("继续等待后没有留在生成页面");
  }

  await workspaceBar.getByRole("button", { name: /放弃生成/ }).click();
  await dialog.getByRole("button", { name: "放弃并返回首页" }).click();
  await page.locator(".notes-input-layout").waitFor({ state: "visible" });
  const pollsAtExit = livePollRequests;
  await page.waitForTimeout(1_100);
  if (!(await page.locator(".notes-input-layout").isVisible()) || await workspaceBar.isVisible()) {
    throw new Error("离开生成后没有稳定停留在笔记首页");
  }
  if (livePollRequests > pollsAtExit + 1) {
    throw new Error(`离开后仍在持续轮询旧任务：退出时 ${pollsAtExit} 次，之后 ${livePollRequests} 次`);
  }
  if (deleteRequests !== 1) {
    throw new Error(`主动放弃没有准确删除一次后台任务：${deleteRequests}`);
  }

  await openNotesState(page, "generation-complete");
  if (await workspaceBar.isVisible()) throw new Error("生成完成页不应继续显示顶部任务状态栏");
  await page.getByRole("button", { name: "再生成一份" }).click();
  await page.locator(".notes-input-layout").waitFor({ state: "visible" });

  await openNotesState(page, "reading");
  if (await workspaceBar.isVisible()) throw new Error("阅读页不应显示重复的新建笔记状态栏");
  if (await page.getByRole("button", { name: /新建笔记/ }).count() !== 1) {
    throw new Error("阅读页应该只保留一个新建笔记入口");
  }
  await page.locator(".reader-command-bar").getByRole("button", { name: /新建笔记/ }).click();
  await page.locator(".notes-input-layout").waitFor({ state: "visible" });

  await openNotesState(page, "reading");
  await page.screenshot({ path: `${output}/desktop-reading-entry.png`, fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: "networkidle" });
  await openNotesState(page, "direct-generating");
  const mobileBar = page.locator("[data-notes-workspace-bar]");
  const box = await mobileBar.boundingBox();
  if (!box || box.x < 0 || box.x + box.width > 390) {
    throw new Error(`手机端工作区入口溢出视口：${JSON.stringify(box)}`);
  }
  await page.screenshot({ path: `${output}/mobile-generating-entry.png`, fullPage: true });

  console.log(JSON.stringify({ ok: true, generationDialog: true, completionEntry: true, readingEntry: true, mobile: true }));
} finally {
  await browser.close();
}
