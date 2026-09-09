---
name: quality-flow
description: Coordinate three independent agents to analyze quality risks, build requested tests and independently review results, then deliver one HTML report. Use for a story, feature change or failure investigation.
---

# Quality Flow

One entry point, three independently spawned workers, one readable report. You are
the coordinator, not the three workers. Use the current assistant's native agent
tools to run Risk Analyst, Test Engineer and Quality Reviewer in separate contexts.
The user provides a story, a change or a failure log; coordinate discovery, handoffs,
execution and reporting. Read [references/delegation.md](references/delegation.md)
and follow its capability check, dispatch order and independent review boundary.
Do not ask the user to run the Python CLI or manually prepare/import JSON.

## Choose the work from the request

- **Analyze** is the default: map a supplied story or scoped working diff to risks,
  existing assertions and the lowest reliable test layer. Do not change test/source code.
- **Build** when the user asks to implement/generate tests: use the current analyzed
  scope or perform focused risk mapping first, implement requested tests and run
  applicable checks when the environment permits. Review the diff before delivery.
- **Triage** for a failure: read actual supplied/available execution evidence and
  trace likely causes. Diagnosis alone does not authorize changing code.

If neither a target nor a meaningful current diff exists, ask which story/feature
to analyze. Do not substitute an unrequested whole-repository audit. A ticket URL
is usable only with an available authorized connector; otherwise ask for its text.
Build does not need a second authorization if the user already requested that work.

## Read context and use the right role

1. Read applicable repo instructions, `docs/agents/quality.md` and
   `docs/agents/testing.md` when present. If setup hasn't run, infer essential facts
   for this task and continue; recommend the setup skill for recurring use.
2. Record HEAD and relevant working changes. A dirty tree is supported: identify
   analyzed local edits, preserve unrelated work, and name omissions. Never claim
   the snapshot is a committed release when it includes uncommitted changes.
3. Read [references/roles.md](references/roles.md) for the selected mode. Workers inspect
   implementation AND actual test assertions before judging coverage. Existing
   sdet-skills conventions can inform the work, but this skill also works alone.
4. Dispatch the three workers with explicit scope and separate host agent ids.
   Do not act out their roles yourself or claim independence from three headings.
   No separate accounts or model training are required; execution uses the host's
   agent runtime and account limits. Do not launch extra workers beyond this team.

For build, use existing project conventions and limit edits to requested test
scope. Do not weaken assertions, add retries to hide a failure, auto-quarantine,
or fix product behavior just to turn a regression green. If product behavior is
wrong, report the useful failing test and propose the product fix separately.
Don't install dependencies or use remote environments without applicable user
authorization. Respect the host's execution permissions; this skill is not a sandbox.

## Deliver the result, not orchestration chores

Always produce one self-contained **report.html** using
[references/report.md](references/report.md). The report includes the decision,
risk/test map, actual execution state, evidence and next action. Create its data
yourself and run the bundled renderer; the user should only open the HTML file.
Follow host artifact-saving rules. Local default is a fresh OS-temp directory;
write task artifacts outside the target source tree unless the user chooses otherwise.

Never mark a check passed without real execution evidence. Name unrun checks,
missing data and limitations. The renderer validates presentation data, not the
truth of a diagnosis or adequacy of coverage. All model findings remain reviewable.
Include the three host agent ids and their actual statuses in the report. If a
worker cannot run, show the blocked/incomplete team rather than a completed workflow.

If no Node runtime is available, create equivalent standalone HTML directly using
the included template's layout and escaped text; do not introduce an installation
step solely for reporting. The report must remain readable offline without JavaScript.

Finish in chat with: the main finding, what was changed/tested, the report's absolute
path/link, and one useful next action. Open the report only on a local interactive
desktop when supported; a remote browser opens on the remote host, not the user's PC.

## Follow-up work

When the user says “build the tests from this report”, re-read the source and prior
scope before editing; refresh anything that changed. Generate a new report retaining
the relevant scenario ids and linking evidence in text. Do not silently reuse an old
coverage claim after its source changed. A conversational review is not the Python
CLI's hash-bound approval receipt; use that optional workflow only when requested.
