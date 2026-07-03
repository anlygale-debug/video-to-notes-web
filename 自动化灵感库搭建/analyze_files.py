#!/usr/bin/env python3
"""分析 designlang 输出文件：跨 4 个站点对比，确定保留策略"""
import os, json, re
from pathlib import Path

BASE = Path(__file__).parent
SITES = {
    "01-vercel": "SaaS 落地页",
    "02-linear": "Web App",
    "03-tailwindcss": "文档站",
    "04-stripe": "企业 SaaS",
}

# designlang 固定输出的 40 个文件名后缀（去掉站点名前缀）
FILE_SUFFIXES = {
    "AGENT.md": "AGENT",
    "DESIGN.md": "DESIGN",
    "design-language.md": "design-language",
    "design-tokens.json": "design-tokens",
    "variables.css": "variables",
    "tailwind-v4.css": "tailwind-v4",
    "tailwind.config.js": "tailwind-v3",
    "shadcn-theme.css": "shadcn",
    "theme.js": "theme",
    "reset.css": "reset",
    "gradients.css": "gradients-css",
    "gradients.json": "gradients-json",
    "anatomy.tsx": "anatomy",
    "voice.json": "voice",
    "visual-dna.json": "visual-dna",
    "intent.json": "intent",
    "motion.framer.js": "motion-framer",
    "motion.gsap.js": "motion-gsap",
    "motion.waapi.js": "motion-waapi",
    "motion.one.js": "motion-one",
    "motion.tailwind.js": "motion-tailwind",
    "motion.css": "motion-css",
    "motion.html": "motion-html",
    "motion-tokens.json": "motion-tokens",
    "figma-variables.json": "figma",
    "wordpress-theme.json": "wordpress",
    "tokens.d.ts": "tokens-ts",
    "preview.html": "preview",
    "mcp.json": "mcp",
    "library.json": "library",
    "logo.json": "logo",
    "icon-system.json": "icon-system",
    "stack-intel.json": "stack-intel",
    "seo.json": "seo",
    "perf.json": "perf",
    "form-states.json": "form-states",
    "screenshots.json": "screenshots-meta",
    "responsive.json": "responsive",
    "multipage.json": "multipage",
}


def find_file(site_dir, suffix):
    """在站点目录里找匹配后缀的文件"""
    for f in os.listdir(site_dir):
        if f.endswith(suffix):
            return os.path.join(site_dir, f)
    return None


def measure_md(path):
    """测量 Markdown 文件的丰富度"""
    if not path: return {"size": 0, "sections": 0, "has_data": False}
    with open(path) as f:
        content = f.read()
    sections = len(re.findall(r"^#{1,4}\s", content, re.MULTILINE))
    return {
        "size": len(content),
        "sections": sections,
        "has_data": len(content) > 200,
    }


def measure_js_animation(path):
    """测量 JS 动画文件的丰富度"""
    if not path:
        return {"size": 0, "variants": 0, "easings": 0, "exports": 0}
    with open(path) as f:
        content = f.read()
    variants = len(re.findall(r"export const |export function |module\.exports", content))
    easings = len(re.findall(r"ease|spring|duration|cubic-bezier", content, re.I))
    return {
        "size": len(content),
        "variants": variants,
        "easings": easings,
        "has_data": len(content) > 300,
    }


def measure_css(path):
    """测量 CSS 文件的丰富度"""
    if not path:
        return {"size": 0, "vars": 0, "rules": 0}
    with open(path) as f:
        content = f.read()
    vars_count = len(re.findall(r"--[\w-]+:", content))
    rules = len(re.findall(r"\{[^}]*\}", content))
    return {
        "size": len(content),
        "vars": vars_count,
        "rules": rules,
        "has_data": vars_count > 5,
    }


