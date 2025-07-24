import time

import pytest

from fuseline.broker import MemoryBroker, RepositoryInfo, StepAssignment, StepReport
from fuseline.workflow import Status, Task, Workflow
from fuseline.workflow.policies import StepTimeoutPolicy


class Simple(Task):
    def run_step(self) -> None:
        pass


def test_assignment_lifecycle():
    s = Simple()
    s.policies.append(StepTimeoutPolicy(10.0))
    wf = Workflow(outputs=[s], workflow_id="wfa")
    broker = MemoryBroker()
    worker = broker.register_worker([wf.to_schema()])
    instance = broker.dispatch_workflow(wf.to_schema())

    assignment = broker.get_step(worker)
    assert isinstance(assignment, StepAssignment)
    assert assignment.expires_at - assignment.assigned_at == pytest.approx(60.0)
    assert broker._store.get_assignment(wf.workflow_id, instance, assignment.step_name)[0] == worker

    broker.report_step(
        worker,
        StepReport(
            workflow_id=assignment.workflow_id,
            instance_id=assignment.instance_id,
            step_name=assignment.step_name,
            state=Status.SUCCEEDED,
            result=None,
        ),
    )
    assert broker._store.get_assignment(wf.workflow_id, instance, assignment.step_name) is None


def test_worker_pruning(monkeypatch):
    s = Simple()
    wf = Workflow(outputs=[s], workflow_id="wfb")
    broker = MemoryBroker(worker_ttl=0.01)
    wid = broker.register_worker([wf.to_schema()])
    broker.keep_alive(wid)
    assert wid in broker._workers
    time.sleep(0.02)
    broker.get_step(wid)
    assert wid not in broker._workers


def test_repository_registration():
    broker = MemoryBroker()
    repo = RepositoryInfo(
        name="repo",
        url="http://example.com/repo.git",
        workflows=["pkg:wf"],
        credentials={"token": "x"},
    )
    broker.register_repository(repo)
    assert broker.get_repository("repo") == repo


def test_list_workers():
    broker = MemoryBroker()
    wid = broker.register_worker([])
    info = broker.list_workers()[0]
    assert info.worker_id == wid
    assert info.connected_at > 0


def test_list_repositories():
    broker = MemoryBroker()
    assert broker.list_repositories(page=1) == []
    repo = RepositoryInfo(name="r", url="u", workflows=[], credentials={})
    broker.register_repository(repo)
    assert broker.list_repositories(page=1) == [repo]
