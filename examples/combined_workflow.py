from fuseline import Computed, Depends, Step, Workflow


class AddTask(Step):
    def run_step(self, x: int, y: int) -> int:
        return x + y


class MulTask(Step):
    add = AddTask()

    def run_step(self, val: Computed[int] = Depends(add)) -> int:
        return val * 2


class PrintTask(Step):
    mul = MulTask()

    def run_step(self, val: Computed[int] = Depends(mul)) -> None:
        print(f"result: {val}")


class DoneTask(Step):
    def run_step(self, setup_res):
        print("done")


if __name__ == "__main__":
    done = DoneTask()
    printer = PrintTask()
    printer >> done  # manual chaining after typed dependencies
    wf = Workflow(outputs=[done])
    wf.run({"x": 2, "y": 3})
