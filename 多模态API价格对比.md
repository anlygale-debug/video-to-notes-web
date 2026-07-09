# 多模态 API 性价比对比（2026年7月）

> 搜罗国内外 20+ 多模态（视觉）模型 API，按价格从低到高排列。美元兑人民币按 1:7.3 估算。

---

## 一图总结：性价比推荐

| 场景                           | 首选                        | 备选                      |
| ------------------------------ | --------------------------- | ------------------------- |
| 最低成本（简单 OCR/分类/打标） | Pixtral 12B / Reka Edge     | GLM-4.6V-Flash（免费）    |
| 日常图片理解（性价比甜点）     | **DeepSeek V4 Flash** | Qwen-VL-Plus              |
| 复杂视觉推理（便宜又好用）     | **GLM-5V-Turbo**      | Step-3.7-Flash / Grok 4.3 |
| 视频理解                       | MiniMax M3 / GLM-5V-Turbo   | Qwen3-Omni-30B            |
| 设计稿转代码                   | **GLM-5V-Turbo**      | Claude Sonnet 4.6         |
| 高精度、不差钱                 | Claude Sonnet 4.6           | Gemini 3.1 Pro            |

---

## 详细价格对比

> 价格单位：人民币 ¥/百万 tokens（美元标注 $）。DeepSeek V4 峰谷定价：谷段=工作日9-12点、14-18点之外的时段+周末全天，峰段价格=谷段×2。

### 一、极致低价（输入 ≤ ¥2/1M）

| 模型                                                                                                                                                                                  | 厂商      | 输入                                                   | 输出                | 缓存输入        | 上下文                      | 特点                     |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------ | ------------------- | --------------- | --------------------------- | ------------------------ |
| **GLM-4.6V-Flash** (9B)                                                                                                                                                         | 智谱      | **免费**                                         | **免费**      | —              | 128K                        | 开源可商用，9B 轻量      |
| **Reka Edge** (7B)                                                                                                                                                              | Reka AI   | **$0.10** (~¥0.73) | **$0.10** (~¥0.73) | $0.085              | 16K             | 图片+视频，极轻量           |                          |
| **Pixtral 12B**                                                                                                                                                                 | Mistral   | **$0.15** (~¥1.1) | **$0.15** (~¥1.1)   | —                  | 128K            | 开源 Apache，最便宜有性能的 |                          |
| **GPT-5 Nano**                                                                                                                                                                  | OpenAI    | **$0.05** (~¥0.36) | **$0.40** (~¥2.9)  | $0.02               | 400K            | 超便宜但能力有限            |                          |
| **Qwen-VL-Plus**                                                                                                                                                                | 阿里      | **¥0.75**                                       | **¥2.25**    | —              | 131K                        | 国内性价比王，OCR 好     |
| **GLM-4.6V** (106B)                                                                                                                                                             | 智谱      | **¥1**                                          | **¥3**       | ¥0.2           | 128K                        | 开源，原生 Function Call |
| **主要是用的agent是claudecode 接入的是deepseek的api 不是多模态 但是文本能力超强 我可以用网页版的gmini作为我的多模态 这也是我需要agent互通协议的原因 你能明白吗DeepSeek V4 Fla** | DeepSeek  | **¥1 / ¥2**                                    | **¥2 / ¥4** | ¥0.02 / ¥0.04 | 1M                          | 识图强，视觉压缩 7056 倍 |
| **InternVL3 8B**                                                                                                                                                                | OpenGVLab | **$0.20** (~¥1.5) | **$0.20** (~¥1.5)   | —                  | 16K             | 开源可自部署                |                          |

### 二、性价比甜点（输入 ¥1-5/1M）

