# -*- coding: utf-8 -*-
"""Lightweight workflow interface.

This module provides simple synchronous and asynchronous workflow primitives
based on nodes and flows. The design is inspired by the user's suggestion in
the issue conversation and is intentionally minimal so it can be adopted
incrementally without disrupting the existing network implementation.
"""

from __future__ import annotations

import asyncio
import inspect
import time
import uuid
import warnings
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence

from .engines import PoolEngine
from .interfaces import ExecutionEngine, Exporter, Tracer
from .storage import RuntimeStorage


class Status(str, Enum):
    """Execution status for workflow steps and workflows."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


class Step:
    """Minimal unit of work in a :class:`Workflow`.

    The lifecycle provides per-step hooks as well as hooks that are executed
    once for the lifetime of the step within a workflow run.  Subclasses can
    override :py:meth:`before_all`, :py:meth:`setup`, :py:meth:`run_step`,
    :py:meth:`teardown` and :py:meth:`after_all` to customise behaviour.
    """

    def __init__(self) -> None:
        self.params: Dict[str, Any] = {}
        self.successors: Dict[str, List["Step"]] = {}
        self.predecessors: List["Step"] = []
        self.tracer: Tracer | None = None
        self.execution_group = 0
        self.state: Status = Status.PENDING

    def _log_event(self, event: str, **data: Any) -> None:
        if self.tracer:
            self.tracer.record({"event": event, "step": type(self).__name__, **data})

    def set_params(self, params: Dict[str, Any]) -> None:
        """Store parameters passed from the workflow."""
        self.params = params

    def next(self, node: "Step", action: str = "default") -> "Step":
        """Add a successor step to run after this one."""
        self.successors.setdefault(action, []).append(node)
        if self not in node.predecessors:
            node.predecessors.append(self)
        return node

    def before_all(self, shared: Any) -> Any:  # pragma: no cover - to be overridden
        """Hook executed once before the first call to :py:meth:`run`."""
        pass

    def setup(self, shared: Any) -> Any:  # pragma: no cover - to be overridden
        """Prepare the step for execution."""
        return None

    def run_step(self, setup_res: Any) -> Any:  # pragma: no cover - to be overridden
        """Execute the step."""
        pass

    def teardown(
        self, shared: Any, setup_res: Any, exec_res: Any
    ) -> Any:  # pragma: no cover
        """Clean up after :py:meth:`run_step`. Return value is propagated as the step result."""
        return exec_res

    def after_all(self, shared: Any) -> Any:  # pragma: no cover - to be overridden
        """Hook executed once after the final call to :py:meth:`run`."""
        pass

    def _exec(self, setup_res: Any) -> Any:
        return self.run_step(setup_res)

    def _run(self, shared: Any) -> Any:
        p = self.setup(shared)
        e = self._exec(p)
        return self.teardown(shared, p, e)

    def run(self, shared: Any) -> Any:
        if self.successors:
            warnings.warn("Step won't run successors. Use Workflow.")
        self.before_all(shared)
        self._log_event("step_started")
        result = self._run(shared)
        self._log_event(
            "step_finished", result=result, skipped=getattr(self, "was_skipped", False)
        )
        self.after_all(shared)
        return result

    def __rshift__(self, other: "Step") -> "Step":
        """Shorthand for :py:meth:`next`."""
        return self.next(other)

    def __sub__(self, action: str) -> "_ConditionalTransition":
        if isinstance(action, str):
            return _ConditionalTransition(self, action)
        raise TypeError("Action must be a string")


class _ConditionalTransition:
    def __init__(self, src: Step, action: str) -> None:
        self.src = src
        self.action = action

    def __rshift__(self, tgt: Step) -> Step:
        return self.src.next(tgt, self.action)


class Task(Step):
    """Step with optional retry logic and typed dependencies."""

    def __init__(self, max_retries: int = 1, wait: float = 0) -> None:
        super().__init__()
        self.max_retries = max_retries
        self.wait = wait
        self.cur_retry: Optional[int] = None
        self.deps: Dict[str, Step | List[Step]] = {}
        self.dep_conditions: Dict[str, Callable[[Any], bool]] = {}
        self.or_groups: Dict[str, List[Step]] = {}
        self.or_triggered: Dict[str, Step] = {}
        self.was_skipped = False
        run_method = type(self).run_step
        sig = inspect.signature(run_method)
        params = list(sig.parameters.values())
        self.param_names: List[str] = []
        for param in params:
            if isinstance(param.default, Depends):
                dep_obj = param.default.obj
                if isinstance(dep_obj, list):
                    dep_steps: List[Step] = []
                    for obj in dep_obj:
                        dstep = obj if isinstance(obj, Step) else FunctionTask(obj)
                        dstep >> self
                        dep_steps.append(dstep)
                    self.deps[param.name] = dep_steps
                    self.or_groups[param.name] = dep_steps
                else:
                    dep_step = (
                        dep_obj if isinstance(dep_obj, Step) else FunctionTask(dep_obj)
                    )
                    dep_step >> self
                    self.deps[param.name] = dep_step
                if param.default.condition is not None:
                    self.dep_conditions[param.name] = param.default.condition
            elif param.name not in {"self", "setup_res", "shared"}:
                self.param_names.append(param.name)
        self.is_typed = bool(self.deps) or not (
            len(params) == 2 and params[1].name in {"setup_res", "shared"}
        )

    def setup(self, shared: Any) -> Any:  # type: ignore[override]
        if self.is_typed:
            return shared
        return super().setup(shared)

    def _exec(self, setup_res: Any) -> Any:
        self.was_skipped = False
        for self.cur_retry in range(self.max_retries):
            try:
                if self.is_typed:
                    kwargs = {}
                    for name, dep in self.deps.items():
                        if isinstance(dep, list):
                            chosen = self.or_triggered.get(name) or dep[0]
                            val = setup_res[chosen]
                            cond = self.dep_conditions.get(name)
                            if cond is not None:
                                passed = (
                                    bool(cond(val, chosen))
                                    if isinstance(cond, Condition)
                                    else bool(cond(val))
                                )
                                self._log_event(
                                    "condition_check",
                                    dependency=name,
                                    value=val,
                                    passed=passed,
                                )
                                if not passed:
                                    self.was_skipped = True
                                    return None
                            kwargs[name] = val
                        else:
                            val = setup_res[dep]
                            cond = self.dep_conditions.get(name)
                            if cond is not None:
                                passed = (
                                    bool(cond(val, dep))
                                    if isinstance(cond, Condition)
                                    else bool(cond(val))
                                )
                                self._log_event(
                                    "condition_check",
                                    dependency=name,
                                    value=val,
                                    passed=passed,
                                )
                                if not passed:
                                    self.was_skipped = True
                                    return None

                            kwargs[name] = val
                    kwargs.update(
                        {
                            k: v
                            for k, v in self.params.items()
                            if k in self.param_names and k not in kwargs
                        }
                    )
                    result = type(self).run_step(self, **kwargs)
                    if isinstance(setup_res, dict):
                        setup_res[self] = result
                    return result
                return type(self).run_step(self, setup_res)
            except Exception as e:
                if self.cur_retry == self.max_retries - 1:
                    return self.exec_fallback(setup_res, e)
                if self.wait > 0:
                    time.sleep(self.wait)

    def exec_fallback(self, setup_res: Any, exc: Exception) -> Any:
        raise exc


class BatchTask(Task):
    """Execute a sequence of items using a :class:`Task`."""

    def _exec(self, items: Any) -> Any:
        return [super(BatchTask, self)._exec(i) for i in (items or [])]


class Workflow(Step):
    """A sequence of :class:`Step` objects executed via an engine."""

    def __init__(
        self,
        outputs: List[Step],
        execution_engine: "ExecutionEngine | None" = None,
        *,
        trace: str | Tracer | None = None,
    ) -> None:
        super().__init__()
        self.outputs = outputs
        self.execution_engine = execution_engine
        if isinstance(trace, str):
            from .tracing import FileTracer

            self.tracer: Tracer | None = FileTracer(trace)
            self.trace_path = trace
        else:
            self.tracer = trace
            self.trace_path = None
        self.roots = self._find_roots(outputs)
        self.start_step = self.roots[0] if self.roots else None
        self.workflow_id = uuid.uuid4().hex
        self.workflow_instance_id: str | None = None
        self.state: Status = Status.PENDING
        self._assign_execution_groups()

    def _find_roots(self, outputs: List[Step]) -> List[Step]:
        steps: List[Step] = []
        preds: Dict[Step, bool] = {}

        def walk(step: Step) -> None:
            if step in steps:
                return
            steps.append(step)
            for pred in step.predecessors:
                preds[step] = True
                walk(pred)
            if isinstance(step, Task):
                for dep in step.deps.values():
                    if isinstance(dep, list):
                        for d in dep:
                            preds[step] = True
                            walk(d)
                    else:
                        preds[step] = True
                        walk(dep)
            preds.setdefault(step, False)

        for out in outputs:
            walk(out)

        return [s for s, has_pred in preds.items() if not has_pred]

    def _assign_execution_groups(self) -> None:
        """Compute execution groups based on dependencies."""
        steps = self._collect_steps()
        indegree: Dict[Step, int] = {s: len(s.predecessors) for s in steps}
        ready = [s for s in steps if indegree[s] == 0]
        group = 0
        while ready:
            next_ready: List[Step] = []
            for step in ready:
                step.execution_group = group
                for succs in step.successors.values():
                    for succ in succs:
                        indegree[succ] -= 1
                        if indegree[succ] == 0:
                            next_ready.append(succ)
            ready = next_ready
            group += 1

    def export(self, path: str, exporter: "Exporter | None" = None) -> None:
        """Serialize the workflow graph using *exporter*.

        By default the workflow is exported to YAML via :class:`YamlExporter`.
        """

        from .exporters import YamlExporter

        exporter = exporter or YamlExporter()
        exporter.export(self, path)

    def dispatch(
        self,
        runtime_store: "RuntimeStorage",
        inputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Queue the initial steps of this workflow in *runtime_store*.

        Returns the created workflow instance ID.
        """

        self.params = inputs or {}
        self.workflow_instance_id = uuid.uuid4().hex
        step_names = self._step_name_map()
        runtime_store.create_run(
            self.workflow_id,
            self.workflow_instance_id,
            step_names.values(),
        )
        nodes = self._collect_steps()
        indegree: Dict[Step, int] = {n: 0 for n in nodes}
        for succ in nodes:
            group_preds: set[Step] = set()
            if isinstance(succ, Task):
                succ.or_remaining = {k: True for k in succ.or_groups}
                for group in succ.or_groups.values():
                    indegree[succ] += 1
                    group_preds.update(group)
            for pred in succ.predecessors:
                if pred not in group_preds:
                    indegree[succ] += 1

        ready = [n for n, d in indegree.items() if d == 0]
        for step in ready:
            runtime_store.enqueue(
                self.workflow_id,
                self.workflow_instance_id,
                step_names[step],
            )
        return self.workflow_instance_id

    def run(
        self,
        inputs: Optional[Dict[str, Any]] = None,
        execution_engine: "ExecutionEngine | None" = None,
        runtime_store: "RuntimeStorage | None" = None,
    ) -> Any:  # type: ignore[override]
        """Execute the workflow.

        Parameters
        ----------
        inputs:
            Parameters passed to the starting steps.  They are distributed to
            tasks based on parameter names.
        runtime_store:
            Optional :class:`RuntimeStorage` used to persist step state.  When
            provided, step statuses are written to the store as the workflow
            runs.
        """
        self.params = inputs or {}
        shared: Dict[Any, Any] = {}
        engine = execution_engine or self.execution_engine or PoolEngine()
        self.workflow_instance_id = uuid.uuid4().hex
        step_names = None
        if runtime_store:
            step_names = self._step_name_map()
            runtime_store.create_run(
                self.workflow_id,
                self.workflow_instance_id,
                step_names.values(),
            )
        if self.tracer:
            from .tracing import BoundTracer

            bound = BoundTracer(
                self.tracer, self.workflow_id, self.workflow_instance_id
            )
            for step in self._collect_steps():
                step.tracer = bound
            bound.record({"event": "workflow_started"})
        self.state = Status.RUNNING
        try:
            self.before_all(shared)
            setup_res = self.setup(shared)
            result = self._run_engine(shared, engine, runtime_store, step_names)
            result = self.teardown(shared, setup_res, result)
            self.state = Status.SUCCEEDED
        except Exception:
            self.state = Status.FAILED
            for step in self._collect_steps():
                if step.state == Status.PENDING:
                    step.state = Status.CANCELLED
                    step._log_event("step_cancelled")
            if self.tracer:
                from .tracing import BoundTracer

                BoundTracer(
                    self.tracer, self.workflow_id, self.workflow_instance_id
                ).record({"event": "workflow_finished"})
            return None
        finally:
            self.after_all(shared)
        if self.tracer and self.state != Status.FAILED:
            from .tracing import BoundTracer

            BoundTracer(
                self.tracer, self.workflow_id, self.workflow_instance_id
            ).record({"event": "workflow_finished"})
        if runtime_store:
            runtime_store.finalize_run(self.workflow_id, self.workflow_instance_id)
        if self.outputs:
            if len(self.outputs) == 1:
                return shared.get(self.outputs[0], result)
            return [shared.get(o) for o in self.outputs]
        return result

    def start(self, start: Step) -> Step:
        """Specify the initial step for this workflow."""
        self.start_step = start
        return start

    def get_next_steps(self, curr: Step, action: Optional[str]) -> List[Step]:
        nxt = curr.successors.get(action or "default", [])
        if not nxt and curr.successors:
            warnings.warn(
                f"Workflow ends: '{action}' not found in {list(curr.successors)}"
            )
        return list(nxt)

    def _collect_steps(self) -> List[Step]:
        seen: List[Step] = []

        def walk(step: Step) -> None:
            if step in seen:
                return
            for pred in step.predecessors:
                walk(pred)
            if isinstance(step, Task):
                for dep in step.deps.values():
                    if isinstance(dep, list):
                        for d in dep:
                            walk(d)
                    else:
                        walk(dep)
            seen.append(step)

        for out in self.outputs:
            walk(out)
        return seen

    def _step_name_map(self) -> dict[Step, str]:
        """Return a stable name mapping for steps."""
        steps = self._collect_steps()
        return {step: f"step{idx}" for idx, step in enumerate(steps)}

    def _execute_step(self, step: Step, shared: Dict[Any, Any]) -> Any:
        step.set_params({**self.params, **step.params})
        step.before_all(shared)
        step._log_event("step_started")
        step.state = Status.RUNNING
        try:
            result = step._run(shared)
            step.state = (
                Status.SKIPPED if getattr(step, "was_skipped", False) else Status.SUCCEEDED
            )
            step._log_event(
                "step_finished",
                result=result,
                skipped=getattr(step, "was_skipped", False),
            )
            if isinstance(shared, dict):
                shared[step] = result
            step.after_all(shared)
            return result
        except Exception as exc:
            step.state = Status.FAILED
            step._log_event("step_failed", error=str(exc))
            step.after_all(shared)
            raise

    def _run_engine(
        self,
        shared: Any,
        engine: ExecutionEngine,
        runtime_store: "RuntimeStorage | None" = None,
        step_names: dict[Step, str] | None = None,
    ) -> Any:
        nodes = self._collect_steps()
        indegree: Dict[Step, int] = {n: 0 for n in nodes}
        if runtime_store and step_names:
            for step in nodes:
                runtime_store.set_state(
                    self.workflow_id,
                    self.workflow_instance_id,
                    step_names[step],
                    Status.PENDING,
                )
        if runtime_store and step_names:
            for step in nodes:
                runtime_store.set_state(
                    self.workflow_id,
                    self.workflow_instance_id,
                    step_names[step],
                    Status.PENDING,
                )
        for succ in nodes:
            group_preds: set[Step] = set()
            if isinstance(succ, Task):
                succ.or_remaining = {k: True for k in succ.or_groups}
                for group in succ.or_groups.values():
                    indegree[succ] += 1
                    group_preds.update(group)
            for pred in succ.predecessors:
                if pred not in group_preds:
                    indegree[succ] += 1

        ready = [n for n, d in indegree.items() if d == 0]
        for step in ready:
            step._log_event("step_enqueued")
            if runtime_store and step_names:
                runtime_store.enqueue(
                    self.workflow_id,
                    self.workflow_instance_id,
                    step_names[step],
                )
            if runtime_store and step_names:
                runtime_store.enqueue(
                    self.workflow_id,
                    self.workflow_instance_id,
                    step_names[step],
                )
        last_result: Any = None
        while ready:
            current_group = min(s.execution_group for s in ready)
            batch = [s for s in ready if s.execution_group == current_group]
            ready = [s for s in ready if s.execution_group != current_group]

            exc: dict[str, Exception] = {}

            def run_step(s: Step = None) -> Any:
                if runtime_store and step_names:
                    runtime_store.set_state(
                        self.workflow_id,
                        self.workflow_instance_id,
                        step_names[s],
                        Status.RUNNING,
                    )
                try:
                    result = self._execute_step(s, shared)
                    if runtime_store and step_names:
                        runtime_store.set_state(
                            self.workflow_id,
                            self.workflow_instance_id,
                            step_names[s],
                            s.state,
                        )
                    return result
                except Exception as e:  # pragma: no cover - bubble up
                    exc['err'] = e
                    if runtime_store and step_names:
                        runtime_store.set_state(
                            self.workflow_id,
                            self.workflow_instance_id,
                            step_names[s],
                            Status.FAILED,
                        )
                    return None

            results = engine.run_steps([lambda s=s: run_step(s) for s in batch])

            if exc:
                raise exc['err']

            for step, res in zip(batch, results):
                last_result = res
                action = res if isinstance(res, str) else None
                for succ in self.get_next_steps(step, action):
                    decreased = False
                    if isinstance(succ, Task):
                        for name, group in succ.or_groups.items():
                            if step in group and succ.or_remaining.get(name):
                                succ.or_remaining[name] = False
                                succ.or_triggered[name] = step
                                indegree[succ] -= 1
                                decreased = True
                                break
                    if not decreased:
                        indegree[succ] -= 1
                    if indegree[succ] == 0:
                        succ._log_event("step_enqueued")
                        if runtime_store and step_names:
                            runtime_store.enqueue(
                                self.workflow_id,
                                self.workflow_instance_id,
                                step_names[succ],
                            )
                        ready.append(succ)

        return last_result

    def teardown(self, shared: Any, setup_res: Any, exec_res: Any) -> Any:
        return exec_res


