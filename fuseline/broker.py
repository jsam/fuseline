from __future__ import annotations

from abc import ABC, abstractmethod
import uuid
from typing import Any, Iterable, Optional

from .workflow import Status, Workflow, Step, Task
from .storage import MemoryRuntimeStorage


class Broker(ABC):
    """Interface implemented by the workflow broker."""

    @abstractmethod
    def register_worker(self, workflows: Iterable[Workflow]) -> str:
        """Register a worker and return a worker ID."""

    @abstractmethod
    def dispatch_workflow(
        self, workflow: Workflow, inputs: Optional[dict[str, Any]] = None
    ) -> str:
        """Create a workflow run and queue initial steps."""

    @abstractmethod
    def get_step(self, worker_id: str) -> tuple[str, str, str, dict[str, Any]] | None:
        """Return the next step and input payload for *worker_id* or ``None``."""

    @abstractmethod
    def report_step(
        self,
        worker_id: str,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        state: Status,
        result: Any,
    ) -> None:
        """Update the state of *step_name* for *worker_id*."""

    @abstractmethod
    def keep_alive(self, worker_id: str) -> None:
        """Notify the broker that *worker_id* is still active."""


class MemoryBroker(Broker):
    """Simple in-memory broker used for tests."""

    def __init__(self) -> None:
        self._workers: dict[str, set[tuple[str, str]]] = {}
        self._wf_defs: dict[tuple[str, str], Workflow] = {}
        self._step_names: dict[tuple[str, str], dict[Step, str]] = {}
        self._rev_names: dict[tuple[str, str], dict[str, Step]] = {}
        self._instances: list[tuple[str, str, str]] = []
        self._instance_version: dict[tuple[str, str], str] = {}
        self._store = MemoryRuntimeStorage()
        self._wid = 0
        self._heartbeat: set[str] = set()

    def register_worker(self, workflows: Iterable[Workflow]) -> str:
        self._wid += 1
        wid = str(self._wid)
        wf_keys: set[tuple[str, str]] = set()
        for wf in workflows:
            key = (wf.workflow_id, wf.workflow_version)
            existing = self._wf_defs.get(key)
            if existing and existing is not wf:
                raise ValueError("workflow schema mismatch")
            self._wf_defs.setdefault(key, wf)
            if key not in self._step_names:
                mapping = wf._step_name_map()
                self._step_names[key] = mapping
                self._rev_names[key] = {n: s for s, n in mapping.items()}
            wf_keys.add(key)
        self._workers[wid] = wf_keys
        return wid

    def dispatch_workflow(
        self, workflow: Workflow, inputs: Optional[dict[str, Any]] = None
    ) -> str:
        instance = uuid.uuid4().hex
        key = (workflow.workflow_id, workflow.workflow_version)
        if key not in self._wf_defs:
            self.register_worker([workflow])
        self._wf_defs[key] = workflow
        mapping = self._step_names[key]
        self._store.create_run(workflow.workflow_id, instance, mapping.values())
        self._store.set_inputs(workflow.workflow_id, instance, inputs or {})
        self._instances.append((workflow.workflow_id, workflow.workflow_version, instance))
        self._instance_version[(workflow.workflow_id, instance)] = workflow.workflow_version
        nodes = workflow._collect_steps()
        indegree: dict[Step, int] = {n: 0 for n in nodes}
        for succ in nodes:
            group_preds: set[Step] = set()
            if isinstance(succ, Task):
                succ.or_remaining = {k: True for k in succ.or_groups}
                for group in succ.or_groups.values():
                    indegree[succ] += 1
                    group_preds.update(group)
            for pred in succ.predecessors:
                if pred not in group_preds:
                    indegree[succ] += 1
        ready = [n for n, d in indegree.items() if d == 0]
        for step in ready:
            self._store.enqueue(workflow.workflow_id, instance, mapping[step])
        workflow.workflow_instance_id = instance
        return instance

    def _ready(self, workflow: Workflow, step: Step, instance_id: str) -> bool:
        key = (workflow.workflow_id, workflow.workflow_version)
        mapping = self._step_names[key]
        finished = {Status.SUCCEEDED, Status.SKIPPED}
        groups = {p for g in getattr(step, "or_groups", {}).values() for p in g}
        for group in getattr(step, "or_groups", {}).values():
            if not any(
                self._store.get_state(workflow.workflow_id, instance_id, mapping[p])
                in finished
                for p in group
            ):
                return False
        for pred in step.predecessors:
            if pred in groups:
                continue
            if (
                self._store.get_state(workflow.workflow_id, instance_id, mapping[pred])
                not in finished
            ):
                return False
        state = self._store.get_state(workflow.workflow_id, instance_id, mapping[step])
        return state == Status.PENDING

    def _build_inputs(self, workflow: Workflow, instance_id: str, step: Step) -> dict[str, Any]:
        key = (workflow.workflow_id, workflow.workflow_version)
        mapping = self._step_names[key]
        deps = {
            mapping[p]: self._store.get_result(workflow.workflow_id, instance_id, mapping[p])
            for p in step.predecessors
        }
        return {
            "workflow_inputs": self._store.get_inputs(workflow.workflow_id, instance_id),
            "results": {k: v for k, v in deps.items() if v is not None},
        }

    def get_step(self, worker_id: str) -> tuple[str, str, str, dict[str, Any]] | None:
        allowed = self._workers.get(worker_id, set())
        for wf_id, version, instance in self._instances:
            if (wf_id, version) not in allowed:
                continue
            step_name = self._store.fetch_next(wf_id, instance)
            if step_name:
                key = (wf_id, version)
                workflow = self._wf_defs[key]
                step = self._rev_names[key].get(step_name)
                if step is None:
                    # ignore unknown entries
                    continue
                inputs = self._build_inputs(workflow, instance, step)
                return wf_id, instance, step_name, inputs
        return None

    def report_step(
        self,
        worker_id: str,
        workflow_id: str,
        instance_id: str,
        step_name: str,
        state: Status,
        result: Any,
    ) -> None:
        version = self._instance_version[(workflow_id, instance_id)]
        key = (workflow_id, version)
        workflow = self._wf_defs[key]
        mapping = self._step_names[key]
        step = self._rev_names[key][step_name]
        self._store.set_state(workflow_id, instance_id, step_name, state)
        self._store.set_result(workflow_id, instance_id, step_name, result)
        if state in {Status.SUCCEEDED, Status.SKIPPED}:
            action = result if isinstance(result, str) else None
            for succ in workflow.get_next_steps(step, action):
                if self._ready(workflow, succ, instance_id):
                    self._store.enqueue(workflow_id, instance_id, mapping[succ])
        # finalize when no more tasks remain
        if not self._store._queues[(workflow_id, instance_id)]:
            self._store.finalize_run(workflow_id, instance_id)

    def keep_alive(self, worker_id: str) -> None:
        self._heartbeat.add(worker_id)

