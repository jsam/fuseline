---
title: "Fail-fast policy"
---

Downstream steps are cancelled when a dependency fails.

```python
from fuseline import Task, Workflow

class Fails(Task):
    def run_step(self):
        raise RuntimeError()

class Dep(Task):
    def run_step(self):
        print("will not run")

f = Fails()
d = Dep()
f >> d
Workflow(outputs=[d]).run()
```

