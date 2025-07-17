import asyncio

from fuseline import AsyncStep, AsyncWorkflow, Computed, Depends


class AsyncAddTask(AsyncStep):
    async def run_step_async(self, x: int, y: int) -> int:
        await asyncio.sleep(0.1)
        return x + y


class AsyncMulTask(AsyncStep):
    add = AsyncAddTask()

    async def run_step_async(self, val: Computed[int] = Depends(add)) -> int:
        await asyncio.sleep(0.1)
        return val * 2


async def main():
    mul = AsyncMulTask()
    wf = AsyncWorkflow(outputs=[mul])
    result = await wf.run_async({"x": 2, "y": 3})
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
