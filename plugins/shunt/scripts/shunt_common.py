"""Shared helpers for the shunt hooks."""
import json
import os
import sys

BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".bz2", ".xz", ".7z", ".mp3", ".mp4", ".mov", ".wav", ".ttf",
    ".otf", ".woff", ".woff2", ".ipynb", ".sqlite", ".db", ".pyc", ".class",
    ".o", ".a", ".so", ".dylib", ".dll", ".exe", ".bin",
}


def min_lines() -> int:
    try:
        return max(1, int(os.environ.get("SHUNT_MIN_LINES", "350")))
    except ValueError:
        return 350


def disabled() -> bool:
    return os.environ.get("SHUNT_DISABLE", "").lower() in {"1", "true", "yes"}


def read_input() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def count_lines(path):
    """Return the line count of a regular text file, or None if it should be skipped."""
    if not os.path.isfile(path):
        return None
    if os.path.splitext(path)[1].lower() in BINARY_EXT:
        return None
    try:
        with open(path, "rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return None


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def redirect_message(path: str, lines: int, limit: int) -> str:
    return (
        f"shunt: {path} is {lines} lines (limit {limit}). Reading it whole would burn frontier-model tokens.\n"
        "Do one of these instead:\n"
        f"  1. Delegate: launch the `bulk-reader` subagent (Agent tool, subagent_type \"bulk-reader\") with the file path and the specific question you need answered. It runs on Sonnet and returns only a summary or the relevant excerpts.\n"
        "  2. Target: search first (Grep for the symbol you need), then Read with `offset` and `limit` to pull just those lines.\n"
        f"Set SHUNT_MIN_LINES to change the threshold, or SHUNT_DISABLE=1 to turn shunt off."
    )
