# NFA-60 - LinkedIn Generation Controls

## Purpose

NFA-60 gives an authenticated user the controls needed to request a private AI-generated LinkedIn draft from the article selected in NFA-59. The interface supports only the writing choices accepted by FastAPI, prevents avoidable duplicate submissions, and explains when generation is unavailable.

The browser never calls OpenAI directly. It sends a narrow request through a same-origin Next.js route, and FastAPI remains responsible for authentication, CSRF validation, source rights, usage controls, OpenAI access, output validation, persistence, and safe errors.

## User flow

```text
Authorised article selected in NFA-59
    |
    v
Choose tone and length
    |
    v
Next.js validates the visible preferences
    |
    | POST /api/generations
    v
Same-origin Next.js gateway
    |
    | session cookies, CSRF header, idempotency key
    v
FastAPI repeats authentication, rights, and request checks
    |
    v
Private draft receipt or a controlled error state
```

No step publishes content to LinkedIn. A successful result remains a private AI draft that requires human review.

## Supported preferences

The controls and backend share these exact enum values:

| Control | API value        | Interface meaning                                            |
| ------- | ---------------- | ------------------------------------------------------------ |
| Tone    | `professional`   | Clear and polished writing for a broad professional audience |
| Tone    | `conversational` | Approachable writing that invites discussion                 |
| Tone    | `analytical`     | Structured writing focused on context and implications       |
| Length  | `short`          | Approximately 80 to 120 words                                |
| Length  | `medium`         | Approximately 130 to 200 words                               |
| Length  | `long`           | Approximately 220 to 320 words                               |

The default request is `professional` and `medium`. Next.js validates these choices for user experience, while FastAPI performs the authoritative validation.

## Request contract

Browser request:

```text
POST /api/generations
Content-Type: application/json
X-CSRF-Token: <newsflow_csrf cookie value>
Idempotency-Key: generation:<random UUID>
```

Example synthetic body:

```json
{
  "article_id": "10000000-0000-4000-8000-000000000003",
  "tone": "professional",
  "length": "medium"
}
```

Only the article UUID, tone, and length are accepted. The browser does not send source text, a user ID, a prompt, a model name, a token allowance, an OpenAI key, or publishing instructions.

The same-origin route at `app/api/generations/route.ts` forwards only:

- `Content-Type`.
- `Idempotency-Key`.
- `X-CSRF-Token`.
- `newsflow_session` and `newsflow_csrf` cookies.

It does not forward analytics cookies, browser authorisation headers, or unrelated headers. Responses always use `Cache-Control: no-store`. The gateway preserves a safe `Retry-After` response so the interface can temporarily prevent another request.

## Duplicate request protection

The component uses two complementary controls:

1. A synchronous in-memory lock stops rapid repeated form submissions before React completes a rerender.
2. The Generate button and preference controls are disabled while the request is active.
3. A random idempotency key is created for one article, tone, and length combination.
4. A safe retry of that same combination reuses the key.
5. Changing the article, tone, or length invalidates the old key.

The key is not a credential and is not stored in local storage or session storage. FastAPI still applies its shared duplicate, concurrency, daily, and rate-limit controls.

## Controlled states

| Condition                                 | Interface behaviour                                                           |
| ----------------------------------------- | ----------------------------------------------------------------------------- |
| No article                                | Controls and Generate action are disabled; user is sent back to the catalogue |
| Invalid article UUID                      | Controls remain disabled and the selection is rejected locally                |
| Restricted article                        | Permitted source details remain visible but generation is disabled            |
| Insufficient permitted source information | Generation is disabled with a specific explanation                            |
| Active request                            | All inputs and the Generate action are disabled with accessible progress text |
| Authentication failure                    | The user returns to login and the protected route is refreshed                |
| Usage or concurrency limit                | Safe message is shown and retry remains disabled for `Retry-After` seconds    |
| Validation or rights failure              | Safe backend message is shown without internal details                        |
| Provider, storage, or network failure     | Preferences remain selected and a deliberate retry is possible                |
| Successful request                        | Private-draft receipt, mandatory review reminder, and generation ID are shown |

An unreadable, malformed, or request-mismatched success response is rejected by the TypeScript runtime validator. Raw response bodies, stack traces, prompts, credentials, and provider request identifiers are never displayed.

## Accessibility and responsive behaviour

