---
title: "Implementing Workers"
---

Workers are long running processes that execute workflow steps. They
hold the actual :class:`Workflow` objects (including any attached
policies) and communicate with a broker via a :class:`BrokerClient`.

## Using ``ProcessEngine``

``ProcessEngine`` already implements the worker loop. It registers the
workflow schemas, fetches step assignments and reports results back to
the broker. A typical worker looks like this:

```python
from fuseline.broker import MemoryBroker
from fuseline.clients import LocalBrokerClient
from fuseline.engines import ProcessEngine
from my_workflows import rag_workflow

broker = MemoryBroker()
client = LocalBrokerClient(broker)
engine = ProcessEngine(client, [rag_workflow])
engine.work()
```

Every time ``engine.work()`` is called the worker asks the broker for the
next step, executes it and then reports a ``StepReport``. Attached
policies are executed automatically by ``ProcessEngine``.

## Writing a custom worker

When implementing your own worker you still use a ``BrokerClient`` to
communicate with the broker. The following skeleton shows the core loop:

```python
client = LocalBrokerClient(broker)
worker_id = client.register_worker([workflow.to_schema()])

while True:
    assignment = client.get_step(worker_id)
    if assignment is None:
        break

    step = step_lookup[assignment.step_name]
    shared = {step_lookup[name]: val
              for name, val in assignment.payload.get("results", {}).items()}
    workflow.params.update(assignment.payload.get("workflow_inputs", {}))
    result = workflow._execute_step(step, shared)

    client.report_step(worker_id, StepReport(
        workflow_id=assignment.workflow_id,
        instance_id=assignment.instance_id,
        step_name=assignment.step_name,
        state=step.state,
        result=result,
    ))
```

``workflow._execute_step`` applies all ``WorkflowPolicy`` and
``StepPolicy`` objects so custom workers behave the same way as the
provided engine. Workers may also send heartbeats using
``BrokerClient.keep_alive``.

## Multiple workers

Several workers can connect to the same broker. Each one retrieves the
next available step and processes it independently. The broker ensures a
step is only assigned to one worker at a time.
