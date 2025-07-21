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
from typing import TYPE_CHECKING, Any, Callable, Dict, Type, Awaitable

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from ..workflow import Step, StepSchema, Workflow, WorkflowSchema


# registry for serializable policies
_POLICY_REGISTRY: Dict[str, Type["Policy"]] = {}


class Policy(abc.ABC):
    """Base class for all policies.

    Policies are instantiated on the driver process when a workflow is
    defined.  They are executed in the worker process once the workflow is
    dispatched.  To support this separation policies may override the
    :py:meth:`attach_to_step` and :py:meth:`attach_to_workflow` hooks which are
    invoked when the policy is associated with a :class:`~fuseline.workflow.Step`
    or :class:`~fuseline.workflow.Workflow`.
    """

    name = "policy"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "name"):
            _POLICY_REGISTRY[cls.name] = cls

    def to_config(self) -> Dict[str, Any]:
        """Return a serialisable representation used in ``WorkflowSchema``."""
        return {}

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "Policy":
        return cls(**cfg)  # type: ignore[arg-type]

    # lifecycle -----------------------------------------------------------
    def attach_to_step(self, step: "Step") -> None:  # pragma: no cover - default
        """Called when the policy is added to a step."""
        pass

    def attach_to_workflow(self, wf: "Workflow") -> None:  # pragma: no cover - default
        """Called when the policy is added to a workflow."""
        pass


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

    def attach_to_step(self, step: "Step") -> None:  # pragma: no cover - default
        pass

    def execute(self, step: "Step", call: Callable[[], Any]) -> Any:
        """Run ``call`` applying this policy."""
        return call()

    async def execute_async(
        self, step: "Step", call: Callable[[], Awaitable[Any]]
    ) -> Any:
        """Run ``call`` in an asynchronous context."""
        return await call()

    def on_start(self, step: "Step") -> None:
        pass

    def on_success(self, step: "Step", result: Any) -> None:
        pass

    def on_failure(self, step: "Step", exc: Exception, attempt: int) -> FailureDecision | None:
        return None


class WorkflowPolicy(Policy):
    """Policy applied to workflow execution."""

    def attach_to_workflow(self, wf: "Workflow") -> None:  # pragma: no cover - default
        pass

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


