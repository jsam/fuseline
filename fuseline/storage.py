from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Any, Iterable, Optional, TYPE_CHECKING

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
    def set_inputs(
        self,
        workflow_id: str,
        instance_id: str,
        inputs: dict[str, Any],
    ) -> None:
        """Persist workflow input parameters."""

    @abstractmethod
    def get_inputs(self, workflow_id: str, instance_id: str) -> dict[str, Any]:
        """Return stored workflow parameters."""

    @abstractmethod
    def set_result(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        result: Any,
    ) -> None:
        """Persist a step result for dependency lookups."""

    @abstractmethod
    def get_result(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
    ) -> Any | None:
        """Return the stored result for *step_name* if any."""

    @abstractmethod
    def finalize_run(self, workflow_id: str, instance_id: str) -> None:
        """Mark the run as finished."""


class MemoryRuntimeStorage(RuntimeStorage):
    """In-memory storage used for testing and examples."""

    def __init__(self) -> None:
        self._queues: dict[tuple[str, str], deque[str]] = defaultdict(deque)
        self._queued: dict[tuple[str, str], set[str]] = defaultdict(set)
        self._states: dict[tuple[str, str, str], "Status"] = {}
        self._results: dict[tuple[str, str, str], Any] = {}
        self._inputs: dict[tuple[str, str], dict[str, Any]] = {}
        self._finished: set[tuple[str, str]] = set()

    def create_run(
        self, workflow_id: str, instance_id: str, steps: Iterable[str]
    ) -> None:
        from .workflow import Status
        for step in steps:
            self._states[(workflow_id, instance_id, step)] = Status.PENDING
        key = (workflow_id, instance_id)
        self._queues[key].clear()
        self._queued[key].clear()
        self._results = {
            k: v
            for k, v in self._results.items()
            if k[:2] != key
        }
        self._inputs.pop(key, None)

    def enqueue(self, workflow_id: str, instance_id: str, step_name: str) -> None:
        key = (workflow_id, instance_id)
        if step_name in self._queued[key]:
            return
        self._queues[key].append(step_name)
        self._queued[key].add(step_name)

    def fetch_next(self, workflow_id: str, instance_id: str) -> Optional[str]:
        q = self._queues.get((workflow_id, instance_id))
        if not q:
            return None
        step = q.popleft()
        self._queued[(workflow_id, instance_id)].discard(step)
        return step

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

    # RuntimeStorage extras
    def set_inputs(
        self,
        workflow_id: str,
        instance_id: str,
        inputs: dict[str, Any],
    ) -> None:
        self._inputs[(workflow_id, instance_id)] = inputs

    def get_inputs(self, workflow_id: str, instance_id: str) -> dict[str, Any]:
        return self._inputs.get((workflow_id, instance_id), {})

    def set_result(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        result: Any,
    ) -> None:
        self._results[(workflow_id, instance_id, step_name)] = result

    def get_result(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> Any | None:
        return self._results.get((workflow_id, instance_id, step_name))
