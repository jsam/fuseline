---
title: "Broker API"
---

The broker acts as the persistence layer for running workflows. Workers
communicate with it over HTTP (or another transport) using four
endpoints.

### Worker registration

```
POST /worker/register
```

A worker sends a list of workflow IDs it can execute and receives a
unique worker ID in response.

### Fetching work

```
GET /workflow/step
```

The broker returns the next step for the worker as a tuple of workflow
ID, instance ID and step name. If no step is available the response is
empty.

### Reporting progress

```
POST /workflow/step
```

Workers report step completion, failure or progress by posting the step
state back to the broker.  The payload may include a list of
`next_steps` to enqueue.  This allows the worker to control progression
without the broker needing the workflow definition.

### Keep alive

```
POST /worker/keep-alive
```

Periodic heartbeats let the broker know a worker is still active.

These endpoints map directly onto the `RuntimeStorage` interface used by
`ProcessEngine`. Implementations can store data in a database, message
queue or any other system.
