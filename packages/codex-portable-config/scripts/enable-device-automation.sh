#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_ID="${CODEX_PORTABLE_HOST:-}"
PROFILE="${CODEX_PORTABLE_PROFILE:-research}"
INTERVAL_MINUTES="30"
AUTOSYNC_PUSH="0"
RUN_INITIAL_SYNC="1"
ZSHRC_PATH="${HOME}/.zshrc"

usage() {
  cat <<USAGE
Usage: enable-device-automation.sh --host <host-id> [--profile core|research|ops] [--interval-minutes <n>] [--autosync-push] [--no-initial-sync]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST_ID="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --interval-minutes) INTERVAL_MINUTES="$2"; shift 2 ;;
    --autosync-push) AUTOSYNC_PUSH="1"; shift ;;
    --no-initial-sync) RUN_INITIAL_SYNC="0"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$HOST_ID" ]]; then
  echo "--host is required" >&2
  exit 2
fi

if ! [[ "$INTERVAL_MINUTES" =~ ^[0-9]+$ ]] || [[ "$INTERVAL_MINUTES" -lt 5 ]]; then
  echo "--interval-minutes must be an integer >= 5" >&2
  exit 2
fi

mkdir -p "$HOME/.local/bin"
ln -sf "$ROOT/bin/codex-portable" "$HOME/.local/bin/codex-portable"
ln -sf "$ROOT/bin/isbard" "$HOME/.local/bin/isbard"
chmod u+x "$HOME/.local/bin/codex-portable" "$HOME/.local/bin/isbard"

touch "$ZSHRC_PATH"
tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

start_marker="# >>> codex-portable managed >>>"
end_marker="# <<< codex-portable managed <<<"

awk -v start="$start_marker" -v end="$end_marker" '
  $0 == start { skip = 1; next }
  $0 == end { skip = 0; next }
  !skip { print }
' "$ZSHRC_PATH" > "$tmp_file"

cat >> "$tmp_file" <<EOF
$start_marker
export PATH="\$HOME/.local/bin:\$PATH"
export CODEX_PORTABLE_REPO="$ROOT"
export CODEX_PORTABLE_HOST="$HOST_ID"
export CODEX_PORTABLE_PROFILE="$PROFILE"
alias cpsync='codex-portable sync --host \$CODEX_PORTABLE_HOST --profile \$CODEX_PORTABLE_PROFILE'
alias cpsyncp='codex-portable sync --host \$CODEX_PORTABLE_HOST --profile \$CODEX_PORTABLE_PROFILE --push'
alias cpdoctor='codex-portable doctor --host \$CODEX_PORTABLE_HOST --profile \$CODEX_PORTABLE_PROFILE'
$end_marker
EOF

mv "$tmp_file" "$ZSHRC_PATH"
trap - EXIT

autosync_args=(install --host "$HOST_ID" --profile "$PROFILE" --interval-minutes "$INTERVAL_MINUTES")
if [[ "$AUTOSYNC_PUSH" == "1" ]]; then
  autosync_args+=(--push)
fi

if ! "$ROOT/scripts/autosync-launchd.sh" "${autosync_args[@]}"; then
  echo "Autosync load failed in current shell context, falling back to plist-only mode."
  "$ROOT/scripts/autosync-launchd.sh" "${autosync_args[@]}" --no-load
fi

if [[ "$RUN_INITIAL_SYNC" == "1" ]]; then
  "$ROOT/scripts/sync-all.sh" --host "$HOST_ID" --profile "$PROFILE"
fi

echo "Device automation enabled."
echo "Open a new shell to load aliases: cpsync, cpsyncp, cpdoctor"
