#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REF_DIR="$SKILL_DIR/references"
OFFICIAL_DIR="${1:-/Applications/Surge.app/Contents/Resources/Skills/surge}"

if [[ ! -d "$OFFICIAL_DIR" ]]; then
  echo "official Surge skill not found: $OFFICIAL_DIR" >&2
  exit 1
fi

if [[ ! -f "$OFFICIAL_DIR/SKILL.md" ]]; then
  echo "official SKILL.md not found: $OFFICIAL_DIR/SKILL.md" >&2
  exit 1
fi

if [[ ! -f "$OFFICIAL_DIR/references/command-reference.md" ]]; then
  echo "official command reference not found: $OFFICIAL_DIR/references/command-reference.md" >&2
  exit 1
fi

mkdir -p "$REF_DIR"
cp "$OFFICIAL_DIR/SKILL.md" "$REF_DIR/official-skill.md"
cp "$OFFICIAL_DIR/references/command-reference.md" "$REF_DIR/command-reference.md"

echo "synced official Surge skill reference from: $OFFICIAL_DIR"
