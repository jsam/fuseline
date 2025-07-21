from __future__ import annotations

import importlib
import multiprocessing as mp
import os
import sys
from typing import Iterable

from .process import ProcessEngine
from ..broker.clients import HttpBrokerClient, BrokerClient
from ..workflow import Workflow


def _load_workflow(spec: str) -> Workflow:
    module_name, attr = spec.split(":", 1)
    mod = importlib.import_module(module_name)
    wf = getattr(mod, attr)
    if not isinstance(wf, Workflow):
        raise TypeError(f"{spec} is not a Workflow")
    return wf


def _run_once(client: BrokerClient, specs: Iterable[str]) -> None:
    workflows = [_load_workflow(s) for s in specs]
    engine = ProcessEngine(client, workflows)
    engine.work()


def run_from_env(specs: list[str]) -> None:
    base_url = os.environ.get("BROKER_URL", "http://localhost:8000")
    processes = int(os.environ.get("WORKER_PROCESSES", "1"))
    def target() -> None:
        client = HttpBrokerClient(base_url)
        _run_once(client, specs)

    if processes <= 1:
        target()
        return

    procs = [mp.Process(target=target) for _ in range(processes)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m fuseline.worker module:workflow [module:workflow...]", file=sys.stderr)
        raise SystemExit(1)
    run_from_env(sys.argv[1:])


if __name__ == "__main__":  # pragma: no cover - manual
    main()