class BatchWorkflow(Workflow):
    """Run the same workflow for a batch of parameter sets."""

    def run(
        self,
        inputs: Optional[Dict[str, Any]] = None,
        execution_engine: "ExecutionEngine | None" = None,
    ) -> Any:
        self.params = inputs or {}
        shared: Dict[Any, Any] = {}
        engine = execution_engine or self.execution_engine or PoolEngine()
        self.before_all(shared)
        param_sets = self.setup(shared) or []
        for bp in param_sets:
            self.params.update(bp)
            self._run_engine(shared, engine)
        result = self.teardown(shared, param_sets, None)
        self.after_all(shared)
        return result


class AsyncTask(Task):
    def __init__(self, max_retries: int = 1, wait: float = 0) -> None:
        super().__init__(max_retries, wait)
        self.deps = {}
        self.dep_conditions: Dict[str, Callable[[Any], bool]] = {}
        self.or_groups: Dict[str, List[Step]] = {}
        self.or_triggered: Dict[str, Step] = {}
        self.was_skipped = False
        run_method = type(self).run_step_async
        sig = inspect.signature(run_method)
        params = list(sig.parameters.values())
        self.param_names = []
        for param in params:
            if isinstance(param.default, Depends):
                dep_obj = param.default.obj
                if isinstance(dep_obj, list):
                    dep_steps: List[Step] = []
                    for obj in dep_obj:
                        dstep = obj if isinstance(obj, Step) else FunctionTask(obj)
                        dstep >> self
                        dep_steps.append(dstep)
                    self.deps[param.name] = dep_steps
                    self.or_groups[param.name] = dep_steps
                else:
                    dep_step = (
                        dep_obj if isinstance(dep_obj, Step) else FunctionTask(dep_obj)
                    )
                    dep_step >> self
                    self.deps[param.name] = dep_step
                if param.default.condition is not None:
                    self.dep_conditions[param.name] = param.default.condition
            elif param.name not in {"self", "setup_res", "shared"}:
                self.param_names.append(param.name)
        self.is_typed = bool(self.deps) or not (
            len(params) == 2 and params[1].name in {"setup_res", "shared"}
        )

    async def before_all_async(self, shared: Any) -> Any:  # pragma: no cover
        pass

    async def setup_async(self, shared: Any) -> Any:  # pragma: no cover
        if self.is_typed:
            return shared
        return None

    async def run_step_async(
        self, setup_res: Any
    ) -> Any:  # pragma: no cover - to be overridden
        pass

    async def _exec(self, setup_res: Any) -> Any:
        self.was_skipped = False
        for i in range(self.max_retries):
            try:
                if self.is_typed:
                    kwargs = {}
                    for name, dep in self.deps.items():
                        if isinstance(dep, list):
                            chosen = self.or_triggered.get(name) or dep[0]
                            val = setup_res[chosen]
                            cond = self.dep_conditions.get(name)
                            if cond is not None:
                                passed = (
                                    bool(cond(val, chosen))
                                    if isinstance(cond, Condition)
                                    else bool(cond(val))
                                )
                                self._log_event(
                                    "condition_check",
                                    dependency=name,
                                    value=val,
                                    passed=passed,
                                )
                                if not passed:
                                    self.was_skipped = True
                                    return None
                            kwargs[name] = val
                        else:
                            val = setup_res[dep]
                            cond = self.dep_conditions.get(name)
                            if cond is not None:
                                passed = (
                                    bool(cond(val, dep))
                                    if isinstance(cond, Condition)
                                    else bool(cond(val))
                                )
                                self._log_event(
                                    "condition_check",
                                    dependency=name,
                                    value=val,
                                    passed=passed,
                                )
                                if not passed:
                                    self.was_skipped = True
                                    return None
                            kwargs[name] = val
                    kwargs.update(
                        {
                            k: v
                            for k, v in self.params.items()
                            if k in self.param_names and k not in kwargs
                        }
                    )
                    method = type(self).run_step_async
                    result = await method(self, **kwargs)
                    if isinstance(setup_res, dict):
                        setup_res[self] = result
                    return result
                method = type(self).run_step_async
                return await method(self, setup_res)
            except Exception as e:
                if i == self.max_retries - 1:
                    return await self.run_step_fallback_async(setup_res, e)
                if self.wait > 0:
                    await asyncio.sleep(self.wait)

    async def run_step_fallback_async(
        self, setup_res: Any, exc: Exception
    ) -> Any:  # pragma: no cover
        raise exc

    async def teardown_async(
        self, shared: Any, setup_res: Any, exec_res: Any
    ) -> Any:  # pragma: no cover
        return exec_res

    async def after_all_async(self, shared: Any) -> Any:  # pragma: no cover
        pass

    async def run_async(self, inputs: Optional[Dict[str, Any]] = None) -> Any:
        """Execute the workflow asynchronously."""
        self.params = inputs or {}
        shared: Dict[Any, Any] = {}
        await self.before_all_async(shared)
        self._log_event("step_started")
        result = await self._run_async(shared)
        self._log_event(
            "step_finished", result=result, skipped=getattr(self, "was_skipped", False)
        )
        await self.after_all_async(shared)
        if self.outputs:
            if len(self.outputs) == 1:
                return shared.get(self.outputs[0], result)
            return [shared.get(o) for o in self.outputs]
        return result

    async def _run_async(self, shared: Any) -> Any:
        p = await self.setup_async(shared)
        e = await self._exec(p)
        return await self.teardown_async(shared, p, e)

    def _run(self, shared: Any) -> Any:
        raise RuntimeError("Use run_async.")


