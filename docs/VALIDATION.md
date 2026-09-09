# Verification record — 2026-09-09

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
