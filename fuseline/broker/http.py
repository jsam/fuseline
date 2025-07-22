from __future__ import annotations

import os

try:  # optional dependency
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional

    def load_dotenv() -> None:  # type: ignore
        return None


from dataclasses import asdict
from typing import Any, Iterable
import json

try:
    from robyn import Robyn, Response, status_codes
except Exception:  # pragma: no cover - optional

    class status_codes:  # pragma: no cover - minimal stub
        HTTP_204_NO_CONTENT = 204
        HTTP_404_NOT_FOUND = 404

    from typing import Any as _Any  # silence flake warnings

    class Response:  # pragma: no cover - minimal stub matching Robyn's API
        def __init__(
            self,
            description: str = "",
            status_code: int = 200,
            headers: list[tuple[str, str]] | None = None,
        ) -> None:
            self.description = description
            self.status_code = status_code
            self.headers = headers or []

    class Robyn:  # pragma: no cover - dummy stub for type checkers
        def __init__(self, *args: _Any, **kwargs: _Any) -> None: ...


from ..workflow import WorkflowSchema
from . import Broker, PostgresBroker, RepositoryInfo, StepReport
from .openapi import OPENAPI_SPEC, SWAGGER_HTML

__all__ = [
    "OPENAPI_SPEC",
    "SWAGGER_HTML",
    "create_app",
    "handle_dispatch_workflow",
    "handle_get_repository",
    "handle_get_step",
    "handle_keep_alive",
    "handle_status",
    "handle_get_workers",
    "handle_register_repository",
    "handle_register_worker",
    "handle_report_step",
    "main",
    "register_routes",
    "register_worker_routes",
    "register_repository_routes",
    "register_workflow_routes",
]


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
    async def register(request):  # pragma: no cover - integration
        payload = json.loads(request.body)
        return handle_register_worker(broker, payload)

    @app.post("/worker/keep-alive", openapi_tags=["worker"])
    async def keep_alive(request):  # pragma: no cover - integration
        wid = request.query_params.get("worker_id", None)
        handle_keep_alive(broker, wid)
        return ""

    @app.get("/workers", openapi_tags=["worker"])
    async def workers(request):  # pragma: no cover - integration
        return handle_get_workers(broker)

    @app.get("/status", openapi_tags=["system"])
    async def status(request):  # pragma: no cover - integration
        return handle_status(broker)


def register_repository_routes(app: Robyn, broker: Broker) -> None:
    """Register repository endpoints."""

    @app.post("/repository/register", openapi_tags=["repository"])
    async def register_repo(request):  # pragma: no cover - integration
        payload = json.loads(request.body)
        handle_register_repository(broker, payload)
        return ""

    @app.get("/repository", openapi_tags=["repository"])
    async def get_repo(request):  # pragma: no cover - integration
        name = request.query_params.get("name", None)
        data = handle_get_repository(broker, name)
        if data is None:
            return Response("", status_codes.HTTP_404_NOT_FOUND, [])
        return data


def register_workflow_routes(app: Robyn, broker: Broker) -> None:
    """Register workflow endpoints."""

    @app.post("/workflow/dispatch", openapi_tags=["workflow"])
    async def dispatch(request):  # pragma: no cover - integration
        payload = json.loads(request.body)
        return handle_dispatch_workflow(broker, payload)

    @app.get("/workflow/step", openapi_tags=["workflow"])
    async def get_step(request):  # pragma: no cover - integration
        wid = request.query_params.get("worker_id", None)
        data = handle_get_step(broker, wid)
        if data is None:
            return Response("", status_codes.HTTP_204_NO_CONTENT, [])
        return data

    @app.post("/workflow/step", openapi_tags=["workflow"])
    async def report_step(request):  # pragma: no cover - integration
        wid = request.query_params.get("worker_id", None)
        payload = json.loads(request.body)
        handle_report_step(broker, wid, payload)
        return ""


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
    host = os.environ.get("HOST", "0.0.0.0")
    create_app().start(port=port, host=host)


if __name__ == "__main__":  # pragma: no cover - manual start
    main()