class AsyncBatchTask(AsyncTask, BatchTask):
    async def _exec(self, items: Any) -> Any:
        return [await super(AsyncBatchTask, self)._exec(i) for i in items]


class AsyncParallelBatchTask(AsyncTask, BatchTask):
    async def _exec(self, items: Any) -> Any:
        return await asyncio.gather(
            *(super(AsyncParallelBatchTask, self)._exec(i) for i in items)
        )


class AsyncWorkflow(Workflow, AsyncTask):
    async def _execute_step_async(
        self, step: Step, shared: Dict[Any, Any], engine: ExecutionEngine
    ) -> Any:
        step.set_params({**self.params, **step.params})
        if isinstance(step, AsyncWorkflow):
            result = await step._run_async(shared, engine)
        elif isinstance(step, AsyncTask):
            await step.before_all_async(shared)
            step._log_event("step_started")
            step.state = Status.RUNNING
            try:
                result = await step._run_async(shared)
                step.state = (
                    Status.SKIPPED if getattr(step, "was_skipped", False) else Status.SUCCEEDED
                )
                step._log_event(
                    "step_finished",
                    result=result,
                    skipped=getattr(step, "was_skipped", False),
                )
                if isinstance(shared, dict):
                    shared[step] = result
                await step.after_all_async(shared)
            except Exception as exc:
                step.state = Status.FAILED
                step._log_event("step_failed", error=str(exc))
                await step.after_all_async(shared)
                raise
        else:
            result = self._execute_step(step, shared)
        return result

    async def run_async(
        self,
        inputs: Optional[Dict[str, Any]] = None,
        execution_engine: "ExecutionEngine | None" = None,
        runtime_store: "RuntimeStorage | None" = None,
    ) -> Any:
        """Execute the workflow asynchronously.

        Parameters
        ----------
        inputs:
            Parameters passed to the starting steps.
        runtime_store:
            Optional :class:`RuntimeStorage` used to persist step state during
            execution.
        """
        self.params = inputs or {}
        shared: Dict[Any, Any] = {}
        engine = execution_engine or self.execution_engine or PoolEngine()
        self.workflow_instance_id = uuid.uuid4().hex
        step_names = None
        if runtime_store:
            step_names = self._step_name_map()
            runtime_store.create_run(
                self.workflow_id,
                self.workflow_instance_id,
                step_names.values(),
            )
        if self.tracer:
            from .tracing import BoundTracer

            bound = BoundTracer(
                self.tracer, self.workflow_id, self.workflow_instance_id
            )
            for step in self._collect_steps():
                step.tracer = bound
            bound.record({"event": "workflow_started"})
        self.state = Status.RUNNING
        try:
            await self.before_all_async(shared)
            result = await self._run_async(shared, engine, runtime_store, step_names)
            await self.after_all_async(shared)
            self.state = Status.SUCCEEDED
        except Exception:
            self.state = Status.FAILED
            for step in self._collect_steps():
                if step.state == Status.PENDING:
                    step.state = Status.CANCELLED
                    step._log_event("step_cancelled")
            if self.tracer:
                from .tracing import BoundTracer

                BoundTracer(
                    self.tracer, self.workflow_id, self.workflow_instance_id
                ).record({"event": "workflow_finished"})
            return None
        if self.tracer:
            from .tracing import BoundTracer

            BoundTracer(
                self.tracer, self.workflow_id, self.workflow_instance_id
            ).record({"event": "workflow_finished"})
        if runtime_store:
            runtime_store.finalize_run(self.workflow_id, self.workflow_instance_id)
        if self.outputs:
            if len(self.outputs) == 1:
                return shared.get(self.outputs[0], result)
            return [shared.get(o) for o in self.outputs]
        return result

    async def _run_engine_async(
        self,
        shared: Any,
        engine: ExecutionEngine,
        runtime_store: "RuntimeStorage | None" = None,
        step_names: dict[Step, str] | None = None,
    ) -> Any:
        nodes = self._collect_steps()
        indegree: Dict[Step, int] = {n: 0 for n in nodes}
        for succ in nodes:
            group_preds: set[Step] = set()
            if isinstance(succ, Task):
                succ.or_remaining = {k: True for k in succ.or_groups}
                for group in succ.or_groups.values():
                    indegree[succ] += 1
                    group_preds.update(group)
            for pred in succ.predecessors:
                if pred not in group_preds:
                    indegree[succ] += 1

        ready = [n for n, d in indegree.items() if d == 0]
        for step in ready:
            step._log_event("step_enqueued")
        last_result: Any = None
        while ready:
            current_group = min(s.execution_group for s in ready)
            batch = [s for s in ready if s.execution_group == current_group]
            ready = [s for s in ready if s.execution_group != current_group]

            exc: dict[str, Exception] = {}

            async def run_step(s: Step) -> Any:
                if runtime_store and step_names:
                    runtime_store.set_state(
                        self.workflow_id,
                        self.workflow_instance_id,
                        step_names[s],
                        Status.RUNNING,
                    )
                try:
                    result = await self._execute_step_async(s, shared, engine)
                    if runtime_store and step_names:
                        runtime_store.set_state(
                            self.workflow_id,
                            self.workflow_instance_id,
                            step_names[s],
                            s.state,
                        )
                    return result
                except Exception as e:  # pragma: no cover - bubble up
                    exc['err'] = e
                    if runtime_store and step_names:
                        runtime_store.set_state(
                            self.workflow_id,
                            self.workflow_instance_id,
                            step_names[s],
                            Status.FAILED,
                        )
                    return None

            results = await engine.run_async_steps(
                [lambda s=s: run_step(s) for s in batch]
            )

            if exc:
                raise exc['err']

            for step, res in zip(batch, results):
                last_result = res
                action = res if isinstance(res, str) else None
                for succ in self.get_next_steps(step, action):
                    decreased = False
                    if isinstance(succ, Task):
                        for name, group in succ.or_groups.items():
                            if step in group and succ.or_remaining.get(name):
                                succ.or_remaining[name] = False
                                succ.or_triggered[name] = step
                                indegree[succ] -= 1
                                decreased = True
                                break
                    if not decreased:
                        indegree[succ] -= 1
                    if indegree[succ] == 0:
                        succ._log_event("step_enqueued")
                        if runtime_store and step_names:
                            runtime_store.enqueue(
                                self.workflow_id,
                                self.workflow_instance_id,
                                step_names[succ],
                            )
                        ready.append(succ)

        return last_result

    async def _run_async(
        self,
        shared: Any,
        engine: ExecutionEngine,
        runtime_store: "RuntimeStorage | None" = None,
        step_names: dict[Step, str] | None = None,
    ) -> Any:
        p = await self.setup_async(shared)
        o = await self._run_engine_async(shared, engine, runtime_store, step_names)
        return await self.teardown_async(shared, p, o)

    async def teardown_async(self, shared: Any, setup_res: Any, exec_res: Any) -> Any:
        return exec_res


