# ==============================================================================
#  Copyright (c) 2024 Sam Hart                                        =
#  <contact@justsam.io>                                  =
#                                                                              =
#  Permission is hereby granted, free of charge, to any person obtaining a     =
#  copy of this software and associated documentation files (the "Software"),  =
#  to deal in the Software without restriction, including without limitation   =
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,    =
#  and/or sell copies of the Software, and to permit persons to whom the       =
#  Software is furnished to do so, subject to the following conditions:        =
#                                                                              =
#  The above copyright notice and this permission notice shall be included in  =
#  all copies or substantial portions of the Software.                         =
#                                                                              =
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR  =
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,    =
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL     =
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER  =
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING     =
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER         =
#  DEALINGS IN THE SOFTWARE.                                                   =
# ==============================================================================

__version__ = "0.1.2"
__version_tuple__ = (0, 1, 2)
from .broker import Broker, MemoryBroker, PostgresBroker, StepReport
from .broker.clients import BrokerClient, HttpBrokerClient, LocalBrokerClient
from .broker.storage import (
    MemoryRuntimeStorage,
    PostgresRuntimeStorage,
    RuntimeStorage,
)
from .typing import Computed, T
from .worker import ExecutionEngine, run_from_env
from .workflow import (
    AsyncBatchStep,
    AsyncBatchWorkflow,
    AsyncParallelBatchStep,
    AsyncParallelBatchWorkflow,
    AsyncStep,
    AsyncWorkflow,
    BatchStep,
    BatchWorkflow,
    Condition,
    Depends,
    FunctionStep,
    Step,
    Task,
    TypedStep,
    Workflow,
    WorkflowSchema,
    workflow_from_functions,
)
from .workflow.exporters import Exporter, YamlExporter
from .workflow.tracing import FileTracer, Tracer


def __getattr__(name: str):
    if name == "PoolEngine":
        from .worker import PoolEngine as _PoolEngine
        return _PoolEngine
    if name == "ProcessEngine":
        from .worker import ProcessEngine as _ProcessEngine
        return _ProcessEngine
    if name == "run_from_env":
        from .worker import run_from_env as _run_from_env
        return _run_from_env
    raise AttributeError(name)
