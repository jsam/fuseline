import json
from pathlib import Path

from fuseline import Workflow
from fuseline.storage import FileRuntimeStorage
from fuseline.workflow import Task


class SimpleTask(Task):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def run_step(self, setup_res):
        print(self.label)
        return None


def test_file_runtime_storage(tmp_path: Path) -> None:
    s1 = SimpleTask("a")
    s2 = SimpleTask("b")
    s1 >> s2
    store = FileRuntimeStorage(tmp_path.as_posix())
    wf = Workflow(outputs=[s2])
    wf.run(runtime_store=store)
    files = list(tmp_path.iterdir())
    assert files
    data = json.loads(files[0].read_text())
    assert data["finished"] is True
    assert len(data["states"]) == 2
    assert set(data["states"].values()) == {"SUCCEEDED"}
