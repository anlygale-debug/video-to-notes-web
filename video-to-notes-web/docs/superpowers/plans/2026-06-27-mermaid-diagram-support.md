# Mermaid 图表支持 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Mermaid diagram support to generated notes — 1 fixed framework diagram at top + max 2-3 content diagrams inline.

**Architecture:** Prompt-only changes on backend (add Mermaid guidance to 4 prompt templates), CDN + async render on frontend (mermaid@10 via jsdelivr). No new Python deps, no PDF changes.

**Tech Stack:** Python FastAPI, vanilla HTML/CSS/JS, marked.js, Mermaid 10

## Global Constraints

- 不新增 Python 依赖
- 不改动 PDF 导出
- 不改动下载功能
- 不改动 `_basic_notes()` fallback
- 不改动 detailed/scholar 分块拼接逻辑
- 不改变现有笔记内容结构
- Mermaid 版本锁定 mermaid@10，`neutral` 主题，`securityLevel: 'strict'`
- 框架图 1 张（笔记开头） + 内容图最多 2-3 张

---

### Task 1: Backend — Prompt 模板追加 Mermaid 指引

**Files:**

- Modify: `app.py:364-397` (`_generate_standard` prompt)
- Modify: `app.py:433-436` (`_generate_detailed` chunk prompt)
- Modify: `app.py:476-479` (`_scholar_prompt` chunk prompt)
- Modify: `app.py:481-521` (`_scholar_prompt` full prompt)

**Interfaces:**

- Produces: modified prompt strings — same return type, same callers, just longer prompts

- [ ] **Step 1: Modify `_generate_standard()` prompt (~L364-397)**

In the Output format section, insert before `## 核心论点`:

```python
## 内容框架图
用 Mermaid 图表展示本文的知识结构，放在笔记最前面。选择合适的图表类型（mindmap 或 graph TD），让读者一眼看清内容脉络和要点关系。

---
```

In the Rules section, after `- Output ONLY the markdown, no extra text`, append:

```python
- When content benefits from visualization, insert Mermaid diagrams (```mermaid code blocks). Use max 2-3 diagrams in the body
- Choose chart types wisely: flowchart (流程/步骤), quadrantChart (对比/四象限), sequenceDiagram (交互/消息传递), mindmap (层级关系), ganttChart (时间线/阶段)
- Only use diagrams when they genuinely add clarity — never force one
- The opening 内容框架图 diagram does NOT count toward the 2-3 limit
```

The full edited prompt becomes:

```python
    prompt = f"""You are a study note generator. Take the transcript of a video and produce structured markdown notes.

Output format:

# {title} — 课后笔记

> 视频作者：{creator} | 平台：{platform} | ❤️ {likes}
> 转录：本地 Whisper

---

## 内容框架图
用 Mermaid 图表展示本文的知识结构，放在笔记最前面。选择合适的图表类型（mindmap 或 graph TD），让读者一眼看清内容脉络和要点关系。

---

## 核心论点
[The main thesis — what is the key takeaway?]

## 内容框架
[Organize by the video's logical structure. Walk through every section/chapter in chronological order. Each section should have a subheading and at least one paragraph of detail. Do NOT skip any section.]

## 关键概念
[List and explain every key term or concept mentioned, with definitions]

## 个人思考
[3-5 actionable takeaways]

Rules:
- Output notes in Chinese, regardless of the transcript's original language
- Preserve the creator's exact key phrases in > blockquotes
- Use tables when comparing things
- **Cover every section — do not skip or gloss over any content**
- For each section, write at least one detailed paragraph explaining what was said
- Write so notes are useful without watching the video
- When content benefits from visualization, insert Mermaid diagrams (```mermaid code blocks). Use max 2-3 diagrams in the body
- Choose chart types wisely: flowchart (流程/步骤), quadrantChart (对比/四象限), sequenceDiagram (交互/消息传递), mindmap (层级关系), ganttChart (时间线/阶段)
- Only use diagrams when they genuinely add clarity — never force one
- The opening 内容框架图 diagram does NOT count toward the 2-3 limit
- Output ONLY the markdown, no extra text

Transcript:
{transcript}"""
```

- [ ] **Step 2: Modify `_generate_detailed()` chunk prompt (~L433)**

```python
        prompt = f"""Part {idx+1}/{total} of a video transcript. Generate detailed Chinese study notes for this section. Include key points, concepts, and important quotes (> blockquotes). Use ## headings. When content benefits from visualization, insert a Mermaid diagram (```mermaid code block) — but only if it genuinely adds clarity. Output ONLY the markdown.

Section {idx+1}/{total}:
{chunk}"""
```

- [ ] **Step 3: Modify `_scholar_prompt()` chunk prompt (~L476)**

```python
        return f"""Part {idx+1}/{total} of a transcript. Generate detailed Chinese study notes for this section in narrative paragraph style — NOT bullet points. Cover every concept mentioned. Preserve the speaker's key phrases in > blockquotes. Explain each concept thoroughly. Use ### for section headings. When content benefits from visualization, insert a Mermaid diagram (```mermaid code block) — but only if it genuinely adds clarity. Output ONLY markdown.

Section {idx+1}/{total}:
{transcript}"""
```

- [ ] **Step 4: Modify `_scholar_prompt()` full prompt (~L481-521)**

In Output format, insert before `## 本节概览`:

