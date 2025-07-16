from pathlib import Path

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
        return self.label


def test_memory_runtime_storage(tmp_path: Path) -> None:
    s1 = SimpleTask("a")
    s2 = SimpleTask("b")
    (s1 - "a") >> s2
    store = MemoryRuntimeStorage()
    wf = Workflow(outputs=[s2])
    instance = wf.dispatch(runtime_store=store)
    engine = ProcessEngine(wf, store)
    engine.work(instance)
    names = wf._step_name_map()
    assert (
        store.get_state(wf.workflow_id, wf.workflow_instance_id, names[s1])
        == store.get_state(wf.workflow_id, wf.workflow_instance_id, names[s2])
        == Status.SUCCEEDED
    )
    assert store.get_result(wf.workflow_id, wf.workflow_instance_id, names[s1]) == "a"
    assert store.get_result(wf.workflow_id, wf.workflow_instance_id, names[s2]) == "b"
    assert store.get_inputs(wf.workflow_id, wf.workflow_instance_id) == {}
