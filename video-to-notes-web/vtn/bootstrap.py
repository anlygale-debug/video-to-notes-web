import os
import threading
from pathlib import Path

from vtn.adapters.llm import FakeLLM, OpenAICompatibleLLM
from vtn.adapters.media import FakePlatformMedia, YtDlpPlatformMedia
from vtn.adapters.transcription import (
    CloudflareTranscriber,
    FakeTranscriber,
    FasterWhisperTranscriber,
    SwitchableTranscriber,
    WhisperTranscriber,
)
from vtn.documents.notes import NoteDocument
from vtn.domain.errors import DomainError
from vtn.exports.exporter import Exporter
from vtn.storage.sqlite import SQLiteRepository
from vtn.web.api import create_v3_router
from vtn.workflows.notes import NoteWorkflow
from vtn.workflows.parser import ParserWorkflow
from vtn.access import AccessManager, install_access_middleware
from vtn.transcription_provider import TranscriptionProviderStore
from vtn.llm_provider import LLMProviderStore


def build_transcriber(env=None, *, provider_store=None):
    env = os.environ if env is None else env
    if provider_store is not None:
        local = FasterWhisperTranscriber(env.get("VTN_WHISPER_MODEL") or "tiny")
        initial_prompt = (env.get("VTN_TRANSCRIPTION_PROMPT") or "").strip()
        return SwitchableTranscriber(
            provider_store,
            local,
            cloudflare_factory=lambda account_id, api_token: CloudflareTranscriber(
                account_id,
                api_token,
                initial_prompt=initial_prompt,
            ),
        )
    provider = (env.get("VTN_TRANSCRIBER") or "local").strip().lower()
    if provider in ("local", "faster-whisper"):
        return FasterWhisperTranscriber(env.get("VTN_WHISPER_MODEL") or "tiny")
    if provider in ("tiny", "whisper"):
        return WhisperTranscriber(env.get("VTN_WHISPER_MODEL") or "tiny")
    if provider == "cloudflare":
        account_id = (env.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
        api_token = (env.get("CLOUDFLARE_API_TOKEN") or "").strip()
        if not account_id or not api_token:
            raise DomainError(
                "TRANSCRIPTION_CONFIG_MISSING",
                "Cloudflare 转录需要账户 ID 和 API Token。",
                retryable=False,
            )
        return CloudflareTranscriber(
            account_id,
            api_token,
            initial_prompt=(env.get("VTN_TRANSCRIPTION_PROMPT") or "").strip(),
        )
    raise DomainError(
        "TRANSCRIPTION_CONFIG_INVALID",
        f"不支持的转录方式：{provider}",
        retryable=False,
    )


def mount_v3(app, base_path):
    base = Path(base_path)
    database_path = Path(os.environ.get("VTN_DATABASE_PATH", base / "data" / "vtn.sqlite3"))
    repository = SQLiteRepository(database_path)
    repository.migrate()
    repository.recover_interrupted_tasks()
    paid_calls_enabled = os.environ.get("VTN_PAID_CALLS_ENABLED", "1") != "0"
    llm_store = LLMProviderStore(
        Path(
            os.environ.get(
                "VTN_LLM_PROVIDER_PATH",
                base / "data" / "settings.json",
            )
        ),
        default_enabled=paid_calls_enabled,
    )
    access_manager = None
    if os.environ.get("VTN_ACCESS_CONTROL") == "1":
        access_manager = AccessManager(
            repository,
            (os.environ.get("VTN_SESSION_SECRET") or "").strip(),
            secure_cookie=os.environ.get("VTN_COOKIE_SECURE", "1") != "0",
            paid_calls_enabled=paid_calls_enabled,
            paid_calls_status=llm_store.is_enabled,
            parser_calls_enabled=(
                os.environ.get(
                    "VTN_PARSER_CALLS_ENABLED",
                    "1" if paid_calls_enabled else "0",
                )
                != "0"
            ),
        )
    fake_mode = os.environ.get("VTN_FAKE_ADAPTERS") == "1"
    heavy_task_lock = threading.Lock()
    media = FakePlatformMedia() if fake_mode else YtDlpPlatformMedia()
    provider_store = TranscriptionProviderStore(
        Path(
            os.environ.get(
                "VTN_TRANSCRIPTION_PROVIDER_PATH",
                (
                    "/var/lib/video-to-notes/transcription-provider.json"
                    if access_manager is not None
                    else base / "data" / "transcription-provider.json"
                ),
            )
        ),
        local_model_name=os.environ.get("VTN_WHISPER_MODEL", "tiny"),
    )
    transcriber = (
        FakeTranscriber()
        if fake_mode
        else build_transcriber(provider_store=provider_store)
    )
    parser = ParserWorkflow(
        repository, media, transcriber, access_manager=access_manager,
        heavy_task_lock=heavy_task_lock,
    )
    llm = FakeLLM() if fake_mode else OpenAICompatibleLLM(llm_store)
    notes = NoteWorkflow(
        repository, llm, access_manager=access_manager,
        heavy_task_lock=heavy_task_lock,
    )
    document = NoteDocument(repository, llm, heavy_task_lock=heavy_task_lock)
    exporter = Exporter(repository)
    app.include_router(create_v3_router(
        repository, parser, notes, document, exporter, access_manager=access_manager
    ))
    if access_manager is not None:
        install_access_middleware(app, access_manager)
    app.state.vtn_repository = repository
    app.state.parser_workflow = parser
    app.state.note_workflow = notes
    app.state.access_manager = access_manager
    return repository
