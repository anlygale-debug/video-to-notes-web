from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class WorkflowEvent:
    workflow_type: str
    task_id: str
    seq: int
    event_type: str
    payload: dict[str, Any]
    created_at: str
