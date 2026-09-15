#!/usr/bin/env python3
"""PreToolUse hook for Read: deny whole-file reads above SHUNT_MIN_LINES in the main session.

Allowed through: subagents, targeted reads (offset/limit), small files, binary files.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shunt_common import (count_lines, deny, disabled, is_subagent, min_lines,  # noqa: E402
                          read_input, redirect_message)


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
    deny(redirect_message(path, lines, limit))


if __name__ == "__main__":
    main()
