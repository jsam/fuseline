from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from .workflow import Status


class RuntimeStorage(ABC):
    """Interface for persisting workflow runtime state."""

    @abstractmethod
    def create_run(
        self,
        workflow_id: str,
        instance_id: str,
        steps: Iterable[str],
    ) -> None:
        """Initialize storage for a workflow run."""

    @abstractmethod
    def enqueue(self, workflow_id: str, instance_id: str, step_name: str) -> None:
        """Mark *step_name* ready for execution."""

    @abstractmethod
    def fetch_next(self, workflow_id: str, instance_id: str) -> Optional[str]:
        """Return the next ready step or ``None``."""

    @abstractmethod
    def set_state(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        state: "Status",
    ) -> None:
        """Persist the state of *step_name* for this run."""

    @abstractmethod
    def get_state(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
    ) -> "Status | None":
        """Return the stored state for *step_name* if any."""

    @abstractmethod
    def finalize_run(self, workflow_id: str, instance_id: str) -> None:
        """Mark the run as finished."""


class FileRuntimeStorage(RuntimeStorage):
    """Store workflow runtime state in JSON files."""

    def __init__(self, directory: str) -> None:
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def _path(self, workflow_id: str, instance_id: str) -> str:
        return os.path.join(self.directory, f"{workflow_id}_{instance_id}.json")

    def _load(self, workflow_id: str, instance_id: str) -> dict:
        path = self._path(workflow_id, instance_id)
        if not os.path.exists(path):
            return {"queue": [], "states": {}}
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _save(self, workflow_id: str, instance_id: str, data: dict) -> None:
        with open(self._path(workflow_id, instance_id), "w", encoding="utf-8") as fh:
            json.dump(data, fh)

    def create_run(
        self,
        workflow_id: str,
        instance_id: str,
        steps: Iterable[str],
    ) -> None:
        from .workflow import Status

        data = {"queue": list(steps), "states": {s: Status.PENDING.value for s in steps}}
        self._save(workflow_id, instance_id, data)

    def enqueue(self, workflow_id: str, instance_id: str, step_name: str) -> None:
        from .workflow import Status

        data = self._load(workflow_id, instance_id)
        data.setdefault("queue", []).append(step_name)
        data.setdefault("states", {}).setdefault(step_name, Status.PENDING.value)
        self._save(workflow_id, instance_id, data)

    def fetch_next(self, workflow_id: str, instance_id: str) -> Optional[str]:
        data = self._load(workflow_id, instance_id)
        if not data.get("queue"):
            return None
        step = data["queue"].pop(0)
        self._save(workflow_id, instance_id, data)
        return step

    def set_state(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        state: "Status",
    ) -> None:
        from .workflow import Status

        data = self._load(workflow_id, instance_id)
        data.setdefault("states", {})[step_name] = state.value
        self._save(workflow_id, instance_id, data)

    def get_state(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> "Status | None":
        from .workflow import Status

        data = self._load(workflow_id, instance_id)
        val = data.get("states", {}).get(step_name)
        return Status(val) if val is not None else None

    def finalize_run(self, workflow_id: str, instance_id: str) -> None:
        path = self._path(workflow_id, instance_id)
        if os.path.exists(path):
            data = self._load(workflow_id, instance_id)
            data["finished"] = True
            self._save(workflow_id, instance_id, data)
