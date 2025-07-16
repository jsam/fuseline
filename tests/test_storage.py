from pathlib import Path

from fuseline import Workflow

from fuseline.storage import MemoryRuntimeStorage
from fuseline.workflow import Task, Status


class SimpleTask(Task):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def run_step(self, setup_res):
        print(self.label)
        return None


def test_memory_runtime_storage(tmp_path: Path) -> None:
    s1 = SimpleTask("a")
    s2 = SimpleTask("b")
    s1 >> s2
    store = MemoryRuntimeStorage()
    wf = Workflow(outputs=[s2])
    wf.run(runtime_store=store)
    names = wf._step_name_map()
    assert (
        store.get_state(wf.workflow_id, wf.workflow_instance_id, names[s1])
        == store.get_state(wf.workflow_id, wf.workflow_instance_id, names[s2])
        == Status.SUCCEEDED
    )