class AsyncBatchWorkflow(AsyncWorkflow, BatchWorkflow):
    async def _run_async(self, shared: Any) -> Any:
        pr = await self.setup_async(shared) or []
        for bp in pr:
            await self._orch_async(shared, {**self.params, **bp})
        return await self.teardown_async(shared, pr, None)


class AsyncParallelBatchWorkflow(AsyncWorkflow, BatchWorkflow):
    async def _run_async(self, shared: Any) -> Any:
        pr = await self.setup_async(shared) or []
        await asyncio.gather(
            *(self._orch_async(shared, {**self.params, **bp}) for bp in pr)
        )
        return await self.teardown_async(shared, pr, None)


class Condition:
    """Base class for conditional dependency evaluation."""

    def __call__(self, value: Any, source: Step) -> bool:
        return bool(value)


class Depends:
    """Declare a dependency on another callable or step with an optional condition."""

    def __init__(
        self,
        *objs: Callable[..., Any] | Step | Sequence[Callable[..., Any] | Step],
        condition: Callable[[Any], bool] | Condition | type[Condition] | None = None,
    ) -> None:
        if len(objs) == 1:
            obj = objs[0]
            if isinstance(obj, (list, tuple)):
                self.obj = list(obj)
            else:
                self.obj = obj
        else:
            self.obj = [o for obj in objs for o in (obj if isinstance(obj, (list, tuple)) else [obj])]
        if isinstance(condition, type) and issubclass(condition, Condition):
            self.condition = condition()
        else:
            self.condition = condition


