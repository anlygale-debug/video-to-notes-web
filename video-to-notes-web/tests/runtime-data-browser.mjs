import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
page.setDefaultTimeout(8_000);

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.locator(".notes-textarea").first().fill(
    "固定数据清扫验收：解释真实问题、给出具体方法和两步行动。"
  );
  await page.getByRole("button", { name: /分析逐字稿/ }).click();
  await page.getByRole("button", { name: "自定义生成" }).waitFor();
  await page.locator("#suggested-note-title").fill("运行数据清扫验收笔记");
  await page.getByRole("button", { name: "自定义生成" }).click();
  await page.locator('[data-setting-group="structure"] [data-choice="thematic"]').click();
  await page.locator('[data-setting-group="detail"] [data-choice="quick"]').click();
  await page.getByRole("button", { name: /按当前设置开始生成/ }).click();

  await page.locator("[data-direct-stage-count]").waitFor();
  const directText = await page.locator(".generation-stack").innerText();
  if (directText.includes("N-0727") || directText.includes("03 / 05") || directText.includes("4 项")) {
    throw new Error("直接生成页仍显示原型固定运行数据");
  }
  if (!(await page.locator("[data-direct-task-label]").innerText()).startsWith("TASK ")) {
    throw new Error("直接生成页没有显示真实任务标识");
  }
  if ((await page.locator("[data-direct-stage-count]").textContent()).replace(/\s/g, "") !== "04/05阶段") {
    throw new Error("直接生成阶段没有绑定真实进度");
  }
  if (!(await page.locator("[data-generation-settings]").innerText()).includes("按主题分类")) {
    throw new Error("直接生成回执没有绑定真实最终设置");
  }

  await page.getByRole("button", { name: /打开笔记/ }).waitFor({ timeout: 15_000 });
  const completeText = await page.locator(".generation-complete-stack").innerText();
  for (const fixed of ["N-0727", "5 / 5", "3,486 字", "Bilibili · 08:42"]) {
    if (completeText.includes(fixed)) throw new Error(`完成回执仍显示固定数据：${fixed}`);
  }
  if ((await page.locator("[data-completion-title]").innerText()).trim() !== "运行数据清扫验收笔记") {
    throw new Error("完成回执没有显示真实笔记标题");
  }
  const actualChars = Number(await page.locator("[data-completion-character-count]").getAttribute("data-value"));
  if (!Number.isFinite(actualChars) || actualChars <= 0) {
    throw new Error("完成回执没有显示真实正文字符数");
  }
  if (!(await page.locator("[data-completion-modules]").innerText()).includes("关键概念")) {
    throw new Error("完成回执没有显示真实附加模块");
  }

  console.log(JSON.stringify({ ok: true, directDynamic: true, completionDynamic: true, actualChars }));
} finally {
  await browser.close();
}
