from fuseline import Depends, Task, Workflow
from fuseline.typing import Computed


class AddTask(Task):
    def task(self, x: int, y: int) -> int:
        return x + y


class MulTask(Task):
    add = AddTask()

    def task(self, val: Computed[int] = Depends(add)) -> int:
        return val * 2


class PrintTask(Task):
    mul = MulTask()

    def task(self, val: Computed[int] = Depends(mul)) -> None:
        print(f"result: {val}")


class DoneTask(Task):
    def run_step(self, setup_res):
        print("done")


if __name__ == "__main__":
    done = DoneTask()
    printer = PrintTask()
    printer >> done  # manual chaining after typed dependencies
    wf = Workflow(printer.mul.add)
    printer.mul.add.params = {"x": 2, "y": 3}
    wf.run({})
