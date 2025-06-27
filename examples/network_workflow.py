from fuseline import Computed, Depends, Network
from fuseline.workflow import NetworkTask, Workflow


def multiply(x: int) -> int:
    return x * 2


def add_one(x: Computed[int] = Depends(multiply)) -> int:
    return x + 1


network = Network("simple", outputs=[add_one])


if __name__ == "__main__":
    task = NetworkTask(network)
    wf = Workflow(task)
    task.params = {"x": 3}
    wf.run(None)
    print("Output:", network.output)
