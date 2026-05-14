#!/usr/bin/env python3
"""Claude Code Stop hook — 交付验收：改代码必须验证，否则不许停。

Exit codes:
  0 — 允许停止 (无变更 / 已验证 / stop_hook_active)
  2 — 阻止停止，stderr 注入给 Claude 作为继续指令
"""

import json
import os
import subprocess
import sys


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    # ── 防止无限循环 ──
    if data.get("stop_hook_active"):
        sys.exit(0)

    cwd = data.get("cwd", os.getcwd())
    transcript_path = data.get("transcript_path", "")

    # ── 1. 检测是否有代码/配置/文档变更 ──
    has_changes = _git_has_changes(cwd)
    if not has_changes:
        sys.exit(0)

    # ── 2. 读取 transcript 检查验证行为 ──
    transcript_content = _read_transcript(transcript_path)
    if not transcript_content:
        # 无法读取 transcript，保守放行
        sys.exit(0)

    # ── 3. 检查各类验证证据 ──
    verification_checks = [
        _check_tests,
        _check_lint,
        _check_typecheck,
        _check_functional_verification,
        _check_todo_completion,
    ]

    for check in verification_checks:
        if check(transcript_content):
            sys.exit(0)

    # ── 4. 未经验证，阻止停止 ──
    changed_files = _git_changed_files(cwd)
    _block(
        changed_files=changed_files,
        total_checks=", ".join(c.__name__.replace("_check_", "") for c in verification_checks),
    )


# ═══════════════════════════════════════════════════════════════════
# 检测函数
# ═══════════════════════════════════════════════════════════════════

def _git_has_changes(cwd: str) -> bool:
    """检查 working tree 和暂存区是否有变更（排除 .claude/settings*）。"""
    try:
        # 未暂存变更
        r1 = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, cwd=cwd,
        )
        # 已暂存变更
        r2 = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=cwd,
        )
        all_changed = (r1.stdout.strip() + "\n" + r2.stdout.strip()).strip()
        if not all_changed:
            return False
        # 只过滤掉纯 .claude 配置变更
        meaningful = [f for f in all_changed.splitlines()
                      if f and not f.startswith(".claude/settings")]
        return len(meaningful) > 0
    except Exception:
        return False


def _git_changed_files(cwd: str) -> str:
    """返回变更文件列表（供提示用）。"""
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only"], capture_output=True, text=True, cwd=cwd
        )
        r2 = subprocess.run(
            ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, cwd=cwd
        )
        files = set((r.stdout + "\n" + r2.stdout).strip().splitlines()) - {""}
        return "\n".join(f"  - {f}" for f in sorted(files))
    except Exception:
        return "(无法获取变更列表)"


def _read_transcript(path: str) -> str:
    """读取 transcript JSONL 文件。"""
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════
# 验证证据检查器
# ═══════════════════════════════════════════════════════════════════

def _check_tests(transcript: str) -> bool:
    """检查是否运行了测试。"""
    patterns = [
        "npm test", "npm run test", "yarn test", "pnpm test",
        "pytest", "python -m pytest", "python -m unittest",
        "go test", "go test ./", "cargo test", "cargo t",
        "npx vitest", "npx jest", "npx playwright test",
        "npx mocha", "npx ava", "rspec", "bundle exec rspec",
        "mix test", "dotnet test", "mvn test", "gradle test",
        "make test", "make check",
        # 直接用 bash 跑脚本
        "python test", "python tests", "python -m ", ".test.",
        "node_modules/.bin/",
        "bin/test", "bin/rspec",
        # 通用的测试命令形式
        '"command"', '"test"',
    ]
    return _match_any(transcript, patterns)


def _check_lint(transcript: str) -> bool:
    """检查是否运行了 lint。"""
    patterns = [
        "eslint", "npx eslint", "prettier --check", "npx prettier",
        "flake8", "ruff check", "ruff format --check",
        "pylint", "black --check", "isort --check",
        "shellcheck", "shfmt -d",
        "stylelint", "markdownlint",
        "clippy", "golangci-lint",
        "hadolint", "tflint",
        "npx oxlint", "npx biome check",
        "deno lint", "deno fmt --check",
        "dart analyze", "flutter analyze",
        "luacheck",
        "lint-staged",
        "git diff --check",
    ]
    return _match_any(transcript, patterns)


def _check_typecheck(transcript: str) -> bool:
    """检查是否运行了类型检查。"""
    patterns = [
        "tsc", "npx tsc", "tsc --noEmit", "npx tsc --noEmit",
        "mypy", "pyright", "npx pyright",
        "go vet",
        "flow check", "npx flow",
        "sorbet", "steep check",
        "dart analyze",
        "cargo check",
        "npx tsc -p",
        "vue-tsc",
    ]
    return _match_any(transcript, patterns)


def _check_functional_verification(transcript: str) -> bool:
    """检查是否做了功能验证（打开浏览器、curl 测试、手动验证说明等）。"""
    patterns = [
        # 浏览器验证
        "open ", "xdg-open ", "browser", "浏览器",
        "功能验证", "验证结果", "验证通过",
        "端到端", "e2e", "E2E",
        # 手动验证说明
        "确认.*正常", "验证.*通过", "测试.*通过",
        "确认.*渲染", "验证.*功能",
        # curl / API 测试
        "curl ", "httpie ", "grpcurl ",
        # 构建验证
        "npm run build", "yarn build", "pnpm build",
        "npx vite build", "webpack --mode production",
        "go build", "cargo build",
        "make build", "make all",
        # 尝试打开页面
        "start ", "dev server", "localhost",
        # 一般性确认
        "all tests pass", "all checks pass",
        "everything works", "works as expected",
        "no errors", "successfully",
    ]
    return _match_any(transcript, patterns)


def _check_todo_completion(transcript: str) -> bool:
    """检查是否有 TODO 完成的证据（TodoWrite 标记 completed）。"""
    # TodoWrite tool calls with "completed" status
    patterns = [
        '"status": "completed"',
        '"_status": "completed"',
        "TodoWrite.*completed",
        "all todos completed",
        "All todos completed",
        "所有.*完成", "全部.*完成",
        "checklist.*complete",
    ]
    return _match_any(transcript, patterns)


def _match_any(text: str, patterns: list[str]) -> bool:
    """大小写不敏感匹配。"""
    lower = text.lower()
    return any(p.lower() in lower for p in patterns)


# ═══════════════════════════════════════════════════════════════════
# 阻止输出
# ═══════════════════════════════════════════════════════════════════

def _block(changed_files: str, total_checks: str):
    msg = {
        "decision": "block",
        "reason": (
            "⚠️  检测到以下文件变更，但未发现测试、lint、typecheck、"
            "功能验证或 TODO 完成标记：\n\n"
            f"{changed_files}\n\n"
            "请在结束前完成至少一项验证：\n"
            "  - 运行测试（npm test / pytest / go test 等）\n"
            "  - 运行 lint（eslint / ruff check / shellcheck 等）\n"
            "  - 运行 typecheck（tsc --noEmit / mypy / go vet 等）\n"
            "  - 功能验证（浏览器打开确认 / curl API 测试 / 构建验证）\n"
            "  - 标记所有 TODO 为 completed\n\n"
            "验证通过后再次尝试结束即可。"
        ),
    }
    print(json.dumps(msg, ensure_ascii=False), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
