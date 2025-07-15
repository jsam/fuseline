---
title: "Retries with backoff"
---

Tasks accept `max_retries` and `wait` parameters to retry on failure.


```python
from fuseline import Task

class SometimesFails(Task):
    def run_step(self):
        raise RuntimeError("oops")

step = SometimesFails(max_retries=3, wait=1)
```


