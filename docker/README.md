This folder contains Docker configurations for running Fuseline with Postgres.

* ``Dockerfile.broker`` builds the broker image and installs ``robyn`` and
  ``psycopg`` along with ``curl`` which the container's health check uses.
* ``Dockerfile.worker`` installs ``git`` so repositories can be cloned and
  builds a simple worker image that connects to the broker using
  ``HttpBrokerClient``.
* ``docker-compose.yml`` runs Postgres using the ``pgvector/pgvector:pg16``
  image, the broker and a worker connected to it. Health checks ensure the
  database starts first, then the broker, and finally the worker.

Run ``docker compose up --build`` inside this directory to start all
services.
