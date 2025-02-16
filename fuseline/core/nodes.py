import inspect
from typing import Any, Callable, Dict, List, Optional, Union

from networkx.classes.multidigraph import MultiDiGraph
from typeguard import TypeCheckError, check_type

from fuseline.utils.logging import get_logger

# Get the logger
logger = get_logger()


class NodeRaisedError(Exception):
    """Gear exception."""

    def __init__(self, gear: "GearNode", params: Dict[str, Any], raised: BaseException) -> None:
        """ "Gear exception constructor."""
        self.gear = gear
        self.params = params
        self.raised_exception = raised

        super().__init__(self.raised_exception)
        logger.error(f"NodeRaisedError: {self.raised_exception}")


class InvalidGraphError(Exception):
    """Invalid graph structure found."""

    def __init__(self, msg: str, **kwargs: Any) -> None:
        """ "Gear exception constructor."""
        self.msg = msg
        self.params: Dict[str, Any] = kwargs

        super().__init__(msg)
        logger.error(f"InvalidGraphError: {self.msg}")


class GraphAssociationMixin:
    """Graph association mixin."""

    def __init__(self, graph: Optional[MultiDiGraph] = None) -> None:
        """GraphAssociationMixin constructor."""
        self._graph = graph

    @property
    def graph(self) -> Optional[MultiDiGraph]:
        """Return associated graph."""
        return self._graph

    def set_graph(self, graph: Optional[MultiDiGraph]) -> None:
        """Associate/Disassociate graph with/from a node."""
        self._graph = graph
        logger.debug(f"Graph set for {self.__class__.__name__}")


class Signature(GraphAssociationMixin):
    """Analyze function signature."""

    def __init__(self, func: Callable[..., Any], graph: Optional[MultiDiGraph] = None) -> None:
        """Signature constructor."""
        self._func = func
        self._name = func.__name__
        self._signature = inspect.signature(func)
        self._params = dict(self._signature.parameters)
        self._return_type = self._signature.return_annotation

        super().__init__(graph=graph)
        logger.debug(f"Signature created for function: {self._name}")

    @property
    def name(self) -> str:
        """Returns the name of the wrapped object."""
        return self._name

    @property
    def output_type(self) -> Any:
        """Get output type."""
        return self._return_type

    @property
    def params(self) -> Dict[str, inspect.Parameter]:
        """Get all function input parameters."""
        return self._params


class GearNode(Signature):
    """Node representing data transformation."""

    shape = "circle"

    def __init__(self, func: Callable[..., Any], graph: Optional[MultiDiGraph] = None) -> None:
        """Gear constructor."""
        super().__init__(func, graph=graph)
        logger.debug(f"GearNode created: {self.name}")

        self.has_run = False

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        """Execute the given callable with in going nodes as parameters."""
        params = self.input_values
        logger.debug(f"Executing GearNode: {self.name} with params: {params}")

        try:
            result = self._func(**params)
            logger.debug(f"GearNode {self.name} execution completed")
            self.has_run = True
            return result
        except BaseException as e:
            logger.error(f"Error in GearNode {self.name}: {e!s}")
            raise NodeRaisedError(self, params, e)

    def __repr__(self) -> str:
        """String representation of a gear."""
        return self.name

    @property
    def name_unique(self) -> str:
        return f"gear_{self._name}"

    @property
    def input_values(self) -> Dict[str, Any]:
        """Input values for the gear computation."""
        if self._graph is None:
            logger.error(f"No graph associated with GearNode: {self.name}")
            raise ValueError("no graph associated")

        params: Dict[str, Any] = {p.name: p.value for p in self._graph.predecessors(self)}  # type: ignore
        return params

    @property
    def is_ready(self) -> bool:
        """Check if node can run and has not been runned already."""
        if self.has_run is True:
            return False

        return all([
            not(p.is_empty)
            for p in self._graph.predecessors(self)
        ])


class DataNode(GraphAssociationMixin):
    """Node representing data."""

    def __init__(
        self,
        name: str,
        value: Optional[Any],
        annotation: type,
        graph: Optional[MultiDiGraph] = None,
    ):
        """Data node constructor."""
        self._name: str = name
        self._value: Optional[Any] = value
        self._annotation: type = annotation

        super().__init__(graph=graph)
        logger.debug(f"DataNode created: {self._name}")

    def __repr__(self) -> str:
        """String representation."""
        if self._graph is None:
            return self._name

        suffix = ")"

        annotation: str = str(self._annotation)

        if hasattr(self._annotation, "__name__"):
            annotation = self._annotation.__name__  # type: ignore

        successors: List[NetworkNode] = list(self._graph.successors(self))  # type: ignore

        # NOTE: Successor of a DataNode is GearNode or network output.
        if not successors:
            child_out: str = self._graph.name  # type: ignore
        else:
            child = successors[0]
            child_out = child.name
            if isinstance(child, GearNode) and len(child.params) > 1:
                suffix = ", ...)"

        return f"{child_out}({self._name}[{annotation}] = {self._value}{suffix}"

    @property
    def name(self) -> str:
        """Node name."""
        return self._name  # f"data_{self._name}"

    @property
    def name_unique(self) -> str:
        """Ensure and return unique name."""
        return str(self)

    @property
    def value(self) -> Any:
        """Returns wrapped data."""
        return self._value

    @property
    def annotation(self) -> type:
        """Node annotation."""
        return self._annotation

    @property
    def is_empty(self) -> bool:
        """Check if the data node is empty."""
        return self._value is None

    def set_value(self, value: Any) -> None:
        """Sets node value."""
        logger.debug(f"Setting value for DataNode: {self.name}")
        try:
            if self._annotation is not inspect._empty:
                check_type(value, self._annotation)
        except TypeCheckError as e:
            logger.error(f"Invalid type for DataNode {self.name}: {e!s}")
            raise TypeError(f"`{self.name}` received invalid type - {e}")

        self._value = value
        logger.debug(f"Value set for DataNode: {self.name}")


class GearInput(DataNode):
    """Input to the gear."""

    shape = "invhouse"


class GearOutput(DataNode):
    """Output of a gear without additional depedency."""

    shape = "house"


class GearInputOutput(DataNode):
    """Gear input and output node."""

    shape = "note"


NetworkNode = Union[GearNode, DataNode]
OutputNode = Union[GearOutput, GearInputOutput]
