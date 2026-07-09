# 设置页重构 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 切换 API 格式到 OpenAI 兼容，设置页改为全页接管 + 分组布局 + tooltip + 保存自动验证。

**Architecture:** 后端 `_call_llm()` 和 `test_connection()` 从 Anthropic `/messages` + `x-api-key` 切到 OpenAI `/chat/completions` + `Authorization: Bearer`。前端设置页从侧边栏改为全屏 overlay，分组渲染字段，tooltip 问号图标，保存时自动测试连接。

**Tech Stack:** Python FastAPI, vanilla HTML/CSS/JS

## Global Constraints

- 不改变现有生成/下载/PDF 流程
- 不改变 `data/settings.json` 存储结构
- 未配置 API 时的错误保护保持
- Mermaid CDN + 渲染保持
- UI 风格保持现有暖色极简配色

---

### Task 1: Backend — `_call_llm()` 切换到 OpenAI 格式

**Files:**
- Modify: `app.py:354-378`

- [ ] **Step 1: 修改 `_call_llm()`**

Replace lines 354-378 with:

```python
def _call_llm(prompt, max_tokens=8000):
    """Single LLM call via OpenAI-compatible API. Returns text or None."""
    api_key, api_base, model = _read_api_config()
    if not api_key or not api_base:
        return None

    body = {"model": model, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    api_url = f"{api_base}/chat/completions"
    r = subprocess.run([
        "curl", "-s", "-X", "POST", api_url,
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "content-type: application/json",
        "-d", json.dumps(body)
    ], capture_output=True, text=True, timeout=180)

    try:
        resp = json.loads(r.stdout)
        return resp["choices"][0]["message"]["content"]
    except Exception:
        pass
    return None
```

- [ ] **Step 2: 更新默认 base URL**

In `_load_settings()` line 327, change:

```python
    defaults = {"api_base": "https://api.deepseek.com/v1", ...
```

(Already done as `v1` — verify.)

- [ ] **Step 3: 验证语法**

```bash
cd "/Users/yubo/Claude code test/video-to-notes-web" && python3 -c "from app import app; print('OK')"
```

Expected: OK

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: switch _call_llm to OpenAI-compatible API format"
```

---

### Task 2: Backend — `test_connection()` 同步切换

**Files:**
- Modify: `app.py:968-1000`

- [ ] **Step 1: 修改 `test_connection()`**

Find `@app.post("/api/test-connection")` and replace the curl call block (the subprocess.run call) with:

```python
    start = _time.time()
    try:
        r = subprocess.run([
            "curl", "-s", "-X", "POST", f"{api_base}/chat/completions",
            "-H", f"Authorization: Bearer {api_key}",
            "-H", "content-type: application/json",
            "-d", json.dumps({"model": model, "max_tokens": 10,
                              "messages": [{"role": "user", "content": "hi"}]})
        ], capture_output=True, text=True, timeout=30)
        elapsed = int((_time.time() - start) * 1000)
        resp = json.loads(r.stdout)
        if "choices" in resp:
            return JSONResponse({"ok": True, "latency_ms": elapsed, "model": model})
        err = resp.get("error", {}).get("message", r.stdout[:200])
        return JSONResponse({"ok": False, "error": err})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})
