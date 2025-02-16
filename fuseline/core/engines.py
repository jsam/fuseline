from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from typing import Any, Dict, Optional

from fuseline.core.abc import EngineAPI, NetworkAPI
from fuseline.core.nodes import DataNode, GearNode
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
            successor: DataNode = next(self._network.graph.successors(compute_node))
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
        futures: Dict[Future[Any], GearNode] = {}

        gear_node: GearNode
        for gear_node in self._network.compute_next():
            logger.debug(f"Submitting gear for execution: {gear_node.name}")
            future = self._executor.submit(gear_node, kwargs=gear_node.input_values)
            futures[future] = gear_node

        for future in as_completed(futures):
            gear_node = futures[future]
            value = future.result()

            successor: DataNode = next(self._network.graph.successors(gear_node))
            successor.set_value(value)

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
