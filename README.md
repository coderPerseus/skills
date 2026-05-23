# luckySnail / skills

A curated collection of portable agent skills, designed to work in both **Claude Code** and **OpenAI Codex CLI** from a single source — no per-tool forks.

Inspired by [antfu/skills](https://github.com/antfu/skills): each skill lives in its own folder under `skills/`, with a `SKILL.md` entry point plus any references / templates / scripts it needs.

## Skills

| Skill | Description |
|---|---|
| [`bug-hunt`](./skills/bug-hunt) | Five-phase, evidence-driven root-cause debugging methodology. Enforces multi-layered cause chains, structured log discipline, and a bug-report artifact. |

More skills will land here over time. Each one is independently installable.

## Layout

```
skills-luckySnail/
├── README.md                    # this file — index of all skills
├── scripts/
│   └── install.sh               # repo-wide installer (links every skill)
└── skills/
    └── bug-hunt/
        ├── SKILL.md             # entry, used by both Claude Code and Codex
        ├── README.md            # per-skill docs
        ├── references/          # deep-dive playbooks, case studies
        ├── templates/           # copy-paste artifacts (bug report, log snippets)
        ├── scripts/             # per-skill installer
        └── examples/
```

Each `skills/<name>/` is a self-contained skill directory. You can symlink it into your tool's skills folder directly, or use the helpers below.

## Install

### All skills at once

```bash
git clone https://github.com/luckySnail/skills ~/code/personal/skills-luckySnail
~/code/personal/skills-luckySnail/scripts/install.sh
```

The installer symlinks every `skills/*/` into both `~/.claude/skills/<name>` and `~/.agents/skills/<name>`. Re-running is safe — symlinks pick up edits after `git pull`.

Flags:

- `--claude` — Claude Code only
- `--codex` — Codex CLI only
- `--project DIR` — also install project-level into `DIR/.claude/skills` and `DIR/.agents/skills`
- `--only NAME` — install just one skill (e.g. `--only bug-hunt`)

### One skill only

Every skill also ships its own installer:

```bash
./skills/bug-hunt/scripts/install.sh
```

Or symlink by hand — see the per-skill README for details.

## Authoring a new skill

1. Create `skills/<your-skill>/SKILL.md` with frontmatter:
   ```
   ---
   name: <your-skill>
   description: <when this skill should auto-invoke — be specific>
   ---
   ```
2. Keep the body to the cross-tool subset of SKILL.md syntax:
   - Plain Markdown only.
   - Reference subfiles by relative path (`references/foo.md`).
   - No `${CLAUDE_SKILL_DIR}` substitution, no dynamic `` !`command` `` blocks, no tool-specific frontmatter fields.
3. Add a row to the **Skills** table above.
4. (Optional) Add a `scripts/install.sh` for single-skill installs.

This means a single source directory works in both Claude Code and Codex without forks.

## License

MIT.
