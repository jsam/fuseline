# -*- coding: utf-8 -*-
"""Lightweight workflow interface.

This module provides simple synchronous and asynchronous workflow primitives
based on nodes and flows. The design is inspired by the user's suggestion in
the issue conversation and is intentionally minimal so it can be adopted
incrementally without disrupting the existing network implementation.
"""

from __future__ import annotations

import asyncio
import copy
import time
import warnings
from typing import Any, Dict, Optional

from .core.network import Network


class Step:
    """Minimal unit of work in a :class:`Workflow`."""

    def __init__(self) -> None:
        self.params: Dict[str, Any] = {}
        self.successors: Dict[str, "Step"] = {}

    def set_params(self, params: Dict[str, Any]) -> None:
        """Store parameters passed from the workflow."""
        self.params = params

    def next(self, node: "Step", action: str = "default") -> "Step":
        """Add a successor step to run after this one."""
        if action in self.successors:
            warnings.warn(f"Overwriting successor for action '{action}'")
        self.successors[action] = node
        return node

    def prep(self, shared: Any) -> Any:  # pragma: no cover - to be overridden
        pass

    def exec(self, prep_res: Any) -> Any:  # pragma: no cover - to be overridden
        pass

    def post(self, shared: Any, prep_res: Any, exec_res: Any) -> Any:  # pragma: no cover
        pass

    def _exec(self, prep_res: Any) -> Any:
        return self.exec(prep_res)

    def _run(self, shared: Any) -> Any:
        p = self.prep(shared)
        e = self._exec(p)
        return self.post(shared, p, e)

    def run(self, shared: Any) -> Any:
        if self.successors:
            warnings.warn("Step won't run successors. Use Workflow.")
        return self._run(shared)

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
    """Step with optional retry logic."""

    def __init__(self, max_retries: int = 1, wait: float = 0) -> None:
        super().__init__()
        self.max_retries = max_retries
        self.wait = wait
        self.cur_retry: Optional[int] = None

    def exec_fallback(self, prep_res: Any, exc: Exception) -> Any:
        raise exc

    def _exec(self, prep_res: Any) -> Any:
        for self.cur_retry in range(self.max_retries):
            try:
                return self.exec(prep_res)
            except Exception as e:
                if self.cur_retry == self.max_retries - 1:
                    return self.exec_fallback(prep_res, e)
                if self.wait > 0:
                    time.sleep(self.wait)


class BatchTask(Task):
    """Execute a sequence of items using a :class:`Task`."""

    def _exec(self, items: Any) -> Any:
        return [super(BatchTask, self)._exec(i) for i in (items or [])]


class Workflow(Step):
    """A sequence of :class:`Step` objects."""

    def __init__(self, start: Optional[Step] = None) -> None:
        super().__init__()
        self.start_step = start

    def start(self, start: Step) -> Step:
        """Specify the initial step for this workflow."""
        self.start_step = start
        return start

    def get_next_step(self, curr: Step, action: Optional[str]) -> Optional[Step]:
        nxt = curr.successors.get(action or "default")
        if not nxt and curr.successors:
            warnings.warn(
                f"Workflow ends: '{action}' not found in {list(curr.successors)}"
            )
        return nxt

    def _orch(self, shared: Any, params: Optional[Dict[str, Any]] = None) -> Any:
        curr: Optional[Step] = copy.copy(self.start_step)
        p = params or {**self.params}
        last_action: Optional[str] = None
        while curr:
            curr.set_params(p)
            last_action = curr._run(shared)
            curr = copy.copy(self.get_next_step(curr, last_action))
        return last_action

    def _run(self, shared: Any) -> Any:
        p = self.prep(shared)
        o = self._orch(shared)
        return self.post(shared, p, o)

    def post(self, shared: Any, prep_res: Any, exec_res: Any) -> Any:
        return exec_res


class BatchWorkflow(Workflow):
    """Run the same workflow for a batch of parameter sets."""

    def _run(self, shared: Any) -> Any:
        pr = self.prep(shared) or []
        for bp in pr:
            self._orch(shared, {**self.params, **bp})
        return self.post(shared, pr, None)


class AsyncTask(Task):
    async def prep_async(self, shared: Any) -> Any:  # pragma: no cover
        pass

    async def exec_async(self, prep_res: Any) -> Any:  # pragma: no cover
        pass

    async def exec_fallback_async(self, prep_res: Any, exc: Exception) -> Any:  # pragma: no cover
        raise exc

    async def post_async(self, shared: Any, prep_res: Any, exec_res: Any) -> Any:  # pragma: no cover
        pass

    async def _exec(self, prep_res: Any) -> Any:
        for i in range(self.max_retries):
            try:
                return await self.exec_async(prep_res)
            except Exception as e:
                if i == self.max_retries - 1:
                    return await self.exec_fallback_async(prep_res, e)
                if self.wait > 0:
                    await asyncio.sleep(self.wait)

    async def run_async(self, shared: Any) -> Any:
        if self.successors:
            warnings.warn("Step won't run successors. Use AsyncWorkflow.")
        return await self._run_async(shared)

    async def _run_async(self, shared: Any) -> Any:
        p = await self.prep_async(shared)
        e = await self._exec(p)
        return await self.post_async(shared, p, e)

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
    async def _orch_async(self, shared: Any, params: Optional[Dict[str, Any]] = None) -> Any:
        curr: Optional[Step] = copy.copy(self.start_step)
        p = params or {**self.params}
        last_action: Optional[str] = None
        while curr:
            curr.set_params(p)
            last_action = (
                await curr._run_async(shared)
                if isinstance(curr, AsyncTask)
                else curr._run(shared)
            )
            curr = copy.copy(self.get_next_step(curr, last_action))
        return last_action

    async def _run_async(self, shared: Any) -> Any:
        p = await self.prep_async(shared)
        o = await self._orch_async(shared)
        return await self.post_async(shared, p, o)

    async def post_async(self, shared: Any, prep_res: Any, exec_res: Any) -> Any:
        return exec_res


class AsyncBatchWorkflow(AsyncWorkflow, BatchWorkflow):
    async def _run_async(self, shared: Any) -> Any:
        pr = await self.prep_async(shared) or []
        for bp in pr:
            await self._orch_async(shared, {**self.params, **bp})
        return await self.post_async(shared, pr, None)


class AsyncParallelBatchWorkflow(AsyncWorkflow, BatchWorkflow):
    async def _run_async(self, shared: Any) -> Any:
        pr = await self.prep_async(shared) or []
        await asyncio.gather(
            *(self._orch_async(shared, {**self.params, **bp}) for bp in pr)
        )
        return await self.post_async(shared, pr, None)


class NetworkTask(Task):
    """Wrap a :class:`~fuseline.core.network.Network` as a :class:`Task`."""

    def __init__(self, network: Network, max_retries: int = 1, wait: float = 0) -> None:
        super().__init__(max_retries, wait)
        self.network = network

    def exec(self, prep_res: Any) -> Any:
        return self.network.run(**self.params)


class AsyncNetworkTask(AsyncTask):
    """Async wrapper around :class:`NetworkTask`."""

    def __init__(self, network: Network, max_retries: int = 1, wait: float = 0) -> None:
        super().__init__(max_retries, wait)
        self.network = network

    async def exec_async(self, prep_res: Any) -> Any:
        return await asyncio.to_thread(self.network.run, **self.params)

