# NFA-54 - E5 Image Workflow Testing

## Purpose

This document defines and records the automated test strategy for the complete NewsFlow AI E5 image workflow. The suite verifies prompt composition, source rights, sensitive-news safety, mocked OpenAI image generation, output validation, private storage, immutable regeneration, PostgreSQL metadata, and owner-scoped delivery.

Routine tests use original synthetic article data and locally generated image bytes. They do not access CNN, call OpenAI, spend provider credits, read a real API key, or modify the development database and image store.

## Scope

The evidence covers the E5 tasks implemented by NFA-48 through NFA-53:

- NFA-48 - rights-aware image-prompt composition.
- NFA-49 - sensitive-news image safety policy.
- NFA-50 - bounded OpenAI Images API integration.
- NFA-51 - image validation and private storage.
- NFA-52 - immutable, owner-scoped image regeneration.
- NFA-53 - secure metadata, preview, and download delivery.

## Test layers

| Layer | Main evidence | Purpose |
|---|---|---|
| Unit | `test_image_prompt.py`, `test_image_safety.py`, `test_openai_image_service.py`, and `test_image_validation.py` | Verify each policy and transformation independently. |
| Service and API integration | `test_image_storage.py`, `test_image_regeneration.py`, and `test_image_delivery.py` | Verify validation, storage, API security, versioning, limits, failures, and delivery interactions. |
| Joined acceptance workflow | `test_image_workflow_acceptance.py` | Exercise the connected prompt-to-delivery and regeneration path using a mocked provider and temporary private storage. |
| PostgreSQL and storage proof | `test_image_workflow_integration.py` | Apply all migrations to a named disposable database, persist real image metadata, verify version relationships and ownership, and use a temporary private directory. |
| Continuous integration | `.github/workflows/quality.yml` | Run deterministic tests on pull requests and `main`, including the safety-gated PostgreSQL proof. |

## Reusable synthetic fixtures

`tests/fixtures/image_workflow_cases.json` contains only original fictional scenarios:

- a permitted accessibility-technology article;
- a source record with no AI-processing permission; and
- a sensitive fictional conflict scenario used to test documentary-fabrication rejection.

`tests/support/image_workflow.py` provides:

- validated synthetic `NewsArticle` objects;
- deterministic 1536 by 1024 PNG files generated from solid-colour pixels;
- a second valid image used to distinguish a regeneration from its parent;
- plain-text, truncated-PNG, and oversized invalid files;
- a mocked OpenAI Images client that returns Base64 image data and synthetic usage metadata; and
- a function-scoped temporary-file fixture exposed through `tests/conftest.py`.

No fixture includes a real person, real event, restricted photograph, provider response, credential, or personal information.

## Acceptance coverage

| Requirement | Automated evidence |
|---|---|
| Safe prompt construction and controlled preferences | `test_image_prompt.py` and joined acceptance workflow |
| Current source rights required before provider access | Image-prompt, provider-service, regeneration, and joined acceptance tests |
| Restricted content not sent to OpenAI | Mock-client call count remains zero after rights rejection |
| Sensitive-news restrictions and documentary-fabrication rejection | `test_image_safety.py` and joined acceptance workflow |
| Conceptual illustration controls | Image-safety policy tests |
| Mocked provider success and controlled provider failures | `test_openai_image_service.py` and joined acceptance workflow |
| Credential, prompt, provider-detail, and generated-data protection | OpenAI image service log and exception tests |
| Valid, invalid, corrupt, oversized, wrong-type, and metadata-bearing images | `test_image_validation.py` and reusable fixture tests |
| Private storage, safe keys, idempotency, and compensation deletion | `test_image_storage.py` |
| Storage and database failure safety | Image-storage and regeneration tests |
| Authentication, CSRF, object ownership, and not-found privacy | Regeneration, delivery, and joined acceptance API tests |
| Successful immutable regeneration and version relationships | `test_image_regeneration.py`, joined acceptance workflow, and PostgreSQL proof |
| Original image preserved after failed regeneration | Joined acceptance workflow |
| Duplicate protection and request limits | Regeneration and OpenAI image service tests |
| Private metadata, content, and download delivery | `test_image_delivery.py` and joined acceptance workflow |
| Safe MIME type, filename, cache policy, digest, and missing-object handling | `test_image_delivery.py` |
| AI-generated designation and review metadata | Storage tests and PostgreSQL proof |
| Isolated database and object storage | Named disposable PostgreSQL fixture and Pytest temporary directories |

