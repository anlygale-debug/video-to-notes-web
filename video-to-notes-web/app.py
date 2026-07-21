"""Video to Notes Web App — FastAPI backend."""
import os, sys, json, re, uuid, shutil, subprocess, threading, time, tempfile, urllib.request
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Video to Notes")
BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")
tasks: dict = {}

def _parse_duration(dur_str):
    """Parse B站 duration like '1083:13' or '9:42' to seconds."""
    if not dur_str:
        return 0
    parts = dur_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def _extract_xhs_thumbnail(note_card):
    """从 XHS note_card 提取封面图 URL。兼容驼峰和下划线两种命名风格。"""
    il = note_card.get("imageList") or note_card.get("image_list", [])
    if not il:
        return ""
    img = il[0]
    return (img.get("urlDefault") or img.get("url_default") or
            img.get("urlPre") or img.get("url_pre") or "")


def _venv(cmd):
    """Run a command inside the agent-reach venv."""
    venv_py = os.path.expanduser("~/.agent-reach-venv/bin/python3")
    venv_bin = os.path.expanduser("~/.agent-reach-venv/bin")
    env = os.environ.copy()
    env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
    return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                          timeout=300, env=env, cwd="/tmp")


# ═══════════════════════════════════════════════════════════════════
# Platform Resolver Layer — unified video parser abstraction
# ═══════════════════════════════════════════════════════════════════

class BaseResolver:
    """平台解析器抽象基类。每个平台实现 search / resolve / download。"""
    platform_id: str = ""

    def search(self, query: str, task: dict) -> list[dict]:
        """搜索视频，返回标准化结果列表 [{id, title, creator, likes, url, duration, platform}]"""
        raise NotImplementedError

    def resolve(self, url: str, task: dict, **kwargs) -> dict:
        """解析 URL 为统一 Meta 字典"""
        raise NotImplementedError

    def download(self, meta: dict, output_path: str, task: dict) -> bool:
        """下载音频到 output_path，返回是否成功"""
        raise NotImplementedError


# ─── B站搜索覆盖（B站公开 API，不需要认证，比 yt-dlp 搜索更可靠）───

def _search_bilibili_api(query: str, task: dict) -> list[dict]:
    """B站公开搜索 API。返回标准化搜索结果。"""
    from urllib.parse import quote
    api_url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={quote(query)}"
    r = subprocess.run([
        "curl", "-s",
        "-H", "User-Agent: Mozilla/5.0",
        api_url
    ], capture_output=True, text=True, timeout=15)
    try:
        data = json.loads(r.stdout)
        results = []
        for item in data.get("data", {}).get("result", [])[:12]:
            bvid = item.get("bvid", "")
            if bvid:
                results.append({
                    "id": bvid,
                    "url": f"https://www.bilibili.com/video/{bvid}",
                    "title": re.sub(r'<[^>]+>', '', item.get("title", "")),
                    "creator": item.get("author", ""),
                    "likes": str(item.get("video_review", 0)),
                    "duration": _parse_duration(item.get("duration", "")),
                    "platform": "bilibili"
                })
        return results
    except Exception as e:
        task["error"] = str(e)
        return []


# 搜索覆盖表：平台 → 专用搜索函数（默认走 yt-dlp ytsearch）
_SEARCH_OVERRIDES = {
    "bilibili": _search_bilibili_api,
}


# ─── YtDlpResolver：主力解析器，覆盖 1800+ 平台 ───

