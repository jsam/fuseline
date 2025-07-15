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
