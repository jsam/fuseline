from __future__ import annotations

import json
from datetime import datetime

from .interfaces import Tracer


class FileTracer(Tracer):
    """Write trace events to a file as JSON lines."""

    def __init__(self, path: str) -> None:
        self.path = path
        # Ensure the file exists so multiple runs append to it
        open(self.path, "a", encoding="utf-8").close()

    def record(self, event: dict) -> None:
        event.setdefault("timestamp", datetime.utcnow().isoformat())
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")


class BoundTracer(Tracer):
    """Tracer that injects workflow identifiers into each event."""

    def __init__(self, tracer: Tracer, workflow_id: str, instance_id: str) -> None:
        self.tracer = tracer
        self.workflow_id = workflow_id
        self.instance_id = instance_id

    def record(self, event: dict) -> None:
        event.setdefault("workflow_id", self.workflow_id)
        event.setdefault("workflow_instance_id", self.instance_id)
        self.tracer.record(event)
