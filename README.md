# claude-code-shunt

A local, self-hosted take on the idea in Spotify's ["Portal by Spotify cut my Claude Code token usage by 90%"](https://engineering.atspotify.com/2026/9/portal-by-spotify-cut-my-claude-code-token-usage-by-90): keep the frontier model from reading huge files or churning out boilerplate, and hand that work to a cheaper model instead.

Spotify's version routes files to workers on their internal Portal platform. This one uses nothing but Claude Code itself: two hooks plus two Sonnet subagents. No external service, no extra auth, no source code leaving your Anthropic account.

## What it does

| Piece | Role |
|---|---|
| `Read` hook | Denies whole-file reads over `SHUNT_MIN_LINES` (default 350) and tells Claude to delegate or read a targeted window instead. |
| `Bash` hook | Denies `cat` / `less` / `more` / `bat` of large files when the output is not piped anywhere. `cat big.log \| grep ERROR` is still allowed. |
| `bulk-reader` agent | Sonnet subagent that reads files in chunks and returns a summary or only the relevant excerpts. |
| `code-writer` agent | Sonnet subagent that generates pattern-following boilerplate and reports back a short summary instead of the code. |
| `shunt` skill | Guidance for when the main model should delegate on its own, before the hooks force it. |

## Install

```
claude plugin marketplace add Alexcding/claude-code-shunt
claude plugin install shunt@claude-code-shunt
```

Restart Claude Code (or start a new session). `python3` must be on your `PATH`; nothing else is required.

## Configure

Environment variables, settable in your shell or in `.claude/settings.json`:

```json
{
  "env": {
    "SHUNT_MIN_LINES": "500"
  }
}
```

| Variable | Default | Meaning |
|---|---|---|
| `SHUNT_MIN_LINES` | `350` | Files longer than this are blocked from whole-file reads. |
| `SHUNT_DISABLE` | unset | Set to `1` to switch the hooks off. |

To use a different worker model, edit `model:` in `plugins/shunt/agents/*.md` (`haiku` is cheaper still, `opus` if you want more judgement in summaries).

## How a blocked read looks

```
shunt: src/generated/api.ts is 4210 lines (limit 350). Reading it whole would burn frontier-model tokens.
Do one of these instead:
  1. Delegate: launch the `bulk-reader` subagent ...
  2. Target: search first (Grep for the symbol you need), then Read with `offset` and `limit` ...
```

Claude then either spawns the subagent or narrows the read. Reads that already pass a `limit` at or under the threshold go straight through, so chunked reading inside the subagents is never blocked.

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
  agents/                           bulk-reader and code-writer subagents
  skills/shunt/SKILL.md             delegation guidance
```

## License

MIT
