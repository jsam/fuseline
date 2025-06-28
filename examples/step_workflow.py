from fuseline import Task, Workflow


class PrintStep(Task):
    def __init__(self, message: str, action: str = "default") -> None:
        super().__init__()
        self.message = message
        self.action = action

    def run_step(self, setup_res):
        print(self.message)
        return self.action


if __name__ == "__main__":
    hello = PrintStep("hello")
    world = PrintStep("world")

    hello >> world
    flow = Workflow(outputs=[world])
    flow.run()
