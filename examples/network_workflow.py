from fuseline import NetworkTask, workflow_from_functions
from fuseline.core.network import Depends
from fuseline.typing import Computed


def multiply(x: int) -> int:
    return x * 2


def add_one(x: Computed[int] = Depends(multiply)) -> int:
    return x + 1


if __name__ == "__main__":
    wf = workflow_from_functions("simple", outputs=[add_one])
    task = wf.start_step  # type: ignore[attr-defined]
    if isinstance(task, NetworkTask):
        task.params = {"x": 3}
    result = wf.run(None)
    if result is not None:
        print("Output:", result.outputs[0].value)
