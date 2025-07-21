from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Iterable, Optional

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from . import Broker

from . import StepAssignment, StepReport
from ..workflow import WorkflowSchema


class BrokerClient(ABC):
    """Client-side interface used by workers to communicate with the broker."""

    @abstractmethod
    def register_worker(self, workflows: Iterable[WorkflowSchema]) -> str:
        """Register a worker and return a worker ID."""

    @abstractmethod
    def dispatch_workflow(self, workflow: WorkflowSchema, inputs: Optional[dict[str, Any]] = None) -> str:
        """Create a workflow run and queue initial steps."""

    @abstractmethod
    def get_step(self, worker_id: str) -> StepAssignment | None:
        """Return the next step for ``worker_id``."""

    @abstractmethod
    def report_step(self, worker_id: str, report: StepReport) -> None:
        """Send a completed step report back to the broker."""

    @abstractmethod
    def keep_alive(self, worker_id: str) -> None:
        """Notify the broker that ``worker_id`` is still alive."""


class LocalBrokerClient(BrokerClient):
    """Client that directly calls a :class:`Broker` instance."""

    def __init__(self, broker: "Broker") -> None:
        self._broker = broker

    def register_worker(self, workflows: Iterable[WorkflowSchema]) -> str:
        return self._broker.register_worker(workflows)

    def dispatch_workflow(self, workflow: WorkflowSchema, inputs: Optional[dict[str, Any]] = None) -> str:
        return self._broker.dispatch_workflow(workflow, inputs)

    def get_step(self, worker_id: str) -> StepAssignment | None:
        return self._broker.get_step(worker_id)

    def report_step(self, worker_id: str, report: StepReport) -> None:
        self._broker.report_step(worker_id, report)

    def keep_alive(self, worker_id: str) -> None:
        self._broker.keep_alive(worker_id)
