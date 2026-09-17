#!/usr/bin/env python3
"""PreToolUse hook for Bash: deny dumping a large file into the main session.

Catches `cat`, `less`, `more`, `bat`. Globs are expanded before the size check, and a
dump command the hook cannot parse is denied rather than waved through.

Allowed through: subagents, anything piped or redirected (`cat big | grep x`,
`cat big > copy`), small files, binary files. `head` and `tail` are never blocked.
"""
import glob
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flash_common import (count_lines, deny, disabled, is_subagent, min_lines,  # noqa: E402
                          read_input, redirect_message, strip_wrappers)

DUMP_CMDS = {"cat", "less", "more", "bat", "batcat"}
DUMP_START = re.compile(r"^(?:\S*/)?(?:cat|less|more|bat|batcat)\s")
UNPARSABLE = "flash: could not parse this command to check the file it dumps; quote it plainly or pipe through head/grep."


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
            if DUMP_START.match(stage):
                deny(UNPARSABLE)  # fail closed: an odd quote must not smuggle a dump through
            continue
        if not words or os.path.basename(words[0]) not in DUMP_CMDS:
            continue
        for arg in words[1:]:
            if arg.startswith("-"):
                continue
            path = arg if os.path.isabs(arg) else os.path.join(cwd, os.path.expanduser(arg))
            matches = glob.glob(path) or [path]  # `cat *.log` is checked file by file
            lines = max((count_lines(m) or 0) for m in matches)
            if lines > limit:
                deny(redirect_message(arg, lines, limit))


if __name__ == "__main__":
    main()