```

- [ ] **Step 2: 验证语法**

```bash
cd "/Users/yubo/Claude code test/video-to-notes-web" && python3 -c "from app import app; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: switch test_connection to OpenAI-compatible API format"
```

---

### Task 3: Frontend — 全页设置 + 分组 + tooltip + 保存验证

**Files:**
- Modify: `static/index.html`

**Important:** 这是最大改动块。需要：
1. 删除旧的侧边栏 HTML
2. 替换为全屏 overlay 设置页 HTML（分组 + tooltip）
3. 替换旧的侧边栏 CSS 为全页设置 CSS
4. 重写设置相关 JS（loadSettings/saveSettings/testConnection/openSettings/closeSettings）
5. 更新 `ensureApiConfig()` 和 `initDefaults()` 适配新的 DOM 结构

- [ ] **Step 1: 删除旧侧边栏 HTML**

找到 `<!-- Settings Overlay -->` 到 `</div>` (settings-sidebar 结束) 之间的 HTML，替换为：

```html
<!-- Settings Page -->
<div class="settings-page" id="settingsPage">
  <header class="settings-page-head">
    <button class="settings-back" onclick="closeSettings()" aria-label="返回">‹ 返回</button>
    <h1>设置</h1>
  </header>

  <div class="settings-body">
    <!-- Group: API 配置 -->
    <div class="settings-group">
      <h2 class="settings-group-title">API 配置（必填）</h2>
      <p class="settings-group-desc">支持 OpenAI 兼容协议的服务都能用。默认指向 DeepSeek，换服务改地址即可。</p>

      <div class="settings-field">
        <label>API Key <span class="help-icon" data-tip="服务商提供的 API Key，通常 sk- 开头。密钥仅存储在本地">?</span></label>
        <div class="input-with-eye">
          <input type="password" id="setApiKey" placeholder="sk-xxx">
          <button class="eye-btn" onclick="toggleKeyVisibility()">👁</button>
        </div>
      </div>

      <div class="settings-field">
        <label>Base URL <span class="help-icon" data-tip="OpenAI 兼容 API 入口。DeepSeek: https://api.deepseek.com/v1。Moonshot/OpenRouter/vLLM 等改这里">?</span></label>
        <input type="text" id="setApiBase" placeholder="https://api.deepseek.com/v1">
      </div>

      <div class="settings-field">
        <label>模型名称 <span class="help-icon" data-tip="模型标识符，如 deepseek-chat、gpt-4o。以服务商文档为准">?</span></label>
        <input type="text" id="setModel" placeholder="deepseek-chat">
      </div>
    </div>

    <!-- Group: 默认偏好 -->
    <div class="settings-group">
      <h2 class="settings-group-title">默认偏好</h2>

      <div class="settings-field">
        <label>笔记模式 <span class="help-icon" data-tip="新笔记的默认生成模式，可随时在主页切换">?</span></label>
        <div class="settings-radios">
          <label><input type="radio" name="setMode" value="standard"> 标准</label>
          <label><input type="radio" name="setMode" value="detailed"> 详细</label>
          <label><input type="radio" name="setMode" value="scholar"> 详解</label>
        </div>
      </div>

      <div class="settings-field">
        <div class="settings-toggle">
          <span>默认 Mermaid 图解 <span class="help-icon" data-tip="开启后笔记自动插入框架图和内容图解">?</span></span>
          <input type="checkbox" id="setMermaid">
        </div>
      </div>
    </div>

    <div class="settings-error" id="settingsError"></div>
    <div class="settings-success" id="settingsSuccess"></div>
  </div>

  <div class="settings-page-foot">
    <button class="btn btn-sm" onclick="testConnection()">测试连接</button>
    <button class="btn btn-primary btn-sm" id="settingsSaveBtn" onclick="saveSettings()">保存设置</button>
  </div>
