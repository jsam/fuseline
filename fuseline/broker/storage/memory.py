from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING, Any, Iterable, Optional

from .base import RuntimeStorage

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from ...workflow import Status


class MemoryRuntimeStorage(RuntimeStorage):
    """In-memory storage used for testing and examples."""

    def __init__(self) -> None:
        self._queues: dict[tuple[str, str], deque[str]] = defaultdict(deque)
        self._queued: dict[tuple[str, str], set[str]] = defaultdict(set)
        self._states: dict[tuple[str, str, str], "Status"] = {}
        self._results: dict[tuple[str, str, str], Any] = {}
        self._inputs: dict[tuple[str, str], dict[str, Any]] = {}
        self._finished: set[tuple[str, str]] = set()
        self._assignments: dict[tuple[str, str, str], tuple[str, float]] = {}

    def create_run(
        self, workflow_id: str, instance_id: str, steps: Iterable[str]
    ) -> None:
        from ...workflow import Status

        for step in steps:
            self._states[(workflow_id, instance_id, step)] = Status.PENDING
        key = (workflow_id, instance_id)
        self._queues[key].clear()
        self._queued[key].clear()
        self._assignments = {k: v for k, v in self._assignments.items() if k[:2] != key}
        self._results = {k: v for k, v in self._results.items() if k[:2] != key}
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

    def assign_step(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        worker_id: str,
        expires_at: float,
    ) -> None:
        self._assignments[(workflow_id, instance_id, step_name)] = (
            worker_id,
            expires_at,
        )

    def clear_assignment(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> None:
        self._assignments.pop((workflow_id, instance_id, step_name), None)

    def get_assignment(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> tuple[str, float] | None:
        return self._assignments.get((workflow_id, instance_id, step_name))

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
        self._assignments = {
            k: v
            for k, v in self._assignments.items()
            if k[:2] != (workflow_id, instance_id)
        }

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


