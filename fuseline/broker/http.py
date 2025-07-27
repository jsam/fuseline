import os

try:  # optional dependency
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional

    def load_dotenv() -> None:  # type: ignore
        return None


import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Type, TypeVar

try:
    from robyn import Response, Robyn
    from robyn import status_codes as robyn_status_codes
    from robyn.robyn import QueryParams, Request
    from robyn.types import Body, JSONResponse
except Exception:  # pragma: no cover - optional

    class StatusCodes:  # pragma: no cover - minimal stub
        HTTP_200_OK = 200
        HTTP_204_NO_CONTENT = 204
        HTTP_404_NOT_FOUND = 404

    robyn_status_codes = StatusCodes

    from typing import Any as _Any  # silence flake warnings

    class Response:  # pragma: no cover - minimal stub matching Robyn's API
        def __init__(
            self,
            status_code: int,
            headers: dict[str, str],
            description: str = "",
        ) -> None:
            self.status_code = status_code
            self.headers = headers
            self.description = description

    class Robyn:  # pragma: no cover - dummy stub for type checkers
        def __init__(self, *args: _Any, **kwargs: _Any) -> None: ...

    class Body:  # pragma: no cover - stub for typed requests
        pass

    class JSONResponse:  # pragma: no cover - stub for typed responses
        pass

    class QueryParams:  # pragma: no cover - stub for typed query parameters
        pass


from ..workflow import Status, WorkflowSchema
from . import Broker, PostgresBroker, RepositoryInfo, StepReport
from .openapi import OPENAPI_SPEC, SWAGGER_HTML

