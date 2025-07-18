---
title: "Policies"
---

Fuseline exposes a pluggable *policy* system used to change how steps and
workflows execute. Policies are instantiated when a workflow is defined but
are executed by the worker process at runtime.

A policy may be attached to a single step or to the entire workflow. When a
policy object is added the framework calls ``attach_to_step`` or
``attach_to_workflow`` so the instance can bind itself to the target.

Two base classes exist:

* ``StepPolicy`` – modifies the behaviour of an individual ``Step``.  The
  worker calls ``execute`` (and ``execute_async`` for async steps) around the
  step's ``run_step`` method.
* ``WorkflowPolicy`` – observes the workflow lifecycle and receives
  ``on_workflow_start``/``on_step_start``/``on_step_success`` and other hooks.

Policies keep their own configuration and implementation in a single class so a
worker only needs to invoke the interface methods.

## Using built‑in policies

Fuseline ships with a couple of common policies.

### RetryPolicy

``RetryPolicy`` retries a step after failure and optionally waits between
attempts.

```python
from fuseline import Step, Workflow
from fuseline.policies import RetryPolicy

class Flaky(Step):
    def run_step(self) -> None:
        raise RuntimeError("boom")

step = Flaky()
step.add_policy(RetryPolicy(max_retries=3, wait=1))
Workflow(outputs=[step]).run()
```

### StepTimeoutPolicy

``StepTimeoutPolicy`` aborts a step if it runs longer than the configured number
of seconds. It works for synchronous and asynchronous steps.

```python
from fuseline import Workflow
from fuseline.policies import StepTimeoutPolicy

step.add_policy(StepTimeoutPolicy(5.0))
Workflow(outputs=[step]).run()
```

## Attaching custom policies

A custom policy subclasses ``StepPolicy`` or ``WorkflowPolicy`` and overrides
the hooks it cares about. Both the configuration and behaviour live in the same
class.

```python
from fuseline.policies import StepPolicy

class LogStartPolicy(StepPolicy):
    def execute(self, step, call):
        print(f"running {step}")
        return call()
```

Attach it to a step or workflow using ``add_policy``:

```python
s = Flaky()
s.add_policy(LogStartPolicy())
wf = Workflow(outputs=[s])
```

## Executing policies in a custom worker

Workers communicate with a ``Broker`` to fetch ``StepAssignment`` objects and
report results back via ``StepReport``. The easiest way to run workflows is to
use :class:`ProcessEngine` which already handles policy execution. Custom
workers can replicate this by calling ``workflow._execute_step`` with the
assigned step and inputs:

```python
assignment = broker.get_step(worker_id)
step = workflow_step_map[assignment.step_name]
shared = build_shared_dict(assignment.payload)
result = workflow._execute_step(step, shared)
broker.report_step(worker_id, StepReport(
    workflow_id=assignment.workflow_id,
    instance_id=assignment.instance_id,
    step_name=assignment.step_name,
    state=step.state,
    result=result,
))
```

``_execute_step`` applies all policies attached to the workflow and the step.
This ensures behaviour is consistent regardless of the worker implementation.

## Broker and worker processes

In a production setup the **broker** and the **worker** are usually
separate processes. The broker acts as a long running server that stores
workflow schemas, decides which step is ready next and records results.
Workers are clients that keep the actual `Workflow` objects with all of
their policies. A worker contacts the broker to fetch a step assignment,
executes it and then reports the outcome back.

### Starting a broker (server side)

```python
from fuseline.broker import MemoryBroker

# In a real deployment this broker would be exposed via HTTP
BROKER = MemoryBroker()
```

### Running a worker (client side)

```python
from fuseline.engines import ProcessEngine
from my_workflow import rag_workflow  # contains custom policies

engine = ProcessEngine(BROKER, [rag_workflow])
engine.work()
```

The worker registers the workflow schema with the broker and then enters a
loop where it repeatedly calls ``get_step`` and ``report_step``.  Policies
attached to the workflow or to individual steps are automatically applied
by :class:`ProcessEngine` when the step runs.

### Dispatching a workflow run

```python
from my_workflow import rag_workflow

instance = BROKER.dispatch_workflow(rag_workflow.to_schema(), {
    "query": "How does Fuseline work?",
})
```

The broker enqueues the starting steps and the worker picks them up.

## Example: RAG worker with retries and timeouts

Below is a simplified example of building an AI agent that retrieves
documents and then generates an answer.  The retrieval step has a timeout
and the generation step retries on failure.  The code is executed by the
worker process while the broker merely coordinates step order.

```python
from fuseline import Step, Workflow
from fuseline.policies import StepTimeoutPolicy, RetryPolicy

class RetrieveDocs(Step):
    def run_step(self, query: str) -> list[str]:
        # fetch documents from a vector store
        return search_vector_store(query)

class GenerateAnswer(Step):
    def run_step(self, docs: list[str], query: str) -> str:
        return call_llm(query, docs)

retrieve = RetrieveDocs(policies=[StepTimeoutPolicy(5.0)])
answer = GenerateAnswer(policies=[RetryPolicy(max_retries=2, wait=1)])
retrieve.next(answer)

rag_workflow = Workflow(outputs=[answer])

engine = ProcessEngine(BROKER, [rag_workflow])
engine.work()
```

The policies modify how each step executes: ``RetrieveDocs`` will abort
if it takes longer than five seconds, and ``GenerateAnswer`` will retry up
to two times if an exception is raised.
