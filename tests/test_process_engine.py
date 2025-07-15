import json
import os
from pathlib import Path

import pytest

from fuseline import Workflow
from fuseline.engines import ProcessEngine
from fuseline.storage import PostgresRuntimeStorage
from fuseline.workflow import Task, Status


class SimpleTask(Task):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def run_step(self, setup_res):
        print(self.label)
        return None


def test_process_engine_runs_tasks(tmp_path: Path) -> None:
    dsn = os.environ.get("FUSELINE_PG_DSN")
    if not dsn:
        pytest.skip("PostgreSQL not available")
    s1 = SimpleTask("a")
    s2 = SimpleTask("b")
    s1 >> s2
    wf = Workflow(outputs=[s2])
    store = PostgresRuntimeStorage(dsn)
    instance = wf.dispatch(runtime_store=store)

    engine = ProcessEngine(wf, store)
    engine.work(instance)

    assert store.get_state(wf.workflow_id, instance, "a") == store.get_state(
        wf.workflow_id, instance, "b"
    )


class FailingTask(Task):
    def __init__(self) -> None:
        super().__init__(max_retries=2)
        self.calls = 0

    def run_step(self, setup_res):
        self.calls += 1
        if self.calls < 2:
            raise RuntimeError("boom")
        return None


def test_process_engine_retry_success(tmp_path: Path) -> None:
    dsn = os.environ.get("FUSELINE_PG_DSN")
    if not dsn:
        pytest.skip("PostgreSQL not available")
    s1 = FailingTask()
    s2 = SimpleTask("done")
    s1 >> s2
    wf = Workflow(outputs=[s2])
    store = PostgresRuntimeStorage(dsn)
    instance = wf.dispatch(runtime_store=store)

    engine = ProcessEngine(wf, store)
    engine.work(instance)

    assert store.get_state(wf.workflow_id, instance, "done") == Status.SUCCEEDED


def test_process_engine_ignores_unknown_step(tmp_path: Path) -> None:
    dsn = os.environ.get("FUSELINE_PG_DSN")
    if not dsn:
        pytest.skip("PostgreSQL not available")
    s = SimpleTask("only")
    wf = Workflow(outputs=[s])
    store = PostgresRuntimeStorage(dsn)
    instance = wf.dispatch(runtime_store=store)

    with store.conn.cursor() as cur:
        cur.execute(
            "INSERT INTO step_queue (workflow_id, instance_id, step_name) VALUES (%s, %s, %s)",
            (wf.workflow_id, instance, "ghost"),
        )
    store.conn.commit()

    engine = ProcessEngine(wf, store)
    engine.work(instance)

    assert store.get_state(wf.workflow_id, instance, "only") == Status.SUCCEEDED

