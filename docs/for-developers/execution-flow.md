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

### Determining successors

Each step keeps a list of successor steps.  After a step finishes,
the workflow checks each successor's predecessors.  When all
predecessors have succeeded (or been skipped), the successor becomes
ready and is enqueued.  Branching actions may return a string to
select which edge to follow.

### Executing tasks

Workers load tasks from the store and run them using either
`ProcessEngine` or another execution engine.  Task results are kept
in a shared dictionary so later steps can access their dependencies.
