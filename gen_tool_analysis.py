#!/usr/bin/env python3
"""生成 UI 灵感库工具深度分析 Excel 报告"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()

# ===== 通用样式 =====
header_font = Font(name="Arial", size=12, bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
sub_header_fill = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
sub_header_font = Font(name="Arial", size=11, bold=True, color="2F5496")
cell_font = Font(name="Arial", size=10)
bold_font = Font(name="Arial", size=10, bold=True)
green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
yellow_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
orange_fill = PatternFill(start_color="F4B183", end_color="F4B183", fill_type="solid")
wrap = Alignment(wrap_text=True, vertical="top")
center = Alignment(horizontal="center", vertical="top", wrap_text=True)
thin_border = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin")
)

def style_header(ws, row, max_col):
    for col in range(1, max_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin_border

def style_row(ws, row, max_col, is_sub=False):
    for col in range(1, max_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = sub_header_font if is_sub else cell_font
        cell.fill = sub_header_fill if is_sub else PatternFill()
        cell.alignment = wrap
        cell.border = thin_border

def apply_rating(ws, row, col, rating):
    """rating: best / good / medium / low / none"""
    cell = ws.cell(row=row, column=col)
    fills = {
        "best": green_fill, "good": green_fill,
        "medium": yellow_fill, "low": orange_fill,
        "none": red_fill
    }
    cell.fill = fills.get(rating, PatternFill())
    cell.alignment = center


# =============================================
# Sheet 1: 综合对比总览
# =============================================
ws1 = wb.active
ws1.title = "综合对比总览"

# 标题行
title_row = [
    "对比维度", "designlang\n(design-extract)", "Liftit\n(@ahmedessyad/liftit)",
    "brandmd", "SkillUI"
]
for c, t in enumerate(title_row, 1):
    ws1.cell(row=1, column=c, value=t)
style_header(ws1, 1, len(title_row))

# 数据
rows_data = [
    # (维度, designlang, liftit, brandmd, skillui, [rating_d, rating_l, rating_b, rating_s])
    ["npm 包名", "designlang", "@ahmedessyad/liftit", "brandmd", "skillui", None],
    ["当前版本", "v12.24+", "v1.1.0", "v0.12.0", "v1.3.4", None],
    ["许可证", "MIT（完全免费）", "公开包（免费）", "MIT（完全免费）", "MIT（完全免费）", None],
    ["GitHub Stars", "~1,700+", "N/A（仅npm）", "⭐36", "~860+", None],
    ["安装方式", "npx designlang", "npm i -g liftit", "npx brandmd", "npm i -g skillui", None],
    ["依赖/体积", "Playwright ~150MB", "Playwright ~150MB", "Playwright ~150MB", "默认模式无需浏览器\nUltra需Playwright ~150MB", None],
    ["是否需要 API Key", "不需要", "不需要", "默认不需要\n--vision需Gemini key", "不需要", None],

    # 核心能力评级
    ["⭐ 设计Token提取\n(颜色/字体/间距/阴影/圆角)", "★★★★★", "★★★★★", "★★★★☆", "★★★★☆", ["best","best","good","good"]],
    ["⭐ 动画/动效提取", "★★★★★\n(runtime + static)", "★★★★★\n(逐帧录制)", "★☆☆☆☆\n(几乎不支持)", "★★★☆☆\n(仅keyframes)", ["best","best","none","medium"]],
    ["⭐ 组件检测/提取", "★★★★★\n(React TSX + variant矩阵)", "★★★★★\n(React .tsx+.module.css)", "★★★☆☆\n(buttons/cards/inputs)", "★★★★☆\n(DOM指纹识别)", ["best","best","medium","good"]],
    ["⭐ 交互动画\n(hover/scroll/过渡)", "★★★★★\n(runtime捕获)", "★★★★★\n(逐帧hover+scroll)", "★☆☆☆☆\n(不支持)", "★★★☆☆\n(hover diffs)", ["best","best","none","medium"]],
    ["⭐ 多页面爬取", "★★★★★\n(site命令全站)", "★★★★☆\n(scan --crawl 20页)", "★★☆☆☆\n(手动多URL合并)", "★★★☆☆\n(最多20页)", ["best","good","low","medium"]],
    ["⭐ 响应式断点", "★★★★★\n(4个viewport)", "★★★★★\n(8个断点)", "★★☆☆☆\n(无)", "★★☆☆☆\n(无)", ["best","best","low","low"]],
    ["⭐ Claude Code 集成", "★★★★★\n(13个slash命令+MCP)", "★★★☆☆\n(DESIGN.md兼容)", "★★★★☆\n(--agent写规则文件)", "★★★★★\n(SKILL.md自动加载)", ["best","medium","good","best"]],
    ["⭐ Obsidian 友好度", "★★★★☆\n(19节MD文档)", "★★★★☆\n(DESIGN.md)", "★★★★★\n(DESIGN.md简洁)", "★★★★☆\n(DESIGN.md+SKILL.md)", ["good","good","best","good"]],

    # 输入/输出
    ["输入方式", "URL", "URL / 本地CSS文件", "URL", "URL / 本地目录 / Git仓库", None],
    ["输出文件数", "17+ 个", "~10 个", "1-5 个", "~12 个", None],
    ["Markdown 输出", "✅ 19节设计语言MD", "✅ DESIGN.md", "✅ DESIGN.md\n(精简5-7节)", "✅ DESIGN.md + SKILL.md", None],
    ["JSON 输出", "✅ DTCG tokens + motion + voice", "✅ design-system.json + motion-distilled.json", "✅ --json标志", "✅ colors/spacing/typography分文件", None],
    ["Tailwind 输出", "✅ v4 @theme", "✅ tailwind.config.ts", "✅ v4 @theme块", "❌ 无", None],
    ["组件代码输出", "✅ React TSX + variant矩阵\n+iOS/Android/Flutter", "✅ React .tsx + .module.css\n(逐组件提取)", "❌ 无", "❌ 无", None],

    # 特色能力
    ["独特能力1", "品牌声音提取\n(tone/pronoun/CTA风格)", "帧级CSS Diff/Match\n(对比你的代码vs目标站)", "--vision标志\n(Gemini视觉分析)", "Default模式无需浏览器\n(纯静态分析)", None],
    ["独特能力2", "WCAG无障碍评分\n+修复建议", "pixelmatch像素级验证\n(0.1阈值)", "多URL Token合并", "Ultra模式7段滚动截图\n+交互前后状态diff", None],
    ["独特能力3", "设计一致性评分\n(0-100分)", "76个CSS属性/元素\n+scroll-interaction映射", "HTML品牌指南\n(带色块字体可视化)", ".skill ZIP打包\n(Claude Code一键加载)", None],

    # 局限性
    ["主要局限", "偏重(150MB)\nSPA需tune --wait参数", "较新(1.1.0)\n社区小", "无动画提取\n~20%字体错误率\n仅公开URL", "较新(2026.4发布)\nUltra模式动画=仅keyframes\nJS动画捕获不完整", None],
]

for i, data in enumerate(rows_data):
    row = i + 2
    for c, val in enumerate(data[:5], 1):
        ws1.cell(row=row, column=c, value=val)
    style_row(ws1, row, 5)
    # Apply rating fills if present
    if data[5]:
        for c, rating in enumerate(data[5], 2):
            apply_rating(ws1, row, c, rating)

# 列宽
ws1.column_dimensions['A'].width = 24
for col in ['B', 'C', 'D', 'E']:
    ws1.column_dimensions[col].width = 30

# 冻结首行
ws1.freeze_panes = "B2"


# =============================================
# Sheet 2: 动画提取能力深度对比
# =============================================
ws2 = wb.create_sheet("动画提取能力深度对比")

anim_title = ["动画提取维度", "designlang", "Liftit", "brandmd", "SkillUI"]
for c, t in enumerate(anim_title, 1):
    ws2.cell(row=1, column=c, value=t)
style_header(ws2, 1, len(anim_title))

anim_data = [
    # 分组标题
    ["═══ CSS 动画提取 ═══", "", "", "", ""],
    ["CSS @keyframes 提取", "✅ 完整提取+审计", "✅ 提取", "❌", "✅ Ultra模式提取"],
    ["CSS transition 提取", "✅ 含duration/easing/延迟", "✅ 76属性/元素", "❌", "❌"],
    ["animation-duration 分桶", "✅ 语义化分桶\n(instant/xs/sm/md/lg/xl)", "❌", "❌", "❌"],
    ["easing 家族分类", "✅ ease/ease-in/cubic-bezier\nspring曲线检测", "✅ from/to值+triggers", "❌", "❌"],
    ["spring 弹簧检测", "✅ 识别overshoot cubic-bezier\n标记spring曲线", "❌", "❌", "❌"],

    # 运行时动画
    ["═══ 运行时动画捕获 ═══", "", "", "", ""],
    ["document.getAnimations()", "✅ --motion-runtime标志\n捕获实际运行动画", "✅ Web Animations API", "❌", "❌"],
    ["实际测量duration", "✅ 测量运行时间线\n(非仅CSS声明值)", "✅ 压缩为from/to值+triggers", "❌", "❌"],
    ["动效风格指纹", "✅ springy/smooth/mechanical", "❌", "❌", "❌"],

    # 微交互
    ["═══ 微交互/状态 ═══", "", "", "", ""],
    ["Hover 状态捕获", "✅ --interactions标志\n触发hover并记录style delta", "✅ 逐帧录制hover\n记录每个元素前后状态", "❌", "✅ Ultra模式\nhover/focus状态diff"],
    ["Focus 状态捕获", "✅ 同上", "✅ 逐帧录制", "❌", "✅ Ultra模式"],
    ["Active 状态捕获", "✅ 同上", "✅ 逐帧录制", "❌", "❌"],
    ["动画库检测", "❌", "❌", "❌", "✅ 检测window.*全局变量\n(GSAP/Framer/AOS等)"],

    # 滚动动画
    ["═══ 滚动动画 ═══", "", "", "", ""],
    ["滚动驱动动画检测", "✅ 检测scroll-linked动画\nparallax/pin/reveal", "✅ 逐位置录制样式变化\nscroll-interaction映射", "❌", "❌"],
    ["Stagger/编排检测", "✅ 检测元素延迟偏移\n输出choreography数组", "❌", "❌", "❌"],
    ["滚动截图", "✅ --full包含", "✅ 8个断点截图", "❌", "✅ Ultra模式7段截图"],

    # 输出
    ["═══ 动画输出格式 ═══", "", "", "", ""],
    ["专用动画文件", "✅ motion-tokens.json\n含choreography+scrollRecipes", "✅ motion-distilled.json\nscroll-interactions.json", "❌", "✅ ANIMATIONS.md\nINTERACTIONS.md"],
    ["动画参数格式", "durations/easings/springs\nscroll-linked flag\nchoreography/stagger\nscroll recipes", "from/to值+triggers\n+durations", "无", "@keyframes源码\n动画库名称列表"],
    ["Claude Code 可读性", "★★★★★\n可直接转为Framer Motion参数", "★★★★☆\nfrom/to值可直接用", "无", "★★★☆☆\n需人工补充参数"],

    # 综合评价
    ["═══ 综合评价 ═══", "", "", "", ""],
    ["动画提取总分", "🥇 9.5/10\n业界唯一双重提取", "🥈 8.5/10\n逐帧录制最细致", "0/10\n不支持动画", "🥉 5/10\n仅CSS keyframes"],
    ["适合场景", "需要精确动画参数\n+编排关系的场景", "需要像素级还原\n+本地代码对比的场景", "仅静态品牌色板/字体", "快速扫描+截图存档"],
]

for i, data in enumerate(anim_data):
    row = i + 2
    for c, val in enumerate(data, 1):
        ws2.cell(row=row, column=c, value=val)
    is_sub = data[0].startswith("═══")
    style_row(ws2, row, 5, is_sub=is_sub)

ws2.column_dimensions['A'].width = 28
for col in ['B', 'C', 'D', 'E']:
    ws2.column_dimensions[col].width = 30
ws2.freeze_panes = "B2"


# =============================================
# Sheet 3: 与用户工作流匹配度
# =============================================
ws3 = wb.create_sheet("与你的工作流匹配度")

wf_title = ["你的工作流环节", "需求描述", "designlang 匹配度", "Liftit 匹配度", "brandmd 匹配度", "SkillUI 匹配度"]
for c, t in enumerate(wf_title, 1):
    ws3.cell(row=1, column=c, value=t)
style_header(ws3, 1, len(wf_title))

wf_data = [
    [
        "🔍 提取网页设计",
        "访问URL，自动提取\n设计token+动画+组件",
        "⭐⭐⭐⭐⭐\nnpx一键，17+文件输出\n覆盖全部需求",
        "⭐⭐⭐⭐⭐\nnpx一键，~10文件\n动画录制最细致",
        "⭐⭐⭐\n仅静态token，无动画\n不适合你的需求",
        "⭐⭐⭐⭐\n双模式灵活\n但动画弱"
    ],
    [
        "🎬 动画捕获\n（核心需求）",
        "交互动画灵感→\n可执行参数",
        "⭐⭐⭐⭐⭐\n双层捕获+编排检测\n直接输出spring参数",
        "⭐⭐⭐⭐⭐\n逐帧录制+压缩参数\n像素级还原",
        "⭐\n不支持动画",
        "⭐⭐⭐\n仅keyframes\n缺少时序参数"
    ],
    [
        "🧬 生成基因档案\n（存入Obsidian）",
        "结构化Markdown\n→ Obsidian笔记",
        "⭐⭐⭐⭐\n19节MD文档\n内容全面但偏长",
        "⭐⭐⭐⭐\nDESIGN.md\n格式兼容AI agent",
        "⭐⭐⭐⭐⭐\nDESIGN.md简洁\nObsidian收集最友好",
        "⭐⭐⭐⭐\nSKILL.md+DESIGN.md\n双文档格式"
    ],
    [
        "🤖 Claude Code\n读取执行\n（DeepSeek API）",
        "我(Claude Code)读MD\n→生成React代码",
        "⭐⭐⭐⭐⭐\nMCP Server + 13命令\nAgent规则自动生成",
        "⭐⭐⭐⭐\nDESIGN.md Stitch兼容\n需手动指引",
        "⭐⭐⭐⭐\n--agent写规则\n.claude/skills/目录",
        "⭐⭐⭐⭐⭐\nSKILL.md原生加载\nCLAUDE.md自动读取"
    ],
    [
        "📱 Gemini网页版\n手动配合",
        "你手动截图给Gemini\n拿到感性描述",
        "⭐⭐⭐⭐⭐\n可替代Gemini\n直接提取精确色值",
        "⭐⭐⭐⭐⭐\n同样可替代Gemini\n76属性/元素",
        "⭐⭐⭐⭐\n--vision需API\n不能用网页Gemini",
        "⭐⭐⭐⭐\n纯静态分析\n配合Gemini截图用"
    ],
    [
        "📦 Obsidian存储",
        "存为Markdown笔记\n标签+双链分类",
        "⭐⭐⭐⭐\n输出到文件夹\n需手动搬入Obsidian",
        "⭐⭐⭐⭐\n同上\n输出到文件夹",
        "⭐⭐⭐⭐⭐\nDESIGN.md直接\n可拖入Obsidian",
        "⭐⭐⭐⭐\n.skill ZIP格式\n需解压后放入"
    ],
    [
        "💰 零成本",
        "不能付费\n只能免费工具",
        "✅ MIT免费\n无任何付费项",
        "✅ 公开免费包\n无付费项",
        "✅ MIT免费\n无付费项",
        "✅ MIT免费\n无付费项"
    ],
    [
        "🏗️ 多页面支持",
        "复刻多页面\n交互流程",
        "⭐⭐⭐⭐⭐\nsite命令全站爬取\n+一致性评分",
        "⭐⭐⭐⭐\nscan --crawl 20页\n+cookie支持",
        "⭐⭐\n手动合并URL\n非自动化",
        "⭐⭐⭐\n--screens最多20页\n单次截图"
    ],
    [
        "🎯 综合匹配度",
        "",
        "🥇 30/35\n最全面但偏重",
        "🥈 28/35\n动画最强但社区小",
        "🥉 17/35\n动画缺失不适合",
        "🥈 25/35\n轻量但动画弱"
    ],
]

for i, data in enumerate(wf_data):
    row = i + 2
    for c, val in enumerate(data, 1):
        ws3.cell(row=row, column=c, value=val)
    style_row(ws3, row, 6)

ws3.column_dimensions['A'].width = 22
ws3.column_dimensions['B'].width = 24
for col in ['C', 'D', 'E', 'F']:
    ws3.column_dimensions[col].width = 28
ws3.freeze_panes = "C2"


# =============================================
# Sheet 4: 推荐方案 & 行动步骤
# =============================================
ws4 = wb.create_sheet("推荐方案")

# 结论区
ws4.merge_cells('A1:D1')
ws4.cell(row=1, column=1, value="UI 灵感库工具推荐 — 最终结论")
ws4['A1'].font = Font(name="Arial", size=14, bold=True, color="2F5496")
ws4['A1'].alignment = Alignment(horizontal="center", vertical="center")
ws4['A1'].fill = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")

# 推荐组合
rec = [
    ["", "工具", "角色", "原因"],
    ["首选", "designlang\n(design-extract)", "主提取引擎", "业界唯一支持双层动画捕获（CSS静态+runtime）\n17+文件输出量最全\nMCP Server原生对接Claude Code\nmotion-tokens.json直接映射你的「物理基因」层\nWCAG+一致性评分可做质量把关\nMIT免费无限制"],
    ["首选", "Liftit", "补充+验证引擎", "逐帧录制动画精度最高（76属性/元素）\npixelmatch像素级验证确保还原度\n组件提取输出React .tsx+.module.css直接可用\nCSS Diff/Match功能可对比你的代码vs原站\n适合需要极高动画还原精度的场景"],
    ["备选", "SkillUI", "轻量快速扫描", "Default模式无需浏览器，秒级分析\nUltra模式有7段滚动截图便于人工检视\n.skill ZIP一键加载到Claude Code\n适合日常快速收集灵感时使用"],
    ["不推荐", "brandmd", "N/A", "无动画提取能力，不适合你的核心需求\n如果你只需要静态品牌色板，可以考虑\n但作为UI交互动画灵感库=不适用"],
]

for i, data in enumerate(rec):
    row = i + 3
    for c, val in enumerate(data, 1):
        cell = ws4.cell(row=row, column=c, value=val)
        if i == 0:
            cell.font = bold_font
            cell.fill = sub_header_fill
        else:
            cell.font = cell_font
        cell.alignment = wrap
        cell.border = thin_border

# 为什么选两工具组合
ws4.merge_cells('A9:D9')
ws4.cell(row=9, column=1, value="为什么推荐 designlang + Liftit 组合？")
ws4['A9'].font = Font(name="Arial", size=12, bold=True, color="2F5496")

reasons = [
    "1. designlang 覆盖面最广，但动画的「精细度」不如 Liftit 逐帧录制——两者互补",
    "2. designlang 的 MCP Server 让我（Claude Code）能直接读取token，省去手动喂入的步骤",
    "3. Liftit 的 CSS Diff/Match 功能独一无二——你复刻后可以对比原站验证还原度",
    "4. designlang 输出 DTCG 标准token → 未来迁移到其他工具/框架无压力",
    "5. 两者都是免费+本地运行，不花一分钱",
]

for i, reason in enumerate(reasons):
    row = 10 + i
    ws4.merge_cells(f'A{row}:D{row}')
    ws4.cell(row=row, column=1, value=reason).font = cell_font

# 行动步骤
ws4.merge_cells('A16:D16')
ws4.cell(row=16, column=1, value="行动步骤")
ws4['A16'].font = Font(name="Arial", size=12, bold=True, color="2F5496")

steps = [
    ["第1步", "安装工具", "npm i -g designlang liftit\nnpx playwright install chromium", "5分钟"],
    ["第2步", "测试提取", "在你的 daydream 页面和另一个喜欢的网站上\n分别跑 designlang --full 和 liftit", "10分钟"],
    ["第3步", "对比输出", "打开两个工具的输出文件夹\n看看哪个格式你更喜欢，哪个更适合存 Obsidian", "15分钟"],
    ["第4步", "制定基因档案模板", "基于你选定的工具输出\n我帮你做标准化的 Obsidian 笔记模板", "由我来做"],
    ["第5步", "跑通闭环", "拿第一个基因档案\n让我（Claude Code）实际生成 React 代码\n验证「零损耗复刻」", "由我来做"],
]

step_header = ["", "步骤", "具体操作", "预计耗时"]
for c, h in enumerate(step_header, 1):
    cell = ws4.cell(row=17, column=c, value=h)
    cell.font = bold_font
    cell.fill = sub_header_fill
    cell.alignment = center
    cell.border = thin_border

for i, data in enumerate(steps):
    row = 18 + i
    for c, val in enumerate(data, 1):
        cell = ws4.cell(row=row, column=c, value=val)
        cell.font = bold_font if c == 1 else cell_font
        cell.alignment = wrap
        cell.border = thin_border

# 列宽
ws4.column_dimensions['A'].width = 16
ws4.column_dimensions['B'].width = 20
ws4.column_dimensions['C'].width = 45
ws4.column_dimensions['D'].width = 18

# ===== 保存 =====
output_path = "/Users/yubo/Claude code test/UI灵感库工具深度分析.xlsx"
wb.save(output_path)
print(f"Done: {output_path}")