class FunctionTask(Task):
    """Task wrapping a Python callable."""

    def __init__(
        self, func: Callable[..., Any], max_retries: int = 1, wait: float = 0
    ) -> None:
        super().__init__(max_retries, wait)
        self.func = func
        self.deps: Dict[str, FunctionTask] = {}
        self.dep_conditions: Dict[str, Callable[[Any], bool]] = {}

    def setup(self, shared: Dict["FunctionTask", Any]) -> Dict["FunctionTask", Any]:  # type: ignore[override]
        return shared

    def run_step(self, shared: Dict["FunctionTask", Any]) -> Any:
        kwargs = {}
        for name, dep in self.deps.items():
            if isinstance(dep, list):
                chosen = self.or_triggered.get(name) or dep[0]
                val = shared[chosen]
                cond = self.dep_conditions.get(name)
                if cond is not None:
                    if isinstance(cond, Condition):
                        if not cond(val, chosen):
                            return None
                    else:
                        if not cond(val):
                            return None
                kwargs[name] = val
            else:
                val = shared[dep]
                cond = self.dep_conditions.get(name)
                if cond is not None:
                    if isinstance(cond, Condition):
                        if not cond(val, dep):
                            return None
                    else:
                        if not cond(val):
                            return None
                kwargs[name] = val
        kwargs.update({k: v for k, v in self.params.items() if k not in kwargs})
        result = self.func(**kwargs)
        shared[self] = result
        return result

    def teardown(self, shared: Any, setup_res: Any, exec_res: Any) -> Any:  # type: ignore[override]
        return exec_res


