import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });

try {
  await page.goto(`${baseURL}/next`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "笔记生成", exact: true }).click();
  await page.locator(".notes-textarea").first().fill(
    "逐章进度测试：先解释控制欲从何而来，再拆解三重心理机制，最后给出关系中的破解练习。"
  );
  await page.getByRole("button", { name: /分析逐字稿/ }).click();
  await page.getByRole("button", { name: "自定义生成" }).waitFor();
  await page.getByRole("button", { name: "自定义生成" }).click();
  await page.locator('[data-setting-group="method"] [data-choice="outline"]').click();
  await page.getByRole("button", { name: /按当前设置开始生成/ }).click();
  await page.getByRole("button", { name: /确认大纲并开始生成/ }).waitFor();
  await page.getByRole("button", { name: /确认大纲并开始生成/ }).click();
  await page.getByRole("heading", { name: "正在按已确认大纲生成" }).waitFor();

  const meter = page.locator("[data-chapter-meter-count]");
  if (await meter.count() !== 1) throw new Error("逐章页没有真实进度计数绑定点");
  const taskLabel = await page.locator("[data-chapter-task-label]").innerText();
  if (taskLabel.includes("N-0727-04")) throw new Error("逐章页仍显示原型固定任务编号");

  const observedCounts = new Set();
  const observedWidths = new Set();
  const observedCurrentTitles = new Set();
  const matchedSideExplanations = new Set();
  let observedRealSummary = false;
  const deadline = Date.now() + 12_000;
  while (Date.now() < deadline) {
    if (await meter.count()) {
      observedCounts.add((await meter.innerText()).replaceAll(" ", ""));
      observedWidths.add(await page.locator("[data-chapter-meter-fill]").getAttribute("style"));
      const current = page.locator(".chapter-list .is-current strong");
      if (await current.count()) {
        const title = (await current.innerText()).trim();
        observedCurrentTitles.add(title);
        const side = await page.locator("[data-chapter-saved-copy]").innerText();
        if (side.includes(title)) matchedSideExplanations.add(title);
      }
      const summary = await page.locator("[data-chapter-context-summary]").innerText();
      if (summary.includes("已说明")) observedRealSummary = true;
    }
    if (await page.getByRole("button", { name: /打开笔记/ }).count()) break;
    await page.waitForTimeout(160);
  }

  for (const expected of ["0/3", "1/3", "2/3"]) {
    if (!observedCounts.has(expected)) {
      throw new Error(`没有观察到真实章节进度 ${expected}；实际：${[...observedCounts].join(", ")}`);
    }
  }
  if (observedWidths.size < 3) {
    throw new Error(`进度条宽度没有随章节推进：${[...observedWidths].join(", ")}`);
  }
  if (observedCurrentTitles.size < 3) {
    throw new Error(`没有观察到三章标题依次生成：${[...observedCurrentTitles].join(" / ")}`);
  }
  if (matchedSideExplanations.size !== observedCurrentTitles.size) {
    throw new Error(`右侧看板没有始终匹配左侧正在生成的章节标题；左侧：${[...observedCurrentTitles].join(" / ")}；右侧：${[...matchedSideExplanations].join(" / ")}`);
  }
  if (!observedRealSummary) throw new Error("右侧看板没有显示真实上下文摘要");
  console.log(JSON.stringify({
    ok: true,
    counts: [...observedCounts],
    currentTitles: [...observedCurrentTitles],
    sideMatches: [...matchedSideExplanations],
  }));
} finally {
  await browser.close();
}
