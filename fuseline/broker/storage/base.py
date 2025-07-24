from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Iterable, Optional

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from ...workflow import Status


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
    def assign_step(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        worker_id: str,
        expires_at: float,
    ) -> None:
        """Record that *worker_id* is processing *step_name*."""

    @abstractmethod
    def clear_assignment(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> None:
        """Remove assignment for *step_name*."""

    @abstractmethod
    def get_assignment(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> tuple[str, float] | None:
        """Return ``(worker_id, expires_at)`` for assigned *step_name*."""

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


