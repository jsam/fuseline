from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class StepAPI(ABC):
    """Abstract interface for a workflow step."""

    def __init__(self) -> None:
        self.params: Dict[str, Any] = {}
        self.successors: Dict[str, "StepAPI"] = {}

    def set_params(self, params: Dict[str, Any]) -> None:
        self.params = params

    def next(self, node: "StepAPI", action: str = "default") -> "StepAPI":
        self.successors[action] = node
        return node

    @abstractmethod
    def run(self, shared: Any) -> Any:
        """Execute this step."""


class WorkflowAPI(StepAPI):
    """Interface for a workflow composed of steps."""

    @abstractmethod
    def start(self, start: StepAPI) -> StepAPI:
        """Specify the entry step."""