class YtDlpResolver(BaseResolver):
    """基于 yt-dlp 的统一解析器。支持 B站、YouTube、抖音、快手、优酷等 1800+ 平台。"""

    def __init__(self, platform_id: str, cookie_required: bool = False):
        self.platform_id = platform_id
        self._cookie_required = cookie_required

    # ── cookie 降级链 ──
    def _cookie_flags(self) -> list[str]:
        """返回尝试序列。bilibili 先带 Chrome cookie 再裸连；其他平台直接裸连。"""
        if self._cookie_required or self.platform_id == "bilibili":
            return ["--cookies-from-browser chrome", ""]
        return [""]

    # ── yt-dlp JSON → 统一 Meta ──
    def _map_meta(self, d: dict, original_url: str) -> dict:
        """yt-dlp --dump-json 输出 → 标准 Meta 字典"""
        desc = d.get("description", "")
        if not desc or desc == "-":
            desc = ""
        return {
            "title":       d.get("title", ""),
            "creator":     d.get("uploader") or d.get("channel", ""),
            "platform":    self.platform_id,
            "likes":       str(d.get("like_count", 0)),
            "duration":    d.get("duration", 0) or 0,
            "thumbnail":   d.get("thumbnail", ""),
            "webpage_url": d.get("webpage_url", original_url),
            "download_url": original_url,
            "description": desc,
        }

    def _empty_meta(self, url: str) -> dict:
        """失败时返回字段齐全的空字典（不再静默返回 {}）"""
        return {"title": "", "creator": "", "platform": self.platform_id,
                "likes": "0", "duration": 0, "thumbnail": "",
                "webpage_url": url, "download_url": url, "description": ""}

    # ── 搜索 ──
    def search(self, query: str, task: dict) -> list[dict]:
        # 先检查是否有专用搜索覆盖
        override = _SEARCH_OVERRIDES.get(self.platform_id)
        if override:
            return override(query, task)

        # 默认走 yt-dlp 搜索
        r = _venv(
            f"yt-dlp --flat-playlist --dump-json "
            f"\"ytsearch8:{query}\" 2>/dev/null"
        )
        results = []
        for line in r.stdout.strip().split("\n"):
            try:
                d = json.loads(line)
                results.append({
                    "id":       d.get("id", ""),
                    "url":      d.get("webpage_url", ""),
                    "title":    d.get("title", ""),
                    "creator":  d.get("uploader", ""),
                    "likes":    str(d.get("like_count", 0)),
                    "duration": d.get("duration", 0),
                    "platform": self.platform_id,
                })
            except Exception:
                pass
        return results

    # ── 解析 ──
    def resolve(self, url: str, task: dict, **kwargs) -> dict:
        for flag in self._cookie_flags():
            cmd = f"yt-dlp {flag} --dump-json '{url}'"
            r = _venv(cmd)
            try:
                d = json.loads(r.stdout)
                return self._map_meta(d, url)
            except Exception:
                continue

        task["error"] = (
            f"解析 {self.platform_id} 链接失败。"
            f"视频可能已删除、私密或需要登录。"
        )
        return self._empty_meta(url)

    # ── 下载 ──
    def download(self, meta: dict, output_path: str, task: dict) -> bool:
        url = meta.get("download_url") or meta.get("webpage_url", "")
        for flag in self._cookie_flags():
            cmd = f"yt-dlp {flag} -x --audio-format mp3 -o '{output_path}' '{url}'"
            _venv(cmd)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return True

        task["error"] = f"下载 {self.platform_id} 视频失败。请检查网络或登录状态。"
        return False


# ─── XhsResolver：小红书专用（xhs CLI）───

class XhsResolver(BaseResolver):
    """小红书专用解析器。使用 xhs CLI，不走 yt-dlp（yt-dlp 的 XHS extractor 已挂）。"""
    platform_id = "xhs"

    def search(self, query: str, task: dict) -> list[dict]:
        r = _venv(f"xhs search '{query}' --json")
        try:
            data = json.loads(r.stdout)
            results = []
            for item in data.get("data", {}).get("items", [])[:8]:
                nc = item.get("note_card", {})
                info = nc.get("interact_info", {})
                results.append({
                    "id":       item["id"],
                    "xsec":     item.get("xsec_token", ""),
                    "title":    nc.get("display_title", ""),
                    "creator":  nc.get("user", {}).get("nickname", ""),
                    "likes":    info.get("liked_count", "0"),
                    "platform": "xhs",
                })
            return results
        except Exception as e:
            task["error"] = f"小红书搜索失败: {e}"
            return []

    def resolve(self, url: str, task: dict, **kwargs) -> dict:
        xsec = kwargs.get("xsec", "")
        meta = {"url": url, "platform": "xhs",
                "title": "", "creator": "", "likes": "0",
                "duration": 0, "thumbnail": "", "webpage_url": url,
                "download_url": "", "description": "",
                "note_id": "", "xsec_token": xsec}

        # ── 短链追踪 ──
        if "xhslink" in url:
            r = subprocess.run(
                ["curl", "-sL", "-o", "/dev/null", "-w", "%{url_effective}", url],
                capture_output=True, text=True, timeout=15)
            final_url = r.stdout.strip()
            note_id = re.search(r'/item/([a-f0-9]+)', final_url)
            if note_id:
                meta["note_id"] = note_id.group(1)
            else:
                meta["note_id"] = url.split("/")[-1].split("?")[0]
            if not xsec:
                xt = re.search(r'xsec_token=([^&]+)', final_url)
                if xt:
                    meta["xsec_token"] = xt.group(1)
        elif "/explore/" in url:
            meta["note_id"] = url.split("/explore/")[-1].split("?")[0]
        else:
            meta["note_id"] = url

        # ── 读取笔记元数据 ──
        xsec_flag = f"--xsec-token '{meta['xsec_token']}'" if meta["xsec_token"] else ""
        sr = _venv(f"xhs read '{meta['note_id']}' {xsec_flag} --json")
        try:
            resp_data = json.loads(sr.stdout).get("data", {})

            # 兼容新旧两种响应格式
            if "items" in resp_data:
                if not resp_data.get("items"):
                    task["error"] = "无法访问该链接。视频可能已被删除或设为私密。"
                    return meta
                nc = resp_data["items"][0].get("note_card", {})
                meta["title"]       = nc.get("display_title") or nc.get("title", "")
                meta["creator"]     = nc.get("user", {}).get("nickname", "")
                meta["likes"]       = nc.get("interact_info", {}).get("liked_count", "0")
                meta["description"] = nc.get("desc", "")
                meta["thumbnail"]   = _extract_xhs_thumbnail(nc)
                meta["duration"]    = nc.get("video", {}).get("capa", {}).get("duration", 0)
                video = nc.get("video", {})
            elif "title" in resp_data:
                meta["title"]       = resp_data.get("title", "")
                meta["creator"]     = resp_data.get("user", {}).get("nickname", "")
                meta["likes"]       = str(resp_data.get("interactInfo", {}).get("likedCount", 0))
                meta["description"] = resp_data.get("desc", "")
                meta["thumbnail"]   = _extract_xhs_thumbnail(resp_data)
                meta["duration"]    = resp_data.get("video", {}).get("capa", {}).get("duration", 0)
                video = resp_data.get("video", {})
            else:
                task["error"] = "无法访问该链接。请确认链接有效后重试。"
                return meta

            # ── 提取 CDN 直链 ──
            streams = video.get("media", {}).get("stream", {})
            for codec, formats in streams.items():
                for f in formats:
                    dl_url = f.get("masterUrl") or f.get("master_url", "")
                    if dl_url:
                        meta["download_url"] = dl_url
                        break
                if meta.get("download_url"):
                    break
        except Exception as e:
            task["error"] = f"小红书解析失败: {e}"

        return meta

    def download(self, meta: dict, output_path: str, task: dict) -> bool:
        dl_url = meta.get("download_url")
        if not dl_url:
            task["error"] = "无 CDN 下载地址。视频可能已被删除或 token 已过期。"
            return False

        tempdir = os.path.dirname(output_path)
        video_path = os.path.join(tempdir, "video.mp4")

        subprocess.run(["curl", "-sL", "-o", video_path, dl_url],
                       timeout=120, capture_output=True)
        if os.path.getsize(video_path) <= 1000:
            task["error"] = "CDN 下载失败：视频文件过小。token 可能已过期，请刷新后重试。"
            return False

        subprocess.run(["ffmpeg", "-y", "-i", video_path, "-vn",
                        "-acodec", "libmp3lame", "-q:a", "2", output_path],
                       timeout=120, capture_output=True)
        os.remove(video_path)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000


