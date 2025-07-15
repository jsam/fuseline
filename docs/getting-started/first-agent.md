---
title: "Writing Your First Agent"
---


This tutorial walks through the basics of building an agent using Fuseline.

## Building Steps

Steps subclass `Task` and implement `run_step` to perform work. Steps can be chained using the `>>` operator.

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
flow = Workflow(outputs=[world])
flow.run()
```

## Typed Dependencies

Steps can depend on the output of other steps using `Depends` and `Computed`.

```python
from fuseline import Computed, Depends, Task, Workflow

class Add(Task):
    def run_step(self, x: int, y: int) -> int:
        return x + y

class Multiply(Task):
    add = Add()
    def run_step(self, value: Computed[int] = Depends(add)) -> int:
        return value * 2

mul = Multiply()
wf = Workflow(outputs=[mul])
print(wf.run({"x": 2, "y": 3}))  # prints 10
```

## Asynchronous Workflows

Use `AsyncTask` and `AsyncWorkflow` to execute steps asynchronously.

```python
import asyncio
from fuseline import AsyncTask, AsyncWorkflow

class AsyncHello(AsyncTask):
    async def run_step_async(self, _setup_res):
        await asyncio.sleep(0.1)
        print("hello")

async def main():
    step = AsyncHello()
    wf = AsyncWorkflow(outputs=[step])
    await wf.run_async()

asyncio.run(main())
```

## Parallel Execution

Run independent branches in parallel using an execution engine such as `ProcessEngine`.

```python
from fuseline import ProcessEngine

wf.run({"a": 1, "b": 2}, execution_engine=ProcessEngine(2))
```

## Exporting and Tracing

Workflows can be exported to YAML with `Workflow.export()` and execution traces can be recorded using the `trace` parameter.

```python
wf.export("workflow.yaml")
wf = Workflow(outputs=[step], trace="trace.log")
wf.run({})
```

