from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fuseline.core.abc import EngineAPI, NetworkAPI
from fuseline.core.nodes import DataNode, GearNode, InvalidGraph, OutputNode


class SerialEngine(EngineAPI):
    """Serial engine executor."""

    def __init__(self) -> None:
        """Serial engine constructor."""
        self._network: Optional[NetworkAPI] = None

    def _submit_next(self) -> bool:
        """Submit next batch of jobs to the pool."""
        if self._network is None:
            raise ValueError

        computed: Dict[GearNode, Any] = {}

        data_node: OutputNode
        for data_node in self._network.compute_next():

            predeccesors: List[GearNode] = list(self._network.graph.predecessors(data_node))  # type: ignore
            if len(predeccesors) != 1:
                raise InvalidGraph(f"found a data node produced by multiple gears: {predeccesors}", gears=predeccesors)

            gear = predeccesors[0]
            result = gear(gear.input_values)

            computed[gear] = result
            data_node.set_value(result)

        return bool(computed)

    def setup(self) -> None:
        """Prepare the given computation for executor."""
        pass

    def teardown(self) -> None:
        """Engine cleanup phase."""
        pass

    def is_ready(self) -> bool:
        """Check if engine is ready for computation."""
        return True

    def execute(self, network: NetworkAPI, **kwargs: Any) -> NetworkAPI:
        """Runs the computational network and returns the result object."""
        if network is None:
            raise ValueError("cannot execute empty network")

        self._network = network
        self._network.set_input(kwargs)

        while self._submit_next():
            pass

        return self._network


class PoolEngine(EngineAPI):
    """Pool engine executor."""

    def __init__(self, max_workers: int = 4) -> None:
        """Pool engine constructor."""
        self._network: Optional[NetworkAPI] = None
        self._executor: Optional[ProcessPoolExecutor] = None
        self._max_workers = max_workers

    def _submit_next(self) -> Dict[str, Any]:
        """Submit next batch of jobs to the pool."""
        if self._network is None:
            raise ValueError("computational graph not found")

        if self._executor is None:
            raise ValueError("engine not ready")

        results: Dict[str, Any] = {}
        futures: Dict[Future[Any], Tuple[DataNode, GearNode]] = {}

        data_node: DataNode
        gear_node: GearNode
        for data_node in self._network.compute_next():
            predeccesors: List[GearNode] = list(self._network.graph.predecessors(data_node))  # type: ignore
            if len(predeccesors) != 1:
                raise InvalidGraph(f"found a data node produced by multiple gears: {predeccesors}", gears=predeccesors)

            gear_node = predeccesors[0]
            future = self._executor.submit(gear_node, kwargs=gear_node.input_values)
            futures[future] = (data_node, gear_node)

        for future in as_completed(futures):
            result_tpl: Tuple[DataNode, GearNode] = futures[future]
            data_node, gear_node = result_tpl
            value = future.result()

            data_node.set_value(value)
            results[gear_node.name] = value

        return results

    def is_ready(self) -> bool:
        """Check if engine is ready for computation."""
        return self._executor is not None

    def setup(self) -> None:
        """Prepare the given computation for executor."""
        self._executor = ProcessPoolExecutor(max_workers=self._max_workers)

    def execute(self, network: NetworkAPI, **kwargs: Any) -> NetworkAPI:
        """Runs the computational network and returns the result object."""
        if network is None:
            raise ValueError("cannot execute empty network")

        self._network = network
        self._network.set_input(kwargs)

        while self._submit_next():
            pass

        return self._network

    def register(self) -> None:
        """Registers the computational network with external executor."""
        raise NotImplementedError

    def teardown(self) -> None:
        """Cleanup phase."""
        if self._executor is None:
            raise ValueError("engine not running")

        self._executor.shutdown(wait=True)


# def dask_install(requirements: List[str]) -> None:
#     """Install depedencies on cluster workers."""
#     import os

#     aligned: str = " ".join(requirements)
#     os.system(f"pip install -U setuptools {aligned}")


# def dask_clean() -> None:
#     """Cleanup previously deployed eggs."""
#     import os

#     os.system("find . -type f -name '*.egg' -delete")


class DaskEngine(EngineAPI):
    """Dask engine executor."""

    def __init__(self, address: str, requirements: List[str], egg_path: Path, **config: Any) -> None:
        """Dask engine constructor."""
        from dask.distributed import Client, as_completed  # type: ignore[import]

        self.as_completed = as_completed
        self._executor: Optional[Client] = None
        self._network: Optional[NetworkAPI] = None

        self._address = address
        self._requirements = requirements

        self._egg_path = egg_path
        self._config: Dict[str, Any] = config

        self.dask_install = lambda os, aligned: os.system(f"pip install -U {aligned}")  # type: ignore
        self.dask_clean = lambda os: os.system("find . -type f -name '*.egg' -delete")  # type: ignore
        self.dask_update = lambda os: os.system("pip install -U setuptools cloudpickle blosc lz4 msgpack numpy")  # type: ignore

    def _submit_next(self) -> bool:
        """Submit next batch of jobs to the pool."""
        if self._network is None:
            raise ValueError("network not found")

        if self._executor is None:
            raise ValueError("engine not found")

        futures = {}
        gear: GearNode
        data_node: OutputNode

        for data_node in self._network.compute_next():
            predeccesors: List[GearNode] = list(self._network.graph.predecessors(data_node))  # type: ignore
            if len(predeccesors) != 1:
                raise InvalidGraph(f"found a data node produced by multiple gears: {predeccesors}", gears=predeccesors)

            gear = predeccesors[0]
            data_node.set_value(gear(gear.input_values))

            future = self._executor.submit(gear, kwargs=gear.input_values)  # type: ignore
            futures[future] = (data_node, gear)

        if not futures:
            return False

        for future in self.as_completed(futures):  # type: ignore
            data_node, gear = futures[future]  # type: ignore
            data_node.set_value(future.result())  # type: ignore

        return True

    def setup(self) -> None:
        """Prepare the given computation for executor."""
        import importlib

        from dask.distributed import Client, PipInstall
        from distributed.diagnostics.plugin import UploadFile  # type: ignore[import]

        self._executor = Client(self._address, timeout=30)
        install_deps = PipInstall(packages=self._requirements, pip_options=["--upgrade"])
        upload_egg = UploadFile(self._egg_path)

        self._executor.run(lambda ilib: ilib.invalidate_caches(), importlib)  # type: ignore

        self._executor.register_worker_plugin(install_deps, "install_deps")  # type: ignore
        self._executor.register_worker_plugin(upload_egg, "upload_egg")  # type: ignore

        self._executor.wait_for_workers(timeout=10)  # type: ignore
        _ = self._executor.get_versions(check=True)  # type: ignore

    def is_ready(self) -> bool:
        """Check if engine is ready for computation."""
        return self._executor is not None

    def execute(self, network: NetworkAPI, **kwargs: Any) -> NetworkAPI:
        """Runs the computational network and returns the result object."""
        if network is None:
            raise ValueError("cannot execute empty network")

        if self._executor is None:
            raise ValueError("engine is not ready")

        self._network = network
        self._network.set_input(kwargs)

        while self._submit_next():
            pass

        return self._network

    def teardown(self) -> None:
        """Enging cleanup phase."""
        if self._executor is None:
            raise ValueError("engine not running")

        self._executor.close()  # type: ignore

        # NOTE: This will kill the entire grid.
        # self._executor.shutdown()
