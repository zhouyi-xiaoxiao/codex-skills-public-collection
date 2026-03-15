# Codex Skills Public Collection

This repository is a curated public collection of reusable Codex skills and related setup kits. It was assembled as a fresh public-safe export, with live personal configuration removed and package contents normalized for reuse.

Clone the collection:

```bash
git clone https://github.com/zhouyi-xiaoxiao/codex-skills-public-collection.git
cd codex-skills-public-collection
```

## Packages

| Package | Purpose | Who it's for | Install path | Required tools | Contents |
| --- | --- | --- | --- | --- | --- |
| `gmail-gws-codex-kit` | Gmail access for Codex via `gws-gmail`, local OAuth refresh, and a Codex skill | People who want Gmail alongside Outlook in Codex | `packages/gmail-gws-codex-kit/` | `bash`, `python3`, optional `npm`, Google OAuth desktop client | One skill plus wrapper scripts |
| `teaching-hours-claim-skill` | Reconstruct teaching-hour claims from email evidence and draft approval messages | Teaching assistants, tutors, markers, and hourly-paid teaching staff | `packages/teaching-hours-claim-skill/` | Codex skill runtime plus email access | One skill plus reference templates |
| `codex-secure-skills` | Security-focused skills for browser credential handling and verification recovery | People building careful account-recovery or credential-maintenance workflows | `packages/codex-secure-skills/` | `python3` for bundled script usage | Two standalone skills |
| `codex-portable-config` | Portable Codex and MCP configuration template for multi-device setups | People adapting a reusable local configuration template | `packages/codex-portable-config/` | `bash`, Codex, optional launchd/macOS automation tools | Template scripts, skills, and config scaffolding |

## How to use this repo

- Read the package-level `README.md` in the package you want to use.
- Copy skills into `~/.codex/skills/` only from the public-safe package directories in this repo.
- Keep OAuth files, tokens, cookies, local databases, and live host env files on your machine only.

See [SANITIZATION.md](SANITIZATION.md) for the export policy and [SECURITY.md](SECURITY.md) for safe reuse guidance.
