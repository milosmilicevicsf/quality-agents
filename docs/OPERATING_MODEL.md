# A quality process that can scale

This is a proposed operating model for Element451 and future projects. It assumes
access to the relevant code and test frameworks; it does not claim knowledge of
Element451's private architecture, current test coverage or measured bottleneck.

## The six stages

| Stage | Practical work | Accountable human | Agent contribution |
|---|---|---|---|
| Story refinement | Agree observable acceptance criteria, boundaries and risk | Product + developer; QA for significant risk | Risk Mapper flags ambiguity, drafts scenarios and traces implementation |
| Test design | Decide lowest reliable layer; inspect existing assertions | Implementing developer with risk-based QA review | Risk Mapper records layer, oracle, coverage evidence and unknowns |
| Development | Implement behavior and produce reviewed regression tests | Developer | Test Builder proposes test files tied to approved scenario ids |
| PR and CI | Run deterministic project gates; review code and failures | Developer/code owner | Failure Analyst interprets supplied CI evidence and suggests next investigation |
| QA verification | Explore uncertainty, cross-system behavior and high-risk changes | QA | Existing reports reduce preparation and log gathering; human determines remaining tests |
| Release feedback | Monitor agreed signals, triage escaped defects, feed learning into scenarios | Release owner + feature owner | Failure Analyst reviews exported evidence; new scenarios go back through Risk Mapper |

The toolkit implements analysis, proposals, local review records and explicit local
execution. It does not implement a product backlog, CI service, monitoring platform,
release automation or automatic production-log ingestion.

## Who reviews what

An implementing developer can review low-risk scenario drafts and test proposals
under the team's existing code-review rules. QA reviews higher-risk boundaries and
samples lower-risk work to find patterns. Product resolves ambiguous requirements.
The release owner accepts residual risk. These responsibilities should be assigned
before introducing agents, not left as a generic “QA must approve” queue.

Changes involving permissions, tenant boundaries, sensitive data, irreversible
actions or complex external integrations deserve explicit specialist review and
appropriate integration/end-to-end coverage. Lower-layer tests must not mock away
the exact boundary at risk. Tests of AI-dependent product behavior may also require
curated evaluation datasets, tool-use assertions and repeated-run evaluation; a
passing unit test is insufficient evidence for nondeterministic behavior.

## A focused first rollout

1. Select a component with usable local tests, a developer owner and baseline QA data.
2. Run Risk Mapper on historical stories; compare recommendations with known results.
3. Introduce Test Builder when scenario quality is acceptable. Keep code review in
   the normal developer workflow and run regressions on known historical failures.
4. Introduce Failure Analyst using exported logs. Compare diagnoses with human triage.
5. Measure total human effort, review waiting time, flaky blocking runs and escaped
   defects. Expand only where the combined process improves these outcomes.

No staffing guarantee follows from adding three prompts. The hypothesis is that
moving repeatable preparation, test drafting and evidence gathering out of the QA
queue creates capacity. [PILOT.md](PILOT.md) defines how to check that hypothesis.

## Mapping to the earlier presentation

“Story Analyst” became **Risk Mapper**: it now covers both acceptance criteria and
repository-level test placement. “Automation Engineer” became **Test Builder** with
reviewed proposals and separate execution. “Quality Analyst” became **Failure
Analyst** with evidence requirements and explicit uncertainty. These are different
contracts around a shared model adapter; no separate model training is required.
