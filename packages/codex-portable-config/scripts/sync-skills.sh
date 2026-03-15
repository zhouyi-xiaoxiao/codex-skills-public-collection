#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/skills"
DST="$HOME/.codex/skills"

mkdir -p "$DST"

if [[ ! -d "$SRC" ]]; then
  echo "No skills directory found in repository: $SRC"
  exit 0
fi

synced=0
for skill_dir in "$SRC"/*; do
  if [[ ! -d "$skill_dir" ]]; then
    continue
  fi
  skill_name="$(basename "$skill_dir")"
  mkdir -p "$DST/$skill_name"
  rsync -a --delete "$skill_dir/" "$DST/$skill_name/"
  echo "Synced skill: $skill_name"
  synced=1
done

if [[ "$synced" -eq 0 ]]; then
  echo "No skill directories to sync."
fi
