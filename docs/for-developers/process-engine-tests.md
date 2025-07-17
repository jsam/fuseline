---
title: "ProcessEngine test matrix"
---

The `ProcessEngine` executes tasks stored in a `RuntimeStorage` backend. The table below lists baseline scenarios and edge cases to cover when writing tests for this worker.

| Scenario | Description | Expected behaviour |
| --- | --- | --- |
| Single task | One task enqueued and executed | State transitions from `PENDING` → `RUNNING` → `SUCCEEDED`; run marked finished |
| Sequential steps | Two tasks with dependency | Second task only runs after first succeeds |
| Branch choice | Task returns string to select next edge | Only chosen successor is enqueued |
| Retry succeeds | Failing task with retries eventually passes | State ends as `SUCCEEDED`; remaining retries not used |
| Retry fails | Task fails after max retries | Workflow marked `FAILED`; successors cancelled |
| Unknown step | Queue contains a name not in workflow | Step ignored; processing continues |
| Empty queue | No more tasks available | Worker finalizes run without error |
| Multiple workers | Two workers share same store | Each step executed exactly once |
| Resume run | Steps remain in queue across worker restarts | Pending tasks are picked up and completed |
| Cancel successors | Dependency fails after retries | Downstream steps marked `CANCELLED` |
| Duplicate entries | Step name appears multiple times in queue | Step executes only once |

These cases ensure the engine handles normal operation as well as unusual situations like invalid queue entries or simultaneous workers.
