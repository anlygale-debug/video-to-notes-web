import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4176";
const installCommand = "npx skills add anlygale-debug/to-notes --skill to-notes -g -y";
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1100 },
  permissions: ["clipboard-read", "clipboard-write"],
});
const page = await context.newPage();
const errors = [];

await page.addInitScript(() => {
  localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
});
page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();

  await page.getByRole("heading", { name: "第一步：导入逐字稿", exact: true }).waitFor();
  await page.locator("#notes-transcript-input").fill("这是一段用于验证三种笔记生成方式的逐字稿。");
  await page.getByRole("button", { name: /继续选择生成方式/ }).click();

  await page.getByRole("heading", { name: "第二步：选择一种方式生成笔记", exact: true }).waitFor();
  await page.getByRole("heading", { name: "直接在本站生成", exact: true }).waitFor();
  await page.getByRole("heading", { name: "用你常用的 AI 生成", exact: true }).waitFor();
  await page.getByRole("heading", { name: "To Notes Skill", exact: true }).waitFor();
  await page.getByText("给 Agent 工具使用", { exact: true }).waitFor();
  await page.getByText("长短内容都适合", { exact: true }).waitFor();
  await page.getByText("处理长内容时优势更明显", { exact: true }).waitFor();
  await page.getByText(/Codex、Claude Code、WorkBuddy/).waitFor();

  const primaryButton = page.locator('[data-select-note-route="free"]');
  if (!(await primaryButton.isVisible())) throw new Error("本站生成主入口不可见");

  const skillCopy = page.getByRole("button", { name: "复制安装命令", exact: true });
  await skillCopy.click();
  if (await page.evaluate(() => navigator.clipboard.readText()) !== installCommand) {
    throw new Error("Skill 安装命令复制内容不正确");
  }
  await page.getByText("Skill 安装命令已复制", { exact: true }).waitFor();

  const promptCopy = page.getByRole("button", { name: "复制提示词", exact: true });
  await promptCopy.click();
  await page.getByText("To Notes 完整提示词已复制", { exact: true }).waitFor();
  const prompt = await page.evaluate(() => navigator.clipboard.readText());
  if (!prompt.startsWith("你是一名擅长理解长内容")) {
    throw new Error(`复制内容仍然包含提示词之外的使用说明：${prompt.slice(0, 80)}`);
  }
  if (!prompt.includes("动态询问四个偏好") || !prompt.includes("没有得到确认，不要开始写完整笔记")) {
    throw new Error(`复制的通用提示词缺少 To Notes 核心流程：${prompt.slice(0, 120)}`);
  }
  const promptResponse = await page.request.get(`${baseURL}/static/resources/to-notes-universal-zh.md`);
  if (!promptResponse.ok()) throw new Error("通用提示词下载资源不可访问");
  const zipResponse = await page.request.get(`${baseURL}/static/resources/to-notes-skill.zip`);
  if (!zipResponse.ok()) throw new Error("Skill ZIP 下载资源不可访问");

  const githubHref = await page.getByRole("link", { name: "查看使用说明", exact: true }).getAttribute("href");
  if (githubHref !== "https://github.com/anlygale-debug/to-notes") {
    throw new Error(`GitHub 入口不正确：${githubHref}`);
  }

  await page.setViewportSize({ width: 720, height: 1000 });
  await page.locator(".ready-methods__grid").scrollIntoViewIfNeeded();
  const columns = await page.locator(".ready-methods__grid").evaluate((element) => getComputedStyle(element).gridTemplateColumns);
  if (columns.split(" ").length !== 1) throw new Error(`移动端没有切换为单列：${columns}`);

  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({
    ok: true,
    website: true,
    skillCommand: true,
    universalPromptCharacters: prompt.length,
    resources: true,
    mobile: true,
  }));
} finally {
  await context.close();
  await browser.close();
}
