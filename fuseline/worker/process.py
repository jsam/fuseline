from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..workflow import Step, Workflow

from ..broker.clients import BrokerClient
if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..broker import StepReport


class ProcessEngine:
    """Execute workflow steps fetched via a :class:`BrokerClient`."""

    def __init__(self, client: BrokerClient, workflows: Iterable["Workflow"]) -> None:
        self.client = client
        self.workflows = {wf.workflow_id: wf for wf in workflows}
        self._step_names: dict[str, dict["Step", str]] = {}
        self._rev_names: dict[str, dict[str, "Step"]] = {}
        for wf in workflows:
            mapping = wf._step_name_map()
            self._step_names[wf.workflow_id] = mapping
            self._rev_names[wf.workflow_id] = {n: s for s, n in mapping.items()}
        schemas = [wf.to_schema() for wf in workflows]
        self.worker_id = client.register_worker(schemas)

    def work(self) -> None:
        while True:
            assignment = self.client.get_step(self.worker_id)
            if assignment is None:
                break
            wf_id = assignment.workflow_id
            instance_id = assignment.instance_id
            step_name = assignment.step_name
            payload = assignment.payload
            workflow = self.workflows[wf_id]
            step = self._rev_names[wf_id][step_name]
            shared = {self._rev_names[wf_id][name]: value for name, value in payload.get("results", {}).items()}
            workflow.params.update(payload.get("workflow_inputs", {}))
            result = workflow._execute_step(step, shared)
            from ..broker import StepReport  # imported lazily to avoid cycle

            self.client.report_step(
                self.worker_id,
                StepReport(
                    workflow_id=wf_id,
                    instance_id=instance_id,
                    step_name=step_name,
                    state=step.state,
                    result=result,
                ),
            )
