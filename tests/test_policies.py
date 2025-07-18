import pytest

import time
import asyncio

from fuseline.workflow import AsyncStep

from fuseline.workflow import Step, Workflow, Status
from fuseline.policies import StepPolicy, WorkflowPolicy, StepTimeoutPolicy


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


class SlowStep(Step):
    def run_step(self) -> None:
        time.sleep(0.1)


def test_step_timeout() -> None:
    s = SlowStep(policies=[StepTimeoutPolicy(0.01)])
    wf = Workflow(outputs=[s])
    wf.run()
    assert wf.state == Status.FAILED


class AsyncSlowStep(AsyncStep):
    async def run_step_async(self) -> None:  # type: ignore[override]
        await asyncio.sleep(0.1)


def test_step_timeout_async() -> None:
    from fuseline.workflow import AsyncWorkflow

    s = AsyncSlowStep(policies=[StepTimeoutPolicy(0.01)])
    wf = AsyncWorkflow(outputs=[s])
    asyncio.run(wf.run_async())
    assert wf.state == Status.FAILED
