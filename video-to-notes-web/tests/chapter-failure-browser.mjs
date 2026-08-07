import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
page.setDefaultTimeout(5_000);

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.locator(".notes-textarea").first().fill(
    "失败态测试：先解释控制欲从何而来，再拆解三重心理机制，最后给出关系练习。"
  );
  await page.getByRole("button", { name: /分析逐字稿/ }).click();
  await page.getByRole("button", { name: "自定义生成" }).waitFor();
  await page.getByRole("button", { name: "自定义生成" }).click();
  await page.locator('[data-setting-group="method"] [data-choice="outline"]').click();
  await page.getByRole("button", { name: /按当前设置开始生成/ }).click();
  await page.getByRole("button", { name: /确认大纲并开始生成/ }).waitFor();
  await page.getByRole("button", { name: /确认大纲并开始生成/ }).click();
  await page.locator(".chapter-failure-stack").waitFor({ timeout: 12_000 });

  const heading = (await page.locator(".chapter-failure-banner h2").innerText()).trim();
  const copy = (await page.locator(".chapter-failure-banner p").innerText()).trim();
  const attempt = (await page.locator("[data-chapter-failure-attempt]").innerText()).trim();
  const continueLabel = (await page.locator("[data-continue-chapter]").innerText()).trim();
  const failedTitle = (await page.locator(".chapter-list .is-failed strong").innerText()).trim();

  if (heading !== "第 1 章《控制欲从何而来》生成未完成。") {
    throw new Error(`失败标题没有使用真实第一章：${heading}`);
  }
  if (!copy.includes("尚无已完成章节") || !copy.includes("第一章")) {
    throw new Error(`失败说明没有使用真实保留数量：${copy}`);
  }
  if (attempt !== "本章尝试 1 次") {
    throw new Error(`失败次数不真实：${attempt}`);
  }
  if (continueLabel !== "从第 1 章继续") {
    throw new Error(`继续按钮没有使用真实章节：${continueLabel}`);
  }
  if (failedTitle !== "控制欲从何而来") {
    throw new Error(`左侧失败章节不正确：${failedTitle}`);
  }
  if ((await page.locator("body").innerText()).includes("第三章连续重试后仍未完成")) {
    throw new Error("页面仍显示原型固定的第三章失败文案");
  }

  await page.locator("[data-continue-chapter]").click();
  await page.locator("[data-chapter-failure-attempt]").waitFor({ timeout: 12_000 });
  await page.waitForFunction(
    () => document.querySelector("[data-chapter-failure-attempt]")?.textContent?.trim()
      === "本章尝试 2 次",
    null,
    { timeout: 12_000 },
  );
  const retryHeading = (await page.locator(".chapter-failure-banner h2").innerText()).trim();
  const retryAttempt = (await page.locator("[data-chapter-failure-attempt]").innerText()).trim();
  if (retryHeading !== "第 1 章《控制欲从何而来》第 2 次尝试仍未完成。") {
    throw new Error(`重试失败标题没有使用真实章节和次数：${retryHeading}`);
  }

  console.log(JSON.stringify({
    ok: true,
    heading,
    attempt,
    continueLabel,
    retryHeading,
    retryAttempt,
  }));
} finally {
  await browser.close();
}
