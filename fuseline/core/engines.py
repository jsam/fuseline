from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fuseline.core.abc import EngineAPI, NetworkAPI
from fuseline.core.nodes import DataNode, GearNode, InvalidGraphError, OutputNode
from fuseline.utils.logging import get_logger

# Get the logger
logger = get_logger()


class SerialEngine(EngineAPI):
    """Serial engine executor."""

    def __init__(self) -> None:
        """Serial engine constructor."""
        self._network: Optional[NetworkAPI] = None
        logger.info("SerialEngine initialized")

    def _submit_next(self) -> bool:
        """Submit next batch of jobs to the pool."""
        if self._network is None:
            logger.error("Network not found in SerialEngine")
            raise ValueError

        computed: Dict[GearNode, DataNode] = {}
        nodes = self._network.compute_next()

        for compute_node in nodes:
            logger.debug(f"Executing gear: {compute_node.name}")
            result = compute_node(compute_node.input_values)
            successor: GearNode = next(self._network.graph.successors(compute_node))
            computed[compute_node] = result
            successor.set_value(result)

        return bool(computed)

    def setup(self) -> None:
        """Prepare the given computation for executor."""
        logger.info("Setting up SerialEngine")
        pass

    def teardown(self) -> None:
        """Engine cleanup phase."""
        logger.info("Tearing down SerialEngine")
        pass

    def is_ready(self) -> bool:
        """Check if engine is ready for computation."""
        ready = True
        logger.info(f"SerialEngine ready status: {ready}")
        return ready

    def execute(self, network: NetworkAPI, **kwargs: Any) -> NetworkAPI:
        """Runs the computational network and returns the result object."""
        if network is None:
            logger.error("Cannot execute empty network")
            raise ValueError("cannot execute empty network")

        self._network = network
        self._network.set_input(kwargs)

        logger.info("Starting network execution in SerialEngine")
        while self._submit_next():
            pass
        logger.info("Network execution completed in SerialEngine")

        return self._network


