---
title: "Workflow orchestration"
---

Chain tasks with `>>` or dependency injection and run them with `Workflow`.

```python
from fuseline import Task, Workflow

class Hello(Task):
    def run_step(self, _setup_res):
        print("hello")

class World(Task):
    def run_step(self, _setup_res):
        print("world")

hello = Hello()
world = World()
hello >> world
Workflow(outputs=[world]).run()
```

