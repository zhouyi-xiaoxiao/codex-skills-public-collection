# Security Policy

## Scope

This repository is intended to hold reusable skill logic only. It must not contain personal credentials, browser databases, cookies, exported email content, API keys, private callback URLs, or user-specific host paths.

## Required Safeguards

- Read secrets from `stdin` or Keychain, never from committed files.
- Back up browser password stores locally before modification, but never commit those backups.
- Keep repository examples generic. Use placeholder domains and emails in docs.
- Treat any CAPTCHA, SMS, biometric, passkey, hardware-key, or payment challenge as a manual handoff point.

## Explicit Non-Goals

- CAPTCHA bypass
- anti-bot evasion
- token forgery
- credential stuffing
- importing or exporting another user's secrets

## Reporting

If you discover that a secret or local artifact was committed by mistake, rotate it first, then remove it from repository history before sharing the repo further.
