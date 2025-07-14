---
title: "Workflow export"
---

Serialize graphs to YAML using `Workflow.export` and `YamlExporter`.

```python
from fuseline import Workflow

wf = Workflow(outputs=[...])
wf.export("workflow.yaml")
```
