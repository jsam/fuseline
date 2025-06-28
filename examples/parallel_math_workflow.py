from fuseline import Depends, Task, Workflow
from fuseline.typing import Computed


class AddTask(Task):
    def run_step(self, a: int, b: int) -> int:
        return a + b


class MultiplyBy2(Task):
    add = AddTask()

    def run_step(self, value: Computed[int] = Depends(add)) -> int:
        return value * 2


class MultiplyBy3(Task):
    add = AddTask()

    def run_step(self, value: Computed[int] = Depends(add)) -> int:
        return value * 3


class JoinTask(Task):
    mul2 = MultiplyBy2()
    mul3 = MultiplyBy3()

    def run_step(
        self,
        res2: Computed[int] = Depends(mul2),
        res3: Computed[int] = Depends(mul3),
    ) -> None:
        print(f"results: {res2}, {res3}")


if __name__ == "__main__":
    join = JoinTask()
    wf = Workflow(outputs=[join])
    # Rewire execution order to run all tasks sequentially
    join.mul2.add.successors["default"] = join.mul2
    join.mul2.successors["default"] = join.mul3.add
    join.mul3.add.successors["default"] = join.mul3
    wf.start_step = join.mul2.add
    wf.run({"a": 1, "b": 2})
