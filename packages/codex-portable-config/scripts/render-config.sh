#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="research"
HOST_ID=""
CODEX_OUT="$HOME/.codex/config.toml.next"
SSH_OUT="$HOME/.ssh/config.next"
DRY_RUN="0"

usage() {
  cat <<USAGE
Usage: render-config.sh --host <host-id> [--profile core|research|ops] [--codex-out <path>] [--ssh-out <path>] [--dry-run]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --host) HOST_ID="$2"; shift 2 ;;
    --codex-out) CODEX_OUT="$2"; shift 2 ;;
    --ssh-out) SSH_OUT="$2"; shift 2 ;;
    --dry-run) DRY_RUN="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$HOST_ID" ]]; then
  echo "--host is required" >&2
  exit 2
fi

HOST_FILE="$ROOT/hosts/${HOST_ID}.env"
if [[ ! -f "$HOST_FILE" ]]; then
  echo "Host file not found: $HOST_FILE" >&2
  exit 2
fi

set -a
source "$HOST_FILE"
set +a

for v in HOST_ID HOME_DIR WORKSPACE_ROOT FILESYSTEM_MCP_ROOT ISAMBARD_HOST_ALIAS ISAMBARD_REMOTE_ROOT; do
  if [[ -z "${!v:-}" ]]; then
    echo "Missing required variable $v in $HOST_FILE" >&2
    exit 2
  fi
done

is_enabled() {
  local raw="${1:-0}"
  local val
  val="$(printf "%s" "$raw" | tr '[:upper:]' '[:lower:]')"
  case "$val" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

case "$PROFILE" in
  core) FRAGMENTS=("$ROOT/templates/codex/profile.core.toml") ;;
  research) FRAGMENTS=("$ROOT/templates/codex/profile.core.toml" "$ROOT/templates/codex/profile.research.toml") ;;
  ops) FRAGMENTS=("$ROOT/templates/codex/profile.core.toml" "$ROOT/templates/codex/profile.ops.toml") ;;
  *) echo "Invalid profile: $PROFILE" >&2; exit 2 ;;
esac

if is_enabled "${ENABLE_MCP_GITHUB:-1}"; then
  FRAGMENTS+=("$ROOT/templates/codex/feature.github.toml")
fi
if is_enabled "${ENABLE_MCP_IONOS:-1}"; then
  FRAGMENTS+=("$ROOT/templates/codex/feature.ionos.toml")
fi
if is_enabled "${ENABLE_MCP_OUTLOOK:-1}"; then
  if [[ -z "${OUTLOOK_TENANT_ID:-}" ]]; then
    echo "Missing required variable OUTLOOK_TENANT_ID when ENABLE_MCP_OUTLOOK is enabled" >&2
    exit 2
  fi
  FRAGMENTS+=("$ROOT/templates/codex/feature.outlook.toml")
fi

mkdir -p "$(dirname "$CODEX_OUT")" "$(dirname "$SSH_OUT")"

python3 - "$ROOT/templates/codex/base.toml" "$CODEX_OUT" "${FRAGMENTS[@]}" <<'PY'
import os, re, sys, pathlib
base = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
out = pathlib.Path(sys.argv[2])
fragments = [pathlib.Path(p).read_text(encoding='utf-8') for p in sys.argv[3:]]
text = base + "\n\n" + "\n\n".join(fragments) + "\n"
pat = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
missing = set()
def repl(m):
    k = m.group(1)
    v = os.environ.get(k)
    if v is None:
        missing.add(k)
        return m.group(0)
    return v
rendered = pat.sub(repl, text)
if missing:
    raise SystemExit(f"Missing template vars: {', '.join(sorted(missing))}")
if pat.search(rendered):
    raise SystemExit("Unresolved placeholders remain")
out.write_text(rendered, encoding='utf-8')
PY

python3 - "$ROOT/templates/ssh/config.base" "$SSH_OUT" <<'PY'
import os, re, sys, pathlib
text = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
out = pathlib.Path(sys.argv[2])
pat = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
def repl(m):
    k = m.group(1)
    v = os.environ.get(k)
    if v is None:
        raise SystemExit(f"Missing template var: {k}")
    return v
rendered = pat.sub(repl, text)
out.write_text(rendered, encoding='utf-8')
PY

if [[ "$DRY_RUN" == "1" ]]; then
  echo "Rendered (dry-run): $CODEX_OUT"
  echo "Rendered (dry-run): $SSH_OUT"
else
  echo "Rendered: $CODEX_OUT"
  echo "Rendered: $SSH_OUT"
fi
