---
title: "Batch workflows"
---

`BatchStep` and `BatchWorkflow` run steps for multiple parameter sets.


```python
from fuseline import BatchStep, BatchWorkflow

class Echo(BatchStep):
    def run_step(self, word: str) -> str:
        return word

batch = BatchWorkflow(task=Echo())
print(batch.run([{"word": "hi"}, {"word": "bye"}]))
```


