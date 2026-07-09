# 需求速览

- 输入：B站/YouTube 等平台的视频链接（如 `https://www.bilibili.com/video/BV1GJ411x7h7`）
- 输出：该视频各清晰度（1080P、720P、480P、音频、封面等）的**真实下载链接**
- 数据由 yt-dlp 的 `extract_info(url, download=False)` 提供，直接返回 `formats[].url`
- 前端只做透传展示，不做本地转码/合并，用户拿到链接后自行下载

---

# 一、kedou.life 逆向分析

## 1.1 技术栈识别

| 层  | 技术                                                 |
|-----|------------------------------------------------------|
| 前端 | Nuxt.js (Vue 3 SSR) + Element Plus + Pinia 状态管理   |
| 加密 | JSEncrypt (RSA-1024) + CryptoJS (AES-128-CBC)          |
| 请求 | Nuxt 内置 `$fetch`（`/api/` 前缀走内置代理，避免跨域）    |
| 后端 | 推测 Java/Spring Boot（基于统一响应结构 `{code, message, data}`） |
| 解析 | yt-dlp 命令行 + FFmpeg                                  |
| 前端入口 | [CNrQBoNa.js](https://www.kedou.life/_nuxt/CNrQBoNa.js)（~2.7MB） |
| 加密模块 | [BJCOAhp2.js](https://www.kedou.life/_nuxt/BJCOAhp2.js)（~184KB）   |

## 1.2 所有 API 接口

```
认证
  GET    /api/auth/keys              获取 RSA 公钥（k1/k2）
  POST   /api/auth/login             登录
  POST   /api/auth/register          注册
  POST   /api/auth/sendVerCode       发送验证码
  POST   /api/auth/findBackPassword  找回密码
  POST   /api/auth/updatePassword    修改密码
  GET    /api/auth/getUserInfo       用户信息（含剩余解析次数）
  GET    /api/auth/devices           设备管理
  POST   /api/auth/logout            登出

视频解析（请求体全部加密）
  POST   /api/video/extract/v2       核心：视频解析
  POST   /api/video/cnSimpleExtract  国内平台解析（B站/抖音等）
  POST   /api/video/subtitleExtract  字幕提取
  POST   /api/video/danmakuExtract   弹幕提取
  POST   /api/video/extractLyric     歌词提取

其他
  GET    /api/system                系统配置（公告、分类、平台列表）
  POST   /api/message/commit        反馈提交
  POST   /api/message/report        问题报告（加密）

用户
  GET    /api/user/getUserInfo      用户信息（未登录用户也有数据）
```

## 1.3 加密体系

### 加密 URL 列表（硬编码在 Pinia Setting store）

```
/video/cnSimpleExtract
/video/extract/v2
/video/subtitleExtract
/video/danmakuExtract
/video/extractLyric
/message/report
```

### 加密封装逻辑（来自 `BJCOAhp2.js`）

```
BJCOAhp2.js 导出四个函数：
  encryptByPublicKey(data)      — RSA 加密（短数据）
  encryptLongByPublicKey(data)  — RSA 分段加密（长数据）
  decryptByPublicKey(data)      — RSA 解密
  aesEncryptString(data)        — AES-128-CBC + PKCS7 → Base64

加密流程：
  1. GET /api/auth/keys → 拿到 1024 位 RSA 公钥 (k1/k2)
  2. 生成随机 salt（16进制字符串）
  3. 用 RSA 公钥加密 salt → saltEncrypted
  4. 用 salt 作为 AES 密钥，加密 JSON.stringify(requestBody) → bodyEncrypted
  5. 拼装: saltEncrypted + "@@@@" + bodyEncrypted
  6. 最终请求体是这个拼接后的密文
```

### 实测 RSA 公钥

```
k1: MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAkJZWIUIje8VjJ3okESY8stCs/
    a95hTUqK3fD/AST0F8mf7rTLoHCaW+AjmrqVR9NM/tvQNni67b5tGC5z3PD6oROJJ24
    QfcAW9urz8WjtrS/pTAfGeP/2AMCZfCu9eECidy16U2oQzBl9Q0SPoz0paJ9AfgcrHa0
    Zm3RVPL7JvOUzscL4AnirYImPsdaHZ52hAwz5y9bYoiWzUkuG7LvnAxO6JHQ71B3VTzM
    3ZmstS7wBsQ4lIbD318b49x+baaXVmC3yPW/E4Ol+OBZIBMWhzl7FgwIpgbGmsJSsqrO
    q3D8IgjS12K5CgkOT7EB/sil7lscgc22E5DckRpMYRG8dwIDAQAB
```

### 解析请求示例

```
POST /api/video/extract/v2
Headers:
  Content-Type: application/json
  KdSystem: Kedou
  Authorization: Bearer <token>  (可选)
Body: "BPmV5W4IuzoPJdpoYgXENXkYM87/ONrBRAxVRPwE..."  (密文字符串)
```

## 1.4 解析响应（页面渲染结果）

请求成功后，页面显示以下清晰度按钮：

```
[1080P+]  (disabled - VIP专属)
[1080P]   (disabled - 需要登录/VIP)
[高清720P]
[高清]
[清晰480P]
[流畅320P]
[音频]     — 仅提取音频
[图片(封面)] — 仅下载封面
```

## 1.5 后端解析流程（推测）

```
用户提交 URL
    │
    ▼
后端解密请求体 → 拿到原始视频 URL
    │
    ▼
调用 yt-dlp <url> --dump-json  (或 extract_info)
    │
    ▼
从 formats 数组中提取各清晰度的直链
    │
    ▼
返回 JSON: { title, cover, formats: [{ quality, format, size, url }] }
    │
    ▼
前端渲染按钮，用户点击后跳转到对应直链
```

## 1.6 前端路由结构

| 路由                 | 页面         | 说明           |
|----------------------|--------------|----------------|
| `/extract`           | 视频解析主页 | 单链接解析     |
| `/extract/:website`  | 平台专用页   | 如 /extract/bilibili |
| `/batch-extract`     | 批量解析     | 多链接批量处理 |
| `/downloader`        | 下载器页     | 桌面端推广     |
| `/video/player`      | 视频播放器   | 在线预览       |
| `/video/vip`         | VIP 页       | 会员购买       |

## 1.7 前端导航结构

```
首页    视频解析    批量解析下载    下载器    教程    更多（下拉）    博客
                                                      ├ 字幕下载
                                                      ├ 弹幕下载
                                                      ├ 歌词下载
                                                      └ 文本提取
```

## 1.8 支持的平台（前端展示）

**主流平台：** Twitter, YouTube, TikTok, Instagram, Facebook, 哔哩哔哩, 西瓜视频, 好看视频, AcFun, Naver

**热门网站：** 抖音, Envato Elements, IMDb, AfreecaTV, Streamable, ESPN, Discovery, F1, Reddit, TED, Vimeo, VK

**其他分类：** 影院影视、娱乐直播、综合网站、知识教育、电视卫视

**字幕/弹幕/歌词/文本提取：** B站, YouTube, 腾讯, 优酷, 爱奇艺, Dailymotion, Ted, Viki, Vimeo, Weverse, 抖音, 芒果TV, 网易云音乐, QQ音乐, 酷狗音乐, 知乎, 小红书, CSDN, 博客园, 简书, 百度文库 等
