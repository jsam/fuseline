from __future__ import annotations

from typing import Any, Dict

from .interfaces import Exporter
from .workflow import Task, Workflow


class YamlExporter(Exporter):
    """Serialize workflows to a simple YAML format."""

    def export(self, workflow: Workflow, path: str) -> None:
        steps = workflow._collect_steps()
        name_map = {step: f"step{idx}" for idx, step in enumerate(steps)}

        data: Dict[str, Any] = {"steps": {}, "outputs": [name_map[o] for o in workflow.outputs]}
        for step in steps:
            succ = step.successors
            if len(succ) == 1 and "default" in succ:
                succ_data: Any = [name_map[t] for t in succ.get("default", [])]
            else:
                succ_data = {act: [name_map[t] for t in tgts] for act, tgts in succ.items()}

            entry = {
                "class": type(step).__name__,
                "successors": succ_data,
                "execution_group": step.execution_group,
            }
            if isinstance(step, Task) and step.deps:
                deps_data = {}
                for name, dep in step.deps.items():
                    dep_entry: Dict[str, Any] = {"step": name_map[dep]}
                    cond = step.dep_conditions.get(name)
                    if cond is not None:
                        cond_name = getattr(cond, "__name__", cond.__class__.__name__)
                        cond_info: Dict[str, Any] = {"type": cond_name}
                        cond_params = getattr(cond, "__dict__", None)
                        if cond_params:
                            cond_info["params"] = cond_params
                        dep_entry["condition"] = cond_info
                    deps_data[name] = dep_entry
                entry["dependencies"] = deps_data
            data["steps"][name_map[step]] = entry

        def _dump_yaml(obj: Any, indent: int = 0) -> str:
            pad = "  " * indent
            if isinstance(obj, dict):
                lines = []
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        lines.append(f"{pad}{k}:")
                        lines.append(_dump_yaml(v, indent + 1))
                    else:
                        lines.append(f"{pad}{k}: {v}")
                return "\n".join(lines)
            if isinstance(obj, list):
                lines = []
                for item in obj:
                    if isinstance(item, (dict, list)):
                        lines.append(f"{pad}-")
                        lines.append(_dump_yaml(item, indent + 1))
                    else:
                        lines.append(f"{pad}- {item}")
                return "\n".join(lines)
            return f"{pad}{obj}"

        with open(path, "w", encoding="utf-8") as f:
            f.write(_dump_yaml(data))
