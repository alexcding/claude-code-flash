"""Shared helpers for the flash hooks (python3 stdlib only)."""
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


def env(name, default=""):
    """FLASH_<name>, falling back to the pre-rename SHUNT_<name>."""
    return os.environ.get("FLASH_" + name, os.environ.get("SHUNT_" + name, default))


def flag(name):
    return env(name).lower() in {"1", "true", "yes"}


def min_lines():
    try:
        return max(1, int(env("MIN_LINES", "200")))
    except ValueError:
        return 200


def disabled():
    return flag("DISABLE")


def deny_mode():
    """FLASH_DENY=1 restores the old behaviour: refuse the call instead of windowing it."""
    return flag("DENY")


def read_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def is_subagent(data):
    """Subagents are the cheap workers; they are allowed to read whatever they need.

    `agent_id` is only present when the hook fires inside a subagent. The transcript path
    check covers older Claude Code versions that do not send it.
    """
    if data.get("agent_id"):
        return True
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


def _emit(payload):
    print(json.dumps({"hookSpecificOutput": dict(hookEventName="PreToolUse", **payload)}))
    sys.exit(0)


def deny(reason):
    _emit({"permissionDecision": "deny", "permissionDecisionReason": reason})


def allow_rewritten(updated_input, context):
    """Let the call through with a rewritten input and a note the model sees with the result.

    Costs no extra turn: the model gets a bounded window instead of a refusal it must
    react to, and the note tells it how to get the rest.
    """
    _emit({
        "permissionDecision": "allow",
        "updatedInput": updated_input,
        "additionalContext": context,
    })


_HOW_TO_GET_THE_REST = (
    "Either delegate to the `bulk-reader` subagent (`flash:bulk-reader` as a plugin) with a "
    "precise question, or Grep for the symbol and Read one window with `offset`/`limit`. "
    "Do not page through the whole file."
)


def window_message(path, lines, limit):
    return "flash: {p} is {n} lines; this is lines 1-{m} only. ".format(p=path, n=lines, m=limit) + _HOW_TO_GET_THE_REST


def redirect_message(path, lines, limit):
    return (
        "flash: {p} is {n} lines (limit {m}); whole-file reads stay out of the main session. ".format(p=path, n=lines, m=limit)
        + _HOW_TO_GET_THE_REST
        + " FLASH_MIN_LINES changes the threshold; FLASH_DISABLE=1 turns flash off."
    )
