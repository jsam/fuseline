---
title: "Branching actions"
---

Steps can return action names to select successor steps.


```python
from fuseline import Step

class Chooser(Step):
    def run_step(self) -> str:
        return "next"
```


