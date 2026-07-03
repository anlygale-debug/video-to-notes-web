# 文本输入 + 详解模式 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add text-input mode (paste transcript directly) and scholar mode (narrative notes for reading-based learning) with adaptive chunking for long content.

**Architecture:** Backend changes are confined to `app.py` — new `_generate_scholar()` function and a text-mode branch in `/api/process` SSE handler. Frontend changes are confined to `static/index.html` — CSS/HTML/JS additions with no modifications to existing styles or logic.

**Tech Stack:** Python FastAPI, vanilla HTML/CSS/JS, DeepSeek via Anthropic-compatible API, local Whisper

## Global Constraints

- 不改动现有 standard/detailed 模式的任何逻辑
- 不改动链接处理流程（搜索、下载、转录）
- 不改动现有 CSS 变量和全局样式
- 不新增 Python 依赖
- UI 复用现有暖色极简配色体系（--bg, --surface, --border, --text, --heading, --accent）
- 文本模式下不提供音频/转录/合并/完整包下载

---

### Task 1: Backend — `_generate_scholar()` function

**Files:**
- Modify: `app.py` — insert after `_generate_detailed()` (after line 467), before `_basic_notes()`

**Interfaces:**
- Consumes: `_call_llm(prompt, max_tokens)` (existing), `_basic_notes(meta, transcript)` (existing)
- Produces: `_generate_scholar(task_id, transcript, meta)` → returns str (markdown notes)
- Produces helper: `_scholar_prompt(transcript, title, creator, platform, likes)` → returns str (prompt)

- [ ] **Step 1: Add `_scholar_prompt()` helper and `_generate_scholar()` function**

Insert the following code at line 468 (after `_generate_detailed` ends, before `_basic_notes`):

```python
def _scholar_prompt(transcript, title, creator, platform, likes, is_chunk=False, idx=0, total=0):
    """Build the scholar-mode prompt. is_chunk=True for per-chunk processing."""
    if is_chunk:
        return f"""Part {idx+1}/{total} of a transcript. Generate detailed Chinese study notes for this section in narrative paragraph style — NOT bullet points. Cover every concept mentioned. Preserve the speaker's key phrases in > blockquotes. Explain each concept thoroughly. Use ### for section headings. Output ONLY markdown.

Section {idx+1}/{total}:
{transcript}"""

    return f"""You are a study note generator for a knowledge/theory course. Generate comprehensive narrative notes that allow someone to learn the material by reading alone — without watching the original video. The goal is completeness: no concept, example, or reasoning chain should be omitted.

Output format:

# {title} — 详解笔记

> 视频作者：{creator} | 平台：{platform} | ❤️ {likes}
> 转录：本地 Whisper

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
- Output ONLY the markdown, no extra text

Transcript:
{transcript}"""


def _generate_scholar(task_id, transcript, meta):
    """Option C: scholar mode — detailed narrative notes for reading-based learning.
    
    Short text (≤8000 chars): single LLM pass.
    Long text (>8000 chars): chunk → parallel process → summary pass.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    title = meta.get("title", "Untitled")
    creator = meta.get("creator", "Unknown")
    platform = meta.get("platform", "text")
    likes = meta.get("likes", "0")

    # ── Short text: single pass ──
    if len(transcript) <= 8000:
        tasks[task_id]["progress"] = {"step": "generate", "status": "running",
                                       "message": "Generating scholar notes..."}
        prompt = _scholar_prompt(transcript, title, creator, platform, likes)
        notes = _call_llm(prompt, max_tokens=32000)
        if not notes:
            notes = _basic_notes(meta, transcript)
        tasks[task_id]["notes"] = notes
        tasks[task_id]["progress"] = {"step": "generate", "status": "done",
                                       "message": "Scholar notes ready"}
        return notes

    # ── Long text: chunk + summarize ──
    chunk_size = 6000
    overlap = 300
    chunks = []
    start = 0
    while start < len(transcript):
        end = min(start + chunk_size, len(transcript))
        chunks.append(transcript[start:end])
        start = end - overlap if end < len(transcript) else end

    total = len(chunks)
    tasks[task_id]["progress"] = {"step": "generate", "status": "running",
                                   "message": f"Scholar: processing {total} sections..."}

    def process_chunk(idx_chunk):
        idx, chunk = idx_chunk
        prompt = _scholar_prompt(chunk, title, creator, platform, likes,
                                 is_chunk=True, idx=idx, total=total)
        return idx, _call_llm(prompt, max_tokens=8000)

    chunk_notes = [""] * total
    with ThreadPoolExecutor(max_workers=min(total, 3)) as pool:
        futures = {pool.submit(process_chunk, (i, c)): i for i, c in enumerate(chunks)}
        for fut in as_completed(futures):
            idx, notes = fut.result()
            if notes:
                chunk_notes[idx] = notes
            done = sum(1 for n in chunk_notes if n)
            tasks[task_id]["progress"] = {"step": "generate", "status": "running",
                                           "message": f"Scholar: section {done}/{total} done"}

    chunk_notes = [n for n in chunk_notes if n]
    if not chunk_notes:
        notes = _basic_notes(meta, transcript)
        tasks[task_id]["notes"] = notes
        return notes

    body = "\n\n".join(chunk_notes)

    # Summary pass
    tasks[task_id]["progress"] = {"step": "generate", "status": "running",
                                   "message": "Scholar: generating overview..."}
    summary_prompt = f"""Based on these detailed notes from a transcript, generate a header section:

1. Line: "# {title} — 详解笔记"
2. Line: "> 视频作者：{creator} | 平台：{platform} | ❤️ {likes}"
3. "## 本节概览" — 2-3 Chinese sentences summarizing ALL the content
4. "## 关键术语表" — markdown table: 术语 | 解释 | 关键表述
5. "## 一句话总结" — one sentence takeaway in Chinese

Output this header. Then output the exact marker "<!--BODY-->" on its own line.

Detailed notes:
{body}"""

    header = _call_llm(summary_prompt, max_tokens=4000)

    if header and "<!--BODY-->" in header:
        header_part = header.split("<!--BODY-->")[0].strip()
        final = f"{header_part}\n\n---\n\n## 逐节详解\n\n{body}"
    else:
        final = f"""# {title} — 详解笔记

> 视频作者：{creator} | 平台：{platform} | ❤️ {likes}
> 转录：本地 Whisper（详解模式 · {total} 段并行处理）

---

## 逐节详解

{body}"""

    tasks[task_id]["notes"] = final
    tasks[task_id]["progress"] = {"step": "generate", "status": "done",
                                   "message": f"Scholar notes ready ({total} sections)"}
    return final
```

