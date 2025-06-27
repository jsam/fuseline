class MultiDiGraph:
    def __init__(self, name=None):
        self.name = name
        self._succ = {}
        self._pred = {}
        self.nodes = []

    def add_edge(self, u, v):
        if u not in self.nodes:
            self.nodes.append(u)
        if v not in self.nodes:
            self.nodes.append(v)
        self._succ.setdefault(u, []).append(v)
        self._pred.setdefault(v, []).append(u)

    def successors(self, node):
        return iter(self._succ.get(node, []))

    def predecessors(self, node):
        return iter(self._pred.get(node, []))
