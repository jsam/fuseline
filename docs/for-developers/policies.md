---
title: "Policies"
---

Fuseline exposes a pluggable *policy* system. Policies attach to steps or
workflows and modify how they run.

### Retries and backoff

`RetryPolicy` controls how many times a step is retried. `Task` and
`AsyncTask` automatically include a policy configured via the
`max_retries` and `wait` arguments.

```python
from fuseline import Task, Workflow
from fuseline.policies import RetryPolicy

class Flaky(Task):
    def run_step(self) -> None:
        raise RuntimeError("boom")

step = Flaky()
step.policies.append(RetryPolicy(max_retries=3, wait=1))
Workflow(outputs=[step]).run()
```

Custom policies can subclass `StepPolicy` and override the hooks to
implement additional behaviour.

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
