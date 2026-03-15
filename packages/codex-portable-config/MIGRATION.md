# Migration Runbook

## From this machine to another Mac

1. Clone the public collection and change into `packages/codex-portable-config`.
2. Create `hosts/<new-host-id>.env` from template.
3. Run:

```bash
./bin/codex-portable bootstrap --host <new-host-id> --profile research
```

4. Rebuild credentials locally (not synced):
- Codex/OpenAI auth
- Outlook MCP device login
- SSH onboarding auth (`isbard auth`)

5. Validate:

```bash
codex-portable doctor --host <new-host-id> --profile research
```

## Ongoing sync

```bash
codex-portable sync --host <host-id> --profile research
```

## Quick automation on a new machine

```bash
codex-portable enable --host <host-id> --profile research --interval-minutes 30
```

Blue-green switch behavior:
- keeps `<target>.bak`
- writes timestamp backup under `~/.codex.backups/<timestamp>/`
- prints a short diff summary
- supports rollback via `--doctor-cmd`

If this machine should also push local updates to cloud:

```bash
codex-portable sync --host <host-id> --profile research --push
```

Optional automatic sync:

```bash
codex-portable autosync install --host <host-id> --profile research --interval-minutes 30
```

By default autosync runs with `--skip-backup` (stable in launchd background context).
If you need OneDrive backup in autosync, add `--with-backup`.

If current shell cannot load launchd GUI jobs, create plist first:

```bash
codex-portable autosync install --host <host-id> --profile research --interval-minutes 30 --no-load
```

## Backup mirror to cloud storage

```bash
codex-portable backup --target onedrive --host <host-id>
```
