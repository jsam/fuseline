---
title: "AND/OR joins"
---

Join branches after all or any parent steps finish.

```python
from fuseline import Step

class Joiner(Step):
    def run_step(self):
        print("joined")
```
