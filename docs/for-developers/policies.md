---
title: "Policies"
---

Fuseline exposes a pluggable *policy* system. Policies attach to steps or
workflows and modify how they run.

### Retries and backoff

`RetryPolicy` controls how many times a step is retried. Attach it to a
`Step` or `AsyncStep` to enable retry behaviour.

```python
from fuseline import Step, Workflow
from fuseline.policies import RetryPolicy

class Flaky(Step):
    def run_step(self) -> None:
        raise RuntimeError("boom")

step = Flaky()
step.policies.append(RetryPolicy(max_retries=3, wait=1))
Workflow(outputs=[step]).run()
```

Custom policies can subclass `StepPolicy` and override the hooks to
implement additional behaviour.

### Worker policies

`WorkerPolicy` influences how a worker interacts with the broker. The
provided `StepTimeoutWorkerPolicy` reads a `StepTimeoutPolicy` attached to
a step and sets the assignment expiry accordingly.

```python
from fuseline.policies import StepTimeoutPolicy, StepTimeoutWorkerPolicy

step = Flaky()
step.policies.append(StepTimeoutPolicy(30.0))
engine = ProcessEngine(
    broker,
    [Workflow(outputs=[step])],
    worker_policies={"workflow-id": [StepTimeoutWorkerPolicy()]},
)
```

### Fail-fast

If any step fails after exhausting retries, downstream steps are marked
`CANCELLED` and the workflow state becomes `FAILED`. Set `max_retries=0`
to disable retries. Custom engines may implement alternative semantics.

### Common questions

- How do I override retry logic?  Subclass `StepPolicy`.
- Can I pause a workflow?  Persist state using `RuntimeStorage` and resume
  with `ProcessEngine`.
- Can I change timeouts or other limits?  Implement a custom policy and
  raise exceptions in `run_step` when limits are hit.
