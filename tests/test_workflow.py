import json
import re

from fuseline import Computed, Depends
from fuseline.workflow import (
    AsyncTask,
    AsyncWorkflow,
    Task,
    Workflow,
    workflow_from_functions,
)


class RecorderStep(Task):
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
    wf = Workflow(outputs=[s2])
    wf.run()
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
    wf = Workflow(outputs=[s2, s3])
    wf.run()
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
    wf = AsyncWorkflow(outputs=[s1])

    import asyncio

    asyncio.run(wf.run_async({}))

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

    from fuseline import Computed, Depends

    def add_one(x: Computed[int] = Depends(multiply)) -> int:
        return x + 1

    wf = workflow_from_functions(outputs=[add_one])
    result = wf.run({"x": 3})
    assert result == 7


class AddTask(Task):
    def run_step(self, x: int, y: int) -> int:
        return x + y


class MulTask(Task):
    add_step = AddTask()

    def run_step(self, val: Computed[int] = Depends(add_step)) -> int:
        return val * 2


def test_typed_step_dependencies():
    mul = MulTask()
    wf = Workflow(outputs=[mul])
    result = wf.run({"x": 2, "y": 3})
    assert result == 10


def test_workflow_export(tmp_path):
    class LocalAdd(Task):
        def run_step(self, x: int, y: int) -> int:
            return x + y

    class LocalMul(Task):
        add_step = LocalAdd()

        def run_step(self, val: Computed[int] = Depends(add_step)) -> int:
            return val * 2

    add = LocalAdd()
    mul = LocalMul()
    add >> mul
    wf = Workflow(outputs=[mul])
    path = tmp_path / "wf.yaml"
    wf.export(str(path))

    text = path.read_text().splitlines()
    steps = set()
    edges: dict[str, list[str]] = {}
    deps: dict[str, list[str]] = {}
    current = None
    for line in text:
        m = re.match(r"\s*(step\d+):", line)
        if m:
            current = m.group(1)
            steps.add(current)
        m = re.match(r"\s*outputs:\s*", line)
        if m:
            current = "outputs"
            edges[current] = []
        m = re.match(r"\s*-\s*(step\d+)", line)
        if m and current:
            if current == "outputs":
                edges.setdefault("outputs", []).append(m.group(1))
            else:
                edges.setdefault(current, []).append(m.group(1))
        m = re.match(r"\s*(\w+):\s*(step\d+)", line)
        if m and current:
            deps.setdefault(current, []).append(m.group(2))
        m = re.match(r"\s*step:\s*(step\d+)", line)
        if m and current:
            deps.setdefault(current, []).append(m.group(1))

    assert edges.get("outputs")
    for lst in edges.values():
        for sid in lst:
            assert sid in steps
    for lst in deps.values():
        for sid in lst:
            assert sid in steps


def test_export_with_condition(tmp_path):
    class Equals:
        def __init__(self, expected: int) -> None:
            self.expected = expected

        def __call__(self, value: int) -> bool:  # pragma: no cover - trivial
            return value == self.expected

    class Dec(Task):
        def run_step(self, flag: int) -> int:
            return flag

    dec = Dec()

    class Left(Task):
        def run_step(self, _flag: int = Depends(dec, condition=Equals(1))) -> None:
            pass

    class Right(Task):
        def run_step(self, _flag: int = Depends(dec, condition=Equals(2))) -> None:
            pass

    wf = Workflow(outputs=[Left(), Right()])
    path = tmp_path / "cond.yaml"
    wf.export(path)

    text = path.read_text()
    assert "expected: 1" in text
    assert "expected: 2" in text


def test_workflow_trace(tmp_path):
    class A(Task):
        def run_step(self) -> int:
            return 1

    class B(Task):
        a = A()

        def run_step(self, val: Computed[str] = Depends(a)) -> None:
            pass

    b = B()
    trace_path = tmp_path / "trace.log"
    wf = Workflow(outputs=[b], trace=str(trace_path))
    wf.run({})
    entries = [json.loads(line) for line in trace_path.read_text().splitlines()]
    assert [e["event"] for e in entries] == [
        "workflow_started",
        "step_enqueued",
        "step_started",
        "step_finished",
        "step_enqueued",
        "step_started",
        "step_finished",
        "workflow_finished",
    ]
    assert entries[2]["step"] == "A"
    assert entries[5]["step"] == "B"
    workflow_id = entries[0]["workflow_id"]
    instance_id = entries[0]["workflow_instance_id"]
    for e in entries:
        assert e["workflow_id"] == workflow_id
        assert e["workflow_instance_id"] == instance_id
        assert "timestamp" in e


def test_trace_with_conditions(tmp_path):
    class Dec(Task):
        def run_step(self, flag: bool) -> bool:
            return flag

    dec = Dec()

    class B1(Task):
        def run_step(self, _flag: bool = Depends(dec, condition=lambda x: x)) -> None:
            pass

    class B2(Task):
        def run_step(self, _flag: bool = Depends(dec, condition=lambda x: not x)) -> None:
            pass

    b1 = B1()
    b2 = B2()
    wf = Workflow(outputs=[b1, b2], trace=str(tmp_path / "trace.log"))
    wf.run({"flag": True})
    lines = (tmp_path / "trace.log").read_text().splitlines()
    events = [json.loads(line) for line in lines]
    assert any(e.get("step") == "B2" and e["event"] == "step_finished" and e["skipped"] for e in events)
    wf_id = events[0]["workflow_id"]
    inst_id = events[0]["workflow_instance_id"]
    for e in events:
        assert e["workflow_id"] == wf_id
        assert e["workflow_instance_id"] == inst_id
        assert "timestamp" in e


def test_trace_multiple_runs(tmp_path) -> None:
    class Dec(Task):
        def run_step(self, flag: bool) -> bool:  # pragma: no cover - trivial
            return flag

    dec = Dec()

    class Left(Task):
        def run_step(self, _flag: bool = Depends(dec, condition=lambda x: x)) -> None:  # pragma: no cover - simple
            pass

    class Right(Task):
        def run_step(self, _flag: bool = Depends(dec, condition=lambda x: not x)) -> None:  # pragma: no cover - simple
            pass

    left = Left()
    right = Right()
    trace_path = tmp_path / "trace.log"
    wf = Workflow(outputs=[left, right], trace=str(trace_path))
    wf.run({"flag": True})
    wf.run({"flag": False})

    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    started = [e for e in events if e["event"] == "workflow_started"]
    assert len(started) == 2
    assert len({e["workflow_instance_id"] for e in started}) == 2
