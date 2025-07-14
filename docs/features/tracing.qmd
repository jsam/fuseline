---
title: "Tracing"
---

Record execution events using `FileTracer`.

```python
from fuseline import Workflow

wf = Workflow(outputs=[...], trace="trace.log")
wf.run({})
```
