---
title: "Docker Setup"
---

Fuseline provides Dockerfiles for running the broker and a basic worker.
The ``docker`` directory contains:

* ``Dockerfile.broker`` – builds an image that starts the Robyn broker
  with ``PostgresBroker``. The Dockerfile installs ``robyn`` and
  ``psycopg[binary]`` so the server can run against Postgres.
* ``Dockerfile.worker`` – builds a worker image that connects to the
  broker.
* ``docker-compose.yml`` – launches Postgres with the ``pgvector``
  extension using the ``pgvector/pgvector:pg16`` image, the broker and a demo
  worker.

From the ``docker`` directory run:

```bash
docker compose up --build
```

The broker becomes available on ``http://localhost:8000``. Swagger
documentation is served at ``/docs``.