class TypedTask(Task):
    """Deprecated alias for :class:`Task`."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            "TypedTask is deprecated; inherit from Task instead", DeprecationWarning
        )
        super().__init__(*args, **kwargs)


def workflow_from_functions(outputs: List[Callable[..., Any]]) -> Workflow:
    """Create a :class:`Workflow` from typed Python functions."""

    steps: Dict[Callable[..., Any], FunctionTask] = {}
    has_pred: Dict[Step, bool] = {}

    def build_step(obj: Callable[..., Any] | Step) -> Step:
        if isinstance(obj, Step):
            return obj
        func = obj
        if func in steps:
            return steps[func]
        step = FunctionTask(func)
        steps[func] = step
        for param in inspect.signature(func).parameters.values():
            if isinstance(param.default, Depends):
                dep_obj = param.default.obj
                if isinstance(dep_obj, list):
                    deps = [build_step(o) for o in dep_obj]
                    for d in deps:
                        d >> step
                    if isinstance(step, FunctionTask):
                        step.deps[param.name] = deps  # type: ignore[assignment]
                        step.or_groups[param.name] = deps
                        if param.default.condition is not None:
                            step.dep_conditions[param.name] = param.default.condition
                    has_pred[step] = True
                else:
                    dep = build_step(dep_obj)
                    dep >> step
                    if isinstance(step, FunctionTask):
                        step.deps[param.name] = dep  # type: ignore[assignment]
                        if param.default.condition is not None:
                            step.dep_conditions[param.name] = param.default.condition
                    has_pred[step] = True
        has_pred.setdefault(step, False)
        return step

    step_outputs = [build_step(func) for func in outputs]

    return Workflow(outputs=step_outputs)
