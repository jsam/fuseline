---
title: "Retries with backoff"
---

Use `RetryPolicy` to retry a step after failure.


```python
from fuseline import Step

class SometimesFails(Step):
    def run_step(self):
        raise RuntimeError("oops")

step = SometimesFails()
step.policies.append(RetryPolicy(max_retries=3, wait=1))
```


