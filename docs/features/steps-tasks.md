---
title: "Steps"
---

Fuseline builds workflows out of **steps**. A `Step` defines the minimal
lifecycle for a unit of work with `setup`, `run_step` and `teardown`
hooks. Steps can be chained together to form a `Workflow`.

Steps support typed dependencies and a pluggable policy system. Parameters
annotated with `Depends` are automatically wired from previous steps.
Attach policies such as `RetryPolicy` to control behaviour like retries and
backoff.

### AsyncStep

`AsyncStep` mirrors `Step` but uses async lifecycle methods such as
`run_step_async`. Use it when a step needs to `await` other work.

### BatchStep

`BatchStep` executes its step for each item in an iterable input. This
is useful when the same logic should run over multiple parameter sets.

```python
from fuseline import Step

class Hello(Step):
    def run_step(self, _setup_res):
        print("hello")
```