# ─── 平台注册表：URL 域名 → 解析器 ───

PLATFORM_REGISTRY: list[tuple] = [
    (r'(xhs|xiaohongshu|xhslink)\.com',   XhsResolver()),
    (r'bilibili\.com|b23\.tv',           YtDlpResolver("bilibili", cookie_required=True)),
    (r'youtube\.com|youtu\.be',          YtDlpResolver("youtube")),
    (r'douyin\.com',                     YtDlpResolver("douyin", cookie_required=True)),
    (r'kuaishou\.com',                   YtDlpResolver("kuaishou")),
    (r'(youku|yk)\.com',                 YtDlpResolver("youku")),
    (r'mgtv\.com',                       YtDlpResolver("mgtv")),
    (r'v\.qq\.com',                      YtDlpResolver("qqvideo")),
    (r'iqiyi\.com',                      YtDlpResolver("iqiyi")),
]

# platform_id → 解析器（用于搜索场景，用户手动选择平台）
PLATFORM_MAP: dict[str, BaseResolver] = {
    r.platform_id: r for _, r in PLATFORM_REGISTRY
}


def detect_platform(url: str) -> BaseResolver:
    """根据 URL 域名自动匹配解析器。未匹配时兜底走 yt-dlp 通用解析。"""
    for pattern, resolver in PLATFORM_REGISTRY:
        if re.search(pattern, url):
            return resolver
    return YtDlpResolver("unknown")


# ─── Pipeline steps (synchronous, run in threads) ────────────────

def step_search(task_id, query, platform):
    """搜索视频。通过 PLATFORM_MAP 找到对应解析器并委托搜索。"""
    tasks[task_id]["progress"] = {"step": "search", "status": "running",
                                   "message": f"Searching {platform}..."}

    resolver = PLATFORM_MAP.get(platform)
    if not resolver:
        tasks[task_id]["error"] = f"未知平台: {platform}"
        tasks[task_id]["progress"] = {"step": "search", "status": "error",
                                       "message": f"Unknown platform: {platform}"}
        return []

    results = resolver.search(query, tasks[task_id])
    tasks[task_id]["search_results"] = results
    tasks[task_id]["progress"] = {"step": "search", "status": "done",
                                   "message": f"Found {len(results)} results"}
    return results


def step_resolve(task_id, url, xsec=""):
    """解析视频 URL。自动检测平台并委托给对应解析器。"""
    tasks[task_id]["progress"] = {"step": "resolve", "status": "running",
                                   "message": "检测平台..."}

    # 检查是否为合法 URL（含 http/https协议）
    is_url = re.match(r'^https?://', url)
    if not is_url:
        tasks[task_id]["error"] = "输入的不是视频链接。请粘贴完整的视频 URL（以 http:// 或 https:// 开头）。"
        tasks[task_id]["progress"] = {"step": "resolve", "status": "error",
                                       "message": "非视频链接",
                                       "error_type": "invalid_url"}
        return {"title": "", "creator": "", "platform": "unknown",
                "likes": "0", "duration": 0, "thumbnail": "",
                "webpage_url": url, "download_url": url, "description": ""}

    resolver = detect_platform(url)
    is_unknown = isinstance(resolver, YtDlpResolver) and resolver.platform_id == "unknown"

    tasks[task_id]["progress"] = {"step": "resolve", "status": "running",
                                   "message": f"解析 {resolver.platform_id} 链接...",
                                   "platform": resolver.platform_id,
                                   "unknown_platform": is_unknown}

    meta = resolver.resolve(url, tasks[task_id], xsec=xsec)
    tasks[task_id]["meta"] = meta

    # 未知平台 + 解析失败 → 明确说明平台不支持
    if is_unknown and tasks[task_id].get("error"):
        tasks[task_id]["error"] = "暂不支持该视频平台，或该链接不包含视频。请确认链接来自支持的视频网站（小红书、B站、YouTube 等）。"

    tasks[task_id]["progress"] = {"step": "resolve", "status": "done",
                                   "message": meta.get("title", url)[:60],
                                   "platform": resolver.platform_id,
                                   "unknown_platform": is_unknown}
    return meta