- [ ] **Step 2: Add `scholar` branch to `step_generate()`**

In `step_generate()` (line 295), change:

```python
def step_generate(task_id, transcript, meta, mode="standard"):
    """Generate structured markdown notes from transcript.

    mode: "standard" = optimized prompt, single pass (fast, good for <15min)
          "detailed"  = chunked processing + merge (slower, good for >20min)
    """
    tasks[task_id]["progress"] = {"step": "generate", "status": "running",
                                   "message": "Structuring notes..."}

    if mode == "detailed" and len(transcript) > 4000:
        return _generate_detailed(task_id, transcript, meta)
    else:
        return _generate_standard(task_id, transcript, meta)
```

To:

```python
def step_generate(task_id, transcript, meta, mode="standard"):
    """Generate structured markdown notes from transcript.

    mode: "standard" = optimized prompt, single pass (fast, good for <15min)
          "detailed"  = chunked processing + merge (slower, good for >20min)
          "scholar"   = detailed narrative for reading-based learning
    """
    tasks[task_id]["progress"] = {"step": "generate", "status": "running",
                                   "message": "Structuring notes..."}

    if mode == "scholar":
        return _generate_scholar(task_id, transcript, meta)
    elif mode == "detailed" and len(transcript) > 4000:
        return _generate_detailed(task_id, transcript, meta)
    else:
        return _generate_standard(task_id, transcript, meta)
```

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add scholar mode with adaptive chunking for reading-based notes"
```

---

### Task 2: Backend — Text input support in `/api/process`

**Files:**
- Modify: `app.py` — `/api/process` endpoint (lines 514-578)

**Interfaces:**
- Consumes: `step_generate()` (existing, now with scholar branch)
- Produces: SSE stream with `skipped` progress events for text mode

- [ ] **Step 1: Rewrite `/api/process` to support text input**

Replace the `/api/process` function (lines 514-578) with:

```python
@app.post("/api/process")
async def process(request: Request):
    """Process a video URL or direct text: download → transcribe → notes. SSE for progress."""
    body = await request.json()
    url = body.get("url", "").strip()
    platform = body.get("platform", "xhs")
    mode = body.get("mode", "standard")
    text = body.get("text", "").strip()
    override_title = body.get("title", "")
    override_xsec = body.get("xsec", "")

    if not url and not text:
        return JSONResponse({"error": "empty url or text"}, status_code=400)

    task_id = str(uuid.uuid4())[:8]
    tempdir = tempfile.mkdtemp(prefix="vtn-")
    tasks[task_id] = {"progress": {}, "tempdir": tempdir, "url": url or "(text input)"}

    def event_stream():
        try:
            if text:
                # ── Text mode: skip download/transcribe ──
                meta = {"title": override_title or "Untitled", "creator": "",
                        "platform": "text", "likes": "0"}
                tasks[task_id]["meta"] = meta
                tasks[task_id]["transcript"] = text

                for step_name in ["resolve", "download", "transcribe"]:
                    tasks[task_id]["progress"] = {"step": step_name, "status": "done",
                                                   "message": "skipped"}
                    yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"

                notes = step_generate(task_id, text, meta, mode=mode)
                yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"

                tasks[task_id]["done"] = True
                yield f"data: {json.dumps({'event': 'complete', 'data': {'task_id': task_id, 'notes': notes, 'transcript': text, 'meta': {'title': meta.get('title',''), 'creator': '', 'platform': 'text', 'likes': '0'}}})}\n\n"
                return

            # ── Link mode: existing flow, UNCHANGED ──
            meta = step_resolve(task_id, url, platform, xsec=override_xsec)
            if override_title:
                meta["title"] = override_title
            yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"
            if tasks[task_id].get("error"):
                yield f"data: {json.dumps({'event': 'error', 'data': tasks[task_id]['error']})}\n\n"
                return

            audio = step_download(task_id, meta)
            yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"
            if not audio:
                yield f"data: {json.dumps({'event': 'error', 'data': 'Download failed'})}\n\n"
                return

            transcript = step_transcribe(task_id, audio)
            yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"
            if not transcript:
                yield f"data: {json.dumps({'event': 'error', 'data': 'Transcription failed'})}\n\n"
                return

            notes = step_generate(task_id, transcript, meta, mode=mode)
            yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"

            tasks[task_id]["done"] = True
            yield f"data: {json.dumps({'event': 'complete', 'data': {'task_id': task_id, 'notes': notes, 'transcript': transcript, 'meta': {'title': meta.get('title',''), 'creator': meta.get('creator',''), 'platform': platform, 'likes': meta.get('likes','0')}}})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"
        finally:
            ap = tasks[task_id].get("audio_path", "")
            if ap and os.path.exists(ap):
                persistent = f"/tmp/vtn-audio-{task_id}.mp3"
                shutil.copy(ap, persistent)
                tasks[task_id]["audio_download"] = persistent
            if os.path.exists(tempdir):
                shutil.rmtree(tempdir, ignore_errors=True)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 2: Commit**

