---
title: "PostgresRuntimeStorage"
---

`PostgresRuntimeStorage` persists runtime state in PostgreSQL. The class reads
its connection string from the `DATABASE_URL` environment variable by default and
supports simple schema migrations so future Fuseline versions can upgrade the
database structure automatically.

``psycopg`` must be installed to use this backend. The provided Dockerfile
includes ``psycopg[binary]`` so the HTTP broker works out of the box.

```python
from fuseline.broker.storage import PostgresRuntimeStorage

store = PostgresRuntimeStorage()  # uses DATABASE_URL
```

When instantiated it checks a `fuseline_meta` table to determine the current
schema version. Missing migrations are applied sequentially until the database
reaches the latest version. Migrations are built into the library and run
whenever the broker or worker starts.

This storage backend is used by `PostgresBroker` and the example HTTP server.
```
