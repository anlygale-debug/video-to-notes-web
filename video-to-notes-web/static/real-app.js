(() => {
  const acceptance = new URLSearchParams(location.search).get("acceptance") === "1";
  if (acceptance) {
    document.body.classList.add("acceptance-mode");
    return;
  }

  const state = {
    deviceId: localStorage.getItem("vtn-device-id") || crypto.randomUUID(),
    parserTask: null,
    parserRecord: null,
    noteTask: null,
    note: null,
    regenerateFromNote: null,
    candidate: null,
    inputTranscript: "",
    uploadedTranscript: null,
    noteRequestText: "",
    selectedGenerationRoute: null,
    noteGeneration: { enabled: false, routes: {} },
    sourceMode: "independent",
    saveTimer: null,
    pendingTitle: "",
    parserHistoryCursor: null,
    noteHistoryCursor: null,
    recoveryCursor: null,
    parserHistoryIds: new Set(),
    noteHistoryIds: new Set(),
    recoveryTaskIds: new Set(),
    parserSubmitting: false,
    parserPollToken: 0,
    notePollToken: 0,
    noteWorkspaceToken: 0,
    integrityRecheckAvailable: false,
    accessControlEnabled: false,
    access: null,
    transcriptionProviders: { local: true, cloudflare: true },
  };
  localStorage.setItem("vtn-device-id", state.deviceId);

  function withDeviceId(path) {
    const separator = path.includes("?") ? "&" : "?";
    return `${path}${separator}device_id=${encodeURIComponent(state.deviceId)}`;
  }

  function transcriptCharacterCount(value) {
    return Array.from(String(value || "").trim()).length;
  }

  function bindFreeCapacityNotices({
    host = document,
    transcript = state.inputTranscript,
    durationSeconds = null,
  } = {}) {
    if (!window.VTNFreeCapacity) return null;
    const assessment = window.VTNFreeCapacity.assess({ transcript, durationSeconds });
    host.querySelectorAll("[data-free-capacity]").forEach((notice) => {
      notice.dataset.freeCapacityLevel = assessment.level;
      const title = notice.querySelector("[data-free-capacity-title]");
      const copy = notice.querySelector("[data-free-capacity-copy]");
      const facts = notice.querySelector("[data-free-capacity-facts]");
      const chip = notice.querySelector("[data-free-capacity-chip]");
      if (title) title.textContent = assessment.title;
      if (copy) copy.textContent = assessment.copy;
      if (facts) facts.textContent = assessment.facts
        ? `本次：${assessment.facts}｜免费线路较稳定范围：30 分钟且约 9,000 字以内`
        : "";
      if (chip) chip.textContent = assessment.chip;
    });
    return assessment;
  }

  function bindTranscriptReady() {
    const characterCount = transcriptCharacterCount(state.inputTranscript).toLocaleString("zh-CN");
    const summary = notesStateHost.querySelector("[data-ready-source-summary]");
    const fileType = notesStateHost.querySelector("[data-ready-file-type]");
    const fileName = notesStateHost.querySelector("[data-ready-file-name]");
    const fileMeta = notesStateHost.querySelector("[data-ready-file-meta]");
    const requestInput = notesStateHost.querySelector("#ready-request-input");
    let sourceLabel = "直接粘贴";
    let typeLabel = "TXT";
    let displayName = "粘贴的逐字稿.txt";
    if (state.sourceMode === "linked" && state.parserRecord) {
      sourceLabel = `${state.parserRecord.platform || "视频"}解析`;
      displayName = `${state.parserRecord.title || "视频"} — 逐字稿.md`;
      typeLabel = "VIDEO";
    } else if (state.uploadedTranscript) {
      sourceLabel = "文件上传";
      displayName = state.uploadedTranscript.name;
      typeLabel = state.uploadedTranscript.extension.toUpperCase();
    }
    if (summary) summary.textContent = `来源 / ${sourceLabel} // ${characterCount} 字`;
    if (fileType) fileType.textContent = `${typeLabel} / 01`;
    if (fileName) fileName.textContent = displayName;
    if (fileMeta) fileMeta.textContent = `${characterCount} 字 · UTF-8 · 已读取`;
    if (requestInput) requestInput.value = state.noteRequestText;
    bindFreeCapacityNotices({ host: notesStateHost, transcript: state.inputTranscript });
    bindNoteGenerationChooser();
  }

  function highSpeedRemaining() {
    return state.access?.remaining_high_speed_generations
      ?? state.access?.remaining_note_generations
      ?? null;
  }

  function bindNoteGenerationChooser() {
    const host = notesStateHost.querySelector("[data-note-route-host]");
    if (!host) return;
    const routes = state.noteGeneration?.routes || {};
    const remaining = highSpeedRemaining();
    ["free", "paid"].forEach((routeId) => {
      const button = host.querySelector(`[data-select-note-route="${routeId}"]`);
      const status = host.querySelector(`[data-route-status="${routeId}"]`);
      if (!button || !status) return;
      const route = routes[routeId] || {};
      const needsAccess = routeId === "paid" && state.accessControlEnabled && !state.access;
      const exhausted = routeId === "paid" && remaining !== null && remaining <= 0;
      const available = route.available === true && !exhausted;
      button.disabled = !available;
      button.classList.toggle("is-selected", state.selectedGenerationRoute === routeId);
      if (needsAccess) status.textContent = "输入内测码后可使用";
      else if (exhausted) status.textContent = "高速体验次数已用完";
      else if (route.available === true) status.textContent = route.description || "当前可用";
      else status.textContent = route.description || "当前线路未开放";
    });
    const remainingNode = host.querySelector("[data-high-speed-remaining]");
    if (remainingNode) {
      remainingNode.textContent = remaining === null ? "" : ` · 剩余 ${remaining} 次`;
    }
    const contact = host.querySelector("[data-route-contact-note]");
    if (contact) contact.hidden = !(remaining !== null && remaining <= 0);
    bindRouteConfirmation();
  }

  function bindRouteConfirmation() {
    const panel = notesStateHost.querySelector("[data-note-route-confirmation]");
    if (!panel) return;
    const routeId = state.selectedGenerationRoute;
    panel.hidden = !routeId;
    if (!routeId) return;
    const label = panel.querySelector("[data-route-confirmation-label]");
    const title = panel.querySelector("[data-route-confirmation-title]");
    const copy = panel.querySelector("[data-route-confirmation-copy]");
    const confirm = panel.querySelector("[data-confirm-note-route]");
    if (routeId === "free") {
      if (label) label.textContent = "FREE LINE // 已选择";
      if (title) title.textContent = "使用免费线路，不消耗高速次数";
      if (copy) copy.textContent = "生成可能需要数分钟或更久，也可能因免费服务波动失败。任务创建后可以离开页面，稍后从“恢复任务”继续。";
      if (confirm) confirm.textContent = "确认使用免费线路 →";
    } else {
      if (label) label.textContent = "HIGH SPEED // 已选择";
      if (title) title.textContent = "使用 1 次高速体验";
      if (copy) copy.textContent = "创建任务会占用 1 次高速体验；若模型调用失败，系统会自动退回本次额度。";
      if (confirm) confirm.textContent = "确认使用高速体验线路 →";
    }
  }

  async function request(path, options = {}) {
    const { timeoutMs = 15_000, timeoutLabel = "请求", ...fetchOptions } = options;
    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
    try {
      const response = await fetch(path, {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "X-VTN-Device-ID": state.deviceId,
          ...(fetchOptions.headers || {}),
        },
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const error = new Error(payload.error?.message || `请求失败（${response.status}）`);
        error.code = payload.error?.code || "HTTP_REQUEST_FAILED";
        error.status = response.status;
        if (response.status === 401 && error.code === "ACCESS_REQUIRED") {
          showAccessDialog(error.message);
        }
        throw error;
      }
      if (response.status === 204) return null;
      return await response.json();
    } catch (error) {
      if (!timedOut) throw error;
      const timeoutError = new Error(`${timeoutLabel} ${Math.round(timeoutMs / 1000)} 秒内没有响应，已停止等待。`);
      timeoutError.code = "REQUEST_TIMEOUT";
      throw timeoutError;
    } finally {
      clearTimeout(timer);
    }
  }

  function formatMinutes(seconds) {
    if (seconds === null || seconds === undefined) return "不限";
    return `${Math.ceil(seconds / 60)} 分钟`;
  }

  function bindAccess(access) {
    state.access = access || null;
    const button = document.querySelector("[data-open-access]");
    const label = document.querySelector("[data-access-label]");
    const quota = document.querySelector("[data-access-quota]");
    if (!button || !state.accessControlEnabled) return;
    button.hidden = false;
    button.classList.toggle("is-authenticated", Boolean(access));
    label.textContent = access?.label || "免费使用";
    quota.textContent = access
      ? `转录 ${formatMinutes(access.remaining_transcription_seconds)} · 高速 ${access.remaining_high_speed_generations ?? access.remaining_note_generations ?? "不限"} 次`
      : "输入内测码，解锁高速线路";
    bindNoteGenerationChooser();
    if (state.parserRecord) bindParserRecord();
  }

  function showAccessDialog(message = "") {
    const dialog = document.querySelector("#access-dialog");
    if (!dialog) return;
    const error = dialog.querySelector("[data-access-error]");
    error.textContent = message;
    error.hidden = !message;
    if (!dialog.open) dialog.showModal();
    setTimeout(() => dialog.querySelector("input[name=access-code]")?.focus(), 0);
  }

  async function refreshAccessStatus() {
    const response = await fetch("/api/v3/access/status");
    if (response.status === 404) {
      state.accessControlEnabled = false;
      return false;
    }
    if (!response.ok) return false;
    const payload = await response.json();
    if (payload.enabled === false) {
      state.accessControlEnabled = false;
      return false;
    }
    state.accessControlEnabled = true;
    bindAccess(payload.authenticated ? payload.access : null);
    return payload.authenticated === true;
  }

  document.querySelector("[data-access-form]")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type=submit]");
    const error = form.querySelector("[data-access-error]");
    button.disabled = true;
    error.hidden = true;
    try {
      const response = await fetch("/api/v3/access/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: form.elements["access-code"].value.trim() }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error?.message || "内测码验证失败");
      bindAccess(payload.access);
      form.reset();
      document.querySelector("#access-dialog")?.close();
    } catch (loginError) {
      error.textContent = loginError.message;
      error.hidden = false;
    } finally {
      button.disabled = false;
    }
  });

  document.querySelector("[data-open-access]")?.addEventListener("click", () => {
    if (!state.access) showAccessDialog();
  });
  document.querySelector("[data-close-access]")?.addEventListener("click", () => {
    document.querySelector("#access-dialog")?.close();
  });

  const welcomeDialog = document.querySelector("#welcome-dialog");
  const welcomeVersion = "beta-2026-07-31-v1";
  const welcomeStorageKey = "vtn-welcome-version";

  function rememberWelcome() {
    localStorage.setItem(welcomeStorageKey, welcomeVersion);
  }

  function openWelcome() {
    if (!welcomeDialog || welcomeDialog.open) return;
    welcomeDialog.showModal();
    if (window.VTNMotion?.animateWelcome) {
      window.VTNMotion.animateWelcome(welcomeDialog, true);
    }
  }

  function closeWelcome(onClosed) {
    if (!welcomeDialog?.open) {
      onClosed?.();
      return;
    }
    rememberWelcome();
    const finish = () => {
      welcomeDialog.close();
      onClosed?.();
    };
    if (window.VTNMotion?.animateWelcome) {
      window.VTNMotion.animateWelcome(welcomeDialog, false, finish);
    } else {
      finish();
    }
  }

  document.querySelector("[data-open-welcome]")?.addEventListener("click", openWelcome);
  document.querySelectorAll("[data-welcome-dismiss]").forEach((button) => {
    button.addEventListener("click", () => closeWelcome());
  });
  document.querySelector("[data-welcome-demo]")?.addEventListener("click", () => {
    closeWelcome(() => document.querySelector(".nav-link--demo")?.click());
  });
  document.querySelectorAll("[data-open-public-demo]").forEach((button) => {
    button.addEventListener("click", rememberWelcome);
  });
  welcomeDialog?.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeWelcome();
  });
  welcomeDialog?.addEventListener("click", (event) => {
    if (event.target === welcomeDialog) closeWelcome();
  });

  window.setTimeout(() => {
    if (localStorage.getItem(welcomeStorageKey) === welcomeVersion) return;
    if (document.body.classList.contains("public-demo-active")) return;
    if (document.querySelector("dialog[open]")) return;
    openWelcome();
  }, 520);

  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");

  const detailLabels = { quick: "速查摘要", key: "要点提炼＋关键原话", complete: "完整详解" };
  const methodLabels = { direct: "一次性生成", outline: "先确认大纲" };
  const platformLabels = {
    bilibili: "Bilibili",
    xiaohongshu: "小红书",
    youtube: "YouTube",
    douyin: "抖音",
    other: "其他平台",
  };
  const platformLabel = (platform) => platformLabels[platform] || platform || "其他平台";
  const moduleLabels = {
    summary: "核心摘要", concepts: "关键概念",
    actions: "实践提炼", review_questions: "复习问题",
  };

  async function migrateLegacyHistory() {
    if (localStorage.getItem("vtn-v3-migration-complete") === "1") return;
    const readArray = (key) => {
      try {
        const value = JSON.parse(localStorage.getItem(key) || "[]");
        return Array.isArray(value) ? value : [];
      } catch {
        return [];
      }
    };
    await request("/api/v3/migrations/browser-history", {
      method: "POST",
      body: JSON.stringify({
        device_id: state.deviceId,
        transcripts: readArray("vtn-transcripts"),
        notes: readArray("vtn-history"),
      }),
    });
    localStorage.setItem("vtn-v3-migration-complete", "1");
  }

  async function detectCapabilities() {
    const response = await fetch("/api/v3/capabilities");
    if (!response.ok) return;
    const capabilities = await response.json();
    state.integrityRecheckAvailable = capabilities.integrity_recheck === true;
    state.noteGeneration = capabilities.note_generation || { enabled: false, routes: {} };
    if (capabilities.transcription_providers) {
      state.transcriptionProviders = {
        local: capabilities.transcription_providers.local !== false,
        cloudflare: capabilities.transcription_providers.cloudflare === true,
      };
      if (state.parserRecord) bindParserRecord();
    }
    if (notesStateHost.querySelector(".generation-complete-stack") && state.noteTask) {
      bindGenerationComplete(state.noteTask);
    }
    bindNoteGenerationChooser();
  }

  function runtimeMessage(message, danger = false) {
    document.querySelectorAll(".runtime-message").forEach((node) => node.remove());
    const node = document.createElement("div");
    node.className = "runtime-message";
    if (danger) node.style.background = "#f6d3c5";
    node.textContent = message;
    const host = notesView.hidden ? stateHost : notesStateHost;
    host.prepend(node);
  }

  async function copyParserTranscript(button) {
    const preview = button.closest(".transcript-panel")?.querySelector(".transcript-preview");
    const transcript = preview?.textContent || state.parserRecord?.transcript_text || "";
    if (!transcript) throw new Error("当前没有可复制的逐字稿");
    try {
      await navigator.clipboard.writeText(transcript);
    } catch {
      throw new Error("复制失败，请检查浏览器剪贴板权限后重试。");
    }
    button.classList.add("is-copied");
    button.textContent = "✓ 已复制";
    runtimeMessage("逐字稿全文已复制到剪贴板");
    window.setTimeout(() => {
      if (!button.isConnected) return;
      button.classList.remove("is-copied");
      button.textContent = "复制全文";
    }, 1_600);
  }

  const toNotesInstallCommand = "npx skills add anlygale-debug/to-notes --skill to-notes -g -y";

  async function copyOpenNoteResource(button, kind) {
    const originalLabel = button.textContent;
    let value;
    if (kind === "skill") {
      value = toNotesInstallCommand;
    } else {
      const response = await fetch("/static/resources/to-notes-universal-zh.md", { cache: "no-store" });
      if (!response.ok) throw new Error("通用提示词暂时无法读取，请使用下载或 GitHub 入口。");
      value = await response.text();
    }
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      throw new Error("复制失败，请检查浏览器剪贴板权限后重试。");
    }
    button.classList.add("is-copied");
    button.textContent = "✓ 已复制";
    runtimeMessage(kind === "skill" ? "Skill 安装命令已复制" : "To Notes 完整提示词已复制");
    window.setTimeout(() => {
      if (!button.isConnected) return;
      button.classList.remove("is-copied");
      button.textContent = originalLabel;
    }, 1_600);
  }

  async function copyReadyTranscript(button) {
    if (!state.inputTranscript.trim()) throw new Error("当前没有可复制的逐字稿");
    const originalLabel = button.textContent;
    await navigator.clipboard.writeText(state.inputTranscript);
    button.textContent = "✓ 已复制全文";
    runtimeMessage("逐字稿全文已复制，可以直接粘贴到你的 AI 中");
    window.setTimeout(() => {
      if (button.isConnected) button.textContent = originalLabel;
    }, 1_600);
  }

  function downloadReadyTranscript(format) {
    if (!state.inputTranscript.trim()) throw new Error("当前没有可下载的逐字稿");
    const linkedParserTitle = state.sourceMode === "linked"
      ? state.parserRecord?.title
      : "";
    const rawTitle = linkedParserTitle
      || state.uploadedTranscript?.name?.replace(/\.(txt|md)$/i, "")
      || "逐字稿";
    const downloadTitle = linkedParserTitle ? `${rawTitle}-逐字稿` : rawTitle;
    const safeTitle = downloadTitle.replace(/[\\/:*?"<>|]/g, "-").slice(0, 80) || "逐字稿";
    const markdown = format === "md";
    const content = markdown
      ? `# ${rawTitle} — 逐字稿\n\n${state.inputTranscript.trim()}\n`
      : `${state.inputTranscript.trim()}\n`;
    const blob = new Blob([content], { type: markdown ? "text/markdown;charset=utf-8" : "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${safeTitle}.${markdown ? "md" : "txt"}`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    runtimeMessage(`逐字稿 ${markdown ? "MD" : "TXT"} 已开始下载`);
  }

  function startParserMediaDownload(kind, button) {
    const label = kind === "video" ? "视频" : "音频";
    const extension = kind === "video" ? "video" : "audio";
    const token = crypto.randomUUID();
    const originalLabel = button.textContent;
    const frame = document.createElement("iframe");
    let finished = false;
    let signalTimer;
    let timeoutTimer;

    const finish = () => {
      if (finished) return;
      finished = true;
      clearInterval(signalTimer);
      clearTimeout(timeoutTimer);
      button.disabled = false;
      button.textContent = originalLabel;
      setTimeout(() => frame.remove(), 1000);
    };
    const reportFailure = (message) => {
      runtimeMessage(message || `${label}下载失败，请稍后重试。`, true);
      finish();
    };

    button.disabled = true;
    button.textContent = `正在准备${label}…`;
    frame.hidden = true;
    frame.title = `${label}下载`;
    frame.addEventListener("load", () => {
      if (finished || frame.contentWindow?.location.href === "about:blank") return;
      try {
        const body = frame.contentDocument?.body?.innerText?.trim() || "";
        if (!body) return;
        let message = body;
        try {
          message = JSON.parse(body)?.error?.message || body;
        } catch {
          // Plain-text server errors are still useful to the user.
        }
        reportFailure(message);
      } catch {
        reportFailure(`${label}下载失败，请稍后重试。`);
      }
    });
    document.body.append(frame);

    signalTimer = setInterval(() => {
      const signal = document.cookie
        .split("; ")
        .find((entry) => entry.startsWith("vtn_download="))
        ?.slice("vtn_download=".length);
      if (signal !== token) return;
      document.cookie = "vtn_download=; Max-Age=0; Path=/; SameSite=Lax";
      runtimeMessage(`${label}下载已开始，请在浏览器下载列表查看。`);
      finish();
    }, 200);
    timeoutTimer = setTimeout(
      () => reportFailure(`${label}准备超时，请检查网络后重试。`),
      30 * 60 * 1000,
    );
    frame.src = withDeviceId(
      `/api/v3/parser/records/${state.parserRecord.id}/${extension}` +
      `?download_token=${encodeURIComponent(token)}`,
    );
  }

  function markdownToEditorHtml(markdown) {
    const escape = (value) => value
      .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
    const inline = (value) => escape(value)
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/__(.+?)__/g, "<strong>$1</strong>")
      .replace(/~~(.+?)~~/g, "<del>$1</del>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");
    const lines = markdown.split("\n");
    const output = [];
    const isHorizontalRule = (value) => /^\s{0,3}((\*\s*){3,}|(-\s*){3,}|(_\s*){3,})\s*$/.test(value);
    const isTableDivider = (value) => /^\s*\|?\s*:?-{3,}/.test(value);
    const isBlockStart = (value, next = "") => !value.trim() ||
      /^(#{1,6})\s+/.test(value) || isHorizontalRule(value) ||
      /^>\s?/.test(value) || /^[-*]\s+/.test(value) ||
      /^\d+\.\s+/.test(value) || /^```/.test(value) ||
      (value.includes("|") && isTableDivider(next));
    const cells = (value) => value.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());

    for (let index = 0; index < lines.length;) {
      const line = lines[index];
      if (!line.trim()) {
        index += 1;
        continue;
      }
      if (/^```/.test(line)) {
        const code = [];
        index += 1;
        while (index < lines.length && !/^```/.test(lines[index])) code.push(lines[index++]);
        if (index < lines.length) index += 1;
        output.push(`<pre><code>${escape(code.join("\n"))}</code></pre>`);
        continue;
      }
      if (isHorizontalRule(line)) {
        output.push("<hr />");
        index += 1;
        continue;
      }
      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      if (heading) {
        const level = heading[1].length;
        output.push(`<h${level}>${inline(heading[2])}</h${level}>`);
        index += 1;
        continue;
      }
      if (line.includes("|") && isTableDivider(lines[index + 1] || "")) {
        const header = cells(line);
        index += 2;
        const rows = [];
        while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
          rows.push(cells(lines[index++]));
        }
        output.push(`<table><thead><tr>${header.map((cell) => `<th>${inline(cell)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${inline(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
        continue;
      }
      if (/^[-*]\s+/.test(line)) {
        const items = [];
        while (index < lines.length && /^[-*]\s+/.test(lines[index])) {
          items.push(lines[index++].replace(/^[-*]\s+/, ""));
        }
        const taskList = items.every((item) => /^\[[ xX]\]\s+/.test(item));
        output.push(`<ul${taskList ? ' class="task-list"' : ""}>${items.map((item) => {
          const task = item.match(/^\[([ xX])\]\s+(.+)$/);
          if (!task) return `<li>${inline(item)}</li>`;
          return `<li><input type="checkbox" disabled${task[1].toLowerCase() === "x" ? " checked" : ""} /><span>${inline(task[2])}</span></li>`;
        }).join("")}</ul>`);
        continue;
      }
      if (/^\d+\.\s+/.test(line)) {
        const items = [];
        while (index < lines.length && /^\d+\.\s+/.test(lines[index])) {
          items.push(lines[index++].replace(/^\d+\.\s+/, ""));
        }
        output.push(`<ol>${items.map((item) => `<li>${inline(item)}</li>`).join("")}</ol>`);
        continue;
      }
      if (/^>\s?/.test(line)) {
        const quote = [];
        while (index < lines.length && /^>\s?/.test(lines[index])) {
          quote.push(lines[index++].replace(/^>\s?/, ""));
        }
        output.push(`<blockquote>${inline(quote.join("\n"))}</blockquote>`);
        continue;
      }
      const paragraph = [line.trim()];
      index += 1;
      while (index < lines.length && !isBlockStart(lines[index], lines[index + 1] || "")) {
        paragraph.push(lines[index++].trim());
      }
      output.push(`<p>${inline(paragraph.join(" "))}</p>`);
    }
    return output.join("");
  }

  function renderStructuredNote(markdown, body, deck) {
    const scratch = document.createElement("div");
    scratch.innerHTML = markdownToEditorHtml(markdown);
    const headingLevel = (heading) => Number(heading.tagName.slice(1));
    const summaryQuote = [...scratch.querySelectorAll("blockquote")].find((quote) =>
      quote.querySelector("strong")?.textContent.trim() === "核心摘要"
    );
    const summaryHeading = !summaryQuote && [...scratch.querySelectorAll("h2, h3, h4")].find((heading) =>
      /^(核心摘要|内容概述|核心概述|摘要|概述|executive summary)$/i.test(heading.textContent.trim())
    );
    const overviewNodes = [];
    if (summaryQuote) {
      const overview = summaryQuote.cloneNode(true);
      overview.querySelector("strong")?.remove();
      overviewNodes.push(...overview.childNodes);
      summaryQuote.remove();
    } else if (summaryHeading) {
      const summaryLevel = headingLevel(summaryHeading);
      let node = summaryHeading.nextSibling;
      while (node && !(
        node.nodeType === Node.ELEMENT_NODE &&
        /^H[1-6]$/.test(node.tagName) &&
        headingLevel(node) <= summaryLevel
      )) {
        const next = node.nextSibling;
        overviewNodes.push(node);
        node = next;
      }
      summaryHeading.remove();
    } else {
      const firstHeading = scratch.querySelector("h2, h3, h4");
      const firstParagraph = [...scratch.querySelectorAll("p")].find((paragraph) =>
        !firstHeading || (paragraph.compareDocumentPosition(firstHeading) & Node.DOCUMENT_POSITION_FOLLOWING)
      );
      if (firstParagraph) overviewNodes.push(firstParagraph);
    }
    if (deck) {
      deck.innerHTML = "";
      overviewNodes.forEach((node) => deck.append(node));
      if (!deck.textContent.trim()) {
        deck.textContent = "这份笔记已按核心问题与行动路径整理，正文保留完整解释与实践细节。";
      }
    }

    body.innerHTML = "";
    const structuralLevel = [2, 3, 4].find((level) => scratch.querySelector(`h${level}`));
    const headings = structuralLevel ? [...scratch.querySelectorAll(`h${structuralLevel}`)] : [];
    const moduleMarkers = [...scratch.querySelectorAll("p")].filter((paragraph) =>
      /^复习增强｜/.test(paragraph.querySelector(":scope > strong")?.textContent.trim() || "")
    );
    const toc = document.createElement("nav");
    toc.className = "note-toc";
    toc.setAttribute("aria-label", "笔记目录");
    toc.innerHTML = '<span class="eyebrow">阅读地图 / CONTENTS</span>';
    const content = document.createElement("div");
    content.className = "note-content";

    const prefaceNodes = [];
    while (scratch.firstChild && scratch.firstChild !== headings[0]) {
      prefaceNodes.push(scratch.firstChild);
      scratch.firstChild.remove();
    }
    if (prefaceNodes.length) {
      const preface = document.createElement("section");
      preface.className = "note-preface";
      prefaceNodes.forEach((node) => preface.append(node));
      if (preface.textContent.trim()) content.append(preface);
    }

    headings.forEach((heading, index) => {
      const section = document.createElement("section");
      const title = heading.textContent.trim();
      const isModule = /^(关键概念|实践提炼|行动清单|复习问题|常见问题)/.test(title);
      section.className = `note-chapter${isModule ? " note-module" : ""}`;
      section.id = `note-${String(index + 1).padStart(2, "0")}`;
      const nextHeading = headings[index + 1];
      const nodes = [];
      let node = heading.nextSibling;
      while (node && node !== nextHeading && !moduleMarkers.includes(node)) {
        const next = node.nextSibling;
        nodes.push(node);
        node = next;
      }
      const headingRow = document.createElement("div");
      headingRow.className = "chapter-heading-row";
      const headingWrap = document.createElement("div");
      const label = document.createElement("div");
      label.className = "chapter-label meta";
      label.textContent = isModule
        ? "附加模块 / MODULE"
        : `${String(index + 1).padStart(2, "0")} / CHAPTER`;
      const displayHeading = document.createElement("h2");
      displayHeading.innerHTML = heading.innerHTML;
      heading.remove();
      headingWrap.append(label, displayHeading);
      headingRow.append(headingWrap);
      if (index === 0 && currentNotesState === "reading") {
        const button = document.createElement("button");
        button.className = "text-action";
        button.type = "button";
        button.dataset.regenerateChapter = "";
        button.dataset.chapterTitle = title;
        button.textContent = "重新生成本章 ↻";
        headingRow.append(button);
      }
      section.append(headingRow, ...nodes);
      content.append(section);

      const link = document.createElement("a");
      link.href = `#${section.id}`;
      link.innerHTML = `<span>${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(title)}</strong>`;
      toc.append(link);
    });

    moduleMarkers.forEach((marker, index) => {
      const module = document.createElement("section");
      module.className = "note-module";
      const heading = document.createElement("h2");
      heading.textContent = marker.querySelector("strong")?.textContent
        .replace(/^复习增强｜/, "") || "复习增强";
      const label = document.createElement("div");
      label.className = "chapter-label meta";
      label.textContent = "复习增强 / MODULE";
      const nextMarker = moduleMarkers[index + 1];
      let node = marker.nextSibling;
      const nodes = [];
      while (node && node !== nextMarker) {
        const next = node.nextSibling;
        nodes.push(node);
        node = next;
      }
      marker.remove();
      module.append(label, heading, ...nodes);
      content.append(module);
    });

    if (!headings.length) {
      const section = document.createElement("section");
      section.className = "note-chapter note-chapter--single";
      while (scratch.firstChild) section.append(scratch.firstChild);
      content.append(section);
    }
    if (headings.length) body.append(toc);
    body.append(content);

    const sourceDrawer = document.createElement("details");
    sourceDrawer.className = "reading-source-drawer";
    sourceDrawer.innerHTML = "<summary>查看生成依据与来源信息 <span>＋</span></summary><div></div>";
    body.append(sourceDrawer);
  }

  function editorHtmlToMarkdown(root) {
    const renderChildren = (node) => [...node.childNodes].map(renderNode).join("");
    const renderListItem = (node, prefix) => {
      const value = renderChildren(node).trim().replace(/\n{3,}/g, "\n\n");
      return `${prefix}${value.replace(/\n/g, "\n  ")}\n`;
    };
    const renderNode = (node) => {
      if (node.nodeType === Node.TEXT_NODE) return node.textContent || "";
      if (node.nodeType !== Node.ELEMENT_NODE) return "";
      const tag = node.tagName.toLowerCase();
      if (tag === "br") return "\n";
      if (tag === "h1") return `# ${renderChildren(node).trim()}\n\n`;
      if (tag === "h2") return `## ${renderChildren(node).trim()}\n\n`;
      if (tag === "h3") return `### ${renderChildren(node).trim()}\n\n`;
      if (tag === "h4") return `#### ${renderChildren(node).trim()}\n\n`;
      if (tag === "h5") return `##### ${renderChildren(node).trim()}\n\n`;
      if (tag === "h6") return `###### ${renderChildren(node).trim()}\n\n`;
      if (tag === "hr") return "---\n\n";
      if (tag === "p") return `${renderChildren(node).trim()}\n\n`;
      if (tag === "strong" || tag === "b") return `**${renderChildren(node)}**`;
      if (tag === "em" || tag === "i") return `*${renderChildren(node)}*`;
      if (tag === "del" || tag === "s") return `~~${renderChildren(node)}~~`;
      if (tag === "blockquote") {
        return `${renderChildren(node).trim().split("\n").map((line) => `> ${line}`).join("\n")}\n\n`;
      }
      if (tag === "pre") return `\`\`\`\n${node.innerText.trim()}\n\`\`\`\n\n`;
      if (tag === "code") return `\`${renderChildren(node)}\``;
      if (tag === "a") return `[${renderChildren(node)}](${node.getAttribute("href") || ""})`;
      if (tag === "ul") return `${[...node.children].map((item) => {
        const checkbox = item.querySelector(':scope > input[type="checkbox"]');
        return renderListItem(item, checkbox ? `- [${checkbox.checked ? "x" : " "}] ` : "- ");
      }).join("")}\n`;
      if (tag === "input" && node.type === "checkbox") return "";
      if (tag === "ol") return `${[...node.children].map((item, index) => renderListItem(item, `${index + 1}. `)).join("")}\n`;
      if (tag === "li") return renderChildren(node);
      if (tag === "table") {
        const rows = [...node.querySelectorAll("tr")].map((row) =>
          [...row.querySelectorAll("th, td")].map((cell) => renderChildren(cell).trim())
        );
        if (!rows.length) return "";
        const header = `| ${rows[0].join(" | ")} |\n`;
        const divider = `| ${rows[0].map(() => "---").join(" | ")} |\n`;
        const body = rows.slice(1).map((row) => `| ${row.join(" | ")} |`).join("\n");
        return `${header}${divider}${body}\n\n`;
      }
      return renderChildren(node);
    };
    return renderChildren(root).replace(/\n{3,}/g, "\n\n").trim();
  }

  function setParserBusy(busy) {
    state.parserSubmitting = busy;
    const button = document.querySelector('#parser-form button[type="submit"]');
    if (button) {
      button.disabled = busy;
      button.setAttribute("aria-busy", String(busy));
      button.innerHTML = busy ? "正在解析…" : "<span>→</span>开始解析";
    }
    if (videoLink) videoLink.readOnly = busy;
  }

  function bindParserProgress(task) {
    const profiles = {
      resolve: ["正在识别视频来源", "正在确认平台并读取视频标题、作者和时长。", 10],
      download: ["正在获取音频内容", "视频信息已读取，正在准备供语音识别使用的音频。", 30],
      transcribe: ["正在生成逐字稿", "正在把音频转换成文字；长视频通常在这一步等待最久。", 55],
      save: ["正在整理解析结果", "逐字稿已经生成，正在保存来源信息和可下载材料。", 90],
    };
    const stage = profiles[task?.progress?.stage] ? task.progress.stage : "resolve";
    const [title, description, fallbackPercent] = profiles[stage];
    const percent = Number.isFinite(task?.progress?.percent)
      ? Math.max(0, Math.min(99, task.progress.percent)) : fallbackPercent;
    const panel = stateHost.querySelector(".progress-panel");
    if (!panel) return;
    const metadataOnly = task?.operation === "metadata";
    panel.dataset.parserStage = stage;
    const taskLabel = panel.querySelector("[data-parser-task-label]");
    if (taskLabel) taskLabel.textContent = task?.id ? `TASK #${task.id.slice(0, 8).toUpperCase()}` : "TASK / 正在创建";
    const titleNode = panel.querySelector("[data-parser-progress-title]");
    if (titleNode) titleNode.textContent = title;
    const descriptionNode = panel.querySelector("[data-parser-progress-description]");
    if (descriptionNode) descriptionNode.textContent = description;
    const chip = panel.querySelector("[data-parser-progress-chip]");
    if (chip) chip.textContent = `${task?.progress?.label || title.replace(/^正在/, "")} · ${percent}%`;
    const track = panel.querySelector(".parser-progress-track");
    if (track) track.setAttribute("aria-valuenow", String(percent));
    const bar = panel.querySelector("[data-parser-progress-bar]");
    if (bar) bar.style.width = `${percent}%`;
    const live = panel.querySelector("[data-parser-progress-live]");
    if (live) live.textContent = `当前：${task?.progress?.label || title.replace(/^正在/, "")}`;
    const order = metadataOnly ? ["resolve", "save"] : ["resolve", "download", "transcribe", "save"];
    const currentIndex = order.indexOf(stage);
    panel.querySelectorAll("[data-parser-stage-item]").forEach((item) => {
      const itemStage = item.dataset.parserStageItem;
      item.hidden = metadataOnly && ["download", "transcribe"].includes(itemStage);
      const index = order.indexOf(itemStage);
      if (index < 0) return;
      item.classList.toggle("is-complete", index < currentIndex);
      item.classList.toggle("is-current", index === currentIndex);
      const status = item.querySelector("em");
      if (status) status.textContent = index < currentIndex ? "完成" : index === currentIndex ? "进行中" : "等待";
    });
  }

  function bindParserFailure(task = {}) {
    const panel = stateHost.querySelector(".failure-panel");
    if (!panel) return;
    const code = task.error_code || "PARSER_FAILED";
    const title = code.startsWith("TRANSCRIPTION")
      ? "云端转录没有完成。"
      : "这条链接暂时无法解析。";
    const codeNode = panel.querySelector("[data-parser-failure-code]");
    if (codeNode) {
      const taskLabel = task.id ? `TASK #${task.id.slice(0, 8).toUpperCase()}` : "TASK";
      codeNode.textContent = `${taskLabel} / ${code}`;
    }
    const titleNode = panel.querySelector("[data-parser-failure-title]");
    if (titleNode) titleNode.textContent = title;
    const messageNode = panel.querySelector("[data-parser-failure-message]");
    if (messageNode) messageNode.textContent = task.error_message || "解析失败，请检查后重试。";
    const retryButton = panel.querySelector("[data-retry]");
    if (retryButton) retryButton.hidden = task.error_retryable === false;
  }

  async function pollParser(taskId, pollToken) {
    while (pollToken === state.parserPollToken) {
      const payload = await request(`/api/v3/parser/tasks/${taskId}`);
      if (pollToken !== state.parserPollToken) return;
      state.parserTask = payload.task;
      if (payload.task.state === "completed") {
        const recordPayload = await request(`/api/v3/parser/records/${payload.task.record_id}`);
        if (pollToken !== state.parserPollToken) return;
        state.parserRecord = recordPayload.record;
        setParserState("success");
        bindParserRecord();
        return;
      }
      if (payload.task.state === "failed") {
        setParserState("failure");
        bindParserFailure(payload.task);
        runtimeMessage(payload.task.error_message || "解析失败", true);
        return;
      }
      if (!stateHost.querySelector(".progress-panel")) setParserState("loading");
      bindParserProgress(payload.task);
      await new Promise((resolve) => setTimeout(resolve, 700));
    }
  }

  function bindTranscriptionProgress(task) {
    const panel = stateHost.querySelector(".transcript-panel");
    const status = stateHost.querySelector("[data-transcription-status]");
    if (!panel || !status) return;
    panel.classList.add("is-generating");
    panel.querySelectorAll("[data-generate-transcript]").forEach((button) => {
      button.disabled = true;
    });
    const providerLabel = task?.transcription_provider === "cloudflare"
      ? "高速高质量转录" : "免费转录";
    const label = task?.progress?.label || "正在创建逐字稿任务";
    const percent = Number.isFinite(task?.progress?.percent) ? task.progress.percent : 5;
    status.textContent = `${providerLabel} · ${label} · ${percent}%`;
    const running = stateHost.querySelector("[data-transcription-running]");
    const runningCopy = stateHost.querySelector("[data-transcription-running-copy]");
    const errorPanel = stateHost.querySelector("[data-transcription-error]");
    const regeneratePanel = stateHost.querySelector("[data-transcript-regenerate]");
    if (running) running.hidden = false;
    if (runningCopy) runningCopy.textContent = `${providerLabel} · ${label} · ${percent}%`;
    if (errorPanel) errorPanel.hidden = true;
    if (regeneratePanel) regeneratePanel.hidden = true;
  }

  function showTranscriptionError(error) {
    bindParserRecord();
    const panel = stateHost.querySelector("[data-transcription-error]");
    const message = stateHost.querySelector("[data-transcription-error-message]");
    if (panel) panel.hidden = false;
    if (message) message.textContent = error.message || "转录没有完成，请重试或切换线路。";
  }

  async function pollTranscription(taskId, pollToken) {
    while (pollToken === state.parserPollToken) {
      const payload = await request(`/api/v3/parser/tasks/${taskId}`);
      if (pollToken !== state.parserPollToken) return;
      state.parserTask = payload.task;
      bindTranscriptionProgress(payload.task);
      if (payload.task.state === "completed") {
        const recordPayload = await request(
          `/api/v3/parser/records/${encodeURIComponent(state.parserRecord.id)}`
        );
        if (pollToken !== state.parserPollToken) return;
        state.parserRecord = recordPayload.record;
        bindParserRecord();
        runtimeMessage("逐字稿已经生成，可以复制、下载或继续生成笔记。");
        return;
      }
      if (payload.task.state === "failed") {
        const error = new Error(payload.task.error_message || "逐字稿生成失败");
        error.code = payload.task.error_code || "TRANSCRIPTION_FAILED";
        throw error;
      }
      await new Promise((resolve) => setTimeout(resolve, 700));
    }
  }

  function bindParserRecord() {
    const record = state.parserRecord;
    if (!record) return;
    bindFreeCapacityNotices({
      host: stateHost,
      transcript: record.transcript_text || "",
      durationSeconds: record.duration_seconds,
    });
    const displayedPlatform = platformLabel(record.platform);
    const result = stateHost.querySelector(".result-card");
    const title = result?.querySelector("h3");
    if (title) title.textContent = record.title;
    const meta = result?.querySelector(".result-meta .meta");
    if (meta) meta.textContent = record.creator || "未知作者";
    const description = result?.querySelector(".result-main > p");
    if (description) description.textContent = record.description || "该视频暂无简介。";
    const values = result?.querySelectorAll("dd");
    if (values?.[0]) values[0].textContent = record.creator || "未知作者";
    if (values?.[1]) values[1].textContent = displayedPlatform;
    if (values?.[2]) values[2].textContent = `${Math.floor(record.duration_seconds / 60)} 分钟`;
    const sourceLink = values?.[3]?.querySelector("a");
    if (sourceLink) {
      sourceLink.href = record.source_url;
      sourceLink.target = "_blank";
      sourceLink.rel = "noopener noreferrer";
    }
    const duration = result?.querySelector(".cover-duration");
    if (duration) duration.textContent = `${Math.floor(record.duration_seconds / 60)}:${String(record.duration_seconds % 60).padStart(2, "0")}`;
    const coverPlatform = result?.querySelector(".cover-platform");
    if (coverPlatform) coverPlatform.textContent = displayedPlatform;
    const cover = result?.querySelector(".video-cover");
    const coverImage = cover?.querySelector("[data-result-thumbnail]");
    if (cover && coverImage) {
      cover.classList.remove("has-real-thumbnail");
      cover.setAttribute("aria-label", record.thumbnail_url ? `视频封面：${record.title}` : "该视频没有可用封面，显示默认占位图");
      coverImage.onload = () => cover.classList.add("has-real-thumbnail");
      coverImage.onerror = () => {
        cover.classList.remove("has-real-thumbnail");
        cover.setAttribute("aria-label", "视频封面加载失败，显示默认占位图");
        coverImage.removeAttribute("src");
      };
      if (record.thumbnail_url) {
        coverImage.src = withDeviceId(
          `/api/v3/parser/records/${encodeURIComponent(record.id)}/thumbnail`,
        );
      } else {
        coverImage.removeAttribute("src");
      }
    }
    const transcriptText = String(record.transcript_text || "").trim();
    const hasTranscript = Boolean(transcriptText);
    const transcriptPanel = stateHost.querySelector(".transcript-panel");
    const transcriptEmpty = stateHost.querySelector("[data-transcript-empty]");
    const transcriptReady = stateHost.querySelector("[data-transcript-ready]");
    if (transcriptEmpty) transcriptEmpty.hidden = hasTranscript;
    if (transcriptReady) transcriptReady.hidden = !hasTranscript;
    stateHost.querySelectorAll("[data-transcript-dependent]").forEach((node) => {
      node.hidden = !hasTranscript;
    });
    transcriptPanel?.classList.remove("is-generating");
    const transcriptionRunning = stateHost.querySelector("[data-transcription-running]");
    const transcriptionError = stateHost.querySelector("[data-transcription-error]");
    const transcriptRegenerate = stateHost.querySelector("[data-transcript-regenerate]");
    if (transcriptionRunning) transcriptionRunning.hidden = true;
    if (transcriptionError) transcriptionError.hidden = true;
    if (transcriptRegenerate) transcriptRegenerate.hidden = true;
    const transcriptionStatus = stateHost.querySelector("[data-transcription-status]");
    if (transcriptionStatus && !hasTranscript) {
      transcriptionStatus.textContent = state.transcriptionProviders.cloudflare
        ? "免费线路可直接使用；高速线路需要内测码。"
        : "高速线路暂未开放；当前可以使用免费转录。";
    }
    stateHost.querySelectorAll("[data-generate-transcript]").forEach((button) => {
      const provider = button.dataset.generateTranscript;
      const needsAccess = provider === "cloudflare" && state.accessControlEnabled && !state.access;
      const available = state.transcriptionProviders[provider] !== false;
      button.disabled = !available;
      if (!available && provider === "cloudflare") {
        button.title = "高速高质量转录暂未配置";
        const detail = button.querySelector("small");
        if (detail) detail.textContent = "暂未配置 · 请先在管理后台开启";
      } else {
        if (needsAccess) button.title = "输入内测码后可使用高速转录";
        else button.removeAttribute("title");
        const detail = button.querySelector("small");
        if (detail && provider === "cloudflare") {
          detail.textContent = needsAccess ? "需内测码 · 更快、更稳定" : "高速 · 更快、更稳定";
        }
      }
    });
    const transcript = stateHost.querySelector(".transcript-preview");
    const transcriptToggle = stateHost.querySelector("[data-toggle-transcript]");
    const transcriptTitle = stateHost.querySelector("[data-transcript-character-count]");
    if (!hasTranscript || !transcript) return;

    const transcriptCharacterCount = Array.from(transcriptText).length;
    transcript.textContent = transcriptText;
    transcript.classList.remove("is-collapsed");
    if (transcriptTitle) transcriptTitle.textContent = `逐字稿 · ${transcriptCharacterCount.toLocaleString()} 字`;
    if (!transcriptToggle) return;

    const styles = getComputedStyle(transcript);
    const lineHeight = Number.parseFloat(styles.lineHeight);
    const verticalPadding = Number.parseFloat(styles.paddingTop) + Number.parseFloat(styles.paddingBottom);
    const previewHeight = lineHeight * 7 + verticalPadding;
    const shouldCollapse = transcript.scrollHeight > previewHeight + 1;
    transcript.classList.toggle("is-collapsed", shouldCollapse);
    transcriptToggle.hidden = !shouldCollapse;
    if (!shouldCollapse) {
      return;
    }
    transcriptToggle.setAttribute("aria-expanded", "false");
    transcriptToggle.textContent = "展开完整逐字稿 ↓";
  }

  function noteStateName(task) {
    const map = {
      analyzing: "analyzing",
      recommendation_ready: "recommendations",
      recommendation_stale: "stale",
      analysis_failed: "analysis-failure",
      generating_direct: "direct-generating",
      outline_ready: "outline",
      outline_regenerating: "outline-regenerating",
      generating_chapters: "chapter-generating",
      chapter_failed: "chapter-failure",
      generation_failed: "chapter-failure",
      complete: "generation-complete",
    };
    return map[task.state] || "input";
  }

  async function pollNote(taskId) {
    const pollToken = ++state.notePollToken;
    const workspaceToken = state.noteWorkspaceToken;
    try {
      while (true) {
        const payload = await request(`/api/v3/note-tasks/${taskId}`, {
          timeoutMs: 5_000,
          timeoutLabel: "状态查询",
        });
        if (pollToken !== state.notePollToken || workspaceToken !== state.noteWorkspaceToken) return null;
        state.noteTask = payload.task;
        if (payload.task.state === "complete" && payload.task.note_id) {
          const notePayload = await request(`/api/v3/notes/${payload.task.note_id}`);
          if (pollToken !== state.notePollToken || workspaceToken !== state.noteWorkspaceToken) return null;
          state.note = notePayload.note;
        }
        const nextState = noteStateName(payload.task);
        if (currentNotesState !== nextState) setNotesState(nextState);
        bindNoteTask();
        if (["recommendation_ready", "analysis_failed", "outline_ready", "chapter_failed",
             "generation_failed", "complete"].includes(payload.task.state)) return payload.task;
        await new Promise((resolve) => setTimeout(resolve, 700));
      }
    } catch (error) {
      if (pollToken !== state.notePollToken || workspaceToken !== state.noteWorkspaceToken) return null;
      const previousState = state.noteTask?.state || "analyzing";
      const analysisStage = previousState === "analyzing";
      state.noteTask = {
        ...(state.noteTask || {}),
        id: taskId,
        state: analysisStage ? "analysis_failed" : "generation_failed",
        error_code: error.code || "NOTE_STATUS_UNAVAILABLE",
        error_message: error.message || "无法获取任务状态，已停止等待。",
        error_retryable: true,
        client_poll_failure: true,
        failed_from_state: previousState,
      };
      setNotesState(noteStateName(state.noteTask));
      bindNoteTask();
      throw error;
    }
  }

  function bindNoteTask() {
    const task = state.noteTask;
    if (!task) return;
    window.noteTitle = task.proposed_title || window.noteTitle;
    const input = notesStateHost.querySelector("#suggested-note-title");
    if (input) input.value = task.proposed_title;
    const transcriptEditor = notesStateHost.querySelector("[data-transcript-edit]");
    if (transcriptEditor) transcriptEditor.value = task.basis_transcript;
    const source = notesStateHost.querySelector("[data-analysis-source]");
    if (source) {
      const label = task.source_snapshot?.title || task.source_name || "独立逐字稿";
      source.textContent = `生成依据：${label} // ${task.basis_transcript.length.toLocaleString()} 字`;
    }
    const analysisTaskLabel = notesStateHost.querySelector("[data-analysis-task-label]");
    if (analysisTaskLabel) {
      analysisTaskLabel.textContent = `AI PRE-READ // TASK ${String(task.id || "").slice(0, 8).toUpperCase()}`;
    }
    const drawerCount = notesStateHost.querySelector("[data-transcript-drawer-count]");
    if (drawerCount) drawerCount.textContent = `默认收起 // ${task.basis_transcript.length.toLocaleString()} 字 ＋`;
    const reason = notesStateHost.querySelector(".recommendation-reason");
    if (reason && task.recommendation?.reason) reason.textContent = task.recommendation.reason;
    bindRecommendation(task.recommendation);
    const outlineFeedbackInput = notesStateHost.querySelector("#outline-feedback");
    if (outlineFeedbackInput) outlineFeedbackInput.value = task.outline_feedback || "";
    const outlineFeedbackCopy = notesStateHost.querySelector("[data-outline-feedback-copy]");
    if (outlineFeedbackCopy) outlineFeedbackCopy.textContent = task.outline_feedback || "按本次要求重新组织";
    const outlineContext = notesStateHost.querySelector(".outline-context");
    if (outlineContext) {
      const values = outlineContext.querySelectorAll("strong");
      if (values[0]) values[0].textContent = task.proposed_title || "未命名笔记";
      if (values[1]) values[1].textContent = task.request_text || "未填写额外要求";
    }
    const outlineList = notesStateHost.querySelector(".outline-list");
    if (outlineList && task.outline?.length) {
      outlineList.innerHTML = task.outline.map((chapter, index) => {
        const subtopics = Array.isArray(chapter.subtopics) ? chapter.subtopics : [];
        const subtopicList = subtopics.length
          ? `<ul class="outline-subtopics">${subtopics.map((subtopic) =>
              `<li>${escapeHtml(subtopic)}</li>`).join("")}</ul>`
          : "";
        return `<li><span class="outline-index">${String(index + 1).padStart(2, "0")}</span>
          <div><strong>${escapeHtml(chapter.title)}</strong><p>${escapeHtml(chapter.goal || "根据逐字稿展开本章")}</p>${subtopicList}</div>
          <span class="meta">章节任务</span></li>`;
      }).join("");
    }
    const chapterList = notesStateHost.querySelector(".chapter-list");
    if (chapterList && task.chapters?.length) {
      chapterList.innerHTML = task.chapters.map((chapter) => {
        const statusClass = chapter.status === "complete" ? "is-complete" :
          chapter.status === "failed" ? "is-failed" : chapter.status === "running" ? "is-current" : "";
        const statusLabel = chapter.status === "complete" ? "✓" :
          chapter.status === "failed" ? "失败" : chapter.status === "running" ? "•••" : "—";
        const detail = chapter.status === "complete" ? `${chapter.content_md.length.toLocaleString()} 字 · 已保存` :
          chapter.status === "failed" ? "本章未写入，已完成章节仍保留" :
          chapter.status === "running" ? "正在结合上下文生成" : "等待";
        return `<li class="${statusClass}"><span>${String(chapter.position).padStart(2, "0")}</span>
          <div><strong>${escapeHtml(chapter.title)}</strong><small>${detail}</small></div><em>${statusLabel}</em></li>`;
      }).join("");
    }
    bindChapterProgress(task);
    bindChapterFailure(task);
    bindDirectGeneration(task);
    bindGenerationComplete(task);
    if (task.state === "analysis_failed") {
      const message = notesStateHost.querySelector("[data-analysis-failure-message]");
      if (message) {
        message.textContent = task.error_message ||
          "内容已经安全保留。你可以重试分析，或返回检查逐字稿与本次需求。";
      }
      const code = notesStateHost.querySelector("[data-analysis-failure-code]");
      if (code) code.textContent = task.error_code || "ANALYSIS_FAILED";
    }
    if (task.state === "chapter_failed" && task.error_message) {
      runtimeMessage(task.error_message, true);
    }
  }

  function bindDirectGeneration(task) {
    const host = notesStateHost.querySelector(".generation-stack");
    if (!host) return;
    const stages = ["understand", "organize", "generate_content", "check", "complete"];
    const stage = stages.includes(task.progress?.stage) ? task.progress.stage : "understand";
    const currentIndex = stages.indexOf(stage);
    const taskLabel = host.querySelector("[data-direct-task-label]");
    if (taskLabel) {
      taskLabel.textContent = `TASK ${String(task.id || "").slice(0, 8).toUpperCase()} // DIRECT GENERATION`;
    }
    const stageCurrent = host.querySelector("[data-direct-stage-current]");
    if (stageCurrent) stageCurrent.textContent = String(currentIndex + 1).padStart(2, "0");
    const stageTotal = host.querySelector("[data-direct-stage-total]");
    if (stageTotal) stageTotal.textContent = `/ ${String(stages.length).padStart(2, "0")} 阶段`;
    host.querySelectorAll("[data-direct-stage]").forEach((item, index) => {
      item.classList.toggle("is-complete", index < currentIndex);
      item.classList.toggle("is-current", index === currentIndex);
      const status = item.querySelector("em");
      if (status) status.textContent = index < currentIndex ? "完成" : index === currentIndex ? "进行中" : "等待";
    });
    const plan = task.final_settings || {};
    const values = {
      "[data-generation-structure]": plan.structure?.label || "按逐字稿组织",
      "[data-generation-detail]": plan.detail?.label || "按推荐详细度",
      "[data-generation-method]": plan.method === "outline" ? "大纲确认后生成" : "一次性生成",
      "[data-generation-modules]": (plan.modules || []).map((module) => module.label).join(" · ") || "不增加附加模块",
    };
    Object.entries(values).forEach(([selector, value]) => {
      const node = host.querySelector(selector);
      if (node) node.textContent = value;
    });
  }

  function bindGenerationComplete(task) {
    const host = notesStateHost.querySelector(".generation-complete-stack");
    if (!host) return;
    const note = state.note;
    const chapters = task.chapters || [];
    const plan = task.final_settings || {};
    const markdown = note?.current_markdown || "";
    const title = note?.title || task.proposed_title || "未命名笔记";
    const source = note?.source_snapshot || task.source_snapshot || {};
    const status = host.querySelector("[data-completion-status]");
    if (status) status.textContent = chapters.length ? `${chapters.length} / ${chapters.length} 章完成` : "生成完成";
    const receipt = host.querySelector("[data-completion-receipt]");
    if (receipt) receipt.textContent = `NOTE RECEIPT // ${String(note?.id || task.note_id || task.id || "").slice(0, 8).toUpperCase()}`;
    const titleNode = host.querySelector("[data-completion-title]");
    if (titleNode) titleNode.textContent = title;
    const characterCount = Array.from(markdown).length;
    const characterNode = host.querySelector("[data-completion-character-count]");
    if (characterNode) {
      characterNode.dataset.value = String(characterCount);
      characterNode.textContent = chapters.length
        ? `${chapters.length} 章 · ${characterCount.toLocaleString()} 字`
        : `${characterCount.toLocaleString()} 字`;
    }
    const modules = host.querySelector("[data-completion-modules]");
    if (modules) modules.textContent = (plan.modules || []).map((module) => module.label).join(" · ") || "未增加附加模块";
    const sourceNode = host.querySelector("[data-completion-source]");
    if (sourceNode) {
      sourceNode.textContent = [
        task.source_type === "parser" ? "视频解析" : "独立逐字稿",
        source.platform,
        source.creator,
      ].filter(Boolean).join(" · ");
    }
    const time = host.querySelector("[data-completion-time]");
    if (time) time.textContent = note?.updated_at
      ? new Date(note.updated_at).toLocaleString("zh-CN")
      : "刚刚完成";
    const integrity = note?.integrity || {};
    const integrityPanel = host.querySelector("[data-integrity-panel]");
    const integrityChip = host.querySelector("[data-integrity-chip]");
    const integrityTitle = host.querySelector("[data-integrity-title]");
    const integrityMessage = host.querySelector("[data-integrity-message]");
    const integrityRetry = host.querySelector("[data-recheck-integrity]");
    const integrityState = integrity.status || "check_unavailable";
    const unavailableMessage = {
      LLM_REQUEST_FAILED: "篇章与所选模块已经通过结构校验；AI 服务请求失败，可以稍后重新检查内容。",
      LLM_INVALID_RESPONSE: "篇章与所选模块已经通过结构校验；AI 返回格式暂时无法识别，可以重新检查内容。",
      LLM_RATE_LIMITED: "篇章与所选模块已经通过结构校验；AI 服务当前请求较多，可以稍后重新检查内容。",
      LLM_SERVICE_UNAVAILABLE: "篇章与所选模块已经通过结构校验；AI 服务暂时不可用，可以稍后重新检查内容。",
      LLM_TIMEOUT: "篇章与所选模块已经通过结构校验；AI 服务响应超时，可以稍后重新检查内容。",
      LLM_AUTH_FAILED: "篇章与所选模块已经通过结构校验；AI 服务配置或权限需要检查。",
    }[integrity.error_code] ||
      "篇章与所选模块已经通过结构校验；本次内容完整性检查未能完成，因此不会显示为检查通过。";
    const integrityView = integrityState === "ok"
      ? {
          className: "is-ok", chipClass: "chip-green", chip: "✓ 内容检查完成",
          title: "未发现明显遗漏",
          message: "已结合生成依据逐字稿、本次笔记需求与最终设置完成检查。合理压缩的重复表达未计为遗漏。",
        }
      : integrityState === "possible_omission"
        ? {
            className: "is-warning", chipClass: "chip-red", chip: "需要复核",
            title: `发现 ${Math.max(1, integrity.items?.length || 0)} 项可能遗漏`,
            message: "笔记已经保存，但内容检查发现可能需要补充的部分。打开笔记后可继续编辑或重新生成。",
          }
        : {
            className: "is-unavailable", chipClass: "chip-blue", chip: "结构检查完成",
            title: "内容检查暂不可用",
            message: unavailableMessage,
          };
    if (integrityPanel) {
      integrityPanel.classList.remove("is-ok", "is-warning", "is-unavailable");
      integrityPanel.classList.add(integrityView.className);
    }
    if (integrityChip) {
      integrityChip.classList.remove("chip-green", "chip-red", "chip-blue");
      integrityChip.classList.add(integrityView.chipClass);
      integrityChip.textContent = integrityView.chip;
    }
    if (integrityTitle) integrityTitle.textContent = integrityView.title;
    if (integrityMessage) integrityMessage.textContent = integrityView.message;
    if (integrityRetry) {
      integrityRetry.hidden = !state.integrityRecheckAvailable ||
        integrityState !== "check_unavailable" || integrity.retryable === false;
      integrityRetry.disabled = false;
      integrityRetry.textContent = "重新检查内容";
    }
  }

  function bindCandidate(candidate) {
    if (!candidate) return;
    const chapter = candidate.chapter_id || "当前章节";
    const heading = notesStateHost.querySelector("[data-candidate-heading]");
    if (heading) heading.textContent = `《${chapter}》的新版本已经准备好。`;
    const context = notesStateHost.querySelector("[data-candidate-context]");
    if (context) context.textContent = `章节 / ${chapter}`;
    notesStateHost.querySelectorAll("[data-candidate-title]").forEach((node) => {
      node.textContent = chapter;
    });
    const stripHeading = (markdown) => String(markdown || "").replace(/^#{1,6}\s+.+\n+/, "");
    const currentMarkdown = stripHeading(candidate.current_chapter_markdown);
    const newMarkdown = stripHeading(candidate.candidate_markdown);
    const currentContent = notesStateHost.querySelector("[data-candidate-current-content]");
    if (currentContent) currentContent.innerHTML = markdownToEditorHtml(currentMarkdown);
    const newContent = notesStateHost.querySelector("[data-candidate-new-content]");
    if (newContent) newContent.innerHTML = markdownToEditorHtml(newMarkdown);
    const currentCount = notesStateHost.querySelector("[data-candidate-current-count]");
    if (currentCount) currentCount.textContent = `包含你的编辑 · ${Array.from(currentMarkdown).length.toLocaleString()} 字`;
    const newCount = notesStateHost.querySelector("[data-candidate-new-count]");
    if (newCount) newCount.textContent = `新候选 · ${Array.from(newMarkdown).length.toLocaleString()} 字 · 尚未保存`;
  }

  function bindChapterProgress(task) {
    const chapters = task.chapters || [];
    const total = chapters.length;
    const completed = chapters.filter((chapter) => chapter.status === "complete");
    const running = chapters.find((chapter) => chapter.status === "running");
    const failed = chapters.find((chapter) => chapter.status === "failed");
    const percent = total ? Math.round((completed.length / total) * 10000) / 100 : 0;
    const taskLabel = notesStateHost.querySelector("[data-chapter-task-label]");
    if (taskLabel) {
      taskLabel.textContent = `TASK ${String(task.id || "").slice(0, 8).toUpperCase()} // OUTLINE LOCKED`;
    }
    const meterCount = notesStateHost.querySelector("[data-chapter-meter-count]");
    if (meterCount) meterCount.textContent = `${completed.length} / ${total}`;
    const meterLabel = notesStateHost.querySelector("[data-chapter-meter-label]");
    if (meterLabel) {
      meterLabel.textContent = running
        ? `章节完成 · 正在第 ${running.position} 章`
        : failed ? `章节完成 · 第 ${failed.position} 章失败` : "章节完成 · 准备下一步";
    }
    const progressbar = notesStateHost.querySelector("[data-chapter-progressbar]");
    if (progressbar) {
      progressbar.setAttribute("aria-valuemax", String(total));
      progressbar.setAttribute("aria-valuenow", String(completed.length));
      progressbar.setAttribute("aria-valuetext", `${completed.length} / ${total} 章已完成`);
    }
    const meterFill = notesStateHost.querySelector("[data-chapter-meter-fill]");
    if (meterFill) {
      meterFill.style.width = `${percent}%`;
      meterFill.classList.toggle("is-active", task.state === "generating_chapters");
    }

    const savedTitle = notesStateHost.querySelector("[data-chapter-saved-title]");
    if (savedTitle) savedTitle.textContent = `已安全保存 ${completed.length} / ${total} 章`;
    const savedCopy = notesStateHost.querySelector("[data-chapter-saved-copy]");
    if (savedCopy) {
      savedCopy.textContent = running
        ? `第 ${running.position} 章《${running.title}》正在生成。已完成章节已经写入本地，即使本章失败也不会丢失。`
        : failed
          ? `第 ${failed.position} 章《${failed.title}》生成失败；前 ${completed.length} 章仍然安全保留。`
          : total
            ? `已创建 ${total} 章任务，正在准备第一章。`
            : "正在创建已确认大纲对应的章节任务。";
    }
    const latestCompleted = completed.at(-1);
    const contextSummary = notesStateHost.querySelector("[data-chapter-context-summary]");
    if (contextSummary) {
      const summary = String(latestCompleted?.context_summary || "")
        .replace(/[#>*_`\[\]]/g, " ").replace(/\s+/g, " ").trim();
      contextSummary.textContent = summary
        ? `${summary.slice(0, 110)}${summary.length > 110 ? "…" : ""}`
        : "第一章完成后会在这里显示真实上下文摘要";
    }
    const panel = notesStateHost.querySelector("[data-chapter-saved-panel]");
    const nextPosition = running?.position || failed?.position || 0;
    if (panel && panel.dataset.chapterPosition !== String(nextPosition)) {
      panel.dataset.chapterPosition = String(nextPosition);
      panel.classList.remove("is-updating");
      requestAnimationFrame(() => panel.classList.add("is-updating"));
    }
  }

  function bindChapterFailure(task) {
    const title = notesStateHost.querySelector("[data-chapter-failure-title]");
    if (!title) return;
    const chapters = task.chapters || [];
    const failed = chapters.find((chapter) => chapter.status === "failed");
    const completed = chapters.filter((chapter) => chapter.status === "complete");
    const eyebrow = notesStateHost.querySelector("[data-chapter-failure-eyebrow]");
    const copy = notesStateHost.querySelector("[data-chapter-failure-copy]");
    const attempt = notesStateHost.querySelector("[data-chapter-failure-attempt]");
    const continueButton = notesStateHost.querySelector("[data-continue-chapter]");
    if (!failed) {
      if (eyebrow) eyebrow.textContent = "GENERATION // RETRY AVAILABLE";
      title.textContent = "笔记生成暂时中断。";
      if (copy) copy.textContent = task.error_message || "任务可以安全重试，现有输入与设置仍然保留。";
      if (attempt) attempt.textContent = "等待重试";
      if (continueButton) continueButton.hidden = true;
      return;
    }
    const attempts = Math.max(Number(failed.attempt_count) || 1, 1);
    if (eyebrow) {
      eyebrow.textContent = `CHAPTER ${String(failed.position).padStart(2, "0")} // RETRY AVAILABLE`;
    }
    title.textContent = attempts === 1
      ? `第 ${failed.position} 章《${failed.title}》生成未完成。`
      : `第 ${failed.position} 章《${failed.title}》第 ${attempts} 次尝试仍未完成。`;
    if (copy) {
      copy.textContent = completed.length
        ? `已安全保存 ${completed.length} / ${chapters.length} 章。你可以从第 ${failed.position} 章继续，已完成内容不会丢失。`
        : `尚无已完成章节；失败发生在第一章。你可以从第 ${failed.position} 章继续，逐字稿、最终设置和大纲仍然保留。`;
    }
    if (attempt) attempt.textContent = `本章尝试 ${attempts} 次`;
    if (continueButton) {
      continueButton.hidden = false;
      continueButton.textContent = `从第 ${failed.position} 章继续`;
    }
  }

  function bindRecommendation(recommendation) {
    if (!recommendation) return;
    const currentPlan = state.noteTask?.final_settings || null;
    const structure = recommendation.structure || {};
    const structureOptions = structure.options || [];
    const detailOptions = (recommendation.detail?.options || []).map((option) => {
      const id = typeof option === "string" ? option : option.id;
      return typeof option === "string"
        ? { id, label: detailLabels[id] || id, reason: "根据本次内容密度选择。" }
        : option;
    });
    const methodOptions = (recommendation.method?.options || []).map((option) => {
      const id = typeof option === "string" ? option : option.id;
      return typeof option === "string"
        ? { id, label: methodLabels[id] || id, reason: id === "outline" ? "先确认章节结构再逐章生成。" : "直接得到完整结果。" }
        : option;
    });
    const recommendedStructure = structureOptions.find(
      (option) => option.id === structure.recommended_id
    ) || structureOptions[0];
    const detailId = recommendation.detail?.recommended_id || "complete";
    const methodId = recommendation.method?.recommended_id || "direct";
    const moduleIds = (recommendation.modules?.recommended_ids || []).slice(0, 3);
    const selectedStructureId = currentPlan?.structure?.id || structure.recommended_id;
    const selectedDetailId = currentPlan?.detail?.id || detailId;
    const selectedMethodId = currentPlan?.method || methodId;
    const selectedModuleIds = currentPlan
      ? (currentPlan.modules || []).map((module) => module.id)
      : moduleIds;

    const cardValues = {
      structure: [recommendedStructure?.label || "沿原文脉络", structure.reason || recommendation.reason],
      detail: [detailLabels[detailId] || "完整详解", recommendation.detail?.reason || recommendation.reason],
      method: [methodLabels[methodId] || "一次性生成", recommendation.method?.reason || recommendation.reason],
      modules: [moduleIds.length ? `${moduleIds.length} 项` : "只要正文", moduleIds.map((id) => moduleLabels[id]).filter(Boolean).join(" · ") || "不额外增加模块"],
    };
    Object.entries(cardValues).forEach(([name, values]) => {
      const card = notesStateHost.querySelector(`[data-recommendation-card="${name}"]`);
      if (!card) return;
      const strong = card.querySelector("strong");
      const paragraph = card.querySelector("p");
      if (strong) strong.textContent = values[0];
      if (paragraph) paragraph.textContent = values[1];
    });

    const customReason = notesStateHost.querySelector("[data-custom-recommendation-reason]");
    if (customReason) customReason.textContent = recommendation.reason;
    const structureQuestion = notesStateHost.querySelector("[data-structure-question]");
    if (structureQuestion) structureQuestion.textContent = structure.question || "这份笔记最适合怎样组织？";
    const structureReason = notesStateHost.querySelector("[data-structure-reason]");
    if (structureReason) structureReason.textContent = structure.reason || recommendation.reason;
    const structureHost = notesStateHost.querySelector("[data-structure-options]");
    if (structureHost) {
      structureHost.innerHTML = structureOptions.map((option) => {
        const selected = option.id === selectedStructureId;
        const recommended = option.id === structure.recommended_id;
        return `<button class="choice-card ${selected ? "is-selected" : ""}" type="button" data-choice="${escapeHtml(option.id)}">
          ${recommended ? '<span class="chip chip-blue">AI 推荐</span>' : ""}
          <strong>${escapeHtml(option.label)}</strong><small>${escapeHtml(option.reason || "可用于本次内容")}</small></button>`;
      }).join("");
    }
    const detailReason = notesStateHost.querySelector("[data-detail-reason]");
    if (detailReason) detailReason.textContent = recommendation.detail?.reason || recommendation.reason;
    const detailQuestion = notesStateHost.querySelector("[data-detail-question]");
    if (detailQuestion) detailQuestion.textContent = recommendation.detail?.question || "这次需要保留多少解释、案例和原话？";
    const methodReason = notesStateHost.querySelector("[data-method-reason]");
    if (methodReason) methodReason.textContent = recommendation.method?.reason || recommendation.reason;
    const methodQuestion = notesStateHost.querySelector("[data-method-question]");
    if (methodQuestion) methodQuestion.textContent = recommendation.method?.question || "生成正文前，要不要先确认大纲？";
    const modulesQuestion = notesStateHost.querySelector("[data-modules-question]");
    if (modulesQuestion) modulesQuestion.textContent = recommendation.modules?.question || "正文之外，还需要哪些复习工具？";
    const renderDecisionOptions = (selector, options, selectedId, recommendedId) => {
      const host = notesStateHost.querySelector(selector);
      if (!host || !options.length) return;
      host.innerHTML = options.map((option) => `<button class="choice-card ${option.id === selectedId ? "is-selected" : ""}" type="button" data-choice="${escapeHtml(option.id)}">
        ${option.id === recommendedId ? '<span class="chip chip-blue">AI 推荐</span>' : ""}
        <strong>${escapeHtml(option.label)}</strong><small>${escapeHtml(option.reason || "根据本次内容判断")}</small></button>`).join("");
    };
    renderDecisionOptions("[data-detail-options]", detailOptions, selectedDetailId, detailId);
    renderDecisionOptions("[data-method-options]", methodOptions, selectedMethodId, methodId);
    [
      ["detail", selectedDetailId, detailId], ["method", selectedMethodId, methodId],
    ].forEach(([groupName, selectedId, recommendedId]) => {
      const group = notesStateHost.querySelector(`[data-setting-group="${groupName}"]`);
      if (!group) return;
      group.querySelectorAll(".choice-card").forEach((card) => {
        const selected = card.dataset.choice === selectedId;
        card.classList.toggle("is-selected", selected);
        card.querySelector(".chip")?.remove();
        if (card.dataset.choice === recommendedId) {
          card.insertAdjacentHTML("afterbegin", '<span class="chip chip-blue">AI 推荐</span>');
        }
      });
    });
    notesStateHost.querySelectorAll(".module-choice").forEach((choice) => {
      const selected = choice.hasAttribute("data-module-none")
        ? selectedModuleIds.length === 0
        : selectedModuleIds.includes(choice.dataset.module);
      const input = choice.querySelector("input");
      if (input) input.checked = selected;
      choice.classList.toggle("is-selected", selected);
      const small = choice.querySelector("small");
      const moduleReason = choice.hasAttribute("data-module-none")
        ? (moduleIds.length === 0 ? "AI 判断正文已经足够。" : "不额外增加复习模块。")
        : recommendation.modules?.reasons?.[choice.dataset.module];
      if (small && moduleReason) small.textContent = moduleReason;
    });
    const additionalRequest = notesStateHost.querySelector("#custom-other-request");
    if (additionalRequest && currentPlan) {
      additionalRequest.value = currentPlan.additional_request || "";
    }
  }

  async function createNoteAnalysis(generationRoute = state.selectedGenerationRoute) {
    if (state.noteTask && currentNotesState === "stale") {
      setNotesState("analyzing");
      await noteCommand({ type: "update_transcript", transcript: state.inputTranscript });
      await noteCommand({ type: "retry_analysis" });
      await pollNote(state.noteTask.id);
      return;
    }
    if (!["free", "paid"].includes(generationRoute)) {
      throw new Error("请先选择免费线路或高速体验线路");
    }
    if (currentNotesState === "analysis-failure" && state.noteTask?.state === "analysis_failed") {
      setNotesState("analyzing");
      if (state.noteTask.client_poll_failure) {
        if (state.noteTask.error_code === "NOTE_TASK_NOT_FOUND") {
          state.inputTranscript = state.noteTask.basis_transcript || state.inputTranscript;
          state.noteTask = null;
          await createNoteAnalysis();
          return;
        }
        const taskId = state.noteTask.id;
        state.noteTask = {
          ...state.noteTask,
          state: state.noteTask.failed_from_state || "analyzing",
          client_poll_failure: false,
          error_code: null,
          error_message: null,
        };
        await pollNote(taskId);
        return;
      }
      await noteCommand({ type: "retry_analysis" });
      await pollNote(state.noteTask.id);
      return;
    }
    let source;
    if (state.sourceMode === "linked" && state.parserRecord) {
      source = { type: "parser", parser_record_id: state.parserRecord.id };
    } else {
      const textarea = notesStateHost.querySelector(".notes-textarea");
      state.inputTranscript = (textarea?.value || state.inputTranscript).trim();
      if (!state.inputTranscript) throw new Error("请先粘贴逐字稿或选择 TXT / MD 文件");
      source = state.uploadedTranscript
        ? { type: "file", name: state.uploadedTranscript.name, transcript: state.inputTranscript }
        : { type: "paste", name: "粘贴文本", transcript: state.inputTranscript };
    }
    const requestText = notesStateHost.querySelector(".notes-request")?.value || state.noteRequestText || "";
    state.noteRequestText = requestText;
    state.selectedGenerationRoute = generationRoute;
    const workspaceToken = state.noteWorkspaceToken;
    setNotesState("analyzing");
    const payload = await request("/api/v3/note-tasks", {
      method: "POST",
      body: JSON.stringify({
        device_id: state.deviceId,
        source,
        request_text: requestText,
        generation_route: generationRoute,
      }),
    });
    if (workspaceToken !== state.noteWorkspaceToken) return;
    state.noteTask = payload.task;
    refreshAccessStatus().catch(() => {});
    await pollNote(payload.task.id);
  }

  async function noteCommand(command) {
    if (!state.noteTask) throw new Error("当前没有笔记任务");
    const workspaceToken = state.noteWorkspaceToken;
    const taskId = state.noteTask.id;
    const payload = await request(`/api/v3/note-tasks/${taskId}/commands`, {
      method: "POST", body: JSON.stringify(command),
    });
    if (workspaceToken !== state.noteWorkspaceToken) {
      const error = new Error("已离开当前笔记工作区");
      error.code = "NOTE_WORKSPACE_LEFT";
      throw error;
    }
    state.noteTask = payload.task;
    return payload.task;
  }

  async function startRealGeneration() {
    if (state.pendingTitle) {
      await noteCommand({ type: "update_title", title: state.pendingTitle });
      state.pendingTitle = "";
    }
    const custom = currentNotesState === "custom";
    if (custom) {
      const structure = notesStateHost.querySelector('[data-setting-group="structure"] .choice-card.is-selected')?.dataset.choice || "source_flow";
      const method = notesStateHost.querySelector('[data-setting-group="method"] .choice-card.is-selected')?.dataset.choice || "direct";
      const detail = notesStateHost.querySelector('[data-setting-group="detail"] .choice-card.is-selected')?.dataset.choice || "complete";
      const modules = [...notesStateHost.querySelectorAll(".module-choice input:checked")]
        .map((input) => input.closest(".module-choice")?.dataset.module)
        .filter(Boolean);
      const additionalRequest = notesStateHost.querySelector("#custom-other-request")?.value.trim() || "";
      await noteCommand({
        type: "save_settings",
        settings: { structure, method, detail, modules, additional_request: additionalRequest },
      });
    }
    const predictedMethod = custom
      ? notesStateHost.querySelector('[data-setting-group="method"] .choice-card.is-selected')?.dataset.choice
      : state.noteTask.recommendation?.method?.recommended_id;
    setNotesState(predictedMethod === "outline" ? "outline-regenerating" : "direct-generating");
    await noteCommand({ type: "start_generation" });
    await pollNote(state.noteTask.id);
  }

  async function openCurrentNote() {
    if (!state.noteTask?.note_id) throw new Error("成品笔记尚未生成");
    const payload = await request(`/api/v3/notes/${state.noteTask.note_id}`);
    state.note = payload.note;
    state.regenerateFromNote = null;
    setNotesState("reading");
    bindNote();
  }

  function bindNoteRegeneration() {
    const original = state.regenerateFromNote || state.note;
    if (!original) return;
    const title = notesStateHost.querySelector("[data-regenerate-original-title]");
    if (title) title.textContent = original.title;
    const transcript = notesStateHost.querySelector("[data-regenerate-transcript]");
    if (transcript) transcript.value = original.basis_transcript || "";
    const count = notesStateHost.querySelector("[data-regenerate-character-count]");
    if (count) {
      count.textContent = `${Array.from(original.basis_transcript || "").length.toLocaleString()} 字 ＋`;
    }
    bindNoteGenerationChooser();
  }

  async function startNoteRegeneration() {
    const original = state.regenerateFromNote || state.note;
    if (!original) throw new Error("当前没有可重新生成的成品笔记");
    const requestText = notesStateHost.querySelector("#regenerate-note-request")?.value.trim() || "";
    const generationRoute = state.selectedGenerationRoute;
    if (!["free", "paid"].includes(generationRoute)) {
      throw new Error("请先为这次重新生成选择免费线路或高速体验线路");
    }
    const workspaceToken = state.noteWorkspaceToken;
    try {
      const payload = await request("/api/v3/note-tasks", {
        method: "POST",
        body: JSON.stringify({
          device_id: state.deviceId,
          source: { type: "note", note_id: original.id },
          request_text: requestText,
          generation_route: generationRoute,
        }),
      });
      if (workspaceToken !== state.noteWorkspaceToken) return;
      state.noteTask = payload.task;
      refreshAccessStatus().catch(() => {});
      state.sourceMode = "regenerated";
      setNotesState("analyzing");
      await pollNote(payload.task.id);
    } catch (error) {
      setNotesState("regenerate");
      bindNoteRegeneration();
      throw error;
    }
  }

  function bindNote() {
    if (!state.note) return;
    notesStateHost.querySelectorAll("[data-note-title]").forEach((node) => {
      node.textContent = state.note.title;
    });
    const body = notesStateHost.querySelector(".note-body");
    if (body) {
      const withoutDuplicateTitle = state.note.current_markdown.replace(/^#\s+.+\n+/, "");
      const deck = notesStateHost.querySelector(".note-document:not(.note-document--editing) .note-deck");
      if (currentNotesState === "reading") renderStructuredNote(withoutDuplicateTitle, body, deck);
      else body.innerHTML = markdownToEditorHtml(withoutDuplicateTitle);
    }
    const sourceMeta = notesStateHost.querySelector(".note-kicker > span:not(.chip)");
    if (sourceMeta) {
      const source = state.note.source_snapshot || {};
      sourceMeta.textContent = [source.platform, source.creator].filter(Boolean).join(" · ") || source.type;
    }
    const byline = notesStateHost.querySelectorAll(".note-document:not(.note-document--editing) .note-byline span");
    if (byline[0]) byline[0].textContent = `生成 / ${new Date(state.note.created_at).toLocaleString("zh-CN")}`;
    if (byline[1]) byline[1].textContent = `修改 / ${new Date(state.note.updated_at).toLocaleString("zh-CN")}`;
    if (byline[2]) byline[2].textContent = `${state.note.current_markdown.length.toLocaleString()} 字`;
    const receipt = notesStateHost.querySelector(".reader-command-bar .eyebrow");
    if (receipt) receipt.textContent = `NOTE ${state.note.id.slice(0, 8).toUpperCase()} // CURRENT VERSION`;
    const saveLabel = notesStateHost.querySelector("[data-save-label]");
    if (saveLabel) saveLabel.textContent = `已保存 · ${new Date(state.note.updated_at).toLocaleString("zh-CN")}`;
    const version = notesStateHost.querySelector(".note-version-footer .eyebrow");
    if (version) version.textContent = `VERSION / ${String(state.note.version).padStart(2, "0")}`;
    const sourceDrawer = notesStateHost.querySelector(".reading-source-drawer > div");
    if (sourceDrawer) {
      const source = state.note.source_snapshot || {};
      sourceDrawer.innerHTML = `<p><strong>生成依据逐字稿：</strong>实际生成版本，共 ${state.note.basis_transcript.length.toLocaleString()} 字。</p>
        <p><strong>来源：</strong>${escapeHtml(source.title || source.name || "独立逐字稿")}${source.creator ? ` · ${escapeHtml(source.creator)}` : ""}${source.platform ? ` · ${escapeHtml(source.platform)}` : ""}</p>`;
    }
    const editable = notesStateHost.querySelector(".note-document--editing");
    if (editable) {
      editable.querySelectorAll("[data-editor-content]").forEach((node) => {
        node.removeAttribute("data-editor-content");
      });
      const title = editable.querySelector("[data-note-title]");
      if (title) {
        title.textContent = state.note.title;
      }
      const deck = editable.querySelector(".note-deck");
      if (deck) deck.hidden = true;
      const body = editable.querySelector(".note-body");
      if (body) {
        const withoutDuplicateTitle = state.note.current_markdown.replace(/^#\s+.+\n+/, "");
        body.innerHTML = markdownToEditorHtml(withoutDuplicateTitle);
        body.contentEditable = "true";
        body.classList.add("visual-editable");
        body.setAttribute("data-editor-content", "");
      }
    }
  }

  function bindExport() {
    if (!state.note) return;
    const previewTitle = notesStateHost.querySelector(".paper-lines strong");
    if (previewTitle) previewTitle.textContent = state.note.title;

    const headings = [...state.note.current_markdown.matchAll(/^##\s+(.+)$/gm)]
      .map((match) => match[1].trim())
      .slice(0, 2);
    notesStateHost.querySelectorAll(".paper-lines h4").forEach((heading, index) => {
      if (headings[index]) heading.textContent = `${String(index + 1).padStart(2, "0")} ${headings[index]}`;
    });

    const format = notesStateHost.querySelector('input[name="export-format"]:checked')?.value || "md";
    const extension = format === "pdf" ? "pdf" : "md";
    const safeTitle = state.note.title.trim()
      .replace(/[^a-zA-Z0-9\u4e00-\u9fff_-]+/g, "_")
      .replace(/^_+|_+$/g, "") || "笔记";
    const filename = notesStateHost.querySelector("[data-export-filename]");
    if (filename && format !== "copy") filename.textContent = `${safeTitle}.${extension}`;
  }

  async function saveEditor(checkpoint = false) {
    if (!state.note) return;
    const title = notesStateHost.querySelector("[data-note-title]")?.textContent.trim() || state.note.title;
    const editor = notesStateHost.querySelector("[data-editor-content]:not([data-note-title])");
    const bodyMarkdown = editor ? editorHtmlToMarkdown(editor) : state.note.current_markdown.replace(/^#\s+.+\n+/, "");
    const markdown = `# ${title}\n\n${bodyMarkdown}`.trim();
    const payload = await request(`/api/v3/notes/${state.note.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        expected_version: state.note.version, title, markdown, checkpoint,
      }),
    });
    state.note = payload.note;
    const status = notesStateHost.querySelector("[data-autosave-status]");
    if (status) status.textContent = "已自动保存 · 刚刚";
  }

  async function showParserHistory(reset = true) {
    if (reset) {
      state.parserHistoryCursor = null;
      state.parserHistoryIds = new Set();
      setParserState("history");
    }
    const cursor = state.parserHistoryCursor
      ? `&cursor=${encodeURIComponent(state.parserHistoryCursor)}` : "";
    const payload = await request(`/api/v3/parser/records?limit=30${cursor}`);
    const list = stateHost.querySelector(".history-list");
    if (!list) return;
    const items = payload.items.filter((record) => !state.parserHistoryIds.has(record.id));
    if (!items.length && reset) {
      list.innerHTML = '<div class="empty-state framed-panel"><div><h3>还没有解析记录。</h3><p>完成一次视频解析后，会在这里保留来源和处理状态。</p></div></div>';
    } else if (reset) {
      list.innerHTML = "";
    }
    items.forEach((record) => state.parserHistoryIds.add(record.id));
    list.insertAdjacentHTML("beforeend", items.map((record) => {
      const hasTranscript = Boolean(String(record.transcript_text || "").trim());
      const statusLabel = record.note_id ? "已生成笔记" : hasTranscript ? "逐字稿已生成" : "待生成逐字稿";
      const statusCopy = hasTranscript ? "逐字稿已保存" : "尚未生成逐字稿";
      return `
      <article class="history-item ${record.note_id ? "is-linked" : ""}" data-real-record="${record.id}">
        <div class="history-thumb"></div><div class="history-copy"><div class="history-line">
        <span class="chip ${record.note_id ? "chip-green" : "chip-blue"}">${statusLabel}</span>
        <span class="meta">${escapeHtml(platformLabel(record.platform))}</span></div>
        <h3>${escapeHtml(record.title)}</h3><p>${escapeHtml(record.creator || "未知作者")} · ${Math.floor((record.duration_seconds || 0) / 60)} 分钟 · ${statusCopy}</p></div>
        <div class="history-actions">${record.note_id ? `<button class="text-action" type="button" data-real-open-linked-note="${record.note_id}">查看已生成笔记 →</button>` : `<button class="text-action" type="button" data-real-use-record="${record.id}">查看记录 →</button>`}
        <button class="text-action" type="button" data-real-delete-record="${record.id}">删除</button></div>
      </article>`;
    }).join(""));
    state.parserHistoryCursor = payload.next_cursor;
    const section = list.closest(".history-section");
    let loadMore = section?.querySelector("[data-load-more-parser]");
    if (!loadMore && section) {
      loadMore = document.createElement("button");
      loadMore.className = "load-more-button";
      loadMore.type = "button";
      loadMore.dataset.loadMoreParser = "";
      loadMore.textContent = "加载更早的解析记录 ↓";
      section.insertBefore(loadMore, section.querySelector(".history-foot"));
    }
    if (loadMore) loadMore.hidden = !state.parserHistoryCursor;
  }

  async function showRecovery(reset = true) {
    if (reset) {
      state.recoveryCursor = null;
      state.recoveryTaskIds = new Set();
      setNotesState("recovery");
    }
    const cursor = state.recoveryCursor
      ? `&cursor=${encodeURIComponent(state.recoveryCursor)}` : "";
    const payload = await request(`/api/v3/note-tasks?device_id=${encodeURIComponent(state.deviceId)}&limit=30${cursor}`);
    const list = notesStateHost.querySelector(".recovery-list");
    if (!list) return;
    const items = payload.items.filter((task) => !state.recoveryTaskIds.has(task.id));
    if (!items.length && reset) {
      list.innerHTML = '<article><span class="status-rail waiting"></span><div><strong>没有可恢复任务</strong><small>新任务开始后会自动保存在当前电脑。</small></div></article>';
    } else if (reset) {
      list.innerHTML = "";
    }
    const presentation = {
      recommendation_ready: ["waiting", "等待设置", "继续设置"],
      recommendation_stale: ["failed", "需要重新分析", "继续处理"],
      analysis_failed: ["failed", "预读失败", "重试分析"],
      outline_ready: ["outline", "等待大纲", "查看大纲"],
      outline_regenerating: ["running", "重拟大纲", "重新连接"],
      generating_chapters: ["running", "逐章生成", "重新连接"],
      chapter_failed: ["failed", "需要处理", "处理失败"],
      generation_failed: ["failed", "生成中断", "继续处理"],
      generating_direct: ["running", "直接生成", "重新连接"],
      complete: ["complete", "已完成", "打开结果"],
      analyzing: ["running", "预读中", "重新连接"],
    };
    items.forEach((task) => state.recoveryTaskIds.add(task.id));
    list.insertAdjacentHTML("beforeend", items.map((task) => {
      const item = presentation[task.state] || ["waiting", task.state, "继续任务"];
      const progress = task.progress?.label || task.error_message || "本地任务状态已保存";
      return `<article><span class="status-rail ${item[0]}"></span><div><span class="meta">${escapeHtml(item[1])}</span>
        <strong>${escapeHtml(task.proposed_title || task.source_name || "未命名笔记任务")}</strong><small>${escapeHtml(progress)}</small></div>
        <button class="button button-secondary" type="button" data-real-resume-task="${task.id}">${item[2]}</button></article>`;
    }).join(""));
    state.recoveryCursor = payload.next_cursor;
    const section = list.closest(".recovery-stack");
    let loadMore = section?.querySelector("[data-load-more-tasks]");
    if (!loadMore && section) {
      loadMore = document.createElement("button");
      loadMore.className = "load-more-button";
      loadMore.type = "button";
      loadMore.dataset.loadMoreTasks = "";
      loadMore.textContent = "加载更早的任务 ↓";
      section.insertBefore(loadMore, section.querySelector(".recovery-note"));
    }
    if (loadMore) loadMore.hidden = !state.recoveryCursor;
  }

  async function showHistory(reset = true) {
    if (reset) {
      state.noteHistoryCursor = null;
      state.noteHistoryIds = new Set();
      setNotesState("note-history");
    }
    const cursor = state.noteHistoryCursor
      ? `&cursor=${encodeURIComponent(state.noteHistoryCursor)}` : "";
    const payload = await request(`/api/v3/notes?limit=30${cursor}`);
    const list = notesStateHost.querySelector(".note-history-list");
    if (!list) return;
    const items = payload.items.filter((note) => !state.noteHistoryIds.has(note.id));
    if (!items.length && reset) {
      list.innerHTML = '<article><div class="note-history-index">N0</div><div><h3>还没有成品笔记。</h3><p>完成一次生成后，会在这里保留最新版本。</p></div></article>';
    } else if (reset) {
      list.innerHTML = "";
    }
    const startIndex = state.noteHistoryIds.size;
    items.forEach((note) => state.noteHistoryIds.add(note.id));
    list.insertAdjacentHTML("beforeend", items.map((note, index) => `
      <article class="${startIndex + index === 0 ? "is-featured" : ""}" data-real-note="${note.id}">
        <div class="note-history-index">N${startIndex + index + 1}</div>
        <div><div class="history-line"><span class="chip chip-green">已完成</span>
        <span class="meta">${escapeHtml(note.source_type)}</span></div><h3>${escapeHtml(note.title)}</h3>
        <p>当前版本 v${note.version} · 本地保存</p></div>
        <div class="history-actions"><button class="text-action" type="button" data-real-open-note="${note.id}">打开笔记 →</button>
        ${note.parser_record_id ? `<button class="text-action" type="button" data-real-open-parser-record="${note.parser_record_id}">查看来源解析</button>` : ""}
        <button class="text-action" type="button" data-real-delete-note="${note.id}">删除</button></div>
      </article>`).join(""));
    state.noteHistoryCursor = payload.next_cursor;
    const loadMore = notesStateHost.querySelector("[data-load-more]");
    if (loadMore) loadMore.hidden = !state.noteHistoryCursor;
  }

  function resetNoteWorkspace(message = "已回到笔记首页。已完成的笔记仍保留在笔记历史中。") {
    state.noteWorkspaceToken += 1;
    state.notePollToken += 1;
    clearTimeout(state.saveTimer);
    state.noteTask = null;
    state.note = null;
    state.regenerateFromNote = null;
    state.candidate = null;
    state.inputTranscript = "";
    state.uploadedTranscript = null;
    state.noteRequestText = "";
    state.selectedGenerationRoute = null;
    state.sourceMode = "independent";
    state.pendingTitle = "";
    switchView("notes");
    setNotesState("input");
    bindFreeCapacityNotices({ host: notesStateHost, transcript: "" });
    runtimeMessage(message);
    window.scrollTo({ top: document.querySelector("#notes")?.offsetTop || 0, behavior: "smooth" });
  }

  async function abandonNoteWorkspace() {
    const taskId = state.noteTask?.id;
    if (taskId) {
      await request(`/api/v3/note-tasks/${taskId}`, { method: "DELETE" });
    }
    document.querySelector("#new-note-dialog")?.close();
    resetNoteWorkspace("已放弃本次笔记并删除未完成进度。");
  }

  document.addEventListener("submit", async (event) => {
    if (event.target.id !== "parser-form") return;
    if (document.body.classList.contains("public-demo-active")) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (state.parserSubmitting) {
      runtimeMessage("当前解析任务仍在进行，请等待完成后再提交新的链接。");
      return;
    }
    const pollToken = ++state.parserPollToken;
    setParserBusy(true);
    try {
      setParserState("loading");
      bindParserProgress({ id: "", operation: "metadata", progress: { stage: "resolve", label: "创建解析任务", percent: 5 } });
      const payload = await request("/api/v3/parser/tasks", {
        method: "POST",
        body: JSON.stringify({
          device_id: state.deviceId,
          source_url: videoLink.value.trim(),
          include_transcript: false,
        }),
      });
      state.parserTask = payload.task;
      videoLink.value = payload.task.source_url;
      bindParserProgress(payload.task);
      await pollParser(payload.task.id, pollToken);
    } catch (error) {
      if (pollToken === state.parserPollToken) {
        setParserState("failure");
        bindParserFailure({
          ...state.parserTask,
          error_message: error.message,
          error_retryable: true,
        });
        runtimeMessage(error.message, true);
      }
    } finally {
      if (pollToken === state.parserPollToken) setParserBusy(false);
    }
  }, true);

  document.addEventListener("click", async (event) => {
    const target = event.target.closest("button");
    if (!target) return;
    if (
      document.body.classList.contains("public-demo-active") &&
      target.dataset.copyTranscript === undefined &&
      target.dataset.copyReadyTranscript === undefined &&
      target.dataset.copySkillInstall === undefined &&
      target.dataset.copyUniversalPrompt === undefined
    ) return;
    const realAction = target.dataset.openNotes !== undefined ||
      target.dataset.startAnalysis !== undefined || target.dataset.prepareNotes !== undefined ||
      target.dataset.copyReadyTranscript !== undefined ||
      target.dataset.downloadReadyTranscript !== undefined ||
      target.dataset.selectNoteRoute !== undefined ||
      target.dataset.confirmNoteRoute !== undefined || target.dataset.phase3 !== undefined ||
      target.dataset.confirmOutline !== undefined || target.dataset.regenerateOutline !== undefined ||
      target.dataset.continueChapter !== undefined || target.dataset.phase4 !== undefined ||
      target.dataset.recheckIntegrity !== undefined ||
      target.dataset.editNote !== undefined || target.dataset.finishEdit !== undefined ||
      target.dataset.exportNote !== undefined || target.dataset.runExport !== undefined ||
      target.dataset.openNoteHistory !== undefined || target.dataset.openParserHistory !== undefined ||
      target.dataset.openTaskRecovery !== undefined || target.dataset.fakeUpload !== undefined ||
      target.dataset.download !== undefined || target.dataset.copyTranscript !== undefined ||
      target.dataset.copySkillInstall !== undefined || target.dataset.copyUniversalPrompt !== undefined ||
      target.dataset.generateTranscript !== undefined ||
      target.dataset.regenerateTranscript !== undefined ||
      target.dataset.cancelTranscriptRegeneration !== undefined ||
      target.dataset.retryTranscription !== undefined ||
      target.dataset.switchTranscription !== undefined ||
      target.dataset.dismissTranscriptionError !== undefined ||
      target.dataset.toggleTranscript !== undefined || target.dataset.retry !== undefined ||
      target.dataset.resumeLater !== undefined || target.dataset.restartGeneration !== undefined ||
      target.dataset.confirmRestore !== undefined || target.dataset.realOpenNote ||
      target.dataset.realDeleteNote || target.dataset.confirmNoteDelete !== undefined ||
      target.dataset.realResumeTask || target.dataset.realUseRecord ||
      target.dataset.realDeleteRecord || target.dataset.realOpenLinkedNote ||
      target.dataset.realOpenParserRecord || target.dataset.confirmDelete !== undefined ||
      target.dataset.regenerateChapter !== undefined ||
      target.dataset.regenerateNote !== undefined ||
      target.dataset.regeneratePrompt !== undefined ||
      target.dataset.cancelRegenerate !== undefined ||
      target.dataset.confirmRegenerate !== undefined ||
      target.dataset.notesStateJump !== undefined ||
      target.dataset.acceptCandidate !== undefined || target.dataset.keepCurrent !== undefined ||
      target.dataset.loadMore !== undefined || target.dataset.loadMoreParser !== undefined ||
      target.dataset.loadMoreTasks !== undefined || target.dataset.newNote !== undefined ||
      target.dataset.abandonNote !== undefined ||
      target.dataset.confirmAbandonNote !== undefined || target.dataset.nav !== undefined;
    if (!realAction) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    try {
      if (target.dataset.copySkillInstall !== undefined) {
        await copyOpenNoteResource(target, "skill");
      } else if (target.dataset.copyUniversalPrompt !== undefined) {
        await copyOpenNoteResource(target, "prompt");
      } else if (target.dataset.copyReadyTranscript !== undefined) {
        await copyReadyTranscript(target);
      } else if (target.dataset.downloadReadyTranscript !== undefined) {
        downloadReadyTranscript(target.dataset.downloadReadyTranscript);
      } else if (target.dataset.selectNoteRoute !== undefined) {
        if (
          target.dataset.selectNoteRoute === "paid"
          && state.accessControlEnabled
          && !state.access
        ) {
          showAccessDialog("高速笔记线路目前仅对内测用户开放，请输入内测码后继续。");
          return;
        }
        state.selectedGenerationRoute = target.dataset.selectNoteRoute;
        bindNoteGenerationChooser();
      } else if (target.dataset.confirmNoteRoute !== undefined) {
        await createNoteAnalysis(state.selectedGenerationRoute);
      } else if (target.dataset.generateTranscript !== undefined) {
        if (!state.parserRecord) throw new Error("当前没有可生成逐字稿的视频记录");
        const replaceExisting = target.dataset.replaceExisting !== undefined;
        if (state.parserRecord.transcript_text && !replaceExisting) {
          throw new Error("这条视频已经生成过逐字稿");
        }
        if (state.parserSubmitting) return;
        const provider = target.dataset.generateTranscript;
        if (provider === "cloudflare" && state.accessControlEnabled && !state.access) {
          showAccessDialog("高速转录目前仅对内测用户开放，请输入内测码后继续。");
          return;
        }
        const pollToken = ++state.parserPollToken;
        setParserBusy(true);
        try {
          bindTranscriptionProgress({
            transcription_provider: provider,
            progress: { label: "创建逐字稿任务", percent: 5 },
          });
          const payload = await request(
            `/api/v3/parser/records/${encodeURIComponent(state.parserRecord.id)}/transcription-tasks`,
            {
              method: "POST",
              body: JSON.stringify({
                device_id: state.deviceId,
                provider,
                replace_existing: replaceExisting,
              }),
            },
          );
          state.parserTask = payload.task;
          await pollTranscription(payload.task.id, pollToken);
        } catch (error) {
          if (pollToken === state.parserPollToken) {
            showTranscriptionError(error);
          }
          throw error;
        } finally {
          if (pollToken === state.parserPollToken) setParserBusy(false);
        }
      } else if (target.dataset.regenerateTranscript !== undefined) {
        const chooser = stateHost.querySelector("[data-transcript-regenerate]");
        const errorPanel = stateHost.querySelector("[data-transcription-error]");
        if (chooser) chooser.hidden = false;
        if (errorPanel) errorPanel.hidden = true;
        chooser?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      } else if (target.dataset.cancelTranscriptRegeneration !== undefined) {
        const chooser = stateHost.querySelector("[data-transcript-regenerate]");
        if (chooser) chooser.hidden = true;
      } else if (target.dataset.dismissTranscriptionError !== undefined) {
        const errorPanel = stateHost.querySelector("[data-transcription-error]");
        const chooser = stateHost.querySelector("[data-transcript-regenerate]");
        if (errorPanel) errorPanel.hidden = true;
        if (chooser) chooser.hidden = true;
      } else if (target.dataset.switchTranscription !== undefined) {
        const errorPanel = stateHost.querySelector("[data-transcription-error]");
        if (errorPanel) errorPanel.hidden = true;
        if (state.parserRecord?.transcript_text) {
          const chooser = stateHost.querySelector("[data-transcript-regenerate]");
          if (chooser) chooser.hidden = false;
        }
      } else if (target.dataset.retryTranscription !== undefined) {
        if (!state.parserTask || state.parserTask.state !== "failed") {
          throw new Error("当前没有可以重试的逐字稿任务");
        }
        if (state.parserSubmitting) return;
        const pollToken = ++state.parserPollToken;
        setParserBusy(true);
        try {
          bindTranscriptionProgress(state.parserTask);
          const payload = await request(
            `/api/v3/parser/tasks/${encodeURIComponent(state.parserTask.id)}/commands`,
            {
              method: "POST",
              body: JSON.stringify({ command: "retry" }),
            },
          );
          state.parserTask = payload.task;
          await pollTranscription(payload.task.id, pollToken);
        } catch (error) {
          if (pollToken === state.parserPollToken) showTranscriptionError(error);
          throw error;
        } finally {
          if (pollToken === state.parserPollToken) setParserBusy(false);
        }
      } else if (target.dataset.copyTranscript !== undefined) {
        await copyParserTranscript(target);
      } else if (target.dataset.toggleTranscript !== undefined) {
        const transcript = target.closest(".transcript-panel")?.querySelector(".transcript-preview");
        if (!transcript) return;
        const expanded = transcript.classList.contains("is-collapsed");
        if (window.VTNMotion?.toggleTranscript) {
          window.VTNMotion.toggleTranscript(transcript, expanded);
        } else {
          transcript.classList.toggle("is-collapsed", !expanded);
        }
        target.setAttribute("aria-expanded", String(expanded));
        target.textContent = expanded ? "收起逐字稿 ↑" : "展开完整逐字稿 ↓";
      } else if (target.dataset.newNote !== undefined) {
        resetNoteWorkspace();
      } else if (target.dataset.abandonNote !== undefined) {
        document.querySelector("#new-note-dialog")?.showModal();
      } else if (target.dataset.confirmAbandonNote !== undefined) {
        await abandonNoteWorkspace();
      } else if (target.dataset.nav !== undefined) {
        const view = target.dataset.nav;
        const activeArchive = view === "notes"
          ? !notesView.hidden && Boolean(notesStateHost.querySelector(".note-history-stack, .recovery-stack"))
          : !parserView.hidden && Boolean(stateHost.querySelector(".history-section"));
        switchView(view);
        if (activeArchive && view === "notes") {
          setNotesState("input");
        } else if (activeArchive) {
          setParserState(state.parserRecord ? "success" : "empty");
          if (state.parserRecord) bindParserRecord();
        }
      } else if (target.dataset.openNotes !== undefined) {
        if (!state.parserRecord?.transcript_text) {
          throw new Error("请先生成逐字稿，再继续生成笔记");
        }
        state.sourceMode = "linked";
        state.inputTranscript = state.parserRecord.transcript_text.trim();
        state.uploadedTranscript = null;
        state.noteRequestText = "";
        state.selectedGenerationRoute = null;
        switchView("notes");
        setNotesState("ready");
        bindTranscriptReady();
      } else if (target.dataset.notesStateJump !== undefined) {
        const nextState = target.dataset.notesStateJump;
        if (nextState === "input") {
          state.inputTranscript = "";
          state.uploadedTranscript = null;
          state.noteRequestText = "";
          state.selectedGenerationRoute = null;
        }
        setNotesState(nextState);
        if (nextState === "input") {
          bindFreeCapacityNotices({ host: notesStateHost, transcript: "" });
        }
        bindNoteTask();
        if (["reading", "editing"].includes(nextState)) bindNote();
      } else if (target.dataset.regenerateNote !== undefined) {
        if (!state.note) throw new Error("请先打开一份成品笔记");
        state.regenerateFromNote = state.note;
        state.selectedGenerationRoute = null;
        setNotesState("regenerate");
        bindNoteRegeneration();
      } else if (target.dataset.regeneratePrompt !== undefined) {
        const input = notesStateHost.querySelector("#regenerate-note-request");
        if (input) {
          input.value = target.dataset.regeneratePrompt;
          input.focus();
        }
      } else if (target.dataset.cancelRegenerate !== undefined) {
        state.note = state.regenerateFromNote || state.note;
        state.regenerateFromNote = null;
        setNotesState("reading");
        bindNote();
      } else if (target.dataset.confirmRegenerate !== undefined) {
        await startNoteRegeneration();
      } else if (target.dataset.fakeUpload !== undefined) {
        const fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.accept = ".txt,.md,text/plain,text/markdown";
        fileInput.onchange = async () => {
          const file = fileInput.files[0];
          if (!file) return;
          const extension = file.name.split(".").pop()?.toLowerCase();
          if (!["txt", "md"].includes(extension) || file.size > 5 * 1024 * 1024) {
            return runtimeMessage("文件必须为 5 MB 以内的 TXT 或 MD", true);
          }
          state.inputTranscript = await file.text();
          state.uploadedTranscript = { name: file.name, extension };
          state.sourceMode = "independent";
          state.noteRequestText = "";
          state.selectedGenerationRoute = null;
          setNotesState("ready");
          bindTranscriptReady();
        };
        fileInput.click();
      } else if (target.dataset.prepareNotes !== undefined) {
        const transcript = notesStateHost.querySelector("#notes-transcript-input")?.value.trim() || "";
        if (!transcript) throw new Error("请先粘贴逐字稿");
        state.inputTranscript = transcript;
        state.noteRequestText = notesStateHost.querySelector("#notes-request-input")?.value.trim() || "";
        state.uploadedTranscript = null;
        state.sourceMode = "independent";
        state.selectedGenerationRoute = null;
        setNotesState("ready");
        bindTranscriptReady();
      } else if (target.dataset.startAnalysis !== undefined) {
        await createNoteAnalysis();
      } else if (target.dataset.phase3 !== undefined) {
        await startRealGeneration();
      } else if (target.dataset.confirmOutline !== undefined) {
        setNotesState("chapter-generating");
        await noteCommand({ type: "confirm_outline" });
        await pollNote(state.noteTask.id);
      } else if (target.dataset.regenerateOutline !== undefined) {
        const feedback = notesStateHost.querySelector("#outline-feedback")?.value || "";
        setNotesState("outline-regenerating");
        await noteCommand({ type: "regenerate_outline", feedback });
        await pollNote(state.noteTask.id);
      } else if (target.dataset.continueChapter !== undefined) {
        await noteCommand({ type: "retry_failed_chapter" });
        await pollNote(state.noteTask.id);
      } else if (target.dataset.phase4 !== undefined) {
        await openCurrentNote();
      } else if (target.dataset.recheckIntegrity !== undefined) {
        if (!state.note) throw new Error("请先打开一份成品笔记");
        target.disabled = true;
        target.textContent = "正在重新检查…";
        try {
          const payload = await request(`/api/v3/notes/${state.note.id}/integrity-check`, {
            method: "POST",
          });
          state.note = payload.note;
          bindGenerationComplete(state.noteTask);
          if (state.note.integrity?.status === "ok") {
            runtimeMessage("内容完整性检查已完成");
          } else if (state.note.integrity?.status === "possible_omission") {
            runtimeMessage("检查完成，发现可能需要复核的内容", true);
          } else {
            runtimeMessage("内容检查仍未完成，请稍后再试", true);
          }
        } finally {
          target.disabled = false;
          target.textContent = "重新检查内容";
        }
      } else if (target.dataset.editNote !== undefined) {
        setNotesState("editing");
        bindNote();
      } else if (target.dataset.finishEdit !== undefined) {
        await saveEditor(true);
        setNotesState("reading");
        bindNote();
      } else if (target.dataset.exportNote !== undefined) {
        setNotesState("export");
        bindExport();
      } else if (target.dataset.openNoteHistory !== undefined) {
        switchView("notes");
        await showHistory();
        window.VTNHistoryNavigation?.scrollToHistory("notes");
      } else if (target.dataset.openParserHistory !== undefined) {
        switchView("parser");
        await showParserHistory();
        window.VTNHistoryNavigation?.scrollToHistory("parser");
      } else if (target.dataset.loadMore !== undefined) {
        if (state.noteHistoryCursor) await showHistory(false);
      } else if (target.dataset.loadMoreParser !== undefined) {
        if (state.parserHistoryCursor) await showParserHistory(false);
      } else if (target.dataset.loadMoreTasks !== undefined) {
        if (state.recoveryCursor) await showRecovery(false);
      } else if (target.dataset.openTaskRecovery !== undefined || target.dataset.resumeLater !== undefined) {
        await showRecovery();
      } else if (target.dataset.realResumeTask) {
        state.noteTask = (await request(`/api/v3/note-tasks/${target.dataset.realResumeTask}`)).task;
        if (state.noteTask.state === "complete" && state.noteTask.note_id) {
          await openCurrentNote();
        } else {
          setNotesState(noteStateName(state.noteTask));
          bindNoteTask();
          if (["analyzing", "outline_regenerating", "generating_direct", "generating_chapters"].includes(state.noteTask.state)) {
            await pollNote(state.noteTask.id);
          }
        }
      } else if (target.dataset.realOpenNote) {
        state.note = (await request(`/api/v3/notes/${target.dataset.realOpenNote}`)).note;
        setNotesState("reading");
        bindNote();
      } else if (target.dataset.realDeleteNote) {
        state.note = (await request(`/api/v3/notes/${target.dataset.realDeleteNote}`)).note;
        setNotesState("note-delete");
      } else if (target.dataset.realUseRecord) {
        state.parserRecord = (await request(`/api/v3/parser/records/${target.dataset.realUseRecord}`)).record;
        videoLink.value = state.parserRecord.source_url;
        setParserState("success");
        bindParserRecord();
      } else if (target.dataset.realDeleteRecord) {
        state.parserRecord = (await request(`/api/v3/parser/records/${target.dataset.realDeleteRecord}`)).record;
        deleteDialog.showModal();
      } else if (target.dataset.confirmDelete !== undefined) {
        if (!state.parserRecord) throw new Error("当前没有可删除的解析记录");
        await request(`/api/v3/parser/records/${state.parserRecord.id}`, { method: "DELETE" });
        deleteDialog.close();
        state.parserRecord = null;
        await showParserHistory();
      } else if (target.dataset.realOpenLinkedNote) {
        state.note = (await request(`/api/v3/notes/${target.dataset.realOpenLinkedNote}`)).note;
        switchView("notes");
        setNotesState("reading");
        bindNote();
      } else if (target.dataset.realOpenParserRecord) {
        state.parserRecord = (await request(`/api/v3/parser/records/${target.dataset.realOpenParserRecord}`)).record;
        switchView("parser");
        videoLink.value = state.parserRecord.source_url;
        setParserState("success");
        bindParserRecord();
      } else if (target.dataset.confirmRestore !== undefined) {
        const payload = await request(`/api/v3/notes/${state.note.id}/restore-ai-initial`, {
          method: "POST", body: JSON.stringify({ expected_version: state.note.version }),
        });
        state.note = payload.note;
        restoreDialog.close();
        setNotesState("reading");
        bindNote();
      } else if (target.dataset.regenerateChapter !== undefined) {
        if (!state.note) throw new Error("请先打开成品笔记");
        const chapter = target.dataset.chapterTitle || state.note.current_markdown.match(/^##\s+(.+)$/m)?.[1];
        if (!chapter) throw new Error("当前笔记没有可重新生成的章节");
        const payload = await request(
          `/api/v3/notes/${state.note.id}/chapters/${encodeURIComponent(chapter)}/candidates`,
          { method: "POST" }
        );
        state.candidate = payload.candidate;
        setNotesState("chapter-candidate");
        bindCandidate(state.candidate);
      } else if (target.dataset.acceptCandidate !== undefined || target.dataset.keepCurrent !== undefined) {
        if (!state.candidate) throw new Error("当前没有待处理候选");
        const decision = target.dataset.acceptCandidate !== undefined ? "accept" : "reject";
        const payload = await request(
          `/api/v3/notes/${state.note.id}/candidates/${state.candidate.id}/decision`,
          {
            method: "POST",
            body: JSON.stringify({ decision, expected_version: state.note.version }),
          }
        );
        state.note = payload.note;
        state.candidate = null;
        setNotesState("reading");
        bindNote();
      } else if (target.dataset.confirmNoteDelete !== undefined) {
        if (!state.note) throw new Error("当前没有可删除的笔记");
        await request(`/api/v3/notes/${state.note.id}`, { method: "DELETE" });
        noteDeleteDialog.close();
        state.note = null;
        await showHistory();
      } else if (target.dataset.restartGeneration !== undefined) {
        setNotesState("direct-generating");
        await noteCommand({ type: "restart_generation" });
        await pollNote(state.noteTask.id);
      } else if (target.dataset.runExport !== undefined) {
        const format = notesStateHost.querySelector('input[name="export-format"]:checked')?.value || "md";
        const content = notesStateHost.querySelector('input[name="export-content"]:checked')?.value === "transcript" ? "note_transcript" : "note";
        const source = notesStateHost.querySelector(".source-toggle input")?.checked ? "include" : "exclude";
        const url = withDeviceId(`/api/v3/notes/${state.note.id}/export?format=${format === "copy" ? "md" : format}&content=${content}&source=${source}`);
        if (format === "copy") {
          const response = await fetch(url);
          await navigator.clipboard.writeText(await response.text());
          runtimeMessage("最新版本已复制到剪贴板");
        } else {
          location.href = url;
        }
      } else if (target.dataset.download !== undefined) {
        if (!state.parserRecord) throw new Error("当前没有可下载的解析记录");
        if (["video", "audio"].includes(target.dataset.download)) {
          startParserMediaDownload(target.dataset.download, target);
          return;
        }
        const suffix = {
          "transcript-txt": "transcript.txt", "transcript-md": "transcript.md",
        }[target.dataset.download];
        location.href = withDeviceId(
          `/api/v3/parser/records/${state.parserRecord.id}/${suffix}`,
        );
      } else if (target.dataset.retry !== undefined) {
        if (state.parserSubmitting) return;
        const pollToken = ++state.parserPollToken;
        setParserBusy(true);
        try {
          setParserState("loading");
          bindParserProgress(state.parserTask);
          const payload = await request(`/api/v3/parser/tasks/${state.parserTask.id}/commands`, {
            method: "POST", body: JSON.stringify({ command: "retry" }),
          });
          state.parserTask = payload.task;
          await pollParser(payload.task.id, pollToken);
        } catch (error) {
          if (pollToken === state.parserPollToken) {
            setParserState("failure");
            bindParserFailure({
              ...state.parserTask,
              error_message: error.message,
              error_retryable: true,
            });
          }
          throw error;
        } finally {
          if (pollToken === state.parserPollToken) setParserBusy(false);
        }
      }
    } catch (error) {
      if (error.code === "NOTE_WORKSPACE_LEFT") return;
      runtimeMessage(error.message, true);
    }
  }, true);

  document.addEventListener("input", (event) => {
    if (event.target.matches("#notes-transcript-input")) {
      state.inputTranscript = event.target.value;
      bindFreeCapacityNotices({ host: notesStateHost, transcript: state.inputTranscript });
      return;
    }
    if (event.target.matches("#suggested-note-title") && state.noteTask) {
      const title = event.target.value.trim();
      state.pendingTitle = title;
      state.noteTask.proposed_title = title;
      return;
    }
    if (event.target.matches("[data-transcript-edit]") && state.noteTask) {
      event.stopImmediatePropagation();
      state.inputTranscript = event.target.value;
      setNotesState("stale");
      const staleEditor = notesStateHost.querySelector(".notes-textarea");
      if (staleEditor) staleEditor.value = state.inputTranscript;
      return;
    }
    if (!event.target.matches("[data-editor-content], [data-note-title]") || !state.note) return;
    clearTimeout(state.saveTimer);
    state.saveTimer = setTimeout(() => saveEditor(false).catch((error) => runtimeMessage(error.message, true)), 650);
  }, true);

  document.addEventListener("change", (event) => {
    if (!event.target.closest(".export-choice, .export-radio, .source-toggle")) return;
    bindExport();
  });

  const resumeRecordId = new URLSearchParams(location.search).get("record");
  bindFreeCapacityNotices({ host: notesStateHost, transcript: state.inputTranscript });
  detectCapabilities().catch(() => {});
  refreshAccessStatus()
    .then(() => {
      if (!state.accessControlEnabled) {
        return migrateLegacyHistory();
      }
      return null;
    })
    .catch((error) => runtimeMessage(`启动检查未完成：${error.message}`, true));
  if (resumeRecordId) {
    request(`/api/v3/parser/records/${encodeURIComponent(resumeRecordId)}`)
      .then((payload) => {
        state.parserRecord = payload.record;
        videoLink.value = payload.record.source_url;
        renderPlatformDetection();
        setParserState("success");
        bindParserRecord();
      })
      .catch((error) => runtimeMessage(error.message, true));
  }
})();
