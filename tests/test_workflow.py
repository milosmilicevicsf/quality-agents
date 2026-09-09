import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quality_agents.cli import main
from quality_agents.context import DEFAULT, collect, config
from quality_agents.demo import DATA, builder_fixture, demo, risk_fixture
from quality_agents.provider import call, parse_response, payload
from quality_agents.schemas import SCHEMAS, validate
from quality_agents.utils import QAError, envelope, git, load, redact, safe_relative, save, unwrap
from quality_agents.workflow import accept, approve, prepare, stage, verify


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "project"
        shutil.copytree(DATA, self.repo, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        git(self.repo, "init", "-b", "main")
        self.commit()
        self.story = self.repo / "story.md"

    def tearDown(self):
        self.temp.cleanup()

    def commit(self):
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-m", "test")

    def risk(self):
        run = prepare("risk", self.repo, self.story, self.root / "risk")
        accept(run, risk_fixture(), {"provider": "test"})
        approve(run, "human", "Reviewed assertions and source")
        return run

    def builder(self):
        risk = self.risk()
        run = prepare("builder", self.repo, self.story, self.root / "builder", plan=risk)
        accept(run, builder_fixture(), {"provider": "test"})
        approve(run, "human", "Reviewed complete test code")
        return run

    def test_full_workflow_preserves_target_and_executes_real_test(self):
        before = git(self.repo, "rev-parse", "HEAD")
        folder = stage(self.builder(), self.root / "staged")
        result = verify(folder, [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
        self.assertEqual(result["status"], "failed")
        log = (folder / "verification.txt").read_text()
        self.assertIn("AssertionError: True is not false", log)
        self.assertIn("Ran 3 tests", log)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), before)
        git(self.repo, "apply", "--check", str(folder / "changes.patch"))

    def test_dirty_repo_is_rejected(self):
        (self.repo / "admissions.py").write_text("changed")
        with self.assertRaisesRegex(QAError, "Commit/stash"):
            prepare("risk", self.repo, self.story, self.root / "run")

    def test_patch_applies_to_existing_test_without_final_newline(self):
        existing = self.repo / "tests/test_existing.py"
        existing.write_bytes(existing.read_bytes().rstrip(b"\n"))
        self.commit()
        risk = self.risk()
        run = prepare("builder", self.repo, self.story, self.root / "builder", plan=risk)
        report = builder_fixture()
        report["files"][0]["path"] = "tests/test_existing.py"
        report["files"][0]["content"] = existing.read_text() + "\n# reviewed addition\n"
        accept(run, report, {"provider": "test"})
        approve(run, "human", "Reviewed complete file")
        folder = stage(run, self.root / "staged")
        git(self.repo, "apply", "--check", str(folder / "changes.patch"))
        git(self.repo, "apply", str(folder / "changes.patch"))
        self.assertEqual(existing.read_bytes(), (folder / "repo/tests/test_existing.py").read_bytes())

    def test_untracked_file_is_rejected(self):
        (self.repo / "new.py").write_text("pass\n")
        with self.assertRaises(QAError):
            prepare("risk", self.repo, self.story, self.root / "run")

    def test_context_excludes_secrets_and_marks_omissions(self):
        (self.repo / ".env").write_text("PASSWORD=not-for-the-model")
        (self.repo / "credentials.json").write_text('{"password":"not-for-the-model"}')
        (self.repo / "token.py").write_text('api_key = "super-secret-value"\n')
        self.commit()
        data = collect(self.repo, self.story, config())
        encoded = json.dumps(data)
        self.assertNotIn("not-for-the-model", encoded)
        self.assertNotIn("super-secret-value", encoded)
        self.assertGreaterEqual(len(data["omitted"]), 3)

    def test_context_budget_and_focus_are_explicit(self):
        data = collect(self.repo, self.story, {**config(), "max_files": 1, "focus": ["admissions.py"]})
        self.assertEqual(data["files"][0]["path"], "admissions.py")
        self.assertTrue(any(x["reason"] == "context budget" for x in data["omitted"]))

    def test_citations_must_exist(self):
        run = prepare("risk", self.repo, self.story, self.root / "risk")
        report = risk_fixture()
        report["scenarios"][0]["references"][0]["end_line"] = 1000
        with self.assertRaisesRegex(QAError, "Citation"):
            accept(run, report, {"provider": "test"})
        self.assertFalse((run / "result.json").exists())

    def test_covered_requires_test_evidence(self):
        run = prepare("risk", self.repo, self.story, self.root / "risk")
        report = risk_fixture()
        report["scenarios"][1]["coverage"] = "covered"
        with self.assertRaisesRegex(QAError, "included test"):
            accept(run, report, {"provider": "test"})

    def test_duplicate_scenarios_rejected(self):
        run = prepare("risk", self.repo, self.story, self.root / "risk")
        report = risk_fixture()
        report["scenarios"][1]["id"] = "S1"
        with self.assertRaisesRegex(QAError, "unique"):
            accept(run, report, {"provider": "test"})

    def test_builder_requires_approval(self):
        with self.assertRaisesRegex(QAError, "requires --plan"):
            prepare("builder", self.repo, self.story, self.root / "builder")

    def test_changed_report_invalidates_approval(self):
        risk = self.risk()
        result = unwrap(risk / "result.json")
        result["report"]["summary"] = "tampered"
        save(risk / "result.json", envelope(result))
        with self.assertRaisesRegex(QAError, "stale"):
            prepare("builder", self.repo, self.story, self.root / "builder", plan=risk)

    def test_changed_commit_invalidates_approval(self):
        risk = self.risk()
        with (self.repo / "admissions.py").open("a") as f:
            f.write("\n# new commit\n")
        self.commit()
        with self.assertRaisesRegex(QAError, "HEAD"):
            prepare("builder", self.repo, self.story, self.root / "builder", plan=risk)

    def test_changed_story_invalidates_approval(self):
        risk = self.risk()
        external = self.root / "different.md"
        external.write_text("A different requirement")
        with self.assertRaisesRegex(QAError, "Story"):
            prepare("builder", self.repo, external, self.root / "builder", plan=risk)

    def test_production_file_proposal_rejected(self):
        risk = self.risk()
        run = prepare("builder", self.repo, self.story, self.root / "builder", plan=risk)
        report = builder_fixture()
        report["files"][0]["path"] = "admissions.py"
        with self.assertRaisesRegex(QAError, "non-test"):
            accept(run, report, {"provider": "test"})

    def test_traversal_rejected(self):
        risk = self.risk()
        run = prepare("builder", self.repo, self.story, self.root / "builder", plan=risk)
        report = builder_fixture()
        report["files"][0]["path"] = "tests/../../outside.py"
        with self.assertRaisesRegex(QAError, "Unsafe"):
            accept(run, report, {"provider": "test"})

    def test_unapproved_scenario_rejected(self):
        risk = self.risk()
        run = prepare("builder", self.repo, self.story, self.root / "builder", plan=risk)
        report = builder_fixture()
        report["files"][0]["scenario_ids"] = ["invented"]
        with self.assertRaisesRegex(QAError, "unapproved"):
            accept(run, report, {"provider": "test"})

    def test_stage_tamper_blocks_execution(self):
        folder = stage(self.builder(), self.root / "stage")
        (folder / "repo/admissions.py").write_text("tampered")
        with self.assertRaisesRegex(QAError, "changed after approval"):
            verify(folder, [sys.executable, "--version"])

    def test_timeout_is_failure(self):
        folder = stage(self.builder(), self.root / "stage")
        result = verify(folder, [sys.executable, "-c", "import time; time.sleep(5)"], timeout=1)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["exit_code"], 124)

    def test_execution_does_not_inherit_api_credentials(self):
        folder = stage(self.builder(), self.root / "stage")
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-sensitive-value"}):
            result = verify(folder, [sys.executable, "-c",
                "import os; assert 'OPENAI_API_KEY' not in os.environ; print('clean')"])
        self.assertEqual(result["status"], "passed")

    def test_failure_requires_actual_evidence(self):
        with self.assertRaisesRegex(QAError, "actual logs"):
            prepare("failure", self.repo, self.story, self.root / "failure")

    def test_results_not_overwritten(self):
        run = self.risk()
        with self.assertRaisesRegex(QAError, "already exists"):
            accept(run, risk_fixture(), {"provider": "test"})

    def test_offline_demo(self):
        result = demo(self.root / "demo")
        self.assertIn("No model called", result)
        summary = load(self.root / "demo/summary.json")
        self.assertFalse(summary["target_modified"])

    def test_diff_and_framework_hints(self):
        base = git(self.repo, "rev-parse", "HEAD")
        with (self.repo / "admissions.py").open("a") as f:
            f.write("\n# changed\n")
        self.commit()
        data = collect(self.repo, self.story, config(), base=base)
        self.assertIn("+# changed", data["selected_diff"])
        self.assertIn("unittest", data["framework_hints"])


