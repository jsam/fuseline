---
title: "For Developers"
---

Understand Fuseline internals and how the runtime operates.
This workspace answers frequent questions and walks through how to
extend the framework.  Below is a non‑exhaustive list of topics
covered across the pages:

* **How are tasks queued and scheduled?**  Learn how steps are placed
  into storage and how multiple workers can process them concurrently.
* **Where do inputs and outputs live?**  Understand how parameter
  values are passed to each step and how results are shared via the
  workflow's dictionary.
* **How is state recorded for each step and workflow?**  Explore the
  `Status` enum and see how `RuntimeStorage` persists state so runs can
  be resumed.
* **How does the engine decide what to run next?**  Dive into the
  successor logic that enqueues steps when all predecessors have
  finished.
* **How are retries and other policies applied?**  Learn how the engine
  handles failures, backoff and fail-fast behaviour.
* **Can I implement my own storage or execution engine?**  Yes!  The
  pages below describe the required interfaces and show example
  implementations.
* **How do I debug and trace workflows?**  See the tracing feature and
  learn how events are logged during execution.

Use the navigation links or start with these sections:

See also:

- [Execution flow](execution-flow.md)
- [State & storage](state-management.md)
- [Policies](policies.md)
