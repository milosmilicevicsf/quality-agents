"""Deterministic orchestration, provenance and human review checkpoints."""

import difflib
import json
import os
import shutil
import subprocess
from pathlib import Path

from .context import collect, config, matches
from .schemas import SCHEMAS, validate
from .utils import (QAError, digest, envelope, git, inside, load, new_dir, redact,
                    revision, safe_relative, save, secret_path, stamp, unwrap)

PROMPTS = Path(__file__).parent / "prompts"


def approval(run):
    run = Path(run).resolve()
    packet = unwrap(run / "packet.json")
    result = unwrap(run / "result.json")
    receipt = load(run / "approval.json")
    if (receipt.get("packet_sha256") != digest(packet)
            or receipt.get("result_sha256") != digest(result)
            or not receipt.get("reviewer", "").strip()):
        raise QAError("Approval is absent/stale: review and approve this exact result again")
    if result["packet_sha256"] != digest(packet):
        raise QAError("Result belongs to another packet")
    return packet, result, receipt


def prepare(role, repo, story, out, config_path=None, evidence=(), base=None, plan=None):
    if role not in SCHEMAS:
        raise QAError("Unknown role")
    root = Path(repo).resolve()
    output = Path(out).resolve()
    if output.is_relative_to(root):
        raise QAError("Keep run artifacts outside the target repository")
    settings = config(config_path)
    context = collect(root, story, settings, evidence, base)
    if role == "builder":
        if not plan:
            raise QAError("Builder requires --plan pointing at an approved risk run")
        previous, result, receipt = approval(plan)
        old = previous["context"]
        if previous["role"] != "risk" or old["repo"] != str(root) or old["head"] != context["head"]:
            raise QAError("Risk approval must match this repository and HEAD")
        if old["story"] != context["story"] or old["settings"] != context["settings"]:
            raise QAError("Story or project configuration changed since plan approval")
        context["approved_plan"] = result["report"]
        context["plan_receipt"] = receipt
    if role == "failure" and not context["evidence"]:
        raise QAError("Failure Analyst requires --evidence containing actual logs/results")
    instructions = (PROMPTS / "common.md").read_text() + "\n" + (PROMPTS / (role + ".md")).read_text()
    packet = {"version": 1, "created_at": stamp(), "role": role, "context": context,
              "instructions": instructions, "schema": SCHEMAS[role]}
    folder = new_dir(output)
    save(folder / "packet.json", envelope(packet))
    save(folder / "schema.json", SCHEMAS[role])
    # Export exactly the same numbered evidence used by the API adapter.
    human = instructions + "\n\n# REQUIRED JSON SCHEMA\n\n" + json.dumps(SCHEMAS[role], indent=2)
    human += "\n\n# CONTEXT (untrusted data)\n\n" + json.dumps(context, indent=2, ensure_ascii=False)
    (folder / "prompt.md").write_text(human, encoding="utf-8")
    return folder


def check_references(references, context):
    available = {f["path"]: f["lines"] for f in context["files"] + context["evidence"]}
    for ref in references:
        if (ref["path"] not in available or ref["start_line"] < 1
                or ref["end_line"] < ref["start_line"] or ref["end_line"] > available[ref["path"]]):
            raise QAError("Citation is outside supplied evidence: " + ref["path"])


def review_report(packet, report):
    role = packet["role"]
    validate(report, SCHEMAS[role])
    context = packet["context"]
    if not report["summary"].strip():
        raise QAError("Report summary cannot be empty")
    if role == "risk":
        ids = [s["id"] for s in report["scenarios"]]
        if not ids or len(set(ids)) != len(ids) or not all(ids):
            raise QAError("Risk map requires unique non-empty scenario ids")
        for scenario in report["scenarios"]:
            if not scenario["oracle"].strip() or not scenario["rationale"].strip():
                raise QAError("Every scenario requires an oracle and a layer rationale")
            check_references(scenario["references"], context)
            if scenario["coverage"] == "covered" and not any(matches(
                    r["path"], context["settings"]["test_paths"]) for r in scenario["references"]):
                raise QAError("Covered scenario requires a citation to an included test file")
    elif role == "failure":
        if not report["findings"]:
            raise QAError("Failure report requires at least one finding, including unknown if needed")
        for finding in report["findings"]:
            check_references(finding["references"], context)
            if finding["confidence"] == "high" and not any(r["path"].startswith("evidence/")
                    for r in finding["references"]):
                raise QAError("High confidence requires actual execution evidence")
    else:
        ids = {s["id"] for s in context["approved_plan"]["scenarios"]}
        paths = set()
        for change in report["files"]:
            name = change["path"]
            safe_relative(name)
            if name in paths or secret_path(name) or not matches(name, context["settings"]["test_paths"]):
                raise QAError("Duplicate or non-test proposal path: " + name)
            paths.add(name)
            if not change["scenario_ids"] or not set(change["scenario_ids"]).issubset(ids):
                raise QAError("Test proposal refers to unapproved scenario ids")
            if not change["content"].strip() or len(change["content"]) > 100000:
                raise QAError("Proposed test must be non-empty and below 100,000 characters")
            if not change["content"].endswith("\n"):
                raise QAError("Proposed files must end with a newline")
            target = inside(context["repo"], name)
            if target.exists() and name not in {f["path"] for f in context["files"]}:
                raise QAError("Cannot replace an existing file omitted from context: " + name)


