const header = document.querySelector("[data-header]");
const revealTargets = document.querySelectorAll(".reveal");

const updateHeader = () => {
  header?.classList.toggle("is-scrolled", window.scrollY > 18);
};

updateHeader();
window.addEventListener("scroll", updateHeader, { passive: true });

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.12 }
  );

  revealTargets.forEach((target) => observer.observe(target));
} else {
  revealTargets.forEach((target) => target.classList.add("is-visible"));
}

const scenarioTabs = document.querySelectorAll("[data-scenario]");
const scenarioPanels = document.querySelectorAll("[data-scenario-panel]");

scenarioTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const target = tab.dataset.scenario;

    scenarioTabs.forEach((candidate) => {
      const isActive = candidate === tab;
      candidate.classList.toggle("is-active", isActive);
      candidate.setAttribute("aria-selected", String(isActive));
    });

    scenarioPanels.forEach((panel) => {
      const isActive = panel.dataset.scenarioPanel === target;
      panel.classList.toggle("is-active", isActive);
      panel.hidden = !isActive;
    });
  });
});

const proofData = {
  parser: {
    src: "/static/landing/assets/parser-result.png",
    alt: "视频解析完成结果页面",
    shift: "-34%",
    kicker: "STEP 01 / PARSER",
    title: "先把内容拿出来。",
    copy: "解析完成后，视频信息、逐字稿、复制与下载入口集中在同一页面。",
  },
  recommend: {
    src: "/static/landing/assets/note-recommendations.png",
    alt: "系统预读逐字稿后的笔记方案推荐页面",
    shift: "-25%",
    kicker: "STEP 02 / PRE-READ",
    title: "先理解，再决定笔记结构。",
    copy: "系统结合逐字稿与本次用途，推荐结构、详细程度、生成方式和附加模块。",
  },
  reading: {
    src: "/static/landing/assets/note-reading.png",
    alt: "结构化笔记成品阅读页面",
    shift: "-10%",
    kicker: "STEP 03 / READING",
    title: "最后得到可继续使用的成品。",
    copy: "笔记可以阅读、编辑、复制和导出；逐字稿也始终保留，不强制绑定在笔记流程里。",
  },
};

const proofTabs = document.querySelectorAll("[data-proof]");
const proofImage = document.querySelector("[data-proof-image]");
const proofCaption = document.querySelector("[data-proof-caption]");

proofTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const next = proofData[tab.dataset.proof];
    if (!next || !proofImage || !proofCaption) return;

    proofTabs.forEach((candidate) => {
      const isActive = candidate === tab;
      candidate.classList.toggle("is-active", isActive);
      candidate.setAttribute("aria-selected", String(isActive));
    });

    proofImage.classList.add("is-changing");
    window.setTimeout(() => {
      proofImage.src = next.src;
      proofImage.alt = next.alt;
      proofImage.style.setProperty("--proof-shift", next.shift);
      proofImage.classList.remove("is-changing");
    }, 160);

    proofCaption.innerHTML = `
      <span>${next.kicker}</span>
      <h3>${next.title}</h3>
      <p>${next.copy}</p>
    `;
  });
});

const copyPromptButton = document.querySelector("[data-copy-prompt]");
const toast = document.querySelector("[data-toast]");
let toastTimer;

copyPromptButton?.addEventListener("click", async () => {
  const prompt = "请分析这组逐字稿的选题规律、开头结构和信息展开方式，并用表格比较。请只总结方法，不复制原文。";

  try {
    await navigator.clipboard.writeText(prompt);
    copyPromptButton.firstChild.textContent = "已复制 ";
    toast?.classList.add("is-visible");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toast?.classList.remove("is-visible");
      copyPromptButton.firstChild.textContent = "复制示例提示词 ";
    }, 1800);
  } catch {
    toast.textContent = "浏览器未允许复制，请手动选择提示词";
    toast?.classList.add("is-visible");
  }
});
