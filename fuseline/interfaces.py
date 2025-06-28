from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Iterable, List

if TYPE_CHECKING:  # pragma: no cover - circular import for type checking
    from .workflow import Workflow


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


class Tracer(ABC):
    """Interface for recording workflow execution events."""

    @abstractmethod
    def record(self, event: dict) -> None:
        """Persist a trace event."""


class Exporter(ABC):
    """Interface for serializing workflows."""

    @abstractmethod
    def export(self, workflow: "Workflow", path: str) -> None:
        """Export *workflow* to *path* in a specific format."""
