#!/usr/bin/env python3
"""Queue one continuation to an exact local Codex daemon thread after a reset.

Dry-run unless --run. Does not read transcripts, change config, redeem credits,
install a scheduler, retry a failed delivery, or confirm execution/completion.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

UTC = dt.timezone.utc


def timestamp(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use ISO8601 with date, time and UTC offset") from exc
    if "T" not in value or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("date, time and explicit UTC offset are required")
    return parsed.astimezone(UTC)


def existing_absolute(value):
    path = Path(value).expanduser()
    if not path.is_absolute() or not path.exists():
        raise argparse.ArgumentTypeError("path must be absolute and already exist")
    return path.resolve()


def session_uuid(value):
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("exact session UUID is required") from exc
    if str(parsed) != value.lower() or parsed.int == 0:
        raise argparse.ArgumentTypeError("use a nonzero, canonical session UUID")
    return str(parsed)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session", required=True, type=session_uuid)
    p.add_argument("--project", required=True, type=existing_absolute)
    p.add_argument("--codex-home", required=True, type=existing_absolute)
    p.add_argument("--codex", required=True, type=existing_absolute)
    p.add_argument("--reset-at", required=True, type=timestamp)
    p.add_argument("--buffer-minutes", type=int, default=10)
    p.add_argument("--max-wait-minutes", type=int, default=720)
    p.add_argument("--max-lateness-seconds", type=int, default=300)
    p.add_argument("--timeout-seconds", type=int, default=120)
    p.add_argument("--message", required=True)
    p.add_argument("--log", required=True, type=Path)
    p.add_argument("--run", action="store_true")
    return p


def execute(args, now=lambda: dt.datetime.now(UTC), sleep=time.sleep,
            runner=subprocess.run, monotonic=time.monotonic):
    # These selectors can redirect state, identity or the executor despite an
    # explicit CODEX_HOME. Refuse unsupported setups instead of changing them.
    unsupported = (
        "CODEX_SQLITE_HOME", "CODEX_EXEC_SERVER_URL",
        "CODEX_EXEC_SERVER_NOISE_REGISTRY_URL", "CODEX_EXEC_SERVER_NOISE_ENVIRONMENT_ID",
        "CODEX_EXEC_SERVER_NOISE_AUTH_TOKEN", "CODEX_EXEC_SERVER_NOISE_CHATGPT_ACCOUNT_ID",
        "OPENAI_FEDERATION_RULE_ID", "OPENAI_IDENTITY_TOKEN_FILE",
        "OPENAI_WORKLOAD_IDENTITY_CONTEXT",
    )
    present = [name for name in unsupported if name in os.environ]
    if present:
        raise ValueError("unsupported state/executor/identity overrides: " + ", ".join(present)
                         + "; use a verified native command for this environment")
    for name in ("project", "codex_home"):
        if not getattr(args, name).is_dir():
            raise ValueError(f"{name} must be an existing directory")
    if not args.codex.is_file():
        raise ValueError("codex must be an existing executable file")
    if os.name == "nt" and args.codex.suffix.lower() != ".exe":
        raise ValueError("Windows requires a verified native codex.exe, not a script wrapper")
    if os.name != "nt" and not os.access(args.codex, os.X_OK):
        raise ValueError("codex file is not executable")
    if not args.message.strip() or args.message.lstrip().startswith("/"):
        raise ValueError("provide a plain-language message, not a TUI slash command")
    if not 0 <= args.buffer_minutes <= 1440:
        raise ValueError("buffer-minutes must be 0..1440")
    if not 1 <= args.max_wait_minutes <= 1440:
        raise ValueError("max-wait-minutes must be 1..1440")
    if not 0 <= args.max_lateness_seconds <= 3600:
        raise ValueError("max-lateness-seconds must be 0..3600")
    if not 1 <= args.timeout_seconds <= 600:
        raise ValueError("timeout-seconds must be 1..600")
    log = args.log.expanduser()
    if not log.is_absolute() or not log.parent.is_dir() or log.exists():
        raise ValueError("log must be a new absolute path with an existing parent")
    target = args.reset_at + dt.timedelta(minutes=args.buffer_minutes)
    delay = (target - now()).total_seconds()
    if delay > args.max_wait_minutes * 60:
        raise ValueError("target exceeds maximum permitted wait")
    if delay < -args.max_lateness_seconds:
        raise ValueError("target has passed beyond maximum permitted lateness")
    command = [str(args.codex), "queue", "-C", str(args.project),
               "--thread", args.session, "--message", args.message, "--resume"]
    print(json.dumps({"dry_run": not args.run, "target_utc": target.isoformat(),
                      "cwd": str(args.project), "CODEX_HOME": str(args.codex_home),
                      "command": command}, ensure_ascii=False))
    if not args.run:
        return 0
    wait_budget = min(args.max_wait_minutes * 60,
                      max(delay, 0) + args.max_lateness_seconds + 60)
    # Exclusive receipt creation prevents accidental reruns of this same plan.
    # Output may include project details. POSIX permissions are owner-only;
    # on Windows use a directory whose ACL is already private to the user.
    fd = os.open(log, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as receipt:
        def record(kind, **fields):
            receipt.write(json.dumps({"time": now().isoformat(), "event": kind,
                                      **fields}, ensure_ascii=False) + "\n")
            receipt.flush()
        record("scheduled", session=args.session, target_utc=target.isoformat())
        started = monotonic()
        while True:
            remaining = (target - now()).total_seconds()
            if remaining <= 0:
                break
            if remaining > args.max_wait_minutes * 60:
                record("aborted_clock_change")
                return 4
            elapsed = monotonic() - started
            if elapsed >= wait_budget:
                record("aborted_wait_budget")
                return 4
            interval = min(remaining, 60, wait_budget - elapsed)
            sleep(interval)
        # A late wakeup can reach the target before the loop checks its budget.
        # Check monotonic elapsed time again before dispatch, even within wall lateness.
        if monotonic() - started > wait_budget:
            record("aborted_wait_budget")
            return 4
        if (now() - target).total_seconds() > args.max_lateness_seconds:
            record("aborted_late_wakeup")
            return 4
        env = os.environ.copy()
        env["CODEX_HOME"] = str(args.codex_home)
        record("dispatch_started")
        try:
            result = runner(command, cwd=args.project, env=env,
                            stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, encoding="utf-8", errors="replace",
                            timeout=args.timeout_seconds, check=False)
        except subprocess.TimeoutExpired:
            record("dispatch_timeout", delivery="unknown; do not retry automatically")
            return 124
        except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
            record("dispatch_error", error=str(exc), delivery="unknown; do not retry automatically")
            return 1
        record("dispatch_result", returncode=result.returncode,
               stdout=result.stdout, stderr=result.stderr)
        if result.returncode:
            return 1
        if "could not resume thread" in (result.stdout + result.stderr).casefold():
            record("resume_unconfirmed", delivery="queued; resume failed")
            return 3
        acknowledged = any(line.startswith("queued message ")
                           and line.endswith(f" for thread {args.session}.")
                           for line in result.stdout.casefold().splitlines())
        if not acknowledged:
            record("delivery_unconfirmed", delivery="unknown; inspect the thread before retrying")
            return 5
        record("queued", execution="not confirmed; inspect the target thread")
    return 0


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        return execute(args)
    except (ValueError, OSError) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
