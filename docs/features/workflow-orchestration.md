---
title: "Workflow orchestration"
---

Chain steps with `>>` or dependency injection and run them with `Workflow`.


```python
from fuseline import Step, Workflow

class Hello(Step):
    def run_step(self, _setup_res):
        print("hello")

class World(Step):
    def run_step(self, _setup_res):
        print("world")

hello = Hello()
world = World()
hello >> world
Workflow(outputs=[world]).run()
```


