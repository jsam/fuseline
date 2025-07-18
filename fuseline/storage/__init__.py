from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict, deque
import json
from typing import TYPE_CHECKING, Any, Iterable, Optional

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from ..workflow import Status


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
    def assign_step(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        worker_id: str,
        expires_at: float,
    ) -> None:
        """Record that *worker_id* is processing *step_name*."""

    @abstractmethod
    def clear_assignment(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> None:
        """Remove assignment for *step_name*."""

    @abstractmethod
    def get_assignment(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> tuple[str, float] | None:
        """Return ``(worker_id, expires_at)`` for assigned *step_name*."""

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
    def set_inputs(
        self,
        workflow_id: str,
        instance_id: str,
        inputs: dict[str, Any],
    ) -> None:
        """Persist workflow input parameters."""

    @abstractmethod
    def get_inputs(self, workflow_id: str, instance_id: str) -> dict[str, Any]:
        """Return stored workflow parameters."""

    @abstractmethod
    def set_result(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        result: Any,
    ) -> None:
        """Persist a step result for dependency lookups."""

    @abstractmethod
    def get_result(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
    ) -> Any | None:
        """Return the stored result for *step_name* if any."""

    @abstractmethod
    def finalize_run(self, workflow_id: str, instance_id: str) -> None:
        """Mark the run as finished."""


class MemoryRuntimeStorage(RuntimeStorage):
    """In-memory storage used for testing and examples."""

    def __init__(self) -> None:
        self._queues: dict[tuple[str, str], deque[str]] = defaultdict(deque)
        self._queued: dict[tuple[str, str], set[str]] = defaultdict(set)
        self._states: dict[tuple[str, str, str], "Status"] = {}
        self._results: dict[tuple[str, str, str], Any] = {}
        self._inputs: dict[tuple[str, str], dict[str, Any]] = {}
        self._finished: set[tuple[str, str]] = set()
        self._assignments: dict[tuple[str, str, str], tuple[str, float]] = {}

    def create_run(
        self, workflow_id: str, instance_id: str, steps: Iterable[str]
    ) -> None:
        from ..workflow import Status

        for step in steps:
            self._states[(workflow_id, instance_id, step)] = Status.PENDING
        key = (workflow_id, instance_id)
        self._queues[key].clear()
        self._queued[key].clear()
        self._assignments = {k: v for k, v in self._assignments.items() if k[:2] != key}
        self._results = {k: v for k, v in self._results.items() if k[:2] != key}
        self._inputs.pop(key, None)

    def enqueue(self, workflow_id: str, instance_id: str, step_name: str) -> None:
        key = (workflow_id, instance_id)
        if step_name in self._queued[key]:
            return
        self._queues[key].append(step_name)
        self._queued[key].add(step_name)

    def fetch_next(self, workflow_id: str, instance_id: str) -> Optional[str]:
        q = self._queues.get((workflow_id, instance_id))
        if not q:
            return None
        step = q.popleft()
        self._queued[(workflow_id, instance_id)].discard(step)
        return step

    def assign_step(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        worker_id: str,
        expires_at: float,
    ) -> None:
        self._assignments[(workflow_id, instance_id, step_name)] = (
            worker_id,
            expires_at,
        )

    def clear_assignment(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> None:
        self._assignments.pop((workflow_id, instance_id, step_name), None)

    def get_assignment(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> tuple[str, float] | None:
        return self._assignments.get((workflow_id, instance_id, step_name))

    def set_state(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        state: "Status",
    ) -> None:
        self._states[(workflow_id, instance_id, step_name)] = state

    def get_state(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> "Status | None":
        return self._states.get((workflow_id, instance_id, step_name))

    def finalize_run(self, workflow_id: str, instance_id: str) -> None:
        self._finished.add((workflow_id, instance_id))
        self._assignments = {
            k: v
            for k, v in self._assignments.items()
            if k[:2] != (workflow_id, instance_id)
        }

    # RuntimeStorage extras
    def set_inputs(
        self,
        workflow_id: str,
        instance_id: str,
        inputs: dict[str, Any],
    ) -> None:
        self._inputs[(workflow_id, instance_id)] = inputs

    def get_inputs(self, workflow_id: str, instance_id: str) -> dict[str, Any]:
        return self._inputs.get((workflow_id, instance_id), {})

    def set_result(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        result: Any,
    ) -> None:
        self._results[(workflow_id, instance_id, step_name)] = result

    def get_result(
        self, workflow_id: str, instance_id: str, step_name: str
    ) -> Any | None:
        return self._results.get((workflow_id, instance_id, step_name))


class PostgresRuntimeStorage(RuntimeStorage):
    """Store runtime state in a PostgreSQL database with migrations."""

    LATEST_VERSION = 1

    MIGRATIONS: dict[int, list[str]] = {
        1: [
            """
            CREATE TABLE IF NOT EXISTS steps (
                workflow_id TEXT,
                instance_id TEXT,
                step_name TEXT,
                state TEXT,
                result JSONB,
                worker_id TEXT,
                expires_at DOUBLE PRECISION,
                PRIMARY KEY (workflow_id, instance_id, step_name)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS queue (
                workflow_id TEXT,
                instance_id TEXT,
                step_name TEXT,
                PRIMARY KEY (workflow_id, instance_id, step_name)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS inputs (
                workflow_id TEXT,
                instance_id TEXT,
                payload JSONB,
                PRIMARY KEY (workflow_id, instance_id)
            );
            """,
        ]
    }

    def __init__(self, dsn: str | None = None) -> None:
        import os

        self.dsn = dsn or os.environ.get("DATABASE_URL", "postgresql://localhost/fuseline")
        self._connect()
        self._migrate()

    def _connect(self) -> None:
        try:
            import psycopg
        except Exception:  # pragma: no cover - optional dep
            raise RuntimeError("psycopg package required for PostgresRuntimeStorage")
        self._conn = psycopg.connect(self.dsn, autocommit=True)

    def _get_version(self) -> int:
        with self._conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS fuseline_meta (key TEXT PRIMARY KEY, value TEXT)"
            )
            cur.execute("SELECT value FROM fuseline_meta WHERE key='version'")
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def _set_version(self, version: int) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO fuseline_meta (key, value) VALUES ('version', %s)"
                " ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
                (str(version),),
            )

    def _migrate(self) -> None:
        version = self._get_version()
        for v in range(version + 1, self.LATEST_VERSION + 1):
            stmts = self.MIGRATIONS.get(v, [])
            for stmt in stmts:
                with self._conn.cursor() as cur:
                    cur.execute(stmt)
            self._set_version(v)

    # ------------------------------------------------------------------
    def create_run(self, workflow_id: str, instance_id: str, steps: Iterable[str]) -> None:
        from ..workflow import Status

        with self._conn.cursor() as cur:
            for step in steps:
                cur.execute(
                    "INSERT INTO steps (workflow_id, instance_id, step_name, state)"
                    " VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (workflow_id, instance_id, step, Status.PENDING.value),
                )

    def enqueue(self, workflow_id: str, instance_id: str, step_name: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO queue (workflow_id, instance_id, step_name)"
                " VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (workflow_id, instance_id, step_name),
            )

    def fetch_next(self, workflow_id: str, instance_id: str) -> Optional[str]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT step_name FROM queue WHERE workflow_id=%s AND instance_id=%s LIMIT 1",
                (workflow_id, instance_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            step_name = row[0]
            cur.execute(
                "DELETE FROM queue WHERE workflow_id=%s AND instance_id=%s AND step_name=%s",
                (workflow_id, instance_id, step_name),
            )
            return step_name

    def assign_step(
        self,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        worker_id: str,
        expires_at: float,
    ) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE steps SET worker_id=%s, expires_at=%s WHERE workflow_id=%s AND instance_id=%s AND step_name=%s",
                (worker_id, expires_at, workflow_id, instance_id, step_name),
            )

    def clear_assignment(self, workflow_id: str, instance_id: str, step_name: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE steps SET worker_id=NULL, expires_at=NULL WHERE workflow_id=%s AND instance_id=%s AND step_name=%s",
                (workflow_id, instance_id, step_name),
            )

    def get_assignment(self, workflow_id: str, instance_id: str, step_name: str) -> tuple[str, float] | None:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT worker_id, expires_at FROM steps WHERE workflow_id=%s AND instance_id=%s AND step_name=%s",
                (workflow_id, instance_id, step_name),
            )
            row = cur.fetchone()
            return (row[0], row[1]) if row else None

    def set_state(self, workflow_id: str, instance_id: str, step_name: str, state: "Status") -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE steps SET state=%s WHERE workflow_id=%s AND instance_id=%s AND step_name=%s",
                (state.value, workflow_id, instance_id, step_name),
            )

    def get_state(self, workflow_id: str, instance_id: str, step_name: str) -> "Status | None":
        from ..workflow import Status

        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT state FROM steps WHERE workflow_id=%s AND instance_id=%s AND step_name=%s",
                (workflow_id, instance_id, step_name),
            )
            row = cur.fetchone()
            return Status(row[0]) if row else None

    def finalize_run(self, workflow_id: str, instance_id: str) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "DELETE FROM queue WHERE workflow_id=%s AND instance_id=%s",
                (workflow_id, instance_id),
            )

    # extras -------------------------------------------------------------
    def set_inputs(self, workflow_id: str, instance_id: str, inputs: dict[str, Any]) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO inputs (workflow_id, instance_id, payload) VALUES (%s, %s, %s)"
                " ON CONFLICT (workflow_id, instance_id) DO UPDATE SET payload=EXCLUDED.payload",
                (workflow_id, instance_id, json.dumps(inputs)),
            )

    def get_inputs(self, workflow_id: str, instance_id: str) -> dict[str, Any]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM inputs WHERE workflow_id=%s AND instance_id=%s",
                (workflow_id, instance_id),
            )
            row = cur.fetchone()
            return row[0] if row else {}

    def set_result(self, workflow_id: str, instance_id: str, step_name: str, result: Any) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE steps SET result=%s WHERE workflow_id=%s AND instance_id=%s AND step_name=%s",
                (json.dumps(result), workflow_id, instance_id, step_name),
            )

    def get_result(self, workflow_id: str, instance_id: str, step_name: str) -> Any | None:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT result FROM steps WHERE workflow_id=%s AND instance_id=%s AND step_name=%s",
                (workflow_id, instance_id, step_name),
            )
            row = cur.fetchone()
            return row[0] if row else None
