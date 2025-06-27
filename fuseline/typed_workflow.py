from __future__ import annotations

from typing import Any, Callable, List

from .core.network import Network
from .rshift_workflow import NetworkTask, Workflow


class TypedWorkflow(Workflow):
    """Workflow built from typed function outputs."""

    def __init__(self, name: str, outputs: List[Callable[..., Any]], version: str = "0.1.0") -> None:
        network = Network(name, outputs=outputs, version=version)
        self._network_task = NetworkTask(network)
        super().__init__(self._network_task)

    @property
    def network(self) -> Network:
        return self._network_task.network

    def run(self, shared: Any = None, **params: Any) -> Any:
        self._network_task.params = params
        return super().run(shared)

