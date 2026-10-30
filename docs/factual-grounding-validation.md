# NFA-42 - Factual Grounding and Output Validation

## Outcome

NFA-42 adds deterministic safeguards after OpenAI returns a LinkedIn draft and before NewsFlow AI stores or returns that draft.

The safeguards check structure, trusted source-reference integrity, permitted grounding context, numerical claims, direct quotations, dates, named entities, and factual assertions. Every returned result still requires human review. No automated status means that a post is factually verified.

## Validation flow

```text
Permitted PostgreSQL article snapshot
              |
              v
NFA-39 rights-aware prompt
              |
              v
NFA-38 OpenAI service
              |
              v
Strict JSON and word-limit validation
              |
              v
NFA-42 deterministic grounding checks
      |              |              |
      v              v              v
passed checks   review required    rejected
      |              |              |
      +------> private draft        `--> no draft stored
                     |
                     v
             human verification
```

The validator never fetches an article, follows a link, calls a second model, or reads restricted content. It receives the same trusted `NewsArticle` object that passed the NFA-32 rights gate and was used to build the NFA-39 prompt.

## Structured contracts

OpenAI must first satisfy the existing strict `LinkedInModelOutput` contract:

```json
{
  "status": "ready",
  "draft": "Generated draft text",
  "insufficiency_reason": null
}
```

Pydantic rejects malformed JSON, missing or extra fields, empty ready drafts, and contradictory status values. The generation service then checks the selected length range before factual-grounding evaluation.

The deterministic validator returns a `GroundingResult`:

```json
{
  "status": "review_required",
  "warnings": [
    {
      "code": "unsupported_numerical_claim",
      "category": "unsupported_claim",
      "severity": "review",
      "message": "A numerical claim was not found in the permitted source information."
    }
  ],
  "policy_version": "grounding_v1",
  "checked_claim_count": 1,
  "human_review_required": true
}
```

Warnings contain only stable codes and generic messages. They do not contain draft excerpts, article text, URLs, prompts, credentials, or private rights information.

## Validation stages

### 1. Structural validation

- The OpenAI response must match the strict JSON Schema and Pydantic model.
- A ready draft must contain text.
- The draft must remain within the configured short, medium, or long word range.
- Unexpected fields and malformed values are rejected.

### 2. Trusted source-reference validation

- The article ID must equal the selected backend article ID.
- The source URL must equal the canonical URL on the trusted backend article record.
- The source ID, URL, title, attribution, and rights version are built by NewsFlow AI from trusted records. They are not accepted from model output.
- A mismatch is a blocking error and the draft is rejected.

### 3. Permitted factual-grounding checks

The validator builds its comparison context only from the six NFA-39 permitted fields:

- title
- source name
- publication date
- category
- description
- permitted content

The validator applies these explainable checks:

- A number, percentage, or currency value absent from the permitted context creates an `unsupported_numerical_claim` warning.
- A direct quotation absent from the permitted context creates an `unsupported_quotation` blocking warning.
- A written date absent from the permitted context creates an `unsupported_date_claim` warning.
- A multiword named entity absent from the permitted context creates an `unsupported_named_entity` warning.
- A factual sentence with low meaningful-word overlap against the permitted context creates an `unsupported_factual_assertion` warning.
- Clearly framed commentary, including phrases such as `In my view`, `I think`, `may`, `might`, or `could`, is not treated as source-reported fact by the factual-sentence overlap check.

These are conservative text checks, not a general truth engine. A warning means the user must compare the statement with the source. A missing warning does not prove the statement is correct.

### 4. Review decision

| Status | Meaning | Application treatment |
|---|---|---|
| `passed_automated_checks` | No configured deterministic rule raised a warning. | Store as a private draft with human review still required. Never label it verified. |
| `review_required` | One or more non-blocking concerns were found. | Store as a private draft, return safe warnings, and require the user to review or revise it. |
| `rejected` | A blocking failure was found. | Do not store or return the generated draft. Return a safe validation error. |

Blocking failures currently include:

- Empty draft.
- Trusted source-reference mismatch.
- Insufficient permitted grounding context.
- Direct quotation not found in the permitted source information.

Unsupported numbers, dates, named entities, and low-support factual assertions currently produce `review_required`. This allows a user to inspect and revise a questionable draft without presenting it as verified.

## Insufficient and restricted information

Grounding requires available content that explicitly permits AI processing and derivative output, plus enough meaningful description or permitted-content terms for a useful comparison. If this context is insufficient, the result is `rejected`.

The earlier rights and prompt stages already reject missing, expired, revoked, or restricted content before OpenAI is called. NFA-42 repeats the permitted-context gate defensively and never retrieves additional content to fill a gap.

## API behaviour

The frontend-facing `POST /api/generations` response now adds:

```json
{
  "grounding_status": "passed_automated_checks",
  "validation_warnings": [],
  "grounding_policy_version": "grounding_v1",
  "review_required": true
}
```

The private `/api/v1/linkedin-drafts` response includes the complete nested `grounding` object. Both APIs keep `review_required` set to `true` for every draft.

If a blocking grounding result occurs, the API returns HTTP `502` with safe code `grounding_validation_rejected`. The response does not include the rejected draft or source content.

## Persistence and troubleshooting

Alembic revision `20261030_0008` adds these nullable fields to `generation_runs`:

- `grounding_status`
- `grounding_policy_version`
- `grounding_warnings`
- `grounding_checked_claims`

The warning JSON stores only safe structured warning data. Existing rows created before NFA-42 remain readable and are conservatively returned as `review_required` with `legacy_unvalidated`.

For a rejected output, the application emits only a safe structured event containing the status and counts. It does not log the prompt, source content, generated draft, or unsupported claim excerpt. The rejected prose is not stored.

## Automated evidence

Run the focused checks from `apps/api`:

```bash
pytest tests/test_generation_validator.py \
  tests/test_linkedin_generation_service.py \
  tests/test_generation_api.py \
  tests/test_linkedin_generation_api.py
```

The synthetic tests cover:

- Supported facts and clearly framed commentary.
- Empty and malformed model output.
- Unsupported statistics.
- Fabricated quotations.
- Trusted source-reference mismatch.
- Insufficient permitted context.
- Opinion compared with factual reporting.
- Unsupported named entities and factual assertions.
- Safe warning messages without restricted excerpts.
- Service rejection before persistence.
- Grounding fields in both generation APIs.
- Migration columns and index.

No test sends a live OpenAI request or uses live CNN information.

Verified locally on 30 October 2026:

- The focused NFA-42 validation, service, and API run passed 49 tests.
- The complete backend suite passed 254 tests and safely skipped 11 opt-in PostgreSQL integration tests.
- Branch-aware coverage was 79.71 percent, above the enforced 75 percent minimum.
- Ruff linting, Ruff formatting, Docker Compose validation, Git whitespace validation, and the one-head Alembic check passed.

## Limitations

- Word overlap cannot detect every subtle contradiction, misleading implication, or incorrect paraphrase.
- Entity and date recognition is deliberately lightweight and may create false positives or miss unusual formats.
- Supported wording can still be outdated, incomplete, or misleading if the authorised source itself has those problems.
- The checks do not establish truth from external knowledge.
- A second model would also be fallible, so no model judgement is treated as conclusive proof.
- Human comparison with the displayed source remains mandatory before publication.

## Review status

- Jira issue: NFA-42
- Implementation status: Ready for Mashood Ogunbiyi's review
- Approval status: Pending review
- Live CNN status: Blocked by ADR-001
