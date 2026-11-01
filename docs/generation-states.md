# NFA-61 - Frontend Generation States

## Purpose

NFA-61 provides one reusable frontend state system for slow text and image generation operations. It tells users when a request is ready, being submitted, being processed, completed, or unsuccessful while preventing avoidable duplicate requests and outdated results.

The implementation does not change the FastAPI contract, expose provider credentials, or invent a background-job endpoint.

## Supported state model

| State | Meaning | Interface behaviour |
|---|---|---|
| `idle` | No request has started. | The interface displays a ready message and permits a valid request. |
| `submitting` | The browser is preparing and sending the request. | A loading indicator is shown and conflicting actions are disabled. |
| `processing` | The synchronous API request is still waiting for its result. | The loading message explains that generation may take time and duplicate submission remains blocked. |
| `completed` | A verified response has been received. | The private result is presented with a mandatory human-review reminder. |
| `failed` | The request could not complete safely. | A controlled message is displayed and a deliberate retry is offered only when appropriate. |

The current text and image APIs are synchronous from the browser's point of view. The browser waits for one response instead of polling for a background job.

`cancelled` is deliberately not exposed. FastAPI does not currently provide a confirmed cancellation operation for text generation or image regeneration. Resetting or leaving the component can abort the browser request and prevent its result from updating the interface, but it cannot prove that provider-side work stopped. A user-facing cancel action must not be added until the backend implements and documents that guarantee.

## State transitions

```text
idle
  |
  v
submitting
  |
  v
processing
  |\
  | +--> failed -- deliberate retry --> submitting
  |
  +----> completed

reset from completed or failed --> idle
```

The interface does not display a fabricated percentage because the synchronous APIs do not provide measurable progress.

## Reusable implementation

| File | Responsibility |
|---|---|
| `apps/web/types/generation-state.ts` | Defines the discriminated text and image state model and safe failure categories. |
| `apps/web/hooks/use-generation.ts` | Owns transitions, the active-request lock, retry input, request identity, abort handling, and stale-response protection. |
| `apps/web/hooks/use-image-generation.ts` | Applies the same lifecycle to image operations without creating a separate inconsistent model. |
| `apps/web/components/generation/generation-loading.tsx` | Displays text-specific or image-specific submitting and processing feedback. |
| `apps/web/components/generation/generation-error.tsx` | Displays a controlled failure and an optional deliberate retry action. |
| `apps/web/components/generation/generation-status.tsx` | Selects the correct idle, loading, completed, or failed presentation. |
| `apps/web/components/generation/generation-controls.tsx` | Integrates the reusable text state system with the existing NFA-60 request controls. |

The image hook and shared status components use the real synchronous image-operation model and are ready for a dedicated image control to supply its existing backend operation. NFA-61 does not invent a new image route or background-job workflow.

## Duplicate and stale-response protection

The hook assigns every accepted request a local request identifier and holds a synchronous active-request lock before React renders the loading state. A rapid second click is rejected before its operation can execute.

Resetting the state invalidates the active identifier and aborts the browser request. If an operation ignores the abort signal and later returns, the identifier check prevents that older response from replacing the current state. Starting a later request therefore cannot be overwritten by an outdated result.

The backend idempotency key remains a separate server-side protection. The frontend lock improves the experience, while FastAPI continues to enforce duplicate and concurrency rules authoritatively.

## Failure and retry policy

| Failure category | Example | Retry behaviour |
|---|---|---|
| Authentication | Missing or expired session | No automatic retry. The existing flow redirects the user to sign in. |
| Permissions | Article rights no longer permit generation | No retry from the same request. The user must choose an authorised source. |
| Validation | Invalid article, tone, length, or response | No automatic retry. The input or contract must be corrected. |
| Usage limit | Backend returns `429` and may provide `Retry-After` | A retry button is disabled for the safe delay, then the user may retry deliberately. |
| Conflict | A matching operation is already active | The user may retry deliberately after the active request finishes. |
| Provider timeout | Backend returns `504` | A controlled timeout message and deliberate retry are available. |
| Network | The browser cannot complete the request | Selections are preserved and the user may retry deliberately. |
| Service | A safe provider or gateway failure | The user may retry deliberately when the failure is marked retryable. |

No failure triggers an automatic repeat of a potentially expensive provider operation. Internal stack traces, prompts, source content, credentials, and provider error details are never displayed.

## Accessibility

- Submitting and processing messages use `role="status"` and `aria-live="polite"`.
- Failures use `role="alert"` and `aria-live="assertive"`.
- Completion uses a polite status announcement.
- The existing text-generation integration moves focus to important completed or failed feedback.
- Loading text is specific to drafts or illustrations and does not rely on animation alone.
- Retry remains a native button with a visible disabled countdown when a safe delay applies.

## Automated verification

`apps/web/__tests__/generation-state.test.tsx` covers:

- Initial idle state.
- Submitting and processing transitions.
- Successful completion and controlled failures.
- Deliberate retry after a timeout.
- Duplicate-request prevention.
- Stale-response protection.
- Image-specific processing and completion messages.
- Usage-limit retry countdowns.
- Polite status and assertive alert semantics.
- The absence of an unsupported cancellation action.

The existing generation-control suite also checks the integrated text workflow, including provider timeout handling.

Run the focused checks from `apps/web`:

```bash
npm test -- --run \
  __tests__/generation-state.test.tsx \
  __tests__/generation-controls.test.tsx \
  __tests__/generate-page.test.tsx
```

Run the complete frontend quality gate:

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

All tests use mocked operations and synthetic data. They do not contact OpenAI, CNN, or another external provider.

## Known limitations and next steps

- Cancellation remains unavailable until FastAPI can confirm that an operation was cancelled.
- No progress percentage is available from the synchronous APIs.
- Text generation is connected to the Create Post page. A later image-control task must connect its operation to `useImageGeneration` and `GenerationStatus` when that user interface is introduced.
- Generated drafts and illustrations still require human review and are never automatically published.
- Live CNN access remains blocked by ADR-001.

## Acceptance status

- Jira issue: NFA-61
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review
