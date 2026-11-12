"""Read-only Windows host/backend probes. Run from normal PowerShell, not from a Codex tool.
Requires Python 3.11+, Codex, gh, and installed Playwright CLI. No login or config changes.
Native sandbox startup may request its normal Windows provisioning approval.
Reports contain no credential values; generated reports must not be committed.
"""
import argparse
import copy
import ctypes as c
import ctypes.wintypes as w
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
import uuid

BACKENDS = ("elevated", "unelevated", "mxc")
MARKER = "COURSE_PROBE_JSON:"


def toml_literal(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(map(toml_literal, value)) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(toml_literal(k) + " = " + toml_literal(v) for k, v in value.items()) + " }"
    raise ValueError("Unsupported TOML value")


def probe_profiles(original, denied_file):
    profiles = copy.deepcopy(original)
    profiles["course-open-probe"] = {"extends": ":workspace", "network": {"enabled": True}}
    profiles["course-probe"] = {
        "extends": "course-root",
        "filesystem": {denied_file.resolve().as_posix(): "deny"},
    }
    return profiles


def sandbox_command(codex, backend, profile, profiles, child):
    if backend not in BACKENDS:
        raise ValueError("Unknown backend")
    return [
        codex, "-c", "features.prefer_mxc=false",
        "-c", "windows.sandbox=" + toml_literal(backend),
        "-c", "permissions=" + toml_literal(profiles),
        "sandbox", "--include-managed-config", "--permission-profile", profile,
        "--", *child,
    ]


def summarize(code, stdout, stderr, timed_out=False):
    text = (stdout + "\n" + stderr).lower()
    patterns = {
        "http_401": r"\b401\b",
        "access_denied": r"access.denied|odmow|0xc0000022",
        "mxc_unavailable": r"native mxc is unavailable",
        "deny_reads_unsupported": r"cannot enforce deny-read",
        "sandbox_setup_failed": r"orchestrator_helper|sandbox failed|cap sid",
        "chrome_ipc": r"transactnamedpipe|crash server failed",
        "daemon_failed": r"daemon.*(?:exited|failed)",
        "unknown_profile": r"unknown.*(?:permission|profile)|not found.*profile",
    }
    return {
        "exit_code": code, "timed_out": timed_out,
        "error_tags": [tag for tag, pattern in patterns.items() if re.search(pattern, text)],
    }


def execute(argv, cwd, timeout=90):
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout, shell=False)
        summary = summarize(result.returncode, result.stdout, result.stderr)
        for line in result.stdout.splitlines():
            if line.startswith(MARKER):
                summary["probe"] = json.loads(line[len(MARKER):])
        return summary
    except subprocess.TimeoutExpired:
        return summarize(None, "", "", timed_out=True)
    except OSError as error:
        return {"exit_code": None, "launch_error": type(error).__name__}


def require_host(token):
    if (token.get("is_appcontainer") or token.get("is_restricted")
            or token.get("integrity_level") == "low"
            or token.get("account_kind") == "codex_sandbox_account"):
        raise RuntimeError("Run this probe from normal Windows PowerShell, outside Codex command execution.")


def token_info():
    if os.name != "nt":
        raise RuntimeError("Windows only")
    adv = c.WinDLL("advapi32", use_last_error=True)
    kernel = c.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    adv.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
    adv.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, w.LPVOID, w.DWORD, c.POINTER(w.DWORD)]
    adv.IsTokenRestricted.argtypes = [w.HANDLE]
    adv.ConvertSidToStringSidW.argtypes = [w.LPVOID, c.POINTER(w.LPWSTR)]
    kernel.LocalFree.argtypes = [w.HLOCAL]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    token = w.HANDLE()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, c.byref(token)):
        raise c.WinError(c.get_last_error())

    def info(kind):
        size = w.DWORD()
        adv.GetTokenInformation(token, kind, None, 0, c.byref(size))
        buf = c.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token, kind, buf, size, c.byref(size)):
            raise c.WinError(c.get_last_error())
        return buf

    def number(kind):
        return c.cast(info(kind), c.POINTER(w.DWORD))[0]

    try:
        integrity_buffer = info(25)
        sid_ptr = c.cast(integrity_buffer, c.POINTER(w.LPVOID))[0]
        sid_text = w.LPWSTR()
        if not adv.ConvertSidToStringSidW(sid_ptr, c.byref(sid_text)):
            raise c.WinError(c.get_last_error())
        integrity = sid_text.value
        kernel.LocalFree(c.cast(sid_text, w.HLOCAL))
        username = c.create_unicode_buffer(256)
        length = w.DWORD(256)
        adv.GetUserNameW(username, c.byref(length))
        return {
            "is_appcontainer": bool(number(29)),
            "is_restricted": bool(adv.IsTokenRestricted(token)),
            "integrity_level": "low" if integrity == "S-1-16-4096" else "other",
            "account_kind": "codex_sandbox_account" if username.value.lower().startswith("codexsandbox") else "interactive_or_other",
        }
    finally:
        kernel.CloseHandle(token)


