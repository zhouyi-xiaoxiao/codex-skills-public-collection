#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="research"
HOST_ID=""

usage() {
  cat <<USAGE
Usage: doctor.sh --host <host-id> [--profile core|research|ops]
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

ok=1
for c in bash python3 git rsync; do
  if command -v "$c" >/dev/null 2>&1; then
    echo "[OK] command: $c"
  else
    echo "[FAIL] missing command: $c"
    ok=0
  fi
done

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if "$ROOT/scripts/render-config.sh" --host "$HOST_ID" --profile "$PROFILE" --codex-out "$TMP_DIR/config.toml" --ssh-out "$TMP_DIR/ssh.config" --dry-run >/dev/null; then
  echo "[OK] render-config"
else
  echo "[FAIL] render-config"
  ok=0
fi

if python3 - <<'PY' "$TMP_DIR/config.toml"
import sys, tomllib, pathlib
p = pathlib.Path(sys.argv[1])
tomllib.loads(p.read_text(encoding='utf-8'))
print('[OK] toml parse')
PY
then
  true
else
  echo "[FAIL] toml parse"
  ok=0
fi

if command -v rg >/dev/null 2>&1; then
  SCAN_OUT="$TMP_DIR/secret_scan.txt"
  if rg -n --hidden 'ghp_[A-Za-z0-9]{20,}|BEGIN OPENSSH PRIVATE KEY|"refresh_token"|"access_token"|OPENAI_API_KEY\\s*=\\s*"[^"]+"' \
    "$ROOT/templates" "$ROOT/hosts" "$ROOT/skills" "$ROOT/bin" "$ROOT/README.md" "$ROOT/SETUP.md" "$ROOT/MIGRATION.md" \
    >"$SCAN_OUT" 2>/dev/null; then
    echo "[FAIL] possible secret material found in repository:" >&2
    sed -n '1,30p' "$SCAN_OUT" >&2
    ok=0
  else
    echo "[OK] repository secret scan"
  fi
elif command -v grep >/dev/null 2>&1; then
  SCAN_OUT="$TMP_DIR/secret_scan.txt"
  if grep -R -nE 'ghp_[A-Za-z0-9]{20,}|BEGIN OPENSSH PRIVATE KEY|"refresh_token"|"access_token"|OPENAI_API_KEY[[:space:]]*=[[:space:]]*"[^"]+"' \
    "$ROOT/templates" "$ROOT/hosts" "$ROOT/skills" "$ROOT/bin" "$ROOT/README.md" "$ROOT/SETUP.md" "$ROOT/MIGRATION.md" \
    >"$SCAN_OUT" 2>/dev/null; then
    echo "[FAIL] possible secret material found in repository:" >&2
    sed -n '1,30p' "$SCAN_OUT" >&2
    ok=0
  else
    echo "[OK] repository secret scan (grep fallback)"
  fi
else
  echo "[FAIL] repository secret scan skipped (no rg/grep)"
  ok=0
fi

if [[ -f "$ROOT/skills/isambard-automation/scripts/isbard_cli.py" ]]; then
  echo "[OK] Isambard skill present"
else
  echo "[FAIL] Isambard skill missing"
  ok=0
fi

if [[ "$ok" -eq 1 ]]; then
  echo "Doctor passed"
  exit 0
else
  echo "Doctor failed"
  exit 1
fi
