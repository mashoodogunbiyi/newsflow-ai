# E6 Generation Frontend Integration Contract

## Purpose

This contract defines exactly how the future E6 Next.js interface must use the completed E4 LinkedIn generation backend.

E6 owns presentation and user interaction. FastAPI remains authoritative for sessions, CSRF, request validation, article rights, OpenAI access, output validation, usage limits, ownership, and audit evidence.

## Recommended Next.js boundary

The existing frontend sends authentication requests through same-origin Next.js route handlers. E6 should follow the same pattern by adding a server-side Next.js gateway such as:

```text
Browser POST /api/generations
       |
       v
Next.js route handler
       |
       | API_INTERNAL_BASE_URL
       v
FastAPI POST /api/generations
```

The gateway must forward only the required content type, `Idempotency-Key`, `X-CSRF-Token`, `newsflow_session`, and `newsflow_csrf` values. It must not log the draft, cookies, CSRF token, prompt, or error body. Direct browser-to-FastAPI requests are possible only when the exact origin and credentialed CORS configuration are correct, but the same-origin gateway is consistent with the current application.

## Authentication and CSRF

Generation requires:

- An active `newsflow_session` HTTP-only cookie.
- The readable `newsflow_csrf` cookie created by the backend login response.
- An `X-CSRF-Token` request header containing that CSRF value.
- Credentials included in the same-origin browser request.

The session identifier must never be read by client JavaScript or copied into local storage. The CSRF token is not an authentication credential and must still not be logged.

## Endpoint

```text
POST /api/generations
Content-Type: application/json
X-CSRF-Token: <current newsflow_csrf value>
Idempotency-Key: <optional 8-128 character client request key>
```

Request body:

```json
{
  "article_id": "46000000-0000-4000-8000-000000000002",
  "tone": "professional",
  "length": "medium"
}
```

Required request fields:

| Field | Type | Values |
|---|---|---|
| `article_id` | UUID string | ID returned by the authorised article catalogue. |
| `tone` | String enum | `professional`, `conversational`, or `analytical`. |
| `length` | String enum | `short`, `medium`, or `long`. |

Extra fields are rejected. E6 must not submit a prompt, model, user ID, token limit, source text, rights override, API key, or publishing instruction.

## Writing choices

| Length | Backend word range | Interface wording suggestion |
|---|---:|---|
| `short` | 80-120 words | Short |
| `medium` | 130-200 words | Medium |
| `long` | 220-320 words | Long |

The frontend can explain the choices, but it must send only the enum value. The backend validates them again.

## Successful response

HTTP status: `201 Created`

```json
{
  "generation_id": "generated-uuid",
  "article_id": "46000000-0000-4000-8000-000000000002",
  "draft": "Generated LinkedIn draft for human review.",
  "tone": "professional",
  "length": "medium",
  "source_title": "Synthetic article title",
  "source_name": "NewsFlow AI synthetic fixture",
  "source_url": "https://example.invalid/newsflow-ai/article",
  "source_attribution": "Source: NewsFlow AI synthetic fixture",
  "status": "draft",
  "review_required": true,
  "grounding_status": "passed_automated_checks",
  "validation_warnings": [],
  "grounding_policy_version": "grounding_v1",
  "created_at": "2026-10-30T16:00:00Z"
}
```

Suggested TypeScript contract:

```ts
type GenerationTone = "professional" | "conversational" | "analytical";
type GenerationLength = "short" | "medium" | "long";
type GroundingStatus =
  | "passed_automated_checks"
  | "review_required"
  | "rejected";

interface GenerationResponse {
  generation_id: string;
  article_id: string;
  draft: string;
  tone: GenerationTone;
  length: GenerationLength;
  source_title: string;
  source_name: string;
  source_url: string;
  source_attribution: string;
  status: "draft";
  review_required: true;
  grounding_status: GroundingStatus;
  validation_warnings: Array<{
    code: string;
    category:
      | "structure"
      | "source_reference"
      | "insufficient_context"
      | "unsupported_claim"
      | "legacy_data";
    message: string;
    severity: "review" | "blocking";
  }>;
  grounding_policy_version: "grounding_v1";
  created_at: string;
}
```

E6 should confirm the generated OpenAPI schema before finalising its TypeScript type. The backend Pydantic models remain the source of truth.

## Source reference presentation

The UI must keep the source reference visually separate from the generated draft. Display:

- Source title.
- Source name.
- Approved attribution text.
- A safe link using `source_url` with appropriate external-link protection.

Do not treat text inside the generated draft as the source reference. Do not replace the trusted backend URL or attribution with model-generated text.

## Review and validation presentation

Every successful response has `review_required = true`. E6 must:

