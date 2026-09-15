#!/usr/bin/env python3
"""SessionStart hook: inject context/rules.md into the main session, like a global CLAUDE.md.

Runs on startup, resume, /clear and after compaction so the rules survive a compact.
SHUNT_DISABLE=1 or SHUNT_NO_RULES=1 skips it.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shunt_common import disabled  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# Plugin layout keeps rules in ../context; the standalone install copies them next to this script.
CANDIDATES = [os.path.join(HERE, "rules.md"), os.path.join(os.path.dirname(HERE), "context", "rules.md")]


def main():
    if disabled() or os.environ.get("SHUNT_NO_RULES", "").lower() in {"1", "true", "yes"}:
        return
    rules = None
    for path in CANDIDATES:
        try:
            with open(path, encoding="utf-8") as fh:
                rules = fh.read()
            break
        except OSError:
            continue
    if not rules:
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": rules,
        }
    }))


if __name__ == "__main__":
    main()
