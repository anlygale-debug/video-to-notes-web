# Mermaid 图表支持设计

## 目标

在生成的笔记中加入 Mermaid 图表，辅助理解。不改变原有内容结构，只在 prompt 中引导 LLM 插入 Mermaid 代码块，前端支持渲染。

两类图表：
- **内容框架图**（1 张，固定在笔记开头）：快速了解笔记内容脉络
- **内容详解图**（最多 2-3 张，散布文中）：辅助理解具体概念/流程/关系

## 功能规格

### 1. Prompt 改动（app.py）

所有模式的 prompt 模板统一追加 Mermaid 相关指引：

**输出格式中新增框架图占位**（在所有现有结构之前）：

```
## 内容框架图
用 Mermaid 图表展示本文的知识结构，放在笔记最前面。选择合适的图表类型（mindmap 或 graph TD），让读者一眼看清内容脉络和要点关系。
```

**新增加规则段落**：

```
Mermaid 图表使用规则：
- 内容框架图必须放在笔记开头（不占正文图表配额）
- 正文中可在合适位置插入图表辅助理解，最多 2-3 张
- 只在确实需要可视化时才用，不要为了画图而画图
- 选择最合适的图表类型：flowchart（流程）、quadrantChart（对比/四象限）、sequenceDiagram（交互/消息传递）、mindmap（层级关系）、ganttChart（时间线/阶段）
- Mermaid 代码块去掉外层 ```mermaid 标记中的空格，严格用 ```mermaid 格式
```

**需要改动的 prompt 位置**：

| 函数 | 模式 | 改动 |
|------|------|------|
| `_generate_standard()` (~L364) | standard 全文 | Output format 前插入框架图占位，Rules 后追加 Mermaid 规则 |
| `_generate_detailed()` 分块 (~L433) | detailed 分块 | 加简化 Mermaid 规则（不要求框架图） |
| `_scholar_prompt()` 全文 (~L481) | scholar 全文 | Output format 前插入框架图占位，Rules 后追加 Mermaid 规则 |
| `_scholar_prompt()` 分块 (~L476) | scholar 分块 | 加简化 Mermaid 规则（不要求框架图） |

**不动的**：
- `_generate_detailed()` 拼接逻辑 — 纯字符串拼接，不动
- `_generate_scholar()` summary pass — 框架图由分块内容自然包含，summary 不管
- `_basic_notes()` fallback — 不加，这是纯转录输出

### 2. 前端渲染（static/index.html）

**新增 CDN 脚本**，在 `<head>` 中 `marked` 之后：

```html
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
```

**初始化**，在 `<script>` 末尾：

```js
mermaid.initialize({ startOnLoad: false, theme: 'neutral' });
```

**showPreview() 改动**，在 `$previewContent.innerHTML = marked.parse(md)` 之后追加：

```js
await mermaid.run({ nodes: $previewContent.querySelectorAll('code.language-mermaid') });
```

marked.js 默认将 ` ```mermaid ` 渲染为 `<pre><code class="language-mermaid">`，mermaid.run() 自动找到并替换为 SVG。无需 marked 插件。

`showPreview()` 需要改为 `async`。

### 3. PDF 导出

本次不改 PDF 导出。Mermaid 是 JS 渲染，weasyprint 不执行 JS，PDF 中 Mermaid 代码块保持为纯文本代码块。用户主要使用场景（网页预览、Obsidian）均原生支持 Mermaid 渲染。

如后续需要 PDF 支持，需引入 puppeteer/playwright 或 mermaid-cli 进行服务端预渲染。

## 技术实现

### 不变项
- 不新增 Python 依赖
- 不改动 PDF 导出
- 不改动下载功能
- 不改动 `_basic_notes()` fallback
- 不改动 detailed/scholar 分块拼接逻辑
- 不改变现有笔记结构和内容约定

### 前端改动细节

`showPreview()` 改为 async：

```javascript
async function showPreview(md) {
  $preview.style.display = 'block';
  $progress.style.display = 'none';
  $previewContent.innerHTML = marked.parse(md);
  document.getElementById('backToSearchBtn').style.display = _lastSearchResults ? '' : 'none';

  // Render Mermaid diagrams
  try {
    await mermaid.run({
      nodes: $previewContent.querySelectorAll('code.language-mermaid'),
    });
  } catch (e) {
    // Mermaid rendering failure should not block note display
  }

  // ... rest of existing showPreview logic (download buttons, transcript preview)
}
```

### Mermaid 初始化

使用 `neutral` 主题匹配项目现有暖色系：

```js
mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  securityLevel: 'strict',
});
```

## 验证

1. 加载页面 → `mermaid` 全局对象存在（控制台输入 `typeof mermaid` 返回 `object`）
2. 生成一篇笔记（任意模式）→ 预览中 Mermaid 代码块被渲染为 SVG 图形
3. 多张图表页面 → 所有图表均正确渲染
4. 无 Mermaid 代码块的笔记 → showPreview 不报错
5. PDF 导出 → 不崩溃，Mermaid 代码块以纯文本显示
6. 深色背景图 → 图表颜色与页面风格协调（neutral 主题）
