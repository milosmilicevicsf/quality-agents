# Boundaries and responsible use

- No API key is stored in source/config. Only `OPENAI_API_KEY` is used by the API
  adapter. Credentials are not included in packet metadata or subprocess environment.
- `prepare` includes Git-tracked text under explicit patterns, with file/count/size
  budgets. Known credential paths and files containing recognized secrets are excluded.
- Story and text logs use heuristic redaction. This is not complete secret, student,
  health-data or PII detection. Review `prompt.md`; use synthetic/redacted inputs and
  approved AI accounts. Do not send employer/customer code without authorization.
- The OpenAI adapter has a fixed HTTPS endpoint and does not follow redirects. It
  requests `store: false`; this is not a claim about all provider retention policies.
- Prompt injection is addressed through untrusted-context instructions and restricted
  capabilities. Model compliance is not a security boundary: the orchestrator never
  gives the model a shell, arbitrary file access or permission to merge.
- Test writes are constrained by a configurable allowlist, path validation and human
  review. Wildcards can be configured too broadly. Only include genuine test paths.
- Generated code can be malicious or wrong, including deletion/weakening of assertions.
  Instructions prohibit that, but it cannot be reliably detected by schema validation.
  Review full code and the diff before executing. No command is sourced from model output.
- `verify` is NOT a sandbox. It executes local code, which may have network/filesystem
  effects. Use an ephemeral container/VM/CI runner for untrusted inputs. Environment
  filtering does not stop code reading credentials from disk. Do not mount credentials.
- The execution log is temporarily written beside the stage, then redacted and capped
  at 60,000 bytes for the saved text. A highly verbose process can fill disk before
  timeout; disposable runners should have disk quotas. CLI does not provide OS quotas.
- Symlinks/submodules are unsupported for staging. Context collection marks them as
  omitted rather than following them. Working-tree changes invalidate preparation.
- Hash receipts detect accidental tampering/staleness, not a malicious local operator.
  Reviewers are self-declared. Enforce real ownership using normal PR/CODEOWNERS rules.
- Run outputs contain source excerpts. Keep them outside the toolkit and do not commit
  them to its public/private repo. A private repo alone is not client-data authorization.
- CI examples avoid `pull_request_target` and automatic model calls. Review fork PRs
  without exposing secrets; do not grant AI jobs repository write access by default.

Report security issues privately to the repository owner; do not include credentials
or customer data in a public issue.
