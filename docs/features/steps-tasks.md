---
title: "Steps and Tasks"
---

A **Step** defines the basic lifecycle for a unit of work while a **Task** adds typed dependencies and retry support.

```python
from fuseline import Task

class Hello(Task):
    def run_step(self, _setup_res):
        print("hello")
```
