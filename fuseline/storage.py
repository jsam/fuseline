from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Optional, TYPE_CHECKING

try:  # pragma: no cover - optional dependency
    import psycopg
except Exception:  # pragma: no cover - missing optional dep
    psycopg = None

if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from .workflow import Status


class RuntimeStorage(ABC):
    """Interface for persisting workflow runtime state."""

    @abstractmethod
    def create_run(
        self,
        workflow_id: str,
        instance_id: str,
        steps: Iterable[str],
    ) -> None:
        """Initialize storage for a workflow run."""

    @abstractmethod
    def enqueue(self, workflow_id: str, instance_id: str, step_name: str) -> None:
        """Mark *step_name* ready for execution."""

    @abstractmethod
    def fetch_next(self, workflow_id: str, instance_id: str) -> Optional[str]:
        """Return the next ready step or ``None``."""

    @abstractmethod
    def set_state(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        state: "Status",
    ) -> None:
        """Persist the state of *step_name* for this run."""

    @abstractmethod
    def get_state(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
    ) -> "Status | None":
        """Return the stored state for *step_name* if any."""

    @abstractmethod
    def finalize_run(self, workflow_id: str, instance_id: str) -> None:
        """Mark the run as finished."""


class PostgresRuntimeStorage(RuntimeStorage):
    """Store runtime state in a PostgreSQL database."""

    def __init__(self, dsn: str) -> None:
        if psycopg is None:
            raise RuntimeError("psycopg package is required for PostgresRuntimeStorage")
        self.conn = psycopg.connect(dsn)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    workflow_id TEXT,
                    instance_id TEXT,
                    finished BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (workflow_id, instance_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS step_states (
                    workflow_id TEXT,
                    instance_id TEXT,
                    step_name TEXT,
                    state TEXT,
                    PRIMARY KEY (workflow_id, instance_id, step_name)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS step_queue (
                    id BIGSERIAL PRIMARY KEY,
                    workflow_id TEXT,
                    instance_id TEXT,
                    step_name TEXT
                )
                """
            )
        self.conn.commit()

    def create_run(
        self,
        workflow_id: str,
        instance_id: str,
        steps: Iterable[str],
    ) -> None:
        from .workflow import Status

        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO workflow_runs (workflow_id, instance_id) VALUES (%s, %s)",
                (workflow_id, instance_id),
            )
            for step in steps:
                cur.execute(
                    "INSERT INTO step_states (workflow_id, instance_id, step_name, state) VALUES (%s, %s, %s, %s)",
                    (workflow_id, instance_id, step, Status.PENDING.value),
                )
        self.conn.commit()

    def enqueue(self, workflow_id: str, instance_id: str, step_name: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO step_queue (workflow_id, instance_id, step_name) VALUES (%s, %s, %s)",
                (workflow_id, instance_id, step_name),
            )
        self.conn.commit()

    def fetch_next(self, workflow_id: str, instance_id: str) -> Optional[str]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, step_name FROM step_queue WHERE workflow_id=%s AND instance_id=%s ORDER BY id LIMIT 1",
                (workflow_id, instance_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            cur.execute("DELETE FROM step_queue WHERE id=%s", (row[0],))
        self.conn.commit()
        return row[1]

    def set_state(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        state: "Status",
    ) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE step_states SET state=%s WHERE workflow_id=%s AND instance_id=%s AND step_name=%s",
                (state.value, workflow_id, instance_id, step_name),
            )
        self.conn.commit()

    def get_state(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> "Status | None":
        from .workflow import Status

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT state FROM step_states WHERE workflow_id=%s AND instance_id=%s AND step_name=%s",
                (workflow_id, instance_id, step_name),
            )
            row = cur.fetchone()
        return Status(row[0]) if row else None

    def finalize_run(self, workflow_id: str, instance_id: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE workflow_runs SET finished=TRUE WHERE workflow_id=%s AND instance_id=%s",
                (workflow_id, instance_id),
            )
        self.conn.commit()
