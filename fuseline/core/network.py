import inspect
import json
import zlib
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

import numpy
from colorama import Fore, Style
from networkx import MultiDiGraph
from tabulate import tabulate

from fuseline.core.abc import EngineAPI, NetworkAPI, NetworkPlotAPI
from fuseline.core.engines import SerialEngine
from fuseline.core.nodes import (
    DataNode,
    GearInput,
    GearInputOutput,
    GearNode,
    GearOutput,
    NetworkNode,
    OutputNode,
)
from fuseline.typing import T
from fuseline.utils.logging import get_logger

# Get the logger
logger = get_logger()


class WorkflowNotFoundError(Exception):
    """Workflow not found exception."""

    pass


class Depends(Generic[T]):
    """Express input dependency."""

    def __init__(self, func: Callable[..., Any]) -> None:
        """Constructor for dependency edge."""
        from fuseline.core.nodes import GearNode

        self._func: Callable[..., Any] = func
        self._gear = GearNode(self._func)

    @property
    def gear(self) -> GearNode:
        """Return function dependencies as a gear."""
        return self._gear


class NetworkPropertyMixin(NetworkAPI):
    """Network property mixin."""

    def __init__(self, name: str, version: str, graph: MultiDiGraph) -> None:
        """Network property mixin."""
        self._name = name
        self._version = version

        self._graph = graph

    def __repr__(self) -> str:
        """String representation."""
        return f"{self._name}-{self._version}"

    @property
    def name(self) -> str:
        """Name of the feature."""
        return self._name

    @property
    def version(self) -> str:
        """Version of the feature."""
        return self._version

    @property
    def identifier(self) -> int:
        """Identifier containing name and version."""
        _id: int = zlib.crc32(bytes(f"{self._name}-{self._version}", "utf-8"))
        return _id

    @property
    def graph(self) -> MultiDiGraph:
        """Get computational graph representation."""
        return self._graph

    @property
    def plot(self) -> NetworkPlotAPI:
        """Plot the network."""
        from fuseline.core.plot import NetworkPlot

        return NetworkPlot(self._graph)

    @property
    def roots(self) -> List[GearNode]:
        """Calculate entry points into the network."""

        def check_predecessors(node: NetworkNode) -> bool:
            """Checks predecessors of a node."""
            if not isinstance(node, GearNode):
                return False

            all_inputs = [True if isinstance(p, GearInput) else False for p in self._graph.predecessors(node)]  # type: ignore

            return all(all_inputs) or not all_inputs

        roots: List[GearNode] = [
            node
            for node in self._graph.nodes  # type: ignore
            if check_predecessors(node)  # type: ignore
        ]

        return roots

    @property
    def input_shape(self) -> Dict[str, Type[Any]]:
        """Returns input shape of the computational graph."""
        inputs: Dict[str, Type[Any]] = {
            node.name: node.annotation for node in self._graph.nodes if isinstance(node, GearInput)
        }  # type: ignore

        return inputs

    @property
    def inputs(self) -> List[GearInput]:
        """Return all inputs with values of a graph."""
        inputs: List[GearInput] = [node for node in self._graph.nodes if isinstance(node, GearInput)]  # type: ignore

        return inputs

    @property
    def outputs(self) -> List[OutputNode]:
        """Return all outputs of a graph."""
        outputs: List[OutputNode] = [
            node for node in self._graph.nodes if isinstance(node, GearInputOutput) or isinstance(node, GearOutput)
        ]  # type: ignore

        return outputs

    def print_outputs(self, tabular: bool = True, colored: bool = True, as_json: bool = False) -> Union[str, None]:
        """
        Print or return a formatted representation of the graph outputs.

        Args:
        tabular (bool): If True, format output as a table (ignored if as_json is True).
        colored (bool): If True, use colors in the output (ignored if as_json is True).
        as_json (bool): If True, return the result as a JSON string.

        Returns:
        Union[str, None]: JSON string if as_json is True, None otherwise (prints to console).
        """
        outputs = self.outputs

        if as_json:
            json_data = {
                "outputs": [
                    {
                        "type": type(node).__name__,
                        "name": node.name,
                        "value": str(node.value),  # Convert to string to ensure JSON serialization
                        "annotation": str(node.annotation),
                        "is_empty": node.is_empty,
                    }
                    for node in outputs
                ]
            }
            return json.dumps(json_data, indent=2)

        table_data = []
        for node in outputs:
            node_type = type(node).__name__
            if colored:
                color = Fore.GREEN if isinstance(node, GearOutput) else Fore.YELLOW
                status = f"{color}{node_type}{Style.RESET_ALL}"
            else:
                status = node_type

            is_empty = "Yes" if node.is_empty else "No"

            table_data.append(
                [
                    status,
                    str(node.annotation),
                    is_empty,
                    node.name,
                    str(node.value),
                ]
            )

        if tabular:
            headers = [
                "Name",
                "Type",
                "Is Empty",
                "Name",
                "Output",
            ]
            table = tabulate(table_data, headers=headers, tablefmt="grid")
            output = f"{table}"
        else:
            output = "\n\n"
            for row in table_data:
                output += f"Node: {row[0]}, Type: {row[1]}, Is Empty: {row[2]}, Name: {row[3]}, Output: {row[4]}\n"

        return output


