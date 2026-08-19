#!/usr/bin/env bash
# Installs every skill under skills/ into Claude Code and/or Codex CLI skill
# directories via symlink, so `git pull` edits take effect immediately.
#
# Usage:
#   ./install.sh                 # all skills, both tools, user-level
#   ./install.sh --claude        # Claude Code only
#   ./install.sh --codex         # Codex only
#   ./install.sh --only NAME     # install just one skill (e.g. --only pdf-to-epub)
#   ./install.sh --project DIR   # also install project-level into DIR/.claude and DIR/.agents
#
# Re-running is safe: existing symlinks pointing at this repo are kept; broken
# symlinks are replaced; foreign files at the target path are refused.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"

CLAUDE=1
CODEX=1
PROJECT_DIR=""
ONLY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude) CODEX=0; shift ;;
    --codex)  CLAUDE=0; shift ;;
    --only)
      ONLY="${2:-}"
      [[ -z "$ONLY" ]] && { echo "--only requires a skill name"; exit 2; }
      shift 2 ;;
    --project)
      PROJECT_DIR="${2:-}"
      [[ -z "$PROJECT_DIR" ]] && { echo "--project requires a directory"; exit 2; }
      [[ ! -d "$PROJECT_DIR" ]] && { echo "not a directory: $PROJECT_DIR"; exit 2; }
      shift 2 ;;
    -h|--help)
      sed -n '1,15p' "$0"
      exit 0 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

[[ ! -d "$SKILLS_DIR" ]] && { echo "no skills/ directory at $SKILLS_DIR"; exit 1; }

link_one() {
  local skill_src="$1"
  local target_dir="$2"
  local label="$3"
  local skill_name
  skill_name="$(basename "$skill_src")"
  local target="$target_dir/$skill_name"

  mkdir -p "$target_dir"

  if [[ -L "$target" ]]; then
    local current
    current="$(readlink "$target")"
    if [[ "$current" == "$skill_src" ]]; then
      echo "  [$label] already linked: $target"
      return 0
    fi
    echo "  [$label] replacing stale symlink ($current -> $skill_src)"
    rm "$target"
  elif [[ -e "$target" ]]; then
    echo "  [$label] refusing — $target exists and is not a symlink to this repo."
    echo "          inspect it and remove manually if you want to install."
    return 1
  fi

  ln -s "$skill_src" "$target"
  echo "  [$label] installed: $target -> $skill_src"
}

install_skill() {
  local skill_src="$1"
  local skill_name
  skill_name="$(basename "$skill_src")"

  if [[ ! -f "$skill_src/SKILL.md" ]]; then
    echo "Skipping $skill_name: no SKILL.md found"
    return 0
  fi

  echo "Installing skill '$skill_name' from $skill_src"

  if [[ $CLAUDE -eq 1 ]]; then
    link_one "$skill_src" "$HOME/.claude/skills" "Claude Code (user)"
  fi
  if [[ $CODEX -eq 1 ]]; then
    link_one "$skill_src" "$HOME/.agents/skills" "Codex (user)"
  fi
  if [[ -n "$PROJECT_DIR" ]]; then
    if [[ $CLAUDE -eq 1 ]]; then
      link_one "$skill_src" "$PROJECT_DIR/.claude/skills" "Claude Code (project: $PROJECT_DIR)"
    fi
    if [[ $CODEX -eq 1 ]]; then
      link_one "$skill_src" "$PROJECT_DIR/.agents/skills" "Codex (project: $PROJECT_DIR)"
    fi
  fi
}

shopt -s nullglob
count=0
for skill_src in "$SKILLS_DIR"/*/; do
  skill_src="${skill_src%/}"
  skill_name="$(basename "$skill_src")"
  if [[ -n "$ONLY" && "$skill_name" != "$ONLY" ]]; then
    continue
  fi
  install_skill "$skill_src"
  count=$((count + 1))
done

if [[ $count -eq 0 ]]; then
  if [[ -n "$ONLY" ]]; then
    echo "No skill named '$ONLY' under $SKILLS_DIR/"
  else
    echo "No skills found under $SKILLS_DIR/"
  fi
  exit 1
fi

cat <<EOF

Done — installed $count skill(s).

Verify:
  - Claude Code: open a chat, type '/<skill-name>' — should appear in slash menu.
  - Codex CLI:   type '/skills' — installed skills should be listed.
EOF
