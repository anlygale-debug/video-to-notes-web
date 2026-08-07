import { chromium } from "playwright";

const baseURL = process.env.VTN_ADMIN_E2E_URL || "http://127.0.0.1:4177";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
page.setDefaultTimeout(6_000);

const channelConfig = {
  free: { enabled: false, default_profile_id: "" },
  paid: { enabled: true, default_profile_id: "deepseek" },
};
let activeChannel = "paid";
let masterEnabled = false;
const profiles = [
  {
    id: "deepseek",
    label: "DeepSeek 高速",
    api_base: "https://api.deepseek.com",
    model: "deepseek-v4-pro",
    channel: "paid",
    protocol: "openai_chat",
    enabled: true,
    api_key_saved: true,
    created_at: "2026-07-31T10:00:00Z",
    updated_at: "2026-07-31T10:00:00Z",
    verified_at: null,
  },
];

function currentState() {
  const views = profiles.map((profile) => ({
    ...profile,
    channel_default: channelConfig[profile.channel].default_profile_id === profile.id,
    active: activeChannel === profile.channel &&
      channelConfig[profile.channel].default_profile_id === profile.id,
  }));
  const channels = {};
  for (const channel of ["free", "paid"]) {
    const items = views.filter((profile) => profile.channel === channel);
    const defaultProfile = items.find((profile) => profile.channel_default) || null;
    channels[channel] = {
      id: channel,
      label: channel === "free" ? "免费线路" : "高速线路",
      enabled: channelConfig[channel].enabled,
      default_profile_id: defaultProfile?.id || "",
      default_profile: defaultProfile,
      available_profile_count: items.filter((profile) => profile.enabled).length,
      profile_count: items.length,
    };
  }
  const activeProfile = channels[activeChannel].default_profile;
  const routeReady = Boolean(
    channels[activeChannel].enabled && activeProfile?.enabled
  );
  return {
    notes_enabled: masterEnabled && routeReady,
    notes_master_enabled: masterEnabled,
    route_ready: routeReady,
    active_channel: activeChannel,
    active_profile_id: activeProfile?.id || "",
    active_profile: activeProfile,
    channels,
    profiles: views,
  };
}

const reply = (route, payload, status = 200) => route.fulfill({
  status,
  contentType: "application/json",
  body: JSON.stringify(payload),
});

