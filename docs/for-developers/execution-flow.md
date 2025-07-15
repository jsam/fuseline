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
implementation.  For `FileRuntimeStorage` this is a JSON file on disk
containing a list of step names.  When dispatching, the workflow
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

### Executing tasks

Workers load tasks from the store and run them using either
`ProcessEngine` or another execution engine.  Task results are kept
in a shared dictionary so later steps can access their dependencies.

`ProcessEngine` drives this loop by repeatedly calling
`fetch_next()` on the store, running the returned step and then storing
its final state.  Successors are checked after each execution and, if
ready, are enqueued for future workers.  The synchronous
`PoolEngine` behaves similarly but operates entirely in‑memory without
persistent state.

```python
from fuseline import Workflow, FileRuntimeStorage
from fuseline.engines import ProcessEngine

store = FileRuntimeStorage("runs")
instance = workflow.dispatch(runtime_store=store)

worker = ProcessEngine(workflow, store)
worker.work(instance)
```

Multiple processes can create their own `ProcessEngine` instances
pointing at the same store to distribute work.  Each worker grabs the
next available step and pushes any newly‑ready steps back to the queue.
