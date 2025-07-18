from fuseline import Computed, Depends, Step, Workflow


class AddTask(Step):
    def run_step(self, x: int, y: int) -> int:
        return x + y


class MulTask(Step):
    add = AddTask()

    def run_step(self, val: Computed[int] = Depends(add)) -> int:
        return val * 2


if __name__ == "__main__":
    mul = MulTask()
    wf = Workflow(outputs=[mul])
    result = wf.run({"x": 2, "y": 3})
    print(result)
