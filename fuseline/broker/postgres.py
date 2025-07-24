from __future__ import annotations

from .memory import MemoryBroker
from .storage import PostgresRuntimeStorage


class PostgresBroker(MemoryBroker):
    """Broker backed by :class:`PostgresRuntimeStorage`."""

    def __init__(self, dsn: str | None = None, *, worker_ttl: float = 30.0) -> None:
        store = PostgresRuntimeStorage(dsn)
        super().__init__(worker_ttl=worker_ttl)
        self._store = store
