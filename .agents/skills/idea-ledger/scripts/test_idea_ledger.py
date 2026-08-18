import importlib.util
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


SCRIPT = Path(__file__).with_name("idea_ledger.py")
SPEC = importlib.util.spec_from_file_location("idea_ledger", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class IdeaLedgerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "demo"
        self.project.mkdir()
        (self.project / "project.yaml").write_text("project_id: demo\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def create_args(self):
        return Namespace(
            project_dir=str(self.project), title="同步六面采集", kind="method", status="active",
            statement="六面图应在同一仿真时刻采集。", motivation="避免动态错位。",
            assumption=["仿真状态可冻结。"], alternative=["状态缓存后重放。"],
            success_criterion=["动态物体跨面一致。"], failure_signal=["接缝处出现时间错位。"],
            source=None, source_anchor=None, source_role="researcher-provided",
            capture_reason="test", tag=["capture"], lit_id=[], task_id=[], parent_idea=[],
        )

    def test_id_is_stable(self):
        expected = f"IDEA-{MODULE.digest('demo|同步六面采集', 12)}"
        result = MODULE.command_create(self.create_args())
        self.assertEqual(expected, result["idea_id"])

    def test_create_writes_record_note_and_index(self):
        result = MODULE.command_create(self.create_args())
        idea_id = result["idea_id"]
        self.assertTrue((self.project / "ideas" / "records" / f"{idea_id}.json").is_file())
        self.assertIn("同一仿真时刻", (self.project / "ideas" / "notes" / f"{idea_id}.md").read_text(encoding="utf-8"))
        index = json.loads((self.project / "ideas" / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(idea_id, index["ideas"][0]["idea_id"])

    def test_duplicate_is_rejected(self):
        MODULE.command_create(self.create_args())
        with self.assertRaises(ValueError):
            MODULE.command_create(self.create_args())

    def test_evolution_is_append_only(self):
        result = MODULE.command_create(self.create_args())
        MODULE.command_evolve(Namespace(
            project_dir=str(self.project), idea_id=result["idea_id"], event_type="refined",
            summary="补充验收条件", reason="smoke test", source=None, status="testing",
            statement=None,
        ))
        path = self.project / "ideas" / "records" / f"{result['idea_id']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(2, len(record["evolution"]))
        self.assertEqual("testing", record["status"])

    def test_validate(self):
        MODULE.command_create(self.create_args())
        result = MODULE.command_validate(Namespace(project_dir=str(self.project)))
        self.assertEqual(1, result["record_count"])

    def test_task_id_is_stable(self):
        value = f"TASK-{MODULE.digest('demo|固定 ue 版本', 10)}"
        self.assertEqual(value, f"TASK-{MODULE.digest('demo|固定 ue 版本', 10)}")


if __name__ == "__main__":
    unittest.main()