```python
## 内容框架图
用 Mermaid 图表展示本文的知识结构，放在笔记最前面。选择合适的图表类型（mindmap 或 graph TD），让读者一眼看清内容脉络和要点关系。

---
```

In Rules section, after the last rule bullet, before `Output ONLY the markdown`, insert:

```python
- When content benefits from visualization, insert Mermaid diagrams (```mermaid code blocks) in the body. Use max 2-3 diagrams
- Choose chart types wisely: flowchart (流程/步骤), quadrantChart (对比/四象限), sequenceDiagram (交互/消息传递), mindmap (层级关系), ganttChart (时间线/阶段)
- Only use diagrams when they genuinely add clarity — never force one
- The opening 内容框架图 diagram does NOT count toward the 2-3 limit
```

The full edited `_scholar_prompt()` becomes:

```python
def _scholar_prompt(transcript, title, creator, platform, likes, is_chunk=False, idx=0, total=0):
    """Build the scholar-mode prompt. is_chunk=True for per-chunk processing."""
    if is_chunk:
        return f"""Part {idx+1}/{total} of a transcript. Generate detailed Chinese study notes for this section in narrative paragraph style — NOT bullet points. Cover every concept mentioned. Preserve the speaker's key phrases in > blockquotes. Explain each concept thoroughly. Use ### for section headings. When content benefits from visualization, insert a Mermaid diagram (```mermaid code block) — but only if it genuinely adds clarity. Output ONLY markdown.

Section {idx+1}/{total}:
{transcript}"""

    return f"""You are a study note generator for a knowledge/theory course. Generate comprehensive narrative notes that allow someone to learn the material by reading alone — without watching the original video. The goal is completeness: no concept, example, or reasoning chain should be omitted.

Output format:

# {title} — 详解笔记

> 视频作者：{creator} | 平台：{platform} | ❤️ {likes}
> 转录：本地 Whisper

---

## 内容框架图
用 Mermaid 图表展示本文的知识结构，放在笔记最前面。选择合适的图表类型（mindmap 或 graph TD），让读者一眼看清内容脉络和要点关系。

---

## 本节概览
[2-3 sentences: what this lecture covers, what problem it solves, who it's for]

## 逐节详解
(Organize by the video's logical structure. Every topic/concept gets its own ### subsection. Walk through in chronological order — do NOT skip any section.)
### 一、{{first topic/concept}}
[Narrative paragraph(s) covering: how the teacher introduced it, the core definition, why it matters, examples given, key details and caveats. Use > blockquotes to preserve the teacher's exact key phrases.]
### 二、{{second topic/concept}}
[Continue for every topic — do not skip any]

## 关键术语表
| 术语 | 解释 | 关键表述 |
|------|------|----------|
| ... | ... | ... |

## 一句话总结
[One sentence takeaway]

Rules:
- Output in Chinese, regardless of transcript language
- Narrative paragraphs, NOT bullet points — preserve context and logical flow
- Use > blockquotes for the speaker's exact key phrases
- Each topic subsection must have at least one detailed paragraph
- Do NOT skip or gloss over any section of the content
- Write so the notes are a complete substitute for watching the video
- Suitable for reading and highlighting in Obsidian
- When content benefits from visualization, insert Mermaid diagrams (```mermaid code blocks) in the body. Use max 2-3 diagrams
- Choose chart types wisely: flowchart (流程/步骤), quadrantChart (对比/四象限), sequenceDiagram (交互/消息传递), mindmap (层级关系), ganttChart (时间线/阶段)
- Only use diagrams when they genuinely add clarity — never force one
- The opening 内容框架图 diagram does NOT count toward the 2-3 limit
- Output ONLY the markdown, no extra text

Transcript:
{transcript}"""
```

- [ ] **Step 5: Verify syntax**

```bash
cd "/Users/yubo/Claude code test/video-to-notes-web" && source ~/.agent-reach-venv/bin/activate && python3 -c "from app import app; print('OK')"
```

Expected: OK

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: add Mermaid diagram guidance to all prompt templates"
```

