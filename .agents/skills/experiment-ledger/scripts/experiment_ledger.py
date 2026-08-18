#!/usr/bin/env python3
"""Create, validate, preflight, and transition ResearchCenter experiment records."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TYPES = {"contract-test", "preflight", "smoke-test", "training", "evaluation", "benchmark", "ablation", "data-generation", "analysis"}
STATUSES = {"planned", "blocked", "ready", "queued", "running", "verifying", "complete", "failed", "stopped", "cancelled"}
TRANSITIONS = {
    "planned": {"blocked", "ready", "cancelled"},
    "blocked": {"ready", "cancelled"},
    "ready": {"queued", "running", "blocked", "cancelled"},
    "queued": {"running", "failed", "stopped"},
    "running": {"verifying", "failed", "stopped"},
    "verifying": {"complete", "failed"},
    "failed": {"ready", "cancelled"},
    "complete": set(),
    "stopped": {"ready", "cancelled"},
    "cancelled": set(),
}
EXP_PATTERN = re.compile(r"^EXP-[0-9A-F]{12}$")
IDEA_PATTERN = re.compile(r"^IDEA-[0-9A-F]{12}$")
TASK_PATTERN = re.compile(r"^TASK-[0-9A-F]{10}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def digest(text: str, length: int) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length].upper()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_project_id(project_dir: Path) -> str:
    config = project_dir / "project.yaml"
    if not project_dir.is_dir() or not config.is_file():
        raise ValueError(f"Project directory must exist and contain project.yaml: {project_dir}")
    for line in config.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^project_id:\s*['\"]?([^'\"#\s]+)", line)
        if match:
            return match.group(1)
    raise ValueError(f"project_id is missing from {config}")


def file_sha256(location: str | None) -> str | None:
    if not location:
        return None
    path = Path(location)
    if not path.is_file():
        return None
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def record_paths(project_dir: Path, experiment_id: str) -> tuple[Path, Path]:
    return (
        project_dir / "experiments" / "records" / f"{experiment_id}.json",
        project_dir / "experiments" / "notes" / f"{experiment_id}.md",
    )


def spec_value(spec: dict[str, Any], key: str, default: Any) -> Any:
    value = spec.get(key, default)
    return default if value is None and isinstance(default, (dict, list)) else value


def create_note(record: dict[str, Any]) -> str:
    trace = record["traceability"]
    protocol = record["protocol"]
    resources = record["resources"]
    accelerator = resources.get("accelerator", {})
    blockers = "\n".join(
        f"- `{item.get('code', 'UNSPECIFIED')}`：{item.get('description', '未说明')}；解除条件：{item.get('resolution', '待补充')}"
        for item in record["blockers"]
    ) or "- 当前没有登记阻塞项。"
    success = "\n".join(f"- {item}" for item in protocol.get("success_criteria", [])) or "- 待补充"
    failure = "\n".join(f"- {item}" for item in protocol.get("failure_criteria", [])) or "- 待补充"
    return f'''---
experiment_id: "{record['experiment_id']}"
status: "{record['status']}"
type: "{record['type']}"
---

# {record['title']}

> 这是实验计划与证据索引，不代表实验已经执行。

## 目标

{record['objective']}

## 当前状态

- 状态：`{record['status']}`
- 执行器：`{record['execution'].get('executor_id') or '未配置'}`
- 加速器：`{accelerator.get('vendor') or '未指定'}` × {accelerator.get('count') or 0}
- 类型：`{record['type']}`

## 阻塞项

{blockers}

## 协议

{protocol.get('scope') or '待补充。'}

### 成功标准

{success}

### 失败标准

{failure}

## 代码、数据与环境

- 代码仓：{record['code'].get('repository') or '待确认'}
- Commit：`{record['code'].get('commit') or '待确认'}`
- 数据：{len(record['data'].get('datasets', []))} 个已登记数据入口
- OS：`{record['environment'].get('os') or '待确认'}`
- 命令：`{json.dumps(record['execution'].get('command_argv', []), ensure_ascii=False)}`

## 可追溯关系

- Idea：{', '.join(trace.get('idea_ids', [])) or '尚未关联'}
- TODO：{', '.join(trace.get('task_ids', [])) or '尚未关联'}
- 文献：{', '.join(trace.get('lit_ids', [])) or '尚未关联'}
- Claim：{', '.join(trace.get('claim_ids', [])) or '尚未关联'}

## Preflight

- 最新状态：`{record['preflight'].get('latest_status', 'not-run')}`
- 报告：尚未生成或请查看机器记录中的 report 指针。

## 结果与解释

尚未执行，不得据此更新 Idea 或论文结论。
'''


def rebuild_index(project_dir: Path) -> list[dict[str, Any]]:
    records_dir = project_dir / "experiments" / "records"
    items: list[dict[str, Any]] = []
    if records_dir.is_dir():
        for path in sorted(records_dir.glob("EXP-*.json")):
            record = load_json(path)
            items.append({
                "experiment_id": record["experiment_id"],
                "title": record["title"],
                "type": record["type"],
                "status": record["status"],
                "objective": record["objective"],
                "idea_ids": record["traceability"].get("idea_ids", []),
                "record_path": f"records/{path.name}",
                "note_path": f"notes/{path.stem}.md",
                "updated_at": record["updated_at"],
            })
    write_json(project_dir / "experiments" / "index.json", {"schema_version": 1, "experiments": items})
    return items


def build_record(project_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    for key in ("title", "type", "status", "objective"):
        if not spec.get(key):
            raise ValueError(f"Spec field is required: {key}")
    if spec["type"] not in TYPES:
        raise ValueError(f"Invalid experiment type: {spec['type']}")
    if spec["status"] not in STATUSES:
        raise ValueError(f"Invalid experiment status: {spec['status']}")
    identity = f"{project_id}|{normalize(spec['title'])}"
    experiment_id = f"EXP-{digest(identity, 12)}"
    now = utc_now()
    source = spec.get("source")
    record = {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "project_id": project_id,
        "title": spec["title"],
        "type": spec["type"],
        "status": spec["status"],
        "objective": spec["objective"],
        "protocol": spec_value(spec, "protocol", {"scope": "", "success_criteria": [], "failure_criteria": [], "expected_outputs": []}),
        "traceability": spec_value(spec, "traceability", {"idea_ids": [], "task_ids": [], "lit_ids": [], "claim_ids": [], "parent_experiment_ids": []}),
        "execution": spec_value(spec, "execution", {"executor_id": None, "cwd": {"connection": None, "relative_path": None}, "command_argv": [], "required_commands": [], "required_connections": [], "watchdog_policy": None}),
        "code": spec_value(spec, "code", {"repository": None, "commit": None, "dirty": None, "patch_uri": None}),
        "data": spec_value(spec, "data", {"datasets": []}),
        "environment": spec_value(spec, "environment", {"os": None, "runtime": None, "lockfile": None, "seeds": {}}),
        "resources": spec_value(spec, "resources", {"accelerator": {"vendor": "none", "count": 0, "min_vram_gb": None, "cuda": None, "driver": None}, "min_disk_gb": None}),
        "blockers": spec_value(spec, "blockers", []),
        "preflight": {"latest_status": "not-run", "reports": []},
        "results": {"metrics": [], "artifacts": [], "output_validation": "not-run", "conclusion": None, "idea_effects": [], "limitations": [], "reviewed_by": None, "reviewed_at": None},
        "events": [{
            "event_id": f"EVT-{digest(f'{experiment_id}|{now}|created', 10)}",
            "timestamp": now,
            "type": "created",
            "from_status": None,
            "to_status": spec["status"],
            "reason": spec.get("creation_reason", "Created from an experiment specification."),
            "evidence": None,
        }],
        "provenance": {"source": source, "source_sha256": file_sha256(source), "created_by": spec.get("created_by", "Codex")},
        "created_at": now,
        "updated_at": now,
    }
    return record


def command_create(args: argparse.Namespace) -> dict[str, Any]:
    project_dir = Path(args.project_dir).resolve()
    project_id = read_project_id(project_dir)
    spec = load_json(Path(args.spec).resolve())
    record = build_record(project_id, spec)
    record_path, note_path = record_paths(project_dir, record["experiment_id"])
    if record_path.exists():
        raise ValueError(f"Experiment already exists: {record['experiment_id']}")
    write_json(record_path, record)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(create_note(record), encoding="utf-8")
    rebuild_index(project_dir)
    return {"action": "created", "experiment_id": record["experiment_id"], "record_path": str(record_path), "note_path": str(note_path)}


def resolve_command(name: str, executor: dict[str, Any]) -> str | None:
    candidate = executor.get("commands", {}).get(name, name)
    path = Path(candidate)
    if path.is_absolute():
        return str(path) if path.is_file() else None
    return shutil.which(candidate)


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "passed": passed, "detail": detail})


def run_preflight(record: dict[str, Any], executor: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    current_os = platform.system().casefold()
    required_os = (record["environment"].get("os") or "").casefold()
    executor_os = (executor.get("os") or current_os).casefold()
    add_check(checks, "os", not required_os or required_os == executor_os, f"required={required_os or 'any'}, executor={executor_os}")

    required_connections = set(record["execution"].get("required_connections", []))
    cwd_connection = record["execution"].get("cwd", {}).get("connection")
    if cwd_connection:
        required_connections.add(cwd_connection)
    mappings = executor.get("connections", {})
    for connection in sorted(required_connections):
        mapped = mappings.get(connection)
        passed = bool(mapped and Path(mapped).exists())
        add_check(checks, f"connection:{connection}", passed, "mapped path exists" if passed else "mapping missing or path unavailable")

    for command in record["execution"].get("required_commands", []):
        resolved = resolve_command(command, executor)
        add_check(checks, f"command:{command}", bool(resolved), "available" if resolved else "not found")

    accelerator = record["resources"].get("accelerator", {})
    vendor = (accelerator.get("vendor") or "none").casefold()
    if vendor == "nvidia":
        nvidia_smi = resolve_command("nvidia-smi", executor)
        if not nvidia_smi:
            add_check(checks, "accelerator:nvidia", False, "nvidia-smi not found")
        else:
            try:
                result = subprocess.run(
                    [nvidia_smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5, check=False,
                )
                rows = [row.strip() for row in result.stdout.splitlines() if row.strip()]
                required_count = int(accelerator.get("count") or 0)
                passed = result.returncode == 0 and len(rows) >= required_count
                detail = f"detected={len(rows)}, required={required_count}" if result.returncode == 0 else "nvidia-smi query failed"
                add_check(checks, "accelerator:nvidia", passed, detail)
            except (OSError, subprocess.TimeoutExpired):
                add_check(checks, "accelerator:nvidia", False, "nvidia-smi query failed or timed out")
    elif vendor in {"ascend", "npu"}:
        npu_smi = resolve_command("npu-smi", executor)
        if not npu_smi:
            add_check(checks, "accelerator:ascend", False, "npu-smi not found")
        else:
            try:
                result = subprocess.run(
                    [npu_smi, "info", "-l"], capture_output=True, text=True,
                    timeout=5, check=False,
                )
                device_ids = set(re.findall(r"NPU ID\s*:\s*(\d+)", result.stdout))
                required_count = int(accelerator.get("count") or 0)
                passed = result.returncode == 0 and len(device_ids) >= required_count
                detail = f"detected={len(device_ids)}, required={required_count}" if result.returncode == 0 else "npu-smi query failed"
                add_check(checks, "accelerator:ascend", passed, detail)
            except (OSError, subprocess.TimeoutExpired):
                add_check(checks, "accelerator:ascend", False, "npu-smi query failed or timed out")
    elif vendor not in {"none", "cpu"}:
        add_check(checks, f"accelerator:{vendor}", False, "unsupported by local preflight")

    unresolved = []
    if not record["execution"].get("executor_id"):
        unresolved.append("executor_id")
    if not record["execution"].get("command_argv"):
        unresolved.append("command_argv")
    if not record["code"].get("commit"):
        unresolved.append("code.commit")
    add_check(checks, "immutable-execution-metadata", not unresolved, "resolved" if not unresolved else f"unresolved: {', '.join(unresolved)}")

    now = utc_now()
    return {
        "schema_version": 1,
        "experiment_id": record["experiment_id"],
        "executor_id": executor.get("executor_id", "current-local"),
        "checked_at": now,
        "passed": all(item["passed"] for item in checks),
        "launch_performed": False,
        "checks": checks,
    }


def command_preflight(args: argparse.Namespace) -> dict[str, Any]:
    project_dir = Path(args.project_dir).resolve()
    read_project_id(project_dir)
    record_path, _ = record_paths(project_dir, args.experiment_id)
    if not record_path.is_file():
        raise ValueError(f"Unknown experiment: {args.experiment_id}")
    record = load_json(record_path)
    executor = load_json(Path(args.executor).resolve()) if args.executor else {
        "schema_version": 1, "executor_id": "current-local", "kind": "local",
        "os": platform.system().casefold(), "connections": {}, "commands": {},
    }
    report = run_preflight(record, executor)
    report_path = None
    if args.write_report:
        stamp = report["checked_at"].replace("-", "").replace(":", "")
        report_path = project_dir / "experiments" / "preflight" / f"{args.experiment_id}-{stamp}.json"
        write_json(report_path, report)
        relative = report_path.relative_to(project_dir / "experiments").as_posix()
        record["preflight"]["latest_status"] = "passed" if report["passed"] else "failed"
        record["preflight"]["reports"].append(relative)
        record["updated_at"] = report["checked_at"]
        write_json(record_path, record)
        rebuild_index(project_dir)
    return {"action": "preflight", "passed": report["passed"], "report_path": str(report_path) if report_path else None, "report": report}


def command_transition(args: argparse.Namespace) -> dict[str, Any]:
    project_dir = Path(args.project_dir).resolve()
    read_project_id(project_dir)
    record_path, _ = record_paths(project_dir, args.experiment_id)
    if not record_path.is_file():
        raise ValueError(f"Unknown experiment: {args.experiment_id}")
    record = load_json(record_path)
    current = record["status"]
    if args.status not in TRANSITIONS[current]:
        raise ValueError(f"Invalid transition: {current} -> {args.status}")
    if args.status == "ready":
        if record["blockers"]:
            raise ValueError("Cannot transition to ready while blockers remain")
        required = [record["execution"].get("executor_id"), record["execution"].get("command_argv"), record["code"].get("commit")]
        if not all(required) or record["preflight"].get("latest_status") != "passed":
            raise ValueError("Ready requires executor, command, immutable commit, and a passing preflight")
    if args.status == "complete":
        if record["results"].get("output_validation") != "passed" or not record["results"].get("conclusion"):
            raise ValueError("Complete requires passed output validation and a recorded conclusion")
    now = utc_now()
    record["events"].append({
        "event_id": f"EVT-{digest(f'{args.experiment_id}|{now}|{current}|{args.status}|{args.reason}', 10)}",
        "timestamp": now,
        "type": "status-transition",
        "from_status": current,
        "to_status": args.status,
        "reason": args.reason,
        "evidence": args.evidence,
    })
    record["status"] = args.status
    record["updated_at"] = now
    write_json(record_path, record)
    rebuild_index(project_dir)
    return {"action": "transitioned", "experiment_id": args.experiment_id, "from": current, "to": args.status}


def validate_record(record: dict[str, Any], path: Path, project_dir: Path, project_id: str) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version", "experiment_id", "project_id", "title", "type", "status", "objective",
        "protocol", "traceability", "execution", "code", "data", "environment", "resources",
        "blockers", "preflight", "results", "events", "provenance", "created_at", "updated_at",
    }
    missing = sorted(required - record.keys())
    if missing:
        return [f"{path}: missing fields: {', '.join(missing)}"]
    if record["schema_version"] != 1:
        errors.append(f"{path}: unsupported schema_version")
    if not EXP_PATTERN.fullmatch(record["experiment_id"]) or path.stem != record["experiment_id"]:
        errors.append(f"{path}: invalid or mismatched experiment_id")
    if record["project_id"] != project_id:
        errors.append(f"{path}: project_id mismatch")
    if record["type"] not in TYPES:
        errors.append(f"{path}: invalid type")
    if record["status"] not in STATUSES:
        errors.append(f"{path}: invalid status")
    if record["status"] == "blocked" and not record["blockers"]:
        errors.append(f"{path}: blocked experiment requires blockers")
    if record["status"] in {"ready", "queued", "running", "verifying", "complete"}:
        if record["blockers"]:
            errors.append(f"{path}: executable experiment must not retain blockers")
        execution_ready = (
            record["execution"].get("executor_id")
            and record["execution"].get("command_argv")
            and record["code"].get("commit")
            and record["preflight"].get("latest_status") == "passed"
        )
        if not execution_ready:
            errors.append(f"{path}: executable status requires executor, command, commit, and passing preflight")
    if record["status"] == "complete":
        if record["results"].get("output_validation") != "passed" or not record["results"].get("conclusion"):
            errors.append(f"{path}: complete requires validated outputs and a conclusion")
    for report in record["preflight"].get("reports", []):
        if not (project_dir / "experiments" / report).is_file():
            errors.append(f"{path}: missing preflight report: {report}")
    for idea_id in record["traceability"].get("idea_ids", []):
        if not IDEA_PATTERN.fullmatch(idea_id) or not (project_dir / "ideas" / "records" / f"{idea_id}.json").is_file():
            errors.append(f"{path}: unresolved idea link: {idea_id}")
    todo_text = (project_dir / "TODO.md").read_text(encoding="utf-8") if (project_dir / "TODO.md").is_file() else ""
    for task_id in record["traceability"].get("task_ids", []):
        if not TASK_PATTERN.fullmatch(task_id) or task_id not in todo_text:
            errors.append(f"{path}: unresolved task link: {task_id}")
    event_ids = [item.get("event_id") for item in record["events"]]
    if not event_ids or len(event_ids) != len(set(event_ids)):
        errors.append(f"{path}: events must be non-empty and unique")
    return errors


def command_validate(args: argparse.Namespace) -> dict[str, Any]:
    project_dir = Path(args.project_dir).resolve()
    project_id = read_project_id(project_dir)
    records_dir = project_dir / "experiments" / "records"
    errors: list[str] = []
    count = 0
    for path in sorted(records_dir.glob("EXP-*.json")) if records_dir.is_dir() else []:
        count += 1
        try:
            record = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        errors.extend(validate_record(record, path, project_dir, project_id))
        note = project_dir / "experiments" / "notes" / f"{path.stem}.md"
        if not note.is_file():
            errors.append(f"{path}: missing note {note}")
    rebuild_index(project_dir)
    if errors:
        raise ValueError("\n".join(errors))
    return {"action": "validated", "project_id": project_id, "record_count": count}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain ResearchCenter experiment records.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--project-dir", required=True)
    create.add_argument("--spec", required=True)
    create.set_defaults(handler=command_create)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--project-dir", required=True)
    preflight.add_argument("--experiment-id", required=True)
    preflight.add_argument("--executor")
    preflight.add_argument("--write-report", action="store_true")
    preflight.set_defaults(handler=command_preflight)
    transition = subparsers.add_parser("transition")
    transition.add_argument("--project-dir", required=True)
    transition.add_argument("--experiment-id", required=True)
    transition.add_argument("--status", required=True, choices=sorted(STATUSES))
    transition.add_argument("--reason", required=True)
    transition.add_argument("--evidence")
    transition.set_defaults(handler=command_transition)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--project-dir", required=True)
    validate.set_defaults(handler=command_validate)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = args.handler(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
