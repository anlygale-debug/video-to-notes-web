const parserTemplates = {
  empty: "empty-template",
  loading: "loading-template",
  success: "success-template",
  failure: "failure-template",
  history: "history-template",
};

const notesTemplates = {
  input: "notes-input-template",
  ready: "notes-ready-template",
  analyzing: "notes-analyzing-template",
  recommendations: "notes-recommendations-template",
  custom: "notes-custom-template",
  stale: "notes-stale-template",
  "analysis-failure": "notes-analysis-failure-template",
  "direct-generating": "notes-direct-generating-template",
  outline: "notes-outline-template",
  "outline-regenerating": "notes-outline-regenerating-template",
  "chapter-generating": "notes-chapter-generating-template",
  "chapter-failure": "notes-chapter-failure-template",
  recovery: "notes-recovery-template",
  "generation-complete": "notes-generation-complete-template",
  reading: "notes-reading-template",
  editing: "notes-editing-template",
  "chapter-candidate": "notes-chapter-candidate-template",
  export: "notes-export-template",
  omission: "notes-omission-template",
  "note-history": "notes-note-history-template",
  "note-delete": "notes-note-history-template",
  regenerate: "notes-regenerate-template",
};

const notesStateNames = {
  input: "输入",
  ready: "已就绪",
  analyzing: "预读中",
  recommendations: "推荐",
  custom: "自定义",
  stale: "推荐过期",
  "analysis-failure": "预读失败",
  "direct-generating": "直接生成",
  outline: "大纲确认",
  "outline-regenerating": "重拟大纲",
  "chapter-generating": "逐章生成",
  "chapter-failure": "章节失败",
  recovery: "任务恢复",
  "generation-complete": "生成完成",
  reading: "阅读",
  editing: "编辑",
  "chapter-candidate": "单章候选",
  export: "导出",
  omission: "可能遗漏",
  "note-history": "笔记历史",
  "note-delete": "删除确认",
  regenerate: "重新生成",
};

const parserView = document.querySelector("#parser-view");
const notesView = document.querySelector("#notes-view");
const stateHost = document.querySelector("#state-host");
const notesStateHost = document.querySelector("#notes-state-host");
const parserStateButtons = [...document.querySelectorAll("[data-parser-state]")];
const notesStateButtons = [...document.querySelectorAll("[data-notes-state]")];
const parserForm = document.querySelector("#parser-form");
const videoLink = document.querySelector("#video-link");
const platformDetection = document.querySelector("#platform-detection");
const platformChip = platformDetection.querySelector(".platform-chip");
const platformMessage = platformDetection.querySelector(".platform-message");
const notesDialog = document.querySelector("#notes-dialog");
const deleteDialog = document.querySelector("#delete-dialog");
const restoreDialog = document.querySelector("#restore-dialog");
const noteDeleteDialog = document.querySelector("#note-delete-dialog");
const newNoteDialog = document.querySelector("#new-note-dialog");
const publicDemoTour = document.querySelector("#public-demo-tour");

let currentNotesState = "input";
let notesSourceMode = "independent";
let publicDemoActive = false;
let publicDemoStep = "parser";
let notesTransitionTimer;
let autosaveTimer;
const defaultNoteTitle = "用 AI Agent 重建个人学习系统：从收藏到行动";
const defaultNotesRequest = "用于快速复习，保留学习步骤、案例和行动方法。";
let noteTitle = defaultNoteTitle;
let notesRequest = defaultNotesRequest;
let outlineFeedback = "请把第四章的失败复盘写得更具体。";

const platformProfiles = {
  bilibili: { label: "BILIBILI", name: "Bilibili", creator: "UP 主", message: "已识别为 Bilibili 视频链接。" },
  xiaohongshu: { label: "小红书", name: "小红书", creator: "作者", message: "已识别为小红书视频链接。" },
  youtube: { label: "YOUTUBE", name: "YouTube", creator: "频道", message: "已识别为 YouTube 视频链接。" },
  other: { label: "其他平台", name: "其他平台", creator: "作者", message: "未匹配三类主要平台，将尝试通用解析。" },
  waiting: { label: "等待链接", name: "", creator: "作者", message: "输入链接后，这里会显示识别到的视频平台。" },
};

