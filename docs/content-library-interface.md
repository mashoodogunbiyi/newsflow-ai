# NFA-69 - Frontend Content Library

## Outcome

Authenticated NewsFlow AI users can now browse their private saved LinkedIn drafts, inspect useful metadata, move through bounded result pages, and reopen one saved record in the existing editor with its source and selected illustration restored.

The interface consumes the NFA-68 REST contract. FastAPI remains responsible for authentication and object-level authorisation.

## Routes

| Frontend route | Purpose |
| --- | --- |
| `/library` | Display one paginated page of the active user's saved drafts. |
| `/library?page={number}` | Restore a specific library page through the URL. |
| `/library/{saved_draft_id}` | Retrieve and reopen one owned saved draft. |

Both routes remain inside the authenticated workspace layout. Requests without a valid session are redirected to the login page.

## Backend integration

The server-rendered Next.js pages use:

```text
GET /api/v1/drafts?page={number}&page_size=6
GET /api/v1/drafts/{saved_draft_id}
```

Next.js reads the HTTP-only session cookie on the server and forwards only that cookie to FastAPI. It does not expose the session value to browser JavaScript. Requests use `cache: "no-store"` so one user's private library is not reused for another request.

Every backend response is runtime-validated before rendering. Validation covers:

- UUIDs and timestamps.
- Supported tone and length values.
- Saved status and positive version number.
- HTTPS source URLs and bounded source fields.
- Approved image media types, positive dimensions, and AI-designation fields.
- Collection page, page size, totals, stable sort identifier, and total-page consistency.

Malformed or unexpected backend data produces the same safe unavailable state as a temporary service failure.

## Library cards

Each reusable card displays:

- The private title, falling back to the source title when no private title exists.
- A bounded plain-text excerpt from the reviewed draft.
- Saved status and current optimistic version.
- Original source title and required attribution.
- Last-modified date and time in UTC.
- A selected private illustration thumbnail, or a text-only fallback.
- An `Open draft` link and a separate original-source link.

Thumbnail bytes continue to use the existing same-origin `/api/images/{image_id}/content` gateway. That gateway forwards the session to NFA-53's owner-scoped image endpoint. The page never receives a storage key, filesystem path, credential, or unrestricted private image URL.

## Pagination

The content library requests 6 drafts per page. The `page` search parameter is the URL source of truth, so browser refresh, back, forward, and copied links restore the requested page.

Only one positive safe integer is accepted. Duplicate, zero, negative, decimal, or otherwise invalid page values are rejected without requesting FastAPI. Previous and next links are shown only when the backend totals permit them. A page that becomes empty after records change returns safe recovery to the first library page.

The backend's fixed `updated_at_desc` order remains authoritative. The frontend does not download the entire library or perform its own pagination.

## Reopening a draft

Selecting `Open draft` carries only the saved-draft UUID in the path. The detail route then asks FastAPI for the owned record. FastAPI returns the same not-found response when the UUID is missing, deleted, or belongs to another user.

After a valid response, the interface restores:

- The exact current saved text into the multiline editor.
- The original article title, attribution, and source URL.
- The selected private image through the authenticated delivery route.
- The draft length, generation reference, saved title, version, and last-modified time.

The reused editor keeps the source and human-review guidance visible, renders user text literally, synchronises the preview, and warns before navigation would discard new local edits.

NFA-69 does not add another update endpoint or automatically save editor keystrokes. New edits made after reopening remain local until the separate frontend update controls are implemented. Nothing is automatically published to LinkedIn.

## Controlled states

| State | Interface behaviour |
| --- | --- |
| Loading list | Route-level responsive skeleton with an accessible loading label. |
| Loading detail | Route-level editor skeleton with an accessible loading label. |
| Empty library | Clear explanation and a link to browse authorised articles. |
| API unavailable | Safe message and a retry action that refreshes the route. |
| Invalid page or UUID | Safe message and a return-to-library action. |
| Missing, deleted, or differently owned draft | One indistinguishable not-found message without private details. |
| Missing image | Text-only thumbnail and preview remain usable. |
| Failed image delivery | Controlled unavailable fallback without affecting the draft text. |
| Expired session | Redirect to login with the authentication-required reason. |

## Responsive and accessible behaviour

- Cards use one column on small screens, two on medium screens, and three on wide screens.
- Actions stack on narrow cards and become horizontal when space permits.
- Native links, headings, sections, navigation landmarks, time elements, and labels preserve semantics.
- Every required action is reachable with a keyboard and receives the project's shared visible focus treatment.
- Private images have meaningful alt text or a controlled fallback.
- Loading and error states expose suitable busy, status, or alert semantics.
- Motion-based loading feedback respects `prefers-reduced-motion`.
- The dynamic route uses the Next.js 16 asynchronous `params` contract and route-level loading boundary.

## Verification

Run the focused NFA-69 tests from `apps/web`:

```bash
npm test -- --run \
  __tests__/draft-api.test.ts \
  __tests__/content-library.test.tsx \
  __tests__/saved-draft-page.test.tsx
```

The 14 focused tests cover:

- Authenticated list and detail requests using the real API paths.
- No request without a session or with invalid client parameters.
- Runtime rejection of unsafe image metadata and malformed responses.
- Saved metadata, source, excerpt, status, date, and secure thumbnail rendering.
- Empty, unavailable, invalid, missing, and authentication-required states.
- Backend pagination and URL restoration.
- Keyboard focus and responsive layout classes.
- Reopening the exact saved text, source attribution, and selected image.
- Continuing local editing with synchronised preview and unsaved-change status.

The complete local NFA-69 verification produced:

- 14 focused tests passed across 3 files.
- 143 frontend tests passed across 29 files.
- ESLint passed.
- Prettier formatting verification passed.
- Strict TypeScript checking passed.
- The Next.js 16 production build passed and generated both `/library` and `/library/[draftId]`.

No test used live CNN content, a live OpenAI request, real user data, or production credentials.

## Limitations and next steps

- Saving the current editor text was implemented in the backend by NFA-67 and NFA-68, but its frontend save and conflict-resolution controls remain a separate E7 task.
- Search, filtering, deletion, restore, copy, and export are not part of NFA-69.
- A final human browser review at the supported mobile, tablet, and desktop widths remains appropriate before release.
- Live CNN integration remains blocked by ADR-001 until explicit authorisation and a Go decision exist.
