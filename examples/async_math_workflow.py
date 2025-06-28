import asyncio

from fuseline import AsyncTask, AsyncWorkflow, Computed, Depends


class AsyncAddTask(AsyncTask):
    async def run_step_async(self, a: int, b: int) -> int:
        await asyncio.sleep(0.1)
        return a + b


class AsyncMultiplyTask(AsyncTask):
    add = AsyncAddTask()

    async def run_step_async(
        self, value: Computed[int] = Depends(add), c: int = 1
    ) -> int:
        await asyncio.sleep(0.1)
        return value * c


class AsyncPrintTask(AsyncTask):
    mul = AsyncMultiplyTask()

    async def run_step_async(self, result: Computed[int] = Depends(mul)) -> None:
        await asyncio.sleep(0.1)
        print(f"result: {result}")


async def main() -> None:
    printer = AsyncPrintTask()
    wf = AsyncWorkflow(outputs=[printer])
    await wf.run_async({"a": 1, "b": 2, "c": 3})


if __name__ == "__main__":
    asyncio.run(main())