</div>
```

- [ ] **Step 2: 替换 CSS**

删除旧的 `/* Settings sidebar */` 块中的所有 CSS，替换为：

```css
  /* Settings page — — — — — — — — — — — — — — — — — — — — */
  .settings-page {
    position: fixed; inset: 0; z-index: 300;
    background: var(--bg);
    display: flex; flex-direction: column;
    opacity: 0; pointer-events: none; transition: opacity 0.2s;
  }
  .settings-page.open { opacity: 1; pointer-events: auto; }
  .settings-page-head {
    display: flex; align-items: center; gap: 16px;
    padding: 20px 28px;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }
  .settings-page-head h1 {
    font-size: 1.1rem; font-weight: 600; color: var(--heading);
    letter-spacing: -0.02em; margin: 0;
  }
  .settings-back {
    background: none; border: none; font-size: 1.2rem; cursor: pointer;
    color: var(--text-dim); padding: 0; transition: color 0.15s;
  }
  .settings-back:hover { color: var(--heading); }
  .settings-body {
    flex: 1; overflow-y: auto; padding: 24px 28px;
  }
  .settings-group {
    margin-bottom: 28px;
  }
  .settings-group-title {
    font-size: 0.95rem; font-weight: 600; color: var(--heading);
    margin: 0 0 6px; letter-spacing: -0.02em;
  }
  .settings-group-desc {
    font-size: 0.82rem; color: var(--text-dim);
    margin: 0 0 18px; line-height: 1.5;
  }
  .settings-field { margin-bottom: 16px; }
  .settings-field label {
    display: flex; align-items: center; gap: 4px;
    font-size: 0.84rem; font-weight: 500; color: var(--text);
    margin-bottom: 4px;
  }
  .settings-field input[type="text"],
  .settings-field input[type="password"] {
    width: 100%;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 9px 12px;
    color: var(--heading); font-size: 0.88rem; font-family: var(--font);
    outline: none; transition: border-color 0.15s;
  }
  .settings-field input:focus { border-color: var(--accent); }
  .settings-field input::placeholder { color: var(--text-dim); }
  .settings-radios {
    display: flex; gap: 16px; font-size: 0.86rem;
  }
  .settings-radios label {
    cursor: pointer; color: var(--text-dim); transition: color 0.15s;
    display: flex; align-items: center; gap: 4px; font-weight: 400;
  }
  .settings-radios label:has(input:checked) { color: var(--heading); }
  .settings-radios input[type="radio"] { accent-color: var(--heading); }
  .settings-toggle {
    display: flex; align-items: center; justify-content: space-between;
    font-size: 0.84rem; color: var(--text);
  }
  .settings-toggle input[type="checkbox"] {
    accent-color: var(--accent); width: 16px; height: 16px;
  }
  .settings-page-foot {
    display: flex; gap: 8px; padding: 16px 28px;
    border-top: 1px solid var(--border);
    background: var(--surface);
    justify-content: flex-end;
  }
  .input-with-eye { position: relative; }
  .input-with-eye input { width: 100%; padding-right: 36px; }
  .input-with-eye .eye-btn {
    position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
    background: none; border: none; cursor: pointer; color: var(--text-dim);
    font-size: 0.9rem; padding: 2px 4px;
  }
  /* Help icon + tooltip — — — — — — — — — — — — — — — — */
  .help-icon {
    display: inline-flex; align-items: center; justify-content: center;
    width: 15px; height: 15px; border-radius: 50%;
    border: 1px solid var(--border);
    color: var(--text-dim); font-size: 0.65rem; font-weight: 500;
    cursor: help; transition: color 0.15s, border-color 0.15s;
    position: relative;
  }
  .help-icon:hover {
    color: var(--accent); border-color: var(--accent);
  }
  .help-icon::after {
    content: attr(data-tip);
    display: none;
    position: absolute; bottom: calc(100% + 8px); left: 50%;
    transform: translateX(-50%);
    background: var(--heading); color: #fff;
    font-size: 0.76rem; font-weight: 400; line-height: 1.5;
    padding: 6px 12px; border-radius: var(--radius-sm);
    max-width: 260px; white-space: normal;
    z-index: 10; pointer-events: none;
  }
  .help-icon:hover::after { display: block; }
  /* Error / Success — — — — — — — — — — — — — — — — — — */
  .settings-error {
    color: var(--red); font-size: 0.84rem; padding: 10px 14px;
    background: #fef2f2; border-radius: var(--radius-sm); display: none;
    margin-bottom: 16px;
  }
  .settings-success {
    color: var(--green); font-size: 0.84rem; padding: 10px 14px;
    background: #f0faf0; border-radius: var(--radius-sm); display: none;
    margin-bottom: 16px;
  }
  @media (max-width: 600px) {
    .settings-page-head { padding: 16px 18px; }
    .settings-body { padding: 18px; }
    .settings-page-foot { padding: 12px 18px; }
  }
```

- [ ] **Step 3: 重写设置 JS**

删除旧的 `// ── Settings ──` 段（从 `function openSettings()` 到 `initDefaults()` IIFE 结束），替换为：