def step_download(task_id, meta):
    """下载视频并提取音频。委托给对应解析器。"""
    platform = meta.get("platform", "unknown")
    tempdir = tasks[task_id]["tempdir"]
    audio_path = os.path.join(tempdir, "audio.mp3")

    tasks[task_id]["progress"] = {"step": "download", "status": "running",
                                   "message": "下载中..."}

    resolver = PLATFORM_MAP.get(platform)
    if not resolver:
        # 兜底：走 yt-dlp 通用下载
        resolver = YtDlpResolver(platform)

    ok = resolver.download(meta, audio_path, tasks[task_id])

    if ok and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
        tasks[task_id]["audio_path"] = audio_path
        size_kb = os.path.getsize(audio_path) // 1024
        tasks[task_id]["progress"] = {"step": "download", "status": "done",
                                       "message": f"{size_kb} KB"}
        return audio_path
    else:
        tasks[task_id]["progress"] = {"step": "download", "status": "error",
                                       "message": tasks[task_id].get("error", "下载失败")}
        return None


_whisper_model = None

def step_transcribe(task_id, audio_path):
    """Transcribe audio with local Whisper."""
    global _whisper_model
    tasks[task_id]["progress"] = {"step": "transcribe", "status": "running",
                                   "message": "Loading model..."}

    try:
        import whisper

        if _whisper_model is None:
            # tiny model: ~70MB, fastest, downloads once via curl
            _whisper_model = whisper.load_model("tiny")
            tasks[task_id]["progress"] = {"step": "transcribe", "status": "running",
                                           "message": "Transcribing..."}

        result = _whisper_model.transcribe(
            audio_path,
            task="transcribe",
            verbose=False,
            fp16=False
        )
        text = result.get("text", "").strip()
        try:
            from zhconv import convert
            text = convert(text, 'zh-cn')
        except Exception:
            pass
        if text:
            tasks[task_id]["transcript"] = text
            tasks[task_id]["progress"] = {"step": "transcribe", "status": "done",
                                           "message": f"{len(text)} chars"}
            return text
    except Exception as e:
        tasks[task_id]["progress"] = {"step": "transcribe", "status": "error",
                                       "message": str(e)[:80]}
        return None


def step_generate(task_id, transcript, meta, mode="standard", mermaid=False):
    """Generate structured markdown notes from transcript.

    mode: "standard" = optimized prompt, single pass (fast, good for <15min)
          "detailed"  = chunked processing + merge (slower, good for >20min)
          "scholar"   = detailed narrative for reading-based learning
    mermaid: True = run second pass to insert Mermaid diagrams
    """
    tasks[task_id]["progress"] = {"step": "generate", "status": "running",
                                   "message": "Structuring notes..."}

    if mode == "scholar":
        result = _generate_scholar(task_id, transcript, meta)
    elif mode == "detailed" and len(transcript) > 4000:
        result = _generate_detailed(task_id, transcript, meta)
    else:
        result = _generate_standard(task_id, transcript, meta)

    if mermaid and result:
        tasks[task_id]["progress"] = {"step": "generate", "status": "running",
                                       "message": "Inserting diagrams..."}
        result = _insert_mermaid(result, meta, task_id)
        tasks[task_id]["notes"] = result

    return result


SETTINGS_PATH = os.path.join(BASE, "data", "settings.json")


def _load_settings():
    """Load settings from data/settings.json. Returns dict with defaults."""
    defaults = {"api_base": "https://api.deepseek.com/v1", "api_key": "", "model": "deepseek-chat",
                "default_mode": "standard", "default_mermaid": False}
    try:
        with open(SETTINGS_PATH) as f:
            saved = json.load(f)
        defaults.update(saved)
    except Exception:
        pass
    return defaults


def _save_settings(data):
    """Save settings to data/settings.json."""
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _read_api_config():
    """读取 API 配置。优先级: 项目专属环境变量 > settings.json > 默认值。
    注意: 不使用 ANTHROPIC_* 环境变量（那是 Claude Code 自己的配置）。
    """
    s = _load_settings()
    api_key = os.environ.get("VTN_API_KEY") or s.get("api_key", "")
    api_base = os.environ.get("VTN_API_BASE") or s.get("api_base", "")
    model = os.environ.get("VTN_MODEL") or s.get("model", "deepseek-chat")
    return api_key, api_base, model


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


