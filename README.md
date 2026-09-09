# Quality Agents

Your reusable quality engineering toolkit: **Risk Mapper → Test Builder → Failure Analyst**.

Python 3.11+ and Git. No runtime pip dependencies. Windows, macOS and Linux CLI.
English agent instructions and reports; [Serbian getting-started guide](docs/POCNI_OVDE.md).

This is an executable workflow, not just a prompt collection. It collects bounded
repository context, validates model outputs, records review decisions, stages test
proposals outside the target repository and records real command results.

## Try it now — no API key

From the repository root:

```sh
python -m quality_agents demo --out ../quality-demo
```

The bundled synthetic admissions project contains an intentional deadline bug.
The demo executes three real tests; one is expected to fail. It produces:

```text
quality-demo/
  sample-project/          Original Git project, unchanged
  01-risk/                Context, fixture risk map, simulated demo approval
  02-builder/             Proposed regression tests, simulated demo approval
  03-staged/
    repo/                 Separate copy with proposed tests
    changes.patch         Human-reviewable patch
    verification.json     Actual command status
    verification.txt      Actual sanitized log
  04-failure/             Evidence-backed fixture diagnosis
  summary.json
```

**Demo agent responses are deterministic fixtures. No model is called.** The test
execution and target-preservation checks are real. Normal commands never select
fixtures or auto-approve reports. An optional install exposes `quality-agents`:

```sh
python -m pip install -e .
quality-agents --help
```

## What each role does

| Role | Input | Output | Human decision |
|---|---|---|---|
| Risk Mapper | Story, code, tests, optional diff | Scenarios, oracle, layer, existing coverage, evidence, questions | Agree coverage and unresolved risk |
| Test Builder | Approved plan for the same revision | Full test file proposals mapped to scenario ids | Review assertions and test code |
| Failure Analyst | Story, code and actual execution evidence | Hypotheses, evidence, alternatives, next action | Decide owner, fix and priority |

The process is sequential where evidence depends on earlier work. Three roles do
not mean three agents running indiscriminately in parallel. There is no fourth AI
release approver. Deterministic validators reject malformed outputs, invalid
citations, non-test file proposals and stale approvals.

## Use it on your own project

Keep this toolkit, the target Git repository and output folders separate. The target
must have a committed HEAD and a clean working tree. Make a local feature commit
before analysis; a remote push is not required.

### 1. Configure context once per project

```sh
python -m quality_agents init --out ../my-project.qa.json
```

Edit `project_context`, `focus`, `include`, `exclude` and `test_paths`. See
[profiles](profiles/) for Python/pytest, Playwright/TypeScript, .NET and Java examples.
Patterns use Python `fnmatch` over repository-relative POSIX paths; `*` also matches
slashes. `test_paths` is the write allowlist: keep it narrow. It does not prove a
file is semantically a test. Framework detection produces hints, not certifications.

### 2. Prepare a Risk Mapper packet

```sh
python -m quality_agents prepare risk --repo ../my-project --story ../story.md --config ../my-project.qa.json --out ../qa-runs/story-42-risk
```

Optional `--base main` adds a diff between the resolved base and HEAD, restricted to
selected files. `focus` patterns are prioritized first, followed by changed files,
tests and other included files. Open `prompt.md`: this is the exact context you are
about to share. The packet records omitted files and truncation explicitly.

### 3. Choose how the model runs

**Existing coding assistant / subscription workflow**

Give `prompt.md` to your approved coding assistant. Ask it to return only JSON using
the included schema. Save the answer as `response.json`, without markdown fences:

```sh
python -m quality_agents import --run ../qa-runs/story-42-risk --response ../response.json
```

This is a manual handoff, not an automatic integration with a ChatGPT, Claude or
Copilot subscription. The CLI makes no model/network call in this mode.

**OpenAI API workflow**

Set `OPENAI_API_KEY` in your local environment and select a model supporting
Responses Structured Outputs that is available to your account:

```sh
python -m quality_agents run --run ../qa-runs/story-42-risk --model YOUR_MODEL_ID --send
```

`--send` explicitly authorizes transmitting the reviewed packet to OpenAI. One API
call per run; no automatic retry or multi-agent spending loop. Refusal, incomplete
responses and schema errors fail closed. Usage metadata is recorded. API access and
billing are separate from this repository; no key is included.

### 4. Review, then approve the risk map

Read `report.md`, source assertions and the story. Resolve important questions before
recording approval; the note should explain accepted residual risk.

