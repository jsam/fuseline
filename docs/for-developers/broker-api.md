---
title: "Broker API"
---

The broker stores workflow definitions and tracks running instances.
Workers communicate with it over HTTP (or another transport) using four
endpoints.

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
inputs and the results of any dependencies.  The response contains the
workflow ID, instance ID, step name and a dictionary of parameters.  If
no step is available the response is empty.

### Reporting progress

```
POST /workflow/step
```

Workers report step completion, failure or progress by posting the step
state and result back to the broker.  The broker then determines which
successor steps become ready based on the stored workflow definition.

### Keep alive

```
POST /worker/keep-alive
```

Periodic heartbeats let the broker know a worker is still active.

These endpoints map directly onto the `RuntimeStorage` interface used by
`ProcessEngine`. Implementations can store data in a database, message
queue or any other system.
