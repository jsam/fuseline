import importlib
from pathlib import Path
from typing import Callable, Dict, List, Optional

import toml
from pydantic import BaseModel, ConfigDict, Field

from fuseline.core.abc import NetworkAPI
from fuseline.core.network import Network, WorkflowNotFoundError


def source_execution_node(path: str) -> Callable:
    """Parse source code node path and make Python runnable."""
    module_name, function_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, function_name)


class EngineConfig(BaseModel):
    engine: str
    model_config = ConfigDict(arbitrary_types_allowed=True)


class NetworkConfig(BaseModel):
    name: str
    outputs: List[str]  # Store paths as strings
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def build(self) -> Network:
        return Network(
            self.name,
            outputs=[source_execution_node(output) for output in self.outputs],
        )


class FuselineConfig(BaseModel):
    config: EngineConfig
    workflows: List[NetworkConfig] = Field(default_factory=list)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __getitem__(self, workflow_name: str) -> NetworkAPI:
        for workflow in self.workflows:
            if workflow.name == workflow_name:
                return workflow.build()
        raise WorkflowNotFoundError

    @classmethod
    def model_validate(cls, obj: Dict):
        modified_obj = obj.copy()
        if "workflows" in modified_obj and isinstance(modified_obj["workflows"], dict):
            modified_obj["workflows"] = [
                NetworkConfig(name=wf_name, outputs=outputs) for wf_name, outputs in modified_obj["workflows"].items()
            ]
        return super().model_validate(modified_obj)

    def model_dump(self, *args, **kwargs):
        result = super().model_dump(*args, **kwargs)
        result["workflows"] = {network.name: network.outputs for network in self.workflows}
        return result


def get_fuseline_config() -> Optional[FuselineConfig]:
    """
    Read the pyproject.toml file and return the [tool.fuseline] configuration if present.

    Returns:
        Optional[Dict]: The fuseline configuration if present, None otherwise.
    """
    current_dir = Path.cwd()
    pyproject_path = current_dir / "pyproject.toml"

    if not pyproject_path.is_file():
        print(f"pyproject.toml not found at {pyproject_path}")
        return None

    try:
        pyproject_data = toml.load(pyproject_path)
        if "tool" in pyproject_data and "fuseline" in pyproject_data["tool"]:
            config = pyproject_data["tool"]["fuseline"]
            return FuselineConfig.model_validate(config)
        else:
            print("[tool.fuseline] configuration not found in pyproject.toml")

    except FileNotFoundError:
        print(f"Error: pyproject.toml file not found at {pyproject_path}")
    except PermissionError:
        print(f"Error: Permission denied when trying to read {pyproject_path}")
    except toml.TomlDecodeError as e:
        print(f"Error: Invalid TOML in pyproject.toml: {e}")
    except KeyError as e:
        print(f"Error: Expected key not found in pyproject.toml: {e}")
    except ValueError as e:
        print(f"Error: Incorrect value in pyproject.toml: {e}")
    except IOError as e:
        print(f"Error: IO problem when reading pyproject.toml: {e}")

    return None
