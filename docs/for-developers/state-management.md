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
steps can access them. When a `RuntimeStorage` backend is configured,
the engine stores the workflow inputs and each step's result so other
workers can resume processing after a crash or restart.

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
    def set_inputs(self, workflow_id: str, instance_id: str, inputs: dict[str, Any]) -> None: ...
    def get_inputs(self, workflow_id: str, instance_id: str) -> dict[str, Any]: ...
    def set_result(self, workflow_id: str, instance_id: str, step_name: str, result: Any) -> None: ...
    def get_result(self, workflow_id: str, instance_id: str, step_name: str) -> Any | None: ...
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

The provided in-memory backend stores both step states and their
results along with the workflow inputs.  More advanced backends can
persist these values in databases or message queues so multiple workers
can cooperate on the same run.
