import { chromium } from "playwright";

const baseURL = process.env.VTN_ADMIN_E2E_URL || "http://127.0.0.1:4177";
const browser = await chromium.launch({ headless: true });
const viewport = process.env.VTN_E2E_MOBILE === "1"
  ? { width: 390, height: 844 }
  : { width: 1440, height: 1000 };
const testerLabel = process.env.VTN_E2E_MOBILE === "1"
  ? "小王｜移动端体验"
  : "小王｜产品体验";
const context = await browser.newContext({
  viewport,
  permissions: ["clipboard-read", "clipboard-write"],
});
const page = await context.newPage();
page.setDefaultTimeout(5_000);

try {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "内测码控制台" }).waitFor();
  await page.getByText("备注只供你识别，不参与用户登录。", { exact: true }).waitFor();
  await page.getByText("仅通过 SSH 安全通道访问", { exact: true }).waitFor();
  if (process.env.VTN_E2E_READ_ONLY === "1") {
    if (process.env.VTN_E2E_EXPECT_LEGACY === "1") {
      const legacyGrant = page.locator("[data-grant-card]", { hasText: "owner" });
      await legacyGrant.getByRole("button", { name: "从剪贴板导入旧码" }).waitFor();
      if (process.env.VTN_E2E_EXPECT_EDIT === "1") {
        await legacyGrant.getByRole("button", { name: "编辑额度" }).click();
        const editDialog = page.getByRole("dialog", { name: "编辑测试资格" });
        await editDialog.waitFor({ state: "visible" });
        await editDialog.getByLabel("剩余转录分钟").waitFor();
        await editDialog.getByLabel("剩余高速次数").waitFor();
        await editDialog.getByLabel("单个视频最长分钟").waitFor();
        await editDialog.getByRole("button", { name: "取消" }).click();
      }
    }
    console.log(JSON.stringify({ ok: true, adminPageVisible: true, readOnlySmoke: true }));
    process.exitCode = 0;
  } else {

    await page.locator("[data-create-form]").getByLabel("测试者备注").fill(testerLabel);
    await page.getByRole("button", { name: "深度体验" }).click();
    await page.getByRole("button", { name: "生成内测码" }).click();

    const resultDialog = page.getByRole("dialog", { name: "内测码已生成" });
    await resultDialog.waitFor({ state: "visible" });
    const code = (await resultDialog.locator("[data-created-code]").innerText()).trim();
    if (!code.startsWith("VTN-")) throw new Error("未生成预期格式的内测码");
    await resultDialog.locator("[data-created-qr] svg").waitFor();
    await resultDialog.getByRole("button", { name: "复制内测码" }).click();
    await resultDialog.getByText("已复制", { exact: true }).waitFor();
    if (await page.evaluate(() => navigator.clipboard.readText()) !== code) {
      throw new Error("复制到剪贴板的内测码不正确");
    }
    if (process.env.VTN_E2E_SCREENSHOT) {
      await page.screenshot({ path: process.env.VTN_E2E_SCREENSHOT, fullPage: false });
    }
    await resultDialog.getByRole("button", { name: "完成" }).click();
    await resultDialog.waitFor({ state: "hidden" });

    const grant = page.locator("[data-grant-card]", { hasText: testerLabel });
    await grant.waitFor();
    await grant.getByText("可使用", { exact: true }).waitFor();
    await grant.getByText("120 分钟", { exact: true }).waitFor();
    await grant.getByText("3 次", { exact: true }).waitFor();
    await grant.getByText(code, { exact: true }).waitFor();
    await grant.getByRole("button", { name: "复制此内测码" }).click();
    await grant.getByText("已复制", { exact: true }).waitFor();
    if (await page.evaluate(() => navigator.clipboard.readText()) !== code) {
      throw new Error("卡片复制的内测码不正确");
    }
    if (process.env.VTN_E2E_ROSTER_SCREENSHOT) {
      await page.screenshot({ path: process.env.VTN_E2E_ROSTER_SCREENSHOT, fullPage: true });
    }

    await page.reload({ waitUntil: "networkidle" });
    const reloadedGrant = page.locator("[data-grant-card]", { hasText: testerLabel });
    await reloadedGrant.getByText(code, { exact: true }).waitFor();
    await reloadedGrant.getByRole("button", { name: "复制此内测码" }).waitFor();

    await page.evaluate(() => localStorage.clear());
    await page.reload({ waitUntil: "networkidle" });
    const legacyGrant = page.locator("[data-grant-card]", { hasText: testerLabel });
    await legacyGrant.getByRole("button", { name: "从剪贴板导入旧码" }).click();
    const importDialog = page.getByRole("dialog", { name: "导入已有内测码" });
    await importDialog.waitFor({ state: "visible" });
    await importDialog.getByLabel("已有内测码").waitFor();
    await importDialog.getByRole("button", { name: "验证并保存" }).click();
    await importDialog.waitFor({ state: "hidden" });
    await legacyGrant.getByText(code, { exact: true }).waitFor();

    await legacyGrant.getByRole("button", { name: "编辑额度" }).click();
    const editDialog = page.getByRole("dialog", { name: "编辑测试资格" });
    await editDialog.waitFor({ state: "visible" });
    await editDialog.getByLabel("测试者备注").fill(`${testerLabel}｜已调整`);
    await editDialog.getByLabel("剩余转录分钟").fill("30");
    await editDialog.getByLabel("单个视频最长分钟").fill("60");
    await editDialog.getByText(
      "单视频上限高于剩余转录额度，请同时补充转录额度。",
      { exact: true }
    ).waitFor();
    await editDialog.getByLabel("剩余转录分钟").fill("200");
    await editDialog.getByLabel("剩余高速次数").fill("30");
    await editDialog.getByText("120 → 200", { exact: true }).waitFor();
    await editDialog.getByText("3 → 30", { exact: true }).waitFor();
    await editDialog.getByText("20 → 60", { exact: true }).waitFor();
    if (process.env.VTN_E2E_EDIT_SCREENSHOT) {
      await page.screenshot({ path: process.env.VTN_E2E_EDIT_SCREENSHOT, fullPage: false });
    }
    await editDialog.getByRole("button", { name: "保存修改" }).click();
    await editDialog.waitFor({ state: "hidden" });

    const updatedGrant = page.locator("[data-grant-card]", {
      hasText: `${testerLabel}｜已调整`,
    });
    await updatedGrant.getByText("200 分钟", { exact: true }).waitFor();
    await updatedGrant.getByText("30 次", { exact: true }).waitFor();
    await updatedGrant.getByText("60 分钟", { exact: true }).waitFor();
    await updatedGrant.getByText(code, { exact: true }).waitFor();

    await updatedGrant.getByRole("button", { name: "吊销" }).click();
    const revokeDialog = page.getByRole("dialog", { name: "确认吊销内测码" });
    await revokeDialog.waitFor({ state: "visible" });
    await revokeDialog.getByRole("button", { name: "确认吊销" }).click();
    await reloadedGrant.getByText("已吊销", { exact: true }).waitFor();

    console.log(JSON.stringify({
      ok: true,
      createdOnce: true,
      copied: true,
      qrVisible: true,
      locallyRetained: true,
      legacyCodeImported: true,
      quotasEdited: true,
      revoked: true,
    }));
  }
} finally {
  await browser.close();
}
