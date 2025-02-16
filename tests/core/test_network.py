
import numpy as np
import pytest

from fuseline.core.engines import PoolEngine, SerialEngine
from fuseline.core.network import Depends, Network
from fuseline.typing import Computed


class TestComputeNext:

    @pytest.fixture
    def linear_network(self) -> Network:
        """
        Creates a simple linear network:
        input -> gear1 -> gear2 -> output
        """
        def gear1(x: int) -> int:
            return x * 2

        def gear2(x: Computed[int] = Depends(gear1)) -> int:
            return x + 1

        def final_gear(x: Computed[int] = Depends(gear2)) -> int:
            return x

        return Network("linear", outputs=[final_gear])

    @pytest.fixture
    def branching_network(self) -> Network:
        """
        Creates a network with branches:
        input -> gear1 -> gear2 -> output1
              -> gear3 -> output2
        """
        def gear1(x: int) -> int:
            return x * 2

        def gear2(x: Computed[int] = Depends(gear1)) -> int:
            return x + 1

        def gear3(x: int) -> int:
            return x - 1

        return Network("branching", outputs=[gear2, gear3])

    @pytest.fixture
    def diamond_network(self) -> Network:
        """
        Creates a diamond-shaped network:
        input -> gear1 -> gear2 -> gear4 -> output
              -> gear3 ----------/
        """
        def gear1(x: int) -> int:
            return x * 2

        def gear2(x: Computed[int] = Depends(gear1)) -> int:
            return x + 1

        def gear3(x: int) -> int:
            return x - 1

        def gear4(a: Computed[int] = Depends(gear2), b: Computed[int] = Depends(gear3)) -> int:
            return a + b

        return Network("diamond", outputs=[gear4])

    @pytest.mark.parametrize("engine_class", [SerialEngine, PoolEngine])
    def test_linear_compute_next(self, linear_network: Network, engine_class):
        """Test compute_next on a linear network."""
        engine = engine_class()
        engine.setup()

        # Set input
        linear_network.set_input({"x": 5})

        # First computation should return the first output node
        next_nodes = linear_network.compute_next()
        assert len(next_nodes) == 1
        assert ["gear1"] == [str(node) for node in next_nodes]

        # Execute the gear and set the output
        for node in next_nodes:
            pred_gear = next(linear_network.graph.predecessors(node))
            assert pred_gear.value == 5
            assert pred_gear.name == "x"

            result = node(node.input_values)
            succ_gear = next(linear_network.graph.successors(node))
            succ_gear.set_value(result)

        # Second computation should return the next output node
        next_nodes = linear_network.compute_next()
        assert len(next_nodes) == 1
        assert ["gear2"] == [str(node) for node in next_nodes]

        for node in next_nodes:
            pred_gear = next(linear_network.graph.predecessors(node))
            assert pred_gear.value == 10
            assert pred_gear.name == "x"

            result = node(node.input_values)
            succ_gear = next(linear_network.graph.successors(node))
            succ_gear.set_value(result)

        final_nodes = linear_network.compute_next()
        assert len(final_nodes) == 1
        assert ["final_gear"] == [str(node) for node in final_nodes]

        node = next(iter(final_nodes))
        result = node(node.input_values)
        succ_gear = next(linear_network.graph.successors(node))
        succ_gear.set_value(result)

        no_next = linear_network.compute_next()
        assert len(no_next) == 0


    @pytest.mark.parametrize("engine_class", [SerialEngine, PoolEngine])
    def test_branching_compute_next(self, branching_network: Network, engine_class):
        """Test compute_next on a branching network."""
        engine = engine_class()
        engine.setup()

        # Set input
        branching_network.set_input({"x": 5})

        # First computation should return both parallel branches
        next_nodes = branching_network.compute_next()
        assert len(next_nodes) == 2
        assert ["gear1", "gear3"] == [str(node) for node in next_nodes]

        # Execute gears and set outputs
        for node in next_nodes:
            pred_gear = next(branching_network.graph.predecessors(node))
            assert pred_gear.value == 5
            assert pred_gear.name == "x"

            result = node(node.input_values)
            succ_gear = next(branching_network.graph.successors(node))
            succ_gear.set_value(result)

        # Next computation should return remaining output
        next_nodes = branching_network.compute_next()
        assert len(next_nodes) == 1
        assert ["gear2"] == [str(node) for node in next_nodes]

        for node in next_nodes:
            pred_gear = next(branching_network.graph.predecessors(node))
            assert pred_gear.value == 10
            assert pred_gear.name == "x"

            result = node(node.input_values)
            succ_gear = next(branching_network.graph.successors(node))
            succ_gear.set_value(result)

        no_nodes = branching_network.compute_next()
        assert no_nodes == []

    @pytest.mark.parametrize("engine_class", [SerialEngine, PoolEngine])
    def test_diamond_compute_next(self, diamond_network: Network, engine_class):
        """Test compute_next on a diamond network."""
        engine = engine_class()
        engine.setup()

        # Set input
        diamond_network.set_input({"x": 5})

        # First computation should return both parallel paths
        next_nodes = diamond_network.compute_next()
        assert len(next_nodes) == 2
        assert ["gear1", "gear3"] == [str(node) for node in next_nodes]

        # Execute parallel gears and set outputs
        for node in next_nodes:
            pred_gear = next(diamond_network.graph.predecessors(node))
            assert pred_gear.value == 5
            assert pred_gear.name == "x"

            result = node(node.input_values)
            succ_gear = next(diamond_network.graph.successors(node))
            succ_gear.set_value(result)

        next_nodes = diamond_network.compute_next()
        assert len(next_nodes) == 1
        assert ["gear2"] == [str(node) for node in next_nodes]
        for node in next_nodes:
            pred_gear = next(diamond_network.graph.predecessors(node))
            assert pred_gear.value == 10
            assert pred_gear.name == "x"

            result = node(node.input_values)
            succ_gear = next(diamond_network.graph.successors(node))
            succ_gear.set_value(result)

        final_nodes = diamond_network.compute_next()
        assert len(final_nodes) == 1
        assert ["gear4"] == [str(node) for node in final_nodes]
        for node in final_nodes:
            pred_gears = [
                (node.name, node.value)
                for node in diamond_network.graph.predecessors(node)
            ]
            assert [('a', 11), ('b', 4)] == pred_gears

            result = node(node.input_values)
            succ_gear = next(diamond_network.graph.successors(node))
            succ_gear.set_value(result)

        finalized = diamond_network.compute_next()
        assert finalized == []

    @pytest.mark.parametrize("engine_class", [SerialEngine, PoolEngine])
    def test_error_handling(self, engine_class):
        """Test error handling in compute_next."""
        def error_gear(x: int) -> int:
            raise ValueError("Test error")

        network = Network("error", outputs=[error_gear])
        engine = engine_class()
        engine.setup()

        network.set_input({"x": 5})

        next_nodes = network.compute_next()
        assert len(next_nodes) == 1
        assert ["error_gear"] == [str(node) for node in next_nodes]

        node = next(iter(next_nodes))

        with pytest.raises(Exception):
            pred_gear = next(network.graph.predecessors(node))
            pred_gear(pred_gear.input_values)

    @pytest.mark.parametrize("engine_class", [SerialEngine, PoolEngine])
    def test_empty_input_handling(self, linear_network: Network, engine_class):
        """Test compute_next behavior with empty inputs."""
        engine = engine_class()
        engine.setup()

        # Don't set any inputs, so no compute nodes should be ready!
        next_nodes = linear_network.compute_next()

        assert len(next_nodes) == 0
        assert [] == [str(node) for node in next_nodes]


    @pytest.mark.parametrize("engine_class", [SerialEngine, PoolEngine])
    def test_numpy_array_handling(self, engine_class):
        """Test compute_next with NumPy array inputs/outputs."""
        def array_gear(x: np.ndarray) -> np.ndarray:
            return x * 2

        network = Network("numpy", outputs=[array_gear])
        engine = engine_class()
        engine.setup()

        input_array = np.array([1, 2, 3])
        network.set_input({"x": input_array})

        next_nodes = network.compute_next()
        assert len(next_nodes) == 1
        assert ["array_gear"] == [str(node) for node in next_nodes]

        node = next(iter(next_nodes))
        pred_gear = next(network.graph.predecessors(node))
        assert (pred_gear.value == input_array).all()
        assert pred_gear.name == "x"

        result = node(node.input_values)
        succ_gear = next(network.graph.successors(node))
        succ_gear.set_value(result)

        assert np.array_equal(succ_gear.value, input_array * 2)