class Network(NetworkPropertyMixin):
    """Representation of a DAG which contains all processing data."""

    def __init__(
        self,
        name: str,
        outputs: Optional[List[Callable[..., numpy.ndarray]]] = None,
        version: str = "0.1.0",
        engine: Optional[EngineAPI] = None,
    ) -> None:
        """Network constructor."""
        logger.info(f"Initializing Network: {name} (version: {version})")
        self._outputting_nodes = outputs or []
        self._graph: MultiDiGraph = MultiDiGraph(name=name)

        self._last_results: List[Tuple[str, str]]

        for output in self._outputting_nodes:
            gear = GearNode(output, graph=self._graph)
            self._attach_output(gear, graph_output=True)
            self._add_gear(gear)

        if engine is None:
            self._engine = SerialEngine()

        super().__init__(name, version, self._graph)

    def _attach_input(self, param: inspect.Parameter, dst: GearNode) -> None:
        """Attach input to the gear."""
        value = param.default if param.default != param.empty else None
        annotation = param.annotation if param.annotation != param.empty else Any

        gear_input = GearInput(param.name, value, annotation, graph=self._graph)
        self._graph.add_edge(gear_input, dst)  # type: ignore

    def _attach_output(self, src_gear: GearNode, name: Optional[str] = None, graph_output: bool = False) -> OutputNode:
        """Attach output to the gear."""
        if not name:
            name = f"{src_gear!s}"

        src_gear_output: OutputNode
        if graph_output:
            src_gear_output = GearOutput(name, None, src_gear.output_type, graph=self._graph)
        else:
            src_gear_output = GearInputOutput(name, None, src_gear.output_type, graph=self._graph)

        self._graph.add_edge(src_gear, src_gear_output)  # type: ignore
        return src_gear_output

    def _add_gear(self, gear: GearNode) -> None:
        """Add gear to the graph."""
        gear.set_graph(self._graph)

        for name, param in gear.params.items():
            if param.default is not inspect.Parameter.empty and isinstance(param.default, Depends):
                src_gear = param.default.gear
                src_gear_output = self._attach_output(src_gear, name=name)
                self._graph.add_edge(src_gear_output, gear)  # type: ignore
                self._add_gear(src_gear)
            else:
                self._attach_input(param, gear)

    def compute_next(self) -> List[GearNode]:
        """Returns next nodes ready for evaluation."""
        logger.debug("Computing next nodes for evaluation")

        next_batch = []

        for compute_node in self.roots:
            curr = compute_node
            while True:
                result_node: DataNode = next(self._graph.successors(curr))
                if result_node.is_empty and curr.is_ready and curr not in next_batch:
                    next_batch.append(curr)

                try:
                    curr = next(self._graph.successors(result_node))
                except StopIteration:
                    break

        return next_batch

    def copy(self, name: Optional[str] = None, version: Optional[str] = None) -> "Network":
        """Create a copy of an `Network` instance."""
        _version = version or self._version
        _name = name or self._name

        return Network(_name, outputs=self._outputting_nodes, version=_version)  # type: ignore

    def _check_input_data(self, input_data: Dict, expected_shape: Dict, as_json: bool = False) -> Optional[str]:
        """
        Check if the input data matches the expected shape.

        Args:
        input_data (dict): The input data to be checked.
        expected_shape (dict): The expected shape of the input data.
        as_json (bool): If True, return the result as a JSON string.

        Returns:
        Optional[str]: JSON string if as_json is True, None otherwise.

        Raises:
        ValueError: If the input data doesn't match the expected shape.
        """
        all_keys = set(expected_shape.keys()) | set(input_data.keys())
        table_data = []

        for key in all_keys:
            if key in expected_shape and key in input_data:
                status = f"{Fore.GREEN}✓{Style.RESET_ALL}"
            elif key in expected_shape:
                status = f"{Fore.RED}Missing{Style.RESET_ALL}"
            else:
                status = f"{Fore.RED}Extra{Style.RESET_ALL}"

            expected_value = expected_shape.get(key, "N/A")
            provided_value = input_data.get(key, "N/A")

            table_data.append([key, expected_value, provided_value, status])

        table = tabulate(
            table_data,
            headers=["Key", "Expected", "Provided", "Status"],
            tablefmt="grid",
        )

        if as_json:
            json_data = {
                "keys": [
                    {
                        "name": row[0],
                        "expected": str(row[1]),
                        "provided": str(row[2]),
                        "status": "correct" if "✓" in row[3] else "incorrect",
                    }
                    for row in table_data
                ]
            }
            return json.dumps(json_data, indent=2)

        if set(input_data.keys()) != set(expected_shape.keys()):
            error_message = f"Input data format is incorrect!\n\n{table}\n\n"
            error_message += (
                "Please ensure that the input data matches the expected format defined in `network.input_shape`."
            )
            raise ValueError(error_message)

        return None

    def set_input(self, input_data: Dict[str, Any]) -> None:
        """Set input data for the graph computation."""
        logger.info(f"Setting input data: {input_data}")
        self._check_input_data(input_data, self.input_shape)

        inputs: List[GearInput] = [
            node
            for node in self._graph.nodes
            if isinstance(node, GearInput)
        ]

        for var_name, var_value in input_data.items():
            for node in inputs:
                if node.name == var_name:
                    node.set_value(var_value)

    @property
    def results(self) -> List[GearOutput]:
        """Return results of the feature data flow."""
        _results: List[GearOutput] = [
            output_node
            for output_node in self.outputs
            if isinstance(output_node, GearOutput) and self.name in str(output_node)
        ]

        return _results

    def run(self, **kwargs: Any) -> NetworkAPI:
        """Compute all data nodes of the network."""
        logger.info(f"Running network with kwargs: {kwargs}")
        if self._engine is None:
            raise ValueError("engine not running")

        if not self._engine.is_ready():
            self._engine.setup()

        network_run = self._engine.execute(self.copy(), **kwargs)
        logger.info("Network execution completed")
        return network_run
