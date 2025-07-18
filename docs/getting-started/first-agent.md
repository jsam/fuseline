---
title: "Writing Your First Agent"
---


This tutorial walks through the basics of building an agent using Fuseline.

## Building Steps

Steps subclass `Step` and implement `run_step` to perform work. Steps can be chained using the `>>` operator.



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
flow = Workflow(outputs=[world])
flow.run()

```


## Typed Dependencies

Steps can depend on the output of other steps using `Depends` and `Computed`.


```python
from fuseline import Computed, Depends, Step, Workflow

class Add(Step):
    def run_step(self, x: int, y: int) -> int:
        return x + y

class Multiply(Step):
    add = Add()
    def run_step(self, value: Computed[int] = Depends(add)) -> int:
        return value * 2

mul = Multiply()
wf = Workflow(outputs=[mul])
print(wf.run({"x": 2, "y": 3}))  # prints 10

```


## Asynchronous Workflows

Use `AsyncStep` and `AsyncWorkflow` to execute steps asynchronously.


```python
import asyncio
from fuseline import AsyncStep, AsyncWorkflow

class AsyncHello(AsyncStep):
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

Run independent branches in parallel using an execution engine such as `PoolEngine`.


```python
from fuseline import PoolEngine

wf.run({"a": 1, "b": 2}, execution_engine=PoolEngine(2))

```


## Exporting and Tracing

Workflows can be exported to YAML with `Workflow.export()` and execution traces can be recorded using the `trace` parameter.


```python
wf.export("workflow.yaml")
wf = Workflow(outputs=[step], trace="trace.log")
wf.run({})

```