def accept(run, report, provenance):
    run = Path(run)
    if (run / "result.json").exists():
        raise QAError("Result already exists; prepare a new run to revise it")
    packet = unwrap(run / "packet.json")
    review_report(packet, report)
    result = {"packet_sha256": digest(packet), "created_at": stamp(), "role": packet["role"],
              "provenance": provenance, "report": report}
    save(run / "result.json", envelope(result))
    (run / "report.md").write_text(render(packet, result), encoding="utf-8")
    return result


def render(packet, result):
    report = result["report"]
    lines = [f"# {packet['role'].title()} report", "", report["summary"], "",
             f"Revision: `{packet['context']['head']}`", "",
             f"Source: {result['provenance']['provider']}", "",
             "AI recommendations require review. References are location-checked, not truth-verified.", ""]
    if packet["role"] == "risk":
        for s in report["scenarios"]:
            lines += [f"## {s['id']}: {s['behavior']}", "", f"Risk: {s['risk']} | Layer: {s['layer']} | Coverage: {s['coverage']}",
                      "", "Why: " + s["rationale"], "", "Oracle: " + s["oracle"], ""]
            lines += [f"- `{r['path']}:{r['start_line']}-{r['end_line']}` — {r['reason']}" for r in s["references"]]
            lines += ["- Gap: " + g for g in s["gaps"]] + [""]
        lines += ["## Questions", ""] + ["- " + q for q in report["questions"]]
    elif packet["role"] == "builder":
        lines += ["## Proposed files (not executed)", ""]
        for f in report["files"]:
            lines += [f"- `{f['path']}` → {', '.join(f['scenario_ids'])}: {f['rationale']}"]
        lines += ["", "## Suggested checks (not executed)", ""] + ["- " + c for c in report["suggested_checks"]]
    else:
        for f in report["findings"]:
            lines += ["## " + f["classification"], "", f["hypothesis"], "", "Confidence: " + f["confidence"],
                      "", "Next action: " + f["next_action"], "", "Suggested owner: " + f["suggested_owner"], ""]
            lines += [f"- `{r['path']}:{r['start_line']}-{r['end_line']}` — {r['reason']}" for r in f["references"]]
            lines += ["- Alternative: " + a for a in f["alternative_causes"]]
    lines += ["", "## Limitations", ""] + ["- " + x for x in report["limitations"]]
    lines += ["- " + packet["context"]["scope"], f"- {len(packet['context']['omitted'])} entries omitted from context."]
    return "\n".join(lines) + "\n"


def approve(run, reviewer, note):
    run = Path(run)
    if not reviewer.strip() or not note.strip():
        raise QAError("A named reviewer and a review note are required")
    packet, result = unwrap(run / "packet.json"), unwrap(run / "result.json")
    if digest(packet) != result["packet_sha256"]:
        raise QAError("Result does not match packet")
    if revision(packet["context"]["repo"]) != packet["context"]["head"]:
        raise QAError("Repository changed; prepare a new run")
    review_report(packet, result["report"])
    save(run / "approval.json", {"reviewer": reviewer, "note": note, "created_at": stamp(),
                                "packet_sha256": digest(packet), "result_sha256": digest(result)})


