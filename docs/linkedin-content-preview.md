# NFA-63 - LinkedIn-Inspired Content Preview

## Purpose

NFA-63 adds a reusable, responsive preview that combines the user's current edited draft, original source reference, selected AI-generated illustration, and review warnings before later saving or exporting.

The preview is a planning aid. It is not affiliated with LinkedIn, does not claim to reproduce LinkedIn exactly, does not display fake engagement information, and never publishes content.

## User journey

1. The authenticated user generates and edits a private LinkedIn draft.
2. The preview receives the current editor text and updates immediately in the browser.
3. When an image-selection workflow supplies a private generated-image ID, the preview displays it through the protected same-origin delivery route.
4. The preview keeps the original article source and backend review warnings visible outside the editable text.
5. The user reviews the combined presentation before later save or export actions are used.

## Component structure

| File | Responsibility |
|---|---|
| `apps/web/components/preview/linkedin-preview.tsx` | Composes the text, source, image, warnings, AI notice, and preview limitation. |
| `apps/web/components/preview/preview-image.tsx` | Displays the protected image, accessible alternative text, AI designation, no-image state, and failed-image fallback. |
| `apps/web/components/preview/preview-source.tsx` | Displays only the trusted source reference and accepts only HTTPS source links. |
| `apps/web/types/preview.ts` | Defines the serialisable preview content, source, and selected-image contracts and validates image UUIDs. |
| `apps/web/lib/image-content-proxy.ts` | Proxies private image bytes while forwarding only the session cookie and accepting only PNG, JPEG, or WebP. |
| `apps/web/app/api/images/[imageId]/content/route.ts` | Exposes the narrow same-origin image-preview route used by the browser. |
| `apps/web/components/editor/linkedin-editor.tsx` | Passes live edited text, source data, warnings, and an optional selected image to the reusable preview. |

## Preview data contract

The component receives:

- Current edited text.
- Grounding status and backend validation warnings.
- Source title, source name, attribution text, and the original validated URL.
- Either one selected generated-image UUID with accessible alternative text or `null`.

The component does not receive article descriptions, full article content, object-storage keys, signed storage URLs, credentials, prompts, or session identifiers. This prevents the preview layer from becoming another route for restricted source content or private storage details.

## Live synchronisation

The controlled editor passes its current text directly to the preview. React rerenders the preview after each edit without calling FastAPI or OpenAI.

The selected image is also a prop. When the selected image ID changes, React replaces the image asset and clears any previous load-failure state. This contract allows a later image picker to update the preview without changing the preview components.

The existing Create Post flow does not yet contain an image picker, so it currently passes no selected image. The documented no-image state is therefore the normal interface until that separate workflow is implemented.

## Private image delivery

The browser requests:

```text
GET /api/images/{image_id}/content
```

The Next.js route:

1. Rejects a non-UUID image identifier before contacting FastAPI.
2. Extracts only the `newsflow_session` cookie from the incoming request.
3. Calls the existing NFA-53 owner-protected FastAPI content endpoint.
4. Does not forward analytics cookies, CSRF cookies, authorisation headers, or arbitrary request headers.
5. Returns only validated `image/png`, `image/jpeg`, or `image/webp` bytes.
6. Applies private, no-store caching and `nosniff` protection.
7. Replaces backend and network details with a controlled error response.

The Next.js `Image` component uses `unoptimized` because its normal optimisation request does not forward authentication headers. The original validated private bytes still pass through the same-origin gateway, and no public object URL is created.

## Text, source, and image safety

- Edited text is rendered as React text with `white-space: pre-wrap`; `dangerouslySetInnerHTML` is not used.
- HTML-like input remains visible text and cannot create scripts or elements.
- Source details are separate from the edited post and only a validated HTTPS URL becomes a link.
- The preview does not accept or reproduce article body content.
- Every image area displays `AI-generated illustration` and `Not authentic news photography`.
- Missing and failed images do not remove the draft or source reference.
- Review warnings remain visible after editing, and no-warning results still require human fact-checking.
- No LinkedIn logo, official branding, engagement counts, reactions, comments, or publishing control is reproduced.

## Empty and error states

| State | Behaviour |
|---|---|
| Empty draft | Shows a clear placeholder while leaving the editor usable. |
| No selected image | Keeps the text and source visible with a neutral no-image panel. |
| Invalid image ID | Does not make a request and displays the unavailable-image fallback. |
| Missing or unauthorised image | FastAPI returns a private not-found response and the preview displays a controlled fallback. |
| Unsupported image media type | The gateway rejects it instead of relaying executable or unapproved content. |
| Invalid source URL | Displays the source details without creating a link. |

## Accessibility and responsive behaviour

- The preview has a labelled section and logical heading structure.
- The illustration requires meaningful alternative text, with a safe fallback description for empty input.
- Failed image delivery is announced as a status without blocking access to the text.
- Source links use descriptive wording and open with `noopener noreferrer`.
- Text and long links wrap instead of creating horizontal overflow.
- The editor and preview stack on smaller screens and use two columns at the existing wide-screen breakpoint.
- Padding, image height, caption layout, and card rounding adapt at the small-screen breakpoint.

## Automated verification

`apps/web/__tests__/linkedin-preview.test.tsx` covers:

- Multiline text and source rendering.
- Selected image delivery path and accessible alternative text.
- AI-generated image designation.
- Live text and selected-image changes.
- Empty text, no-image, and image-error states.
- Literal HTML-like text rendering.
- Review warnings and unsafe source-link rejection.
- Fluid responsive layout classes.

`apps/web/__tests__/image-content-proxy.test.ts` covers:

- Session-cookie-only forwarding.
- Private cache and content-type headers.
- UUID rejection before backend access.
- Unsupported media-type rejection.
- Controlled not-found and network failures.

`apps/web/__tests__/linkedin-editor.test.tsx` confirms the selected-image contract is integrated with live editor text.

Run the focused checks from `apps/web`:

```bash
npm test -- --run \
  __tests__/linkedin-preview.test.tsx \
  __tests__/image-content-proxy.test.ts \
  __tests__/linkedin-editor.test.tsx \
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

The tests use synthetic text, source records, image IDs, and local byte fixtures. They do not contact CNN, OpenAI, private storage, or another external service.

## Preview limitations

- The preview is inspired by the intended destination but is not a pixel-accurate LinkedIn emulator.
- LinkedIn can change its typography, truncation, image cropping, and other rendering behaviour independently.
- The current Create Post flow has no image-selection control, so the preview shows the no-image state until that separate UI is implemented.
- The preview does not save, export, copy, or publish content. Those actions belong to later tasks.
- The preview does not replace factual, legal, source-rights, or image-safety review.
- Live CNN access remains blocked by ADR-001.

## Acceptance status

- Jira issue: NFA-63
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review
