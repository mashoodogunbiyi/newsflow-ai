# NewsFlow AI Frontend

The NewsFlow AI frontend is a Next.js, React, TypeScript, and Tailwind CSS application. It is located in `apps/web` and provides the user-facing layer of the project. NFA-17 adds automated linting, formatting, type checking, and component testing. NFA-24 adds the complete frontend authentication experience. NFA-56 adds the reusable authenticated application shell, responsive navigation, primary routes, shared interface components, and protected loading and error states. NFA-57 adds the responsive authorised-article dashboard and FastAPI catalogue integration. NFA-58 adds approved category filtering and URL-based browsing state. NFA-59 adds UUID-only article selection, protected detail retrieval, and the responsive source information panel. NFA-60 adds accessible tone and length controls, the same-origin generation gateway, duplicate protection, safe response validation, and controlled request feedback. NFA-61 adds a reusable text and image generation lifecycle, deliberate retries, accessible announcements, and stale-response protection. NFA-62 adds the accessible multiline draft editor, text-only live preview, source and warning preservation, and local unsaved-change protection.

The application contains a responsive homepage, registration and login pages, a protected workspace, session restoration, and logout. The workspace includes Dashboard, Create Post, Content Library, and Account routes. The dashboard retrieves rights-approved synthetic article metadata from FastAPI and does not retrieve live CNN information. The Create Post route restores the selected article from its UUID, presents permitted source information and current generation readiness, lets an authorised user request a private LinkedIn draft using supported tone and length choices, and opens a responsive editor after a valid result. The editor updates its local preview without another provider request and never receives an OpenAI credential.

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

| Route                | Purpose                                                                                         | Access                   |
| -------------------- | ----------------------------------------------------------------------------------------------- | ------------------------ |
| `/register`          | Validates account details and creates an account through FastAPI.                               | Public                   |
| `/login`             | Verifies credentials and starts a secure session.                                               | Public                   |
| `/dashboard`         | Displays the searchable, category-filtered, paginated, rights-approved article catalogue.       | Authenticated users only |
| `/generate`          | Reviews a selected source and submits validated LinkedIn draft preferences.                     | Authenticated users only |
| `/library`           | Provides the protected foundation for owner-scoped saved content.                               | Authenticated users only |
| `/account`           | Displays account security and ownership information.                                            | Authenticated users only |
| `/api/auth/[action]` | Same-origin server gateway for the FastAPI register, login, logout, and current-user endpoints. | Internal frontend route  |
| `/api/generations`   | Same-origin gateway for CSRF-protected private LinkedIn draft requests.                         | Internal frontend route  |

The workspace is protected in two layers. `proxy.ts` quickly redirects requests that have no session cookie. The shared server layout then asks FastAPI to validate any presented session before returning account content. FastAPI remains the authority for identity and access control.

Logout reads the separate, non-secret CSRF cookie and submits it in the required `X-CSRF-Token` header. The secure session identifier remains in an HTTP-only cookie and is not accessible to client-side JavaScript. The frontend does not put passwords, session identifiers, or account secrets in `localStorage` or `sessionStorage`.

## Quality checks

NFA-17 uses ESLint with the Next.js Core Web Vitals and TypeScript rules, Prettier for formatting, TypeScript for static type checking, and Vitest with React Testing Library and jsdom for component tests.

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
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

The frontend tests cover the homepage, form validation, registration, login errors, loading feedback, logout and CSRF behaviour, session restoration, gateway failure handling, workspace route protection, active navigation, mobile menu behavior, reusable components, safe error recovery, server-layout authentication, article response validation, approved-field cards, source-link safety, category selection, URL-state restoration, pagination resets, UUID-only selection, detail retrieval, source-panel states, generation preferences, duplicate protection, usage limits, authentication recovery, generation gateway allowlists, state transitions, provider timeouts, deliberate retries, stale-response protection, text-specific and image-specific status messages, draft editing, preview synchronisation, warning preservation, unsaved navigation, and literal HTML-like text rendering. They use synthetic values and mocked network responses, so they make no real account, network, or paid API calls.

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
├── app/
│   ├── api/                  # Same-origin FastAPI authentication and generation gateways
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
│   ├── generation/          # Tone, length, submission, and generation feedback controls
│   ├── layout/              # Application shell, navigation, page header, and auth fallback
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
