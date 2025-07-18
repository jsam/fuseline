from fuseline import Computed, Depends, PoolEngine, Step, Workflow


class Add(Step):
    def run_step(self, x: int, y: int) -> int:
        return x + y

add = Add()

class Mul(Step):
    def run_step(self, value: Computed[int] = Depends(add)) -> int:
        return value * 2

mul = Mul()
add >> mul

if __name__ == "__main__":
    wf = Workflow(outputs=[mul], trace=str(__file__).replace('.py', '.trace'))
    wf.run({"x": 1, "y": 2}, execution_engine=PoolEngine())
    print("workflow traced")
