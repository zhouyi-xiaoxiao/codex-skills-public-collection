# Outlook Web Workflow

This skill packages the unstable part of Outlook reply automation into one local script:

- `doctor`: check Chrome availability, the debugging endpoint, Python imports, and whether Outlook-related cookies can be discovered from the local Chrome profile
- `reply`: search Outlook Web for the original message, open native Reply, fill the body from `stdin`, attach files, send, and then verify the sent result
- `compose`: open Outlook Web's native new-message composer, fill `To`, `Subject`, body, attach files, send, and then verify the sent result
- `verify`: search Sent Items in Outlook Web and confirm that a matching message exists, optionally with specific attachment names

## Command Contract

Reply with browser fallback:

```bash
cat reply.txt | python3 ~/.codex/skills/outlook-reply-assistant/scripts/outlook_web_reply.py reply \
  --from-email someone@example.com \
  --subject "Exact subject line" \
  --received-after <YYYY-MM-DD> \
  --attachment /absolute/path/to/file.pdf
```

Verify a sent reply:

```bash
python3 ~/.codex/skills/outlook-reply-assistant/scripts/outlook_web_reply.py verify \
  --to someone@example.com \
  --subject "Exact subject line" \
  --attachment-name file.pdf \
  --after <YYYY-MM-DD>
```

Compose a fresh message:

```bash
cat reply.txt | python3 ~/.codex/skills/outlook-reply-assistant/scripts/outlook_web_reply.py compose \
  --to someone@example.com \
  --subject "Skill speed test" \
  --attachment /absolute/path/to/file.pdf
```

## Output Shape

Successful commands print JSON like:

```json
{
  "ok": true,
  "command": "reply",
  "path": "browser",
  "to": "someone@example.com",
  "subject": "Exact subject line",
  "attachments": ["file.pdf"],
  "sent_at": "2026-01-01T12:00:00+00:00"
}
```

Failures still print JSON, then exit non-zero:

```json
{
  "ok": false,
  "command": "reply",
  "handoff_required": true,
  "error": "Outlook needs an interactive sign-in step."
}
```

## Behavioral Notes

- The script creates a fresh tab so it does not hijack the user’s existing Outlook tab.
- If it started a temporary Chrome instance itself and the run finishes normally, it closes that instance and cleans up the temporary profile.
- If Outlook asks for login, MFA, or CAPTCHA, the script stops instead of guessing.
- `received-after` and `after` are freshness hints for repeated subjects. Outlook Web search still decides the actual result set.
- `compose` is useful for smoke tests and ad hoc sends that are not tied to an existing thread.
- The reply body is read from `stdin` so it does not leak through shell history or process listings.

## Recommended Agent Usage

1. Use Outlook MCP first to locate the original email and gather sender, subject, and timing context.
2. If no attachments are needed, prefer Outlook MCP `reply_to_email`.
3. If attachments are needed, use this script for the browser-native reply flow.
4. After send, prefer Outlook MCP to confirm the message in Sent Items. Use the bundled `verify` command only when Outlook MCP confirmation is unavailable or ambiguous.
