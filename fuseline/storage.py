from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type hints only
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


class MemoryRuntimeStorage(RuntimeStorage):
    """In-memory storage used for testing and examples."""

    def __init__(self) -> None:
        self._queues: dict[tuple[str, str], deque[str]] = defaultdict(deque)
        self._states: dict[tuple[str, str, str], "Status"] = {}
        self._finished: set[tuple[str, str]] = set()

    def create_run(
        self, workflow_id: str, instance_id: str, steps: Iterable[str]
    ) -> None:
        from .workflow import Status

        for step in steps:
            self._states[(workflow_id, instance_id, step)] = Status.PENDING

    def enqueue(self, workflow_id: str, instance_id: str, step_name: str) -> None:
        self._queues[(workflow_id, instance_id)].append(step_name)

    def fetch_next(self, workflow_id: str, instance_id: str) -> Optional[str]:
        q = self._queues.get((workflow_id, instance_id))
        if not q:
            return None
        return q.popleft() if q else None

    def set_state(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        state: "Status",
    ) -> None:
        self._states[(workflow_id, instance_id, step_name)] = state

    def get_state(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> "Status | None":
        return self._states.get((workflow_id, instance_id, step_name))

    def finalize_run(self, workflow_id: str, instance_id: str) -> None:
        self._finished.add((workflow_id, instance_id))
