from fuseline import TypedWorkflow
from fuseline.core.network import Depends
from fuseline.typing import Computed


def multiply(x: int) -> int:
    return x * 2


def add_one(x: Computed[int] = Depends(multiply)) -> int:
    return x + 1


if __name__ == "__main__":
    wf = TypedWorkflow("simple", outputs=[add_one])
    result = wf.run(None, x=3)
    if result is not None:
        print("Output:", result.outputs[0].value)
