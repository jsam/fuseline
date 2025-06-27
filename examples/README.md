# Workflow Examples

This directory contains small scripts that demonstrate how to build and run
workflows using the lightweight interface provided by `fuseline.workflow`.

To run an example, execute it with Python. For instance:

```bash
python simple_workflow.py
```

## simple_workflow.py

Builds a two step workflow using `Step` and `Workflow` where each step just
prints a message.

## async_workflow.py

Demonstrates the asynchronous workflow API using `AsyncTask` and `AsyncWorkflow`.

## network_workflow.py

Shows how to wrap a `Network` in a `NetworkTask` and execute it as part of a
workflow.
