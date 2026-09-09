---
name: setup-quality-agents
description: Register three independent quality agents in Claude Code or Codex and discover project testing conventions, reusing sdet-skills configuration. Use on first setup or when conventions change.
---

# Setup Quality Agents

Prepare the current project for `quality-flow` with three independent subagents. This is a coding-assistant workflow;
do not require the user to install the Python toolkit, configure an API key, or
exchange JSON files. Use the current assistant and its existing repository access.

## Register the three workers

Determine the current host from the actual session, not a guessed OS or installed
folder. Resolve this skill's installed directory and run its bundled script:

```sh
node "<this-skill>/scripts/install-agents.mjs" --target "<project>" --host claude-code
```

Use `--host codex` for Codex. It creates three native agent definitions inside
`.claude/agents/` or `.codex/agents/`: `qa-risk-analyst`, `qa-test-engineer`,
`qa-quality-reviewer`. Risk Analyst and Quality Reviewer are configured for read-only
work; Test Engineer inherits the host's normal execution/edit permissions. No model,
API key, bypass flag or global permission change is required. Roles inherit model
selection. Existing customized definitions are never overwritten. If a conflict is
reported, inspect it and preserve the user's customization rather than forcing a reset.

The script needs Node 18+, already used by the skills installer. If unavailable,
create equivalent native definitions from `assets/roles.json` using the host's
documented format. Never pretend agent registration succeeded when it did not.
Restart/reload the coding assistant if the new agents aren't discoverable. Do not
spawn billable workers just to complete setup; quality-flow verifies delegation on use.
On a hosted assistant with native delegation but no local agent registry, record
`generic native subagents` as the adapter and use explicit role briefs per spawn.
If no delegation capability exists, explain that the three-agent workflow cannot
run there; do not silently replace it with one assistant playing three roles.

## Discover once

Read applicable repository instructions, then `docs/agents/testing.md` and
`docs/agents/quality.md` if present. Reuse sdet-skills facts; never overwrite its
configuration or conduct the same setup interview again.

Inspect manifests, actual test examples and CI configuration to establish:

- Source/test roots and frameworks; which unit, component, API and E2E layers exist.
- Existing commands for focused tests, type checking and linting, with their source.
- Test-data conventions and environments. Record credential variable names, not values.
- Important boundaries, reviewer ownership and any user-specified report location.

Write `docs/agents/quality.md` with concise sections: Project, Existing conventions,
Test layers and commands, Risk boundaries, Review ownership, Reports, Unknowns.
Link to `testing.md` instead of duplicating its conventions. Distinguish observed
facts from proposals. Leave unknown commands/owners explicitly unknown; don't
invent CI settings or force setup to stop for every missing field. Ask one focused
question only when an unresolved fact prevents meaningful setup.

On reruns, merge only relevant detected changes and preserve user-written decisions.
Do not change test frameworks, package manifests, CI, global permissions or existing
AGENTS.md/CLAUDE.md as part of this setup. `quality-flow` reads the doc directly.

## Report and finish

Default report location: a fresh OS-temp directory per run, outside the project.
Use a user-selected location when supplied. Reports should be English unless the
user chooses another language. Temp files are disposable; explain how to keep an
important report outside the project's source tree.

Show the detected stack and at most three unresolved facts, then give this next
message to paste into the assistant:

> Use quality-flow to analyze this story: [paste acceptance criteria here].

The user can select the installed skill instead: `/quality-flow` in Claude Code,
or `$quality-flow` in Codex. These are assistant inputs, not terminal commands.
If quality-flow is not installed, say to select both skills in the same installer.
