#!/usr/bin/env python3
import argparse
import datetime as dt
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile
from typing import Optional


DEFAULT_HOST = os.environ.get("ISAMBARD_HOST_ALIAS", "replace-me.cluster.example")
DEFAULT_REMOTE_ROOT = os.environ.get("ISAMBARD_REMOTE_ROOT", "~/codex_jobs")
DEFAULT_LOCAL_ROOT = os.environ.get(
    "ISAMBARD_LOCAL_ROOT", "~/.codex/isambard_artifacts"
)
DEFAULT_IDENTITY = os.environ.get("ISAMBARD_IDENTITY_FILE", "~/.ssh/id_ed25519")
DEFAULT_CLIFTON = os.environ.get("ISAMBARD_CLIFTON_BIN", "~/.local/bin/clifton")


def run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = True,
    timeout: Optional[int] = None,
) -> subprocess.CompletedProcess:
    kwargs = {
        "text": True,
        "check": check,
        "timeout": timeout,
    }
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    return subprocess.run(cmd, **kwargs)


def print_block(title: str, text: str) -> None:
    print(f"== {title} ==")
    print(text.rstrip() or "(empty)")


def expand(path: str) -> str:
    return str(pathlib.Path(path).expanduser())


def resolve_clifton() -> str:
    found = run(["bash", "-lc", "command -v clifton"], check=False)
    if found.returncode == 0 and (found.stdout or "").strip():
        return (found.stdout or "").strip()
    fallback = expand(DEFAULT_CLIFTON)
    if pathlib.Path(fallback).exists():
        return fallback
    return "clifton"


def ssh_cmd(host: str, remote_cmd: str) -> list[str]:
    return ["ssh", host, remote_cmd]


def scp_to(host: str, src: str, dst: str) -> list[str]:
    return ["scp", src, f"{host}:{dst}"]


def scp_from(host: str, src: str, dst: str) -> list[str]:
    return ["scp", "-r", f"{host}:{src}", dst]


def cmd_auth(args: argparse.Namespace) -> int:
    identity = expand(args.identity)
    clifton_bin = resolve_clifton()
    cmd = [
        clifton_bin,
        "auth",
        "--identity",
        identity,
        "--write-config",
        "true",
    ]
    if args.no_browser:
        cmd.extend(["--open-browser", "false"])
    print(f"Running: {' '.join(shlex.quote(x) for x in cmd)}")
    cp = run(cmd, check=False, capture=True)
    if cp.stdout:
        print(cp.stdout.rstrip())
    if cp.stderr:
        print(cp.stderr.rstrip(), file=sys.stderr)
    return cp.returncode


def cmd_aliases(args: argparse.Namespace) -> int:
    cfg = pathlib.Path(expand("~/.ssh/config_clifton"))
    if not cfg.exists():
        print("config_clifton not found. Run `isbard auth` first.", file=sys.stderr)
        return 1
    aliases: list[str] = []
    for line in cfg.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("Host "):
            continue
        hosts = line[5:].split()
        for h in hosts:
            if h.startswith("jump."):
                continue
            if "*" in h:
                continue
            aliases.append(h)
    aliases = sorted(set(aliases))
    if not aliases:
        print("No concrete aliases found.")
        return 1
    for alias in aliases:
        print(alias)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    ok = True
    checks: list[tuple[str, bool, str]] = []
    for bin_name in ("ssh", "scp"):
        cp = run(["bash", "-lc", f"command -v {shlex.quote(bin_name)}"], check=False)
        checks.append(
            (
                f"binary:{bin_name}",
                cp.returncode == 0,
                (cp.stdout or "").strip() or (cp.stderr or "").strip(),
            )
        )
    clifton_bin = resolve_clifton()
    clifton_ok = pathlib.Path(clifton_bin).exists() or clifton_bin == "clifton"
    checks.append(("binary:clifton", clifton_ok, clifton_bin))
    cfg = pathlib.Path(expand("~/.ssh/config_clifton"))
    checks.append(("file:~/.ssh/config_clifton", cfg.exists(), str(cfg)))
    main_cfg = pathlib.Path(expand("~/.ssh/config"))
    checks.append(("file:~/.ssh/config", main_cfg.exists(), str(main_cfg)))
    if main_cfg.exists():
        include_ok = "config_clifton" in main_cfg.read_text(encoding="utf-8")
        checks.append(("config include", include_ok, "Include config_clifton"))
    cp = run(
        ssh_cmd(args.host, "echo SSH_OK"),
        check=False,
        capture=True,
        timeout=args.ssh_timeout,
    )
    checks.append(
        (
            f"ssh:{args.host}",
            cp.returncode == 0 and "SSH_OK" in (cp.stdout or ""),
            (cp.stdout or cp.stderr or "").strip(),
        )
    )
    for name, passed, detail in checks:
        status = "OK" if passed else "FAIL"
        print(f"[{status}] {name}: {detail}")
        if not passed:
            ok = False
    return 0 if ok else 1