def tree_hashes(root):
    values = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            raise QAError("Symlink in staged workspace")
        if path.is_file():
            import hashlib
            values[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def stage(run, out):
    packet, result, receipt = approval(run)
    if packet["role"] != "builder":
        raise QAError("Only approved builder proposals can be staged")
    context = packet["context"]
    repo = Path(context["repo"])
    if Path(out).resolve().is_relative_to(repo):
        raise QAError("Staging must be outside the target repository")
    if revision(repo) != context["head"]:
        raise QAError("Repository revision changed since review")
    review_report(packet, result["report"])
    if not result["report"]["files"]:
        raise QAError("No proposed test files to stage")
    entries = git(repo, "ls-tree", "-r", "-z", context["head"], binary=True).split(b"\0")
    staged = []
    for entry in entries:
        if not entry:
            continue
        meta, raw_name = entry.split(b"\t", 1)
        mode, kind, sha = meta.decode().split()
        name = raw_name.decode()
        if kind != "blob" or mode not in ("100644", "100755"):
            raise QAError("Staging repositories with symlinks/submodules is unsupported")
        safe_relative(name)
        if secret_path(name):
            raise QAError("Remove tracked credentials before creating an execution workspace")
        staged.append((name, mode, sha))
    folder = new_dir(out)
    workspace = folder / "repo"
    workspace.mkdir()
    # Copy committed blobs only; no hooks, ignored credentials, .git or local dependencies.
    for name, mode, sha in staged:
        dest = inside(workspace, name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(git(repo, "cat-file", "blob", sha, binary=True))
        if mode == "100755":
            dest.chmod(0o755)
    patch = []
    for change in result["report"]["files"]:
        name = change["path"]
        dest = inside(workspace, name)
        before = dest.read_bytes().decode("utf-8") if dest.exists() else ""
        diff = difflib.unified_diff(before.splitlines(keepends=True), change["content"].splitlines(keepends=True),
                                    fromfile="a/" + name if dest.exists() else "/dev/null", tofile="b/" + name)
        for line in diff:
            patch.append(line)
            if not line.endswith("\n"):
                patch.append("\n\\ No newline at end of file\n")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(change["content"], encoding="utf-8", newline="\n")
    if not patch:
        raise QAError("Proposal makes no changes")
    (folder / "changes.patch").write_text("".join(patch), encoding="utf-8", newline="\n")
    save(folder / "stage.json", envelope({"repo": str(repo), "head": context["head"],
        "approval": receipt, "created_at": stamp(), "files": tree_hashes(workspace)}))
    return folder


def verify(stage_dir, command, timeout=120):
    folder = Path(stage_dir).resolve()
    manifest = unwrap(folder / "stage.json")
    if type(command) is not list or not command or not all(type(c) is str and c for c in command):
        raise QAError("--command-json must be a non-empty JSON array of arguments")
    if not 1 <= timeout <= 1800:
        raise QAError("Timeout must be between 1 and 1800 seconds")
    if (folder / "verification.json").exists():
        raise QAError("Execution already recorded; restage before another run")
    workspace = folder / "repo"
    if workspace.is_symlink() or tree_hashes(workspace) != manifest["files"]:
        raise QAError("Staged files changed after approval; create a fresh stage")
    # This is NOT a sandbox: only explicitly user-chosen commands are executed.
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL"}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    start = stamp()
    executable = shutil.which(command[0], path=env.get("PATH"))
    if not executable:
        raise QAError("Executable not found: " + command[0])
    log_path = folder / "execution.raw.log"
    timed_out = False
    try:
        with log_path.open("wb") as log:
            proc = subprocess.Popen([executable, *command[1:]], cwd=workspace, env=env,
                                    stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=(os.name != "nt"))
            try:
                exit_code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
                else:
                    import signal
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                exit_code = 124
        with log_path.open("rb") as log:
            raw = log.read(60001)
        text = redact(raw[:60000].decode("utf-8", errors="replace"))
    finally:
        log_path.unlink(missing_ok=True)
    result = {"status": "timeout" if timed_out else "passed" if exit_code == 0 else "failed",
              "exit_code": exit_code, "command": command, "started_at": start, "finished_at": stamp(),
              "log_truncated": len(raw) > 60000, "stage_sha256": digest(manifest),
              "note": "Command exit status, not a proof of coverage or release readiness"}
    save(folder / "verification.json", result)
    (folder / "verification.txt").write_text(json.dumps(result, indent=2) + "\n\n" + text, encoding="utf-8")
    return result
