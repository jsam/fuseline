---
title: "Function workflows"
---

Wrap callables with `FunctionStep` or use `workflow_from_functions`.


```python
from fuseline import FunctionStep, workflow_from_functions

@workflow_from_functions
def flow(a: int, b: int) -> int:
    return a + b

print(flow(1, 2))
```


