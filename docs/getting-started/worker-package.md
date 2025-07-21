---
title: "Packaging Workflows"
---

This page walks through creating a standalone git repository that defines a
workflow and runs it using Fuseline's built-in worker.

## 1. Create the repository

Start a new project and add a `pyproject.toml` using Poetry. The only
runtime dependency is `fuseline`:

```toml
[tool.poetry]
name = "my-workflow"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.11"
fuseline = "*"
```

Install the package in editable mode so the worker can import it:

```bash
poetry install
```

## 2. Implement the workflow

Inside the package create a module with a `Workflow` object. Any policies
should be attached here.

```python
from fuseline import Step, Workflow
from fuseline.workflow.policies import RetryPolicy

class Hello(Step):
    def run_step(self) -> None:
        print("hello")

hello = Hello(policies=[RetryPolicy(3)])
workflow = Workflow(outputs=[hello])
```

Commit the repository to GitHub, GitLab or Bitbucket.

## 3. Run the worker

Clone the repository wherever you want to run workers and install the
package with Poetry or `uv`:

```bash
uv pip install -e .
```

Then launch the worker by pointing the Fuseline CLI at the workflow
object. Set `BROKER_URL` to the broker address and optionally
`WORKER_PROCESSES` to spawn multiple workers.

```bash
BROKER_URL=http://localhost:8000 \
    python -m fuseline.worker my_workflow:workflow
```

The worker loads the installed package, registers the workflow with the
broker and begins processing assignments.
