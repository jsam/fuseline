from pathlib import Path

from fuseline import Workflow
from fuseline.broker import MemoryBroker
from fuseline.broker.clients import LocalBrokerClient
from fuseline.worker import ProcessEngine
from fuseline.workflow.policies import RetryPolicy
from fuseline.workflow import Status, Task


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
    wf = Workflow(outputs=[s2], workflow_id="wf1")
    broker = MemoryBroker()
    client = LocalBrokerClient(broker)
    instance = client.dispatch_workflow(wf.to_schema())
    names = wf._step_name_map()

    engine = ProcessEngine(client, [wf])
    engine.work()

    store = broker._store
    assert store.get_state(wf.workflow_id, instance, names[s1]) == store.get_state(wf.workflow_id, instance, names[s2])
    assert store.get_result(wf.workflow_id, instance, names[s1]) is None
    assert store.get_result(wf.workflow_id, instance, names[s2]) is None


class FailingTask(Task):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0
        self.policies.append(RetryPolicy(max_retries=2))

    def run_step(self, setup_res):
        self.calls += 1
        if self.calls < 2:
            raise RuntimeError("boom")
        return None


def test_process_engine_retry_success(tmp_path: Path) -> None:
    s1 = FailingTask()
    s2 = SimpleTask("done")
    s1 >> s2
    wf = Workflow(outputs=[s2], workflow_id="wf2")
    broker = MemoryBroker()
    client = LocalBrokerClient(broker)
    instance = client.dispatch_workflow(wf.to_schema())
    names = wf._step_name_map()

    engine = ProcessEngine(client, [wf])
    engine.work()

    store = broker._store
    assert store.get_state(wf.workflow_id, instance, names[s2]) == Status.SUCCEEDED
    assert store.get_result(wf.workflow_id, instance, names[s2]) is None


def test_process_engine_ignores_unknown_step(tmp_path: Path) -> None:
    s = SimpleTask("only")
    wf = Workflow(outputs=[s], workflow_id="wf3")
    broker = MemoryBroker()
    client = LocalBrokerClient(broker)
    instance = client.dispatch_workflow(wf.to_schema())

    names = wf._step_name_map()

    # insert bogus step into queue
    broker._store.enqueue(wf.workflow_id, instance, "ghost")

    engine = ProcessEngine(client, [wf])
    engine.work()

    store = broker._store
    assert store.get_state(wf.workflow_id, instance, names[s]) == Status.SUCCEEDED
