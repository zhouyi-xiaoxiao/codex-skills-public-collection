# Portable Codex Config Template

Portable Codex and MCP configuration template for macOS.

- Public-safe template extracted from a working multi-device setup
- Secrets policy: keep credentials local (Keychain / re-login), never commit tokens
- Profile model: `core` / `research` / `ops`
- MCP toggles by host: `ENABLE_MCP_GITHUB` / `ENABLE_MCP_OUTLOOK` / `ENABLE_MCP_IONOS`

## Entry point

Use `bin/codex-portable` directly or install symlink into `~/.local/bin`.

From the monorepo root, work from this package directory:

```bash
cd packages/codex-portable-config
```

## One-command sync (recommended)

```bash
codex-portable sync --host <host-id> --profile research
```

This command performs:
- `git pull --rebase --autostash`
- render + blue-green switch for `~/.codex/config.toml` and `~/.ssh/config`
- sync all repo skills into `~/.codex/skills`
- `doctor` validation with rollback on failure
- optional cloud backup

If you want this device to also publish local config/script updates:

```bash
codex-portable sync --host <host-id> --profile research --push
```

## One-command full automation

```bash
codex-portable enable --host <host-id> --profile research --interval-minutes 30
```

This sets default host/profile in `~/.zshrc`, installs autosync, and runs an initial full sync.
Autosync defaults to `--skip-backup`; backup can still be run manually via `codex-portable backup --target onedrive`.

## Public-template note

- Keep only `hosts/host.example.env` in version control.
- Create your real host file locally and do not commit it.
- Replace placeholder values such as `replace-me.cluster.example`, `your-user/your-portable-config-repo`, and `/Users/<user>` before using the template.
