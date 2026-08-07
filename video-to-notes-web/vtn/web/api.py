import base64
import binascii
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from vtn.adapters.media import detect_platform
from vtn.adapters.images import SafeThumbnailFetcher
from vtn.domain.errors import DomainError
from vtn.access import SESSION_COOKIE


def _error(error: DomainError, status=400):
    return JSONResponse(error.as_dict(), status_code=status)


def _encode_cursor(item):
    payload = json.dumps(
        {"created_at": item["created_at"], "id": item["id"]},
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(cursor):
    if cursor is None:
        return None
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding).decode("utf-8"))
        created_at, item_id = payload["created_at"], payload["id"]
        if not isinstance(created_at, str) or not created_at or not isinstance(item_id, str) or not item_id:
            raise ValueError
        return created_at, item_id
    except (
        binascii.Error, KeyError, TypeError, ValueError, UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise DomainError("INVALID_CURSOR", "历史记录游标无效")


def _page(items, limit):
    has_more = len(items) > limit
    page_items = items[:limit]
    return {
        "items": page_items,
        "next_cursor": _encode_cursor(page_items[-1]) if has_more else None,
    }


def _extract_http_url(value):
    match = re.search(r"https?://[^\s<>\"']+", str(value or "").strip())
    if not match:
        return ""
    return match.group(0).rstrip(".,;:!?)]}>，。；：！？）】》")


def _signal_download(response, token):
    if token and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", token):
        response.set_cookie(
            "vtn_download", token, max_age=60, path="/", samesite="lax"
        )
    return response


def _present_parser_record(record):
    if not record or record.get("platform") != "other":
        return record
    detected = detect_platform(record.get("source_url") or "")
    if detected == "other":
        return record
    return {**record, "platform": detected}


def create_v3_router(
    repository, parser_workflow, note_workflow=None, note_document=None, exporter=None,
    access_manager=None, thumbnail_fetcher=None,
):
    router = APIRouter(prefix="/api/v3")
    thumbnail_fetcher = thumbnail_fetcher or SafeThumbnailFetcher()

    def request_access_id(request):
        if access_manager is None:
            return None
        return getattr(request.state, "vtn_access_id", None)

    def owned_parser_task(task_id, request):
        task = parser_workflow.get_task(task_id)
        access_id = request_access_id(request)
        if task and access_id is not None and task.get("device_id") != access_id:
            return None
        return task

    def owned_parser_record(record_id, request):
        return repository.get_parser_record(record_id, request_access_id(request))

    def owned_note_task(task_id, request):
        task = note_workflow.get_task(task_id) if note_workflow is not None else None
        access_id = request_access_id(request)
        if task and access_id is not None and task.get("device_id") != access_id:
            return None
        return task

    def owned_note(note_id, request):
        note = repository.get_note(note_id)
        if not note:
            return None
        return note if owned_note_task(note["task_id"], request) else None

    if access_manager is not None:
        @router.post("/access/login")
        async def access_login(request: Request):
            body = await request.json()
            grant = access_manager.authenticate(body.get("code"))
            if not grant:
                return _error(DomainError("ACCESS_CODE_INVALID", "内测码无效或已到期"), 401)
            response = JSONResponse({"access": access_manager.snapshot(grant["id"])})
            response.set_cookie(
                SESSION_COOKIE, access_manager.issue_session(grant["id"]),
                max_age=access_manager.session_seconds, httponly=True,
                secure=access_manager.secure_cookie, samesite="lax", path="/",
            )
            return response

        @router.post("/access/logout")
        async def access_logout():
            response = JSONResponse({"ok": True})
            response.delete_cookie(SESSION_COOKIE, path="/")
            return response

        @router.get("/access/status")
        async def access_status(request: Request):
            access_id = access_manager.access_id_from_session(
                request.cookies.get(SESSION_COOKIE, "")
            )
            return {"enabled": True, "authenticated": bool(access_id), "access": access_manager.snapshot(access_id) if access_id else None}
    else:
        @router.get("/access/status")
        async def access_status_disabled():
            return {"enabled": False, "authenticated": False, "access": None}

    @router.get("/capabilities")
    async def capabilities():
        return {"integrity_recheck": note_document is not None}

    @router.post("/parser/tasks", status_code=202)
    async def create_parser_task(request: Request):
        body = await request.json()
        source_url = _extract_http_url(body.get("source_url"))
        if not source_url:
            return _error(DomainError("INVALID_SOURCE_URL", "请输入完整的视频链接"), 422)
        owner = request_access_id(request) or body.get("device_id") or "local-browser"
        task = parser_workflow.start_parse(owner, source_url)
        return {"task": task}

    @router.get("/parser/tasks/{task_id}")
    async def get_parser_task(task_id: str, request: Request):
        task = owned_parser_task(task_id, request)
        if not task:
            return _error(DomainError("PARSER_TASK_NOT_FOUND", "解析任务不存在"), 404)
        return {"task": task}

    @router.post("/parser/tasks/{task_id}/commands")
    async def parser_command(task_id: str, request: Request):
        body = await request.json()
        if not owned_parser_task(task_id, request):
            return _error(DomainError("PARSER_TASK_NOT_FOUND", "解析任务不存在"), 404)
        try:
            return {"task": parser_workflow.command(task_id, body.get("command", ""))}
        except DomainError as exc:
            return _error(exc, 404 if exc.code == "PARSER_TASK_NOT_FOUND" else 409)

    @router.get("/parser/tasks/{task_id}/events")
    async def parser_events(task_id: str, request: Request, after: int = 0):
        if not owned_parser_task(task_id, request):
            return _error(DomainError("PARSER_TASK_NOT_FOUND", "解析任务不存在"), 404)

        def event_stream():
            cursor = after
            last_heartbeat = 0.0
            while True:
                events = parser_workflow.subscribe(task_id, cursor)
                for event in events:
                    cursor = event.seq
                    yield (
                        f"id: {event.seq}\n"
                        f"event: {event.event_type}\n"
                        f"data: {json.dumps(event.payload, ensure_ascii=False)}\n\n"
                    )
                now = time.monotonic()
                if now - last_heartbeat >= 15:
                    last_heartbeat = now
                    yield "event: heartbeat\ndata: {}\n\n"
                time.sleep(0.25)

        return StreamingResponse(
            event_stream(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.get("/parser/records")
    async def parser_records(request: Request, limit: int = 30, cursor: str | None = None):
        safe_limit = min(max(limit, 1), 100)
        try:
            decoded_cursor = _decode_cursor(cursor)
        except DomainError as exc:
            return _error(exc, 422)
        records = repository.list_parser_records(
            safe_limit + 1, decoded_cursor, request_access_id(request)
        )
        return _page([_present_parser_record(record) for record in records], safe_limit)

    @router.get("/parser/records/{record_id}")
    async def parser_record(record_id: str, request: Request):
        record = owned_parser_record(record_id, request)
        if not record:
            return _error(DomainError("PARSER_RECORD_NOT_FOUND", "解析记录不存在"), 404)
        return {"record": _present_parser_record(record)}

    @router.get("/parser/records/{record_id}/thumbnail")
    async def parser_record_thumbnail(record_id: str, request: Request):
        record = owned_parser_record(record_id, request)
        if not record:
            return _error(
                DomainError("PARSER_RECORD_NOT_FOUND", "解析记录不存在"),
                404,
            )
        if not record.get("thumbnail_url"):
            return _error(
                DomainError("THUMBNAIL_UNAVAILABLE", "该视频没有可用封面。"),
                404,
            )
        try:
            content, content_type = await run_in_threadpool(
                thumbnail_fetcher.fetch,
                record["thumbnail_url"],
            )
        except DomainError as exc:
            return _error(exc, 404 if not exc.retryable else 502)
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "private, max-age=3600"},
        )

    @router.delete("/parser/records/{record_id}")
    async def delete_parser_record(record_id: str, request: Request):
        if not owned_parser_record(record_id, request):
            return _error(DomainError("PARSER_RECORD_NOT_FOUND", "解析记录不存在"), 404)
        repository.delete_parser_record(record_id)
        return Response(status_code=204)

    @router.get("/parser/records/{record_id}/transcript.txt")
    async def parser_transcript_txt(record_id: str, request: Request):
        record = owned_parser_record(record_id, request)
        if not record:
            return _error(DomainError("PARSER_RECORD_NOT_FOUND", "解析记录不存在"), 404)
        return Response(
            record["transcript_text"], media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="transcript-{record_id}.txt"'},
        )

    @router.get("/parser/records/{record_id}/transcript.md")
    async def parser_transcript_md(record_id: str, request: Request):
        record = owned_parser_record(record_id, request)
        if not record:
            return _error(DomainError("PARSER_RECORD_NOT_FOUND", "解析记录不存在"), 404)
        record = _present_parser_record(record)
        content = (
            f"# {record['title']} — 逐字稿\n\n"
            f"> 作者：{record['creator'] or '未知'} | 平台：{record['platform']}\n\n"
            f"---\n\n{record['transcript_text']}\n"
        )
        return Response(
            content, media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="transcript-{record_id}.md"'},
        )

    @router.get("/parser/records/{record_id}/video")
    async def parser_video(record_id: str, request: Request, download_token: str | None = None):
        record = owned_parser_record(record_id, request)
        if not record:
            return _error(DomainError("PARSER_RECORD_NOT_FOUND", "解析记录不存在"), 404)
        directory = Path(tempfile.mkdtemp(prefix="vtn-video-download-"))
        try:
            path = await run_in_threadpool(
                parser_workflow.media.download_video, record["source_url"], directory
            )
        except DomainError as exc:
            shutil.rmtree(directory, ignore_errors=True)
            return _error(
                exc,
                502,
            )
        return _signal_download(
            FileResponse(
                path, filename=f"video-{record_id}.mp4", media_type="video/mp4",
                background=BackgroundTask(shutil.rmtree, directory, ignore_errors=True),
            ),
            download_token,
        )

    @router.get("/parser/records/{record_id}/audio")
    async def parser_audio(record_id: str, request: Request, download_token: str | None = None):
        record = owned_parser_record(record_id, request)
        if not record:
            return _error(DomainError("PARSER_RECORD_NOT_FOUND", "解析记录不存在"), 404)
        directory = Path(tempfile.mkdtemp(prefix="vtn-audio-download-"))
        try:
            path = await run_in_threadpool(
                parser_workflow.media.download_audio, record["source_url"], directory
            )
        except DomainError as exc:
            shutil.rmtree(directory, ignore_errors=True)
            return _error(exc, 502)
        return _signal_download(
            FileResponse(
                path, filename=f"audio-{record_id}.mp3", media_type="audio/mpeg",
                background=BackgroundTask(shutil.rmtree, directory, ignore_errors=True),
            ),
            download_token,
        )

    if note_workflow is None:
        return router

    @router.post("/migrations/browser-history")
    async def migrate_browser_history(request: Request):
        body = await request.json()
        imported = {"parser_records": 0, "notes": 0}
        for item in body.get("transcripts", []):
            source_url = item.get("url") or item.get("source_url") or ""
            transcript = item.get("transcript") or item.get("text") or ""
            if not source_url or not transcript or repository.parser_record_exists_for_url(source_url):
                continue
            record_id = item.get("id") or uuid.uuid4().hex
            repository.create_parser_record(
                {
                    "id": record_id, "source_url": source_url,
                    "platform": item.get("platform", "other"),
                    "title": item.get("title", "旧解析记录"),
                    "creator": item.get("creator", ""), "description": item.get("description", ""),
                    "duration_seconds": item.get("duration", 0),
                    "thumbnail_url": item.get("thumbnail", ""),
                    "transcript_text": transcript,
                }
            )
            imported["parser_records"] += 1
        for item in body.get("notes", []):
            markdown = item.get("notes") or item.get("markdown") or ""
            if not markdown.strip():
                continue
            legacy_key = str(item.get("id") or f"{item.get('title', '')}:{markdown}")
            note_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"vtn-legacy-note:{legacy_key}"))
            if repository.get_note(note_id):
                continue
            task_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"vtn-legacy-task:{legacy_key}"))
            source_url = item.get("url") or item.get("source_url") or ""
            parser_record_id = repository.parser_record_exists_for_url(source_url) if source_url else None
            source_type = "parser" if parser_record_id else "paste"
            source_snapshot = {
                "type": source_type,
                "name": "旧本地历史",
                "title": item.get("title") or "旧版成品笔记",
                "platform": item.get("platform") or "",
                "source_url": source_url,
            }
            if parser_record_id:
                source_snapshot["parser_record_id"] = parser_record_id
            title = (item.get("title") or "旧版成品笔记").strip()
            basis = item.get("transcript") or markdown
            repository.create_note_task(
                {
                    "id": task_id,
                    "device_id": body.get("device_id") or "legacy-browser",
                    "state": "complete",
                    "source_type": source_type,
                    "source_name": title,
                    "source_snapshot": source_snapshot,
                    "basis_transcript": basis,
                    "request_text": "从旧版本本地历史导入",
                    "proposed_title": title,
                }
            )
            if parser_record_id:
                repository.link_parser_note(parser_record_id, task_id)
            repository.create_note(
                {
                    "id": note_id,
                    "task_id": task_id,
                    "title": title,
                    "current_markdown": markdown,
                    "integrity": {"status": "ok", "migrated_from": "vtn-history"},
                    "source_snapshot": source_snapshot,
                    "basis_transcript": basis,
                }
            )
            imported["notes"] += 1
        return {"ok": True, "imported": imported}

    @router.post("/note-tasks", status_code=202)
    async def create_note_task(request: Request):
        body = await request.json()
        access_id = request_access_id(request)
        task_id = None
        if access_id is not None:
            source = body.get("source") or {}
            if source.get("type") == "parser" and not owned_parser_record(
                source.get("parser_record_id", ""), request
            ):
                return _error(DomainError("PARSER_RECORD_NOT_FOUND", "解析记录不存在"), 404)
            if source.get("type") == "note" and not owned_note(
                source.get("note_id", ""), request
            ):
                return _error(DomainError("NOTE_NOT_FOUND", "原笔记不存在"), 404)
            body["device_id"] = access_id
            task_id = str(uuid.uuid4())
        try:
            task = note_workflow.start_analysis(body, task_id=task_id)
            return {"task": task}
        except DomainError as exc:
            return _error(
                exc,
                404 if exc.code in {"PARSER_RECORD_NOT_FOUND", "NOTE_NOT_FOUND"}
                else 429 if exc.code in {
                    "PAID_CALLS_PAUSED", "NOTE_QUOTA_EXCEEDED"
                } else 422,
            )

    @router.get("/note-tasks")
    async def note_tasks(
        request: Request, device_id: str | None = None, limit: int = 30,
        cursor: str | None = None,
    ):
        safe_limit = min(max(limit, 1), 100)
        try:
            decoded_cursor = _decode_cursor(cursor)
        except DomainError as exc:
            return _error(exc, 422)
        return _page(
            repository.list_note_tasks(
                request_access_id(request) or device_id, safe_limit + 1, decoded_cursor
            ), safe_limit
        )

    @router.get("/note-tasks/{task_id}")
    async def get_note_task(task_id: str, request: Request):
        task = owned_note_task(task_id, request)
        if not task:
            return _error(DomainError("NOTE_TASK_NOT_FOUND", "笔记任务不存在"), 404)
        task["chapters"] = repository.list_note_chapters(task_id)
        return {"task": task}

    @router.post("/note-tasks/{task_id}/commands")
    async def note_command(task_id: str, request: Request):
        if not owned_note_task(task_id, request):
            return _error(DomainError("NOTE_TASK_NOT_FOUND", "笔记任务不存在"), 404)
        try:
            task = note_workflow.command(task_id, await request.json())
            task["chapters"] = repository.list_note_chapters(task_id)
            return {"task": task}
        except DomainError as exc:
            return _error(exc, 404 if exc.code == "NOTE_TASK_NOT_FOUND" else 409)

    @router.get("/note-tasks/{task_id}/events")
    async def note_events(task_id: str, request: Request, after: int = 0):
        if not owned_note_task(task_id, request):
            return _error(DomainError("NOTE_TASK_NOT_FOUND", "笔记任务不存在"), 404)

        def stream():
            cursor = after
            last_heartbeat = 0.0
            while True:
                for event in note_workflow.subscribe(task_id, cursor):
                    cursor = event.seq
                    yield (
                        f"id: {event.seq}\nevent: {event.event_type}\n"
                        f"data: {json.dumps(event.payload, ensure_ascii=False)}\n\n"
                    )
                now = time.monotonic()
                if now - last_heartbeat >= 15:
                    last_heartbeat = now
                    yield "event: heartbeat\ndata: {}\n\n"
                time.sleep(0.25)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @router.delete("/note-tasks/{task_id}")
    async def delete_note_task(task_id: str, request: Request):
        if not owned_note_task(task_id, request):
            return _error(DomainError("NOTE_TASK_NOT_FOUND", "笔记任务不存在"), 404)
        try:
            note_workflow.abandon(task_id)
        except DomainError as exc:
            return _error(exc, 404 if exc.code == "NOTE_TASK_NOT_FOUND" else 409)
        return Response(status_code=204)

    @router.get("/notes")
    async def notes(request: Request, limit: int = 30, cursor: str | None = None):
        safe_limit = min(max(limit, 1), 100)
        try:
            decoded_cursor = _decode_cursor(cursor)
        except DomainError as exc:
            return _error(exc, 422)
        return _page(
            repository.list_notes(safe_limit + 1, decoded_cursor, request_access_id(request)),
            safe_limit,
        )

    @router.get("/notes/{note_id}")
    async def note(note_id: str, request: Request):
        if not owned_note(note_id, request):
            return _error(DomainError("NOTE_NOT_FOUND", "笔记不存在"), 404)
        try:
            return {"note": note_document.get(note_id)}
        except DomainError as exc:
            return _error(exc, 404)

    @router.patch("/notes/{note_id}")
    async def patch_note(note_id: str, request: Request):
        if not owned_note(note_id, request):
            return _error(DomainError("NOTE_NOT_FOUND", "笔记不存在"), 404)
        body = await request.json()
        try:
            return {
                "note": note_document.save(
                    note_id, int(body["expected_version"]), body["title"], body["markdown"],
                    checkpoint=bool(body.get("checkpoint")),
                )
            }
        except DomainError as exc:
            return _error(exc, 409 if exc.code == "NOTE_VERSION_CONFLICT" else 404)

    @router.post("/notes/{note_id}/restore-ai-initial")
    async def restore_note(note_id: str, request: Request):
        if not owned_note(note_id, request):
            return _error(DomainError("NOTE_NOT_FOUND", "笔记不存在"), 404)
        body = await request.json()
        try:
            return {"note": note_document.restore_ai_initial(note_id, int(body["expected_version"]))}
        except DomainError as exc:
            return _error(exc, 409 if exc.code == "NOTE_VERSION_CONFLICT" else 404)

    @router.post("/notes/{note_id}/integrity-check")
    async def recheck_note_integrity(note_id: str, request: Request):
        if not owned_note(note_id, request):
            return _error(DomainError("NOTE_NOT_FOUND", "笔记不存在"), 404)
        try:
            return {
                "note": await run_in_threadpool(note_document.recheck_integrity, note_id)
            }
        except DomainError as exc:
            return _error(exc, 404 if exc.code in {"NOTE_NOT_FOUND", "NOTE_TASK_NOT_FOUND"} else 422)

    @router.post("/notes/{note_id}/chapters/{chapter_id}/candidates", status_code=202)
    async def create_candidate(note_id: str, chapter_id: str, request: Request):
        if not owned_note(note_id, request):
            return _error(DomainError("NOTE_NOT_FOUND", "笔记不存在"), 404)
        try:
            return {"candidate": note_document.regenerate_chapter(note_id, chapter_id)}
        except DomainError as exc:
            return _error(exc, 404)

    @router.post("/notes/{note_id}/candidates/{candidate_id}/decision")
    async def decide_candidate(note_id: str, candidate_id: str, request: Request):
        if not owned_note(note_id, request):
            return _error(DomainError("NOTE_NOT_FOUND", "笔记不存在"), 404)
        body = await request.json()
        try:
            return {
                "note": note_document.decide_candidate(
                    note_id, candidate_id, body["decision"], int(body["expected_version"])
                )
            }
        except DomainError as exc:
            return _error(exc, 409 if exc.code == "NOTE_VERSION_CONFLICT" else 404)

    @router.get("/notes/{note_id}/export")
    async def export_note(
        note_id: str, request: Request, format: str = "md", content: str = "note",
        source: str = "exclude"
    ):
        if not owned_note(note_id, request):
            return _error(DomainError("NOTE_NOT_FOUND", "笔记不存在"), 404)
        try:
            result = exporter.markdown(
                note_id, include_transcript=content == "note_transcript",
                include_source=source == "include",
            )
        except DomainError as exc:
            return _error(exc, 404)
        if format == "md":
            return Response(
                result.content, media_type=result.media_type,
                headers={
                    "Content-Disposition":
                    f"attachment; filename=note.md; filename*=UTF-8''{quote(result.filename)}"
                },
            )
        if format != "pdf":
            return _error(DomainError("INVALID_EXPORT_FORMAT", "不支持该导出格式"), 422)
        import markdown as markdown_library
        directory = Path(tempfile.mkdtemp(prefix="vtn-pdf-"))
        html_path = directory / "note.html"
        pdf_path = directory / "note.pdf"
        html = (
            '<meta charset="utf-8"><style>body{font-family:sans-serif;line-height:1.8;'
            'max-width:760px;margin:auto}h1,h2{page-break-after:avoid}'
            '.transcript{page-break-before:always}</style>'
            + markdown_library.markdown(result.content, extensions=["tables", "fenced_code"])
        )
        html_path.write_text(html, encoding="utf-8")
        binary = shutil.which("weasyprint") or "/opt/homebrew/bin/weasyprint"
        try:
            subprocess.run([binary, str(html_path), str(pdf_path)], check=True, timeout=60)
        except Exception as exc:
            shutil.rmtree(directory, ignore_errors=True)
            return _error(
                DomainError("PDF_EXPORT_FAILED", f"PDF 导出失败：{exc}", retryable=True), 500
            )
        return FileResponse(
            pdf_path, filename=result.filename.removesuffix(".md") + ".pdf",
            media_type="application/pdf",
            background=BackgroundTask(shutil.rmtree, directory, ignore_errors=True),
        )

    @router.delete("/notes/{note_id}")
    async def delete_note(note_id: str, request: Request):
        if not owned_note(note_id, request):
            return _error(DomainError("NOTE_NOT_FOUND", "笔记不存在"), 404)
        if not repository.delete_note(note_id):
            return _error(DomainError("NOTE_NOT_FOUND", "笔记不存在"), 404)
        return Response(status_code=204)

    return router
