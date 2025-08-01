# Workflow Examples

This directory contains small scripts that demonstrate how to build and run
workflows using the lightweight interface provided by ``fuseline``.

To run an example, execute it with Python. For instance:

```bash
python step_workflow.py
```

## step_workflow.py

Builds a two step workflow using ``Step`` and ``Workflow`` where each step just
prints a message.

## async_step_workflow.py

Demonstrates the asynchronous workflow API using ``AsyncStep`` and ``AsyncWorkflow``.

## typed_task_workflow.py

Shows how steps can declare dependencies on each other using ``Depends`` and ``Computed``.

## async_typed_task_workflow.py

Asynchronous variant of the typed workflow example using ``AsyncStep`` and ``AsyncWorkflow``.

## combined_workflow.py

Mixes typed task dependencies with manual ``>>`` chaining to build a hybrid workflow.

## math_workflow.py

Demonstrates a small workflow accepting three parameters ``a``, ``b`` and ``c``. Two
tasks compute ``a + b`` and then multiply that result by ``c`` before a final task
prints the outcome.

## async_math_workflow.py

Asynchronous version of ``math_workflow.py`` showing the same logic executed with
``AsyncStep`` and ``AsyncWorkflow``.


## parallel_math_workflow.py

Expands the math example by sending the sum into two separate multiply tasks
that multiply by ``2`` and ``3``. A final task prints both results. The
workflow is executed with ``PoolEngine(2)`` to run the branches in parallel.

## async_parallel_math_workflow.py

Asynchronous version of ``parallel_math_workflow.py`` using ``AsyncStep`` and
``AsyncWorkflow``.

## conditional_workflow.py

Illustrates branching based on the return value of a step. The first task
chooses between ``"default"`` and ``"skip"`` paths, showing how to name actions
and wire steps for each option.

## export_workflow.py

Builds a fork-join workflow similar to ``parallel_math_workflow.py`` and then
exports the graph structure to ``export_workflow.yaml`` using
``Workflow.export``.

The exported YAML describes each step with its class name, successors and
dependencies.  ``successors`` is a mapping from an *action* name to a list of
steps executed when that action is returned from the step.  When a step only
has one path forward the action name defaults to ``"default"``.

## trace_workflow.py

Runs a simple workflow while recording the order of executed steps to
``trace_workflow.trace`` using the ``trace`` argument on ``Workflow``.

## policy_workflow.py

Demonstrates attaching a ``RetryPolicy`` to a step.

## HTTP broker

Run a production-ready broker with Robyn and Postgres using the built-in
module:

```bash
python -m fuseline.broker.http
```

See `../docker/docker-compose.yml` for a runnable setup that also
includes a worker container.

## worker_package

Demonstrates creating a standalone package containing a workflow. The
package can be installed from a git repository and run with the Fuseline
worker CLI:

```bash
cd worker_package
uv pip install -e .
BROKER_URL=http://localhost:8000 \
    python -m fuseline.worker my_workflow:workflow
```
