from .base import ExecutionEngine

__all__ = ["ExecutionEngine", "PoolEngine", "ProcessEngine"]


def __getattr__(name: str):
    if name == "PoolEngine":
        from .pool import PoolEngine as _PoolEngine
        return _PoolEngine
    if name == "ProcessEngine":
        from .process import ProcessEngine as _ProcessEngine
        return _ProcessEngine
    raise AttributeError(name)
