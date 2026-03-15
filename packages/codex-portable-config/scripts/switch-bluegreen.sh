#!/usr/bin/env bash
set -euo pipefail

CANDIDATE=""
TARGET="$HOME/.codex/config.toml"
DOCTOR_CMD=""

usage() {
  cat <<USAGE
Usage: switch-bluegreen.sh --candidate <path> [--target <path>] [--doctor-cmd "<cmd>"]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --candidate) CANDIDATE="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    --doctor-cmd) DOCTOR_CMD="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$CANDIDATE" ]]; then
  echo "--candidate is required" >&2
  exit 2
fi
if [[ ! -f "$CANDIDATE" ]]; then
  echo "Candidate not found: $CANDIDATE" >&2
  exit 2
fi

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$HOME/.codex.backups/$TS"
mkdir -p "$BACKUP_DIR" "$(dirname "$TARGET")"

if [[ -f "$TARGET" ]]; then
  cp "$TARGET" "$BACKUP_DIR/$(basename "$TARGET").pre-switch"
  cp "$TARGET" "${TARGET}.bak"
fi

TMP_TARGET="${TARGET}.tmp"
cp "$CANDIDATE" "$TMP_TARGET"
mv "$TMP_TARGET" "$TARGET"
cp "$TARGET" "$BACKUP_DIR/$(basename "$TARGET").post-switch"

echo "Switched target: $TARGET"
if [[ -f "${TARGET}.bak" ]]; then
  DIFF_FILE="$BACKUP_DIR/$(basename "$TARGET").diff"
  if diff -u "${TARGET}.bak" "$TARGET" > "$DIFF_FILE"; then
    echo "No content diff."
  else
    echo "Diff summary (first 80 lines):"
    sed -n '1,80p' "$DIFF_FILE"
  fi
fi
echo "Backup dir: $BACKUP_DIR"
echo "Rollback backup: ${TARGET}.bak"

if [[ -n "$DOCTOR_CMD" ]]; then
  if ! bash -lc "$DOCTOR_CMD"; then
    echo "Doctor check failed, attempting rollback..." >&2
    if [[ -f "${TARGET}.bak" ]]; then
      cp "${TARGET}.bak" "$TARGET"
      echo "Rolled back target: $TARGET" >&2
    else
      rm -f "$TARGET"
      echo "Removed target (no .bak existed): $TARGET" >&2
    fi
    exit 1
  fi
fi