const publicDemoStepOrder = ["parser", "analysis", "generation", "note"];

function syncPublicDemoTour(step = publicDemoStep) {
  if (!publicDemoTour) return;
  publicDemoStep = step;
  publicDemoTour.hidden = !publicDemoActive;
  document.body.classList.toggle("public-demo-active", publicDemoActive);
  document.querySelector(".nav-link--demo")?.classList.toggle("is-demo-active", publicDemoActive);
  const activeIndex = publicDemoStepOrder.indexOf(step);
  publicDemoTour.querySelectorAll("[data-public-demo-step]").forEach((item) => {
    const itemIndex = publicDemoStepOrder.indexOf(item.dataset.publicDemoStep);
    item.classList.toggle("is-current", itemIndex === activeIndex);
    item.classList.toggle("is-complete", itemIndex < activeIndex);
  });
}

function startPublicDemo() {
  publicDemoActive = true;
  notesSourceMode = "linked";
  noteTitle = defaultNoteTitle;
  notesRequest = defaultNotesRequest;
  videoLink.value = "https://www.bilibili.com/video/BV1-demo-0727";
  syncPublicDemoTour("parser");
  switchView("parser");
  setParserState("success");
  stateHost.scrollIntoView({ behavior: "smooth", block: "start" });
}

function exitPublicDemo() {
  publicDemoActive = false;
  window.clearTimeout(notesTransitionTimer);
  syncPublicDemoTour("parser");
  switchView("parser");
  videoLink.value = "";
  renderPlatformDetection();
  setParserState("empty");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function detectPlatform(value) {
  const normalized = value.trim().toLowerCase();
  if (!normalized) return platformProfiles.waiting;
  if (normalized.includes("bilibili.com") || normalized.includes("b23.tv")) return platformProfiles.bilibili;
  if (normalized.includes("xiaohongshu.com") || normalized.includes("xhslink.com") || normalized.includes("xhslink.cn") || normalized.includes("rednote.com")) return platformProfiles.xiaohongshu;
  if (normalized.includes("youtube.com") || normalized.includes("youtu.be")) return platformProfiles.youtube;
  return platformProfiles.other;
}

function renderPlatformDetection() {
  const profile = detectPlatform(videoLink.value);
  platformDetection.classList.toggle("is-waiting", profile === platformProfiles.waiting);
  platformDetection.classList.toggle("is-unknown", profile === platformProfiles.other);
  platformChip.textContent = profile.label;
  platformMessage.textContent = profile.message;
  return profile;
}

function syncResultPlatform() {
  const profile = renderPlatformDetection();
  const resultChip = stateHost.querySelector("[data-result-platform]");
  if (!resultChip) return;
  resultChip.textContent = profile.label;
  stateHost.querySelector("[data-result-platform-name]").textContent = profile.name;
  stateHost.querySelector("[data-result-creator-label]").textContent = profile.creator;
}

function mountTemplate(host, templateId) {
  const content = document.querySelector(`#${templateId}`).content.cloneNode(true);
  host.replaceChildren(content);
}

function setParserState(state) {
  if (state === "delete") {
    setParserState("history");
    parserStateButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.parserState === "delete"));
    document.querySelector("#parser .issue-stamp strong").textContent = "状态 06 — 删除确认";
    deleteDialog.showModal();
    return;
  }
  if (state === "success" && !videoLink.value.trim()) {
    videoLink.value = "https://www.bilibili.com/video/BV1-demo-0727";
    renderPlatformDetection();
  }
  mountTemplate(stateHost, parserTemplates[state]);
  if (state === "success") syncResultPlatform();
  parserStateButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.parserState === state));
  const index = Object.keys(parserTemplates).indexOf(state) + 1;
  const labels = { empty: "初始", loading: "解析中", success: "结果", failure: "失败", history: "历史" };
  document.querySelector("#parser .issue-stamp strong").textContent = `状态 ${String(index).padStart(2, "0")} — ${labels[state]}`;
}

