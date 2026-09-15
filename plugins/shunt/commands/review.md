---
description: Opus code review via the shunt reviewer subagent. With no words, reviews the working tree. Accepts a PR number, branch, or paths.
argument-hint: [PR number | branch | paths]
allowed-tools: Agent, Bash(git status:*), Bash(git rev-parse:*), Bash(git diff --stat:*), Bash(gh pr view:*)
---

Review target: **$ARGUMENTS**

Do not read the diff yourself. The reviewer does that on its own model.

1. Work out the target:
   - No words: the working tree (staged and unstaged changes).
   - A number: that pull request.
   - A branch name: `git diff main...<branch>`, using the repo's default branch in place of `main`.
   - Paths: those files.
   If the working tree is the target and `git diff --stat HEAD` is empty, say there is nothing
   to review and stop.
2. Run `git status --short` and keep the output.
3. Launch the `shunt:reviewer` subagent (`reviewer` if shunt was installed standalone) with a
   brief that names the repo root, the exact target from step 1, and anything the user added
   about what to focus on. Do not pass your own opinion of the change.
4. Run `git status --short` again. If it differs from step 2, the reviewer edited files: say
   so, list the changed paths, and discard its verdict.
5. Relay the reviewer's findings table and its `ACCEPT` / `REWORK` line as returned. Then add
   at most three lines: which findings you checked against the code yourself, and which
   nobody has checked.
