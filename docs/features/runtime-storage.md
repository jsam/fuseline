---
title: "Runtime storage"
---

Persist workflow state using a `RuntimeStorage` backend so runs can be resumed or executed by multiple workers.

You can run a workflow in a single process while persisting state, or dispatch tasks to a storage backend and have separate workers process them.

```python
from fuseline import Workflow
from fuseline.broker import MemoryBroker
from fuseline.engines import ProcessEngine

broker = MemoryBroker()
wf = Workflow(outputs=[...])

# enqueue starting steps and store state
instance = broker.dispatch_workflow(wf)

# workers consume queued steps
worker = ProcessEngine(broker, [wf])
worker.work()
```

The store keeps track of workflow inputs and each step's output so any
worker can pick up where another left off. The broker determines which
steps become ready based on the stored workflow definition.
