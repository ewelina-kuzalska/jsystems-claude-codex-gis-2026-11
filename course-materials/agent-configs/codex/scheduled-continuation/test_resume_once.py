import contextlib
import datetime as dt
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import resume_once as tool


class ResumeOnceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root / "project with spaces"
        self.home = self.root / "home"
        self.project.mkdir()
        self.home.mkdir()
        self.cli = self.root / "stub-codex"
        self.cli.write_text("#!/bin/sh\nexit 0\n")
        self.cli.chmod(0o700)
        self.clock = dt.datetime(2030, 1, 1, 5, 59, tzinfo=tool.UTC)
        self.calls = []
        self.elapsed = 0.0

    def args(self, *extra):
        return tool.parser().parse_args([
            "--session", "11111111-1111-4111-8111-111111111111",
            "--project", str(self.project), "--codex-home", str(self.home),
            "--codex", str(self.cli), "--reset-at", "2030-01-01T06:00:00+00:00",
            "--message", "Continue the agreed task; preserve its boundaries.",
            "--log", str(self.root / "receipt.jsonl"), *extra])

    def sleep(self, seconds):
        self.assertLessEqual(seconds, 60)
        self.clock += dt.timedelta(seconds=seconds)
        self.elapsed += seconds

    def runner(self, command, **kw):
        self.calls.append((command, kw))
        return subprocess.CompletedProcess(command, 0, "Queued message synthetic for thread 11111111-1111-4111-8111-111111111111.\n", "")

    def run_args(self, args, runner=None, sleep=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return tool.execute(args, now=lambda: self.clock,
                                sleep=sleep or self.sleep, runner=runner or self.runner,
                                monotonic=lambda: self.elapsed)

    def test_rejects_state_or_executor_override_without_exposing_value(self):
        for name in ("CODEX_SQLITE_HOME", "CODEX_EXEC_SERVER_URL",
                     "CODEX_EXEC_SERVER_NOISE_AUTH_TOKEN", "OPENAI_IDENTITY_TOKEN_FILE"):
            with self.subTest(name=name), patch.dict(os.environ, {name: "SYNTHETIC_PRIVATE_VALUE"}):
                args = self.args("--run")
                args.log = self.root / f"{name}.jsonl"
                self.calls.clear()
                with self.assertRaises(ValueError) as raised:
                    self.run_args(args)
                self.assertIn(name, str(raised.exception))
                self.assertNotIn("SYNTHETIC_PRIVATE_VALUE", str(raised.exception))
                self.assertFalse(self.calls)
                self.assertFalse(args.log.exists())

    def test_empty_identity_selector_is_rejected_before_waiting(self):
        with patch.dict(os.environ, {"OPENAI_IDENTITY_TOKEN_FILE": ""}):
            with self.assertRaisesRegex(ValueError, "OPENAI_IDENTITY_TOKEN_FILE"):
                self.run_args(self.args("--run"))
        self.assertEqual(self.elapsed, 0)
        self.assertFalse(self.calls)
        self.assertFalse((self.root / "receipt.jsonl").exists())

    def test_oversleep_within_lateness_still_exceeds_maximum_wait(self):
        def oversleep(seconds):
            self.clock += dt.timedelta(seconds=661)
            self.elapsed += 661
        self.assertEqual(self.run_args(self.args("--run", "--max-wait-minutes", "11"),
                                       sleep=oversleep), 4)
        self.assertFalse(self.calls)
        events = [json.loads(line)["event"] for line in (self.root / "receipt.jsonl").read_text().splitlines()]
        self.assertEqual(events[-1], "aborted_wait_budget")
        self.assertEqual((self.clock - dt.datetime(2030, 1, 1, 6, 10, tzinfo=tool.UTC)).total_seconds(), 1)

    def test_dry_run_never_sleeps_invokes_or_writes(self):
        self.assertEqual(self.run_args(self.args()), 0)
        self.assertFalse(self.calls)
        self.assertFalse((self.root / "receipt.jsonl").exists())
        self.assertEqual(self.clock.hour, 5)

    def test_one_exact_call_after_buffer_and_private_receipt(self):
        self.assertEqual(self.run_args(self.args("--run")), 0)
        self.assertEqual(self.clock.hour, 6)
        self.assertEqual(self.clock.minute, 10)
        self.assertEqual(len(self.calls), 1)
        command, kw = self.calls[0]
        self.assertEqual(command, [str(self.cli), "queue", "-C", str(self.project),
            "--thread", "11111111-1111-4111-8111-111111111111",
            "--message", self.args().message, "--resume"])
        self.assertEqual(kw["encoding"], "utf-8")
        self.assertEqual(kw["errors"], "replace")
        events = [json.loads(line)["event"] for line in (self.root / "receipt.jsonl").read_text().splitlines()]
        self.assertEqual(events, ["scheduled", "dispatch_started", "dispatch_result", "queued"])
        self.assertEqual(kw["env"]["CODEX_HOME"], str(self.home))
        self.assertEqual(kw["cwd"], self.project)
        self.assertEqual(kw["stdin"], subprocess.DEVNULL)
        self.assertFalse(any(x.startswith("--danger") for x in command))
        if os.name != "nt":
            self.assertEqual((self.root / "receipt.jsonl").stat().st_mode & 0o777, 0o600)

    def test_stdout_warning_or_missing_ack_is_unconfirmed(self):
        for output, expected in [("Warning: message was queued, but could not resume thread x", 3),
                                 ("", 5),
                                 ("Queued message synthetic for thread ANOTHER-THREAD.", 5)]:
            with self.subTest(output=output):
                args = self.args("--run")
                args.log = self.root / f"ack-{expected}-{len(output)}.jsonl"
                def result(command, **kw):
                    return subprocess.CompletedProcess(command, 0, output, "")
                self.assertEqual(self.run_args(args, runner=result), expected)

    def test_native_windows_executable_and_utf8_transport(self):
        args = self.args("--run")
        args.codex = self.root / "codex.cmd"
        args.codex.write_text("synthetic wrapper")
        with patch.object(tool.os, "name", "nt"):
            with self.assertRaisesRegex(ValueError, "native codex.exe"):
                self.run_args(args)
        def result(command, **kw):
            self.assertEqual(kw["encoding"], "utf-8")
            self.assertEqual(kw["errors"], "replace")
            return subprocess.CompletedProcess(command, 0,
                "Queued message synthetic for thread 11111111-1111-4111-8111-111111111111.\nŁódź", "")
        self.assertEqual(self.run_args(self.args("--run"), runner=result), 0)

    def test_time_offset_and_malformed_inputs(self):
        self.assertEqual(tool.timestamp("2030-01-01T07:00:00+01:00").hour, 6)
        for bad in ["2030-01-01T06:00:00", "2030-01-01", "06:00", "garbage"]:
            with self.subTest(bad=bad), self.assertRaises(Exception):
                tool.timestamp(bad)
        for bad in ["--last", "current", "00000000-0000-0000-0000-000000000000"]:
            with self.subTest(bad=bad), self.assertRaises(Exception):
                tool.session_uuid(bad)

    def test_rejects_missing_home_past_target_and_excessive_wait(self):
        args = self.args()
        args.codex_home = self.root / "missing"
        with self.assertRaises(ValueError):
            self.run_args(args)
        self.clock += dt.timedelta(days=1)
        with self.assertRaises(ValueError):
            self.run_args(self.args())
        self.clock -= dt.timedelta(days=2)
        with self.assertRaises(ValueError):
            self.run_args(self.args())

    def test_no_retry_on_missing_session_timeout_or_resume_warning(self):
        for code, stderr, expected in [(1, "Thread not found", 1),
                                       (0, "Warning: message was queued, but could not resume thread x", 3)]:
            with self.subTest(code=code):
                args = self.args("--run")
                args.log = self.root / f"result-{code}.jsonl"
                calls = []
                def fail(command, **kw):
                    calls.append(command)
                    return subprocess.CompletedProcess(command, code, "", stderr)
                self.assertEqual(self.run_args(args, runner=fail), expected)
                self.assertEqual(len(calls), 1)
        args = self.args("--run")
        def timeout(command, **kw):
            raise subprocess.TimeoutExpired(command, kw["timeout"])
        self.assertEqual(self.run_args(args, runner=timeout), 124)

    def test_late_wakeup_aborts_without_dispatch(self):
        def oversleep(seconds):
            self.clock += dt.timedelta(days=1)
        self.assertEqual(self.run_args(self.args("--run"), sleep=oversleep), 4)
        self.assertFalse(self.calls)

    def test_rejects_slash_commands_and_existing_receipt(self):
        args = self.args()
        args.message = "/goal resume"
        with self.assertRaises(ValueError):
            self.run_args(args)
        args = self.args("--run")
        self.run_args(args)
        with self.assertRaises(ValueError):
            self.run_args(args)

    def test_stopped_clock_does_not_wait_forever(self):
        args = self.args("--run", "--max-wait-minutes", "11")
        def frozen_wall_clock(seconds):
            self.elapsed += seconds
        self.assertEqual(self.run_args(args, sleep=frozen_wall_clock), 4)
        self.assertFalse(self.calls)

    @unittest.skipIf(os.name == "nt", "POSIX executable stub; Windows remains unverified")
    def test_real_subprocess_uses_only_synthetic_cli(self):
        capture = self.root / "stub-capture.json"
        self.cli.write_text(
            "#!" + sys.executable + "\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            f"Path({str(capture)!r}).write_text(json.dumps({{'args': sys.argv[1:], "
            "'cwd': os.getcwd(), 'home': os.environ['CODEX_HOME']}))\n"
            "print('Queued message synthetic for thread 11111111-1111-4111-8111-111111111111.')\n")
        self.clock = dt.datetime(2030, 1, 1, 6, 10, tzinfo=tool.UTC)
        self.assertEqual(self.run_args(self.args("--run"), runner=subprocess.run), 0)
        actual = json.loads(capture.read_text())
        self.assertEqual(actual["args"][0], "queue")
        self.assertEqual(actual["cwd"], str(self.project))
        self.assertEqual(actual["home"], str(self.home))
if __name__ == "__main__":
    unittest.main()
