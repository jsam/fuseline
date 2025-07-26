---
title: "Broker API"
---

The broker stores workflow definitions and tracks running instances.
Workers communicate with it over HTTP using a small set of endpoints.
Each endpoint uses typed dataclasses from ``robyn.types`` for request
payloads and responses so the API surface is self-documenting.  Steps
handed to a worker are represented by a `StepAssignment` object
containing the workflow identifiers, the payload needed to run the task
and a timeout deadline.

## Repository endpoints

### Register repository

```
POST /repository/register
```

Store the location and credentials for a repository containing workflow
implementations. The payload must include a unique ``name`` used by
workers, the repository ``url``, a list of ``workflows`` specified as
``module:object`` strings and any ``credentials`` needed to clone the
repository.

### Get repository info

```
GET /repository?name=<repo>
```

Workers call this endpoint when starting up. The broker returns the URL
and credentials for the requested repository along with the workflow
objects to load.

## Worker endpoints

### Register worker

```
POST /worker/register
```

A worker sends the full workflow schemas it can execute.  Each schema has
a name and a version.  If the broker already knows a workflow under the
same name and version but the definition differs, the registration is
rejected.  A successful call returns a unique worker ID.

## Workflow endpoints

### Get next step

```
GET /workflow/step
```

The broker returns the next step for the worker including the workflow
inputs and dependency results.  It also records when the task was
handed out and when it should expire.  The response contains the
workflow ID, instance ID, step name, parameters and timeout metadata.
If no step is available the request yields an HTTP ``204`` response
with an empty body.

### Report step result

```
POST /workflow/step
```

Workers send a ``StepReport`` object containing the step state and any
returned value. The broker stores this output so it can become the input
for downstream steps and then decides which successors are ready to run
next.

### Worker keep‑alive

```
POST /worker/keep-alive
```

Periodic heartbeats let the broker know a worker is still active.
The in-memory broker removes workers that fail to send a heartbeat
before the timeout elapses.

### Broker status

```
GET /status
```

Returns ``{"status": "ok"}`` if the broker is running.

### List workers

```
GET /workers
```

Return detailed information about each connected worker. The response looks like
this:

```json
[
  {
    "worker_id": "1",
    "connected_at": 1690000000.0,
    "last_seen": 1690000100.0,
    "last_task": {
      "workflow_id": "wf",
      "instance_id": "abc",
      "step_name": "build",
      "success": true
    }
  }
]
```

``last_task`` is ``null`` if the worker has not completed any steps yet.

### List workflows

```
GET /workflows
```

Return all workflow specifications registered via repositories. Each entry
includes the repository name and the ``module:object`` string identifying the
workflow.

### Swagger documentation

The built-in HTTP broker exposes an OpenAPI specification at
``/openapi.json`` and a Swagger UI under ``/docs`` when running
``python -m fuseline.broker.http``. Visit the ``/docs`` endpoint in your
browser to explore and try the API.  Endpoints are grouped by resource
(``repository``, ``worker``, ``workflow`` and ``system``) so related APIs
appear together rather than being sorted by HTTP verb.

These endpoints map directly onto the `RuntimeStorage` interface used by
`ProcessEngine`. Implementations can store data in a database, message
queue or any other system.
