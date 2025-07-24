from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence

from ..workflow import Status, WorkflowSchema


@dataclass
class StepAssignment:
    """Information returned by :meth:`Broker.get_step`."""

    workflow_id: str
    instance_id: str
    step_name: str
    payload: dict[str, Any]
    assigned_at: float
    expires_at: float


@dataclass
class StepReport:
    """Information sent to :meth:`Broker.report_step`."""

    workflow_id: str
    instance_id: str
    step_name: str
    state: Status
    result: Any


@dataclass
class RepositoryInfo:
    """Metadata for a workflow repository."""

    name: str
    url: str
    workflows: Sequence[str]
    credentials: Mapping[str, str] = field(default_factory=dict)


@dataclass
class WorkflowInfo:
    """Workflow specification paired with its repository."""

    repository: str
    workflow: str


@dataclass
class LastTask:
    """Information about the most recent step processed by a worker."""

    workflow_id: str
    instance_id: str
    step_name: str
    success: bool


@dataclass
class WorkerInfo:
    """Metadata returned by :meth:`Broker.list_workers`."""

    worker_id: str
    connected_at: float
    last_seen: float
    last_task: LastTask | None


class Broker(ABC):
    """Interface implemented by the workflow broker."""

    @abstractmethod
    def register_worker(self, workflows: Iterable[WorkflowSchema]) -> str:
        """Register a worker and return a worker ID."""

    @abstractmethod
    def dispatch_workflow(self, workflow: WorkflowSchema, inputs: Optional[dict[str, Any]] = None) -> str:
        """Create a workflow run and queue initial steps."""

    @abstractmethod
    def get_step(self, worker_id: str) -> StepAssignment | None:
        """Return the next step for *worker_id* and record the assignment."""

    @abstractmethod
    def report_step(
        self,
        worker_id: str,
        report: StepReport,
    ) -> None:
        """Store step output and mark it completed."""

    @abstractmethod
    def keep_alive(self, worker_id: str) -> None:
        """Notify the broker that *worker_id* is still active."""

    # Repository management -------------------------------------------------

    @abstractmethod
    def register_repository(self, repo: RepositoryInfo) -> None:
        """Store metadata for a workflow repository."""

    @abstractmethod
    def get_repository(self, name: str) -> RepositoryInfo | None:
        """Return the repository information for *name* if known."""

    @abstractmethod
    def list_repositories(self, page: int = 1, page_size: int = 50) -> Iterable[RepositoryInfo]:
        """Return repositories for the specified page."""

    def status(self) -> dict[str, str]:
        """Return a simple status dictionary."""
        return {"status": "ok"}

    @abstractmethod
    def list_workers(self) -> Iterable[WorkerInfo]:
        """Return metadata for currently connected workers."""

    @abstractmethod
    def list_workflows(self) -> Iterable[WorkflowInfo]:
        """Return registered workflow specifications grouped by repository."""
