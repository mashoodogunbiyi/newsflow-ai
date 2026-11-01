# NFA-59 - Article Selection and Source Information Panel

## Purpose

NFA-59 connects the authorised article dashboard to the Create Post journey. A signed-in user selects an article, NewsFlow AI preserves only its stable identifier in the URL, FastAPI retrieves the current permitted detail, and the interface presents a source panel before any generation setup begins.

This workflow keeps the future LinkedIn draft visibly connected to its source. It does not make a live CNN request, expose restricted article text, or treat a frontend permission state as final authorisation.

## Selection flow

```text
Authorised dashboard card
    |
    | Select article
    v
/generate?articleId=<UUID>
    |
    v
Next.js validates the identifier
    |
    v
GET /api/articles/{article_id}
    |
    v
FastAPI applies authentication, display, rights, and retention rules
    |
    v
Responsive source panel or a controlled recovery state
```

Only the article UUID appears in the URL. Titles, summaries, source URLs, attribution, permission flags, and restricted content are never placed in query parameters.

The selection remains available through refresh, browser history, and links within the current creation route because the UUID remains in `articleId`.

## Detail API contract

The protected endpoint is:

```text
GET /api/articles/{article_id}
```

Example synthetic response:

```json
{
  "id": "10000000-0000-4000-8000-000000000003",
  "title": "Synthetic company announces an energy-efficient data platform",
  "description": "A fictional technology company announced a test platform.",
  "source_url": "https://example.invalid/newsflow-ai/fixture-technology-001",
  "provider": "fixture-v1",
  "published_at": "2026-10-12T09:00:00Z",
  "category": "Technology",
  "attribution": {
    "display_name": "NewsFlow AI synthetic fixture",
    "text": "Source: NewsFlow AI synthetic fixture - not live news",
    "byline": null,
    "copyright_notice": null
  },
  "generation": {
    "allowed": true,
    "status": "available"
  }
}
```

The `generation` object is a safe current readiness summary:

| Status                            | Meaning                                                                         | Frontend behaviour                                                        |
| --------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `available`                       | Current rights and permitted grounding information allow the source to continue | Enable the Continue with this source link                                 |
| `restricted`                      | Current rights or source-level permissions deny AI derivative generation        | Disable continuation and ask the user to choose another article           |
| `insufficient_source_information` | The metadata can be displayed, but authorised grounding information is missing  | Disable continuation and explain that more source information is required |

`allowed` is true only for `available`. Pydantic and the TypeScript runtime validator reject contradictory combinations.

## Backend decision

The detail endpoint returns an article only when its current record is active and displayable, its source is enabled, its rights are verified and effective, retention has not expired, and required attribution is complete.

Generation is available only when all of the following are true:

- The current rights version permits AI processing.
- The current rights version permits derivative output.
- The current article snapshot permits AI processing.
- The current article snapshot permits derivative output.
- Permitted grounding content has an `available` status and a non-empty value.

The grounding content is used only to calculate readiness. Its text is not returned by the article detail endpoint or displayed in the source panel.

The generation API remains authoritative. It repeats current display and AI-use checks, rebuilds the permitted source package, and refuses generation when rights or source information have changed since the panel was rendered.

## Source panel

The panel displays only the public article contract:

- Article title.
- Approved source display name and provider profile.
- Publication date.
- Category.
- Permitted summary when available.
- Canonical HTTPS source URL.
- Required attribution, optional byline, and optional copyright notice.
- Safe generation availability.
- A reminder that every AI result requires human comparison with the original source.

The original-source link opens in a new tab with `rel="noopener noreferrer"`. All source values are rendered as React text. The interface does not use `dangerouslySetInnerHTML`.

## Controlled states

| Condition                                 | Behaviour                                                             |
| ----------------------------------------- | --------------------------------------------------------------------- |
| No `articleId`                            | Ask the user to choose an authorised article                          |
| Duplicate `articleId` parameters          | Reject the link without calling FastAPI                               |
| Invalid UUID                              | Reject the selection before a network request                         |
| Missing, expired, or inaccessible article | Show one non-disclosing unavailable state and return to the catalogue |
| Invalid or unsafe API response            | Show a controlled service-unavailable state                           |
| Authentication rejected                   | Redirect to login                                                     |
| Restricted generation                     | Display permitted metadata but disable continuation                   |
| Insufficient grounding                    | Explain the limitation without inventing article details              |

