# Workflow Examples

This directory contains small scripts that demonstrate how to build and run
workflows using the lightweight interface provided by ``fuseline``.

To run an example, execute it with Python. For instance:

```bash
python step_workflow.py
```

## step_workflow.py

Builds a two step workflow using ``Task`` and ``Workflow`` where each step just
prints a message.

## async_step_workflow.py

Demonstrates the asynchronous workflow API using ``AsyncTask`` and ``AsyncWorkflow``.

