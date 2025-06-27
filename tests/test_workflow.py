
from fuseline.workflow import (
    AsyncTask,
    AsyncWorkflow,
    Step,
    Workflow,
    workflow_from_functions,
)


class RecorderStep(Step):
    def __init__(self, log, label="step", action="default"):
        super().__init__()
        self.log = log
        self.label = label
        self.action = action
    def before_all(self, shared):
        self.log.append(f"{self.label}-before_all")
    def setup(self, shared):
        self.log.append(f"{self.label}-setup")
        return self.label
    def run_step(self, setup_res):
        self.log.append(f"{self.label}-run:{setup_res}")
        return self.action
    def teardown(self, shared, setup_res, exec_res):
        self.log.append(f"{self.label}-teardown")
        return exec_res
    def after_all(self, shared):
        self.log.append(f"{self.label}-after_all")


def test_step_run_lifecycle():
    log = []
    step = RecorderStep(log, label="s1", action="result")
    result = step.run(None)
    assert result == "result"
    assert log == [
        "s1-before_all",
        "s1-setup",
        "s1-run:s1",
        "s1-teardown",
        "s1-after_all",
    ]


def test_workflow_sequence():
    log = []
    s1 = RecorderStep(log, label="s1")
    s2 = RecorderStep(log, label="s2")
    s1 >> s2
    wf = Workflow(s1)
    wf.run(None)
    assert log == [
        "s1-before_all",
        "s1-setup",
        "s1-run:s1",
        "s1-teardown",
        "s1-after_all",
        "s2-before_all",
        "s2-setup",
        "s2-run:s2",
        "s2-teardown",
        "s2-after_all",
    ]


def test_workflow_conditional_transition():
    log = []
    s1 = RecorderStep(log, label="s1", action="skip")
    s2 = RecorderStep(log, label="s2")
    s3 = RecorderStep(log, label="s3")
    s1 >> s2
    (s1 - "skip") >> s3
    wf = Workflow(s1)
    wf.run(None)
    assert log == [
        "s1-before_all",
        "s1-setup",
        "s1-run:s1",
        "s1-teardown",
        "s1-after_all",
        "s3-before_all",
        "s3-setup",
        "s3-run:s3",
        "s3-teardown",
        "s3-after_all",
    ]


class AsyncRecorderStep(AsyncTask):
    def __init__(self, log, label="ast", action=None):
        super().__init__()
        self.log = log
        self.label = label
        self.action = action

    async def before_all_async(self, shared):
        self.log.append(f"{self.label}-before_all")

    async def setup_async(self, shared):
        self.log.append(f"{self.label}-setup")
        return self.label

    async def run_step_async(self, setup_res):
        self.log.append(f"{self.label}-run:{setup_res}")
        return self.action

    async def teardown_async(self, shared, setup_res, exec_res):
        self.log.append(f"{self.label}-teardown")
        return exec_res

    async def after_all_async(self, shared):
        self.log.append(f"{self.label}-after_all")

def test_async_workflow():
    log = []
    s1 = AsyncRecorderStep(log)
    wf = AsyncWorkflow(s1)

    import asyncio
    asyncio.run(wf.run_async(None))

    assert log == [
        "ast-before_all",
        "ast-setup",
        "ast-run:ast",
        "ast-teardown",
        "ast-after_all",
    ]

def test_typed_workflow():
    def multiply(x: int) -> int:
        return x * 2

    from fuseline import Depends
    from fuseline.typing import Computed

    def add_one(x: Computed[int] = Depends(multiply)) -> int:
        return x + 1

    wf = workflow_from_functions(outputs=[add_one])
    wf.start_step.params = {"x": 3}  # type: ignore[attr-defined]
    result = wf.run({})
    assert result == 7