class ContractTest(unittest.TestCase):
    def test_unknown_fields_rejected(self):
        report = risk_fixture()
        report["release_approved"] = True
        with self.assertRaises(QAError):
            validate(report, SCHEMAS["risk"])

    def test_unsafe_paths(self):
        for name in ["../x", "/tmp/x", "C:\\temp\\x", ".", "tests/../x", ".git/hooks/x", "tests//x"]:
            with self.subTest(name=name), self.assertRaises(QAError):
                safe_relative(name)

    def test_redaction(self):
        value = redact("api_key=private\nContact: someone@example.com\nsk-abcdefghijklmnopqrstuvwxyz")
        self.assertNotIn("private", value)
        self.assertNotIn("someone@example.com", value)
        self.assertNotIn("sk-abc", value)

    def test_api_requires_explicit_send(self):
        with self.assertRaisesRegex(QAError, "--send"):
            call({}, "test-model")

    def test_api_requires_local_key(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaisesRegex(QAError, "OPENAI_API_KEY"):
            call({}, "test-model", send=True)

    def test_response_refusal_and_incomplete_are_not_reports(self):
        for response in [{"status": "incomplete"}, {"status": "completed", "output": []},
                         {"status": "completed", "output": [{"content": [{"type": "refusal"}]}]}]:
            with self.subTest(response=response), self.assertRaises(QAError):
                parse_response(response)

    def test_completed_api_json_parsed(self):
        response = {"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(risk_fixture())}]}]}
        self.assertEqual(parse_response(response), risk_fixture())

    def test_request_uses_schema_no_remote_tools_and_no_storage(self):
        packet = {"instructions": "x", "context": {}, "role": "risk", "schema": SCHEMAS["risk"]}
        request = payload(packet, "selected-model")
        self.assertFalse(request["store"])
        self.assertNotIn("tools", request)
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertEqual(request["model"], "selected-model")


if __name__ == "__main__":
    unittest.main()
