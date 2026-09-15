---
name: shunt
description: Model routing rules. The main session is for thinking; reading files, writing boilerplate, and reviewing diffs go to the bulk-reader, code-writer, and reviewer subagents. Load when a task involves reading large or many files, generating boilerplate, or reviewing a diff.
---

# Shunt: the main session is for thinking only

Planning, architecture, debugging, synthesis: main session. Reading files and writing boilerplate are I/O, not thinking. Use the Agent tool for them.

| Work | Agent | Model |
|------|-------|-------|
| Reading files / searching code | `bulk-reader` | Sonnet |
| Boilerplate mirroring an existing file | `code-writer` | Sonnet |
| Diff review | `reviewer` | Opus |

## Reading
Delegate to `bulk-reader` whenever you need a file over the threshold (default 200 lines), more than one file, or a sweep of a directory to answer a question. Give it precise paths plus the exact question; it returns bullets, never file dumps. The Read hook denies whole-file reads above `SHUNT_MIN_LINES`; treat that denial as the rule working, not an obstacle to route around.

Read directly only for a file you already know is small and must quote or edit verbatim, or a targeted `offset`/`limit` range you have already located.

## Writing
Delegate to `code-writer` for mechanical code that follows an existing pattern. Always pass a spec, at least one reference file to match, and the target path. Keep new architecture and subtle logic in the main session; no hook enforces this side.

## Reviewing
Hand diff reviews to `reviewer`. The Bash hook denies bare `git diff` / `git show` / `gh pr diff` in the main session; use `--stat` or `--name-only` there.

## Always
- Launch independent agents in a single message so they run concurrently.
- Relay the conclusion, not the agent's transcript.

## Tuning
- `SHUNT_MIN_LINES`: line threshold (default 200).
- `SHUNT_ALLOW_DIFF=1`: turn off only the diff hook.
- `SHUNT_DISABLE=1`: turn off all hooks.
