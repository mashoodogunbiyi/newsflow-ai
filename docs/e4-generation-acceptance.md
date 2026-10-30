# E4 AI Generation Acceptance Record

## Decision

The NewsFlow AI E4 generation backend is implemented and ready for E6 frontend integration using synthetic or otherwise authorised article data.

This decision does not approve production release, live CNN integration, automatic LinkedIn publishing, or use of an unapproved OpenAI model.

## Scope reviewed

| Jira task | Capability | Primary evidence |
|---|---|---|
| NFA-38 | Secure OpenAI service | [OpenAI integration](openai-integration.md) |
| NFA-39 | Source-grounded prompt design | [LinkedIn prompting](linkedin-prompting.md) |
| NFA-40 | LinkedIn generation service | [Generation service](linkedin-generation-service.md) |
| NFA-41 | Frontend generation REST API | [Generation API](generation-api.md) |
| NFA-42 | Factual grounding and output validation | [Grounding validation](factual-grounding-validation.md) |
| NFA-43 | Error handling, usage limits, and cost controls | [Generation operations](generation-operations.md) |
| NFA-44 | Evaluation and prompt regression | [AI generation evaluation](ai-generation-evaluation.md) |
| NFA-45 | Monitoring and audit | [Generation monitoring](generation-monitoring.md) |
| NFA-46 | Architecture, joined verification, E6 contract, and acceptance | This record and linked evidence |

## Acceptance criteria

| Requirement | Result | Evidence |
|---|---|---|
| E4 technical architecture documented | Pass | [E4 architecture](architecture/ai-generation-architecture.md) |
| Complete request lifecycle documented | Pass | Architecture lifecycle section |
| OpenAI configuration and environment variables documented | Pass | Architecture configuration section, `.env.example`, and OpenAI guide |
| Generation REST API documented | Pass | [Generation API](generation-api.md) |
| Supported writing preferences documented | Pass | Architecture and E6 contract |
| Prompt construction and versioning documented | Pass | Architecture and prompting guide |
| Source-rights verification documented | Pass | Architecture and provenance-rights guide |
| Grounding and output validation documented | Pass | Architecture and grounding guide |
| Error handling and usage controls documented | Pass | Generation API and operations guide |
| Monitoring, audit, and retention documented | Pass | Generation monitoring guide |
| Automated test strategy documented | Pass | [Testing](testing.md) |
| Complete workflow verified with synthetic fixtures | Pass | `test_generation_workflow_acceptance.py` |
| Authentication and CSRF verified | Pass | NFA-46 acceptance tests and existing API tests |
| Restricted articles rejected before OpenAI | Pass | NFA-46 restricted-article scenario |
| Trusted source references preserved | Pass | NFA-46 success scenario |
| Human review mandatory | Pass | Response model and NFA-46 success/no-publish scenarios |
| No automatic LinkedIn publishing | Pass | No publish route or client exists; verified by NFA-46 test |
| Known limitations and unresolved risks recorded | Pass | This record and architecture limitations |
| Relevant automated tests pass | Pass | Verification record below |
| E6 integration contract prepared | Pass | [E6 contract](e6-generation-integration-contract.md) |
| Final E4 results recorded | Pass | This document |

## Joined acceptance scenarios

The NFA-46 suite sends requests through the real FastAPI route and generation orchestration using an original synthetic article, actual rights service, actual prompt builder, actual grounding validator, usage tracking, audit tracking, and a mocked OpenAI generator.

| Scenario | Expected result | Status |
|---|---|---|
| Authenticated authorised generation | HTTP 201 private draft with the documented frontend schema | Pass |
| Missing authentication | HTTP 401 before generation | Pass |
| Invalid CSRF proof | HTTP 403 before generation | Pass |
| Restricted article | HTTP 403 before OpenAI access | Pass |
| Unsupported tone and length | HTTP 422 before generation | Pass |
| Insufficient permitted context | HTTP 422 without invented content or OpenAI access | Pass |
| OpenAI unavailable | Safe HTTP 503 plus failure usage and audit evidence | Pass |
| Malformed provider output | Safe HTTP 502, validation failure, no saved draft | Pass |
| Shared generation allowance exceeded | HTTP 429 with `Retry-After`, no OpenAI access, audited rejection | Pass |
| Trusted source reference | Backend article ID, title, URL, source, and attribution preserved | Pass |
| Mandatory human review | `status = "draft"` and `review_required = true` | Pass |
| No automatic publishing | No publish route or LinkedIn client in the workflow | Pass |
| Audit correlation | Start, rights, validation, and completion share one request ID | Pass |
| Token metadata | Synthetic provider token counts recorded by usage controls | Pass |

## Commands

Run the focused E4 acceptance suite from the repository root:

```bash
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_generation_workflow_acceptance.py \
  apps/api/tests/test_generation_api.py \
  apps/api/tests/test_linkedin_generation_service.py \
  apps/api/tests/test_generation_audit.py \
  apps/api/tests/test_admin_generation_monitoring.py \
  apps/api/tests/evaluation
```

Run complete backend quality verification:

```bash
cd apps/api
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
.venv/bin/pytest --cov=app --cov-report=term-missing --cov-fail-under=75
```

The NFA-46 acceptance suite and normal backend suite do not call CNN or OpenAI. Optional live-model and destructive PostgreSQL tests remain explicitly gated.

## Verification record

Verification date: 30 October 2026

- Focused NFA-46 evidence set: 79 passed and 1 optional live-model test skipped.
- Complete backend suite: 306 passed and 13 explicitly gated tests skipped.
- Backend branch-aware coverage: 80.06 percent, above the 75 percent requirement.
- Ruff linting: Passed.
- Ruff formatting: Passed for all 140 checked Python files.
- Git whitespace validation: Passed.

## Known defects

No unresolved defect is currently known in the tested E4 synthetic generation workflow.

## Known limitations and unresolved risks

- Automated checks reduce but cannot eliminate hallucination or factual error risk.
- Every draft requires human review before copying, exporting, or publishing.
- OpenAI output may vary between requests and model versions.
- Source rights or insufficient permitted context may prevent generation.
- Provider availability, latency, rate limits, and quota remain external dependencies.
- The approved production model, budget, secret store, deployment boundary, external monitoring destination, and incident process remain deployment decisions.
- Token usage is recorded when available, but application code does not calculate currency cost from changing provider prices.
- The local burst limiter is process-specific; shared daily, concurrency, and duplicate controls use PostgreSQL.
- Audit cleanup also needs a production schedule instead of relying only on new generation traffic.
- Optional live-model evaluation is billable and excluded from routine CI.
- E6 must implement and test the interface states, accessibility, responsiveness, and safe browser gateway described in the frontend contract.
- Live CNN access remains blocked by ADR-001 and cannot be enabled by E4 or E6 code alone.

## Security and privacy confirmation

- No real API key, password, session, personal information, or licensed article text is used in the NFA-46 tests or documentation.
- OpenAI credentials remain backend-only.
- Restricted source information fails before provider access.
- Private drafts remain owner-scoped.
- Public errors and audit events exclude prompts, drafts, restricted content, credentials, and raw provider details.
- The workflow has no automatic LinkedIn publishing capability.

## E4 acceptance conclusion

E4 is ready for Mashood Ogunbiyi's review and E6 frontend integration using synthetic or otherwise authorised source data. Jira should move NFA-46 and the E4 parent to Done only after the pull request is merged and repository evidence is attached.
