---
name: gmail-gws
description: Use this skill for Gmail tasks in Codex when the user wants to read, search, triage, send, or modify Gmail messages via the local gws-gmail wrapper instead of Outlook or browser automation. Also use it when the user mentions email generally and Gmail should be offered as an option.
---

# Gmail via gws-gmail

Use the local wrapper:

```bash
gws-gmail ...
```

Do not prefer raw `gws gmail` for this setup. The wrapper refreshes a working access token first and then passes it through `GOOGLE_WORKSPACE_CLI_TOKEN`.

## Provider routing

If the user asks for email help and does not name a provider:

- mention both Outlook and Gmail
- use Gmail when the user wants the Gmail account specifically

## Common commands

```bash
gws-gmail +triage --max 3
gws-gmail users messages list --params '{"userId":"me","maxResults":5}'
gws-gmail users messages get --params '{"userId":"me","id":"MESSAGE_ID","format":"full"}'
gws-gmail +send --to you@example.com --subject 'Hello' --body 'Test'
gws-gmail users messages modify --params '{"userId":"me","id":"MESSAGE_ID"}' --json '{"addLabelIds":["STARRED"]}'
```

## Auth recovery

If `gws-gmail` fails while refreshing the token:

```bash
gws-gmail-auth
```

The resulting authorized-user file lives at:

```text
~/.config/gws/gmail-authorized-user.json
```
