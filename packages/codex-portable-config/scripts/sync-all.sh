#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="research"
HOST_ID="${CODEX_PORTABLE_HOST:-}"
PUSH_CHANGES="0"
SKIP_BACKUP="0"
COMMIT_MESSAGE=""

usage() {
  cat <<USAGE
Usage: sync-all.sh --host <host-id> [--profile core|research|ops] [--push] [--message <msg>] [--skip-backup]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --host) HOST_ID="$2"; shift 2 ;;
    --push) PUSH_CHANGES="1"; shift ;;
    --message) COMMIT_MESSAGE="$2"; shift 2 ;;
    --skip-backup) SKIP_BACKUP="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$HOST_ID" ]]; then
  echo "--host is required (or set CODEX_PORTABLE_HOST)" >&2
  exit 2
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "sync is macOS only." >&2
  exit 2
fi

if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Repository is not a git work tree: $ROOT" >&2
  exit 2
fi

mkdir -p "$HOME/.codex" "$HOME/.codex/skills" "$HOME/.ssh" "$HOME/.local/bin"
ln -sf "$ROOT/bin/codex-portable" "$HOME/.local/bin/codex-portable"
ln -sf "$ROOT/bin/isbard" "$HOME/.local/bin/isbard"
chmod u+x "$HOME/.local/bin/codex-portable" "$HOME/.local/bin/isbard"

cd "$ROOT"

if [[ "$PUSH_CHANGES" == "1" ]]; then
  git add -A
  if ! git diff --cached --quiet; then
    if [[ -z "$COMMIT_MESSAGE" ]]; then
      COMMIT_MESSAGE="chore: portable sync from $(hostname -s) $(date +%Y-%m-%d_%H:%M:%S)"
    fi
    git commit -m "$COMMIT_MESSAGE"
  fi
fi

git fetch origin main
git rebase --autostash origin/main

if [[ "$PUSH_CHANGES" == "1" ]]; then
  git push origin main
fi

"$ROOT/scripts/render-config.sh" --host "$HOST_ID" --profile "$PROFILE" --codex-out "$HOME/.codex/config.toml.next" --ssh-out "$HOME/.ssh/config.next"
"$ROOT/scripts/switch-bluegreen.sh" --candidate "$HOME/.codex/config.toml.next" --target "$HOME/.codex/config.toml"
"$ROOT/scripts/switch-bluegreen.sh" --candidate "$HOME/.ssh/config.next" --target "$HOME/.ssh/config"
"$ROOT/scripts/sync-skills.sh"

if ! "$ROOT/scripts/doctor.sh" --host "$HOST_ID" --profile "$PROFILE"; then
  echo "Doctor failed after sync, rolling back..." >&2
  for t in "$HOME/.codex/config.toml" "$HOME/.ssh/config"; do
    if [[ -f "${t}.bak" ]]; then
      cp "${t}.bak" "$t"
      echo "Rolled back: $t" >&2
    fi
  done
  exit 1
fi

if [[ "$SKIP_BACKUP" != "1" ]]; then
  "$ROOT/scripts/backup-onedrive.sh" --target onedrive --host "$HOST_ID"
fi

echo "Sync complete."