```bash
git add app.py
git commit -m "feat: add text input mode to /api/process endpoint"
```

---

### Task 3: Frontend — CSS additions

**Files:**
- Modify: `static/index.html` — inside existing `<style>` block

**Interfaces:**
- Produces: `.input-tabs`, `.input-tab`, `.input-tab.active`, `.text-input-area`, `.text-title-input` CSS classes

- [ ] **Step 1: Add CSS for input tabs, textarea, and title input**

Insert after line 110 (after `select:focus` rule), before `/* Buttons */` comment:

```css
  /* Input tabs — — — — — — — — — — — — — — — — — — — — — — */
  .input-tabs {
    display: flex;
    gap: 0;
    margin-bottom: 16px;
  }
  .input-tab {
    padding: 8px 20px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-dim);
    font-size: 0.88rem;
    font-family: var(--font);
    cursor: pointer;
    transition: all 0.15s;
    letter-spacing: -0.01em;
  }
  .input-tab:first-child { border-radius: var(--radius) 0 0 var(--radius); }
  .input-tab:last-child { border-radius: 0 var(--radius) var(--radius) 0; }
  .input-tab.active {
    background: var(--heading);
    color: #fff;
    border-color: var(--heading);
  }
  .input-tab:not(.active):hover { color: var(--heading); background: #faf8f5; }

  /* Text input — — — — — — — — — — — — — — — — — — — — — — */
  .text-input-area {
    width: 100%;
    min-height: 280px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 16px;
    color: var(--heading);
    font-size: 0.9rem;
    font-family: var(--font);
    line-height: 1.7;
    outline: none;
    resize: vertical;
    transition: border-color 0.2s, box-shadow 0.2s;
    letter-spacing: -0.01em;
  }
  .text-input-area:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(139,115,85,0.08);
  }
  .text-input-area::placeholder { color: var(--text-dim); }

  .text-title-input {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 16px;
    color: var(--heading);
    font-size: 0.9rem;
    font-family: var(--font);
    outline: none;
    margin-bottom: 10px;
    transition: border-color 0.2s, box-shadow 0.2s;
    letter-spacing: -0.01em;
  }
  .text-title-input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(139,115,85,0.08);
  }
  .text-title-input::placeholder { color: var(--text-dim); }
```

