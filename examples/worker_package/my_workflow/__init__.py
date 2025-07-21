from fuseline import Step, Workflow

class Hello(Step):
    def run_step(self) -> None:
        print("hello from packaged workflow")

hello_step = Hello()
workflow = Workflow(outputs=[hello_step])
