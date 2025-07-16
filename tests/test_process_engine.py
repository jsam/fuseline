import json
from pathlib import Path

import pytest

from fuseline import Workflow
from fuseline.engines import ProcessEngine
from fuseline.storage import MemoryRuntimeStorage
from fuseline.workflow import Task, Status


class SimpleTask(Task):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def run_step(self, setup_res):
        print(self.label)
        return None


def test_process_engine_runs_tasks(tmp_path: Path) -> None:
    s1 = SimpleTask("a")
    s2 = SimpleTask("b")
    s1 >> s2
    wf = Workflow(outputs=[s2])
    store = MemoryRuntimeStorage()
    instance = wf.dispatch(runtime_store=store)
    names = wf._step_name_map()

    engine = ProcessEngine(wf, store)
    engine.work(instance)

    assert store.get_state(wf.workflow_id, instance, names[s1]) == store.get_state(
        wf.workflow_id, instance, names[s2]
    )
    assert store.get_result(wf.workflow_id, instance, names[s1]) is None
    assert store.get_result(wf.workflow_id, instance, names[s2]) is None


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
    s1 = FailingTask()
    s2 = SimpleTask("done")
    s1 >> s2
    wf = Workflow(outputs=[s2])
    store = MemoryRuntimeStorage()
    instance = wf.dispatch(runtime_store=store)
    names = wf._step_name_map()

    engine = ProcessEngine(wf, store)
    engine.work(instance)

    assert store.get_state(wf.workflow_id, instance, names[s2]) == Status.SUCCEEDED
    assert store.get_result(wf.workflow_id, instance, names[s2]) is None


def test_process_engine_ignores_unknown_step(tmp_path: Path) -> None:
    s = SimpleTask("only")
    wf = Workflow(outputs=[s])
    store = MemoryRuntimeStorage()
    instance = wf.dispatch(runtime_store=store)

    names = wf._step_name_map()

    # insert bogus step into queue
    store.enqueue(wf.workflow_id, instance, "ghost")

    engine = ProcessEngine(wf, store)
    engine.work(instance)

    assert store.get_state(wf.workflow_id, instance, names[s]) == Status.SUCCEEDED

