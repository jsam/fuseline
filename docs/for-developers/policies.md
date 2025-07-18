---
title: "Policies"
---

Fuseline exposes a pluggable *policy* system. Policies attach to steps or
workflows and modify how they run.

Policies are instantiated when a workflow is defined but executed by the
worker when the workflow runs.  When a policy is associated with a step or a
workflow the framework calls ``attach_to_step`` or ``attach_to_workflow`` on the
policy instance allowing it to prepare internal state.

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

### Timeouts

`StepTimeoutPolicy` aborts a step if it runs longer than the configured
number of seconds.

```python
from fuseline.policies import StepTimeoutPolicy

step = Flaky()
step.policies.append(StepTimeoutPolicy(5.0))
Workflow(outputs=[step]).run()
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
