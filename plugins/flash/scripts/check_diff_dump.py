#!/usr/bin/env python3
"""PreToolUse hook for Bash: keep raw diff dumps out of the main session.

Denies bare `git diff`, `git show`, `gh pr diff`. Allowed through: subagents, anything
piped or redirected, and summary forms (--stat, --name-only, --oneline, --format, -s, ...).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flash_common import deny, disabled, flag, is_subagent, read_input, strip_wrappers  # noqa: E402

DIFF_CMD = re.compile(r"^(git\s+(diff|show)|gh\s+pr\s+diff)(\s|$)")
SUMMARY_FLAGS = re.compile(
    r"--(stat|shortstat|numstat|name-only|name-status|format|pretty|oneline|quiet|check|dirstat)"
    r"|(^|\s)-s(\s|$)"
)
REASON = (
    "flash: raw diff output stays out of the main session. Use --stat or --name-only here, "
    "pipe to grep/head for one hunk, or hand the review to the `reviewer` or `bulk-reader` "
    "subagent (`flash:reviewer` / `flash:bulk-reader` as a plugin) and relay its conclusion. FLASH_DISABLE=1 turns flash off."
)


def main():
    if disabled() or flag("ALLOW_DIFF"):
        return
    data = read_input()
    if is_subagent(data):
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    for chunk in re.split(r"\n|;|&&|\|\|", command):
        if "|" in chunk or ">" in chunk:
            continue
        stage = strip_wrappers(chunk)
        if DIFF_CMD.match(stage) and not SUMMARY_FLAGS.search(stage):
            deny(REASON)


if __name__ == "__main__":
    main()
