---
title: "Retries with backoff"
---

Steps accept `max_retries` and `wait` parameters to retry on failure.


```python
from fuseline import Step

class SometimesFails(Step):
    def run_step(self):
        raise RuntimeError("oops")

step = SometimesFails(max_retries=3, wait=1)
```


