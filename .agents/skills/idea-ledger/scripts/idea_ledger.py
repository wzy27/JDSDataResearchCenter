#!/usr/bin/env python3
"""Create and maintain deterministic ResearchCenter idea records."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KINDS = {"hypothesis", "method", "research-question", "system-design", "dataset", "analysis"}
STATUSES = {"proposed", "active", "testing", "supported", "challenged", "superseded", "rejected", "parked"}
EVENT_TYPES = {"captured", "refined", "pivoted", "challenged", "supported", "rejected", "superseded"}
IDEA_PATTERN = re.compile(r"^IDEA-[0-9A-F]{12}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def digest(text: str, length: int) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length].upper()


def read_project_id(project_dir: Path) -> str:
    config = project_dir / "project.yaml"
    if not project_dir.is_dir() or not config.is_file():
        raise ValueError(f"Project directory must exist and contain project.yaml: {project_dir}")
    for line in config.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^project_id:\s*['\"]?([^'\"#\s]+)", line)
        if match:
            return match.group(1)
    raise ValueError(f"project_id is missing from {config}")


def file_sha256(location: str) -> str | None:
    path = Path(location)
    if not path.is_file():
        return None
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def idea_paths(project_dir: Path, idea_id: str) -> tuple[Path, Path]:
    return (
        project_dir / "ideas" / "records" / f"{idea_id}.json",
        project_dir / "ideas" / "notes" / f"{idea_id}.md",
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_entry(location: str | None, anchor: str | None, role: str) -> dict[str, Any] | None:
    if not location:
        return None
    return {
        "location": location,
        "sha256": file_sha256(location),
        "anchor": anchor,
        "role": role,
    }


def create_note(record: dict[str, Any]) -> str:
    sources = record["provenance"]["sources"]
    source_lines = "\n".join(
        f"- `{item['location']}`"
        + (f"，位置：{item['anchor']}" if item.get("anchor") else "")
        + (f"，SHA-256：`{item['sha256']}`" if item.get("sha256") else "")
        for item in sources
    ) or "- 尚未登记"
    assumptions = "\n".join(f"- {item}" for item in record["assumptions"]) or "- 待补充"
    alternatives = "\n".join(f"- {item}" for item in record["alternatives"]) or "- 待补充"
    success = "\n".join(f"- {item}" for item in record["validation"]["success_criteria"]) or "- 待补充"
    failure = "\n".join(f"- {item}" for item in record["validation"]["failure_signals"]) or "- 待补充"
    return f'''---
idea_id: "{record['idea_id']}"
status: "{record['status']}"
kind: "{record['kind']}"
---

# {record['title']}

> 本页记录研究想法及其演变；机器可读状态以对应 JSON 记录为准。

## 当前表述

{record['statement']}

## 动机

{record['motivation'] or '待补充。'}

## 来源与归属

{source_lines}

初始记录由 Agent 根据已注明来源整理，需由研究者继续评审。

## 假设与前提

{assumptions}

## 已考虑的替代方案

{alternatives}

## 验证与证伪

### 成功标准

{success}

### 失败信号

{failure}

### 计划实验

- 尚未关联 `EXP-*`。

## 演变记录

- {record['created_at']} `captured`：首次登记。

## 可追溯关系

- 相关文献：{', '.join(record['traceability']['lit_ids']) or '尚未关联'}
- 相关 TODO：{', '.join(record['traceability']['task_ids']) or '尚未关联'}
- 相关实验：{', '.join(record['traceability']['experiment_ids']) or '尚未关联'}
- 相关论文结论：{', '.join(record['traceability']['claim_ids']) or '尚未关联'}
'''


def rebuild_index(project_dir: Path) -> list[dict[str, Any]]:
    records_dir = project_dir / "ideas" / "records"
    works: list[dict[str, Any]] = []
    if records_dir.is_dir():
        for path in sorted(records_dir.glob("IDEA-*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            works.append({
                "idea_id": record["idea_id"],
                "title": record["title"],
                "kind": record["kind"],
                "status": record["status"],
                "statement": record["statement"],
                "record_path": f"records/{path.name}",
                "note_path": f"notes/{path.stem}.md",
                "updated_at": record["updated_at"],
            })
    write_json(project_dir / "ideas" / "index.json", {"schema_version": 1, "ideas": works})
    return works


def command_create(args: argparse.Namespace) -> dict[str, Any]:
    project_dir = Path(args.project_dir).resolve()
    project_id = read_project_id(project_dir)
    idea_id = f"IDEA-{digest(f'{project_id}|{normalize(args.title)}', 12)}"
    record_path, note_path = idea_paths(project_dir, idea_id)
    if record_path.exists():
        raise ValueError(f"Idea already exists: {idea_id}")
    now = utc_now()
    source = source_entry(args.source, args.source_anchor, args.source_role)
    event_id = f"EVT-{digest(f'{idea_id}|{now}|captured|{args.statement}', 10)}"
    record = {
        "schema_version": 1,
        "idea_id": idea_id,
        "project_id": project_id,
        "title": args.title,
        "kind": args.kind,
        "status": args.status,
        "statement": args.statement,
        "motivation": args.motivation,
        "assumptions": args.assumption,
        "alternatives": args.alternative,
        "validation": {
            "success_criteria": args.success_criterion,
            "failure_signals": args.failure_signal,
            "experiment_ids": [],
        },
        "evolution": [{
            "event_id": event_id,
            "timestamp": now,
            "type": "captured",
            "summary": "Initial capture",
            "reason": args.capture_reason,
            "source": args.source,
        }],
        "tags": args.tag,
        "provenance": {"sources": [source] if source else []},
        "traceability": {
            "lit_ids": args.lit_id,
            "task_ids": args.task_id,
            "experiment_ids": [],
            "claim_ids": [],
            "parent_idea_ids": args.parent_idea,
            "supersedes": [],
            "superseded_by": [],
        },
        "created_at": now,
        "updated_at": now,
    }
    write_json(record_path, record)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(create_note(record), encoding="utf-8")
    rebuild_index(project_dir)
    return {"action": "created", "idea_id": idea_id, "record_path": str(record_path), "note_path": str(note_path)}


def command_evolve(args: argparse.Namespace) -> dict[str, Any]:
    project_dir = Path(args.project_dir).resolve()
    read_project_id(project_dir)
    record_path, _ = idea_paths(project_dir, args.idea_id)
    if not record_path.is_file():
        raise ValueError(f"Unknown idea: {args.idea_id}")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    now = utc_now()
    event = {
        "event_id": f"EVT-{digest(f'{args.idea_id}|{now}|{args.event_type}|{args.summary}', 10)}",
        "timestamp": now,
        "type": args.event_type,
        "summary": args.summary,
        "reason": args.reason,
        "source": args.source,
    }
    record["evolution"].append(event)
    if args.status:
        record["status"] = args.status
    if args.statement:
        record["statement"] = args.statement
    record["updated_at"] = now
    write_json(record_path, record)
    rebuild_index(project_dir)
    return {"action": "evolved", "idea_id": args.idea_id, "event_id": event["event_id"]}


def validate_record(record: dict[str, Any], path: Path, project_id: str) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version", "idea_id", "project_id", "title", "kind", "status", "statement",
        "motivation", "assumptions", "alternatives", "validation", "evolution", "provenance",
        "traceability", "created_at", "updated_at",
    }
    missing = sorted(required - record.keys())
    if missing:
        errors.append(f"{path}: missing fields: {', '.join(missing)}")
        return errors
    if record["schema_version"] != 1:
        errors.append(f"{path}: unsupported schema_version")
    if not IDEA_PATTERN.fullmatch(record["idea_id"]) or path.stem != record["idea_id"]:
        errors.append(f"{path}: invalid or mismatched idea_id")
    if record["project_id"] != project_id:
        errors.append(f"{path}: project_id mismatch")
    if record["kind"] not in KINDS:
        errors.append(f"{path}: invalid kind: {record['kind']}")
    if record["status"] not in STATUSES:
        errors.append(f"{path}: invalid status: {record['status']}")
    if not record["statement"].strip():
        errors.append(f"{path}: statement must not be empty")
    event_ids = [event.get("event_id") for event in record["evolution"]]
    if not event_ids or len(event_ids) != len(set(event_ids)):
        errors.append(f"{path}: evolution must contain unique events")
    return errors


def command_validate(args: argparse.Namespace) -> dict[str, Any]:
    project_dir = Path(args.project_dir).resolve()
    project_id = read_project_id(project_dir)
    records_dir = project_dir / "ideas" / "records"
    errors: list[str] = []
    count = 0
    for path in sorted(records_dir.glob("IDEA-*.json")) if records_dir.is_dir() else []:
        count += 1
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        errors.extend(validate_record(record, path, project_id))
        note = project_dir / "ideas" / "notes" / f"{path.stem}.md"
        if not note.is_file():
            errors.append(f"{path}: missing note {note}")
    rebuild_index(project_dir)
    if errors:
        raise ValueError("\n".join(errors))
    return {"action": "validated", "project_id": project_id, "record_count": count}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain traceable ResearchCenter idea records.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create an idea record and Chinese note")
    create.add_argument("--project-dir", required=True)
    create.add_argument("--title", required=True)
    create.add_argument("--kind", choices=sorted(KINDS), required=True)
    create.add_argument("--status", choices=sorted(STATUSES), default="proposed")
    create.add_argument("--statement", required=True)
    create.add_argument("--motivation", default="")
    create.add_argument("--assumption", action="append", default=[])
    create.add_argument("--alternative", action="append", default=[])
    create.add_argument("--success-criterion", action="append", default=[])
    create.add_argument("--failure-signal", action="append", default=[])
    create.add_argument("--source")
    create.add_argument("--source-anchor")
    create.add_argument("--source-role", default="researcher-provided")
    create.add_argument("--capture-reason", default="Captured from supplied research material.")
    create.add_argument("--tag", action="append", default=[])
    create.add_argument("--lit-id", action="append", default=[])
    create.add_argument("--task-id", action="append", default=[])
    create.add_argument("--parent-idea", action="append", default=[])
    create.set_defaults(handler=command_create)

    evolve = subparsers.add_parser("evolve", help="Append an evolution event")
    evolve.add_argument("--project-dir", required=True)
    evolve.add_argument("--idea-id", required=True)
    evolve.add_argument("--event-type", choices=sorted(EVENT_TYPES), required=True)
    evolve.add_argument("--summary", required=True)
    evolve.add_argument("--reason", required=True)
    evolve.add_argument("--source")
    evolve.add_argument("--status", choices=sorted(STATUSES))
    evolve.add_argument("--statement")
    evolve.set_defaults(handler=command_evolve)

    validate = subparsers.add_parser("validate", help="Validate records and rebuild the index")
    validate.add_argument("--project-dir", required=True)
    validate.set_defaults(handler=command_validate)

    task_id = subparsers.add_parser("task-id", help="Generate a stable TASK ID")
    task_id.add_argument("--project-dir", required=True)
    task_id.add_argument("--text", required=True)
    task_id.set_defaults(handler=lambda args: {
        "task_id": f"TASK-{digest(f'{read_project_id(Path(args.project_dir).resolve())}|{normalize(args.text)}', 10)}"
    })
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
