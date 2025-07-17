from pathlib import Path

from fuseline import Computed, Depends, PoolEngine, Step, Workflow


class AddTask(Step):
    def run_step(self, a: int, b: int) -> int:
        return a + b


add = AddTask()


class MultiplyBy2(Step):
    def run_step(self, value: Computed[int] = Depends(add)) -> int:
        return value * 2


class MultiplyBy3(Step):
    def run_step(self, value: Computed[int] = Depends(add)) -> int:
        return value * 3


class JoinTask(Step):
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
    wf.run({"a": 1, "b": 2}, execution_engine=PoolEngine(2))
    path = Path(__file__).with_suffix(".yaml")
    wf.export(str(path))
    print(f"exported to {path}")
