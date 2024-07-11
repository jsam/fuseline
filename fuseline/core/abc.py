import abc
from typing import Any, Dict, List, Optional, Type

import networkx

from fuseline.core.nodes import GearInput, GearNode, GearOutput, OutputNode


class NetworkPlotAPI(metaclass=abc.ABCMeta):
    """Network plot actions."""

    @property
    def show(self) -> None:
        """Render pydot for viewing in Jupyter notebook."""
        raise NotImplementedError

    @property
    def meta(self) -> Dict[str, Any]:
        """Return metadata of network plot."""
        raise NotImplementedError

    def to_file(self, filename: str) -> None:
        """Write plot to a file."""
        raise NotImplementedError


class NetworkAPI(metaclass=abc.ABCMeta):
    """Abstract class defining network actions."""

    @property
    def name(self) -> str:
        """Name of the feature."""
        raise NotImplementedError

    @property
    def version(self) -> str:
        """Version of the feature."""
        raise NotImplementedError

    @property
    def identifier(self) -> int:
        """Identifier containing name and version."""
        raise NotImplementedError

    @property
    def graph(self) -> networkx.MultiDiGraph:
        """Get computational graph representation."""
        raise NotImplementedError

    @property
    def plot(self) -> NetworkPlotAPI:
        """Plot the network."""
        raise NotImplementedError

    @property
    def roots(self) -> List[GearNode]:
        """Calculate ranks of gears in a network."""
        raise NotImplementedError

    @property
    def input_shape(self) -> Dict[str, Type[Any]]:
        """Returns input shape of the computational graph."""
        raise NotImplementedError

    @property
    def inputs(self) -> List[GearInput]:
        """Return all inputs with values of a graph."""
        raise NotImplementedError

    @property
    def outputs(self) -> List[OutputNode]:
        """Return all outputs of a graph."""
        raise NotImplementedError

    @property
    def results(self) -> List[GearOutput]:
        """Return results of the feature data flow."""
        raise NotImplementedError

    def compute_next(self) -> List[OutputNode]:
        """Return next in line to compute nodes."""
        raise NotImplementedError

    def copy(self, name: Optional[str] = None, version: Optional[str] = None) -> "NetworkAPI":
        """Copy existing network."""
        raise NotImplementedError

    def set_input(self, input_data: Dict[str, Any]) -> None:
        """Set input data for the graph computation."""
        raise NotImplementedError


class EngineAPI(metaclass=abc.ABCMeta):
    """Executor which contains low level operations for communication with RedisGears."""

    def setup(self) -> None:
        """Prepare the given computation for executor."""
        raise NotImplementedError

    def is_ready(self) -> bool:
        """Check if engine is ready for computation."""
        raise NotImplementedError

    def execute(self, network: NetworkAPI, **kwargs: Any) -> NetworkAPI:
        """Runs the computational network and returns the result object."""
        raise NotImplementedError

    def teardown(self) -> None:
        """Cleanup phase."""
        raise NotImplementedError
