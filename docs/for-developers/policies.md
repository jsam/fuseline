---
title: "Policies"
---

Fuseline tasks expose simple reliability controls.

### Retries and backoff

`Task` and `AsyncTask` accept `max_retries` and `wait` arguments. When a
step raises an exception, it will be retried until `max_retries` is
exhausted. The optional `wait` value sleeps between attempts.

### Fail-fast

If any step fails after exhausting retries, downstream steps are marked
`CANCELLED` and the workflow state becomes `FAILED`.

### Common questions

- How do I override retry logic?  Subclass `Task` and implement
  `exec_fallback` to customize what happens after the final failure.
- Can I pause a workflow?  Persist state using `RuntimeStorage` and resume
  with `ProcessEngine`.
