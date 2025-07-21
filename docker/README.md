This folder contains Docker configurations for running Fuseline with Postgres.

* ``Dockerfile.broker`` builds the broker image.
* ``Dockerfile.worker`` builds a simple worker image.
* ``docker-compose.yml`` runs Postgres using the ``pgvector/pgvector:pg16``
  image, the broker and a worker connected to it.

Run ``docker compose up --build`` inside this directory to start all
services.
