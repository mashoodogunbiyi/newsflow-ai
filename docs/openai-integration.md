# NFA-38 - Secure OpenAI Integration Service

## Outcome

NFA-38 adds a secure, reusable OpenAI text-generation boundary to the FastAPI backend. Backend workflows can now request generated text through one service without exposing credentials to Next.js, duplicating provider logic, or making uncontrolled repeated requests.

This task provides the foundation for later E4 generation features. It does not add a public generation endpoint and it does not send live article information to OpenAI.

## Architecture

```text
Next.js frontend
       |
       | Future authenticated generation request
       v
FastAPI route and application service
       |
       | Authentication, authorisation, rights, and input checks
       v
OpenAIService
       |
       | Official server-side OpenAI Python SDK
       v
OpenAI Responses API
```

The browser never receives `OPENAI_API_KEY` and never calls OpenAI with a secret key. A future generation workflow must authenticate the user, verify object ownership, confirm that the selected article permits AI processing and derivative output, and prepare the smallest permitted fact set before calling `OpenAIService`.

## Implementation

| Component | Responsibility |
|---|---|
| `app/core/ai_config.py` | Holds one immutable, validated, secret-safe OpenAI configuration object. |
| `app/core/config.py` | Loads the key, model, timeout, output limit, and retry budget from environment variables. |
| `app/models/ai.py` | Defines masked input, structured output, and optional token-usage models. |
| `app/services/openai_service.py` | Initialises the official asynchronous SDK, sends bounded Responses API requests, maps failures, and returns provider-neutral results. |
| `tests/test_openai_service.py` | Uses test doubles for successful and failed provider responses without making network requests. |

The service uses the official `openai` Python package and its asynchronous `AsyncOpenAI` client. It calls `client.responses.create` with:

- The model selected through application configuration.
- Sensitive input and optional instructions supplied by an authorised backend caller.
- A per-request output-token limit that cannot exceed the configured maximum.
- `store=False` so the request does not ask OpenAI to store the response.

