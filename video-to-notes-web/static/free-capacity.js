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
        title: "导入逐字稿后，这里会给出明确结论",
        copy: "系统会告诉你这份内容是否适合免费线路、可能需要等待多久，以及内容过长时应该换哪种方式。",
      },
      recommended: {
        chip: "可以直接使用",
        title: "本次笔记适合使用免费线路",
        copy: "内容长度在建议范围内，预计等待约 3–7 分钟。选择免费线路后可以直接开始。",
      },
      caution: {
        chip: "可能等待更久",
        title: "可以使用免费线路，但速度和稳定性会下降",
        copy: "这份内容已经超过较稳定的建议范围，仍可尝试；如果生成失败，可以改用高速线路、常用 AI 或 To Notes Skill。",
      },
      high_risk: {
        chip: "建议更换方式",
        title: "本次笔记不建议使用免费线路",
        copy: "内容已经超出免费线路较稳定的处理范围，生成过程中可能中断。建议改用高速线路、常用 AI 或 To Notes Skill。",
      },
    }[level];

    return { level, characters, minutes, facts, ...content };
  }

  window.VTNFreeCapacity = { LIMITS, assess, nonWhitespaceCharacters };
})();
