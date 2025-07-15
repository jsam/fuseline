---
title: "Typed dependencies"
---

Pass values between tasks using `Depends` and `Computed`.

```python
from fuseline import Computed, Depends, Task, Workflow

class Add(Task):
    def run_step(self, x: int, y: int) -> int:
        return x + y

class Multiply(Task):
    add = Add()
    def run_step(self, value: Computed[int] = Depends(add)) -> int:
        return value * 2

wf = Workflow(outputs=[Multiply()])
print(wf.run({"x": 2, "y": 3}))
```

