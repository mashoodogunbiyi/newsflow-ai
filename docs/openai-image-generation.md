# NFA-50 - OpenAI Image Generation Integration

## Status

- Implementation: complete
- Automated provider calls: mocked only
- Live OpenAI calls: not performed by the normal test suite
- Human review before publication: required
- Owner approval: pending Mashood Ogunbiyi's review

## Purpose

NFA-50 adds a reusable backend-only service that submits an approved NFA-48 image prompt to OpenAI only after NFA-49 and the current article-rights decision permit the call. The service returns validated image data and content-free operational metadata through a provider-neutral internal model.

The frontend never receives or handles `OPENAI_API_KEY`.

## Provider and API selection

The integration uses the official asynchronous OpenAI Python SDK version 2.54 or later within major version 2 and the direct Images API. This endpoint fits NewsFlow AI because one reviewed prompt produces one new illustration. Multi-turn conversational image editing is not required for this task.

The reviewed default is `gpt-image-2.5-flare`. The approved allowlist is:

- `gpt-image-2.5-flare`
- `gpt-image-2.5-flare-2026-09-08`
- `gpt-image-2.5-sunburst`
- `gpt-image-2.5-sunburst-2026-09-08`

Flare is the default for fast, high-quality everyday generation. Sunburst remains available when a future reviewed workflow needs more precise image editing. A newly released model must be reviewed and added to the backend allowlist before it can be configured.

Official references:

