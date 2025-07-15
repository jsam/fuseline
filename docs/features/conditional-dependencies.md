---
title: "Conditional dependencies"
---

Attach a `Condition` to `Depends` for branch logic.


```python
from fuseline import Condition, Depends

Condition(lambda ctx: ctx["flag"])(Depends(task))
```


