from pathlib import Path

from fuseline import Workflow
import os

import pytest

from fuseline.storage import PostgresRuntimeStorage
from fuseline.workflow import Task, Status


class SimpleTask(Task):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def run_step(self, setup_res):
        print(self.label)
        return None


def test_postgres_runtime_storage(tmp_path: Path) -> None:
    dsn = os.environ.get("FUSELINE_PG_DSN")
    if not dsn:
        pytest.skip("PostgreSQL not available")
    s1 = SimpleTask("a")
    s2 = SimpleTask("b")
    s1 >> s2
    store = PostgresRuntimeStorage(dsn)
    wf = Workflow(outputs=[s2])
    wf.run(runtime_store=store)
    # fetch states from DB
    assert (
        store.get_state(wf.workflow_id, wf.workflow_instance_id, "a")
        == store.get_state(wf.workflow_id, wf.workflow_instance_id, "b")
        == Status.SUCCEEDED
    )