```javascript
// ── Settings ─────────────────────────────────────────────────
function openSettings() {
  document.getElementById('settingsPage').classList.add('open');
  loadSettings();
}

function closeSettings() {
  document.getElementById('settingsPage').classList.remove('open');
  document.getElementById('settingsError').style.display = 'none';
  document.getElementById('settingsSuccess').style.display = 'none';
}

async function loadSettings() {
  try {
    const resp = await fetch('/api/settings');
    const s = await resp.json();
    document.getElementById('setApiBase').value = s.api_base || '';
    document.getElementById('setApiKey').value = s.api_key || '';
    document.getElementById('setModel').value = s.model || 'deepseek-chat';
    document.getElementById('setMermaid').checked = s.default_mermaid || false;
    const modeRadio = document.querySelector(`input[name="setMode"][value="${s.default_mode || 'standard'}"]`);
    if (modeRadio) modeRadio.checked = true;
  } catch (e) {}
}

async function saveSettings() {
  const apiKey = document.getElementById('setApiKey').value.trim();
  const apiBase = document.getElementById('setApiBase').value.trim();
  const model = document.getElementById('setModel').value.trim() || 'deepseek-chat';
  const body = {
    api_base: apiBase,
    api_key: apiKey,
    model: model,
    default_mode: document.querySelector('input[name="setMode"]:checked')?.value || 'standard',
    default_mermaid: document.getElementById('setMermaid').checked,
  };

  // Save first
  try {
    const resp = await fetch('/api/settings', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    if (!resp.ok) { showToast('保存失败'); return; }
  } catch (e) { showToast('保存失败'); return; }

  // Auto test connection
  const errEl = document.getElementById('settingsError');
  const okEl = document.getElementById('settingsSuccess');
  errEl.style.display = 'none';
  okEl.style.display = 'block';
  okEl.textContent = '验证中…';

  try {
    const r = await fetch('/api/test-connection', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({api_key: apiKey, api_base: apiBase, model}),
    });
    const data = await r.json();
    if (data.ok) {
      showToast('已保存');
      setTimeout(() => closeSettings(), 600);
    } else {
      errEl.style.display = 'block';
      errEl.textContent = '连接失败: ' + (data.error || '未知错误');
      okEl.style.display = 'none';
    }
  } catch (e) {
    errEl.style.display = 'block';
    errEl.textContent = '连接失败: ' + e.message;
    okEl.style.display = 'none';
  }
}

async function testConnection() {
  const apiKey = document.getElementById('setApiKey').value.trim();
  const apiBase = document.getElementById('setApiBase').value.trim();
  const model = document.getElementById('setModel').value.trim() || 'deepseek-chat';
  if (!apiKey || !apiBase) {
    document.getElementById('settingsError').style.display = 'block';
    document.getElementById('settingsError').textContent = '请填写 API Key 和 Base URL';
    document.getElementById('settingsSuccess').style.display = 'none';
    return;
  }
  const errEl = document.getElementById('settingsError');
  const okEl = document.getElementById('settingsSuccess');
  errEl.style.display = 'none';
  okEl.style.display = 'block';
  okEl.textContent = '测试中…';
  try {
    const resp = await fetch('/api/test-connection', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({api_key: apiKey, api_base: apiBase, model}),
    });
    const r = await resp.json();
    if (r.ok) {
      okEl.textContent = `连接成功 · ${r.latency_ms}ms · ${r.model}`;
    } else {
      errEl.style.display = 'block';
      errEl.textContent = '连接失败: ' + (r.error || '未知错误');
      okEl.style.display = 'none';
    }
  } catch (e) {
    errEl.style.display = 'block';
    errEl.textContent = '连接失败: ' + e.message;
    okEl.style.display = 'none';
  }
}

function toggleKeyVisibility() {
  const input = document.getElementById('setApiKey');
  input.type = input.type === 'password' ? 'text' : 'password';
}

async function ensureApiConfig() {
  try {
    const resp = await fetch('/api/settings');
    const s = await resp.json();
    if (!s.api_base || !s.api_key) {
      showToast('请先配置 API');
      openSettings();
      return false;
    }
    return true;
  } catch (e) { return true; }
}

(async function initDefaults() {
  try {
    const resp = await fetch('/api/settings');
    const s = await resp.json();
    if (s.default_mode) {
      const radio = document.querySelector(`input[name="mode"][value="${s.default_mode}"]`);
      if (radio) { radio.checked = true; updateModeHint(); }
    }
    if (s.default_mermaid) {
      document.getElementById('mermaidToggle').checked = true;
    }
  } catch (e) {}
})();
```

- [ ] **Step 4: 删除旧的 settings-overlay / settings-sidebar 相关 CSS 残留**

确认 `.gear-btn`、`.header-row` CSS 保留（齿轮图标在主页 header 仍需要）。
确认 `.settings-overlay`、`.settings-sidebar`、`.settings-close`、`.settings-sub`、`.settings-help`、`.settings-actions` CSS 已删除。

- [ ] **Step 5: Commit**

```bash
git add static/index.html
git commit -m "feat: redesign settings as full-page overlay with groups and tooltips"
```

---

### Task 4: Manual verification

- [ ] **Step 1: 打开主页面**

```bash
cd "/Users/yubo/Claude code test/video-to-notes-web" && source ~/.agent-reach-venv/bin/activate && uvicorn app:app --host 0.0.0.0 --port 3000 &
```
Open http://localhost:3000

- [ ] **Step 2: 验证设置页面**

- 点击齿轮 → 全屏设置页出现
- 返回按钮可见，点击 → 关闭设置
- 重新打开，hover `(?)` 图标 → 变色 + tooltip 弹出
- 填写 API 配置 → 点测试连接 → 成功/失败反馈
- 点保存 → 自动验证 → 通过后弹回主页

- [ ] **Step 3: 验证回归**

- 未配置 API 点生成 → toast + 自动打开设置
- 配置好 API 后生成笔记 → 正常生成
- PDF 导出 → 正常
- 默认模式/Mermaid 偏好 → 页面加载后生效
