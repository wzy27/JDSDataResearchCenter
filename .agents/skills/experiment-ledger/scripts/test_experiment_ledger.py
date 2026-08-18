import importlib.util
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("experiment_ledger.py")
SPEC = importlib.util.spec_from_file_location("experiment_ledger", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ExperimentLedgerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "demo"
        self.project.mkdir()
        (self.project / "project.yaml").write_text("project_id: demo\n", encoding="utf-8")
        (self.project / "TODO.md").write_text("TASK-1234567890\n", encoding="utf-8")
        idea_dir = self.project / "ideas" / "records"
        idea_dir.mkdir(parents=True)
        (idea_dir / "IDEA-123456789ABC.json").write_text("{}\n", encoding="utf-8")
        self.spec = {
            "title": "最小 smoke test", "type": "smoke-test", "status": "blocked",
            "objective": "验证最小链路。",
            "protocol": {"scope": "一条样本", "success_criteria": ["输出完整"], "failure_criteria": ["输出缺失"], "expected_outputs": []},
            "traceability": {"idea_ids": ["IDEA-123456789ABC"], "task_ids": ["TASK-1234567890"], "lit_ids": [], "claim_ids": [], "parent_experiment_ids": []},
            "execution": {"executor_id": None, "cwd": {"connection": "code", "relative_path": "."}, "command_argv": [], "required_commands": ["definitely-missing-command"], "required_connections": ["code"], "watchdog_policy": None},
            "code": {"repository": None, "commit": None, "dirty": None, "patch_uri": None},
            "data": {"datasets": []},
            "environment": {"os": None, "runtime": None, "lockfile": None, "seeds": {}},
            "resources": {"accelerator": {"vendor": "none", "count": 0, "min_vram_gb": None, "cuda": None, "driver": None}, "min_disk_gb": None},
            "blockers": [{"code": "NO-EXECUTOR", "description": "missing", "resolution": "configure"}],
        }
        self.spec_path = Path(self.temp.name) / "spec.json"
        self.spec_path.write_text(json.dumps(self.spec, ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def create(self):
        return MODULE.command_create(Namespace(project_dir=str(self.project), spec=str(self.spec_path)))

    def test_create_and_stable_id(self):
        result = self.create()
        expected = f"EXP-{MODULE.digest('demo|最小 smoke test', 12)}"
        self.assertEqual(expected, result["experiment_id"])
        self.assertTrue(Path(result["note_path"]).is_file())

    def test_duplicate_is_rejected(self):
        self.create()
        with self.assertRaises(ValueError):
            self.create()

    def test_validate_links(self):
        self.create()
        result = MODULE.command_validate(Namespace(project_dir=str(self.project)))
        self.assertEqual(1, result["record_count"])

    def test_blocked_requires_blocker(self):
        record = MODULE.build_record("demo", {**self.spec, "blockers": []})
        path = Path(self.temp.name) / f"{record['experiment_id']}.json"
        errors = MODULE.validate_record(record, path, self.project, "demo")
        self.assertTrue(any("requires blockers" in item for item in errors))

    def test_preflight_does_not_launch(self):
        result = self.create()
        record = MODULE.load_json(Path(result["record_path"]))
        report = MODULE.run_preflight(record, {"executor_id": "test", "os": "windows", "connections": {}, "commands": {}})
        self.assertFalse(report["passed"])
        self.assertFalse(report["launch_performed"])

    def test_preflight_detects_ascend_devices(self):
        record = MODULE.build_record("demo", {
            **self.spec,
            "resources": {"accelerator": {"vendor": "ascend", "count": 2}, "min_disk_gb": None},
        })
        with patch.object(MODULE, "resolve_command", return_value="npu-smi"), patch.object(
            MODULE.subprocess, "run",
            return_value=SimpleNamespace(returncode=0, stdout="NPU ID : 0\nNPU ID : 1\n", stderr=""),
        ):
            report = MODULE.run_preflight(record, {"executor_id": "test", "os": "windows", "connections": {}})
        accelerator_check = next(item for item in report["checks"] if item["name"] == "accelerator:ascend")
        self.assertTrue(accelerator_check["passed"])
        self.assertEqual("detected=2, required=2", accelerator_check["detail"])

    def test_ready_rejects_remaining_blockers(self):
        result = self.create()
        with self.assertRaises(ValueError):
            MODULE.command_transition(Namespace(
                project_dir=str(self.project), experiment_id=result["experiment_id"], status="ready",
                reason="not actually ready", evidence=None,
            ))

    def test_validate_rejects_manually_forced_ready(self):
        record = MODULE.build_record("demo", {**self.spec, "status": "ready", "blockers": []})
        path = Path(self.temp.name) / f"{record['experiment_id']}.json"
        errors = MODULE.validate_record(record, path, self.project, "demo")
        self.assertTrue(any("executable status requires" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