Missing and non-disclosable backend records both return HTTP 404. This prevents the interface from confirming that restricted records exist.

## Responsive and accessible behaviour

- The source panel uses semantic `article`, `section`, `aside`, `dl`, `dt`, `dd`, and `time` elements.
- Panel headings are connected through `aria-labelledby`.
- Source metadata uses one column on small screens, two from the small breakpoint, and four on wide screens.
- Long UUIDs and source URLs wrap instead of forcing horizontal scrolling.
- Links and controls keep the shared 44-pixel minimum interaction height and visible focus treatment.
- Restricted continuation is a real disabled button rather than a colour-only indication.
- Loading and error states expose meaningful assistive-technology labels.

## Main implementation files

| Path                                                 | Responsibility                                                   |
| ---------------------------------------------------- | ---------------------------------------------------------------- |
| `apps/api/app/models/article_catalogue.py`           | Public detail and safe generation-availability schemas           |
| `apps/api/app/repositories/article_catalogue.py`     | Current display and generation evidence from PostgreSQL          |
| `apps/api/app/services/article_catalogue.py`         | Fail-closed readiness decision and public response construction  |
| `apps/api/app/api/routes/articles.py`                | Authenticated detail endpoint and safe errors                    |
| `apps/web/components/articles/article-selection.tsx` | Reusable article selection link carrying only the UUID           |
| `apps/web/components/articles/source-panel.tsx`      | Responsive source information and availability panel             |
| `apps/web/app/(workspace)/generate/page.tsx`         | Selection restoration, detail retrieval, and controlled states   |
| `apps/web/lib/article-api.ts`                        | Server-only authenticated detail request and response validation |
| `apps/web/types/article.ts`                          | Runtime-validated public detail contract                         |

## Automated tests

Backend tests cover:

- Available generation details.
- Restricted generation details.
- Insufficient source details.
- Omission of permitted content and confidential rights fields.
- Missing and inaccessible records.
- Authentication, safe errors, and OpenAPI documentation.
- Real PostgreSQL detail readiness in the safety-gated catalogue integration suite.

Frontend tests cover:

- UUID-only selection URLs.
- Authenticated detail retrieval.
- Invalid, missing, unavailable, and malformed responses.
- Title, provider, date, category, summary, source link, and attribution rendering.
- Available, restricted, and insufficient states.
- Disabled restricted continuation.
- HTML-like source values rendered as text.
- Responsive metadata layout and selection restoration.

Run from `apps/api`:

```bash
ruff check .
ruff format --check .
pytest tests/test_article_catalogue.py
```

Run from `apps/web`:

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

## Verification results

Verified locally on 1 November 2026:

- Backend linting and formatting passed.
- The normal backend suite passed 417 tests, skipped 13 safety-gated tests, and deselected the optional live-model test.
- Backend coverage measured 81.15 percent, above the enforced 75 percent floor.
- All 59 frontend tests passed across 14 test files.
- Frontend ESLint, Prettier, generated route types, TypeScript, and the Next.js production build passed.
- The NFA-59 PostgreSQL catalogue test remains safety-gated for a disposable database and is configured to run in GitHub Actions.
- No test used live CNN content, a live OpenAI request, real user information, or production credentials.
- Automated browser control was unavailable in the local workspace session, so the manual responsive review below remains part of acceptance.

## Manual verification

1. Start PostgreSQL, FastAPI, and Next.js.
2. Sign in and open `/dashboard`.
3. Select one synthetic article.
4. Confirm the URL contains only `articleId=<UUID>` for the selected source.
5. Confirm the panel shows the permitted source fields and attribution.
6. Open the original synthetic source and confirm the new tab is protected.
7. Refresh the page and use browser back and forward to confirm the selection behaves predictably.
8. Review an available, restricted, insufficient, missing, and invalid source state.
9. Test the workflow on mobile, tablet, and desktop widths using keyboard navigation.

## Rights and limitations

- Live CNN access remains disabled under ADR-001.
- Current development records are synthetic fixtures.
- A safe availability response is a user-interface aid, not an authorisation token.
- FastAPI must repeat current rights, source, and grounding checks before every generation request.
- NFA-59 prepares the selected source state. Later creation tasks add tone, length, generation, editing, and saving controls.
- Human browser and responsive review remains part of final acceptance.
