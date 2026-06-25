#!/usr/bin/env bash
set -euo pipefail

RUN_DIAGNOSTICS=0
SHOW_LOGS=0
SHOW_REQUESTS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --diagnostics) RUN_DIAGNOSTICS=1; shift ;;
    --logs) SHOW_LOGS=1; shift ;;
    --requests) SHOW_REQUESTS=1; shift ;;
    -h|--help)
      cat <<'EOF'
Usage: surge_snapshot.sh [--diagnostics] [--logs] [--requests]

Collects a read-only Surge/Mac network snapshot. It avoids dumping full profiles
or secrets.
EOF
      exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

section() {
  printf '\n== %s ==\n' "$1"
}

run() {
  local label="$1"
  shift
  printf '\n$ %s\n' "$label"
  "$@" 2>&1 || true
}

find_surge_app() {
  if [[ -d /Applications/Surge.app ]]; then
    echo /Applications/Surge.app
    return
  fi
  mdfind 'kMDItemFSName == "Surge.app"' 2>/dev/null | head -n 1 || true
}

find_surge_cli() {
  local cli
  cli="$(command -v surge-cli 2>/dev/null || true)"
  if [[ -n "$cli" ]]; then
    echo "$cli"
    return
  fi

  local app_path="$1"
  if [[ -n "$app_path" && -x "$app_path/Contents/Applications/surge-cli" ]]; then
    echo "$app_path/Contents/Applications/surge-cli"
  fi
}

APP_PATH="$(find_surge_app)"
CLI_PATH="$(find_surge_cli "$APP_PATH")"
PROFILE_DIR="$HOME/Library/Application Support/Surge/Profiles"
LOG_DIR="$HOME/Library/Logs/Surge"

section "Surge discovery"
echo "app_path=${APP_PATH:-not found}"
echo "cli_path=${CLI_PATH:-not found}"

if [[ -n "$APP_PATH" && -f "$APP_PATH/Contents/Info.plist" ]]; then
  run "plutil version" /usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" "$APP_PATH/Contents/Info.plist"
  run "plutil build" /usr/libexec/PlistBuddy -c "Print :CFBundleVersion" "$APP_PATH/Contents/Info.plist"
fi

run "ps surge" pgrep -afil '(/Applications/Surge\.app/|com\.nssurge\.surge-mac|surge-mac\.helper)'

section "macOS network"
run "route -n get default" route -n get default
run "scutil --proxy" scutil --proxy
run "lsof -nP -iTCP:8888 -sTCP:LISTEN" lsof -nP -iTCP:8888 -sTCP:LISTEN

section "Profiles"
if [[ -d "$PROFILE_DIR" ]]; then
  find "$PROFILE_DIR" -maxdepth 1 -type f \( -name '*.conf' -o -name '*.surgeconfig' \) -print | sort
else
  echo "profile_dir=not found"
fi

if [[ -z "$CLI_PATH" ]]; then
  section "surge-cli"
  echo "surge-cli not found; GUI or app installation may be needed."
  exit 0
fi

section "surge-cli environment"
run "surge-cli environment" "$CLI_PATH" environment

section "Profile validation"
if [[ -d "$PROFILE_DIR" ]]; then
  while IFS= read -r profile; do
    [[ -z "$profile" ]] && continue
    run "surge-cli --check $(basename "$profile")" "$CLI_PATH" --check "$profile"
  done < <(find "$PROFILE_DIR" -maxdepth 1 -type f \( -name '*.conf' -o -name '*.surgeconfig' \) -print | sort)
fi

section "Fast network test"
run "surge-cli test-network" "$CLI_PATH" test-network

if [[ "$RUN_DIAGNOSTICS" -eq 1 ]]; then
  section "Surge diagnostics"
  run "surge-cli diagnostics" "$CLI_PATH" diagnostics
fi

if [[ "$SHOW_REQUESTS" -eq 1 ]]; then
  section "Recent requests"
  run "surge-cli dump request" "$CLI_PATH" dump request
fi

if [[ "$SHOW_LOGS" -eq 1 ]]; then
  section "Recent Surge log errors"
  if [[ -d "$LOG_DIR" ]]; then
    latest_log="$(find "$LOG_DIR" -maxdepth 1 -type f -name 'Surge-*.log' -print | sort | tail -n 1)"
    if [[ -n "${latest_log:-}" ]]; then
      echo "log_file=$latest_log"
      tail -n 160 "$latest_log" | rg 'NETWORK-ERROR|WARNING|DNS|Connection setup failed|timeout|failed|error' || true
    else
      echo "no Surge log found"
    fi
  else
    echo "log_dir=not found"
  fi
fi
