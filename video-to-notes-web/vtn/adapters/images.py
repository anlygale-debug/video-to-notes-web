import ipaddress
import socket
import ssl
import urllib.error
import urllib.request
from urllib.parse import urlparse, urlunparse

from vtn.domain.errors import DomainError


ALLOWED_THUMBNAIL_HOST_SUFFIXES = (
    "hdslb.com",
    "biliimg.com",
    "xhscdn.com",
    "douyinpic.com",
)


def _validate_thumbnail_url(url):
    try:
        parsed = urlparse(str(url or ""))
        port = parsed.port
    except ValueError as exc:
        raise DomainError(
            "THUMBNAIL_UNAVAILABLE",
            "视频封面地址无效。",
            retryable=False,
        ) from exc
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or port not in (None, 443)
        or not any(
            hostname == suffix or hostname.endswith(f".{suffix}")
            for suffix in ALLOWED_THUMBNAIL_HOST_SUFFIXES
        )
    ):
        raise DomainError(
            "THUMBNAIL_UNAVAILABLE",
            "该视频没有可安全加载的封面。",
            retryable=False,
        )
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                hostname,
                443,
                type=socket.SOCK_STREAM,
            )
        }
    except OSError as exc:
        raise DomainError(
            "THUMBNAIL_UNAVAILABLE",
            "视频封面暂时无法连接。",
            retryable=True,
        ) from exc
    if not addresses or any(
        not ipaddress.ip_address(address).is_global
        for address in addresses
    ):
        raise DomainError(
            "THUMBNAIL_UNAVAILABLE",
            "该视频没有可安全加载的封面。",
            retryable=False,
        )
    return parsed.geturl()


class _SafeThumbnailRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        _validate_thumbnail_url(new_url)
        return super().redirect_request(
            request,
            file_pointer,
            code,
            message,
            headers,
            new_url,
        )


class SafeThumbnailFetcher:
    MAX_BYTES = 8 * 1024 * 1024

    @staticmethod
    def _ssl_context():
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()

    def fetch(self, url):
        parsed = urlparse(str(url or ""))
        if parsed.scheme == "http":
            parsed = parsed._replace(scheme="https", netloc=parsed.hostname or "")
            url = urlunparse(parsed)
        safe_url = _validate_thumbnail_url(url)
        hostname = urlparse(safe_url).hostname or ""
        if hostname == "xhscdn.com" or hostname.endswith(".xhscdn.com"):
            referer = "https://www.xiaohongshu.com/"
        elif hostname == "douyinpic.com" or hostname.endswith(".douyinpic.com"):
            referer = "https://www.douyin.com/"
        else:
            referer = "https://www.bilibili.com/"
        request = urllib.request.Request(
            safe_url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": referer,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            },
        )
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=self._ssl_context()),
            _SafeThumbnailRedirectHandler(),
        )
        try:
            with opener.open(request, timeout=20) as response:
                content_type = (
                    response.headers.get("Content-Type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                content_length = int(
                    response.headers.get("Content-Length") or 0
                )
                if (
                    not content_type.startswith("image/")
                    or content_length > self.MAX_BYTES
                ):
                    raise DomainError(
                        "THUMBNAIL_UNAVAILABLE",
                        "视频封面返回了无效内容。",
                        retryable=False,
                    )
                content = response.read(self.MAX_BYTES + 1)
        except DomainError:
            raise
        except (
            OSError,
            ValueError,
            urllib.error.URLError,
        ) as exc:
            raise DomainError(
                "THUMBNAIL_UNAVAILABLE",
                "视频封面暂时无法加载。",
                retryable=True,
            ) from exc
        if len(content) > self.MAX_BYTES:
            raise DomainError(
                "THUMBNAIL_UNAVAILABLE",
                "视频封面文件过大。",
                retryable=False,
            )
        return content, content_type
