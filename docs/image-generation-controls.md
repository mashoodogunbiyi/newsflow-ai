# NFA-64 - Image Generation Controls

## Outcome

NFA-64 connects the Create Post editor to the approved E5 image workflow. An authenticated user can generate the first private illustration for a generated LinkedIn draft, review it in the existing preview, create immutable alternatives, and select which version is displayed.

The feature does not publish an image, save edited draft text, expose an OpenAI credential, or create documentary news photography.

## User workflow

1. Generate a valid LinkedIn draft from an authorised article.
2. Choose one supported illustration style, image shape, and composition.
3. Select **Generate image**.
4. Review the private result, its AI designation, and its safety status.
5. Select **Regenerate image** to create an alternative without deleting the original.
6. Select any retained version to update the LinkedIn-inspired preview.

Text edits remain unchanged during every image operation. Image selection affects only the local preview until the later E7 persistence workflow is implemented.

## Supported preferences

The browser and FastAPI use the same closed values:

| Preference  | Supported values                                                                                     |
| ----------- | ---------------------------------------------------------------------------------------------------- |
| Style       | Editorial illustration, Minimalist illustration, Abstract technology, Professional infographic style |
| Shape       | Landscape, Square, Portrait                                                                          |
| Composition | Balanced, Focus left, Focus right                                                                    |

FastAPI validates the request again. A browser value is never treated as trusted merely because it came from a controlled form.

## Request flow

```text
Image controls
    |
    | POST /api/images or /api/images/{id}/regenerate
    | CSRF proof + idempotency key
    v
Next.js same-origin gateway
    |
    | allowlisted headers and authentication cookies only
    v
FastAPI image service
    |
    | owner lookup -> current rights -> safety -> usage limit
    | -> OpenAI boundary -> validation -> private storage
    v
Private image metadata and protected content endpoint
```

### Initial image

`POST /api/images` accepts the text `generation_id` returned by the existing draft API. FastAPI resolves that identifier together with the authenticated owner. It does not accept a user ID or trust the browser to provide a generated-post database ID.

### Regeneration

`POST /api/images/{image_id}/regenerate` reuses the E5 immutable regeneration service. The selected private image is the parent. A successful result has a new image ID and increasing sequence while the parent remains stored and selectable.

### Delivery

The gallery and preview load bytes through `/api/images/{imageId}/content`. Next.js forwards only the session cookie to the owner-protected FastAPI delivery endpoint. Private storage keys and provider credentials never reach browser code. Next.js image optimisation is deliberately disabled for these protected resources because the optimiser does not forward authentication headers.

## States and failures

The controls reuse the NFA-61 lifecycle:

- Idle - no request has started.
- Submitting - the request is being prepared and sent.
- Processing - the backend or image provider is working.
- Completed - a private result is available for human review.
- Failed - a safe, category-specific message is shown.

Authentication, permissions, and validation failures are not automatically retried. Conflict, usage-limit, timeout, network, and service failures can be retried deliberately. A valid `Retry-After` header temporarily disables retry. The synchronous request lock prevents rapid duplicate clicks, and idempotency protects a retried request at the backend.

If regeneration fails, the original image and edited draft remain available. The interface never reports success without a runtime-validated response.

## Safety and privacy

- The central NFA-49 safety policy runs before every provider call.
- Current article rights are checked again for initial generation and regeneration.
- All results are labelled `AI-generated illustration` and `Not authentic news photography`.
- Human review remains required even when the automated safety status is approved.
- OpenAI keys, storage keys, session identifiers, prompts, source content, and image bytes are not written to browser storage or logs.
- The backend rate limiter and durable generation usage controls remain authoritative.
- No live CNN source is enabled. ADR-001 remains No-Go for live CNN integration.

## Accessibility and responsive behaviour

- Styles use native labelled radio inputs.
- Shape and composition use native labelled selects.
- Version selection uses one native radio group.
- All generated images receive contextual alternative text.
- Loading uses polite status announcements and failures use alert semantics.
- Controls disable truthfully during a request and remain keyboard operable.
- The controls and gallery collapse to one column on narrow screens and expand to two columns when space permits.

## Automated evidence

| Behaviour                                                    | Evidence                                            |
| ------------------------------------------------------------ | --------------------------------------------------- |
| Owner-scoped initial generation and private root version     | `apps/api/tests/test_image_regeneration.py`         |
| Initial-request idempotency and cross-user protection        | `apps/api/tests/test_image_regeneration.py`         |
| FastAPI initial-image contract                               | `apps/api/tests/test_image_regeneration.py`         |
| Browser request validation and safe failure mapping          | `apps/web/__tests__/image-generation-api.test.ts`   |
| Same-origin gateway header and cookie allowlist              | `apps/web/__tests__/image-generation-proxy.test.ts` |
| Generation, preview update, and AI designation               | `apps/web/__tests__/image-controls.test.tsx`        |
| Regeneration, original preservation, and draft preservation  | `apps/web/__tests__/image-controls.test.tsx`        |
| Duplicate-click protection                                   | `apps/web/__tests__/image-controls.test.tsx`        |
| Existing preview, editor, and generation regression coverage | `apps/web/__tests__`                                |

All automated tests use synthetic records and mocked network or provider boundaries. They make no real OpenAI call and spend no provider credits.

## Known boundaries

- Image generation requires a valid generated LinkedIn draft; it is not available before text generation.
- The first real local provider request requires a correctly configured server-side OpenAI key and may incur provider cost.
- Image selection is local to the current editor session. Persistent saved-content version selection belongs to E7.
- The interface cannot cancel a provider request after FastAPI has accepted it.
- Responsive and assistive-technology behaviour should still receive a manual browser review before release.

## Acceptance status

The NFA-64 implementation is complete in code and automated tests. It remains pending Mashood Ogunbiyi's review and Jira approval.
