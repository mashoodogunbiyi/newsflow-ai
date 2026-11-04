# NewsFlow AI Frontend

The NewsFlow AI frontend is a Next.js, React, TypeScript, and Tailwind CSS application. It is located in `apps/web` and provides the user-facing layer of the project. NFA-17 adds automated linting, formatting, type checking, and component testing. NFA-24 adds the complete frontend authentication experience. NFA-56 adds the reusable authenticated application shell, responsive navigation, primary routes, shared interface components, and protected loading and error states. NFA-57 adds the responsive authorised-article dashboard and FastAPI catalogue integration. NFA-58 adds approved category filtering and URL-based browsing state. NFA-59 adds UUID-only article selection, protected detail retrieval, and the responsive source information panel. NFA-60 adds accessible tone and length controls, the same-origin generation gateway, duplicate protection, safe response validation, and controlled request feedback. NFA-61 adds a reusable text and image generation lifecycle, deliberate retries, accessible announcements, and stale-response protection. NFA-62 adds the accessible multiline draft editor, source and warning preservation, and local unsaved-change protection. NFA-63 adds the responsive LinkedIn-inspired text and image preview, owner-protected image gateway, AI designation, controlled fallbacks, and preview limitations. NFA-64 adds supported illustration preferences, secure initial generation and regeneration gateways, immutable version selection, and live preview updates. NFA-65 adds the responsive and accessibility review, consistent focus behaviour, reviewed contrast, reduced-motion support, overflow protection, axe checks, and final manual acceptance checklist. NFA-69 adds the authenticated personal content library, runtime-validated draft API integration, responsive saved-draft cards, backend pagination, secure thumbnails, and saved-draft reopening in the editor. NFA-77 adds the generated-draft save action and deterministic Playwright journeys across authentication, articles, mocked generation, editing, private saving, export, deletion, empty states, provider errors, and ownership denial.

The application contains a responsive homepage, registration and login pages, a protected workspace, session restoration, and logout. The workspace includes Dashboard, Create Post, Content Library, and Account routes. The dashboard retrieves rights-approved synthetic article metadata from FastAPI and does not retrieve live CNN information. The Create Post route restores the selected article from its UUID, presents permitted source information and current generation readiness, lets an authorised user request a private LinkedIn draft using supported tone and length choices, and opens a responsive editor after a valid result. The editor keeps text editable while the user generates a private illustration, creates immutable alternatives, selects the version displayed in the combined preview, and saves the reviewed result through the authenticated E7 API. The Content Library lists only the authenticated user's saved drafts, restores URL-based pages, and reopens one saved record with its source and selected image. It never receives an OpenAI credential or publishes automatically.

The E6 implementation must follow the [generation frontend integration contract](../../docs/e6-generation-integration-contract.md), including same-origin gateway, session and CSRF behaviour, request and response types, safe errors, mandatory human review, source presentation, accessibility, and no automatic LinkedIn publishing.

## Requirements

- Node.js 20.19 or later.
- npm 11 or a compatible npm release.

## Local development

From the repository root:

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in a browser. FastAPI and PostgreSQL must also be running for the account pages to complete authentication requests.

## Run with Docker Compose

NFA-16 adds a frontend development image and runs it with FastAPI and PostgreSQL from the repository-root `compose.yaml` file. From the repository root:

```bash
cp .env.example .env
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). The browser sends authentication requests to same-origin Next.js route handlers. Those server-side handlers use `API_INTERNAL_BASE_URL` to reach FastAPI at `http://backend:8000` inside Docker. Use `docker compose down` for a normal shutdown. See the [complete Docker development guide](../../infrastructure/docker/README.md) for all commands and service checks.

## Authentication journey

| Route                              | Purpose                                                                                         | Access                   |
| ---------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------ |
| `/register`                        | Validates account details and creates an account through FastAPI.                               | Public                   |
| `/login`                           | Verifies credentials and starts a secure session.                                               | Public                   |
| `/dashboard`                       | Displays the searchable, category-filtered, paginated, rights-approved article catalogue.       | Authenticated users only |
| `/generate`                        | Reviews a selected source and submits validated LinkedIn draft preferences.                     | Authenticated users only |
| `/library`                         | Lists the active user's saved drafts with secure thumbnails and backend pagination.             | Authenticated users only |
| `/library/[draftId]`               | Reopens one owned draft with its source and selected image in the editor.                       | Authenticated users only |
| `/account`                         | Displays account security and ownership information.                                            | Authenticated users only |
| `/api/auth/[action]`               | Same-origin server gateway for the FastAPI register, login, logout, and current-user endpoints. | Internal frontend route  |
| `/api/generations`                 | Same-origin gateway for CSRF-protected private LinkedIn draft requests.                         | Internal frontend route  |
| `/api/drafts`                      | Same-origin gateway for CSRF-protected creation of reviewed saved drafts.                       | Internal frontend route  |
| `/api/images`                      | Same-origin gateway for CSRF-protected initial image generation.                                | Internal frontend route  |
| `/api/images/[imageId]/regenerate` | Same-origin gateway for immutable owner-scoped image alternatives.                              | Internal frontend route  |
| `/api/images/[imageId]/content`    | Same-origin gateway for owner-protected generated-image preview bytes.                          | Internal frontend route  |

