import hmac
import html
import io
import json
import os
import secrets
from pathlib import Path

import qrcode
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from qrcode.image.svg import SvgPathImage

from vtn.access import AccessManager
from vtn.domain.errors import DomainError
from vtn.storage.sqlite import SQLiteRepository
from vtn.transcription_provider import (
    CloudflareCredentialVerifier,
    TranscriptionProviderStore,
)
from vtn.llm_provider import LLMConnectionVerifier, LLMProviderStore


class CreateGrantRequest(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    transcription_minutes: int = Field(ge=1, le=1440)
    note_generations: int = Field(ge=1, le=500)
    max_video_minutes: int = Field(ge=1, le=180)

    @field_validator("label")
    @classmethod
    def label_must_contain_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("请输入测试者备注")
        return value


class VerifyGrantCodeRequest(BaseModel):
    invite_code: str = Field(min_length=1, max_length=200)


class EditGrantRequest(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    remaining_transcription_minutes: float = Field(ge=0, le=10080)
    remaining_note_generations: int = Field(ge=0, le=5000)
    max_video_minutes: float = Field(ge=1, le=180)

    @field_validator("label")
    @classmethod
    def label_must_contain_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("请输入测试者备注")
        return value


class CloudflareCredentialsRequest(BaseModel):
    account_id: str = Field(pattern=r"^[0-9a-fA-F]{32}$")
    api_token: str = Field(default="", max_length=512)

    @field_validator("api_token")
    @classmethod
    def token_is_blank_or_complete(cls, value):
        value = value.strip()
        if value and len(value) < 20:
            raise ValueError("Cloudflare API Token 长度不正确")
        return value


class SwitchTranscriptionProviderRequest(BaseModel):
    provider: str = Field(pattern=r"^(local|cloudflare)$")


class LLMProfileRequest(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    api_base: str = Field(min_length=8, max_length=500)
    api_key: str = Field(default="", max_length=2048)
    model: str = Field(min_length=1, max_length=200)
    channel: str = Field(default="paid", pattern=r"^(free|paid)$")
    protocol: str = Field(
        default="openai_chat",
        pattern=r"^(openai_chat|anthropic_messages)$",
    )
    enabled: bool = True

    @field_validator("label", "api_base", "api_key", "model")
    @classmethod
    def strip_text(cls, value):
        return value.strip()


class LLMEnabledRequest(BaseModel):
    enabled: bool


class LLMChannelRequest(BaseModel):
    channel: str = Field(pattern=r"^(free|paid)$")


def _qr_svg(value):
    image = qrcode.make(
        value,
        image_factory=SvgPathImage,
        box_size=8,
        border=2,
    )
    output = io.BytesIO()
    image.save(output)
    return output.getvalue().decode("utf-8")


def _minutes(seconds):
    if seconds is None:
        return None
    return round(seconds / 60, 1)


def _grant_view(repository, manager, access_id):
    row = repository._fetchone(
        "SELECT * FROM access_grants WHERE id=?",
        (access_id,),
    )
    if not row:
        return None
    snapshot = manager.snapshot(access_id)
    adjustment = repository._fetchone(
        "SELECT COUNT(*) AS count,MAX(created_at) AS last_adjusted_at "
        "FROM access_grant_adjustments WHERE access_id=?",
        (access_id,),
    )
    return {
        "id": row["id"],
        "label": row["label"],
        "status": "enabled" if row["enabled"] else "revoked",
        "enabled": bool(row["enabled"]),
        "transcription_minutes_limit": _minutes(
            row["transcription_seconds_limit"]
        ),
        "remaining_transcription_minutes": _minutes(
            snapshot["remaining_transcription_seconds"]
        ),
        "note_generation_limit": row["note_generation_limit"],
        "remaining_note_generations": snapshot["remaining_note_generations"],
        "max_video_minutes": _minutes(row["max_video_seconds"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "adjustment_count": adjustment["count"],
        "last_adjusted_at": adjustment["last_adjusted_at"],
    }


def create_invite_admin_app(
    repository,
    access_manager,
    *,
    csrf_token=None,
    static_dir=None,
    provider_store=None,
    cloudflare_verifier=None,
    llm_store=None,
    llm_verifier=None,
):
    app = FastAPI(
        title="Video to Notes Invite Control",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    token = csrf_token or secrets.token_urlsafe(32)
    provider_store = provider_store or TranscriptionProviderStore(
        Path("data/transcription-provider.json")
    )
    cloudflare_verifier = cloudflare_verifier or CloudflareCredentialVerifier()
    llm_store = llm_store or LLMProviderStore(Path("data/settings.json"))
    llm_verifier = llm_verifier or LLMConnectionVerifier()
    static_dir = Path(static_dir or Path(__file__).parents[1] / "static" / "invite-admin")
    app.mount("/assets", StaticFiles(directory=static_dir), name="invite-admin-assets")

    def require_csrf(x_vtn_admin_csrf: str = Header(default="")):
        if not hmac.compare_digest(x_vtn_admin_csrf, token):
            raise HTTPException(status_code=403, detail="管理会话校验失败，请刷新页面")

    @app.get("/", response_class=HTMLResponse)
    async def admin_page():
        page_path = static_dir / "index.html"
        if page_path.exists():
            source = page_path.read_text(encoding="utf-8")
        else:
            source = (
                "<!doctype html><html lang='zh-CN'><head>"
                '<meta name="vtn-admin-csrf" content="__VTN_ADMIN_CSRF__">'
                "<title>内测码控制台</title></head><body>内测码控制台</body></html>"
            )
        return source.replace("__VTN_ADMIN_CSRF__", html.escape(token, quote=True))

    @app.get("/api/grants")
    async def list_grants(_=Depends(require_csrf)):
        rows = repository._fetchall(
            "SELECT id FROM access_grants ORDER BY created_at DESC, id DESC"
        )
        return {"items": [_grant_view(repository, access_manager, row["id"]) for row in rows]}

    @app.get("/api/transcription-provider")
    async def transcription_provider_status(_=Depends(require_csrf)):
        return provider_store.status()

    @app.get("/api/llm-providers")
    async def llm_provider_status(_=Depends(require_csrf)):
        return llm_store.status()

    @app.post("/api/llm-providers", status_code=201)
    async def create_llm_profile(
        body: LLMProfileRequest,
        _=Depends(require_csrf),
    ):
        try:
            profile = llm_store.save_profile(**body.model_dump())
            return {"profile": profile, **llm_store.status()}
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc

    @app.put("/api/llm-providers/notes-enabled")
    async def set_llm_enabled(
        body: LLMEnabledRequest,
        _=Depends(require_csrf),
    ):
        try:
            return llm_store.set_enabled(body.enabled)
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc

    @app.put("/api/llm-providers/active-channel")
    async def set_llm_active_channel(
        body: LLMChannelRequest,
        _=Depends(require_csrf),
    ):
        try:
            return llm_store.set_active_channel(body.channel)
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc

    @app.put("/api/llm-providers/channels/{channel}/enabled")
    async def set_llm_channel_enabled(
        channel: str,
        body: LLMEnabledRequest,
        _=Depends(require_csrf),
    ):
        try:
            return llm_store.set_channel_enabled(channel, body.enabled)
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc

    @app.put("/api/llm-providers/{profile_id}")
    async def edit_llm_profile(
        profile_id: str,
        body: LLMProfileRequest,
        _=Depends(require_csrf),
    ):
        try:
            profile = llm_store.save_profile(
                profile_id=profile_id,
                **body.model_dump(),
            )
            return {"profile": profile, **llm_store.status()}
        except DomainError as exc:
            status_code = 404 if exc.code == "LLM_PROFILE_NOT_FOUND" else 422
            raise HTTPException(status_code=status_code, detail=exc.message) from exc

    @app.post("/api/llm-providers/{profile_id}/activate")
    async def activate_llm_profile(profile_id: str, _=Depends(require_csrf)):
        try:
            return llm_store.activate(profile_id)
        except DomainError as exc:
            status_code = 404 if exc.code == "LLM_PROFILE_NOT_FOUND" else 422
            raise HTTPException(status_code=status_code, detail=exc.message) from exc

    @app.post("/api/llm-providers/{profile_id}/default")
    async def set_default_llm_profile(profile_id: str, _=Depends(require_csrf)):
        try:
            return llm_store.set_default(profile_id)
        except DomainError as exc:
            status_code = 404 if exc.code == "LLM_PROFILE_NOT_FOUND" else 422
            raise HTTPException(status_code=status_code, detail=exc.message) from exc

    @app.put("/api/llm-providers/{profile_id}/enabled")
    async def set_llm_profile_enabled(
        profile_id: str,
        body: LLMEnabledRequest,
        _=Depends(require_csrf),
    ):
        try:
            return llm_store.set_profile_enabled(profile_id, body.enabled)
        except DomainError as exc:
            status_code = 404 if exc.code == "LLM_PROFILE_NOT_FOUND" else 422
            raise HTTPException(status_code=status_code, detail=exc.message) from exc

    @app.post("/api/llm-providers/{profile_id}/test")
    async def test_llm_profile(profile_id: str, _=Depends(require_csrf)):
        try:
            llm_verifier.verify(llm_store.credentials(profile_id))
            profile = llm_store.mark_verified(profile_id)
            return {"profile": profile, **llm_store.status()}
        except DomainError as exc:
            status_code = 503 if exc.retryable else 422
            raise HTTPException(status_code=status_code, detail=exc.message) from exc

    @app.delete("/api/llm-providers/{profile_id}")
    async def delete_llm_profile(profile_id: str, _=Depends(require_csrf)):
        try:
            return llm_store.delete(profile_id)
        except DomainError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc

    @app.put("/api/transcription-provider/cloudflare")
    async def save_cloudflare_credentials(
        body: CloudflareCredentialsRequest,
        _=Depends(require_csrf),
    ):
        try:
            api_token = body.api_token
            if not api_token:
                credentials = provider_store.cloudflare_credentials()
                if not credentials:
                    raise DomainError(
                        "CLOUDFLARE_TOKEN_REQUIRED",
                        "首次配置 Cloudflare 时必须填写 API Token。",
                        retryable=False,
                    )
                api_token = credentials[1]
            cloudflare_verifier.verify(body.account_id, api_token)
            return provider_store.save_cloudflare(body.account_id, api_token)
        except DomainError as exc:
            raise HTTPException(
                status_code=503 if exc.retryable else 422,
                detail=exc.message,
            ) from exc

    @app.post("/api/transcription-provider/switch")
    async def switch_transcription_provider(
        body: SwitchTranscriptionProviderRequest,
        _=Depends(require_csrf),
    ):
        try:
            if body.provider == "cloudflare":
                credentials = provider_store.cloudflare_credentials()
                if not credentials:
                    raise DomainError(
                        "CLOUDFLARE_NOT_CONFIGURED",
                        "请先保存并验证 Cloudflare Account ID 与 API Token。",
                        retryable=False,
                    )
                cloudflare_verifier.verify(*credentials)
            return provider_store.activate(body.provider)
        except DomainError as exc:
            raise HTTPException(
                status_code=503 if exc.retryable else 422,
                detail=exc.message,
            ) from exc

    @app.delete("/api/transcription-provider/cloudflare")
    async def delete_cloudflare_credentials(_=Depends(require_csrf)):
        return provider_store.delete_cloudflare()

    @app.post("/api/grants", status_code=201)
    async def create_grant(
        body: CreateGrantRequest,
        _=Depends(require_csrf),
    ):
        created = access_manager.create_grant(
            body.label,
            transcription_seconds_limit=body.transcription_minutes * 60,
            note_generation_limit=body.note_generations,
            max_video_seconds=body.max_video_minutes * 60,
        )
        return {
            "grant": _grant_view(repository, access_manager, created["id"]),
            "invite_code": created["code"],
            "qr_svg": _qr_svg(created["code"]),
        }

    @app.delete("/api/grants/{access_id}")
    async def revoke_grant(access_id: str, _=Depends(require_csrf)):
        if not access_manager.revoke(access_id):
            raise HTTPException(status_code=404, detail="未找到该内测资格")
        return {"grant": _grant_view(repository, access_manager, access_id)}

    @app.patch("/api/grants/{access_id}")
    async def edit_grant(
        access_id: str,
        body: EditGrantRequest,
        _=Depends(require_csrf),
    ):
        snapshot = access_manager.adjust_grant(
            access_id,
            label=body.label,
            remaining_transcription_seconds=round(
                body.remaining_transcription_minutes * 60
            ),
            remaining_note_generations=body.remaining_note_generations,
            max_video_seconds=round(body.max_video_minutes * 60),
        )
        if not snapshot:
            raise HTTPException(status_code=404, detail="未找到可修改的内测资格")
        warnings = []
        if body.max_video_minutes > body.remaining_transcription_minutes:
            warnings.append("单视频上限高于剩余转录额度，请同时补充转录额度。")
        return {
            "grant": _grant_view(repository, access_manager, access_id),
            "warnings": warnings,
        }

    @app.get("/api/grants/{access_id}/adjustments")
    async def list_grant_adjustments(
        access_id: str,
        _=Depends(require_csrf),
    ):
        if not _grant_view(repository, access_manager, access_id):
            raise HTTPException(status_code=404, detail="未找到该内测资格")
        rows = repository._fetchall(
            "SELECT id,previous_json,next_json,created_at "
            "FROM access_grant_adjustments WHERE access_id=? "
            "ORDER BY created_at DESC,id DESC",
            (access_id,),
        )
        return {
            "items": [
                {
                    "id": row["id"],
                    "previous": json.loads(row["previous_json"]),
                    "next": json.loads(row["next_json"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
        }

    @app.post("/api/grants/{access_id}/verify-code")
    async def verify_grant_code(
        access_id: str,
        body: VerifyGrantCodeRequest,
        _=Depends(require_csrf),
    ):
        grant = access_manager.authenticate(body.invite_code)
        if not grant or grant["id"] != access_id:
            raise HTTPException(status_code=422, detail="内测码与该资格不匹配")
        return {"verified": True}

    return app


def create_invite_admin_app_from_environment(base_dir=None):
    database_path = Path(os.environ.get("VTN_DATABASE_PATH", "data/vtn.sqlite3"))
    session_secret = (os.environ.get("VTN_SESSION_SECRET") or "").strip()
    if not session_secret:
        raise RuntimeError("VTN_SESSION_SECRET 未配置")
    repository = SQLiteRepository(database_path)
    repository.migrate()
    base = Path(base_dir or Path(__file__).parents[1])
    app = create_invite_admin_app(
        repository,
        AccessManager(repository, session_secret),
        static_dir=base / "static" / "invite-admin",
        provider_store=TranscriptionProviderStore(
            Path(
                os.environ.get(
                    "VTN_TRANSCRIPTION_PROVIDER_PATH",
                    "/var/lib/video-to-notes/transcription-provider.json",
                )
            ),
            local_model_name=os.environ.get("VTN_WHISPER_MODEL", "tiny"),
        ),
        llm_store=LLMProviderStore(
            Path(
                os.environ.get(
                    "VTN_LLM_PROVIDER_PATH",
                    base / "data" / "settings.json",
                )
            ),
            default_enabled=(
                os.environ.get("VTN_PAID_CALLS_ENABLED", "1") != "0"
            ),
        ),
    )

    @app.on_event("shutdown")
    async def close_repository():
        repository.close()

    return app