- Tone and length use native radio inputs grouped by labelled `fieldset` and `legend` elements.
- Every choice has a visible label and description.
- The form and Generate button work with keyboard navigation.
- Disabled states use real HTML `disabled` behaviour rather than colour alone.
- Progress uses `aria-busy` and a polite live region.
- Errors use an assertive alert; successful feedback uses a polite status.
- Focus moves to the result or error summary after the request finishes.
- Controls use one column on small screens and three columns from the small breakpoint.
- Buttons retain the shared minimum interaction height and visible focus treatment.

## Security, privacy, and rights boundary

- The OpenAI API key remains in the FastAPI environment and is never placed in `NEXT_PUBLIC_` configuration.
- The HTTP-only session cookie is never read by browser JavaScript.
- The readable CSRF cookie is copied only to the required request header.
- No password, session ID, prompt, article body, or generated draft is written to browser storage.
- The article readiness state helps the interface, but FastAPI repeats current rights checks before every provider request.
- The interface never describes automated checks as factual verification.
- Nothing is automatically published to LinkedIn.
- Live CNN access remains disabled under ADR-001; current development uses synthetic fixtures.

## Main implementation files

| Path                                                     | Responsibility                                                                    |
| -------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `apps/web/components/generation/generation-controls.tsx` | Form state, validation, duplicate protection, submission, and controlled feedback |
| `apps/web/components/generation/tone-selector.tsx`       | Accessible supported-tone selection                                               |
| `apps/web/components/generation/length-selector.tsx`     | Accessible supported-length selection                                             |
| `apps/web/lib/generation-api.ts`                         | Browser request, CSRF proof, response validation, and safe failure mapping        |
| `apps/web/lib/generation-proxy.ts`                       | Narrow server-side FastAPI gateway and cookie allowlist                           |
| `apps/web/app/api/generations/route.ts`                  | Same-origin generation route                                                      |
| `apps/web/types/generation.ts`                           | Shared request types, response types, option lists, and runtime guards            |
| `apps/web/app/(workspace)/generate/page.tsx`             | Selected source and generation controls integration                               |

## Automated tests

Frontend tests cover:

- Professional and medium defaults.
- Exact supported option list.
- Tone and length selection in the submitted JSON request.
- Article UUID, CSRF header, cookies, and idempotency header handling.
- Missing and restricted article states.
- Synchronous duplicate submission protection and active loading state.
- Authentication recovery.
- Usage-limit message and retry lock.
- Success receipt, review reminder, and no automatic publishing.
- Focus movement, native labels, radio groups, and keyboard-compatible controls.
- Gateway header and cookie allowlists.
- Safe gateway failure and `Retry-After` forwarding.
- Create Post page integration for available and restricted sources.

Run from `apps/web`:

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

All tests use synthetic values and mocked network responses. They do not make a live OpenAI request, retrieve CNN content, use real credentials, or spend provider credits.

## Verification results

Verified locally on 1 November 2026:

- The focused NFA-60 component, gateway, and page-integration run passed 17 tests across 3 files.
- The complete frontend suite passed 72 tests across 16 files.
- The existing FastAPI generation endpoint suites passed 33 tests, confirming the frontend request contract remains aligned.
- Ruff passed for the FastAPI generation models, route, and shared HTTP boundary.
- ESLint passed.
- Prettier validation passed.
- TypeScript validation passed.
- The Next.js production build completed and generated `/api/generations` as a dynamic route.
- The local Next.js server returned HTTP 200 for the public login page.
- No automated test contacted OpenAI or CNN, used a real secret, or published content.
- The native browser automation surface was unavailable in this workspace session, so the responsive browser review remains a manual acceptance step.

## Manual verification

1. Start PostgreSQL, FastAPI, and Next.js.
2. Sign in and select an available synthetic article from `/dashboard`.
3. Confirm Professional and Medium are selected by default.
4. Operate every tone, length, and Generate control using only the keyboard.
5. Submit one request and confirm a processing state immediately disables another request.
6. Confirm a successful request is described as a private draft requiring human review.
7. Confirm the interface does not claim that content was published or factually verified.
8. Review authentication, restricted-source, invalid-source, usage-limit, and unavailable states.
9. Repeat at mobile, tablet, and desktop widths.

## Limitations and next steps

- NFA-60 implements preference selection and the generation request boundary. A later task owns the complete editable draft presentation and content actions.
- A valid local OpenAI configuration is required to generate a real development draft; automated tests use a provider double.
- The frontend prevents accidental duplicates, but FastAPI remains responsible for distributed usage and duplicate enforcement.
- Automated browser and responsive inspection supplements, but does not replace, the component and production-build checks.
