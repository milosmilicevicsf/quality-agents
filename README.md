# Quality Agents

**Three independent agents. One task. One report.**

Give your coding assistant a story or failure. A **Risk Analyst** inspects it, a
**Test Engineer** designs or writes the tests, and a **Quality Reviewer** independently
challenges the result. Each worker has its own agent context and identity. Your
current assistant coordinates the handoffs and produces one offline HTML report.

## Start here

### 1. Install once

In the terminal of the project you want to test:

```sh
npx skills@latest add milosmilicevicsf/quality-agents
```

Select **both** `setup-quality-agents` and `quality-flow`, then your coding assistant.
Use the same installer you use for `sdet-skills`. Choose global installation if you
want the entry points available across projects. Setup still runs once per project.

### 2. Set up the team

In **Cursor Agent or Claude Code's chat**, run:

```text
/setup-quality-agents
```

In **Codex's chat**, select the installed skill or type:

```text
$setup-quality-agents
```

The assistant discovers your existing test stack, reuses `docs/agents/testing.md`
from sdet-skills when present, and registers three native agents for the project.
It writes the discovered conventions to `docs/agents/quality.md`. Restart the
assistant if it hasn't picked up the newly registered agents.

### 3. Give the team a task

In Cursor Agent or Claude Code:

```text
/quality-flow Analyze this story: users cannot submit an application at or after its deadline.
```

In Codex:

```text
$quality-flow Analyze this story: users cannot submit an application at or after its deadline.
```

To request implementation too:

```text
Use quality-flow to analyze this story, implement the regression tests, run them,
and have the Quality Reviewer independently review the result: [paste story here].
```

You receive one **report.html** with the scenario/layer map, actual checks, independent
review, next actions and the three host agent ids. Open it in any browser; no server
or internet is needed. The assistant handles the internal artifacts and JSON.

**The slash/dollar inputs belong in your coding assistant, not PowerShell or Bash.**
Start with the [Serbian walkthrough](docs/POCNI_OVDE.md) if you want a complete example.

## What runs

| Worker | Own context | Responsibility | Code ownership |
|---|---|---|---|
| Risk Analyst | Separate native agent | Inspect requirements, implementation and existing assertions; choose reliable test layers | Read-only |
| Test Engineer | Separate native agent | Design tests; write and execute when requested | Requested test files |
| Quality Reviewer | Fresh native agent | Review original requirements, raw diff and logs; challenge coverage and diagnose failures | Read-only |

The coordinator waits for the risk plan before dispatching the engineer, then gives
the reviewer raw evidence instead of the writer's verdict. All three participate
in analysis too: the engineer checks feasibility without editing, and the reviewer
challenges the proposed plan. Separate agents can still share model biases; human
judgment and the actual test results remain necessary.

These are **on-demand native subagents**, not background services or three names
inside one model response. Skills are only the setup and coordinator entry points.
The installed host supplies the execution engine, permissions, model and billing.
No extra API key or Python package is required for this default path. Your host's
normal usage limits apply; agent calls are not free unlimited compute.

## Three common tasks

| Your request | What the team does |
|---|---|
| “Analyze this story” | Risk map → implementation advice → independent plan review. No test edits. |
| “Write tests for this story” | Risk map → test implementation/execution → independent review. |
| “Investigate this failed test” + log | Business impact → evidence investigation/reproduction → independent diagnosis. No automatic fix. |

Analysis doesn't silently authorize edits. A request to write tests already authorizes
that scoped work; no repetitive approval commands or manual packet handoffs.

## Requirements and honest limits

- Node 18+ for the installer/helpers, Git, and a coding assistant with native subagents.
- Claude Code: setup writes project agent Markdown files in `.claude/agents/`.
- Cursor: setup writes Markdown definitions in `.cursor/agents/` with native
  `readonly` settings for the analyst and reviewer. Use Agent mode with subagent support.
- Current Codex: setup writes standalone agent TOML files in `.codex/agents/`.
- A hosted assistant with native delegation can instead spawn generic agents with
  explicit role briefs. Agent tool access is required in either case.
- Older/disabled hosts may need an update or restart. If delegation is unavailable,
  the workflow reports that blocker; it does not pretend a single response was three agents.
- Registration preserves custom agent files and doesn't change global permissions.
- Read-only settings are constrained by host behavior and inherited policies. Test
  execution has the host's OS permissions; this is not a new security sandbox.
- Reports default outside your repo to a fresh temp directory. Save/copy the HTML
  somewhere permanent to retain it; hosted environments use their artifact system.

[Preview the report](examples/report-preview.html) by downloading the HTML and opening
it locally. It is clearly labeled illustrative data, not a completed agent run.
For a real three-worker smoke test, see [the observed run report](examples/native-agent-report.html).

## How this fits sdet-skills

Keep both repos. `sdet-skills` supplies your reusable test-writing disciplines and
conventions. `quality-agents` supplies actual worker definitions, their division of
responsibility, evidence handoffs and consolidated results. Setup reuses the existing
conventions instead of asking the same questions again.

## What happened to the Python code?

It remains an **optional advanced workflow** for direct OpenAI API calls, structured
validation, review receipts, separate test staging and CI scripting. It is not
required by the native three-agent path, and its bounded role calls do not become
native subagents merely because they share the role names.

Use [the advanced CLI guide](docs/CLI.md) only if you need that execution mode.
The native path's reviews are conversational, not the CLI's hash-bound receipts.

## Development and validation

```sh
python -m unittest discover -s tests -v
node --test tests/skills.test.mjs
```

See [validation](docs/VALIDATION.md), [agent architecture](docs/NATIVE_AGENTS.md),
[team operating model](docs/OPERATING_MODEL.md), [pilot measurement](docs/PILOT.md)
and [security boundaries](SECURITY.md).

Installation follows the [Skills CLI](https://github.com/vercel-labs/skills).
Native definitions follow [Cursor subagents](https://cursor.com/docs/subagents),
[Claude Code subagents](https://code.claude.com/docs/en/sub-agents)
and [Codex subagents](https://developers.openai.com/codex/multi-agent).

MIT licensed. No client code, credentials or production data belong in this toolkit.
