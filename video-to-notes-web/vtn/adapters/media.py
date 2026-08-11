import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from vtn.domain.errors import DomainError


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "bilibili.com" in host or "b23.tv" in host:
        return "bilibili"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "xiaohongshu.com" in host or "xhslink.com" in host or "xhslink.cn" in host:
        return "xiaohongshu"
    if (
        host == "douyin.com"
        or host.endswith(".douyin.com")
        or host == "iesdouyin.com"
        or host.endswith(".iesdouyin.com")
    ):
        return "douyin"
    return "other"


class PlatformMedia:
    def resolve(self, url: str) -> dict:
        raise NotImplementedError

    def download_audio(self, url: str, directory: Path) -> Path:
        raise NotImplementedError

    def download_video(self, url: str, directory: Path) -> Path:
        raise NotImplementedError

    def video_stream_command(self, url: str) -> list[str]:
        return ["yt-dlp", "-f", "best[ext=mp4]/best", "-o", "-", url]

    def process_environment(self):
        return None


class YtDlpPlatformMedia(PlatformMedia):
    def __init__(self, executable="yt-dlp"):
        self.executable = executable
        runtime_bin = Path(sys.executable).parent
        self.env = {
            **os.environ,
            "PATH": (
                f"{runtime_bin}:{Path.home() / '.agent-reach-venv/bin'}:"
                f"{os.environ.get('PATH', '')}"
            ),
        }

    def _run(self, args, timeout):
        try:
            return subprocess.run(
                args, capture_output=True, text=True, timeout=timeout, env=self.env, check=True
            )
        except (subprocess.SubprocessError, OSError) as exc:
            raise DomainError("MEDIA_RESOLVE_FAILED", f"视频解析失败：{exc}", retryable=True)

    def process_environment(self):
        return self.env

    def _chrome_cookie_database_exists(self):
        home = Path(self.env.get("HOME") or Path.home())
        roots = [
            home / ".config" / "google-chrome",
            home / "Library" / "Application Support" / "Google" / "Chrome",
        ]
        local_app_data = self.env.get("LOCALAPPDATA")
        if local_app_data:
            roots.append(Path(local_app_data) / "Google" / "Chrome" / "User Data")
        for root in roots:
            for profile in (root / "Default", *root.glob("Profile *")):
                if (
                    (profile / "Cookies").is_file()
                    or (profile / "Network" / "Cookies").is_file()
                ):
                    return True
        return False

    def _cookie_attempts(self, url):
        platform = detect_platform(url)
        if platform == "douyin":
            attempts = []
            cookie_path = str(
                self.env.get("VTN_DOUYIN_COOKIES_PATH") or ""
            ).strip()
            if cookie_path:
                expanded_path = Path(cookie_path).expanduser()
                if expanded_path.is_file():
                    attempts.append(["--cookies", str(expanded_path)])
            if self._chrome_cookie_database_exists():
                attempts.append(["--cookies-from-browser", "chrome"])
            attempts.append([])
            return attempts
        if platform == "bilibili" and self._chrome_cookie_database_exists():
            return [[], ["--cookies-from-browser", "chrome"]]
        return [[]]

    @staticmethod
    def _douyin_video_id(url):
        parsed = urlparse(url)
        modal_id = (parse_qs(parsed.query).get("modal_id") or [""])[0]
        if re.fullmatch(r"\d{10,24}", modal_id):
            return modal_id
        match = re.search(
            r"/(?:video|share/video|shipin)/(\d{10,24})(?:/|$)",
            parsed.path,
        )
        return match.group(1) if match else ""

    def _normalize_douyin_url(self, url):
        video_id = self._douyin_video_id(url)
        if video_id:
            return f"https://www.douyin.com/video/{video_id}"
        host = (urlparse(url).hostname or "").lower()
        if host not in {"v.douyin.com", "jx.douyin.com"}:
            return url
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                redirected_url = response.geturl()
        except (OSError, urllib.error.URLError):
            return url
        redirected_video_id = self._douyin_video_id(redirected_url)
        if redirected_video_id:
            return f"https://www.douyin.com/video/{redirected_video_id}"
        return redirected_url

    def _normalize_source_url(self, url):
        if detect_platform(url) == "douyin":
            return self._normalize_douyin_url(url)
        return url

    @staticmethod
    def _douyin_access_error(last_error):
        lowered = (last_error or "").lower()
        if not any(
            marker in lowered
            for marker in ("cookie", "verification", "forbidden", "http error 403")
        ):
            return None
        return DomainError(
            "DOUYIN_ACCESS_REQUIRED",
            "抖音解析凭证已失效，请先在 Chrome 打开一次抖音后再重试。",
            retryable=True,
        )

    @staticmethod
    def _xiaohongshu_creator_from_page(page_html, uploader_id):
        if not page_html or not uploader_id:
            return ""
        candidates = []
        for user_match in re.finditer(re.escape(uploader_id), page_html):
            start = max(0, user_match.start() - 800)
            end = min(len(page_html), user_match.end() + 800)
            area = page_html[start:end]
            for nickname_match in re.finditer(
                r'"nickname"\s*:\s*"([^"\\]{1,80})"',
                area,
            ):
                distance = abs(
                    start + nickname_match.start() - user_match.start()
                )
                candidates.append((distance, nickname_match.group(1)))
        if not candidates:
            return ""
        raw_nickname = min(candidates, key=lambda item: item[0])[1]
        try:
            return json.loads(f'"{raw_nickname}"').strip()
        except (json.JSONDecodeError, AttributeError):
            return raw_nickname.strip()

    @staticmethod
    def _xiaohongshu_creator_via_ytdlp_page(webpage_url, note_id, uploader_id):
        parsed = urlparse(webpage_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or not (
                parsed.hostname == "xiaohongshu.com"
                or parsed.hostname.endswith(".xiaohongshu.com")
            )
            or not re.fullmatch(r"[0-9a-f]+", note_id or "")
        ):
            return ""
        try:
            from yt_dlp import YoutubeDL
            from yt_dlp.extractor.xiaohongshu import XiaoHongShuIE
            from yt_dlp.utils import js_to_json
            from yt_dlp.utils.traversal import traverse_obj

            with YoutubeDL({"quiet": True, "no_warnings": True}) as downloader:
                extractor = XiaoHongShuIE(downloader)
                page_html = extractor._download_webpage(webpage_url, note_id)
                initial_state = extractor._search_json(
                    r"window\.__INITIAL_STATE__\s*=",
                    page_html,
                    "initial state",
                    note_id,
                    transform_source=js_to_json,
                )
            user = traverse_obj(
                initial_state,
                ("note", "noteDetailMap", note_id, "note", "user"),
            ) or {}
            page_user_id = str(user.get("userId") or "").strip()
            if uploader_id and page_user_id and page_user_id != uploader_id:
                return ""
            return str(user.get("nickname") or "").strip()
        except Exception:
            return ""

    def _resolve_xiaohongshu_creator(self, metadata, source_url=""):
        webpage_url = str(metadata.get("webpage_url") or source_url or "")
        parsed = urlparse(webpage_url)
        page_html = ""
        note_match = re.search(
            r"/(?:discovery/item|explore|item)/([a-f0-9]+)",
            parsed.path,
        )
        if not note_match and detect_platform(source_url) == "xiaohongshu":
            try:
                redirect_request = urllib.request.Request(
                    source_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(
                    redirect_request,
                    timeout=30,
                ) as response:
                    redirected_url = response.geturl()
                    try:
                        page_html = response.read(
                            2 * 1024 * 1024 + 1
                        ).decode("utf-8", errors="replace")
                    except AttributeError:
                        page_html = ""
                redirected = urlparse(redirected_url)
                if (
                    redirected.hostname == "xiaohongshu.com"
                    or (
                        redirected.hostname
                        and redirected.hostname.endswith(".xiaohongshu.com")
                    )
                ):
                    webpage_url = redirected_url
                    parsed = redirected
                    note_match = re.search(
                        r"/(?:discovery/item|explore|item)/([a-f0-9]+)",
                        parsed.path,
                    )
            except (OSError, urllib.error.URLError):
                pass
        uploader_id = str(metadata.get("uploader_id") or "").strip()
        page_creator = self._xiaohongshu_creator_from_page(
            page_html,
            uploader_id,
        )
        if page_creator:
            return page_creator
        if not note_match:
            return ""
        xsec_token = (parse_qs(parsed.query).get("xsec_token") or [""])[0]
        proxy_names = {
            "all_proxy", "http_proxy", "https_proxy",
        }
        xhs_env = {
            key: value for key, value in self.env.items()
            if key.lower() not in proxy_names
        }
        data = {}
        if xsec_token:
            try:
                result = subprocess.run(
                    [
                        "xhs", "read", note_match.group(1),
                        "--xsec-token", xsec_token, "--json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=xhs_env,
                    check=True,
                )
                data = json.loads(result.stdout).get("data") or {}
            except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
                pass
        items = data.get("items") if isinstance(data, dict) else None
        if isinstance(items, list) and items:
            note_card = items[0].get("note_card") or {}
            nickname = (note_card.get("user") or {}).get("nickname")
            if nickname:
                return str(nickname).strip()
        if isinstance(data, dict):
            nickname = str(
                (data.get("user") or {}).get("nickname") or ""
            ).strip()
            if nickname:
                return nickname
        if (
            uploader_id
            and (
                parsed.hostname == "xiaohongshu.com"
                or (
                    parsed.hostname
                    and parsed.hostname.endswith(".xiaohongshu.com")
                )
            )
        ):
            try:
                page_request = urllib.request.Request(
                    webpage_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(
                    page_request,
                    timeout=30,
                ) as response:
                    fallback_page = response.read(
                        2 * 1024 * 1024 + 1
                    ).decode("utf-8", errors="replace")
                page_creator = self._xiaohongshu_creator_from_page(
                    fallback_page,
                    uploader_id,
                )
                if page_creator:
                    return page_creator
            except (OSError, urllib.error.URLError):
                pass
        ytdlp_page_creator = self._xiaohongshu_creator_via_ytdlp_page(
            webpage_url,
            note_match.group(1),
            uploader_id,
        )
        if ytdlp_page_creator:
            return ytdlp_page_creator
        if re.fullmatch(r"[0-9a-f]{16,64}", uploader_id):
            try:
                profile_request = urllib.request.Request(
                    "https://www.xiaohongshu.com/user/profile/"
                    f"{uploader_id}",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(
                    profile_request,
                    timeout=30,
                ) as response:
                    profile_page = response.read(
                        2 * 1024 * 1024 + 1
                    ).decode("utf-8", errors="replace")
                return self._xiaohongshu_creator_from_page(
                    profile_page,
                    uploader_id,
                )
            except (OSError, urllib.error.URLError):
                pass
        return ""

    @staticmethod
    def _bilibili_bvid(url):
        match = re.search(r"/video/(BV[0-9A-Za-z]+)", url, re.IGNORECASE)
        return match.group(1) if match else ""

    def _resolve_bilibili_api(self, url):
        bvid = self._bilibili_bvid(url)
        if not bvid:
            return None
        request = urllib.request.Request(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.bilibili.com/",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            return None
        if payload.get("code") != 0 or not isinstance(payload.get("data"), dict):
            return None
        data = payload["data"]
        return {
            "source_url": url,
            "platform": "bilibili",
            "title": data.get("title") or "未命名视频",
            "creator": (data.get("owner") or {}).get("name") or "",
            "description": data.get("desc") or "",
            "duration_seconds": int(data.get("duration") or 0),
            "thumbnail_url": data.get("pic") or "",
        }

    def _download_bilibili_audio(self, url, directory):
        bvid = self._bilibili_bvid(url)
        if not bvid:
            return None
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/",
        }
        try:
            view_request = urllib.request.Request(
                f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
                headers=headers,
            )
            with urllib.request.urlopen(view_request, timeout=30) as response:
                view_payload = json.load(response)
            view_data = view_payload.get("data") or {}
            query = urlencode({
                "bvid": bvid,
                "cid": view_data["cid"],
                "fnval": 16,
                "qn": 64,
                "fourk": 0,
            })
            play_request = urllib.request.Request(
                f"https://api.bilibili.com/x/player/playurl?{query}",
                headers=headers,
            )
            with urllib.request.urlopen(play_request, timeout=30) as response:
                play_payload = json.load(response)
            audio_streams = (
                ((play_payload.get("data") or {}).get("dash") or {}).get("audio")
                or []
            )
            audio_streams.sort(
                key=lambda stream: int(stream.get("bandwidth") or 0),
                reverse=True,
            )
            stream_url = (
                (audio_streams[0].get("baseUrl") or audio_streams[0].get("base_url"))
                if audio_streams
                else ""
            )
            parsed_stream = urlparse(stream_url)
            if (
                parsed_stream.scheme != "https"
                or not parsed_stream.hostname
                or not parsed_stream.hostname.endswith(
                    (".bilivideo.com", ".bilivideo.cn")
                )
            ):
                return None
            media_request = urllib.request.Request(stream_url, headers=headers)
            output = directory / "audio.m4a"
            with urllib.request.urlopen(media_request, timeout=1800) as response:
                with output.open("wb") as handle:
                    shutil.copyfileobj(response, handle)
            return output if output.stat().st_size > 0 else None
        except (
            KeyError,
            OSError,
            ValueError,
            urllib.error.URLError,
            json.JSONDecodeError,
        ):
            return None

    def _download_bilibili_video(self, url, directory):
        bvid = self._bilibili_bvid(url)
        if not bvid:
            return None
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/",
        }
        try:
            view_request = urllib.request.Request(
                f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
                headers=headers,
            )
            with urllib.request.urlopen(view_request, timeout=30) as response:
                view_payload = json.load(response)
            view_data = view_payload.get("data") or {}
            query = urlencode({
                "bvid": bvid,
                "cid": view_data["cid"],
                "fnval": 16,
                "qn": 64,
                "fourk": 0,
            })
            play_request = urllib.request.Request(
                f"https://api.bilibili.com/x/player/playurl?{query}",
                headers=headers,
            )
            with urllib.request.urlopen(play_request, timeout=30) as response:
                play_payload = json.load(response)
            dash = (play_payload.get("data") or {}).get("dash") or {}
            video_streams = dash.get("video") or []
            audio_streams = dash.get("audio") or []
            h264_streams = [
                stream
                for stream in video_streams
                if str(stream.get("codecs") or "").startswith("avc1")
            ]
            video_streams = h264_streams or video_streams
            video_streams.sort(
                key=lambda stream: int(stream.get("bandwidth") or 0),
                reverse=True,
            )
            audio_streams.sort(
                key=lambda stream: int(stream.get("bandwidth") or 0),
                reverse=True,
            )
            video_url = (
                video_streams[0].get("baseUrl")
                or video_streams[0].get("base_url")
            )
            audio_url = (
                audio_streams[0].get("baseUrl")
                or audio_streams[0].get("base_url")
            )
            for stream_url in (video_url, audio_url):
                parsed_stream = urlparse(stream_url)
                if (
                    parsed_stream.scheme != "https"
                    or not parsed_stream.hostname
                    or not parsed_stream.hostname.endswith(
                        (".bilivideo.com", ".bilivideo.cn")
                    )
                ):
                    return None
            video_input = directory / "bilibili-video.m4s"
            audio_input = directory / "bilibili-audio.m4s"
            for stream_url, output_path in (
                (video_url, video_input),
                (audio_url, audio_input),
            ):
                media_request = urllib.request.Request(
                    stream_url,
                    headers=headers,
                )
                with urllib.request.urlopen(
                    media_request,
                    timeout=1800,
                ) as response:
                    with output_path.open("wb") as handle:
                        shutil.copyfileobj(response, handle)
            output = directory / "video.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(video_input),
                    "-i",
                    str(audio_input),
                    "-c",
                    "copy",
                    "-movflags",
                    "+faststart",
                    str(output),
                ],
                capture_output=True,
                text=True,
                timeout=1800,
                env=self.env,
                check=True,
            )
            return output if output.stat().st_size > 0 else None
        except (
            IndexError,
            KeyError,
            OSError,
            ValueError,
            subprocess.SubprocessError,
            urllib.error.URLError,
            json.JSONDecodeError,
        ):
            return None

    def resolve(self, url: str) -> dict:
        result = None
        last_error = ""
        normalized_url = self._normalize_source_url(url)
        for cookie_args in self._cookie_attempts(url):
            try:
                result = subprocess.run(
                    [
                        self.executable, *cookie_args, "--no-playlist",
                        "--dump-single-json", normalized_url,
                    ],
                    capture_output=True, text=True, timeout=120, env=self.env, check=True,
                )
                break
            except subprocess.CalledProcessError as exc:
                last_error = (exc.stderr or str(exc)).strip().splitlines()[-1]
            except (subprocess.SubprocessError, OSError) as exc:
                last_error = str(exc)
        if result is None:
            if detect_platform(url) == "bilibili":
                fallback = self._resolve_bilibili_api(url)
                if fallback is not None:
                    return fallback
            if detect_platform(url) == "douyin":
                access_error = self._douyin_access_error(last_error)
                if access_error is not None:
                    raise access_error
            raise DomainError(
                "MEDIA_RESOLVE_FAILED",
                "视频解析失败：视频平台暂时拒绝解析，可能需要登录凭证或链接已失效",
                retryable=True,
            )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise DomainError("MEDIA_RESOLVE_FAILED", "视频平台返回了无法识别的信息", retryable=True) from exc
        platform = detect_platform(url)
        if platform == "douyin":
            # Douyin exposes the public nickname as ``channel``/``artist``.
            # ``uploader`` is often only a numeric account handle.
            creator = (
                data.get("channel")
                or data.get("artist")
                or data.get("uploader")
                or ""
            )
        else:
            creator = data.get("uploader") or data.get("channel") or ""
        if not creator and platform == "xiaohongshu":
            creator = self._resolve_xiaohongshu_creator(data, url)
        return {
            "source_url": url,
            "platform": platform,
            "title": data.get("title") or "未命名视频",
            "creator": creator,
            "description": data.get("description") or "",
            "duration_seconds": int(data.get("duration") or 0),
            "thumbnail_url": data.get("thumbnail") or "",
        }

    def download_audio(self, url: str, directory: Path) -> Path:
        output = directory / "audio.%(ext)s"
        last_error = ""
        normalized_url = self._normalize_source_url(url)
        for cookie_args in self._cookie_attempts(url):
            try:
                subprocess.run(
                    [
                        self.executable, *cookie_args, "--no-playlist", "-x",
                        "--audio-format", "mp3", "-o", str(output), normalized_url,
                    ],
                    capture_output=True, text=True, timeout=1800, env=self.env, check=True,
                )
                break
            except subprocess.CalledProcessError as exc:
                last_error = (exc.stderr or str(exc)).strip().splitlines()[-1]
            except (subprocess.SubprocessError, OSError) as exc:
                last_error = str(exc)
        matches = list(directory.glob("audio.*"))
        if not matches and detect_platform(url) == "bilibili":
            fallback = self._download_bilibili_audio(url, directory)
            if fallback is not None:
                return fallback
        if not matches:
            if detect_platform(url) == "douyin":
                access_error = self._douyin_access_error(last_error)
                if access_error is not None:
                    raise access_error
            raise DomainError(
                "MEDIA_DOWNLOAD_FAILED", f"没有生成可转录音频：{last_error}", retryable=True
            )
        return matches[0]

    def download_video(self, url: str, directory: Path) -> Path:
        output = directory / "video.%(ext)s"
        last_error = ""
        normalized_url = self._normalize_source_url(url)
        for cookie_args in self._cookie_attempts(url):
            try:
                subprocess.run(
                    [
                        self.executable, *cookie_args, "--no-playlist", "-f",
                        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                        "--merge-output-format", "mp4", "--remux-video", "mp4",
                        "-o", str(output), normalized_url,
                    ],
                    capture_output=True, text=True, timeout=1800,
                    env=self.env, check=True,
                )
                break
            except subprocess.CalledProcessError as exc:
                last_error = (exc.stderr or str(exc)).strip().splitlines()[-1]
            except (subprocess.SubprocessError, OSError) as exc:
                last_error = str(exc)
        matches = [
            path for path in directory.glob("video.*")
            if path.is_file() and path.suffix == ".mp4" and path.stat().st_size > 0
        ]
        if not matches and detect_platform(url) == "bilibili":
            fallback = self._download_bilibili_video(url, directory)
            if fallback is not None:
                return fallback
        if not matches:
            if detect_platform(url) == "douyin":
                access_error = self._douyin_access_error(last_error)
                if access_error is not None:
                    raise access_error
            raise DomainError(
                "MEDIA_DOWNLOAD_FAILED",
                f"没有生成可下载视频：{last_error or '平台未返回有效视频'}",
                retryable=True,
            )
        return matches[0]

    def video_stream_command(self, url: str):
        attempts = self._cookie_attempts(url)
        cookie_args = (
            attempts[0]
            if detect_platform(url) == "douyin" and attempts
            else attempts[-1] if len(attempts) > 1 else []
        )
        return [
            self.executable, *cookie_args, "--no-playlist", "-f",
            "best[ext=mp4]/best", "-o", "-", self._normalize_source_url(url),
        ]


class FakePlatformMedia(PlatformMedia):
    def __init__(self, *, fail_once=False):
        self.fail_once = fail_once

    def resolve(self, url: str) -> dict:
        if self.fail_once:
            self.fail_once = False
            raise DomainError("MEDIA_RESOLVE_FAILED", "测试解析失败", retryable=True)
        return {
            "source_url": url,
            "platform": detect_platform(url),
            "title": "心理学：亲密关系中的控制欲破解路径",
            "creator": "测试作者",
            "description": "固定验收来源",
            "duration_seconds": 600,
            "thumbnail_url": "",
        }

    def download_audio(self, url: str, directory: Path) -> Path:
        path = directory / "audio.mp3"
        path.write_bytes(b"fixture")
        return path

    def download_video(self, url: str, directory: Path) -> Path:
        path = directory / "video.mp4"
        path.write_bytes(b"fixture-video")
        return path
