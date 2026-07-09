# 设置页重构 — 设计文档

## 目标

参考 TJ-Sylva 项目，重构设置页：后端切到 OpenAI 兼容格式，前端改为全页接管 + 分组布局 + tooltip 帮助。

## 一、后端：Anthropic → OpenAI 兼容格式

### `_call_llm()` 改动

| | 现在（Anthropic） | 改为（OpenAI 兼容） |
|------|---|---|
| 端点 | `{base}/messages` | `{base}/chat/completions` |
| 认证头 | `x-api-key: {key}` | `Authorization: Bearer {key}` |
| 响应解析 | `content[].text` | `choices[0].message.content` |
| 默认地址 | `https://api.deepseek.com/anthropic` | `https://api.deepseek.com/v1` |
| 默认模型 | `deepseek-chat` | `deepseek-chat`（不变） |

请求体格式（同 OpenAI）：
```python
body = {
    "model": model,
    "max_tokens": max_tokens,
    "messages": [{"role": "user", "content": prompt}]
}
```
请求体结构不变，和 Anthropic 格式一致。

### `test_connection()` 同步切换

同 `_call_llm()`，请求格式和响应解析跟切换。

### 不变

- `subprocess` + `curl` 方式
- 超时、异常处理
- `_insert_mermaid()` 等调用方

## 二、前端：全页接管 + 分组布局

### 交互

- 齿轮图标 → 全屏 overlay 接管视口（不是侧边栏）
- 顶部"返回"按钮 + 标题"设置"
- 两组：**API 配置（必填）** + **默认偏好**
- 每个字段标签旁 `(?)` 图标，hover 时变色 + 展开 tooltip
- 底部：[测试连接] + [保存设置]
- 保存成功 → 自动返回主页

### 字段

**API 配置（必填）**，组说明：*"支持 OpenAI 兼容协议的服务都能用。默认指向 DeepSeek，换服务改地址即可。"*

| 字段 | 类型 | tooltip |
|------|------|---------|
| API Key | password + 眼睛 | 服务商提供的 API Key，通常 sk- 开头。密钥仅存储在本地 |
| Base URL | text | OpenAI 兼容 API 入口。DeepSeek: https://api.deepseek.com/v1。Moonshot/OpenRouter/vLLM 等改这里 |
| 模型名称 | text | 模型标识符，如 deepseek-chat、gpt-4o。以服务商文档为准 |

**默认偏好**，组说明：无

| 字段 | 类型 | tooltip |
|------|------|---------|
| 笔记模式 | radio × 3 | 新笔记的默认生成模式，可随时在主页切换 |
| 默认 Mermaid | toggle | 开启后笔记自动插入框架图和内容图解 |

### tooltip CSS

```css
.settings-tooltip {
  display: none;
  position: absolute;
  /* positioned relative to the (?) icon */
  background: var(--heading);
  color: #fff;
  font-size: 0.78rem;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  max-width: 260px;
  line-height: 1.5;
  z-index: 10;
  pointer-events: none;
  white-space: normal;
}
.help-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px; height: 16px;
  border-radius: 50%;
  border: 1px solid var(--border);
  color: var(--text-dim);
  font-size: 0.7rem;
  cursor: help;
  transition: color 0.15s, border-color 0.15s;
  margin-left: 6px;
  vertical-align: middle;
}
.help-icon:hover {
  color: var(--accent);
  border-color: var(--accent);
}
.help-icon:hover .settings-tooltip {
  display: block;
}
```

### 不变

- 现有生成/下载/PDF 流程
- `data/settings.json` 存储
- 未配置 API 时的错误保护
- Mermaid CDN + 渲染

## 三、存储

`data/settings.json` 结构保持不变，只改默认值：
```json
{
  "api_base": "https://api.deepseek.com/v1",
  "api_key": "",
  "model": "deepseek-chat",
  "default_mode": "standard",
  "default_mermaid": false
}
```

### 保存流程

```
点击保存 → [保存配置到 data/settings.json]
          → [自动测试连接]
          → 通过 ✓ → toast "已保存" → 自动返回主页
          → 失败 ✗ → 显示错误（连接失败: xxx）→ 留在设置页
```

用户不需要手动点"测试连接"——保存时自动验证。测试连接按钮保留，让用户在保存前可以单独测试。

## 验证

1. 打开设置 → 全屏 overlay 出现，分组标题 + 字段正确
2. hover `(?)` 图标 → 变色 + tooltip 弹出
3. 填写正确 API 配置 → 点保存 → 自动测试通过 → 弹回主页
4. 填写错误 API 配置 → 点保存 → 测试失败 → 留在设置页，显示错误信息
5. 未配置 API 时点生成 → toast + 自动打开设置页
6. 点击返回/遮罩 → 关闭设置，回到主页
