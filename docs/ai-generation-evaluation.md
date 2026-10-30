# NFA-44 AI Generation Evaluation and Regression Framework

## Purpose

This document defines how NewsFlow AI evaluates generated LinkedIn post drafts for required structure, source grounding, attribution, tone, length, writing quality, safety, rights, and operational reliability.

The framework prevents known problems from silently returning when prompts, models, or generation logic change. It does not claim that automated checks can prove factual accuracy. Every generated draft still requires human review before publication.

## Plain-language explanation

Normal API tests answer questions such as, "Did the server return a `201` response?"

AI evaluation asks a different question: "Was the returned draft actually suitable?"

NFA-44 gives each generated draft a structured report card. It checks individual properties rather than expecting the model to use exactly the same words on every run. A prompt change is treated as a regression when a required property becomes worse, even if the new draft still looks fluent.

## Architecture

| Component | Location | Responsibility |
|---|---|---|
| Evaluation schemas | `apps/api/app/evaluation/schemas.py` | Strict result, finding, threshold, score, and regression models |
| Generation evaluator | `apps/api/app/evaluation/generation_evaluator.py` | Deterministic structure, grounding, source, tone, length, quality, and safety scoring |
| Regression comparison | `apps/api/app/evaluation/regression.py` | Compares the same case across prompt versions by property score |
| Synthetic articles | `apps/api/tests/fixtures/evaluation_articles.json` | Original fictional records covering required subjects and difficult cases |
| Mocked outputs | `apps/api/tests/fixtures/expected_generation_cases.json` | Stable provider responses for repeatable regression evaluation |
| Evaluation tests | `apps/api/tests/evaluation` | Focused quality, grounding, safety, rights, injection, and regression tests |
| Existing workflow tests | `apps/api/tests/test_generation_*.py` and related service tests | API failures, invalid preferences, limits, authentication, authorisation, and provider handling |

The evaluator reuses the NFA-42 `GenerationGroundingValidator`. This avoids two factual-grounding policies disagreeing with each other.

## Synthetic evaluation dataset

The dataset includes fictional examples for:

- Technology development.
- Artificial intelligence.
- Business announcements.
- Scientific research.
- Healthcare technology.
- Economic developments.
- Insufficient source information.
- Unsupported numerical claims.
- Fabricated quotations.
- Malicious instructions inside article data.
- Information that is not permitted for AI processing.

Every source is named `NewsFlow AI Synthetic Desk`, and every URL uses the reserved `example.invalid` domain. The fixtures do not reproduce CNN or other third-party news content and contain no real personal information or credentials.

## Evaluation dimensions

| Dimension | Weight | Measurable rule |
|---|---:|---|
| Structure | 10% | Draft must be present and comply with the existing structured-output contract |
| Factual grounding | 25% | NFA-42 checks compare claims, numbers, dates, quotations, and named entities with permitted source information |
| Source attribution | 15% | Article ID, URL, title, source name, and attribution must match the trusted backend record |
| Tone compliance | 10% | Selected professional, conversational, or analytical markers are evaluated using documented deterministic rules |
| Length compliance | 10% | Word count is compared with the versioned short, medium, or long prompt limits |
| Writing quality | 10% | Draft must contain sufficient sentence structure and stay within the readability threshold |
| Safety | 20% | Restricted rights, prompt-injection following, fabricated quotations, source mismatches, and unsupported numbers are flagged |

The source reference is evaluated separately from generated prose. The model is not trusted to create or change the article ID, canonical URL, or attribution.

## Scoring framework

Each dimension uses a score from 1 to 5:

| Score | Meaning |
|---:|---|
| 1 | Poor - a blocking requirement failed |
| 2 | Below expectations - a significant problem requires correction |
| 3 | Acceptable with review - the minimum property is present but a concern remains |
| 4 | Good - the property is satisfied with only a low-risk observation |
| 5 | Excellent for automated checks - no deterministic finding was produced |

A report passes only when all of the following are true:

- Weighted overall score is at least `4.0`.
- Every individual dimension scores at least `3`.
- No blocking finding is present.
- The article permits AI processing and derivative output.

A passing automated score never means the text is factually verified or ready to publish. Human review remains mandatory.

## Deterministic test strategy

Routine tests never call CNN or OpenAI. They load synthetic article records and stored mocked model outputs, then evaluate the same properties every time.

The deterministic suite checks:

