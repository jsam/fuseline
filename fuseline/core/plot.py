from typing import Any, Dict

import networkx

from fuseline.core.abc import NetworkPlotAPI
from fuseline.core.nodes import NetworkNode


class NetworkPlot(NetworkPlotAPI):
    """Network plotting utility."""

    def __init__(self, graph: networkx.DiGraph) -> None:
        """Network plot constructor."""
        import pydot  # type: ignore

        self._graph: networkx.DiGraph = graph

        g = pydot.Dot(graph_type="digraph", rank="same")

        nx_node: NetworkNode
        for nx_node in self._graph.nodes:  # type: ignore
            node = pydot.Node(name=nx_node.name_unique, label=str(nx_node))
            g.add_node(node)  # type: ignore

        src: NetworkNode
        dst: NetworkNode
        for src, dst, _ in self._graph.edges(data=True):  # type: ignore
            edge = pydot.Edge(src=src.name_unique, dst=dst.name_unique)
            g.add_edge(edge)  # type: ignore

        self._pydot_graph = g
        self._meta: Dict[str, Any] = g.obj_dict  # type: ignore

    @property
    def meta(self) -> Dict[str, Any]:
        """Return metadata of network plot."""
        return self._meta

    # @property
    # def show(self) -> None:
    #     """Render pydot for viewing in Jupyter notebook."""
    #     from IPython.display import Image, display
    #     _png: bytes = self._pydot_graph.create_png()  # type: ignore
    #     display(Image(_png))

    def to_file(self, filename: str) -> None:
        """Write plot to a file."""
        if filename is None:
            raise ValueError("No filename provided.")

        self._pydot_graph.write_png(filename)  # type: ignore
