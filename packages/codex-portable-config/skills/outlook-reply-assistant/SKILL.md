---
name: outlook-reply-assistant
description: "Reply to Outlook emails while keeping the original thread, adding attachments when needed, and checking that the sent message exists afterward. Use when the user asks for Outlook reply work such as “回这封邮件”, “回复发件人”, “把附件发回去”, “帮我回 Outlook 邮件”, “reply to this email”, or “send this back with attachment”."
---

# Outlook Reply Assistant

## Overview

Use this skill for Outlook reply tasks that must stay in the original thread and may need file attachments.

It also includes a small `compose` helper for smoke tests or one-off sends when you want to measure the browser path directly with an attachment.

Prefer Outlook MCP for simple text-only replies. Use the bundled browser script when attachments are required, when Outlook MCP cannot attach files to a reply cleanly, or when the native Outlook Web reply flow must be preserved.

## Workflow Decision Tree

1. Find the original email with Outlook MCP and capture:
   - sender email
   - exact subject
   - a recent date/time hint
   - the plain-text reply body you want to send
2. If the reply is plain text and has no attachments:
   - use Outlook MCP `reply_to_email`
   - then confirm the message appears in Sent Items with Outlook MCP
3. If the reply needs attachments, or the reply must definitely stay on the original thread:
   - pipe the body into `scripts/outlook_web_reply.py reply ...`
   - let the script search Outlook Web, open the original message, click native Reply, attach files, and send
4. After browser fallback sends the message:
   - prefer Outlook MCP to confirm the sent mail
   - use `outlook_web_reply.py verify ...` as a browser-side fallback when needed

## Quick Start

Check local prerequisites:

```bash
python3 ~/.codex/skills/outlook-reply-assistant/scripts/outlook_web_reply.py doctor
```

Reply with one attachment:

```bash
cat reply.txt | python3 ~/.codex/skills/outlook-reply-assistant/scripts/outlook_web_reply.py reply \
  --from-email instructor@example.edu \
  --subject "Course scheduling question" \
  --received-after <YYYY-MM-DD> \
  --attachment /absolute/path/to/file.pdf
```

Verify the sent mail in Outlook Web:

```bash
python3 ~/.codex/skills/outlook-reply-assistant/scripts/outlook_web_reply.py verify \
  --to instructor@example.edu \
  --subject "Course scheduling question" \
  --attachment-name file.pdf \
  --after <YYYY-MM-DD>
```

Compose a fresh test email with an attachment:

```bash
cat reply.txt | python3 ~/.codex/skills/outlook-reply-assistant/scripts/outlook_web_reply.py compose \
  --to someone@example.com \
  --subject "Skill speed test" \
  --attachment /absolute/path/to/file.pdf
```

## Required Inputs

- `--from-email`: the sender address of the original message you are replying to
- `--subject`: the exact subject used to search Outlook Web
- `--received-after` / `--after`: a freshness hint for repeated subjects
- `--attachment`: absolute local file paths only
- `stdin`: the final plain-text reply body

For `compose`, only `--to`, `--subject`, optional `--attachment`, and `stdin` are required.

## Safety Rules

- Validate attachment paths before opening Outlook Web.
- Stop and hand off if Outlook requires login, MFA, CAPTCHA, or account approval.
- Keep replies plain text in v1. Do not add HTML, tables, or inline images.
- Never commit cookies, local browser profiles, exported inbox data, or user-specific secrets.
- Treat the date arguments as disambiguation hints, not as guaranteed server-side filters.

## Notes

- The browser script reuses an existing controllable Chrome debugging session when possible.
- If no controllable Chrome session exists, the script can launch a temporary Chrome instance and import only Outlook-related cookies for the current run.
- The script prints structured JSON so another agent can decide whether to continue, verify, or hand off.

## References

- Read `references/outlook-web-workflow.md` for command contracts, browser fallback behavior, and handoff conditions.
