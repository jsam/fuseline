---
title: "ProcessEngine test matrix"
---

The `ProcessEngine` executes steps stored in a `RuntimeStorage` backend. The table below lists baseline scenarios and edge cases to cover when writing tests for this worker.

| Scenario | Description | Expected behaviour |
| --- | --- | --- |
| Single step | One step enqueued and executed | State transitions from `PENDING` → `RUNNING` → `SUCCEEDED`; run marked finished |
| Sequential steps | Two steps with dependency | Second step only runs after first succeeds |
| Branch choice | Step returns string to select next edge | Only chosen successor is enqueued |
| Retry succeeds | Failing step with retries eventually passes | State ends as `SUCCEEDED`; remaining retries not used |
| Retry fails | Step fails after max retries | Workflow marked `FAILED`; successors cancelled |
| Unknown step | Queue contains a name not in workflow | Step ignored; processing continues |
| Empty queue | No more steps available | Worker finalizes run without error |
| Multiple workers | Two workers share same store | Each step executed exactly once |
| Resume run | Steps remain in queue across worker restarts | Pending steps are picked up and completed |
| Cancel successors | Dependency fails after retries | Downstream steps marked `CANCELLED` |
| Duplicate entries | Step name appears multiple times in queue | Step executes only once |

These cases ensure the engine handles normal operation as well as unusual situations like invalid queue entries or simultaneous workers.