The workspace is protected in two layers. `proxy.ts` quickly redirects requests that have no session cookie. The shared server layout then asks FastAPI to validate any presented session before returning account content. FastAPI remains the authority for identity and access control.

Logout reads the separate, non-secret CSRF cookie and submits it in the required `X-CSRF-Token` header. The secure session identifier remains in an HTTP-only cookie and is not accessible to client-side JavaScript. The frontend does not put passwords, session identifiers, or account secrets in `localStorage` or `sessionStorage`.

## Quality checks

NFA-17 uses ESLint with the Next.js Core Web Vitals and TypeScript rules, Prettier for formatting, TypeScript for static type checking, and Vitest with React Testing Library and jsdom for component tests.

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run test:e2e
npm run build
```

To apply Prettier formatting instead of checking it:

```bash
npm run format
```

For a test watcher during development:

```bash
npm run test:watch
```

Vitest covers the homepage, authentication, route protection, reusable components, article contracts, generation states, editing, private image gateways, saving, the content library, export, deletion, accessibility, and responsive layout contracts. Playwright runs the real Next.js application in Chromium against a deterministic local FastAPI contract mock and completes the joined user journeys. The tests use synthetic values and mocked provider responses, so they make no live CNN, OpenAI, LinkedIn, production-account, or paid API call. See the [NFA-77 integration and end-to-end testing guide](../../docs/integration-e2e-testing.md).

To serve the production build locally after a successful build:

```bash
npm run start
```

## Project structure

```text
apps/web/
├── .dockerignore          # Files excluded from the image build context
├── .prettierignore        # Files excluded from formatting checks
├── Dockerfile             # Next.js development image
├── __tests__/              # Homepage, authentication, article, selection, and generation tests
├── e2e/                    # Playwright browser journeys and deterministic API fixture server
├── app/
│   ├── api/                  # Same-origin FastAPI authentication, generation, and image gateways
│   ├── (workspace)/          # Shared protected layout, boundaries, dashboard, and application routes
│   ├── login/               # Login page
│   ├── register/            # Registration page
│   ├── globals.css          # Tailwind import and global design tokens
│   ├── layout.tsx           # Root layout, fonts, and metadata
│   └── page.tsx             # Public homepage
├── components/
│   ├── auth/                # Reusable forms, page shell, and logout control
│   ├── articles/            # Article discovery, selection, source panel, and controlled states
│   ├── editor/              # Draft textarea, character count, warnings, and preview
│   ├── images/              # Image preferences, request states, and version selection
│   ├── generation/          # Tone, length, submission, and generation feedback controls
│   ├── library/             # Saved-draft cards, thumbnails, pagination, and controlled states
│   ├── layout/              # Application shell, navigation, page header, and auth fallback
│   ├── preview/             # Combined text, source, warning, and private image preview
│   ├── ui/                  # Buttons, inputs, cards, statuses, loading, and errors
│   ├── brand-mark.tsx       # Reusable project identity
│   ├── product-preview.tsx  # Fixture-mode product demonstration
│   └── workflow-step.tsx    # Reusable workflow item
├── hooks/                   # Reusable text and image generation lifecycle hooks
├── lib/                     # Authentication, article, and generation API utilities
├── types/                   # Runtime-validated frontend data contracts
├── public/                  # Static assets
├── proxy.ts                 # Optimistic protected-workspace cookie check
├── eslint.config.mjs        # Next.js and TypeScript linting
├── next.config.ts           # Next.js and Tailwind build configuration
├── package.json             # Frontend scripts and dependencies
├── package-lock.json        # Reproducible npm dependency versions
├── playwright.config.ts     # Browser projects, test servers, reports, and CI behaviour
├── postcss.config.mjs       # Tailwind CSS PostCSS integration
├── prettier.config.mjs      # Frontend formatting configuration
├── tsconfig.json            # Strict TypeScript configuration
└── vitest.config.mts        # Frontend unit-test configuration
```

Add future routes under `app`, shared interface elements under `components`, and framework-independent contracts or utilities under `lib`.

## NFA-56 layout conventions

- Add authenticated application routes inside `app/(workspace)` so the server session check and shell remain consistent.
- Keep public authentication and marketing routes outside that group.
- Use `PageHeader`, `Card`, `Button`, `Input`, `StatusBadge`, `LoadingState`, and `ErrorState` before introducing another visual pattern.
- Add primary navigation items only in `components/layout/app-navigation.tsx` so desktop and mobile remain aligned.
- Keep active navigation available to assistive technology with `aria-current="page"`.
- Never rely on the shell or proxy as the only authorisation control. FastAPI must authorise private data access.
- Keep unfinished functionality visibly disabled or described as upcoming rather than presenting placeholder interactions as complete.

The complete component, route, spacing, accessibility, and test conventions are documented in [the NFA-56 frontend layout guide](../../docs/frontend-layout.md).

## NFA-57 article dashboard conventions

- Fetch protected article data on the Next.js server and forward only the HTTP-only session cookie to FastAPI.
- Use the NFA-34 public schema from `types/article.ts`; do not introduce internal rights or database fields into frontend types.
- Render all external article values as React text and accept only validated HTTPS source URLs.
- Keep attribution visible on every card and do not invent a summary when no permitted description exists.
- Preserve opaque cursors unchanged and keep catalogue requests `no-store`.
- Disable Next.js prefetch on cursor pagination links to avoid unnecessary authenticated API requests.
- Keep fixture mode and the live CNN authorisation limitation visible.

The full data requirements, states, security rules, test approach, and manual verification steps are documented in [the NFA-57 article dashboard guide](../../docs/article-dashboard.md).

## NFA-58 article filtering conventions

- Use the approved category identifiers from `types/article.ts`; never build database filters from display labels.
- Keep category, search, ordering, and cursor state in the URL so refresh and browser navigation restore the view.
- Use the native GET filter form and omit the existing cursor when filters are submitted so changed filters restart at page one.
- Preserve the approved category, search, and ordering values in pagination links without altering the opaque backend cursor.
- Reject unsupported category values before the frontend calls FastAPI. FastAPI must independently validate every request.
- Apply category filtering in PostgreSQL before pagination; do not filter only the records loaded in the browser.
- Keep the category selector visibly labelled, keyboard operable, and responsive without custom browser storage.

The complete category contract, state flow, empty and invalid states, tests, and manual verification steps are documented in [the NFA-58 article filtering guide](../../docs/article-filtering.md).

## NFA-59 article selection conventions

- Carry only the stable article UUID in `/generate?articleId=...`; never place titles, summaries, URLs, rights evidence, or source content in the browser URL.
- Fetch the selected detail on the Next.js server with the HTTP-only session and `cache: no-store`.
- Render only the runtime-validated public detail contract and keep source values as React text.
- Preserve attribution and provide a protected external-source link with `noopener noreferrer`.
- Treat missing and non-disclosable articles as the same unavailable state.
- Use the backend availability state to guide the interface, but require FastAPI to repeat current rights and grounding checks before generation.
- Disable continuation for restricted or insufficient sources and never invent missing source information.

The complete selection flow, detail contract, generation states, controlled errors, tests, and manual review steps are documented in [the NFA-59 article selection guide](../../docs/article-selection.md).

## NFA-60 generation control conventions

- Use only the tone and length values exported from `types/generation.ts`; do not add a frontend-only option.
- Keep Professional and Medium as the documented defaults unless the backend contract is formally changed.
- Send the browser request through `/api/generations` with same-origin credentials, CSRF proof, and one idempotency key for the selected article and preferences.
- Forward only the allowlisted headers and authentication cookies from the Next.js route to FastAPI.
- Keep the synchronous request lock as well as the visible disabled loading state so rapid submissions cannot create a second request.
- Preserve user choices after controlled failures and respect a backend `Retry-After` delay.
- Validate every successful response at runtime before presenting it as a private draft receipt.
- Never place an OpenAI key, session identifier, prompt, source content, or generated draft in browser storage or logs.
- Keep FastAPI authoritative for authentication, rights, validation, limits, provider access, and persistence.
- Never automatically publish a generated result or describe automated checks as factual verification.

The exact request contract, state mapping, duplicate controls, accessibility rules, tests, and limitations are documented in [the NFA-60 LinkedIn generation controls guide](../../docs/linkedin-generation-controls.md).

## NFA-61 generation state conventions

- Use `useGeneration` for the shared lifecycle and `useTextGeneration` or `useImageGeneration` for operation-specific controls.
- Keep the supported states truthful: idle, submitting, processing, completed, and failed.
- Do not expose cancellation until FastAPI can confirm provider-side cancellation.
- Do not invent progress percentages, polling, or a background-job endpoint.
- Acquire the active-request lock before awaiting work so rapid clicks cannot start a duplicate operation.
- Use the request identifier and abort signal to stop an outdated result from replacing current state.
- Preserve the user's input after a controlled failure and retry only after an explicit user action.
- Do not retry authentication, permission, or validation failures as if they were temporary.
- Respect a valid `Retry-After` delay for usage limits.
- Use polite status announcements for progress and completion, and assertive alerts for failures.
- Keep FastAPI authoritative for authentication, rights, limits, idempotency, provider access, and persistence.

The complete model, transitions, failure and retry policy, stale-response design, accessibility behaviour, test coverage, and current cancellation limitation are documented in [the NFA-61 frontend generation states guide](../../docs/generation-states.md).

## NFA-62 draft editor conventions

- Pass only a runtime-validated generation response into the editor adapter.
- Use the controlled native textarea for multiline editing; do not add a rich-text dependency without an approved requirement.
- Keep source attribution and all backend validation warnings outside the editable text and visible after edits.
- Render preview content as React text with preserved line breaks; never use `dangerouslySetInnerHTML` for generated or edited content.
- Keep the current character count separate from the configured short, medium, or long word guidance.
- Do not claim the character count is LinkedIn's current platform limit.
- Keep normal rerenders from resetting edited text.
- When a newer result arrives after an edit, require the user to choose between the new result and their local changes.
- Warn before a reload, close, or normal same-tab link discards unsaved local edits.
- Do not add a non-functional Save action. Persistent saving and draft history belong to E7.
- Do not send local edits to FastAPI or OpenAI merely to update the preview.
- Keep the AI-assisted label, mandatory human-review language, and no-automatic-publishing boundary visible.

The full state model, overwrite protection, navigation warning, preview, security, accessibility, tests, and E7 boundary are documented in [the NFA-62 LinkedIn draft editor guide](../../docs/linkedin-draft-editor.md).

## NFA-63 content preview conventions

- Pass edited text as React text and preserve line breaks; never inject draft HTML.
- Keep source details and validation warnings outside the editable post text.
- Pass only a validated generated-image UUID and accessible alternative text into the preview.
- Request image bytes through `/api/images/[imageId]/content`; never expose storage keys, credentials, or public object URLs.
- Forward only the HTTP-only session cookie to the owner-protected FastAPI image endpoint.
- Accept only PNG, JPEG, and WebP responses and keep them private with no-store caching.
- Keep the draft and source usable when no image is selected or image delivery fails.
- Always label synthetic imagery as `AI-generated illustration` and not authentic news photography.
- Do not reproduce LinkedIn branding, fake engagement information, or publishing functionality.
- Explain that the planning preview can differ from LinkedIn's live rendering.

The complete data contract, secure delivery path, states, accessibility behaviour, tests, and limitations are documented in [the NFA-63 LinkedIn content preview guide](../../docs/linkedin-content-preview.md).

## NFA-64 image generation control conventions

- Use only the style, shape, and composition values exported from `types/image-generation.ts`.
- Link initial generation to the validated text-generation ID and let FastAPI resolve the private generated post for the authenticated owner.
- Send initial and regeneration requests through the same-origin image gateways with CSRF proof and idempotency keys.
- Preserve the edited draft and every earlier image while an alternative is generated or a request fails.
- Select exactly one image version for the live preview using native radio controls.
- Load image bytes only through the owner-protected content gateway and never expose storage keys or provider credentials.
- Keep the AI-generated and non-photographic designations visible.
- Reuse the NFA-61 lifecycle, duplicate lock, safe error categories, deliberate retry, and `Retry-After` handling.
- Keep FastAPI authoritative for ownership, rights, safety, rate limits, usage limits, provider access, validation, and storage.
- Do not persist the selected version or edited text until the E7 saved-content contract is implemented.

The complete user flow, API boundary, security controls, version behaviour, accessibility rules, tests, and limitations are documented in [the NFA-64 image generation controls guide](../../docs/image-generation-controls.md).

## NFA-65 responsive and accessibility conventions

- Use 375 px, 768 px, and 1440 px as the representative mobile, tablet, and desktop acceptance widths.
- Preserve fluid widths, `min-width: 0`, safe text wrapping, and responsive stacking so content does not force page-level horizontal scrolling.
- Keep a visible focus indicator on every interactive element and preserve the skip links.
- Move focus deliberately after opening or closing navigation and after validation or request errors.
- Associate field errors with their controls and use status or alert semantics for important updates.
- Keep text labels alongside colour-coded status and provide meaningful alternative text for generated illustrations.
- Use reviewed text tokens that meet the WCAG 2.2 AA normal-text contrast target.
- Respect reduced-motion preferences for scrolling, transitions, and repeated animation.
- Run axe, contrast, responsive, component, lint, format, type, and production-build checks before review.
- Complete the documented keyboard, 375 px, 768 px, 1440 px, and VoiceOver pass before marking the review Done.

The full defect record, automated evidence, supported-width matrix, manual acceptance steps, and limitations are documented in [the NFA-65 responsive and accessibility review](../../docs/responsive-accessibility-review.md).

## NFA-69 content library conventions

- Fetch saved drafts from Server Components and forward only the HTTP-only session cookie to FastAPI.
- Use `/api/v1/drafts` and `/api/v1/drafts/{saved_draft_id}` as the authoritative NFA-68 paths.
- Runtime-validate every response before rendering private draft, source, generation, or image metadata.
- Keep the page number in the URL and request only one bounded backend page at a time.
- Disable prefetch for authenticated draft and pagination links to avoid unnecessary private API requests.
- Load selected-image bytes only through the owner-protected same-origin image gateway.
- Never render storage keys, filesystem paths, credentials, owner IDs, idempotency hashes, or restricted source content.
- Treat a missing draft and a differently owned draft as the same unavailable record.
- Preserve responsive cards, semantic headings, native links, visible focus, alt text, and accessible loading and error states.
- Restore saved text, source, and selected image into the existing editor without automatically publishing or silently saving later keystrokes.

The complete request flow, response validation, pagination, controlled states, editor restoration, accessibility behaviour, tests, and limitations are documented in [the NFA-69 content library guide](../../docs/content-library-interface.md).

## NFA-77 browser testing conventions

- Use only synthetic articles, users, drafts, and images in routine browser tests.
- Reset the deterministic mock API before each scenario and keep Playwright on one worker while it uses shared in-memory state.
- Prove the real Next.js pages and same-origin gateways in Playwright; prove real FastAPI, PostgreSQL, and temporary image storage in Pytest integration suites.
- Never add a real OpenAI key, live CNN call, production user, or production database to browser fixtures.
- Keep exact user-visible assertions for authentication, generation, editing, saving, export, deletion, empty, failure, and cross-user states.
- Do not weaken a failed assertion merely to make CI pass; compare the test against the current public contract first.
- Keep screenshots, videos, traces, and HTML reports in Git-ignored test-output directories.
- Run `npm run test:e2e` locally before review and let GitHub Actions repeat it in Chromium.

The complete scope, isolation model, primary journey, CI behaviour, defect record, commands, and limitations are documented in [the NFA-77 integration and end-to-end testing guide](../../docs/integration-e2e-testing.md).

## Configuration and security

- Keep real secrets in the repository-root `.env`, which Git ignores.
- Never expose `OPENAI_API_KEY` through a `NEXT_PUBLIC_` environment variable.
- Set `API_INTERNAL_BASE_URL=http://localhost:8000` for a manually run frontend. Docker Compose supplies `http://backend:8000` automatically.
- The browser uses the same-origin `/api/auth` gateway for authentication. The backend owns sessions, OpenAI, database, and future authorised-source credentials.
- Treat the frontend redirect as navigation help only. FastAPI must still enforce authorisation for every protected backend operation.
- `NEWS_SOURCE_MODE` remains `fixture` until the live-source No-Go decision is formally replaced.

The production dependency audit completed with no known vulnerabilities on 23 October 2026. NFA-17 updated Next.js and its matching ESLint configuration from 16.4.0 to 16.4.2 to resolve the critical advisories found during the quality-tool setup. The complete development audit still reports a transitive `braces` advisory through `eslint-config-next`; npm does not provide a compatible non-breaking fix. Track the upstream dependency and do not use the suggested forced downgrade because it would make the Next.js toolchain inconsistent.

The project uses ESLint 10, which Next.js 16.4 supports. Some plugins bundled by `eslint-config-next` have not yet added ESLint 10 to their peer-version declarations, so npm can display peer dependency warnings during a clean install. The installed configuration has been verified with `npm run lint` under both the local runtime and the Node 20 Docker image. Do not enable `legacy-peer-deps` or suppress the warnings globally; remove this note when the upstream plugin declarations are updated.

The production build uses Next.js's supported Webpack option with Tailwind's official PostCSS plugin. Local development continues to use the standard `next dev` command.
