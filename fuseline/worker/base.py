from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Iterable, List


class ExecutionEngine(ABC):
    """Interface for workflow execution backends."""

    @abstractmethod
    def run_steps(self, steps: Iterable[Callable[[], Any]]) -> List[Any]:
        """Execute a sequence of callables synchronously."""

    async def run_async_steps(
        self, steps: Iterable[Callable[[], Awaitable[Any]]]
    ) -> List[Any]:
        """Execute a sequence of async callables."""
        return [await step() for step in steps]
