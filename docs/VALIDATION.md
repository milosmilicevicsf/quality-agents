# Verification record — 2026-09-09

## Native three-agent update

- Both entry skills passed skill frontmatter/reference validation.
- Skills CLI 1.5.25 discovered and installed both complete skill folders from the
  local source into isolated Claude Code and Codex project paths.
- Installed setup script registered all three agents for both hosts. Codex output
  parsed successfully with Python's standard TOML parser.
- 11 Node tests pass: idempotent registration, conflict preservation, symlink
  rejection, dry run, HTML injection escaping, distinct worker identity requirement,
  blocked delegation, execution-evidence fields and standalone copied-skill rendering.
- The existing 31 Python tests still pass.
- Three real hosted subagents ran sequentially with separate contexts/ids:
  `/root/qa_risk_analyst`, `/root/qa_test_engineer`, `/root/qa_quality_reviewer`.
  Reviewer received original requirements and raw source/tests/logs, not the writer's
  conclusions. It identified a missing regression and requested one repair round.
- Final synthetic-project run: 13 tests, 10 passed, 3 failed, exit 1. The failures
  expose two product defects; no product code or existing assertions were changed.
  See [the observed run report](../examples/native-agent-report.html).

Native agent definitions are registration-tested against the documented host formats;
local Claude Code/Codex app execution wasn't available here. The live smoke test used
the hosted generic native-subagent adapter. It does not benchmark model accuracy.
HTML generation and escaping were tested; a local browser screenshot was not completed
because the browser binary download was unavailable. No visual-browser pass is claimed.

## Original optional CLI verification

Executed on Linux, Python 3.12, with local Git. No customer repository or data was
used. No live model call was made and no GitHub Actions run is claimed.

| Check | Observed result |
|---|---|
| `python3 -m unittest discover -s tests -v` | 31 tests passed |
| Full workflow | Risk approval → builder approval → staging → actual failing test → diagnosis packet |
| Original target | Original source and Git revision preserved by normal staging/execution |
| Patch application | `git apply --check` succeeds; existing file without trailing newline round-trips correctly |
| Rejection paths | Dirty repos, stale approvals, invalid references, unknown schema fields, production paths and traversal rejected |
| Execution | Timeout recorded; inherited API credentials omitted; modified staged files rejected |
| Provider contract | Schema request, explicit send/key, response parsing and refusal/incomplete handling tested offline |
| Distribution | Wheel built and installed without downloading dependencies |
| Installed distribution | Demo executed outside source tree, including packaged prompts and sample files |
| Installed demo | Three real tests, one intentional product failure; no model called |

The intentional demo failure is expected; it is distinct from the 31 passing tests
that verify the toolkit itself. Demo analysis is explicitly marked as fixture data.

## Not established by these checks

- Live API credentials, account model availability, network operation or LLM accuracy.
- Performance/coverage on Element451 or any private production repository.
- Windows/macOS runtime results. Ubuntu/Windows Python 3.11/3.12 CI is configured,
  but must execute after publishing. macOS is not in the CI matrix.
- OS isolation, complete secret detection, authenticated approvals or release safety.
- A measured reduction in QA time. Use the pilot protocol before making that claim.

Reproduce with the README commands. Inspect actual test counts and logs; an exit
code by itself is not evidence that meaningful tests were discovered.
