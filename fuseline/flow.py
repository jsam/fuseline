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


class BaseNode:
    """Base building block for a workflow graph."""

    def __init__(self) -> None:
        self.params: Dict[str, Any] = {}
        self.successors: Dict[str, "BaseNode"] = {}

    def set_params(self, params: Dict[str, Any]) -> None:
        self.params = params

    def next(self, node: "BaseNode", action: str = "default") -> "BaseNode":
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
            warnings.warn("Node won't run successors. Use Flow.")
        return self._run(shared)

    def __rshift__(self, other: "BaseNode") -> "BaseNode":
        return self.next(other)

    def __sub__(self, action: str) -> "_ConditionalTransition":
        if isinstance(action, str):
            return _ConditionalTransition(self, action)
        raise TypeError("Action must be a string")


class _ConditionalTransition:
    def __init__(self, src: BaseNode, action: str) -> None:
        self.src = src
        self.action = action

    def __rshift__(self, tgt: BaseNode) -> BaseNode:
        return self.src.next(tgt, self.action)


class Node(BaseNode):
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


class BatchNode(Node):
    def _exec(self, items: Any) -> Any:
        return [super(BatchNode, self)._exec(i) for i in (items or [])]


class Flow(BaseNode):
    def __init__(self, start: Optional[BaseNode] = None) -> None:
        super().__init__()
        self.start_node = start

    def start(self, start: BaseNode) -> BaseNode:
        self.start_node = start
        return start

    def get_next_node(self, curr: BaseNode, action: Optional[str]) -> Optional[BaseNode]:
        nxt = curr.successors.get(action or "default")
        if not nxt and curr.successors:
            warnings.warn(
                f"Flow ends: '{action}' not found in {list(curr.successors)}"
            )
        return nxt

    def _orch(self, shared: Any, params: Optional[Dict[str, Any]] = None) -> Any:
        curr: Optional[BaseNode] = copy.copy(self.start_node)
        p = params or {**self.params}
        last_action: Optional[str] = None
        while curr:
            curr.set_params(p)
            last_action = curr._run(shared)
            curr = copy.copy(self.get_next_node(curr, last_action))
        return last_action

    def _run(self, shared: Any) -> Any:
        p = self.prep(shared)
        o = self._orch(shared)
        return self.post(shared, p, o)

    def post(self, shared: Any, prep_res: Any, exec_res: Any) -> Any:
        return exec_res


class BatchFlow(Flow):
    def _run(self, shared: Any) -> Any:
        pr = self.prep(shared) or []
        for bp in pr:
            self._orch(shared, {**self.params, **bp})
        return self.post(shared, pr, None)


class AsyncNode(Node):
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
            warnings.warn("Node won't run successors. Use AsyncFlow.")
        return await self._run_async(shared)

    async def _run_async(self, shared: Any) -> Any:
        p = await self.prep_async(shared)
        e = await self._exec(p)
        return await self.post_async(shared, p, e)

    def _run(self, shared: Any) -> Any:
        raise RuntimeError("Use run_async.")


class AsyncBatchNode(AsyncNode, BatchNode):
    async def _exec(self, items: Any) -> Any:
        return [await super(AsyncBatchNode, self)._exec(i) for i in items]


class AsyncParallelBatchNode(AsyncNode, BatchNode):
    async def _exec(self, items: Any) -> Any:
        return await asyncio.gather(
            *(super(AsyncParallelBatchNode, self)._exec(i) for i in items)
        )


class AsyncFlow(Flow, AsyncNode):
    async def _orch_async(self, shared: Any, params: Optional[Dict[str, Any]] = None) -> Any:
        curr: Optional[BaseNode] = copy.copy(self.start_node)
        p = params or {**self.params}
        last_action: Optional[str] = None
        while curr:
            curr.set_params(p)
            last_action = (
                await curr._run_async(shared)
                if isinstance(curr, AsyncNode)
                else curr._run(shared)
            )
            curr = copy.copy(self.get_next_node(curr, last_action))
        return last_action

    async def _run_async(self, shared: Any) -> Any:
        p = await self.prep_async(shared)
        o = await self._orch_async(shared)
        return await self.post_async(shared, p, o)

    async def post_async(self, shared: Any, prep_res: Any, exec_res: Any) -> Any:
        return exec_res


class AsyncBatchFlow(AsyncFlow, BatchFlow):
    async def _run_async(self, shared: Any) -> Any:
        pr = await self.prep_async(shared) or []
        for bp in pr:
            await self._orch_async(shared, {**self.params, **bp})
        return await self.post_async(shared, pr, None)


class AsyncParallelBatchFlow(AsyncFlow, BatchFlow):
    async def _run_async(self, shared: Any) -> Any:
        pr = await self.prep_async(shared) or []
        await asyncio.gather(
            *(self._orch_async(shared, {**self.params, **bp}) for bp in pr)
        )
        return await self.post_async(shared, pr, None)