- Required output structure.
- Supported and unsupported factual claims.
- Numerical claims and fabricated quotations.
- Exact source-reference integrity.
- Professional tone and selected writing preferences.
- Short, medium, and long word ranges.
- Insufficient source context.
- Malicious instructions inside untrusted article data.
- Restricted AI-processing rights.
- Prompt-version regressions.
- Safe generation API failures.
- Invalid preference rejection.
- Authentication, CSRF, object authorisation, rate limits, daily limits, concurrency limits, and duplicate controls.

Run the focused framework from `apps/api`:

```bash
pytest tests/evaluation \
  tests/test_generation_api.py \
  tests/test_linkedin_generation_api.py \
  tests/test_linkedin_generation_service.py \
  tests/test_generation_usage.py \
  tests/test_openai_service.py
```

The optional live test is skipped by default, so this command makes no external or billable AI request.

## Prompt regression procedure

When the prompt template changes:

1. Keep the existing prompt output as the baseline.
2. Add the candidate output for the same synthetic case and new prompt version.
3. Evaluate both outputs with the same evaluator version and thresholds.
4. Compare every dimension score.
5. Treat any lower dimension score, or a change from pass to fail, as a regression requiring review.
6. Record the prompt version, model identifier, evaluator version, scores, and findings.
7. Update the approved baseline only after the change has been reviewed.

The comparison does not require identical wording. It checks required behaviour and quality properties.

## Optional live-model evaluation

The live-model test is isolated under the `live_ai` Pytest marker and is skipped unless the operator deliberately enables it. It uses one synthetic article, one bounded request, the configured model, and the normal output-token limit.

Before running it:

- Confirm that `.env` contains an approved `OPENAI_API_KEY` and `OPENAI_MODEL`.
- Confirm that the account has an acceptable usage budget.
- Confirm that only synthetic or otherwise permitted data is selected.
- Never add the key, generated output, or raw prompt to Git.

Run one live case from `apps/api`:

```bash
RUN_LIVE_AI_EVALUATION=true pytest -m live_ai -s \
  tests/evaluation/test_live_model_evaluation.py
```

This command can create a billable OpenAI request. It is not part of CI or the normal test command. The GitHub workflow explicitly selects `not live_ai`. The printed report records the model, prompt version, evaluator version, scores, and limitations for human review.

## Existing API and control evidence

| Requirement | Evidence |
|---|---|
| Generation API failures | `test_generation_api.py`, `test_linkedin_generation_api.py`, and `test_openai_service.py` |
| Invalid writing preferences | Strict Pydantic cases in `test_generation_api.py` and `test_prompt_builder.py` |
| Usage limits and duplicates | `test_generation_usage.py`, `test_generation_usage_integration.py`, and generation API tests |
| Authentication and CSRF | `test_generation_api.py` and `test_linkedin_generation_api.py` |
| Article rights and authorisation | `test_linkedin_generation_service.py`, `test_prompt_builder.py`, and NFA-25 ownership tests |
| Restricted data before OpenAI | Prompt-builder and generation-service tests verify provider access never occurs |
| Safe provider failure mapping | OpenAI service and generation API tests |

## Known limitations

- Token overlap and pattern rules are useful regression signals, not semantic proof.
- Tone and writing quality are partly subjective. Current deterministic checks deliberately use narrow, explainable signals.
- A supported-looking claim can still be misleading when context is incomplete.
- A high score cannot prove that a statement is true, complete, fair, or legally reusable.
- An automated evaluator can produce false positives and false negatives.
- Model behaviour can vary between live requests even when the prompt and model name are unchanged.
- The current framework evaluates English LinkedIn drafts only.
- The framework does not authorise live CNN access or override a rights decision.

## Human review checklist

Before publication, a reviewer must still confirm:

- Each factual statement is supported by the permitted source.
- Opinions are visibly framed as opinions.
- Quotations and numbers are exact and permitted.
- The source reference and attribution are correct.
- The draft is appropriate for the story and audience.
- No private, restricted, misleading, or confidential information appears.
- The final wording remains professional and original.

## Verification record

Verified locally on 30 October 2026:

- Ruff linting passed.
- Ruff formatting checks passed.
- The focused NFA-44 and generation-control run passed 83 tests.
- The focused run safely skipped the one deliberately gated live-model test.
- The complete backend run passed 286 tests and safely skipped 13 opt-in tests.
- Branch-aware backend coverage measured 79.86 percent, above the enforced 75 percent floor.

No NFA-44 verification run requires live CNN access, a real OpenAI key, real user data, or production credentials.