| 模型                            | 厂商     | 输入                                                  | 输出                 | 缓存输入         | 上下文                  | 特点                |
| ------------------------------- | -------- | ----------------------------------------------------- | -------------------- | ---------------- | ----------------------- | ------------------- |
| **Qwen-VL-Max**           | 阿里     | **¥1.5**                                       | **¥4.5**      | —               | 131K                    | 复杂视觉理解强      |
| **Qwen3-VL-32B**          | 阿里     | **$0.52** (~¥3.8) | **$0.52** (~¥3.8)  | —                   | 32K              | MoE 高效架构            |                     |
| **Qwen3-Omni-30B**        | 阿里     | **$0.52** (~¥3.8) | **$0.52** (~¥3.8)  | —                   | 32K              | 图片+音频+视频+文本     |                     |
| **DeepSeek V4 Pro**       | DeepSeek | **¥3 / ¥6**                                   | **¥6 / ¥12** | ¥0.025 / ¥0.05 | 1M                      | 谷段便宜，1.6T 参数 |
| **Step-3.7-Flash**        | 阶跃星辰 | **¥1.35**                                      | **¥8.1**      | ¥0.27           | 256K                    | 198B MoE，推理强    |
| **MiniMax M3** (第三方)   | MiniMax  | **$0.30** (~¥2.2) | **$1.20** (~¥8.7)  | $0.06                | ≤512K           | Fireworks/OpenRouter 价 |                     |
| **Gemini 2.5 Flash**      | Google   | **$0.30** (~¥2.2) | **$2.50** (~¥18.2) | —                   | 1M               | 原生多模态，生态好      |                     |
| **Grok 4.1 Fast**         | xAI      | **$0.20** (~¥1.5) | **$0.50** (~¥3.6)  | $0.05                | 2M               | 极便宜，视觉+音频       |                     |
| **GPT-5 Mini**            | OpenAI   | **$0.25** (~¥1.8) | **$2.00** (~¥14.5) | —                   | 400K             | 品牌可靠，生态完善      |                     |
| **Doubao-Seed-2.1 Turbo** | 字节     | **¥3**                                         | **¥15**       | —               | —                      | 高频调用场景        |

### 三、中档（输入 ¥5-15/1M）

| 模型                          | 厂商      | 输入                                                  | 输出           | 缓存输入 | 上下文              | 特点                                  |
| ----------------------------- | --------- | ----------------------------------------------------- | -------------- | -------- | ------------------- | ------------------------------------- |
| **GLM-5V-Turbo**        | 智谱      | **¥5**                                         | **¥22** | —       | 200K                | 原生多模态 Agent，Design2Code 94.8 分 |
| **Hunyuan-Vision**      | 腾讯      | **¥3**                                         | **¥9**  | —       | 32K                 | 国内渠道方便                          |
| **InternVL3 38B/78B**   | OpenGVLab | **$0.90** (~¥6.6) | **$0.90** (~¥6.6)  | $0.45          | 16K      | 开源可自部署        |                                       |
| **Grok 4.3**            | xAI       | **$1.25** (~¥9.1) | **$2.50** (~¥18.2) | $0.20          | 1M       | 输出便宜，1M 上下文 |                                       |
| **GPT-5**               | OpenAI    | **$1.25** (~¥9.1) | **$10** (~¥73)     | —             | 272K     | 综合能力强          |                                       |
| **Gemini 3 Flash**      | Google    | **$0.50** (~¥3.6) | **$3.00** (~¥21.8) | —             | 1M       | 原生多模态          |                                       |
| **Claude Haiku 4.5**    | Anthropic | **$1** (~¥7.3) | **$5** (~¥36.4)       | $0.10          | 1M       | 品质可靠，速度快    |                                       |
| **Kimi K2.6**           | 月之暗面  | **¥6.5**                                       | **¥27** | —       | 256K                | 图文视频全支持                        |
| **Doubao-Seed-2.1 Pro** | 字节      | **¥6**                                         | **¥30** | ¥1.2    | —                  | 综合 Coding+Agent+VLM                 |

### 四、高端旗舰（输入 > ¥15/1M）

