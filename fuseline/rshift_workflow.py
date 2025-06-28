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
import json
import time
import warnings
from typing import Any, Callable, Dict, List, Optional

from .engines import ProcessEngine


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
        self.trace_event: Callable[[dict], None] | None = None

    def _log_event(self, event: str, **data: Any) -> None:
        if self.trace_event:
            self.trace_event({"event": event, "step": type(self).__name__, **data})

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

    def teardown(self, shared: Any, setup_res: Any, exec_res: Any) -> Any:  # pragma: no cover
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
        self._log_event("step_finished", result=result, skipped=getattr(self, "was_skipped", False))
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
        self.deps: Dict[str, Step] = {}
        self.dep_conditions: Dict[str, Callable[[Any], bool]] = {}
        self.was_skipped = False
        run_method = type(self).run_step
        sig = inspect.signature(run_method)
        params = list(sig.parameters.values())
        self.param_names: List[str] = []
        for param in params:
            if isinstance(param.default, Depends):
                dep_obj = param.default.obj
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
                        val = setup_res[dep]
                        cond = self.dep_conditions.get(name)
                        if cond is not None:
                            passed = bool(cond(val))
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
        execution_engine: "ProcessEngine | None" = None,
        *,
        trace: str | None = None,
    ) -> None:
        super().__init__()
        self.outputs = outputs
        self.execution_engine = execution_engine
        self.trace_path = trace
        self.roots = self._find_roots(outputs)
        self.start_step = self.roots[0] if self.roots else None

    def _write_trace(self, record: dict) -> None:
        if not self.trace_path:
            return
        with open(self.trace_path, "a", encoding="utf-8") as f:
            json_line = json.dumps(record, default=str)
            f.write(json_line + "\n")

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
                    preds[step] = True
                    walk(dep)
            preds.setdefault(step, False)

        for out in outputs:
            walk(out)

        return [s for s, has_pred in preds.items() if not has_pred]

    def export(self, path: str) -> None:
        """Serialize the workflow graph to YAML.

        The output contains all steps with their class names, successors and
        typed dependencies. The file is written using a JSON compatible YAML
        format so no extra dependencies are required.
        """

        steps = self._collect_steps()
        name_map = {step: f"step{idx}" for idx, step in enumerate(steps)}

        data: Dict[str, Any] = {"steps": {}, "outputs": [name_map[o] for o in self.outputs]}
        for step in steps:
            succ = step.successors
            if len(succ) == 1 and "default" in succ:
                succ_data: Any = [name_map[t] for t in succ.get("default", [])]
            else:
                succ_data = {act: [name_map[t] for t in tgts] for act, tgts in succ.items()}

            entry = {
                "class": type(step).__name__,
                "successors": succ_data,
            }
            if isinstance(step, Task) and step.deps:
                deps_data = {}
                for name, dep in step.deps.items():
                    dep_entry: Dict[str, Any] = {"step": name_map[dep]}
                    cond = step.dep_conditions.get(name)
                    if cond is not None:
                        cond_name = getattr(cond, "__name__", cond.__class__.__name__)
                        cond_info: Dict[str, Any] = {"type": cond_name}
                        cond_params = getattr(cond, "__dict__", None)
                        if cond_params:
                            cond_info["params"] = cond_params
                        dep_entry["condition"] = cond_info
                    deps_data[name] = dep_entry
                entry["dependencies"] = deps_data
            data["steps"][name_map[step]] = entry

        def _dump_yaml(obj: Any, indent: int = 0) -> str:
            pad = "  " * indent
            if isinstance(obj, dict):
                lines = []
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        lines.append(f"{pad}{k}:")
                        lines.append(_dump_yaml(v, indent + 1))
                    else:
                        lines.append(f"{pad}{k}: {v}")
                return "\n".join(lines)
            if isinstance(obj, list):
                lines = []
                for item in obj:
                    if isinstance(item, (dict, list)):
                        lines.append(f"{pad}-")
                        lines.append(_dump_yaml(item, indent + 1))
                    else:
                        lines.append(f"{pad}- {item}")
                return "\n".join(lines)
            return f"{pad}{obj}"

        with open(path, "w", encoding="utf-8") as f:
            f.write(_dump_yaml(data))

    def run(
        self, inputs: Optional[Dict[str, Any]] = None, execution_engine: "ProcessEngine | None" = None
    ) -> Any:  # type: ignore[override]
        """Execute the workflow.

        Parameters
        ----------
        inputs:
            Parameters passed to the starting steps.  They are distributed to
            tasks based on parameter names.
        """
        self.params = inputs or {}
        shared: Dict[Any, Any] = {}
        engine = execution_engine or self.execution_engine or ProcessEngine()
        if self.trace_path:
            open(self.trace_path, "w", encoding="utf-8").close()
            for step in self._collect_steps():
                step.trace_event = self._write_trace
            self._write_trace({"event": "workflow_started"})
        self.before_all(shared)
        setup_res = self.setup(shared)
        result = self._run_engine(shared, engine)
        result = self.teardown(shared, setup_res, result)
        self.after_all(shared)
        if self.trace_path:
            self._write_trace({"event": "workflow_finished"})
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
                    walk(dep)
            seen.append(step)

        for out in self.outputs:
            walk(out)
        return seen

    def _execute_step(self, step: Step, shared: Dict[Any, Any]) -> Any:
        step.set_params({**self.params, **step.params})
        step.before_all(shared)
        step._log_event("step_started")
        result = step._run(shared)
        step._log_event(
            "step_finished",
            result=result,
            skipped=getattr(step, "was_skipped", False),
        )
        if isinstance(shared, dict):
            shared[step] = result
        step.after_all(shared)
        return result

    def _run_engine(self, shared: Any, engine: ProcessEngine) -> Any:
        nodes = self._collect_steps()
        indegree: Dict[Step, int] = {n: 0 for n in nodes}
        for n in nodes:
            for succs in n.successors.values():
                for succ in succs:
                    indegree[succ] = indegree.get(succ, 0) + 1

        ready = [n for n, d in indegree.items() if d == 0]
        for step in ready:
            step._log_event("step_enqueued")
        last_result: Any = None
        while ready:
            batch = ready
            ready = []

            def run_step(s: Step = None) -> Any:
                return self._execute_step(s, shared)

            results = engine.run_steps([lambda s=s: run_step(s) for s in batch])

            for step, res in zip(batch, results):
                last_result = res
                action = res if isinstance(res, str) else None
                for succ in self.get_next_steps(step, action):
                    indegree[succ] -= 1
                    if indegree[succ] == 0:
                        succ._log_event("step_enqueued")
                        ready.append(succ)

        return last_result

    def teardown(self, shared: Any, setup_res: Any, exec_res: Any) -> Any:
        return exec_res


