#!/usr/bin/env bash
# Installs the bug-hunt skill into both Claude Code and Codex user-level skill directories
# via symlink, so updates to the source repo (e.g. `git pull`) take effect immediately.
#
# Usage:
#   ./install.sh                 # both tools, user-level
#   ./install.sh --claude        # Claude Code only
#   ./install.sh --codex         # Codex only
#   ./install.sh --project DIR   # also install project-level into DIR/.claude and DIR/.agents
#
# Re-running is safe: existing symlinks pointing at this repo are kept; broken symlinks
# are replaced; foreign files at the target path are refused (the script prints and exits).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_NAME="$(basename "$SKILL_SRC")"

CLAUDE=1
CODEX=1
PROJECT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude) CODEX=0; shift ;;
    --codex)  CLAUDE=0; shift ;;
    --project)
      PROJECT_DIR="${2:-}"
      [[ -z "$PROJECT_DIR" ]] && { echo "--project requires a directory"; exit 2; }
      [[ ! -d "$PROJECT_DIR" ]] && { echo "not a directory: $PROJECT_DIR"; exit 2; }
      shift 2 ;;
    -h|--help)
      sed -n '1,20p' "$0"
      exit 0 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

link_into() {
  local target_dir="$1"
  local label="$2"
  local target="$target_dir/$SKILL_NAME"

  mkdir -p "$target_dir"

  if [[ -L "$target" ]]; then
    local current
    current="$(readlink "$target")"
    if [[ "$current" == "$SKILL_SRC" ]]; then
      echo "  [$label] already linked: $target"
      return 0
    fi
    echo "  [$label] replacing stale symlink ($current -> $SKILL_SRC)"
    rm "$target"
  elif [[ -e "$target" ]]; then
    echo "  [$label] refusing — $target exists and is not a symlink to this repo."
    echo "          inspect it and remove manually if you want to install."
    return 1
  fi

  ln -s "$SKILL_SRC" "$target"
  echo "  [$label] installed: $target -> $SKILL_SRC"
}

echo "Installing skill '$SKILL_NAME' from $SKILL_SRC"

if [[ $CLAUDE -eq 1 ]]; then
  link_into "$HOME/.claude/skills" "Claude Code (user)"
fi

if [[ $CODEX -eq 1 ]]; then
  link_into "$HOME/.agents/skills" "Codex (user)"
fi

if [[ -n "$PROJECT_DIR" ]]; then
  if [[ $CLAUDE -eq 1 ]]; then
    link_into "$PROJECT_DIR/.claude/skills" "Claude Code (project: $PROJECT_DIR)"
  fi
  if [[ $CODEX -eq 1 ]]; then
    link_into "$PROJECT_DIR/.agents/skills" "Codex (project: $PROJECT_DIR)"
  fi
fi

cat <<EOF

Done.

Verify:
  - Claude Code: open a chat, type '/$SKILL_NAME' — should appear in slash menu.
  - Codex CLI:   type '/skills' — '$SKILL_NAME' should be listed.

Trigger phrases (auto-invoke):
  "debug this", "fix this bug", "why is X broken", "find the root cause",
  "排查一下", "X 不工作"
EOF
