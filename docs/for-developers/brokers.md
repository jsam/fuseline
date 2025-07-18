---
title: "Implementing Brokers"
---

A **broker** coordinates workflow runs. It stores workflow schemas,
queues step assignments and records results so workers can cooperate.
Production deployments expose the broker via a network API while unit
tests often use :class:`MemoryBroker` directly.

## Responsibilities

- **Store schemas** – workers register the workflow versions they can
  execute. The broker persists these definitions and rejects incompatible
  changes.
- **Dispatch runs** – creating a workflow instance enqueues all starting
  steps using a :class:`RuntimeStorage` backend.
- **Serve assignments** – workers call :py:meth:`Broker.get_step` to
  receive a :class:`StepAssignment` containing the inputs and a timeout
  deadline.
- **Accept reports** – after executing a step, a worker sends back a
  :class:`StepReport`. The broker records the result and enqueues any
  successors.
- **Persist state** – concrete implementations typically delegate all
  persistence to ``RuntimeStorage`` which may use a database or message
  queue.

## Example

```python
from fuseline.broker import MemoryBroker
from fuseline.workflow import Workflow

broker = MemoryBroker()
wf = Workflow(outputs=[...])  # build a workflow graph
broker.dispatch_workflow(wf.to_schema())
```

``MemoryBroker`` lives entirely in memory and is useful for tests or
single‑process demos. Real deployments usually expose the broker over
HTTP. The [Broker API](broker-api.md) page describes the network
endpoints.

## Custom broker class

To implement your own broker, subclass :class:`Broker` and provide all
abstract methods. At minimum you must handle workflow registration,
dispatching runs, handing out ``StepAssignment`` objects and accepting
``StepReport`` updates. Most methods simply wrap calls to an underlying
``RuntimeStorage`` implementation.

```python
from fuseline.broker import Broker, StepAssignment, StepReport
from fuseline.workflow import WorkflowSchema
from fuseline.storage import RuntimeStorage

class MyBroker(Broker):
    def __init__(self, storage: RuntimeStorage) -> None:
        self._store = storage

    def register_worker(self, workflows: list[WorkflowSchema]) -> str:
        ...  # persist schemas and return a worker id

    def dispatch_workflow(self, workflow: WorkflowSchema, inputs=None) -> str:
        ...  # create run and enqueue starting steps

    def get_step(self, worker_id: str) -> StepAssignment | None:
        ...  # pop the next ready step from storage

    def report_step(self, worker_id: str, report: StepReport) -> None:
        ...  # store state and enqueue successors

    def keep_alive(self, worker_id: str) -> None:
        ...  # optional heartbeat handling
```

Once a broker exposes these methods it can be wrapped in a network
service and used by multiple workers.
