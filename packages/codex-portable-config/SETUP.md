# Setup (macOS)

## 1. Clone repo

```bash
git clone https://github.com/zhouyi-xiaoxiao/codex-skills-public-collection.git
cd codex-skills-public-collection/packages/codex-portable-config
```

## 2. Prepare host file

```bash
cp hosts/host.example.env hosts/<your-host-id>.env
# edit values for your machine
```

Keep the new host file local only. Do not commit it back to this public template repo.

## 3. Bootstrap

```bash
./bin/codex-portable bootstrap --host <your-host-id> --profile research
```

Available profiles: `core`, `research`, `ops`.

If you want to disable specific MCP servers on a host, set these in `hosts/<your-host-id>.env`:
- `ENABLE_MCP_GITHUB=0`
- `ENABLE_MCP_OUTLOOK=0`
- `ENABLE_MCP_IONOS=0`

## 4. Re-login for local credentials if needed

```bash
isbard auth
# and re-login MCPs that use device flow (e.g. Outlook)
```

## 5. Validate

```bash
codex-portable doctor --host <your-host-id> --profile research
```

## 6. Optional cloud backup

```bash
codex-portable backup --target onedrive --host <your-host-id>
```

You can omit `--host` when only one host file exists, or set `CODEX_PORTABLE_HOST=<your-host-id>`.

## 7. Daily cross-device sync (recommended)

Apply cloud changes locally and keep MCP/skills in sync:

```bash
codex-portable sync --host <your-host-id> --profile research
```

If this device should also publish local changes to GitHub:

```bash
codex-portable sync --host <your-host-id> --profile research --push
```

## 8. One-command automation setup (recommended)

```bash
codex-portable enable --host <your-host-id> --profile research --interval-minutes 30
```

It will:
- write default host/profile and aliases to `~/.zshrc`
- install autosync (with fallback to `--no-load` if current shell cannot load launchd)
- run an initial full sync immediately
## 9. Optional automatic sync (launchd, manual control)

Install 30-minute autosync:

```bash
codex-portable autosync install --host <your-host-id> --profile research --interval-minutes 30
```

Default autosync skips OneDrive backup (`--skip-backup`) to avoid cloud-drive permission issues in background jobs.
If you explicitly want backup in autosync:

```bash
codex-portable autosync install --host <your-host-id> --profile research --interval-minutes 30 --with-backup
```

If launchd cannot be loaded in current shell context, generate plist only:

```bash
codex-portable autosync install --host <your-host-id> --profile research --interval-minutes 30 --no-load
```

Check status:

```bash
codex-portable autosync status --host <your-host-id>
```

Remove autosync:

```bash
codex-portable autosync uninstall --host <your-host-id>
```
