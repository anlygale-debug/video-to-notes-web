import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from vtn.domain.errors import DomainError
from vtn.domain.models import utc_now


class CloudflareCredentialVerifier:
    def __init__(self, *, timeout_seconds=20):
        self.timeout_seconds = timeout_seconds

    def verify(self, account_id, api_token):
        query = urllib.parse.urlencode(
            {"search": "@cf/openai/whisper-large-v3-turbo", "per_page": 1}
        )
        request = urllib.request.Request(
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{account_id}/ai/models/search?{query}",
            headers={"Authorization": f"Bearer {api_token}"},
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 404):
                raise DomainError(
                    "CLOUDFLARE_AUTH_FAILED",
                    "Cloudflare Account ID、Token 或 Workers AI 权限无效。",
                    retryable=False,
                ) from exc
            raise DomainError(
                "CLOUDFLARE_VERIFY_FAILED",
                f"Cloudflare 验证暂时失败（HTTP {exc.code}）。",
                retryable=True,
            ) from exc
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            raise DomainError(
                "CLOUDFLARE_VERIFY_FAILED",
                "暂时无法连接 Cloudflare，请稍后重试。",
                retryable=True,
            ) from exc
        if not payload.get("success"):
            raise DomainError(
                "CLOUDFLARE_AUTH_FAILED",
                "Cloudflare Account ID、Token 或 Workers AI 权限无效。",
                retryable=False,
            )


class TranscriptionProviderStore:
    DAILY_FREE_NEURONS = 10_000
    WHISPER_NEURONS_PER_MINUTE = 46.63

    def __init__(self, path, *, local_model_name="tiny"):
        self.path = Path(path)
        self.local_model_name = str(local_model_name)

    def _read(self):
        if not self.path.exists():
            return {
                "active_provider": "local",
                "cloudflare": {},
                "usage_seconds_by_utc_date": {},
            }
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DomainError(
                "TRANSCRIPTION_CONFIG_INVALID",
                "转录服务配置文件损坏，请先恢复本地转录。",
                retryable=False,
            ) from exc
        if not isinstance(data, dict):
            raise DomainError(
                "TRANSCRIPTION_CONFIG_INVALID",
                "转录服务配置文件格式无效。",
                retryable=False,
            )
        return data

    def _write(self, data):
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

    def save_cloudflare(self, account_id, api_token):
        data = self._read()
        data["cloudflare"] = {
            "account_id": account_id,
            "api_token": api_token,
            "verified_at": utc_now(),
        }
        self._write(data)
        return self.status()

    def cloudflare_credentials(self):
        cloudflare = self._read().get("cloudflare") or {}
        account_id = str(cloudflare.get("account_id") or "")
        api_token = str(cloudflare.get("api_token") or "")
        return (account_id, api_token) if account_id and api_token else None

    def activate(self, provider):
        if provider not in {"local", "cloudflare"}:
            raise DomainError(
                "TRANSCRIPTION_PROVIDER_INVALID",
                "请选择本地 tiny 或 Cloudflare API。",
                retryable=False,
            )
        data = self._read()
        if provider == "cloudflare" and not self.cloudflare_credentials():
            raise DomainError(
                "CLOUDFLARE_NOT_CONFIGURED",
                "请先保存并验证 Cloudflare Account ID 与 API Token。",
                retryable=False,
            )
        data["active_provider"] = provider
        self._write(data)
        return self.status()

    def delete_cloudflare(self):
        data = self._read()
        data["active_provider"] = "local"
        data["cloudflare"] = {}
        self._write(data)
        return self.status()

    def record_cloudflare_usage(self, duration_seconds):
        duration_seconds = max(0.0, float(duration_seconds or 0))
        if not duration_seconds:
            return self.status()
        data = self._read()
        today = datetime.now(timezone.utc).date().isoformat()
        usage = data.get("usage_seconds_by_utc_date")
        if not isinstance(usage, dict):
            usage = {}
        usage[today] = round(float(usage.get(today) or 0) + duration_seconds, 3)
        data["usage_seconds_by_utc_date"] = {
            date: seconds
            for date, seconds in usage.items()
            if date >= (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()
        }
        self._write(data)
        return self.status()

    def status(self):
        data = self._read()
        cloudflare = data.get("cloudflare") or {}
        configured = bool(
            cloudflare.get("account_id") and cloudflare.get("api_token")
        )
        now = datetime.now(timezone.utc)
        today = now.date().isoformat()
        usage_by_date = data.get("usage_seconds_by_utc_date") or {}
        today_seconds = max(0.0, float(usage_by_date.get(today) or 0))
        today_minutes = today_seconds / 60
        estimated_used_neurons = (
            today_minutes * self.WHISPER_NEURONS_PER_MINUTE
        )
        estimated_remaining_neurons = max(
            0.0,
            self.DAILY_FREE_NEURONS - estimated_used_neurons,
        )
        reset_at = datetime.combine(
            now.date() + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        return {
            "active_provider": (
                data.get("active_provider")
                if data.get("active_provider") in {"local", "cloudflare"}
                else "local"
            ),
            "local": {
                "configured": True,
                "model_name": self.local_model_name,
            },
            "cloudflare": {
                "configured": configured,
                "token_saved": bool(cloudflare.get("api_token")),
                "account_id": str(cloudflare.get("account_id") or ""),
                "verified_at": cloudflare.get("verified_at"),
                "model_name": "@cf/openai/whisper-large-v3-turbo",
            },
            "usage": {
                "daily_free_neurons": self.DAILY_FREE_NEURONS,
                "model_neurons_per_minute": self.WHISPER_NEURONS_PER_MINUTE,
                "source": "local_estimate",
                "scope": "this_app_only",
                "today_transcription_minutes": round(today_minutes, 2),
                "estimated_used_neurons": round(estimated_used_neurons, 2),
                "estimated_remaining_free_neurons": round(
                    estimated_remaining_neurons,
                    2,
                ),
                "estimated_remaining_free_minutes": round(
                    estimated_remaining_neurons
                    / self.WHISPER_NEURONS_PER_MINUTE,
                    2,
                ),
                "reset_at_utc": reset_at.isoformat().replace("+00:00", "Z"),
            },
        }
