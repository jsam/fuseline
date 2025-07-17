---
title: "Parallel execution"
---

Run independent branches concurrently using an execution engine.


```python
from fuseline import PoolEngine, Workflow

wf = Workflow(outputs=[...])
wf.run({}, execution_engine=PoolEngine(2))
```


