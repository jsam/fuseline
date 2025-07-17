---
title: "Steps and Tasks"
---

Fuseline builds workflows out of **steps**. A `Step` defines the minimal
lifecycle for a unit of work with `setup`, `run_step` and `teardown`
hooks. Steps can be chained together to form a `Workflow`.

A **Task** is a more convenient `Step` that understands typed
dependencies and includes a simple retry policy. Parameters annotated
with `Depends` are automatically wired from previous steps. The
`max_retries` and `wait` arguments configure the default
`RetryPolicy` attached to the task.

### AsyncTask

`AsyncTask` mirrors `Task` but uses async lifecycle methods such as
`run_step_async`. Use it when a step needs to `await` other work.

### BatchTask

`BatchTask` executes its step for each item in an iterable input. This
is useful when the same logic should run over multiple parameter sets.

```python
from fuseline import Task

class Hello(Task):
    def run_step(self, _setup_res):
        print("hello")
```