class BatchWorkflow(Workflow):
    """Run the same workflow for a batch of parameter sets."""

    def run(
        self, inputs: Optional[Dict[str, Any]] = None, execution_engine: "ProcessEngine | None" = None
    ) -> Any:
        self.params = inputs or {}
        shared: Dict[Any, Any] = {}
        engine = execution_engine or self.execution_engine or ProcessEngine()
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
        self.was_skipped = False
        run_method = type(self).run_step_async
        sig = inspect.signature(run_method)
        params = list(sig.parameters.values())
        self.param_names = []
        for param in params:
            if isinstance(param.default, Depends):
                dep_obj = param.default.obj
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

    async def run_step_async(self, setup_res: Any) -> Any:  # pragma: no cover - to be overridden
        pass

    async def _exec(self, setup_res: Any) -> Any:
        self.was_skipped = False
        for i in range(self.max_retries):
            try:
                if self.is_typed:
                    kwargs = {}
                    for name, dep in self.deps.items():
                        val = setup_res[dep]
                        cond = self.dep_conditions.get(name)
                        if cond is not None:
                            passed = bool(cond(val))
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
    async def run_step_fallback_async(self, setup_res: Any, exc: Exception) -> Any:  # pragma: no cover
        raise exc

    async def teardown_async(self, shared: Any, setup_res: Any, exec_res: Any) -> Any:  # pragma: no cover
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
        self._log_event("step_finished", result=result, skipped=getattr(self, "was_skipped", False))
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
    async def _execute_step_async(self, step: Step, shared: Dict[Any, Any], engine: ProcessEngine) -> Any:
        step.set_params({**self.params, **step.params})
        if isinstance(step, AsyncWorkflow):
            result = await step._run_async(shared, engine)
        elif isinstance(step, AsyncTask):
            await step.before_all_async(shared)
            step._log_event("step_started")
            result = await step._run_async(shared)
            step._log_event(
                "step_finished",
                result=result,
                skipped=getattr(step, "was_skipped", False),
            )
            if isinstance(shared, dict):
                shared[step] = result
            await step.after_all_async(shared)
        else:
            result = self._execute_step(step, shared)
        return result

    async def run_async(
        self, inputs: Optional[Dict[str, Any]] = None, execution_engine: "ProcessEngine | None" = None
    ) -> Any:
        self.params = inputs or {}
        shared: Dict[Any, Any] = {}
        engine = execution_engine or self.execution_engine or ProcessEngine()
        if self.trace_path:
            open(self.trace_path, "w", encoding="utf-8").close()
            for step in self._collect_steps():
                step.trace_event = self._write_trace
            self._write_trace({"event": "workflow_started"})
        await self.before_all_async(shared)
        result = await self._run_async(shared, engine)
        await self.after_all_async(shared)
        if self.trace_path:
            self._write_trace({"event": "workflow_finished"})
        if self.outputs:
            if len(self.outputs) == 1:
                return shared.get(self.outputs[0], result)
            return [shared.get(o) for o in self.outputs]
        return result

    async def _run_engine_async(self, shared: Any, engine: ProcessEngine) -> Any:
        nodes = self._collect_steps()
        indegree: Dict[Step, int] = {n: 0 for n in nodes}
        for n in nodes:
            for succs in n.successors.values():
                for succ in succs:
                    indegree[succ] = indegree.get(succ, 0) + 1

        ready = [n for n, d in indegree.items() if d == 0]
        for step in ready:
            step._log_event("step_enqueued")
        last_result: Any = None
        while ready:
            batch = ready
            ready = []

            async def run_step(s: Step) -> Any:
                return await self._execute_step_async(s, shared, engine)

            if engine.processes == 1 or len(batch) <= 1:
                results = [await run_step(s) for s in batch]
            else:
                if len(batch) > engine.processes:
                    warnings.warn(
                        f"ProcessEngine limited to {engine.processes} workers; running {len(batch)} tasks sequentially"
                    )
                    results = [await run_step(s) for s in batch]
                else:
                    results = await asyncio.gather(*(run_step(s) for s in batch))

            for step, res in zip(batch, results):
                last_result = res
                action = res if isinstance(res, str) else None
                for succ in self.get_next_steps(step, action):
                    indegree[succ] -= 1
                    if indegree[succ] == 0:
                        succ._log_event("step_enqueued")
                        ready.append(succ)

        return last_result

    async def _run_async(self, shared: Any, engine: ProcessEngine) -> Any:
        p = await self.setup_async(shared)
        o = await self._run_engine_async(shared, engine)
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

    def __call__(self, value: Any) -> bool:
        return bool(value)


class Depends:
    """Declare a dependency on another callable or step with an optional condition."""

    def __init__(
        self,
        obj: Callable[..., Any] | Step,
        *,
        condition: Callable[[Any], bool] | Condition | type[Condition] | None = None,
    ) -> None:
        self.obj = obj
        if isinstance(condition, type) and issubclass(condition, Condition):
            self.condition = condition()
        else:
            self.condition = condition


class FunctionTask(Task):
    """Task wrapping a Python callable."""

    def __init__(self, func: Callable[..., Any], max_retries: int = 1, wait: float = 0) -> None:
        super().__init__(max_retries, wait)
        self.func = func
        self.deps: Dict[str, FunctionTask] = {}
        self.dep_conditions: Dict[str, Callable[[Any], bool]] = {}

    def setup(self, shared: Dict["FunctionTask", Any]) -> Dict["FunctionTask", Any]:  # type: ignore[override]
        return shared

    def run_step(self, shared: Dict["FunctionTask", Any]) -> Any:
        kwargs = {}
        for name, dep in self.deps.items():
            val = shared[dep]
            cond = self.dep_conditions.get(name)
            if cond is not None and not cond(val):
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
        warnings.warn("TypedTask is deprecated; inherit from Task instead", DeprecationWarning)
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

