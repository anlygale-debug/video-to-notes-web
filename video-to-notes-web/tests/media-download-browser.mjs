import { chromium } from "playwright";

const baseURL = process.env.VTN_E2E_URL || "http://127.0.0.1:4175";
const recordId = "record-media-download";
const audioBytes = Buffer.from("audio-fixture");
const videoBytes = Buffer.from("video-fixture");
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ acceptDownloads: true });
const page = await context.newPage();
page.setDefaultTimeout(5000);
const errors = [];
let videoShouldFail = true;

page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error" && !message.text().includes("status of 502")) {
    errors.push(`console: ${message.text()}`);
  }
});

page.route("**/api/v3/migrations/browser-history", async (route) => {
  await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
});
page.route(`**/api/v3/parser/records/${recordId}`, async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      record: {
        id: recordId,
        source_url: "https://example.test/video",
        platform: "bilibili",
        title: "媒体下载测试视频",
        creator: "测试作者",
        description: "验证下载留在当前页面",
        duration_seconds: 120,
        thumbnail_url: null,
        transcript_text: "用于媒体下载测试的逐字稿。",
      },
    }),
  });
});
page.route(`**/api/v3/parser/records/${recordId}/audio*`, async (route) => {
  const token = new URL(route.request().url()).searchParams.get("download_token");
  await route.fulfill({
    status: 200,
    contentType: "audio/mpeg",
    headers: {
      "Content-Disposition": `attachment; filename="audio-${recordId}.mp3"`,
      ...(token ? { "Set-Cookie": `vtn_download=${token}; Path=/; SameSite=Lax` } : {}),
    },
    body: audioBytes,
  });
});
page.route(`**/api/v3/parser/records/${recordId}/video*`, async (route) => {
  if (videoShouldFail) {
    await route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({
        error: { code: "MEDIA_DOWNLOAD_FAILED", message: "视频下载失败：测试错误" },
      }),
    });
    return;
  }
  const token = new URL(route.request().url()).searchParams.get("download_token");
  await route.fulfill({
    status: 200,
    contentType: "video/mp4",
    headers: {
      "Content-Disposition": `attachment; filename="video-${recordId}.mp4"`,
      ...(token ? { "Set-Cookie": `vtn_download=${token}; Path=/; SameSite=Lax` } : {}),
    },
    body: videoBytes,
  });
});

try {
  await page.goto(`${baseURL}/next?record=${recordId}`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "媒体下载测试视频", exact: true }).waitFor();
  const resultURL = page.url();

  const audioDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "↓ 音频 MP3", exact: true }).click();
  const audioDownload = await audioDownloadPromise;
  if (audioDownload.suggestedFilename() !== `audio-${recordId}.mp3`) {
    throw new Error("音频没有使用浏览器附件下载");
  }
  await page.getByText("音频下载已开始，请在浏览器下载列表查看。", { exact: true }).waitFor();
  if (page.url() !== resultURL) throw new Error("音频下载离开了解析结果页");

  await page.getByRole("button", { name: "↓ 视频 MP4", exact: true }).click();
  await page.getByText("视频下载失败：测试错误", { exact: true }).waitFor();
  if (page.url() !== resultURL) throw new Error("视频下载失败后跳转到了错误页");

  videoShouldFail = false;
  const videoDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "↓ 视频 MP4", exact: true }).click();
  const videoDownload = await videoDownloadPromise;
  if (videoDownload.suggestedFilename() !== `video-${recordId}.mp4`) {
    throw new Error("视频没有使用浏览器附件下载");
  }
  await page.getByText("视频下载已开始，请在浏览器下载列表查看。", { exact: true }).waitFor();
  if (page.url() !== resultURL) throw new Error("视频下载离开了解析结果页");
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify({ ok: true, audio: true, videoError: true, video: true }));
} finally {
  await context.close();
  await browser.close();
}