__all__ = [
    "OPENAPI_SPEC",
    "SWAGGER_HTML",
    "create_app",
    "handle_dispatch_workflow",
    "handle_get_repository",
    "handle_get_step",
    "handle_get_workers",
    "handle_keep_alive",
    "handle_list_workflows",
    "handle_register_repository",
    "handle_register_worker",
    "handle_report_step",
    "handle_status",
    "main",
    "register_repository_routes",
    "register_routes",
    "register_worker_routes",
    "register_workflow_routes",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

T = TypeVar("T")


def _coerce_dataclass(data: Any, model: Type[T]) -> T:
    """Convert ``data`` to an instance of ``model``."""

    if isinstance(data, model):
        return data
    if isinstance(data, (bytes, bytearray)):
        data = data.decode()
    if isinstance(data, str):
        data = json.loads(data or "{}")
    return model(**data)


# ---------------------------------------------------------------------------
# Typed request and response models
# ---------------------------------------------------------------------------

@dataclass
class WorkerRegisterBody(Body):
    workflows: list[dict]


@dataclass
class WorkerIdResponse(JSONResponse):
    worker_id: str


@dataclass
class KeepAliveQuery(QueryParams):
    worker_id: str


@dataclass
class StatusResponse(JSONResponse):
    status: str


@dataclass
class WorkersResponse(JSONResponse):
    workers: list[dict]


@dataclass
class RepositoryRegisterBody(Body):
    name: str
    url: str
    workflows: list[str]
    credentials: dict[str, str]


@dataclass
class RepositoryResponse(JSONResponse):
    repository: dict | list[dict] | None


@dataclass
class DispatchBody(Body):
    workflow: dict
    inputs: dict | None = None


@dataclass
class DispatchResponse(JSONResponse):
    instance_id: str


@dataclass
class StepQuery(QueryParams):
    worker_id: str


@dataclass
class StepBody(Body):
    workflow_id: str
    instance_id: str
    step_name: str
    state: Status
    result: dict | list | str | int | float | bool | None


@dataclass
class StepResponse(JSONResponse):
    step: dict | None


@dataclass
class WorkflowsResponse(JSONResponse):
    workflows: list[dict]


class RepositoryQuery(QueryParams):
    """Query parameters for repository retrieval."""

    name: str | None = None
    page: int = 1
    page_size: int = 50


def handle_register_worker(broker: Broker, payload: Iterable[dict[str, Any]]) -> str:
    """Register a worker using *payload* workflow schemas."""
    workflows = [WorkflowSchema(**wf) for wf in payload]
    return broker.register_worker(workflows)


def handle_register_repository(broker: Broker, payload: dict[str, Any]) -> None:
    """Store workflow repository information."""
    broker.register_repository(RepositoryInfo(**payload))


def handle_get_repository(broker: Broker, name: str) -> dict[str, Any] | None:
    repo = broker.get_repository(name)
    return asdict(repo) if repo else None


def handle_list_repositories(broker: Broker, page: int, page_size: int) -> list[dict[str, Any]]:
    repos = broker.list_repositories(page, page_size)
    return [asdict(r) for r in repos]


def handle_list_workflows(broker: Broker) -> list[dict[str, Any]]:
    """Return all registered workflows with their repositories."""
    workflows = broker.list_workflows()
    return [asdict(wf) for wf in workflows]


def handle_dispatch_workflow(broker: Broker, payload: dict[str, Any]) -> str:
    """Dispatch a new workflow run described by *payload*."""
    wf = WorkflowSchema(**payload["workflow"])
    return broker.dispatch_workflow(wf, payload.get("inputs"))


def handle_get_step(broker: Broker, worker_id: str) -> dict[str, Any] | None:
    """Return the next step assignment for *worker_id* if available."""
    assignment = broker.get_step(worker_id)
    if assignment is None:
        return None
    return asdict(assignment)


def handle_report_step(broker: Broker, worker_id: str, payload: dict[str, Any]) -> None:
    """Report completed step results back to the broker."""
    broker.report_step(worker_id, StepReport(**payload))


def handle_keep_alive(broker: Broker, worker_id: str) -> None:
    """Record that *worker_id* is still alive."""
    broker.keep_alive(worker_id)


def handle_status(broker: Broker) -> dict[str, str]:
    """Return broker health status."""
    return broker.status()


def handle_get_workers(broker: Broker) -> list[dict[str, Any]]:
    """Return status information for all connected workers."""
    return [asdict(w) for w in broker.list_workers()]


def register_worker_routes(app: Robyn, broker: Broker) -> None:
    """Register worker-related routes on *app*."""

    @app.post("/worker/register", openapi_tags=["worker"])
    def register(request: Request, body: WorkerRegisterBody) -> WorkerIdResponse:
        # pragma: no cover - integration
        body = _coerce_dataclass(body, WorkerRegisterBody)
        wid = handle_register_worker(broker, body.workflows)
        return WorkerIdResponse(worker_id=wid)

    @app.post("/worker/keep-alive", openapi_tags=["worker"])
    def keep_alive(query_params: KeepAliveQuery) -> JSONResponse:  # pragma: no cover - integration
        handle_keep_alive(broker, query_params.worker_id)
        return JSONResponse()

    @app.get("/workers", openapi_tags=["worker"])
    def workers() -> WorkersResponse:  # pragma: no cover - integration
        data = handle_get_workers(broker)
        return WorkersResponse(workers=data)

    @app.get("/status", openapi_tags=["system"])
    def status() -> StatusResponse:  # pragma: no cover - integration
        data = handle_status(broker)
        return StatusResponse(status=data["status"])


def register_repository_routes(app: Robyn, broker: Broker) -> None:
    """Register repository endpoints."""

    @app.post("/repository/register", openapi_tags=["repository"])
    def register_repo(body: RepositoryRegisterBody) -> JSONResponse:  # pragma: no cover - integration
        body = _coerce_dataclass(body, RepositoryRegisterBody)
        handle_register_repository(broker, asdict(body))
        return JSONResponse()

    @app.get("/repository", openapi_tags=["repository"])
    def get_repo(query_params: RepositoryQuery) -> RepositoryResponse:
        # pragma: no cover - integration
        name = query_params.name
        page = query_params.page
        if name:
            data = handle_get_repository(broker, name)
            if data is None:
                return RepositoryResponse(repository=None)
            payload = data
        else:
            repos = handle_list_repositories(broker, page, query_params.page_size)
            if not repos and page > 1:
                return RepositoryResponse(repository=None)
            payload = repos
        return RepositoryResponse(repository=payload)


def register_workflow_routes(app: Robyn, broker: Broker) -> None:
    """Register workflow endpoints."""

    @app.post("/workflow/dispatch", openapi_tags=["workflow"])
    def dispatch(body: DispatchBody) -> DispatchResponse:  # pragma: no cover - integration
        body = _coerce_dataclass(body, DispatchBody)
        instance = handle_dispatch_workflow(broker, asdict(body))
        return DispatchResponse(instance_id=instance)

    @app.get("/workflow/step", openapi_tags=["workflow"])
    def get_step(query_params: StepQuery) -> StepResponse:  # pragma: no cover - integration
        data = handle_get_step(broker, query_params.worker_id)
        return StepResponse(step=data)

    @app.post("/workflow/step", openapi_tags=["workflow"])
    def report_step(query_params: StepQuery, body: StepBody) -> JSONResponse:  # pragma: no cover - integration
        body = _coerce_dataclass(body, StepBody)
        handle_report_step(broker, query_params.worker_id, asdict(body))
        return JSONResponse()

    @app.get("/workflows", openapi_tags=["workflow"])
    def list_wfs() -> WorkflowsResponse:  # pragma: no cover - integration
        data = handle_list_workflows(broker)
        return WorkflowsResponse(workflows=data)


def register_routes(app: Robyn, broker: Broker) -> None:
    """Register all broker API routes on *app*."""

    register_repository_routes(app, broker)
    register_worker_routes(app, broker)
    register_workflow_routes(app, broker)


def create_app(dsn: str | None = None, broker: Broker | None = None) -> Robyn:
    """Return a Robyn app exposing the broker API."""
    load_dotenv()
    if broker is None:
        dsn = dsn or os.environ.get("DATABASE_URL")
        broker = PostgresBroker(dsn)
    app = Robyn(__file__)
    register_routes(app, broker)
    app.openapi_spec = OPENAPI_SPEC
    app.swagger_html = SWAGGER_HTML
    return app


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104 - external binding
    create_app().start(port=port, host=host)


if __name__ == "__main__":  # pragma: no cover - manual start
    main()
