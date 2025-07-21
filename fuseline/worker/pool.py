"""Thread-based execution engine."""

from __future__ import annotations

import asyncio
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, Iterable, List

from ..interfaces import ExecutionEngine


class PoolEngine(ExecutionEngine):
    """Execute callables using a pool of worker threads."""

    def __init__(self, processes: int = 1) -> None:
        self.processes = max(1, processes)

    def run_steps(self, steps: Iterable[Callable[[], Any]]) -> List[Any]:
        tasks = list(steps)
        if len(tasks) <= 1 or self.processes == 1:
            return [task() for task in tasks]
        if len(tasks) > self.processes:
            warnings.warn(f"PoolEngine limited to {self.processes} workers; running {len(tasks)} tasks sequentially")
            return [task() for task in tasks]
        with ThreadPoolExecutor(max_workers=self.processes) as executor:
            futures = [executor.submit(task) for task in tasks]
            return [f.result() for f in futures]

    async def run_async_steps(self, steps: Iterable[Callable[[], Awaitable[Any]]]) -> List[Any]:
        tasks = list(steps)
        if len(tasks) <= 1 or self.processes == 1:
            return [await t() for t in tasks]
        if len(tasks) > self.processes:
            warnings.warn(f"PoolEngine limited to {self.processes} workers; running {len(tasks)} tasks sequentially")
            return [await t() for t in tasks]
        return await asyncio.gather(*(t() for t in tasks))
