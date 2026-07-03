import { motion } from "framer-motion";

// ============================================================
// 全部参数从 Obsidian Vercel 笔记提取，仅主色从蓝换紫
// ============================================================

const tokens = {
  colors: {
    primary: "#7c3aed",    // ← 原 #0070f3，换成紫色
    bg: "#fafafa",         // 保持
    fg: "#171717",         // 保持
    muted: "#666666",      // 保持
    border: "#ebebeb",     // 保持
  },
  font: {
    sans: "GeistSans, system-ui, -apple-system, sans-serif",
    mono: "Geist Mono, ui-monospace, monospace",
  },
  radii: { xs: "2px", md: "6px", lg: "12px" },
};

// ===== 动画参数 — 全部从笔记物理基因提取 =====
const ease = [0.4, 0, 0.2, 1];

const transitions = {
  base: { duration: 0.3, ease },
  spring: { type: "spring" as const, stiffness: 320, damping: 30 },
};

const fadeIn = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: transitions.base },
};

const slideUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: transitions.base },
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.96 },
  show: { opacity: 1, scale: 1, transition: transitions.base },
};

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.075 } },
};

const inView = {
  once: true,
  amount: 0.3,
};

// ============================================================
// Hero 首屏
// ============================================================
function Hero() {
  return (
    <section
      style={{
        background: tokens.colors.bg,
        fontFamily: tokens.font.sans,
      }}
      className="min-h-screen flex flex-col items-center justify-center px-6 text-center"
    >
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="max-w-3xl"
      >
        {/* h1: 64px / 400 — 从笔记标题层级提取 */}
        <motion.h1
          variants={slideUp}
          style={{
            fontSize: 64,
            fontWeight: 400,
            lineHeight: "64px",
            color: tokens.colors.fg,
          }}
        >
          用 AI 把灵感变成产品，<br />
          <span style={{ color: tokens.colors.primary }}>
            比想象中快 10 倍
          </span>
        </motion.h1>

        {/* 正文: 14px — 从笔记提取 */}
        <motion.p
          variants={slideUp}
          style={{
            fontSize: 14,
            fontWeight: 400,
            lineHeight: "20px",
            color: tokens.colors.muted,
          }}
          className="mt-6 max-w-xl mx-auto"
        >
          不需要写一行代码，上传你的灵感截图，AI 自动生成可运行的产品页面。
          从想法到上线，原来要走三周的路，现在一顿午饭的时间就够了。
        </motion.p>

        {/* 按钮区 */}
        <motion.div variants={fadeIn} className="mt-10 flex gap-4 justify-center">
          <button
            style={{
              background: tokens.colors.primary,
              color: "#fff",
              borderRadius: tokens.radii.md,
              fontSize: 14,
            }}
            className="px-8 py-3 font-medium hover:opacity-90 transition-opacity"
          >
            免费开始使用
          </button>
          <button
            style={{
              color: tokens.colors.fg,
              borderRadius: tokens.radii.md,
              border: `1px solid ${tokens.colors.border}`,
              fontSize: 14,
            }}
            className="px-8 py-3 font-medium hover:bg-gray-50 transition-colors"
          >
            观看演示
          </button>
        </motion.div>
      </motion.div>
    </section>
  );
}

// ============================================================
// 特性卡片区
// ============================================================
const features = [
  {
    title: "截图即代码",
    desc: "上传任意网页截图或设计稿，AI 自动识别布局、配色、动效，输出可运行的 React 代码。",
  },
  {
    title: "灵感基因库",
    desc: "喜欢的交互动画一键存入 Obsidian，永久积累。下次做项目直接调用，不再从零开始。",
  },
  {
    title: "精确动画还原",
    desc: "不是「感觉很流畅」——是 stiffness: 320, damping: 30。每个参数都精准复刻。",
  },
  {
    title: "Claude Code 驱动",
    desc: "读取你的基因档案，生成符合你审美标准的生产级代码。DeepSeek 不瞎猜。",
  },
  {
    title: "多框架输出",
    desc: "React、Vue、Svelte 自由切换。动画同步输出 Framer Motion、GSAP、WAAPI 三种版本。",
  },
  {
    title: "一键部署",
    desc: "代码生成后直接连 Vercel 部署，链接发出去就是成品。改颜色改文案随时重生成。",
  },
];

