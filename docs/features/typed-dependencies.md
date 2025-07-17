---
title: "Typed dependencies"
---

Pass values between steps using `Depends` and `Computed`.


```python
from fuseline import Computed, Depends, Step, Workflow

class Add(Step):
    def run_step(self, x: int, y: int) -> int:
        return x + y

class Multiply(Step):
    add = Add()
    def run_step(self, value: Computed[int] = Depends(add)) -> int:
        return value * 2

wf = Workflow(outputs=[Multiply()])
print(wf.run({"x": 2, "y": 3}))
```


