from __future__ import annotations

from .base import Exporter
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..workflow import Workflow, WorkflowSchema


class YamlExporter(Exporter):
    """Serialize workflows to a simple YAML format."""

    def export(self, workflow: "Workflow | WorkflowSchema", path: str) -> None:
        """Serialize *workflow* or schema to YAML and write it to *path*."""

        schema = workflow.to_schema() if hasattr(workflow, "to_schema") else workflow
        with open(path, "w", encoding="utf-8") as f:
            f.write(schema.to_yaml())
