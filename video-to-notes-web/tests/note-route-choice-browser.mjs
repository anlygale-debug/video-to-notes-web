import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1100 },
  permissions: ["clipboard-read", "clipboard-write"],
});
const page = await context.newPage();
let notePosts = 0;
let noteRequest = null;
const transcript = "这是用于验证线路选择的完整逐字稿。用户进入笔记页时，不应该立刻调用模型。";

await page.addInitScript(() => {
  localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
});
await page.route("**/api/v3/access/status", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    enabled: true,
    authenticated: true,
    access: {
      label: "线路测试",
      remaining_transcription_seconds: 1200,
      remaining_note_generations: 0,
      remaining_high_speed_generations: 0,
    },
  }),
}));
await page.route("**/api/v3/capabilities", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    integrity_recheck: true,
    transcription_providers: { local: true, cloudflare: true },
    note_generation: {
      enabled: true,
      routes: {
        free: { id: "free", available: true, enabled: true, description: "免费线路当前可用" },
        paid: { id: "paid", available: true, enabled: true, description: "高速线路当前可用" },
      },
    },
  }),
}));
await page.route("**/api/v3/parser/records/route-record", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    record: {
      id: "route-record",
      source_url: "https://www.bilibili.com/video/BVROUTE",
      platform: "bilibili",
      title: "线路选择测试视频",
      creator: "测试作者",
      description: "验证进入笔记页不会立即调用 LLM。",
      duration_seconds: 180,
      thumbnail_url: "",
      transcript_text: transcript,
    },
  }),
}));
await page.route("**/api/v3/note-tasks", async (route) => {
  if (route.request().method() !== "POST") return route.continue();
  notePosts += 1;
  noteRequest = route.request().postDataJSON();
  await route.fulfill({
    status: 202,
    contentType: "application/json",
    body: JSON.stringify({
      task: {
        id: "note-route-task",
        state: "analysis_failed",
        generation_route: noteRequest.generation_route,
        basis_transcript: transcript,
        error_code: "TEST_STOP",
        error_message: "浏览器测试在任务创建后停止。",
      },
    }),
  });
});
await page.route("**/api/v3/note-tasks/note-route-task", (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({
    task: {
      id: "note-route-task",
      state: "analysis_failed",
      generation_route: "free",
      basis_transcript: transcript,
      error_code: "TEST_STOP",
      error_message: "浏览器测试在任务创建后停止。",
    },
  }),
}));

try {
  await page.goto(`${baseURL}/next?record=route-record`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "线路选择测试视频", exact: true }).waitFor();
  await page.getByRole("button", { name: /选择笔记生成方式/ }).click();

  await page.getByRole("heading", { name: "第二步：选择一种方式生成笔记", exact: true }).waitFor();
  if (notePosts !== 0) throw new Error(`进入笔记页时错误创建了 ${notePosts} 个 LLM 任务`);
  await page.getByRole("heading", { name: "To Notes Skill", exact: true }).waitFor();
  await page.getByRole("heading", { name: "用你常用的 AI 生成", exact: true }).waitFor();
  await page.getByRole("heading", { name: "直接在本站生成", exact: true }).waitFor();

  await page.getByRole("button", { name: "复制逐字稿", exact: true }).click();
  if (await page.evaluate(() => navigator.clipboard.readText()) !== transcript) {
    throw new Error("就绪页复制的逐字稿不是当前视频全文");
  }

  const paid = page.locator('[data-select-note-route="paid"]');
  if (!(await paid.isDisabled())) throw new Error("高速次数为 0 时，高速线路仍然可以点击");
  await page.getByText("高速体验次数已用完。你仍可使用免费线路，或联系作者补充体验次数。", { exact: true }).waitFor();

  await page.locator('[data-select-note-route="free"]').click();
  if (notePosts !== 0) throw new Error("仅选择免费线路就错误创建了 LLM 任务");
  await page.getByText("使用免费线路，不消耗高速次数", { exact: true }).waitFor();
  await page.getByRole("button", { name: /确认使用免费线路/ }).click();

  if (notePosts !== 1) throw new Error(`确认后任务创建次数异常：${notePosts}`);
  if (noteRequest?.generation_route !== "free") {
    throw new Error(`创建任务没有携带免费线路：${JSON.stringify(noteRequest)}`);
  }
  if (noteRequest?.source?.parser_record_id !== "route-record") {
    throw new Error(`创建任务没有沿用当前解析记录：${JSON.stringify(noteRequest)}`);
  }

  console.log(JSON.stringify({
    ok: true,
    noImmediateLLM: true,
    transcriptCopy: true,
    highSpeedZeroDisabled: true,
    confirmedRoute: noteRequest.generation_route,
  }));
} finally {
  await context.close();
  await browser.close();
}
