# NewsFlow AI Frontend

The NewsFlow AI frontend is a Next.js, React, TypeScript, and Tailwind CSS application. It is located in `apps/web` and provides the user-facing layer of the project. NFA-17 adds automated linting, formatting, type checking, and component testing. NFA-24 adds the complete frontend authentication experience.

The application contains a responsive homepage, registration and login pages, a protected dashboard, session restoration, and logout. It uses original static demonstration content and does not retrieve live CNN information or call the OpenAI API.

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
| `/dashboard`         | Restores the session from the HTTP-only cookie and displays the account workspace.              | Authenticated users only |
| `/api/auth/[action]` | Same-origin server gateway for the FastAPI register, login, logout, and current-user endpoints. | Internal frontend route  |

The dashboard is protected in two layers. `proxy.ts` quickly redirects requests that have no session cookie. The dashboard then asks FastAPI to validate any presented session before returning account content. FastAPI remains the authority for identity and access control.

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

The frontend tests cover the homepage, form validation, registration, login errors, loading feedback, logout and CSRF behaviour, session restoration, gateway failure handling, and dashboard route protection. They use synthetic values and mocked network responses, so they make no real account, network, or paid API calls.

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
├── __tests__/              # Homepage and authentication tests
├── app/
│   ├── api/auth/[action]/   # Same-origin FastAPI authentication gateway
│   ├── dashboard/           # Protected account workspace
│   ├── login/               # Login page
│   ├── register/            # Registration page
│   ├── globals.css          # Tailwind import and global design tokens
│   ├── layout.tsx           # Root layout, fonts, and metadata
│   └── page.tsx             # Public homepage
├── components/
│   ├── auth/                # Reusable forms, page shell, and logout control
│   ├── brand-mark.tsx       # Reusable project identity
│   ├── product-preview.tsx  # Fixture-mode product demonstration
│   └── workflow-step.tsx    # Reusable workflow item
├── lib/                     # Authentication contracts and server utilities
├── public/                  # Static assets
├── proxy.ts                 # Optimistic dashboard cookie check
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
