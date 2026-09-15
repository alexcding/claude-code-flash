"""Shared helpers for the shunt hooks (python3 stdlib only)."""
import json
import os
import re
import sys

BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".bz2", ".xz", ".7z", ".mp3", ".mp4", ".mov", ".wav", ".ttf",
    ".otf", ".woff", ".woff2", ".ipynb", ".sqlite", ".db", ".pyc", ".class",
    ".o", ".a", ".so", ".dylib", ".dll", ".exe", ".bin",
}


def min_lines():
    try:
        return max(1, int(os.environ.get("SHUNT_MIN_LINES", "200")))
    except ValueError:
        return 200


def disabled():
    return os.environ.get("SHUNT_DISABLE", "").lower() in {"1", "true", "yes"}


def read_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def is_subagent(data):
    """Subagents are the cheap workers; they are allowed to read whatever they need."""
    transcript = data.get("transcript_path") or ""
    return "/subagents/" in transcript


def strip_wrappers(command):
    """Drop leading env assignments and known wrappers (rtk, sudo, time, nice)."""
    command = command.strip()
    while True:
        new = re.sub(r"^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)+", "", command)
        new = re.sub(r"^(?:rtk|sudo|time|nice)\s+", "", new)
        if new == command:
            return command
        command = new


def count_lines(path):
    """Line count of a regular text file, or None if the file should be ignored."""
    if not os.path.isfile(path):
        return None
    if os.path.splitext(path)[1].lower() in BINARY_EXT:
        return None
    try:
        with open(path, "rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return None


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def redirect_message(path, lines, limit):
    return (
        "shunt: {p} is {n} lines (limit {m}). Reading it whole into the main session burns frontier-model tokens.\n"
        "Do one of these instead:\n"
        "  1. Delegate: launch the `bulk-reader` subagent (Agent tool, subagent_type \"bulk-reader\") with the path(s) and a precise question. It runs on a cheaper model and returns bullets, not file dumps.\n"
        "  2. Target: Grep for the symbol you need, then Read with `offset` and `limit`, or use `sed -n` / `head -n` for that range.\n"
        "Treat this denial as the rule working, not an obstacle to route around. SHUNT_MIN_LINES changes the threshold; SHUNT_DISABLE=1 turns shunt off."
    ).format(p=path, n=lines, m=limit)