class PoolEngine(EngineAPI):
    """Pool engine executor."""

    def __init__(self, max_workers: int = 4) -> None:
        """Pool engine constructor."""
        self._network: Optional[NetworkAPI] = None
        self._executor: Optional[ProcessPoolExecutor] = None
        self._max_workers = max_workers
        logger.info(f"PoolEngine initialized with max_workers: {max_workers}")

    def _submit_next(self) -> Dict[str, Any]:
        """Submit next batch of jobs to the pool."""
        if self._network is None:
            logger.error("Computational graph not found in PoolEngine")
            raise ValueError("computational graph not found")

        if self._executor is None:
            logger.error("PoolEngine not ready")
            raise ValueError("engine not ready")

        results: Dict[str, Any] = {}
        futures: Dict[Future[Any], Tuple[DataNode, GearNode]] = {}

        data_node: DataNode
        gear_node: GearNode
        for data_node in self._network.compute_next():
            predeccesors: List[GearNode] = list(self._network.graph.predecessors(data_node))  # type: ignore
            if len(predeccesors) != 1:
                logger.error(f"Invalid graph structure: multiple predecessors for data node: {predeccesors}")
                raise InvalidGraphError(
                    f"found a data node produced by multiple gears: {predeccesors}",
                    gears=predeccesors,
                )

            gear_node = predeccesors[0]
            logger.debug(f"Submitting gear for execution: {gear_node.name}")
            future = self._executor.submit(gear_node, kwargs=gear_node.input_values)
            futures[future] = (data_node, gear_node)

        for future in as_completed(futures):
            result_tpl: Tuple[DataNode, GearNode] = futures[future]
            data_node, gear_node = result_tpl
            value = future.result()

            data_node.set_value(value)
            results[gear_node.name] = value
            logger.debug(f"Gear execution completed: {gear_node.name}")

        return results

    def is_ready(self) -> bool:
        """Check if engine is ready for computation."""
        ready = self._executor is not None
        logger.info(f"PoolEngine ready status: {ready}")
        return ready

    def setup(self) -> None:
        """Prepare the given computation for executor."""
        logger.info(f"Setting up PoolEngine with {self._max_workers} workers")
        self._executor = ProcessPoolExecutor(max_workers=self._max_workers)

    def execute(self, network: Optional[NetworkAPI], **kwargs: Any) -> NetworkAPI:
        """Runs the computational network and returns the result object."""
        if network is None:
            logger.error("Cannot execute empty network")
            raise ValueError("cannot execute empty network")

        self._network = network
        self._network.set_input(kwargs)

        logger.info("Starting network execution in PoolEngine")
        while self._submit_next():
            pass
        logger.info("Network execution completed in PoolEngine")

        return self._network

    def register(self) -> None:
        """Registers the computational network with external executor."""
        logger.warning("PoolEngine register method not implemented")
        raise NotImplementedError

    def teardown(self) -> None:
        """Cleanup phase."""
        if self._executor is None:
            logger.error("PoolEngine not running")
            raise ValueError("engine not running")

        logger.info("Tearing down PoolEngine")
        self._executor.shutdown(wait=True)


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

        logger.info(f"DaskEngine initialized with address: {address}")

    def _submit_next(self) -> bool:
        """Submit next batch of jobs to the pool."""
        if self._network is None:
            logger.error("Network not found in DaskEngine")
            raise ValueError("network not found")

        if self._executor is None:
            logger.error("DaskEngine not ready")
            raise ValueError("engine not found")

        futures = {}
        gear: GearNode
        data_node: OutputNode

        for data_node in self._network.compute_next():
            predeccesors: List[GearNode] = list(self._network.graph.predecessors(data_node))  # type: ignore
            if len(predeccesors) != 1:
                logger.error(f"Invalid graph structure: multiple predecessors for data node: {predeccesors}")
                raise InvalidGraphError(
                    f"found a data node produced by multiple gears: {predeccesors}",
                    gears=predeccesors,
                )

            gear = predeccesors[0]
            data_node.set_value(gear(gear.input_values))

            logger.debug(f"Submitting gear for execution: {gear.name}")
            future = self._executor.submit(gear, kwargs=gear.input_values)  # type: ignore
            futures[future] = (data_node, gear)

        if not futures:
            return False

        for future in self.as_completed(futures):  # type: ignore
            data_node, gear = futures[future]  # type: ignore
            data_node.set_value(future.result())  # type: ignore
            logger.debug(f"Gear execution completed: {gear.name}")

        return True

    def setup(self) -> None:
        """Prepare the given computation for executor."""
        import importlib

        from dask.distributed import Client, PipInstall
        from distributed.diagnostics.plugin import UploadFile  # type: ignore[import]

        logger.info(f"Setting up DaskEngine with address: {self._address}")
        self._executor = Client(self._address, timeout=30)
        install_deps = PipInstall(packages=self._requirements, pip_options=["--upgrade"])
        upload_egg = UploadFile(self._egg_path)

        self._executor.run(lambda ilib: ilib.invalidate_caches(), importlib)  # type: ignore

        self._executor.register_worker_plugin(install_deps, "install_deps")  # type: ignore
        self._executor.register_worker_plugin(upload_egg, "upload_egg")  # type: ignore

        self._executor.wait_for_workers(timeout=10)  # type: ignore
        _ = self._executor.get_versions(check=True)  # type: ignore
        logger.info("DaskEngine setup completed")

    def is_ready(self) -> bool:
        """Check if engine is ready for computation."""
        ready = self._executor is not None
        logger.info(f"DaskEngine ready status: {ready}")
        return ready

    def execute(self, network: NetworkAPI, **kwargs: Any) -> NetworkAPI:
        """Runs the computational network and returns the result object."""
        if network is None:
            logger.error("Cannot execute empty network")
            raise ValueError("cannot execute empty network")

        if self._executor is None:
            logger.error("DaskEngine not ready")
            raise ValueError("engine is not ready")

        self._network = network
        self._network.set_input(kwargs)

        logger.info("Starting network execution in DaskEngine")
        while self._submit_next():
            pass
        logger.info("Network execution completed in DaskEngine")

        return self._network

    def teardown(self) -> None:
        """Enging cleanup phase."""
        if self._executor is None:
            logger.error("DaskEngine not running")
            raise ValueError("engine not running")

        logger.info("Tearing down DaskEngine")
        self._executor.close()  # type: ignore

        # NOTE: This will kill the entire grid.
        # self._executor.shutdown()
