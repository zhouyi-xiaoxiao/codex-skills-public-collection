---
name: isambard-automation
description: Use Isambard-style HPC resources via SSH and SLURM for heavy compute, remote command execution, job submission, status tracking, and artifact retrieval. Trigger when users ask to run or accelerate workloads on institutional cluster infrastructure, including requests like "用ISBARD跑", "run on Isambard", "submit SLURM job", "check Isambard job status", or "fetch Isambard results".
---

# Isambard Automation

Use the local CLI wrapper:

`python3 ~/.codex/skills/isambard-automation/scripts/isbard_cli.py <subcommand> ...`

or:

`isbard <subcommand> ...`

## First-time and Session Prep

1. Run `isbard doctor`.
2. If certificate is missing or expired, run `isbard auth`.
3. Verify alias availability with `isbard aliases`.

## Subcommands

- `isbard auth`: start local SSH onboarding and write SSH config.
- `isbard doctor`: check local prerequisites and basic SSH readiness.
- `isbard run --cmd "<command>"`: run a synchronous remote command.
- `isbard submit --cmd "<command>"`: submit a SLURM job and return job ID.
- `isbard status --job-id <id>`: check job status.
- `isbard cancel --job-id <id>`: cancel job.
- `isbard fetch --remote <path> [--local <dir>]`: download output artifacts.
- `isbard aliases`: list host aliases from `~/.ssh/config_clifton`.

## Defaults

- Host alias default: `replace-me.cluster.example`
- Remote root default: `~/codex_jobs`
- Local artifact root default: `~/.codex/isambard_artifacts`
- Identity default: `~/.ssh/id_ed25519`

Override with environment variables:

- `ISAMBARD_HOST_ALIAS`
- `ISAMBARD_REMOTE_ROOT`
- `ISAMBARD_LOCAL_ROOT`
- `ISAMBARD_IDENTITY_FILE`

## Notes

- If remote login returns maintenance notices, stop and check the relevant cluster status page.
- Prefer `submit/status/fetch` for long-running jobs.
- Keep secrets out of command text.
