<div align="center">

# fuseline

![Static Badge](https://img.shields.io/badge/Python-%3E%3D3.10-blue?logo=python&logoColor=white)
[![Stable Version](https://img.shields.io/pypi/v/fuseline?color=blue)](https://pypi.org/project/fuseline/)
[![stability-beta](https://img.shields.io/badge/stability-beta-33bbff.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#beta)
[![Maintainability](https://api.codeclimate.com/v1/badges/ffcc038906c2c7e2274f/maintainability)](https://codeclimate.com/github/jsam/fuseline/maintainability)
[![Python tests](https://github.com/jsam/fuseline/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/jsam/fuseline/actions/workflows/python-tests.yml)
[![Test Coverage](https://api.codeclimate.com/v1/badges/ffcc038906c2c7e2274f/test_coverage)](https://codeclimate.com/github/jsam/fuseline/test_coverage)
</div>

Fuseline is an **AI agents framework with batteries included**. Think of it as
what Django is for web developers, but for building intelligent agents.

## Documentation

The project documentation uses [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).
First install the development extras:

```bash
pip install -e .[dev]
```

This will install `mkdocs-material`, `mkdocstrings[python]` and
`pymdown-extensions`. The docs use `pymdownx.highlight` with the
GitHub Pygments style so Python snippets are rendered
with proper syntax highlighting in both light and dark mode.

Then start the preview server:

```bash
mkdocs serve
```

GitHub Pages builds the docs from the `gh-pages` branch automatically.
The Material theme provides a search box, workspace tabs for
**Getting Started**, **Concepts & Features**, and **API Reference**.
Code blocks are highlighted using Pygments in the GitHub style and a
light/dark palette toggle.
## Features

| Feature | Description |
|---------|-------------|
| **Steps and Tasks** | `Step` provides basic lifecycle hooks while `Task` adds typed dependencies and retry support |
| **Workflow orchestration** | Chain steps using `>>` or dependency injection and run them with `Workflow` |
| **Typed dependencies** | Pass values between tasks using `Depends` and `Computed` |
| **Asynchronous tasks** | Use `AsyncTask` and `AsyncWorkflow` for async execution |
| **Batch workflows** | `BatchTask` and `BatchWorkflow` run tasks for multiple parameter sets |
| **Parallel execution** | `PoolEngine` executes independent branches concurrently |
| **Conditional dependencies** | Attach `Condition` functions to `Depends` for branch logic |
| **Retries with backoff** | Tasks accept `max_retries` and `wait` to retry on failure |
| **Workflow export** | Serialize graphs to YAML with `Workflow.export` and `YamlExporter` |
| **Tracing** | Record execution events using `FileTracer` |
| **Runtime storage** | Persist workflow state so multiple workers can resume runs |
| **Function workflows** | Wrap callables with `FunctionTask` or use `workflow_from_functions` |
| **Branching actions** | Steps can return action names to select successor steps |
| **Fail-fast policy** | Downstream steps are cancelled when a dependency fails |
| **AND/OR joins** | Support joining branches after all or any parent steps finish |

## Roadmap

| Missing Feature | Importance | Description |
|-----------------|------------|-------------|
| **Web UI and monitoring** | High | Visual dashboard to inspect runs and logs, similar to Airflow or Prefect |
| **Persistent storage** | High | Database-backed state to resume workflows after interruption |
| **Distributed executors** | High | Native support for Kubernetes, Dask or Celery clusters |
| **Scheduling** | High | Cron-like triggers and recurring workflow runs |
| **Step caching / resume** | High | Avoid re-executing completed steps across runs |
| **Artifact management** | Medium | Built‑in integration with object stores and artifact tracking |
| **Dynamic parameter mapping** | Medium | Generate task instances from lists or grids of values |
| **Command line tools** | Medium | CLI for creating, running and inspecting workflows |
| **Data lineage and metadata** | Medium | Track dataset versions and dependency history |
| **Visual DAG editing** | Low | Drag-and-drop interface for authoring workflows |
| **Multi-language tasks** | Low | Ability to implement steps in languages other than Python |
| **Security & access control** | Low | Authentication and role-based permissions for multi-user deployments |


