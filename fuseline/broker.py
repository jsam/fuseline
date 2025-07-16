from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Iterable, Optional

from .workflow import Status


class Broker(ABC):
    """Interface implemented by the workflow broker."""

    @abstractmethod
    def register_worker(self, workflows: Iterable[str]) -> str:
        """Register a worker and return a worker ID."""

    @abstractmethod
    def get_step(self, worker_id: str) -> tuple[str, str, str] | None:
        """Return the next step for *worker_id* or ``None``."""

    @abstractmethod
    def report_step(
        self,
        worker_id: str,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        state: Status,
    ) -> None:
        """Update the state of *step_name* for *worker_id*."""

    @abstractmethod
    def keep_alive(self, worker_id: str) -> None:
        """Notify the broker that *worker_id* is still active."""


class MemoryBroker(Broker):
    """Simple in-memory broker used for tests."""

    def __init__(self) -> None:
        self._workers: dict[str, set[str]] = {}
        self._queues: dict[str, deque[tuple[str, str, str]]] = defaultdict(deque)
        self._states: dict[tuple[str, str, str], Status] = {}
        self._heartbeat: set[str] = set()
        self._wid = 0

    def register_worker(self, workflows: Iterable[str]) -> str:
        self._wid += 1
        wid = str(self._wid)
        self._workers[wid] = set(workflows)
        return wid

    def get_step(self, worker_id: str) -> tuple[str, str, str] | None:
        q = self._queues.get(worker_id)
        if not q:
            return None
        return q.popleft() if q else None

    def report_step(
        self,
        worker_id: str,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        state: Status,
    ) -> None:
        self._states[(workflow_id, instance_id, step_name)] = state

    def keep_alive(self, worker_id: str) -> None:
        self._heartbeat.add(worker_id)

    # utility for tests
    def enqueue_step(
        self, worker_id: str, workflow_id: str, instance_id: str, step_name: str
    ) -> None:
        self._queues[worker_id].append((workflow_id, instance_id, step_name))
