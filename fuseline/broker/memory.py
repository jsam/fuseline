from __future__ import annotations

import time
import uuid
from typing import Any, Iterable, Optional

from .storage import MemoryRuntimeStorage
from ..workflow import Status, StepSchema, WorkflowSchema
from .base import (
    Broker,
    StepAssignment,
    StepReport,
    RepositoryInfo,
    LastTask,
    WorkerInfo,
)


class MemoryBroker(Broker):
    """Simple in-memory broker used for tests."""

    def __init__(self, worker_ttl: float = 30.0) -> None:
        self._workers: dict[str, set[tuple[str, str]]] = {}
        self._wf_defs: dict[tuple[str, str], WorkflowSchema] = {}
        self._steps: dict[tuple[str, str], dict[str, StepSchema]] = {}
        self._instances: list[tuple[str, str, str]] = []
        self._instance_version: dict[tuple[str, str], str] = {}
        self._repositories: dict[str, RepositoryInfo] = {}
        self._store = MemoryRuntimeStorage()
        self._wid = 0
        self._last_seen: dict[str, float] = {}
        self._connected_at: dict[str, float] = {}
        self._last_task: dict[str, LastTask] = {}
        self._worker_ttl = worker_ttl

    def _prune_dead(self) -> None:
        now = time.time()
        expired = [wid for wid, ts in self._last_seen.items() if now - ts > self._worker_ttl]
        for wid in expired:
            self._workers.pop(wid, None)
            self._last_seen.pop(wid, None)
            self._connected_at.pop(wid, None)
            self._last_task.pop(wid, None)

    def register_worker(self, workflows: Iterable[WorkflowSchema]) -> str:
        self._prune_dead()
        self._wid += 1
        wid = str(self._wid)
        wf_keys: set[tuple[str, str]] = set()
        for wf in workflows:
            key = (wf.workflow_id, wf.version)
            existing = self._wf_defs.get(key)
            if existing and existing != wf:
                raise ValueError("workflow schema mismatch")
            self._wf_defs.setdefault(key, wf)
            if key not in self._steps:
                self._steps[key] = wf.steps
            wf_keys.add(key)

        now = time.time()
        self._workers[wid] = wf_keys
        self._last_seen[wid] = now
        self._connected_at[wid] = now
        self._last_task.pop(wid, None)
        return wid

    def dispatch_workflow(self, workflow: WorkflowSchema, inputs: Optional[dict[str, Any]] = None) -> str:
        self._prune_dead()
        instance = uuid.uuid4().hex
        key = (workflow.workflow_id, workflow.version)
        if key not in self._wf_defs:
            self.register_worker([workflow])
        self._wf_defs[key] = workflow
        self._steps.setdefault(key, workflow.steps)
        self._store.create_run(workflow.workflow_id, instance, workflow.steps.keys())
        self._store.set_inputs(workflow.workflow_id, instance, inputs or {})
        self._instances.append((workflow.workflow_id, workflow.version, instance))
        self._instance_version[(workflow.workflow_id, instance)] = workflow.version
        for step_name, step in workflow.steps.items():
            if not step.predecessors:
                self._store.enqueue(workflow.workflow_id, instance, step_name)
        return instance

    def _ready(self, workflow: WorkflowSchema, step: StepSchema, instance_id: str) -> bool:
        finished = {Status.SUCCEEDED, Status.SKIPPED}
        groups = {p for g in step.or_groups.values() for p in g}
        for group in step.or_groups.values():
            if not any(self._store.get_state(workflow.workflow_id, instance_id, p) in finished for p in group):
                return False
        for pred in step.predecessors:
            if pred in groups:
                continue
            if self._store.get_state(workflow.workflow_id, instance_id, pred) not in finished:
                return False
        state = self._store.get_state(workflow.workflow_id, instance_id, step.name)
        return state == Status.PENDING

    def _build_inputs(self, workflow: WorkflowSchema, instance_id: str, step: StepSchema) -> dict[str, Any]:
        deps = {p: self._store.get_result(workflow.workflow_id, instance_id, p) for p in step.predecessors}
        return {
            "workflow_inputs": self._store.get_inputs(workflow.workflow_id, instance_id),
            "results": {k: v for k, v in deps.items() if v is not None},
        }

    def get_step(self, worker_id: str) -> StepAssignment | None:
        self._prune_dead()
        allowed = self._workers.get(worker_id, set())
        self._last_seen[worker_id] = time.time()
        for wf_id, version, instance in self._instances:
            if (wf_id, version) not in allowed:
                continue
            step_name = self._store.fetch_next(wf_id, instance)
            if step_name:
                key = (wf_id, version)
                workflow = self._wf_defs[key]
                step = workflow.steps.get(step_name)
                if step is None:
                    # ignore unknown entries
                    continue
                inputs = self._build_inputs(workflow, instance, step)
                assigned_at = time.time()
                expires_at = assigned_at + 60.0
                self._store.assign_step(wf_id, instance, step_name, worker_id, expires_at)
                return StepAssignment(
                    workflow_id=wf_id,
                    instance_id=instance,
                    step_name=step_name,
                    payload=inputs,
                    assigned_at=assigned_at,
                    expires_at=expires_at,
                )
        return None

    def report_step(
        self,
        worker_id: str,
        report: StepReport,
    ) -> None:
        self._prune_dead()
        workflow_id = report.workflow_id
        instance_id = report.instance_id
        step_name = report.step_name
        state = report.state
        result = report.result

        version = self._instance_version[(workflow_id, instance_id)]
        key = (workflow_id, version)
        workflow = self._wf_defs[key]
        step = workflow.steps[step_name]
        assignment = self._store.get_assignment(workflow_id, instance_id, step_name)
        if assignment and assignment[0] != worker_id:
            return
        self._store.clear_assignment(workflow_id, instance_id, step_name)
        self._store.set_state(workflow_id, instance_id, step_name, state)
        self._store.set_result(workflow_id, instance_id, step_name, result)
        if state in {Status.SUCCEEDED, Status.SKIPPED}:
            action = result if isinstance(result, str) else None
            succ_names = []
            if action and action in step.successors:
                succ_names.extend(step.successors[action])
            else:
                succ_names.extend(step.successors.get("default", []))
            for succ in succ_names:
                succ_schema = workflow.steps[succ]
                if self._ready(workflow, succ_schema, instance_id):
                    self._store.enqueue(workflow_id, instance_id, succ)
        # finalize when no more tasks remain
        if not self._store._queues[(workflow_id, instance_id)]:
            self._store.finalize_run(workflow_id, instance_id)

        self._last_seen[worker_id] = time.time()
        self._last_task[worker_id] = LastTask(
            workflow_id=workflow_id,
            instance_id=instance_id,
            step_name=step_name,
            success=state == Status.SUCCEEDED,
        )

    def keep_alive(self, worker_id: str) -> None:
        self._last_seen[worker_id] = time.time()
        self._prune_dead()

    # Repository management -------------------------------------------------

    def register_repository(self, repo: RepositoryInfo) -> None:
        self._repositories[repo.name] = repo

    def get_repository(self, name: str) -> RepositoryInfo | None:
        return self._repositories.get(name)

    def list_repositories(self, page: int = 1, page_size: int = 50) -> list[RepositoryInfo]:
        repos = list(self._repositories.values())
        start = (page - 1) * page_size
        end = start + page_size
        return repos[start:end]

    def list_workers(self) -> list[WorkerInfo]:
        self._prune_dead()
        workers: list[WorkerInfo] = []
        for wid in self._workers.keys():
            workers.append(
                WorkerInfo(
                    worker_id=wid,
                    connected_at=self._connected_at.get(wid, 0.0),
                    last_seen=self._last_seen.get(wid, 0.0),
                    last_task=self._last_task.get(wid),
                )
            )
        return workers
