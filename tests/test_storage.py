from pathlib import Path

from fuseline import Workflow
from fuseline.broker import MemoryBroker
from fuseline.connectors import LocalBrokerConnector
from fuseline.engines import ProcessEngine
from fuseline.workflow import Status, Task


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
    broker = MemoryBroker()
    connector = LocalBrokerConnector(broker)
    wf = Workflow(outputs=[s2], workflow_id="wf-store")
    wf.dispatch(broker)
    engine = ProcessEngine(connector, [wf])
    engine.work()
    names = wf._step_name_map()
    store = broker._store
    assert (
        store.get_state(wf.workflow_id, wf.workflow_instance_id, names[s1])
        == store.get_state(wf.workflow_id, wf.workflow_instance_id, names[s2])
        == Status.SUCCEEDED
    )
    assert store.get_result(wf.workflow_id, wf.workflow_instance_id, names[s1]) == "a"
    assert store.get_result(wf.workflow_id, wf.workflow_instance_id, names[s2]) == "b"
    assert store.get_inputs(wf.workflow_id, wf.workflow_instance_id) == {}