The implementation follows the [official OpenAI Python SDK documentation](https://developers.openai.com/api/reference/python) and the [Responses API create reference](https://developers.openai.com/api/reference/python/resources/responses/methods/create).

## Configuration

Copy `.env.example` to the ignored `.env` file. Put real values only in `.env` or an approved deployed secret store.

```dotenv
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=your_approved_openai_model_here
OPENAI_REQUEST_TIMEOUT=30
OPENAI_MAX_OUTPUT_TOKENS=800
OPENAI_MAX_RETRIES=2
```

| Variable | Required for OpenAI use | Sensitive | Validation and purpose |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | Yes | Server-side credential. Empty and committed example values are rejected. |
| `OPENAI_MODEL` | Yes | No | Selects one approved model without hard-coding a model name in service code. |
| `OPENAI_REQUEST_TIMEOUT` | No | No | Request deadline in seconds from 1 to 300. Default: 30. |
| `OPENAI_MAX_OUTPUT_TOKENS` | No | No | Maximum generated output from 1 to 100000 tokens. Default: 800. |
| `OPENAI_MAX_RETRIES` | No | No | Extra SDK attempts for eligible temporary failures from 0 to 5. Default: 2. |

The service validates this configuration only when an OpenAI feature tries to initialise it. The rest of NewsFlow AI can therefore run locally without an OpenAI key. Placeholder values produce controlled configuration errors and are never printed.

Never use a `NEXT_PUBLIC_` name for the OpenAI key. Next.js exposes variables with that prefix to browser code.

## Backend usage

Only an authorised backend service should construct and use this integration:

```python
from app.models.ai import AITextGenerationRequest
from app.services.openai_service import OpenAIService

service = OpenAIService.from_settings()
try:
    result = await service.generate_text(
        AITextGenerationRequest(
            input_text="Permitted, validated fact set",
            instructions="Create a concise professional draft.",
            max_output_tokens=500,
        )
    )
finally:
    await service.close()
```

`result` contains generated text, the returned or configured model, optional response and request identifiers, and any available input, output, and total token counts. The service does not automatically repeat a completed generation request.

This example shows the provider boundary only. A later E4 application service must add user-level limits, article-rights checks, approved prompting, persistence, and a FastAPI endpoint before the frontend can request a draft.

## Failure handling and retry policy

| Provider condition | Application error code | Retryable after this call | Behaviour |
|---|---|---|---|
| Invalid credentials | `openai_authentication_failed` | No | Rejects the request without revealing the key or provider message. |
| Rate limit after the SDK retry budget | `openai_rate_limited` | Yes | Returns a safe temporary failure to the calling workflow. |
| Timeout after the SDK retry budget | `openai_timeout` | Yes | Returns a safe timeout failure. |
| Connection or service failure | `openai_unavailable` | Yes | Returns a safe availability failure. |
| Other provider rejection | `openai_request_rejected` | No | Returns a generic rejection without provider details. |
| Incomplete or empty response | `openai_incomplete_response` or `openai_empty_response` | No | Rejects unusable generated output. |
| Requested output above the configured cap | `openai_output_limit_exceeded` | No | Blocks the call before the provider is contacted. |

`OPENAI_MAX_RETRIES` controls the official SDK's bounded retry behaviour for eligible temporary failures. Authentication errors and application validation failures are not deliberately retried by NewsFlow AI. A later workflow may retry a reported temporary application error only through an explicitly reviewed job policy with its own strict limit.

## Security, privacy, and cost controls

- The API key is read by FastAPI only and stored in Pydantic `SecretStr` values.
- Prompt input and instructions are also represented as `SecretStr`, so normal model representations mask them.
- Logs contain only stable events, the configured model, safe status, safe error code, request ID, and token counts.
- Logs do not contain the API key, prompt, instructions, generated output, provider response body, or raw provider error.
- Generated output is capped before access to control unexpected cost.
- Timeout and retry values are bounded by validation.
- Token usage is recorded in the structured result when OpenAI supplies it.
- Automated tests use mocked responses and never require a real key or billable request.
- Restricted article information must not be sent to this service. NFA-32 rights checks remain mandatory for future generation workflows.

## Automated verification

Run the focused checks from the repository root:

```bash
apps/api/.venv/bin/ruff check apps/api/app/core/ai_config.py apps/api/app/core/config.py apps/api/app/models/ai.py apps/api/app/services/openai_service.py apps/api/tests/test_config.py apps/api/tests/test_openai_service.py
apps/api/.venv/bin/pytest -q apps/api/tests/test_config.py apps/api/tests/test_openai_service.py
```

The automated coverage includes:

- Successful structured text generation.
- SDK client configuration and default output limits.
- Missing keys and models.
- Authentication, rate-limit, timeout, connection, and incomplete-response failures.
- Output-limit enforcement before provider access.
- Present and absent usage metadata.
- Masked request representations and log redaction.

No test makes a live OpenAI request.

Verified locally on 29 October 2026:

- The focused configuration and OpenAI service run passed 27 tests.
- The complete backend run passed 185 tests and safely skipped 11 opt-in PostgreSQL tests.
- Branch-aware backend coverage measured 80.36 percent, above the enforced 75 percent floor.
- Ruff linting and formatting checks passed.
- Docker Compose configuration validation passed.

## Limitations and next steps

- NFA-38 provides a reusable internal service, not a user-facing API endpoint.
- No real OpenAI credential or model is committed or validated against the live service.
- No article is sent to OpenAI in this task.
- A later E4 task must build the generation use case, call the NFA-32 rights service first, apply user and cost limits, and persist an approved draft safely.
- Live CNN access remains blocked by ADR-001. The existence of this OpenAI service does not authorise CNN content use.

## Acceptance evidence

- Official SDK installed: `openai>=2,<3` in `apps/api/pyproject.toml`.
- Reusable backend service: `apps/api/app/services/openai_service.py`.
- Environment configuration: `.env.example`, `app/core/config.py`, and `app/core/ai_config.py`.
- Structured request and result models: `apps/api/app/models/ai.py`.
- Safe logs and failure mapping: `app/services/openai_service.py` and `app/core/logging_config.py`.
- Mocked automated tests: `apps/api/tests/test_openai_service.py` and `apps/api/tests/test_config.py`.
- Configuration and local development documentation: this guide, the root README, the backend README, and `docs/development-setup.md`.

NFA-38 is implemented and ready for Mashood Ogunbiyi's review. The Jira issue should move to Done only after the branch checks pass, the pull request is merged, and the final repository evidence is attached.
