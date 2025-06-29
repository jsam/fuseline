import json
import re
import time
from typing import Any

import pytest

from fuseline import Computed, Depends, ProcessEngine
from fuseline.workflow import (
    AsyncTask,
    AsyncWorkflow,
    Condition,
    Step,
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
    assert sum("execution_group:" in line for line in text) == len(steps)


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
    process_id = entries[0]["process_id"]
    host_id = entries[0]["host_id"]
    for e in entries:
        assert e["workflow_id"] == workflow_id
        assert e["workflow_instance_id"] == instance_id
        assert e["process_id"] == process_id
        assert e["host_id"] == host_id
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
        def run_step(
            self, _flag: bool = Depends(dec, condition=lambda x: not x)
        ) -> None:
            pass

    b1 = B1()
    b2 = B2()
    wf = Workflow(outputs=[b1, b2], trace=str(tmp_path / "trace.log"))
    wf.run({"flag": True})
    lines = (tmp_path / "trace.log").read_text().splitlines()
    events = [json.loads(line) for line in lines]
    assert any(
        e.get("step") == "B2" and e["event"] == "step_finished" and e["skipped"]
        for e in events
    )
    wf_id = events[0]["workflow_id"]
    inst_id = events[0]["workflow_instance_id"]
    proc_id = events[0]["process_id"]
    host_id = events[0]["host_id"]
    for e in events:
        assert e["workflow_id"] == wf_id
        assert e["workflow_instance_id"] == inst_id
        assert e["process_id"] == proc_id
        assert e["host_id"] == host_id
        assert "timestamp" in e


def test_trace_multiple_runs(tmp_path) -> None:
    class Dec(Task):
        def run_step(self, flag: bool) -> bool:  # pragma: no cover - trivial
            return flag

    dec = Dec()

    class Left(Task):
        def run_step(
            self, _flag: bool = Depends(dec, condition=lambda x: x)
        ) -> None:  # pragma: no cover - simple
            pass

    class Right(Task):
        def run_step(
            self, _flag: bool = Depends(dec, condition=lambda x: not x)
        ) -> None:  # pragma: no cover - simple
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


def test_execution_groups_order() -> None:
    log: list[str] = []

    class Rec(Task):
        def __init__(self, label: str) -> None:
            super().__init__()
            self.label = label

        def run_step(self, setup_res: Any) -> None:  # pragma: no cover - simple
            log.append(self.label)

    s1 = Rec("s1")
    s2 = Rec("s2")
    s2 >> s1
    wf = Workflow(outputs=[s1])
    wf.run(execution_engine=ProcessEngine())

    assert log == ["s2", "s1"]


def test_linear_chain_execution_time() -> None:
    """Verify sequential execution order and timing in a simple chain."""

    class SleepTask(Task):
        def __init__(self, label: str, duration: float) -> None:
            super().__init__()
            self.label = label
            self.duration = duration
            self.start: float | None = None
            self.end: float | None = None

        def run_step(self, setup_res: Any) -> str | None:
            self.start = time.perf_counter()
            time.sleep(self.duration)
            self.end = time.perf_counter()
            return "SUCCESS" if self.label == "C" else None

    a = SleepTask("A", 0.05)
    b = SleepTask("B", 0.05)
    c = SleepTask("C", 0.05)

    a >> b
    b >> c

    wf = Workflow(outputs=[c])

    start = time.perf_counter()
    result = wf.run(execution_engine=ProcessEngine())
    elapsed = time.perf_counter() - start

    assert result == "SUCCESS"
    assert (
        a.end is not None
        and b.start is not None
        and b.end is not None
        and c.start is not None
    )
    assert a.end <= b.start
    assert b.end <= c.start
    assert elapsed == pytest.approx(a.duration + b.duration + c.duration, rel=0.2)


def test_parallel_fan_out_join_execution_time(tmp_path) -> None:
    """Verify parallel scheduling, join behaviour and single execution."""

    class SleepTask(Task):
        def __init__(self, duration: float, result: int | None = None) -> None:
            super().__init__()
            self.duration = duration
            self.result = result
            self.start: float | None = None
            self.end: float | None = None

        def run_step(self, setup_res: Any) -> int | None:  # pragma: no cover - simple
            self.start = time.perf_counter()
            time.sleep(self.duration)
            self.end = time.perf_counter()
            return self.result

    class StartStep(SleepTask):
        pass

    class P1Step(SleepTask):
        pass

    class P2Step(SleepTask):
        pass

    start_step = StartStep(0.05)
    p1 = P1Step(0.1, 1)
    p2 = P2Step(0.05, 2)

    class JoinTask(Task):
        def __init__(self, duration: float) -> None:
            super().__init__()
            self.duration = duration
            self.start: float | None = None
            self.end: float | None = None

        def run_step(
            self,
            val1: Computed[int] = Depends(p1),
            val2: Computed[int] = Depends(p2),
        ) -> list[str]:
            self.start = time.perf_counter()
            time.sleep(self.duration)
            self.end = time.perf_counter()
            return [f"op{val1}", f"op{val2}"]

    join = JoinTask(0.05)

    start_step >> p1
    start_step >> p2
    p1 >> join
    p2 >> join

    trace_path = tmp_path / "trace.log"
    wf = Workflow(outputs=[join], trace=str(trace_path))

    start_time = time.perf_counter()
    result = wf.run(execution_engine=ProcessEngine(2))
    elapsed = time.perf_counter() - start_time

    assert result == ["op1", "op2"]

    assert (
        start_step.end is not None
        and p1.start is not None
        and p2.start is not None
        and join.start is not None
        and p1.end is not None
        and p2.end is not None
    )

    assert start_step.end <= p1.start
    assert start_step.end <= p2.start
    assert max(p1.end, p2.end) <= join.start
    assert elapsed == pytest.approx(
        start_step.duration + max(p1.duration, p2.duration) + join.duration,
        rel=0.3,
    )

    assert (
        start_step.execution_group
        < p1.execution_group
        == p2.execution_group
        < join.execution_group
    )

    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    start_started = [
        e for e in events if e["event"] == "step_started" and e["step"] == "StartStep"
    ]
    start_finished = [
        e for e in events if e["event"] == "step_finished" and e["step"] == "StartStep"
    ]
    join_started = [
        e for e in events if e["event"] == "step_started" and e["step"] == "JoinTask"
    ]
    join_finished = [
        e for e in events if e["event"] == "step_finished" and e["step"] == "JoinTask"
    ]

    assert len(start_started) == len(start_finished) == 1
    assert len(join_started) == len(join_finished) == 1


def test_multi_target_outputs(tmp_path) -> None:
    """Verify fan-out from one task into two independent branches."""

    class A(Task):
        def run_step(self) -> dict:
            return {"payload": object()}

    a = A()

    class B(Task):
        def __init__(self) -> None:
            super().__init__()
            self.seen: Any | None = None

        def run_step(self, data: Computed[dict] = Depends(a)) -> dict:
            self.seen = data
            return {"result": "B"}

    class C(Task):
        def __init__(self) -> None:
            super().__init__()
            self.seen: Any | None = None

        def run_step(self, data: Computed[dict] = Depends(a)) -> dict:
            self.seen = data
            return {"result": "C"}

    b = B()
    c = C()

    class D(Task):
        def run_step(self, val: Computed[dict] = Depends(b)) -> str:
            return f"{val['result']}\N{MULTIPLICATION X}"

    class E(Task):
        def run_step(self, val: Computed[dict] = Depends(c)) -> str:
            return f"{val['result']}\N{MULTIPLICATION X}"

    d = D()
    e = E()

    a >> b
    a >> c
    b >> d
    c >> e

    trace_path = tmp_path / "trace.log"
    wf = Workflow(outputs=[d, e], trace=str(trace_path))

    result = wf.run(execution_engine=ProcessEngine(2))

    assert result == ["B\N{MULTIPLICATION X}", "C\N{MULTIPLICATION X}"]
    assert b.seen is c.seen
    assert (
        a.execution_group
        < b.execution_group
        == c.execution_group
        < d.execution_group
        == e.execution_group
    )

    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    started = [e["step"] for e in events if e["event"] == "step_started"]
    assert started[0] == "A"
    assert set(started[1:3]) == {"B", "C"}
    assert set(started[3:5]) == {"D", "E"}


def test_edge_skipped_false_condition(tmp_path) -> None:
    """TC-04: Verify that a false edge-condition prevents the target task."""

    class Start(Task):
        def run_step(self, payload: dict) -> dict:
            return payload

    start = Start()

    class Validate(Task):
        def run_step(self, payload: Computed[dict] = Depends(start)) -> str:
            return "valid" if payload["valid"] else "reject"

    validate = Validate()

    class Process(Task):
        def __init__(self) -> None:
            super().__init__()
            self.executed = False

        def run_step(self, _flag: str) -> str:  # pragma: no cover - should not run
            self.executed = True
            return "PROCESSED"

    process = Process()

    class Reject(Task):
        def __init__(self) -> None:
            super().__init__()
            self.status: str | None = None

        def run_step(self) -> str:
            self.status = "REJECTED"
            return "FAILED"

    reject = Reject()

    start >> validate
    validate >> process
    (validate - "reject") >> reject

    trace_path = tmp_path / "trace.log"
    wf = Workflow(outputs=[process, reject], trace=str(trace_path))
    result = wf.run({"payload": {"valid": False}})

    assert result == [None, "FAILED"]
    assert reject.status == "REJECTED"
    assert not process.executed

    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    started = [e["step"] for e in events if e["event"] == "step_started"]
    assert started == ["Start", "Validate", "Reject"]
    assert not any(e.get("step") == "Process" for e in events)


def test_diamond_mixed_conditions(tmp_path) -> None:
    """TC-05 - Diamond with mixed conditions."""

    class Gate(Task):
        def run_step(self, x: int) -> str:
            if x < 0:
                return "A"
            if x > 10:
                return "C"
            return "B"

    gate = Gate()

    class A(Task):
        def __init__(self) -> None:
            super().__init__()
            self.executed = False

        def run_step(self, x: int) -> None:  # pragma: no cover - should not run
            self.executed = True

    class B(Task):
        def run_step(self, x: int) -> int:
            return x * x

    class C(Task):
        def __init__(self) -> None:
            super().__init__()
            self.executed = False

        def run_step(self, x: int) -> None:  # pragma: no cover - should not run
            self.executed = True

    a = A()
    b = B()
    c = C()

    (gate - "A") >> a
    (gate - "B") >> b
    (gate - "C") >> c

    trace_path = tmp_path / "trace.log"
    wf = Workflow(outputs=[a, b, c], trace=str(trace_path))
    result = wf.run({"x": 7})

    assert result == [None, 49, None]
    assert not a.executed
    assert not c.executed

    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    started = [e["step"] for e in events if e["event"] == "step_started"]
    assert started == ["Gate", "B"]
    assert not any(e.get("step") in {"A", "C"} for e in events)


def test_diamond_mixed_conditions_depends(tmp_path) -> None:
    """TC-05b - Diamond with mixed conditions using dependency checks."""

    class Gate(Task):
        def run_step(self, x: int) -> dict:
            if x < 0:
                return {"branch": "A"}
            if x > 10:
                return {"branch": "C"}
            return {"branch": "B"}

    gate = Gate()

    class A(Task):
        def __init__(self) -> None:
            super().__init__()
            self.executed = False

        def run_step(
            self,
            _res: dict = Depends(gate, condition=lambda v: v["branch"] == "A"),
        ) -> None:  # pragma: no cover - should not run
            self.executed = True

    class B(Task):
        def run_step(
            self,
            _res: dict = Depends(gate, condition=lambda v: v["branch"] == "B"),
            x: int = 0,
        ) -> int:
            return x * x

    class C(Task):
        def __init__(self) -> None:
            super().__init__()
            self.executed = False

        def run_step(
            self,
            _res: dict = Depends(gate, condition=lambda v: v["branch"] == "C"),
        ) -> None:  # pragma: no cover - should not run
            self.executed = True

    a = A()
    b = B()
    c = C()

    trace_path = tmp_path / "trace.log"
    wf = Workflow(outputs=[a, b, c], trace=str(trace_path))
    result = wf.run({"x": 7})

    assert result == [None, 49, None]
    assert not a.executed
    assert not c.executed

    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    started = [e["step"] for e in events if e["event"] == "step_started"]
    assert started == ["Gate", "A", "B", "C"]

    finished = [e for e in events if e["event"] == "step_finished"]
    assert any(e["step"] == "A" and e["skipped"] for e in finished)
    assert any(e["step"] == "C" and e["skipped"] for e in finished)
    assert not any(e["step"] == "B" and e["skipped"] for e in finished)


def test_runtime_computed_condition_on_merged_edge(tmp_path) -> None:
    """TC-06 - Runtime-computed condition on merged edge."""

    class Root(Task):
        def run_step(self) -> None:  # pragma: no cover - simple
            pass

    root = Root()

    class PLeft(Task):
        def run_step(self) -> dict:
            return {"val": "foo"}

    class PRight(Task):
        def run_step(self) -> dict:
            return {"val": "bar"}

    left = PLeft()
    right = PRight()

    class Decide(Task):
        def run_step(
            self,
            left_value: Computed[dict] = Depends(left),
            right_value: Computed[dict] = Depends(right),
        ) -> str:
            return "same" if left_value["val"] == right_value["val"] else "different"

    decide = Decide()

    class Same(Task):
        def run_step(self) -> None:  # pragma: no cover - should not run
            pass

    same = Same()

    class Different(Task):
        def __init__(self) -> None:
            super().__init__()
            self.reason: str | None = None

        def run_step(
            self,
            left_value: Computed[dict] = Depends(left),
            right_value: Computed[dict] = Depends(right),
        ) -> str:
            self.reason = (
                f"Values diverged: {left_value['val']} vs {right_value['val']}"
            )
            return self.reason

    diff = Different()

    root >> left
    root >> right
    left >> decide
    right >> decide
    (decide - "same") >> same
    (decide - "different") >> diff

    trace_path = tmp_path / "trace.log"
    wf = Workflow(outputs=[same, diff], trace=str(trace_path))
    result = wf.run()

    assert result == [None, "Values diverged: foo vs bar"]
    assert diff.reason == "Values diverged: foo vs bar"

    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    started = [e["step"] for e in events if e["event"] == "step_started"]
    assert started[0] == "Root"
    assert set(started[1:3]) == {"PLeft", "PRight"}
    assert started[3] == "Decide"
    assert started[4] == "Different"
    assert "Same" not in started

    decide_start = next(
        i
        for i, e in enumerate(events)
        if e["event"] == "step_started" and e["step"] == "Decide"
    )
    left_finished = next(
        i
        for i, e in enumerate(events)
        if e["event"] == "step_finished" and e["step"] == "PLeft"
    )
    right_finished = next(
        i
        for i, e in enumerate(events)
        if e["event"] == "step_finished" and e["step"] == "PRight"
    )
    assert decide_start > left_finished
    assert decide_start > right_finished
    assert (
        len(
            [
                e
                for e in events
                if e["event"] == "step_started" and e["step"] == "Decide"
            ]
        )
        == 1
    )


def test_three_parent_and_join(tmp_path) -> None:
    """TC-07 - AND-join with three parents."""

    class SleepTask(Task):
        def __init__(self, label: str, duration: float, value: int) -> None:
            super().__init__()
            self.label = label
            self.duration = duration
            self.value = value
            self.start: float | None = None
            self.end: float | None = None

        def run_step(self) -> dict:
            self.start = time.perf_counter()
            time.sleep(self.duration)
            self.end = time.perf_counter()
            return {f"from{self.label}": self.value}

    class StepA(SleepTask):
        pass

    class StepB(SleepTask):
        pass

    class StepC(SleepTask):
        pass

    a = StepA("A", 0.05, 1)
    b = StepB("B", 0.15, 2)
    c = StepC("C", 0.05, 3)

    class JoinZ(Task):
        def __init__(self, duration: float) -> None:
            super().__init__()
            self.duration = duration
            self.received: dict[str, int] | None = None
            self.start: float | None = None
            self.end: float | None = None

        def run_step(
            self,
            from_a: Computed[dict] = Depends(a),
            from_b: Computed[dict] = Depends(b),
            from_c: Computed[dict] = Depends(c),
        ) -> dict:
            self.start = time.perf_counter()
            time.sleep(self.duration)
            self.received = {**from_a, **from_b, **from_c}
            self.end = time.perf_counter()
            return self.received

    join = JoinZ(0.05)

    a >> join
    b >> join
    c >> join

    trace_path = tmp_path / "trace.log"
    wf = Workflow(outputs=[join], trace=str(trace_path))

    start_time = time.perf_counter()
    result = wf.run(execution_engine=ProcessEngine(3))
    elapsed = time.perf_counter() - start_time

    assert result == {"fromA": 1, "fromB": 2, "fromC": 3}
    assert join.received == result

    assert (
        a.end is not None
        and b.end is not None
        and c.end is not None
        and join.start is not None
    )
    assert max(a.end, b.end, c.end) <= join.start
    assert elapsed == pytest.approx(
        max(a.duration, b.duration, c.duration) + join.duration, rel=0.3
    )

    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    join_started = [
        e for e in events if e["event"] == "step_started" and e["step"] == "JoinZ"
    ]
    join_finished = [
        e for e in events if e["event"] == "step_finished" and e["step"] == "JoinZ"
    ]
    assert len(join_started) == len(join_finished) == 1

    join_start = next(
        i
        for i, e in enumerate(events)
        if e["event"] == "step_started" and e["step"] == "JoinZ"
    )
    a_finished = next(
        i
        for i, e in enumerate(events)
        if e["event"] == "step_finished" and e["step"] == "StepA"
    )
    b_finished = next(
        i
        for i, e in enumerate(events)
        if e["event"] == "step_finished" and e["step"] == "StepB"
    )
    c_finished = next(
        i
        for i, e in enumerate(events)
        if e["event"] == "step_finished" and e["step"] == "StepC"
    )
    assert join_start > a_finished
    assert join_start > b_finished
    assert join_start > c_finished


def test_or_join_first_completer(tmp_path) -> None:
    """TC-08 - OR-join where the first completed parent triggers the join."""

    class Producer(Task):
        def __init__(self, label: str, delay: float) -> None:
            super().__init__()
            self.label = label
            self.delay = delay

        def run_step(self) -> dict:
            time.sleep(self.delay)
            return {"payload": {"source": self.label}}

    class P1(Producer):
        pass

    class P2(Producer):
        pass

    p1 = P1("Producer1", 0.05)
    p2 = P2("Producer2", 0.1)

    class RaceWinner(Task):
        def __init__(self) -> None:
            super().__init__()
            self.triggers = 0
            self.payload: dict | None = None

        def run_step(self, payload: dict = Depends(p1, p2)) -> dict:
            self.triggers += 1
            self.payload = payload
            return payload

    winner = RaceWinner()

    # RaceWinner should start as soon as either producer finishes

    trace_path = tmp_path / "trace.log"
    wf = Workflow(outputs=[winner], trace=str(trace_path))

    result = wf.run(execution_engine=ProcessEngine(2))

    assert winner.triggers == 1
    assert result["payload"]["source"] in {"Producer1", "Producer2"}

    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    started = [
        i
        for i, e in enumerate(events)
        if e["event"] == "step_started" and e["step"] == "RaceWinner"
    ]
    finished = [
        i
        for i, e in enumerate(events)
        if e["event"] == "step_finished" and e["step"] == "RaceWinner"
    ]
    assert len(started) == len(finished) == 1

    p1_finished = next(
        i
        for i, e in enumerate(events)
        if e["event"] == "step_finished" and e["step"] == "P1"
    )
    p2_finished = next(
        i
        for i, e in enumerate(events)
        if e["event"] == "step_finished" and e["step"] == "P2"
    )

    winner_started = started[0]
    assert winner_started > p1_finished or winner_started > p2_finished


@pytest.mark.xfail(reason="OR-join via edges alone is not supported")
def test_or_join_first_completer_rshift(tmp_path) -> None:
    """TC-08b - OR-join expressed with explicit edges using >>."""

    class Producer(Task):
        def __init__(self, label: str, delay: float) -> None:
            super().__init__()
            self.label = label
            self.delay = delay

        def run_step(self) -> dict:
            time.sleep(self.delay)
            return {"payload": {"source": self.label}}

    p1 = Producer("Producer1", 0.05)
    p2 = Producer("Producer2", 0.1)

    class RaceWinner(Task):
        def __init__(self) -> None:
            super().__init__()
            self.triggers = 0

        def run_step(self) -> None:
            self.triggers += 1

    winner = RaceWinner()

    # Explicit edge construction using rshift operator
    p1 >> winner
    p2 >> winner

    trace_path = tmp_path / "trace.log"
    wf = Workflow(outputs=[winner], trace=str(trace_path))

    wf.run(execution_engine=ProcessEngine(2))

    assert winner.triggers == 1

    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    started = [
        i
        for i, e in enumerate(events)
        if e["event"] == "step_started" and e["step"] == "RaceWinner"
    ]
    finished = [
        i
        for i, e in enumerate(events)
        if e["event"] == "step_finished" and e["step"] == "RaceWinner"
    ]
    assert len(started) == len(finished) == 1

    p1_finished = next(
        i
        for i, e in enumerate(events)
        if e["event"] == "step_finished" and e["step"] == "Producer1"
    )
    p2_finished = next(
        i
        for i, e in enumerate(events)
        if e["event"] == "step_finished" and e["step"] == "Producer2"
    )

    winner_started = started[0]
    assert winner_started < max(p1_finished, p2_finished)


def test_or_join_condition_source(tmp_path) -> None:
    """TC-08c - Ensure Depends with condition knows which producer triggered."""

    class CaptureSource(Condition):
        def __init__(self) -> None:
            self.source: Step | None = None

        def __call__(
            self, value: Any, source: Step
        ) -> bool:  # pragma: no cover - simple
            self.source = source
            return True

    class Producer(Task):
        def __init__(self, label: str, delay: float) -> None:
            super().__init__()
            self.label = label
            self.delay = delay

        def run_step(self) -> dict:
            time.sleep(self.delay)
            return {"payload": {"source": self.label}}

    class P1(Producer):
        pass

    class P2(Producer):
        pass

    p1 = P1("Producer1", 0.05)
    p2 = P2("Producer2", 0.1)

    cond = CaptureSource()

    class RaceWinner(Task):
        def run_step(self, payload: dict = Depends(p1, p2, condition=cond)) -> dict:
            return payload

    winner = RaceWinner()

    wf = Workflow(outputs=[winner])
    result = wf.run(execution_engine=ProcessEngine(2))

    assert cond.source is p1
    assert result["payload"]["source"] == "Producer1"
