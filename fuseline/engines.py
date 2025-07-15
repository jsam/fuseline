"""Execution engines for Workflow."""

from __future__ import annotations

import asyncio
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, Iterable, List

from .interfaces import ExecutionEngine


class PoolEngine(ExecutionEngine):
    """Execute callables using a pool of worker threads."""

    def __init__(self, processes: int = 1) -> None:
        self.processes = max(1, processes)

    def run_steps(self, steps: Iterable[Callable[[], Any]]) -> List[Any]:
        tasks = list(steps)
        if len(tasks) <= 1 or self.processes == 1:
            return [task() for task in tasks]
        if len(tasks) > self.processes:
            warnings.warn(
                f"PoolEngine limited to {self.processes} workers; running {len(tasks)} tasks sequentially"
            )
            return [task() for task in tasks]
        with ThreadPoolExecutor(max_workers=self.processes) as executor:
            futures = [executor.submit(task) for task in tasks]
            return [f.result() for f in futures]

    async def run_async_steps(
        self, steps: Iterable[Callable[[], Awaitable[Any]]]
    ) -> List[Any]:
        tasks = list(steps)
        if len(tasks) <= 1 or self.processes == 1:
            return [await t() for t in tasks]
        if len(tasks) > self.processes:
            warnings.warn(
                f"PoolEngine limited to {self.processes} workers; running {len(tasks)} tasks sequentially"
            )
            return [await t() for t in tasks]
        return await asyncio.gather(*(t() for t in tasks))


class ProcessEngine:
    """Execute workflow steps fetched from a :class:`RuntimeStorage`."""

    def __init__(self, workflow: "Workflow", store: "RuntimeStorage") -> None:
        from .workflow import Step

        self.workflow = workflow
        self.store = store
        self.step_names = workflow._step_name_map()
        self._step_map: dict[str, Step] = {n: s for s, n in self.step_names.items()}

    def work(self, instance_id: str) -> None:
        from .workflow import Status

        shared: dict[Any, Any] = {}
        while True:
            step_name = self.store.fetch_next(
                self.workflow.workflow_id, instance_id
            )
            if step_name is None:
                break
            step = self._step_map.get(step_name)
            if step is None:
                continue
            self.store.set_state(
                self.workflow.workflow_id, instance_id, step_name, Status.RUNNING
            )
            result = self.workflow._execute_step(step, shared)
            self.store.set_state(
                self.workflow.workflow_id, instance_id, step_name, step.state
            )
            action = result if isinstance(result, str) else None
            for succ in self.workflow.get_next_steps(step, action):
                if all(
                    self.store.get_state(
                        self.workflow.workflow_id,
                        instance_id,
                        self.step_names[pred],
                    )
                    in {Status.SUCCEEDED, Status.SKIPPED}
                    for pred in succ.predecessors
                ):
                    self.store.enqueue(
                        self.workflow.workflow_id,
                        instance_id,
                        self.step_names[succ],
                    )
        self.store.finalize_run(self.workflow.workflow_id, instance_id)