function syncNotesSource() {
  const sourceLine = notesStateHost.querySelector("[data-analysis-source]");
  if (!sourceLine) return;
  sourceLine.innerHTML = notesSourceMode === "linked"
    ? '<span class="square green"></span> 生成依据：视频解析 / 刚毕业一年，我如何用 AI 重建自己的学习系统 // 08:42'
    : '<span class="square green"></span> 生成依据：AI_Agent_学习方法.md // 3,842 字';
}

function noteFilename(extension) {
  const safeTitle = noteTitle
    .trim()
    .replace(/[^a-zA-Z0-9\u4e00-\u9fff_-]+/g, "_")
    .replace(/^_+|_+$/g, "") || "笔记";
  return `${safeTitle}.${extension}`;
}

function syncNotesContext() {
  const recommendedTitle = notesStateHost.querySelector("#suggested-note-title");
  if (recommendedTitle) recommendedTitle.value = noteTitle;

  const outlineContext = notesStateHost.querySelector(".outline-context");
  if (outlineContext) {
    const values = outlineContext.querySelectorAll("strong");
    if (values[0]) values[0].textContent = noteTitle;
    if (values[1]) values[1].textContent = notesRequest;
  }

  const outlineFeedbackInput = notesStateHost.querySelector("#outline-feedback");
  if (outlineFeedbackInput) outlineFeedbackInput.value = outlineFeedback;

  const outlineFeedbackCopy = notesStateHost.querySelector("[data-outline-feedback-copy]");
  if (outlineFeedbackCopy) outlineFeedbackCopy.textContent = outlineFeedback;

  notesStateHost.querySelectorAll("[data-note-title]").forEach((element) => {
    if (element.id !== "suggested-note-title") element.textContent = noteTitle;
  });

  const editingTitle = notesStateHost.querySelector(".note-document--editing .note-document-header h2");
  if (editingTitle) editingTitle.textContent = noteTitle;

  const completionTitle = notesStateHost.querySelector(".completion-summary h3");
  if (completionTitle) completionTitle.textContent = noteTitle;

  const omissionTitle = notesStateHost.querySelector(".note-document--compact .note-document-header h2");
  if (omissionTitle) omissionTitle.textContent = noteTitle;

  const exportTitle = notesStateHost.querySelector(".paper-lines strong");
  if (exportTitle) exportTitle.textContent = noteTitle;

  const currentHistoryTitle = notesStateHost.querySelector(".note-history-list .is-featured h3");
  if (currentHistoryTitle) currentHistoryTitle.textContent = noteTitle;

  const regenerateTitle = notesStateHost.querySelector("[data-regenerate-original-title]");
  if (regenerateTitle) regenerateTitle.textContent = noteTitle;
  const regenerateTranscript = notesStateHost.querySelector("[data-regenerate-transcript]");
  if (regenerateTranscript && !regenerateTranscript.value) {
    regenerateTranscript.value = "以前我学习新东西，总是先收藏很多资料。后来我改为从真实问题出发，让 AI 帮助整理材料、形成行动笔记，并在实践后复盘。";
  }
  const regenerateCount = notesStateHost.querySelector("[data-regenerate-character-count]");
  if (regenerateCount && regenerateTranscript) {
    regenerateCount.textContent = `${Array.from(regenerateTranscript.value).length.toLocaleString()} 字 ＋`;
  }
}

function setNotesState(state) {
  if (state === "note-delete") {
    setNotesState("note-history");
    notesStateButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.notesState === "note-delete"));
    document.querySelector("#notes-state-stamp").textContent = "状态 21 — 删除确认";
    noteDeleteDialog.showModal();
    return;
  }
  window.clearTimeout(notesTransitionTimer);
  currentNotesState = state;
  mountTemplate(notesStateHost, notesTemplates[state]);
  syncNotesWorkspaceBar(state);
  syncNotesSource();
  syncNotesContext();
  notesStateButtons.forEach((button) => button.classList.toggle("is-active", button.dataset.notesState === state));
  const index = Object.keys(notesTemplates).indexOf(state) + 1;
  document.querySelector("#notes-state-stamp").textContent = `状态 ${String(index).padStart(2, "0")} — ${notesStateNames[state]}`;
  if (publicDemoActive) {
    if (["analyzing", "recommendations", "custom", "stale", "analysis-failure"].includes(state)) syncPublicDemoTour("analysis");
    else if (["direct-generating", "outline", "outline-regenerating", "chapter-generating", "chapter-failure", "generation-complete"].includes(state)) syncPublicDemoTour("generation");
    else if (["reading", "editing", "chapter-candidate", "export", "omission", "note-history", "regenerate"].includes(state)) syncPublicDemoTour("note");
  }
}

