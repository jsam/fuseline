<div align="center">

# fuseline

![Static Badge](https://img.shields.io/badge/Python-%3E%3D3.10-blue?logo=python&logoColor=white)
[![Stable Version](https://img.shields.io/pypi/v/fuseline?color=blue)](https://pypi.org/project/fuseline/)
[![stability-beta](https://img.shields.io/badge/stability-beta-33bbff.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#beta)
[![Maintainability](https://api.codeclimate.com/v1/badges/ffcc038906c2c7e2274f/maintainability)](https://codeclimate.com/github/jsam/fuseline/maintainability)
[![Python tests](https://github.com/jsam/fuseline/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/jsam/fuseline/actions/workflows/python-tests.yml)
[![Test Coverage](https://api.codeclimate.com/v1/badges/ffcc038906c2c7e2274f/test_coverage)](https://codeclimate.com/github/jsam/fuseline/test_coverage)
</div>

## Documentation

The project documentation is written using [Quarto](https://quarto.org). Run

```bash
quarto preview docs
```

to start a local preview server. The GitHub Pages workflow automatically builds
the docs and publishes them from the `gh-pages` branch.
## Features

| Feature | Description |
|---------|-------------|
| **Tasks and Steps** | Build units of work by subclassing `Task` or `Step` with lifecycle hooks |
| **Workflow orchestration** | Chain steps using `>>` or dependency injection and run them with `Workflow` |
| **Typed dependencies** | Pass values between tasks using `Depends` and `Computed` |
| **Asynchronous tasks** | Use `AsyncTask` and `AsyncWorkflow` for async execution |
| **Batch workflows** | `BatchTask` and `BatchWorkflow` run tasks for multiple parameter sets |
| **Parallel execution** | `ProcessEngine` executes independent branches concurrently |
| **Conditional dependencies** | Attach `Condition` functions to `Depends` for branch logic |
| **Retries with backoff** | Tasks accept `max_retries` and `wait` to retry on failure |
| **Workflow export** | Serialize graphs to YAML with `Workflow.export` and `YamlExporter` |
| **Tracing** | Record execution events using `FileTracer` |
| **Function workflows** | Wrap callables with `FunctionTask` or use `workflow_from_functions` |
| **Branching actions** | Steps can return action names to select successor steps |