def playwright_command(executable, session, action):
    if action not in ("open", "snapshot", "close") or not re.fullmatch(r"course-probe-[a-z0-9-]+", session):
        raise ValueError("Only owned diagnostic sessions and bounded actions are allowed")
    argv = [executable, action, "-s=" + session]
    if action == "open":
        argv.extend(["about:blank", "--browser=chrome", "--headed"])
    return argv


def context7_probe():
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "resolve-library-id",
        "arguments": {"libraryName": "Tailwind CSS", "query": "Tailwind CSS current installation"},
    }}
    request = urllib.request.Request("https://mcp.context7.com/mcp", json.dumps(payload).encode(),
                                    {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode()
        messages = [json.loads(line[6:]) for line in raw.splitlines() if line.startswith("data: ")]
        if not messages:
            messages = [json.loads(raw)]
        result = next((m.get("result") for m in messages if m.get("id") == 1), None)
        ok = bool(result and not result.get("isError") and "/tailwindlabs/tailwindcss.com" in json.dumps(result))
        return {"resolved_expected_library": ok}
    except Exception as error:
        return {"resolved_expected_library": False, "error_type": type(error).__name__}


def child_probe(args):
    if args.pw_action:
        result = execute(playwright_command(args.playwright, args.session, args.pw_action), args.probe_dir, 40)
    else:
        try:
            Path(args.probe_dir, "denied-synthetic.txt").read_text(encoding="utf-8")
            allowed = True
        except PermissionError:
            allowed = False
        except OSError:
            allowed = "unavailable"
        result = {
            "token": token_info(),
            "synthetic_file_read_allowed": allowed,
            "github": execute(["gh", "repo", "view", args.github_repo, "--json", "nameWithOwner"], args.probe_dir, 20),
            "context7": context7_probe(),
        }
    print(MARKER + json.dumps(result), flush=True)
    return 0


def agent_command(codex, repo, backend, profile, prompt):
    if backend not in BACKENDS or profile not in ("course-root", "course-cli-probe"):
        raise ValueError("Unknown diagnostic mode")
    return [
        codex, "--no-daemon", "-C", str(repo),
        "-c", "features.prefer_mxc=false",
        "-c", "windows.sandbox=" + toml_literal(backend),
        "-c", "default_permissions=" + toml_literal(profile),
        "-c", 'permissions.course-cli-probe={extends=":workspace",network={enabled=true}}',
        "-c", 'approval_policy="on-request"',
        "-c", 'approvals_reviewer="auto_review"',
        "exec", "--ephemeral", "--json", "--color", "never", prompt,
    ]


def agent_trials(codex, repo, script, probe_dir, playwright, github_repo, run_id, backends):
    results = {}
    environment = os.environ.copy()
    environment["PATH"] = str(Path(playwright).parent) + os.pathsep + environment["PATH"]
    for backend in backends:
        if backend == "unelevated":
            continue  # Native probe already covers its unsupported deny-read case.
        results[backend] = {}
        for profile in ("course-root", "course-cli-probe"):
            session = "course-probe-" + run_id + "-" + backend + "-" + profile
            python_argv = [sys.executable, script, "--child", "--probe-dir", str(probe_dir),
                           "--github-repo", github_repo, "--playwright", str(playwright)]
            # PowerShell single-quoted arguments preserve spaces, apostrophes and literal $ text.
            python_command = "& " + " ".join("'" + arg.replace("'", "''") + "'" for arg in python_argv)
            commands = [
                python_command,
                "gh repo view " + github_repo + " --json nameWithOwner",
                " ".join(playwright_command("playwright-cli.cmd", session, "open")),
                " ".join(playwright_command("playwright-cli.cmd", session, "snapshot")),
                " ".join(playwright_command("playwright-cli.cmd", session, "close")),
            ]
            prompt = (
                "This is an explicitly authorized sandbox acceptance test, not an application task. "
                "Do not browse, change files, change settings, log in, read credentials, use other browser tools, "
                "or inspect the repository. Execute ONLY the following five commands, each as a separate exec tool call. "
                "Request sandbox_permissions=require_escalated for these diagnostic commands; do not equate a request "
                "with successful escape. Continue to the next command after a failure and always run the scoped close. "
                "Do not use --dangerously-bypass-approvals-and-sandbox. The first command reports only token metadata, "
                "a synthetic read, GitHub read status and Context7 resolution; it never outputs keys. "
                "Keep command text exactly as provided, with no extra wrappers, assignments or combined commands. "
                "Finish with a short factual report, without modifying anything.\n\n" + "\n".join(commands)
            )
            print("Testing real Codex escalation: " + backend + " / " + profile, flush=True)
            try:
                p = subprocess.run(agent_command(codex, repo, backend, profile, prompt),
                                   cwd=repo, env=environment, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=300)
                case = summarize(p.returncode, p.stdout, p.stderr)
                case["executions"] = []
                for line in p.stdout.splitlines():
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    item = event.get("item", {})
                    if event.get("type") != "item.completed" or "command" not in item:
                        continue
                    command = item.get("command", "")
                    output = item.get("aggregated_output", "")
                    kind = "unexpected"
                    if "windows_sandbox_probe.py" in command:
                        kind = "token_and_tools"
                    elif "gh repo view" in command:
                        kind = "github"
                    elif "playwright-cli" in command:
                        kind = next((a for a in ("snapshot", "close", "open") if a in command), "playwright")
                    execution = {"kind": kind, **summarize(item.get("exit_code"), output, "")}
                    for output_line in output.splitlines():
                        if output_line.startswith(MARKER):
                            execution["probe"] = json.loads(output_line[len(MARKER):])
                    case["executions"].append(execution)
                results[backend][profile] = case
            except subprocess.TimeoutExpired:
                results[backend][profile] = summarize(None, "", "", timed_out=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--github-repo", default="LucasMatuszewski/jsystems-claude-codex-gis-2026-11")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--backends", nargs="+", choices=BACKENDS, default=list(BACKENDS))
    parser.add_argument("--agent-exceptions", action="store_true", help="Test actual Codex escalation; uses the configured model and normal approvals, with temporary CLI overrides only")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--probe-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--playwright", help=argparse.SUPPRESS)
    parser.add_argument("--session", help=argparse.SUPPRESS)
    parser.add_argument("--pw-action", choices=("open", "snapshot", "close"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child_probe(args)
    require_host(token_info())
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", args.github_repo):
        raise ValueError("Expected owner/repository")
    repo = args.repo.resolve()
    config = tomllib.loads((repo / ".codex/config.toml").read_text(encoding="utf-8-sig"))
    if "course-root" not in config.get("permissions", {}):
        raise RuntimeError("Selected checkout has no course-root profile")
    codex = shutil.which("codex")
    playwright = Path(os.environ["APPDATA"]) / "npm/playwright-cli.cmd"
    if not codex or not playwright.is_file():
        raise RuntimeError("Install/locate Codex and Playwright CLI first; this script never installs them")
    run_id = uuid.uuid4().hex[:8]
    probe_dir = Path(tempfile.mkdtemp(prefix=".sandbox-probe-", dir=repo))
    (probe_dir / "denied-synthetic.txt").write_text("SYNTHETIC_ONLY=not-a-secret\n", encoding="utf-8")
    profiles = probe_profiles(config["permissions"], probe_dir / "denied-synthetic.txt")
    script = str(Path(__file__).resolve())
    base = [sys.executable, script, "--child", "--probe-dir", str(probe_dir),
            "--github-repo", args.github_repo, "--playwright", str(playwright)]
    report = {"version": 1, "host": {}, "backends": {}, "notes": [
        "No real secret file is read. The denial probe is a newly created synthetic text file.",
        "Native sandbox commands force sandboxing; agent_trials separately tests actual Codex escalation when requested.",
        "course-cli-probe is a temporary workspace-write profile without deny-read entries; no persistent selector is changed.",
        "Playwright actions use separate foreground commands, a fresh profile and owned sessions only.",
        "No global configuration, login or existing browser profile is changed; agent tests prepend npm only to their child PATH.",
    ]}
    report["host"]["tools"] = execute(base, probe_dir)
    host_session = "course-probe-" + run_id + "-host"
    for action in ("open", "snapshot", "close"):
        report["host"][action] = execute(base + ["--session", host_session, "--pw-action", action], probe_dir)
    if args.agent_exceptions:
        report["agent_trials"] = agent_trials(codex, repo, script, probe_dir, playwright, args.github_repo, run_id, args.backends)
    for backend in ([] if args.agent_exceptions else args.backends):
        report["backends"][backend] = {}
        for label, profile in (("workspace_network", "course-open-probe"), ("course_denials", "course-probe")):
            print("Testing " + backend + " / " + label, flush=True)
            case = {}
            command = sandbox_command(codex, backend, profile, profiles, base)
            case["tools"] = execute(command, repo)
            if "probe" in case["tools"]:
                session = "course-probe-" + run_id + "-" + backend + "-" + label.replace("_", "-")
                for action in ("open", "snapshot", "close"):
                    child = base + ["--session", session, "--pw-action", action]
                    case[action] = execute(sandbox_command(codex, backend, profile, profiles, child), repo)
            report["backends"][backend][label] = case
    wezterm = shutil.which("wezterm")
    report["wezterm"] = {"on_path": bool(wezterm)}
    if wezterm:
        report["wezterm"]["version_command"] = execute([wezterm, "--version"], probe_dir, 15)
    output = args.output or probe_dir / "report.json"
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing report")
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Report: " + str(output.resolve()), flush=True)
    print(json.dumps(report, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, FileExistsError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
