#!/usr/bin/env python3
"""PreToolUse hook for Bash: keep large-file dumps out of the main session.

Catches `cat`, `less`, `more`, `bat`. Only a bare `cat <one file>` is rewritten to
`head -n FLASH_MIN_LINES <file>` with a note, so no turn is wasted on a refusal; anything
more complex (flags, several files, chained commands) is denied. FLASH_DENY=1 always denies.

Allowed through: subagents, anything piped or redirected (`cat big | grep x`,
`cat big > copy`), small files, binary files. `head` and `tail` are never blocked.
"""
import glob
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flash_common import (allow_rewritten, count_lines, deny, deny_mode, disabled,  # noqa: E402
                          is_subagent, min_lines, read_input, redirect_message,
                          strip_wrappers, window_message)

DUMP_CMDS = {"cat", "less", "more", "bat", "batcat"}
DUMP_START = re.compile(r"^(?:\S*/)?(?:cat|less|more|bat|batcat)\s")
UNPARSABLE = "flash: could not parse this command to check the file it dumps; quote it plainly or pipe through head/grep."


def main():
    if disabled():
        return
    data = read_input()
    if is_subagent(data):
        return
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command") or ""
    cwd = data.get("cwd") or os.getcwd()
    if not command.strip():
        return

    limit = min_lines()
    chunks = re.split(r"\n|;|&&|\|\|", command)
    for chunk in chunks:
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
            if lines <= limit:
                continue
            if len(matches) > 1:
                deny(redirect_message(arg, lines, limit))
            # Only a bare `cat <file>` is rewritten; less/more/bat change output semantics.
            simple = (len(chunks) == 1 and len(words) == 2 and stage == command.strip()
                      and os.path.basename(words[0]) == "cat")
            if deny_mode() or not simple:
                deny(redirect_message(arg, lines, limit))
            head = "head -n {} {}".format(limit, shlex.quote(arg))
            allow_rewritten(dict(tool_input, command=head), window_message(arg, lines, limit))


if __name__ == "__main__":
    main()
