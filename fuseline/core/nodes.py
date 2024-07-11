import inspect
from typing import Any, Callable, Dict, List, Optional, Union

from networkx.classes.multidigraph import MultiDiGraph
from typeguard import check_type, TypeCheckError


class GearException(Exception):
    """Gear exception."""

    def __init__(self, gear: "GearNode", params: Dict[str, Any], raised: BaseException) -> None:
        """"Gear exception constructor."""
        self.gear = gear
        self.params = params
        self.raised_exception = raised

        super().__init__(self.raised_exception)


class InvalidGraph(Exception):
    """Invalid graph structure found."""

    def __init__(self, msg: str, **kwargs: Any) -> None:
        """"Gear exception constructor."""
        self.msg = msg
        self.params: Dict[str, Any] = kwargs

        super().__init__(msg)


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

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        """Execute the given callable with in going nodes as parameters."""
        params = self.input_values

        try:
            result = self._func(**params)
        except BaseException as e:
            raise GearException(self, params, e)

        return result

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
            raise ValueError("no graph associated")

        params: Dict[str, Any] = {p.name: p.value for p in self._graph.predecessors(self)}  # type: ignore

        return params


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
        try:
            check_type(value, self._annotation)
        except TypeCheckError as e:
            raise TypeError(f"`{self.name}` received invalid type - {e}")

        self._value = value


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