def measure_json(path):
    """测量 JSON 文件的丰富度"""
    if not path:
        return {"size": 0, "keys": 0, "depth": 0}
    try:
        with open(path) as f:
            data = json.load(f)
    except:
        return {"size": os.path.getsize(path) if path else 0, "keys": 0, "depth": 0}

    def count_keys(obj, depth=0):
        if isinstance(obj, dict):
            return sum(1 + count_keys(v, depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            return sum(count_keys(v, depth) for v in obj)
        return 0

    def max_depth(obj):
        if isinstance(obj, dict) and obj:
            return 1 + max(max_depth(v) for v in obj.values())
        elif isinstance(obj, list) and obj:
            return max(max_depth(v) for v in obj)
        return 0

    return {
        "size": len(json.dumps(data)),
        "keys": count_keys(data),
        "depth": max_depth(data),
        "has_data": bool(data) and len(json.dumps(data)) > 50,
    }


def measure_tsx(path):
    """测量 TSX 组件文件的丰富度"""
    if not path:
        return {"size": 0, "components": 0, "props": 0}
    with open(path) as f:
        content = f.read()
    components = len(re.findall(r"export (?:function|interface|const)", content))
    props = len(re.findall(r"Props\b", content))
    return {
        "size": len(content),
        "components": components,
        "props": props,
        "has_data": components >= 1,
    }


def analyze_file_type(suffix, filename_pattern, measurer):
    """跨 4 站点分析一种文件类型"""
    results = {}
    for site_id, site_label in SITES.items():
        site_dir = BASE / site_id
        filepath = find_file(str(site_dir), filename_pattern)
        results[site_id] = {
            "label": site_label,
            "found": filepath is not None,
            **measurer(filepath),
        }
    return results


def analyze_all():
    """分析所有文件类型"""
    report = {}

    # ---- Markdown 类 ----
    for suffix, pattern in [("AGENT.md", "AGENT.md"), ("DESIGN.md", "DESIGN.md")]:
        report[suffix] = analyze_file_type(suffix, pattern, measure_md)

    # design-language.md 用不同 pattern（含站点名）
    report["design-language.md"] = analyze_file_type(
        "design-language.md", "design-language.md", measure_md
    )

    # ---- JSON 类 ----
    json_files = [
        "design-tokens.json", "gradients.json", "voice.json", "visual-dna.json",
        "intent.json", "motion-tokens.json", "mcp.json",
        "library.json", "logo.json", "icon-system.json",
        "stack-intel.json", "seo.json", "perf.json", "form-states.json",
        "screenshots.json", "responsive.json", "multipage.json",
        "figma-variables.json", "wordpress-theme.json",
    ]
    for f in json_files:
        report[f] = analyze_file_type(f, f, measure_json)

    # ---- CSS 类 ----
    css_files = [
        "variables.css", "tailwind-v4.css", "shadcn-theme.css",
        "reset.css", "gradients.css", "motion.css",
    ]
    for f in css_files:
        report[f] = analyze_file_type(f, f, measure_css)

    # ---- JS 动画类 ----
    js_files = [
        "motion.framer.js", "motion.gsap.js", "motion.waapi.js",
        "motion.one.js", "motion.tailwind.js",
    ]
    for f in js_files:
        report[f] = analyze_file_type(f, f, measure_js_animation)

    # ---- TS 类型 ----
    report["tokens.d.ts"] = analyze_file_type("tokens.d.ts", "tokens.d.ts", measure_css)

    # ---- TSX 组件 ----
    report["anatomy.tsx"] = analyze_file_type("anatomy.tsx", "anatomy.tsx", measure_tsx)

    # ---- 其他 ----
    report["tailwind.config.js"] = analyze_file_type(
        "tailwind.config.js", "tailwind.config.js", measure_css
    )
    report["theme.js"] = analyze_file_type("theme.js", "theme.js", measure_js_animation)
    report["motion.html"] = analyze_file_type("motion.html", "motion.html", measure_md)
    report["preview.html"] = analyze_file_type("preview.html", "preview.html", measure_md)

    return report


def classify(report):
    """根据 4 站点分析结果，把文件分三类"""
    always_keep = []   # 4 站都有丰富内容 → 固定保留
    always_skip = []   # 4 站都没有内容/极低价值 → 固定跳过
    varies = []        # 不同站差异大 → 需按内容判断

    for filename, site_data in report.items():
        found_count = sum(1 for s in site_data.values() if s.get("found"))
        has_data_count = sum(1 for s in site_data.values() if s.get("has_data", False))
        sizes = [s.get("size", 0) for s in site_data.values()]

        max_size = max(sizes) if sizes else 0
        min_size = min(sizes) if sizes else 0

        # 提取细节指标
        details = {}
        for metric in ["sections", "variants", "easings", "vars", "rules", "keys", "depth", "components", "props"]:
            vals = [s.get(metric, 0) for s in site_data.values()]
            if any(v > 0 for v in vals):
                details[metric] = {"min": min(vals), "max": max(vals), "avg": sum(vals) / len(vals)}

        # 判断逻辑
        # 始终保留：4 站都有内容且至少 3 站数据丰富
        if has_data_count >= 4:
            always_keep.append(filename)
        # 始终跳过：4 站都没内容或全部 < 200 bytes
        elif has_data_count == 0 or (max_size < 300 and min_size < 100):
            always_skip.append(filename)
        # 其余：内容因站而异
        else:
            varies.append(filename)

        # 补充细节
        report[filename]["_summary"] = {
            "found": found_count,
            "has_data": has_data_count,
            "size_range": f"{min_size:,} – {max_size:,}",
            "details": details,
        }

    return always_keep, always_skip, varies


# ===== 运行分析 =====
if __name__ == "__main__":
    report = analyze_all()
    always_keep, always_skip, varies = classify(report)

    # 保存 JSON 报告
    output = {
        "always_keep": always_keep,
        "always_skip": always_skip,
        "varies": varies,
        "per_file": {},
    }
    for fname, sitedata in report.items():
        output["per_file"][fname] = sitedata["_summary"]

    with open(BASE / "analysis-report.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # 打印摘要
    print("=== 始终保留 ===")
    for f in always_keep:
        print(f"  ✅ {f}")

    print("\n=== 始终跳过 ===")
    for f in always_skip:
        print(f"  ❌ {f}")

    print("\n=== 因站而异 ===")
    for f in varies:
        s = report[f]["_summary"]
        print(f"  🔶 {f} (有数据: {s['has_data']}/4, 大小: {s['size_range']})")

    print("\n完整 JSON 已保存到 analysis-report.json")