---

### Task 2: Frontend — Mermaid CDN + async rendering

**Files:**

- Modify: `static/index.html:7` (add CDN after marked.js)
- Modify: `static/index.html:~1043` (add mermaid.initialize before `</script>`)
- Modify: `static/index.html:941-962` (make showPreview async with mermaid.run)

**Interfaces:**

- Consumes: `marked.parse()` output (existing), DOM node `#previewContent`
- Produces: rendered SVG diagrams inside `#previewContent`

- [ ] **Step 1: Add Mermaid CDN in `<head>`**

After line 7 (`<script src="marked...">`), add:

```html
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
```

- [ ] **Step 2: Add mermaid.initialize() at end of `<script>`**

Before line 1044 (`</script>`), add:

```javascript
mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'strict' });
```

- [ ] **Step 3: Modify `showPreview()` to async with mermaid.run()**

Replace the existing `showPreview()` function (lines 941-962) with:

```javascript
async function showPreview(md) {
  $preview.style.display = 'block';
  $progress.style.display = 'none';
  $previewContent.innerHTML = marked.parse(md);
  document.getElementById('backToSearchBtn').style.display = _lastSearchResults ? '' : 'none';

  // In text mode, hide download buttons that don't apply and transcript preview
  const dlBtns = document.querySelectorAll('.dl-audio, .dl-transcript, .dl-merged, .dl-full');
  if (currentInputMode === 'text') {
    dlBtns.forEach(b => b.style.display = 'none');
    document.getElementById('transcriptPreview').style.display = 'none';
  } else {
    dlBtns.forEach(b => b.style.display = '');
    // Show transcript preview if available
    if (currentTranscript) {
      document.getElementById('transcriptPreview').style.display = 'block';
      document.getElementById('transcriptContent').textContent = currentTranscript;
      document.getElementById('transcriptLen').textContent = `(${currentTranscript.length} 字)`;
    }
  }
  $preview.scrollIntoView({behavior: 'smooth'});

  // Render Mermaid diagrams (async, non-blocking)
  try {
    await mermaid.run({
      nodes: $previewContent.querySelectorAll('code.language-mermaid'),
    });
  } catch (e) {
    // Mermaid rendering failure must not block note display
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add static/index.html
git commit -m "feat: add Mermaid CDN and async diagram rendering"
```

---

### Task 3: Manual verification

- [ ] **Step 1: Start server**

```bash
cd "/Users/yubo/Claude code test/video-to-notes-web" && source ~/.agent-reach-venv/bin/activate && uvicorn app:app --host 0.0.0.0 --port 3000 &
```

- [ ] **Step 2: Verify Mermaid library loads**

Open http://localhost:3000 → DevTools Console → type `typeof mermaid`
Expected: `"object"`

- [ ] **Step 3: Test with a sample markdown containing Mermaid**

Use text mode, paste a short transcript, select any mode, generate. Verify the framework diagram appears as rendered SVG at the top of notes.

- [ ] **Step 4: Test without Mermaid (regression check)**

Generate notes from a short transcript — verify no JS errors in console, notes render normally without diagrams.

- [ ] **Step 5: Test all 3 modes**

Run one generation in each mode (standard/detailed/scholar) — verify all complete without errors.

- [ ] **Step 6: Test PDF export**

Export any generated notes to PDF — verify PDF generates without crashing, Mermaid code blocks appear as plain text.

- [ ] **Step 7: Stop server**

```bash
kill $(lsof -ti :3000) 2>/dev/null
```