## Joined workflow

The fast joined test performs this sequence without a network request:

1. Build a permitted synthetic article and a private LinkedIn draft.
2. Confirm the article's current AI-generation rights.
3. Compose a controlled illustration prompt.
4. Apply the central image safety policy.
5. Call the OpenAI service through an injected mocked Images client.
6. validate and clean the returned PNG.
7. write it to an isolated temporary private store.
8. persist metadata through an in-memory repository.
9. retrieve owner-scoped metadata and image content through FastAPI.
10. request a regeneration through FastAPI.
11. verify that the child has a distinct record and content.
12. verify that the parent remains available and a different user cannot retrieve it.

Separate joined scenarios prove that denied rights and documentary fabrication stop before the provider, invalid fixtures are rejected deterministically, and a failed regeneration leaves the original intact.

## PostgreSQL isolation

The real-database proof accepts only a `TEST_DATABASE_URL` containing `newsflow_image_pipeline_test` and also requires `ALLOW_DATABASE_RESET_FOR_TESTS=true`. It applies all Alembic migrations before the test and rolls the schema back to `base` afterwards.

Never point this command at the normal development database, a shared database, staging, or production:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_image_pipeline_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
apps/api/.venv/bin/pytest -q -m integration \
  apps/api/tests/test_image_workflow_integration.py
```

The test inserts only synthetic users, source metadata, an article snapshot, a generated post, and two image versions. Image files are written under Pytest's temporary directory and removed by Pytest. Development records and the configured Docker image-storage volume are not used.

## Local commands

Run the focused deterministic E5 set from the repository root:

```bash
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_image_prompt.py \
  apps/api/tests/test_image_safety.py \
  apps/api/tests/test_openai_image_service.py \
  apps/api/tests/test_image_validation.py \
  apps/api/tests/test_image_storage.py \
  apps/api/tests/test_image_regeneration.py \
  apps/api/tests/test_image_delivery.py \
  apps/api/tests/test_image_workflow_acceptance.py
```

Run all normal backend checks:

```bash
cd apps/api
ruff check .
ruff format --check .
pytest -m "not live_ai" --cov=app --cov-report=term-missing --cov-fail-under=75
```

## CI behaviour

GitHub Actions runs the normal deterministic suite without a live OpenAI key. It then creates the short-lived `newsflow_image_pipeline_test` database inside the PostgreSQL service and runs only the NFA-54 integration module with explicit reset permission. The service and all its test data disappear with the CI job.

The workflow contains only disposable CI database values. Real credentials must never be placed in the workflow.

## Verification record

Verified locally on 1 November 2026:

| Run | Passed | Failed | Skipped | Deselected | Coverage |
|---|---:|---:|---:|---:|---:|
| Joined NFA-54 acceptance workflow | 4 | 0 | 0 | 0 | Included in full backend result |
| Complete deterministic E5 image set | 107 | 0 | 0 | 0 | Included in full backend result |
| Isolated PostgreSQL and private-storage proof | 1 | 0 | 0 | 0 | Not collected separately |
| Complete normal backend suite | 416 | 0 | 13 | 1 | 81.10 percent branch-aware coverage |

- Backend Ruff checks passed for the new fixtures and NFA-54 tests.
- All migrations through `20261031_0012` applied before the database proof and rolled back afterwards.
- The 13 full-suite skips are explicitly gated PostgreSQL modules without their named database environment; the one deselected test is the optional live-model evaluation.
- No test contacted CNN or OpenAI, used production credentials, or modified the development image store.

## Known limitations and unresolved defects

- Routine automation verifies the OpenAI boundary with a mocked client. It does not prove current live-provider availability, latency, billing, or output quality.
- No live CNN integration is tested because ADR-001 keeps that integration at No-Go without authorisation.
- The local adapter is tested with temporary filesystem storage. A future hosted S3-compatible adapter needs its own integration and signed-delivery tests.
- Signed URLs are not used by the current backend-proxy delivery design, so expiry testing is not applicable.
- Browser rendering, visual similarity, and human editorial suitability are outside this backend suite. Human review remains mandatory before publication.
- CI execution of the new workflow step can be confirmed only after the branch is pushed and GitHub Actions runs.

No unresolved implementation defect was found during the recorded local NFA-54 runs.

## Review status

- Jira issue: NFA-54
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review

