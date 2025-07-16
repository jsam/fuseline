---
title: "State & storage"
---

Fuseline tracks both step state and workflow state.

### Step states

Steps transition through several `Status` values:

- `PENDING` – waiting to run
- `RUNNING` – currently executing
- `SUCCEEDED` – completed normally
- `FAILED` – raised an exception
- `CANCELLED` – skipped because a dependency failed
- `SKIPPED` – condition evaluated to false

These states are visible on each `Step` instance and may be persisted
via a `RuntimeStorage` implementation.

### Workflow state

A workflow mirrors its steps and finishes as `SUCCEEDED` or `FAILED`.
The engine writes workflow status after execution and calls
`RuntimeStorage.finalize_run` when complete.

### Storing inputs and outputs

Each task receives parameters from the workflow's input mapping. Results
are placed in the shared dictionary keyed by the step object so other
steps can access them. When using a runtime store, states—not data—are
persisted. Developers can persist additional artifacts in custom step
logic if needed.

### RuntimeStorage interface

Workflow state is stored via a pluggable backend.  A storage backend
implements the `RuntimeStorage` abstract base class.  The key methods
look like this:

```python
class RuntimeStorage(ABC):
    def create_run(self, workflow_id: str, instance_id: str, steps: Iterable[str]) -> None: ...
    def enqueue(self, workflow_id: str, instance_id: str, step_name: str) -> None: ...
    def fetch_next(self, workflow_id: str, instance_id: str) -> str | None: ...
    def set_state(self, workflow_id: str, instance_id: str, step_name: str, state: Status) -> None: ...
    def get_state(self, workflow_id: str, instance_id: str, step_name: str) -> Status | None: ...
    def finalize_run(self, workflow_id: str, instance_id: str) -> None: ...
```

Any backend that implements this interface can be used to persist state.
When writing a custom backend, keep these
responsibilities in mind:

1. **Create runs** – called once to initialise the queue and set all
   steps to `PENDING`.
2. **Enqueue/fetch steps** – provide a simple FIFO queue so workers can
   coordinate.
3. **Persist state** – update step status after execution and expose it
   via `get_state`.
4. **Finalize** – mark the run complete so other tools know the
   workflow finished.

Only statuses are stored.  Step results remain in memory and should be
persisted separately if desired.  For advanced storage backends you may
choose to store results or metadata alongside the status values.