await page.route("**/api/grants", (route) => reply(route, { items: [] }));
await page.route("**/api/transcription-provider", (route) => reply(route, {
  active_provider: "local",
  local: { configured: true, model_name: "tiny" },
  cloudflare: {
    configured: false,
    token_saved: false,
    account_id: "",
    verified_at: null,
    model_name: "@cf/openai/whisper-large-v3-turbo",
  },
  usage: {
    today_transcription_minutes: 0,
    estimated_remaining_free_minutes: 214.45,
    estimated_used_neurons: 0,
    daily_free_neurons: 10000,
    model_neurons_per_minute: 46.63,
  },
}));
await page.route("**/api/llm-providers**", async (route) => {
  const request = route.request();
  const path = new URL(request.url()).pathname;
  if (request.method() === "GET" && path.endsWith("/models")) {
    const id = path.split("/").at(-2);
    const profile = profiles.find((item) => item.id === id);
    return reply(route, {
      profile_id: id,
      current_model: profile.model,
      count: 3,
      source: "provider_live_catalog",
      models: [
        {
          id: "anthropic/nvidia_nim/nvidia/nemotron-3-super-120b-a12b",
          upstream_id: "nvidia/nemotron-3-super-120b-a12b",
          publisher: "nvidia",
          label: "nvidia/nemotron-3-super-120b-a12b",
        },
        {
          id: "anthropic/nvidia_nim/z-ai/glm-5.2",
          upstream_id: "z-ai/glm-5.2",
          publisher: "z-ai",
          label: "z-ai/glm-5.2",
        },
        {
          id: "claude-3-freecc-no-thinking/nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b",
          upstream_id: "nvidia/nemotron-3-ultra-550b-a55b",
          publisher: "nvidia",
          label: "nvidia/nemotron-3-ultra-550b-a55b（关闭深度思考｜适合笔记）",
          reasoning_mode: "off",
        },
      ],
    });
  }
  if (request.method() === "GET") return reply(route, currentState());
  if (request.method() === "POST" && path.endsWith("/reveal-key")) {
    return reply(route, {
      profile_id: path.split("/").at(-2),
      api_key: "browser-secret-must-stay-hidden",
    });
  }
  if (request.method() === "POST" && path === "/api/llm-providers") {
    const body = request.postDataJSON();
    const profile = {
      id: "fcc-free",
      label: body.label,
      api_base: body.api_base,
      model: body.model,
      channel: body.channel,
      protocol: body.protocol,
      enabled: body.enabled,
      api_key_saved: true,
      created_at: "2026-08-07T11:00:00Z",
      updated_at: "2026-08-07T11:00:00Z",
      verified_at: null,
    };
    profiles.push(profile);
    if (!channelConfig[profile.channel].default_profile_id) {
      channelConfig[profile.channel].default_profile_id = profile.id;
    }
    return reply(route, { profile, ...currentState() }, 201);
  }
  if (request.method() === "PUT" && path.includes("/channels/") && path.endsWith("/enabled")) {
    const channel = path.split("/").at(-2);
    channelConfig[channel].enabled = request.postDataJSON().enabled;
    return reply(route, currentState());
  }
  if (request.method() === "PUT" && path.endsWith("/active-channel")) {
    activeChannel = request.postDataJSON().channel;
    return reply(route, currentState());
  }
  if (request.method() === "POST" && path.endsWith("/default")) {
    const id = path.split("/").at(-2);
    const profile = profiles.find((item) => item.id === id);
    channelConfig[profile.channel].default_profile_id = id;
    return reply(route, currentState());
  }
  if (request.method() === "PUT" && /\/api\/llm-providers\/[^/]+\/enabled$/.test(path)) {
    const id = path.split("/").at(-2);
    profiles.find((item) => item.id === id).enabled = request.postDataJSON().enabled;
    return reply(route, currentState());
  }
  if (request.method() === "PUT" && path.endsWith("/model")) {
    const id = path.split("/").at(-2);
    const profile = profiles.find((item) => item.id === id);
    profile.model = request.postDataJSON().model;
    profile.verified_at = "2026-08-07T11:03:00Z";
    return reply(route, {
      profile,
      verification: {
        requested_model: profile.model,
        response_model: profile.model,
      },
      ...currentState(),
    });
  }
  if (
    request.method() === "PUT" &&
    /\/api\/llm-providers\/[^/]+$/.test(path) &&
    profiles.some((item) => item.id === path.split("/").at(-1))
  ) {
    const id = path.split("/").at(-1);
    const profile = profiles.find((item) => item.id === id);
    Object.assign(profile, request.postDataJSON());
    profile.api_key_saved = true;
    return reply(route, { profile, ...currentState() });
  }
  if (request.method() === "POST" && path.endsWith("/test")) {
    const id = path.split("/").at(-2);
    const profile = profiles.find((item) => item.id === id);
    profile.verified_at = "2026-08-07T11:05:00Z";
    return reply(route, { profile, ...currentState() });
  }
  if (request.method() === "PUT" && path.endsWith("/notes-enabled")) {
    masterEnabled = request.postDataJSON().enabled;
    return reply(route, currentState());
  }
  return reply(route, { detail: `unexpected mocked request: ${request.method()} ${path}` }, 400);
});

