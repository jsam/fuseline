from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict

from .base import StepPolicy

if TYPE_CHECKING:  # pragma: no cover - for type hints
    from ..core import Step


class StepTimeoutPolicy(StepPolicy):
    """Specify the processing timeout for a step."""

    name = "timeout"

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds

    def to_config(self) -> Dict[str, Any]:
        return {"seconds": self.seconds}

    def execute(self, step: "Step", call: Callable[[], Any]) -> Any:
        from concurrent.futures import ThreadPoolExecutor
        from concurrent.futures import TimeoutError as TimeoutError_

        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(call)
            try:
                return fut.result(timeout=self.seconds)
            except TimeoutError_:
                raise TimeoutError(f"step exceeded {self.seconds}s")

    async def execute_async(self, step: "Step", call: Callable[[], Awaitable[Any]]) -> Any:
        import asyncio

        try:
            return await asyncio.wait_for(call(), timeout=self.seconds)
        except asyncio.TimeoutError as e:
            raise TimeoutError(f"step exceeded {self.seconds}s") from e
