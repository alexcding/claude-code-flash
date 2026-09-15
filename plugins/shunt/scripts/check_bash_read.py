#!/usr/bin/env python3
"""PreToolUse hook for Bash: deny dumping a large file into the main session.

Catches `cat`, `head`, `tail`, `less`, `more`, `bat`. Allowed through: subagents,
anything piped or redirected (`cat big | grep x`, `cat big > copy`), head/tail with an
explicit count (`head -50`, `tail -n 20`), small files, binary files.
"""
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shunt_common import (count_lines, deny, disabled, is_subagent, min_lines,  # noqa: E402
                          read_input, redirect_message, strip_wrappers)

DUMP_CMDS = {"cat", "head", "tail", "less", "more", "bat", "batcat"}
COUNTED = re.compile(r"(^|\s)-(n|c)?\s*\d+(\s|$)|(^|\s)-(n|c)\s+\d+|--(lines|bytes)[= ]")


def main():
    if disabled():
        return
    data = read_input()
    if is_subagent(data):
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    cwd = data.get("cwd") or os.getcwd()
    if not command.strip():
        return

    limit = min_lines()
    for chunk in re.split(r"\n|;|&&|\|\|", command):
        if "|" in chunk or ">" in chunk:
            continue  # piped or redirected: output is filtered or not shown
        stage = strip_wrappers(chunk)
        try:
            words = shlex.split(stage)
        except ValueError:
            continue
        if not words or os.path.basename(words[0]) not in DUMP_CMDS:
            continue
        if words[0] in {"head", "tail"} and COUNTED.search(stage):
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
