---
name: chromium-password-store
description: "Safely insert or update saved logins in Chromium-style browser stores on macOS, including ChatGPT Atlas-style profiles. Use when a user wants an agent to back up the browser login database, encrypt a password with the browser-compatible method, and save credentials without exposing them in logs."
---

# Chromium Password Store

## Overview

Use this skill when the user wants browser credentials written directly into a Chromium-style `Login Data` database. It is designed for macOS flows where the browser expects passwords encrypted with the same `Safe Storage` key material that Chromium-derived browsers use.

## Quick Start

1. Identify the target browser profile and its `Login Data` database.
2. Close the browser before editing the database.
3. Read the password from `stdin` or from Keychain, never from a command-line flag.
4. Back up `Login Data` before every write.
5. Reopen the browser and verify the login entry exists.

## Workflow

### 1. Resolve the correct profile

- Prefer an explicit `Login Data` path when the user gives one.
- If the browser uses a Chromium-style `Local State` file, you can resolve the last active profile from `profile.last_used`.
- For Atlas-like browsers, the active profile often lives under a `user-data-dir` with profile subdirectories such as `Default` or `user-...`.

### 2. Protect the existing store

- Never edit the database while the browser is still running.
- Always create a timestamped backup before modifying `Login Data`.
- Treat `Login Data`, `Login Data-journal`, and backup files as sensitive local artifacts. Never commit them.

### 3. Source the secret safely

- Pass the password on `stdin`, or pipe it from Keychain lookup output.
- Do not place passwords in shell history or commit them to files.
- Use `scripts/upsert_chromium_login.py` to derive the browser-compatible encryption key from macOS Keychain and insert the encrypted credential.

Example usage with a known database path:

```bash
printf '%s' "$PASSWORD" | python3 scripts/upsert_chromium_login.py \
  --login-db "$HOME/Library/Application Support/com.openai.atlas/browser-data/host/Default/Login Data" \
  --origin-url "https://example.com/" \
  --action-url "https://example.com/login" \
  --signon-realm "https://example.com/" \
  --username "user@example.com" \
  --display-name "Example"
```

Example usage with a Chromium-style user-data directory and active profile detection:

```bash
security find-internet-password -s "example.com" -w | python3 scripts/upsert_chromium_login.py \
  --user-data-dir "$HOME/Library/Application Support/com.openai.atlas/browser-data/host" \
  --active-profile-from-local-state \
  --origin-url "https://example.com/" \
  --action-url "https://example.com/login" \
  --signon-realm "https://example.com/" \
  --username "user@example.com" \
  --display-name "Example"
```

### 4. Verify after writing

- Confirm the row exists in `logins` after insertion.
- Reopen the browser after the write completes.
- If the browser rewrites the row on launch, check whether you targeted the wrong profile.

## Safety Rules

- Never print the plaintext password.
- Never commit browser databases, cookies, backups, or local state files.
- Never publish absolute user paths, account emails, or domain-specific secrets in a reusable skill.
- If the browser is managed by MDM, enterprise policy, or sync constraints, ask before modifying the store.
