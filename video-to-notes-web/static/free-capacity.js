(() => {
  const LEVELS = { unknown: 0, recommended: 1, caution: 2, high_risk: 3 };
  const LIMITS = {
    recommendedSeconds: 30 * 60,
    cautionSeconds: 45 * 60,
    recommendedCharacters: 9_000,
    cautionCharacters: 13_500,
  };

  function nonWhitespaceCharacters(value) {
    return Array.from(String(value || "").replace(/\s/gu, "")).length;
  }

  function metricLevel(value, recommendedLimit, cautionLimit) {
    if (!Number.isFinite(value) || value <= 0) return "unknown";
    if (value <= recommendedLimit) return "recommended";
    if (value <= cautionLimit) return "caution";
    return "high_risk";
  }

  function assess({ transcript = "", durationSeconds = null } = {}) {
    const characters = nonWhitespaceCharacters(transcript);
    const duration = Number(durationSeconds);
    const durationLevel = metricLevel(
      duration,
      LIMITS.recommendedSeconds,
      LIMITS.cautionSeconds,
    );
    const characterLevel = metricLevel(
      characters,
      LIMITS.recommendedCharacters,
      LIMITS.cautionCharacters,
    );
    const level = LEVELS[durationLevel] >= LEVELS[characterLevel]
      ? durationLevel : characterLevel;
    const minutes = Number.isFinite(duration) && duration > 0
      ? Math.max(1, Math.ceil(duration / 60)) : null;
    const facts = [
      minutes ? `${minutes} 分钟` : null,
      characters ? `${characters.toLocaleString("zh-CN")} 字` : null,
    ].filter(Boolean).join(" · ");

    const content = {
      unknown: {
        chip: "等待内容",
        title: "粘贴后自动判断免费线路适配度",
        copy: "系统会同时参考视频时长和逐字稿字量；两项不一致时按风险更高的一项提示。",
      },
      recommended: {
        chip: "推荐范围",
        title: "适合使用免费线路",
        copy: "建议 30 分钟、约 9,000 字以内。实测通常需要等待约 3–7 分钟。",
      },
      caution: {
        chip: "谨慎尝试",
        title: "可以使用免费线路，但稳定性会下降",
        copy: "30–45 分钟或约 9,000–13,500 字可能等待更久；若格式漂移，系统会自动兼容可安全恢复的结果。",
      },
      high_risk: {
        chip: "失败风险较高",
        title: "当前不建议用免费线路直接生成",
        copy: "超过 45 分钟或约 13,500 字后，长输出可能中途断开。建议使用分段生成；高速线路开放后也可切换。",
      },
    }[level];

    return { level, characters, minutes, facts, ...content };
  }

  window.VTNFreeCapacity = { LIMITS, assess, nonWhitespaceCharacters };
})();