function syncNotesWorkspaceBar(state) {
  const bar = document.querySelector("[data-notes-workspace-bar]");
  if (!bar) return;
  const activeGenerationStates = ["analyzing", "direct-generating", "outline-regenerating", "chapter-generating"];
  const abandonableStates = [
    "ready", "analyzing", "recommendations", "custom", "stale",
    "analysis-failure", "direct-generating", "outline", "outline-regenerating",
    "chapter-generating", "chapter-failure",
  ];
  const isGenerating = activeGenerationStates.includes(state);
  bar.hidden = !abandonableStates.includes(state);
  bar.classList.toggle("is-generating", isGenerating);
  const kicker = bar.querySelector("[data-notes-workspace-kicker]");
  const title = bar.querySelector("[data-notes-workspace-title]");
  const copy = bar.querySelector("[data-notes-workspace-copy]");
  const label = bar.querySelector("[data-abandon-note-label]");
  if (kicker) kicker.textContent = isGenerating
    ? "TASK IN PROGRESS // 放弃后无法恢复"
    : "UNFINISHED NOTE // 当前任务尚未完成";
  if (title) title.textContent = isGenerating
    ? "正在生成这份笔记"
    : "这份笔记还没有完成";
  if (copy) copy.textContent = "返回首页将删除本次未完成进度。";
  if (label) label.textContent = isGenerating ? "放弃生成" : "放弃本次笔记";
}

function beginPrototypeNewNote() {
  if (publicDemoActive) exitPublicDemo();
  notesSourceMode = "independent";
  switchView("notes");
  setNotesState("input");
  window.scrollTo({ top: document.querySelector("#notes")?.offsetTop || 0, behavior: "smooth" });
}

function switchView(view) {
  const showNotes = view === "notes";
  parserView.hidden = showNotes;
  notesView.hidden = !showNotes;
  document.querySelectorAll("[data-nav]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.nav === view);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function scrollHistoryIntoView(kind) {
  const selector = kind === "notes"
    ? "#notes-state-host .note-history-stack"
    : "#state-host .history-section";
  const history = document.querySelector(selector);
  if (!history) return false;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const top = Math.max(0, window.scrollY + history.getBoundingClientRect().top - 24);
  window.scrollTo({ top, behavior: reduceMotion ? "auto" : "smooth" });
  return true;
}

function scheduleHistoryScroll(kind) {
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => scrollHistoryIntoView(kind));
  });
}

window.VTNHistoryNavigation = { scrollToHistory: scheduleHistoryScroll };

function runAnalysis(sourceMode = notesSourceMode) {
  notesSourceMode = sourceMode;
  switchView("notes");
  setNotesState("analyzing");
  notesTransitionTimer = window.setTimeout(() => setNotesState("recommendations"), 1200);
}

function startGeneration() {
  const selectedMethod = notesStateHost.querySelector('[data-setting-group="method"] .choice-card.is-selected')?.dataset.choice;
  if (selectedMethod === "outline") {
    setNotesState("outline");
    return;
  }
  setNotesState("direct-generating");
  notesTransitionTimer = window.setTimeout(() => setNotesState("generation-complete"), 2400);
}

function startChapterGeneration() {
  setNotesState("chapter-generating");
  notesTransitionTimer = window.setTimeout(() => setNotesState("generation-complete"), 2800);
}

function regenerateOutline() {
  setNotesState("outline-regenerating");
  notesTransitionTimer = window.setTimeout(() => setNotesState("outline"), 1600);
}

