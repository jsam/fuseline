from fuseline import Depends, Task, Workflow
from fuseline.typing import Computed


class AddTask(Task):
    def run_step(self, x: int, y: int) -> int:
        return x + y


class MulTask(Task):
    add = AddTask()

    def run_step(self, val: Computed[int] = Depends(add)) -> int:
        return val * 2


if __name__ == "__main__":
    mul = MulTask()
    wf = Workflow(mul.add)
    mul.add.params = {"x": 2, "y": 3}
    result = wf.run({})
    print(result)
