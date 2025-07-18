from __future__ import annotations

import os

try:  # optional dependency
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional
    def load_dotenv() -> None:  # type: ignore
        return None

from robyn import Robyn

from . import PostgresBroker, StepReport
from ..workflow import WorkflowSchema


def create_app(dsn: str | None = None) -> Robyn:
    """Return a Robyn app exposing the broker API."""
    load_dotenv()
    dsn = dsn or os.environ.get("DATABASE_URL")
    broker = PostgresBroker(dsn)
    app = Robyn(__file__)

    @app.post("/worker/register")
    async def register(request):  # pragma: no cover - integration
        workflows = [WorkflowSchema(**wf) for wf in request.json]
        return broker.register_worker(workflows)

    @app.post("/workflow/dispatch")
    async def dispatch(request):  # pragma: no cover - integration
        wf = WorkflowSchema(**request.json["workflow"])
        return broker.dispatch_workflow(wf, request.json.get("inputs"))

    @app.get("/workflow/step")
    async def get_step(request):  # pragma: no cover - integration
        wid = request.qs_params.get("worker_id")
        assignment = broker.get_step(wid)
        if assignment is None:
            return {"status_code": 204}
        return assignment.model_dump()

    @app.post("/workflow/step")
    async def report_step(request):  # pragma: no cover - integration
        wid = request.qs_params.get("worker_id")
        broker.report_step(wid, StepReport(**request.json))
        return ""

    return app


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    create_app().start(port=port)


if __name__ == "__main__":  # pragma: no cover - manual start
    main()
