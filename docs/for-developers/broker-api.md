---
title: "Broker API"
---

The broker stores workflow definitions and tracks running instances.
Workers communicate with it over HTTP (or another transport) using a few
endpoints.  Each step handed to a worker is represented by a
`StepAssignment` object containing the workflow identifiers, the payload
needed to run the task and a timeout deadline.

### Registering workflow repositories

```
POST /repository/register
```

Store the location and credentials for a repository containing workflow
implementations. The payload must include a unique ``name`` used by
workers, the repository ``url``, a list of ``workflows`` specified as
``module:object`` strings and any ``credentials`` needed to clone the
repository.

### Fetching repository info

```
GET /repository?name=<repo>
```

Workers call this endpoint when starting up. The broker returns the URL
and credentials for the requested repository along with the workflow
objects to load.

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
If no step is available the request yields an HTTP ``204`` response
with an empty body.

Older broker versions returned a JSON object like ``{"status_code": 204}``.  The
``HttpBrokerClient`` still accepts this legacy format for compatibility but new
implementations should rely on the proper HTTP status code.

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

### Swagger documentation

The built-in HTTP broker exposes an OpenAPI specification at
``/openapi.json`` and a Swagger UI under ``/docs`` when running
``python -m fuseline.broker.http``. Visit the ``/docs`` endpoint in your
browser to explore and try the API.

These endpoints map directly onto the `RuntimeStorage` interface used by
`ProcessEngine`. Implementations can store data in a database, message
queue or any other system.
