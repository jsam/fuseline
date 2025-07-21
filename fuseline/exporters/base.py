from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for typing only
    from ..workflow import Workflow
    from ..workflow import WorkflowSchema

class Exporter(ABC):
    """Interface for serializing workflows."""

    @abstractmethod
    def export(self, workflow: "Workflow | WorkflowSchema", path: str) -> None:
        """Export *workflow* to *path* in a specific format."""
