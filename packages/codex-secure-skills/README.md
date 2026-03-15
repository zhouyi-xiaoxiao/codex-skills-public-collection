# Codex Secure Skills

This repository packages two reusable Codex skills for safer account onboarding and browser credential handling on macOS.

Run the install commands below from the monorepo root.

## Included Skills

### `chromium-password-store`

- Backs up and updates saved logins in Chromium-style `Login Data` stores.
- Supports direct `Login Data` paths or `user-data-dir` resolution through `Local State`.
- Encrypts passwords with macOS `Safe Storage`-compatible key material instead of writing plaintext.

### `verification-recovery-handoff`

- Helps agents recover stalled onboarding flows through legitimate email links, session reuse, and first-party OAuth callbacks.
- Explicitly stops at CAPTCHA, 2FA, payment confirmation, and other human-only approval steps.
- Does not include CAPTCHA bypass, token forgery, or anti-abuse evasion guidance.

## Install

Copy one or both skill directories into your Codex skills directory:

```bash
mkdir -p "$HOME/.codex/skills"
cp -R packages/codex-secure-skills/skills/chromium-password-store "$HOME/.codex/skills/"
cp -R packages/codex-secure-skills/skills/verification-recovery-handoff "$HOME/.codex/skills/"
```

## Security Notes

- This repository contains no live credentials, browser databases, cookies, inbox exports, or account-specific URLs.
- Do not commit `Login Data`, `Cookies`, `Local State`, backups, or other local browser artifacts.
- Review [SECURITY.md](SECURITY.md) before adapting the scripts for another browser.

## License

MIT