def cmd_run(args: argparse.Namespace) -> int:
    cp = run(
        ssh_cmd(args.host, args.cmd),
        check=False,
        capture=True,
        timeout=args.timeout,
    )
    print_block("STDOUT", cp.stdout or "")
    print_block("STDERR", cp.stderr or "")
    print(f"EXIT_CODE={cp.returncode}")
    return cp.returncode


def render_sbatch_script(workdir: str, user_cmd: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail
mkdir -p {shlex.quote(workdir)}
cd {shlex.quote(workdir)}
{user_cmd}
"""


def cmd_submit(args: argparse.Namespace) -> int:
    ts = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    job_name = args.job_name or f"codex_{ts}"
    remote_root = args.remote_root
    remote_dir = f"{remote_root}/{job_name}"
    remote_script = f"{remote_dir}/job.sh"
    local_script_fd, local_script_path = tempfile.mkstemp(prefix="isbard_", suffix=".sh")
    os.close(local_script_fd)
    try:
        script = render_sbatch_script(remote_dir, args.cmd)
        pathlib.Path(local_script_path).write_text(script, encoding="utf-8")
        run(ssh_cmd(args.host, f"mkdir -p {shlex.quote(remote_dir)}"), check=True)
        run(scp_to(args.host, local_script_path, remote_script), check=True)
        run(
            ssh_cmd(args.host, f"chmod +x {shlex.quote(remote_script)}"),
            check=True,
        )
        sbatch_parts = ["sbatch", "--parsable", f"--job-name={job_name}"]
        if args.partition:
            sbatch_parts.append(f"--partition={args.partition}")
        if args.time:
            sbatch_parts.append(f"--time={args.time}")
        if args.cpus:
            sbatch_parts.append(f"--cpus-per-task={args.cpus}")
        if args.mem:
            sbatch_parts.append(f"--mem={args.mem}")
        sbatch_parts.append(remote_script)
        submit_cmd = " ".join(shlex.quote(x) for x in sbatch_parts)
        cp = run(ssh_cmd(args.host, submit_cmd), check=True)
        raw = (cp.stdout or "").strip()
        job_id = raw.split(";")[0].strip()
        if not re.fullmatch(r"\d+", job_id):
            print(f"Unexpected sbatch output: {raw}", file=sys.stderr)
            return 2
        print(f"JOB_ID={job_id}")
        print(f"REMOTE_DIR={remote_dir}")
        print(f"REMOTE_SCRIPT={remote_script}")
        return 0
    finally:
        try:
            os.remove(local_script_path)
        except OSError:
            pass


def cmd_status(args: argparse.Namespace) -> int:
    squeue = run(
        ssh_cmd(
            args.host,
            f"squeue -j {shlex.quote(args.job_id)} -h -o '%i|%T|%M|%R'",
        ),
        check=False,
        capture=True,
    )
    out = (squeue.stdout or "").strip()
    if out:
        print(out)
        return 0
    sacct = run(
        ssh_cmd(
            args.host,
            f"sacct -j {shlex.quote(args.job_id)} --format=JobID,State,Elapsed,ExitCode -P -n",
        ),
        check=False,
        capture=True,
    )
    sacct_out = (sacct.stdout or "").strip()
    if sacct_out:
        print(sacct_out)
        return 0
    if squeue.stderr:
        print(squeue.stderr.rstrip(), file=sys.stderr)
    if sacct.stderr:
        print(sacct.stderr.rstrip(), file=sys.stderr)
    return 1


def cmd_cancel(args: argparse.Namespace) -> int:
    cp = run(
        ssh_cmd(args.host, f"scancel {shlex.quote(args.job_id)}"),
        check=False,
        capture=True,
    )
    if cp.stdout:
        print(cp.stdout.rstrip())
    if cp.stderr:
        print(cp.stderr.rstrip(), file=sys.stderr)
    return cp.returncode


def cmd_fetch(args: argparse.Namespace) -> int:
    local_root = pathlib.Path(expand(args.local))
    local_root.mkdir(parents=True, exist_ok=True)
    cp = run(
        scp_from(args.host, args.remote, str(local_root)),
        check=False,
        capture=True,
    )
    if cp.stdout:
        print(cp.stdout.rstrip())
    if cp.stderr:
        print(cp.stderr.rstrip(), file=sys.stderr)
    if cp.returncode == 0:
        print(f"FETCHED_TO={local_root}")
    return cp.returncode


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Isambard helper CLI for Codex workflows.")
    p.add_argument("--host", default=DEFAULT_HOST, help=f"SSH host alias (default: {DEFAULT_HOST})")
    sub = p.add_subparsers(dest="subcommand", required=True)

    auth = sub.add_parser("auth", help="Authenticate with Clifton and write SSH config.")
    auth.add_argument("--identity", default=DEFAULT_IDENTITY, help="SSH private key path.")
    auth.add_argument("--no-browser", action="store_true", help="Do not auto-open browser.")
    auth.set_defaults(func=cmd_auth)

    aliases = sub.add_parser("aliases", help="List concrete host aliases from config_clifton.")
    aliases.set_defaults(func=cmd_aliases)

    doctor = sub.add_parser("doctor", help="Check local prerequisites and basic SSH readiness.")
    doctor.add_argument("--ssh-timeout", type=int, default=10, help="SSH check timeout seconds.")
    doctor.set_defaults(func=cmd_doctor)

    run_p = sub.add_parser("run", help="Run a synchronous remote command via SSH.")
    run_p.add_argument("--cmd", required=True, help="Remote command to execute.")
    run_p.add_argument("--timeout", type=int, default=0, help="Timeout seconds (0 disables).")
    run_p.set_defaults(func=cmd_run)

    submit = sub.add_parser("submit", help="Submit a SLURM job with sbatch.")
    submit.add_argument("--cmd", required=True, help="Command executed in job script.")
    submit.add_argument("--job-name", default="", help="SLURM job name.")
    submit.add_argument("--partition", default="", help="SLURM partition.")
    submit.add_argument("--time", default="", help="SLURM time, e.g. 00:30:00.")
    submit.add_argument("--cpus", type=int, default=0, help="cpus-per-task.")
    submit.add_argument("--mem", default="", help="SLURM --mem value, e.g. 8G.")
    submit.add_argument(
        "--remote-root",
        default=DEFAULT_REMOTE_ROOT,
        help=f"Remote root dir (default: {DEFAULT_REMOTE_ROOT}).",
    )
    submit.set_defaults(func=cmd_submit)

    status = sub.add_parser("status", help="Query SLURM status for a job.")
    status.add_argument("--job-id", required=True, help="SLURM job ID.")
    status.set_defaults(func=cmd_status)

    cancel = sub.add_parser("cancel", help="Cancel a SLURM job.")
    cancel.add_argument("--job-id", required=True, help="SLURM job ID.")
    cancel.set_defaults(func=cmd_cancel)

    fetch = sub.add_parser("fetch", help="Fetch remote output files to local.")
    fetch.add_argument("--remote", required=True, help="Remote file or directory path.")
    fetch.add_argument(
        "--local",
        default=DEFAULT_LOCAL_ROOT,
        help=f"Local target directory (default: {DEFAULT_LOCAL_ROOT}).",
    )
    fetch.set_defaults(func=cmd_fetch)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if hasattr(args, "timeout") and args.timeout == 0:
        args.timeout = None
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