function FeatureCards() {
  return (
    <section
      style={{
        background: "#fff",
        fontFamily: tokens.font.sans,
      }}
      className="py-32 px-6"
    >
      <motion.div
        variants={stagger}
        initial="hidden"
        whileInView="show"
        viewport={inView}
        className="max-w-5xl mx-auto"
      >
        {/* h2: 56px / 450 — 从笔记标题层级提取 */}
        <motion.h2
          variants={slideUp}
          style={{
            fontSize: 56,
            fontWeight: 450,
            lineHeight: "56px",
            color: tokens.colors.fg,
          }}
          className="text-center mb-4"
        >
          你需要的，我们都准备好了
        </motion.h2>
        <motion.p
          variants={slideUp}
          style={{ fontSize: 14, color: tokens.colors.muted }}
          className="text-center mb-20"
        >
          六个核心能力，覆盖从灵感到上线的全过程
        </motion.p>

        {/* 卡片网格: 3 列，间距 32px — 从笔记间距尺度提取 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((f, i) => (
            <motion.div
              key={i}
              variants={scaleIn}
              style={{
                borderRadius: tokens.radii.lg,
                border: `1px solid ${tokens.colors.border}`,
                background: tokens.colors.bg,
              }}
              className="p-8 hover:shadow-md transition-shadow"
            >
              {/* 紫色装饰线 — 替代原来的蓝色 */}
              <div
                style={{
                  width: 32,
                  height: 4,
                  borderRadius: tokens.radii.xs,
                  background: tokens.colors.primary,
                }}
                className="mb-4"
              />
              <h3
                style={{
                  fontSize: 14,
                  fontWeight: 500,
                  color: tokens.colors.fg,
                }}
                className="mb-2"
              >
                {f.title}
              </h3>
              <p
                style={{
                  fontSize: 14,
                  lineHeight: "20px",
                  color: tokens.colors.muted,
                }}
              >
                {f.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
  );
}

// ============================================================
// CTA 行动按钮区
// ============================================================
function CTA() {
  return (
    <section
      style={{
        background: tokens.colors.fg,
        fontFamily: tokens.font.sans,
      }}
      className="py-32 px-6 text-center"
    >
      <motion.div
        variants={stagger}
        initial="hidden"
        whileInView="show"
        viewport={inView}
        className="max-w-2xl mx-auto"
      >
        <motion.h2
          variants={slideUp}
          style={{
            fontSize: 56,
            fontWeight: 450,
            lineHeight: "56px",
            color: "#fff",
          }}
        >
          现在就开始构建
        </motion.h2>

        <motion.p
          variants={slideUp}
          style={{ fontSize: 14, lineHeight: "20px", color: "#a1a1aa" }}
          className="mt-6"
        >
          免费账户包含 10 次 AI 生成额度，不需要信用卡。
          把积压的设计灵感，变成可以点开的产品页面。
        </motion.p>

        <motion.div variants={fadeIn} className="mt-10 flex gap-4 justify-center">
          <button
            style={{
              background: tokens.colors.primary,
              color: "#fff",
              borderRadius: tokens.radii.md,
              fontSize: 14,
            }}
            className="px-8 py-3 font-medium hover:opacity-90 transition-opacity"
          >
            免费注册
          </button>
          <button
            style={{
              color: "#d4d4d8",
              borderRadius: tokens.radii.md,
              border: "1px solid #3f3f46",
              fontSize: 14,
            }}
            className="px-8 py-3 font-medium hover:bg-neutral-800 transition-colors"
          >
            联系销售
          </button>
        </motion.div>
      </motion.div>
    </section>
  );
}

// ============================================================
// 完整页面
// ============================================================
export default function AIToolLanding() {
  return (
    <main>
      <Hero />
      <FeatureCards />
      <CTA />
    </main>
  );
}
