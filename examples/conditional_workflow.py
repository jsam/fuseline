from fuseline import Task, Workflow


class DecideTask(Task):
    def run_step(self, flag: bool) -> str:
        print("deciding")
        return "skip" if flag else "default"

class DefaultTask(Task):
    def run_step(self) -> None:
        print("default branch")

class SkipTask(Task):
    def run_step(self) -> None:
        print("skip branch")

if __name__ == "__main__":
    decide = DecideTask()
    default = DefaultTask()
    skip = SkipTask()

    decide.next(default, "default")
    (decide - "skip") >> skip

    wf = Workflow(outputs=[default, skip])
    wf.run({"flag": True})
