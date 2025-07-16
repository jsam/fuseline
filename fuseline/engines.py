"""Execution engines for Workflow."""

from __future__ import annotations

import asyncio
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, Iterable, List

from .broker import Broker

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
    """Execute workflow steps fetched from a :class:`Broker`."""

    def __init__(self, broker: "Broker", workflows: Iterable["Workflow"]) -> None:
        self.broker = broker
        self.workflows = {wf.workflow_id: wf for wf in workflows}
        self._step_names: dict[str, dict["Step", str]] = {}
        self._rev_names: dict[str, dict[str, "Step"]] = {}
        for wf in workflows:
            mapping = wf._step_name_map()
            self._step_names[wf.workflow_id] = mapping
            self._rev_names[wf.workflow_id] = {n: s for s, n in mapping.items()}
        self.worker_id = broker.register_worker(workflows)

    def work(self) -> None:
        while True:
            item = self.broker.get_step(self.worker_id)
            if item is None:
                break
            wf_id, instance_id, step_name, payload = item
            workflow = self.workflows[wf_id]
            step = self._rev_names[wf_id][step_name]
            shared = {
                self._rev_names[wf_id][name]: value
                for name, value in payload.get("results", {}).items()
            }
            workflow.params.update(payload.get("workflow_inputs", {}))
            result = workflow._execute_step(step, shared)
            self.broker.report_step(
                self.worker_id,
                wf_id,
                instance_id,
                step_name,
                step.state,
                result,
            )