- [ ] **Step 2: Add third mode radio button style adjustment**

The existing `.mode-select` and radio button CSS (lines 143-162) already handles 2 or 3 buttons generically via flexbox — no changes needed. Verify the three radio buttons render with equal spacing.

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "style: add CSS for input tabs, textarea, and title input"
```

---

### Task 4: Frontend — HTML additions

**Files:**
- Modify: `static/index.html` — inside `.input-card` div, and inside download button area

**Interfaces:**
- Produces: tab buttons, textarea#textInput, input#titleInput, URL input group wrapper

- [ ] **Step 1: Add tab buttons and text-mode inputs**

Replace the `.input-card` div (lines 389-406) with:

```html
  <!-- Input -->
  <div class="input-card" id="inputCard">
    <div class="input-tabs">
      <button class="input-tab active" onclick="switchMode('url')" id="tabUrl">链接</button>
      <button class="input-tab" onclick="switchMode('text')" id="tabText">文本</button>
    </div>

    <!-- URL input group -->
    <div id="urlInputGroup">
      <div class="input-row">
        <input type="text" id="urlInput" placeholder="粘贴视频链接，或输入搜索关键词…">
        <select id="platformSelect">
          <option value="xhs">小红书</option>
          <option value="bilibili">Bilibili</option>
          <option value="youtube">YouTube</option>
        </select>
      </div>
    </div>

    <!-- Text input group (hidden by default) -->
    <div id="textInputGroup" style="display:none">
      <input type="text" id="titleInput" class="text-title-input" placeholder="输入标题（必填）…">
      <textarea id="textInput" class="text-input-area" placeholder="粘贴转录文本内容…"></textarea>
    </div>

    <div class="mode-select">
      <label><input type="radio" name="mode" value="standard" checked onchange="updateModeHint()"><span>标准笔记</span></label>
      <label><input type="radio" name="mode" value="detailed" onchange="updateModeHint()"><span>详细笔记</span></label>
      <label><input type="radio" name="mode" value="scholar" onchange="updateModeHint()"><span>详解笔记</span></label>
      <span id="modeHint">快，适合短视频</span>
    </div>
    <button class="btn btn-primary btn-full" id="submitBtn" onclick="handleSubmit()">
      开始处理
    </button>
  </div>
```

- [ ] **Step 2: Update download buttons to support conditional rendering**

Add `class="dl-audio dl-transcript dl-merged dl-full"` to the audio/transcript/merged/full download buttons (lines 447-450) so they can be hidden in text mode:

```html
    <div class="btn-row">
      <button class="btn btn-primary btn-sm" onclick="downloadNotes()">下载 Markdown</button>
      <button class="btn btn-sm" onclick="downloadPDF()">下载 PDF</button>
      <button class="btn btn-sm dl-audio" onclick="downloadAudio()">🎵 下载音频</button>
      <button class="btn btn-sm dl-transcript" onclick="downloadTranscript()">📝 下载转录文本</button>
      <button class="btn btn-sm dl-merged" onclick="downloadMerged()">📋 笔记+转录</button>
      <button class="btn btn-sm dl-full" onclick="downloadFull()">📦 下载完整包</button>
      <button class="btn btn-sm" onclick="copyNotes()">复制全文</button>
      <button class="btn btn-sm" id="backToSearchBtn" onclick="backToSearch()" style="display:none">← 返回搜索结果</button>
      <button class="btn btn-sm" onclick="resetAll()">重新开始</button>
    </div>