- Label the result as an AI-generated draft.
- Tell the user to verify facts and wording before use.
- Display safe validation warnings when present.
- Never label `passed_automated_checks` as factually verified.
- Keep editing, copying, saving, and exporting as deliberate user actions.
- Never automatically publish to LinkedIn.

A blocking validation failure is returned as an error and has no draft for display.

## Error contract

Expected failures use:

```json
{
  "error": {
    "code": "stable_machine_readable_code",
    "message": "Safe user-facing message."
  }
}
```

| HTTP | Typical meaning | E6 behaviour |
|---:|---|---|
| 401 | Session missing or expired. | Clear local auth state and redirect to login with a return path. |
| 403 | CSRF failure or article rights denial. | For CSRF, restore session state before retrying. For rights denial, disable generation for the article and show the backend message. |
| 404 | Article missing or not disclosable. | Remove or refresh the selected article and ask the user to choose another. |
| 409 | Duplicate generation active or idempotency conflict. | Keep the form state. Respect `Retry-After` for an active duplicate or create a new key after a true conflict. |
| 422 | Invalid preferences or insufficient permitted source context. | Show field validation or ask the user to choose another article. Do not silently change the request. |
| 429 | Burst, daily, or concurrency allowance exceeded. | Disable resubmission until `Retry-After` expires and explain the temporary limit. |
| 502 | Provider output was invalid or failed grounding. | Keep the selection and show a safe retry message without displaying rejected output. |
| 503 | Generation, storage, rights data, configuration, or OpenAI unavailable. | Show a temporary service message and allow a deliberate later retry. |
| 504 | OpenAI request timed out. | Show a timeout message and allow a deliberate retry with a new idempotency key. |

The UI should display the safe backend message and use the stable code for behaviour. It must not show raw response bodies, tracebacks, provider request IDs, or internal details.

## Idempotency and loading behaviour

For each deliberate submit action, E6 should generate one non-secret client request key of 8 to 128 allowed characters and reuse it only while retrying the same article, tone, and length request.

While the request is active:

- Disable the submit button.
- Show an accessible loading state.
- Prevent double submission.
- Preserve the selected article and writing preferences.

Do not reuse one idempotency key after changing the article, tone, or length. Do not store it as an authentication secret.

## Example browser request

```ts
const response = await fetch("/api/generations", {
  method: "POST",
  credentials: "same-origin",
  headers: {
    "Content-Type": "application/json",
    "X-CSRF-Token": csrfToken,
    "Idempotency-Key": requestKey,
  },
  body: JSON.stringify({
    article_id: selectedArticleId,
    tone,
    length,
  }),
});

const payload = await response.json();
if (!response.ok) {
  throw payload.error;
}
```

The production component must validate that an error object exists before using it and provide a generic safe fallback for an unreadable response.

## E6 interface states

The generator should explicitly support:

1. No article selected.
2. Article selected and preferences ready.
3. Generation submitting.
4. Private draft returned.
5. Draft returned with review warnings.
6. Validation or rights failure.
7. Usage-limited state with retry countdown.
8. Temporary provider or backend failure.
9. Session-expired state.

Keyboard focus must move to the result or error summary after submission. Loading and error messages should use appropriate accessible live regions.

## Security requirements for E6

- Never expose `OPENAI_API_KEY`, `DATABASE_URL`, or backend-only configuration.
- Never store the session identifier, password, prompt, or generated draft in browser storage.
- Do not log request cookies, CSRF values, article content, or drafts.
- Treat the frontend protected route as navigation help only. FastAPI must remain the authority.
- Render the draft as text, not untrusted HTML.
- Preserve source and warning fields from the response without allowing them to override application controls.
- Do not add direct LinkedIn publishing under this contract.
- Continue using fixture data until live source authorisation replaces ADR-001.

## E6 acceptance checklist

- [ ] Authenticated user can select an authorised article.
- [ ] Tone and length controls use only documented enum values.
- [ ] Submit sends the CSRF header, cookies, and one request key.
- [ ] Loading prevents duplicate submission.
- [ ] Draft, source, attribution, and review requirement are displayed.
- [ ] Safe validation warnings are accessible.
- [ ] All documented error states are handled.
- [ ] Session expiry returns the user to login safely.
- [ ] No secret or session identifier enters client storage or logs.
- [ ] The interface does not describe automated checks as factual verification.
- [ ] The interface does not automatically publish to LinkedIn.
- [ ] Responsive and accessibility tests cover mobile, tablet, desktop, keyboard, and screen-reader behaviour.

## Backend evidence

- [Generation API](generation-api.md)
- [E4 AI generation architecture](architecture/ai-generation-architecture.md)
- [E4 acceptance results](e4-generation-acceptance.md)
- `apps/api/tests/test_generation_workflow_acceptance.py`

This contract is ready for E6 implementation. It does not itself implement the generator interface.
