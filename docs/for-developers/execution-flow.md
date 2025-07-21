---
title: "Execution flow"
---

This page outlines how Fuseline schedules and executes tasks.

### Queuing tasks

When a workflow is **dispatched** or **run** with a runtime store,
all starting steps are placed into the store's queue.  The
`dispatch()` method performs this without executing any work so
workers can pick up tasks later.

Steps are identified by name and enqueued in dependency order.  The
`RuntimeStorage` interface exposes `enqueue()` and `fetch_next()`
methods so workers can retrieve ready steps.

The queue itself lives inside the configured `RuntimeStorage`
implementation.  The storage backend keeps a list of step names and
their states.  When dispatching, the workflow
creates an entry for each step and immediately enqueues those without
predecessors.  The remaining steps wait until their dependencies have
finished.

### Determining successors

Each step keeps a list of successor steps.  After a step finishes,
the workflow checks each successor's predecessors.  When all
predecessors have succeeded (or been skipped), the successor becomes
ready and is enqueued.  Branching actions may return a string to
select which edge to follow.

Each successor is only queued once all of its predecessors have a final
state of `SUCCEEDED` or `SKIPPED`.  Steps that fail will cause
downstream steps to be marked `CANCELLED` unless they belong to an OR
group.  Branching actions can return a custom string matching one of
the successor keys to choose the next edge.

### Executing steps

Workers load steps from the broker and run them using either
`ProcessEngine` or another execution engine.  Step results are written
back so the broker can decide which successors to enqueue.  In a real
deployment the broker runs in its own process and workers communicate
over the :class:`BrokerClient` interface.

`ProcessEngine` drives this loop by repeatedly asking the broker for the
next step, executing it and reporting the result.  The broker examines
the workflow definition to determine which successors become ready.  The
synchronous `PoolEngine` behaves similarly but operates entirely
in‑memory without persistent state.

```python
from fuseline import Workflow
from fuseline.broker import MemoryBroker
from fuseline.broker.clients import LocalBrokerClient, HttpBrokerClient
from fuseline.worker import ProcessEngine

broker = MemoryBroker()
client = LocalBrokerClient(broker)  # HttpBrokerClient("http://localhost:8000") for real deployments
instance = client.dispatch_workflow(workflow.to_schema())

worker = ProcessEngine(client, [workflow])
worker.work()
```

This code uses ``MemoryBroker`` for simplicity.  In a real deployment the
worker would call a broker service over the network via a
``BrokerClient`` implementation.

Multiple processes can create their own `ProcessEngine` instances
pointing at the same broker to distribute work.  Each worker grabs the
next available step and the broker handles queuing of successors.  See
[Implementing brokers](brokers.md) and [Implementing workers](workers.md)
for more about building these components.
