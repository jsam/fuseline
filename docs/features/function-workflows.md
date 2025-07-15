---
title: "Function workflows"
---

Wrap callables with `FunctionTask` or use `workflow_from_functions`.


```python
from fuseline import FunctionTask, workflow_from_functions

@workflow_from_functions
def flow(a: int, b: int) -> int:
    return a + b

print(flow(1, 2))
```


