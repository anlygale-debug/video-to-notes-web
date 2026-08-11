(() => {
  const csrf = document.querySelector('meta[name="vtn-admin-csrf"]')?.content || "";
  const form = document.querySelector("[data-create-form]");
  const list = document.querySelector("[data-grant-list]");
  const emptyState = document.querySelector("[data-empty-state]");
  const resultDialog = document.querySelector("[data-result-dialog]");
  const revokeDialog = document.querySelector("[data-revoke-dialog]");
  const importDialog = document.querySelector("[data-import-dialog]");
  const editDialog = document.querySelector("[data-edit-dialog]");
  const cloudflareDialog = document.querySelector("[data-cloudflare-dialog]");
  const cloudflareDeleteDialog = document.querySelector(
    "[data-cloudflare-delete-dialog]"
  );
  const cloudflareForm = document.querySelector("[data-cloudflare-form]");
  const llmDialog = document.querySelector("[data-llm-dialog]");
  const llmForm = document.querySelector("[data-llm-form]");
  const llmEnableDialog = document.querySelector("[data-llm-enable-dialog]");
  const llmDeleteDialog = document.querySelector("[data-llm-delete-dialog]");
  const codeNode = document.querySelector("[data-created-code]");
  const qrNode = document.querySelector("[data-created-qr]");
  const copyButton = document.querySelector("[data-copy-code]");
  const formError = document.querySelector("[data-form-error]");
  const localCodeStorageKey = "vtn-admin-local-codes-v1";
  let currentCode = "";
  let pendingRevokeId = "";
  let pendingImportGrant = null;
  let pendingEditGrant = null;
  let providerState = null;
  let llmState = null;
  let editingLLMProfile = null;
  let deletingLLMProfile = null;
  let loadedLLMSecret = "";
  let localCodes = readLocalCodes();

  function readLocalCodes() {
    try {
      const value = JSON.parse(localStorage.getItem(localCodeStorageKey) || "{}");
      return value && typeof value === "object" ? value : {};
    } catch {
      return {};
    }
  }

  function persistLocalCodes() {
    localStorage.setItem(localCodeStorageKey, JSON.stringify(localCodes));
  }

  function rememberLocalCode(accessId, inviteCode) {
    localCodes[accessId] = inviteCode;
    persistLocalCodes();
  }

  function forgetLocalCode(accessId) {
    if (!(accessId in localCodes)) return;
    delete localCodes[accessId];
    persistLocalCodes();
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-VTN-Admin-CSRF": csrf,
        ...(options.headers || {}),
      },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join("；")
        : payload.detail;
      throw new Error(detail || "操作失败，请稍后重试");
    }
    return payload;
  }

  function formatNumber(value) {
    if (value === null || value === undefined) return "不限";
    return Number.isInteger(value) ? String(value) : value.toFixed(1);
  }

  function escapeHTML(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date);
  }

  function grantCard(grant, index) {
    const card = document.createElement("article");
    card.className = `grant-card${grant.enabled ? "" : " is-revoked"}`;
    card.dataset.grantCard = "";
    card.style.animationDelay = `${Math.min(index * 35, 210)}ms`;

    const identity = document.createElement("div");
    identity.className = "grant-identity";
    const status = document.createElement("span");
    status.className = "status-badge";
    status.textContent = grant.enabled ? "可使用" : "已吊销";
    const label = document.createElement("strong");
    label.textContent = grant.label;
    const created = document.createElement("small");
    created.textContent = `创建于 ${formatDate(grant.created_at)}`;
    identity.append(status, label, created);
    if (grant.last_adjusted_at) {
      const adjusted = document.createElement("small");
      adjusted.textContent = `额度调整于 ${formatDate(grant.last_adjusted_at)}`;
      identity.append(adjusted);
    }

    const transcription = metric(
      "剩余转录",
      `${formatNumber(grant.remaining_transcription_minutes)} 分钟`
    );
    const notes = metric(
      "剩余高速",
      `${formatNumber(grant.remaining_note_generations)} 次`
    );
    const maxVideo = metric(
      "单条上限",
      `${formatNumber(grant.max_video_minutes)} 分钟`
    );

    const action = document.createElement("div");
    action.className = "grant-action";
    if (grant.enabled) {
      const editButton = document.createElement("button");
      editButton.className = "edit-button";
      editButton.type = "button";
      editButton.textContent = "编辑额度";
      editButton.addEventListener("click", () => openEdit(grant));
      const button = document.createElement("button");
      button.className = "revoke-button";
      button.type = "button";
      button.textContent = "吊销";
      button.addEventListener("click", () => openRevoke(grant));
      action.append(editButton, button);
    } else {
      const mark = document.createElement("span");
      mark.className = "revoked-mark";
      mark.textContent = "ACCESS OFF";
      action.append(mark);
    }

    card.append(identity, transcription, notes, maxVideo, action);
    if (grant.enabled) card.append(grantCodeVault(grant));
    return card;
  }

  function metric(label, value) {
    const node = document.createElement("div");
    node.className = "grant-metric";
    const small = document.createElement("small");
    small.textContent = label;
    const strong = document.createElement("strong");
    strong.textContent = value;
    node.append(small, strong);
    return node;
  }

  function grantCodeVault(grant) {
    const vault = document.createElement("div");
    vault.className = "grant-code-vault";
    const copy = document.createElement("div");
    copy.className = "grant-code-copy";
    const eyebrow = document.createElement("small");
    const code = localCodes[grant.id];

    if (code) {
      eyebrow.textContent = "LOCAL CODE VAULT // 仅存于这台 Mac";
      const value = document.createElement("strong");
      value.textContent = code;
      const hint = document.createElement("p");
      hint.textContent = "服务器仍只保存哈希；清除浏览器数据后需要重新导入。";
      copy.append(eyebrow, value, hint);
      const button = document.createElement("button");
      button.className = "card-copy-button";
      button.type = "button";
      button.setAttribute("aria-label", "复制此内测码");
      button.textContent = "复制";
      button.addEventListener("click", async () => {
        await copyText(code);
        button.textContent = "已复制";
        button.classList.add("is-copied");
      });
      vault.append(copy, button);
      return vault;
    }

    vault.classList.add("is-missing");
    eyebrow.textContent = "LEGACY PASS // 旧码未存于本机";
    const value = document.createElement("strong");
    value.textContent = "服务器无法反查旧码明文";
    const hint = document.createElement("p");
    hint.textContent = "从剪贴板导入一次，之后即可在这张卡片直接复制。";
    copy.append(eyebrow, value, hint);
    const button = document.createElement("button");
    button.className = "import-code-button";
    button.type = "button";
    button.textContent = "从剪贴板导入旧码";
    button.addEventListener("click", () => openImport(grant));
    vault.append(copy, button);
    return vault;
  }

  function updateStats(items) {
    document.querySelector("[data-stat-total]").textContent = items.length;
    document.querySelector("[data-stat-active]").textContent =
      items.filter((item) => item.enabled).length;
    document.querySelector("[data-stat-revoked]").textContent =
      items.filter((item) => !item.enabled).length;
  }

  async function loadGrants() {
    const payload = await api("/api/grants");
    const activeIds = new Set(
      payload.items.filter((item) => item.enabled).map((item) => item.id)
    );
    let changed = false;
    Object.keys(localCodes).forEach((accessId) => {
      if (activeIds.has(accessId)) return;
      delete localCodes[accessId];
      changed = true;
    });
    if (changed) persistLocalCodes();
    list.replaceChildren(...payload.items.map(grantCard));
    emptyState.hidden = payload.items.length !== 0;
    updateStats(payload.items);
  }

  function setProviderMessage(message, tone = "success") {
    const node = document.querySelector("[data-provider-message]");
    node.textContent = message;
    node.dataset.tone = tone;
    node.hidden = !message;
  }

  function renderProvider(payload) {
    providerState = payload;
    const isLocal = payload.active_provider === "local";
    const configured = payload.cloudflare.configured;
    document.querySelector("[data-active-provider]").textContent = isLocal
      ? "本地 tiny 运行中"
      : "Cloudflare API 运行中";
    document
      .querySelector('[data-provider-card="local"]')
      .classList.toggle("is-active", isLocal);
    document
      .querySelector('[data-provider-card="cloudflare"]')
      .classList.toggle("is-active", !isLocal);
    document.querySelector("[data-local-badge]").textContent = isLocal
      ? "正在使用"
      : "随时可切换";
    document.querySelector("[data-cloudflare-badge]").textContent = !configured
      ? "未配置"
      : !isLocal
        ? "正在使用"
        : "已连接";
    document.querySelector("[data-local-model]").textContent =
      payload.local.model_name;
    document.querySelector("[data-cloudflare-account]").textContent = configured
      ? payload.cloudflare.account_id
      : "尚未保存";
    document.querySelector("[data-cloudflare-token]").textContent =
      payload.cloudflare.token_saved ? "已安全保存，不回显" : "尚未保存";
    document.querySelector("[data-cloudflare-verified]").textContent =
      payload.cloudflare.verified_at
        ? formatDate(payload.cloudflare.verified_at)
        : "—";
    document.querySelector("[data-open-cloudflare]").textContent = configured
      ? "编辑 Cloudflare 凭证"
      : "配置 Cloudflare";
    document.querySelector("[data-delete-cloudflare]").hidden = !configured;
    document.querySelector("[data-switch-local]").disabled = isLocal;
    document.querySelector("[data-switch-local]").textContent = isLocal
      ? "本地 tiny 正在使用"
      : "切换到本地 tiny";
    const cloudSwitch = document.querySelector("[data-switch-cloudflare]");
    cloudSwitch.disabled = !configured || !isLocal;
    cloudSwitch.textContent = !configured
      ? "请先配置凭证"
      : !isLocal
        ? "Cloudflare 正在使用"
        : "切换到 Cloudflare";

    const usage = payload.usage;
    const used = Number(usage.estimated_used_neurons || 0);
    const free = Number(usage.daily_free_neurons || 10000);
    const percentage = Math.min(100, Math.max(0, (used / free) * 100));
    document.querySelector("[data-usage-minutes]").textContent = formatNumber(
      Number(usage.today_transcription_minutes || 0)
    );
    document.querySelector("[data-remaining-minutes]").textContent = formatNumber(
      Number(usage.estimated_remaining_free_minutes || 0)
    );
    document.querySelector("[data-used-neurons]").textContent =
      new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(used);
    document.querySelector("[data-free-neurons]").textContent =
      new Intl.NumberFormat("zh-CN").format(free);
    document.querySelector("[data-neuron-rate]").textContent =
      formatNumber(Number(usage.model_neurons_per_minute));
    document.querySelector("[data-usage-bar]").style.width = `${percentage}%`;
  }

  async function loadProvider() {
    renderProvider(await api("/api/transcription-provider"));
  }

  function setLLMMessage(message, tone = "success") {
    const node = document.querySelector("[data-llm-message]");
    node.textContent = message;
    node.dataset.tone = tone;
    node.hidden = !message;
  }

  function llmMetric(label, value) {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    const description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value;
    row.append(term, description);
    return row;
  }

  const llmChannelLabels = { free: "免费线路", paid: "高速线路" };
  const llmProtocolLabels = {
    openai_chat: "OpenAI Chat",
    anthropic_messages: "Anthropic / FCC",
  };

  function llmModelDisplayName(modelId) {
    const value = String(modelId || "");
    const noThinkingPrefix = "claude-3-freecc-no-thinking/nvidia_nim/";
    const directPrefix = "anthropic/nvidia_nim/";
    if (value.startsWith(noThinkingPrefix)) {
      return `${value.slice(noThinkingPrefix.length)}（关闭深度思考｜适合笔记）`;
    }
    return value.startsWith(directPrefix) ? value.slice(directPrefix.length) : value;
  }

  function llmCard(profile, index) {
    const card = document.createElement("article");
    card.className = `llm-card llm-card--${profile.channel}` +
      `${profile.active ? " is-active" : ""}` +
      `${profile.channel_default ? " is-default" : ""}` +
      `${profile.enabled ? "" : " is-disabled"}`;
    card.dataset.llmCard = "";
    card.dataset.routeIndex = String(index + 1).padStart(2, "0");
    card.style.animationDelay = `${Math.min(index * 45, 225)}ms`;

    const top = document.createElement("div");
    top.className = "llm-card-top";
    const route = document.createElement("span");
    route.className = "llm-card-route";
    route.textContent = `${profile.channel === "free" ? "FREE" : "FAST"} ${String(index + 1).padStart(2, "0")}`;
    const badge = document.createElement("span");
    badge.className = "llm-card-badge";
    badge.textContent = !profile.enabled
      ? "已关闭"
      : profile.active
        ? "当前使用"
        : profile.channel_default
          ? "线路默认"
          : "已启用";
    top.append(route, badge);

    const identity = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = profile.label;
    const model = document.createElement("div");
    model.className = "llm-model-name";
    model.textContent = llmModelDisplayName(profile.model);
    identity.append(title, model);

    const details = document.createElement("dl");
    details.append(
      llmMetric("API 地址", profile.api_base),
      llmMetric("接口协议", llmProtocolLabels[profile.protocol] || profile.protocol),
      llmMetric("API 密钥", profile.api_key_saved ? "已安全保存，不回显" : "尚未保存"),
      llmMetric("连接状态", profile.verified_at ? "连接可用" : "尚未测试"),
      llmMetric("最近测试", profile.verified_at ? formatDate(profile.verified_at) : "—"),
    );

    const actions = document.createElement("div");
    actions.className = "llm-card-actions";
    const makeDefault = document.createElement("button");
    makeDefault.type = "button";
    makeDefault.className = "llm-activate";
    makeDefault.textContent = profile.channel_default ? "该线路默认模型" : "设为该线路默认";
    makeDefault.disabled = profile.channel_default || !profile.enabled;
    makeDefault.addEventListener("click", () => setDefaultLLMProfile(profile, makeDefault));
    const toggleProfile = document.createElement("button");
    toggleProfile.type = "button";
    toggleProfile.className = "llm-profile-toggle";
    toggleProfile.textContent = profile.enabled ? "关闭此 API" : "开启此 API";
    toggleProfile.addEventListener("click", () => toggleLLMProfile(profile, toggleProfile));
    const test = document.createElement("button");
    test.type = "button";
    test.textContent = "测试连接";
    test.addEventListener("click", () => testLLMProfile(profile, test));
    const edit = document.createElement("button");
    edit.type = "button";
    edit.textContent = "编辑配置";
    edit.addEventListener("click", () => openLLMForm(profile));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "llm-delete";
    remove.textContent = "删除配置";
    remove.addEventListener("click", () => openLLMDelete(profile));
    actions.append(makeDefault, toggleProfile, test, edit, remove);

    card.append(top, identity, details, actions);
    return card;
  }

  function llmChannelCard(channel) {
    const config = llmState.channels[channel];
    const active = llmState.active_channel === channel;
    const ready = Boolean(config.enabled && config.default_profile?.enabled);
    const card = document.createElement("article");
    card.className = `llm-channel-card llm-channel-card--${channel}` +
      `${active ? " is-active" : ""}${config.enabled ? "" : " is-off"}`;
    card.dataset.llmChannel = channel;
    card.innerHTML = `
      <div class="llm-channel-index">${channel === "free" ? "F0" : "P1"}</div>
      <div class="llm-channel-copy">
        <span class="eyebrow">${channel === "free" ? "FREE ROUTE // 慢速" : "FAST ROUTE // 高速"}</span>
        <h3>${llmChannelLabels[channel]}</h3>
        <p>${channel === "free" ? "优先使用免费额度；长内容可能等待更久。" : "优先稳定性和速度；可能消耗账户额度。"}</p>
        <small>${config.available_profile_count} 个 API 开启 / ${config.profile_count} 个已保存</small>
        <strong>${config.default_profile ? `默认：${escapeHTML(config.default_profile.label)} / ${escapeHTML(llmModelDisplayName(config.default_profile.model))}` : "尚未选择默认模型"}</strong>
      </div>
      <div class="llm-channel-actions"></div>`;
    const actions = card.querySelector(".llm-channel-actions");
    const choose = document.createElement("button");
    choose.type = "button";
    choose.className = "llm-channel-choose";
    choose.textContent = active ? "当前兼容默认线路" : "设为兼容默认线路";
    choose.disabled = active || !ready;
    choose.addEventListener("click", () => switchLLMChannel(channel, choose));
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "llm-channel-toggle";
    toggle.textContent = config.enabled ? "关闭整条线路" : "开启整条线路";
    toggle.addEventListener("click", () => toggleLLMChannel(channel, !config.enabled, toggle));
    actions.append(choose, toggle);
    return card;
  }

  function llmChannelGroup(channel, profiles) {
    const section = document.createElement("section");
    section.className = `llm-channel-group llm-channel-group--${channel}`;
    const heading = document.createElement("header");
    heading.innerHTML = `<span><small>${channel === "free" ? "FREE POOL" : "FAST POOL"}</small><strong>${llmChannelLabels[channel]} API 池</strong></span><em>${profiles.length} 套配置</em>`;
    const grid = document.createElement("div");
    grid.className = "llm-channel-profile-grid";
    if (profiles.length) {
      grid.replaceChildren(...profiles.map(llmCard));
    } else {
      grid.innerHTML = `<div class="llm-channel-empty"><strong>这条线路还没有 API</strong><span>点击“新增 LLM 配置”后选择${llmChannelLabels[channel]}。</span></div>`;
    }
    section.append(heading, grid);
    return section;
  }

  function renderLLM(payload) {
    llmState = payload;
    const enabled = Boolean(payload.notes_enabled);
    const masterEnabled = Boolean(payload.notes_master_enabled);
    const active = payload.active_profile;
    const master = document.querySelector("[data-llm-master]");
    master.classList.toggle("is-enabled", enabled);
    master.classList.toggle("has-route-error", masterEnabled && !payload.route_ready);
    document.querySelector("[data-llm-enabled-label]").textContent = enabled
      ? "笔记生成已开启"
      : masterEnabled
        ? "已开启，但当前线路不可用"
        : "笔记生成已暂停";
    document.querySelector("[data-llm-active-summary]").textContent = active
      ? `${llmChannelLabels[payload.active_channel]} / ${active.label}`
      : `${llmChannelLabels[payload.active_channel]}尚未选择默认模型`;
    document.querySelector("[data-llm-current]").textContent = active
      ? `${llmChannelLabels[payload.active_channel]}：${active.label} / ${llmModelDisplayName(active.model)}`
      : `${llmChannelLabels[payload.active_channel]}尚未选择模型`;
    const toggle = document.querySelector("[data-toggle-llm]");
    toggle.textContent = masterEnabled ? "暂停笔记生成" : "开启笔记生成";
    toggle.disabled = !masterEnabled && !payload.route_ready;
    const channelBoard = document.querySelector("[data-llm-channel-board]");
    channelBoard.replaceChildren(llmChannelCard("free"), llmChannelCard("paid"));
    const listNode = document.querySelector("[data-llm-list]");
    listNode.replaceChildren(
      llmChannelGroup("free", payload.profiles.filter((profile) => profile.channel === "free")),
      llmChannelGroup("paid", payload.profiles.filter((profile) => profile.channel === "paid")),
    );
    document.querySelector("[data-llm-empty]").hidden = payload.profiles.length !== 0;
  }

  async function loadLLM() {
    renderLLM(await api("/api/llm-providers"));
  }

  function resetLLMModelPicker() {
    const picker = document.querySelector("[data-llm-model-picker]");
    const manual = document.querySelector("[data-llm-model-manual-field]");
    const select = document.querySelector("[data-llm-model-select]");
    const status = document.querySelector("[data-llm-model-status]");
    picker.hidden = true;
    manual.hidden = false;
    select.replaceChildren();
    status.textContent = "正在读取代理的实时模型目录……";
    delete status.dataset.tone;
  }

  async function loadFreeLLMModels(profile = editingLLMProfile) {
    resetLLMModelPicker();
    if (!profile?.id || profile.channel !== "free") return;
    const picker = document.querySelector("[data-llm-model-picker]");
    const manual = document.querySelector("[data-llm-model-manual-field]");
    const select = document.querySelector("[data-llm-model-select]");
    const status = document.querySelector("[data-llm-model-status]");
    const refresh = document.querySelector("[data-llm-model-refresh]");
    picker.hidden = false;
    manual.hidden = true;
    refresh.disabled = true;
    status.textContent = "正在从本地 NVIDIA 代理读取实时模型目录……";
    try {
      const payload = await api(
        `/api/llm-providers/${encodeURIComponent(profile.id)}/models`,
      );
      if (editingLLMProfile?.id !== profile.id) return;
      const groups = new Map();
      payload.models.forEach((model) => {
        if (!groups.has(model.publisher)) groups.set(model.publisher, []);
        groups.get(model.publisher).push(model);
      });
      if (!payload.models.some((model) => model.id === profile.model)) {
        const unavailable = document.createElement("optgroup");
        unavailable.label = "当前配置｜目录未列出，可能已下线";
        const option = document.createElement("option");
        option.value = profile.model;
        option.textContent = llmModelDisplayName(profile.model);
        unavailable.append(option);
        select.append(unavailable);
      }
      groups.forEach((models, publisher) => {
        const group = document.createElement("optgroup");
        group.label = publisher.toUpperCase();
        models.forEach((model) => {
          const option = document.createElement("option");
          option.value = model.id;
          option.textContent = model.label;
          group.append(option);
        });
        select.append(group);
      });
      select.value = profile.model;
      document.querySelector("[data-llm-model]").value = select.value;
      status.textContent = `已读取 ${payload.count} 个可用模型与笔记模式；已过滤实时确认下线的模型。选择后保存时会发起真实请求，验证失败不会替换原模型。`;
      delete status.dataset.tone;
    } catch (error) {
      manual.hidden = false;
      picker.hidden = false;
      status.textContent = error.message;
      status.dataset.tone = "error";
    } finally {
      refresh.disabled = false;
    }
  }

  async function loadLLMSecret(profile = editingLLMProfile) {
    const keyInput = document.querySelector("[data-llm-api-key]");
    const toggle = document.querySelector("[data-toggle-llm-key]");
    const status = document.querySelector("[data-llm-key-status]");
    loadedLLMSecret = "";
    keyInput.value = "";
    keyInput.classList.remove("is-secret-visible");
    toggle.textContent = "显示";
    delete status.dataset.tone;
    if (!profile?.api_key_saved) {
      toggle.disabled = false;
      status.textContent = "首次配置时请填写密钥；输入内容默认隐藏。";
      return;
    }
    toggle.disabled = true;
    status.textContent = "正在从这台电脑读取已保存密钥……";
    try {
      const payload = await api(
        `/api/llm-providers/${encodeURIComponent(profile.id)}/reveal-key`,
        { method: "POST" },
      );
      if (editingLLMProfile?.id !== profile.id) return;
      loadedLLMSecret = payload.api_key;
      keyInput.value = payload.api_key;
      status.textContent = "已填入本地保存的密钥；默认以圆点隐藏。";
    } catch (error) {
      keyInput.value = "";
      status.textContent = error.message;
      status.dataset.tone = "error";
    } finally {
      toggle.disabled = false;
    }
  }

  function openLLMForm(profile = null) {
    editingLLMProfile = profile;
    document.querySelector("[data-llm-dialog-title]");
    document.getElementById("llm-dialog-title").textContent = profile
      ? "编辑 LLM 配置"
      : "新增 LLM 配置";
    document.querySelector("[data-llm-label]").value = profile?.label || "";
    document.querySelector("[data-llm-api-base]").value = profile?.api_base || "";
    document.querySelector("[data-llm-channel]").value = profile?.channel || "paid";
    document.querySelector("[data-llm-protocol]").value = profile?.protocol || "openai_chat";
    document.querySelector("[data-llm-profile-enabled]").checked = profile?.enabled ?? true;
    const keyInput = document.querySelector("[data-llm-api-key]");
    keyInput.value = "";
    keyInput.classList.remove("is-secret-visible");
    keyInput.placeholder = profile?.api_key_saved
      ? "正在读取已保存密钥"
      : "首次配置时必须填写";
    document.querySelector("[data-llm-model]").value = profile?.model || "";
    resetLLMModelPicker();
    document.querySelector("[data-toggle-llm-key]").textContent = "显示";
    document.querySelector("[data-llm-error]").hidden = true;
    llmDialog.showModal();
    document.querySelector("[data-llm-label]").focus();
    loadLLMSecret(profile);
    loadFreeLLMModels(profile);
  }

  function closeLLMForm() {
    editingLLMProfile = null;
    loadedLLMSecret = "";
    if (llmDialog.open) llmDialog.close();
    llmForm.reset();
    resetLLMModelPicker();
  }

  async function switchLLMChannel(channel, button) {
    setLLMMessage("");
    button.disabled = true;
    button.textContent = "正在切换…";
    try {
      const payload = await api("/api/llm-providers/active-channel", {
        method: "PUT",
        body: JSON.stringify({ channel }),
      });
      renderLLM(payload);
      setLLMMessage(`已将${llmChannelLabels[channel]}设为兼容旧任务的默认线路。用户主动选择线路时仍以用户选择为准。`);
    } catch (error) {
      setLLMMessage(error.message, "error");
      button.disabled = false;
      button.textContent = "设为兼容默认线路";
    }
  }

  async function toggleLLMChannel(channel, enabled, button) {
    setLLMMessage("");
    button.disabled = true;
    try {
      const payload = await api(`/api/llm-providers/channels/${channel}/enabled`, {
        method: "PUT",
        body: JSON.stringify({ enabled }),
      });
      renderLLM(payload);
      setLLMMessage(`${llmChannelLabels[channel]}已${enabled ? "开启" : "关闭"}。另一条线路不受影响。`);
    } catch (error) {
      setLLMMessage(error.message, "error");
      button.disabled = false;
    }
  }

  async function setDefaultLLMProfile(profile, button) {
    setLLMMessage("");
    button.disabled = true;
    try {
      const payload = await api(
        `/api/llm-providers/${encodeURIComponent(profile.id)}/default`,
        { method: "POST" },
      );
      renderLLM(payload);
      setLLMMessage(`${profile.label} 已设为${llmChannelLabels[profile.channel]}的默认模型。`);
    } catch (error) {
      setLLMMessage(error.message, "error");
      button.disabled = false;
      button.textContent = "设为该线路默认";
    }
  }

  async function toggleLLMProfile(profile, button) {
    setLLMMessage("");
    button.disabled = true;
    try {
      const payload = await api(
        `/api/llm-providers/${encodeURIComponent(profile.id)}/enabled`,
        {
          method: "PUT",
          body: JSON.stringify({ enabled: !profile.enabled }),
        },
      );
      renderLLM(payload);
      setLLMMessage(`${profile.label} 已${profile.enabled ? "关闭" : "开启"}；配置和密钥仍然保留。`);
    } catch (error) {
      setLLMMessage(error.message, "error");
      button.disabled = false;
    }
  }

  async function testLLMProfile(profile, button) {
    setLLMMessage("");
    button.disabled = true;
    button.textContent = "正在发起最小请求…";
    try {
      const payload = await api(
        `/api/llm-providers/${encodeURIComponent(profile.id)}/test`,
        { method: "POST" },
      );
      renderLLM(payload);
      setLLMMessage(`${profile.label} 连接测试成功，当前密钥和模型可用。`);
    } catch (error) {
      setLLMMessage(error.message, "error");
      button.disabled = false;
      button.textContent = "测试连接";
    }
  }

  function openLLMDelete(profile) {
    deletingLLMProfile = profile;
    document.querySelector("[data-llm-delete-label]").textContent = profile.label;
    document.querySelector("[data-llm-delete-error]").hidden = true;
    llmDeleteDialog.showModal();
  }

  async function setLLMEnabled(enabled, button) {
    button.disabled = true;
    try {
      const payload = await api("/api/llm-providers/notes-enabled", {
        method: "PUT",
        body: JSON.stringify({ enabled }),
      });
      renderLLM(payload);
      setLLMMessage(
        enabled
          ? "笔记生成已开启。之后的新任务会调用当前 LLM。"
          : "笔记生成已暂停。视频解析仍可正常使用。",
      );
      if (llmEnableDialog.open) llmEnableDialog.close();
    } catch (error) {
      if (llmEnableDialog.open) {
        const errorNode = document.querySelector("[data-llm-enable-error]");
        errorNode.textContent = error.message;
        errorNode.hidden = false;
      } else {
        setLLMMessage(error.message, "error");
      }
    } finally {
      button.disabled = false;
    }
  }

  function openCloudflareCredentials() {
    const accountInput = document.querySelector(
      "[data-cloudflare-account-input]"
    );
    const tokenInput = document.querySelector("[data-cloudflare-token-input]");
    accountInput.value = providerState?.cloudflare?.account_id || "";
    tokenInput.value = "";
    tokenInput.type = "password";
    tokenInput.placeholder = providerState?.cloudflare?.token_saved
      ? "已保存；留空则不修改"
      : "首次配置时必须填写";
    document.querySelector("[data-toggle-cloudflare-token]").textContent = "显示";
    document.querySelector("[data-cloudflare-error]").hidden = true;
    cloudflareDialog.showModal();
    accountInput.focus();
  }

  function closeCloudflareCredentials() {
    if (cloudflareDialog.open) cloudflareDialog.close();
    cloudflareForm.reset();
  }

  async function switchProvider(provider, button) {
    setProviderMessage("");
    button.disabled = true;
    const previousText = button.textContent;
    button.textContent = "正在验证并切换…";
    try {
      const payload = await api("/api/transcription-provider/switch", {
        method: "POST",
        body: JSON.stringify({ provider }),
      });
      renderProvider(payload);
      setProviderMessage(
        provider === "local"
          ? "已切换到本地 tiny。下一次视频解析会直接使用本地模型。"
          : "已切换到 Cloudflare。下一次视频解析会调用 Workers AI。",
      );
    } catch (error) {
      setProviderMessage(error.message, "error");
      button.disabled = false;
      button.textContent = previousText;
    }
  }

  function showError(message) {
    formError.textContent = message;
    formError.hidden = false;
  }

  function clearResult() {
    currentCode = "";
    codeNode.textContent = "";
    qrNode.replaceChildren();
    copyButton.textContent = "复制内测码";
    copyButton.classList.remove("is-copied");
  }

  function closeResult() {
    if (resultDialog.open) resultDialog.close();
    clearResult();
  }

  function openRevoke(grant) {
    pendingRevokeId = grant.id;
    document.querySelector("[data-revoke-label]").textContent = grant.label;
    revokeDialog.showModal();
  }

  async function copyText(value) {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      const input = document.createElement("textarea");
      input.value = value;
      input.style.position = "fixed";
      input.style.opacity = "0";
      document.body.append(input);
      input.select();
      document.execCommand("copy");
      input.remove();
    }
  }

  async function openImport(grant) {
    pendingImportGrant = grant;
    document.querySelector("[data-import-label]").textContent = grant.label;
    const input = document.querySelector("[data-import-code]");
    const error = document.querySelector("[data-import-error]");
    input.value = "";
    error.hidden = true;
    try {
      const clipboardCode = (await navigator.clipboard.readText()).trim();
      if (clipboardCode.startsWith("VTN-")) input.value = clipboardCode;
    } catch {
      // Clipboard permission is optional; the user can always paste manually.
    }
    importDialog.showModal();
    input.focus();
  }

  function formatInputNumber(value) {
    return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(1)));
  }

  function editValues() {
    return {
      label: document.querySelector("[data-edit-label]").value.trim(),
      remainingTranscription: Number(
        document.querySelector("[data-edit-transcription]").value
      ),
      remainingNotes: Number(document.querySelector("[data-edit-notes]").value),
      maxVideo: Number(document.querySelector("[data-edit-max-video]").value),
    };
  }

  function updateEditPreview() {
    if (!pendingEditGrant) return;
    const values = editValues();
    document.querySelector("[data-preview-transcription]").textContent =
      `${formatNumber(pendingEditGrant.remaining_transcription_minutes)} → ${formatNumber(values.remainingTranscription)}`;
    document.querySelector("[data-preview-notes]").textContent =
      `${formatNumber(pendingEditGrant.remaining_note_generations)} → ${formatNumber(values.remainingNotes)}`;
    document.querySelector("[data-preview-max-video]").textContent =
      `${formatNumber(pendingEditGrant.max_video_minutes)} → ${formatNumber(values.maxVideo)}`;
    document.querySelector("[data-edit-warning]").hidden =
      !Number.isFinite(values.maxVideo) ||
      !Number.isFinite(values.remainingTranscription) ||
      values.maxVideo <= values.remainingTranscription;
  }

  function openEdit(grant) {
    pendingEditGrant = grant;
    document.querySelector("[data-edit-label]").value = grant.label;
    document.querySelector("[data-edit-transcription]").value =
      formatInputNumber(grant.remaining_transcription_minutes);
    document.querySelector("[data-edit-notes]").value =
      formatInputNumber(grant.remaining_note_generations);
    document.querySelector("[data-edit-max-video]").value =
      formatInputNumber(grant.max_video_minutes);
    document.querySelector("[data-edit-error]").hidden = true;
    updateEditPreview();
    editDialog.showModal();
  }

  function closeEdit() {
    pendingEditGrant = null;
    if (editDialog.open) editDialog.close();
  }

  document.querySelectorAll("[data-preset]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-preset]").forEach((item) => {
        item.classList.toggle("is-selected", item === button);
      });
      const presets = {
        light: [30, 1, 20],
        deep: [120, 3, 20],
      };
      const values = presets[button.dataset.preset];
      if (!values) {
        form.elements.transcription_minutes.focus();
        return;
      }
      form.elements.transcription_minutes.value = values[0];
      form.elements.note_generations.value = values[1];
      form.elements.max_video_minutes.value = values[2];
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    try {
      const payload = await api("/api/grants", {
        method: "POST",
        body: JSON.stringify({
          label: form.elements.label.value,
          transcription_minutes: Number(form.elements.transcription_minutes.value),
          note_generations: Number(form.elements.note_generations.value),
          max_video_minutes: Number(form.elements.max_video_minutes.value),
        }),
      });
      currentCode = payload.invite_code;
      rememberLocalCode(payload.grant.id, currentCode);
      codeNode.textContent = currentCode;
      qrNode.innerHTML = payload.qr_svg;
      resultDialog.showModal();
      form.reset();
      form.elements.transcription_minutes.value = 30;
      form.elements.note_generations.value = 1;
      form.elements.max_video_minutes.value = 20;
      document.querySelectorAll("[data-preset]").forEach((item) => item.classList.remove("is-selected"));
      await loadGrants();
    } catch (error) {
      showError(error.message);
    } finally {
      submit.disabled = false;
    }
  });

  copyButton.addEventListener("click", async () => {
    if (!currentCode) return;
    await copyText(currentCode);
    copyButton.textContent = "已复制";
    copyButton.classList.add("is-copied");
  });

  document.querySelector("[data-result-complete]").addEventListener("click", closeResult);
  document.querySelector("[data-result-close]").addEventListener("click", closeResult);
  resultDialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeResult();
  });

  document.querySelector("[data-revoke-cancel]").addEventListener("click", () => {
    pendingRevokeId = "";
    revokeDialog.close();
  });
  document.querySelector("[data-revoke-confirm]").addEventListener("click", async () => {
    if (!pendingRevokeId) return;
    const button = document.querySelector("[data-revoke-confirm]");
    button.disabled = true;
    try {
      await api(`/api/grants/${encodeURIComponent(pendingRevokeId)}`, { method: "DELETE" });
      forgetLocalCode(pendingRevokeId);
      pendingRevokeId = "";
      revokeDialog.close();
      await loadGrants();
    } catch (error) {
      window.alert(error.message);
    } finally {
      button.disabled = false;
    }
  });
  revokeDialog.addEventListener("cancel", () => {
    pendingRevokeId = "";
  });

  document.querySelector("[data-import-cancel]").addEventListener("click", () => {
    pendingImportGrant = null;
    importDialog.close();
  });
  document.querySelector("[data-import-confirm]").addEventListener("click", async () => {
    if (!pendingImportGrant) return;
    const input = document.querySelector("[data-import-code]");
    const error = document.querySelector("[data-import-error]");
    const button = document.querySelector("[data-import-confirm]");
    const inviteCode = input.value.trim();
    error.hidden = true;
    button.disabled = true;
    try {
      await api(
        `/api/grants/${encodeURIComponent(pendingImportGrant.id)}/verify-code`,
        {
          method: "POST",
          body: JSON.stringify({ invite_code: inviteCode }),
        }
      );
      rememberLocalCode(pendingImportGrant.id, inviteCode);
      pendingImportGrant = null;
      importDialog.close();
      await loadGrants();
    } catch (importError) {
      error.textContent = importError.message;
      error.hidden = false;
    } finally {
      button.disabled = false;
    }
  });
  importDialog.addEventListener("cancel", () => {
    pendingImportGrant = null;
  });

  editDialog.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", updateEditPreview);
  });
  document.querySelector("[data-edit-cancel]").addEventListener("click", closeEdit);
  document.querySelector("[data-edit-close]").addEventListener("click", closeEdit);
  editDialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeEdit();
  });
  document.querySelector("[data-edit-save]").addEventListener("click", async () => {
    if (!pendingEditGrant) return;
    const error = document.querySelector("[data-edit-error]");
    const button = document.querySelector("[data-edit-save]");
    const values = editValues();
    error.hidden = true;
    button.disabled = true;
    try {
      await api(`/api/grants/${encodeURIComponent(pendingEditGrant.id)}`, {
        method: "PATCH",
        body: JSON.stringify({
          label: values.label,
          remaining_transcription_minutes: values.remainingTranscription,
          remaining_note_generations: values.remainingNotes,
          max_video_minutes: values.maxVideo,
        }),
      });
      closeEdit();
      await loadGrants();
    } catch (editError) {
      error.textContent = editError.message;
      error.hidden = false;
    } finally {
      button.disabled = false;
    }
  });

  document.querySelector("[data-refresh]").addEventListener("click", () => {
    Promise.all([loadGrants(), loadProvider(), loadLLM()]).catch((error) =>
      setProviderMessage(error.message, "error")
    );
  });

  document.querySelector("[data-add-llm]").addEventListener("click", () => {
    openLLMForm();
  });
  document.querySelector("[data-llm-close]").addEventListener("click", closeLLMForm);
  document.querySelector("[data-llm-cancel]").addEventListener("click", closeLLMForm);
  llmDialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeLLMForm();
  });
  document.querySelectorAll("[data-llm-preset]").forEach((button) => {
    button.addEventListener("click", () => {
      const presets = {
        fcc: {
          apiBase: "http://127.0.0.1:8082",
          model: "claude-sonnet-4-5",
          channel: "free",
          protocol: "anthropic_messages",
        },
        nvidia: {
          apiBase: "https://integrate.api.nvidia.com/v1",
          model: "deepseek-ai/deepseek-v4-pro",
          channel: "free",
          protocol: "openai_chat",
        },
        deepseek: {
          apiBase: "https://api.deepseek.com",
          model: "deepseek-v4-pro",
          channel: "paid",
          protocol: "openai_chat",
        },
        openrouter: {
          apiBase: "https://openrouter.ai/api/v1",
          model: "openai/gpt-4.1-mini",
          channel: "paid",
          protocol: "openai_chat",
        },
        custom: { apiBase: "", model: "", channel: "paid", protocol: "openai_chat" },
      };
      const preset = presets[button.dataset.llmPreset];
      document.querySelector("[data-llm-api-base]").value = preset.apiBase;
      document.querySelector("[data-llm-model]").value = preset.model;
      document.querySelector("[data-llm-channel]").value = preset.channel;
      document.querySelector("[data-llm-protocol]").value = preset.protocol;
      if (!document.querySelector("[data-llm-label]").value) {
        document.querySelector("[data-llm-label]").value = button.textContent.trim();
      }
      loadFreeLLMModels();
    });
  });
  document.querySelector("[data-toggle-llm-key]").addEventListener("click", (event) => {
    const input = document.querySelector("[data-llm-api-key]");
    const willShow = !input.classList.contains("is-secret-visible");
    input.classList.toggle("is-secret-visible", willShow);
    event.currentTarget.textContent = willShow ? "隐藏" : "显示";
  });
  document.querySelector("[data-llm-model-select]").addEventListener("change", (event) => {
    document.querySelector("[data-llm-model]").value = event.currentTarget.value;
  });
  document.querySelector("[data-llm-model-refresh]").addEventListener("click", () => {
    loadFreeLLMModels();
  });
  document.querySelector("[data-llm-channel]").addEventListener("change", (event) => {
    if (editingLLMProfile) {
      editingLLMProfile = { ...editingLLMProfile, channel: event.currentTarget.value };
    }
    loadFreeLLMModels();
  });
  llmForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorNode = document.querySelector("[data-llm-error]");
    const saveButton = document.querySelector("[data-llm-save]");
    errorNode.hidden = true;
    saveButton.disabled = true;
    saveButton.textContent = "正在安全保存…";
    try {
      const profileId = editingLLMProfile?.id;
      const keyInput = document.querySelector("[data-llm-api-key]");
      const enteredKey = keyInput.value.trim();
      const apiKey = enteredKey === loadedLLMSecret ? "" : enteredKey;
      const selectedModel = document.querySelector("[data-llm-model]").value.trim();
      const channel = document.querySelector("[data-llm-channel]").value;
      let modelVerified = false;
      if (
        profileId &&
        channel === "free" &&
        selectedModel !== editingLLMProfile.model
      ) {
        saveButton.textContent = "正在真实验证所选模型…";
        const verified = await api(
          `/api/llm-providers/${encodeURIComponent(profileId)}/model`,
          {
            method: "PUT",
            body: JSON.stringify({ model: selectedModel }),
          },
        );
        modelVerified = true;
        editingLLMProfile = verified.profile;
      }
      saveButton.textContent = "正在安全保存…";
      const payload = await api(
        profileId
          ? `/api/llm-providers/${encodeURIComponent(profileId)}`
          : "/api/llm-providers",
        {
          method: profileId ? "PUT" : "POST",
          body: JSON.stringify({
            label: document.querySelector("[data-llm-label]").value.trim(),
            api_base: document.querySelector("[data-llm-api-base]").value.trim(),
            api_key: apiKey,
            model: selectedModel,
            channel,
            protocol: document.querySelector("[data-llm-protocol]").value,
            enabled: document.querySelector("[data-llm-profile-enabled]").checked,
          }),
        },
      );
      renderLLM(payload);
      const wasEditing = Boolean(profileId);
      closeLLMForm();
      setLLMMessage(
        modelVerified
          ? `已真实验证并切换到 ${llmModelDisplayName(selectedModel)}；之后的新笔记会使用这个模式。`
          : wasEditing
          ? "LLM 配置已更新；密钥未在页面中回显。"
          : "LLM 配置已保存。你可以先测试连接，再按需设为当前使用。",
      );
    } catch (error) {
      errorNode.textContent = error.message;
      errorNode.hidden = false;
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = "保存配置";
    }
  });
  document.querySelector("[data-toggle-llm]").addEventListener("click", (event) => {
    if (llmState?.notes_master_enabled) {
      setLLMEnabled(false, event.currentTarget);
      return;
    }
    const active = llmState?.active_profile;
    if (!active) return;
    document.querySelector("[data-llm-enable-preview]").textContent =
      `${llmChannelLabels[llmState.active_channel]} / ${active.label} / ${llmModelDisplayName(active.model)}`;
    document.querySelector("[data-llm-enable-copy]").textContent =
      llmState.active_channel === "free"
        ? "已设为兼容旧任务的默认线路。用户主动选择免费线路时，长内容可能等待更久，但不消耗高速次数。"
        : "已设为兼容旧任务的默认线路。用户主动选择高速线路时，会消耗邀请码的高速体验次数。";
    document.querySelector("[data-llm-enable-error]").hidden = true;
    llmEnableDialog.showModal();
  });
  document.querySelector("[data-llm-enable-cancel]").addEventListener("click", () => {
    llmEnableDialog.close();
  });
  document.querySelector("[data-llm-enable-confirm]").addEventListener("click", (event) => {
    setLLMEnabled(true, event.currentTarget);
  });
  llmEnableDialog.addEventListener("cancel", () => {
    document.querySelector("[data-llm-enable-error]").hidden = true;
  });
  document.querySelector("[data-llm-delete-cancel]").addEventListener("click", () => {
    deletingLLMProfile = null;
    llmDeleteDialog.close();
  });
  document.querySelector("[data-llm-delete-confirm]").addEventListener("click", async (event) => {
    if (!deletingLLMProfile) return;
    const errorNode = document.querySelector("[data-llm-delete-error]");
    const button = event.currentTarget;
    errorNode.hidden = true;
    button.disabled = true;
    try {
      const label = deletingLLMProfile.label;
      const payload = await api(
        `/api/llm-providers/${encodeURIComponent(deletingLLMProfile.id)}`,
        { method: "DELETE" },
      );
      deletingLLMProfile = null;
      renderLLM(payload);
      llmDeleteDialog.close();
      setLLMMessage(`${label} 已删除。若它原本正在使用，笔记生成已安全暂停。`);
    } catch (error) {
      errorNode.textContent = error.message;
      errorNode.hidden = false;
    } finally {
      button.disabled = false;
    }
  });

  document
    .querySelector("[data-open-cloudflare]")
    .addEventListener("click", openCloudflareCredentials);
  document
    .querySelector("[data-cloudflare-close]")
    .addEventListener("click", closeCloudflareCredentials);
  document
    .querySelector("[data-cloudflare-cancel]")
    .addEventListener("click", closeCloudflareCredentials);
  cloudflareDialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeCloudflareCredentials();
  });
  document
    .querySelector("[data-toggle-cloudflare-token]")
    .addEventListener("click", (event) => {
      const input = document.querySelector("[data-cloudflare-token-input]");
      const willShow = input.type === "password";
      input.type = willShow ? "text" : "password";
      event.currentTarget.textContent = willShow ? "隐藏" : "显示";
    });
  cloudflareForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorNode = document.querySelector("[data-cloudflare-error]");
    const saveButton = document.querySelector("[data-cloudflare-save]");
    errorNode.hidden = true;
    saveButton.disabled = true;
    saveButton.textContent = "正在验证…";
    try {
      const payload = await api("/api/transcription-provider/cloudflare", {
        method: "PUT",
        body: JSON.stringify({
          account_id: document
            .querySelector("[data-cloudflare-account-input]")
            .value.trim(),
          api_token: document
            .querySelector("[data-cloudflare-token-input]")
            .value.trim(),
        }),
      });
      renderProvider(payload);
      closeCloudflareCredentials();
      setProviderMessage(
        "Cloudflare 凭证已验证并保存。当前线路没有改变，你可以按需切换。",
      );
    } catch (error) {
      errorNode.textContent = error.message;
      errorNode.hidden = false;
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = "验证并保存";
    }
  });
  document
    .querySelector("[data-switch-local]")
    .addEventListener("click", (event) =>
      switchProvider("local", event.currentTarget)
    );
  document
    .querySelector("[data-switch-cloudflare]")
    .addEventListener("click", (event) =>
      switchProvider("cloudflare", event.currentTarget)
    );
  document
    .querySelector("[data-delete-cloudflare]")
    .addEventListener("click", () => {
      document.querySelector("[data-cloudflare-delete-error]").hidden = true;
      cloudflareDeleteDialog.showModal();
    });
  document
    .querySelector("[data-cloudflare-delete-cancel]")
    .addEventListener("click", () => cloudflareDeleteDialog.close());
  document
    .querySelector("[data-cloudflare-delete-confirm]")
    .addEventListener("click", async (event) => {
      const errorNode = document.querySelector(
        "[data-cloudflare-delete-error]"
      );
      const button = event.currentTarget;
      errorNode.hidden = true;
      button.disabled = true;
      try {
        const payload = await api(
          "/api/transcription-provider/cloudflare",
          { method: "DELETE" },
        );
        renderProvider(payload);
        cloudflareDeleteDialog.close();
        setProviderMessage(
          "Cloudflare 凭证已删除，转录线路已安全回到本地 tiny。",
        );
      } catch (error) {
        errorNode.textContent = error.message;
        errorNode.hidden = false;
      } finally {
        button.disabled = false;
      }
    });
  cloudflareDeleteDialog.addEventListener("cancel", () => {
    document.querySelector("[data-cloudflare-delete-error]").hidden = true;
  });

  Promise.all([loadGrants(), loadProvider(), loadLLM()]).catch((error) => {
    showError(error.message);
    setProviderMessage(error.message, "error");
    setLLMMessage(error.message, "error");
  });
})();
