---
title: "Runtime storage"
---

Persist workflow state using a `RuntimeStorage` backend so runs can be resumed or executed by multiple workers.

You can run a workflow in a single process while persisting state, or dispatch tasks to a storage backend and have separate workers process them.

```python
from fuseline import Workflow, MemoryRuntimeStorage, ProcessEngine

store = MemoryRuntimeStorage()
wf = Workflow(outputs=[...])

# enqueue starting steps and store state
instance = wf.dispatch(runtime_store=store)

# workers consume queued steps
worker = ProcessEngine(wf, store)
worker.work(instance)
```
