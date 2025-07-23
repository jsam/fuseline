from __future__ import annotations

import importlib
import logging
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable

from ..broker import RepositoryInfo
from ..broker.clients import BrokerClient, HttpBrokerClient
from ..workflow import Workflow
from .process import ProcessEngine


def _load_workflow(spec: str) -> Workflow:
    module_name, attr = spec.split(":", 1)
    mod = importlib.import_module(module_name)
    wf = getattr(mod, attr)
    if not isinstance(wf, Workflow):
        raise TypeError(f"{spec} is not a Workflow")
    return wf


def _clone_repository(info: RepositoryInfo) -> str:
    path = tempfile.mkdtemp(prefix="fuseline_repo_")
    url = info.url
    token = info.credentials.get("token")
    user = info.credentials.get("username", "")
    if token and url.startswith("https://"):
        prefix = "https://"
        url = f"https://{user}:{token}@" + url[len(prefix) :]
    git_exe = shutil.which("git")
    if not git_exe:
        raise RuntimeError("git executable not found")
    subprocess.run([git_exe, "clone", "--", url, path], check=True)  # noqa: S603
    sys.path.insert(0, path)
    return path


def _run_once(client: BrokerClient, specs: Iterable[str]) -> None:
    workflows: list[Workflow] = []
    for spec in specs:
        if ":" in spec:
            workflows.append(_load_workflow(spec))
        else:
            info = client.get_repository(spec)
            if info is None:
                raise RuntimeError(f"unknown repository {spec}")
            _clone_repository(info)
            for wf_spec in info.workflows:
                workflows.append(_load_workflow(wf_spec))
    engine = ProcessEngine(client, workflows)
    engine.work(block=True)


def run_from_env(specs: list[str]) -> None:
    base_url = os.environ.get("BROKER_URL", "http://localhost:8000")
    processes = int(os.environ.get("WORKER_PROCESSES", "1"))
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")

    def target() -> None:
        client = HttpBrokerClient(base_url)
        _run_once(client, specs)

    if processes <= 1:
        logging.info("starting single worker process")
        target()
        return

    procs = [mp.Process(target=target) for _ in range(processes)]
    for p in procs:
        p.start()
        logging.info("started worker process %s", p.pid)
    for p in procs:
        p.join()


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python -m fuseline.worker repo-name | module:workflow [more...]",
            file=sys.stderr,
        )
        raise SystemExit(1)
    run_from_env(sys.argv[1:])


if __name__ == "__main__":  # pragma: no cover - manual
    main()
