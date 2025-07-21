---
title: "Broker API"
---

The broker stores workflow definitions and tracks running instances.
Workers communicate with it over HTTP (or another transport) using four
endpoints.  Each step handed to a worker is represented by a
`StepAssignment` object containing the workflow identifiers, the payload
needed to run the task and a timeout deadline.

### Worker registration

```
POST /worker/register
```

A worker sends the full workflow schemas it can execute.  Each schema has
a name and a version.  If the broker already knows a workflow under the
same name and version but the definition differs, the registration is
rejected.  A successful call returns a unique worker ID.

### Fetching work

```
GET /workflow/step
```

The broker returns the next step for the worker including the workflow
inputs and dependency results.  It also records when the task was
handed out and when it should expire.  The response contains the
workflow ID, instance ID, step name, parameters and timeout metadata.
If no step is available the response is empty.

### Reporting progress

```
POST /workflow/step
```

Workers send a ``StepReport`` object containing the step state and any
returned value. The broker stores this output so it can become the input
for downstream steps and then decides which successors are ready to run
next.

### Keep alive

```
POST /worker/keep-alive
```

Periodic heartbeats let the broker know a worker is still active.
The in-memory broker removes workers that fail to send a heartbeat
before the timeout elapses.

These endpoints map directly onto the `RuntimeStorage` interface used by
`ProcessEngine`. Implementations can store data in a database, message
queue or any other system.
