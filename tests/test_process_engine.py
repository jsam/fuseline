import json
from pathlib import Path

from fuseline import Workflow
from fuseline.engines import ProcessEngine
from fuseline.storage import FileRuntimeStorage
from fuseline.workflow import Task


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
    store = FileRuntimeStorage(tmp_path.as_posix())
    instance = wf.dispatch(runtime_store=store)

    engine = ProcessEngine(wf, store)
    engine.work(instance)

    data = json.loads(next(tmp_path.iterdir()).read_text())
    assert data["finished"] is True
    assert len(data["states"]) == 2
    assert set(data["states"].values()) == {"SUCCEEDED"}


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
    store = FileRuntimeStorage(tmp_path.as_posix())
    instance = wf.dispatch(runtime_store=store)

    engine = ProcessEngine(wf, store)
    engine.work(instance)

    data = json.loads(next(tmp_path.iterdir()).read_text())
    assert data["finished"] is True
    assert set(data["states"].values()) == {"SUCCEEDED"}


def test_process_engine_ignores_unknown_step(tmp_path: Path) -> None:
    s = SimpleTask("only")
    wf = Workflow(outputs=[s])
    store = FileRuntimeStorage(tmp_path.as_posix())
    instance = wf.dispatch(runtime_store=store)

    file = next(tmp_path.iterdir())
    payload = json.loads(file.read_text())
    payload["queue"].insert(0, "ghost")
    file.write_text(json.dumps(payload))

    engine = ProcessEngine(wf, store)
    engine.work(instance)

    data = json.loads(file.read_text())
    assert data["finished"] is True
    assert set(data["states"].values()) == {"SUCCEEDED"}
    assert not data["queue"]
