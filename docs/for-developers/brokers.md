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

## Example: simple HTTP broker

``MemoryBroker`` lives entirely in memory and is mostly useful for unit
tests or single‑process demos.  A real deployment runs the broker as a
server and exposes the API described in [Broker API](broker-api.md).  The
snippet below sketches a small HTTP service using `FastAPI` that wraps a
``MemoryBroker`` so workers can connect over the network.

```python
# broker_server.py (server process)
from fastapi import FastAPI, HTTPException

from fuseline.broker import MemoryBroker, StepReport
from fuseline.workflow import WorkflowSchema

broker = MemoryBroker()
app = FastAPI()

@app.post("/worker/register")
def register(workflows: list[dict]) -> str:
    return broker.register_worker([WorkflowSchema(**wf) for wf in workflows])

@app.post("/workflow/dispatch")
def dispatch(payload: dict) -> str:
    wf = WorkflowSchema(**payload["workflow"])
    return broker.dispatch_workflow(wf, payload.get("inputs"))

@app.get("/workflow/step")
def get_step(worker_id: str):
    assignment = broker.get_step(worker_id)
    if assignment is None:
        raise HTTPException(status_code=204)
    return assignment.model_dump()

@app.post("/workflow/step")
def report_step(worker_id: str, report: dict) -> None:
    broker.report_step(worker_id, StepReport(**report))
```

Workers would send HTTP requests to these endpoints instead of calling
``MemoryBroker`` methods directly.

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
