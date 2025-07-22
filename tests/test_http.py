import pytest

pytest.importorskip("robyn")

from fuseline.broker import MemoryBroker
from fuseline.broker.http import (
    OPENAPI_SPEC,
    SWAGGER_HTML,
    create_app,
    handle_dispatch_workflow,
    handle_get_repository,
    handle_get_step,
    handle_keep_alive,
    handle_status,
    handle_get_workers,
    handle_register_repository,
    handle_register_worker,
    handle_report_step,
)
from fuseline.workflow import Status, Task, Workflow


class Simple(Task):
    def run_step(self):
        return "ok"


def test_handler_flow():
    s = Simple()
    wf = Workflow(outputs=[s], workflow_id="wf")
    broker = MemoryBroker()

    wid = handle_register_worker(broker, [wf.to_schema()])
    instance = handle_dispatch_workflow(broker, {"workflow": wf.to_schema()})

    assignment = handle_get_step(broker, wid)
    assert assignment is not None
    assert assignment["workflow_id"] == wf.workflow_id
    assert assignment["instance_id"] == instance

    handle_report_step(
        broker,
        wid,
        {
            "workflow_id": wf.workflow_id,
            "instance_id": instance,
            "step_name": assignment["step_name"],
            "state": Status.SUCCEEDED,
            "result": None,
        },
    )

    assert handle_get_step(broker, wid) is None


def test_keep_alive_handler():
    s = Simple()
    wf = Workflow(outputs=[s], workflow_id="wf2")
    broker = MemoryBroker()
    wid = handle_register_worker(broker, [wf.to_schema()])
    handle_keep_alive(broker, wid)
    assert wid in broker._last_seen


def test_create_app_returns_robyn():
    robyn = pytest.importorskip("robyn")
    app = create_app(broker=MemoryBroker())
    assert isinstance(app, robyn.Robyn)


def test_repository_handlers():
    broker = MemoryBroker()
    payload = {
        "name": "repo",
        "url": "http://example.com/repo.git",
        "workflows": ["pkg:wf"],
        "credentials": {},
    }
    handle_register_repository(broker, payload)
    repo = handle_get_repository(broker, "repo")
    assert repo["url"] == payload["url"]


def test_status_and_list_workers():
    broker = MemoryBroker()
    assert handle_status(broker)["status"] == "ok"
    wid = handle_register_worker(broker, [])
    workers = handle_get_workers(broker)
    assert wid in workers


def test_openapi_constants():
    assert "/worker/register" in OPENAPI_SPEC["paths"]
    assert "swagger-ui" in SWAGGER_HTML
