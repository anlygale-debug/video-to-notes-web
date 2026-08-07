import json
import os
import ssl
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

from vtn.domain.errors import DomainError
from vtn.domain.models import utc_now


LLM_CHANNELS = ("free", "paid")
LLM_PROTOCOLS = ("openai_chat", "anthropic_messages")

FCC_NO_THINKING_PREFIX = "claude-3-freecc-no-thinking/nvidia_nim/"
FCC_DIRECT_PREFIX = "anthropic/nvidia_nim/"
FCC_NOTE_OPTIMIZED_MODELS = {
    "nvidia/nemotron-3-ultra-550b-a55b",
}
NVIDIA_EOL_MODELS = {
    "deepseek-ai/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-pro",
}


def llm_endpoint(profile):
    base = profile["api_base"].rstrip("/")
    protocol = profile.get("protocol") or "openai_chat"
    if protocol == "anthropic_messages":
        return base + ("/messages" if base.endswith("/v1") else "/v1/messages")
    return base + "/chat/completions"


def llm_request(profile, prompt, *, max_tokens, temperature, json_mode=False):
    protocol = profile.get("protocol") or "openai_chat"
    if protocol == "anthropic_messages":
        payload = {
            "model": profile["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {profile['api_key']}",
            "x-api-key": profile["api_key"],
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
    else:
        payload = {
            "model": profile["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {profile['api_key']}",
            "Content-Type": "application/json",
        }
    return urllib.request.Request(
        llm_endpoint(profile),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
    )


def llm_response_text(profile, payload):
    protocol = profile.get("protocol") or "openai_chat"
    if protocol == "anthropic_messages":
        content = payload.get("content") if isinstance(payload, dict) else None
        if not isinstance(content, list):
            raise ValueError("missing Anthropic content")
        text = "".join(
            str(block.get("text") or "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
        if not text:
            raise ValueError("missing Anthropic text")
        return text
    return payload["choices"][0]["message"]["content"]


class LLMModelCatalog:
    """Discover selectable models from a configured provider without exposing its key."""

    def __init__(self, *, timeout_seconds=15):
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _endpoint(profile):
        base = profile["api_base"].rstrip("/")
        return base + ("/models" if base.endswith("/v1") else "/v1/models")

    @staticmethod
    def _catalog_item(raw_model_id, *, fcc_proxy):
        model_id = str(raw_model_id or "").strip()
        if not model_id:
            return None
        reasoning_mode = "provider_default"
        if fcc_proxy:
            if model_id.startswith(FCC_DIRECT_PREFIX):
                upstream_id = model_id[len(FCC_DIRECT_PREFIX):]
            elif model_id.startswith(FCC_NO_THINKING_PREFIX):
                upstream_id = model_id[len(FCC_NO_THINKING_PREFIX):]
                if upstream_id not in FCC_NOTE_OPTIMIZED_MODELS:
                    return None
                reasoning_mode = "off"
            else:
                return None
        else:
            upstream_id = model_id
        if "/" not in upstream_id:
            return None
        if upstream_id in NVIDIA_EOL_MODELS:
            return None
        publisher = upstream_id.split("/", 1)[0]
        label = upstream_id
        if reasoning_mode == "off":
            label += "（关闭深度思考｜适合笔记）"
        return {
            "id": model_id,
            "upstream_id": upstream_id,
            "publisher": publisher,
            "label": label,
            "reasoning_mode": reasoning_mode,
        }

    def list(self, profile):
        parsed = urlparse(profile["api_base"])
        fcc_proxy = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        request = urllib.request.Request(
            self._endpoint(profile),
            headers={
                "Authorization": f"Bearer {profile['api_key']}",
                "x-api-key": profile["api_key"],
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
                context=LLMConnectionVerifier._ssl_context(),
            ) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            message = (
                "无法读取模型列表：API 密钥无效。"
                if exc.code in (401, 403)
                else f"模型目录暂时不可用（HTTP {exc.code}）。"
            )
            raise DomainError(
                "LLM_MODEL_CATALOG_FAILED", message, retryable=exc.code >= 500
            ) from exc
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            raise DomainError(
                "LLM_MODEL_CATALOG_FAILED",
                "暂时无法连接模型目录，请确认本地 NVIDIA 代理正在运行。",
                retryable=True,
            ) from exc
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise DomainError(
                "LLM_MODEL_CATALOG_FAILED",
                "模型目录返回了无法识别的数据。",
                retryable=False,
            ) from exc

        raw_items = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(raw_items, list):
            raise DomainError(
                "LLM_MODEL_CATALOG_FAILED",
                "模型目录没有返回模型列表。",
                retryable=False,
            )
        models = []
        seen = set()
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            item = self._catalog_item(raw_item.get("id"), fcc_proxy=fcc_proxy)
            if item and item["id"] not in seen:
                seen.add(item["id"])
                models.append(item)
        models.sort(key=lambda item: (item["publisher"], item["upstream_id"]))
        return models


class LLMConnectionVerifier:
    def __init__(self, *, timeout_seconds=30):
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _ssl_context():
        try:
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()

    def verify(self, profile):
        request = llm_request(
            profile,
            "Reply with OK.",
            max_tokens=8,
            temperature=0,
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
                context=self._ssl_context(),
            ) as response:
                payload = json.load(response)
            llm_response_text(profile, payload)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                message = "API 密钥无效，或没有当前模型的调用权限。"
                retryable = False
            elif exc.code == 429:
                message = "服务商返回额度不足或请求过于频繁。"
                retryable = True
            elif exc.code == 410:
                message = "这个模型已经被服务商下线，请从模型列表中选择其他模型。"
                retryable = False
            else:
                message = f"模型连接测试失败（HTTP {exc.code}）。"
                retryable = exc.code >= 500
            raise DomainError("LLM_VERIFY_FAILED", message, retryable=retryable) from exc
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            raise DomainError(
                "LLM_VERIFY_FAILED",
                "暂时无法连接该模型服务，请检查 API 地址。",
                retryable=True,
            ) from exc
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise DomainError(
                "LLM_VERIFY_FAILED",
                "服务已响应，但返回格式与所选接口协议不一致。",
                retryable=False,
            ) from exc
        return {
            "requested_model": profile["model"],
            "response_model": str(payload.get("model") or "").strip(),
        }


class LLMProviderStore:
    def __init__(self, path, *, default_enabled=False):
        self.path = Path(path)
        self.default_enabled = bool(default_enabled)

    @staticmethod
    def _legacy_label(data):
        combined = " ".join(
            str(data.get(key) or "") for key in ("api_base", "model")
        ).lower()
        return "DeepSeek" if "deepseek" in combined else "现有 LLM 配置"

    def _empty(self):
        return {
            "version": 3,
            "notes_enabled": self.default_enabled,
            "active_channel": "paid",
            "channels": {
                "free": {"enabled": False, "default_profile_id": ""},
                "paid": {"enabled": True, "default_profile_id": ""},
            },
            "profiles": [],
        }

    @staticmethod
    def _normalized_profile(profile, *, default_channel="paid"):
        result = dict(profile)
        result["channel"] = (
            result.get("channel")
            if result.get("channel") in LLM_CHANNELS
            else default_channel
        )
        result["protocol"] = (
            result.get("protocol")
            if result.get("protocol") in LLM_PROTOCOLS
            else "openai_chat"
        )
        result["enabled"] = bool(result.get("enabled", True))
        return result

    def _normalized_v3(self, data):
        result = self._empty()
        result["notes_enabled"] = bool(data.get("notes_enabled"))
        result["active_channel"] = (
            data.get("active_channel")
            if data.get("active_channel") in LLM_CHANNELS
            else "paid"
        )
        raw_channels = data.get("channels") if isinstance(data.get("channels"), dict) else {}
        for channel in LLM_CHANNELS:
            raw = raw_channels.get(channel) if isinstance(raw_channels.get(channel), dict) else {}
            result["channels"][channel] = {
                "enabled": bool(raw.get("enabled", channel == "paid")),
                "default_profile_id": str(raw.get("default_profile_id") or ""),
            }
        result["profiles"] = [
            self._normalized_profile(profile)
            for profile in data.get("profiles") or []
            if isinstance(profile, dict)
        ]
        return result

    def _migrate_v2(self, data):
        active_id = str(data.get("active_profile_id") or "")
        migrated = self._empty()
        migrated["notes_enabled"] = bool(data.get("notes_enabled"))
        migrated["channels"]["paid"]["default_profile_id"] = active_id
        migrated["profiles"] = [
            self._normalized_profile(profile, default_channel="paid")
            for profile in data.get("profiles") or []
            if isinstance(profile, dict)
        ]
        self._write(migrated)
        return migrated

    def _read(self):
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DomainError(
                "LLM_CONFIG_INVALID",
                "LLM 配置文件损坏，请先修复配置。",
                retryable=False,
            ) from exc
        if not isinstance(data, dict):
            raise DomainError(
                "LLM_CONFIG_INVALID",
                "LLM 配置文件格式无效。",
                retryable=False,
            )
        if data.get("version") == 3 and isinstance(data.get("profiles"), list):
            return self._normalized_v3(data)
        if data.get("version") == 2 and isinstance(data.get("profiles"), list):
            return self._migrate_v2(data)
        if data.get("api_base") or data.get("api_key") or data.get("model"):
            now = utc_now()
            migrated = self._empty()
            migrated["channels"]["paid"]["default_profile_id"] = "legacy-default"
            migrated["profiles"] = [
                {
                    "id": "legacy-default",
                    "label": self._legacy_label(data),
                    "api_base": str(data.get("api_base") or "").strip(),
                    "api_key": str(data.get("api_key") or "").strip(),
                    "model": str(data.get("model") or "deepseek-v4-pro").strip(),
                    "channel": "paid",
                    "protocol": "openai_chat",
                    "enabled": True,
                    "created_at": now,
                    "updated_at": now,
                    "verified_at": None,
                }
            ]
            self._write(migrated)
            return migrated
        return self._empty()

    def _write(self, data):
        data = self._normalized_v3(data)
        active_channel = data["active_channel"]
        active_id = data["channels"][active_channel]["default_profile_id"]
        active = next(
            (profile for profile in data["profiles"] if profile.get("id") == active_id),
            None,
        )
        data["active_profile_id"] = active_id if active else ""
        if active:
            data["api_base"] = active.get("api_base", "")
            data["api_key"] = active.get("api_key", "")
            data["model"] = active.get("model", "")
        else:
            for key in ("api_base", "api_key", "model"):
                data.pop(key, None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            delete=False,
        )
        temporary_path = Path(handle.name)
        try:
            with handle:
                json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def _profile_view(profile, data):
        channel = profile["channel"]
        channel_default = data["channels"][channel]["default_profile_id"] == profile["id"]
        active = channel == data["active_channel"] and channel_default
        return {
            "id": profile["id"],
            "label": profile["label"],
            "api_base": profile["api_base"],
            "model": profile["model"],
            "channel": channel,
            "protocol": profile["protocol"],
            "enabled": bool(profile.get("enabled", True)),
            "api_key_saved": bool(profile.get("api_key")),
            "channel_default": channel_default,
            "active": active,
            "created_at": profile.get("created_at"),
            "updated_at": profile.get("updated_at"),
            "verified_at": profile.get("verified_at"),
        }

    def status(self):
        data = self._read()
        profiles = [self._profile_view(profile, data) for profile in data["profiles"]]
        channel_views = {}
        for channel in LLM_CHANNELS:
            config = data["channels"][channel]
            channel_profiles = [item for item in profiles if item["channel"] == channel]
            default_profile = next(
                (item for item in channel_profiles if item["channel_default"]), None
            )
            channel_views[channel] = {
                "id": channel,
                "label": "免费线路" if channel == "free" else "高速线路",
                "enabled": bool(config["enabled"]),
                "default_profile_id": default_profile["id"] if default_profile else "",
                "default_profile": default_profile,
                "available_profile_count": len(
                    [item for item in channel_profiles if item["enabled"]]
                ),
                "profile_count": len(channel_profiles),
            }
        active_channel = data["active_channel"]
        active_profile = channel_views[active_channel]["default_profile"]
        route_ready = bool(
            channel_views[active_channel]["enabled"]
            and active_profile
            and active_profile["enabled"]
        )
        return {
            "notes_enabled": bool(data["notes_enabled"]) and route_ready,
            "notes_master_enabled": bool(data["notes_enabled"]),
            "route_ready": route_ready,
            "active_channel": active_channel,
            "channels": channel_views,
            "active_profile_id": active_profile["id"] if active_profile else "",
            "active_profile": active_profile,
            "profiles": profiles,
        }

    def is_enabled(self):
        return self.status()["notes_enabled"]

    def active_profile_id(self):
        status = self.status()
        return status["active_profile_id"] if status["route_ready"] else None

    def credentials(self, profile_id=None):
        data = self._read()
        if profile_id:
            selected_id = profile_id
        else:
            channel = data["active_channel"]
            selected_id = data["channels"][channel]["default_profile_id"]
        profile = next(
            (item for item in data["profiles"] if item.get("id") == selected_id),
            None,
        )
        if not profile or not profile.get("api_key") or not profile.get("api_base"):
            raise DomainError(
                "LLM_NOT_CONFIGURED",
                "请先配置并选择 AI 服务。",
                retryable=False,
            )
        return dict(profile)

    @staticmethod
    def _validated_api_base(value):
        value = str(value or "").strip().rstrip("/")
        parsed = urlparse(value)
        local_http = parsed.scheme == "http" and parsed.hostname in {
            "127.0.0.1", "localhost", "::1"
        }
        if (
            parsed.scheme not in {"https", "http"}
            or (parsed.scheme == "http" and not local_http)
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise DomainError(
                "LLM_API_BASE_INVALID",
                "API 地址必须使用 HTTPS；只有本机代理允许使用 HTTP localhost 地址。",
                retryable=False,
            )
        return value

    def save_profile(
        self,
        *,
        label,
        api_base,
        api_key,
        model,
        channel="paid",
        protocol="openai_chat",
        enabled=True,
        profile_id=None,
    ):
        if channel not in LLM_CHANNELS:
            raise DomainError("LLM_CHANNEL_INVALID", "请选择有效的模型线路。")
        if protocol not in LLM_PROTOCOLS:
            raise DomainError("LLM_PROTOCOL_INVALID", "请选择有效的接口协议。")
        data = self._read()
        profiles = data["profiles"]
        existing = next(
            (profile for profile in profiles if profile.get("id") == profile_id),
            None,
        )
        if profile_id and existing is None:
            raise DomainError(
                "LLM_PROFILE_NOT_FOUND", "没有找到这套 LLM 配置。", retryable=False
            )
        api_key = str(api_key or "").strip()
        if existing is None and not api_key:
            raise DomainError(
                "LLM_API_KEY_REQUIRED",
                "首次保存该服务时必须填写 API 密钥。",
                retryable=False,
            )
        now = utc_now()
        normalized_base = self._validated_api_base(api_base)
        normalized_model = str(model or "").strip()
        profile = {
            "id": existing["id"] if existing else str(uuid.uuid4()),
            "label": str(label or "").strip(),
            "api_base": normalized_base,
            "api_key": api_key or (existing.get("api_key", "") if existing else ""),
            "model": normalized_model,
            "channel": channel,
            "protocol": protocol,
            "enabled": bool(enabled),
            "created_at": existing.get("created_at") if existing else now,
            "updated_at": now,
            "verified_at": (
                existing.get("verified_at")
                if existing
                and existing.get("api_base") == normalized_base
                and existing.get("model") == normalized_model
                and existing.get("protocol", "openai_chat") == protocol
                and not api_key
                else None
            ),
        }
        old_channel = existing.get("channel", "paid") if existing else None
        if existing:
            profiles[profiles.index(existing)] = profile
            if old_channel != channel and data["channels"][old_channel]["default_profile_id"] == profile["id"]:
                data["channels"][old_channel]["default_profile_id"] = ""
        else:
            profiles.append(profile)
        if not data["channels"][channel]["default_profile_id"]:
            data["channels"][channel]["default_profile_id"] = profile["id"]
        data["profiles"] = profiles
        self._write(data)
        return self.profile(profile["id"])

    def profile(self, profile_id):
        profile = next(
            (item for item in self.status()["profiles"] if item["id"] == profile_id),
            None,
        )
        if not profile:
            raise DomainError(
                "LLM_PROFILE_NOT_FOUND", "没有找到这套 LLM 配置。", retryable=False
            )
        return profile

    def set_verified_model(self, profile_id, model):
        data = self._read()
        profile = next(
            (item for item in data["profiles"] if item.get("id") == profile_id),
            None,
        )
        if not profile:
            raise DomainError(
                "LLM_PROFILE_NOT_FOUND", "没有找到这套 LLM 配置。", retryable=False
            )
        profile["model"] = str(model or "").strip()
        profile["updated_at"] = utc_now()
        profile["verified_at"] = profile["updated_at"]
        self._write(data)
        return self.profile(profile_id)

    def set_default(self, profile_id):
        profile = self.profile(profile_id)
        if not profile["enabled"]:
            raise DomainError(
                "LLM_PROFILE_DISABLED", "请先开启这套模型配置。", retryable=False
            )
        self.credentials(profile_id)
        data = self._read()
        data["channels"][profile["channel"]]["default_profile_id"] = profile_id
        self._write(data)
        return self.status()

    def activate(self, profile_id):
        profile = self.profile(profile_id)
        self.set_default(profile_id)
        data = self._read()
        data["active_channel"] = profile["channel"]
        self._write(data)
        return self.status()

    def set_active_channel(self, channel):
        if channel not in LLM_CHANNELS:
            raise DomainError("LLM_CHANNEL_INVALID", "请选择有效的模型线路。")
        data = self._read()
        config = data["channels"][channel]
        if not config["enabled"]:
            raise DomainError("LLM_CHANNEL_DISABLED", "请先开启这条线路。", retryable=False)
        profile = self.profile(config["default_profile_id"])
        if not profile["enabled"]:
            raise DomainError(
                "LLM_PROFILE_DISABLED", "该线路的默认模型当前已关闭。", retryable=False
            )
        self.credentials(profile["id"])
        data["active_channel"] = channel
        self._write(data)
        return self.status()

    def set_channel_enabled(self, channel, enabled):
        if channel not in LLM_CHANNELS:
            raise DomainError("LLM_CHANNEL_INVALID", "请选择有效的模型线路。")
        data = self._read()
        if enabled:
            profile_id = data["channels"][channel]["default_profile_id"]
            profile = self.profile(profile_id)
            if not profile["enabled"]:
                raise DomainError(
                    "LLM_PROFILE_DISABLED", "请先开启该线路的默认模型。", retryable=False
                )
            self.credentials(profile_id)
        data["channels"][channel]["enabled"] = bool(enabled)
        self._write(data)
        return self.status()

    def set_profile_enabled(self, profile_id, enabled):
        data = self._read()
        profile = next(
            (item for item in data["profiles"] if item.get("id") == profile_id), None
        )
        if not profile:
            raise DomainError(
                "LLM_PROFILE_NOT_FOUND", "没有找到这套 LLM 配置。", retryable=False
            )
        if enabled:
            self.credentials(profile_id)
        profile["enabled"] = bool(enabled)
        profile["updated_at"] = utc_now()
        self._write(data)
        return self.status()

    def set_enabled(self, enabled):
        data = self._read()
        if enabled:
            status = self.status()
            if not status["route_ready"]:
                raise DomainError(
                    "LLM_ROUTE_NOT_READY",
                    "当前线路没有已开启的默认模型。",
                    retryable=False,
                )
            self.credentials(status["active_profile_id"])
        data["notes_enabled"] = bool(enabled)
        self._write(data)
        return self.status()

    def delete(self, profile_id):
        data = self._read()
        profiles = data["profiles"]
        target = next((item for item in profiles if item.get("id") == profile_id), None)
        if not target:
            raise DomainError(
                "LLM_PROFILE_NOT_FOUND", "没有找到这套 LLM 配置。", retryable=False
            )
        data["profiles"] = [item for item in profiles if item.get("id") != profile_id]
        channel = target["channel"]
        if data["channels"][channel]["default_profile_id"] == profile_id:
            data["channels"][channel]["default_profile_id"] = ""
            if data["active_channel"] == channel:
                data["notes_enabled"] = False
        self._write(data)
        return self.status()

    def mark_verified(self, profile_id):
        data = self._read()
        profile = next(
            (item for item in data["profiles"] if item.get("id") == profile_id), None
        )
        if not profile:
            raise DomainError(
                "LLM_PROFILE_NOT_FOUND", "没有找到这套 LLM 配置。", retryable=False
            )
        profile["verified_at"] = utc_now()
        profile["updated_at"] = utc_now()
        self._write(data)
        return self.profile(profile_id)
