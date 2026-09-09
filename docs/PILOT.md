# Evaluate value before scaling

Start with 10–20 previously reviewed changes in one bounded component. Include known
defects, boundary cases, cross-service behavior and cases where no additional test
is warranted. Include stories with ambiguous criteria. Keep expected answers outside
model input. This repo ships workflow tests, not a benchmark claiming LLM accuracy.

For every case record:

| Field | What to record |
|---|---|
| Human reference | Expected risk, layer and known coverage |
| Source revision | Exact commit and selected context |
| Risk Mapper | Correct/incorrect layer, missed risks, duplicate suggestions, false coverage claims |
| Test Builder | Useful assertions, unsupported dependencies, code review changes, whether the historical bug fails |
| Failure Analyst | Correct cause, evidence quality, plausible alternatives, inappropriate confidence |
| Time | Context preparation + model wait + human review + fixes + triage |
| Cost | Recorded token usage plus provider billing |

Compare total human time with a manual baseline of similar work. Fewer minutes writing
tests is not a win if review and repair consume more time. Do not make generated-test
counts or raw code coverage the main success metric.

Suggested initial promotion criteria (adapt to your real baseline): no fabricated
references in accepted reports, no silently weakened tests, useful regression cases,
and reduced total human effort without more escaped defects. Critical missed risks
should block wider adoption until understood; one average score can hide them.

Deployment order: read-only scenario mapping, reviewed test proposals, CI triage,
then production feedback. Run triage alongside current practice before using its
recommendations for decisions. Each escaped defect should lead to an owner and a
decision: fix by date, explicitly accept risk or close with evidence.

Use developer review for low-risk changes and QA involvement where the risk warrants
it. Mandatory central QA approval of every agent output would recreate the bottleneck.
The failure analyst should not automatically quarantine a test or declare it flaky.
