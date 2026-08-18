#!/usr/bin/env python3

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import watchdog


class WatchdogTest(unittest.TestCase):
    def config(self, root: Path, command: list[str]) -> dict:
        return {
            "schema_version": "experiment-watchdog/v1",
            "name": "test-job", "cwd": str(root), "command": command,
            "resource": {"provider": "none", "stable_seconds": 0.01,
                         "poll_seconds": 0.01, "wait_timeout_seconds": 2},
            "progress": {"poll_seconds": 0.02,
                         "startup_timeout_seconds": 2,
                         "no_progress_timeout_seconds": 2,
                         "task_timeout_seconds": 3,
                         "terminate_grace_seconds": 0.2},
            "outputs": {"required": [
                {"glob": "COMPLETE.json", "min_count": 1,
                 "min_size_bytes": 2}]},
        }

    def run_supervisor(self, config: dict) -> tuple[int, dict]:
        job = Path(config["cwd"]) / "job"
        job.mkdir()
        watchdog.atomic_json(job / "config.json", config)
        watchdog.atomic_json(job / "state.json", {
            "schema_version": "experiment-watchdog.state/v1",
            "name": config["name"], "state": "PREPARED"})
        rc = watchdog.Supervisor(job).run()
        return rc, watchdog.load_json(job / "state.json")

    def test_success_requires_output_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = "from pathlib import Path; Path('COMPLETE.json').write_text('{}')"
            rc, state = self.run_supervisor(
                self.config(root, [sys.executable, "-c", code]))
            self.assertEqual(0, rc)
            self.assertEqual("COMPLETE", state["state"])

    def test_zero_exit_with_missing_output_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rc, state = self.run_supervisor(
                self.config(root, [sys.executable, "-c", "pass"]))
            self.assertEqual(4, rc)
            self.assertEqual("FAILED", state["state"])

    def test_fast_zero_exit_with_fatal_log_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = (
                "from pathlib import Path; "
                "print('RuntimeError: hidden failure'); "
                "Path('COMPLETE.json').write_text('{}')")
            rc, state = self.run_supervisor(
                self.config(root, [sys.executable, "-c", code]))
            self.assertEqual(3, rc)
            self.assertEqual("FAILED", state["state"])

    def test_missing_start_marker_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = "from pathlib import Path; Path('COMPLETE.json').write_text('{}')"
            config = self.config(root, [sys.executable, "-c", code])
            config["progress"]["start_patterns"] = ["RANKS_STARTED"]
            rc, state = self.run_supervisor(config)
            self.assertEqual(5, rc)
            self.assertEqual("FAILED", state["state"])

    def test_fatal_log_terminates_process_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = "import time; print('Traceback (most recent call last)', flush=True); time.sleep(10)"
            started = time.monotonic()
            rc, state = self.run_supervisor(
                self.config(root, [sys.executable, "-c", code]))
            self.assertEqual(3, rc)
            self.assertEqual("FAILED", state["state"])
            self.assertLess(time.monotonic() - started, 2)

    def test_config_rejects_shell_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(Path(tmp), ["python", "train.py"])
            config["command"] = "python train.py"
            with self.assertRaisesRegex(ValueError, "argv"):
                watchdog.validate_config(config)

    def test_config_rejects_embedded_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(Path(tmp), ["python", "train.py"])
            config["env"] = {"API_TOKEN": "must-not-be-here"}
            with self.assertRaisesRegex(ValueError, "sensitive env"):
                watchdog.validate_config(config)

    def test_no_progress_terminates_silent_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.config(root, [sys.executable, "-c", "import time; time.sleep(10)"])
            config["progress"]["no_progress_timeout_seconds"] = 0.15
            rc, state = self.run_supervisor(config)
            self.assertEqual(124, rc)
            self.assertEqual("FAILED", state["state"])
            events = (root / "job" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("NO_PROGRESS", events)

    def test_detached_launch_reaches_complete(self):
        tmux = os.environ.get("EXPERIMENT_WATCHDOG_TEST_TMUX") or shutil.which("tmux")
        if not tmux:
            self.skipTest("tmux not available")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.config(root, [
                sys.executable, "-c",
                "from pathlib import Path; Path('COMPLETE.json').write_text('{}')",
            ])
            config_path = root / "policy.json"
            watchdog.atomic_json(config_path, config)
            job = root / "detached-job"
            self.assertEqual(0, watchdog.launch(config_path, job, tmux))
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                state = watchdog.load_json(job / "state.json")
                if state["state"] in watchdog.TERMINAL:
                    break
                time.sleep(0.05)
            self.assertEqual("COMPLETE", state["state"])

    @mock.patch("watchdog.run_capture")
    def test_ascend_probe_detects_process_rows(self, capture):
        capture.return_value = subprocess.CompletedProcess(
            [], 0, "| 0       0 | 12345 | python | 100 |\n")
        available, detail = watchdog.resource_available({"provider": "ascend"})
        self.assertFalse(available)
        self.assertIn("12345", detail)

    @mock.patch("watchdog.run_capture")
    def test_nvidia_probe_accepts_empty_compute_list(self, capture):
        capture.return_value = subprocess.CompletedProcess([], 0, "")
        available, _ = watchdog.resource_available({"provider": "nvidia"})
        self.assertTrue(available)


if __name__ == "__main__":
    unittest.main()
