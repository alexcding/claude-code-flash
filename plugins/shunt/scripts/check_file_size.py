#!/usr/bin/env python3
"""PreToolUse hook for Read: block whole-file reads above SHUNT_MIN_LINES."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shunt_common import count_lines, deny, disabled, min_lines, read_input, redirect_message  # noqa: E402


def main() -> None:
    if disabled():
        return
    data = read_input()
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path")
    if not path:
        return

    limit = min_lines()
    requested = tool_input.get("limit")
    # A targeted read (explicit small window) is exactly what we want to encourage.
    if isinstance(requested, int) and requested <= limit:
        return

    lines = count_lines(path)
    if lines is None or lines <= limit:
        return

    deny(redirect_message(path, lines, limit))


if __name__ == "__main__":
    main()
