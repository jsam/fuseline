---
title: "Docker Setup"
---

Fuseline provides Dockerfiles for running the broker and a basic worker.
The ``docker`` directory contains:

* ``Dockerfile.broker`` – builds an image that starts the Robyn broker
  with ``PostgresBroker``. The Dockerfile installs ``robyn`` and
  ``psycopg[binary]`` along with ``curl`` used by the health check so the
  server can run against Postgres.
* ``Dockerfile.worker`` – builds a worker image that connects to the
  broker. ``git`` is installed so workflow repositories can be cloned.
* ``docker-compose.yml`` – launches Postgres with the ``pgvector``
  extension using the ``pgvector/pgvector:pg16`` image, the broker and a demo
  worker. Health checks coordinate startup so the worker only begins once the
  broker is ready.

From the ``docker`` directory run:

```bash
docker compose up --build
```

The broker becomes available on ``http://localhost:8000``. Swagger
documentation is served at ``/docs``.

``HOST`` and ``PORT`` environment variables control the address and port
used by the broker. The Dockerfile defaults to ``0.0.0.0`` so the service
is reachable from other containers.
