# Fuseline

`fuseline` is a lightweight framework for building small workflow pipelines in Python. It provides primitives for connecting tasks together and executing them synchronously or asynchronously.

## Installation

```bash
pip install fuseline
```

## Quick start

The following example wires two steps and runs them:

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

Head over to the [Usage Guide](usage.md) for more details.
