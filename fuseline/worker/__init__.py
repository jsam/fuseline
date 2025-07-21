from .base import ExecutionEngine

__all__ = [
    "ExecutionEngine",
    "PoolEngine",
    "ProcessEngine",
    "run_from_env",
]


def __getattr__(name: str):
    if name == "PoolEngine":
        from .pool import PoolEngine as _PoolEngine
        return _PoolEngine
    if name == "ProcessEngine":
        from .process import ProcessEngine as _ProcessEngine
        return _ProcessEngine
    if name == "run_from_env":
        from .runner import run_from_env as _run_from_env
        return _run_from_env
    raise AttributeError(name)
