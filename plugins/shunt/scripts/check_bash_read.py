#!/usr/bin/env python3
"""PreToolUse hook for Bash: block `cat`/`less`/`more`/`bat` dumps of large files.

Only the *final* stage of a pipeline is checked: `cat big.log | grep ERROR`
produces small output and is allowed; a bare `cat big.log` is not.
"""
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shunt_common import count_lines, deny, disabled, min_lines, read_input, redirect_message  # noqa: E402

DUMP_CMDS = {"cat", "less", "more", "bat", "batcat"}


def last_pipeline_stages(command: str):
    """Yield the last stage of each command in a shell string (split on ; && || newline)."""
    for chunk in re.split(r"\n|;|&&|\|\|", command):
        stages = chunk.split("|")
        yield stages[-1].strip()


def main() -> None:
    if disabled():
        return
    data = read_input()
    command = (data.get("tool_input") or {}).get("command") or ""
    cwd = data.get("cwd") or os.getcwd()
    if not command.strip():
        return

    limit = min_lines()
    for stage in last_pipeline_stages(command):
        try:
            words = shlex.split(stage)
        except ValueError:
            continue
        # Skip leading env assignments like FOO=bar cat file
        words = [w for w in words if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w)] or []
        if not words or os.path.basename(words[0]) not in DUMP_CMDS:
            continue
        for arg in words[1:]:
            if arg.startswith("-"):
                continue
            path = arg if os.path.isabs(arg) else os.path.join(cwd, os.path.expanduser(arg))
            lines = count_lines(path)
            if lines is not None and lines > limit:
                deny(redirect_message(arg, lines, limit))


if __name__ == "__main__":
    main()
