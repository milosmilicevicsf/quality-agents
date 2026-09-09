# CI integration

The checked-in workflow tests the toolkit on Windows and Ubuntu. A consuming project
can install this toolkit from an immutable Git commit in its normal test job, then
prepare a failure packet when its own tests fail. Use the job's existing credential
and artifact policies; don't add a personal token simply to run this tool.

Example steps to adapt inside a trusted consumer job, after checking out the toolkit
under `qa-toolkit` and the target repository under `application`:

```yaml
- name: Run application tests
  id: app_tests
  continue-on-error: true
  working-directory: application
  shell: bash
  run: |
    set -o pipefail
    python -m pytest tests -q 2>&1 | tee "$RUNNER_TEMP/application-tests.txt"

- name: Prepare reviewable failure packet
  if: steps.app_tests.outcome == 'failure'
  working-directory: qa-toolkit
  shell: bash
  run: |
    python -m quality_agents prepare failure \
      --repo ../application \
      --story ../application/qa/story.md \
      --evidence "$RUNNER_TEMP/application-tests.txt" \
      --out "$RUNNER_TEMP/quality-failure"

- name: Preserve application test failure
  if: always() && steps.app_tests.outcome == 'failure'
  run: exit 1
```

This snippet assumes application test runs do not modify tracked files or leave
unignored outputs; snapshot preparation rejects dirty repositories. Choose context
patterns for your service. Store the packet as a short-retention internal artifact
only if your source-code policies permit it. Don't print the full packet in CI logs.

The initial rollout should prepare packets for human review. A later trusted job may
invoke `run --model ... --send` with a scoped OpenAI credential once the selected
context and policy have been reviewed. No AI result should turn a failed application
test into a passing gate. Keep AI triage advisory and preserve original test status.

This repo does not automatically post comments, create tickets or run webhook services.
For those extensions, map the existing validated JSON into your organization's approved
connector and retain the same approval and provenance rules.
