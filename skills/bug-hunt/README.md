# bug-hunt — universal root-cause debugging skill

A portable agent skill that encodes a five-phase, evidence-driven debugging methodology. Works in **Claude Code** and **OpenAI Codex CLI** with no per-tool source changes.

Distinct from generic `hunt` / `investigate` skills in three ways:
- Enforces **multi-layered cause chains** — keeps drilling until success criterion met (not just first cause).
- Mandates **structured log discipline** — unique prefix + `JSON.stringify(null, 2)` so output is copy-pasteable, cleanup is a single `grep`.
- Requires a **bug-report artifact** in `docs/` — the investigation isn't done until the markdown lands.

## What it does

When triggered, the skill walks you through:

1. **Reproduce & Frame** — lock down the bug and define a measurable success criterion.
2. **Top-down Localization** — walk the data flow from symptom to suspected source.
3. **Full-chain Instrumentation** — add structured logs with a unique prefix at each layer; ask the user to repro.
4. **Layered Root Cause Analysis** — surface multi-level cause chains; don't stop at the proximate cause.
5. **Surgical Fix & Verify** — minimum-diff change, verify against success criterion, ship a bug report under `docs/`, then grep-clean the debug logs.

It refuses to "fix" via guesswork, bypass, swallow-and-log, or default-masking.

## Why

LLM-driven debugging often pattern-matches a fix from the symptom and stops there. That ships partial fixes, hides deeper causes, and leaks debug logs into production. This skill replaces "guess and try" with "evidence and chain reasoning".

Detailed methodology: see `references/methodology.md`. Worked example: `references/case-studies/youtube-estimated-quote.md`.

This skill lives in the [luckySnail/skills](https://github.com/luckySnail/skills) collection at `skills/bug-hunt/`.

## Layout

```
skills/bug-hunt/
├── SKILL.md                                # entry, used by both Claude Code and Codex
├── README.md                               # this file
├── references/
│   ├── methodology.md                      # 5-phase deep reference
│   ├── frontend-playbook.md                # browser / React / extension stack
│   ├── backend-playbook.md                 # (stub — planned)
│   ├── app-playbook.md                     # (stub — planned)
│   └── case-studies/
│       └── youtube-estimated-quote.md      # end-to-end worked example
├── templates/
│   ├── bug-report.md                       # final report skeleton
│   └── log-snippets.md                     # copy-paste log code (TS/Python/Go/Rust)
└── scripts/
    └── install.sh                          # per-skill installer for both tools
```

## Install

### Via the repo-wide installer

Installs every skill in the collection at once:

```bash
git clone https://github.com/luckySnail/skills ~/code/personal/skills-luckySnail
~/code/personal/skills-luckySnail/scripts/install.sh
```

Or scope to this skill only:

```bash
~/code/personal/skills-luckySnail/scripts/install.sh --only bug-hunt
```

### Via the per-skill installer

```bash
./skills/bug-hunt/scripts/install.sh
```

Both installers symlink the skill into `~/.claude/skills/bug-hunt` and `~/.agents/skills/bug-hunt`. Re-running is safe — symlinks pick up edits after `git pull`.

### Manual — Claude Code

User-level (every project on the machine):
```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/bug-hunt" ~/.claude/skills/bug-hunt
```

Project-level (this repo only):
```bash
mkdir -p .claude/skills
ln -s /absolute/path/to/skills/bug-hunt .claude/skills/bug-hunt
```

Verify: open Claude Code, type `/bug-hunt` — it should appear in the slash menu.

### Manual — OpenAI Codex CLI

User-level (every repo):
```bash
mkdir -p ~/.agents/skills
ln -s "$(pwd)/skills/bug-hunt" ~/.agents/skills/bug-hunt
```

Project-level (this repo only):
```bash
mkdir -p .agents/skills
ln -s /absolute/path/to/skills/bug-hunt .agents/skills/bug-hunt
```

Verify: in Codex CLI, type `/skills` — `bug-hunt` should appear.

## Trigger

In a chat with Claude Code or Codex, any of the following auto-invokes the skill:

- "debug this" / "hunt the bug" / "fix this bug"
- "why is X broken / loading / failing"
- "find the root cause"
- "排查一下" / "X 不工作" / "帮我查一下为什么 X"
- Pasting a console error / stack trace + asking for diagnosis

Explicit invocation: `/bug-hunt` (Claude Code) or `$bug-hunt` / `/skills` → select (Codex).

## Compatibility notes

The skill source uses **only the cross-tool subset** of SKILL.md:

- Frontmatter: `name`, `description` (both required by Codex, recommended by Claude Code).
- Body: plain Markdown. Subfiles referenced by relative path.
- No `${CLAUDE_SKILL_DIR}` substitution.
- No `` !`command` `` dynamic context blocks.
- No tool-specific frontmatter fields (`allowed-tools`, `effort`, etc.).

This means a single source directory works in both tools without forks.

If you fork to add tool-specific extras (e.g., Claude Code `allowed-tools`), keep them in a `claude-overlay/` branch and document the trade-off.

## Roadmap

- Phase 1 (current): Frontend playbook with worked example.
- Phase 2: Backend playbook (real case study from a 5xx / slow-query incident).
- Phase 3: App playbook (mobile crash / blank screen case study).
- Phase 4: Scripts to auto-generate the bug report from a session transcript.
- Phase 5: Optional linter that grep-fails CI if the debug log prefix leaks.

Contributions of real case studies welcome — they're more useful than abstract advice. Drop them into `references/case-studies/<slug>.md` following the structure of the existing one.

## License

MIT (or your preference — replace this line before publishing).
