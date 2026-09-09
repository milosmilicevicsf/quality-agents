# Actual independent workers

The coordinator is the user's current coding assistant. It dispatches work and
consolidates results; it is not one of the three worker identities.

## Capability check

Use the host's native agent tool. Prefer registered `qa-risk-analyst`,
`qa-test-engineer` and `qa-quality-reviewer` types. If the host supports generic
subagents but doesn't load local custom definitions, spawn three separate generic
agents with the role contracts from `roles.md` explicitly included in their tasks.
This is a real-delegation adapter, not a role-switching fallback.

If custom definitions aren't loaded, explain any needed restart. If delegation is
disabled or unavailable, report `execution_model: blocked`, state the actual reason
and the next setup action. Do not claim three agents ran. Do not change host policies
to enable delegation without user authorization. Skill installation cannot add an
agent tool that the host does not provide.

## Dispatch sequence

1. Create a run directory outside the project and capture the original task,
   relevant working diff and starting HEAD. Do not stash or commit the user's work.
2. Spawn **Risk Analyst** with original requirements, repo path, scope and the
   Analyze role contract. It explores independently and returns the scenario plan.
   Save its returned report as `plan.md`; record the actual host agent id.
3. Spawn **Test Engineer** in a separate context with original requirements,
   the plan, mode and permitted file scope. It writes only in build mode; in analyze
   mode it independently checks feasibility and proposes tests; in triage mode it
   investigates/reproduces with available authorized commands. Save returned work
   as `implementation.md`, exact test output as available, and the host agent id.
4. Spawn **Quality Reviewer** in a fresh context with original requirements, raw
   current code, relevant test diff and execution logs. Do NOT seed it with the
   builder's verdict or an instruction to approve. It should form its assessment
   independently, then compare scenario coverage. Save `review.md` and its host id.
5. Reconcile findings without erasing disagreement. If a requested build needs a
   concrete test correction, allow at most ONE engineer repair and reviewer recheck
   in the same run. Don't retry product bugs into green. Report remaining issues.
6. Produce report.json and report.html, recording all actual agent identities,
   outcomes and unexecuted checks. Return one report link to the user.

Where supported, give workers a minimal fresh context rather than the full parent
conversation. The reviewer must be a different agent from the writer. Agents can
share the repo filesystem, so only the Test Engineer gets file ownership for edits.
Read-only workers return findings to the coordinator, which persists them.

## Prompt minimum

Every spawn includes repo path, actual user request, mode, scope, relevant project
instructions, role boundaries and expected output. Never rely on agents implicitly
remembering the coordinator's context. Explicitly tell workers not to spawn others.
Preserve host-provided agent ids; don't manufacture identities for a report.

For the reviewer include: “Inspect the original requirement and raw evidence first.
Find meaningful defects or gaps independently. A no-blocking-findings verdict covers
only inspected scope and is not release approval. Return unresolved risks too.”

Subagent context separation reduces influence from the writer's conclusions; it
doesn't guarantee statistical independence or correctness when models share biases.
These are on-demand workers, not always-on daemons, scheduled bots or distinct people.
