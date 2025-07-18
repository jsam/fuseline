import pytest

from fuseline.workflow import Step, Workflow
from fuseline.policies import StepPolicy, WorkflowPolicy


class BinderStepPolicy(StepPolicy):
    def __init__(self) -> None:
        self.bound_to = None

    def attach_to_step(self, step: Step) -> None:
        self.bound_to = step


class BinderWorkflowPolicy(WorkflowPolicy):
    def __init__(self) -> None:
        self.bound_to = None

    def attach_to_workflow(self, wf: Workflow) -> None:
        self.bound_to = wf


class Simple(Step):
    def run_step(self) -> str:
        return "ok"


def test_policy_binding() -> None:
    sp = BinderStepPolicy()
    wp = BinderWorkflowPolicy()
    s = Simple(policies=[sp])
    wf = Workflow(outputs=[s], policies=[wp])
    assert sp.bound_to is s
    assert wp.bound_to is wf
