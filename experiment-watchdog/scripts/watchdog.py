#!/usr/bin/env python3
"""Portable stateful supervisor for long-running accelerator experiments."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any


TERMINAL = {"COMPLETE", "FAILED", "STOPPED", "LAUNCH_FAILED"}
DEFAULT_FATAL = [
    r"Traceback \(most recent call last\)",
    r"(?:Value|Runtime|Assertion|Memory)Error:",
    r"out of memory",
    r"ChildFailedError",
    r"HCCL.*(?:error|failed)",
    r"NCCL.*(?:error|failed)",
    r"core dumped",
]


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "experiment-watchdog/v1":
        raise ValueError("schema_version must be experiment-watchdog/v1")
    if not isinstance(config.get("name"), str) or not config["name"].strip():
        raise ValueError("name must be a non-empty string")
    command = config.get("command")
    if not isinstance(command, list) or not command or not all(
            isinstance(item, str) and item for item in command):
        raise ValueError("command must be a non-empty argv string array")
    cwd = Path(config.get("cwd", "")).expanduser()
    if not cwd.is_absolute():
        raise ValueError("cwd must be absolute")
    if not cwd.is_dir():
        raise ValueError(f"cwd does not exist: {cwd}")
    sensitive = re.compile(
        r"(?:token|secret|password|credential|api[_-]?key|access[_-]?key)", re.I)
    leaked = [key for key in config.get("env", {}) if sensitive.search(str(key))]
    if leaked:
        raise ValueError(
            f"sensitive env keys must be inherited from the launcher, not stored: {leaked}")
    resource = config.get("resource", {})
    if resource.get("provider", "auto") not in {
            "auto", "ascend", "nvidia", "custom", "none"}:
        raise ValueError("resource.provider is invalid")
    if resource.get("provider") == "custom" and not resource.get("probe_argv"):
        raise ValueError("custom resource provider requires probe_argv")
    for section, keys in {
        "resource": ("poll_seconds", "stable_seconds", "wait_timeout_seconds"),
        "progress": ("poll_seconds", "startup_timeout_seconds",
                     "no_progress_timeout_seconds", "task_timeout_seconds"),
    }.items():
        values = config.get(section, {})
        for key in keys:
            if key in values and float(values[key]) <= 0:
                raise ValueError(f"{section}.{key} must be positive")
    notifier = config.get("notifier")
    if notifier and not isinstance(notifier.get("argv"), list):
        raise ValueError("notifier.argv must be an argv array")


def run_capture(argv: list[str], timeout: float = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=timeout, check=False)


def detect_provider() -> str:
    if shutil.which("npu-smi"):
        return "ascend"
    if shutil.which("nvidia-smi"):
        return "nvidia"
    return "none"


def resource_available(resource: dict[str, Any]) -> tuple[bool, str]:
    provider = resource.get("provider", "auto")
    provider = detect_provider() if provider == "auto" else provider
    if provider == "none":
        return True, "resource probe disabled"
    if provider == "custom":
        result = run_capture(list(resource["probe_argv"]))
        detail = result.stdout.strip()[-1000:]
        return result.returncode == 0, detail or f"probe exit {result.returncode}"
    if provider == "ascend":
        result = run_capture(["npu-smi", "info"])
        if result.returncode != 0:
            raise RuntimeError(f"npu-smi failed: {result.stdout[-1000:]}")
        process_rows = re.findall(
            r"^\|\s*\d+\s+\d+\s+\|\s*(\d+)\s+\|\s*([^|]+)\|",
            result.stdout, flags=re.MULTILINE)
        busy = [(pid, name.strip()) for pid, name in process_rows
                if int(pid) > 0]
        return not busy, f"ascend busy_processes={busy}"
    if provider == "nvidia":
        result = run_capture([
            "nvidia-smi", "--query-compute-apps=pid,process_name",
            "--format=csv,noheader,nounits"])
        if result.returncode != 0:
            raise RuntimeError(f"nvidia-smi failed: {result.stdout[-1000:]}")
        rows = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return not rows, f"nvidia busy_processes={rows}"
    raise ValueError(f"unsupported provider: {provider}")


def process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def process_group_alive(pgid: int | None) -> bool:
    if not pgid:
        return False
    if os.name == "nt":
        return process_alive(pgid)
    try:
        os.killpg(int(pgid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


class Supervisor:
    def __init__(self, job_dir: Path):
        self.job_dir = job_dir.resolve()
        self.config = load_json(self.job_dir / "config.json")
        validate_config(self.config)
        self.state_path = self.job_dir / "state.json"
        self.events_path = self.job_dir / "events.jsonl"
        self.notify_path = self.job_dir / "notifications.jsonl"
        self.task_log = self.job_dir / "task.log"
        self.state = load_json(self.state_path)
        self.stop_requested = False
        self.child: subprocess.Popen | None = None
        self._log_offset = 0
        patterns = self.config.get("progress", {}).get("fatal_patterns", DEFAULT_FATAL)
        self.fatal = [re.compile(pattern, re.I) for pattern in patterns]

    def save(self, **updates: Any) -> None:
        self.state.update(updates)
        self.state["updated_at"] = now()
        atomic_json(self.state_path, self.state)

    def notify(self, event: str, detail: str = "") -> None:
        payload = {
            "schema_version": "experiment-watchdog.event/v1",
            "timestamp": now(), "event": event, "detail": detail,
            "name": self.config["name"], "state": self.state.get("state"),
            "job_dir": str(self.job_dir),
        }
        append_jsonl(self.events_path, payload)
        notifier = self.config.get("notifier")
        if not notifier or event not in notifier.get("events", [event]):
            return
        try:
            result = subprocess.run(
                list(notifier["argv"]), input=json.dumps(payload), text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=float(notifier.get("timeout_seconds", 15)), check=False)
            audit = {**payload, "ok": result.returncode == 0,
                     "returncode": result.returncode,
                     "notifier_output": result.stdout.strip()[-1000:]}
        except Exception as exc:
            audit = {**payload, "ok": False, "error": repr(exc)}
        append_jsonl(self.notify_path, audit)

    def transition(self, state: str, event: str | None = None,
                   detail: str = "", **updates: Any) -> None:
        self.save(state=state, phase_detail=detail, **updates)
        self.notify(event or state, detail)

    def handle_signal(self, signum: int, _frame: Any) -> None:
        self.stop_requested = True
        self.save(stop_signal=signal.Signals(signum).name)

    def terminate_child(self, reason: str) -> None:
        if not self.child or self.child.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(self.child.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False)
            self.child.wait()
            self.save(cleanup_reason=reason, child_alive=False)
            return
        os.killpg(self.child.pid, signal.SIGTERM)
        grace = float(self.config.get("progress", {}).get(
            "terminate_grace_seconds", 30))
        try:
            self.child.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            os.killpg(self.child.pid, signal.SIGKILL)
            self.child.wait()
        if process_group_alive(self.child.pid):
            self.notify("CLEANUP_FAILED", f"process group {self.child.pid} survived SIGTERM")
            os.killpg(self.child.pid, signal.SIGKILL)
            deadline = time.monotonic() + 5
            while process_group_alive(self.child.pid) and time.monotonic() < deadline:
                time.sleep(0.1)
        self.save(cleanup_reason=reason, child_alive=False)

    def wait_resource(self) -> bool:
        cfg = self.config.get("resource", {})
        poll = float(cfg.get("poll_seconds", 5))
        stable = float(cfg.get("stable_seconds", 30))
        timeout = float(cfg.get("wait_timeout_seconds", 86400))
        reminders = sorted(float(v) for v in cfg.get(
            "reminder_seconds", [7200, 21600]))
        started = time.monotonic()
        free_since = None
        sent = set()
        self.transition("WAITING_FOR_RESOURCE", detail="waiting for accelerator")
        while not self.stop_requested:
            elapsed = time.monotonic() - started
            if elapsed >= timeout:
                self.transition("FAILED", "RESOURCE_WAIT_TIMEOUT",
                                f"waited {elapsed:.0f}s")
                return False
            for threshold in reminders:
                if elapsed >= threshold and threshold not in sent:
                    self.notify("RESOURCE_WAIT_REMINDER", f"waited {elapsed:.0f}s")
                    sent.add(threshold)
            try:
                available, detail = resource_available(cfg)
            except Exception as exc:
                self.transition("FAILED", "RESOURCE_PROBE_FAILED", repr(exc))
                return False
            if available:
                free_since = free_since or time.monotonic()
                stable_for = time.monotonic() - free_since
                self.save(phase_detail=f"resource free {stable_for:.1f}/{stable:.1f}s")
                if stable_for >= stable:
                    self.transition("STARTING", "RESOURCE_ACQUIRED", detail)
                    return True
            else:
                free_since = None
                self.save(phase_detail=detail)
            time.sleep(poll)
        self.transition("STOPPED", detail="stopped while waiting")
        return False

    def new_log_text(self) -> str:
        if not self.task_log.exists():
            return ""
        with self.task_log.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(self._log_offset)
            text = handle.read()
            self._log_offset = handle.tell()
            return text

    def progress_mtime(self) -> float:
        paths = [self.task_log]
        cwd = Path(self.config["cwd"])
        for pattern in self.config.get("progress", {}).get("heartbeat_globs", []):
            paths.extend(Path(value) for value in glob.glob(str(cwd / pattern)))
        mtimes = [path.stat().st_mtime for path in paths if path.exists()]
        return max(mtimes, default=time.time())

    def verify_outputs(self) -> tuple[bool, str]:
        cwd = Path(self.config["cwd"])
        failures = []
        for rule in self.config.get("outputs", {}).get("required", []):
            matches = [Path(path) for path in glob.glob(str(cwd / rule["glob"]))]
            minimum = int(rule.get("min_count", 1))
            min_size = int(rule.get("min_size_bytes", 1))
            valid = [path for path in matches if path.is_file()
                     and path.stat().st_size >= min_size]
            if len(valid) < minimum:
                failures.append(
                    f"{rule['glob']}: {len(valid)}/{minimum} valid files")
        return not failures, "; ".join(failures) or "all output gates passed"

    def run_task(self) -> int:
        cfg = self.config.get("progress", {})
        poll = float(cfg.get("poll_seconds", 2))
        startup_timeout = float(cfg.get("startup_timeout_seconds", 900))
        no_progress_timeout = float(cfg.get("no_progress_timeout_seconds", 900))
        task_timeout = float(cfg.get("task_timeout_seconds", 86400))
        start_patterns = [re.compile(value) for value in cfg.get("start_patterns", [])]
        started = time.monotonic()
        running = not start_patterns
        last_progress = time.time()
        env = os.environ.copy()
        env.update({str(k): str(v) for k, v in self.config.get("env", {}).items()})
        popen_kwargs = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                        if os.name == "nt" else {"start_new_session": True})
        with self.task_log.open("w", encoding="utf-8") as handle:
            self.child = subprocess.Popen(
                self.config["command"], cwd=self.config["cwd"], env=env,
                stdout=handle, stderr=subprocess.STDOUT, **popen_kwargs)
            self.save(child_pid=self.child.pid, child_pgid=self.child.pid,
                      child_alive=True, task_started_at=now())
            if running:
                self.transition("RUNNING", "RUN_STARTED", "process launched")
            while self.child.poll() is None and not self.stop_requested:
                handle.flush()
                fresh = self.new_log_text()
                if fresh:
                    last_progress = time.time()
                for pattern in self.fatal:
                    match = pattern.search(fresh)
                    if match:
                        self.notify("FATAL_LOG", match.group(0))
                        self.terminate_child(f"fatal log: {match.group(0)}")
                        self.transition("FAILED", detail=f"fatal log: {match.group(0)}")
                        return 3
                if not running and any(pattern.search(fresh) for pattern in start_patterns):
                    running = True
                    self.transition("RUNNING", "RUN_STARTED", "start marker observed")
                elapsed = time.monotonic() - started
                if not running and elapsed > startup_timeout:
                    self.notify("NO_PROGRESS", "startup marker timeout")
                    self.terminate_child("startup timeout")
                    self.transition("FAILED", detail="startup timeout")
                    return 124
                last_progress = max(last_progress, self.progress_mtime())
                if running and time.time() - last_progress > no_progress_timeout:
                    self.notify("NO_PROGRESS", "business progress timeout")
                    self.terminate_child("no progress timeout")
                    self.transition("FAILED", detail="no progress timeout")
                    return 124
                if elapsed > task_timeout:
                    self.notify("NO_PROGRESS", "task deadline exceeded")
                    self.terminate_child("task timeout")
                    self.transition("FAILED", detail="task timeout")
                    return 124
                self.save(child_alive=True, elapsed_seconds=elapsed,
                          last_progress_at=time.strftime(
                              "%Y-%m-%dT%H:%M:%S%z", time.localtime(last_progress)))
                time.sleep(poll)
        if self.stop_requested:
            self.terminate_child("stop requested")
            self.transition("STOPPED", detail="explicit stop")
            return 143
        fresh = self.new_log_text()
        for pattern in self.fatal:
            match = pattern.search(fresh)
            if match:
                self.notify("FATAL_LOG", match.group(0))
                self.transition("FAILED", detail=f"fatal log: {match.group(0)}")
                return 3
        rc = int(self.child.returncode)
        self.save(child_alive=False, returncode=rc)
        if rc != 0:
            self.transition("FAILED", detail=f"command exit {rc}")
            return rc
        if not running:
            self.transition("FAILED", detail="command exited before start marker")
            return 5
        self.transition("VERIFYING_OUTPUT", detail="command exited zero")
        valid, detail = self.verify_outputs()
        if not valid:
            self.transition("FAILED", "OUTPUT_INCOMPLETE", detail)
            return 4
        self.transition("COMPLETE", detail=detail, ended_at=now())
        return 0

    def run(self) -> int:
        self.save(supervisor_pid=os.getpid(), supervisor_started_at=now())
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, self.handle_signal)
        try:
            if not self.wait_resource():
                return 143 if self.state["state"] == "STOPPED" else 22
            if self.stop_requested:
                self.transition("STOPPED", detail="explicit stop")
                return 143
            return self.run_task()
        except BaseException as exc:
            self.terminate_child(f"supervisor exception: {exc!r}")
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                self.transition("STOPPED", detail=repr(exc))
                return 143
            self.transition("FAILED", detail=f"supervisor exception: {exc!r}")
            return 70


def safe_session(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:80]


def launch(config_path: Path, job_dir: Path, tmux: str | None) -> int:
    config = load_json(config_path.resolve())
    validate_config(config)
    job_dir = job_dir.resolve()
    if job_dir.exists():
        raise FileExistsError(f"refusing to reuse job directory: {job_dir}")
    job_dir.mkdir(parents=True)
    atomic_json(job_dir / "config.json", config)
    state = {
        "schema_version": "experiment-watchdog.state/v1",
        "name": config["name"], "state": "PREPARED",
        "created_at": now(), "updated_at": now(), "job_dir": str(job_dir),
    }
    tmux_bin = tmux or shutil.which("tmux")
    if not tmux_bin:
        state.update(state="LAUNCH_FAILED", phase_detail="tmux not found")
        atomic_json(job_dir / "state.json", state)
        raise RuntimeError("tmux not found; run doctor or use the _run command under a process manager")
    digest = hashlib.sha256(str(job_dir).encode()).hexdigest()[:12]
    socket_path = str(Path(tempfile.gettempdir()) / f"experiment-watchdog-{digest}.sock")
    session = safe_session(config["name"])
    state.update(tmux_binary=tmux_bin, tmux_socket=socket_path,
                 tmux_session=session)
    atomic_json(job_dir / "state.json", state)
    script = str(Path(__file__).resolve())
    command = [tmux_bin, "-S", socket_path, "new-session", "-d", "-s", session,
               sys.executable, script, "_run", "--job-dir", str(job_dir)]
    result = run_capture(command)
    if result.returncode != 0:
        state.update(state="LAUNCH_FAILED", phase_detail=result.stdout[-1000:])
        atomic_json(job_dir / "state.json", state)
        raise RuntimeError(f"tmux launch failed: {result.stdout}")
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        observed = load_json(job_dir / "state.json")
        if process_alive(observed.get("supervisor_pid")):
            state = observed
            break
        time.sleep(0.1)
    else:
        state = load_json(job_dir / "state.json")
        state.update(state="LAUNCH_FAILED",
                     phase_detail="supervisor did not become alive within 5s")
        atomic_json(job_dir / "state.json", state)
        run_capture([tmux_bin, "-S", socket_path, "kill-session", "-t", session])
        raise RuntimeError(state["phase_detail"])
    print(json.dumps(state, indent=2))
    return 0


def status(job_dir: Path) -> int:
    state = load_json(job_dir.resolve() / "state.json")
    state["supervisor_alive"] = process_alive(state.get("supervisor_pid"))
    state["child_alive"] = process_alive(state.get("child_pid"))
    if state.get("tmux_binary") and state.get("tmux_socket") and state.get("tmux_session"):
        try:
            result = run_capture([
                state["tmux_binary"], "-S", state["tmux_socket"],
                "has-session", "-t", state["tmux_session"]])
            state["tmux_session_alive"] = result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            state["tmux_session_alive"] = False
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def stop(job_dir: Path) -> int:
    state_path = job_dir.resolve() / "state.json"
    state = load_json(state_path)
    if state.get("state") in TERMINAL:
        print(f"already terminal: {state['state']}")
        return 0
    pid = state.get("supervisor_pid")
    if not process_alive(pid):
        raise RuntimeError("supervisor is not alive")
    os.kill(int(pid), signal.SIGTERM)
    print(f"sent SIGTERM to supervisor {pid}")
    return 0


def doctor(tmux: str | None = None) -> int:
    tmux_path = tmux or shutil.which("tmux")
    if tmux_path and not Path(tmux_path).is_file():
        tmux_path = None
    report = {
        "python": sys.version.split()[0],
        "tmux": tmux_path,
        "npu_smi": shutil.which("npu-smi"),
        "nvidia_smi": shutil.which("nvidia-smi"),
        "detected_resource_provider": detect_provider(),
    }
    report["launch_ready"] = bool(report["tmux"])
    print(json.dumps(report, indent=2))
    return 0 if report["launch_ready"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="subcommand", required=True)
    doctor_p = commands.add_parser("doctor")
    doctor_p.add_argument("--tmux")
    validate = commands.add_parser("validate")
    validate.add_argument("config", type=Path)
    launch_p = commands.add_parser("launch")
    launch_p.add_argument("--config", type=Path, required=True)
    launch_p.add_argument("--job-dir", type=Path, required=True)
    launch_p.add_argument("--tmux")
    for name in ("status", "stop", "_run"):
        sub = commands.add_parser(name)
        sub.add_argument("--job-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.subcommand == "doctor":
        return doctor(args.tmux)
    if args.subcommand == "validate":
        validate_config(load_json(args.config.resolve()))
        print("VALID")
        return 0
    if args.subcommand == "launch":
        return launch(args.config, args.job_dir, args.tmux)
    if args.subcommand == "status":
        return status(args.job_dir)
    if args.subcommand == "stop":
        return stop(args.job_dir)
    return Supervisor(args.job_dir).run()


if __name__ == "__main__":
    raise SystemExit(main())
