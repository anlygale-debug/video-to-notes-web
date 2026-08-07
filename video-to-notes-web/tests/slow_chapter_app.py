import os
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from vtn.adapters.llm import FakeLLM
from vtn.adapters.media import FakePlatformMedia
from vtn.adapters.transcription import FakeTranscriber
from vtn.documents.notes import NoteDocument
from vtn.exports.exporter import Exporter
from vtn.storage.sqlite import SQLiteRepository
from vtn.web.api import create_v3_router
from vtn.workflows.notes import NoteWorkflow
from vtn.workflows.parser import ParserWorkflow


class SlowChapterLLM(FakeLLM):
    def generate_direct(self, task):
        delay = float(os.environ.get("VTN_TEST_DIRECT_DELAY", "0"))
        if delay:
            time.sleep(delay)
        return super().generate_direct(task)

    def generate_chapter(self, task, chapter, previous_summary):
        time.sleep(float(os.environ.get("VTN_TEST_CHAPTER_DELAY", "1.1")))
        return super().generate_chapter(task, chapter, previous_summary)


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
repository = SQLiteRepository(
    Path(os.environ.get("VTN_DATABASE_PATH", "/tmp/vtn-slow-chapter.sqlite3"))
)
repository.migrate()
llm = SlowChapterLLM()
if os.environ.get("VTN_TEST_FAIL_CHAPTER_POSITION"):
    llm.fail_chapter_position = int(os.environ["VTN_TEST_FAIL_CHAPTER_POSITION"])
parser = ParserWorkflow(
    repository, FakePlatformMedia(), FakeTranscriber(), run_in_background=False
)
notes = NoteWorkflow(repository, llm, run_in_background=True)
app.include_router(
    create_v3_router(repository, parser, notes, NoteDocument(repository, llm), Exporter(repository))
)


@app.get("/next", response_class=HTMLResponse)
async def next_app():
    return Path("static/app.html").read_text(encoding="utf-8")