```

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: add input tabs, text mode fields, scholar radio button"
```

---

### Task 5: Frontend — JavaScript logic

**Files:**
- Modify: `static/index.html` — inside `<script>` block

**Interfaces:**
- Consumes: `handleSSEEvent()`, `showPreview()`, `markStep()`, `$submit`, `steps[]` (existing)
- Produces: `switchMode()`, `processText()`, `currentInputMode`, updated `handleSubmit()`, updated `updateModeHint()`, updated `showPreview()`, updated `resetAll()`

- [ ] **Step 1: Add state and mode-switching**

After line 473 (after `let _lastSearchResults = null;`), add:

```javascript
let currentInputMode = 'url';

function switchMode(mode) {
  currentInputMode = mode;
  document.getElementById('tabUrl').classList.toggle('active', mode === 'url');
  document.getElementById('tabText').classList.toggle('active', mode === 'text');
  document.getElementById('urlInputGroup').style.display = mode === 'url' ? '' : 'none';
  document.getElementById('textInputGroup').style.display = mode === 'text' ? '' : 'none';
  if (mode === 'text') {
    $submit.textContent = '生成笔记';
  } else {
    $submit.textContent = '开始处理';
  }
}
```

- [ ] **Step 2: Update `handleSubmit()` to route text mode**

Replace the `handleSubmit()` function (lines 563-577) with:

```javascript
async function handleSubmit() {
  if (currentInputMode === 'text') {
    await processText();
    return;
  }

  const input = $url.value.trim();
  const platform = $platform.value;
  if (!input) return;

  const extractedURL = extractURL(input);

  if (extractedURL) {
    await processURL(extractedURL, platform);
  } else if (/xhslink/.test(input)) {
    await processURL(input, platform);
  } else {
    await searchVideos(input, platform);
  }
}
```

- [ ] **Step 3: Add `processText()` function**

Insert after `handleSubmit()` (before `updateModeHint`):

```javascript
async function processText() {
  const text = document.getElementById('textInput').value.trim();
  const title = document.getElementById('titleInput').value.trim();

  if (!text) { showToast('请粘贴文本内容'); return; }
  if (!title) { showToast('请输入标题'); return; }

  $submit.disabled = true;
  $submit.textContent = '处理中…';
  $searchResults.style.display = 'none';
  $preview.style.display = 'none';
  currentInputUrl = '';

  // Set steps to pending
  steps.forEach(s => {
    document.getElementById(s).className = 'step pending';
    document.getElementById(s).querySelector('.detail').textContent = '';
  });
  $progress.style.display = 'block';

  const mode = document.querySelector('input[name="mode"]:checked').value;
  try {
    const resp = await fetch('/api/process', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, title, mode})
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try { handleSSEEvent(JSON.parse(line.slice(6))); } catch(e) {}
        }
      }
    }
  } catch (e) {
    markStep('stepResolve', 'error', e.message);
  }

  $submit.disabled = false;
  $submit.textContent = '生成笔记';
}
```

- [ ] **Step 4: Update `updateModeHint()` for 3 modes**

Replace the `updateModeHint()` function (lines 579-583) with:

```javascript
function updateModeHint() {
  const mode = document.querySelector('input[name="mode"]:checked').value;
  const hints = {
    standard: '快，适合短视频',
    detailed: '慢但完整，适合长视频',
    scholar: '逐段详解，替代看视频学习'
  };
  document.getElementById('modeHint').textContent = hints[mode] || '';
}
```

- [ ] **Step 5: Update `showPreview()` to hide audio/transcript downloads in text mode**

Add after line 744 (`$preview.scrollIntoView(...)` in `showPreview`), before the closing `}`:

