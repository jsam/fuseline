from pathlib import Path
from typing import Dict, Optional, TypedDict, List, Callable
import toml
from pydantic import ConfigDict, BaseModel, Field
from pydantic.dataclasses import dataclass
import importlib
from fuseline.core.network import Network, WorkflowNotFoundException


def source_execution_node(path: str) -> Callable:
    """Parse source code node path and make Python runnable."""
    module_name, function_name = path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, function_name)


class EngineConfig(BaseModel):

    engine: str


class NetworkConfig(BaseModel):

    name: str
    outputs: List[str]  # Store paths as strings

    def build(self) -> Network:
        return Network(self.name, outputs=[source_execution_node(output) for output in self.outputs])

class fuselineConfig(BaseModel):

    config: EngineConfig
    workflows: List[NetworkConfig] = Field(default_factory=list)

    def __getitem__(self, workflow_name: str) -> Network:
        for workflow in self.workflows:
            if workflow.name == workflow_name:
                return workflow.build()
        raise WorkflowNotFoundException

    @classmethod
    def parse_obj(cls, obj: Dict):
        modified_obj = obj.copy()
        if 'workflows' in modified_obj and isinstance(modified_obj['workflows'], dict):
            modified_obj['workflows'] = [
                NetworkConfig(name=wf_name, outputs=outputs)
                for wf_name, outputs in modified_obj['workflows'].items()
            ]
        return super().parse_obj(modified_obj)

    def dict(self, *args, **kwargs):
        result = super().dict(*args, **kwargs)
        result['workflows'] = {
            network.name: network.outputs for network in self.workflows
        }
        return result

    class Config:
        arbitrary_types_allowed = True  # Allow arbitrary types in the model


def get_fuseline_config() -> fuselineConfig:
    """
    Read the pyproject.toml file and return the [tool.fuseline] configuration if present.
    
    Returns:
        Optional[Dict]: The fuseline configuration if present, None otherwise.
    """
    # Get the directory of the current script
    current_dir = Path.cwd()
    # Construct the path to pyproject.toml
    pyproject_path = current_dir / 'pyproject.toml'

    # Check if the file exists
    if not pyproject_path.is_file():
        print(f"pyproject.toml not found at {pyproject_path}")
        return None

    # Read and parse the TOML file
    try:
        pyproject_data = toml.load(pyproject_path)

        # Check if [tool.fuseline] configuration is present
        if 'tool' in pyproject_data and 'fuseline' in pyproject_data['tool']:
            config = pyproject_data['tool']['fuseline']
            return fuselineConfig.parse_obj(config)
        else:
            print("[tool.fuseline] configuration not found in pyproject.toml")
            return None

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
