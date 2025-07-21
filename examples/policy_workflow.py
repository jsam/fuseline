from fuseline import Step, Workflow
from fuseline.broker import MemoryBroker
from fuseline.broker.clients import LocalBrokerClient
from fuseline.worker import ProcessEngine
from fuseline.workflow.policies import RetryPolicy, StepTimeoutPolicy


class SometimesFails(Step):
    def __init__(self) -> None:
        super().__init__()
        self.attempts = 0

    def run_step(self) -> None:
        self.attempts += 1
        if self.attempts < 2:
            raise RuntimeError("boom")


fail = SometimesFails()
# attach policies
fail.policies.append(RetryPolicy(max_retries=3, wait=0.5))
fail.policies.append(StepTimeoutPolicy(5.0))

wf = Workflow(outputs=[fail])
broker = MemoryBroker()
client = LocalBrokerClient(broker)
engine = ProcessEngine(client, [wf])
engine.work()
