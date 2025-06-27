import sys
import types
from unittest import mock

import pytest

# Register simple stub modules for external dependencies
stubs = {
    'numpy': types.ModuleType('numpy'),
    'colorama': types.ModuleType('colorama'),
    'tabulate': types.ModuleType('tabulate'),
    'toml': types.ModuleType('toml'),
    'pydantic': types.ModuleType('pydantic'),
    'pydot': types.ModuleType('pydot'),
    'typeguard': types.ModuleType('typeguard'),
    'loguru': types.ModuleType('loguru'),
}

# Fill stub attributes
stubs['numpy'].array = lambda x: x
class _NDArray(list):
    pass
stubs['numpy'].NDArray = _NDArray

class _Color:
    pass

stubs['colorama'].Fore = _Color()
stubs['colorama'].Style = _Color()
stubs['colorama'].init = lambda autoreset=True: None

stubs['tabulate'].tabulate = (
    lambda data, headers=None, tablefmt=None: '\n'.join(
        [' | '.join(headers or [])] + [' | '.join(map(str, row)) for row in data]
    )
)

stubs['toml'].load = lambda path: {}

class _BaseModel:
    def __init__(self, **data):
        for k, v in data.items():
            setattr(self, k, v)
    @classmethod
    def model_validate(cls, obj, **kwargs):
        return cls(**obj)
    def model_dump(self, *a, **k):
        return self.__dict__

stubs['pydantic'].BaseModel = _BaseModel
stubs['pydantic'].ConfigDict = dict
stubs['pydantic'].Field = (
    lambda default=None, default_factory=None: default
    if default_factory is None
    else default_factory()
)

stubs['pydot'].Dot = type(
    'Dot',
    (),
    {
        '__init__': lambda self, *a, **k: None,
        'create_png': lambda self: b'',
        'write_png': lambda self, f: open(f, 'wb').write(b''),
    },
)
stubs['pydot'].Node = type('Node', (), {})
stubs['pydot'].Edge = type('Edge', (), {})

stubs['typeguard'].TypeCheckError = type('TypeCheckError', (Exception,), {})
stubs['typeguard'].check_type = lambda value, expected: True

class _Logger:
    def __getattr__(self, name):
        return lambda *a, **k: None

stubs['loguru'].logger = _Logger()

for name, module in stubs.items():
    sys.modules.setdefault(name, module)

class _Mocker:
    def __init__(self):
        self._patches = []
    def patch(self, *args, **kwargs):
        p = mock.patch(*args, **kwargs)
        m = p.start()
        self._patches.append(p)
        return m
    def stopall(self):
        for p in reversed(self._patches):
            p.stop()
        self._patches.clear()

@pytest.fixture
def mocker():
    m = _Mocker()
    try:
        yield m
    finally:
        m.stopall()
