# claude-code-shunt

A local, self-hosted take on the idea in Spotify's ["Portal by Spotify cut my Claude Code token usage by 90%"](https://engineering.atspotify.com/2026/9/portal-by-spotify-cut-my-claude-code-token-usage-by-90): keep the frontier model from reading huge files or churning out boilerplate, and hand that work to a cheaper model instead.

Spotify's version routes files to workers on their internal Portal platform. This one uses nothing but Claude Code itself: two hooks plus two Sonnet subagents. No external service, no extra auth, no source code leaving your Anthropic account.

## What it does

| Piece | Role |
|---|---|
| `Read` hook | Denies whole-file reads over `SHUNT_MIN_LINES` (default 200) and tells Claude to delegate or read a targeted window instead. |
| `Bash` read hook | Denies `cat` / `head` / `tail` / `less` / `more` / `bat` of large files when the output is not piped or redirected. `cat big.log \| grep ERROR` and `head -50 big.log` are still allowed. |
| `Bash` diff hook | Denies bare `git diff`, `git show`, and `gh pr diff` in the main session. Summary forms (`--stat`, `--name-only`, `--oneline`, ...) and piped forms pass. |
| `bulk-reader` agent | Sonnet subagent that reads files and returns structured bullets, never file dumps. |
| `code-writer` agent | Sonnet subagent that writes pattern-following boilerplate and reports back a file list instead of the code. |
| `reviewer` agent | Opus subagent that reviews a diff and returns verified findings as a table. |
| `shunt` skill | Routing rules so the main model delegates on its own, before the hooks force it. |

Subagents are exempt from all hooks, so the workers can read whatever they need. The hooks also see through `rtk`, `sudo`, `time`, and leading `VAR=x` prefixes.

## Install

```
claude plugin marketplace add Alexcding/claude-code-shunt
claude plugin install shunt@claude-code-shunt
```

Restart Claude Code (or start a new session). `python3` must be on your `PATH`; nothing else is required.

### Without the plugin system

If you would rather have the pieces in `~/.claude` directly (agents, hooks, settings):

```
git clone https://github.com/Alexcding/claude-code-shunt
./claude-code-shunt/standalone/install.sh
cat claude-code-shunt/standalone/CLAUDE.md.snippet >> ~/.claude/CLAUDE.md
```

The script copies the agents and hook scripts, merges the `env` and `hooks` entries from `standalone/settings.json` into your settings, and leaves everything else untouched.

## Configure

Environment variables, settable in your shell or in `.claude/settings.json`:

```json
{
  "env": {
    "SHUNT_MIN_LINES": "350"
  }
}
```

| Variable | Default | Meaning |
|---|---|---|
| `SHUNT_MIN_LINES` | `200` | Files longer than this are blocked from whole-file reads. Raise to `350` or `500` if it feels too eager. |
| `SHUNT_ALLOW_DIFF` | unset | Set to `1` to switch off only the diff hook. |
| `SHUNT_DISABLE` | unset | Set to `1` to switch all hooks off. |
| `CLAUDE_CODE_SUBAGENT_MODEL` | unset | Claude Code's own setting; `sonnet` makes every subagent without an explicit `model:` run on Sonnet. |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | unset | Claude Code's own setting; `1` stops subagents from spawning subagents, so a worker can never fan out on the expensive model. The standalone settings set this. |

Plugins cannot set environment variables for you, so put these in your shell or `.claude/settings.json`.

To use a different worker model, edit `model:` in `plugins/shunt/agents/*.md` (`haiku` is cheaper still, `opus` if you want more judgement in summaries).

## How a blocked read looks

```
shunt: src/generated/api.ts is 4210 lines (limit 200). Reading it whole would burn frontier-model tokens.
Do one of these instead:
  1. Delegate: launch the `bulk-reader` subagent ...
  2. Target: search first (Grep for the symbol you need), then Read with `offset` and `limit` ...
```

Claude then either spawns the subagent or narrows the read. Reads that pass `offset` or `limit` go straight through, and subagents are never blocked.

## Try the hooks by hand

```
echo '{"tool_name":"Read","tool_input":{"file_path":"/path/to/big/file"}}' \
  | python3 plugins/shunt/scripts/check_file_size.py
```

An empty response means "allow". A JSON object with `permissionDecision: "deny"` means blocked.

## Layout

```
.claude-plugin/marketplace.json     marketplace manifest
plugins/shunt/
  .claude-plugin/plugin.json        plugin manifest
  hooks/hooks.json                  PreToolUse hooks for Read and Bash
  scripts/                          hook implementations (python3, stdlib only)
  agents/                           bulk-reader, code-writer, reviewer subagents
  skills/shunt/SKILL.md             routing rules
standalone/                         install without the plugin system
  install.sh, settings.json, CLAUDE.md.snippet
```

## Credits

The routing idea and the hook set come from Spotify's shunt plugin in [spotify/portal-ai-plugins](https://github.com/spotify/portal-ai-plugins). This repo re-implements it without Portal so anyone can run it.

## License

MIT
