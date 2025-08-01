from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Iterable, Optional
from urllib import parse, request
from urllib.parse import urlparse

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from . import Broker

from ..workflow import WorkflowSchema
from . import RepositoryInfo, StepAssignment, StepReport, WorkerInfo


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

    # Repository management -------------------------------------------------

    @abstractmethod
    def register_repository(self, repo: RepositoryInfo) -> None:
        """Register a workflow repository with the broker."""

    @abstractmethod
    def get_repository(self, name: str) -> RepositoryInfo | None:
        """Return repository information for ``name`` if known."""

    @abstractmethod
    def list_repositories(self, page: int = 1) -> Iterable[RepositoryInfo]:
        """Return repositories for the given page."""

    @abstractmethod
    def list_workers(self) -> Iterable[WorkerInfo]:
        """Return information about connected workers."""


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

    def register_repository(self, repo: RepositoryInfo) -> None:
        self._broker.register_repository(repo)

    def get_repository(self, name: str) -> RepositoryInfo | None:
        return self._broker.get_repository(name)

    def list_repositories(self, page: int = 1) -> Iterable[RepositoryInfo]:
        return list(self._broker.list_repositories(page))

    def list_workers(self) -> Iterable[WorkerInfo]:
        return list(self._broker.list_workers())


class HttpBrokerClient(BrokerClient):
    """Client that communicates with a remote HTTP broker."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, data: Any = None, query: Optional[dict[str, str]] = None) -> Any:
        url = self.base_url + path
        if query:
            url += "?" + parse.urlencode(query)
        scheme = urlparse(url).scheme
        if scheme not in {"http", "https"}:
            raise ValueError(f"unsupported URL scheme: {scheme}")
        body = json.dumps(data).encode() if data is not None else b""
        req = request.Request(url, data=body, headers={"Content-Type": "application/json"})  # noqa: S310
        with request.urlopen(req) as resp:  # noqa: S310 - validated scheme
            payload = resp.read()
        if payload:
            return json.loads(payload)
        return None

    def _get(self, path: str, query: Optional[dict[str, str]] = None) -> Any:
        url = self.base_url + path
        if query:
            url += "?" + parse.urlencode(query)
        scheme = urlparse(url).scheme
        if scheme not in {"http", "https"}:
            raise ValueError(f"unsupported URL scheme: {scheme}")
        with request.urlopen(url) as resp:  # noqa: S310 - validated scheme
            if resp.status in {204, 404}:
                return None
            payload = resp.read()
        if not payload:
            return None
        data = json.loads(payload)
        return data

    def register_worker(self, workflows: Iterable[WorkflowSchema]) -> str:
        data = [asdict(wf) for wf in workflows]
        return self._post("/worker/register", data)

    def dispatch_workflow(self, workflow: WorkflowSchema, inputs: Optional[dict[str, Any]] = None) -> str:
        return self._post("/workflow/dispatch", {"workflow": asdict(workflow), "inputs": inputs})

    def get_step(self, worker_id: str) -> StepAssignment | None:
        data = self._get("/workflow/step", {"worker_id": worker_id})
        if not data:
            return None
        return StepAssignment(**data)

    def report_step(self, worker_id: str, report: StepReport) -> None:
        self._post("/workflow/step", asdict(report), {"worker_id": worker_id})

    def keep_alive(self, worker_id: str) -> None:
        self._post("/worker/keep-alive", None, {"worker_id": worker_id})

    def register_repository(self, repo: RepositoryInfo) -> None:
        self._post("/repository/register", asdict(repo))

    def get_repository(self, name: str) -> RepositoryInfo | None:
        data = self._get("/repository", {"name": name})
        return RepositoryInfo(**data) if data else None

    def list_repositories(self, page: int = 1) -> Iterable[RepositoryInfo]:
        data = self._get("/repository", {"page": str(page)}) or []
        return [RepositoryInfo(**r) for r in data]

    def list_workers(self) -> Iterable[WorkerInfo]:
        data = self._get("/workers") or []
        return [WorkerInfo(**w) for w in data]
