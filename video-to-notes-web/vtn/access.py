import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from vtn.domain.errors import DomainError
from vtn.domain.models import utc_now


SESSION_COOKIE = "vtn_session"
PUBLIC_API_PATHS = {
    "/api/v3/access/login",
    "/api/v3/access/logout",
    "/api/v3/access/status",
    "/api/v3/capabilities",
    "/api/health",
}
DISABLED_HOSTED_PATHS = {
    "/api/proxy-image",
    "/api/search",
    "/api/process",
    "/api/export-pdf",
    "/api/settings",
    "/api/test-connection",
    "/api/v3/migrations/browser-history",
}


def _b64encode(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class AccessManager:
    def __init__(
        self, repository, session_secret, *, secure_cookie=True, session_days=30,
        paid_calls_enabled=True, parser_calls_enabled=None, paid_calls_status=None,
    ):
        if not session_secret:
            raise ValueError("VTN_SESSION_SECRET is required when access control is enabled")
        self.repository = repository
        self.secret = session_secret.encode("utf-8")
        self.secure_cookie = secure_cookie
        self.session_seconds = int(session_days * 86400)
        self.paid_calls_enabled = paid_calls_enabled
        self.paid_calls_status = paid_calls_status
        self.parser_calls_enabled = (
            paid_calls_enabled
            if parser_calls_enabled is None
            else parser_calls_enabled
        )

    def _lookup(self, code):
        return hmac.new(self.secret, code.strip().encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _hash_code(code, salt=None):
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.scrypt(
            code.strip().encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
        )
        return f"{_b64encode(salt)}.{_b64encode(digest)}"

    @staticmethod
    def _verify_code(code, encoded):
        try:
            salt_text, expected_text = encoded.split(".", 1)
            candidate = AccessManager._hash_code(code, _b64decode(salt_text)).split(".", 1)[1]
            return hmac.compare_digest(candidate, expected_text)
        except (ValueError, TypeError):
            return False

    def create_grant(
        self, label, *, transcription_seconds_limit=1800, note_generation_limit=5,
        max_video_seconds=1200, expires_at=None, code=None,
    ):
        code = (code or f"VTN-{secrets.token_urlsafe(9)}").strip()
        grant_id = str(uuid.uuid4())
        now = utc_now()
        with self.repository.transaction() as connection:
            connection.execute(
                """INSERT INTO access_grants(
                   id,label,code_lookup,code_hash,enabled,transcription_seconds_limit,
                   note_generation_limit,max_video_seconds,expires_at,created_at,updated_at
                ) VALUES(?,?,?,?,1,?,?,?,?,?,?)""",
                (
                    grant_id, label.strip(), self._lookup(code), self._hash_code(code),
                    transcription_seconds_limit, note_generation_limit, max_video_seconds,
                    expires_at, now, now,
                ),
            )
        return {**self.snapshot(grant_id), "code": code}

    def authenticate(self, code):
        code = str(code or "").strip()
        if not code:
            return None
        row = self.repository._fetchone(
            "SELECT * FROM access_grants WHERE code_lookup=?", (self._lookup(code),)
        )
        if not row or not self._verify_code(code, row["code_hash"]):
            return None
        grant = dict(row)
        if not self._is_active(grant):
            return None
        return grant

    @staticmethod
    def _is_active(grant):
        if not grant or not grant.get("enabled"):
            return False
        expires_at = grant.get("expires_at")
        return not expires_at or expires_at > utc_now()

    def issue_session(self, access_id):
        payload = _b64encode(json.dumps(
            {"access_id": access_id, "exp": int(time.time()) + self.session_seconds},
            separators=(",", ":"),
        ).encode("utf-8"))
        signature = _b64encode(hmac.new(self.secret, payload.encode("ascii"), hashlib.sha256).digest())
        return f"{payload}.{signature}"

    def access_id_from_session(self, token):
        try:
            payload, signature = token.split(".", 1)
            expected = _b64encode(
                hmac.new(self.secret, payload.encode("ascii"), hashlib.sha256).digest()
            )
            if not hmac.compare_digest(signature, expected):
                return None
            data = json.loads(_b64decode(payload))
            if int(data["exp"]) < int(time.time()):
                return None
            grant = self._grant(data["access_id"])
            return grant["id"] if self._is_active(grant) else None
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None

    def _grant(self, access_id):
        row = self.repository._fetchone("SELECT * FROM access_grants WHERE id=?", (access_id,))
        return dict(row) if row else None

    def snapshot(self, access_id):
        grant = self._grant(access_id)
        if not grant:
            return None
        usage_rows = self.repository._fetchall(
            "SELECT kind, COALESCE(SUM(amount), 0) AS amount FROM access_usage "
            "WHERE access_id=? GROUP BY kind",
            (access_id,),
        )
        usage = {row["kind"]: row["amount"] for row in usage_rows}
        transcribed = usage.get("transcription_seconds", 0)
        generated = usage.get("note_generation", 0)
        transcription_limit = grant["transcription_seconds_limit"]
        note_limit = grant["note_generation_limit"]
        return {
            "id": grant["id"],
            "label": grant["label"],
            "expires_at": grant["expires_at"],
            "max_video_seconds": grant["max_video_seconds"],
            "remaining_transcription_seconds": (
                None if transcription_limit is None else max(0, transcription_limit - transcribed)
            ),
            "remaining_note_generations": (
                None if note_limit is None else max(0, note_limit - generated)
            ),
        }

    def ensure_paid_calls_enabled(self):
        enabled = (
            self.paid_calls_status()
            if self.paid_calls_status is not None
            else self.paid_calls_enabled
        )
        if not enabled:
            raise DomainError(
                "PAID_CALLS_PAUSED",
                "真实解析与笔记生成暂时暂停，请稍后再试",
                retryable=True,
            )

    def ensure_parser_calls_enabled(self):
        if not self.parser_calls_enabled:
            raise DomainError(
                "PAID_CALLS_PAUSED",
                "真实解析暂时暂停，请稍后再试",
                retryable=True,
            )

    def consume(self, access_id, kind, reference_id, amount):
        if kind == "transcription_seconds":
            self.ensure_parser_calls_enabled()
        else:
            self.ensure_paid_calls_enabled()
        grant = self._grant(access_id)
        if not self._is_active(grant):
            raise DomainError("ACCESS_REQUIRED", "内测资格无效或已到期")
        if kind == "transcription_seconds" and amount > grant["max_video_seconds"]:
            raise DomainError(
                "VIDEO_TOO_LONG",
                f"当前内测单个视频最长 {grant['max_video_seconds'] // 60} 分钟",
                retryable=False,
            )
        limit_column = {
            "transcription_seconds": "transcription_seconds_limit",
            "note_generation": "note_generation_limit",
        }[kind]
        with self.repository.transaction() as connection:
            existing = connection.execute(
                "SELECT 1 FROM access_usage WHERE access_id=? AND kind=? AND reference_id=?",
                (access_id, kind, reference_id),
            ).fetchone()
            if existing:
                return self.snapshot(access_id)
            used = connection.execute(
                "SELECT COALESCE(SUM(amount),0) AS amount FROM access_usage "
                "WHERE access_id=? AND kind=?",
                (access_id, kind),
            ).fetchone()["amount"]
            limit = grant[limit_column]
            if limit is not None and used + amount > limit:
                code = "TRANSCRIPTION_QUOTA_EXCEEDED" if kind == "transcription_seconds" else "NOTE_QUOTA_EXCEEDED"
                message = "转录分钟额度已用完" if kind == "transcription_seconds" else "笔记生成额度已用完"
                raise DomainError(code, message, retryable=False)
            connection.execute(
                "INSERT INTO access_usage(id,access_id,kind,reference_id,amount,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()), access_id, kind, reference_id, int(amount), utc_now()),
            )
        return self.snapshot(access_id)

    def release(self, access_id, kind, reference_id):
        with self.repository.transaction() as connection:
            connection.execute(
                "DELETE FROM access_usage WHERE access_id=? AND kind=? AND reference_id=?",
                (access_id, kind, reference_id),
            )
        return self.snapshot(access_id)

    def revoke(self, access_id):
        with self.repository.transaction() as connection:
            cursor = connection.execute(
                "UPDATE access_grants SET enabled=0,updated_at=? WHERE id=?",
                (utc_now(), access_id),
            )
        return self.snapshot(access_id) if cursor.rowcount == 1 else None

    def adjust_grant(
        self,
        access_id,
        *,
        label,
        remaining_transcription_seconds,
        remaining_note_generations,
        max_video_seconds,
    ):
        now = utc_now()
        with self.repository.transaction() as connection:
            grant = connection.execute(
                "SELECT * FROM access_grants WHERE id=?",
                (access_id,),
            ).fetchone()
            if not grant or not grant["enabled"]:
                return None
            usage_rows = connection.execute(
                "SELECT kind,COALESCE(SUM(amount),0) AS amount FROM access_usage "
                "WHERE access_id=? GROUP BY kind",
                (access_id,),
            ).fetchall()
            usage = {row["kind"]: row["amount"] for row in usage_rows}
            used_transcription = int(usage.get("transcription_seconds", 0))
            used_notes = int(usage.get("note_generation", 0))
            previous_remaining_seconds = max(
                0, int(grant["transcription_seconds_limit"]) - used_transcription
            )
            previous_remaining_notes = max(
                0, int(grant["note_generation_limit"]) - used_notes
            )
            previous = {
                "label": grant["label"],
                "remaining_transcription_minutes": round(
                    previous_remaining_seconds / 60, 1
                ),
                "remaining_note_generations": previous_remaining_notes,
                "max_video_minutes": round(grant["max_video_seconds"] / 60, 1),
            }
            next_values = {
                "label": label.strip(),
                "remaining_transcription_minutes": round(
                    remaining_transcription_seconds / 60, 1
                ),
                "remaining_note_generations": int(remaining_note_generations),
                "max_video_minutes": round(max_video_seconds / 60, 1),
            }
            connection.execute(
                "UPDATE access_grants SET label=?,transcription_seconds_limit=?,"
                "note_generation_limit=?,max_video_seconds=?,updated_at=? WHERE id=?",
                (
                    next_values["label"],
                    used_transcription + int(remaining_transcription_seconds),
                    used_notes + int(remaining_note_generations),
                    int(max_video_seconds),
                    now,
                    access_id,
                ),
            )
            connection.execute(
                "INSERT INTO access_grant_adjustments("
                "id,access_id,previous_json,next_json,created_at"
                ") VALUES(?,?,?,?,?)",
                (
                    str(uuid.uuid4()),
                    access_id,
                    json.dumps(previous, ensure_ascii=False),
                    json.dumps(next_values, ensure_ascii=False),
                    now,
                ),
            )
        return self.snapshot(access_id)


class AccessMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, manager):
        super().__init__(app)
        self.manager = manager

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api") or path in PUBLIC_API_PATHS:
            return await call_next(request)
        if path in DISABLED_HOSTED_PATHS or path.startswith("/api/download/"):
            return JSONResponse(
                {"error": {"code": "LEGACY_API_DISABLED", "message": "该旧接口未在公网版本开放"}},
                status_code=404,
            )
        access_id = self.manager.access_id_from_session(request.cookies.get(SESSION_COOKIE, ""))
        if not access_id:
            return JSONResponse(
                {"error": {"code": "ACCESS_REQUIRED", "message": "请输入有效内测码后继续"}},
                status_code=401,
            )
        request.state.vtn_access_id = access_id
        return await call_next(request)


def install_access_middleware(app, manager):
    app.add_middleware(AccessMiddleware, manager=manager)