- [OpenAI image generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- [OpenAI Python create-image reference](https://developers.openai.com/api/reference/python/resources/images/methods/generate)
- [OpenAI content provenance guide](https://developers.openai.com/api/docs/guides/content-provenance)

## Workflow

```text
NFA-48 approved image prompt
        |
        v
Current USE_FOR_AI_GENERATION rights decision
        |
        v
NFA-49 allowed or allowed_with_restrictions decision
        |
        v
OpenAIImageGenerationService
        |
        v
OpenAI Images API with moderation=auto
        |
        v
Validate response type, size, format, and image signature
        |
        v
Masked image data reference plus content-free metadata
        |
        v
Storage service in a later task and mandatory human review
```

The service refuses provider access when:

- The article-rights decision is absent, denied, for another article, for another operation, or for a different rights version.
- The NFA-49 decision is rejected or requires review.
- The safety result belongs to a different article or LinkedIn generation.
- Required prompt or output moderation controls are disabled.
- Documentary use is enabled anywhere in the request.
- The assembled provider prompt is empty or exceeds the provider limit.

## Provider request

Every accepted request sends controlled parameters:

| Parameter | Rule |
|---|---|
| `model` | Backend allowlist and environment configuration only |
| `prompt` | NFA-48 trusted instructions, application safety controls, and marked untrusted context |
| `n` | Always `1` |
| `size` | `1024x1024`, `1536x1024`, or `1024x1536`, matched to the approved aspect ratio |
| `quality` | `low`, `medium`, or `high`; default `medium` |
| `output_format` | `png`, `jpeg`, or `webp`; default `png` |
| `background` | Always `opaque` |
| `moderation` | Always `auto`; the less restrictive `low` option is not exposed |
| `safety_identifier` | Optional `nf_` prefixed SHA-256 identifier, never a raw email or username |

GPT Image 2.5 also supports higher quality settings, but NFA-50 deliberately excludes them until product cost and latency limits are reviewed. It also excludes multiple images, streaming partial images, arbitrary dimensions, transparent output, and image editing.

## Configuration

The root ignored `.env` file may contain:

```dotenv
OPENAI_API_KEY=replace_in_your_ignored_env_file
OPENAI_IMAGE_MODEL=gpt-image-2.5-flare
IMAGE_GENERATION_TIMEOUT=120
IMAGE_GENERATION_MAX_CONCURRENT_REQUESTS=2
IMAGE_GENERATION_MAX_RETRIES=1
IMAGE_GENERATION_RETRY_BASE_SECONDS=1
IMAGE_GENERATION_MAX_RESPONSE_BYTES=26214400
IMAGE_GENERATION_DUPLICATE_CACHE_SIZE=100
```

| Variable | Default | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | none | Backend-only provider credential |
| `OPENAI_IMAGE_MODEL` | `gpt-image-2.5-flare` | Reviewed image model |
| `IMAGE_GENERATION_TIMEOUT` | `120` seconds | Hard application and SDK deadline |
| `IMAGE_GENERATION_MAX_CONCURRENT_REQUESTS` | `2` | Per-process provider-call concurrency |
| `IMAGE_GENERATION_MAX_RETRIES` | `1` | Extra attempts for explicit rate-limit rejection only |
| `IMAGE_GENERATION_RETRY_BASE_SECONDS` | `1` | Bounded exponential fallback delay |
| `IMAGE_GENERATION_MAX_RESPONSE_BYTES` | `26214400` | Maximum accepted inline image payload |
| `IMAGE_GENERATION_DUPLICATE_CACHE_SIZE` | `100` | Per-process completed-request cache size |

The application can start without an OpenAI key. A real key becomes required only when the image service is initialised. Empty values, committed placeholders, and unsupported model names produce controlled errors without displaying a key.

Some accounts may need OpenAI API organization verification before a GPT Image model can be used. Account access and current rate limits must be checked in the OpenAI developer console before enabling live calls.

## Response validation

The service supports the provider response forms represented by its internal interface:

- Base64 image data is strictly decoded into masked bytes.
- An HTTPS provider retrieval URL can be represented without fetching it.

Inline data is rejected if it is empty, invalid Base64, larger than the configured limit, or does not match the requested PNG, JPEG, or WebP signature. Plain HTTP URLs, credential-bearing URLs, missing image data, and multiple images are rejected.

The successful internal result includes:

- Application request ID.
- Provider and model identifier.
- Provider request ID when supplied.
- Masked image bytes or masked HTTPS retrieval reference.
- Output media type, length, and SHA-256 digest when bytes are available.
- Prompt, safety-policy, safety-evaluation, and rights-version identifiers.
- Size, quality, and output format.
- Available token usage.
- `AI-generated illustration` designation.
- Mandatory human-review state.

Image bytes, retrieval URLs, prompts, article text, revised prompts, API credentials, and raw provider errors are excluded from logs and safe metadata records.

## Errors and retries

| Condition | Safe category | Retry behaviour |
|---|---|---|
| Missing key or unsupported model | `configuration` | No provider call |
| Safety decision denied | `safety_denied` | No provider call |
| Source rights denied | `rights_denied` | No provider call |
| Active or conflicting request ID | `duplicate_request` | No duplicate provider call |
| Invalid provider credentials | `authentication` | No retry |
| Explicit provider rate limit | `rate_limit` | Bounded retry with capped delay |
| Provider quota or billing limit | `quota` | No retry |
| Timeout | `timeout` | No automatic replay |
| Connection or temporary provider failure | `unavailable` | No automatic replay |
| Provider moderation block | `moderation_blocked` | No retry without a changed request |
| Other provider rejection | `request_rejected` | No retry |
| Missing, oversized, or malformed result | `invalid_response` | No retry |

The official SDK automatic retry count is set to zero for this service. NFA-50 retries only an explicit rate-limit rejection, because that response establishes that generation did not begin. It does not automatically replay timeouts, connection failures, or server failures where the provider might already have accepted an expensive generation request.

## Duplicate and cost controls

Each request requires an application UUID. The service keeps a bounded in-memory fingerprint cache:

- A repeated completed request returns its cached result without a second provider call.
- A request ID currently in progress is rejected as an active duplicate.
- Reusing a request ID with different approved input is rejected as a conflict.
- A semaphore limits concurrent calls within one backend process.
- One request can create only one image.

This cache is a local development and service-layer safeguard. A later persistent image-generation workflow must add database-backed idempotency and shared concurrency controls before multiple backend processes are deployed.

## Usage and metadata

When OpenAI returns usage information, the service captures available input, output, total, text, and image token counts. Prices are not hard-coded because they can change. A recorder interface accepts only content-free completion metadata.

If metadata recording fails after the provider succeeds, the generated result remains cached and is returned. This prevents a recorder failure from encouraging an expensive duplicate call. Operational monitoring must still alert on a recording failure.

## Security and privacy

- `OPENAI_API_KEY` remains a backend `SecretStr` and never enters browser code.
- `.env` remains excluded by `.gitignore`; `.env.example` contains no real secret.
- Prompts, article content, generated bytes, provider URLs, and raw errors are not logged.
- The optional provider safety identifier accepts only a pre-hashed `nf_` SHA-256 value.
- Restricted CNN content must never be passed to the service.
- Current article rights are checked again immediately before provider access.
- Provider output is treated as untrusted and validated before later storage.
- The visible AI designation and human review remain mandatory.

## Automated verification

Run the focused checks from the repository root:

```bash
apps/api/.venv/bin/ruff check \
  apps/api/app/core/config.py \
  apps/api/app/core/image_generation_config.py \
  apps/api/app/models/image_generation.py \
  apps/api/app/services/openai_image_service.py \
  apps/api/tests/test_config.py \
  apps/api/tests/test_openai_image_service.py
apps/api/.venv/bin/ruff format --check \
  apps/api/app/core/config.py \
  apps/api/app/core/image_generation_config.py \
  apps/api/app/models/image_generation.py \
  apps/api/app/services/openai_image_service.py \
  apps/api/tests/test_config.py \
  apps/api/tests/test_openai_image_service.py
apps/api/.venv/bin/pytest -q \
  apps/api/tests/test_config.py \
  apps/api/tests/test_openai_image_service.py
```

The tests use the official SDK exception classes and mocked image responses. They do not call OpenAI, spend credits, use CNN content, or require a real key.

Verified locally on 31 October 2026:

- Focused NFA-50 configuration and image-service run: 44 passed.
- Complete normal backend suite: 376 passed and 13 safely skipped.
- Branch-aware backend coverage: 84.02 percent.
- Ruff linting: passed.
- Ruff formatting check: all 153 Python files formatted.

## Limitations and next steps

NFA-50 provides the provider boundary, not the complete user feature. It does not yet:

- Expose a public image-generation endpoint.
- Persist generated images or shared idempotency state.
- Verify content provenance signals after generation.
- Add the generated image to the user's library.
- Build the frontend image-generation interface.
- Publish an image or LinkedIn post automatically.

Those capabilities require separate reviewed tasks. Live CNN material remains blocked until authorised rights exist, and every generated illustration requires user review before export or publication.
