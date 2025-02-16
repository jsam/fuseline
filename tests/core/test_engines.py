
from fuseline.core.engines import PoolEngine, SerialEngine
from fuseline.core.network import Network


def test_output_value_setting():
    # Create a simple network
    def simple_gear(x: int) -> int:
        return x * 2

    network = Network("test", outputs=[simple_gear])

    # Test SerialEngine
    serial_engine = SerialEngine()
    result = serial_engine.execute(network, x=5)
    assert not any(node.is_empty for node in result.outputs), "Output nodes should not be empty"
    assert any(node.value == 10 for node in result.outputs), "Expected output value not found"

    # Test PoolEngine
    pool_engine = PoolEngine(max_workers=2)
    pool_engine.setup()
    result = pool_engine.execute(network, x=5)
    assert not any(node.is_empty for node in result.outputs), "Output nodes should not be empty"
    assert any(node.value == 10 for node in result.outputs), "Expected output value not found"
