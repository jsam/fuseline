---
title: "Fail-fast policy"
---

Downstream steps are cancelled when a dependency fails.


```python
from fuseline import Step, Workflow

class Fails(Step):
    def run_step(self):
        raise RuntimeError()

class Dep(Step):
    def run_step(self):
        print("will not run")

f = Fails()
d = Dep()
f >> d
Workflow(outputs=[d]).run()
```


