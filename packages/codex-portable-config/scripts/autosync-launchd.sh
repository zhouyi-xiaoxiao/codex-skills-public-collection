#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${1:-}"
if [[ -n "$ACTION" ]]; then
  shift
fi

HOST_ID="${CODEX_PORTABLE_HOST:-}"
PROFILE="research"
INTERVAL_MINUTES="30"
PUSH_CHANGES="0"
LOAD_AGENT="1"
WITH_BACKUP="0"

usage() {
  cat <<USAGE
Usage:
  autosync-launchd.sh install --host <host-id> [--profile core|research|ops] [--interval-minutes <n>] [--push] [--with-backup] [--no-load]
  autosync-launchd.sh uninstall --host <host-id>
  autosync-launchd.sh status --host <host-id>
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST_ID="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --interval-minutes) INTERVAL_MINUTES="$2"; shift 2 ;;
    --push) PUSH_CHANGES="1"; shift ;;
    --with-backup) WITH_BACKUP="1"; shift ;;
    --no-load) LOAD_AGENT="0"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$ACTION" ]]; then
  usage
  exit 2
fi

if [[ -z "$HOST_ID" ]]; then
  echo "--host is required (or set CODEX_PORTABLE_HOST)" >&2
  exit 2
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "autosync is macOS only." >&2
  exit 2
fi

if ! [[ "$INTERVAL_MINUTES" =~ ^[0-9]+$ ]] || [[ "$INTERVAL_MINUTES" -lt 5 ]]; then
  echo "--interval-minutes must be an integer >= 5" >&2
  exit 2
fi

SAFE_HOST="${HOST_ID//[^A-Za-z0-9_.-]/-}"
LABEL="com.codexportable.sync.${SAFE_HOST}"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$HOME/.codex/logs"
LOG_FILE="$LOG_DIR/${LABEL}.log"
PATH_VALUE="/Applications/Codex.app/Contents/Resources:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

sync_cmd="$ROOT/bin/codex-portable sync --host $HOST_ID --profile $PROFILE"
if [[ "$PUSH_CHANGES" == "1" ]]; then
  sync_cmd="$sync_cmd --push"
fi
if [[ "$WITH_BACKUP" != "1" ]]; then
  sync_cmd="$sync_cmd --skip-backup"
fi

install_plist() {
  mkdir -p "$(dirname "$PLIST")" "$LOG_DIR"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>${sync_cmd}</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>${PATH_VALUE}</string>
    <key>HOME</key>
    <string>${HOME}</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>StartInterval</key>
  <integer>$((INTERVAL_MINUTES * 60))</integer>
  <key>StandardOutPath</key>
  <string>${LOG_FILE}</string>
  <key>StandardErrorPath</key>
  <string>${LOG_FILE}</string>
</dict>
</plist>
EOF
}

case "$ACTION" in
  install)
    install_plist
    echo "Autosync installed: $PLIST"
    echo "Log file: $LOG_FILE"
    if [[ "$LOAD_AGENT" == "1" ]]; then
      launchctl bootout "gui/$UID" "$PLIST" >/dev/null 2>&1 || true
      if ! launchctl bootstrap "gui/$UID" "$PLIST"; then
        echo "launchctl bootstrap failed for gui/$UID. Plist is created but not loaded." >&2
        echo "Try again from a logged-in desktop session:" >&2
        echo "  launchctl bootstrap gui/$UID $PLIST" >&2
        exit 1
      fi
      launchctl enable "gui/$UID/$LABEL" >/dev/null 2>&1 || true
      launchctl kickstart -k "gui/$UID/$LABEL" >/dev/null 2>&1 || true
      echo "Autosync loaded into launchd."
    else
      echo "Autosync plist created with --no-load."
      echo "Load later with: launchctl bootstrap gui/$UID $PLIST"
    fi
    ;;
  uninstall)
    launchctl bootout "gui/$UID" "$PLIST" >/dev/null 2>&1 || true
    rm -f "$PLIST"
    echo "Autosync removed: $PLIST"
    ;;
  status)
    if [[ -f "$PLIST" ]]; then
      echo "Autosync plist: $PLIST"
      if launchctl print "gui/$UID/$LABEL" >/tmp/codex_portable_autosync_status.txt 2>/dev/null; then
        sed -n '1,40p' /tmp/codex_portable_autosync_status.txt
      else
        echo "Launchd job is not currently loaded."
        echo "Load with: launchctl bootstrap gui/$UID $PLIST"
      fi
    else
      echo "Autosync is not installed for host: $HOST_ID"
      exit 1
    fi
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    usage
    exit 2
    ;;
esac
