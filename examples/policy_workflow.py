from fuseline import Step, Workflow
from fuseline.policies import RetryPolicy


class SometimesFails(Step):
    def __init__(self) -> None:
        super().__init__(max_retries=1)
        self.attempts = 0

    def run_step(self) -> None:
        self.attempts += 1
        if self.attempts < 2:
            raise RuntimeError("boom")


fail = SometimesFails()
# attach a custom policy
fail.policies.append(RetryPolicy(max_retries=3, wait=0.5))

wf = Workflow(outputs=[fail])
wf.run()
