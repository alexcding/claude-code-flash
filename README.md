# claude-code-flash

A local, self-hosted take on the idea in Spotify's ["Portal by Spotify cut my Claude Code token usage by 90%"](https://engineering.atspotify.com/2026/9/portal-by-spotify-cut-my-claude-code-token-usage-by-90): keep the frontier model from reading huge files or churning out boilerplate, and hand that work to a cheaper model instead.

Spotify's version routes files to workers on their internal Portal platform. This one uses nothing but Claude Code itself: four hooks, three subagents (two on Sonnet, one on Opus) and a rules file. No external service, no extra auth, no source code leaving your Anthropic account.

## What it does

| Piece | Role |
|---|---|
| `Read` hook | Caps whole-file reads over `FLASH_MIN_LINES` (default 200): the read goes through with `limit` set to the threshold and a note telling Claude to delegate or read one more targeted window. No turn is spent on a refusal. `FLASH_DENY=1` refuses instead. |
| `Bash` read hook | Caps `cat` / `less` / `more` / `bat` of large files when the output is not piped or redirected: a bare `cat big.log` becomes `head -n 200 big.log` plus the note; globs, several files, other flags and commands the hook cannot parse are denied. `cat big.log \| grep ERROR`, `head` and `tail` are still allowed. |
| `Bash` diff hook | Denies bare `git diff`, `git show`, and `gh pr diff` in the main session. Summary forms (`--stat`, `--name-only`, `--oneline`, ...) and piped forms pass. |
| `bulk-reader` agent | Sonnet subagent that reads files and returns structured bullets, never file dumps. |
| `code-writer` agent | Sonnet subagent that writes pattern-following boilerplate and reports back a file list instead of the code. |
| `reviewer` agent | Opus subagent that reviews a diff and returns verified findings as a table. |
| `SessionStart` hook | Injects [`context/rules.md`](plugins/flash/context/rules.md) into every main session (startup, resume, `/clear`, after compaction): response contract, roster, delegation, six-part briefs, verification and reporting rules, about 1,100 tokens. Bucket rules live in `/task` so they only load when used. Works like a global `CLAUDE.md` without touching yours. |
| `/review` command | Hands the working tree, a PR number, a branch or paths to the `reviewer` subagent and relays its findings table and ACCEPT / REWORK verdict. Shows as `/flash:review` if another command already uses `/review`. |
| `/task` command | Task dashboard. `/task` lists buckets under `.claude/scratch/`; `/task <sentence>` continues the matching bucket or opens a new one. |

Subagents are exempt from all hooks, so the workers can read whatever they need. The hooks also see through `rtk`, `sudo`, `time`, `nice`, and leading `VAR=x` prefixes.

## Install

```
claude plugin marketplace add Alexcding/claude-code-flash
claude plugin install flash@claude-code-flash
```

Restart Claude Code (or start a new session). `python3` must be on your `PATH`; nothing else is required.

### Without the plugin system

If you would rather have the pieces in `~/.claude` directly (agents, `/review`, `/task`, hooks, rules, settings):

```
git clone https://github.com/Alexcding/claude-code-flash
./claude-code-flash/standalone/install.sh
```

The script copies the agents, `/review`, `/task`, hook scripts and rules, then merges the `env` and `hooks` entries from `standalone/settings.json` into your settings, and leaves everything else untouched.

## Configure

Environment variables, settable in your shell or in `.claude/settings.json`:

```json
{
  "env": {
    "FLASH_MIN_LINES": "350"
  }
}
```

| Variable | Default | Meaning |
|---|---|---|
| `FLASH_MIN_LINES` | `200` | Files longer than this are capped to their first `FLASH_MIN_LINES` lines on a whole-file read. Raise to `350` or `500` if it feels too eager. |
| `FLASH_DENY` | unset | Set to `1` to refuse capped reads outright (the pre-0.4 behaviour) instead of windowing them. Useful for A/B benchmarking. |
| `FLASH_ALLOW_DIFF` | unset | Set to `1` to switch off only the diff hook. |
| `FLASH_DISABLE` | unset | Set to `1` to switch all hooks off, including the rules injection. |
| `FLASH_NO_RULES` | unset | Set to `1` to skip only the `SessionStart` rules injection. |

