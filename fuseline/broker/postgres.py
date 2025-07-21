from __future__ import annotations

from .storage import PostgresRuntimeStorage
from .memory import MemoryBroker


class PostgresBroker(MemoryBroker):
    """Broker backed by :class:`PostgresRuntimeStorage`."""

    def __init__(self, dsn: str | None = None, *, worker_ttl: float = 30.0) -> None:
        store = PostgresRuntimeStorage(dsn)
        super().__init__(worker_ttl=worker_ttl)
        self._store = store
