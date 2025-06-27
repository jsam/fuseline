import asyncio

from fuseline import AsyncTask, AsyncWorkflow, Depends
from fuseline.typing import Computed


class AsyncAddTask(AsyncTask):
    async def run_step_async(self, x: int, y: int) -> int:
        await asyncio.sleep(0.1)
        return x + y


class AsyncMulTask(AsyncTask):
    add = AsyncAddTask()

    async def run_step_async(self, val: Computed[int] = Depends(add)) -> int:
        await asyncio.sleep(0.1)
        return val * 2


async def main():
    mul = AsyncMulTask()
    wf = AsyncWorkflow(mul.add)
    mul.add.params = {"x": 2, "y": 3}
    result = await wf.run_async({})
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