function updateConflictNotice() {
  const detail = notesStateHost.querySelector('[data-setting-group="detail"] .choice-card.is-selected');
  const method = notesStateHost.querySelector('[data-setting-group="method"] .choice-card.is-selected');
  const notice = notesStateHost.querySelector("[data-conflict]");
  if (!detail || !method || !notice) return;
  notice.hidden = !(detail.dataset.choice === "quick" && method.dataset.choice === "outline");
}

function updateExportPreview() {
  const format = notesStateHost.querySelector('input[name="export-format"]:checked')?.value ?? "md";
  const content = notesStateHost.querySelector('input[name="export-content"]:checked')?.value ?? "note";
  const includeSource = notesStateHost.querySelector(".source-toggle input")?.checked ?? true;
  const action = notesStateHost.querySelector("[data-run-export]");
  const filename = notesStateHost.querySelector("[data-export-filename]");
  const scope = notesStateHost.querySelector("[data-export-scope]");
  const labels = {
    md: { action: "准备 Markdown 下载", extension: "md" },
    pdf: { action: "准备 PDF 下载", extension: "pdf" },
    copy: { action: "复制最新笔记全文", extension: "clipboard" },
  };
  if (action) action.innerHTML = `${labels[format].action} <span>→</span>`;
  if (filename) filename.textContent = format === "copy" ? "复制到系统剪贴板" : noteFilename(labels[format].extension);
  if (scope) scope.textContent = `${content === "transcript" ? "笔记 + 生成依据逐字稿" : "仅笔记"} · ${includeSource ? "包含来源" : "不含来源"}`;
}

parserStateButtons.forEach((button) => button.addEventListener("click", () => setParserState(button.dataset.parserState)));
notesStateButtons.forEach((button) => button.addEventListener("click", () => setNotesState(button.dataset.notesState)));

parserForm.addEventListener("submit", (event) => {
  event.preventDefault();
  setParserState("loading");
  window.setTimeout(() => setParserState("success"), 1100);
});

videoLink.addEventListener("input", renderPlatformDetection);

document.addEventListener("submit", (event) => {
  if (!event.target.matches("[data-notes-form]")) return;
  event.preventDefault();
  runAnalysis("independent");
});

document.addEventListener("change", (event) => {
  const moduleChoice = event.target.closest(".module-choice");
  if (moduleChoice) {
    const moduleGrid = moduleChoice.closest(".module-grid");
    const bodyOnly = moduleGrid?.querySelector("[data-module-none] input");
    const regularModules = [...(moduleGrid?.querySelectorAll("[data-module] input") || [])];
    if (moduleChoice.hasAttribute("data-module-none") && event.target.checked) {
      regularModules.forEach((input) => { input.checked = false; });
    } else if (moduleChoice.hasAttribute("data-module") && event.target.checked && bodyOnly) {
      bodyOnly.checked = false;
    }
    if (bodyOnly && !regularModules.some((input) => input.checked)) {
      bodyOnly.checked = true;
    }
    moduleGrid?.querySelectorAll(".module-choice").forEach((choice) => {
      choice.classList.toggle("is-selected", Boolean(choice.querySelector("input")?.checked));
    });
  }
  const exportChoice = event.target.closest(".export-choice");
  if (exportChoice) {
    notesStateHost.querySelectorAll(".export-choice").forEach((choice) => choice.classList.toggle("is-selected", choice.contains(event.target) && event.target.checked));
    updateExportPreview();
  }
  const exportRadio = event.target.closest(".export-radio");
  if (exportRadio) {
    notesStateHost.querySelectorAll(".export-radio").forEach((choice) => choice.classList.toggle("is-selected", choice.contains(event.target) && event.target.checked));
    updateExportPreview();
  }
  const sourceToggle = event.target.closest(".source-toggle");
  if (sourceToggle) {
    sourceToggle.classList.toggle("is-selected", event.target.checked);
    updateExportPreview();
  }
});

