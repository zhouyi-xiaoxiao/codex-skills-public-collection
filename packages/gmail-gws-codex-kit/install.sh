#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$ROOT_DIR/skills/gmail-gws"
BIN_SRC="$ROOT_DIR/bin"

mkdir -p "$HOME/.local/bin" "$HOME/.config/gws" "$HOME/.codex/skills"

if ! command -v gws >/dev/null 2>&1; then
  if command -v npm >/dev/null 2>&1; then
    npm install -g @googleworkspace/cli@0.8.0
  else
    echo "Missing both gws and npm. Install Node/npm first." >&2
    exit 1
  fi
fi

install -m 700 "$BIN_SRC/gws-gmail" "$HOME/.local/bin/gws-gmail"
install -m 700 "$BIN_SRC/gws-gmail-auth" "$HOME/.local/bin/gws-gmail-auth"

rm -rf "$HOME/.codex/skills/gmail-gws"
mkdir -p "$HOME/.codex/skills/gmail-gws"
cp -R "$SKILL_SRC/." "$HOME/.codex/skills/gmail-gws/"

AGENTS_FILE="$HOME/AGENTS.md"
START_MARKER="<!-- gmail-gws-codex:start -->"
END_MARKER="<!-- gmail-gws-codex:end -->"
BLOCK="$(cat <<'EOF'
<!-- gmail-gws-codex:start -->
## Email routing

- When the user asks about email or mailbox work and the provider is not specified, offer both Outlook and Gmail.
- Outlook is available through the built-in Outlook tools.
- Gmail is available through the `gmail-gws` skill and the `gws-gmail` wrapper.
- For Gmail tasks, prefer `gws-gmail` over raw `gws gmail`.
<!-- gmail-gws-codex:end -->
EOF
)"

if [[ -f "$AGENTS_FILE" ]]; then
  python3 - "$AGENTS_FILE" "$START_MARKER" "$END_MARKER" "$BLOCK" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
start = sys.argv[2]
end = sys.argv[3]
block = sys.argv[4]
text = path.read_text(encoding="utf-8")

if start in text and end in text:
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    new_text = before.rstrip() + "\n\n" + block + after
else:
    new_text = text.rstrip() + "\n\n" + block + "\n"

path.write_text(new_text, encoding="utf-8")
PY
else
  printf '%s\n' "$BLOCK" > "$AGENTS_FILE"
fi

cat <<'EOF'
Installed:
- ~/.local/bin/gws-gmail
- ~/.local/bin/gws-gmail-auth
- ~/.codex/skills/gmail-gws

Next steps:
1. Put your Desktop OAuth JSON at ~/.config/gws/client_secret.json
2. Run: gws-gmail-auth
3. Restart Codex
EOF
