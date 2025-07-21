from __future__ import annotations

from ..storage import PostgresRuntimeStorage
from .memory import MemoryBroker


class PostgresBroker(MemoryBroker):
    """Broker backed by :class:`PostgresRuntimeStorage`."""

    def __init__(self, dsn: str | None = None) -> None:
        store = PostgresRuntimeStorage(dsn)
        super().__init__()
        self._store = store
