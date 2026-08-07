import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const transcript = "这是重新生成整份笔记的浏览器测试逐字稿，包含概念解释、真实案例和可以执行的行动步骤。";
const firstRequest = "先生成一份普通的复习笔记。";
const secondRequest = "重新生成得更详细，增加概念解释、案例拆解、常见误区和逐步行动建议。";
const regeneratedTitle = `重新生成的详细笔记-${Date.now()}`;
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
const page = await context.newPage();
page.setDefaultTimeout(5000);
const errors = [];

page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});

async function notes() {
  const response = await page.request.get(`${baseURL}/api/v3/notes?limit=100`);
  return (await response.json()).items;
}

async function tasks() {
  const response = await page.request.get(`${baseURL}/api/v3/note-tasks?limit=100`);
  return (await response.json()).items;
}

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.locator("#notes-transcript-input").fill(transcript);
  await page.locator("#notes-request-input").fill(firstRequest);
  await page.getByRole("button", { name: /分析逐字稿/ }).click();
  await page.getByRole("button", { name: /按推荐快速生成/ }).waitFor();
  await page.getByRole("button", { name: /按推荐快速生成/ }).click();
  await page.getByRole("button", { name: /打开笔记/ }).waitFor();
  await page.getByRole("button", { name: /打开笔记/ }).click();
  await page.getByRole("button", { name: "编辑笔记" }).waitFor();

  const originalNote = (await notes()).find((note) => note.basis_transcript === transcript);
  if (!originalNote) throw new Error("没有找到首次生成的原笔记");
  const originalSnapshot = await page.request.get(`${baseURL}/api/v3/notes/${originalNote.id}`);
  const originalBefore = (await originalSnapshot.json()).note;

  await page.getByRole("button", { name: "重新生成整份笔记" }).click();
  await page.getByRole("heading", { name: "重新生成整份笔记", exact: true }).waitFor();
  if (await page.locator("[data-regenerate-transcript]").inputValue() !== transcript) {
    throw new Error("重新生成页没有自动带入生成依据逐字稿");
  }
  await page.getByText("原笔记会完整保留", { exact: true }).waitFor();
  await page.getByRole("button", { name: "返回当前笔记" }).click();
  await page.getByRole("button", { name: "编辑笔记" }).waitFor();

  await page.getByRole("button", { name: "重新生成整份笔记" }).click();
  await page.locator("#regenerate-note-request").fill(secondRequest);
  await page.getByRole("button", { name: /重新分析并生成新笔记/ }).click();
  await page.getByRole("button", { name: /按推荐快速生成/ }).waitFor();

  const restartedTask = (await tasks()).find(
    (task) => task.source_snapshot?.regenerated_from_note_id === originalNote.id,
  );
  if (!restartedTask) throw new Error("没有创建独立的重新生成任务");
  if (restartedTask.request_text !== secondRequest) throw new Error("新的提问要求没有保存");
  if (restartedTask.basis_transcript !== transcript) throw new Error("新任务的生成依据发生漂移");

  await page.locator("#suggested-note-title").fill(regeneratedTitle);
  await page.getByRole("button", { name: /按推荐快速生成/ }).click();
  await page.getByRole("button", { name: /打开笔记/ }).waitFor();
  await page.getByRole("button", { name: /打开笔记/ }).click();
  await page.getByRole("heading", { name: regeneratedTitle, exact: true }).waitFor();

  const allNotes = await notes();
  const regeneratedNote = allNotes.find((note) => note.title === regeneratedTitle);
  if (!regeneratedNote || regeneratedNote.id === originalNote.id) {
    throw new Error("重新生成没有产生独立的新笔记");
  }
  const originalAfterResponse = await page.request.get(`${baseURL}/api/v3/notes/${originalNote.id}`);
  const originalAfter = (await originalAfterResponse.json()).note;
  if (originalAfter.current_markdown !== originalBefore.current_markdown || originalAfter.version !== originalBefore.version) {
    throw new Error("重新生成覆盖了原笔记");
  }

  await page.getByRole("button", { name: "笔记历史" }).click();
  await page.locator(`[data-real-note="${originalNote.id}"]`).waitFor();
  await page.locator(`[data-real-note="${regeneratedNote.id}"]`).waitFor();
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, preservedOriginal: true, newNote: true, newRequest: true }));
} finally {
  await context.close();
  await browser.close();
}
