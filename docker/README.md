This folder contains Docker configurations for running Fuseline with Postgres.

* ``Dockerfile.broker`` builds the broker image and installs the optional
  ``robyn`` and ``psycopg`` packages so the HTTP broker can connect to
  Postgres.
* ``Dockerfile.worker`` builds a simple worker image that connects to the broker
  using ``HttpBrokerClient``.
* ``docker-compose.yml`` runs Postgres using the ``pgvector/pgvector:pg16``
  image, the broker and a worker connected to it.

Run ``docker compose up --build`` inside this directory to start all
services.