```javascript
  // Hide audio/transcript/merged/full downloads in text mode
  const isTextMode = currentInputMode === 'text';
  document.querySelectorAll('.dl-audio, .dl-transcript, .dl-merged, .dl-full').forEach(el => {
    el.style.display = isTextMode ? 'none' : '';
  });
  // Also hide transcript preview in text mode
  if (isTextMode) {
    document.getElementById('transcriptPreview').style.display = 'none';
  }
```

Full updated `showPreview()`:

```javascript
function showPreview(md) {
  $preview.style.display = 'block';
  $progress.style.display = 'none';
  $previewContent.innerHTML = marked.parse(md);
  document.getElementById('backToSearchBtn').style.display = _lastSearchResults ? '' : 'none';
  if (currentTranscript) {
    document.getElementById('transcriptPreview').style.display = 'block';
    document.getElementById('transcriptContent').textContent = currentTranscript;
    document.getElementById('transcriptLen').textContent = `(${currentTranscript.length} 字)`;
  }
  // Hide audio/transcript/merged/full downloads in text mode
  const isTextMode = currentInputMode === 'text';
  document.querySelectorAll('.dl-audio, .dl-transcript, .dl-merged, .dl-full').forEach(el => {
    el.style.display = isTextMode ? 'none' : '';
  });
  if (isTextMode) {
    document.getElementById('transcriptPreview').style.display = 'none';
  }
  $preview.scrollIntoView({behavior: 'smooth'});
}
```

- [ ] **Step 6: Update `resetAll()` to clear text mode fields**

Replace the `resetAll()` function (lines 807-814) with:

```javascript
function resetAll() {
  $url.value = '';
  document.getElementById('titleInput').value = '';
  document.getElementById('textInput').value = '';
  currentTaskId = null; currentNotes = ''; currentTranscript = ''; currentMeta = {}; currentInputUrl = '';
  $preview.style.display = 'none'; $progress.style.display = 'none';
  $searchResults.style.display = 'none';
  $previewContent.innerHTML = '';
  document.getElementById('transcriptContent').textContent = '';
  document.getElementById('transcriptPreview').style.display = 'none';
  steps.forEach(s => document.getElementById(s).className = 'step pending');
  // Show all download buttons again
  document.querySelectorAll('.dl-audio, .dl-transcript, .dl-merged, .dl-full').forEach(el => {
    el.style.display = '';
  });
}
```

- [ ] **Step 7: Commit**

```bash
git add static/index.html
git commit -m "feat: add text mode and scholar mode JS logic"
```

---

### Task 6: Manual verification

- [ ] **Step 1: Start the server and verify existing functionality**

```bash
./start.sh
```

- Open http://localhost:3000
- Verify the 链接 tab is active by default, URL input and platform select visible
- Verify 3 mode radio buttons (标准/详细/详解) display with hints
- Test existing link flow: paste a B站 or YouTube link, choose standard mode, verify it still works end-to-end
- Test detailed mode with a link
- Verify all 6 download buttons appear and work for link mode

- [ ] **Step 2: Test text input mode**

- Click 文本 tab — verify URL input/平台 select hide, textarea and title input show
- Verify button text changes to "生成笔记"
- Leave fields empty, click button — verify toast "请粘贴文本内容"
- Fill title, leave text empty — verify toast
- Fill both, select 详解 mode, click button — verify progress steps show and notes generate
- Verify only Markdown download and PDF export buttons are visible (no audio/transcript/merged/full)
- Verify no transcript preview section appears

- [ ] **Step 3: Test scholar mode with short text**

- Paste text < 8000 chars in text mode, select 详解, generate
- Verify single pass (progress shows "Generating scholar notes...")
- Verify output has all sections: 本节概览, 逐节详解, 关键术语表, 一句话总结

- [ ] **Step 4: Test scholar mode with long text**

- Paste text > 8000 chars, select 详解, generate
- Verify chunked processing (progress shows "Scholar: section X/N done")
- Verify summary pass runs ("Scholar: generating overview...")
- Verify output has 逐节详解 with all sections, plus 概览/术语表/总结 at top

- [ ] **Step 5: Test link mode with scholar**

- Paste a video link, select 详解 mode
- Verify full pipeline: resolve → download → transcribe → scholar generate
- Verify all 6 download buttons appear

- [ ] **Step 6: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address issues found during manual verification"
```
