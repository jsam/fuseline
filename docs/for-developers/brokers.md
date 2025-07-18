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

## Running the built-in HTTP broker

``MemoryBroker`` lives entirely in memory and is mostly useful for unit
tests or single‑process demos. Production deployments should expose the
broker over HTTP so multiple workers can connect. Fuseline ships with a
ready-to-use server implemented with `Robyn`.

```bash
python -m fuseline.broker.http
```

The server uses :class:`PostgresBroker` under the hood and reads the
database URL from the ``DATABASE_URL`` environment variable. Workers call
the API described in [Broker API](broker-api.md) to register workflows and
fetch assignments.

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

### docker-compose example

``examples/docker-compose.yml`` launches Postgres and the Robyn broker:

```yaml
version: '3'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: fuseline
      POSTGRES_PASSWORD: fuseline
      POSTGRES_DB: fuseline
    ports:
      - "5432:5432"
  broker:
    image: python:3.11-slim
    volumes:
      - ./../:/app
    working_dir: /app/examples
    command: python -m fuseline.broker.http
    environment:
      DATABASE_URL: postgresql://fuseline:fuseline@db:5432/fuseline
    depends_on:
      - db
    ports:
      - "8000:8000"
```
