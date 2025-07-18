import asyncio
from pathlib import Path

from fuseline import AsyncStep, AsyncWorkflow, Computed, Depends, PoolEngine


class AsyncAddTask(AsyncStep):
    async def run_step_async(self, a: int, b: int) -> int:
        await asyncio.sleep(0.1)
        return a + b


add = AsyncAddTask()


class AsyncMultiplyBy2(AsyncStep):
    async def run_step_async(self, value: Computed[int] = Depends(add)) -> int:
        await asyncio.sleep(0.1)
        return value * 2


class AsyncMultiplyBy3(AsyncStep):
    async def run_step_async(self, value: Computed[int] = Depends(add)) -> int:
        await asyncio.sleep(0.1)
        return value * 3


class AsyncJoinTask(AsyncStep):
    mul2 = AsyncMultiplyBy2()
    mul3 = AsyncMultiplyBy3()

    async def run_step_async(
        self,
        res2: Computed[int] = Depends(mul2),
        res3: Computed[int] = Depends(mul3),
    ) -> None:
        await asyncio.sleep(0.1)
        print(f"results: {res2}, {res3}")


async def main() -> None:
    join = AsyncJoinTask()
    wf = AsyncWorkflow(outputs=[join])
    await wf.run_async({"a": 1, "b": 2}, execution_engine=PoolEngine(2))
    path = Path(__file__).with_suffix(".yaml")
    wf.export(str(path))
    print(f"exported to {path}")


if __name__ == "__main__":
    asyncio.run(main())
