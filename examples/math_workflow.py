from fuseline import Computed, Depends, Task, Workflow


class AddTask(Task):
    def run_step(self, a: int, b: int) -> int:
        return a + b


class MultiplyTask(Task):
    add = AddTask()

    def run_step(self, value: Computed[int] = Depends(add), c: int = 1) -> int:
        return value * c


class PrintTask(Task):
    mul = MultiplyTask()

    def run_step(self, result: Computed[int] = Depends(mul)) -> None:
        print(f"result: {result}")


if __name__ == "__main__":
    printer = PrintTask()
    wf = Workflow(outputs=[printer])
    wf.run({"a": 1, "b": 2, "c": 3})
