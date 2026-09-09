"""Deterministic fixture outputs exercise the workflow, not model quality."""

import shutil
import sys
from pathlib import Path

from .utils import QAError, git, new_dir, save
from .workflow import accept, approve, prepare, stage, verify

DATA = Path(__file__).parent / "demo_data"


def ref(path, line, reason):
    return {"path": path, "start_line": line, "end_line": line, "reason": reason}


def risk_fixture():
    return {"summary": "Deadline equality is not covered and contradicts the story.",
        "scenarios": [
            {"id": "S1", "behavior": "Submission before deadline is allowed", "risk": "high", "layer": "unit",
             "rationale": "Isolated deterministic helper", "oracle": "True strictly before deadline",
             "coverage": "covered", "references": [ref("tests/test_existing.py", 10, "Existing happy-path assertion")],
             "gaps": ["API and UI enforcement not inspected"]},
            {"id": "S2", "behavior": "Submission exactly at deadline is rejected", "risk": "high", "layer": "unit",
             "rationale": "Boundary is inside the helper", "oracle": "False at deadline per story",
             "coverage": "missing", "references": [ref("admissions.py", 8, "Inclusive comparison accepts equality")],
             "gaps": ["No equality test in this example's selected files"]},
            {"id": "S3", "behavior": "Submission after deadline is rejected", "risk": "high", "layer": "unit",
             "rationale": "No dependency needs a browser", "oracle": "False after deadline",
             "coverage": "missing", "references": [ref("admissions.py", 8, "Date comparison")], "gaps": []}],
        "questions": [], "limitations": ["Synthetic offline fixture, not an LLM-generated analysis",
                                          "Naive datetime validation still requires a separate scenario"]}


def builder_fixture():
    code = '''import unittest
from datetime import datetime, timedelta, timezone
from admissions import can_submit


class DeadlineRegression(unittest.TestCase):
    def test_at_deadline_rejected(self):
        deadline = datetime(2030, 1, 1, tzinfo=timezone.utc)
        self.assertFalse(can_submit(deadline, deadline))

    def test_after_deadline_rejected(self):
        deadline = datetime(2030, 1, 1, tzinfo=timezone.utc)
        self.assertFalse(can_submit(deadline + timedelta(seconds=1), deadline))
'''
    return {"summary": "Add equality and after-deadline tests. Equality should fail on current code.",
            "files": [{"path": "tests/test_deadline.py", "content": code,
                       "scenario_ids": ["S2", "S3"], "rationale": "Test expected business behavior, not the bug"}],
            "suggested_checks": ["python -m unittest discover -s tests -v"],
            "limitations": ["Synthetic offline fixture; tests have not yet been executed at proposal time"]}


def demo(out):
    root = new_dir(out)
    repo = root / "sample-project"
    shutil.copytree(DATA, repo, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    git(repo, "init", "-b", "main")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Quality Agents Demo", "-c", "user.email=demo@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-m", "Synthetic deadline example")
    story = repo / "story.md"
    risk = prepare("risk", repo, story, root / "01-risk")
    accept(risk, risk_fixture(), {"provider": "offline-fixture", "model": None})
    approve(risk, "DEMO FIXTURE", "Simulated review for bundled synthetic example only")
    builder = prepare("builder", repo, story, root / "02-builder", plan=risk)
    accept(builder, builder_fixture(), {"provider": "offline-fixture", "model": None})
    approve(builder, "DEMO FIXTURE", "Expected failing boundary test is intentional")
    staged = stage(builder, root / "03-staged")
    result = verify(staged, [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    if result["status"] != "failed":
        raise QAError("Demo expected a failing regression test; inspect verification.txt")
    log = (staged / "verification.txt").read_text()
    if "AssertionError: True is not false" not in log or "Ran 3 tests" not in log:
        raise QAError("Demo failed for an unexpected reason")
    failure = prepare("failure", repo, story, root / "04-failure", evidence=[staged / "verification.txt"])
    line = next(i for i, x in enumerate(log.splitlines(), 1) if "AssertionError:" in x)
    accept(failure, {"summary": "Boundary regression caught the intentional product defect.",
        "findings": [{"classification": "product", "confidence": "high",
            "hypothesis": "can_submit accepts equality while the story requires strictly before.",
            "references": [ref("admissions.py", 8, "Inclusive comparison"),
                           ref("evidence/1.txt", line, "Observed assertion failure")],
            "alternative_causes": ["Acceptance criteria might be wrong; product owner must confirm"],
            "next_action": "Developer reviews changing <= to < and reruns the regression. Keep this unit test.",
            "suggested_owner": "Feature developer"}],
        "limitations": ["Offline diagnosis fixture, not model inference. Test execution is real.",
                         "This does not evaluate production agent quality or the whole application."]},
        {"provider": "offline-fixture", "model": None})
    save(root / "summary.json", {"mode": "offline-fixture", "model_called": False,
        "tests_executed": True, "tests_run": 3, "expected_failures": 1,
        "target_modified": bool(git(repo, "status", "--porcelain")), "result": "demo completed"})
    return f"Demo completed: 3 real tests, 1 intentional failure. No model called. Read {failure / 'report.md'}"
