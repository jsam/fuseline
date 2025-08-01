import asyncio

from fuseline import AsyncStep, AsyncWorkflow


class AsyncPrintStep(AsyncStep):
    def __init__(self, message: str, action: str | None = None) -> None:
        super().__init__()
        self.message = message
        self.action = action

    async def run_step_async(self, setup_res):
        await asyncio.sleep(0.1)
        print(self.message)
        return self.action


async def main():
    s1 = AsyncPrintStep("hello")
    s2 = AsyncPrintStep("async world")

    s1 >> s2
    wf = AsyncWorkflow(outputs=[s2])
    await wf.run_async()


if __name__ == "__main__":
    asyncio.run(main())