def _generate_standard(task_id, transcript, meta):
    """Option A: optimized single-pass prompt."""
    title = meta.get("title", "Untitled")
    creator = meta.get("creator", "Unknown")
    platform = meta.get("platform", "")
    likes = meta.get("likes", "0")

    prompt = f"""You are a study note generator. Take the transcript of a video and produce structured markdown notes.

Output format:

# {title} — 课后笔记

> 视频作者：{creator} | 平台：{platform} | ❤️ {likes}
> 转录：本地 Whisper

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
- Output ONLY the markdown, no extra text

Transcript:
{transcript}"""

    notes = _call_llm(prompt, max_tokens=16000)
    if not notes:
        notes = _basic_notes(meta, transcript)
    tasks[task_id]["notes"] = notes
    tasks[task_id]["progress"] = {"step": "generate", "status": "done",
                                   "message": "Notes ready"}
    return notes


def _generate_detailed(task_id, transcript, meta):
    """Option B: chunk transcript, process chunks in parallel, concatenate."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    title = meta.get("title", "Untitled")
    creator = meta.get("creator", "Unknown")
    platform = meta.get("platform", "")
    likes = meta.get("likes", "0")

    # Chunk transcript (~6000 chars, 300 char overlap)
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
                                   "message": f"Processing {total} chunks in parallel..."}

    def process_chunk(idx_chunk):
        idx, chunk = idx_chunk
        prompt = f"""Part {idx+1}/{total} of a video transcript. Generate detailed Chinese study notes for this section. Include key points, concepts, and important quotes (> blockquotes). Use ## headings. Output ONLY the markdown.

Section {idx+1}/{total}:
{chunk}"""
        return idx, _call_llm(prompt, max_tokens=6000)

    # Parallel processing
    chunk_notes = [""] * total
    with ThreadPoolExecutor(max_workers=min(total, 3)) as pool:
        futures = {pool.submit(process_chunk, (i, c)): i for i, c in enumerate(chunks)}
        for fut in as_completed(futures):
            idx, notes = fut.result()
            if notes:
                chunk_notes[idx] = notes
            tasks[task_id]["progress"] = {"step": "generate", "status": "running",
                                           "message": f"Chunk {sum(1 for n in chunk_notes if n)}/{total} done"}

    # Filter empty results
    chunk_notes = [n for n in chunk_notes if n]
    if not chunk_notes:
        notes = _basic_notes(meta, transcript)
        tasks[task_id]["notes"] = notes
        return notes

    # Concatenate directly — no merge LLM call (cuts time in half)
    notes = f"""# {title} — 课后笔记

> 视频作者：{creator} | 平台：{platform} | ❤️ {likes}
> 转录：本地 Whisper（详细模式 · {total} 段并行处理）

---

{chr(10).join(chunk_notes)}"""

    tasks[task_id]["notes"] = notes
    tasks[task_id]["progress"] = {"step": "generate", "status": "done",
                                   "message": f"Detailed notes ready ({total} sections)"}
    return notes


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


def _insert_mermaid(note_text, meta, task_id=None):
    """Second pass: scan completed notes and insert Mermaid diagrams."""
    title = meta.get("title", "Untitled")

    prompt = f"""You are a diagram specialist. Below is a completed set of Chinese study notes. Your ONLY job: insert Mermaid diagrams where they add visual clarity.

Requirements:
1. Insert exactly ONE framework diagram at the very beginning (before the first section), using mindmap or graph TD. This diagram must summarize the overall knowledge structure of the notes.
2. In the body of the notes, insert 3-4 diagrams where content benefits from visualization. Choose the best chart type:
   - flowchart (流程/步骤/决策)
   - quadrantChart (对比/四象限/矩阵)
   - sequenceDiagram (交互/消息传递/时序)
   - mindmap (概念层级/知识树)
   - ganttChart (时间线/阶段/路线图)
