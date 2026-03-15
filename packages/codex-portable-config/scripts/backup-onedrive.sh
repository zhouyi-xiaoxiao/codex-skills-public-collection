#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET=""
HOST_ID="${CODEX_PORTABLE_HOST:-}"

usage() {
  cat <<USAGE
Usage: backup-onedrive.sh --target onedrive [--host <host-id>]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --host) HOST_ID="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ "$TARGET" != "onedrive" ]]; then
  echo "Only --target onedrive is supported" >&2
  exit 2
fi

if [[ -z "$HOST_ID" ]]; then
  host_files=()
  while IFS= read -r hf; do
    host_files+=("$hf")
  done < <(find "$ROOT/hosts" -maxdepth 1 -type f -name "*.env" ! -name "host.example.env" | sort)
  if [[ "${#host_files[@]}" -eq 1 ]]; then
    HOST_ID="$(basename "${host_files[0]}")"
    HOST_ID="${HOST_ID%.env}"
  else
    echo "--host is required (or set CODEX_PORTABLE_HOST). Available hosts:" >&2
    for hf in "${host_files[@]}"; do
      echo "  - $(basename "${hf%.env}")" >&2
    done
    exit 2
  fi
fi

HOST_FILE="$ROOT/hosts/${HOST_ID}.env"
if [[ ! -f "$HOST_FILE" ]]; then
  echo "Host file not found: $HOST_FILE" >&2
  exit 2
fi

set -a
source "$HOST_FILE"
set +a

DEST="${ONEDRIVE_BACKUP_DIR:-}"
if [[ -z "$DEST" ]]; then
  echo "ONEDRIVE_BACKUP_DIR is not set in $HOST_FILE" >&2
  exit 2
fi

mkdir -p "$DEST"
rsync -a --delete --exclude '.git' --exclude '.DS_Store' "$ROOT/" "$DEST/"

MANIFEST="$DEST/.manifest.sha256"
(
  cd "$DEST"
  find . -type f ! -name '.manifest.sha256' -print0 | xargs -0 shasum -a 256
) > "$MANIFEST"

echo "Backup complete: $DEST"
echo "Manifest: $MANIFEST"
