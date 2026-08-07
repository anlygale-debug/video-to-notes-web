import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const transcript = `动态推荐浏览器测试-${Date.now()}：内容先描述一个问题，再解释原因，最后给出练习方法。`;
const additionalRequest = "多保留失败案例，并明确列出下一步行动。";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
await page.addInitScript(() => {
  localStorage.setItem("vtn-welcome-version", "beta-2026-07-31-v1");
});

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.locator(".notes-textarea").first().fill(transcript);
  await page.locator(".notes-request").fill("用于深入复习");
  await page.getByRole("button", { name: /分析逐字稿/ }).click();
  await page.getByRole("button", { name: "自定义生成" }).waitFor();

  const recommendationCards = await page.locator(".recommendation-grid .recommend-card strong").allInnerTexts();
  if (!recommendationCards.includes("问题 → 原因 → 方法")) {
    throw new Error(`推荐页没有展示真实结构推荐：${recommendationCards.join(" / ")}`);
  }
  if (!recommendationCards.some((value) => value.includes("3 项"))) {
    throw new Error(`推荐页没有展示真实模块数量：${recommendationCards.join(" / ")}`);
  }

  await page.getByRole("button", { name: "自定义生成" }).click();
  const structureOptions = page.locator('[data-setting-group="structure"] .choice-card');
  if (await structureOptions.count() !== 3) {
    throw new Error(`结构选项应为 3 个，实际为 ${await structureOptions.count()}`);
  }
  const modules = page.locator(".module-choice[data-module]");
  const moduleCount = await modules.count();
  if (moduleCount !== 4) {
    throw new Error(`附加模块应精简为 4 个，实际为 ${moduleCount}`);
  }
  if (await page.locator(".module-choice[data-module] input:checked").count() > 3) {
    throw new Error("AI 自动推荐的附加模块超过 3 个");
  }
  const bodyOnly = page.locator('[data-module-none]');
  if (await bodyOnly.count() !== 1) {
    throw new Error("附加模块设置中没有“只要正文”选项");
  }
  await bodyOnly.locator("input").check();
  if (await page.locator(".module-choice[data-module] input:checked").count() !== 0) {
    throw new Error("选择“只要正文”后仍保留了附加模块");
  }

  await page.locator('[data-setting-group="structure"] [data-choice="thematic"]').click();
  await page.locator('[data-setting-group="detail"] [data-choice="key"]').click();
  await page.locator('[data-setting-group="method"] [data-choice="outline"]').click();
  await page.locator("#custom-other-request").fill(additionalRequest);
  await page.getByRole("button", { name: /按当前设置开始生成/ }).click();
  await page.getByRole("button", { name: /确认大纲并开始生成/ }).waitFor();
  await page.getByRole("button", { name: "返回修改设置" }).click();
  if (!await page.locator('[data-setting-group="structure"] [data-choice="thematic"]').evaluate((node) => node.classList.contains("is-selected"))) {
    throw new Error("从大纲返回后，自定义结构没有恢复");
  }
  if (!await page.locator('[data-setting-group="detail"] [data-choice="key"]').evaluate((node) => node.classList.contains("is-selected"))) {
    throw new Error("从大纲返回后，自定义详细程度没有恢复");
  }
  if (await page.locator("#custom-other-request").inputValue() !== additionalRequest) {
    throw new Error("从大纲返回后，其他要求没有恢复");
  }
  await page.locator('[data-setting-group="method"] [data-choice="direct"]').click();
  await page.getByRole("button", { name: /按当前设置开始生成/ }).click();
  await page.getByRole("button", { name: /打开笔记/ }).waitFor();

  const tasksResponse = await page.request.get(`${baseURL}/api/v3/note-tasks?limit=100`);
  const tasks = (await tasksResponse.json()).items;
  const task = tasks.find((item) => item.basis_transcript === transcript);
  if (!task) throw new Error("找不到浏览器创建的笔记任务");
  if (task.final_settings?.structure?.id !== "thematic") {
    throw new Error(`自定义结构没有保存：${JSON.stringify(task.final_settings)}`);
  }
  if (task.final_settings?.detail?.id !== "key") {
    throw new Error(`自定义详细程度没有保存：${JSON.stringify(task.final_settings)}`);
  }
  if (task.final_settings?.method !== "direct") {
    throw new Error(`从大纲返回后的生成方式没有保存：${JSON.stringify(task.final_settings)}`);
  }
  if (task.final_settings?.additional_request !== additionalRequest) {
    throw new Error(`其他要求没有保存：${JSON.stringify(task.final_settings)}`);
  }
  if ((task.final_settings?.modules || []).length !== 0) {
    throw new Error(`“只要正文”没有保存为空模块方案：${JSON.stringify(task.final_settings)}`);
  }
  console.log(JSON.stringify({ ok: true, modules: moduleCount, plan: task.final_settings }));
} finally {
  await browser.close();
}
