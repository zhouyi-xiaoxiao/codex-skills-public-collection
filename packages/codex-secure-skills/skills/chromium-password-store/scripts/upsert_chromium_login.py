#!/usr/bin/env python3
"""Back up and upsert a login in a Chromium-style Login Data database on macOS."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from Crypto.Cipher import AES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Insert or update a login entry in a Chromium-style Login Data "
            "database using macOS Safe Storage-compatible encryption."
        )
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--login-db",
        type=Path,
        help="Path to the target Chromium-style Login Data SQLite database.",
    )
    source_group.add_argument(
        "--user-data-dir",
        type=Path,
        help=(
            "Path to a Chromium-style user data directory that contains Local "
            "State and profile subdirectories."
        ),
    )

    parser.add_argument(
        "--profile-name",
        help="Profile directory name under --user-data-dir, such as Default.",
    )
    parser.add_argument(
        "--active-profile-from-local-state",
        action="store_true",
        help="Resolve the last-used profile from Local State under --user-data-dir.",
    )
    parser.add_argument("--origin-url", required=True, help="origin_url value.")
    parser.add_argument(
        "--action-url",
        required=True,
        help="action_url value, usually the login form POST target or page URL.",
    )
    parser.add_argument(
        "--signon-realm",
        required=True,
        help="signon_realm value, usually the site origin with trailing slash.",
    )
    parser.add_argument("--username", required=True, help="username_value to store.")
    parser.add_argument(
        "--display-name",
        default="",
        help="Optional display_name shown in some password managers.",
    )
    parser.add_argument(
        "--safe-storage-service",
        default="Chrome Safe Storage",
        help=(
            "macOS Keychain service name used to derive the Chromium-compatible "
            "encryption key. Defaults to Chrome Safe Storage."
        ),
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Directory for timestamped backups. Defaults to <db-dir>/backups.",
    )
    parser.add_argument(
        "--replace-matching-realm",
        action="store_true",
        default=True,
        help=(
            "Replace any existing entry with the same signon_realm and username. "
            "Enabled by default."
        ),
    )
    parser.add_argument(
        "--no-replace-matching-realm",
        dest="replace_matching_realm",
        action="store_false",
        help="Do not delete an existing matching entry before insert.",
    )
    return parser.parse_args()


def resolve_login_db(args: argparse.Namespace) -> Path:
    if args.login_db:
        return args.login_db.expanduser().resolve()

    user_data_dir = args.user_data_dir.expanduser().resolve()
    if args.active_profile_from_local_state:
        local_state_path = user_data_dir / "Local State"
        local_state = json.loads(local_state_path.read_text())
        profile_name = local_state.get("profile", {}).get("last_used")
        if not profile_name:
            raise SystemExit("Could not resolve profile.last_used from Local State.")
    elif args.profile_name:
        profile_name = args.profile_name
    else:
        raise SystemExit(
            "When using --user-data-dir, supply --profile-name or "
            "--active-profile-from-local-state."
        )

    return (user_data_dir / profile_name / "Login Data").resolve()


def read_password_from_stdin() -> str:
    if sys.stdin.isatty():
        raise SystemExit("Refusing to read a secret from an interactive TTY. Pipe it on stdin.")
    secret = sys.stdin.read()
    if not secret:
        raise SystemExit("No password received on stdin.")
    return secret.rstrip("\n")


def get_safe_storage_secret(service_name: str) -> bytes:
    try:
        value = subprocess.check_output(
            ["security", "find-generic-password", "-s", service_name, "-w"],
            text=True,
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"Could not read Keychain item '{service_name}'. "
            "Check the service name for this browser."
        ) from exc
    return value.encode("utf-8")


def encrypt_password(password: str, safe_storage_secret: bytes) -> bytes:
    key = hashlib.pbkdf2_hmac("sha1", safe_storage_secret, b"saltysalt", 1003, dklen=16)
    raw = password.encode("utf-8")
    pad = 16 - (len(raw) % 16)
    raw += bytes([pad]) * pad
    encrypted = AES.new(key, AES.MODE_CBC, b" " * 16).encrypt(raw)
    return b"v10" + encrypted


def backup_database(login_db: Path, backup_dir: Path | None) -> Path:
    dest_dir = backup_dir or (login_db.parent / "backups")
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = dest_dir / f"{login_db.name}.{stamp}.bak"
    shutil.copy2(login_db, backup)

    journal = login_db.with_name(f"{login_db.name}-journal")
    if journal.exists():
        shutil.copy2(journal, dest_dir / f"{journal.name}.{stamp}.bak")

    return backup


def chrome_timestamp_now() -> int:
    return int((time.time() + 11644473600) * 1_000_000)


def upsert_login(args: argparse.Namespace, login_db: Path, encrypted_password: bytes) -> None:
    now = chrome_timestamp_now()
    connection = sqlite3.connect(login_db)
    try:
        cursor = connection.cursor()
        if args.replace_matching_realm:
            cursor.execute(
                "DELETE FROM logins WHERE signon_realm = ? AND username_value = ?",
                (args.signon_realm, args.username),
            )

        cursor.execute(
            """
            INSERT INTO logins (
                origin_url, action_url, username_element, username_value, password_element,
                password_value, submit_element, signon_realm, date_created,
                blacklisted_by_user, scheme, password_type, times_used, form_data,
                display_name, icon_url, federation_url, skip_zero_click,
                generation_upload_status, possible_username_pairs, date_last_used,
                moving_blocked_for, date_password_modified, sender_email, sender_name,
                date_received, sharing_notification_displayed, keychain_identifier,
                sender_profile_image_url, date_last_filled, actor_login_approved
            ) VALUES (?, ?, '', ?, '', ?, '', ?, ?, 0, 0, 0, 0, NULL, ?, '', NULL, 0, 0,
                      NULL, 0, NULL, ?, NULL, NULL, NULL, 0, NULL, NULL, 0, 0)
            """,
            (
                args.origin_url,
                args.action_url,
                args.username,
                encrypted_password,
                args.signon_realm,
                now,
                args.display_name,
                now,
            ),
        )
        connection.commit()

        row = cursor.execute(
            "SELECT origin_url, username_value, length(password_value) "
            "FROM logins WHERE signon_realm = ? AND username_value = ? "
            "ORDER BY id DESC LIMIT 1",
            (args.signon_realm, args.username),
        ).fetchone()
        if not row:
            raise SystemExit("Insert appeared to succeed, but the verification readback failed.")

        print(f"Inserted login for {row[1]} at {row[0]}")
        print(f"Encrypted password blob length: {row[2]}")
    finally:
        connection.close()


def main() -> None:
    args = parse_args()
    login_db = resolve_login_db(args)
    if not login_db.exists():
        raise SystemExit(f"Login database not found: {login_db}")

    backup = backup_database(login_db, args.backup_dir)
    password = read_password_from_stdin()
    safe_storage_secret = get_safe_storage_secret(args.safe_storage_service)
    encrypted_password = encrypt_password(password, safe_storage_secret)
    upsert_login(args, login_db, encrypted_password)
    print(f"Backup created at: {backup}")


if __name__ == "__main__":
    main()
