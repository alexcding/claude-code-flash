#!/usr/bin/env bash
# Install shunt without the plugin system: copies agents + hooks into ~/.claude and merges settings.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p ~/.claude/agents ~/.claude/hooks/shunt
cp "$HERE"/plugins/shunt/agents/*.md ~/.claude/agents/
cp "$HERE"/plugins/shunt/scripts/*.py ~/.claude/hooks/shunt/
if [ -f ~/.claude/settings.json ]; then
  python3 - "$HERE/standalone/settings.json" <<'PY'
import json, os, sys
dst = os.path.expanduser("~/.claude/settings.json")
cur = json.load(open(dst)); add = json.load(open(sys.argv[1]))
cur.setdefault("env", {}).update(add["env"])
pre = cur.setdefault("hooks", {}).setdefault("PreToolUse", [])
existing = json.dumps(pre)
for entry in add["hooks"]["PreToolUse"]:
    if "shunt/" not in existing or entry["matcher"] not in existing:
        pre.append(entry)
json.dump(cur, open(dst, "w"), indent=2); print("merged into", dst)
PY
else
  cp "$HERE/standalone/settings.json" ~/.claude/settings.json && echo "wrote ~/.claude/settings.json"
fi
echo "Append standalone/CLAUDE.md.snippet to ~/.claude/CLAUDE.md to teach the main model the routing rules."
