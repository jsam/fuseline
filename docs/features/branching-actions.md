---
title: "Branching actions"
---

Steps can return action names to select successor steps.

```python
from fuseline import Task

class Chooser(Task):
    def run_step(self) -> str:
        return "next"
```