```sh
python -m quality_agents approve --run ../qa-runs/story-42-risk --reviewer "Milos" --note "Reviewed boundaries and dependencies; UI exploration remains manual"
```

Approval hashes bind the exact packet and result to the Git revision. They detect
accidental changes; they are not signatures, identity verification or access control.

### 5. Build test proposals

```sh
python -m quality_agents prepare builder --repo ../my-project --story ../story.md --config ../my-project.qa.json --plan ../qa-runs/story-42-risk --out ../qa-runs/story-42-builder
```

Use `run` or `import` as above for this new packet, then review the full file contents
in `result.json`. Check assertions are independent of implementation, dependencies
are real, mocks are appropriate and existing tests have not been weakened.

```sh
python -m quality_agents approve --run ../qa-runs/story-42-builder --reviewer "Milos" --note "Reviewed generated code and expected failures"
python -m quality_agents stage --run ../qa-runs/story-42-builder --out ../qa-runs/story-42-stage
```

This creates a separate copy of committed source with proposed tests and a
`changes.patch`. No files in the target project are modified. Submodules, symlinks
and tracked credential paths are deliberately unsupported for staging in v1.

### 6. Execute a check you choose

Review `changes.patch` first. Dependencies are not installed or copied automatically.
Use an already provisioned environment or disposable CI runner. Then, for example:

```sh
python -m quality_agents verify --stage ../qa-runs/story-42-stage --command-json '["python", "-m", "pytest", "tests", "-q"]'
```

PowerShell usually accepts the same single-quoted JSON. If your Windows shell
rewrites quotes, call from Python with a list or use PowerShell's native argument
passing mode. See [the Windows example](docs/POCNI_OVDE.md).

`verify` executes exactly the user-provided argument list without a shell. It is
**not an OS sandbox**: tests are executable code. It strips inherited credentials
from the subprocess environment and sets a timeout, but code could still read local
files or use the network. Use a disposable runner for untrusted projects/tests.

Status is `passed`, `failed` or `timeout`, from the command exit code. A green status
does not establish coverage, test discovery or release readiness. Inspect test counts
and assertions. Suggested commands in AI reports are never executed automatically.

### 7. Analyze a failure

```sh
python -m quality_agents prepare failure --repo ../my-project --story ../story.md --config ../my-project.qa.json --evidence ../qa-runs/story-42-stage/verification.txt --out ../qa-runs/story-42-failure
```

Then `run` or `import` that packet. You can supply multiple `--evidence` text files,
including sanitized CI logs, extracted JUnit details and prior failure history.
Binary traces/screenshots are not decoded by v1. New generated tests are not part of
the original repository context: include relevant test code as additional evidence
when needed. A diagnosis remains a hypothesis until a human verifies it.

### 8. Apply an accepted proposal to your feature branch

Check the target is still at the reviewed commit, then run from that target:

```sh
git apply --check ../qa-runs/story-42-stage/changes.patch
git apply ../qa-runs/story-42-stage/changes.patch
```

Review and commit through your normal PR workflow. The toolkit does not push, merge,
approve PRs, close defects or make release decisions. Changing the target commit
requires a fresh plan/review cycle; this intentionally avoids stale approvals.

## Documentation

- [Start here, in Serbian](docs/POCNI_OVDE.md)
- [Architecture, article alignment and design tradeoffs](docs/ARCHITECTURE.md)
- [Team workflow and review ownership](docs/OPERATING_MODEL.md)
- [Personal use and coding assistant handoff](docs/ASSISTANT_WORKFLOW.md)
- [Pilot/evaluation and bottleneck measurements](docs/PILOT.md)
- [CI integration](docs/CI.md)
- [Security and practical limits](SECURITY.md)
- [Build verification record](docs/VALIDATION.md)

## Repository checks

```sh
python -m unittest discover -s tests -v
```

CI is configured to run this suite on Ubuntu and Windows with Python 3.11 and 3.12. It does not call
models or upload customer project context. The offline suite validates the workflow;
evaluate live-model quality on your own reviewed examples before expanding use.

## Publishing your copy

This source is intended for `milosmilicevicsf/quality-agents`. Keep it private initially.
If publishing from a local copy with GitHub CLI installed and authenticated:

```sh
python scripts/publish.py --create
```

The script checks the authenticated account, initializes Git if needed, creates a
private repository and pushes without force. Omit `--create` if an empty remote
already exists. It does not handle non-empty remotes by overwriting them.

## License

MIT. This toolkit is generic; client source, evidence, runs and credentials stay out
of the toolkit repository. Respect each employer/client's AI and source-code policies.
