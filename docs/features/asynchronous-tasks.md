---
title: "Asynchronous steps"
---

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


