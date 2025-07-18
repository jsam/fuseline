import pytest

from fuseline.broker import MemoryBroker, StepAssignment, StepReport
from fuseline.policies import StepTimeoutPolicy
from fuseline.workflow import Status, Task, Workflow


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
    assert (
        broker._store.get_assignment(wf.workflow_id, instance, assignment.step_name)[0]
        == worker
    )

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
    assert (
        broker._store.get_assignment(wf.workflow_id, instance, assignment.step_name)
        is None
    )
