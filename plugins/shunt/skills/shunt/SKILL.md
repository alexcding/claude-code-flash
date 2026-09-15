---
name: shunt
description: When to hand work to the bulk-reader and code-writer subagents so the main model stays cheap. Load when a task involves reading large or many files, or generating boilerplate.
---

# Shunt: keep expensive tokens for reasoning

The main model should spend its context on decisions, not on raw file contents or boilerplate.

## Delegate reading when
- A file is over the shunt threshold (default 350 lines). The Read hook will block you anyway.
- You need the gist of several files (a directory overview, "how is auth done here").
- You need to scan logs, fixtures, generated code, or vendored dependencies.

Launch the `bulk-reader` subagent with the path(s) and a precise question. Ask for what you actually need: "list every call site of X with line numbers", "summarise the public API", "find where the timeout is set".

## Delegate writing when
- The code follows an existing pattern you can point to (another handler, another model, another test file).
- The output is long but predictable: fixtures, scaffolding, migrations, config.

Launch the `code-writer` subagent with the target path, the example to copy, and the differences. Read the result only if the report flags a problem.

## Do it yourself when
- The read is small and targeted (Grep, then Read with offset/limit).
- The change requires judgement about design, or touches tricky logic.

## Tuning
- `SHUNT_MIN_LINES` sets the threshold (default 350).
- `SHUNT_DISABLE=1` turns the hooks off for a session.
