# Create one report the user can open

The renderer and assets are bundled INSIDE this skill. Resolve paths relative to
the installed `SKILL.md`, not the target project's working directory. Do not rely
on the toolkit checkout or any sibling skill being installed.

Use a fresh OS-temp folder (Node `fs.mkdtempSync`, Python `tempfile.mkdtemp`, or host
artifact directory). Write `report.json` there yourself. The user does not author,
copy, approve or import this JSON. It is internal presentation data, not a CLI
approval packet. Keep sensitive log material out of the data and final HTML.

## Data contract

All top-level fields below are required. Empty arrays are valid except next_actions.
All prose values are plain text; the renderer escapes HTML characters.

```json
{
  "project": "Project name",
  "task": "The feature or question being investigated",
  "mode": "analyze",
  "status": "review-needed",
  "execution_model": "delegated",
  "agents": [],
  "revision": "Observed commit plus scoped uncommitted changes, if any",
  "summary": "The useful decision and its most important reason.",
  "scope": "What was actually inspected, including omissions.",
  "scenarios": [],
  "checks": [],
  "findings": [],
  "next_actions": ["One concrete next action with a known owner or owner role."],
  "limitations": []
}
```

- mode: `analyze`, `build`, `triage`.
- status: `review-needed` or `blocked`. A green check never becomes release approval.
- execution_model: `delegated` only for real worker calls; `blocked` if delegation
  cannot complete; `example` only for an explicitly requested illustrative preview.
- agents: exactly three entries for delegated runs, each `{role, session_id, status,
  summary}`. Role `risk-analyst|test-engineer|quality-reviewer`; session_id is the
  actual id returned by the host agent tool, unique per worker; status
  `completed|blocked|failed`. Record only workers actually started. A blocked run
  may have fewer than three entries. Its top-level status must be blocked.
  The empty array in the shape above must be filled from actual delegation results
  before rendering a delegated report. Identity shape checks do not authenticate ids.
- scenarios: `{id, priority, behavior, layer, oracle, coverage, evidence}`. Unique id;
  priority `critical|high|medium|low`; layer `unit|component|api|integration|e2e|manual|eval`;
  coverage `covered|partial|missing|unknown`. Evidence is a nonempty string with
  inspected `path:line` references or an explicit explanation that evidence is missing.
- checks: `{name, status, command, scenario_ids, evidence}`. Status
  `passed|failed|timeout|not-run`. `scenario_ids` is an array of ids in scenarios
  (empty is valid for a check not mapped to a scenario). Record actual command,
  relevant output and test count for execution; otherwise the reason it wasn't run.
  Only `not-run` permits an empty command. List generated/changed paths in evidence.
- findings: `{title, classification, confidence, evidence, next_action}`.
  Classification `product|test|environment|data|suspected-flaky|unknown`; confidence
  `low|medium|high`. Include observed evidence and alternative causes in the evidence
  string. A valid JSON shape does not validate those observations.

## Render and deliver

Run with paths you resolved (quote arguments correctly for the current shell):

```sh
node "<installed-skill>/scripts/render-report.mjs" --input "<run>/report.json" --output "<run>/report.html"
```

The renderer refuses to overwrite a report. Use a fresh filename/directory for each
run. No npm dependencies, network, web server or build step. Node 18+ is sufficient.
Append `--open` on a local interactive desktop; otherwise return the report's
absolute file path using the host's artifact link mechanism. Save a durable artifact
if the host requires it. To retain/share a local temp report, copy the HTML alone
to the user's chosen permanent folder. No neighboring files are needed to view it.

If Node is unavailable, use `assets/report.html` as the layout reference and write
equivalent final HTML with inline CSS and properly escaped data. Do not leave
template placeholders or require JavaScript/CDNs to reveal content. Collapse long
evidence with native details/summary. Keep passed, failed and not-run visibly distinct.

`assets/example.json` is only for explicitly requested previews or renderer tests.
Never substitute it for the user's analysis or present it as generated findings.
