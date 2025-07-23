from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from .base import FailureAction, FailureDecision, StepPolicy

if TYPE_CHECKING:  # pragma: no cover - for type hints
    from ..core import Step


class RetryPolicy(StepPolicy):
    """Simple retry policy replicating ``Task`` behaviour."""

    name = "retry"

    def __init__(self, max_retries: int = 1, wait: float = 0.0) -> None:
        self.max_retries = max_retries
        self.wait = wait

    def to_config(self) -> Dict[str, Any]:
        return {"max_retries": self.max_retries, "wait": self.wait}

    def on_failure(self, step: "Step", exc: Exception, attempt: int) -> FailureDecision:
        if attempt < self.max_retries - 1:
            return FailureDecision(FailureAction.RETRY, self.wait)
        return FailureDecision(FailureAction.FAIL)
