---
title: "Batch workflows"
---

`BatchTask` and `BatchWorkflow` run tasks for multiple parameter sets.

```python
from fuseline import BatchTask, BatchWorkflow

class Echo(BatchTask):
    def run_step(self, word: str) -> str:
        return word

batch = BatchWorkflow(task=Echo())
print(batch.run([{"word": "hi"}, {"word": "bye"}]))
```