try {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "控制免费与高速笔记线路" }).waitFor();
  await page.getByText("DeepSeek 高速", { exact: true }).waitFor();
  await page.getByText("笔记生成已暂停", { exact: true }).waitFor();

  await page.getByRole("button", { name: "新增 LLM 配置" }).click();
  const formDialog = page.getByRole("dialog", { name: "新增 LLM 配置" });
  await formDialog.getByRole("button", { name: "FCC / NVIDIA" }).click();
  await formDialog.getByLabel("方案备注").fill("FCC NVIDIA 免费");
  await formDialog.getByLabel("API 密钥").fill("browser-secret-must-stay-hidden");
  await formDialog.getByRole("button", { name: "保存配置" }).click();
  await formDialog.waitFor({ state: "hidden" });

  const freeCard = page.locator("[data-llm-card]", { hasText: "FCC NVIDIA 免费" });
  await freeCard.waitFor();
  await freeCard.getByText("Anthropic / FCC", { exact: true }).waitFor();
  if ((await page.locator("body").innerText()).includes("browser-secret-must-stay-hidden")) {
    throw new Error("LLM 密钥不应出现在工作台页面");
  }

  await freeCard.getByRole("button", { name: "编辑配置" }).click();
  const editDialog = page.getByRole("dialog", { name: "编辑 LLM 配置" });
  const savedKeyInput = editDialog.locator("[data-llm-api-key]");
  await page.waitForFunction(() => {
    const input = document.querySelector("[data-llm-api-key]");
    return Boolean(input?.value);
  });
  if ((await savedKeyInput.inputValue()).length === 0) {
    throw new Error("编辑配置时应自动填入本地保存的 API 密钥");
  }
  if ((await savedKeyInput.evaluate((input) => getComputedStyle(input).webkitTextSecurity)) !== "disc") {
    throw new Error("已保存 API 密钥默认必须以圆点隐藏");
  }
  await editDialog.getByRole("button", { name: "显示" }).click();
  if ((await savedKeyInput.evaluate((input) => getComputedStyle(input).webkitTextSecurity)) !== "none") {
    throw new Error("点击显示后应允许本地管理员查看密钥");
  }
  await editDialog.getByRole("button", { name: "隐藏" }).click();
  await editDialog.getByLabel("NVIDIA 免费模型").waitFor();
  await editDialog.getByText("已读取 3 个可用模型与笔记模式", { exact: false }).waitFor();
  await editDialog.getByLabel("NVIDIA 免费模型").selectOption(
    "claude-3-freecc-no-thinking/nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b",
  );
  await editDialog.getByRole("button", { name: "保存配置" }).click();
  await editDialog.waitFor({ state: "hidden" });
  await freeCard.getByText("nvidia/nemotron-3-ultra-550b-a55b（关闭深度思考｜适合笔记）", { exact: true }).waitFor();
  await page.getByText("已真实验证并切换到", { exact: false }).waitFor();

  const freeChannel = page.locator('[data-llm-channel="free"]');
  await freeChannel.getByRole("button", { name: "开启整条线路" }).click();
  await freeChannel.getByRole("button", { name: "切换新任务到此线路" }).click();
  await page.getByText("免费线路：FCC NVIDIA 免费 / nvidia/nemotron-3-ultra-550b-a55b（关闭深度思考｜适合笔记）", { exact: true }).waitFor();

  await page.getByRole("button", { name: "开启笔记生成" }).click();
  const enableDialog = page.getByRole("dialog", { name: "开启真实笔记生成？" });
  await enableDialog.getByText("不会消耗已配置的付费线路额度", { exact: false }).waitFor();
  await enableDialog.getByRole("button", { name: "确认开启" }).click();
  await page.getByText("笔记生成已开启", { exact: true }).waitFor();

  await freeCard.getByRole("button", { name: "测试连接" }).click();
  await freeCard.getByText("连接可用", { exact: true }).waitFor();
  await freeCard.getByRole("button", { name: "关闭此 API" }).click();
  await page.getByText("已开启，但当前线路不可用", { exact: true }).waitFor();
  await freeCard.getByRole("button", { name: "开启此 API" }).click();
  await page.getByText("笔记生成已开启", { exact: true }).waitFor();

  const openDialogs = await page.locator("dialog[open]").count();
  if (openDialogs !== 0) throw new Error(`操作完成后仍有 ${openDialogs} 个弹窗未关闭`);

  if (process.env.VTN_E2E_SCREENSHOT) {
    await page.locator(".llm-console").screenshot({ path: process.env.VTN_E2E_SCREENSHOT });
  }

  console.log(JSON.stringify({
    ok: true,
    freeProfileCreated: true,
    secretHidden: true,
    freeChannelEnabled: true,
    activeChannelSwitched: true,
    notesEnabled: true,
    profileToggleIndependent: true,
    connectionTestedExplicitly: true,
    liveModelCatalogDropdown: true,
    selectedModelVerifiedBeforeSwitch: true,
    savedKeyPrefilledAndMasked: true,
    browserPasswordAutofillBypassed: true,
    noteOptimizedUltraSelectable: true,
  }));
} finally {
  await browser.close();
}
