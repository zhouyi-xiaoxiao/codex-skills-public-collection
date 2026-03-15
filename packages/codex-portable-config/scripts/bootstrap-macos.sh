#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="research"
HOST_ID=""

usage() {
  cat <<USAGE
Usage: bootstrap-macos.sh --host <host-id> [--profile core|research|ops]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --host) HOST_ID="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$HOST_ID" ]]; then
  echo "--host is required" >&2
  exit 2
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This bootstrap currently supports macOS only." >&2
  exit 2
fi

mkdir -p "$HOME/.codex" "$HOME/.codex/skills" "$HOME/.ssh" "$HOME/.local/bin"

"$ROOT/scripts/render-config.sh" --host "$HOST_ID" --profile "$PROFILE" --codex-out "$HOME/.codex/config.toml.next" --ssh-out "$HOME/.ssh/config.next"

"$ROOT/scripts/switch-bluegreen.sh" --candidate "$HOME/.codex/config.toml.next" --target "$HOME/.codex/config.toml"
"$ROOT/scripts/switch-bluegreen.sh" --candidate "$HOME/.ssh/config.next" --target "$HOME/.ssh/config"

"$ROOT/scripts/sync-skills.sh"

ln -sf "$ROOT/bin/codex-portable" "$HOME/.local/bin/codex-portable"
ln -sf "$ROOT/bin/isbard" "$HOME/.local/bin/isbard"
chmod u+x "$HOME/.local/bin/codex-portable" "$HOME/.local/bin/isbard"

if ! "$ROOT/scripts/doctor.sh" --host "$HOST_ID" --profile "$PROFILE"; then
  echo "Doctor failed after switch, rolling back..." >&2
  for t in "$HOME/.codex/config.toml" "$HOME/.ssh/config"; do
    if [[ -f "${t}.bak" ]]; then
      cp "${t}.bak" "$t"
      echo "Rolled back: $t" >&2
    fi
  done
  exit 1
fi

echo "Bootstrap complete."
echo "Next steps (if needed):"
echo "  1) isbard auth"
echo "  2) codex-portable doctor --host $HOST_ID --profile $PROFILE"
