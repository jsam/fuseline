---
title: "Runtime storage"
---

Persist workflow state using `FileRuntimeStorage` so runs can be resumed or executed by multiple workers.

```python
from fuseline import Workflow, FileRuntimeStorage

store = FileRuntimeStorage("runs")
wf = Workflow(outputs=[...])
wf.run(runtime_store=store)
```