3. CRITICAL: Use ONLY English punctuation inside Mermaid code blocks (; , . : not ； ， 。 ：)
4. Do NOT modify any existing text, headings, tables, or structure. Only add diagram blocks.
5. Wrap diagrams in ```mermaid code blocks.
6. Output the COMPLETE notes with diagrams inserted. Do not omit any original content.

Notes:
{note_text}"""

    result = _call_llm(prompt, max_tokens=32000)
    if not result:
        return note_text
    return _fix_mermaid_syntax(result)


def _fix_mermaid_syntax(text):
    """Deterministic Mermaid syntax fixes — no LLM call. Handles common LLM errors."""
    def fix_block(block):
        # 1. Wrong diagram type name
        block = re.sub(r'\bganttChart\b', 'gantt', block)
        # 2. quadrantChart point with square-bracket label: A[label] → "label"
        block = re.sub(r'^(\s*\w)\[([^\]]+)\]\s*:', r'\1 "\2" :', block, flags=re.MULTILINE)
        # 3. Chinese punctuation → English (inside code blocks)
        block = block.replace('；', ';').replace('，', ',').replace('：', ':')
        block = block.replace('（', '(').replace('）', ')')
        return block

    return re.sub(
        r'```mermaid\n(.*?)```',
        lambda m: '```mermaid\n' + fix_block(m.group(1)) + '```',
        text, flags=re.DOTALL
    )


def _basic_notes(meta, transcript):
    """Fallback: simple notes without LLM structuring."""
    title = meta.get("title", "Untitled")
    creator = meta.get("creator", "")
    platform = meta.get("platform", "")
    return f"""# {title} — 课后笔记

> 视频作者：{creator} | 平台：{platform}
> 转录：本地 Whisper tiny

---

## 转录全文

{transcript}
"""


# ─── API Routes ──────────────────────────────────────────────────

@app.get("/")
async def index():
    return HTMLResponse(open(os.path.join(STATIC, "parser.html")).read())


@app.get("/v1")
async def index_v1():
    return HTMLResponse(open(os.path.join(STATIC, "index.html")).read())


@app.post("/api/search")
async def search(request: Request):
    body = await request.json()
    query = body.get("query", "").strip()
    platform = body.get("platform", "xhs")
    if not query:
        return JSONResponse({"error": "empty query"}, status_code=400)

    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {"progress": {}, "tempdir": None}
    results = step_search(task_id, query, platform)
    return JSONResponse({"task_id": task_id, "results": results})


@app.post("/api/process")
async def process(request: Request):
    """Process a video URL or text input: → transcribe → notes. SSE for progress."""
    body = await request.json()
    url = body.get("url", "").strip()
    stop_at = body.get("stop_at", "generate")  # "transcribe" = 解析后停下，不生成笔记
    # platform 参数保留但不用于解析路由（后端自动检测）
    mode = body.get("mode", "standard")  # "standard", "detailed", or "scholar"
    mermaid = body.get("mermaid", False)  # whether to insert Mermaid diagrams
    # Allow overriding title from search selection
    override_title = body.get("title", "")
    override_xsec = body.get("xsec", "")
    # Text input support
    text = body.get("text", "").strip()

    if not url and not text:
        return JSONResponse({"error": "empty url or text"}, status_code=400)

    api_key, api_base, model = _read_api_config()
    if not api_key or not api_base:
        return JSONResponse({"error": "no_api_config"}, status_code=400)

    task_id = str(uuid.uuid4())[:8]
    tempdir = tempfile.mkdtemp(prefix="vtn-")
    tasks[task_id] = {"progress": {}, "tempdir": tempdir, "url": url}

    def event_stream():
        try:
            if text:
                # ── Text input mode: skip resolve/download/transcribe ──
                # Step 1: Resolve (skipped)
                tasks[task_id]["progress"] = {"step": "resolve", "status": "done",
                                               "message": "Text input mode"}
                yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"

                # Step 2: Download (skipped)
                tasks[task_id]["progress"] = {"step": "download", "status": "done",
                                               "message": "Text input mode"}
                yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"

                # Step 3: Transcribe (skipped)
                tasks[task_id]["progress"] = {"step": "transcribe", "status": "done",
                                               "message": "Text input mode"}
                yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"

                transcript = text
                meta = {
                    "title": override_title or "Untitled",
                    "creator": "",
                    "platform": "text",
                    "likes": "0",
                    "duration": 0,
                    "thumbnail": "",
                    "webpage_url": "",
                }
                tasks[task_id]["meta"] = meta
                tasks[task_id]["transcript"] = transcript

                # 文本模式 + stop_at=transcribe：只返回原文，不生成笔记
                if stop_at == "transcribe":
                    tasks[task_id]["done"] = True
                    yield f"data: {json.dumps({'event': 'complete', 'data': {
                        'task_id': task_id,
                        'transcript': transcript,
                        'meta': meta,
                    }})}\n\n"
                    return
            else:
                # ── Standard URL processing (unchanged) ──
                # Step 1: Resolve
                meta = step_resolve(task_id, url, xsec=override_xsec)
                if override_title:
                    meta["title"] = override_title
                yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"
                if tasks[task_id].get("error"):
                    yield f"data: {json.dumps({'event': 'error', 'data': tasks[task_id]['error']})}\n\n"
                    return

                # Step 2: Download
                audio = step_download(task_id, meta)
                yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"
                if not audio:
                    yield f"data: {json.dumps({'event': 'error', 'data': 'Download failed'})}\n\n"
                    return

                # Step 3: Transcribe
                transcript = step_transcribe(task_id, audio)
                yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"
                if not transcript:
                    yield f"data: {json.dumps({'event': 'error', 'data': 'Transcription failed'})}\n\n"
                    return

                # 如果只需要解析（不生成笔记），在此停下
                if stop_at == "transcribe":
                    tasks[task_id]["done"] = True
                    yield f"data: {json.dumps({'event': 'complete', 'data': {
                        'task_id': task_id,
                        'transcript': transcript,
                        'meta': {
                            'title': meta.get('title', ''),
                            'creator': meta.get('creator', ''),
                            'platform': meta.get('platform', 'unknown'),
                            'likes': meta.get('likes', '0'),
                            'duration': meta.get('duration', 0),
                            'thumbnail': meta.get('thumbnail', ''),
                            'webpage_url': meta.get('webpage_url', url),
                            'description': meta.get('description', ''),
                        }
                    }})}\n\n"
                    return

            # Step 4: Generate notes (common to both paths)
            notes = step_generate(task_id, transcript, meta, mode=mode, mermaid=mermaid)
            yield f"data: {json.dumps({'event': 'progress', 'data': tasks[task_id]['progress']})}\n\n"

            # Done
            tasks[task_id]["done"] = True
            yield f"data: {json.dumps({'event': 'complete', 'data': {'task_id': task_id, 'notes': notes, 'transcript': transcript, 'meta': {'title': meta.get('title',''), 'creator': meta.get('creator',''), 'platform': meta.get('platform', 'unknown'), 'likes': meta.get('likes','0'), 'duration': meta.get('duration', 0), 'thumbnail': meta.get('thumbnail', ''), 'webpage_url': meta.get('webpage_url', url), 'description': meta.get('description', '')}}})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"
        finally:
            # Save audio for download (only relevant for URL processing path)
            ap = tasks[task_id].get("audio_path", "")
            if ap and os.path.exists(ap):
                persistent = f"/tmp/vtn-audio-{task_id}.mp3"
                shutil.copy(ap, persistent)
                tasks[task_id]["audio_download"] = persistent
            # Clean up temp files
            if os.path.exists(tempdir):
                shutil.rmtree(tempdir, ignore_errors=True)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/proxy-image")
async def proxy_image(url: str):
    """代理加载外部图片，绕过浏览器 Referer/CORS 限制。"""
    if not url or not url.startswith("http"):
        raise HTTPException(400, "Invalid image URL")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        content = resp.read()
        content_type = resp.headers.get("Content-Type", "image/jpeg")
        return Response(content=content, media_type=content_type)
    except Exception:
        raise HTTPException(404, "Image not found")


@app.get("/api/download/{task_id}/video")
async def download_video(task_id: str):
    """流式下载原视频。不落盘，直接从 CDN/yt-dlp 透传到浏览器。"""
    task = tasks.get(task_id, {})
    if not task.get("done"):
        raise HTTPException(404, "Task not found or not complete")

    meta = task.get("meta", {})
    platform = meta.get("platform", "")
    url = meta.get("download_url") or meta.get("webpage_url", "")

    if not url:
        raise HTTPException(404, "No video URL available")

    # 小红书：curl 重新下载 CDN 视频
    safe_filename = f"video-{task_id}.mp4"
    if platform == "xhs":
        proc = subprocess.Popen(
            ["curl", "-sL", url],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return StreamingResponse(
            proc.stdout,
            media_type="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
        )

    # yt-dlp 平台：yt-dlp -o - 输出到 stdout
    return StreamingResponse(
        _stream_video_ytdlp(url),
        media_type="video/mp4",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )


def _stream_video_ytdlp(url):
    """用 yt-dlp 下载视频并流式输出。"""
    import select
    cmd = f"yt-dlp -f 'best[ext=mp4]/best' -o - '{url}'"
    proc = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env={**os.environ, "PATH": f"{os.path.expanduser('~/.agent-reach-venv/bin')}:{os.environ.get('PATH', '')}"}
    )
    # 流式读取，每次 64KB
    try:
        while True:
            chunk = proc.stdout.read(65536)
            if not chunk:
                break
            yield chunk
    finally:
        proc.stdout.close()
        proc.wait()


@app.post("/api/export-pdf")
async def export_pdf(request: Request):
    """Generate a styled PDF from markdown content."""
    body = await request.json()
    notes = body.get("notes", "")
    title = body.get("title", "笔记")

    if not notes:
        raise HTTPException(400, "No notes content")

    safe_title = re.sub(r'[^\w\s-]', '', title)[:40]

    import markdown
    md_html = markdown.markdown(notes, extensions=["tables", "fenced_code"])

    css = """body{font-family:"PingFang SC","Noto Sans SC",sans-serif;max-width:750px;margin:2.5rem auto;line-height:1.9;color:#1a1a1a;font-size:11pt}
h1{font-size:1.6rem;border-bottom:2.5px solid #2c3e50;padding-bottom:.6rem;margin-top:0}
h2{font-size:1.25rem;margin-top:2rem;color:#2c3e50}
h3{font-size:1.05rem;color:#5b8def;margin-top:1.5rem}
blockquote{border-left:3.5px solid #5b8def;padding:.4rem 1rem;margin:.8rem 0;background:#f0f4ff;color:#445;font-style:italic}
pre{background:#f4f5f7;padding:1rem;border-radius:5px;font-size:9pt;overflow-x:auto}
code{background:#f0f0f0;padding:.1rem .3rem;border-radius:3px;font-family:"SF Mono",monospace;font-size:9pt}
pre code{background:none;padding:0}
table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:10pt}
th,td{border:1px solid #d0d5dd;padding:.5rem .7rem;text-align:left}
th{background:#f0f3f8;font-weight:600}
strong{color:#2c3e50}
a{color:#5b8def}
hr{border:none;border-top:1px solid #e0e0e0;margin:1.5rem 0}
@media print{@page{margin:2cm}}"""

    html = f"""<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>{title}</title><style>{css}</style></head><body>{md_html}</body></html>"""

    uid = str(uuid.uuid4())[:8]
    html_path = f"/tmp/vtn-pdf-{uid}.html"
    pdf_path = f"/tmp/vtn-pdf-{uid}.pdf"
    with open(html_path, "w") as f:
        f.write(html)

    subprocess.run(["/opt/homebrew/bin/weasyprint", html_path, pdf_path],
                   capture_output=True, timeout=30)
    os.remove(html_path)

    return FileResponse(pdf_path, filename=f"{safe_title}-课后笔记.pdf",
                        media_type="application/pdf")


@app.get("/api/download/{task_id}/audio")
async def download_audio(task_id: str):
    task = tasks.get(task_id, {})
    ap = task.get("audio_download", "")
    if not ap or not os.path.exists(ap):
        raise HTTPException(404, "Audio not found")
    title = task.get("meta", {}).get("title", "audio")
    safe = re.sub(r'[^\w\s-]', '', title)[:30]
    return FileResponse(ap, filename=f"{safe}.mp3", media_type="audio/mpeg")


@app.get("/api/download/{task_id}/transcript")
async def download_transcript(task_id: str):
    task = tasks.get(task_id, {})
    transcript = task.get("transcript", "")
    if not transcript:
        raise HTTPException(404, "Transcript not found")
    title = task.get("meta", {}).get("title", "transcript")
    safe = re.sub(r'[^\w\s-]', '', title)[:30]
    path = f"/tmp/vtn-transcript-{task_id}.txt"
    with open(path, "w") as f:
        f.write(transcript)
    return FileResponse(path, filename=f"{safe}-转录.txt", media_type="text/plain")


@app.get("/api/download/{task_id}/transcript-md")
async def download_transcript_md(task_id: str):
    """下载 .md 格式转录文本，带视频标题和元数据。"""
    task = tasks.get(task_id, {})
    transcript = task.get("transcript", "")
    if not transcript:
        raise HTTPException(404, "Transcript not found")
    meta = task.get("meta", {})
    title = meta.get("title", "transcript")
    safe = re.sub(r'[^\w\s-]', '', title)[:30]

    md = f"""# {title} — 转录全文

> 作者：{meta.get('creator', '未知')} | 平台：{meta.get('platform', 'unknown')}
> 转录：本地 Whisper tiny

---

{transcript}
"""
    path = f"/tmp/vtn-transcript-md-{task_id}.md"
    with open(path, "w") as f:
        f.write(md)
    return FileResponse(path, filename=f"{safe}-转录.md", media_type="text/markdown")


@app.get("/api/download/{task_id}/merged")
async def download_merged(task_id: str):
    task = tasks.get(task_id, {})
    if not task.get("done"):
        raise HTTPException(404, "Task not found")
    notes = task.get("notes", "")
    transcript = task.get("transcript", "")
    title = task.get("meta", {}).get("title", "notes")
    safe = re.sub(r'[^\w\s-]', '', title)[:30]
    merged = notes + "\n\n---\n\n## 转录全文\n\n" + transcript
    path = f"/tmp/vtn-merged-{task_id}.md"
    with open(path, "w") as f:
        f.write(merged)
    return FileResponse(path, filename=f"{safe}-完整笔记.md", media_type="text/markdown")


@app.get("/api/download/{task_id}/full")
async def download_full(task_id: str):
    task = tasks.get(task_id, {})
    if not task.get("done"):
        raise HTTPException(404, "Task not found")
    notes = task.get("notes", "")
    transcript = task.get("transcript", "")
    title = task.get("meta", {}).get("title", "notes")
    safe = re.sub(r'[^\w\s-]', '', title)[:30]
    import zipfile
    zip_path = f"/tmp/vtn-full-{task_id}.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(f"{safe}-笔记.md", notes)
        zf.writestr(f"{safe}-转录.txt", transcript)
    return FileResponse(zip_path, filename=f"{safe}-完整包.zip", media_type="application/zip")


@app.get("/api/download/{task_id}")
async def download(task_id: str):
    task = tasks.get(task_id, {})
    if not task.get("done"):
        raise HTTPException(404, "Task not found or not complete")

    notes = task.get("notes", "")
    title = task.get("meta", {}).get("title", "notes")
    safe_title = re.sub(r'[^\w\s-]', '', title)[:40]

    path = f"/tmp/vtn-{task_id}.md"
    with open(path, "w") as f:
        f.write(notes)

    return FileResponse(path, filename=f"{safe_title}-课后笔记.md",
                        media_type="text/markdown")


# ─── Settings ──────────────────────────────────────────────────

@app.get("/api/settings")
async def get_settings():
    return JSONResponse(_load_settings())


@app.post("/api/settings")
async def save_settings(request: Request):
    body = await request.json()
    s = _load_settings()
    if "api_key" in body:
        s["api_key"] = body["api_key"]
    for field in ["api_base", "model", "default_mode", "default_mermaid"]:
        if field in body:
            s[field] = body[field]
    _save_settings(s)
    return JSONResponse({"ok": True})


@app.post("/api/test-connection")
async def test_connection(request: Request):
    body = await request.json()
    api_key = body.get("api_key", "")
    api_base = body.get("api_base", "")
    model = body.get("model", "deepseek-chat")
    if not api_key or not api_base:
        return JSONResponse({"ok": False, "error": "Missing API key or base URL"})
    import time as _time
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


# ─── Startup ────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    print("🎬 Video to Notes Web App started at http://localhost:3000")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
