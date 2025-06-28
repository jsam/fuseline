"""Example demonstrating conditional execution with ``Depends``."""

from fuseline import Depends, Task, Workflow


class Equals:
    """Simple condition checking that a value equals ``expected``."""

    def __init__(self, expected: object) -> None:
        self.expected = expected

    def __call__(self, value: object) -> bool:  # pragma: no cover - trivial
        return value == self.expected


class DecideTask(Task):
    def run_step(self, flag: bool) -> bool:
        print("deciding")
        return flag

decider = DecideTask()


class DefaultTask(Task):
    def run_step(
        self, _flag: bool = Depends(decider, condition=Equals(False))
    ) -> None:
        print("default branch")

class SkipTask(Task):
    def run_step(
        self, _flag: bool = Depends(decider, condition=Equals(True))
    ) -> None:
        print("skip branch")

if __name__ == "__main__":
    default = DefaultTask()
    skip = SkipTask()
    wf = Workflow(outputs=[default, skip])
    wf.run({"flag": True})