document.addEventListener("input", (event) => {
  if (event.target.matches("#suggested-note-title, [data-note-title]")) {
    const nextTitle = (event.target.value ?? event.target.textContent).trim();
    noteTitle = nextTitle || defaultNoteTitle;
  }
  if (event.target.matches(".notes-request")) {
    const nextRequest = event.target.value.trim();
    notesRequest = nextRequest || defaultNotesRequest;
  }
  if (event.target.matches("#outline-feedback")) {
    outlineFeedback = event.target.value.trim() || "请补充最需要展开的章节。";
  }
  if (event.target.matches("[data-transcript-edit]") && currentNotesState === "recommendations") {
    setNotesState("stale");
  }
  if (event.target.matches("[data-editor-content], [data-note-title]")) {
    const status = document.querySelector("[data-autosave-status]") || document.querySelector("[data-save-label]");
    if (status) status.textContent = "正在自动保存…";
    window.clearTimeout(autosaveTimer);
    autosaveTimer = window.setTimeout(() => {
      const latestStatus = document.querySelector("[data-autosave-status]") || document.querySelector("[data-save-label]");
      if (latestStatus) latestStatus.textContent = "已自动保存 · 刚刚";
    }, 650);
  }
});

document.addEventListener("click", (event) => {
  const target = event.target.closest("button");
  if (!target) return;
  if (target.dataset.openPublicDemo !== undefined) {
    startPublicDemo();
    return;
  }
  if (target.dataset.exitPublicDemo !== undefined) {
    exitPublicDemo();
    return;
  }
  if (target.dataset.newNote !== undefined) {
    beginPrototypeNewNote();
    return;
  }
  if (target.dataset.abandonNote !== undefined) {
    newNoteDialog?.showModal();
    return;
  }
  if (target.dataset.confirmAbandonNote !== undefined) {
    newNoteDialog?.close();
    beginPrototypeNewNote();
    return;
  }

  if (target.dataset.openNotes !== undefined) {
    runAnalysis("linked");
    return;
  }
  if (target.dataset.regenerateNote !== undefined) {
    setNotesState("regenerate");
    return;
  }
  if (target.dataset.regeneratePrompt !== undefined) {
    const input = notesStateHost.querySelector("#regenerate-note-request");
    if (input) input.value = target.dataset.regeneratePrompt;
    return;
  }
  if (target.dataset.cancelRegenerate !== undefined) {
    setNotesState("reading");
    return;
  }
  if (target.dataset.confirmRegenerate !== undefined) {
    runAnalysis("independent");
    return;
  }
  if (target.dataset.fakeUpload !== undefined) {
    notesSourceMode = "independent";
    setNotesState("ready");
    return;
  }
  if (target.dataset.startAnalysis !== undefined) {
    runAnalysis(notesSourceMode);
    return;
  }
  if (target.dataset.notesStateJump) {
    setNotesState(target.dataset.notesStateJump);
    return;
  }
  if (target.dataset.phase3 !== undefined) {
    startGeneration();
    return;
  }
  if (target.dataset.confirmOutline !== undefined) {
    startChapterGeneration();
    return;
  }
  if (target.dataset.regenerateOutline !== undefined) {
    regenerateOutline();
    return;
  }
  if (target.dataset.continueChapter !== undefined) {
    startChapterGeneration();
    return;
  }
  if (target.dataset.resumeLater !== undefined) {
    setNotesState("recovery");
    return;
  }
  if (target.dataset.restartGeneration !== undefined) {
    startChapterGeneration();
    return;
  }
  if (target.dataset.resumeState) {
    setNotesState(target.dataset.resumeState);
    return;
  }
  if (target.dataset.phase4 !== undefined) {
    setNotesState("reading");
    return;
  }
  if (target.dataset.editNote !== undefined) {
    setNotesState("editing");
    return;
  }
  if (target.dataset.finishEdit !== undefined) {
    setNotesState("reading");
    return;
  }
  if (target.dataset.regenerateChapter !== undefined) {
    setNotesState("chapter-candidate");
    return;
  }
  if (target.dataset.acceptCandidate !== undefined || target.dataset.keepCurrent !== undefined) {
    setNotesState("reading");
    return;
  }
  if (target.dataset.exportNote !== undefined) {
    setNotesState("export");
    updateExportPreview();
    return;
  }
  if (target.dataset.openNoteHistory !== undefined) {
    switchView("notes");
    setNotesState("note-history");
    scheduleHistoryScroll("notes");
    return;
  }
  if (target.dataset.openParserHistory !== undefined) {
    switchView("parser");
    setParserState("history");
    scheduleHistoryScroll("parser");
    return;
  }
  if (target.dataset.openNote !== undefined) {
    setNotesState("reading");
    return;
  }
  if (target.dataset.noteDelete !== undefined) {
    setNotesState("note-delete");
    return;
  }
  if (target.dataset.restoreInitial !== undefined) {
    restoreDialog.showModal();
    return;
  }
  if (target.dataset.confirmRestore !== undefined) {
    restoreDialog.close();
    setNotesState("reading");
    return;
  }
  if (target.dataset.confirmNoteDelete !== undefined) {
    noteDeleteDialog.close();
    setNotesState("note-history");
    alert("原型提示：示例笔记已永久删除；关联的视频解析记录仍然保留。刷新页面可恢复固定假数据。");
    return;
  }
  if (target.dataset.editTitle !== undefined) {
    const title = notesStateHost.querySelector("[data-note-title]");
    title.contentEditable = "true";
    title.focus();
    target.textContent = "标题编辑中";
    return;
  }
  if (target.dataset.format) {
    document.execCommand(target.dataset.format, false, target.dataset.value || null);
    return;
  }
  if (target.dataset.runExport !== undefined) {
    const format = notesStateHost.querySelector('input[name="export-format"]:checked')?.value ?? "md";
    const labels = { md: "Markdown 文件", pdf: "PDF 文件", copy: "最新笔记全文" };
    alert(`原型提示：这里会准备${labels[format]}；本阶段不生成真实文件或写入剪贴板。`);
    return;
  }
  if (target.dataset.regenerateModule !== undefined) {
    alert("原型提示：这里会单独重新生成关系图模块；主体笔记不会被阻塞或覆盖。");
    return;
  }
  if (target.dataset.finalBoundary !== undefined) {
    notesDialog.showModal();
    return;
  }
  if (target.dataset.loadMore !== undefined) {
    alert("原型提示：这里会继续加载更早的笔记，不会自动删除第 31 条以后的记录。");
    return;
  }
  if (target.dataset.openExistingNote !== undefined) {
    switchView("notes");
    setNotesState("reading");
    return;
  }
  if (target.classList.contains("choice-card")) {
    const group = target.closest("[data-setting-group]");
    group.querySelectorAll(".choice-card").forEach((choice) => choice.classList.toggle("is-selected", choice === target));
    updateConflictNotice();
    return;
  }

  if (target.dataset.delete !== undefined) deleteDialog.showModal();
  if (target.dataset.retry !== undefined) {
    setParserState("loading");
    window.setTimeout(() => setParserState("success"), 1100);
  }
  if (target.dataset.editLink !== undefined) {
    videoLink.focus();
    videoLink.select();
  }
  if (target.dataset.transcript !== undefined) alert("原型提示：这里会打开完整逐字稿；第二阶段重点验证生成器中的查看与修正流程。");
  if (target.dataset.download !== undefined) {
    const downloadLabels = {
      video: "视频 MP4",
      audio: "音频 MP3",
      "transcript-txt": "逐字稿 TXT",
      "transcript-md": "逐字稿 Markdown",
    };
    alert(`原型提示：这里会按需准备${downloadLabels[target.dataset.download] ?? "文件"}下载；本阶段不产生真实文件。`);
  }
  if (target.dataset.closeModal !== undefined) target.closest("dialog")?.close();
  if (target.dataset.confirmDelete !== undefined) {
    deleteDialog.close();
    setParserState("history");
    alert("原型提示：示例记录已从当前界面移除。刷新页面即可恢复固定假数据。");
  }
});

document.querySelectorAll("[data-nav]").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.nav));
});

[notesDialog, deleteDialog, restoreDialog, noteDeleteDialog, newNoteDialog].filter(Boolean).forEach((dialog) => dialog.addEventListener("click", (event) => {
  const bounds = dialog.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
}));

setParserState("empty");
setNotesState("input");
renderPlatformDetection();
