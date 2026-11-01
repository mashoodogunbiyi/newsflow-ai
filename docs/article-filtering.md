# NFA-58 - Article Filtering and Browsing State

## Purpose

NFA-58 lets signed-in users narrow the authorised article catalogue by an approved category without losing predictable browsing behaviour. Category, search, sorting, and pagination are represented in the dashboard URL, so refreshes and browser back and forward navigation restore the same view.

Filtering happens in PostgreSQL before pagination. The frontend never filters only the nine records already loaded and never presents a partial page as the complete category result.

## Supported browsing parameters

| URL parameter | Values | Behaviour |
|---|---|---|
| `category` | `technology`, `business`, `world_news`, `science`, `other` | Exact approved category filter |
| `search` | 1 to 200 characters | Permitted title and description search |
| `sort` | `newest` or `oldest` | Stable publication order |
| `cursor` | Opaque backend value | Continues the current filter and sort state |

The supported category identifiers come from the approved NFA-6 source data contract. Display labels are configuration, not user-supplied values:

| Identifier | Label |
|---|---|
| `technology` | Technology |
| `business` | Business |
| `world_news` | World News |
| `science` | Science |
| `other` | Other |

Unknown, duplicated, or manipulated category values are not trusted. A blank value intentionally represents All categories. The frontend accepts only one configured identifier, and FastAPI independently validates the enum before PostgreSQL is queried.

## Request flow

```text
Category selection
    |
    v
GET /dashboard?category=technology
    |
    v
Next.js validates URL browsing state
    |
    v
GET /api/articles?limit=9&sort=newest&category=technology
    |
    v
FastAPI validates category and session
    |
    v
PostgreSQL applies rights and category filters before pagination
```

The backend still applies every NFA-34 visibility rule. A category never bypasses authentication, source status, display permission, rights verification, attribution, or retention requirements.

## URL as the browsing-state source

The dashboard uses a native GET form. Search, category, and sorting controls are submitted to `/dashboard`, making the resulting URL shareable and restorable.

This approach provides:

- Refresh persistence because the state is in the URL.
- Browser back and forward support because every submitted filter state is a navigation entry.
- Server-rendered results without duplicating protected article state in browser storage.
- Keyboard operation through native labelled form controls.
- One FastAPI catalogue request for each server render.

No article filter or session value is stored in `localStorage` or `sessionStorage`.

## Pagination policy

The continuation cursor is valid only for the search, category, provider, date, and sort state that created it. FastAPI includes all those values in the cursor fingerprint.

When a user submits a changed category, search, or sort value, the filter form deliberately does not submit the current cursor. The next request therefore begins at the first page of the new result set.

`Next articles` preserves category, search, and sort and adds the opaque cursor. `First page` preserves the active filters but removes the cursor. Changing filters while manually retaining an old cursor is rejected with HTTP 422.

Pagination links keep `prefetch={false}`. This prevents Next.js from making an unnecessary authenticated catalogue request before the user chooses to continue.

## Empty and invalid states

- A valid category with no results displays `No articles found in [Category].`
- The empty state provides a clear-category link while preserving search and sort.
- Selecting `All categories` removes the category parameter on the next form submission.
- An unsupported category produces the controlled invalid-link state without calling FastAPI from the frontend.
- Direct requests with an unsupported category receive HTTP 422 from FastAPI.
- Backend or network failures reuse the NFA-57 controlled retry state.

## Accessibility and responsive behaviour

- The filter uses a native `select` with a visible `Category` label.
- The current selection is communicated by the selected option and URL.
- The native form remains usable with keyboard and assistive technology without custom key handling.
- Controls stack on small screens, use two columns on intermediate screens, and align in one row on wide screens.
- Focus styling and the shared 44-pixel minimum control height remain visible.
- Empty and error states do not depend on colour alone.

## Main implementation files

| Path | Responsibility |
|---|---|
| `apps/api/app/models/article_catalogue.py` | Stable category enum and request validation |
| `apps/api/app/repositories/article_catalogue.py` | PostgreSQL category predicate before pagination |
| `apps/api/app/services/article_catalogue.py` | Validated category forwarding and cursor fingerprinting |
| `apps/web/components/articles/category-filter.tsx` | Native accessible category selector |
| `apps/web/components/articles/article-catalogue.tsx` | URL-state parsing, pagination coordination, and empty states |
| `apps/web/lib/article-api.ts` | Category allowlist and FastAPI query construction |
| `apps/web/types/article.ts` | Stable category identifiers and labels |

## Automated tests

Backend tests cover:

- Approved category validation and normalisation.
- Repository filter forwarding.
- Invalid category rejection.
- Cursor rejection when the category changes.
- OpenAPI parameter documentation.
- PostgreSQL category filtering before pagination.

Frontend tests cover:

- Approved category options and labels.
- Native select keyboard focus and selection.
- Category restoration from URL parameters.
- One filtered API request per render.
- Category preservation across pagination.
- Search and sort preservation when category is cleared.
- Cursor removal when filters are submitted.
- Empty-category results.
- Invalid category handling without an API request.
- Duplicated category-parameter rejection without an API request.

Run the focused backend test from `apps/api`:

```bash
pytest tests/test_article_catalogue.py
```

Run the frontend quality checks from `apps/web`:

```bash
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

The PostgreSQL integration remains opt-in and accepts only the dedicated disposable `newsflow_article_catalogue_test` database described in `docs/article-catalogue-api.md`.

## Verification results

Verified locally on 1 November 2026:

- Backend Ruff linting and formatting passed.
- The focused backend article-catalogue suite passed 10 tests.
- The normal backend suite passed 416 tests, skipped 13 safety-gated PostgreSQL tests, and reached 81.08 percent branch-aware coverage.
- Frontend ESLint, Prettier, route type generation, and TypeScript checks passed.
- All 47 frontend tests passed across 11 files.
- The Next.js production build passed.
- The dedicated PostgreSQL category-filtering test is configured to run in GitHub Actions against `newsflow_article_catalogue_test` after the branch is pushed.
- The native browser-preview connection was unavailable, so the manual responsive and browser-history review remains the human acceptance step.

## Manual verification

1. Sign in and open `/dashboard`.
2. Select Technology and submit the filter form.
3. Confirm the URL contains `category=technology` and only technology records appear.
4. Change search and sort, then continue to another page if available.
5. Change category and confirm the cursor is removed.
6. Use browser back and forward and confirm earlier selections return.
7. Select All categories and confirm the category parameter is removed.
8. Test the controls at mobile, tablet, and desktop widths using only the keyboard.

## Rights and limitations

- Filtering does not change which article fields may be disclosed.
- Returned data is still validated and rendered as plain text.
- Live CNN access remains disabled under ADR-001.
- Categories come from the approved source contract and synthetic fixture catalogue.
- A human visual and browser-history review remains part of final acceptance.
