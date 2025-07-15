---
title: "Policies"
---

Fuseline tasks expose simple reliability controls.

### Retries and backoff

`Task` and `AsyncTask` accept `max_retries` and `wait` arguments. When a
step raises an exception, it will be retried until `max_retries` is
exhausted. The optional `wait` value sleeps between attempts.

Retries happen inside the task's private `_exec` method.  If a retry is
needed the task logs the error and waits before running again.  You may
subclass `Task` to implement custom backoff strategies or additional
recovery logic.

### Fail-fast

If any step fails after exhausting retries, downstream steps are marked
`CANCELLED` and the workflow state becomes `FAILED`.

Individual steps control this behaviour via the `max_retries` argument;
set it to ``0`` to disable retries entirely.  A workflow stops as soon
as any step reaches the `FAILED` state after exhausting its retries.
Custom engines may choose to implement alternative fail-fast semantics.

### Common questions

- How do I override retry logic?  Subclass `Task` and implement
  `exec_fallback` to customize what happens after the final failure.
- Can I pause a workflow?  Persist state using `RuntimeStorage` and resume
  with `ProcessEngine`.
- Can I change timeouts or other limits?  You can extend `Task` and raise
  your own exceptions in `run_step` when conditions are not met.  The
  engine will treat those like any other failure and apply the retry
  policy.
