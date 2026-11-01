# NFA-57 - Authorised Article Discovery Dashboard

## Purpose

NFA-57 connects the protected Next.js dashboard to the authenticated article catalogue created in NFA-34. Signed-in users can browse permitted article metadata, search by topic, choose publication order, follow the original source, and select an article as the starting point for LinkedIn content creation.

The dashboard does not retrieve live CNN information. It displays the approved synthetic development catalogue while ADR-001 blocks live CNN access.

## Plain-language flow

```text
Signed-in user
    |
    v
Protected Next.js dashboard
    |
    v
Server-side article API client
    |
    v
Authenticated FastAPI GET /api/articles
    |
    v
Rights-approved PostgreSQL article metadata
```

The browser never receives or reads the HTTP-only session identifier. The Next.js server reads the session cookie for the current request and forwards it only to FastAPI. FastAPI remains responsible for authentication, rights filtering, and the public response contract.

## Dashboard data requirements

The frontend accepts only the NFA-34 public article fields:

| Field | Frontend use |
|---|---|
| `id` | Stable selection value passed to the Create Post route |
| `title` | Article-card headline |
| `description` | Optional permitted summary |
| `source_url` | HTTPS link to the original source |
| `provider` | Approved source-profile label |
| `published_at` | UTC publication date |
| `category` | Optional topic label |
| `attribution.display_name` | Visible source name |
| `attribution.text` | Required source wording |
| `attribution.byline` | Optional byline |
| `attribution.copyright_notice` | Optional copyright notice |

Internal rights records, stored permitted-content text, provider credentials, snapshot identifiers, fingerprints, and database identifiers are not dashboard data.

## Rendering and rights rules

- React renders all article values as text. The interface never uses `dangerouslySetInnerHTML` for source data.
- The runtime response guard accepts only HTTPS source URLs and the documented public schema.
- A missing permitted summary produces an honest unavailable message and never invented content.
- Source attribution remains visible on every article card.
- Original-source links open in a new tab with `noopener noreferrer` protection and an article-specific accessible label.
- The interface explicitly identifies fixture mode and does not imply CNN supplied or approved the records.
- Selecting an article sends only its stable identifier to `/generate`; FastAPI must repeat all rights and authorisation checks before generation.

## Pagination and request behaviour

The dashboard requests nine records at a time from:

```text
GET /api/articles?limit=9&sort=newest
```

Search, publication order, and the opaque continuation cursor are added only when present. The frontend never edits or interprets a cursor. `Next articles` sends the returned cursor to the next server render, while `First page` clears it.

Article data uses `cache: no-store` because it is authenticated and rights-sensitive. One server fetch supplies each rendered page. Pagination links set `prefetch={false}` so Next.js does not make an unnecessary protected catalogue request before the user chooses to continue.

## Interface states

### Loading

The dashboard route and its article section provide responsive skeleton cards with `aria-busy` and a screen-reader loading label. Reduced-motion preferences disable skeleton animation.

### Empty

An empty catalogue explains that no articles are available. A search with no matches offers a clear-search action. Neither state claims that live CNN content exists.

### Error

Authentication rejection redirects to login. Invalid cursors and filters produce a controlled recovery state. Backend, network, or malformed-response failures display a generic retry action without exposing internal errors or article data.

## Responsive and accessible behaviour

- Cards use one column on small screens, two columns from the medium breakpoint, and three columns on wide screens.
- Search controls and pagination stack on narrow screens and become horizontal when space permits.
- Buttons and links meet the shared 44-pixel minimum interaction height.
- Form controls have visible labels and focus styles.
- Article publication values use semantic `time` elements.
- The catalogue and pagination use semantic list, section, article, and navigation structures.
- Loading, empty, and error states remain understandable without colour or animation.

## Main implementation files

| Path | Responsibility |
|---|---|
| `apps/web/app/(workspace)/dashboard/page.tsx` | Dashboard, controls, server fetch orchestration, states, and pagination |
| `apps/web/app/(workspace)/dashboard/loading.tsx` | Route-level loading interface |
| `apps/web/components/articles/article-catalogue.tsx` | Controls, server fetch orchestration, states, and pagination |
| `apps/web/components/articles/article-card.tsx` | Reusable permitted article presentation and actions |
| `apps/web/components/articles/article-grid.tsx` | Responsive article layout |
| `apps/web/components/articles/article-dashboard-skeleton.tsx` | Accessible loading skeleton |
| `apps/web/components/articles/article-empty-state.tsx` | Empty and no-match states |
| `apps/web/components/articles/article-error-state.tsx` | Retry and invalid-link recovery |
| `apps/web/lib/article-api.ts` | Server-only authenticated catalogue request and safe failure mapping |
| `apps/web/types/article.ts` | Public TypeScript contract and runtime response validation |

## Automated tests

Run the frontend checks from `apps/web`:

```bash
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

The focused tests cover:

- Successful authenticated API retrieval with the correct query.
- Missing and rejected sessions.
- Invalid filters, unavailable services, and malformed responses.
- Approved article fields and required attribution.
- Missing summaries and categories.
- Safe external-source link attributes.
- HTML-like titles rendered as text.
- Responsive grid breakpoints.
- Empty, error, retry, and redirect states.
- Cursor propagation for the next page.

All tests use synthetic records and mocked network responses. They make no live CNN or OpenAI request.

## Verification completed

Verified on 1 November 2026:

- Prettier formatting check passed.
- ESLint passed.
- TypeScript strict checking passed.
- All 10 frontend test files passed with 41 tests and no failures.
- The Next.js production build passed.
- The build classified `/dashboard` as a dynamic server-rendered route.
- No live CNN, OpenAI, or other external-provider request was made.

The native browser-preview connection was unavailable during implementation. Responsive classes, semantic markup, interaction states, and component behaviour are covered automatically; the manual width review below remains the human acceptance step before Jira completion.

## Manual verification

With PostgreSQL, FastAPI, and Next.js running:

1. Sign in with a local development account.
2. Open `http://localhost:3000/dashboard`.
3. Confirm the fixture-mode notice and source attribution are visible.
4. Search for a permitted fixture topic and change publication order.
5. Open the original synthetic source and confirm it uses a new tab.
6. Select an article and confirm its identifier reaches the Create Post route.
7. Test narrow mobile, tablet, and desktop widths.
8. Stop FastAPI temporarily and confirm the controlled retry state appears.

## Limitations

- The dashboard uses synthetic fixture records until written authorisation replaces ADR-001.
- Cursor pagination supports forward navigation and returning to the first page. Browser history provides the previous-page journey.
- Article selection prepares the `/generate` route. The dedicated generation-interface task completes the remaining creation experience.
- Automated layout tests verify responsive classes and behaviour, but a human visual review remains part of acceptance.
