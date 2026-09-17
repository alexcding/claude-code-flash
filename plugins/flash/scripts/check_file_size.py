#!/usr/bin/env python3
"""PreToolUse hook for Read: cap whole-file reads above FLASH_MIN_LINES in the main session.

Default: the call goes through with `limit` set to the threshold, plus a note telling the
model how to get the rest. No extra turn is spent on a refusal. FLASH_DENY=1 refuses instead.

Allowed through untouched: subagents, targeted reads (offset/limit), small files, binary files.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flash_common import (allow_rewritten, count_lines, deny, deny_mode, disabled,  # noqa: E402
                          is_subagent, min_lines, read_input, redirect_message,
                          window_message)


def main():
    if disabled():
        return
    data = read_input()
    if is_subagent(data):
        return
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path")
    if not path:
        return
    # A targeted read is exactly what we want to encourage.
    if tool_input.get("offset") is not None or tool_input.get("limit") is not None:
        return

    limit = min_lines()
    lines = count_lines(path)
    if lines is None or lines <= limit:
        return
    if deny_mode():
        deny(redirect_message(path, lines, limit))
    allow_rewritten(dict(tool_input, limit=limit), window_message(path, lines, limit))


if __name__ == "__main__":
    main()
