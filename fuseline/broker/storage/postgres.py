from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any, ClassVar, Iterable, Optional

from .base import RuntimeStorage

if TYPE_CHECKING:  # pragma: no cover - for type hints
    from ...workflow import Status


class PostgresRuntimeStorage(RuntimeStorage):
    """Store runtime state in a PostgreSQL database with migrations."""

    LATEST_VERSION: ClassVar[int] = 1

    MIGRATIONS: ClassVar[dict[int, list[str]]] = {
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
            cur.execute("CREATE TABLE IF NOT EXISTS fuseline_meta (key TEXT PRIMARY KEY, value TEXT)")
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
        from ...workflow import Status

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
                "INSERT INTO queue (workflow_id, instance_id, step_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
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
                (
                    "UPDATE steps SET worker_id=NULL, expires_at=NULL "
                    "WHERE workflow_id=%s AND instance_id=%s AND step_name=%s"
                ),
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
        from ...workflow import Status

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