The pre-rename `SHUNT_*` names still work when the matching `FLASH_*` variable is unset.
| `CLAUDE_CODE_SUBAGENT_MODEL` | unset | Claude Code's own setting; `sonnet` makes every subagent without an explicit `model:` run on Sonnet. The standalone settings set this. |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | unset | Claude Code's own setting; `1` stops subagents from spawning subagents, so a worker can never fan out on the expensive model. The standalone settings set this. |

Plugins cannot set environment variables for you, so put these in your shell or `.claude/settings.json`. The standalone install sets both; with the plugin install, add them yourself:

```json
{
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1"
  }
}
```

The rules are opinionated. Edit `plugins/flash/context/rules.md` in a fork to change them; a repo's own `CLAUDE.md` wins on conflict.

To use a different worker model, edit `model:` in `plugins/flash/agents/*.md` (`haiku` is cheaper still, `opus` if you want more judgement in summaries).

## How a capped read looks

Claude asks to `Read` a 4,210-line file with no `offset`/`limit`. The hook lets the call
through with `limit: 200` and attaches this note to the result:

```
flash: src/generated/api.ts is 4210 lines; this is lines 1-200 only. Either delegate to the `bulk-reader` subagent (`flash:bulk-reader` as a plugin) with a precise question, or Grep for the symbol and Read one window with `offset`/`limit`. Do not page through the whole file.
```

Claude then either spawns the subagent or narrows the read, without having spent a turn on a
refusal. Reads that pass `offset` or `limit` go straight through, and subagents are never
capped. With `FLASH_DENY=1` the call is refused with a similar message instead.

Why not just deny? Every turn re-sends the whole accumulated context, so on a long task cost
is roughly context size times turn count. A refusal costs one full extra turn each time it
fires and adds nothing to context; the capped read delivers the same first window in the
turn Claude already spent. An internal 8-task benchmark on an Opus driver (not checked in here) showed the denial version
losing 14-24% against plain Claude Code on short read-heavy tasks (many denials, few turns to
amortise them) while winning 23-34% on long PRs; windowing keeps the cap without the wasted turns.

## Try the hooks by hand

```
echo '{"tool_name":"Read","tool_input":{"file_path":"/path/to/big/file"}}' \
  | python3 plugins/flash/scripts/check_file_size.py
```

An empty response means "allow untouched". A JSON object with `permissionDecision: "allow"` and `updatedInput` means the read was capped; `permissionDecision: "deny"` means blocked (`FLASH_DENY=1`, or a `cat` form too complex to rewrite).

## Layout

```
.claude-plugin/marketplace.json     marketplace manifest
plugins/flash/
  .claude-plugin/plugin.json        plugin manifest
  hooks/hooks.json                  PreToolUse hooks for Read and Bash, SessionStart rules hook
  scripts/                          hook implementations (python3, stdlib only)
  agents/                           bulk-reader, code-writer, reviewer subagents
  commands/review.md                /review: Opus review via the reviewer subagent
  commands/task.md                  /task dashboard
  context/rules.md                  rules injected at session start
standalone/                         install without the plugin system
  install.sh, settings.json
```

## Credits

The routing idea and the hook set come from Spotify's shunt plugin in [spotify/portal-ai-plugins](https://github.com/spotify/portal-ai-plugins). This repo re-implements it without Portal so anyone can run it.

The rules (response contract, briefs, task buckets, verification, reporting) and `/task` are adapted from [SirRuggie/claude-code-orchestration-kit](https://github.com/SirRuggie/claude-code-orchestration-kit) (MIT), with the roster swapped for bulk-reader / code-writer / reviewer.

## License

MIT
