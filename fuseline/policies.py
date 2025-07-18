# -*- coding: utf-8 -*-
"""Policy interfaces for workflow behaviour.

These abstractions allow steps and workflows to customise execution
semantics without hardcoding logic in the core classes.  Individual
policies implement hooks which are invoked by :class:`Step` and
:class:`Workflow` during execution.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Type

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from .workflow import Step, StepSchema, Workflow, WorkflowSchema


# registry for serializable policies
_POLICY_REGISTRY: Dict[str, Type["Policy"]] = {}


class Policy(abc.ABC):
    """Base class for all policies."""

    name = "policy"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "name"):
            _POLICY_REGISTRY[cls.name] = cls

    def to_config(self) -> Dict[str, Any]:
        """Return a serialisable representation."""
        return {}

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "Policy":
        return cls(**cfg)  # type: ignore[arg-type]


class FailureAction(str, Enum):
    """Decision returned when a step fails."""

    RETRY = "retry"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class FailureDecision:
    """Outcome from :meth:`StepPolicy.on_failure`."""

    action: FailureAction
    delay: float = 0.0


class StepPolicy(Policy):
    """Policy applied to individual steps."""

    def on_start(self, step: "Step") -> None:
        pass

    def on_success(self, step: "Step", result: Any) -> None:
        pass

    def on_failure(self, step: "Step", exc: Exception, attempt: int) -> FailureDecision | None:
        return None


class WorkflowPolicy(Policy):
    """Policy applied to workflow execution."""

    def on_workflow_start(self, wf: "Workflow") -> None:  # pragma: no cover - default no-op
        pass

    def on_workflow_finished(self, wf: "Workflow", result: Any) -> None:  # pragma: no cover - default no-op
        pass

    def on_step_start(self, wf: "Workflow", step: "Step") -> None:  # pragma: no cover - default no-op
        pass

    def on_step_success(self, wf: "Workflow", step: "Step", result: Any) -> None:  # pragma: no cover - default no-op
        pass

    def on_step_failure(self, wf: "Workflow", step: "Step", exc: Exception) -> None:  # pragma: no cover - default no-op
        pass


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


class StepTimeoutPolicy(StepPolicy):
    """Specify the processing timeout for a step."""

    name = "timeout"

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds

    def to_config(self) -> Dict[str, Any]:
        return {"seconds": self.seconds}


class WorkerPolicy(Policy):
    """Policy consulted by the broker when assigning work to a worker."""

    def step_timeout(
        self, wf: "WorkflowSchema", step: "StepSchema"
    ) -> float | None:  # pragma: no cover - default no-op
        return None


class StepTimeoutWorkerPolicy(WorkerPolicy):
    """Read :class:`StepTimeoutPolicy` from the step definition."""

    name = "worker_timeout"

    def __init__(self, default: float = 60.0) -> None:
        self.default = default

    def step_timeout(
        self, wf: "WorkflowSchema", step: "StepSchema"
    ) -> float | None:
        for pol in step.policies:
            if pol.get("name") == StepTimeoutPolicy.name:
                cfg = pol.get("config", {})
                return float(cfg.get("seconds", self.default))
        return self.default


__all__ = [
    "_POLICY_REGISTRY",
    "FailureAction",
    "FailureDecision",
    "Policy",
    "RetryPolicy",
    "StepPolicy",
    "StepTimeoutPolicy",
    "StepTimeoutWorkerPolicy",
    "WorkerPolicy",
    "WorkflowPolicy",
]
