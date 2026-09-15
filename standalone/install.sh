#!/usr/bin/env bash
# Install shunt without the plugin system: copies agents, /task, hooks and rules into ~/.claude and merges settings.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p ~/.claude/agents ~/.claude/commands ~/.claude/hooks/shunt
cp "$HERE"/plugins/shunt/agents/*.md ~/.claude/agents/
cp "$HERE"/plugins/shunt/commands/*.md ~/.claude/commands/
cp "$HERE"/plugins/shunt/scripts/*.py ~/.claude/hooks/shunt/
cp "$HERE"/plugins/shunt/context/rules.md ~/.claude/hooks/shunt/rules.md
if [ -f ~/.claude/settings.json ]; then
  python3 - "$HERE/standalone/settings.json" <<'PY'
import json, os, sys
dst = os.path.expanduser("~/.claude/settings.json")
cur = json.load(open(dst)); add = json.load(open(sys.argv[1]))
cur.setdefault("env", {}).update(add["env"])
hooks = cur.setdefault("hooks", {})
for event, entries in add["hooks"].items():
    have = hooks.setdefault(event, [])
    for entry in entries:
        if entry not in have:
            have.append(entry)
json.dump(cur, open(dst, "w"), indent=2); print("merged into", dst)
PY
else
  cp "$HERE/standalone/settings.json" ~/.claude/settings.json && echo "wrote ~/.claude/settings.json"
fi
echo "Done. The SessionStart hook injects the shunt rules; nothing to add to CLAUDE.md."
