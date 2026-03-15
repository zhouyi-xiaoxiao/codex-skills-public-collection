# Gmail GWS Codex Kit

Portable Gmail access for Codex using `gws`, a local OAuth refresh flow, and a Codex skill.

From the monorepo root, work from this package directory:

```bash
cd packages/gmail-gws-codex-kit
```

## What this gives you

- `gws-gmail`: a wrapper that refreshes an access token and runs `gws gmail`
- `gws-gmail-auth`: a local OAuth helper that writes a working `authorized_user` file
- `gmail-gws` Codex skill for future chats
- an `AGENTS.md` block so generic email requests can mention both Outlook and Gmail

## Install

```bash
./install.sh
```

If `gws` is missing and `npm` is available, the installer will install:

```bash
@googleworkspace/cli@0.8.0
```

## First-time auth

1. Put your Desktop OAuth client JSON at:

```text
~/.config/gws/client_secret.json
```

2. Run:

```bash
gws-gmail-auth
```

3. Restart Codex so the new skill is visible in future chats.

## Local-only secrets

- Keep the OAuth client JSON and refreshed authorized-user file on your machine only.
- Do not commit `~/.config/gws/client_secret.json` or `~/.config/gws/gmail-authorized-user.json`.
- The package ships wrapper logic only; it does not bundle credentials.

## Daily use

```bash
gws-gmail +triage --max 3
gws-gmail users messages list --params '{"userId":"me","maxResults":5}'
gws-gmail users messages get --params '{"userId":"me","id":"MESSAGE_ID","format":"full"}'
gws-gmail +send --to you@example.com --subject 'Hello' --body 'Test'
```

## Important limitation

If your Google OAuth app stays in `Testing` mode, Google may issue a refresh token with a short lifetime.

If `gws-gmail` starts failing with `invalid_grant`, rerun:

```bash
gws-gmail-auth
```