| 模型                           | 厂商      | 输入                                                  | 输出  | 缓存输入 | 上下文            | 特点 |
| ------------------------------ | --------- | ----------------------------------------------------- | ----- | -------- | ----------------- | ---- |
| **Gemini 3.1 Pro**       | Google    | **$2** (~¥14.6) | **$12** (~¥87.6)     | —    | 1M       | 原生多模态旗舰    |      |
| **GPT-5.4**              | OpenAI    | **$2.50** (~¥18.2) | **$15** (~¥109)   | $1.25 | 1M+      | 最新旗舰          |      |
| **Pixtral Large** (124B) | Mistral   | **$2** (~¥14.6) | **$6** (~¥43.8)      | —    | 131K     | 开源 124B         |      |
| **Claude Sonnet 4.6**    | Anthropic | **$3** (~¥21.9) | **$15** (~¥109)      | $0.30 | 1M       | 编程+视觉综合最强 |      |
| **Claude Opus 4.8**      | Anthropic | **$5** (~¥36.5) | **$25** (~¥182)      | $0.50 | 1M       | 最强但最贵        |      |
| **MiniMax M3** (官方)    | MiniMax   | **$0.60** (~¥4.4) | **$2.40** (~¥17.5) | $0.12 | 1M       | 428B MoE，官方价  |      |

---

## 关键洞察

### 1. DeepSeek V4 是当前性价比之王

DeepSeek V4 Flash **谷段 ¥1/¥2** 的输入/输出价格几乎是最低档，但性能是 284B 参数级别，空间推理和计数能力甚至超过 GPT-5.4。需要注意峰段（工作日白天）价格翻倍，但周末全天谷段。

### 2. 开源模型的隐藏优势

Pixtral 12B、InternVL3、GLM-4.6V 都是开源模型。如果你的调用量大，**自部署可以完全省掉 API 费用**，只需要 GPU 成本。GLM-4.6V-Flash 甚至 API 就直接免费。

### 3. 第三方聚合平台更便宜

MiniMax M3 官方 $0.60/$2.40，但通过 Fireworks/OpenRouter 只要 **$0.30/$1.20**。很多模型都有这个规律，建议比价。

### 4. 缓存命中能省 80-90%

高频重复 prompt（如系统指令、多轮对话前缀）启用 Prompt Caching 后，DeepSeek V4 缓存输入仅 ¥0.025/1M，Claude 缓存输入 $0.30/1M，是原价的 1-10%。

### 5. 按场景选型技巧

- **批量图片打标/过滤** → Pixtral 12B 或 Reka Edge（$0.15 双向统一价）
- **中文 OCR/文档理解** → Qwen-VL-Plus（¥0.75/¥2.25，中文优化）
- **设计稿转代码** → GLM-5V-Turbo（Design2Code 94.8 分，比 Claude Opus 便宜 92%）
- **视频内容理解** → MiniMax M3 或 Qwen3-Omni
- **白天高频调用** → DeepSeek V4 Flash（但尽量错峰到晚上/周末）
- **复杂推理+视觉** → Claude Sonnet 4.6 或 Grok 4.3

---

## 数据来源与日期

所有价格信息采集于 **2026年7月1日**，来源包括各厂商官方文档、OpenRouter、Vercel AI Gateway、360 智脑等。大模型 API 价格变动频繁，实际使用前请以官方最新价格为准。

- [DeepSeek API Docs - Pricing](https://api-docs.deepseek.com/zh-cn/quick_start/pricing)
- [GLM-5V-Turbo on OpenRouter](https://openrouter.ai/z-ai/glm-5v-turbo)
- [Qwen Models &amp; Pricing - Alibaba Cloud](https://www.alibabacloud.com/help/en/model-studio/models-hk)
- [StepFun Platform - Pricing](https://platform.stepfun.com/docs/zh/guides/pricing/details)
- [MiniMax M3 - WaveSpeed](https://wavespeed.ai/blog/posts/minimax-m3-api/)
- [Anthropic API Pricing - Nops](https://www.nops.io/blog/anthropic-api-pricing/)
- [Gemini API Pricing - Morph](https://www.morphllm.com/gemini-api-pricing)
- [OpenAI Pricing - Curlscape](https://curlscape.com/blog/openai-api-pricing-guide-2026)
- [xAI Pricing](https://docs.x.ai/developers/pricing)
- [Pixtral 12B Pricing](https://aipricecompare.org/models/pixtral-12b.html)
- [InternVL3 38B Pricing](https://pricepertoken.com/pricing-page/model/opengvlab-internvl3-38b)
- [Reka Edge on OpenRouter](https://openrouter.ai/rekaai/reka-edge-2603)
