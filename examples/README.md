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

## typed_task_workflow.py

Shows how tasks can declare dependencies on each other using ``Depends`` and ``Computed``.

## async_typed_task_workflow.py

Asynchronous variant of the typed workflow example using ``AsyncTask`` and ``AsyncWorkflow``.

## combined_workflow.py

Mixes typed task dependencies with manual ``>>`` chaining to build a hybrid workflow.

