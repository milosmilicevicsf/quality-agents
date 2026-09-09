"""Cross-platform command-line interface."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .context import DEFAULT
from .provider import call
from .utils import QAError, load, save, unwrap
from .workflow import accept, approve, prepare, stage, verify


def parser():
    p = argparse.ArgumentParser(description="Portable quality agents: evidence → review → tests → diagnosis")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init", help="Write an editable project context configuration")
    init.add_argument("--out", required=True)
    pre = sub.add_parser("prepare", help="Create a bounded context packet and reusable prompt")
    pre.add_argument("role", choices=["risk", "builder", "failure"])
    pre.add_argument("--repo", required=True)
    pre.add_argument("--story", required=True)
    pre.add_argument("--out", required=True)
    pre.add_argument("--config")
    pre.add_argument("--base", help="Optional earlier Git revision for changed-file prioritization")
    pre.add_argument("--plan", help="Approved risk run directory (required by builder)")
    pre.add_argument("--evidence", action="append", default=[])
    imp = sub.add_parser("import", help="Validate JSON returned by your coding assistant")
    imp.add_argument("--run", required=True)
    imp.add_argument("--response", required=True)
    ai = sub.add_parser("run", help="Execute prepared agent using OpenAI Responses API")
    ai.add_argument("--run", required=True)
    ai.add_argument("--model", required=True, help="Explicit model id available in your account")
    ai.add_argument("--send", action="store_true", help="Authorize sending reviewed packet to OpenAI")
    ap = sub.add_parser("approve", help="Record human review of an exact result and repository revision")
    ap.add_argument("--run", required=True)
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--note", required=True)
    st = sub.add_parser("stage", help="Put approved test proposals in a separate committed-source copy")
    st.add_argument("--run", required=True)
    st.add_argument("--out", required=True)
    check = sub.add_parser("verify", help="Run an explicitly chosen command in the staged copy (not a sandbox)")
    check.add_argument("--stage", required=True)
    check.add_argument("--command-json", required=True)
    check.add_argument("--timeout", type=int, default=120)
    de = sub.add_parser("demo", help="Offline fixture demo with real regression-test execution; no AI call")
    de.add_argument("--out", default="demo-output")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.action == "init":
            path = Path(args.out)
            if path.exists():
                raise QAError("Configuration already exists; edit it instead of overwriting")
            save(path, DEFAULT)
            print(path.resolve())
        elif args.action == "prepare":
            print(prepare(args.role, args.repo, args.story, args.out, args.config,
                          args.evidence, args.base, args.plan))
        elif args.action == "import":
            accept(args.run, load(args.response), {"provider": "manual-import", "model": "not recorded"})
            print(Path(args.run).resolve() / "report.md")
        elif args.action == "run":
            if (Path(args.run) / "result.json").exists():
                raise QAError("Result exists; no API request made. Prepare a new run")
            packet = unwrap(Path(args.run) / "packet.json")
            report, provenance = call(packet, args.model, args.send)
            accept(args.run, report, provenance)
            print(Path(args.run).resolve() / "report.md")
        elif args.action == "approve":
            approve(args.run, args.reviewer, args.note)
            print("Review recorded for exact packet, report and source revision")
        elif args.action == "stage":
            print(stage(args.run, args.out))
        elif args.action == "verify":
            result = verify(args.stage, json.loads(args.command_json), args.timeout)
            print(json.dumps(result, indent=2))
            return 0 if result["status"] == "passed" else 1
        elif args.action == "demo":
            from .demo import demo
            print(demo(args.out))
    except (QAError, OSError, ValueError, KeyError, TypeError) as exc:
        print("quality-agents: " + str(exc), file=sys.stderr)
        return 2
    return 0
